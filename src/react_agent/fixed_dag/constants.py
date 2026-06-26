"""Foundational constants for fixed-DAG contracts."""

from __future__ import annotations

from react_agent.fixed_dag.types import FixedDagStage, RouteTaskType
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
REPORT_INPUT_BUNDLE_SCHEMA_VERSION = "report_input_bundle_v1"
AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION = "agent_evidence_bundle_v1"
REPORT_RESULT_SCHEMA_VERSION = "report_result_v1"
WORKFLOW_SNAPSHOT_SCHEMA_VERSION = "workflow_snapshot_v2"
AGENT_TASK_SCHEMA_VERSION = "agent_task_v1"
RESET_SOURCE = "reset_skeleton"
DEFAULT_AS_OF = "not_available"

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
EXECUTED_STEP_STATUSES = {"complete", "pending_implementation"}


__all__ = [
    "AGENT_DIMENSIONS",
    "AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "AGENT_TASK_SCHEMA_VERSION",
    "CONCLUSION_OBJECT_SCHEMA_VERSION",
    "DATA_BUNDLE_SCHEMA_VERSION",
    "DECISION_RESULT_SCHEMA_VERSION",
    "DEFAULT_AS_OF",
    "DIMENSION_COMPOSITE_AGENT_IDS",
    "DIMENSION_COMPOSITE_SCHEMA_VERSION",
    "DIMENSION_GROUPS",
    "ENTITY_RELATION_BUNDLE_SCHEMA_VERSION",
    "EXECUTED_STEP_STATUSES",
    "FIXED_DAG_SCHEMA_VERSION",
    "FIXED_DAG_STAGE_ORDER",
    "INVESTMENT_JUDGMENT_TASK_TYPES",
    "L1_AGENT_IDS",
    "L2_CONCLUSION_AGENT_IDS",
    "L3_COMPOSITE_AGENT_IDS",
    "L4_AGENT_IDS",
    "MACRO_AGENT_IDS",
    "MARKET_AGENT_IDS",
    "REPORT_INPUT_BUNDLE_SCHEMA_VERSION",
    "REPORT_RESULT_SCHEMA_VERSION",
    "RESET_RUNTIME_AGENT_IDS",
    "RESET_SOURCE",
    "RISK_AGENT_IDS",
    "ROUTE_INTENT_SCHEMA_VERSION",
    "ROUTE_TASK_TYPES",
    "SELECTED_FIXED_DAG_SCHEMA_VERSION",
    "SELECTED_PLAN_FALLBACK_TARGETS",
    "SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES",
    "VALUE_AGENT_IDS",
    "WORKFLOW_SNAPSHOT_SCHEMA_VERSION",
]
