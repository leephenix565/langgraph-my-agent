# ruff: noqa: D101, D103
"""Deterministic fixed-DAG reset contracts and function seams.

Phase R3 keeps the active runtime provider-free and external-free while making
the reset skeleton contracts explicit, validated, execution-aware, and reusable
by graph nodes and public workflow mapping.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, cast

from react_agent.fixed_dag.constants import (
    AGENT_DIMENSIONS,
    AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION,
    AGENT_TASK_SCHEMA_VERSION,
    CONCLUSION_OBJECT_SCHEMA_VERSION,
    DATA_BUNDLE_SCHEMA_VERSION,
    DECISION_RESULT_SCHEMA_VERSION,
    DEFAULT_AS_OF,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_COMPOSITE_SCHEMA_VERSION,
    DIMENSION_GROUPS,
    ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
    EXECUTED_STEP_STATUSES,
    FIXED_DAG_SCHEMA_VERSION,
    FIXED_DAG_STAGE_ORDER,
    INVESTMENT_JUDGMENT_TASK_TYPES,
    L1_AGENT_IDS,
    L2_CONCLUSION_AGENT_IDS,
    L3_COMPOSITE_AGENT_IDS,
    L4_AGENT_IDS,
    MACRO_AGENT_IDS,
    MARKET_AGENT_IDS,
    REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
    REPORT_RESULT_SCHEMA_VERSION,
    RESET_RUNTIME_AGENT_IDS,
    RESET_SOURCE,
    RISK_AGENT_IDS,
    ROUTE_INTENT_SCHEMA_VERSION,
    ROUTE_TASK_TYPES,
    SELECTED_FIXED_DAG_SCHEMA_VERSION,
    SELECTED_PLAN_FALLBACK_TARGETS,
    SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES,
    VALUE_AGENT_IDS,
    WORKFLOW_SNAPSHOT_SCHEMA_VERSION,
)
from react_agent.fixed_dag.labels import (
    AGENT_TITLE_LABELS,
    DIMENSION_TITLE_LABELS,
    STAGE_TITLE_LABELS,
)
from react_agent.fixed_dag.safety import (
    LEGACY_CONTRACT_KEYS,  # noqa: F401 - re-exported by the compatibility facade.
    LEGACY_DISPATCH_VALUES,  # noqa: F401 - re-exported by the compatibility facade.
    REPORT_BUNDLE_UNSAFE_KEYS,
    SELECTED_PLAN_FORBIDDEN_KEYS,  # noqa: F401 - re-exported by the compatibility facade.
    SELECTED_PLAN_PUBLIC_UNSAFE_TEXT_TOKENS,  # noqa: F401 - re-exported by the compatibility facade.
    _contains_legacy_dispatch_value,
    _contains_legacy_key,
    _contains_public_unsafe_text,
    _contains_selected_plan_forbidden_key,
    _contains_unsafe_report_key,
    _looks_like_legacy_agent_id,
    _safe_public_detail_list,
    _safe_public_detail_mapping,
    _safe_public_detail_value,  # noqa: F401 - re-exported by the compatibility facade.
    _safe_public_float,
    _safe_public_mapping,
    _safe_public_text,
    _safe_public_text_list,
)
from react_agent.fixed_dag.types import (
    AgentTask,
    ConclusionObject,
    ConclusionStatus,
    DataBundle,
    DecisionResult,
    DimensionCompositeResult,
    DimensionName,
    EntityRelationBundle,
    FixedDagDimension,  # noqa: F401 - re-exported by the compatibility facade.
    FixedDagPlan,
    FixedDagStage,
    FixedDagStep,
    FixedDagStepStatus,  # noqa: F401 - re-exported by the compatibility facade.
    ReportInputBundle,
    ReportResult,
    RouteIntent,
    RouteTaskType,
    SelectedFixedDagPlan,
)


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
        member: dict[str, Any] = {
            "agent_id": agent_id,
            "status": status,
            "weight": round(_bounded_composite_float(weights.get(agent_id)), 4),
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
        candidates.append((agent_id, result, confidence))
    return candidates


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


def _step(
    *,
    step_id: str,
    stage: FixedDagStage,
    title: str,
    description: str,
    status: str = "pending_implementation",
    agent_id: str | None = None,
    target_ids: tuple[str, ...] = (),
    dimension: str | None = None,
    depends_on: tuple[str, ...] = (),
) -> FixedDagStep:
    step: FixedDagStep = {
        "id": step_id,
        "stage": stage,
        "title": title,
        "description": description,
        "status": status,
    }
    if agent_id:
        step["agent_id"] = agent_id
    if target_ids:
        step["target_ids"] = list(target_ids)
    if dimension:
        step["dimension"] = dimension
    if depends_on:
        step["depends_on"] = list(depends_on)
    else:
        step["depends_on"] = []
    return step


def _build_steps() -> list[FixedDagStep]:
    steps = [
        _step(
            step_id="route_planner",
            stage="planning",
            title=AGENT_TITLE_LABELS["route_planner"],
            description="理解问题并组织本轮研判流程。",
            status="complete",
            agent_id="route_planner",
            dimension="l1",
        ),
        _step(
            step_id="financial_data_service",
            stage="evidence",
            title=AGENT_TITLE_LABELS["financial_data_service"],
            description="整理分析所需的基础数据与上下文。",
            agent_id="financial_data_service",
            dimension="l1",
            depends_on=("route_planner",),
        ),
        _step(
            step_id="entity_relation_extractor",
            stage="evidence",
            title=AGENT_TITLE_LABELS["entity_relation_extractor"],
            description="识别公司、行业、事件等关键对象及其关系。",
            agent_id="entity_relation_extractor",
            dimension="l1",
            depends_on=("route_planner",),
        ),
    ]
    for agent_id in L2_CONCLUSION_AGENT_IDS:
        steps.append(
            _step(
                step_id=f"l2:{agent_id}",
                stage="l2_analysis",
                title=AGENT_TITLE_LABELS.get(agent_id, agent_id),
                description="围绕本步骤主题整理研判线索。",
                agent_id=agent_id,
                dimension=AGENT_DIMENSIONS[agent_id],
                depends_on=("financial_data_service", "entity_relation_extractor"),
            )
        )
    for dimension, agent_ids in DIMENSION_GROUPS.items():
        steps.append(
            _step(
                step_id=f"dimension:{dimension}",
                stage="dimension_composite",
                title=DIMENSION_TITLE_LABELS.get(dimension, f"{dimension} 综合"),
                description="汇总单一维度的分析结论，形成维度判断。",
                agent_id=DIMENSION_COMPOSITE_AGENT_IDS[dimension],
                target_ids=agent_ids,
                dimension=dimension,
                depends_on=tuple(f"l2:{agent_id}" for agent_id in agent_ids),
            )
        )
    steps.extend(
        [
            _step(
                step_id="decision_synthesizer",
                stage="decision",
                title=AGENT_TITLE_LABELS["decision_synthesizer"],
                description="综合各维度判断，形成决策线索。",
                agent_id="decision_synthesizer",
                dimension="l4",
                depends_on=tuple(f"dimension:{dimension}" for dimension in DIMENSION_GROUPS),
            ),
            _step(
                step_id="report_generator",
                stage="report",
                title=AGENT_TITLE_LABELS["report_generator"],
                description="生成面向用户的最终回答。",
                agent_id="report_generator",
                dimension="l4",
                depends_on=("decision_synthesizer",),
            ),
        ]
    )
    return steps


def build_default_fixed_dag_plan(
    question: str = "",
    as_of: str | None = None,
) -> FixedDagPlan:
    normalized_as_of = _as_of(as_of)
    steps = _build_steps()
    return {
        "schema": FIXED_DAG_SCHEMA_VERSION,
        "schema_version": FIXED_DAG_SCHEMA_VERSION,
        "plan_id": "reset-fixed-dag-plan-v1",
        "user_text": str(question or ""),
        "as_of": normalized_as_of,
        "stages": [
            {
                "id": stage,
                "title": STAGE_TITLE_LABELS.get(stage, stage),
                "step_ids": [step["id"] for step in steps if step["stage"] == stage],
            }
            for stage in FIXED_DAG_STAGE_ORDER
        ],
        "steps": steps,
        "dag_steps": steps,
        "target_agent_ids": list(RESET_RUNTIME_AGENT_IDS),
        "target": list(RESET_RUNTIME_AGENT_IDS),
        "dimension_groups": {
            dimension: list(agent_ids)
            for dimension, agent_ids in DIMENSION_GROUPS.items()
        },
        "provenance": {
            "source": "deterministic_reset_skeleton",
            "provider_invoked": False,
            "external_invoked": False,
        },
    }


def build_deterministic_fixed_dag_plan(user_text: str = "") -> FixedDagPlan:
    return build_default_fixed_dag_plan(user_text)


def _unique_known_dimensions(values: list[str] | tuple[str, ...] | None) -> list[DimensionName]:
    selected: list[DimensionName] = []
    seen: set[str] = set()
    for value in values or []:
        dimension = str(value or "").strip()
        if dimension in DIMENSION_GROUPS and dimension not in seen:
            selected.append(cast(DimensionName, dimension))
            seen.add(dimension)
    return selected


def _unique_known_agents(values: list[str] | tuple[str, ...] | None) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    known = set(RESET_RUNTIME_AGENT_IDS)
    for value in values or []:
        agent_id = str(value or "").strip()
        if agent_id in known and agent_id not in seen:
            selected.append(agent_id)
            seen.add(agent_id)
    return selected


def _unique_text_values(values: list[str] | tuple[str, ...] | None) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = str(value or "").strip()
        if text and text not in seen:
            selected.append(text)
            seen.add(text)
    return selected


def _agent_dimension(agent_id: str) -> str:
    if agent_id in AGENT_DIMENSIONS:
        return AGENT_DIMENSIONS[agent_id]
    if agent_id in L1_AGENT_IDS:
        return "l1"
    if agent_id in L4_AGENT_IDS:
        return "l4"
    for dimension, composite_agent_id in DIMENSION_COMPOSITE_AGENT_IDS.items():
        if agent_id == composite_agent_id:
            return dimension
    return ""


def build_route_intent(
    *,
    task_type: RouteTaskType = "general",
    targets: list[str] | None = None,
    selected_dimensions: list[DimensionName] | None = None,
    selected_agents: list[str] | None = None,
    task_brief_by_agent: dict[str, str] | None = None,
    route_confidence: float = 0.0,
    needs_clarification: bool = False,
    clarification_question: str = "",
    fallback_reason: str = "",
    provenance: dict[str, Any] | None = None,
) -> RouteIntent:
    selected_dimension_values = _unique_text_values(cast(list[str] | None, selected_dimensions))
    selected_agents = _unique_text_values(selected_agents)
    return {
        "schema": ROUTE_INTENT_SCHEMA_VERSION,
        "schema_version": ROUTE_INTENT_SCHEMA_VERSION,
        "task_type": task_type,
        "targets": [str(item).strip() for item in targets or [] if str(item).strip()],
        "selected_dimensions": cast(list[DimensionName], selected_dimension_values),
        "selected_agents": selected_agents,
        "task_brief_by_agent": {
            str(agent_id): str(brief)
            for agent_id, brief in (task_brief_by_agent or {}).items()
            if str(agent_id) in selected_agents
        },
        "route_confidence": route_confidence,
        "needs_clarification": bool(needs_clarification),
        "clarification_question": str(clarification_question or "").strip(),
        "fallback_reason": str(fallback_reason or "").strip(),
        "provenance": {
            "source": "deterministic_route_intent",
            "provider_invoked": False,
            "external_invoked": False,
            **dict(provenance or {}),
        },
    }


def _infer_route_task_type(question: str, requested: str) -> RouteTaskType:
    if requested in ROUTE_TASK_TYPES and requested != "general":
        return cast(RouteTaskType, requested)
    lowered = str(question or "").lower()
    if any(token in lowered for token in ("compare", "versus", "vs ", "better than")):
        return "compare"
    if any(token in lowered for token in ("screen", "rank", "shortlist")):
        return "screen"
    if any(token in lowered for token in ("macro", "rate", "inflation", "commodity", "index")):
        return "macro"
    if any(token in lowered for token in ("sentiment", "public opinion", "reputation")):
        return "sentiment"
    if any(token in lowered for token in ("industry", "sector")):
        return "industry"
    if any(token in lowered for token in ("event", "announcement", "earnings")):
        return "event"
    if any(token in lowered for token in ("invest", "valuation", "stock", "company", "buy", "sell")):
        return "single"
    return "general"


def build_default_route_intent(
    question: str,
    *,
    task_type: RouteTaskType = "general",
) -> RouteIntent:
    """Build a provider-free mock planner intent for the selected-DAG seam."""
    inferred_task_type = _infer_route_task_type(question, str(task_type or "general"))
    selected_dimensions: list[DimensionName]
    selected_agents: list[str]
    if inferred_task_type in INVESTMENT_JUDGMENT_TASK_TYPES:
        selected_dimensions = ["value", "risk"]
        selected_agents = ["value_research_synthesis", "risk_identification"]
    elif inferred_task_type == "macro":
        selected_dimensions = ["macro"]
        selected_agents = ["macro_analysis"]
    elif inferred_task_type == "sentiment":
        selected_dimensions = ["market"]
        selected_agents = ["sentiment_company_radar"]
    else:
        selected_dimensions = ["value"]
        selected_agents = ["value_research_synthesis"]

    brief_by_agent = {
        "value_research_synthesis": "Summarize value-related research signals for the question.",
        "risk_identification": "Identify risk constraints that should gate the response.",
        "macro_analysis": "Summarize macro and external-environment signals for the question.",
        "sentiment_company_radar": "Summarize market sentiment signals for the question.",
    }
    intent = build_route_intent(
        task_type=inferred_task_type,
        targets=[],
        selected_dimensions=selected_dimensions,
        selected_agents=selected_agents,
        task_brief_by_agent={
            agent_id: brief_by_agent[agent_id]
            for agent_id in selected_agents
            if agent_id in brief_by_agent
        },
        route_confidence=0.55,
        fallback_reason="fallback to full DAG",
        provenance={
            "source": "deterministic_mock_route_planner",
            "planner": "r8_3_provider_free_default_route_intent",
            "provider_invoked": False,
            "external_invoked": False,
        },
    )
    valid, reason = validate_route_intent(intent)
    if valid:
        return intent
    return build_route_intent(
        task_type="general",
        selected_dimensions=[],
        selected_agents=[],
        route_confidence=0.0,
        needs_clarification=True,
        clarification_question="Please clarify the routing target before selected planning.",
        fallback_reason=f"planner_default_failed:{reason}",
        provenance={
            "source": "deterministic_mock_route_planner",
            "planner": "r8_3_provider_free_default_route_intent",
            "provider_invoked": False,
            "external_invoked": False,
        },
    )


def validate_fixed_dag_plan(plan: Mapping[str, Any]) -> tuple[bool, str]:
    if not isinstance(plan, Mapping):
        return False, "plan_not_mapping"
    if plan.get("schema") != FIXED_DAG_SCHEMA_VERSION:
        return False, "invalid_schema"
    if plan.get("schema_version", FIXED_DAG_SCHEMA_VERSION) != FIXED_DAG_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if _contains_legacy_key(plan):
        return False, "legacy_dispatch_field_present"
    if list(plan.get("target_agent_ids", [])) != list(RESET_RUNTIME_AGENT_IDS):
        return False, "target_agent_ids_mismatch"
    if list(plan.get("target", RESET_RUNTIME_AGENT_IDS)) != list(RESET_RUNTIME_AGENT_IDS):
        return False, "target_mismatch"
    if plan.get("dimension_groups") != {
        key: list(value) for key, value in DIMENSION_GROUPS.items()
    }:
        return False, "dimension_groups_mismatch"
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        return False, "steps_missing"
    if len(steps) != len(RESET_RUNTIME_AGENT_IDS):
        return False, "steps_count_mismatch"
    if plan.get("dag_steps") != steps:
        return False, "dag_steps_mismatch"
    step_agent_ids = {
        step.get("agent_id")
        for step in steps
        if isinstance(step, Mapping) and step.get("agent_id")
    }
    if not set(RESET_RUNTIME_AGENT_IDS) <= step_agent_ids:
        return False, "step_agent_ids_mismatch"
    step_ids_by_stage = {
        stage: [step["id"] for step in steps if isinstance(step, Mapping) and step.get("stage") == stage]
        for stage in FIXED_DAG_STAGE_ORDER
    }
    stage_items = plan.get("stages")
    if not isinstance(stage_items, list) or len(stage_items) != len(FIXED_DAG_STAGE_ORDER):
        return False, "stages_mismatch"
    for item in stage_items:
        if not isinstance(item, Mapping):
            return False, "invalid_stage_item"
        stage_id = item.get("id")
        if stage_id not in step_ids_by_stage:
            return False, "unknown_stage"
        if item.get("step_ids") != step_ids_by_stage[stage_id]:
            return False, "stage_step_ids_mismatch"
    return True, "ok"


def validate_route_intent(intent: Mapping[str, Any]) -> tuple[bool, str]:
    if not isinstance(intent, Mapping):
        return False, "intent_not_mapping"
    if intent.get("schema") != ROUTE_INTENT_SCHEMA_VERSION:
        return False, "invalid_schema"
    if intent.get("schema_version", ROUTE_INTENT_SCHEMA_VERSION) != ROUTE_INTENT_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if _contains_legacy_key(intent):
        return False, "legacy_dispatch_field_present"
    if _contains_legacy_dispatch_value(intent):
        return False, "legacy_dispatch_value_present"
    if intent.get("task_type") not in ROUTE_TASK_TYPES:
        return False, "invalid_task_type"
    try:
        confidence = float(intent.get("route_confidence"))
    except (TypeError, ValueError):
        return False, "invalid_route_confidence"
    if not 0.0 <= confidence <= 1.0:
        return False, "route_confidence_out_of_range"
    selected_dimensions = intent.get("selected_dimensions")
    if not isinstance(selected_dimensions, list):
        return False, "invalid_selected_dimensions"
    if len(selected_dimensions) != len(set(selected_dimensions)):
        return False, "duplicate_selected_dimensions"
    if any(dimension not in DIMENSION_GROUPS for dimension in selected_dimensions):
        return False, "unknown_selected_dimension"
    selected_agents = intent.get("selected_agents")
    if not isinstance(selected_agents, list):
        return False, "invalid_selected_agents"
    if len(selected_agents) != len(set(selected_agents)):
        return False, "duplicate_selected_agents"
    if any(_looks_like_legacy_agent_id(str(agent_id)) for agent_id in selected_agents):
        return False, "legacy_agent_id_present"
    if "value_financial_analysis" in selected_agents:
        return False, "removed_agent_present"
    if any(agent_id not in RESET_RUNTIME_AGENT_IDS for agent_id in selected_agents):
        return False, "unknown_selected_agent"
    selected_dimension_set = set(selected_dimensions)
    for agent_id in selected_agents:
        dimension = _agent_dimension(str(agent_id))
        if dimension in DIMENSION_GROUPS and dimension not in selected_dimension_set:
            return False, "agent_dimension_mismatch"
        if agent_id == "sentiment_company_radar" and dimension != "market":
            return False, "sentiment_dimension_mismatch"
    briefs = intent.get("task_brief_by_agent")
    if not isinstance(briefs, Mapping):
        return False, "invalid_task_brief_by_agent"
    if not set(briefs) <= set(selected_agents):
        return False, "task_brief_agent_not_selected"
    needs_clarification = bool(intent.get("needs_clarification"))
    clarification_question = str(intent.get("clarification_question") or "").strip()
    fallback_reason = str(intent.get("fallback_reason") or "").strip()
    if needs_clarification and not clarification_question:
        return False, "clarification_question_missing"
    if not selected_agents and not needs_clarification and not fallback_reason:
        return False, "fallback_reason_missing"
    if fallback_reason and _contains_public_unsafe_text(fallback_reason):
        return False, "fallback_reason_not_public_safe"
    task_type = str(intent.get("task_type") or "")
    if selected_agents and not needs_clarification:
        if task_type in INVESTMENT_JUDGMENT_TASK_TYPES:
            if "risk" not in selected_dimension_set:
                return False, "risk_dimension_required"
            if not any(agent_id in RISK_AGENT_IDS for agent_id in selected_agents):
                return False, "risk_agent_required"
    provenance = intent.get("provenance", {})
    if not isinstance(provenance, Mapping):
        return False, "invalid_provenance"
    if provenance.get("provider_invoked") or provenance.get("external_invoked"):
        return False, "live_invocation_claim_present"
    return True, "ok"


def _steps_for_selected_agents(selected_agents: list[str]) -> list[FixedDagStep]:
    selected = set(selected_agents)
    steps: list[FixedDagStep] = []
    for step in _build_steps():
        agent_id = step.get("agent_id")
        if agent_id and agent_id in selected:
            filtered_step = dict(step)
            filtered_step["depends_on"] = [
                dep_id for dep_id in filtered_step.get("depends_on", []) if dep_id in {item["id"] for item in steps}
            ]
            if "target_ids" in filtered_step:
                filtered_step["target_ids"] = [
                    target_id for target_id in filtered_step["target_ids"] if target_id in selected
                ]
            steps.append(cast(FixedDagStep, filtered_step))
    return steps


def _stage_items_for_steps(steps: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": stage,
            "title": STAGE_TITLE_LABELS.get(stage, stage),
            "step_ids": [
                str(step["id"])
                for step in steps
                if isinstance(step, Mapping) and step.get("stage") == stage and step.get("id")
            ],
        }
        for stage in FIXED_DAG_STAGE_ORDER
    ]


def _selected_l2_agents_by_dimension(selected_agents: list[str]) -> dict[str, list[str]]:
    selected = set(selected_agents)
    return {
        dimension: [agent_id for agent_id in agent_ids if agent_id in selected]
        for dimension, agent_ids in DIMENSION_GROUPS.items()
    }


def _compiled_agent_ids_for_intent(intent: Mapping[str, Any]) -> list[str]:
    selected_dimensions = _unique_known_dimensions(cast(list[str] | None, intent.get("selected_dimensions")))
    selected_agents = _unique_known_agents(cast(list[str] | None, intent.get("selected_agents")))
    if not selected_dimensions:
        raise ValueError("selected_dimensions_missing")
    l2_by_dimension = _selected_l2_agents_by_dimension(selected_agents)
    missing_l2_dimensions = [
        dimension for dimension in selected_dimensions if not l2_by_dimension[dimension]
    ]
    if missing_l2_dimensions:
        raise ValueError("selected_dimension_l2_agents_missing")

    compiled: set[str] = {
        "route_planner",
        "financial_data_service",
        "entity_relation_extractor",
        "report_generator",
    }
    for dimension in selected_dimensions:
        compiled.update(l2_by_dimension[dimension])
        compiled.add(DIMENSION_COMPOSITE_AGENT_IDS[dimension])

    task_type = str(intent.get("task_type") or "")
    if task_type in INVESTMENT_JUDGMENT_TASK_TYPES or "decision_synthesizer" in selected_agents:
        compiled.add("decision_synthesizer")

    return [agent_id for agent_id in RESET_RUNTIME_AGENT_IDS if agent_id in compiled]


def _compiled_steps_for_intent(
    intent: Mapping[str, Any],
    compiled_agent_ids: list[str],
) -> list[FixedDagStep]:
    selected_dimensions = _unique_known_dimensions(cast(list[str] | None, intent.get("selected_dimensions")))
    selected_agents = _unique_known_agents(cast(list[str] | None, intent.get("selected_agents")))
    l2_by_dimension = _selected_l2_agents_by_dimension(selected_agents)
    compiled_agent_set = set(compiled_agent_ids)
    include_decision = "decision_synthesizer" in compiled_agent_set
    terminal_dimension_step_ids = [
        f"dimension:{dimension}"
        for dimension in selected_dimensions
        if l2_by_dimension[dimension]
    ]

    steps: list[FixedDagStep] = []
    for step in _build_steps():
        agent_id = str(step.get("agent_id") or "")
        if agent_id not in compiled_agent_set:
            continue
        compiled_step = dict(step)
        if agent_id == "route_planner":
            compiled_step["depends_on"] = []
        elif agent_id in {"financial_data_service", "entity_relation_extractor"}:
            compiled_step["depends_on"] = ["route_planner"]
        elif agent_id in L2_CONCLUSION_AGENT_IDS:
            compiled_step["depends_on"] = [
                "financial_data_service",
                "entity_relation_extractor",
            ]
        elif agent_id in DIMENSION_COMPOSITE_AGENT_IDS.values():
            dimension = _agent_dimension(agent_id)
            l2_agents = l2_by_dimension[dimension]
            compiled_step["target_ids"] = list(l2_agents)
            compiled_step["depends_on"] = [f"l2:{l2_agent_id}" for l2_agent_id in l2_agents]
        elif agent_id == "decision_synthesizer":
            compiled_step["depends_on"] = list(terminal_dimension_step_ids)
        elif agent_id == "report_generator":
            compiled_step["depends_on"] = (
                ["decision_synthesizer"]
                if include_decision
                else list(terminal_dimension_step_ids)
            )
        steps.append(cast(FixedDagStep, compiled_step))
    return steps


def build_selected_fixed_dag_plan(
    *,
    route_intent: Mapping[str, Any],
    user_text: str = "",
    as_of: str | None = None,
    plan_id: str = "selected-fixed-dag-plan-v1",
    selected_steps: list[FixedDagStep] | None = None,
    fallback_to: str = "full_dag",
    fallback_reason: str = "",
    provenance: dict[str, Any] | None = None,
) -> SelectedFixedDagPlan:
    intent = dict(route_intent)
    selected_dimensions = _unique_known_dimensions(cast(list[str] | None, intent.get("selected_dimensions")))
    intent_selected_agents = _unique_known_agents(cast(list[str] | None, intent.get("selected_agents")))
    steps = list(selected_steps or _steps_for_selected_agents(intent_selected_agents))
    step_agent_ids = [
        str(step.get("agent_id"))
        for step in steps
        if isinstance(step, Mapping) and step.get("agent_id")
    ]
    target_agent_ids = list(dict.fromkeys(step_agent_ids or intent_selected_agents))
    selected_agents = list(target_agent_ids)
    selected_dimension_set = set(selected_dimensions)
    omitted_dimensions = [
        cast(DimensionName, dimension)
        for dimension in DIMENSION_GROUPS
        if dimension not in selected_dimension_set
    ]
    omitted_agents = [
        agent_id for agent_id in RESET_RUNTIME_AGENT_IDS if agent_id not in set(target_agent_ids)
    ]
    return {
        "schema": SELECTED_FIXED_DAG_SCHEMA_VERSION,
        "schema_version": SELECTED_FIXED_DAG_SCHEMA_VERSION,
        "plan_id": str(plan_id or "selected-fixed-dag-plan-v1"),
        "user_text": str(user_text or intent.get("user_text") or ""),
        "as_of": _as_of(as_of),
        "stages": _stage_items_for_steps(cast(list[Mapping[str, Any]], steps)),
        "steps": steps,
        "dag_steps": steps,
        "target_agent_ids": target_agent_ids,
        "target": target_agent_ids,
        "dimension_groups": {
            dimension: [
                agent_id
                for agent_id in DIMENSION_GROUPS[dimension]
                if agent_id in target_agent_ids
            ]
            for dimension in selected_dimensions
        },
        "selected_dimensions": selected_dimensions,
        "selected_agents": selected_agents,
        "omitted_dimensions": omitted_dimensions,
        "omitted_agents": omitted_agents,
        "route_intent": cast(RouteIntent, intent),
        "fallback_to": fallback_to,
        "fallback_reason": str(fallback_reason or intent.get("fallback_reason") or "").strip(),
        "provenance": {
            "source": "selected_fixed_dag_contract",
            "provider_invoked": False,
            "external_invoked": False,
            **dict(provenance or {}),
        },
    }


def compile_selected_fixed_dag_plan(
    route_intent: Mapping[str, Any],
    *,
    user_text: str = "",
    as_of: str | None = None,
) -> SelectedFixedDagPlan:
    """Compile planner intent into a deterministic selected fixed DAG plan."""
    valid, reason = validate_route_intent(route_intent)
    if not valid:
        raise ValueError(f"invalid_route_intent:{reason}")
    if route_intent.get("needs_clarification"):
        raise ValueError("route_intent_needs_clarification")

    compiled_agent_ids = _compiled_agent_ids_for_intent(route_intent)
    selected_steps = _compiled_steps_for_intent(route_intent, compiled_agent_ids)
    plan = build_selected_fixed_dag_plan(
        route_intent=route_intent,
        user_text=user_text,
        as_of=as_of,
        selected_steps=selected_steps,
        fallback_reason=str(route_intent.get("fallback_reason") or "fallback to full DAG"),
        provenance={
            "source": "deterministic_selected_dag_compiler",
            "compiler": "r8_2_deterministic_selected_dag_compiler",
            "provider_invoked": False,
            "external_invoked": False,
        },
    )
    valid, reason = validate_selected_fixed_dag_plan(plan)
    if not valid:
        raise ValueError(f"compiled_selected_plan_invalid:{reason}")
    return plan


def validate_selected_fixed_dag_plan(plan: Mapping[str, Any]) -> tuple[bool, str]:
    if not isinstance(plan, Mapping):
        return False, "plan_not_mapping"
    if plan.get("schema") != SELECTED_FIXED_DAG_SCHEMA_VERSION:
        return False, "invalid_schema"
    if plan.get("schema_version", SELECTED_FIXED_DAG_SCHEMA_VERSION) != SELECTED_FIXED_DAG_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if _contains_legacy_key(plan):
        return False, "legacy_dispatch_field_present"
    if _contains_legacy_dispatch_value(plan):
        return False, "legacy_dispatch_value_present"
    if _contains_selected_plan_forbidden_key(plan):
        return False, "runtime_binding_field_present"
    route_intent = plan.get("route_intent")
    if not isinstance(route_intent, Mapping):
        return False, "route_intent_missing"
    valid, reason = validate_route_intent(route_intent)
    if not valid:
        return False, f"route_intent:{reason}"
    selected_dimensions = plan.get("selected_dimensions")
    if not isinstance(selected_dimensions, list):
        return False, "invalid_selected_dimensions"
    if set(selected_dimensions) != set(route_intent.get("selected_dimensions", [])):
        return False, "route_intent_dimensions_mismatch"
    if len(selected_dimensions) != len(set(selected_dimensions)):
        return False, "duplicate_selected_dimensions"
    if any(dimension not in DIMENSION_GROUPS for dimension in selected_dimensions):
        return False, "unknown_selected_dimension"
    selected_agents = plan.get("selected_agents")
    target_agent_ids = plan.get("target_agent_ids")
    target = plan.get("target")
    if not isinstance(selected_agents, list) or not isinstance(target_agent_ids, list) or not isinstance(target, list):
        return False, "invalid_targets"
    route_intent_agents = set(route_intent.get("selected_agents", []))
    if not route_intent_agents <= set(selected_agents):
        return False, "route_intent_agent_not_selected"
    if any(_looks_like_legacy_agent_id(str(agent_id)) for agent_id in selected_agents):
        return False, "legacy_agent_id_present"
    if "value_financial_analysis" in selected_agents:
        return False, "removed_agent_present"
    if any(agent_id not in RESET_RUNTIME_AGENT_IDS for agent_id in selected_agents):
        return False, "unknown_selected_agent"
    selected_dimension_set = set(selected_dimensions)
    for agent_id in selected_agents:
        dimension = _agent_dimension(str(agent_id))
        if dimension in DIMENSION_GROUPS and dimension not in selected_dimension_set:
            return False, "agent_dimension_not_selected"
    if set(target_agent_ids) != set(target):
        return False, "target_mismatch"
    if set(target_agent_ids) != set(selected_agents):
        return False, "target_selected_agents_mismatch"
    route_task_type = str(route_intent.get("task_type") or "")
    if "report_generator" not in target_agent_ids:
        return False, "report_generator_required"
    if route_task_type in INVESTMENT_JUDGMENT_TASK_TYPES:
        if "risk" not in selected_dimension_set:
            return False, "risk_dimension_required"
        if "decision_synthesizer" not in target_agent_ids:
            return False, "decision_synthesizer_required"
    dimension_groups = plan.get("dimension_groups")
    if not isinstance(dimension_groups, Mapping):
        return False, "invalid_dimension_groups"
    if set(dimension_groups) != set(selected_dimensions):
        return False, "dimension_groups_mismatch"
    for dimension, agent_ids in dimension_groups.items():
        if dimension not in DIMENSION_GROUPS:
            return False, "unknown_dimension_group"
        if not isinstance(agent_ids, list):
            return False, "invalid_dimension_group_agents"
        if not set(agent_ids) <= set(DIMENSION_GROUPS[str(dimension)]):
            return False, "dimension_group_agent_mismatch"
        if not set(agent_ids) <= set(target_agent_ids):
            return False, "dimension_group_agent_not_targeted"
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        return False, "steps_missing"
    dag_steps = plan.get("dag_steps")
    if not isinstance(dag_steps, list):
        return False, "dag_steps_missing"
    step_ids = [step.get("id") for step in steps if isinstance(step, Mapping)]
    dag_step_ids = [step.get("id") for step in dag_steps if isinstance(step, Mapping)]
    if set(dag_step_ids) != set(step_ids):
        return False, "dag_steps_mismatch"
    if len(step_ids) != len(set(step_ids)):
        return False, "duplicate_step_id"
    step_agent_ids = {
        step.get("agent_id")
        for step in steps
        if isinstance(step, Mapping) and step.get("agent_id")
    }
    if any(agent_id not in RESET_RUNTIME_AGENT_IDS for agent_id in step_agent_ids):
        return False, "invalid_agent_id"
    if set(step_agent_ids) != set(target_agent_ids):
        return False, "step_agent_ids_mismatch"
    known_step_ids = set(str(step_id) for step_id in step_ids)
    for step in steps:
        if not isinstance(step, Mapping):
            return False, "invalid_step"
        stage = str(step.get("stage") or "")
        dimension = str(step.get("dimension") or "")
        if stage not in FIXED_DAG_STAGE_ORDER:
            return False, "invalid_stage"
        if dimension not in {"l1", "l4", *DIMENSION_GROUPS}:
            return False, "invalid_dimension"
        agent_id = str(step.get("agent_id") or "")
        expected_dimension = _agent_dimension(agent_id)
        if agent_id and expected_dimension and dimension != expected_dimension:
            return False, "agent_dimension_mismatch"
        if agent_id == "sentiment_company_radar" and dimension != "market":
            return False, "sentiment_dimension_mismatch"
        if agent_id == DIMENSION_COMPOSITE_AGENT_IDS["risk"] and "l2:sentiment_company_radar" in step.get("depends_on", []):
            return False, "risk_reads_sentiment"
        if any(dep_id not in known_step_ids for dep_id in step.get("depends_on", [])):
            return False, "dependency_not_selected"
    step_ids_by_stage = {
        stage: [step["id"] for step in steps if isinstance(step, Mapping) and step.get("stage") == stage]
        for stage in FIXED_DAG_STAGE_ORDER
    }
    stage_items = plan.get("stages")
    if not isinstance(stage_items, list) or len(stage_items) != len(FIXED_DAG_STAGE_ORDER):
        return False, "stages_mismatch"
    for item in stage_items:
        if not isinstance(item, Mapping):
            return False, "invalid_stage_item"
        stage_id = item.get("id")
        if stage_id not in step_ids_by_stage:
            return False, "unknown_stage"
        if item.get("step_ids") != step_ids_by_stage[stage_id]:
            return False, "stage_step_ids_mismatch"
    omitted_dimensions = plan.get("omitted_dimensions")
    omitted_agents = plan.get("omitted_agents")
    if not isinstance(omitted_dimensions, list) or not isinstance(omitted_agents, list):
        return False, "invalid_omitted_fields"
    if set(omitted_dimensions) != (set(DIMENSION_GROUPS) - set(selected_dimensions)):
        return False, "omitted_dimensions_mismatch"
    if set(omitted_agents) != (set(RESET_RUNTIME_AGENT_IDS) - set(target_agent_ids)):
        return False, "omitted_agents_mismatch"
    fallback_to = str(plan.get("fallback_to") or "")
    if fallback_to not in SELECTED_PLAN_FALLBACK_TARGETS:
        return False, "invalid_fallback_to"
    fallback_reason = str(plan.get("fallback_reason") or "").strip()
    if fallback_to == "full_dag" and not fallback_reason:
        return False, "fallback_reason_missing"
    if fallback_reason and _contains_public_unsafe_text(fallback_reason):
        return False, "fallback_reason_not_public_safe"
    provenance = plan.get("provenance", {})
    if not isinstance(provenance, Mapping):
        return False, "invalid_provenance"
    if provenance.get("provider_invoked") or provenance.get("external_invoked"):
        return False, "live_invocation_claim_present"
    return True, "ok"


def normalize_fixed_dag_plan(plan: Mapping[str, Any]) -> FixedDagPlan:
    question = str(plan.get("user_text") or plan.get("question") or "")
    as_of = _as_of(cast(str | None, plan.get("as_of")))
    normalized = build_default_fixed_dag_plan(question, as_of)
    if isinstance(plan.get("plan_id"), str) and str(plan["plan_id"]).strip():
        normalized["plan_id"] = str(plan["plan_id"]).strip()
    normalized["provenance"] = {
        **normalized["provenance"],
        "source": "normalized_fixed_dag_plan",
    }
    return normalized


def build_data_bundle(plan: Mapping[str, Any]) -> DataBundle:
    normalized = normalize_fixed_dag_plan(plan)
    as_of = normalized["as_of"]
    return {
        "schema": DATA_BUNDLE_SCHEMA_VERSION,
        "schema_version": DATA_BUNDLE_SCHEMA_VERSION,
        "status": "pending_implementation",
        "as_of": as_of,
        "data_as_of": _data_as_of_for(as_of),
        "sources": [],
        "notes": [
            "金融数据服务是 R3 阶段的确定性占位接口。",
            "当前为本地固定流程模式。",
        ],
    }


def validate_data_bundle(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != DATA_BUNDLE_SCHEMA_VERSION:
        return False, "invalid_schema"
    if obj.get("schema_version", DATA_BUNDLE_SCHEMA_VERSION) != DATA_BUNDLE_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if obj.get("status") not in {"pending_implementation", "partial", "complete", "error"}:
        return False, "invalid_status"
    if not _data_not_after(obj.get("data_as_of"), obj.get("as_of")):
        return False, "data_as_of_after_as_of"
    if not isinstance(obj.get("sources"), list):
        return False, "invalid_sources"
    if _contains_legacy_key(obj):
        return False, "legacy_dispatch_field_present"
    return True, "ok"


def build_entity_relation_bundle(plan: Mapping[str, Any]) -> EntityRelationBundle:
    normalized = normalize_fixed_dag_plan(plan)
    as_of = normalized["as_of"]
    return {
        "schema": ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
        "schema_version": ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
        "status": "pending_implementation",
        "as_of": as_of,
        "data_as_of": _data_as_of_for(as_of),
        "entities": [],
        "relations": [],
        "notes": [
            "实体与关系抽取是 R3 阶段的确定性占位接口。",
            "当前为本地固定流程模式。",
            f"原始问题长度：{len(normalized['user_text'])}",
        ],
    }


def validate_entity_relation_bundle(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != ENTITY_RELATION_BUNDLE_SCHEMA_VERSION:
        return False, "invalid_schema"
    if obj.get("schema_version", ENTITY_RELATION_BUNDLE_SCHEMA_VERSION) != ENTITY_RELATION_BUNDLE_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if obj.get("status") not in {"pending_implementation", "partial", "complete", "error"}:
        return False, "invalid_status"
    if not _data_not_after(obj.get("data_as_of"), obj.get("as_of")):
        return False, "data_as_of_after_as_of"
    if not isinstance(obj.get("entities"), list) or not isinstance(obj.get("relations"), list):
        return False, "invalid_entity_relation_lists"
    if _contains_legacy_key(obj):
        return False, "legacy_dispatch_field_present"
    return True, "ok"


def build_pending_conclusion(
    agent_id: str,
    dimension: str,
    *,
    as_of: str,
    reason: str,
) -> ConclusionObject:
    item: ConclusionObject = {
        "schema": CONCLUSION_OBJECT_SCHEMA_VERSION,
        "schema_version": CONCLUSION_OBJECT_SCHEMA_VERSION,
        "agent_id": agent_id,
        "dimension": dimension,
        "stance": "not_evaluated",
        "confidence": 0.0,
        "status": "pending_implementation",
        "evidence": [],
        "as_of": as_of,
        "data_as_of": _data_as_of_for(as_of),
        "event_flags": [],
        "provenance": {
            "source": RESET_SOURCE,
            "reason": reason,
            "provider_invoked": False,
            "external_invoked": False,
        },
    }
    if agent_id == "sentiment_company_radar":
        item["output_routes"] = list(SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES)
    return item


def validate_conclusion_object(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != CONCLUSION_OBJECT_SCHEMA_VERSION:
        return False, "invalid_schema"
    if obj.get("schema_version", CONCLUSION_OBJECT_SCHEMA_VERSION) != CONCLUSION_OBJECT_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if obj.get("agent_id") not in L2_CONCLUSION_AGENT_IDS:
        return False, "unknown_agent_id"
    if obj.get("dimension") != AGENT_DIMENSIONS.get(str(obj.get("agent_id"))):
        return False, "dimension_mismatch"
    try:
        confidence = float(obj.get("confidence"))
    except (TypeError, ValueError):
        return False, "invalid_confidence"
    if not 0.0 <= confidence <= 1.0:
        return False, "confidence_out_of_range"
    if obj.get("status") not in {"pending_implementation", "partial", "complete", "error"}:
        return False, "invalid_status"
    if not isinstance(obj.get("evidence"), list):
        return False, "invalid_evidence"
    if "event_flags" in obj and not isinstance(obj.get("event_flags"), list):
        return False, "invalid_event_flags"
    if not _data_not_after(obj.get("data_as_of"), obj.get("as_of")):
        return False, "data_as_of_after_as_of"
    if obj.get("agent_id") == "sentiment_company_radar" and obj.get("output_routes") != [
        "market_composite"
    ]:
        return False, "sentiment_route_mismatch"
    if obj.get("agent_id") != "sentiment_company_radar" and obj.get("output_routes"):
        return False, "unexpected_output_routes"
    provenance = obj.get("provenance", {})
    if not isinstance(provenance, Mapping):
        return False, "invalid_provenance"
    if isinstance(provenance, Mapping) and provenance.get("external_invoked"):
        return False, "live_invocation_claim_present"
    if isinstance(provenance, Mapping) and provenance.get("provider_invoked"):
        if (
            provenance.get("source") != "internal_llm_placeholder"
            or provenance.get("runtime_path") != "internal_llm_placeholder"
        ):
            return False, "live_invocation_claim_present"
        if confidence > 0.4:
            return False, "internal_placeholder_confidence_out_of_range"
    return True, "ok"


def build_l2_conclusions(
    plan: Mapping[str, Any] | None = None,
    *,
    as_of: str | None = None,
) -> dict[str, ConclusionObject]:
    normalized_as_of = _as_of(
        as_of
        or (str(plan.get("as_of")) if isinstance(plan, Mapping) and plan.get("as_of") else None)
    )
    selected_l2_agent_ids = set(L2_CONCLUSION_AGENT_IDS)
    if isinstance(plan, Mapping) and plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION:
        selected_l2_agent_ids = {
            str(agent_id)
            for agent_id in plan.get("target_agent_ids", [])
            if str(agent_id) in L2_CONCLUSION_AGENT_IDS
        }
    return {
        agent_id: build_pending_conclusion(
            agent_id,
            AGENT_DIMENSIONS[agent_id],
            as_of=normalized_as_of,
            reason="业务智能体实现仍处于 R3 阶段待完成状态。",
        )
        for agent_id in L2_CONCLUSION_AGENT_IDS
        if agent_id in selected_l2_agent_ids
    }


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


def _target_from_question(question: str, *, default: str = "600519.SH") -> str:
    match = re.search(r"\b\d{6}\.(?:SH|SZ|BJ)\b", str(question or "").upper())
    if match:
        return match.group(0)
    return default


def _agent_layer(agent_id: str) -> str:
    if agent_id in L1_AGENT_IDS:
        return "L1"
    if agent_id in L2_CONCLUSION_AGENT_IDS:
        return "L2"
    if agent_id in L3_COMPOSITE_AGENT_IDS:
        return "L3"
    if agent_id in L4_AGENT_IDS:
        return "L4"
    return "unknown"


def _agent_task_dimension(agent_id: str) -> str:
    if agent_id in AGENT_DIMENSIONS:
        return AGENT_DIMENSIONS[agent_id]
    if agent_id in DIMENSION_COMPOSITE_AGENT_IDS.values():
        return _agent_dimension(agent_id)
    if agent_id in {"route_planner", "financial_data_service", "entity_relation_extractor"}:
        return "l1"
    if agent_id in L4_AGENT_IDS:
        return "l4"
    return "unknown"


def _required_output_schema_for_agent(agent_id: str) -> str:
    if agent_id == "route_planner":
        return FIXED_DAG_SCHEMA_VERSION
    if agent_id == "financial_data_service":
        return DATA_BUNDLE_SCHEMA_VERSION
    if agent_id == "entity_relation_extractor":
        return ENTITY_RELATION_BUNDLE_SCHEMA_VERSION
    if agent_id in L2_CONCLUSION_AGENT_IDS:
        return "agent_conclusion_v1"
    if agent_id in {"value_composite", "market_composite"}:
        return "dimension_conclusion_v1"
    if agent_id == "risk_composite":
        return "risk_conclusion_v1"
    if agent_id == "macro_composite":
        return "macro_conclusion_v1"
    if agent_id == "decision_synthesizer":
        return DECISION_RESULT_SCHEMA_VERSION
    if agent_id == "report_generator":
        return REPORT_RESULT_SCHEMA_VERSION
    return "unknown"


def _task_instruction_for_agent(agent_id: str) -> str:
    display_name = AGENT_TITLE_LABELS.get(agent_id, agent_id)
    dimension = _agent_task_dimension(agent_id)
    if agent_id == "route_planner":
        return "请理解用户自然语言问题，识别分析对象、任务类型、维度范围，并组织本轮固定 DAG 研判流程。"
    if agent_id == "financial_data_service":
        return "请根据用户问题和固定 DAG 计划整理本轮分析需要的行情、财务、估值和时间点数据，输出 data_bundle_v1；不要给出投资结论。"
    if agent_id == "entity_relation_extractor":
        return "请识别用户问题中的公司、证券代码、行业、事件和关系，输出 entity_relation_bundle_v1；不要替代 L2 分析智能体给观点。"
    if agent_id in L2_CONCLUSION_AGENT_IDS:
        dimension_label = {
            "value": "价值/估值",
            "market": "市场面",
            "risk": "风险",
            "macro": "宏观",
        }.get(dimension, dimension)
        if dimension == "risk":
            return f"你是{display_name}智能体。请阅读用户问题、L1 数据证据和实体关系，从{dimension_label}角度输出结构化 agent_conclusion_v1；风险类输出应表达 gate_member/risk_score，不要输出最终投资裁决。"
        return f"你是{display_name}智能体。请阅读用户问题、L1 数据证据和实体关系，从{dimension_label}角度输出结构化 agent_conclusion_v1，包含 stance、confidence、evidence 和 status。"
    if agent_id in {"value_composite", "market_composite"}:
        dimension_label = "价值维" if agent_id == "value_composite" else "市场维"
        return f"你是{display_name}智能体。请只综合本轮{dimension_label} L2 智能体输出，形成 dimension_conclusion_v1；不要直接调用无关维度，不要替代 L2 重新编造证据。"
    if agent_id == "risk_composite":
        return "你是风险综合智能体。请只综合本轮风险维 L2 输出，形成 risk_conclusion_v1 风险闸门；不要输出方向票，不要消费企业舆情雷达。"
    if agent_id == "macro_composite":
        return "你是宏观综合智能体。请综合本轮宏观维 L2 输出，形成 macro_conclusion_v1 宏观调节器；dimension_weights 只能包含 value 和 market。"
    if agent_id == "decision_synthesizer":
        return "请读取四个 L3 综合结果，形成受风险门和宏观调节约束的 decision_result_v1；不要绕过缺失或错误证据。"
    if agent_id == "report_generator":
        return "请读取完整 report_input_bundle_v1，包括每个 agent 的任务、L1 证据、L2 输出、L3 综合和决策结果，生成面向用户的中文研判报告。"
    return f"请按固定 DAG 当前任务要求执行 {display_name}。"


def _bounded_task_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return ""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, raw in list(value.items())[:40]:
            text_key = str(key)
            if text_key.lower() in REPORT_BUNDLE_UNSAFE_KEYS:
                continue
            bounded = _bounded_task_value(raw, depth=depth + 1)
            if bounded not in ("", [], {}):
                result[text_key] = bounded
        return result
    if isinstance(value, list):
        return [
            bounded
            for item in value[:20]
            if (bounded := _bounded_task_value(item, depth=depth + 1)) not in ("", [], {})
        ]
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    return _safe_public_text(value, limit=500)


def _l2_task_upstream_result(agent_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
    item = _l2_agent_summary(agent_id, result)
    upstream = {
        key: item[key]
        for key in (
            "agent_id",
            "display_name",
            "layer",
            "dimension",
            "status",
            "stance",
            "confidence",
            "summary",
            "risk_score",
            "as_of",
            "data_as_of",
            "source",
        )
        if key in item
    }
    evidence_items = _safe_evidence_detail_items(result.get("evidence"), limit=4)
    if evidence_items:
        upstream["evidence_items"] = evidence_items
    provenance_notes = _provenance_notes(result.get("provenance"))
    for key in ("domain_metrics", "drivers", "research_points", "data_quality"):
        if key in provenance_notes:
            upstream[key] = provenance_notes[key]
    return upstream


def _l3_task_upstream_result(result: Mapping[str, Any]) -> dict[str, Any]:
    item = _l3_composite_summary(result)
    return {
        key: item[key]
        for key in (
            "agent_id",
            "display_name",
            "layer",
            "dimension",
            "status",
            "stance",
            "confidence",
            "summary",
            "members",
            "gate",
            "risk_score",
            "regime",
            "dimension_weights",
            "risk_sensitivity",
            "as_of",
            "data_as_of",
            "source",
        )
        if key in item
    }


def _upstream_results_for_agent(
    agent_id: str,
    *,
    l2_conclusions: Mapping[str, Any] | None,
    dimension_results: Mapping[str, Any] | None,
    decision_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if agent_id in DIMENSION_COMPOSITE_AGENT_IDS.values():
        dimension = _agent_dimension(agent_id)
        return {
            upstream_agent_id: _l2_task_upstream_result(
                upstream_agent_id,
                cast(Mapping[str, Any], result),
            )
            for upstream_agent_id, result in (l2_conclusions or {}).items()
            if upstream_agent_id in DIMENSION_GROUPS[dimension] and isinstance(result, Mapping)
        }
    if agent_id == "decision_synthesizer":
        return {
            dimension: _l3_task_upstream_result(cast(Mapping[str, Any], result))
            for dimension, result in (dimension_results or {}).items()
            if dimension in DIMENSION_GROUPS and isinstance(result, Mapping)
        }
    if agent_id == "report_generator":
        return {
            "l2": {
                upstream_agent_id: _l2_task_upstream_result(
                    upstream_agent_id,
                    cast(Mapping[str, Any], result),
                )
                for upstream_agent_id, result in (l2_conclusions or {}).items()
                if upstream_agent_id in L2_CONCLUSION_AGENT_IDS and isinstance(result, Mapping)
            },
            "l3": {
                dimension: _l3_task_upstream_result(cast(Mapping[str, Any], result))
                for dimension, result in (dimension_results or {}).items()
                if dimension in DIMENSION_GROUPS and isinstance(result, Mapping)
            },
            "decision": _bounded_task_value(decision_result or {}),
        }
    return {}


def build_agent_task(
    agent_id: str,
    *,
    question: str,
    as_of: str,
    data_bundle: Mapping[str, Any] | None = None,
    entity_relation_bundle: Mapping[str, Any] | None = None,
    l2_conclusions: Mapping[str, Any] | None = None,
    dimension_results: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
) -> AgentTask:
    """Build one public-safe natural-language task for a fixed DAG agent."""
    task_agent_id = str(agent_id)
    return {
        "schema": AGENT_TASK_SCHEMA_VERSION,
        "schema_version": AGENT_TASK_SCHEMA_VERSION,
        "agent_id": task_agent_id,
        "display_name": AGENT_TITLE_LABELS.get(task_agent_id, task_agent_id),
        "layer": _agent_layer(task_agent_id),
        "dimension": _agent_task_dimension(task_agent_id),
        "user_question": _safe_public_text(question, limit=500),
        "task_instruction": _task_instruction_for_agent(task_agent_id),
        "target": _target_from_question(question),
        "as_of": _as_of(as_of),
        "data_bundle": cast(dict[str, Any], _bounded_task_value(data_bundle or {})),
        "entity_relation_bundle": cast(
            dict[str, Any],
            _bounded_task_value(entity_relation_bundle or {}),
        ),
        "upstream_results": _upstream_results_for_agent(
            task_agent_id,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            decision_result=decision_result,
        ),
        "required_output_schema": _required_output_schema_for_agent(task_agent_id),
        "provenance": {
            "source": "fixed_dag_agent_task_builder",
            "default_off_demo_contract": True,
            "runtime_binding_enabled": False,
            "invoke_enabled_by_default": False,
        },
    }


def build_agent_tasks_for_plan(
    plan: Mapping[str, Any],
    *,
    question: str,
    as_of: str,
    data_bundle: Mapping[str, Any] | None = None,
    entity_relation_bundle: Mapping[str, Any] | None = None,
    l2_conclusions: Mapping[str, Any] | None = None,
    dimension_results: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
) -> dict[str, AgentTask]:
    """Build agent tasks keyed by step id for a fixed or selected DAG plan."""
    tasks: dict[str, AgentTask] = {}
    raw_steps = plan.get("dag_steps", plan.get("steps", []))
    steps = raw_steps if isinstance(raw_steps, list) else []
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        agent_id = str(step.get("agent_id") or "")
        step_id = str(step.get("id") or agent_id)
        if agent_id in RESET_RUNTIME_AGENT_IDS and step_id:
            tasks[step_id] = build_agent_task(
                agent_id,
                question=question,
                as_of=as_of,
                data_bundle=data_bundle,
                entity_relation_bundle=entity_relation_bundle,
                l2_conclusions=l2_conclusions,
                dimension_results=dimension_results,
                decision_result=decision_result,
            )
    return tasks


def _agent_task_summary(task: Mapping[str, Any]) -> dict[str, Any]:
    upstream = task.get("upstream_results", {})
    upstream_ids: list[str] = []
    if isinstance(upstream, Mapping):
        upstream_ids = [
            str(key)
            for key in upstream
            if str(key) and str(key) not in {"l2", "l3", "decision"}
        ]
        if not upstream_ids:
            for group_key in ("l2", "l3"):
                group = upstream.get(group_key)
                if isinstance(group, Mapping):
                    upstream_ids.extend(str(key) for key in group if str(key))
    return {
        "schema": AGENT_TASK_SCHEMA_VERSION,
        "agent_id": _safe_public_text(task.get("agent_id"), limit=80),
        "display_name": _safe_public_text(task.get("display_name"), limit=80),
        "layer": _safe_public_text(task.get("layer"), limit=20),
        "dimension": _safe_public_text(task.get("dimension"), limit=40),
        "task_instruction": _safe_public_text(task.get("task_instruction"), limit=260),
        "target": _safe_public_text(task.get("target"), limit=80),
        "as_of": _safe_public_text(task.get("as_of"), limit=40),
        "required_output_schema": _safe_public_text(
            task.get("required_output_schema"),
            limit=80,
        ),
        "upstream_agent_ids": upstream_ids[:24],
        "has_l1_data_bundle": bool(task.get("data_bundle")),
        "has_l1_entity_relation_bundle": bool(task.get("entity_relation_bundle")),
    }


def build_agent_task_summaries(agent_tasks: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Return bounded public task summaries for report input and workflow trace."""
    if not isinstance(agent_tasks, Mapping):
        return []
    summaries: list[dict[str, Any]] = []
    for step_id, task in agent_tasks.items():
        if not isinstance(task, Mapping):
            continue
        summary = _agent_task_summary(task)
        summary["step_id"] = _safe_public_text(step_id, limit=120)
        summaries.append(summary)
    return summaries


