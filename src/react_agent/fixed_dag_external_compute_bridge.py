"""Default-off fixed-DAG external compute demo bridge.

This module is intentionally narrow: it only calls explicitly allowlisted
loopback production `/v1/agent/compute` endpoints and maps responses through the
pure fixed-DAG external adapter. It never calls `/v1/agent/invoke`.
"""

from __future__ import annotations

import http.client
import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from react_agent.fixed_dag_contracts import (
    AGENT_TASK_SCHEMA_VERSION,
    CONCLUSION_OBJECT_SCHEMA_VERSION,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_COMPOSITE_SCHEMA_VERSION,
    L2_CONCLUSION_AGENT_IDS,
    validate_agent_task,
)
from react_agent.fixed_dag_external_adapter import (
    ADAPTER_FAILURE_SCHEMA_VERSION,
    map_external_response_to_fixed_dag_object,
)

EXTERNAL_COMPUTE_DEMO_SOURCE = "external_compute_demo_bridge"
EXTERNAL_AGENT_REQUEST_SCHEMA_VERSION = "external_agent_request_v0"
EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION = "external_agent_compute_v0"
COMPUTE_PATH = "/v1/agent/compute"
MAX_RESPONSE_BYTES = 2_000_000


@dataclass(frozen=True)
class ExternalComputeDemoEntry:
    """Demo-only endpoint metadata for one fixed-DAG compute candidate."""

    agent_id: str
    base_url: str
    compute_path: str
    expected_payload: str
    dimension: str
    external_agent_id: str
    default_target: str = "600519.SH"
    timeout_seconds: float = 20.0


Transport = Callable[
    [ExternalComputeDemoEntry, Mapping[str, Any], float],
    Mapping[str, Any],
]


def _demo_base_url(agent_id: str, default: str) -> str:
    env_name = f"EXTERNAL_COMPUTE_DEMO_URL_{agent_id.upper()}"
    return str(os.getenv(env_name, default) or default).strip().rstrip("/")


DEMO_COMPUTE_SERVICE_REGISTRY: dict[str, ExternalComputeDemoEntry] = {
    "value_traditional_valuation": ExternalComputeDemoEntry(
        agent_id="value_traditional_valuation",
        base_url="http://127.0.0.1:10000",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_traditional",
    ),
    "value_ml_valuation": ExternalComputeDemoEntry(
        agent_id="value_ml_valuation",
        base_url="http://127.0.0.1:10001",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_ml",
    ),
    "value_meta_valuation": ExternalComputeDemoEntry(
        agent_id="value_meta_valuation",
        base_url="http://127.0.0.1:10002",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_meta",
    ),
    "value_research_synthesis": ExternalComputeDemoEntry(
        agent_id="value_research_synthesis",
        base_url="http://127.0.0.1:10006",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="analyst_research",
    ),
    "market_stock_technical": ExternalComputeDemoEntry(
        agent_id="market_stock_technical",
        base_url="http://127.0.0.1:10009",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="technical_stock",
    ),
    "market_capital_flow_chip": ExternalComputeDemoEntry(
        agent_id="market_capital_flow_chip",
        base_url="http://127.0.0.1:10022",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="money_flow",
    ),
    "sentiment_company_radar": ExternalComputeDemoEntry(
        agent_id="sentiment_company_radar",
        base_url="http://127.0.0.1:10020",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="company_sentiment_radar",
    ),
    "market_ipo_investor_behavior": ExternalComputeDemoEntry(
        agent_id="market_ipo_investor_behavior",
        base_url="http://127.0.0.1:10008",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="ipo_investor_behavior",
    ),
    "risk_identification": ExternalComputeDemoEntry(
        agent_id="risk_identification",
        base_url="http://127.0.0.1:10010",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="market_risk_reasoning",
    ),
    "risk_compliance_review": ExternalComputeDemoEntry(
        agent_id="risk_compliance_review",
        base_url="http://127.0.0.1:10011",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="announcement_compliance",
    ),
    "risk_financial_fraud": ExternalComputeDemoEntry(
        agent_id="risk_financial_fraud",
        base_url="http://127.0.0.1:10013",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="financial_fraud_agent",
    ),
    "risk_crash": ExternalComputeDemoEntry(
        agent_id="risk_crash",
        base_url="http://127.0.0.1:10012",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="crash_risk",
    ),
    "macro_analysis": ExternalComputeDemoEntry(
        agent_id="macro_analysis",
        base_url="http://127.0.0.1:10014",
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="macro",
        external_agent_id="macro_analysis",
        default_target="CN_A_SHARE_MACRO",
    ),
    "value_composite": ExternalComputeDemoEntry(
        agent_id="value_composite",
        base_url=_demo_base_url("value_composite", "http://127.0.0.1:10015"),
        compute_path=COMPUTE_PATH,
        expected_payload="dimension_conclusion_v1",
        dimension="value",
        external_agent_id="composite_valuation",
    ),
    "market_composite": ExternalComputeDemoEntry(
        agent_id="market_composite",
        base_url=_demo_base_url("market_composite", "http://127.0.0.1:10023"),
        compute_path=COMPUTE_PATH,
        expected_payload="dimension_conclusion_v1",
        dimension="market",
        external_agent_id="market_composite",
    ),
    "risk_composite": ExternalComputeDemoEntry(
        agent_id="risk_composite",
        base_url=_demo_base_url("risk_composite", "http://127.0.0.1:10016"),
        compute_path=COMPUTE_PATH,
        expected_payload="risk_conclusion_v1",
        dimension="risk",
        external_agent_id="risk_synthesis",
    ),
    "macro_composite": ExternalComputeDemoEntry(
        agent_id="macro_composite",
        base_url=_demo_base_url("macro_composite", "http://127.0.0.1:10024"),
        compute_path=COMPUTE_PATH,
        expected_payload="macro_conclusion_v1",
        dimension="macro",
        external_agent_id="macro_synthesis_service",
        default_target="CN_A_SHARE_MACRO",
    ),
}


