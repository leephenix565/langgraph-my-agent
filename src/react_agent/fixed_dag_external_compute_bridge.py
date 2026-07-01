"""Default-off fixed-DAG external compute demo bridge.

This compatibility module preserves the historical import path while the
boundary internals live under ``react_agent.fixed_dag.external``.  It only
calls explicitly allowlisted loopback production `/v1/agent/compute`
endpoints and never calls `/v1/agent/invoke`.
"""

from __future__ import annotations

import http.client
import importlib
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from react_agent.fixed_dag.external import registry as _external_registry
from react_agent.fixed_dag.external.constants import (
    COMPUTE_PATH,
    EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION,
    EXTERNAL_AGENT_REQUEST_SCHEMA_VERSION,
    EXTERNAL_COMPUTE_DEFAULT_SOURCE,
    EXTERNAL_COMPUTE_DEMO_SOURCE,
    MAX_RESPONSE_BYTES,
)
from react_agent.fixed_dag.external.default_runtime import _timeout_from_context
from react_agent.fixed_dag.external.request import (
    _steps,
    build_external_compute_request,
    normalize_demo_allowlist,
)
from react_agent.fixed_dag.external.safety import (
    _mapped_temporal_failure,
    _raw_response_temporal_failure,
    _safe_code,
    validate_demo_entry,
)
from react_agent.fixed_dag.external.transport import _post_json_loopback
from react_agent.fixed_dag.external.types import ExternalComputeDemoEntry, Transport
from react_agent.fixed_dag_contracts import (
    CONCLUSION_OBJECT_SCHEMA_VERSION,
    DATA_BUNDLE_SCHEMA_VERSION,
    DECISION_RESULT_SCHEMA_VERSION,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_COMPOSITE_SCHEMA_VERSION,
    ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
    L2_CONCLUSION_AGENT_IDS,
    REPORT_RESULT_SCHEMA_VERSION,
)
from react_agent.fixed_dag_external_adapter import (
    ADAPTER_FAILURE_SCHEMA_VERSION,
    map_external_response_to_fixed_dag_object,
)

_external_registry = importlib.reload(_external_registry)
DEMO_COMPUTE_SERVICE_REGISTRY = _external_registry.DEMO_COMPUTE_SERVICE_REGISTRY
_demo_base_url = _external_registry._demo_base_url

_SAFE_TELEMETRY_INT_FIELDS = {
    "agent_total_ms",
    "db_query_count",
    "db_total_ms",
    "provider_call_count",
    "provider_total_ms",
}
_SAFE_TELEMETRY_BOOL_FIELDS = {"cache_hit", "timeout_flag"}
_SAFE_TELEMETRY_TEXT_FIELDS = {"fallback_reason", "telemetry_unavailable_reason"}


def _safe_non_negative_int(value: Any, *, max_value: int = 86_400_000) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return min(parsed, max_value)


def sanitize_external_compute_telemetry(response: Mapping[str, Any]) -> dict[str, Any]:
    """Project optional external service timing metadata into a public-safe shape."""
    raw = response.get("telemetry")
    telemetry = raw if isinstance(raw, Mapping) else {}
    sanitized: dict[str, Any] = {}
    for field in _SAFE_TELEMETRY_INT_FIELDS:
        value = _safe_non_negative_int(telemetry.get(field))
        if value is not None:
            sanitized[field] = value
    for field in _SAFE_TELEMETRY_BOOL_FIELDS:
        value = telemetry.get(field)
        if isinstance(value, bool):
            sanitized[field] = value
    for field in _SAFE_TELEMETRY_TEXT_FIELDS:
        text = str(telemetry.get(field) or "").strip()
        if text:
            sanitized[field] = _safe_code(text)

    elapsed = _safe_non_negative_int(response.get("elapsed_ms"))
    if elapsed is not None and "agent_total_ms" not in sanitized:
        sanitized["agent_total_ms"] = elapsed

    metadata = response.get("metadata")
    if isinstance(metadata, Mapping):
        provider_invoked = metadata.get("provider_invoked")
        if isinstance(provider_invoked, bool) and "provider_call_count" not in sanitized:
            sanitized["provider_call_count"] = 1 if provider_invoked else 0
        if metadata.get("provider_output_retained") is False:
            sanitized.setdefault("telemetry_unavailable_reason", "provider_timing_not_reported")
    if not sanitized:
        sanitized["telemetry_unavailable_reason"] = "service_telemetry_not_reported"
    return sanitized


