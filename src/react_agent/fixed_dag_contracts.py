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
            description="创建确定性的固定 DAG 执行计划。",
            status="complete",
            agent_id="route_planner",
            dimension="l1",
        ),
        _step(
            step_id="financial_data_service",
            stage="evidence",
            title=AGENT_TITLE_LABELS["financial_data_service"],
            description="准备数据包占位接口，不调用外部服务。",
            agent_id="financial_data_service",
            dimension="l1",
            depends_on=("route_planner",),
        ),
        _step(
            step_id="entity_relation_extractor",
            stage="evidence",
            title=AGENT_TITLE_LABELS["entity_relation_extractor"],
            description="解析实体并抽取关系，不进行实时查询。",
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
                description="生成标准化的待实现结论对象。",
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
                description="汇总单一维度的 L2 结论，形成确定性占位结果。",
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
                description="生成确定性决策占位结果。",
                agent_id="decision_synthesizer",
                dimension="l4",
                depends_on=tuple(f"dimension:{dimension}" for dimension in DIMENSION_GROUPS),
            ),
            _step(
                step_id="report_generator",
                stage="report",
                title=AGENT_TITLE_LABELS["report_generator"],
                description="生成公开的重置骨架回答。",
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
            "No provider、搜索或外部服务被调用。",
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
            "No provider 或外部服务被调用。",
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
        "固定 DAG 重置骨架已启用。本次 R3 阶段响应来自确定性的 contract、"
        "executor 和 function seam，不来自实时业务智能体算法。No provider、"
        "搜索服务或 external /v1/agent/invoke 端点被调用。"
    )
    if question:
        answer = f"{answer}\n\n收到的问题：{question}"
    return {
        "schema": REPORT_RESULT_SCHEMA_VERSION,
        "schema_version": REPORT_RESULT_SCHEMA_VERSION,
        "title": "固定 DAG 重置骨架",
        "answer": answer,
        "status": "pending_implementation",
        "sections": [
            {
                "id": "runtime_scope",
                "title": "运行时范围",
                "content": "仅执行重置骨架；未执行实时外部调用。",
            },
            {
                "id": "implementation_status",
                "title": "实现状态",
                "content": "业务智能体算法仍待实现。",
            },
        ],
        "evidence_cards": [
            {
                "title": "重置运行时范围",
                "note": "确定性固定 DAG 骨架；业务 Agent 仍为占位实现。",
            }
        ],
        "limitations": [
            "R3 阶段尚未实现业务智能体算法。",
            "未验证 provider 就绪状态。",
            "未验证外部服务就绪状态。",
            "前端 workflow v2 的后续视觉增强仍属于后续重置阶段。",
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
    if "No provider" not in answer or "external /v1/agent/invoke" not in answer:
        return False, "reset_limitation_missing"
    if not isinstance(obj.get("sections"), list):
        return False, "sections_missing"
    if not isinstance(obj.get("evidence_cards"), list):
        return False, "evidence_cards_missing"
    limitations = obj.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        return False, "limitations_missing"
    forbidden_claims = ("provider verified", "external service verified", "live analysis complete")
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
                "summary": "确定性重置骨架综合结果。",
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
        answer = "固定 DAG 重置骨架已完成，但没有报告正文。"
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
