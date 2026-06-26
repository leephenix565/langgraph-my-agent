"""Fixed-DAG execution constants."""

from __future__ import annotations

from react_agent.fixed_dag.constants import (
    FIXED_DAG_STAGE_ORDER,
    L2_CONCLUSION_AGENT_IDS,
    MACRO_AGENT_IDS,
    MARKET_AGENT_IDS,
    RISK_AGENT_IDS,
    VALUE_AGENT_IDS,
)

FIXED_DAG_EXECUTION_SCHEMA_VERSION = "fixed_dag_execution_v1"
FIXED_DAG_STEP_RESULT_SCHEMA_VERSION = "fixed_dag_step_result_v1"
LEGAL_STEP_STATUSES = {
    "complete",
    "pending_implementation",
    "skipped",
    "blocked",
    "failed",
}
LEGAL_DIMENSIONS = {"l1", "value", "market", "risk", "macro", "l4"}
STAGE_ORDER_INDEX = {stage: index for index, stage in enumerate(FIXED_DAG_STAGE_ORDER)}
L2_EVIDENCE_DEPS = {"entity_relation_extractor", "financial_data_service"}
DIMENSION_STEP_IDS = {
    "value": "dimension:value",
    "market": "dimension:market",
    "risk": "dimension:risk",
    "macro": "dimension:macro",
}
COMPOSITE_DEPENDENCY_GROUPS = {
    "value_composite": VALUE_AGENT_IDS,
    "market_composite": MARKET_AGENT_IDS,
    "risk_composite": RISK_AGENT_IDS,
    "macro_composite": MACRO_AGENT_IDS,
}

__all__ = [
    "COMPOSITE_DEPENDENCY_GROUPS",
    "DIMENSION_STEP_IDS",
    "FIXED_DAG_EXECUTION_SCHEMA_VERSION",
    "FIXED_DAG_STEP_RESULT_SCHEMA_VERSION",
    "L2_CONCLUSION_AGENT_IDS",
    "L2_EVIDENCE_DEPS",
    "LEGAL_DIMENSIONS",
    "LEGAL_STEP_STATUSES",
    "STAGE_ORDER_INDEX",
]
