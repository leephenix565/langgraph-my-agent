# ruff: noqa: D101
"""Typed contract shapes for the fixed-DAG reset workflow."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

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
    risk_sensitivity: NotRequired[str | float]
    provenance: NotRequired[dict[str, Any]]


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


class ReportInputBundle(TypedDict):
    schema: str
    schema_version: str
    question: str
    status: ConclusionStatus
    agent_task_summaries: NotRequired[list[dict[str, Any]]]
    agent_evidence_bundle: NotRequired[dict[str, Any]]
    l2_agent_summaries: list[dict[str, Any]]
    l3_composite_summaries: list[dict[str, Any]]
    risk_gate: dict[str, Any]
    macro_regulator: dict[str, Any]
    decision_context: dict[str, Any]
    limitations: list[str]
    provenance: dict[str, Any]


class ReportResult(TypedDict):
    schema: str
    schema_version: str
    title: str
    answer: str
    status: ConclusionStatus
    sections: list[dict[str, Any]]
    evidence_cards: list[dict[str, Any]]
    limitations: list[str]


class AgentTask(TypedDict):
    schema: str
    schema_version: str
    agent_id: str
    display_name: str
    layer: str
    dimension: str
    user_question: str
    task_instruction: str
    target: str
    as_of: str
    data_bundle: dict[str, Any]
    entity_relation_bundle: dict[str, Any]
    upstream_results: dict[str, Any]
    required_output_schema: str
    provenance: dict[str, Any]


__all__ = [
    "AgentTask",
    "ConclusionObject",
    "ConclusionStatus",
    "DataBundle",
    "DecisionResult",
    "DimensionCompositeResult",
    "DimensionName",
    "EntityRelationBundle",
    "FixedDagDimension",
    "FixedDagPlan",
    "FixedDagStage",
    "FixedDagStep",
    "FixedDagStepStatus",
    "ReportInputBundle",
    "ReportResult",
    "RouteIntent",
    "RouteTaskType",
    "SelectedFixedDagPlan",
]
