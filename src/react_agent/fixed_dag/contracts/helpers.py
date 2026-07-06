# ruff: noqa: D101, D103
"""Composite helper functions for deterministic fixed-DAG contracts.
Lowest-level utility functions: member evaluation, bounded values, direction
labels, weight aggregation, composite provenance.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from react_agent.fixed_dag.constants import (
    AGENT_DIMENSIONS,
    DEFAULT_AS_OF,
    DIMENSION_GROUPS,
    L2_CONCLUSION_AGENT_IDS,
)
from react_agent.fixed_dag.labels import AGENT_TITLE_LABELS
from react_agent.fixed_dag.safety import _safe_public_float
from react_agent.fixed_dag.types import ConclusionStatus

def _as_of(value: str | None = None) -> str:
    text = str(value or "").strip()
    return text or DEFAULT_AS_OF


def _data_as_of_for(as_of: str) -> str:
    return as_of


def _data_not_after(data_as_of: Any, as_of: Any) -> bool:
    left = str(data_as_of or "")
    right = str(as_of or "")
    if not left or not right:
        return False
    return left <= right


def _status_for_expected(
    expected_agent_ids: tuple[str, ...],
    conclusions: Mapping[str, Any],
) -> ConclusionStatus:
    member_statuses = [
        _member_status(conclusions.get(agent_id))
        for agent_id in expected_agent_ids
        if agent_id in conclusions
    ]
    if not member_statuses:
        return "pending_implementation"
    if any(status in {"complete", "partial"} for status in member_statuses):
        if (
            len(member_statuses) == len(expected_agent_ids)
            and all(status == "complete" for status in member_statuses)
        ):
            return "complete"
        return "partial"
    if all(status == "error" for status in member_statuses):
        return "error"
    return "pending_implementation"


def _member_status(result: Any) -> ConclusionStatus:
    if not isinstance(result, Mapping):
        return "pending_implementation"
    status = str(result.get("status") or "pending_implementation")
    if status in {"pending_implementation", "partial", "complete", "error"}:
        return cast(ConclusionStatus, status)
    return "pending_implementation"


def _bounded_composite_text(value: Any, *, limit: int = 180) -> str:
    text = str(value or "").strip().replace("\n", " ").replace("\r", " ")
    lowered = text.lower()
    unsafe_tokens = (
        "api_key",
        "secret",
        "token",
        "password",
        "authorization",
        "endpoint",
        "raw_response",
        "raw_provider_response",
        "raw_external_json",
        "traceback",
        "chain-of-thought",
        "/v1/agent/invoke",
    )
    if any(token in lowered for token in unsafe_tokens):
        return ""
    if len(text) > limit:
        return text[: max(limit - 3, 0)].rstrip() + "..."
    return text


def _bounded_composite_float(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _bounded_direction_score(value: Any) -> float | None:
    if isinstance(value, int | float):
        return max(-1.0, min(1.0, float(value)))
    text = str(value or "").strip().lower()
    if not text:
        return None
    try:
        return max(-1.0, min(1.0, float(text)))
    except ValueError:
        pass
    positive_tokens = ("positive", "bullish", "buy", "up", "上涨", "看多", "偏多", "涨")
    negative_tokens = ("negative", "bearish", "sell", "down", "下跌", "看空", "偏空", "跌")
    neutral_tokens = ("neutral", "hold", "flat", "mixed", "中性", "震荡", "观望")
    if "cautious_positive" in text or "slightly_positive" in text:
        return 0.35
    if "cautious_negative" in text or "slightly_negative" in text:
        return -0.35
    if any(token in text for token in positive_tokens):
        return 0.6
    if any(token in text for token in negative_tokens):
        return -0.6
    if any(token in text for token in neutral_tokens):
        return 0.0
    return None


def _direction_label(score: float | None) -> str:
    if score is None:
        return "not_evaluated"
    if score >= 0.2:
        return "positive"
    if score <= -0.2:
        return "negative"
    return "neutral"


def _macro_regime_label(score: float | None) -> str:
    if score is None:
        return "not_evaluated"
    if score >= 0.2:
        return "supportive"
    if score <= -0.2:
        return "restrictive"
    return "neutral"


def _member_risk_score(result: Mapping[str, Any]) -> float | None:
    if result.get("risk_score") is not None:
        return _bounded_composite_float(result.get("risk_score"))
    provenance = result.get("provenance", {})
    if isinstance(provenance, Mapping):
        if provenance.get("risk_score") is not None:
            return _bounded_composite_float(provenance.get("risk_score"))
        domain_metrics = provenance.get("domain_metrics")
        if isinstance(domain_metrics, Mapping) and domain_metrics.get("risk_score") is not None:
            return _bounded_composite_float(domain_metrics.get("risk_score"))
    return None


def _member_summary_text(agent_id: str, result: Mapping[str, Any]) -> str:
    provenance = result.get("provenance", {})
    if isinstance(provenance, Mapping):
        research_points = provenance.get("research_points")
        if isinstance(research_points, list):
            for point in research_points:
                if not isinstance(point, Mapping):
                    continue
                text = _bounded_composite_text(
                    point.get("claim") or point.get("support"),
                    limit=160,
                )
                if text:
                    return text
    evidence = result.get("evidence")
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, Mapping):
                continue
            text = _bounded_composite_text(item.get("fact"), limit=160)
            if text:
                return text
    stance = _bounded_composite_text(result.get("stance") or "not_evaluated", limit=80)
    confidence = _bounded_composite_float(result.get("confidence"))
    return f"{AGENT_TITLE_LABELS.get(agent_id, agent_id)} 输出 {stance} 信号，置信度 {confidence:.2f}。"


def _member_evidence_refs(agent_id: str, result: Mapping[str, Any]) -> list[str]:
    if not _l2_result_real_contributor(agent_id, result):
        return []
    refs: list[str] = []
    evidence = result.get("evidence")
    if isinstance(evidence, list):
        for item in evidence[:3]:
            if not isinstance(item, Mapping):
                continue
            fact = _bounded_composite_text(item.get("fact"), limit=180)
            if fact:
                refs.append(f"{AGENT_TITLE_LABELS.get(agent_id, agent_id)}：{fact}")
    if not refs:
        summary = _member_summary_text(agent_id, result)
        if summary:
            refs.append(f"{AGENT_TITLE_LABELS.get(agent_id, agent_id)}：{summary}")
    return refs[:3]


def _member_weight_summary(
    expected_agent_ids: tuple[str, ...],
    conclusions: Mapping[str, dict[str, Any]],
    weights: Mapping[str, float],
) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []
    for agent_id in expected_agent_ids:
        raw_result = conclusions.get(agent_id)
        status = _member_status(raw_result)
        is_real_contributor = isinstance(raw_result, Mapping) and _l2_result_real_contributor(
            agent_id,
            raw_result,
        )
        member: dict[str, Any] = {
            "agent_id": agent_id,
            "status": status,
            "weight": round(_bounded_composite_float(weights.get(agent_id)) if is_real_contributor else 0.0, 4),
        }
        if isinstance(raw_result, Mapping):
            member["stance"] = _bounded_composite_text(
                raw_result.get("stance") or "not_evaluated",
                limit=80,
            )
            member["confidence"] = round(
                _bounded_composite_float(raw_result.get("confidence")),
                4,
            )
            summary = _member_summary_text(agent_id, raw_result)
            if summary:
                member["summary"] = summary
            risk_score = _member_risk_score(raw_result)
            if risk_score is not None:
                member["risk_score"] = round(risk_score, 4)
        else:
            member["stance"] = "not_evaluated"
            member["confidence"] = 0.0
            member["summary"] = "本轮没有收到该成员的可用输出。"
        members.append(member)
    return members


def _member_boundary_summary(
    expected_agent_ids: tuple[str, ...],
    conclusions: Mapping[str, dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Collect member-level report caveats that should survive L3 compression."""
    rows: list[dict[str, Any]] = []
    for agent_id in expected_agent_ids:
        raw_result = conclusions.get(agent_id)
        if not isinstance(raw_result, Mapping):
            continue
        provenance = raw_result.get("provenance")
        if not isinstance(provenance, Mapping):
            continue
        caveats: list[str] = []
        data_quality = provenance.get("data_quality")
        if isinstance(data_quality, Mapping):
            warnings = data_quality.get("warnings")
            if isinstance(warnings, list):
                for warning in warnings:
                    text = _bounded_composite_text(warning, limit=260)
                    if text and text not in caveats:
                        caveats.append(text)
                    if len(caveats) >= 3:
                        break
        domain_metrics = provenance.get("domain_metrics")
        if isinstance(domain_metrics, Mapping):
            boundary = domain_metrics.get("model_vintage_boundary")
            if isinstance(boundary, Mapping) and boundary.get("model_vintage_caveat") is True:
                interpretation = _bounded_composite_text(
                    boundary.get("interpretation"),
                    limit=260,
                )
                train_year = boundary.get("production_model_trained_through_feature_year")
                market_year = boundary.get("as_of_market_feature_year")
                if interpretation:
                    text = f"模型版本边界：{interpretation}"
                else:
                    text = (
                        "模型版本边界：生产模型训练上界="
                        f"{train_year}，as_of 市场可见特征年={market_year}。"
                    )
                text = _bounded_composite_text(text, limit=300)
                if text and text not in caveats:
                    caveats.append(text)
        if caveats:
            rows.append(
                {
                    "agent_id": agent_id,
                    "status": _member_status(raw_result),
                    "caveats": caveats[:4],
                }
            )
        if len(rows) >= limit:
            break
    return rows


