"""Provider-free mapping from external fixed-DAG payloads to internal contracts.

The adapter is intentionally pure: it accepts already-available payload
dictionaries and never performs HTTP, provider, graph, or runtime binding calls.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, cast

from react_agent.fixed_dag_catalog import ANN_ID_PATTERN, FORBIDDEN_RESET_AGENT_IDS
from react_agent.fixed_dag_contracts import (
    AGENT_DIMENSIONS,
    CONCLUSION_OBJECT_SCHEMA_VERSION,
    DATA_BUNDLE_SCHEMA_VERSION,
    DECISION_RESULT_SCHEMA_VERSION,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_COMPOSITE_SCHEMA_VERSION,
    DIMENSION_GROUPS,
    ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
    L2_CONCLUSION_AGENT_IDS,
    REPORT_RESULT_SCHEMA_VERSION,
    SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES,
    ConclusionObject,
    ConclusionStatus,
    DataBundle,
    DecisionResult,
    DimensionCompositeResult,
    EntityRelationBundle,
    ReportResult,
    validate_conclusion_object,
    validate_data_bundle,
    validate_decision_result,
    validate_dimension_composite_result,
    validate_entity_relation_bundle,
    validate_report_result,
)

EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION = "external_agent_response_v0"
EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION = "external_agent_compute_v0"
EXTERNAL_AGENT_CONCLUSION_SCHEMA_VERSION = "agent_conclusion_v1"
EXTERNAL_DATA_BUNDLE_SCHEMA_VERSION = "data_bundle_v1"
EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION = "entity_relation_bundle_v1"
EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION = "dimension_conclusion_v1"
EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION = "risk_conclusion_v1"
EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION = "macro_conclusion_v1"
FIXED_DAG_EXTERNAL_ADAPTER_SOURCE = "fixed_dag_external_adapter"
ADAPTER_FAILURE_SCHEMA_VERSION = "fixed_dag_external_adapter_failure_v1"

_EXTERNAL_STATUS_TO_INTERNAL: dict[str, ConclusionStatus] = {
    "ok": "complete",
    "partial": "partial",
    "needs_clarification": "partial",
    "error": "error",
}
_UNSAFE_TEXT_TOKENS = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "env",
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
_ALLOWED_EVIDENCE_FIELDS = {
    "id",
    "fact",
    "source",
    "as_of",
    "data_as_of",
    "publish_time",
    "value",
    "unit",
}
_PUBLIC_SAFE_DOMAIN_METRIC_KEYS = {
    "agent_id",
    "aggregate_gate",
    "as_of_date",
    "asset_class_ranking",
    "asset_allocation_view",
    "belief_distribution",
    "best_asset_class",
    "channel_votes",
    "china_out_influence",
    "china_pricing_share",
    "ci_high",
    "ci_low",
    "code",
    "compliance_score",
    "composite_quality",
    "composite_research_packet",
    "components",
    "conflict_level",
    "conflict_summary",
    "current_market_value",
    "current_mv",
    "current_price",
    "data_nowcast",
    "decile",
    "diagnosis",
    "dimension_weights",
    "direction",
    "dominant_signals",
    "down_votes",
    "effective_gate",
    "eps",
    "fair_value",
    "fair_value_center",
    "fair_value_center_mv",
    "fair_value_high",
    "fair_value_low",
    "fair_value_range",
    "fair_value_range_mv",
    "feature_available",
    "feature_diagnostics",
    "feature_drivers",
    "financial_publish_time",
    "financial_report_period",
    "foreign_in_influence",
    "forecast_horizon",
    "fraud_risk_bridge",
    "gate",
    "growth",
    "industry_adjustment",
    "final_implication",
    "horizon_days",
    "index_valuation_level",
    "latest_pe_ttm",
    "limitations",
    "margins",
    "member_boundary_summary",
    "member_count",
    "member_override_gate",
    "method",
    "missing_or_degraded_members",
    "macro_data_window",
    "macro_regime_bridge",
    "macro_signal_table",
    "model_available",
    "model_context",
    "model_confidence",
    "model_vintage_boundary",
    "momentum_20d",
    "n_china_to_foreign_pairs",
    "n_contributors",
    "n_foreign_to_china_pairs",
    "pb",
    "pe",
    "penalty",
    "percentile",
    "prob_up",
    "product",
    "rank",
    "rating",
    "reported_confidence",
    "regime",
    "regime_detail",
    "regulator_suggestion",
    "report_count",
    "requested_target",
    "risk_gate_rule",
    "risk_flags",
    "risk_level",
    "risk_score",
    "risk_sensitivity",
    "roe",
    "sample_size",
    "sector_rotation",
    "sector_rotation_summary",
    "selection_v2",
    "sentiment_level",
    "sentiment_pct",
    "sheet",
    "stance_text",
    "statistic_name",
    "style_bias",
    "target_date",
    "target_pe_raw",
    "target_price",
    "time_window_months",
    "trade_date",
    "trend",
    "undervalued_ratio",
    "universe_size",
    "up_votes",
    "upside_pct",
    "used_forecast_year",
    "valuation",
    "valuation_bridge",
    "valuation_method",
    "valuation_pct",
    "valuation_view",
    "value_basis",
    "verdict",
    "zeping_crosscheck_context",
}
_PUBLIC_SAFE_DRIVER_KEYS = {
    "asset_class_ranking",
    "aggregate_gate",
    "asset_allocation_view",
    "backtest_context",
    "belief_distribution",
    "channel_votes",
    "composite_quality",
    "composite_research_packet",
    "components",
    "conflict_level",
    "conflict_summary",
    "confidence_factors",
    "data_nowcast",
    "diagnosis",
    "dominant_signals",
    "drivers",
    "effective_gate",
    "fair_value_range",
    "feature_drivers",
    "feature_diagnostics",
    "finding_summary",
    "final_implication",
    "fraud_risk_bridge",
    "fusion",
    "hits",
    "industry_adjustment",
    "limitations",
    "margins",
    "member_boundary_summary",
    "member_weight_summary",
    "member_override_gate",
    "members",
    "method",
    "method_assumptions",
    "missing_or_degraded_members",
    "feature_snapshot",
    "macro_data_window",
    "macro_regime_bridge",
    "macro_signal_table",
    "model_context",
    "model_vintage_boundary",
    "model_vote_table",
    "normalized",
    "regime",
    "regime_detail",
    "regulator_suggestion",
    "risk_gate_rule",
    "risk_flags",
    "rubric_score_table",
    "sector_rotation",
    "sector_rotation_summary",
    "selection_v2",
    "shap",
    "shap_values",
    "slice_summary",
    "term_structure",
    "top_drivers",
    "top_terms",
    "triggered_flags",
    "valuation",
    "valuation_bridge",
    "warnings",
    "weakest_dimensions",
    "zeping_crosscheck_context",
}
_PUBLIC_SAFE_QUALITY_KEYS = {
    "annual_feature_available_after",
    "anti_lookahead_passed",
    "available_features",
    "business_core_changed",
    "cached",
    "calibrated",
    "composite_quality",
    "composite_status",
    "contract_ok",
    "corpus_notice",
    "conflict_level",
    "conflict_summary",
    "coverage",
    "data_completeness",
    "data_nowcast",
    "data_source",
    "data_sources",
    "degraded",
    "dimension_coverage",
    "expected_features",
    "feature_available",
    "feature_data_anti_lookahead_passed",
    "financial_publish_time",
    "financial_report_period",
    "freshness",
    "limitations",
    "llm_subjective",
    "member_boundary_summary",
    "member_count",
    "method",
    "method_details",
    "missing_components",
    "missing_dimensions",
    "missing_or_degraded_members",
    "model_available",
    "model",
    "model_vintage_caveat",
    "model_trust",
    "n_cross_market_pairs",
    "n_slices",
    "price_date",
    "knowledge_version",
    "macro_data_window",
    "report_ann_date",
    "report_period",
    "release_dates",
    "sample_size",
    "scoring_method",
    "sector_rotation_available",
    "text_available",
    "upstream_outputs_consumed",
    "warnings",
}
_PUBLIC_SAFE_RESEARCH_POINT_TEXT_KEYS = (
    "claim",
    "support",
    "interpretation",
    "decision_implication",
    "caveat",
)
_PUBLIC_SAFE_DETAIL_MAX_DEPTH = 3


def _safe_code(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_:-]+", "_", text)
    return text[:120] or "adapter_failure"


def _contains_unsafe_text(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _contains_unsafe_text(key) or _contains_unsafe_text(item)
            for key, item in value.items()
        )
    if isinstance(value, list | tuple | set):
        return any(_contains_unsafe_text(item) for item in value)
    lowered = str(value or "").lower()
    return any(token in lowered for token in _UNSAFE_TEXT_TOKENS)


def _safe_string(value: Any, *, limit: int = 240) -> str:
    if _contains_unsafe_text(value):
        return ""
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _safe_keys_summary(value: Any, *, limit: int = 12) -> list[str]:
    if not isinstance(value, Mapping):
        return []
    keys: list[str] = []
    for key in value:
        text = _safe_string(key, limit=80)
        if text and text not in keys:
            keys.append(text)
        if len(keys) >= limit:
            break
    return keys


def _safe_detail_value(value: Any, *, depth: int = 0) -> Any:
    """Return a bounded public-safe value for report-facing diagnostics."""
    if depth > _PUBLIC_SAFE_DETAIL_MAX_DEPTH or _contains_unsafe_text(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        return _safe_string(value, limit=240) or None
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, raw in list(value.items())[:12]:
            field = _safe_string(key, limit=80)
            if not field:
                continue
            bounded = _safe_detail_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                safe[field] = bounded
        return safe or None
    if isinstance(value, list | tuple):
        items: list[Any] = []
        for raw in list(value)[:12]:
            bounded = _safe_detail_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                items.append(bounded)
        return items or None
    return _safe_string(value, limit=160) or None


def _safe_detail_mapping(
    value: Any,
    *,
    allowed_keys: set[str],
    limit: int = 16,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    safe: dict[str, Any] = {}
    for key, raw in value.items():
        field = _safe_string(key, limit=80)
        if not field or field not in allowed_keys:
            continue
        bounded = _safe_detail_value(raw)
        if bounded not in (None, "", [], {}):
            safe[field] = bounded
        if len(safe) >= limit:
            break
    return safe


def _safe_driver_details(value: Any, *, limit: int = 10) -> list[dict[str, Any]]:
    if not isinstance(value, Mapping):
        return []
    drivers: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    raw_driver_list = value.get("drivers")
    if isinstance(raw_driver_list, list):
        for raw in raw_driver_list:
            if isinstance(raw, Mapping):
                name = (
                    _safe_string(raw.get("name"), limit=80)
                    or _safe_string(raw.get("driver"), limit=80)
                    or _safe_string(raw.get("type"), limit=80)
                    or f"driver_{len(drivers) + 1}"
                )
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
            bounded = _safe_detail_value(raw_value)
            if bounded in (None, "", [], {}):
                continue
            if name in seen_names:
                continue
            drivers.append({"name": name, "value": bounded})
            seen_names.add(name)
            if len(drivers) >= limit:
                return drivers
    for key, raw in value.items():
        field = _safe_string(key, limit=80)
        if not field or field == "drivers" or field not in _PUBLIC_SAFE_DRIVER_KEYS:
            continue
        bounded = _safe_detail_value(raw)
        if bounded in (None, "", [], {}):
            continue
        if field in seen_names:
            continue
        drivers.append({"name": field, "value": bounded})
        seen_names.add(field)
        if len(drivers) >= limit:
            break
    return drivers


def _safe_research_points(value: Any, *, limit: int = 8) -> list[dict[str, Any]]:
    """Return bounded public-safe research judgment points for report synthesis."""
    if not isinstance(value, list):
        return []
    points: list[dict[str, Any]] = []
    for raw in value[:limit]:
        if not isinstance(raw, Mapping):
            continue
        point: dict[str, Any] = {}
        for key in _PUBLIC_SAFE_RESEARCH_POINT_TEXT_KEYS:
            text = _safe_string(raw.get(key), limit=360)
            if text:
                point[key] = text
        if raw.get("confidence") is not None:
            confidence = _safe_detail_value(raw.get("confidence"))
            if isinstance(confidence, int | float):
                point["confidence"] = confidence
        evidence_refs = raw.get("evidence_refs")
        if isinstance(evidence_refs, list):
            refs = [
                _safe_string(item, limit=120)
                for item in evidence_refs[:6]
                if _safe_string(item, limit=120)
            ]
            if refs:
                point["evidence_refs"] = refs
        if point.get("claim") or point.get("support"):
            points.append(point)
    return points


def _public_safe_business_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Extract bounded business context without preserving raw external JSON."""
    context: dict[str, Any] = {}
    raw_output = payload.get("raw_output")
    if isinstance(raw_output, Mapping):
        domain_metrics = _safe_detail_mapping(
            raw_output,
            allowed_keys=_PUBLIC_SAFE_DOMAIN_METRIC_KEYS,
            limit=18,
        )
        if domain_metrics:
            context["domain_metrics"] = domain_metrics
    drivers = _safe_driver_details(raw_output, limit=10)
    if drivers:
        context["drivers"] = drivers
    research_points = (
        _safe_research_points(raw_output.get("research_points"), limit=8)
        if isinstance(raw_output, Mapping)
        else []
    )
    if research_points:
        context["research_points"] = research_points
    data_quality = _safe_detail_mapping(
        payload.get("quality"),
        allowed_keys=_PUBLIC_SAFE_QUALITY_KEYS,
        limit=14,
    )
    if data_quality:
        context["data_quality"] = data_quality
    return context


