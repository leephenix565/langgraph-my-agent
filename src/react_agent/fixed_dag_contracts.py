# ruff: noqa: D101, D103
"""Deterministic fixed-DAG reset contracts and function seams.

Phase R3 keeps the active runtime provider-free and external-free while making
the reset skeleton contracts explicit, validated, execution-aware, and reusable
by graph nodes and public workflow mapping.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, NotRequired, TypedDict, cast

from react_agent.fixed_dag_catalog import (
    fixed_dag_agent_ids,
    fixed_dag_agents_by_dimension,
    fixed_dag_agents_by_layer,
    load_fixed_dag_catalog,
    validate_fixed_dag_catalog,
)

FIXED_DAG_SCHEMA_VERSION = "fixed_dag_plan_v1"
ROUTE_INTENT_SCHEMA_VERSION = "route_intent_v1"
SELECTED_FIXED_DAG_SCHEMA_VERSION = "selected_fixed_dag_plan_v1"
DATA_BUNDLE_SCHEMA_VERSION = "data_bundle_v1"
ENTITY_RELATION_BUNDLE_SCHEMA_VERSION = "entity_relation_bundle_v1"
CONCLUSION_OBJECT_SCHEMA_VERSION = "conclusion_object_v1"
DIMENSION_COMPOSITE_SCHEMA_VERSION = "dimension_composite_result_v1"
DECISION_RESULT_SCHEMA_VERSION = "decision_result_v1"
REPORT_RESULT_SCHEMA_VERSION = "report_result_v1"
WORKFLOW_SNAPSHOT_SCHEMA_VERSION = "workflow_snapshot_v2"
RESET_SOURCE = "reset_skeleton"
DEFAULT_AS_OF = "not_available"

FixedDagStage = Literal[
    "planning",
    "evidence",
    "l2_analysis",
    "dimension_composite",
    "decision",
    "report",
]
ConclusionStatus = Literal["pending_implementation", "partial", "complete", "error"]
DimensionName = Literal["value", "market", "risk", "macro"]
FixedDagDimension = Literal["l1", "value", "market", "risk", "macro", "l4"]
RouteTaskType = Literal["single", "compare", "screen", "macro", "sentiment", "industry", "event", "general"]
FixedDagStepStatus = Literal[
    "complete",
    "pending_implementation",
    "skipped",
    "blocked",
    "failed",
]

FIXED_DAG_STAGE_ORDER: tuple[FixedDagStage, ...] = (
    "planning",
    "evidence",
    "l2_analysis",
    "dimension_composite",
    "decision",
    "report",
)

_CATALOG_VALID, _CATALOG_VALIDATION_REASON = validate_fixed_dag_catalog(load_fixed_dag_catalog())
if not _CATALOG_VALID:
    raise RuntimeError(f"Invalid fixed DAG catalog: {_CATALOG_VALIDATION_REASON}")

_AGENTS_BY_LAYER = fixed_dag_agents_by_layer()
_AGENTS_BY_DIMENSION = fixed_dag_agents_by_dimension()

L1_AGENT_IDS: tuple[str, ...] = _AGENTS_BY_LAYER["L1"]
VALUE_AGENT_IDS: tuple[str, ...] = _AGENTS_BY_DIMENSION["value"]
MARKET_AGENT_IDS: tuple[str, ...] = _AGENTS_BY_DIMENSION["market"]
RISK_AGENT_IDS: tuple[str, ...] = _AGENTS_BY_DIMENSION["risk"]
MACRO_AGENT_IDS: tuple[str, ...] = _AGENTS_BY_DIMENSION["macro"]
L2_CONCLUSION_AGENT_IDS: tuple[str, ...] = (
    *VALUE_AGENT_IDS,
    *MARKET_AGENT_IDS,
    *RISK_AGENT_IDS,
    *MACRO_AGENT_IDS,
)
L3_COMPOSITE_AGENT_IDS: tuple[str, ...] = _AGENTS_BY_LAYER["L3"]
L4_AGENT_IDS: tuple[str, ...] = _AGENTS_BY_LAYER["L4"]
RESET_RUNTIME_AGENT_IDS: tuple[str, ...] = fixed_dag_agent_ids()

DIMENSION_GROUPS: dict[str, tuple[str, ...]] = {
    "value": VALUE_AGENT_IDS,
    "market": MARKET_AGENT_IDS,
    "risk": RISK_AGENT_IDS,
    "macro": MACRO_AGENT_IDS,
}
ROUTE_TASK_TYPES: tuple[RouteTaskType, ...] = (
    "single",
    "compare",
    "screen",
    "macro",
    "sentiment",
    "industry",
    "event",
    "general",
)
INVESTMENT_JUDGMENT_TASK_TYPES = {"single", "compare", "screen", "industry", "event"}
SELECTED_PLAN_FALLBACK_TARGETS = {"full_dag", "none"}
DIMENSION_COMPOSITE_AGENT_IDS: dict[str, str] = {
    "value": "value_composite",
    "market": "market_composite",
    "risk": "risk_composite",
    "macro": "macro_composite",
}
AGENT_DIMENSIONS: dict[str, str] = {
    **{agent_id: "value" for agent_id in VALUE_AGENT_IDS},
    **{agent_id: "market" for agent_id in MARKET_AGENT_IDS},
    **{agent_id: "risk" for agent_id in RISK_AGENT_IDS},
    **{agent_id: "macro" for agent_id in MACRO_AGENT_IDS},
}
SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES: tuple[str, ...] = ("market_composite",)
LEGACY_CONTRACT_KEYS = {
    "mode",
    "layerMode",
    "layer_mode",
    "layerPlan",
    "layer_plan",
    "fusionSteps",
    "fusion_verdict",
    "baseline_bundle",
}
SELECTED_PLAN_FORBIDDEN_KEYS = {
    "runtime_kind",
    "implementation_status",
    "binding_source",
    "legacy_agent_id",
    "external_agent_id",
    "invoke_enabled",
    "live_verified",
    "env_var",
    "default_url",
    "endpoint",
    "provider_response",
    "external_response",
}
SELECTED_PLAN_PUBLIC_UNSAFE_TEXT_TOKENS = (
    "provider",
    "external endpoint",
    "env_var",
    "secret",
    "chain-of-thought",
    "pending_implementation",
    "placeholder",
    "runtime binding",
    "default_url",
    "traceback",
)
LEGACY_DISPATCH_VALUES = {"Star", "Chain", "Debate", "Tree"}
EXECUTED_STEP_STATUSES = {"complete", "pending_implementation"}

STAGE_TITLE_LABELS: dict[str, str] = {
    "planning": "规划",
    "evidence": "证据接入",
    "l2_analysis": "L2 分析",
    "dimension_composite": "维度综合",
    "decision": "决策",
    "report": "报告",
}

AGENT_TITLE_LABELS: dict[str, str] = {
    "route_planner": "路径规划器",
    "financial_data_service": "金融数据服务",
    "entity_relation_extractor": "实体关系抽取器",
    "value_traditional_valuation": "传统企业估值",
    "value_ml_valuation": "机器学习企业估值",
    "value_meta_valuation": "元学习企业估值",
    "value_research_synthesis": "研报观点综合",
    "market_stock_technical": "个股技术分析",
    "market_fund_manager_behavior": "基金经理行为分析",
    "market_ipo_investor_behavior": "IPO 投资者行为分析",
    "market_capital_flow_chip": "资金流与筹码分析",
    "sentiment_company_radar": "企业舆情雷达",
    "risk_crash": "股价崩盘风险",
    "risk_financial_fraud": "财务欺诈风险",
    "risk_identification": "风险识别",
    "risk_compliance_review": "公告合规审查",
    "macro_analysis": "宏观分析",
    "macro_commodity_pricing": "商品定价分析",
    "macro_index_valuation": "股票指数估值",
    "macro_sentiment": "宏观情绪感知",
    "macro_industry_hotspot": "行业热点洞察",
    "value_composite": "价值综合",
    "market_composite": "市场综合",
    "risk_composite": "风险综合",
    "macro_composite": "宏观综合",
    "decision_synthesizer": "决策综合器",
    "report_generator": "报告生成器",
}

DIMENSION_TITLE_LABELS: dict[str, str] = {
    "value": "价值综合",
    "market": "市场综合",
    "risk": "风险综合",
    "macro": "宏观综合",
}


class FixedDagStep(TypedDict):
    id: str
    stage: FixedDagStage
    title: str
    description: str
    agent_id: NotRequired[str]
    target_ids: NotRequired[list[str]]
    dimension: NotRequired[str]
    depends_on: NotRequired[list[str]]
    status: str


class FixedDagPlan(TypedDict):
    schema: str
    schema_version: str
    plan_id: str
    user_text: str
    as_of: str
    stages: list[dict[str, Any]]
    steps: list[FixedDagStep]
    dag_steps: list[FixedDagStep]
    target_agent_ids: list[str]
    target: list[str]
    dimension_groups: dict[str, list[str]]
    provenance: dict[str, Any]


class RouteIntent(TypedDict):
    schema: str
    schema_version: str
    task_type: RouteTaskType
    targets: list[str]
    selected_dimensions: list[DimensionName]
    selected_agents: list[str]
    task_brief_by_agent: dict[str, str]
    route_confidence: float
    needs_clarification: bool
    clarification_question: str
    fallback_reason: str
    provenance: dict[str, Any]


class SelectedFixedDagPlan(FixedDagPlan):
    selected_dimensions: list[DimensionName]
    selected_agents: list[str]
    omitted_dimensions: list[DimensionName]
    omitted_agents: list[str]
    route_intent: RouteIntent
    fallback_to: str
    fallback_reason: str


class EntityRelationBundle(TypedDict):
    schema: str
    schema_version: str
    status: ConclusionStatus
    as_of: str
    data_as_of: str
    entities: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    notes: list[str]


class DataBundle(TypedDict):
    schema: str
    schema_version: str
    status: ConclusionStatus
    as_of: str
    data_as_of: str
    sources: list[str]
    notes: list[str]


class ConclusionObject(TypedDict):
    schema: str
    schema_version: str
    agent_id: str
    dimension: str
    stance: str
    confidence: float
    status: ConclusionStatus
    evidence: list[dict[str, Any]]
    as_of: str
    data_as_of: str
    event_flags: NotRequired[list[str]]
    output_routes: NotRequired[list[str]]
    provenance: dict[str, Any]


class DimensionCompositeResult(TypedDict):
    schema: str
    schema_version: str
    agent_id: str
    dimension: str
    stance: str
    confidence: float
    status: ConclusionStatus
    contributing_agents: list[str]
    evidence_refs: list[str]
    as_of: str
    data_as_of: str
    vote_type: NotRequired[str]
    gate: NotRequired[str]
    veto: NotRequired[bool]
    penalty: NotRequired[float]
    risk_score: NotRequired[float]
    regime: NotRequired[str]
    dimension_weights: NotRequired[dict[str, float]]
    risk_sensitivity: NotRequired[str]


class DecisionResult(TypedDict):
    schema: str
    schema_version: str
    decision: str
    score: float
    target_price_range: dict[str, float | None]
    dimension_views: dict[str, dict[str, Any]]
    reasoning_trace: list[dict[str, Any]]
    confidence: float
    status: ConclusionStatus
    as_of: str


class ReportResult(TypedDict):
    schema: str
    schema_version: str
    title: str
    answer: str
    status: ConclusionStatus
    sections: list[dict[str, Any]]
    evidence_cards: list[dict[str, Any]]
    limitations: list[str]


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


def _contains_legacy_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in LEGACY_CONTRACT_KEYS or _contains_legacy_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_legacy_key(item) for item in value)
    return False


def _contains_selected_plan_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in SELECTED_PLAN_FORBIDDEN_KEYS or _contains_selected_plan_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_selected_plan_forbidden_key(item) for item in value)
    return False


def _contains_legacy_dispatch_value(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_legacy_dispatch_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_legacy_dispatch_value(item) for item in value)
    return isinstance(value, str) and value.strip() in LEGACY_DISPATCH_VALUES


def _contains_public_unsafe_text(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(token in lowered for token in SELECTED_PLAN_PUBLIC_UNSAFE_TEXT_TOKENS)


def _looks_like_legacy_agent_id(agent_id: str) -> bool:
    return agent_id.startswith("a") and len(agent_id) >= 3 and agent_id[1:3].isdigit()


def _status_for_expected(
    expected_agent_ids: tuple[str, ...],
    conclusions: Mapping[str, Any],
) -> ConclusionStatus:
    present = [agent_id for agent_id in expected_agent_ids if agent_id in conclusions]
    if not present:
        return "pending_implementation"
    if len(present) < len(expected_agent_ids):
        return "partial"
    if any(
        isinstance(conclusions.get(agent_id), Mapping)
        and conclusions[agent_id].get("status") == "error"
        for agent_id in present
    ):
        return "partial"
    return "pending_implementation"


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
    if isinstance(provenance, Mapping) and (
        provenance.get("provider_invoked") or provenance.get("external_invoked")
    ):
        return False, "live_invocation_claim_present"
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
    return {
        agent_id: build_pending_conclusion(
            agent_id,
            AGENT_DIMENSIONS[agent_id],
            as_of=normalized_as_of,
            reason="业务智能体实现仍处于 R3 阶段待完成状态。",
        )
        for agent_id in L2_CONCLUSION_AGENT_IDS
    }


def _build_dimension_composite(
    dimension: DimensionName,
    expected_agent_ids: tuple[str, ...],
    conclusions: Mapping[str, dict[str, Any]],
    *,
    as_of: str,
) -> DimensionCompositeResult:
    result: DimensionCompositeResult = {
        "schema": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "schema_version": DIMENSION_COMPOSITE_SCHEMA_VERSION,
        "agent_id": DIMENSION_COMPOSITE_AGENT_IDS[dimension],
        "dimension": dimension,
        "stance": "not_evaluated",
        "confidence": 0.0,
        "status": _status_for_expected(expected_agent_ids, conclusions),
        "contributing_agents": list(expected_agent_ids),
        "evidence_refs": [],
        "as_of": as_of,
        "data_as_of": _data_as_of_for(as_of),
    }
    if dimension in {"value", "market"}:
        result["vote_type"] = "direction_vote_placeholder"
    if dimension == "risk":
        result.update(
            {
                "gate": "not_evaluated",
                "veto": False,
                "penalty": 0.0,
                "risk_score": 0.0,
            }
        )
    if dimension == "macro":
        result.update(
            {
                "regime": "not_evaluated",
                "dimension_weights": {
                    "market": 0.25,
                    "value": 0.35,
                    "risk": 0.25,
                    "macro": 0.15,
                },
                "risk_sensitivity": "not_evaluated",
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
    if list(obj.get("contributing_agents", [])) != list(DIMENSION_GROUPS[dimension]):
        return False, "contributing_agents_mismatch"
    if dimension == "risk" and "sentiment_company_radar" in obj.get("contributing_agents", []):
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
    return True, "ok"


def build_dimension_results(
    l2_conclusions: Mapping[str, dict[str, Any]],
    *,
    as_of: str | None = None,
) -> dict[str, DimensionCompositeResult]:
    normalized_as_of = _as_of(as_of)
    return {
        "value": build_value_composite(l2_conclusions, as_of=normalized_as_of),
        "market": build_market_composite(l2_conclusions, as_of=normalized_as_of),
        "risk": build_risk_composite(l2_conclusions, as_of=normalized_as_of),
        "macro": build_macro_composite(l2_conclusions, as_of=normalized_as_of),
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


def build_report_result(
    decision_result: Mapping[str, Any],
    *,
    question: str = "",
) -> ReportResult:
    del decision_result
    answer = (
        "已完成本轮研判流程。系统按照固定研判流程组织本轮分析，包括问题理解、"
        "信息整理、并行分析、维度综合与报告生成；可展开流程详情查看过程记录。"
    )
    if question:
        answer = f"{answer}\n\n收到的问题：{question}"
    return {
        "schema": REPORT_RESULT_SCHEMA_VERSION,
        "schema_version": REPORT_RESULT_SCHEMA_VERSION,
        "title": "研判流程",
        "answer": answer,
        "status": "pending_implementation",
        "sections": [
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
        ],
        "evidence_cards": [
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
            }
        ],
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
    normalized_plan = cast(FixedDagPlan, plan) if plan_valid else normalize_fixed_dag_plan(plan)
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
            for dimension in DIMENSION_GROUPS
        ],
        "currentStage": stage,
        "completedSteps": completed,
        "executionBatches": execution_batches or [],
        "stepResults": dict(step_results or {}),
        "provenance": {
            "source": RESET_SOURCE,
            "providerInvoked": False,
            "externalInvoked": False,
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
    if provenance.get("providerInvoked") or provenance.get("externalInvoked"):
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
    return {"source": RESET_SOURCE, "status": "complete", "answer": answer}


def build_emitted_bundle(report_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "answer": str(report_result.get("answer") or ""),
        "summary_source": RESET_SOURCE,
        "confidence": 0.0,
        "evidence_cards": list(report_result.get("evidence_cards", []) or []),
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
        "report_result": dict(report_result),
    }
