# ruff: noqa: D101, D103
"""Plan, route, selected plan, conclusion, and agent-task builders.
Includes DAG plan construction, route intent, selected-plan compilation,
data/entity bundles, L2 conclusions, and agent tasks.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, cast

from react_agent.fixed_dag.constants import (
    AGENT_DIMENSIONS,
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
    LEGACY_CONTRACT_KEYS,
    LEGACY_DISPATCH_VALUES,
    REPORT_BUNDLE_UNSAFE_KEYS,
    SELECTED_PLAN_FORBIDDEN_KEYS,
    SELECTED_PLAN_PUBLIC_UNSAFE_TEXT_TOKENS,
    _contains_legacy_dispatch_value,
    _contains_legacy_key,
    _contains_public_unsafe_text,
    _contains_selected_plan_forbidden_key,
    _contains_unsafe_report_key,
    _looks_like_legacy_agent_id,
    _safe_public_detail_list,
    _safe_public_detail_mapping,
    _safe_public_detail_value,
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
    DimensionName,
    EntityRelationBundle,
    FixedDagDimension,
    FixedDagPlan,
    FixedDagStage,
    FixedDagStep,
    FixedDagStepStatus,
    ReportInputBundle,
    ReportResult,
    RouteIntent,
    RouteTaskType,
    SelectedFixedDagPlan,
)
from react_agent.fixed_dag.contracts.helpers import (
    _as_of,
    _data_as_of_for,
    _data_not_after,
    _status_for_expected,
)
# Lazy imports for cross-module references (avoid circular imports)
import importlib
def _report_l2_agent_summary(agent_id, result):
    return importlib.import_module(
        'react_agent.fixed_dag.contracts.report'
    )._l2_agent_summary(agent_id, result)
def _report_l3_composite_summary(result):
    return importlib.import_module(
        'react_agent.fixed_dag.contracts.report'
    )._l3_composite_summary(result)
def _report_safe_evidence_detail_items(value, limit=8):
    return importlib.import_module(
        'react_agent.fixed_dag.contracts.report'
    )._safe_evidence_detail_items(value, limit=limit)
def _report_provenance_notes(provenance):
    return importlib.import_module(
        'react_agent.fixed_dag.contracts.report'
    )._provenance_notes(provenance)



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


_ROUTE_INTENT_UNSAFE_KEYS = {
    ".env",
    "chain-of-thought",
    "chain_of_thought",
    "endpoint",
    "endpoint_url",
    "env",
    "environment",
    "external_payload",
    "external_response",
    "provider_payload",
    "provider_response",
    "raw_provider_response",
    "raw_response",
    "raw_responses",
    "secret",
    "secrets",
}
_ROUTE_INTENT_UNSAFE_TEXT_TOKENS = (
    "/v1/agent/compute",
    "/v1/agent/invoke",
    ".env",
    "chain-of-thought",
    "chain_of_thought",
    "endpoint",
    "raw provider",
    "raw_provider_response",
    "raw_response",
    "secret",
)


def _contains_route_intent_unsafe_material(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key or "").strip()
            if key_text in _ROUTE_INTENT_UNSAFE_KEYS:
                return True
            if _contains_route_intent_unsafe_material(item):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_route_intent_unsafe_material(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return any(token in lowered for token in _ROUTE_INTENT_UNSAFE_TEXT_TOKENS)
    return False


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


def build_default_dimension_route_intent(
    question: str,
    *,
    task_type: RouteTaskType = "general",
) -> RouteIntent:
    """Build a provider-free dimension-only intent for the internal router seam."""
    inferred_task_type = _infer_route_task_type(question, str(task_type or "general"))
    if inferred_task_type in INVESTMENT_JUDGMENT_TASK_TYPES:
        selected_dimensions: list[DimensionName] = ["value", "risk"]
    elif inferred_task_type == "macro":
        selected_dimensions = ["macro"]
    elif inferred_task_type == "sentiment":
        selected_dimensions = ["market"]
    else:
        selected_dimensions = ["value"]

    intent = build_route_intent(
        task_type=inferred_task_type,
        targets=[],
        selected_dimensions=selected_dimensions,
        selected_agents=[],
        route_confidence=0.62,
        fallback_reason="",
        provenance={
            "source": "deterministic_dimension_route_planner",
            "planner": "m1a_provider_free_dimension_route_intent",
            "route_granularity": "dimension",
            "dimension_only": True,
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
        fallback_reason=f"planner_dimension_default_failed:{reason}",
        provenance={
            "source": "deterministic_dimension_route_planner",
            "planner": "m1a_provider_free_dimension_route_intent",
            "route_granularity": "dimension",
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
    provenance = intent.get("provenance", {})
    if not isinstance(provenance, Mapping):
        return False, "invalid_provenance"
    dimension_only = (
        bool(selected_dimensions)
        and not selected_agents
        and provenance.get("route_granularity") == "dimension"
    )
    if needs_clarification and not clarification_question:
        return False, "clarification_question_missing"
    if not selected_agents and not needs_clarification and not fallback_reason and not dimension_only:
        return False, "fallback_reason_missing"
    if fallback_reason and _contains_public_unsafe_text(fallback_reason):
        return False, "fallback_reason_not_public_safe"
    if _contains_route_intent_unsafe_material(
        {key: value for key, value in intent.items() if key != "fallback_reason"}
    ):
        return False, "route_intent_unsafe_material_present"
    task_type = str(intent.get("task_type") or "")
    if not needs_clarification and task_type in INVESTMENT_JUDGMENT_TASK_TYPES:
        if "risk" not in selected_dimension_set:
            return False, "risk_dimension_required"
        if selected_agents:
            if not any(agent_id in RISK_AGENT_IDS for agent_id in selected_agents):
                return False, "risk_agent_required"
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


def _effective_l2_agents_by_dimension(intent: Mapping[str, Any]) -> dict[str, list[str]]:
    selected_dimensions = _unique_known_dimensions(cast(list[str] | None, intent.get("selected_dimensions")))
    selected_agents = _unique_known_agents(cast(list[str] | None, intent.get("selected_agents")))
    explicit_l2_by_dimension = _selected_l2_agents_by_dimension(selected_agents)
    effective: dict[str, list[str]] = {}
    for dimension in selected_dimensions:
        explicit_l2_agents = explicit_l2_by_dimension[dimension]
        effective[dimension] = (
            list(explicit_l2_agents)
            if explicit_l2_agents
            else list(DIMENSION_GROUPS[dimension])
        )
    return effective


def _compiled_agent_ids_for_intent(intent: Mapping[str, Any]) -> list[str]:
    selected_dimensions = _unique_known_dimensions(cast(list[str] | None, intent.get("selected_dimensions")))
    selected_agents = _unique_known_agents(cast(list[str] | None, intent.get("selected_agents")))
    if not selected_dimensions:
        raise ValueError("selected_dimensions_missing")
    l2_by_dimension = _effective_l2_agents_by_dimension(intent)

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
    provenance = intent.get("provenance", {})
    provenance = provenance if isinstance(provenance, Mapping) else {}
    dimension_only = provenance.get("route_granularity") == "dimension" and not selected_agents
    if (
        dimension_only
        or task_type in INVESTMENT_JUDGMENT_TASK_TYPES
        or "decision_synthesizer" in selected_agents
    ):
        compiled.add("decision_synthesizer")

    return [agent_id for agent_id in RESET_RUNTIME_AGENT_IDS if agent_id in compiled]


def _compiled_steps_for_intent(
    intent: Mapping[str, Any],
    compiled_agent_ids: list[str],
) -> list[FixedDagStep]:
    selected_dimensions = _unique_known_dimensions(cast(list[str] | None, intent.get("selected_dimensions")))
    l2_by_dimension = _effective_l2_agents_by_dimension(intent)
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
    route_intent_provenance = route_intent.get("provenance", {})
    route_intent_provenance = (
        route_intent_provenance if isinstance(route_intent_provenance, Mapping) else {}
    )
    route_granularity = str(route_intent_provenance.get("route_granularity") or "").strip()
    expanded_from_dimensions = not _unique_known_agents(
        cast(list[str] | None, route_intent.get("selected_agents"))
    )
    compiler_provenance: dict[str, Any] = {
        "source": "deterministic_selected_dag_compiler",
        "compiler": "r8_2_deterministic_selected_dag_compiler",
        "provider_invoked": False,
        "external_invoked": False,
    }
    if route_granularity:
        compiler_provenance.update(
            {
                "route_granularity": route_granularity,
                "expanded_from_selected_dimensions": expanded_from_dimensions,
                "expanded_dimensions": list(route_intent.get("selected_dimensions", []) or []),
                "expanded_agent_count": len(compiled_agent_ids),
            }
        )
    plan = build_selected_fixed_dag_plan(
        route_intent=route_intent,
        user_text=user_text,
        as_of=as_of,
        selected_steps=selected_steps,
        fallback_reason=str(route_intent.get("fallback_reason") or "fallback to full DAG"),
        provenance=compiler_provenance,
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
    item = _report_l2_agent_summary(agent_id, result)
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
    evidence_items = _report_safe_evidence_detail_items(result.get("evidence"), limit=4)
    if evidence_items:
        upstream["evidence_items"] = evidence_items
    provenance_notes = _report_provenance_notes(result.get("provenance"))
    for key in ("domain_metrics", "drivers", "research_points", "data_quality"):
        if key in provenance_notes:
            upstream[key] = provenance_notes[key]
    return upstream


def _l3_task_upstream_result(result: Mapping[str, Any]) -> dict[str, Any]:
    item = _report_l3_composite_summary(result)
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
