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
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from react_agent.fixed_dag_contracts import (
    AGENT_TASK_SCHEMA_VERSION,
    CONCLUSION_OBJECT_SCHEMA_VERSION,
    DATA_BUNDLE_SCHEMA_VERSION,
    DECISION_RESULT_SCHEMA_VERSION,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_COMPOSITE_SCHEMA_VERSION,
    ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
    L2_CONCLUSION_AGENT_IDS,
    REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
    REPORT_RESULT_SCHEMA_VERSION,
    validate_agent_task,
    validate_report_input_bundle,
)
from react_agent.fixed_dag_external_adapter import (
    ADAPTER_FAILURE_SCHEMA_VERSION,
    _normalize_date_text,
    map_external_response_to_fixed_dag_object,
)

EXTERNAL_COMPUTE_DEMO_SOURCE = "external_compute_demo_bridge"
EXTERNAL_COMPUTE_DEFAULT_SOURCE = "external_compute_default_runtime"
EXTERNAL_AGENT_REQUEST_SCHEMA_VERSION = "external_agent_request_v0"
EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION = "external_agent_compute_v0"
COMPUTE_PATH = "/v1/agent/compute"
MAX_RESPONSE_BYTES = 2_000_000
_UPSTREAM_UNSAFE_TEXT_TOKENS = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "authorization",
    "cookie",
    "set-cookie",
    "endpoint",
    "default_url",
    "raw_response",
    "raw_provider_response",
    "raw_external_json",
    "traceback",
    "chain_of_thought",
    "chain-of-thought",
    "cot",
)
_UPSTREAM_RESEARCH_POINT_TEXT_KEYS = (
    "claim",
    "support",
    "interpretation",
    "decision_implication",
    "caveat",
)


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
    "financial_data_service": ExternalComputeDemoEntry(
        agent_id="financial_data_service",
        base_url=_demo_base_url("financial_data_service", "http://127.0.0.1:11000"),
        compute_path=COMPUTE_PATH,
        expected_payload="data_bundle_v1",
        dimension="l1",
        external_agent_id="financial_data_service",
    ),
    "entity_relation_extractor": ExternalComputeDemoEntry(
        agent_id="entity_relation_extractor",
        base_url=_demo_base_url("entity_relation_extractor", "http://127.0.0.1:10017"),
        compute_path=COMPUTE_PATH,
        expected_payload="entity_relation_bundle_v1",
        dimension="l1",
        external_agent_id="entity_relation_agent",
    ),
    "value_traditional_valuation": ExternalComputeDemoEntry(
        agent_id="value_traditional_valuation",
        base_url=_demo_base_url("value_traditional_valuation", "http://127.0.0.1:10000"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_traditional",
    ),
    "value_ml_valuation": ExternalComputeDemoEntry(
        agent_id="value_ml_valuation",
        base_url=_demo_base_url("value_ml_valuation", "http://127.0.0.1:10001"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_ml",
    ),
    "value_meta_valuation": ExternalComputeDemoEntry(
        agent_id="value_meta_valuation",
        base_url=_demo_base_url("value_meta_valuation", "http://127.0.0.1:10002"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="valuation_meta",
    ),
    "value_research_synthesis": ExternalComputeDemoEntry(
        agent_id="value_research_synthesis",
        base_url=_demo_base_url("value_research_synthesis", "http://127.0.0.1:10006"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="value",
        external_agent_id="analyst_research",
    ),
    "market_stock_technical": ExternalComputeDemoEntry(
        agent_id="market_stock_technical",
        base_url=_demo_base_url("market_stock_technical", "http://127.0.0.1:10009"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="technical_stock",
    ),
    "market_capital_flow_chip": ExternalComputeDemoEntry(
        agent_id="market_capital_flow_chip",
        base_url=_demo_base_url("market_capital_flow_chip", "http://127.0.0.1:10022"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="money_flow",
    ),
    "sentiment_company_radar": ExternalComputeDemoEntry(
        agent_id="sentiment_company_radar",
        base_url=_demo_base_url("sentiment_company_radar", "http://127.0.0.1:10020"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="company_sentiment_radar",
    ),
    "market_ipo_investor_behavior": ExternalComputeDemoEntry(
        agent_id="market_ipo_investor_behavior",
        base_url=_demo_base_url("market_ipo_investor_behavior", "http://127.0.0.1:10008"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="market",
        external_agent_id="ipo_investor_behavior",
    ),
    "risk_identification": ExternalComputeDemoEntry(
        agent_id="risk_identification",
        base_url=_demo_base_url("risk_identification", "http://127.0.0.1:10010"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="market_risk_reasoning",
    ),
    "risk_compliance_review": ExternalComputeDemoEntry(
        agent_id="risk_compliance_review",
        base_url=_demo_base_url("risk_compliance_review", "http://127.0.0.1:10011"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="announcement_compliance",
    ),
    "risk_financial_fraud": ExternalComputeDemoEntry(
        agent_id="risk_financial_fraud",
        base_url=_demo_base_url("risk_financial_fraud", "http://127.0.0.1:10013"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="financial_fraud_agent",
    ),
    "risk_crash": ExternalComputeDemoEntry(
        agent_id="risk_crash",
        base_url=_demo_base_url("risk_crash", "http://127.0.0.1:10012"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="risk",
        external_agent_id="crash_risk",
    ),
    "macro_analysis": ExternalComputeDemoEntry(
        agent_id="macro_analysis",
        base_url=_demo_base_url("macro_analysis", "http://127.0.0.1:10014"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="macro",
        external_agent_id="macro_analysis",
        default_target="CN_A_SHARE_MACRO",
    ),
    "macro_commodity_pricing": ExternalComputeDemoEntry(
        agent_id="macro_commodity_pricing",
        base_url=_demo_base_url("macro_commodity_pricing", "http://127.0.0.1:10004"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="macro",
        external_agent_id="price_influence_agent",
        default_target="CU",
    ),
    "macro_index_valuation": ExternalComputeDemoEntry(
        agent_id="macro_index_valuation",
        base_url=_demo_base_url("macro_index_valuation", "http://127.0.0.1:10003"),
        compute_path=COMPUTE_PATH,
        expected_payload="agent_conclusion_v1",
        dimension="macro",
        external_agent_id="valuation_index",
        default_target="沪深300",
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
    "decision_synthesizer": ExternalComputeDemoEntry(
        agent_id="decision_synthesizer",
        base_url=_demo_base_url("decision_synthesizer", "http://127.0.0.1:10025"),
        compute_path=COMPUTE_PATH,
        expected_payload=DECISION_RESULT_SCHEMA_VERSION,
        dimension="l4",
        external_agent_id="l4_decision_synthesizer",
    ),
    "report_generator": ExternalComputeDemoEntry(
        agent_id="report_generator",
        base_url=_demo_base_url("report_generator", "http://127.0.0.1:10026"),
        compute_path=COMPUTE_PATH,
        expected_payload=REPORT_RESULT_SCHEMA_VERSION,
        dimension="l4",
        external_agent_id="l4_report_generator",
        timeout_seconds=120.0,
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


def _strict_date(value: Any) -> date | None:
    normalized = _normalize_date_text(value)
    if normalized in {"", "not_available"}:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _date_fields_temporal_failure(payload: Mapping[str, Any], requested_as_of: str) -> str:
    requested = _strict_date(requested_as_of)
    if requested is None:
        return ""

    if "as_of" in payload:
        mapped_as_of = _strict_date(payload.get("as_of"))
        if mapped_as_of is None:
            return "response_as_of_invalid_for_requested_as_of"
        if mapped_as_of > requested:
            return "response_as_of_after_requested_as_of"

    if "data_as_of" in payload:
        mapped_data_as_of = _strict_date(payload.get("data_as_of"))
        if mapped_data_as_of is None:
            return "response_as_of_invalid_for_requested_as_of"
        if mapped_data_as_of > requested:
            return "response_data_as_of_after_requested_as_of"

    return ""


def _raw_response_temporal_failure(response: Mapping[str, Any], requested_as_of: str) -> str:
    tool_result = response.get("tool_result")
    if not isinstance(tool_result, Mapping):
        return ""
    return _date_fields_temporal_failure(tool_result, requested_as_of)


def _mapped_temporal_failure(mapped: Mapping[str, Any], requested_as_of: str) -> str:
    """Fail closed when a mapped external result crosses the request as_of.

    The pure adapter validates payload-internal chronology, while the bridge is
    the first layer that has both the requested ``as_of`` and the mapped fixed
    DAG object.  Keep report_result_v1 compatible because it has no date field.
    """
    return _date_fields_temporal_failure(mapped, requested_as_of)


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


def _safe_context_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if any(
            marker in lowered
            for marker in (
                "api_key",
                "secret",
                "password",
                "authorization",
                "cookie",
                "endpoint",
                "base_url",
                "provider_endpoint",
                "provider_url",
                "raw_response",
                "raw_provider_response",
                "traceback",
                "chain-of-thought",
                "/v1/agent/invoke",
                ".env",
            )
        ):
            return None
        return text[:1200]
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, raw in list(value.items())[:60]:
            text_key = str(key or "").strip()
            if not text_key:
                continue
            if text_key.lower() in {
                "api_key",
                "secret",
                "token",
                "password",
                "authorization",
                "cookie",
                "endpoint",
                "base_url",
                "provider_endpoint",
                "provider_url",
                "invoke_url",
                "raw_response",
                "raw_provider_response",
                "raw_external_json",
                "traceback",
            }:
                continue
            bounded = _safe_context_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                safe[text_key[:120]] = bounded
        return safe or None
    if isinstance(value, list):
        items: list[Any] = []
        for raw in value[:24]:
            bounded = _safe_context_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                items.append(bounded)
        return items or None
    return str(value or "")[:300] or None


def _safe_context_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    safe = _safe_context_value(value)
    return dict(safe) if isinstance(safe, Mapping) else {}


def _safe_report_input_bundle(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Preserve a validated report_input_bundle_v1 for L4 report services.

    ``report_input_bundle_v1`` is built by the main system as a bounded
    public-safe package.  Re-running the generic context sanitizer on it can
    truncate required nested evidence fields and make the package fail the
    service-side validator, causing the L4 report service to fall back to a
    template report.  Validate the package first and pass it intact only when it
    remains on the public-safe contract.
    """
    if not isinstance(value, Mapping):
        return {}
    valid, _reason = validate_report_input_bundle(value)
    if not valid:
        return {}
    if value.get("schema") != REPORT_INPUT_BUNDLE_SCHEMA_VERSION:
        return {}
    return dict(value)


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
    demo: bool = True,
    agent_task: Mapping[str, Any] | None = None,
    upstream_outputs: Mapping[str, Any] | None = None,
    dimension_results: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
    report_input_bundle: Mapping[str, Any] | None = None,
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
        "as_of_date": as_of,
        "context": {
            "fixed_dag_id": entry.agent_id,
            "dimension": entry.dimension,
            "as_of": as_of,
            "as_of_date": as_of,
            "environment": "production",
            "demo": demo,
            "runtime_default": not demo,
            "user_question": question,
            "task_instruction": (
                safe_agent_task.get("task_instruction", "")
                if safe_agent_task is not None
                else ""
            ),
        },
        "options": {
            "smoke": False,
            "demo": demo,
            "environment": "production",
            "as_of": as_of,
            "as_of_date": as_of,
            "allow_llm": entry.agent_id in {"decision_synthesizer", "report_generator"},
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
    if entry.agent_id == "decision_synthesizer":
        safe_dimensions = _safe_context_mapping(dimension_results)
        if safe_dimensions:
            request["context"]["dimension_results"] = safe_dimensions
            request["context"]["dimension_results_schema"] = "dimension_composite_result_map_v1"
    if entry.agent_id == "report_generator":
        safe_decision = _safe_context_mapping(decision_result)
        safe_report_input = _safe_report_input_bundle(report_input_bundle)
        if safe_decision:
            request["context"]["decision_result"] = safe_decision
        if safe_report_input:
            request["context"]["report_input_bundle"] = safe_report_input
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


def _contains_unsafe_upstream_text(value: Any) -> bool:
    lowered = str(value or "").lower()
    return any(token in lowered for token in _UPSTREAM_UNSAFE_TEXT_TOKENS)


def _safe_upstream_string(value: Any, *, limit: int = 240) -> str:
    if _contains_unsafe_upstream_text(value):
        return ""
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _safe_upstream_detail_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 3:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        return _safe_upstream_string(value, limit=240) or None
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, raw in list(value.items())[:16]:
            field = _safe_upstream_string(key, limit=80)
            if not field:
                continue
            bounded = _safe_upstream_detail_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                safe[field] = bounded
        return safe or None
    if isinstance(value, list | tuple):
        items: list[Any] = []
        for raw in list(value)[:16]:
            bounded = _safe_upstream_detail_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                items.append(bounded)
        return items or None
    return _safe_upstream_string(value, limit=160) or None


def _safe_upstream_detail_mapping(value: Any, *, limit: int = 16) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    safe: dict[str, Any] = {}
    for key, raw in value.items():
        field = _safe_upstream_string(key, limit=80)
        if not field:
            continue
        bounded = _safe_upstream_detail_value(raw)
        if bounded not in (None, "", [], {}):
            safe[field] = bounded
        if len(safe) >= limit:
            break
    return safe


def _safe_upstream_driver_details(value: Any, *, limit: int = 10) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    drivers: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for raw in value[:limit]:
        if isinstance(raw, Mapping):
            raw_name_values = [
                raw.get(key)
                for key in ("name", "driver", "type")
                if raw.get(key) not in (None, "")
            ]
            safe_name = next(
                (
                    name
                    for name in (
                        _safe_upstream_string(raw.get("name"), limit=80),
                        _safe_upstream_string(raw.get("driver"), limit=80),
                        _safe_upstream_string(raw.get("type"), limit=80),
                    )
                    if name
                ),
                "",
            )
            if raw_name_values and not safe_name:
                continue
            name = safe_name or f"driver_{len(drivers) + 1}"
            raw_value = (
                raw.get("value")
                if "value" in raw
                else {
                    key: item
                    for key, item in raw.items()
                    if key not in {"name", "driver", "type"}
                }
            )
        else:
            name = f"driver_{len(drivers) + 1}"
            raw_value = raw
        bounded = _safe_upstream_detail_value(raw_value)
        if not name or name in seen_names or bounded in (None, "", [], {}):
            continue
        drivers.append({"name": name, "value": bounded})
        seen_names.add(name)
    return drivers


def _safe_upstream_research_points(value: Any, *, limit: int = 8) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    points: list[dict[str, Any]] = []
    for raw in value[:limit]:
        if not isinstance(raw, Mapping):
            continue
        point: dict[str, Any] = {}
        for key in _UPSTREAM_RESEARCH_POINT_TEXT_KEYS:
            text = _safe_upstream_string(raw.get(key), limit=360)
            if text:
                point[key] = text
        if raw.get("confidence") is not None:
            confidence = _safe_upstream_detail_value(raw.get("confidence"))
            if isinstance(confidence, int | float):
                point["confidence"] = confidence
        evidence_refs = raw.get("evidence_refs")
        if isinstance(evidence_refs, list):
            refs = [
                _safe_upstream_string(item, limit=120)
                for item in evidence_refs[:6]
                if _safe_upstream_string(item, limit=120)
            ]
            if refs:
                point["evidence_refs"] = refs
        if point.get("claim") or point.get("support"):
            points.append(point)
    return points


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
    provenance = value.get("provenance")
    if isinstance(provenance, Mapping):
        domain_metrics = _safe_upstream_detail_mapping(
            provenance.get("domain_metrics"),
            limit=18,
        )
        if domain_metrics:
            safe["domain_metrics"] = domain_metrics
        drivers = _safe_upstream_driver_details(provenance.get("drivers"), limit=10)
        if drivers:
            safe["drivers"] = drivers
        research_points = _safe_upstream_research_points(
            provenance.get("research_points"),
            limit=8,
        )
        if research_points:
            safe["research_points"] = research_points
        data_quality = _safe_upstream_detail_mapping(
            provenance.get("data_quality"),
            limit=14,
        )
        if data_quality:
            safe["data_quality"] = data_quality
    if (
        "risk_score" not in safe
        and (
            safe.get("role") == "gate_member"
            or safe.get("stance") == "risk_gate_member"
        )
        and isinstance(provenance, Mapping)
        and provenance.get("risk_score") is not None
    ):
        safe["risk_score"] = provenance.get("risk_score")
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
    demo: bool = True,
    agent_task: Mapping[str, Any] | None = None,
    upstream_outputs: Mapping[str, Any] | None = None,
    dimension_results: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
    report_input_bundle: Mapping[str, Any] | None = None,
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
    if timeout == 20.0 and entry.timeout_seconds != 20.0 and "EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS" not in os.environ:
        return entry.timeout_seconds
    return timeout


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
    """Run demo compute calls for allowlisted agents present in a plan."""
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
        upstream_outputs = (
            updated_l2
            if stage == "dimension_composite"
            else None
        )
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
    "EXTERNAL_COMPUTE_DEFAULT_SOURCE",
    "ExternalComputeDemoEntry",
    "build_external_compute_request",
    "invoke_external_compute",
    "merge_external_compute_demo_runs",
    "normalize_demo_allowlist",
    "runtime_compute_entries_from_bindings",
    "run_external_compute_for_plan",
    "validate_demo_entry",
]