def _l3_quality_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    quality: dict[str, Any] = {}
    raw_quality = payload.get("quality")
    if isinstance(raw_quality, Mapping):
        quality.update(dict(raw_quality))
    if payload.get("status") is not None:
        quality["composite_status"] = payload.get("status")
    for key in ("warnings", "cached", "contract_ok"):
        if key in payload:
            quality[key] = payload.get(key)
    members = payload.get("members")
    if isinstance(members, list | Mapping):
        quality["member_count"] = len(members)
    provenance = payload.get("provenance")
    if isinstance(provenance, Mapping):
        for key in ("upstream_outputs_consumed", "business_core_changed"):
            if key in provenance:
                quality[key] = provenance.get(key)
    return quality


def _public_safe_l3_business_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_output = dict(payload)
    member_summary = _member_weight_summary(payload.get("members"))
    if member_summary:
        raw_output["member_weight_summary"] = member_summary
    return _public_safe_business_context(
        {
            "raw_output": raw_output,
            "quality": _l3_quality_context(payload),
        }
    )


def _bounded_float(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _normalize_date_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "not_available"
    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return text


def _date_key(value: Any) -> str:
    normalized = _normalize_date_text(value)
    digits = re.sub(r"[^0-9]", "", normalized)
    return digits or normalized


def _data_not_after(data_as_of: Any, as_of: Any) -> bool:
    left = _date_key(data_as_of)
    right = _date_key(as_of)
    return bool(left and right and left <= right)


def _status_from_external(value: Any) -> ConclusionStatus | None:
    return _EXTERNAL_STATUS_TO_INTERNAL.get(str(value or "").strip().lower())


def _adapter_failure(
    reason: str,
    *,
    agent_id: str = "",
    external_agent_id: str = "",
    schema_version: str = "",
) -> dict[str, Any]:
    return {
        "schema": ADAPTER_FAILURE_SCHEMA_VERSION,
        "schema_version": ADAPTER_FAILURE_SCHEMA_VERSION,
        "status": "error",
        "reason": _safe_code(reason),
        "agent_id": _safe_string(agent_id, limit=120),
        "external_agent_id": _safe_string(external_agent_id, limit=120),
        "payload_schema_version": _safe_string(schema_version, limit=120),
        "provenance": {
            "source": FIXED_DAG_EXTERNAL_ADAPTER_SOURCE,
            "provider_invoked": False,
            "external_invoked": False,
        },
    }


def _identity_failure_reason(agent_id: str, dimension: str) -> str:
    if ANN_ID_PATTERN.match(agent_id):
        return "legacy_agent_id_as_primary"
    if agent_id in FORBIDDEN_RESET_AGENT_IDS or agent_id == "value_financial_analysis":
        return "forbidden_agent_id"
    if agent_id not in L2_CONCLUSION_AGENT_IDS:
        return "unknown_agent_id"
    expected_dimension = AGENT_DIMENSIONS.get(agent_id)
    if dimension != expected_dimension:
        if agent_id == "sentiment_company_radar" and dimension == "risk":
            return "sentiment_company_radar_risk_dimension"
        return "dimension_mismatch"
    return ""


def _safe_evidence_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    evidence: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        safe_item: dict[str, Any] = {}
        for key, raw in item.items():
            field = str(key or "").strip()
            if field not in _ALLOWED_EVIDENCE_FIELDS:
                continue
            if _contains_unsafe_text(field) or _contains_unsafe_text(raw):
                continue
            if field in {"as_of", "data_as_of", "publish_time"}:
                safe_item[field] = _normalize_date_text(raw)
            elif isinstance(raw, int | float | bool):
                safe_item[field] = raw
            else:
                text = _safe_string(raw, limit=260)
                if text:
                    safe_item[field] = text
        if safe_item:
            evidence.append(safe_item)
    return evidence[:10]


def _safe_event_flags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    flags: list[str] = []
    for item in value:
        candidate: str
        if isinstance(item, Mapping):
            candidate = str(item.get("type") or item.get("name") or item.get("label") or "")
        else:
            candidate = str(item or "")
        text = _safe_string(candidate, limit=120)
        if text and text not in flags:
            flags.append(text)
    return flags[:12]


def _source_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    sources: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = _safe_string(item, limit=160)
        elif isinstance(item, Mapping):
            text = _safe_string(
                item.get("name")
                or item.get("source")
                or item.get("id")
                or item.get("title")
                or "",
                limit=160,
            )
        else:
            text = ""
        if text and text not in sources:
            sources.append(text)
    return sources[:20]


def _safe_note_values(label: str, values: Iterable[Any], *, limit: int = 12) -> list[str]:
    notes: list[str] = []
    safe_label = _safe_string(label, limit=80)
    if not safe_label:
        return notes
    for value in values:
        text = _safe_string(value, limit=160)
        if text:
            notes.append(f"{safe_label}: {text}")
        if len(notes) >= limit:
            break
    return notes


def _safe_mapping_items(value: Any, *, limit: int = 50) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping) or _contains_unsafe_text(item):
            continue
        safe_item: dict[str, Any] = {}
        for key, raw in item.items():
            field = _safe_string(key, limit=80)
            if not field:
                continue
            if isinstance(raw, int | float | bool) and not isinstance(raw, bool):
                safe_item[field] = raw
            elif isinstance(raw, bool):
                safe_item[field] = raw
            else:
                text = _safe_string(raw, limit=180)
                if text:
                    safe_item[field] = text
        if safe_item:
            items.append(safe_item)
        if len(items) >= limit:
            break
    return items


