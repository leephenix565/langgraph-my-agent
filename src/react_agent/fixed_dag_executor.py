# ruff: noqa: D103
"""Plan-driven deterministic fixed-DAG executor compatibility facade.

The runner implementation lives in ``react_agent.fixed_dag.execution.runner``.
This module preserves the historical import path for graph, tests, and any
external callers that still import ``react_agent.fixed_dag_executor``.
"""

from __future__ import annotations

from collections import deque as deque
from collections.abc import Mapping as Mapping
from typing import Any as Any
from typing import cast as cast

from react_agent.fixed_dag.execution.constants import (
    COMPOSITE_DEPENDENCY_GROUPS as COMPOSITE_DEPENDENCY_GROUPS,
)
from react_agent.fixed_dag.execution.constants import (
    DIMENSION_STEP_IDS as DIMENSION_STEP_IDS,
)
from react_agent.fixed_dag.execution.constants import (
    FIXED_DAG_EXECUTION_SCHEMA_VERSION as FIXED_DAG_EXECUTION_SCHEMA_VERSION,
)
from react_agent.fixed_dag.execution.constants import (
    FIXED_DAG_STEP_RESULT_SCHEMA_VERSION as FIXED_DAG_STEP_RESULT_SCHEMA_VERSION,
)
from react_agent.fixed_dag.execution.constants import (
    L2_EVIDENCE_DEPS as L2_EVIDENCE_DEPS,
)
from react_agent.fixed_dag.execution.constants import (
    LEGAL_DIMENSIONS as LEGAL_DIMENSIONS,
)
from react_agent.fixed_dag.execution.constants import (
    LEGAL_STEP_STATUSES as LEGAL_STEP_STATUSES,
)
from react_agent.fixed_dag.execution.constants import (
    STAGE_ORDER_INDEX as STAGE_ORDER_INDEX,
)
from react_agent.fixed_dag.execution.runner import (
    execute_fixed_dag_plan as execute_fixed_dag_plan,
)
from react_agent.fixed_dag.execution.step_results import (
    build_initial_step_results as build_initial_step_results,
)
from react_agent.fixed_dag.execution.step_results import (
    build_step_result as build_step_result,
)
from react_agent.fixed_dag.execution.step_results import (
    validate_step_result as validate_step_result,
)
from react_agent.fixed_dag.execution.topology import (
    build_dag_step_index as build_dag_step_index,
)
from react_agent.fixed_dag.execution.topology import (
    topological_batches as topological_batches,
)
from react_agent.fixed_dag.execution.topology import (
    topological_batches_for_selected_plan as topological_batches_for_selected_plan,
)
from react_agent.fixed_dag.execution.validation import (
    validate_dag_execution_result as validate_dag_execution_result,
)
from react_agent.fixed_dag.execution.validation import (
    validate_dag_steps as validate_dag_steps,
)
from react_agent.fixed_dag.execution.validation import (
    validate_selected_dag_steps as validate_selected_dag_steps,
)
from react_agent.fixed_dag_contracts import (
    DECISION_RESULT_SCHEMA_VERSION as DECISION_RESULT_SCHEMA_VERSION,
)
from react_agent.fixed_dag_contracts import (
    DIMENSION_COMPOSITE_AGENT_IDS as DIMENSION_COMPOSITE_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS as DIMENSION_GROUPS,
)
from react_agent.fixed_dag_contracts import (
    FIXED_DAG_SCHEMA_VERSION as FIXED_DAG_SCHEMA_VERSION,
)
from react_agent.fixed_dag_contracts import (
    FIXED_DAG_STAGE_ORDER as FIXED_DAG_STAGE_ORDER,
)
from react_agent.fixed_dag_contracts import (
    L2_CONCLUSION_AGENT_IDS as L2_CONCLUSION_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    LEGACY_CONTRACT_KEYS as LEGACY_CONTRACT_KEYS,
)
from react_agent.fixed_dag_contracts import (
    MACRO_AGENT_IDS as MACRO_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    MARKET_AGENT_IDS as MARKET_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    REPORT_RESULT_SCHEMA_VERSION as REPORT_RESULT_SCHEMA_VERSION,
)
from react_agent.fixed_dag_contracts import (
    RESET_RUNTIME_AGENT_IDS as RESET_RUNTIME_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    RISK_AGENT_IDS as RISK_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    SELECTED_FIXED_DAG_SCHEMA_VERSION as SELECTED_FIXED_DAG_SCHEMA_VERSION,
)
from react_agent.fixed_dag_contracts import (
    VALUE_AGENT_IDS as VALUE_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    build_agent_task_summaries as build_agent_task_summaries,
)
from react_agent.fixed_dag_contracts import (
    build_agent_tasks_for_plan as build_agent_tasks_for_plan,
)
from react_agent.fixed_dag_contracts import (
    build_data_bundle as build_data_bundle,
)
from react_agent.fixed_dag_contracts import (
    build_decision_result as build_decision_result,
)
from react_agent.fixed_dag_contracts import (
    build_default_fixed_dag_plan as build_default_fixed_dag_plan,
)
from react_agent.fixed_dag_contracts import (
    build_dimension_results as build_dimension_results,
)
from react_agent.fixed_dag_contracts import (
    build_entity_relation_bundle as build_entity_relation_bundle,
)
from react_agent.fixed_dag_contracts import (
    build_l2_conclusions as build_l2_conclusions,
)
from react_agent.fixed_dag_contracts import (
    build_report_input_bundle as build_report_input_bundle,
)
from react_agent.fixed_dag_contracts import (
    build_report_result as build_report_result,
)
from react_agent.fixed_dag_contracts import (
    build_workflow_snapshot_v2 as build_workflow_snapshot_v2,
)
from react_agent.fixed_dag_contracts import (
    normalize_fixed_dag_plan as normalize_fixed_dag_plan,
)
from react_agent.fixed_dag_contracts import (
    validate_decision_result as validate_decision_result,
)
from react_agent.fixed_dag_contracts import (
    validate_dimension_composite_result as validate_dimension_composite_result,
)
from react_agent.fixed_dag_contracts import (
    validate_fixed_dag_plan as validate_fixed_dag_plan,
)
from react_agent.fixed_dag_contracts import (
    validate_report_input_bundle as validate_report_input_bundle,
)
from react_agent.fixed_dag_contracts import (
    validate_report_result as validate_report_result,
)
from react_agent.fixed_dag_contracts import (
    validate_selected_fixed_dag_plan as validate_selected_fixed_dag_plan,
)
from react_agent.fixed_dag_contracts import (
    validate_workflow_snapshot_v2 as validate_workflow_snapshot_v2,
)
from react_agent.fixed_dag_llm_placeholders import (
    INTERNAL_LLM_PLACEHOLDER_SOURCE as INTERNAL_LLM_PLACEHOLDER_SOURCE,
)
from react_agent.fixed_dag_llm_placeholders import (
    build_l2_conclusions_with_internal_placeholders as build_l2_conclusions_with_internal_placeholders,
)
from react_agent.fixed_dag_runtime_registry import (
    annotate_step_result_with_binding as annotate_step_result_with_binding,
)
from react_agent.fixed_dag_runtime_registry import (
    binding_by_agent_id as binding_by_agent_id,
)
from react_agent.fixed_dag_runtime_registry import (
    external_compute_default_agent_ids as external_compute_default_agent_ids,
)