def _composite_candidates(
    expected_agent_ids: tuple[str, ...],
    conclusions: Mapping[str, dict[str, Any]],
) -> list[tuple[str, Mapping[str, Any], float]]:
    candidates: list[tuple[str, Mapping[str, Any], float]] = []
    for agent_id in expected_agent_ids:
        result = conclusions.get(agent_id)
        if not isinstance(result, Mapping):
            continue
        if _member_status(result) not in {"complete", "partial"}:
            continue
        confidence = _bounded_composite_float(result.get("confidence"))
        if confidence <= 0.0:
            continue
        if not _l2_result_real_contributor(agent_id, result):
            continue
        candidates.append((agent_id, result, confidence))
    return candidates


_NON_CONTRIBUTOR_L2_MARKERS = (
    "placeholder",
    "standin",
    "stand-in",
    "stand_in",
    "llm_standin",
    "deterministic_fallback",
    "compute_no_llm_deterministic_fallback",
    "fallback",
    "not_evaluated",
    "no_evidence",
    "zero_evidence",
    "no_matching_records",
    "local_snapshot_no_matching_records",
    "data_unavailable",
    "not_available",
    "unavailable",
    "占位",
    "兜底",
    "替身",
    "不可用",
)


def _l2_result_looks_non_contributor(result: Mapping[str, Any]) -> bool:
    parts: list[str] = []
    for key in ("status", "stance", "summary", "label", "quality_label"):
        text = _bounded_composite_text(result.get(key), limit=260)
        if text:
            parts.append(text)
    provenance = result.get("provenance")
    if isinstance(provenance, Mapping):
        for key in ("reason", "external_status", "stance_source", "confidence_source"):
            text = _bounded_composite_text(provenance.get(key), limit=260)
            if text:
                parts.append(text)
        for nested_key in ("raw_output_keys", "quality_keys"):
            value = provenance.get(nested_key)
            if isinstance(value, list):
                parts.extend(_bounded_composite_text(item, limit=120) for item in value[:12])
        for nested_key in ("domain_metrics", "data_quality"):
            value = provenance.get(nested_key)
            if isinstance(value, Mapping):
                parts.extend(_bounded_composite_text(item, limit=120) for item in value.keys())
                parts.extend(_bounded_composite_text(item, limit=120) for item in value.values())
    evidence = result.get("evidence")
    if isinstance(evidence, list):
        for item in evidence[:3]:
            if not isinstance(item, Mapping):
                continue
            for key in ("source", "id", "fact"):
                text = _bounded_composite_text(item.get(key), limit=260)
                if text:
                    parts.append(text)
    marker_text = " ".join(parts).lower()
    return any(token in marker_text for token in _NON_CONTRIBUTOR_L2_MARKERS)