def normalize_demo_allowlist(value: Any) -> tuple[str, ...]:
    """Normalize comma-separated or iterable allowlist values into agent ids."""
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, tuple | list | set):
        raw_items = list(value)
    else:
        raw_items = []
    items: list[str] = []
    for raw in raw_items:
        agent_id = str(raw or "").strip()
        if agent_id and agent_id not in items:
            items.append(agent_id)
    return tuple(items)


def _safe_code(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_:-]+", "_", text)
    return text[:120] or "external_compute_demo_failure"


def _steps(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_steps = plan.get("dag_steps", plan.get("steps", []))
    if not isinstance(raw_steps, list):
        return []
    return [step for step in raw_steps if isinstance(step, Mapping)]


def _target_for_entry(entry: ExternalComputeDemoEntry, question: str) -> str:
    if entry.default_target != "600519.SH":
        return entry.default_target
    match = re.search(r"\b\d{6}\.(?:SH|SZ|BJ)\b", question.upper())
    if match:
        return match.group(0)
    return entry.default_target


def validate_demo_entry(entry: ExternalComputeDemoEntry) -> tuple[bool, str]:
    """Validate that a demo entry can only target loopback compute endpoints."""
    parsed = urlsplit(entry.base_url)
    if parsed.scheme != "http":
        return False, "non_http_base_url"
    if parsed.hostname != "127.0.0.1":
        return False, "non_loopback_host"
    if parsed.username or parsed.password:
        return False, "credentials_not_allowed"
    if not parsed.port:
        return False, "port_missing"
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return False, "base_url_must_not_include_path"
    if entry.compute_path != COMPUTE_PATH or "invoke" in entry.compute_path.lower():
        return False, "compute_path_not_allowed"
    if entry.agent_id not in DEMO_COMPUTE_SERVICE_REGISTRY:
        return False, "agent_not_registered"
    return True, "ok"


def build_external_compute_request(
    entry: ExternalComputeDemoEntry,
    *,
    question: str,
    as_of: str,
    request_id: str,
    agent_task: Mapping[str, Any] | None = None,
    upstream_outputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a production compute request for an allowlisted demo agent."""
    target = _target_for_entry(entry, question)
    safe_agent_task: dict[str, Any] | None = None
    if isinstance(agent_task, Mapping):
        valid_task, _task_reason = validate_agent_task(agent_task)
        if valid_task:
            safe_agent_task = dict(agent_task)
    request = {
        "schema_version": EXTERNAL_AGENT_REQUEST_SCHEMA_VERSION,
        "request_id": request_id,
        "agent_id": entry.agent_id,
        "external_agent_id": entry.external_agent_id,
        "target": target,
        "as_of": as_of,
        "context": {
            "fixed_dag_id": entry.agent_id,
            "dimension": entry.dimension,
            "environment": "production",
            "demo": True,
            "user_question": question,
            "task_instruction": (
                safe_agent_task.get("task_instruction", "")
                if safe_agent_task is not None
                else ""
            ),
        },
        "options": {
            "smoke": False,
            "demo": True,
            "environment": "production",
            "allow_llm": False,
            "return_tool_result": True,
        },
    }
    if safe_agent_task is not None:
        request["agent_task"] = safe_agent_task
        request["context"]["agent_task"] = safe_agent_task
        request["context"]["agent_task_schema_version"] = AGENT_TASK_SCHEMA_VERSION
    safe_upstream_outputs = _safe_upstream_outputs(
        upstream_outputs,
        safe_agent_task,
    )
    if safe_upstream_outputs:
        request["context"]["upstream_outputs"] = safe_upstream_outputs
        request["context"]["upstream_output_schema"] = "fixed_dag_mapped_outputs_v1"
    return request


def _safe_evidence_items(value: Any, *, limit: int = 4) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for item in value[:limit]:
        if not isinstance(item, Mapping):
            continue
        safe_item = {
            key: item[key]
            for key in (
                "id",
                "fact",
                "source",
                "as_of",
                "data_as_of",
                "unit",
                "value",
            )
            if key in item
        }
        if safe_item:
            items.append(safe_item)
    return items


def _safe_upstream_output(agent_id: str, value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("agent_id") != agent_id:
        return None
    safe = {
        key: value.get(key)
        for key in (
            "schema",
            "schema_version",
            "agent_id",
            "dimension",
            "role",
            "status",
            "stance",
            "confidence",
            "risk_score",
            "summary",
            "as_of",
            "data_as_of",
        )
        if key in value
    }
    evidence = _safe_evidence_items(value.get("evidence"))
    if evidence:
        safe["evidence"] = evidence
    return safe


def _safe_upstream_outputs(
    outputs: Mapping[str, Any] | None,
    agent_task: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(outputs, Mapping):
        return {}
    upstream_ids: list[str] = []
    if isinstance(agent_task, Mapping) and isinstance(
        agent_task.get("upstream_agent_ids"),
        list,
    ):
        upstream_ids = [
            str(agent_id)
            for agent_id in agent_task["upstream_agent_ids"]
            if isinstance(agent_id, str)
        ]
    if not upstream_ids:
        upstream_ids = [str(agent_id) for agent_id in outputs if isinstance(agent_id, str)]
    safe_outputs: dict[str, dict[str, Any]] = {}
    for agent_id in upstream_ids[:24]:
        safe_output = _safe_upstream_output(agent_id, outputs.get(agent_id))
        if safe_output is not None:
            safe_outputs[agent_id] = safe_output
    return safe_outputs


def _post_json_loopback(
    entry: ExternalComputeDemoEntry,
    payload: Mapping[str, Any],
    timeout_seconds: float,
) -> Mapping[str, Any]:
    valid, reason = validate_demo_entry(entry)
    if not valid:
        raise ValueError(reason)
    parsed = urlsplit(entry.base_url)
    assert parsed.hostname == "127.0.0.1"
    assert parsed.port is not None
    body = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
    connection = http.client.HTTPConnection(
        parsed.hostname,
        parsed.port,
        timeout=timeout_seconds,
    )
    try:
        connection.request(
            "POST",
            entry.compute_path,
            body=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"http_status_{response.status}")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RuntimeError("response_too_large")
    finally:
        connection.close()
    try:
        parsed_body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_json") from exc
    if not isinstance(parsed_body, Mapping):
        raise ValueError("json_not_object")
    return parsed_body


def invoke_external_compute(
    entry: ExternalComputeDemoEntry,
    *,
    question: str,
    as_of: str,
    request_id: str,
    timeout_seconds: float,
    agent_task: Mapping[str, Any] | None = None,
    upstream_outputs: Mapping[str, Any] | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Call one allowlisted compute endpoint and map its response safely."""
    valid, reason = validate_demo_entry(entry)
    if not valid:
        return _failed_entry(entry.agent_id, reason)
    request = build_external_compute_request(
        entry,
        question=question,
        as_of=as_of,
        request_id=request_id,
        agent_task=agent_task,
        upstream_outputs=upstream_outputs,
    )
    try:
        response = (
            transport(entry, request, timeout_seconds)
            if transport is not None
            else _post_json_loopback(entry, request, timeout_seconds)
        )
    except TimeoutError:
        return _failed_entry(entry.agent_id, "timeout")
    except Exception as exc:  # pragma: no cover - exact network failures are platform-specific.
        return _failed_entry(entry.agent_id, _safe_code(type(exc).__name__))
    if not isinstance(response, Mapping):
        return _failed_entry(entry.agent_id, "invalid_json")
    mapped = map_external_response_to_fixed_dag_object(response)
    if mapped.get("schema") == ADAPTER_FAILURE_SCHEMA_VERSION:
        return _failed_entry(entry.agent_id, f"adapter_mapping_failed:{mapped.get('reason')}")
    return {
        "agent_id": entry.agent_id,
        "status": "pass",
        "mapped": mapped,
        "failure_code": "",
        "warning": "",
        "agent_task": dict(agent_task) if isinstance(agent_task, Mapping) else {},
    }


def _failed_entry(agent_id: str, failure_code: str) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "status": "failed",
        "mapped": None,
        "failure_code": _safe_code(failure_code),
        "warning": f"external_compute_demo_failed:{_safe_code(failure_code)}",
    }


def _timeout_from_context(context: Any, entry: ExternalComputeDemoEntry) -> float:
    raw = getattr(context, "external_compute_demo_timeout_seconds", entry.timeout_seconds)
    try:
        timeout = float(raw)
    except (TypeError, ValueError):
        return entry.timeout_seconds
    if timeout <= 0:
        return entry.timeout_seconds
    return timeout


def _apply_mapped_result(
    *,
    agent_id: str,
    mapped: Mapping[str, Any],
    l2_conclusions: dict[str, Any],
    dimension_results: dict[str, Any],
) -> tuple[bool, str]:
    schema = mapped.get("schema")
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

    return False, "unsupported_demo_agent"


def run_external_compute_for_plan(
    plan: Mapping[str, Any],
    *,
    question: str,
    as_of: str,
    context: Any,
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any] | None = None,
    agent_tasks: Mapping[str, Any] | None = None,
    stages: tuple[str, ...] = ("l2_analysis", "dimension_composite"),
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Run demo compute calls for allowlisted agents present in a plan."""
    allowlist = normalize_demo_allowlist(
        getattr(context, "external_compute_demo_allowlist", ())
    )
    updated_l2 = {str(agent_id): dict(value) for agent_id, value in l2_conclusions.items()}
    updated_dimensions = {
        str(dimension): dict(value)
        for dimension, value in (dimension_results or {}).items()
    }
    result = {
        "l2_conclusions": updated_l2,
        "dimension_results": updated_dimensions,
        "step_updates": {},
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "warnings": [],
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
        entry = DEMO_COMPUTE_SERVICE_REGISTRY.get(agent_id)
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
        upstream_outputs = (
            updated_l2
            if stage == "dimension_composite"
            else None
        )
        mapped_result = invoke_external_compute(
            entry,
            question=question,
            as_of=as_of,
            request_id=f"r8-12-demo-{agent_id}",
            timeout_seconds=timeout,
            agent_task=agent_task,
            upstream_outputs=upstream_outputs,
            transport=transport,
        )
        result["called_agents"].append(agent_id)
        mapped = mapped_result.get("mapped")
        if mapped_result.get("status") != "pass" or not isinstance(mapped, Mapping):
            warning = str(mapped_result.get("warning") or "external_compute_demo_failed")
            result["warnings"].append(warning)
            result["failed_agents"].append(agent_id)
            result["step_updates"][step_id] = {"warning": warning}
            continue

        applied, reason = _apply_mapped_result(
            agent_id=agent_id,
            mapped=mapped,
            l2_conclusions=updated_l2,
            dimension_results=updated_dimensions,
        )
        if not applied:
            warning = f"external_compute_demo_failed:{_safe_code(reason)}"
            result["warnings"].append(warning)
            result["failed_agents"].append(agent_id)
            result["step_updates"][step_id] = {"warning": warning}
            continue

        result["mapped_agents"].append(agent_id)
        result["step_updates"][step_id] = {
            "status": "complete",
            "summary": "演示模式已读取生产 /compute 结构化结果并完成固定 DAG 适配映射。",
            "warning": "external_compute_demo_default_off_not_runtime_binding",
            "agent_task": agent_task,
        }

    return result


def merge_external_compute_demo_runs(*runs: Mapping[str, Any]) -> dict[str, Any]:
    """Merge public-safe run counters from multiple demo bridge phases."""
    merged = {
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "warnings": [],
    }
    for run in runs:
        for key in merged:
            for item in run.get(key, []) if isinstance(run, Mapping) else []:
                text = str(item or "")
                if text and text not in merged[key]:
                    merged[key].append(text)
    return merged


__all__ = [
    "COMPUTE_PATH",
    "DEMO_COMPUTE_SERVICE_REGISTRY",
    "EXTERNAL_COMPUTE_DEMO_SOURCE",
    "ExternalComputeDemoEntry",
    "build_external_compute_request",
    "invoke_external_compute",
    "merge_external_compute_demo_runs",
    "normalize_demo_allowlist",
    "run_external_compute_for_plan",
    "validate_demo_entry",
]
