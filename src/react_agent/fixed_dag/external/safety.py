"""Safety helpers for fixed-DAG external compute payload boundaries."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from react_agent.fixed_dag.external.constants import (
    _UPSTREAM_RESEARCH_POINT_TEXT_KEYS,
    _UPSTREAM_UNSAFE_TEXT_TOKENS,
    COMPUTE_PATH,
)
from react_agent.fixed_dag.external.registry import DEMO_COMPUTE_SERVICE_REGISTRY
from react_agent.fixed_dag.external.types import ExternalComputeDemoEntry


def _safe_code(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_:-]+", "_", text)
    return text[:120] or "external_compute_demo_failure"


def _normalize_date_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "not_available"
    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return text


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
    return _date_fields_temporal_failure(mapped, requested_as_of)


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


def validate_demo_entry(entry: ExternalComputeDemoEntry) -> tuple[bool, str]:
    """Validate that a demo/default entry only targets loopback compute."""
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
        domain_metrics = _safe_upstream_detail_mapping(provenance.get("domain_metrics"), limit=18)
        if domain_metrics:
            safe["domain_metrics"] = domain_metrics
        drivers = _safe_upstream_driver_details(provenance.get("drivers"), limit=10)
        if drivers:
            safe["drivers"] = drivers
        research_points = _safe_upstream_research_points(provenance.get("research_points"), limit=8)
        if research_points:
            safe["research_points"] = research_points
        data_quality = _safe_upstream_detail_mapping(provenance.get("data_quality"), limit=14)
        if data_quality:
            safe["data_quality"] = data_quality
    if (
        "risk_score" not in safe
        and (safe.get("role") == "gate_member" or safe.get("stance") == "risk_gate_member")
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
    if isinstance(agent_task, Mapping) and isinstance(agent_task.get("upstream_agent_ids"), list):
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


__all__ = ["validate_demo_entry"]