def validate_agent_task(task: Mapping[str, Any]) -> tuple[bool, str]:
    if task.get("schema") != AGENT_TASK_SCHEMA_VERSION:
        return False, "invalid_schema"
    if task.get("schema_version", AGENT_TASK_SCHEMA_VERSION) != AGENT_TASK_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    agent_id = str(task.get("agent_id") or "")
    if agent_id not in RESET_RUNTIME_AGENT_IDS:
        return False, "invalid_agent_id"
    if not _safe_public_text(task.get("user_question"), limit=500):
        return False, "user_question_missing"
    if not _safe_public_text(task.get("task_instruction"), limit=260):
        return False, "task_instruction_missing"
    if task.get("required_output_schema") != _required_output_schema_for_agent(agent_id):
        return False, "required_output_schema_mismatch"
    if _contains_unsafe_report_key(task):
        return False, "unsafe_agent_task_present"
    provenance = task.get("provenance", {})
    if not isinstance(provenance, Mapping):
        return False, "invalid_provenance"
    if provenance.get("runtime_binding_enabled") or provenance.get("invoke_enabled_by_default"):
        return False, "runtime_enablement_claim_present"
    return True, "ok"


def _safe_evidence_summary(evidence: Any) -> str:
    if not isinstance(evidence, list):
        return ""
    for item in evidence:
        if not isinstance(item, Mapping):
            continue
        for key in ("fact", "summary", "note", "evidence"):
            text = _safe_public_text(item.get(key), limit=160)
            if text:
                return text
    return ""