def invoke_external_compute(
    entry: ExternalComputeDemoEntry,
    *,
    question: str,
    as_of: str,
    request_id: str,
    timeout_seconds: float,
    demo: bool = True,
    agent_task: Mapping[str, Any] | None = None,
    upstream_outputs: Mapping[str, Any] | None = None,
    dimension_results: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
    report_input_bundle: Mapping[str, Any] | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Call one allowlisted compute endpoint and map its response safely."""
    started = time.monotonic()
    valid, reason = validate_demo_entry(entry)
    if not valid:
        return _failed_entry(entry.agent_id, reason)
    request = build_external_compute_request(
        entry,
        question=question,
        as_of=as_of,
        request_id=request_id,
        demo=demo,
        agent_task=agent_task,
        upstream_outputs=upstream_outputs,
        dimension_results=dimension_results,
        decision_result=decision_result,
        report_input_bundle=report_input_bundle,
    )
    try:
        response = (
            transport(entry, request, timeout_seconds)
            if transport is not None
            else _post_json_loopback(entry, request, timeout_seconds)
        )
    except TimeoutError:
        return _failed_entry(entry.agent_id, "timeout")
    except RuntimeError as exc:
        return _failed_entry(entry.agent_id, str(exc) or "runtime_error")
    except ValueError as exc:
        return _failed_entry(entry.agent_id, str(exc) or "invalid_response")
    except (ConnectionError, OSError, http.client.HTTPException):
        return _failed_entry(entry.agent_id, "connection_error")
    except Exception as exc:  # pragma: no cover - exact network failures are platform-specific.
        return _failed_entry(entry.agent_id, _safe_code(type(exc).__name__))
    if not isinstance(response, Mapping):
        return _failed_entry(entry.agent_id, "invalid_json")
    temporal_failure = _raw_response_temporal_failure(response, as_of)
    if temporal_failure:
        return _failed_entry(entry.agent_id, temporal_failure)
    mapped = map_external_response_to_fixed_dag_object(response)
    if mapped.get("schema") == ADAPTER_FAILURE_SCHEMA_VERSION:
        return _failed_entry(entry.agent_id, f"adapter_mapping_failed:{mapped.get('reason')}")
    temporal_failure = _mapped_temporal_failure(mapped, as_of)
    if temporal_failure:
        return _failed_entry(entry.agent_id, temporal_failure)
    mapped_schema = str(mapped.get("schema") or "")
    mapped_status = str(mapped.get("status") or "")
    return {
        "agent_id": entry.agent_id,
        "status": "pass",
        "mapped": mapped,
        "failure_code": "",
        "warning": "",
        "agent_task": dict(agent_task) if isinstance(agent_task, Mapping) else {},
        "elapsed_ms": int(round((time.monotonic() - started) * 1000)),
        "mapped_schema": mapped_schema,
        "mapped_status": mapped_status,
        "telemetry": sanitize_external_compute_telemetry(response),
    }


def _failed_entry(agent_id: str, failure_code: str) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "status": "failed",
        "mapped": None,
        "failure_code": _safe_code(failure_code),
        "warning": f"external_compute_demo_failed:{_safe_code(failure_code)}",
    }


def _apply_mapped_result(
    *,
    agent_id: str,
    mapped: Mapping[str, Any],
    data_bundle: dict[str, Any] | None,
    entity_relation_bundle: dict[str, Any] | None,
    l2_conclusions: dict[str, Any],
    dimension_results: dict[str, Any],
    decision_result: dict[str, Any],
    report_result: dict[str, Any],
) -> tuple[bool, str]:
    schema = mapped.get("schema")
    if agent_id == "financial_data_service":
        if schema != DATA_BUNDLE_SCHEMA_VERSION:
            return False, "mapped_data_bundle_schema_mismatch"
        if data_bundle is None:
            return False, "data_bundle_target_missing"
        data_bundle.clear()
        data_bundle.update(dict(mapped))
        return True, "ok"

    if agent_id == "entity_relation_extractor":
        if schema != ENTITY_RELATION_BUNDLE_SCHEMA_VERSION:
            return False, "mapped_entity_relation_schema_mismatch"
        if entity_relation_bundle is None:
            return False, "entity_relation_bundle_target_missing"
        entity_relation_bundle.clear()
        entity_relation_bundle.update(dict(mapped))
        return True, "ok"

    if agent_id in L2_CONCLUSION_AGENT_IDS:
        if schema != CONCLUSION_OBJECT_SCHEMA_VERSION or mapped.get("agent_id") != agent_id:
            return False, "mapped_l2_schema_or_identity_mismatch"
        l2_conclusions[agent_id] = dict(mapped)
        return True, "ok"

    if agent_id in set(DIMENSION_COMPOSITE_AGENT_IDS.values()):
        if schema != DIMENSION_COMPOSITE_SCHEMA_VERSION or mapped.get("agent_id") != agent_id:
            return False, "mapped_l3_schema_or_identity_mismatch"
        dimension = str(mapped.get("dimension") or "")
        if not dimension:
            return False, "mapped_l3_dimension_missing"
        dimension_results[dimension] = dict(mapped)
        return True, "ok"

    if agent_id == "decision_synthesizer":
        if schema != DECISION_RESULT_SCHEMA_VERSION:
            return False, "mapped_decision_schema_mismatch"
        decision_result.clear()
        decision_result.update(dict(mapped))
        return True, "ok"

    if agent_id == "report_generator":
        if schema != REPORT_RESULT_SCHEMA_VERSION:
            return False, "mapped_report_schema_mismatch"
        report_result.clear()
        report_result.update(dict(mapped))
        return True, "ok"

    return False, "unsupported_demo_agent"


def apply_mapped_external_compute_result(
    *,
    agent_id: str,
    mapped: Mapping[str, Any],
    data_bundle: dict[str, Any] | None,
    entity_relation_bundle: dict[str, Any] | None,
    l2_conclusions: dict[str, Any],
    dimension_results: dict[str, Any],
    decision_result: dict[str, Any],
    report_result: dict[str, Any],
) -> tuple[bool, str]:
    """Apply a mapped external `/compute` result to fixed-DAG state containers."""
    return _apply_mapped_result(
        agent_id=agent_id,
        mapped=mapped,
        data_bundle=data_bundle,
        entity_relation_bundle=entity_relation_bundle,
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
        decision_result=decision_result,
        report_result=report_result,
    )


def run_external_compute_for_plan(
    plan: Mapping[str, Any],
    *,
    question: str,
    as_of: str,
    context: Any,
    l2_conclusions: Mapping[str, Any],
    data_bundle: Mapping[str, Any] | None = None,
    entity_relation_bundle: Mapping[str, Any] | None = None,
    dimension_results: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
    report_result: Mapping[str, Any] | None = None,
    report_input_bundle: Mapping[str, Any] | None = None,
    agent_tasks: Mapping[str, Any] | None = None,
    stages: tuple[str, ...] = ("l2_analysis", "dimension_composite"),
    allowlist_override: tuple[str, ...] | None = None,
    entry_registry: Mapping[str, ExternalComputeDemoEntry] | None = None,
    runtime_source: str = EXTERNAL_COMPUTE_DEMO_SOURCE,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Run demo/default compute calls for allowlisted agents present in a plan."""
    allowlist = normalize_demo_allowlist(
        allowlist_override
        if allowlist_override is not None
        else getattr(context, "external_compute_demo_allowlist", ())
    )
    registry = dict(entry_registry or DEMO_COMPUTE_SERVICE_REGISTRY)
    is_runtime_default = runtime_source == EXTERNAL_COMPUTE_DEFAULT_SOURCE
    updated_l2 = {str(agent_id): dict(value) for agent_id, value in l2_conclusions.items()}
    updated_data_bundle = dict(data_bundle) if isinstance(data_bundle, Mapping) else {}
    updated_entity_relation_bundle = (
        dict(entity_relation_bundle)
        if isinstance(entity_relation_bundle, Mapping)
        else {}
    )
    updated_dimensions = {
        str(dimension): dict(value)
        for dimension, value in (dimension_results or {}).items()
    }
    updated_decision = dict(decision_result or {})
    updated_report = dict(report_result or {})
    result = {
        "data_bundle": updated_data_bundle,
        "entity_relation_bundle": updated_entity_relation_bundle,
        "l2_conclusions": updated_l2,
        "dimension_results": updated_dimensions,
        "decision_result": updated_decision,
        "report_result": updated_report,
        "step_updates": {},
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "warnings": [],
        "latency_ms_by_agent": {},
        "agent_telemetry_by_agent": {},
        "mapped_schema_by_agent": {},
        "mapped_status_by_agent": {},
    }
    if not allowlist:
        return result

    allowed = set(allowlist)
    stage_set = set(stages)
    for step in _steps(plan):
        stage = str(step.get("stage") or "")
        if stage not in stage_set:
            continue
        agent_id = str(step.get("agent_id") or "")
        if agent_id not in allowed:
            continue
        entry = registry.get(agent_id)
        step_id = str(step.get("id") or agent_id)
        agent_task = {}
        if isinstance(agent_tasks, Mapping):
            raw_task = agent_tasks.get(step_id) or agent_tasks.get(agent_id)
            if isinstance(raw_task, Mapping):
                agent_task = dict(raw_task)
        if entry is None:
            warning = "external_compute_demo_failed:agent_not_registered"
            result["warnings"].append(warning)
            result["failed_agents"].append(agent_id)
            result["step_updates"][step_id] = {"warning": warning}
            continue

        timeout = _timeout_from_context(context, entry)
        upstream_outputs = updated_l2 if stage == "dimension_composite" else None
        mapped_result = invoke_external_compute(
            entry,
            question=question,
            as_of=as_of,
            request_id=(
                f"runtime-default-{agent_id}"
                if is_runtime_default
                else f"r8-12-demo-{agent_id}"
            ),
            timeout_seconds=timeout,
            demo=not is_runtime_default,
            agent_task=agent_task,
            upstream_outputs=upstream_outputs,
            dimension_results=updated_dimensions if stage == "decision" else None,
            decision_result=updated_decision if stage == "report" else None,
            report_input_bundle=report_input_bundle if stage == "report" else None,
            transport=transport,
        )
        result["called_agents"].append(agent_id)
        if isinstance(mapped_result.get("elapsed_ms"), int):
            result["latency_ms_by_agent"][agent_id] = int(mapped_result["elapsed_ms"])
        telemetry = mapped_result.get("telemetry")
        if isinstance(telemetry, Mapping):
            result["agent_telemetry_by_agent"][agent_id] = dict(telemetry)
        if mapped_result.get("mapped_schema"):
            result["mapped_schema_by_agent"][agent_id] = str(mapped_result["mapped_schema"])
        if mapped_result.get("mapped_status"):
            result["mapped_status_by_agent"][agent_id] = str(mapped_result["mapped_status"])
        mapped = mapped_result.get("mapped")
        if mapped_result.get("status") != "pass" or not isinstance(mapped, Mapping):
            warning = str(mapped_result.get("warning") or "external_compute_demo_failed")
            if is_runtime_default:
                warning = warning.replace(
                    "external_compute_demo_failed",
                    "external_compute_default_failed",
                )
            result["warnings"].append(warning)
            result["failed_agents"].append(agent_id)
            result["step_updates"][step_id] = {"warning": warning}
            continue

        applied, reason = _apply_mapped_result(
            agent_id=agent_id,
            mapped=mapped,
            data_bundle=updated_data_bundle,
            entity_relation_bundle=updated_entity_relation_bundle,
            l2_conclusions=updated_l2,
            dimension_results=updated_dimensions,
            decision_result=updated_decision,
            report_result=updated_report,
        )
        if not applied:
            warning = f"external_compute_demo_failed:{_safe_code(reason)}"
            if is_runtime_default:
                warning = warning.replace(
                    "external_compute_demo_failed",
                    "external_compute_default_failed",
                )
            result["warnings"].append(warning)
            result["failed_agents"].append(agent_id)
            result["step_updates"][step_id] = {"warning": warning}
            continue

        result["mapped_agents"].append(agent_id)
        result["step_updates"][step_id] = {
            "status": "complete",
            "summary": (
                "运行时默认 L4 /compute 路径已返回结构化结果并完成固定 DAG 适配映射。"
                if is_runtime_default
                else "演示模式已读取生产 /compute 结构化结果并完成固定 DAG 适配映射。"
            ),
            "warning": (
                "external_compute_default_runtime_binding"
                if is_runtime_default
                else "external_compute_demo_default_off_not_runtime_binding"
            ),
            "agent_task": agent_task,
        }

    return result


def runtime_compute_entries_from_bindings(
    bindings: Mapping[str, Any] | None = None,
) -> dict[str, ExternalComputeDemoEntry]:
    """Build compute entries for runtime-default external L4 bindings."""
    from react_agent.fixed_dag_runtime_registry import (  # noqa: PLC0415
        external_compute_default_bindings,
    )

    entries: dict[str, ExternalComputeDemoEntry] = {}
    for binding in external_compute_default_bindings(bindings):
        agent_id = binding["agent_id"]
        template = DEMO_COMPUTE_SERVICE_REGISTRY.get(agent_id)
        if template is None:
            continue
        parsed = urlsplit(binding["default_url"])
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.port is None
            or parsed.path != COMPUTE_PATH
            or parsed.query
            or parsed.fragment
        ):
            continue
        base_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        entries[agent_id] = ExternalComputeDemoEntry(
            agent_id=agent_id,
            base_url=base_url,
            compute_path=COMPUTE_PATH,
            expected_payload=template.expected_payload,
            dimension=template.dimension,
            external_agent_id=binding["external_agent_id"],
            default_target=template.default_target,
            timeout_seconds=template.timeout_seconds,
        )
    return entries


