# ruff: noqa: D101, D103
"""Deterministic fixed-DAG reset contracts.

These helpers define the reset skeleton protocol used by the active graph in
Phase R1-B.  They deliberately avoid provider calls, external agent invokes, and
legacy routing modes.
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

FIXED_DAG_SCHEMA_VERSION = "fixed_dag_plan_v1"
WORKFLOW_SNAPSHOT_SCHEMA_VERSION = "workflow_snapshot_v2"

FixedDagStage = Literal[
    "planning",
    "evidence",
    "l2_analysis",
    "dimension_composite",
    "decision",
    "report",
]

ConclusionStatus = Literal["pending_implementation", "partial", "complete", "error"]

FIXED_DAG_STAGE_ORDER: tuple[FixedDagStage, ...] = (
    "planning",
    "evidence",
    "l2_analysis",
    "dimension_composite",
    "decision",
    "report",
)

RESET_RUNTIME_AGENT_IDS: tuple[str, ...] = (
    "route_planner",
    "entity_relation_extractor",
    "financial_data_service",
    "value_traditional_valuation",
    "value_ml_valuation",
    "value_meta_valuation",
    "value_research_synthesis",
    "market_stock_technical",
    "market_fund_manager_behavior",
    "market_ipo_investor_behavior",
    "market_capital_flow_chip",
    "sentiment_company_radar",
    "risk_crash",
    "risk_financial_fraud",
    "risk_identification",
    "risk_compliance_review",
    "macro_analysis",
    "macro_commodity_pricing",
    "macro_index_valuation",
    "macro_sentiment",
    "macro_industry_hotspot",
    "value_composite",
    "market_composite",
    "risk_composite",
    "macro_composite",
    "decision_synthesizer",
    "report_generator",
)

L2_CONCLUSION_AGENT_IDS: tuple[str, ...] = (
    "value_traditional_valuation",
    "value_ml_valuation",
    "value_meta_valuation",
    "value_research_synthesis",
    "market_stock_technical",
    "market_fund_manager_behavior",
    "market_ipo_investor_behavior",
    "market_capital_flow_chip",
    "sentiment_company_radar",
    "risk_crash",
    "risk_financial_fraud",
    "risk_identification",
    "risk_compliance_review",
    "macro_analysis",
    "macro_commodity_pricing",
    "macro_index_valuation",
    "macro_sentiment",
    "macro_industry_hotspot",
)

DIMENSION_GROUPS: dict[str, tuple[str, ...]] = {
    "value": (
        "value_traditional_valuation",
        "value_ml_valuation",
        "value_meta_valuation",
        "value_research_synthesis",
    ),
    "market": (
        "market_stock_technical",
        "market_fund_manager_behavior",
        "market_ipo_investor_behavior",
        "market_capital_flow_chip",
        "sentiment_company_radar",
    ),
    "risk": (
        "risk_crash",
        "risk_financial_fraud",
        "risk_identification",
        "risk_compliance_review",
    ),
    "macro": (
        "macro_analysis",
        "macro_commodity_pricing",
        "macro_index_valuation",
        "macro_sentiment",
        "macro_industry_hotspot",
    ),
}

SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES: tuple[str, ...] = (
    "market_composite",
)


class FixedDagStep(TypedDict):
    id: str
    stage: FixedDagStage
    title: str
    description: str
    agent_id: NotRequired[str]
    target_ids: NotRequired[list[str]]
    dimension: NotRequired[str]
    status: str


class FixedDagPlan(TypedDict):
    schema: str
    plan_id: str
    user_text: str
    stages: list[dict[str, Any]]
    steps: list[FixedDagStep]
    target_agent_ids: list[str]
    dimension_groups: dict[str, list[str]]
    provenance: dict[str, Any]


class EntityRelationBundle(TypedDict):
    schema: str
    status: ConclusionStatus
    entities: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    notes: list[str]


class DataBundle(TypedDict):
    schema: str
    status: ConclusionStatus
    as_of: str
    data_as_of: str
    sources: list[str]
    notes: list[str]


class ConclusionObject(TypedDict):
    schema: str
    agent_id: str
    stance: str
    confidence: float
    status: ConclusionStatus
    evidence: list[dict[str, Any]]
    as_of: str
    data_as_of: str
    output_routes: NotRequired[list[str]]


class DimensionCompositeResult(TypedDict):
    schema: str
    dimension: str
    stance: str
    confidence: float
    status: ConclusionStatus
    contributing_agents: list[str]
    evidence_refs: list[str]
    gate: NotRequired[str]
    veto: NotRequired[bool]
    penalty: NotRequired[float]
    dimension_weights: NotRequired[dict[str, float]]
    risk_sensitivity: NotRequired[str]


class DecisionResult(TypedDict):
    schema: str
    decision: str
    score: float | None
    target_price_range: dict[str, float | None]
    reasoning_trace: list[str]
    status: ConclusionStatus


class ReportResult(TypedDict):
    schema: str
    title: str
    answer: str
    status: ConclusionStatus
    sections: list[dict[str, Any]]
    limitations: list[str]


def build_deterministic_fixed_dag_plan(user_text: str = "") -> FixedDagPlan:
    """Build the deterministic reset plan used when no provider is available."""
    steps: list[FixedDagStep] = [
        {
            "id": "route_planner",
            "stage": "planning",
            "title": "Route planner",
            "description": "Create a fixed DAG execution plan.",
            "agent_id": "route_planner",
            "status": "complete",
        },
        {
            "id": "entity_relation_extractor",
            "stage": "evidence",
            "title": "Entity relation extractor",
            "description": "Resolve entities and extract relations without live lookup.",
            "agent_id": "entity_relation_extractor",
            "status": "pending_implementation",
        },
        {
            "id": "financial_data_service",
            "stage": "evidence",
            "title": "Financial data service",
            "description": "Prepare a data bundle seam for future services.",
            "agent_id": "financial_data_service",
            "status": "pending_implementation",
        },
    ]

    for agent_id in L2_CONCLUSION_AGENT_IDS:
        steps.append(
            {
                "id": f"l2:{agent_id}",
                "stage": "l2_analysis",
                "title": agent_id.replace("_", " ").title(),
                "description": "Produce a normalized conclusion object.",
                "agent_id": agent_id,
                "status": "pending_implementation",
            }
        )

    for dimension, agent_ids in DIMENSION_GROUPS.items():
        steps.append(
            {
                "id": f"dimension:{dimension}",
                "stage": "dimension_composite",
                "title": f"{dimension.title()} composite",
                "description": "Combine L2 conclusions for one decision dimension.",
                "target_ids": list(agent_ids),
                "agent_id": f"{dimension}_composite",
                "dimension": dimension,
                "status": "pending_implementation",
            }
        )

    steps.extend(
        [
            {
                "id": "decision_synthesizer",
                "stage": "decision",
                "title": "Decision synthesizer",
                "description": "Create a deterministic decision placeholder.",
                "agent_id": "decision_synthesizer",
                "status": "pending_implementation",
            },
            {
                "id": "report_generator",
                "stage": "report",
                "title": "Report generator",
                "description": "Generate the public reset skeleton answer.",
                "agent_id": "report_generator",
                "status": "pending_implementation",
            },
        ]
    )

    return {
        "schema": FIXED_DAG_SCHEMA_VERSION,
        "plan_id": "reset-fixed-dag-plan-v1",
        "user_text": user_text,
        "stages": [
            {
                "id": stage,
                "title": stage.replace("_", " ").title(),
                "step_ids": [step["id"] for step in steps if step["stage"] == stage],
            }
            for stage in FIXED_DAG_STAGE_ORDER
        ],
        "steps": steps,
        "target_agent_ids": list(RESET_RUNTIME_AGENT_IDS),
        "dimension_groups": {key: list(value) for key, value in DIMENSION_GROUPS.items()},
        "provenance": {
            "source": "deterministic_reset_skeleton",
            "provider_invoked": False,
            "external_invoked": False,
        },
    }


def build_entity_relation_bundle(user_text: str) -> EntityRelationBundle:
    return {
        "schema": "entity_relation_bundle_v1",
        "status": "pending_implementation",
        "entities": [],
        "relations": [],
        "notes": [
            "Entity resolution is a fixed-DAG seam in Phase R1-B.",
            f"Original question length: {len(user_text)}",
        ],
    }


def build_data_bundle() -> DataBundle:
    return {
        "schema": "data_bundle_v1",
        "status": "pending_implementation",
        "as_of": "not_available",
        "data_as_of": "not_available",
        "sources": [],
        "notes": [
            "No provider, search, or external service was invoked in the reset skeleton."
        ],
    }


def build_l2_conclusions() -> dict[str, ConclusionObject]:
    conclusions: dict[str, ConclusionObject] = {}
    for agent_id in L2_CONCLUSION_AGENT_IDS:
        item: ConclusionObject = {
            "schema": "conclusion_object_v1",
            "agent_id": agent_id,
            "stance": "not_evaluated",
            "confidence": 0.0,
            "status": "pending_implementation",
            "evidence": [],
            "as_of": "not_available",
            "data_as_of": "not_available",
        }
        if agent_id == "sentiment_company_radar":
            item["output_routes"] = list(SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES)
        conclusions[agent_id] = item
    return conclusions


def build_dimension_results(
    l2_conclusions: dict[str, ConclusionObject],
) -> dict[str, DimensionCompositeResult]:
    del l2_conclusions
    results: dict[str, DimensionCompositeResult] = {}
    for dimension, agent_ids in DIMENSION_GROUPS.items():
        result: DimensionCompositeResult = {
            "schema": "dimension_composite_result_v1",
            "dimension": dimension,
            "stance": "not_evaluated",
            "confidence": 0.0,
            "status": "pending_implementation",
            "contributing_agents": list(agent_ids),
            "evidence_refs": [],
        }
        if dimension == "risk":
            result.update({"gate": "not_evaluated", "veto": False, "penalty": 0.0})
        if dimension == "macro":
            result.update(
                {
                    "dimension_weights": {
                        "market": 0.25,
                        "value": 0.35,
                        "risk": 0.25,
                        "macro": 0.15,
                    },
                    "risk_sensitivity": "not_evaluated",
                }
            )
        results[dimension] = result
    return results


def build_decision_result() -> DecisionResult:
    return {
        "schema": "decision_result_v1",
        "decision": "pending_implementation",
        "score": None,
        "target_price_range": {"low": None, "mid": None, "high": None},
        "reasoning_trace": [
            "Phase R1-B only verifies the fixed DAG runtime skeleton.",
            "No provider, external agent, or live market data source was invoked.",
        ],
        "status": "pending_implementation",
    }


def build_report_result(question: str, decision: DecisionResult) -> ReportResult:
    del decision
    answer = (
        "Fixed DAG reset skeleton is active. This response is a deterministic "
        "Phase R1-B placeholder, not a live investment analysis. No provider, "
        "search service, or external /v1/agent/invoke endpoint was called. "
        "L1 evidence seams, L2 conclusion agents, L3 dimension composites, "
        "the decision synthesizer, and the report generator are present as "
        "protocol placeholders pending business implementation."
    )
    if question:
        answer = f"{answer}\n\nReceived question: {question}"
    return {
        "schema": "report_result_v1",
        "title": "Fixed DAG Reset Skeleton",
        "answer": answer,
        "status": "pending_implementation",
        "sections": [
            {
                "id": "runtime_scope",
                "title": "Runtime scope",
                "content": "Reset skeleton only; no live external execution.",
            }
        ],
        "limitations": [
            "External service readiness is not verified.",
            "Business agent algorithms are not implemented in Phase R1-B.",
            "Frontend workflow v2 polish remains a later reset phase.",
        ],
    }


def build_workflow_snapshot_v2(
    *,
    plan: FixedDagPlan,
    current_stage: FixedDagStage,
    completed_steps: list[str],
    dimension_results: dict[str, DimensionCompositeResult] | None = None,
) -> dict[str, Any]:
    dimension_results = dimension_results or {}
    return {
        "schema": WORKFLOW_SNAPSHOT_SCHEMA_VERSION,
        "planId": plan["plan_id"],
        "stages": [
            {
                "key": stage["id"],
                "title": stage["title"],
                "stepIds": stage["step_ids"],
            }
            for stage in plan["stages"]
        ],
        "dagSteps": [
            {
                "id": step["id"],
                "stage": step["stage"],
                "agentId": step.get("agent_id"),
                "dimension": step.get("dimension"),
                "title": step["title"],
                "summary": step["description"],
                "status": "complete"
                if step["id"] in completed_steps
                else step["status"],
            }
            for step in plan["steps"]
        ],
        "dimensionGroups": [
            {
                "id": dimension,
                "title": f"{dimension.title()} composite",
                "stepIds": [f"dimension:{dimension}"],
                "status": dimension_results.get(dimension, {}).get(
                    "status", "pending_implementation"
                ),
                "summary": "Deterministic reset skeleton composite.",
            }
            for dimension in DIMENSION_GROUPS
        ],
        "currentStage": current_stage,
        "completedSteps": completed_steps,
        "provenance": {
            "source": "reset_skeleton",
            "providerInvoked": False,
            "externalInvoked": False,
        },
        "finalSource": "reset_skeleton",
    }