def _l2_quality_notes(result: Mapping[str, Any]) -> list[str]:
    """Build bounded report-facing notes explaining thin external evidence."""
    notes: list[str] = []
    provenance = result.get("provenance", {})
    status = _safe_public_text(result.get("status"), limit=40)
    if isinstance(provenance, Mapping):
        reason = _safe_public_text(provenance.get("reason"), limit=120)
        external_status = _safe_public_text(provenance.get("external_status"), limit=80)
        if reason:
            notes.append(f"adapter_reason={reason}")
        if external_status and external_status != status:
            notes.append(f"external_status={external_status}")
        raw_keys = _safe_public_text_list(provenance.get("raw_output_keys"), limit=8)
        if raw_keys:
            notes.append(f"raw_output_keys={','.join(raw_keys)}")
        quality_keys = _safe_public_text_list(provenance.get("quality_keys"), limit=8)
        if quality_keys:
            notes.append(f"quality_keys={','.join(quality_keys)}")
        domain_metrics = _safe_public_detail_mapping(provenance.get("domain_metrics"), limit=8)
        if domain_metrics:
            notes.append(f"domain_metrics_count={len(domain_metrics)}")
        drivers = _safe_public_detail_list(provenance.get("drivers"), limit=6)
        if drivers:
            notes.append(f"drivers_count={len(drivers)}")
        data_quality = _safe_public_detail_mapping(provenance.get("data_quality"), limit=8)
        if data_quality:
            notes.append(f"data_quality_count={len(data_quality)}")
        if provenance.get("adapter_failure") is True:
            notes.append("adapter_failure=true")
    evidence = result.get("evidence")
    evidence_count = len(evidence) if isinstance(evidence, list) else 0
    if evidence_count == 0:
        notes.append("readable_evidence_count=0")
    if status in {"error", "partial"}:
        notes.append(f"service_status={status}")
    return notes[:10]