def _l2_result_has_real_material(result: Mapping[str, Any]) -> bool:
    stance = _bounded_composite_text(result.get("stance"), limit=80).lower()
    if stance and stance not in {"not_evaluated", "not evaluated", "unknown", "n/a"}:
        return True
    if result.get("risk_score") not in (None, ""):
        return True
    evidence = result.get("evidence")
    if isinstance(evidence, list) and evidence:
        return True
    provenance = result.get("provenance")
    if isinstance(provenance, Mapping):
        for key in ("research_points", "drivers", "domain_metrics"):
            value = provenance.get(key)
            if isinstance(value, list) and value:
                return True
            if isinstance(value, Mapping) and value:
                return True
    return False


def _l2_result_real_contributor(agent_id: str, result: Mapping[str, Any]) -> bool:
    status = _member_status(result)
    if status not in {"complete", "partial"}:
        return False
    confidence = _bounded_composite_float(result.get("confidence"))
    if confidence <= 0.0:
        return False
    if _l2_result_looks_non_contributor(result):
        return False
    return _l2_result_has_real_material(result)


def _direction_candidates(
    expected_agent_ids: tuple[str, ...],
    conclusions: Mapping[str, dict[str, Any]],
) -> list[tuple[str, Mapping[str, Any], float, float]]:
    candidates: list[tuple[str, Mapping[str, Any], float, float]] = []
    for agent_id, result, confidence in _composite_candidates(expected_agent_ids, conclusions):
        score = _bounded_direction_score(result.get("stance"))
        if score is None:
            continue
        candidates.append((agent_id, result, confidence, score))
    return candidates


