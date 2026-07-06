# ruff: noqa: D101, D103
"""Dimension composite builders and decision result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from react_agent.fixed_dag.constants import (
    AGENT_DIMENSIONS,
    DECISION_RESULT_SCHEMA_VERSION,
    DEFAULT_AS_OF,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_COMPOSITE_SCHEMA_VERSION,
    DIMENSION_GROUPS,
    L2_CONCLUSION_AGENT_IDS,
    L3_COMPOSITE_AGENT_IDS,
    RESET_RUNTIME_AGENT_IDS,
    RESET_SOURCE,
    RISK_AGENT_IDS,
)
from react_agent.fixed_dag.labels import AGENT_TITLE_LABELS, DIMENSION_TITLE_LABELS
from react_agent.fixed_dag.safety import _safe_public_float
from react_agent.fixed_dag.types import (
    ConclusionStatus,
    DecisionResult,
    DimensionCompositeResult,
    DimensionName,
)
from react_agent.fixed_dag.contracts.helpers import (
    _as_of,
    _base_composite_provenance,
    _bounded_composite_float,
    _bounded_composite_text,
    _bounded_direction_score,
    _composite_candidates,
    _coverage,
    _data_as_of_for,
    _data_not_after,
    _direction_candidates,
    _direction_label,
    _l2_result_has_real_material,
    _l2_result_looks_non_contributor,
    _l2_result_real_contributor,
    _macro_regime_label,
    _member_boundary_summary,
    _member_evidence_refs,
    _member_risk_score,
    _member_status,
    _member_summary_text,
    _member_weight_summary,
    _normalized_weights,
    _status_for_expected,
    _weighted_confidence,
    _weighted_direction_score,
)

def _build_dimension_composite(
    dimension: DimensionName,
    expected_agent_ids: tuple[str, ...],
    conclusions: Mapping[str, dict[str, Any]],
    *,
    as_of: str,
) -> DimensionCompositeResult:
    status = _status_for_expected(expected_agent_ids, conclusions)
    available_candidates = _composite_candidates(expected_agent_ids, conclusions)
    direction_candidates = _direction_candidates(expected_agent_ids, conclusions)
    if not available_candidates:
        status = "pending_implementation"
    direction_weights = _normalized_weights(direction_candidates)
    all_weights = _normalized_weights(available_candidates)
    weighted_score = _weighted_direction_score(direction_candidates)
    evidence_refs: list[str] = []
    for agent_id, result, *_rest in available_candidates:
        evidence_refs.extend(_member_evidence_refs(agent_id, result))
    evidence_refs = evidence_refs[:8]

    missing_names = [
        AGENT_TITLE_LABELS.get(agent_id, agent_id)
        for agent_id in expected_agent_ids
        if agent_id not in {item[0] for item in available_candidates}
    ]
    coverage = _coverage(expected_agent_ids, len(available_candidates))
    expected_count = len(expected_agent_ids)

    result: DimensionCompositeResult = {
        "schema": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "schema_version": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "agent_id": DIMENSION_COMPOSITE_AGENT_IDS[dimension],
        "dimension": dimension,
        "stance": _direction_label(weighted_score) if dimension in {"value", "market"} else "not_evaluated",
        "confidence": _weighted_confidence(
            direction_candidates if dimension in {"value", "market", "macro"} else available_candidates,
            expected_count=expected_count,
        ),
        "status": status,
        "contributing_agents": [
            agent_id for agent_id, *_rest in direction_candidates
        ]
        if dimension in {"value", "market", "macro"}
        else [agent_id for agent_id, *_rest in available_candidates],
        "evidence_refs": evidence_refs,
        "as_of": as_of,
        "data_as_of": _data_as_of_for(as_of),
    }
    if dimension in {"value", "market"}:
        result["vote_type"] = "weighted_member_vote" if direction_candidates else "direction_vote_placeholder"
        direction_label = _direction_label(weighted_score)
        result["provenance"] = _base_composite_provenance(
            dimension=dimension,
            status=status,
            expected_agent_ids=expected_agent_ids,
            conclusions=conclusions,
            candidates=direction_candidates,
            weights=direction_weights,
            domain_metrics={
                "weighted_stance_score": weighted_score,
                "direction": direction_label,
                "vote_type": result["vote_type"],
            },
            drivers=[
                {
                    "name": "member_weight_summary",
                    "value": _member_weight_summary(expected_agent_ids, conclusions, direction_weights),
                },
                {
                    "name": "coverage",
                    "value": {
                        "available": len(available_candidates),
                        "directional": len(direction_candidates),
                        "expected": expected_count,
                        "coverage": coverage,
                    },
                },
                {"name": "missing_components", "value": missing_names},
            ],
            research_points=[
                {
                    "claim": f"{DIMENSION_TITLE_LABELS[dimension]}当前为 {status}：{len(available_candidates)}/{expected_count} 个成员有可用输出。",
                    "support": (
                        f"方向成员 {len(direction_candidates)} 个，综合方向 {direction_label}，"
                        f"加权分 {weighted_score if weighted_score is not None else 'n/a'}。"
                    ),
                    "interpretation": "L3 只对 complete/partial 且具备可读方向的成员赋权，pending/placeholder 成员权重为 0。",
                    "decision_implication": "该综合信号可作为本维度局部线索，但在成员覆盖不足时不能代表完整维度结论。",
                    "caveat": "未调用 LLM 或外部服务；没有把缺失成员包装成真实 evidence。",
                }
            ],
            data_quality={
                "scoring_method": "confidence_weighted_direction_from_available_l2",
                "missing_components": missing_names,
                "directional_member_count": len(direction_candidates),
            },
        )
    if dimension == "risk":
        risk_candidates: list[tuple[str, Mapping[str, Any], float]] = []
        weighted_risk_score = 0.0
        for agent_id, candidate_result, confidence in available_candidates:
            if _member_risk_score(candidate_result) is not None:
                risk_candidates.append((agent_id, candidate_result, confidence))
        member_boundaries = _member_boundary_summary(expected_agent_ids, conclusions)
        risk_weights = _normalized_weights(risk_candidates)
        if risk_weights:
            weighted_risk_score = round(
                sum(
                    (_member_risk_score(candidate_result) or 0.0) * risk_weights[agent_id]
                    for agent_id, candidate_result, _confidence in risk_candidates
                ),
                4,
            )
            gate = "pass"
            if weighted_risk_score >= 0.7:
                gate = "veto"
            elif weighted_risk_score >= 0.35:
                gate = "manual_review"
        elif available_candidates:
            gate = "manual_review"
        else:
            gate = "not_evaluated"
        penalty = 0.0 if gate in {"pass", "not_evaluated"} else weighted_risk_score
        risk_drivers = [
            {
                "name": "member_weight_summary",
                "value": _member_weight_summary(
                    expected_agent_ids,
                    conclusions,
                    risk_weights or all_weights,
                ),
            },
            {
                "name": "risk_gate_rule",
                "value": "risk_score < 0.35 pass; 0.35-0.70 manual_review; >= 0.70 veto.",
            },
            {"name": "missing_components", "value": missing_names},
        ]
        if member_boundaries:
            risk_drivers.append({"name": "member_boundary_summary", "value": member_boundaries})
        risk_research_points = [
            {
                "claim": f"风险综合当前为 {status}，风险门为 {gate}。",
                "support": (
                    f"{len(risk_candidates)}/{expected_count} 个风险成员提供 risk_score，"
                    f"加权风险分 {weighted_risk_score:.4f}。"
                ),
                "interpretation": "风险综合只读取风险维成员；企业舆情雷达不会进入 risk_composite。",
                "decision_implication": "gate 为 pass 时不触发风险否决；manual_review/veto 时应限制后续决策强度。",
                "caveat": "成员缺失或未给出 risk_score 时会降低覆盖率，不作为低风险证明。",
            }
        ]
        if member_boundaries:
            first_boundary = member_boundaries[0]
            first_caveat = ""
            caveats = first_boundary.get("caveats")
            if isinstance(caveats, list) and caveats:
                first_caveat = _bounded_composite_text(caveats[0], limit=240)
            risk_research_points.append(
                {
                    "claim": "风险门通过不等于成员边界消失。",
                    "support": first_caveat or f"{len(member_boundaries)} 个风险成员带有数据或模型边界说明。",
                    "interpretation": "L3 风险分只聚合成员 risk_score；成员的数据时点、模型版本和缺失文本仍应进入报告限制。",
                    "decision_implication": "最终报告可以维持 gate=pass，但必须同步呈现这些 caveat，避免把低风险写成无条件结论。",
                    "caveat": "边界说明不改写成员原始分数，也不把 caveat 当作新的风险事件。",
                }
            )
        result.update(
            {
                "stance": "risk_gate" if available_candidates else "not_evaluated",
                "confidence": _weighted_confidence(risk_candidates or available_candidates, expected_count=expected_count),
                "gate": gate,
                "veto": gate == "veto",
                "penalty": penalty,
                "risk_score": weighted_risk_score,
                "contributing_agents": [
                    agent_id
                    for agent_id, *_rest in (risk_candidates or available_candidates)
                ],
                "provenance": _base_composite_provenance(
                    dimension=dimension,
                    status=status,
                    expected_agent_ids=expected_agent_ids,
                    conclusions=conclusions,
                    candidates=risk_candidates or available_candidates,
                    weights=risk_weights or all_weights,
                    domain_metrics={
                        "gate": gate,
                        "risk_score": weighted_risk_score,
                        "penalty": penalty,
                        "risk_member_count": len(risk_candidates),
                    },
                    drivers=risk_drivers,
                    research_points=risk_research_points,
                    data_quality={
                        "scoring_method": "confidence_weighted_risk_score_from_available_l2",
                        "missing_components": missing_names,
                        "risk_score_member_count": len(risk_candidates),
                        **({"member_boundary_summary": member_boundaries} if member_boundaries else {}),
                    },
                ),
            }
        )
    if dimension == "macro":
        regime = _macro_regime_label(weighted_score)
        result.update(
            {
                "stance": regime,
                "confidence": _weighted_confidence(direction_candidates, expected_count=expected_count),
                "regime": regime,
                "dimension_weights": {
                    "value": 0.5,
                    "market": 0.5,
                },
                "risk_sensitivity": "normal" if direction_candidates else "not_evaluated",
                "provenance": _base_composite_provenance(
                    dimension=dimension,
                    status=status,
                    expected_agent_ids=expected_agent_ids,
                    conclusions=conclusions,
                    candidates=direction_candidates,
                    weights=direction_weights,
                    domain_metrics={
                        "regime": regime,
                        "weighted_stance_score": weighted_score,
                        "dimension_weights": {"value": 0.5, "market": 0.5},
                    },
                    drivers=[
                        {
                            "name": "member_weight_summary",
                            "value": _member_weight_summary(expected_agent_ids, conclusions, direction_weights),
                        },
                        {
                            "name": "dimension_weight_policy",
                            "value": "保持 value/market 默认 0.5/0.5，直到真实宏观成员覆盖足以支持调权。",
                        },
                        {"name": "missing_components", "value": missing_names},
                    ],
                    research_points=[
                        {
                            "claim": f"宏观综合当前为 {status}，regime={regime}。",
                            "support": (
                                f"{len(direction_candidates)}/{expected_count} 个宏观成员提供可读方向；"
                                "value/market 权重保持默认 0.5/0.5。"
                            ),
                            "interpretation": "宏观调节器不会在宏观成员缺失时主动改变价值/市场权重。",
                            "decision_implication": "当前宏观层只能提示覆盖缺口，不能作为独立调权依据。",
                            "caveat": "未调用 LLM 或外部宏观服务；缺失宏观成员不被包装成真实 macro evidence。",
                        }
                    ],
                    data_quality={
                        "scoring_method": "default_equal_weights_until_macro_coverage",
                        "missing_components": missing_names,
                        "directional_member_count": len(direction_candidates),
                    },
                ),
            }
        )
    return result


def build_value_composite(
    conclusions: Mapping[str, dict[str, Any]],
    *,
    as_of: str,
) -> DimensionCompositeResult:
    return _build_dimension_composite("value", VALUE_AGENT_IDS, conclusions, as_of=as_of)


def build_market_composite(
    conclusions: Mapping[str, dict[str, Any]],
    *,
    as_of: str,
) -> DimensionCompositeResult:
    return _build_dimension_composite("market", MARKET_AGENT_IDS, conclusions, as_of=as_of)


def build_risk_composite(
    conclusions: Mapping[str, dict[str, Any]],
    *,
    as_of: str,
) -> DimensionCompositeResult:
    risk_only = {
        agent_id: conclusions[agent_id]
        for agent_id in RISK_AGENT_IDS
        if agent_id in conclusions
    }
    return _build_dimension_composite("risk", RISK_AGENT_IDS, risk_only, as_of=as_of)


def build_macro_composite(
    conclusions: Mapping[str, dict[str, Any]],
    *,
    as_of: str,
) -> DimensionCompositeResult:
    return _build_dimension_composite("macro", MACRO_AGENT_IDS, conclusions, as_of=as_of)


def validate_dimension_composite_result(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != DIMENSION_COMPOSITE_SCHEMA_VERSION:
        return False, "invalid_schema"
    dimension = str(obj.get("dimension") or "")
    if dimension not in DIMENSION_GROUPS:
        return False, "invalid_dimension"
    if obj.get("agent_id") != DIMENSION_COMPOSITE_AGENT_IDS[dimension]:
        return False, "agent_dimension_mismatch"
    contributing_agents = list(obj.get("contributing_agents", []))
    if not contributing_agents:
        status = str(obj.get("status") or "")
        if status not in {"pending_implementation", "error"}:
            return False, "contributing_agents_missing"
    if not set(contributing_agents) <= set(DIMENSION_GROUPS[dimension]):
        return False, "contributing_agents_mismatch"
    if dimension == "risk" and "sentiment_company_radar" in contributing_agents:
        return False, "risk_reads_sentiment"
    try:
        confidence = float(obj.get("confidence"))
    except (TypeError, ValueError):
        return False, "invalid_confidence"
    if not 0.0 <= confidence <= 1.0:
        return False, "confidence_out_of_range"
    if not _data_not_after(obj.get("data_as_of"), obj.get("as_of")):
        return False, "data_as_of_after_as_of"
    if dimension == "risk":
        for field in ("gate", "veto", "penalty", "risk_score"):
            if field not in obj:
                return False, f"missing_{field}"
    if dimension == "macro":
        for field in ("regime", "dimension_weights", "risk_sensitivity"):
            if field not in obj:
                return False, f"missing_{field}"
        dimension_weights = obj.get("dimension_weights")
        if not isinstance(dimension_weights, Mapping):
            return False, "invalid_dimension_weights"
        if set(dimension_weights) != {"value", "market"}:
            return False, "dimension_weights_keys_mismatch"
        for value in dimension_weights.values():
            try:
                weight = float(value)
            except (TypeError, ValueError):
                return False, "invalid_dimension_weight"
            if not 0.0 <= weight <= 1.0:
                return False, "dimension_weight_out_of_range"
    return True, "ok"


def build_dimension_results(
    l2_conclusions: Mapping[str, dict[str, Any]],
    *,
    as_of: str | None = None,
) -> dict[str, DimensionCompositeResult]:
    normalized_as_of = _as_of(as_of)
    selected_by_dimension = {
        dimension: tuple(agent_id for agent_id in agent_ids if agent_id in l2_conclusions)
        for dimension, agent_ids in DIMENSION_GROUPS.items()
    }
    if not l2_conclusions:
        selected_by_dimension = {
            dimension: tuple(agent_ids)
            for dimension, agent_ids in DIMENSION_GROUPS.items()
        }
    return {
        cast(str, dimension): _build_dimension_composite(
            cast(DimensionName, dimension),
            cast(tuple[str, ...], agent_ids),
            l2_conclusions,
            as_of=normalized_as_of,
        )
        for dimension, agent_ids in selected_by_dimension.items()
        if agent_ids
    }


def build_decision_result(
    dimension_results: Mapping[str, dict[str, Any]] | None = None,
    *,
    as_of: str | None = None,
) -> DecisionResult:
    dimension_results = dimension_results or {}
    normalized_as_of = _as_of(as_of)
    risk = dimension_results.get("risk", {})
    risk_veto = bool(risk.get("veto")) if isinstance(risk, Mapping) else False
    decision = "conservative_pending" if risk_veto else "pending_implementation"
    score = -0.25 if risk_veto else 0.0
    return {
        "schema": DECISION_RESULT_SCHEMA_VERSION,
        "schema_version": DECISION_RESULT_SCHEMA_VERSION,
        "decision": decision,
        "score": score,
        "target_price_range": {"low": None, "mid": None, "high": None},
        "dimension_views": {
            dimension: {
                "stance": result.get("stance", "not_evaluated"),
                "confidence": result.get("confidence", 0.0),
                "status": result.get("status", "pending_implementation"),
            }
            for dimension, result in dimension_results.items()
            if isinstance(result, Mapping)
        },
        "reasoning_trace": [
            {
                "stage": "dimension_induction",
                "summary": "维度综合结果仍为确定性占位。",
            },
            {
                "stage": "macro_risk_adjustment",
                "summary": "宏观与风险占位接口可在后续影响业务决策。",
            },
            {
                "stage": "conflict_resolution",
                "summary": "R3 阶段尚未实现实时业务冲突消解。",
            },
        ],
        "confidence": 0.0,
        "status": "pending_implementation",
        "as_of": normalized_as_of,
    }


def validate_decision_result(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != DECISION_RESULT_SCHEMA_VERSION:
        return False, "invalid_schema"
    if obj.get("schema_version", DECISION_RESULT_SCHEMA_VERSION) != DECISION_RESULT_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    try:
        score = float(obj.get("score"))
    except (TypeError, ValueError):
        return False, "invalid_score"
    if not -1.0 <= score <= 1.0:
        return False, "score_out_of_range"
    target_range = obj.get("target_price_range")
    if not isinstance(target_range, Mapping):
        return False, "target_price_range_missing"
    if set(target_range) != {"low", "mid", "high"}:
        return False, "target_price_range_keys_mismatch"
    if not isinstance(obj.get("dimension_views"), Mapping):
        return False, "dimension_views_missing"
    try:
        confidence = float(obj.get("confidence"))
    except (TypeError, ValueError):
        return False, "invalid_confidence"
    if not 0.0 <= confidence <= 1.0:
        return False, "confidence_out_of_range"
    trace = obj.get("reasoning_trace")
    if not isinstance(trace, list) or len(trace) < 3:
        return False, "reasoning_trace_too_short"
    stages = {
        str(item.get("stage"))
        for item in trace
        if isinstance(item, Mapping) and item.get("stage")
    }
    required = {"dimension_induction", "macro_risk_adjustment", "conflict_resolution"}
    if not required <= stages:
        return False, "reasoning_trace_stage_missing"
    if str(obj.get("decision")) == "strong_buy" and score > 0.5:
        return False, "unsupported_strong_positive_decision"
    return True, "ok"