def _evidence_ref_summary(evidence_refs: Any) -> str:
    if not isinstance(evidence_refs, list) or not evidence_refs:
        return ""
    refs = [
        _safe_public_text(item, limit=80)
        for item in evidence_refs[:3]
        if _safe_public_text(item, limit=80)
    ]
    return "；".join(refs)


def _report_source_from_provenance(provenance: Any) -> str:
    if not isinstance(provenance, Mapping):
        return "fixed_dag_placeholder"
    runtime_source = _safe_public_text(provenance.get("runtime_source"), limit=80)
    if runtime_source:
        return runtime_source
    if provenance.get("adapter_source"):
        return "external_compute_demo"
    if provenance.get("runtime_path") == "internal_llm_placeholder":
        return "internal_llm_placeholder"
    return _safe_public_text(provenance.get("source"), limit=80) or "fixed_dag_placeholder"


def _l2_agent_summary(agent_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
    provenance = result.get("provenance", {})
    dimension = _safe_public_text(result.get("dimension") or AGENT_DIMENSIONS.get(agent_id), limit=40)
    risk_score = None
    if isinstance(provenance, Mapping) and provenance.get("risk_score") is not None:
        risk_score = _safe_public_float(provenance.get("risk_score"))
    detail_notes = _l2_quality_notes(result)
    summary = _safe_evidence_summary(result.get("evidence"))
    if not summary:
        detail = f"；诊断：{'；'.join(detail_notes[:3])}" if detail_notes else ""
        summary = (
            f"{AGENT_TITLE_LABELS.get(agent_id, agent_id)} 输出 "
            f"{_safe_public_text(result.get('stance') or 'not_evaluated', limit=80)} "
            f"信号，置信度 {_safe_public_float(result.get('confidence')):.2f}。"
            f"{detail}"
        )
    evidence = result.get("evidence")
    item: dict[str, Any] = {
        "agent_id": agent_id,
        "display_name": AGENT_TITLE_LABELS.get(agent_id, agent_id),
        "layer": "L2",
        "dimension": dimension,
        "status": _safe_public_text(result.get("status"), limit=40),
        "stance": _safe_public_text(result.get("stance") or "risk_gate_member", limit=80),
        "confidence": _safe_public_float(result.get("confidence")),
        "summary": summary,
        "as_of": _safe_public_text(result.get("as_of"), limit=40),
        "data_as_of": _safe_public_text(result.get("data_as_of"), limit=40),
        "source": _report_source_from_provenance(provenance),
        "evidence_count": len(evidence) if isinstance(evidence, list) else 0,
        "detail_notes": detail_notes,
    }
    if risk_score is not None:
        item["risk_score"] = risk_score
    return item


def _safe_member_summaries(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    provenance = result.get("provenance", {})
    raw_members = (
        provenance.get("member_weight_summary")
        if isinstance(provenance, Mapping)
        else None
    )
    members: list[dict[str, Any]] = []
    if isinstance(raw_members, list):
        for item in raw_members[:12]:
            if not isinstance(item, Mapping):
                continue
            agent_id = _safe_public_text(item.get("agent_id"), limit=80)
            if not agent_id:
                continue
            member = {
                "agent_id": agent_id,
                "display_name": AGENT_TITLE_LABELS.get(agent_id, agent_id),
                "stance": _safe_public_text(item.get("stance"), limit=80),
                "status": _safe_public_text(item.get("status"), limit=40),
                "summary": _safe_public_text(item.get("summary"), limit=160),
            }
            if "weight" in item and item.get("weight") is not None:
                member["weight"] = _safe_public_float(item.get("weight"))
            if "confidence" in item and item.get("confidence") is not None:
                member["confidence"] = _safe_public_float(item.get("confidence"))
            if "risk_score" in item and item.get("risk_score") is not None:
                member["risk_score"] = _safe_public_float(item.get("risk_score"))
            members.append(member)
    if members:
        return members
    contributing_agents = result.get("contributing_agents")
    if isinstance(contributing_agents, list):
        for agent_id_value in contributing_agents[:12]:
            agent_id = _safe_public_text(agent_id_value, limit=80)
            if not agent_id:
                continue
            members.append(
                {
                    "agent_id": agent_id,
                    "display_name": AGENT_TITLE_LABELS.get(agent_id, agent_id),
                }
            )
    return members


def _safe_evidence_detail_items(value: Any, *, limit: int = 8) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for raw in value[:limit]:
        if not isinstance(raw, Mapping):
            continue
        item: dict[str, Any] = {}
        for key in ("id", "fact", "source", "as_of", "data_as_of", "unit"):
            text = _safe_public_text(raw.get(key), limit=220 if key == "fact" else 80)
            if text:
                item[key] = text
        if raw.get("value") is not None:
            try:
                item["value"] = float(raw.get("value"))
            except (TypeError, ValueError):
                text = _safe_public_text(raw.get("value"), limit=80)
                if text:
                    item["value"] = text
        if item:
            items.append(item)
    return items


def _provenance_notes(provenance: Any) -> dict[str, Any]:
    if not isinstance(provenance, Mapping):
        return {}
    notes: dict[str, Any] = {}
    for key in (
        "reason",
        "external_status",
        "adapter_input_schema",
        "compute_envelope_status",
        "stance_source",
        "confidence_source",
    ):
        text = _safe_public_text(provenance.get(key), limit=120)
        if text:
            notes[key] = text
    for key in ("raw_output_keys", "quality_keys"):
        values = _safe_public_text_list(provenance.get(key), limit=10, item_limit=80)
        if values:
            notes[key] = values
    domain_metrics = _safe_public_detail_mapping(provenance.get("domain_metrics"), limit=18)
    if domain_metrics:
        notes["domain_metrics"] = domain_metrics
    drivers = _safe_public_detail_list(provenance.get("drivers"), limit=10)
    if drivers:
        notes["drivers"] = drivers
    research_points = _safe_public_detail_list(provenance.get("research_points"), limit=8)
    if research_points:
        notes["research_points"] = research_points
    data_quality = _safe_public_detail_mapping(provenance.get("data_quality"), limit=14)
    if data_quality:
        notes["data_quality"] = data_quality
    if provenance.get("adapter_failure") is True:
        notes["adapter_failure"] = True
    if provenance.get("risk_score") is not None:
        notes["risk_score"] = _safe_public_float(provenance.get("risk_score"))
    return notes


def _l2_agent_evidence_detail(agent_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
    summary = _l2_agent_summary(agent_id, result)
    provenance = result.get("provenance", {})
    provenance_notes = _provenance_notes(provenance)
    detail: dict[str, Any] = {
        **summary,
        "received_output_schema": _safe_public_text(result.get("schema"), limit=80),
        "required_output_schema": "agent_conclusion_v1",
        "evidence_items": _safe_evidence_detail_items(result.get("evidence")),
        "provenance_notes": provenance_notes,
    }
    for key in ("domain_metrics", "drivers", "research_points", "data_quality"):
        if key in provenance_notes:
            detail[key] = provenance_notes[key]
    output_routes = result.get("output_routes")
    if isinstance(output_routes, list):
        detail["output_routes"] = _safe_public_text_list(output_routes, limit=6, item_limit=80)
    return detail


def _l3_composite_evidence_detail(result: Mapping[str, Any]) -> dict[str, Any]:
    summary = _l3_composite_summary(result)
    provenance = result.get("provenance", {})
    evidence_refs = result.get("evidence_refs")
    provenance_notes = _provenance_notes(provenance)
    detail: dict[str, Any] = {
        **summary,
        "received_output_schema": _safe_public_text(result.get("schema"), limit=80),
        "required_output_schema": {
            "value_composite": "dimension_conclusion_v1",
            "market_composite": "dimension_conclusion_v1",
            "risk_composite": "risk_conclusion_v1",
            "macro_composite": "macro_conclusion_v1",
        }.get(str(result.get("agent_id") or ""), "dimension_composite_result_v1"),
        "evidence_refs": [
            _safe_public_text(ref, limit=220)
            for ref in evidence_refs[:8]
            if _safe_public_text(ref, limit=220)
        ]
        if isinstance(evidence_refs, list)
        else [],
        "provenance_notes": provenance_notes,
    }
    for key in ("domain_metrics", "drivers", "research_points", "data_quality"):
        if key in provenance_notes:
            detail[key] = provenance_notes[key]
    return detail


def _l3_composite_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    agent_id = _safe_public_text(result.get("agent_id"), limit=80)
    dimension = _safe_public_text(result.get("dimension"), limit=40)
    provenance = result.get("provenance", {})
    evidence_refs = result.get("evidence_refs")
    detail_notes: list[str] = []
    if isinstance(evidence_refs, list):
        detail_notes.append(f"evidence_refs_count={len(evidence_refs)}")
    members_preview = _safe_member_summaries(result)
    if members_preview:
        detail_notes.append(f"member_count={len(members_preview)}")
    item: dict[str, Any] = {
        "agent_id": agent_id,
        "display_name": AGENT_TITLE_LABELS.get(agent_id, agent_id),
        "layer": "L3",
        "dimension": dimension,
        "status": _safe_public_text(result.get("status"), limit=40),
        "stance": _safe_public_text(result.get("stance"), limit=80),
        "confidence": _safe_public_float(result.get("confidence")),
        "summary": (
            _evidence_ref_summary(result.get("evidence_refs"))
            or f"{DIMENSION_TITLE_LABELS.get(dimension, dimension)} 已形成综合结果。"
        ),
        "members": members_preview,
        "detail_notes": detail_notes[:8],
        "as_of": _safe_public_text(result.get("as_of"), limit=40),
        "data_as_of": _safe_public_text(result.get("data_as_of"), limit=40),
        "source": _report_source_from_provenance(provenance),
    }
    for field in ("gate", "veto", "penalty", "risk_score", "regime", "risk_sensitivity"):
        if field in result:
            raw = result.get(field)
            item[field] = (
                bool(raw)
                if isinstance(raw, bool)
                else _safe_public_float(raw)
                if isinstance(raw, int | float)
                else _safe_public_text(raw, limit=80)
            )
    if isinstance(result.get("dimension_weights"), Mapping):
        item["dimension_weights"] = _safe_public_mapping(
            result.get("dimension_weights"),
            allowed_keys={"value", "market"},
        )
    return item


def build_agent_evidence_bundle(
    *,
    question: str,
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
    decision_result: Mapping[str, Any],
    agent_tasks: Mapping[str, Any] | None = None,
    data_bundle: Mapping[str, Any] | None = None,
    entity_relation_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the richer public-safe bundle consumed by demo report generation."""
    task_summaries = build_agent_task_summaries(agent_tasks)
    l2_items = [
        _l2_agent_evidence_detail(agent_id, cast(Mapping[str, Any], result))
        for agent_id, result in l2_conclusions.items()
        if agent_id in L2_CONCLUSION_AGENT_IDS and isinstance(result, Mapping)
    ]
    l3_items = [
        _l3_composite_evidence_detail(cast(Mapping[str, Any], result))
        for dimension, result in dimension_results.items()
        if dimension in DIMENSION_GROUPS and isinstance(result, Mapping)
    ]
    return {
        "schema": AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "schema_version": AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "question": _safe_public_text(question, limit=500),
        "l1_evidence": {
            "data_bundle_status": _safe_public_text(
                (data_bundle or {}).get("status") if isinstance(data_bundle, Mapping) else "",
                limit=40,
            ),
            "entity_relation_status": _safe_public_text(
                (entity_relation_bundle or {}).get("status")
                if isinstance(entity_relation_bundle, Mapping)
                else "",
                limit=40,
            ),
            "data_sources_count": len((data_bundle or {}).get("sources", []))
            if isinstance((data_bundle or {}).get("sources"), list)
            else 0,
            "entities_count": len((entity_relation_bundle or {}).get("entities", []))
            if isinstance((entity_relation_bundle or {}).get("entities"), list)
            else 0,
            "relations_count": len((entity_relation_bundle or {}).get("relations", []))
            if isinstance((entity_relation_bundle or {}).get("relations"), list)
            else 0,
        },
        "agent_tasks": task_summaries,
        "l2_agent_outputs": l2_items,
        "l3_composite_outputs": l3_items,
        "decision_output": _bounded_task_value(decision_result or {}),
        "quality_summary": {
            "l2_total": len(l2_items),
            "l2_complete": sum(1 for item in l2_items if item.get("status") == "complete"),
            "l2_error": sum(1 for item in l2_items if item.get("status") == "error"),
            "l2_partial": sum(1 for item in l2_items if item.get("status") == "partial"),
            "l2_without_readable_evidence": sum(
                1 for item in l2_items if int(item.get("evidence_count") or 0) == 0
            ),
            "l3_total": len(l3_items),
            "l3_complete": sum(1 for item in l3_items if item.get("status") == "complete"),
            "l3_partial": sum(1 for item in l3_items if item.get("status") == "partial"),
            "l3_error": sum(1 for item in l3_items if item.get("status") == "error"),
            "l3_available": sum(
                1 for item in l3_items if item.get("status") in {"complete", "partial"}
            ),
        },
        "provenance": {
            "source": "fixed_dag_agent_evidence_bundle",
            "provider_invoked": False,
            "external_invoked": False,
            "public_safe": True,
        },
    }


def build_report_input_bundle(
    *,
    question: str,
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
    decision_result: Mapping[str, Any],
    agent_tasks: Mapping[str, Any] | None = None,
    data_bundle: Mapping[str, Any] | None = None,
    entity_relation_bundle: Mapping[str, Any] | None = None,
) -> ReportInputBundle:
    l2_summaries = [
        _l2_agent_summary(agent_id, cast(Mapping[str, Any], result))
        for agent_id, result in l2_conclusions.items()
        if agent_id in L2_CONCLUSION_AGENT_IDS and isinstance(result, Mapping)
    ]
    l3_summaries = [
        _l3_composite_summary(cast(Mapping[str, Any], result))
        for dimension, result in dimension_results.items()
        if dimension in DIMENSION_GROUPS and isinstance(result, Mapping)
    ]
    risk_summary = next(
        (item for item in l3_summaries if item.get("dimension") == "risk"),
        {},
    )
    macro_summary = next(
        (item for item in l3_summaries if item.get("dimension") == "macro"),
        {},
    )
    return {
        "schema": REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
        "schema_version": REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
        "question": _safe_public_text(question, limit=500),
        "status": "complete" if l2_summaries or l3_summaries else "pending_implementation",
        "agent_task_summaries": build_agent_task_summaries(agent_tasks),
        "agent_evidence_bundle": build_agent_evidence_bundle(
            question=question,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            decision_result=decision_result,
            agent_tasks=agent_tasks,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
        ),
        "l2_agent_summaries": l2_summaries,
        "l3_composite_summaries": l3_summaries,
        "risk_gate": dict(risk_summary),
        "macro_regulator": dict(macro_summary),
        "decision_context": {
            "decision": _safe_public_text(decision_result.get("decision"), limit=80),
            "score": float(decision_result.get("score", 0.0) or 0.0),
            "confidence": _safe_public_float(decision_result.get("confidence")),
            "status": _safe_public_text(decision_result.get("status"), limit=40),
        },
        "limitations": [
            "报告输入包仅包含 public-safe 结构化摘要。",
            "不包含原始外部输出、接口地址、密钥、错误栈或内部推理草稿。",
        ],
        "provenance": {
            "source": "fixed_dag_report_input_bundle",
            "provider_invoked": False,
            "external_invoked": False,
        },
    }


def validate_report_input_bundle(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != REPORT_INPUT_BUNDLE_SCHEMA_VERSION:
        return False, "invalid_schema"
    if obj.get("schema_version", REPORT_INPUT_BUNDLE_SCHEMA_VERSION) != REPORT_INPUT_BUNDLE_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if "agent_task_summaries" in obj and not isinstance(obj.get("agent_task_summaries"), list):
        return False, "agent_task_summaries_invalid"
    if "agent_evidence_bundle" in obj:
        bundle = obj.get("agent_evidence_bundle")
        if not isinstance(bundle, Mapping):
            return False, "agent_evidence_bundle_invalid"
        if bundle.get("schema") != AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION:
            return False, "agent_evidence_bundle_invalid_schema"
    if not isinstance(obj.get("l2_agent_summaries"), list):
        return False, "l2_agent_summaries_missing"
    if not isinstance(obj.get("l3_composite_summaries"), list):
        return False, "l3_composite_summaries_missing"
    if not isinstance(obj.get("risk_gate"), Mapping):
        return False, "risk_gate_missing"
    if not isinstance(obj.get("macro_regulator"), Mapping):
        return False, "macro_regulator_missing"
    if _contains_unsafe_report_key(obj):
        return False, "unsafe_report_input_present"
    provenance = obj.get("provenance", {})
    if not isinstance(provenance, Mapping):
        return False, "invalid_provenance"
    if provenance.get("provider_invoked") or provenance.get("external_invoked"):
        return False, "live_invocation_claim_present"
    return True, "ok"


def _summaries_by_dimension(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {dimension: [] for dimension in DIMENSION_GROUPS}
    for item in items:
        dimension = str(item.get("dimension") or "")
        if dimension in result:
            result[dimension].append(item)
    return result


def _format_confidence(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "n/a"


def _format_public_detail_value(value: Any, *, limit: int = 160) -> str:
    if isinstance(value, int | float | bool):
        return str(value)
    if isinstance(value, Mapping | list):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value or "")
    return _safe_public_text(text, limit=limit)


def _format_public_detail_mapping(
    value: Any,
    *,
    limit: int = 5,
    value_limit: int = 80,
) -> str:
    if not isinstance(value, Mapping):
        return ""
    parts: list[str] = []
    for key, raw in list(value.items())[:limit]:
        key_text = _safe_public_text(key, limit=40)
        value_text = _format_public_detail_value(raw, limit=value_limit)
        if key_text and value_text:
            parts.append(f"{key_text}={value_text}")
    return "；".join(parts)


def _format_driver_details(value: Any, *, limit: int = 3) -> str:
    if not isinstance(value, list):
        return ""
    parts: list[str] = []
    for raw in value[:limit]:
        if isinstance(raw, Mapping):
            name = _safe_public_text(raw.get("name"), limit=40)
            driver_value = _format_public_detail_value(raw.get("value"), limit=120)
            if name and driver_value:
                parts.append(f"{name}={driver_value}")
        else:
            text = _format_public_detail_value(raw, limit=120)
            if text:
                parts.append(text)
    return "；".join(parts)


def _format_evidence_items(value: Any, *, limit: int = 3) -> str:
    if not isinstance(value, list):
        return ""
    facts: list[str] = []
    for raw in value[:limit]:
        if not isinstance(raw, Mapping):
            continue
        fact = _safe_public_text(raw.get("fact"), limit=180)
        source = _safe_public_text(raw.get("source"), limit=60)
        data_as_of = _safe_public_text(raw.get("data_as_of"), limit=40)
        if not fact:
            continue
        suffix_parts = []
        if source:
            suffix_parts.append(source)
        if data_as_of:
            suffix_parts.append(data_as_of)
        suffix = f"（{', '.join(suffix_parts)}）" if suffix_parts else ""
        facts.append(f"{fact}{suffix}")
    return "；".join(facts)


def _format_research_points(value: Any, *, limit: int = 3) -> str:
    if not isinstance(value, list):
        return ""
    points: list[str] = []
    for raw in value[:limit]:
        if not isinstance(raw, Mapping):
            continue
        fragments: list[str] = []
        claim = _safe_public_text(raw.get("claim"), limit=180)
        support = _safe_public_text(raw.get("support"), limit=220)
        interpretation = _safe_public_text(raw.get("interpretation"), limit=220)
        decision_implication = _safe_public_text(raw.get("decision_implication"), limit=220)
        caveat = _safe_public_text(raw.get("caveat"), limit=220)
        if claim:
            fragments.append(f"判断：{claim}")
        if support:
            fragments.append(f"依据：{support}")
        if interpretation:
            fragments.append(f"解释：{interpretation}")
        if decision_implication:
            fragments.append(f"含义：{decision_implication}")
        if caveat:
            fragments.append(f"边界：{caveat}")
        if fragments:
            points.append("；".join(fragments))
    return " | ".join(points)


def _format_business_context(item: Mapping[str, Any]) -> str:
    parts: list[str] = []
    research_text = _format_research_points(item.get("research_points"), limit=3)
    if research_text:
        parts.append(f"研究判断：{research_text}")
    evidence_text = _format_evidence_items(item.get("evidence_items"), limit=3)
    if evidence_text:
        parts.append(f"关键证据：{evidence_text}")
    metrics_text = _format_public_detail_mapping(item.get("domain_metrics"), limit=5)
    if metrics_text:
        parts.append(f"核心指标：{metrics_text}")
    drivers_text = _format_driver_details(item.get("drivers"), limit=3)
    if drivers_text:
        parts.append(f"驱动因素：{drivers_text}")
    quality_text = _format_public_detail_mapping(
        item.get("data_quality"),
        limit=5,
        value_limit=60,
    )
    if quality_text:
        parts.append(f"数据质量：{quality_text}")
    return " ".join(parts)


def _format_l2_summary_line(item: Mapping[str, Any]) -> str:
    display_name = _safe_public_text(item.get("display_name"), limit=80)
    stance = _safe_public_text(item.get("stance") or "not_evaluated", limit=80)
    confidence = _format_confidence(item.get("confidence"))
    summary = _safe_public_text(item.get("summary"), limit=140)
    detail_notes = item.get("detail_notes")
    note_text = ""
    if isinstance(detail_notes, list) and detail_notes:
        notes = [
            _safe_public_text(note, limit=80)
            for note in detail_notes[:3]
            if _safe_public_text(note, limit=80)
        ]
        if notes:
            note_text = f" 证据质量：{'；'.join(notes)}。"
    business_context = _format_business_context(item)
    business_text = f" {business_context}" if business_context else ""
    return f"- {display_name}：信号 {stance}，置信度 {confidence}。{summary}{note_text}{business_text}"


def _format_l3_member_preview(value: Any, *, limit: int = 4) -> str:
    if not isinstance(value, list):
        return ""
    parts: list[str] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        status = _safe_public_text(raw.get("status"), limit=40).lower()
        if status in {
            "error",
            "failed",
            "missing",
            "not_available",
            "pending",
            "pending_implementation",
            "skipped",
            "unavailable",
        }:
            continue
        if "confidence" in raw and _safe_public_float(raw.get("confidence")) <= 0.0:
            continue
        if "weight" in raw and _safe_public_float(raw.get("weight")) <= 0.0:
            continue
        name = _safe_public_text(raw.get("display_name") or raw.get("agent_id"), limit=60)
        if not name:
            continue
        fragments = [name]
        if "weight" in raw and raw.get("weight") is not None:
            weight = _safe_public_float(raw.get("weight"))
            fragments.append(f"w={weight}")
        stance = _safe_public_text(raw.get("stance"), limit=50)
        if "risk_score" in raw and raw.get("risk_score") is not None:
            risk_score = _safe_public_float(raw.get("risk_score"))
            fragments.append(f"risk={risk_score}")
        elif stance:
            fragments.append(f"stance={stance}")
        if "confidence" in raw and raw.get("confidence") is not None:
            confidence = _safe_public_float(raw.get("confidence"))
            fragments.append(f"conf={confidence}")
        status = _safe_public_text(raw.get("status"), limit=40)
        if status:
            fragments.append(f"status={status}")
        if len(fragments) > 1:
            parts.append(f"{fragments[0]}({','.join(fragments[1:])})")
        else:
            parts.append(fragments[0])
        if len(parts) >= limit:
            break
    return "；".join(parts)


def _format_l3_summary_line(item: Mapping[str, Any]) -> str:
    display_name = _safe_public_text(item.get("display_name"), limit=80)
    dimension = _safe_public_text(item.get("dimension"), limit=40)
    confidence = _format_confidence(item.get("confidence"))
    detail_notes = item.get("detail_notes")
    note_text = ""
    if isinstance(detail_notes, list) and detail_notes:
        notes = [
            _safe_public_text(note, limit=80)
            for note in detail_notes[:2]
            if _safe_public_text(note, limit=80)
        ]
        if notes:
            note_text = f" 证据质量：{'；'.join(notes)}。"
    members = item.get("members", [])
    member_count = len(members) if isinstance(members, list) else 0
    member_text = _format_l3_member_preview(members)
    member_context = f" 主要成员：{member_text}。" if member_text else ""
    if dimension == "risk":
        business_context = _format_business_context(item)
        business_text = f" {business_context}" if business_context else ""
        return (
            f"- {display_name}：风险门 {item.get('gate', 'not_evaluated')}，"
            f"风险分 {_format_confidence(item.get('risk_score'))}，置信度 {confidence}。"
            f"{note_text}{member_context}{business_text}"
        )
    if dimension == "macro":
        weights = item.get("dimension_weights", {})
        weight_text = ""
        if isinstance(weights, Mapping):
            weight_text = "，".join(
                f"{key}={value}" for key, value in weights.items() if key in {"value", "market"}
            )
        business_context = _format_business_context(item)
        business_text = f" {business_context}" if business_context else ""
        return (
            f"- {display_name}：宏观状态 {item.get('regime', 'not_evaluated')}，"
            f"value/market 权重 {weight_text or 'n/a'}，置信度 {confidence}。"
            f"{note_text}{member_context}{business_text}"
        )
    stance = _safe_public_text(item.get("stance") or "not_evaluated", limit=80)
    business_context = _format_business_context(item)
    business_text = f" {business_context}" if business_context else ""
    return (
        f"- {display_name}：综合信号 {stance}，成员 {member_count} 个，"
        f"置信度 {confidence}。{note_text}{member_context}{business_text}"
    )


def _format_agent_task_summary_line(item: Mapping[str, Any]) -> str:
    display_name = _safe_public_text(item.get("display_name"), limit=80)
    required_schema = _safe_public_text(item.get("required_output_schema"), limit=80)
    instruction = _safe_public_text(item.get("task_instruction"), limit=180)
    upstream = item.get("upstream_agent_ids", [])
    upstream_count = len(upstream) if isinstance(upstream, list) else 0
    return (
        f"- {display_name}：要求输出 {required_schema}；"
        f"上游输入 {upstream_count} 个；任务：{instruction}"
    )


def _count_task_layers(task_items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"L2": 0, "L3": 0, "L4": 0}
    for item in task_items:
        layer = _safe_public_text(item.get("layer"), limit=20)
        if layer in counts:
            counts[layer] += 1
    return counts


def _format_agent_task_overview(task_items: list[dict[str, Any]]) -> str:
    counts = _count_task_layers(task_items)
    total = counts["L2"] + counts["L3"] + counts["L4"]
    if total <= 0:
        return "本轮没有可展示的 agent_task_v1 任务摘要。"
    return (
        "本轮生成 agent_task_v1："
        f"L2 {counts['L2']} 个，L3 {counts['L3']} 个，L4 {counts['L4']} 个。"
        "每个任务携带 target、as_of、required_output_schema 和 public-safe upstream 摘要；"
        "完整任务保留在 report_input_bundle/workflow trace 中，fallback 报告不逐条展开模板化任务指令。"
    )


def _has_report_material(item: Mapping[str, Any]) -> bool:
    for key in ("research_points", "evidence_items", "domain_metrics", "drivers"):
        value = item.get(key)
        if isinstance(value, Mapping) and value:
            return True
        if isinstance(value, list) and value:
            return True
    if _safe_public_float(item.get("evidence_count")) > 0:
        return True
    return _safe_public_text(item.get("status"), limit=40) == "error"


def _placeholder_l2_notice(
    *,
    visible_items: list[dict[str, Any]],
    all_items: list[dict[str, Any]],
) -> str:
    hidden = [item for item in all_items if item not in visible_items]
    if not hidden:
        return ""
    by_dimension: dict[str, int] = {}
    for item in hidden:
        dimension = _safe_public_text(item.get("dimension") or "unknown", limit=40)
        by_dimension[dimension] = by_dimension.get(dimension, 0) + 1
    labels = {
        "value": "估值维",
        "market": "市场维",
        "risk": "风险维",
        "macro": "宏观维",
        "unknown": "未知维",
    }
    parts = [
        f"{labels.get(dimension, dimension)}{count} 个"
        for dimension, count in by_dimension.items()
        if count > 0
    ]
    return (
        f"未展开无可读证据的 L2：{len(hidden)} 个"
        f"（{'，'.join(parts)}）。"
        "这些 agent 仍保留在 report_input_bundle 中，但不在最终报告中伪装成真实研究材料。"
    )


def _report_bundle_sections(report_input_bundle: Mapping[str, Any]) -> list[dict[str, str]]:
    task_items = [
        cast(dict[str, Any], item)
        for item in report_input_bundle.get("agent_task_summaries", [])
        if isinstance(item, Mapping)
    ]
    l2_items = [
        cast(dict[str, Any], item)
        for item in report_input_bundle.get("l2_agent_summaries", [])
        if isinstance(item, Mapping)
    ]
    l3_items = [
        cast(dict[str, Any], item)
        for item in report_input_bundle.get("l3_composite_summaries", [])
        if isinstance(item, Mapping)
    ]
    evidence_bundle = report_input_bundle.get("agent_evidence_bundle", {})
    if isinstance(evidence_bundle, Mapping):
        l2_detail_items = evidence_bundle.get("l2_agent_outputs")
        if isinstance(l2_detail_items, list):
            l2_items = [
                cast(dict[str, Any], item)
                for item in l2_detail_items
                if isinstance(item, Mapping)
            ]
        l3_detail_items = evidence_bundle.get("l3_composite_outputs")
        if isinstance(l3_detail_items, list):
            l3_items = [
                cast(dict[str, Any], item)
                for item in l3_detail_items
                if isinstance(item, Mapping)
            ]
    quality_summary = (
        evidence_bundle.get("quality_summary", {})
        if isinstance(evidence_bundle, Mapping)
        else {}
    )
    visible_l2_items = [item for item in l2_items if _has_report_material(item)]
    by_dimension = _summaries_by_dimension(visible_l2_items)
    l2_lines: list[str] = []
    for dimension, label in (
        ("value", "估值维"),
        ("market", "市场维"),
        ("risk", "风险维"),
        ("macro", "宏观维"),
    ):
        if not by_dimension[dimension]:
            continue
        l2_lines.append(f"{label}单体智能体：")
        l2_lines.extend(_format_l2_summary_line(item) for item in by_dimension[dimension])
    placeholder_notice = _placeholder_l2_notice(
        visible_items=visible_l2_items,
        all_items=l2_items,
    )
    if placeholder_notice:
        l2_lines.append(placeholder_notice)
    l3_lines = [_format_l3_summary_line(item) for item in l3_items]
    quality_lines: list[str] = []
    if isinstance(quality_summary, Mapping):
        quality_lines.append(
            "L2 完成 {complete}/{total}，partial {partial}，error {error}，无可读证据 {thin}；"
            "L3 输出 {l3_available}/{l3_total}，complete {l3_complete}，partial {l3_partial}，error {l3_error}。".format(
                complete=int(quality_summary.get("l2_complete") or 0),
                total=int(quality_summary.get("l2_total") or 0),
                partial=int(quality_summary.get("l2_partial") or 0),
                error=int(quality_summary.get("l2_error") or 0),
                thin=int(quality_summary.get("l2_without_readable_evidence") or 0),
                l3_available=int(quality_summary.get("l3_available") or 0),
                l3_complete=int(quality_summary.get("l3_complete") or 0),
                l3_partial=int(quality_summary.get("l3_partial") or 0),
                l3_error=int(quality_summary.get("l3_error") or 0),
                l3_total=int(quality_summary.get("l3_total") or 0),
            )
        )
    return [
        {
            "id": "evidence_quality",
            "title": "证据质量诊断",
            "content": "\n".join(quality_lines) or "本轮没有可展示的证据质量统计。",
        },
        {
            "id": "agent_task_orchestration",
            "title": "智能体任务编排(agent_task_v1)",
            "content": _format_agent_task_overview(task_items),
        },
        {
            "id": "l2_agent_evidence",
            "title": "单体智能体输入",
            "content": "\n".join(l2_lines) or "本轮没有可展示的单体智能体结构化输入。",
        },
        {
            "id": "l3_composite_evidence",
            "title": "综合智能体输入",
            "content": "\n".join(l3_lines) or "本轮没有可展示的综合智能体结构化输入。",
        },
    ]


def build_report_result(
    decision_result: Mapping[str, Any],
    *,
    question: str = "",
    report_input_bundle: Mapping[str, Any] | None = None,
) -> ReportResult:
    answer = (
        "已完成本轮研判流程。系统按照固定研判流程组织本轮分析，包括问题理解、"
        "信息整理、并行分析、维度综合与报告生成；可展开流程详情查看过程记录。"
    )
    if question:
        answer = f"{answer}\n\n收到的问题：{question}"
    sections = [
        {
            "id": "runtime_scope",
            "title": "分析框架",
            "content": "系统按照固定研判流程组织本轮分析。",
        },
        {
            "id": "implementation_status",
            "title": "流程记录",
            "content": "如需查看过程，可展开流程详情。",
        },
    ]
    evidence_cards = [
        {
            "title": "分析框架",
            "note": "系统按照固定研判流程组织本轮分析，包括问题理解、信息整理、并行分析、维度综合与报告生成。",
        },
        {
            "title": "用户问题",
            "note": "围绕你提出的问题进行结构化梳理。",
        },
        {
            "title": "流程记录",
            "note": "如需查看过程，可展开流程详情。",
        },
    ]
    if isinstance(report_input_bundle, Mapping):
        valid_bundle, _bundle_reason = validate_report_input_bundle(report_input_bundle)
        if valid_bundle:
            detail_sections = _report_bundle_sections(report_input_bundle)
            sections.extend(detail_sections)
            detail_text = "\n\n".join(
                f"{section['title']}：\n{section['content']}"
                for section in detail_sections
            )
            answer = (
                f"{answer}\n\n报告生成输入摘要：\n{detail_text}\n\n"
                "最终结论：以上单体智能体和综合智能体输入用于解释本轮固定 DAG 演示报告；"
                "结论仍需结合业务 owner 复核。"
            )
            evidence_cards.append(
                {
                    "title": "报告生成输入",
                    "note": (
                        f"纳入 {len(report_input_bundle.get('l2_agent_summaries', []) or [])} 个单体智能体摘要和 "
                        f"{len(report_input_bundle.get('l3_composite_summaries', []) or [])} 个综合智能体摘要。"
                    ),
                }
            )
    decision = _safe_public_text(decision_result.get("decision"), limit=80)
    if decision and decision != "pending_implementation":
        evidence_cards.append({"title": "决策上下文", "note": f"决策状态：{decision}。"})
    return {
        "schema": REPORT_RESULT_SCHEMA_VERSION,
        "schema_version": REPORT_RESULT_SCHEMA_VERSION,
        "title": "研判流程",
        "answer": answer,
        "status": "pending_implementation",
        "sections": sections,
        "evidence_cards": evidence_cards,
        "limitations": [
            "当前为本地固定流程模式。",
            "高级连接状态可在设置诊断中查看。",
        ],
    }


def validate_report_result(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != REPORT_RESULT_SCHEMA_VERSION:
        return False, "invalid_schema"
    if obj.get("schema_version", REPORT_RESULT_SCHEMA_VERSION) != REPORT_RESULT_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    answer = str(obj.get("answer") or "")
    if not answer:
        return False, "answer_missing"
    if "研判流程" not in answer:
        return False, "reset_scope_missing"
    if not isinstance(obj.get("sections"), list):
        return False, "sections_missing"
    if not isinstance(obj.get("evidence_cards"), list):
        return False, "evidence_cards_missing"
    limitations = obj.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        return False, "limitations_missing"
    forbidden_claims = (
        "provider verified",
        "external service verified",
        "live analysis complete",
        "provider/live ready",
        "外部服务已全部验证",
        "真实业务智能体已全部上线",
    )
    lowered = answer.lower()
    if any(claim in lowered for claim in forbidden_claims):
        return False, "live_claim_present"
    return True, "ok"


def _completed_from_payloads(
    plan: Mapping[str, Any],
    *,
    l2_conclusions: Mapping[str, Any] | None,
    dimension_results: Mapping[str, Any] | None,
    decision_result: Mapping[str, Any] | None,
    report_result: Mapping[str, Any] | None,
) -> list[str]:
    completed: list[str] = ["route_planner"]
    if plan.get("schema") == FIXED_DAG_SCHEMA_VERSION:
        completed.extend(
            step["id"]
            for step in plan.get("steps", [])
            if isinstance(step, Mapping) and step.get("stage") == "evidence"
        )
    if l2_conclusions:
        completed.extend(
            f"l2:{agent_id}"
            for agent_id in L2_CONCLUSION_AGENT_IDS
            if agent_id in l2_conclusions
        )
    if dimension_results:
        completed.extend(
            f"dimension:{dimension}"
            for dimension in DIMENSION_GROUPS
            if dimension in dimension_results
        )
    if decision_result:
        completed.append("decision_synthesizer")
    if report_result:
        completed.append("report_generator")
    return list(dict.fromkeys(completed))


def _completed_from_step_results(step_results: Mapping[str, Any]) -> list[str]:
    completed: list[str] = []
    for step_id, result in step_results.items():
        if not isinstance(result, Mapping):
            continue
        if result.get("status") in EXECUTED_STEP_STATUSES:
            completed.append(str(result.get("step_id") or step_id))
    return list(dict.fromkeys(completed))


def _step_status_from_results(
    step: Mapping[str, Any],
    step_results: Mapping[str, Any] | None,
    completed_steps: list[str],
) -> str:
    step_id = str(step.get("id") or "")
    if isinstance(step_results, Mapping):
        result = step_results.get(step_id)
        if isinstance(result, Mapping) and result.get("status"):
            return str(result["status"])
    if step_id in completed_steps:
        return "complete"
    return str(step.get("status") or "pending_implementation")


def build_workflow_snapshot_v2(
    *,
    plan: Mapping[str, Any],
    l2_conclusions: Mapping[str, Any] | None = None,
    dimension_results: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
    report_result: Mapping[str, Any] | None = None,
    dag_execution: Mapping[str, Any] | None = None,
    step_results: Mapping[str, Any] | None = None,
    execution_batches: list[list[str]] | None = None,
    current_stage: FixedDagStage | None = None,
    completed_steps: list[str] | None = None,
) -> dict[str, Any]:
    plan_valid, _plan_reason = validate_fixed_dag_plan(plan)
    selected_plan_valid, _selected_plan_reason = validate_selected_fixed_dag_plan(plan)
    normalized_plan = (
        cast(FixedDagPlan, plan)
        if plan_valid or selected_plan_valid
        else normalize_fixed_dag_plan(plan)
    )
    dimension_results = dimension_results or {}
    if isinstance(dag_execution, Mapping):
        if step_results is None and isinstance(dag_execution.get("step_results"), Mapping):
            step_results = cast(Mapping[str, Any], dag_execution["step_results"])
        if execution_batches is None and isinstance(dag_execution.get("execution_batches"), list):
            execution_batches = cast(list[list[str]], dag_execution["execution_batches"])
    completed = (
        completed_steps
        or (_completed_from_step_results(step_results) if isinstance(step_results, Mapping) else [])
        or _completed_from_payloads(
            normalized_plan,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            decision_result=decision_result,
            report_result=report_result,
        )
    )
    stage = current_stage or ("report" if report_result else "planning")
    dimension_group_ids = [
        dimension
        for dimension in DIMENSION_GROUPS
        if dimension in normalized_plan.get("dimension_groups", {})
    ]
    return {
        "schema": WORKFLOW_SNAPSHOT_SCHEMA_VERSION,
        "schemaVersion": WORKFLOW_SNAPSHOT_SCHEMA_VERSION,
        "planId": normalized_plan["plan_id"],
        "stages": [
            {
                "key": item["id"],
                "title": item["title"],
                "stepIds": item["step_ids"],
            }
            for item in normalized_plan["stages"]
        ],
        "dagSteps": [
            {
                "id": step["id"],
                "stage": step["stage"],
                "agentId": step.get("agent_id"),
                "dimension": step.get("dimension"),
                "title": step["title"],
                "summary": step["description"],
                "status": _step_status_from_results(step, step_results, completed),
            }
            for step in normalized_plan["steps"]
        ],
        "dimensionGroups": [
            {
                "id": dimension,
                "title": DIMENSION_TITLE_LABELS.get(dimension, f"{dimension} 综合"),
                "stepIds": [f"dimension:{dimension}"],
                "status": dimension_results.get(dimension, {}).get(
                    "status", "pending_implementation"
                )
                if isinstance(dimension_results.get(dimension), Mapping)
                else "pending_implementation",
        "summary": "维度综合结果。",
            }
            for dimension in dimension_group_ids
        ],
        "currentStage": stage,
        "completedSteps": completed,
        "executionBatches": execution_batches or [],
        "stepResults": dict(step_results or {}),
        "provenance": {
            "source": RESET_SOURCE,
            "providerInvoked": bool(
                dag_execution.get("provenance", {}).get("provider_invoked")
            )
            if isinstance(dag_execution, Mapping)
            and isinstance(dag_execution.get("provenance"), Mapping)
            else False,
            "externalInvoked": bool(
                dag_execution.get("provenance", {}).get("external_invoked")
            )
            if isinstance(dag_execution, Mapping)
            and isinstance(dag_execution.get("provenance"), Mapping)
            else False,
            "executionStatus": str(dag_execution.get("status"))
            if isinstance(dag_execution, Mapping) and dag_execution.get("status")
            else "not_started",
            "fallbackUsed": bool(dag_execution.get("fallback_used"))
            if isinstance(dag_execution, Mapping)
            else False,
            "limitations": list(dag_execution.get("limitations", []) or [])
            if isinstance(dag_execution, Mapping)
            else [],
        },
        "finalSource": RESET_SOURCE,
    }


def validate_workflow_snapshot_v2(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != WORKFLOW_SNAPSHOT_SCHEMA_VERSION:
        return False, "invalid_schema"
    if _contains_legacy_key(obj):
        return False, "legacy_public_field_present"
    if obj.get("finalSource") != RESET_SOURCE:
        return False, "invalid_final_source"
    for field in (
        "planId",
        "stages",
        "dagSteps",
        "dimensionGroups",
        "currentStage",
        "completedSteps",
        "provenance",
    ):
        if field not in obj:
            return False, f"missing_{field}"
    provenance = obj.get("provenance", {})
    if not isinstance(provenance, Mapping):
        return False, "invalid_provenance"
    if provenance.get("externalInvoked"):
        return False, "live_invocation_claim_present"
    dag_steps = obj.get("dagSteps")
    completed = obj.get("completedSteps")
    if not isinstance(dag_steps, list) or not isinstance(completed, list):
        return False, "invalid_steps"
    known_step_ids = {
        item.get("id")
        for item in dag_steps
        if isinstance(item, Mapping) and item.get("id")
    }
    if not set(completed) <= known_step_ids:
        return False, "completed_steps_unknown"
    execution_batches = obj.get("executionBatches", [])
    if not isinstance(execution_batches, list):
        return False, "invalid_execution_batches"
    step_results = obj.get("stepResults", {})
    if not isinstance(step_results, Mapping):
        return False, "invalid_step_results"
    return True, "ok"


def build_final_emit_payload(report_result: Mapping[str, Any]) -> dict[str, Any]:
    answer = str(report_result.get("answer") or "").strip()
    if not answer:
        answer = "研判流程已完成，但没有报告正文。"
    return {
        "source": RESET_SOURCE,
        "status": "complete",
        "answer": answer,
        "sections": list(report_result.get("sections", []) or []),
        "evidence_cards": list(report_result.get("evidence_cards", []) or []),
        "limitations": list(report_result.get("limitations", []) or []),
    }


def build_emitted_bundle(report_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "answer": str(report_result.get("answer") or ""),
        "summary_source": RESET_SOURCE,
        "confidence": 0.0,
        "sections": list(report_result.get("sections", []) or []),
        "evidence_cards": list(report_result.get("evidence_cards", []) or []),
        "limitations": list(report_result.get("limitations", []) or []),
        "provider_invoked": False,
        "external_invoked": False,
    }


def build_reset_multi_agent_bundle(
    *,
    fixed_dag_plan: Mapping[str, Any],
    data_bundle: Mapping[str, Any],
    entity_relation_bundle: Mapping[str, Any],
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
    decision_result: Mapping[str, Any],
    report_result: Mapping[str, Any],
    report_input_bundle: Mapping[str, Any] | None = None,
    dag_execution: Mapping[str, Any] | None = None,
    dag_step_results: Mapping[str, Any] | None = None,
    execution_batches: list[list[str]] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "fixed_dag_reset_bundle_v1",
        "fixed_dag_plan": dict(fixed_dag_plan),
        "data_bundle": dict(data_bundle),
        "entity_relation_bundle": dict(entity_relation_bundle),
        "dag_execution": dict(dag_execution or {}),
        "dag_step_results": dict(dag_step_results or {}),
        "execution_batches": list(execution_batches or []),
        "l2_conclusions": dict(l2_conclusions),
        "dimension_results": dict(dimension_results),
        "decision_result": dict(decision_result),
        "report_input_bundle": dict(report_input_bundle or {}),
        "report_result": dict(report_result),
    }


__all__ = sorted(
    name
    for name in globals()
    if not name.startswith("_")
    and name
    not in {
        "Any",
        "Mapping",
        "cast",
        "json",
        "re",
    }
)