def _normalized_weights(
    candidates: list[tuple[str, Mapping[str, Any], float]]
    | list[tuple[str, Mapping[str, Any], float, float]]
) -> dict[str, float]:
    total = sum(max(float(item[2]), 0.0) for item in candidates)
    if total <= 0.0:
        return {}
    return {item[0]: max(float(item[2]), 0.0) / total for item in candidates}


def _coverage(expected_agent_ids: tuple[str, ...], available_count: int) -> float:
    if not expected_agent_ids:
        return 0.0
    return round(available_count / len(expected_agent_ids), 4)


def _weighted_confidence(
    candidates: list[tuple[str, Mapping[str, Any], float]]
    | list[tuple[str, Mapping[str, Any], float, float]],
    *,
    expected_count: int,
) -> float:
    if not candidates or expected_count <= 0:
        return 0.0
    average_confidence = sum(float(item[2]) for item in candidates) / len(candidates)
    return round(max(0.0, min(1.0, average_confidence * len(candidates) / expected_count)), 4)


def _weighted_direction_score(
    candidates: list[tuple[str, Mapping[str, Any], float, float]]
) -> float | None:
    weights = _normalized_weights(candidates)
    if not weights:
        return None
    score = sum(float(score) * weights[agent_id] for agent_id, _result, _confidence, score in candidates)
    return round(max(-1.0, min(1.0, score)), 4)


def _base_composite_provenance(
    *,
    dimension: DimensionName,
    status: ConclusionStatus,
    expected_agent_ids: tuple[str, ...],
    conclusions: Mapping[str, dict[str, Any]],
    candidates: list[tuple[str, Mapping[str, Any], float]]
    | list[tuple[str, Mapping[str, Any], float, float]],
    weights: Mapping[str, float],
    domain_metrics: Mapping[str, Any],
    drivers: list[dict[str, Any]],
    research_points: list[dict[str, Any]],
    data_quality: Mapping[str, Any],
) -> dict[str, Any]:
    missing_components = [
        AGENT_TITLE_LABELS.get(agent_id, agent_id)
        for agent_id in expected_agent_ids
        if agent_id not in {item[0] for item in candidates}
    ]
    return {
        "source": "fixed_dag_deterministic_l3_projection",
        "provider_invoked": False,
        "external_invoked": False,
        "dimension": dimension,
        "member_weight_summary": _member_weight_summary(expected_agent_ids, conclusions, weights),
        "domain_metrics": {
            "expected_member_count": len(expected_agent_ids),
            "available_member_count": len(candidates),
            "coverage": _coverage(expected_agent_ids, len(candidates)),
            "missing_components": missing_components,
            **dict(domain_metrics),
        },
        "drivers": drivers,
        "research_points": research_points,
        "data_quality": {
            "composite_status": status,
            "member_count": len(expected_agent_ids),
            "upstream_outputs_consumed": len(candidates),
            "coverage": _coverage(expected_agent_ids, len(candidates)),
            "missing_components": missing_components,
            "llm_subjective": False,
            **dict(data_quality),
        },
    }