def merge_external_compute_demo_runs(*runs: Mapping[str, Any]) -> dict[str, Any]:
    """Merge public-safe run counters from multiple demo bridge phases."""
    merged = {
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "warnings": [],
        "latency_ms_by_agent": {},
        "agent_telemetry_by_agent": {},
        "mapped_schema_by_agent": {},
        "mapped_status_by_agent": {},
    }
    for run in runs:
        for key in merged:
            if key.endswith("_by_agent"):
                continue
            for item in run.get(key, []) if isinstance(run, Mapping) else []:
                text = str(item or "")
                if text and text not in merged[key]:
                    merged[key].append(text)
        for key in (
            "latency_ms_by_agent",
            "agent_telemetry_by_agent",
            "mapped_schema_by_agent",
            "mapped_status_by_agent",
        ):
            raw_mapping = run.get(key, {}) if isinstance(run, Mapping) else {}
            if not isinstance(raw_mapping, Mapping):
                continue
            for agent_id, value in raw_mapping.items():
                if key == "latency_ms_by_agent":
                    parsed = _safe_non_negative_int(value)
                    if parsed is not None:
                        merged[key][str(agent_id)] = parsed
                    continue
                if isinstance(value, Mapping):
                    merged[key][str(agent_id)] = dict(value)
                else:
                    text = str(value or "")
                    if text:
                        merged[key][str(agent_id)] = text
    return merged


__all__ = [
    "COMPUTE_PATH",
    "DEMO_COMPUTE_SERVICE_REGISTRY",
    "EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION",
    "EXTERNAL_AGENT_REQUEST_SCHEMA_VERSION",
    "EXTERNAL_COMPUTE_DEMO_SOURCE",
    "EXTERNAL_COMPUTE_DEFAULT_SOURCE",
    "ExternalComputeDemoEntry",
    "MAX_RESPONSE_BYTES",
    "apply_mapped_external_compute_result",
    "build_external_compute_request",
    "invoke_external_compute",
    "merge_external_compute_demo_runs",
    "normalize_demo_allowlist",
    "runtime_compute_entries_from_bindings",
    "run_external_compute_for_plan",
    "sanitize_external_compute_telemetry",
    "validate_demo_entry",
]