def _safe_string_list(value: Any, *, limit: int = 20, item_limit: int = 120) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = _safe_string(item, limit=item_limit)
        if text and text not in items:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def _member_looks_placeholder(item: Mapping[str, Any], fallback_id: str) -> bool:
    marker_text = " ".join(
        str(value or "")
        for value in (
            fallback_id,
            item.get("agent_id"),
            item.get("name"),
            item.get("display_name"),
            item.get("summary"),
            item.get("source"),
            item.get("credibility"),
        )
    ).lower()
    return any(token in marker_text for token in ("placeholder", "standin", "占位"))


def _safe_evidence_refs(value: Any, *, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    refs: list[str] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            continue
        text = _safe_string(
            item.get("id")
            or item.get("source")
            or item.get("fact")
            or f"evidence_{index}",
            limit=160,
        )
        if text and text not in refs:
            refs.append(text)
        if len(refs) >= limit:
            break
    return refs


def _evidence_refs_member_ids(value: Any) -> set[str]:
    member_ids: set[str] = set()
    if not isinstance(value, list):
        return member_ids
    for item in value:
        if not isinstance(item, Mapping):
            continue
        for key in ("agent_id", "source", "id"):
            text = _safe_string(item.get(key), limit=160)
            if text:
                member_ids.add(text)
    return member_ids


def _numeric_in_range(value: Any, *, field: str, minimum: float = 0.0, maximum: float = 1.0) -> tuple[float, str]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0, f"invalid_{field}"
    if not minimum <= number <= maximum:
        return 0.0, f"{field}_out_of_range"
    return number, ""


def _member_weight_summary(members: Any) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    if isinstance(members, Mapping):
        raw_items = [
            (str(key), value)
            for key, value in members.items()
            if isinstance(value, Mapping)
        ]
    elif isinstance(members, list):
        raw_items = [
            ("", value)
            for value in members
            if isinstance(value, Mapping)
        ]
    else:
        return summary
    for fallback_id, item in raw_items[:12]:
        member: dict[str, Any] = {
            "agent_id": _safe_string(
                item.get("agent_id") or item.get("name") or fallback_id,
                limit=120,
            ),
        }
        if item.get("weight") is not None:
            member["weight"] = _bounded_float(item.get("weight"))
        if item.get("confidence") is not None:
            member["confidence"] = _bounded_float(item.get("confidence"))
        if item.get("stance") is not None:
            try:
                member["stance"] = float(item.get("stance"))
            except (TypeError, ValueError):
                member["stance"] = _safe_string(item.get("stance"), limit=80)
        status = _safe_code(item.get("status"))
        if status == "ok" and _member_looks_placeholder(item, fallback_id):
            status = "partial"
        if status:
            member["status"] = status
        if item.get("risk_score") is not None:
            try:
                member["risk_score"] = float(item.get("risk_score"))
            except (TypeError, ValueError):
                pass
        summary_text = _safe_string(item.get("summary"), limit=180)
        if summary_text:
            member["summary"] = summary_text
        summary.append({key: value for key, value in member.items() if value != ""})
    return summary


_NON_CONTRIBUTOR_MEMBER_STATUSES = {
    "error",
    "failed",
    "missing",
    "not_available",
    "pending",
    "pending_implementation",
    "skipped",
    "unavailable",
}


def _member_has_bounded_business_material(item: Mapping[str, Any]) -> bool:
    if item.get("stance") not in (None, ""):
        return True
    if item.get("risk_score") not in (None, ""):
        return True
    if _safe_string(item.get("summary"), limit=180):
        return True
    for key in ("evidence", "research_points", "drivers", "domain_metrics"):
        value = item.get(key)
        if isinstance(value, Mapping) and value:
            return True
        if isinstance(value, list) and value:
            return True
    return False


def _l3_member_real_contributor(item: Mapping[str, Any]) -> bool:
    status = _safe_code(item.get("status"))
    if status in _NON_CONTRIBUTOR_MEMBER_STATUSES:
        return False
    confidence = _bounded_float(item.get("confidence"), default=0.0)
    if confidence <= 0.0:
        return False
    return _member_has_bounded_business_material(item)


def _non_contributor_weight_reason(item: Mapping[str, Any]) -> str:
    status = _safe_code(item.get("status"))
    if status in {
        "missing",
        "not_available",
        "pending",
        "pending_implementation",
        "skipped",
        "unavailable",
    }:
        return "positive_weight_pending_member"
    if status in {"error", "failed"}:
        return "positive_weight_error_member"
    return "positive_weight_no_evidence_member"


def _validate_l3_real_contributors(
    *,
    members: list[Mapping[str, Any]],
    weights: Mapping[str, float],
    declared_contributing_agents: Any,
    evidence: Any,
) -> tuple[list[str], str]:
    real_contributors: list[str] = []
    non_contributors: set[str] = set()
    for item in members:
        member_agent_id = str(item.get("agent_id") or "").strip()
        if _l3_member_real_contributor(item):
            real_contributors.append(member_agent_id)
            continue
        non_contributors.add(member_agent_id)
        if weights.get(member_agent_id, 0.0) > 0.0:
            return [], _non_contributor_weight_reason(item)

    declared = _safe_string_list(declared_contributing_agents, limit=20)
    if declared:
        if not set(declared) <= set(real_contributors):
            return [], "contributing_agent_not_real_contributor"

    evidence_member_refs = _evidence_refs_member_ids(evidence)
    if evidence_member_refs & non_contributors:
        return [], "evidence_ref_from_non_contributor"
    return real_contributors, ""


def _bounded_float_mapping(value: Any, *, allowed_keys: set[str], require_exact_keys: bool) -> tuple[dict[str, float], str]:
    if not isinstance(value, Mapping):
        return {}, "invalid_dimension_weights"
    keys = {str(key) for key in value}
    if not keys:
        return {}, "dimension_weights_missing"
    if not keys <= allowed_keys:
        return {}, "dimension_weights_invalid_keys"
    if require_exact_keys and keys != allowed_keys:
        return {}, "dimension_weights_keys_mismatch"
    weights: dict[str, float] = {}
    for key, raw in value.items():
        number, reason = _numeric_in_range(raw, field="dimension_weight")
        if reason:
            return {}, reason
        weights[str(key)] = number
    return weights, ""


def _composite_provenance(
    *,
    input_schema: str,
    external_agent_id: str,
    legacy_agent_id: str = "",
    envelope: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "source": FIXED_DAG_EXTERNAL_ADAPTER_SOURCE,
        "adapter_source": FIXED_DAG_EXTERNAL_ADAPTER_SOURCE,
        "adapter_input_schema": input_schema,
        "external_agent_id": _safe_string(external_agent_id, limit=120),
        "legacy_agent_id": _safe_string(legacy_agent_id, limit=120),
        "provider_invoked": False,
        "external_invoked": False,
    }
    if isinstance(envelope, Mapping):
        envelope_schema = _safe_string(envelope.get("schema_version"), limit=120)
        if envelope_schema:
            provenance["envelope_schema"] = envelope_schema
        if envelope_schema == EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION:
            provenance["compute_envelope_status"] = _safe_code(envelope.get("status"))
        elif envelope_schema == EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION:
            provenance["response_envelope_status"] = _safe_code(envelope.get("status"))
    provenance.update(dict(extra or {}))
    return provenance


def _validate_l3_dates(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    agent_id: str,
    external_agent_id: str,
) -> tuple[str, str, dict[str, Any] | None]:
    as_of = _normalize_date_text(payload.get("as_of"))
    data_as_of = _normalize_date_text(payload.get("data_as_of") or as_of)
    if not _data_not_after(data_as_of, as_of):
        return as_of, data_as_of, _adapter_failure(
            "data_as_of_after_as_of",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=schema_version,
        )
    return as_of, data_as_of, None


def validate_external_response_envelope(payload: Mapping[str, Any]) -> tuple[bool, str]:
    """Validate the external response envelope without validating tool_result."""
    if not isinstance(payload, Mapping):
        return False, "payload_not_mapping"
    if payload.get("schema_version") != EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    for field in (
        "agent_id",
        "external_agent_id",
        "status",
        "tool_result",
        "confidence",
        "warnings",
        "errors",
    ):
        if field not in payload:
            return False, f"missing_{field}"
    if not isinstance(payload.get("tool_result"), Mapping):
        return False, "invalid_tool_result"
    if _status_from_external(payload.get("status")) is None:
        return False, "invalid_status"
    if not isinstance(payload.get("warnings"), list):
        return False, "invalid_warnings"
    if not isinstance(payload.get("errors"), list):
        return False, "invalid_errors"
    return True, "ok"


def validate_external_compute_envelope(payload: Mapping[str, Any]) -> tuple[bool, str]:
    """Validate a compute endpoint envelope without validating tool_result."""
    if not isinstance(payload, Mapping):
        return False, "payload_not_mapping"
    if payload.get("schema_version") != EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if _status_from_external(payload.get("status")) is None:
        return False, "invalid_status"
    if not isinstance(payload.get("tool_result"), Mapping) or not payload.get("tool_result"):
        return False, "compute_tool_result_missing"
    return True, "ok"


def safe_adapter_failure_conclusion(
    agent_id: str,
    dimension: str,
    *,
    as_of: str,
    reason: str,
    external_agent_id: str = "",
    legacy_agent_id: str = "",
    external_status: str = "error",
) -> dict[str, Any]:
    """Return a validator-legal error conclusion when identity is known."""
    identity_reason = _identity_failure_reason(agent_id, dimension)
    if identity_reason:
        return _adapter_failure(
            identity_reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_AGENT_CONCLUSION_SCHEMA_VERSION,
        )
    normalized_as_of = _normalize_date_text(as_of)
    conclusion: ConclusionObject = {
        "schema": CONCLUSION_OBJECT_SCHEMA_VERSION,
        "schema_version": CONCLUSION_OBJECT_SCHEMA_VERSION,
        "agent_id": agent_id,
        "dimension": dimension,
        "stance": "not_evaluated",
        "confidence": 0.0,
        "status": "error",
        "evidence": [],
        "as_of": normalized_as_of,
        "data_as_of": normalized_as_of,
        "event_flags": [],
        "provenance": {
            "source": FIXED_DAG_EXTERNAL_ADAPTER_SOURCE,
            "adapter_source": FIXED_DAG_EXTERNAL_ADAPTER_SOURCE,
            "adapter_failure": True,
            "reason": _safe_code(reason),
            "external_status": _safe_code(external_status),
            "external_agent_id": _safe_string(external_agent_id, limit=120),
            "legacy_agent_id": _safe_string(legacy_agent_id, limit=120),
            "provider_invoked": False,
            "external_invoked": False,
        },
    }
    if agent_id == "sentiment_company_radar":
        conclusion["output_routes"] = list(SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES)
    valid, validation_reason = validate_conclusion_object(conclusion)
    if not valid:
        return _adapter_failure(
            f"failure_conclusion_invalid:{validation_reason}",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_AGENT_CONCLUSION_SCHEMA_VERSION,
        )
    return cast(dict[str, Any], conclusion)


def map_external_agent_conclusion_to_conclusion_object(
    payload: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Map an external agent_conclusion_v1 payload into conclusion_object_v1."""
    if payload.get("schema_version") != EXTERNAL_AGENT_CONCLUSION_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_agent_conclusion_schema",
            agent_id=str(payload.get("agent_id") or ""),
            external_agent_id=str(payload.get("external_agent_id") or ""),
            schema_version=str(payload.get("schema_version") or ""),
        )
    agent_id = str(payload.get("agent_id") or "").strip()
    dimension = str(payload.get("dimension") or "").strip()
    external_agent_id = str(payload.get("external_agent_id") or "").strip()
    legacy_agent_id = str(payload.get("legacy_agent_id") or "").strip()
    identity_reason = _identity_failure_reason(agent_id, dimension)
    if identity_reason:
        return _adapter_failure(
            identity_reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_AGENT_CONCLUSION_SCHEMA_VERSION,
        )

    role = str(payload.get("role") or "").strip()
    external_status = str(
        payload.get("status")
        or (envelope.get("status") if isinstance(envelope, Mapping) else "")
        or ""
    ).strip()
    internal_status = _status_from_external(external_status)
    if internal_status is None:
        return safe_adapter_failure_conclusion(
            agent_id,
            dimension,
            as_of=str(payload.get("as_of") or ""),
            reason="invalid_external_status",
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            external_status=external_status,
        )

    stance: str
    provenance_extra: dict[str, Any] = {}
    if isinstance(envelope, Mapping):
        envelope_schema = _safe_string(envelope.get("schema_version"), limit=120)
        if envelope_schema:
            provenance_extra["adapter_input_schema"] = envelope_schema
        if envelope_schema == EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION:
            provenance_extra["compute_envelope_status"] = _safe_code(envelope.get("status"))
    if role == "direction":
        if payload.get("stance") is None:
            return safe_adapter_failure_conclusion(
                agent_id,
                dimension,
                as_of=str(payload.get("as_of") or ""),
                reason="direction_stance_missing",
                external_agent_id=external_agent_id,
                legacy_agent_id=legacy_agent_id,
                external_status=external_status,
            )
        if payload.get("risk_score") is not None:
            return safe_adapter_failure_conclusion(
                agent_id,
                dimension,
                as_of=str(payload.get("as_of") or ""),
                reason="direction_must_not_have_risk_score",
                external_agent_id=external_agent_id,
                legacy_agent_id=legacy_agent_id,
                external_status=external_status,
            )
        stance = _safe_string(payload.get("stance"), limit=80)
    elif role == "gate_member":
        if dimension != "risk":
            return safe_adapter_failure_conclusion(
                agent_id,
                dimension,
                as_of=str(payload.get("as_of") or ""),
                reason="gate_member_dimension_mismatch",
                external_agent_id=external_agent_id,
                legacy_agent_id=legacy_agent_id,
                external_status=external_status,
            )
        if payload.get("risk_score") is None:
            return safe_adapter_failure_conclusion(
                agent_id,
                dimension,
                as_of=str(payload.get("as_of") or ""),
                reason="gate_member_risk_score_missing",
                external_agent_id=external_agent_id,
                legacy_agent_id=legacy_agent_id,
                external_status=external_status,
            )
        risk_score = _bounded_float(payload.get("risk_score"))
        stance = "risk_gate_member"
        provenance_extra["risk_score"] = risk_score
    else:
        return safe_adapter_failure_conclusion(
            agent_id,
            dimension,
            as_of=str(payload.get("as_of") or ""),
            reason="unsupported_agent_conclusion_role",
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            external_status=external_status,
        )

    as_of = _normalize_date_text(payload.get("as_of"))
    data_as_of = _normalize_date_text(payload.get("data_as_of") or as_of)
    if not _data_not_after(data_as_of, as_of):
        return safe_adapter_failure_conclusion(
            agent_id,
            dimension,
            as_of=as_of,
            reason="data_as_of_after_as_of",
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            external_status=external_status,
        )

    conclusion: ConclusionObject = {
        "schema": CONCLUSION_OBJECT_SCHEMA_VERSION,
        "schema_version": CONCLUSION_OBJECT_SCHEMA_VERSION,
        "agent_id": agent_id,
        "dimension": dimension,
        "stance": stance or "not_evaluated",
        "confidence": _bounded_float(payload.get("confidence")),
        "status": internal_status,
        "evidence": _safe_evidence_items(payload.get("evidence")),
        "as_of": as_of,
        "data_as_of": data_as_of,
        "event_flags": _safe_event_flags(payload.get("event_flags")),
        "provenance": {
            "source": FIXED_DAG_EXTERNAL_ADAPTER_SOURCE,
            "adapter_source": FIXED_DAG_EXTERNAL_ADAPTER_SOURCE,
            "external_agent_id": _safe_string(external_agent_id, limit=120),
            "legacy_agent_id": _safe_string(legacy_agent_id, limit=120),
            "external_status": _safe_code(external_status),
            "provider_invoked": False,
            "external_invoked": False,
            "raw_output_keys": _safe_keys_summary(payload.get("raw_output")),
            "quality_keys": _safe_keys_summary(payload.get("quality")),
            **_public_safe_business_context(payload),
            **provenance_extra,
        },
    }
    if agent_id == "sentiment_company_radar":
        conclusion["output_routes"] = list(SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES)

    valid, reason = validate_conclusion_object(conclusion)
    if not valid:
        return safe_adapter_failure_conclusion(
            agent_id,
            dimension,
            as_of=as_of,
            reason=f"mapped_conclusion_invalid:{reason}",
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            external_status=external_status,
        )
    return cast(dict[str, Any], conclusion)


def map_external_data_bundle_to_data_bundle(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map an external data_bundle_v1 payload into the current narrow DataBundle."""
    if payload.get("schema_version") != EXTERNAL_DATA_BUNDLE_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_data_bundle_schema",
            schema_version=str(payload.get("schema_version") or ""),
        )
    status = _status_from_external(payload.get("status"))
    if status is None:
        return _adapter_failure("invalid_external_status", schema_version=EXTERNAL_DATA_BUNDLE_SCHEMA_VERSION)

    as_of = _normalize_date_text(payload.get("as_of"))
    data_as_of = _normalize_date_text(payload.get("data_as_of") or as_of)
    if not _data_not_after(data_as_of, as_of):
        return _adapter_failure(
            "data_as_of_after_as_of",
            schema_version=EXTERNAL_DATA_BUNDLE_SCHEMA_VERSION,
        )

    notes = [
        "Mapped by fixed_dag_external_adapter.",
        "No HTTP, provider, or live external invocation was performed by this adapter.",
    ]
    snapshot_id = _safe_string(payload.get("snapshot_id"), limit=160)
    if snapshot_id:
        notes.append(f"snapshot_id: {snapshot_id}")
    publish_time = _safe_string(_normalize_date_text(payload.get("publish_time")), limit=80)
    if publish_time and publish_time != "not_available":
        notes.append(f"publish_time: {publish_time}")
    feature_bundle = payload.get("feature_bundle")
    if isinstance(feature_bundle, Mapping):
        notes.extend(_safe_note_values("feature_key", feature_bundle.keys()))
    missing_fields = payload.get("missing_fields")
    if isinstance(missing_fields, list):
        notes.extend(_safe_note_values("missing_field", missing_fields))

    bundle: DataBundle = {
        "schema": DATA_BUNDLE_SCHEMA_VERSION,
        "schema_version": DATA_BUNDLE_SCHEMA_VERSION,
        "status": status,
        "as_of": as_of,
        "data_as_of": data_as_of,
        "sources": _source_strings(payload.get("sources")),
        "notes": notes[:30],
    }
    valid, reason = validate_data_bundle(bundle)
    if not valid:
        return _adapter_failure(
            f"mapped_data_bundle_invalid:{reason}",
            schema_version=EXTERNAL_DATA_BUNDLE_SCHEMA_VERSION,
        )
    return cast(dict[str, Any], bundle)


def map_external_entity_relation_bundle_to_entity_relation_bundle(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Map an external entity_relation_bundle_v1 payload into EntityRelationBundle."""
    if payload.get("schema_version") != EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_entity_relation_bundle_schema",
            schema_version=str(payload.get("schema_version") or ""),
        )
    status = _status_from_external(payload.get("status"))
    if status is None:
        return _adapter_failure(
            "invalid_external_status",
            schema_version=EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
        )

    as_of = _normalize_date_text(payload.get("as_of"))
    data_as_of = _normalize_date_text(payload.get("data_as_of") or as_of)
    if not _data_not_after(data_as_of, as_of):
        return _adapter_failure(
            "data_as_of_after_as_of",
            schema_version=EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
        )

    notes = [
        "Mapped by fixed_dag_external_adapter.",
        "No HTTP, provider, or live external invocation was performed by this adapter.",
    ]
    notes.extend(_safe_note_values("source", _source_strings(payload.get("sources"))))
    notes.extend(_safe_note_values("note", payload.get("notes") or []))

    bundle: EntityRelationBundle = {
        "schema": ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
        "schema_version": ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
        "status": status,
        "as_of": as_of,
        "data_as_of": data_as_of,
        "entities": _safe_mapping_items(payload.get("entities")),
        "relations": _safe_mapping_items(payload.get("relations")),
        "notes": notes[:30],
    }
    valid, reason = validate_entity_relation_bundle(bundle)
    if not valid:
        return _adapter_failure(
            f"mapped_entity_relation_bundle_invalid:{reason}",
            schema_version=EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
        )
    return cast(dict[str, Any], bundle)


def map_external_dimension_conclusion_to_dimension_composite_result(
    payload: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a value/market dimension_conclusion_v1 payload into an L3 composite."""
    if payload.get("schema_version") != EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_dimension_conclusion_schema",
            agent_id=str(payload.get("agent_id") or ""),
            external_agent_id=str(payload.get("external_agent_id") or ""),
            schema_version=str(payload.get("schema_version") or ""),
        )
    agent_id = str(payload.get("agent_id") or "").strip()
    dimension = str(payload.get("dimension") or "").strip()
    external_agent_id = str(payload.get("external_agent_id") or "").strip()
    legacy_agent_id = str(payload.get("legacy_agent_id") or "").strip()
    if dimension not in {"value", "market"}:
        return _adapter_failure(
            "dimension_conclusion_dimension_mismatch",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
        )
    if agent_id != DIMENSION_COMPOSITE_AGENT_IDS[dimension]:
        return _adapter_failure(
            "dimension_conclusion_agent_mismatch",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
        )
    if payload.get("role") not in (None, "", "direction"):
        return _adapter_failure(
            "dimension_conclusion_role_mismatch",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
        )
    status = _status_from_external(
        payload.get("status") or (envelope.get("status") if isinstance(envelope, Mapping) else "")
    )
    if status is None:
        return _adapter_failure(
            "invalid_external_status",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
        )
    members_value = payload.get("members")
    if not isinstance(members_value, list) or not members_value:
        return _adapter_failure(
            "dimension_members_missing",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
        )
    members: list[Mapping[str, Any]] = []
    weights: dict[str, float] = {}
    seen_members: set[str] = set()
    total_weight = 0.0
    allowed_agents = set(DIMENSION_GROUPS[dimension])
    for item in members_value:
        if not isinstance(item, Mapping):
            return _adapter_failure(
                "invalid_dimension_member",
                agent_id=agent_id,
                external_agent_id=external_agent_id,
                schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
            )
        member_agent_id = str(item.get("agent_id") or "").strip()
        if member_agent_id not in allowed_agents:
            return _adapter_failure(
                "dimension_member_agent_mismatch",
                agent_id=agent_id,
                external_agent_id=external_agent_id,
                schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
            )
        if member_agent_id in seen_members:
            return _adapter_failure(
                "duplicate_dimension_member",
                agent_id=agent_id,
                external_agent_id=external_agent_id,
                schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
            )
        weight, reason = _numeric_in_range(item.get("weight"), field="member_weight")
        if reason:
            return _adapter_failure(
                reason,
                agent_id=agent_id,
                external_agent_id=external_agent_id,
                schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
            )
        total_weight += weight
        weights[member_agent_id] = weight
        seen_members.add(member_agent_id)
        members.append(item)
    if abs(total_weight - 1.0) > 0.01:
        return _adapter_failure(
            "dimension_member_weight_sum_mismatch",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
                schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
            )
    contributing_agents, contribution_reason = _validate_l3_real_contributors(
        members=members,
        weights=weights,
        declared_contributing_agents=payload.get("contributing_agents"),
        evidence=payload.get("evidence"),
    )
    if contribution_reason:
        return _adapter_failure(
            contribution_reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
        )
    confidence, reason = _numeric_in_range(payload.get("confidence"), field="confidence")
    if reason:
        return _adapter_failure(
            reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
        )
    as_of, data_as_of, failure = _validate_l3_dates(
        payload,
        schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
        agent_id=agent_id,
        external_agent_id=external_agent_id,
    )
    if failure is not None:
        return failure
    result: DimensionCompositeResult = {
        "schema": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "schema_version": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "agent_id": agent_id,
        "dimension": dimension,
        "stance": _safe_string(payload.get("stance"), limit=80) or "not_evaluated",
        "confidence": confidence,
        "status": status,
        "contributing_agents": contributing_agents,
        "evidence_refs": _safe_evidence_refs(payload.get("evidence")),
        "as_of": as_of,
        "data_as_of": data_as_of,
        "vote_type": _safe_string(
            payload.get("method") or payload.get("vote_type") or "weighted_member_vote",
            limit=120,
        ),
        "provenance": _composite_provenance(
            input_schema=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            envelope=envelope,
            extra={
                "member_weight_summary": _member_weight_summary(members),
                "event_flags": _safe_event_flags(payload.get("event_flags")),
                **_public_safe_l3_business_context(payload),
            },
        ),
    }
    valid, validation_reason = validate_dimension_composite_result(result)
    if not valid:
        return _adapter_failure(
            f"mapped_dimension_composite_invalid:{validation_reason}",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION,
        )
    return cast(dict[str, Any], result)


def map_external_risk_conclusion_to_dimension_composite_result(
    payload: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a risk_conclusion_v1 gate payload into an L3 risk composite."""
    if payload.get("schema_version") != EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_risk_conclusion_schema",
            agent_id=str(payload.get("agent_id") or ""),
            external_agent_id=str(payload.get("external_agent_id") or ""),
            schema_version=str(payload.get("schema_version") or ""),
        )
    agent_id = str(payload.get("agent_id") or "").strip()
    dimension = str(payload.get("dimension") or "").strip()
    external_agent_id = str(payload.get("external_agent_id") or "").strip()
    legacy_agent_id = str(payload.get("legacy_agent_id") or "").strip()
    if agent_id != "risk_composite" or dimension != "risk":
        return _adapter_failure(
            "risk_conclusion_identity_mismatch",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    if payload.get("role") != "gate":
        return _adapter_failure(
            "risk_role_must_be_gate",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    if payload.get("stance") not in (None, ""):
        return _adapter_failure(
            "risk_conclusion_must_not_have_stance",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    gate = _safe_code(payload.get("gate"))
    if gate not in {"pass", "penalty", "veto", "manual_review"}:
        return _adapter_failure(
            "invalid_risk_gate",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    status = _status_from_external(
        payload.get("status") or (envelope.get("status") if isinstance(envelope, Mapping) else "")
    )
    if status is None:
        return _adapter_failure(
            "invalid_external_status",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    declared_contributing_agents = _safe_string_list(payload.get("contributing_agents"), limit=12)
    if not declared_contributing_agents:
        return _adapter_failure(
            "contributing_agents_missing",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
                schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    if not set(declared_contributing_agents) <= set(DIMENSION_GROUPS["risk"]):
        reason = (
            "risk_reads_sentiment"
            if "sentiment_company_radar" in declared_contributing_agents
            else "contributing_agents_mismatch"
        )
        return _adapter_failure(
            reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    contributing_agents = declared_contributing_agents
    members_value = payload.get("members")
    if isinstance(members_value, list):
        member_items = [item for item in members_value if isinstance(item, Mapping)]
        weights: dict[str, float] = {}
        for item in member_items:
            member_agent_id = str(item.get("agent_id") or "").strip()
            if member_agent_id in DIMENSION_GROUPS["risk"]:
                weights[member_agent_id] = _bounded_float(item.get("weight"), default=0.0)
        real_contributors, contribution_reason = _validate_l3_real_contributors(
            members=member_items,
            weights=weights,
            declared_contributing_agents=declared_contributing_agents,
            evidence=payload.get("evidence"),
        )
        if contribution_reason:
            return _adapter_failure(
                contribution_reason,
                agent_id=agent_id,
                external_agent_id=external_agent_id,
                schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
            )
        contributing_agents = real_contributors
    risk_score, reason = _numeric_in_range(payload.get("risk_score"), field="risk_score")
    if reason:
        return _adapter_failure(
            reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    if gate == "manual_review":
        penalty = _bounded_float(payload.get("penalty"), default=0.0)
    else:
        penalty, reason = _numeric_in_range(payload.get("penalty"), field="penalty")
        if reason:
            return _adapter_failure(
                reason,
                agent_id=agent_id,
                external_agent_id=external_agent_id,
                schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
            )
    confidence, reason = _numeric_in_range(payload.get("confidence"), field="confidence")
    if reason:
        return _adapter_failure(
            reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    as_of, data_as_of, failure = _validate_l3_dates(
        payload,
        schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        agent_id=agent_id,
        external_agent_id=external_agent_id,
    )
    if failure is not None:
        return failure
    result: DimensionCompositeResult = {
        "schema": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "schema_version": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "agent_id": "risk_composite",
        "dimension": "risk",
        "stance": "risk_gate",
        "confidence": confidence,
        "status": status,
        "contributing_agents": contributing_agents,
        "evidence_refs": _safe_evidence_refs(payload.get("evidence")),
        "as_of": as_of,
        "data_as_of": data_as_of,
        "gate": gate,
        "veto": gate == "veto",
        "penalty": penalty,
        "risk_score": risk_score,
        "provenance": _composite_provenance(
            input_schema=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            envelope=envelope,
            extra={
                "member_weight_summary": _member_weight_summary(payload.get("members")),
                "triggered_flags": _safe_string_list(payload.get("triggered_flags"), limit=12),
                "red_lines": _safe_string_list(payload.get("red_lines"), limit=12),
                "event_flags": _safe_event_flags(payload.get("event_flags")),
                **_public_safe_l3_business_context(payload),
            },
        ),
    }
    valid, validation_reason = validate_dimension_composite_result(result)
    if not valid:
        return _adapter_failure(
            f"mapped_risk_composite_invalid:{validation_reason}",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION,
        )
    return cast(dict[str, Any], result)


def map_external_macro_conclusion_to_dimension_composite_result(
    payload: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a macro_conclusion_v1 regulator payload into an L3 macro composite."""
    if payload.get("schema_version") != EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_macro_conclusion_schema",
            agent_id=str(payload.get("agent_id") or ""),
            external_agent_id=str(payload.get("external_agent_id") or ""),
            schema_version=str(payload.get("schema_version") or ""),
        )
    agent_id = str(payload.get("agent_id") or "").strip()
    dimension = str(payload.get("dimension") or "").strip()
    external_agent_id = str(payload.get("external_agent_id") or "").strip()
    legacy_agent_id = str(payload.get("legacy_agent_id") or "").strip()
    if agent_id != "macro_composite" or dimension != "macro":
        return _adapter_failure(
            "macro_conclusion_identity_mismatch",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    if payload.get("role") != "regulator":
        return _adapter_failure(
            "macro_role_must_be_regulator",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    if payload.get("stance") not in (None, ""):
        return _adapter_failure(
            "macro_conclusion_must_not_have_stance",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    regime = _safe_string(payload.get("regime"), limit=120)
    if not regime:
        return _adapter_failure(
            "regime_missing",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    status = _status_from_external(
        payload.get("status") or (envelope.get("status") if isinstance(envelope, Mapping) else "")
    )
    if status is None:
        return _adapter_failure(
            "invalid_external_status",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    declared_contributing_agents = _safe_string_list(payload.get("contributing_agents"), limit=12)
    if not declared_contributing_agents:
        return _adapter_failure(
            "contributing_agents_missing",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
                schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    if not set(declared_contributing_agents) <= set(DIMENSION_GROUPS["macro"]):
        return _adapter_failure(
            "contributing_agents_mismatch",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    members_failure = _validate_macro_member_packet(payload.get("members"))
    if members_failure:
        return _adapter_failure(
            members_failure,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    contributing_agents = declared_contributing_agents
    dimension_weights, reason = _bounded_float_mapping(
        payload.get("dimension_weights"),
        allowed_keys={"value", "market"},
        require_exact_keys=True,
    )
    if reason:
        return _adapter_failure(
            reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    risk_sensitivity, reason = _numeric_in_range(
        payload.get("risk_sensitivity"),
        field="risk_sensitivity",
    )
    if reason:
        return _adapter_failure(
            reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    confidence, reason = _numeric_in_range(payload.get("confidence"), field="confidence")
    if reason:
        return _adapter_failure(
            reason,
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    as_of, data_as_of, failure = _validate_l3_dates(
        payload,
        schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        agent_id=agent_id,
        external_agent_id=external_agent_id,
    )
    if failure is not None:
        return failure
    style_bias, _ = _bounded_float_mapping(
        payload.get("style_bias") or {},
        allowed_keys={"growth", "value", "quality", "defensive", "cyclical"},
        require_exact_keys=False,
    )
    member_items: list[Mapping[str, Any]] = []
    raw_members = payload.get("members")
    if isinstance(raw_members, Mapping):
        member_items = [
            {**dict(value), "agent_id": str(member_id)}
            for member_id, value in raw_members.items()
            if isinstance(value, Mapping)
        ]
    elif isinstance(raw_members, list):
        member_items = [item for item in raw_members if isinstance(item, Mapping)]
    if member_items:
        weights: dict[str, float] = {}
        for item in member_items:
            member_agent_id = str(item.get("agent_id") or "").strip()
            if member_agent_id in DIMENSION_GROUPS["macro"]:
                weights[member_agent_id] = _bounded_float(item.get("weight"), default=0.0)
        real_contributors, contribution_reason = _validate_l3_real_contributors(
            members=member_items,
            weights=weights,
            declared_contributing_agents=declared_contributing_agents,
            evidence=payload.get("evidence"),
        )
        if contribution_reason:
            return _adapter_failure(
                contribution_reason,
                agent_id=agent_id,
                external_agent_id=external_agent_id,
                schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
            )
        contributing_agents = real_contributors
    result: DimensionCompositeResult = {
        "schema": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "schema_version": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "agent_id": "macro_composite",
        "dimension": "macro",
        "stance": "macro_regulator",
        "confidence": confidence,
        "status": status,
        "contributing_agents": contributing_agents,
        "evidence_refs": _safe_evidence_refs(payload.get("evidence")),
        "as_of": as_of,
        "data_as_of": data_as_of,
        "regime": regime,
        "dimension_weights": dimension_weights,
        "risk_sensitivity": risk_sensitivity,
        "provenance": _composite_provenance(
            input_schema=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
            external_agent_id=external_agent_id,
            legacy_agent_id=legacy_agent_id,
            envelope=envelope,
            extra={
                "member_weight_summary": _member_weight_summary(payload.get("members")),
                "style_bias": style_bias,
                "event_flags": _safe_event_flags(payload.get("event_flags")),
                **_public_safe_l3_business_context(payload),
            },
        ),
    }
    valid, validation_reason = validate_dimension_composite_result(result)
    if not valid:
        return _adapter_failure(
            f"mapped_macro_composite_invalid:{validation_reason}",
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            schema_version=EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION,
        )
    return cast(dict[str, Any], result)


def _validate_macro_member_packet(members: Any) -> str:
    if members in (None, ""):
        return ""
    allowed_agents = set(DIMENSION_GROUPS["macro"])
    if isinstance(members, Mapping):
        items = [
            (str(agent_id or "").strip(), value if isinstance(value, Mapping) else {})
            for agent_id, value in members.items()
        ]
    elif isinstance(members, list):
        items = []
        for item in members:
            if not isinstance(item, Mapping):
                return "invalid_macro_member"
            items.append((str(item.get("agent_id") or "").strip(), item))
    else:
        return "invalid_macro_members"

    seen: set[str] = set()
    for member_agent_id, item in items:
        if member_agent_id not in allowed_agents:
            return "macro_member_agent_mismatch"
        if member_agent_id in seen:
            return "duplicate_macro_member"
        seen.add(member_agent_id)

        status = str(item.get("status") or "").strip()
        if status in {"error", "partial", "pending", "not_available"}:
            weight_value = item.get("weight")
            if weight_value not in (None, ""):
                weight, reason = _numeric_in_range(
                    weight_value,
                    field="member_weight",
                )
                if reason:
                    return reason
                if weight > 0.0:
                    return "macro_pending_member_weight_nonzero"
    return ""


def _safe_l4_text(value: Any, *, limit: int = 700) -> str:
    text = str(value or "").strip().replace("\r\n", "\n").replace("\r", "\n")
    if not text or _contains_unsafe_text(text):
        return ""
    if len(text) > limit:
        return f"{text[:limit].rstrip()}..."
    return text


def _safe_l4_float(
    value: Any,
    *,
    default: float = 0.0,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _contains_l4_unsafe_text(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_l4_unsafe_text(key) or _contains_l4_unsafe_text(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_l4_unsafe_text(item) for item in value)
    if isinstance(value, str):
        return _contains_unsafe_text(value)
    return False


def _safe_l4_target_range(value: Any) -> dict[str, float | None]:
    if not isinstance(value, Mapping):
        return {"low": None, "mid": None, "high": None}
    result: dict[str, float | None] = {}
    for key in ("low", "mid", "high"):
        raw = value.get(key)
        if raw is None or raw == "":
            result[key] = None
            continue
        try:
            result[key] = float(raw)
        except (TypeError, ValueError):
            result[key] = None
    return result


def _safe_l4_detail(value: Any, *, depth: int = 0) -> Any:
    if depth > 3 or _contains_l4_unsafe_text(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        return _safe_l4_text(value, limit=240) or None
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, raw in list(value.items())[:16]:
            safe_key = _safe_l4_text(key, limit=80)
            if not safe_key:
                continue
            bounded = _safe_l4_detail(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                result[safe_key] = bounded
        return result or None
    if isinstance(value, list):
        items: list[Any] = []
        for raw in value[:12]:
            bounded = _safe_l4_detail(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                items.append(bounded)
        return items or None
    return _safe_l4_text(value, limit=160) or None


def map_external_decision_result_to_decision_result(
    payload: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a L4 decision_result_v1 payload from an external compute service."""
    external_agent_id = str(
        envelope.get("external_agent_id") if isinstance(envelope, Mapping) else ""
    )
    if payload.get("schema") != DECISION_RESULT_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_decision_result_schema",
            agent_id="decision_synthesizer",
            external_agent_id=external_agent_id,
            schema_version=str(payload.get("schema") or payload.get("schema_version") or ""),
        )
    if payload.get("schema_version", DECISION_RESULT_SCHEMA_VERSION) != DECISION_RESULT_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_decision_result_schema_version",
            agent_id="decision_synthesizer",
            external_agent_id=external_agent_id,
            schema_version=str(payload.get("schema_version") or ""),
        )
    if _contains_l4_unsafe_text(payload):
        return _adapter_failure(
            "unsafe_decision_result",
            agent_id="decision_synthesizer",
            external_agent_id=external_agent_id,
            schema_version=DECISION_RESULT_SCHEMA_VERSION,
        )
    dimension_views = _safe_l4_detail(payload.get("dimension_views"))
    reasoning_trace = _safe_l4_detail(payload.get("reasoning_trace"))
    decision: DecisionResult = {
        "schema": DECISION_RESULT_SCHEMA_VERSION,
        "schema_version": DECISION_RESULT_SCHEMA_VERSION,
        "decision": _safe_l4_text(payload.get("decision"), limit=80) or "partial_review",
        "score": _safe_l4_float(payload.get("score"), minimum=-1.0, maximum=1.0),
        "target_price_range": _safe_l4_target_range(payload.get("target_price_range")),
        "dimension_views": dict(dimension_views) if isinstance(dimension_views, Mapping) else {},
        "reasoning_trace": list(reasoning_trace) if isinstance(reasoning_trace, list) else [],
        "confidence": _safe_l4_float(payload.get("confidence")),
        "status": _safe_code(payload.get("status") or "partial"),
        "as_of": _safe_l4_text(payload.get("as_of"), limit=40),
    }
    valid, reason = validate_decision_result(decision)
    if not valid:
        return _adapter_failure(
            f"decision_result_invalid:{reason}",
            agent_id="decision_synthesizer",
            external_agent_id=external_agent_id,
            schema_version=DECISION_RESULT_SCHEMA_VERSION,
        )
    return cast(dict[str, Any], decision)


def _safe_report_sections(value: Any) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    if not isinstance(value, list):
        return sections
    for index, item in enumerate(value[:8]):
        if not isinstance(item, Mapping):
            continue
        title = _safe_l4_text(item.get("title"), limit=80)
        content = _safe_l4_text(item.get("content"), limit=1400)
        if title and content:
            section_id = _safe_code(item.get("id") or f"section_{index + 1}")
            sections.append({"id": section_id, "title": title, "content": content})
    return sections


def _safe_report_cards(value: Any) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    if not isinstance(value, list):
        return cards
    for item in value[:10]:
        if not isinstance(item, Mapping):
            continue
        title = _safe_l4_text(item.get("title"), limit=80)
        note = _safe_l4_text(item.get("note"), limit=320)
        if title and note:
            cards.append({"title": title, "note": note})
    return cards


_L4_REPORT_BOUNDARY = (
    "L4 报告生成智能体仅在显式计算白名单路径下运行，"
    "不改变默认运行配置，也不代表生产默认启用。"
)
_L4_REPORT_BOUNDARY_MARKERS = (
    "L4 report_generator",
    "L4 报告生成智能体",
    "compute-only",
    "compute allowlist",
    "显式计算白名单路径",
)


def _safe_l4_report_limitations(value: Any) -> list[str]:
    limitations: list[str] = []
    seen: set[str] = set()
    if isinstance(value, list):
        for item in value:
            text = _safe_l4_text(item, limit=220)
            if not text:
                continue
            if any(marker in text for marker in _L4_REPORT_BOUNDARY_MARKERS):
                continue
            key = " ".join(text.strip().split())
            if key in seen:
                continue
            seen.add(key)
            limitations.append(text)
    limitations.append(_L4_REPORT_BOUNDARY)
    return limitations


def map_external_report_result_to_report_result(
    payload: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a L4 report_result_v1 payload from an external compute service."""
    external_agent_id = str(
        envelope.get("external_agent_id") if isinstance(envelope, Mapping) else ""
    )
    if payload.get("schema") != REPORT_RESULT_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_report_result_schema",
            agent_id="report_generator",
            external_agent_id=external_agent_id,
            schema_version=str(payload.get("schema") or payload.get("schema_version") or ""),
        )
    if payload.get("schema_version", REPORT_RESULT_SCHEMA_VERSION) != REPORT_RESULT_SCHEMA_VERSION:
        return _adapter_failure(
            "invalid_report_result_schema_version",
            agent_id="report_generator",
            external_agent_id=external_agent_id,
            schema_version=str(payload.get("schema_version") or ""),
        )
    if _contains_l4_unsafe_text(payload):
        return _adapter_failure(
            "unsafe_report_result",
            agent_id="report_generator",
            external_agent_id=external_agent_id,
            schema_version=REPORT_RESULT_SCHEMA_VERSION,
        )
    answer = _safe_l4_text(payload.get("answer"), limit=7000)
    if answer and "研判流程" not in answer:
        answer = f"研判流程报告：\n{answer}"
    report: ReportResult = {
        "schema": REPORT_RESULT_SCHEMA_VERSION,
        "schema_version": REPORT_RESULT_SCHEMA_VERSION,
        "title": _safe_l4_text(payload.get("title"), limit=80) or "固定 DAG 研判报告",
        "answer": answer,
        "status": _safe_code(payload.get("status") or "partial"),
        "sections": _safe_report_sections(payload.get("sections")),
        "evidence_cards": _safe_report_cards(payload.get("evidence_cards")),
        "limitations": _safe_l4_report_limitations(payload.get("limitations")),
    }
    valid, reason = validate_report_result(report)
    if not valid:
        return _adapter_failure(
            f"report_result_invalid:{reason}",
            agent_id="report_generator",
            external_agent_id=external_agent_id,
            schema_version=REPORT_RESULT_SCHEMA_VERSION,
        )
    return cast(dict[str, Any], report)


def map_external_compute_envelope_to_fixed_dag_object(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map a compute endpoint envelope to a supported internal fixed-DAG object."""
    valid, reason = validate_external_compute_envelope(payload)
    if not valid:
        return _adapter_failure(
            reason,
            agent_id=str(payload.get("agent_id") or ""),
            external_agent_id=str(payload.get("external_agent_id") or ""),
            schema_version=str(payload.get("schema_version") or ""),
        )
    tool_result = cast(Mapping[str, Any], payload["tool_result"])
    schema_version = tool_result.get("schema_version")
    if schema_version == EXTERNAL_AGENT_CONCLUSION_SCHEMA_VERSION:
        return map_external_agent_conclusion_to_conclusion_object(tool_result, envelope=payload)
    if schema_version == EXTERNAL_DATA_BUNDLE_SCHEMA_VERSION:
        return map_external_data_bundle_to_data_bundle(tool_result)
    if schema_version == EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION:
        return map_external_entity_relation_bundle_to_entity_relation_bundle(tool_result)
    if schema_version == EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION:
        return map_external_dimension_conclusion_to_dimension_composite_result(
            tool_result,
            envelope=payload,
        )
    if schema_version == EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION:
        return map_external_risk_conclusion_to_dimension_composite_result(
            tool_result,
            envelope=payload,
        )
    if schema_version == EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION:
        return map_external_macro_conclusion_to_dimension_composite_result(
            tool_result,
            envelope=payload,
        )
    if schema_version == DECISION_RESULT_SCHEMA_VERSION:
        return map_external_decision_result_to_decision_result(tool_result, envelope=payload)
    if schema_version == REPORT_RESULT_SCHEMA_VERSION:
        return map_external_report_result_to_report_result(tool_result, envelope=payload)
    return _adapter_failure(
        "unsupported_compute_tool_result_schema",
        agent_id=str(payload.get("agent_id") or ""),
        external_agent_id=str(payload.get("external_agent_id") or ""),
        schema_version=str(schema_version or ""),
    )


def map_external_response_to_fixed_dag_object(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map an external response envelope or supported tool_result to an internal object."""
    if payload.get("schema_version") == EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION:
        valid, reason = validate_external_response_envelope(payload)
        if not valid:
            return _adapter_failure(
                reason,
                agent_id=str(payload.get("agent_id") or ""),
                external_agent_id=str(payload.get("external_agent_id") or ""),
                schema_version=str(payload.get("schema_version") or ""),
            )
        tool_result = cast(Mapping[str, Any], payload["tool_result"])
        schema_version = tool_result.get("schema_version")
        if schema_version == EXTERNAL_AGENT_CONCLUSION_SCHEMA_VERSION:
            return map_external_agent_conclusion_to_conclusion_object(tool_result, envelope=payload)
        if schema_version == EXTERNAL_DATA_BUNDLE_SCHEMA_VERSION:
            return map_external_data_bundle_to_data_bundle(tool_result)
        if schema_version == EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION:
            return map_external_entity_relation_bundle_to_entity_relation_bundle(tool_result)
        if schema_version == EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION:
            return map_external_dimension_conclusion_to_dimension_composite_result(
                tool_result,
                envelope=payload,
            )
        if schema_version == EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION:
            return map_external_risk_conclusion_to_dimension_composite_result(
                tool_result,
                envelope=payload,
            )
        if schema_version == EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION:
            return map_external_macro_conclusion_to_dimension_composite_result(
                tool_result,
                envelope=payload,
            )
        if schema_version == DECISION_RESULT_SCHEMA_VERSION:
            return map_external_decision_result_to_decision_result(tool_result, envelope=payload)
        if schema_version == REPORT_RESULT_SCHEMA_VERSION:
            return map_external_report_result_to_report_result(tool_result, envelope=payload)
        return _adapter_failure(
            "unsupported_tool_result_schema",
            agent_id=str(payload.get("agent_id") or ""),
            external_agent_id=str(payload.get("external_agent_id") or ""),
            schema_version=str(schema_version or ""),
        )

    if payload.get("schema_version") == EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION:
        return map_external_compute_envelope_to_fixed_dag_object(payload)

    schema_version = payload.get("schema_version")
    if schema_version == EXTERNAL_AGENT_CONCLUSION_SCHEMA_VERSION:
        return map_external_agent_conclusion_to_conclusion_object(payload)
    if schema_version == EXTERNAL_DATA_BUNDLE_SCHEMA_VERSION:
        return map_external_data_bundle_to_data_bundle(payload)
    if schema_version == EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION:
        return map_external_entity_relation_bundle_to_entity_relation_bundle(payload)
    if schema_version == EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION:
        return map_external_dimension_conclusion_to_dimension_composite_result(payload)
    if schema_version == EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION:
        return map_external_risk_conclusion_to_dimension_composite_result(payload)
    if schema_version == EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION:
        return map_external_macro_conclusion_to_dimension_composite_result(payload)
    if schema_version == DECISION_RESULT_SCHEMA_VERSION:
        return map_external_decision_result_to_decision_result(payload)
    if schema_version == REPORT_RESULT_SCHEMA_VERSION:
        return map_external_report_result_to_report_result(payload)
    return _adapter_failure("unsupported_schema_version", schema_version=str(schema_version or ""))


__all__ = [
    "ADAPTER_FAILURE_SCHEMA_VERSION",
    "EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION",
    "EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION",
    "EXTERNAL_DIMENSION_CONCLUSION_SCHEMA_VERSION",
    "EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION",
    "EXTERNAL_MACRO_CONCLUSION_SCHEMA_VERSION",
    "EXTERNAL_RISK_CONCLUSION_SCHEMA_VERSION",
    "FIXED_DAG_EXTERNAL_ADAPTER_SOURCE",
    "map_external_compute_envelope_to_fixed_dag_object",
    "map_external_agent_conclusion_to_conclusion_object",
    "map_external_data_bundle_to_data_bundle",
    "map_external_decision_result_to_decision_result",
    "map_external_dimension_conclusion_to_dimension_composite_result",
    "map_external_entity_relation_bundle_to_entity_relation_bundle",
    "map_external_macro_conclusion_to_dimension_composite_result",
    "map_external_report_result_to_report_result",
    "map_external_response_to_fixed_dag_object",
    "map_external_risk_conclusion_to_dimension_composite_result",
    "safe_adapter_failure_conclusion",
    "validate_external_compute_envelope",
    "validate_external_response_envelope",
]
