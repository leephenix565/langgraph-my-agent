# ruff: noqa: D103
"""Validation helpers for fixed-DAG execution plans and results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from react_agent.fixed_dag.constants import (
    DECISION_RESULT_SCHEMA_VERSION,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_GROUPS,
    FIXED_DAG_SCHEMA_VERSION,
    REPORT_RESULT_SCHEMA_VERSION,
    RESET_RUNTIME_AGENT_IDS,
    SELECTED_FIXED_DAG_SCHEMA_VERSION,
)
from react_agent.fixed_dag.execution.constants import (
    COMPOSITE_DEPENDENCY_GROUPS,
    DIMENSION_STEP_IDS,
    L2_CONCLUSION_AGENT_IDS,
    L2_EVIDENCE_DEPS,
    LEGAL_DIMENSIONS,
    STAGE_ORDER_INDEX,
)
from react_agent.fixed_dag.execution.step_results import validate_step_result
from react_agent.fixed_dag.execution.topology import (
    _deps,
    _l2_step_ids,
    _selected_dimension_step_ids,
    _steps,
    _topological_batches_from_steps,
)
from react_agent.fixed_dag.safety import _contains_legacy_key
from react_agent.fixed_dag_contracts import (
    validate_decision_result,
    validate_dimension_composite_result,
    validate_fixed_dag_plan,
    validate_report_input_bundle,
    validate_report_result,
    validate_selected_fixed_dag_plan,
    validate_workflow_snapshot_v2,
)


def _validate_stage_and_dimension(step: Mapping[str, Any]) -> tuple[bool, str]:
    stage = str(step.get("stage") or "")
    if stage not in STAGE_ORDER_INDEX:
        return False, "invalid_stage"
    dimension = str(step.get("dimension") or "")
    if dimension not in LEGAL_DIMENSIONS:
        return False, "invalid_dimension"
    return True, "ok"


def _validate_step_identity(steps: list[Mapping[str, Any]]) -> tuple[bool, str]:
    seen: set[str] = set()
    for step in steps:
        step_id = str(step.get("id") or "")
        if not step_id:
            return False, "step_id_missing"
        if step_id in seen:
            return False, "duplicate_step_id"
        seen.add(step_id)
        agent_id = str(step.get("agent_id") or "")
        if agent_id not in RESET_RUNTIME_AGENT_IDS:
            return False, "invalid_agent_id"
        valid, reason = _validate_stage_and_dimension(step)
        if not valid:
            return valid, reason
        if agent_id == "sentiment_company_radar" and step.get("dimension") != "market":
            return False, "sentiment_dimension_mismatch"
    return True, "ok"


def _validate_dependency_graph(steps: list[Mapping[str, Any]]) -> tuple[bool, str]:
    by_id = {str(step["id"]): step for step in steps}
    for step in steps:
        current_stage = STAGE_ORDER_INDEX[str(step["stage"])]
        for dep_id in _deps(step):
            dep = by_id.get(dep_id)
            if dep is None:
                return False, "missing_dependency"
            if STAGE_ORDER_INDEX[str(dep["stage"])] > current_stage:
                return False, "stage_order_violation"
    if sum(len(batch) for batch in _topological_batches_from_steps(steps)) != len(steps):
        return False, "cycle_detected"
    return True, "ok"


def _validate_dimension_dependencies(steps: list[Mapping[str, Any]]) -> tuple[bool, str]:
    by_agent = {str(step.get("agent_id")): step for step in steps}

    for agent_id in L2_CONCLUSION_AGENT_IDS:
        step = by_agent.get(agent_id)
        if step is None:
            return False, "missing_l2_step"
        if set(_deps(step)) != L2_EVIDENCE_DEPS:
            return False, "l2_dependency_mismatch"

    for composite_agent_id, agent_ids in COMPOSITE_DEPENDENCY_GROUPS.items():
        step = by_agent.get(composite_agent_id)
        if step is None:
            return False, "missing_composite_step"
        if set(step.get("target_ids", [])) != set(agent_ids):
            return False, f"{composite_agent_id}_target_mismatch"
        if set(_deps(step)) != _l2_step_ids(agent_ids):
            return False, f"{composite_agent_id}_dependency_mismatch"

    market_step = by_agent.get("market_composite", {})
    if "l2:sentiment_company_radar" not in set(_deps(market_step)):
        return False, "market_missing_sentiment_dependency"
    risk_step = by_agent.get("risk_composite", {})
    if "l2:sentiment_company_radar" in set(_deps(risk_step)):
        return False, "risk_reads_sentiment"

    decision_step = by_agent.get("decision_synthesizer")
    if decision_step is None:
        return False, "missing_decision_step"
    if set(_deps(decision_step)) != set(DIMENSION_STEP_IDS.values()):
        return False, "decision_dependency_mismatch"

    report_step = by_agent.get("report_generator")
    if report_step is None:
        return False, "missing_report_step"
    if _deps(report_step) != ["decision_synthesizer"]:
        return False, "report_dependency_mismatch"

    sentiment_dep = "l2:sentiment_company_radar"
    for step in steps:
        if sentiment_dep in _deps(step) and step.get("agent_id") != "market_composite":
            return False, "sentiment_dependency_not_market_only"
    return True, "ok"


def _step_by_agent(steps: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(step.get("agent_id")): step for step in steps}


def _validate_selected_dimension_dependencies(plan: Mapping[str, Any]) -> tuple[bool, str]:
    steps = _steps(plan)
    by_agent = _step_by_agent(steps)
    dimension_groups = plan.get("dimension_groups")
    if not isinstance(dimension_groups, Mapping):
        return False, "invalid_dimension_groups"

    route_step = by_agent.get("route_planner")
    if route_step is None:
        return False, "missing_route_planner"
    if _deps(route_step):
        return False, "route_planner_dependency_mismatch"
    for evidence_agent_id in ("financial_data_service", "entity_relation_extractor"):
        evidence_step = by_agent.get(evidence_agent_id)
        if evidence_step is None:
            return False, "missing_evidence_step"
        if _deps(evidence_step) != ["route_planner"]:
            return False, "evidence_dependency_mismatch"

    for dimension, agent_ids in dimension_groups.items():
        if not isinstance(agent_ids, list) or not agent_ids:
            return False, "selected_dimension_l2_agents_missing"
        composite_agent_id = DIMENSION_COMPOSITE_AGENT_IDS[str(dimension)]
        composite_step = by_agent.get(composite_agent_id)
        if composite_step is None:
            return False, "missing_selected_composite_step"
        if composite_agent_id == "risk_composite" and "l2:sentiment_company_radar" in set(_deps(composite_step)):
            return False, "risk_reads_sentiment"
        if set(composite_step.get("target_ids", [])) != set(agent_ids):
            return False, "selected_composite_target_mismatch"
        expected_l2_step_ids = {f"l2:{agent_id}" for agent_id in agent_ids}
        if set(_deps(composite_step)) != expected_l2_step_ids:
            return False, "selected_composite_dependency_mismatch"
        for agent_id in agent_ids:
            l2_step = by_agent.get(str(agent_id))
            if l2_step is None:
                return False, "missing_selected_l2_step"
            if set(_deps(l2_step)) != L2_EVIDENCE_DEPS:
                return False, "l2_dependency_mismatch"

    risk_step = by_agent.get("risk_composite", {})
    if "l2:sentiment_company_radar" in set(_deps(risk_step)):
        return False, "risk_reads_sentiment"
    sentiment_dep = "l2:sentiment_company_radar"
    for step in steps:
        if sentiment_dep in _deps(step) and step.get("agent_id") != "market_composite":
            return False, "sentiment_dependency_not_market_only"

    selected_dimension_step_ids = _selected_dimension_step_ids(plan)
    decision_step = by_agent.get("decision_synthesizer")
    if decision_step is not None and set(_deps(decision_step)) != set(selected_dimension_step_ids):
        return False, "selected_decision_dependency_mismatch"

    report_step = by_agent.get("report_generator")
    if report_step is None:
        return False, "missing_report_step"
    expected_report_deps = (
        ["decision_synthesizer"]
        if decision_step is not None
        else selected_dimension_step_ids
    )
    if set(_deps(report_step)) != set(expected_report_deps):
        return False, "selected_report_dependency_mismatch"
    return True, "ok"


def validate_selected_dag_steps(plan: Mapping[str, Any]) -> tuple[bool, str]:
    """Validate selected DAG steps without requiring the full 27-agent plan."""
    if not isinstance(plan, Mapping):
        return False, "plan_not_mapping"
    if plan.get("schema") != SELECTED_FIXED_DAG_SCHEMA_VERSION:
        return False, "invalid_schema"
    if _contains_legacy_key(plan):
        return False, "legacy_dispatch_field_present"
    steps = _steps(plan)
    if not steps:
        return False, "steps_missing"
    valid, reason = _validate_step_identity(steps)
    if not valid:
        return valid, reason
    valid, reason = _validate_dependency_graph(steps)
    if not valid:
        return valid, reason
    valid, reason = _validate_selected_dimension_dependencies(plan)
    if not valid:
        return valid, reason
    valid, reason = validate_selected_fixed_dag_plan(plan)
    if not valid:
        return valid, reason
    return True, "ok"


def validate_dag_steps(plan: Mapping[str, Any]) -> tuple[bool, str]:
    """Validate step ids, dependencies, stage/dimension legality, and roster edges."""
    if not isinstance(plan, Mapping):
        return False, "plan_not_mapping"
    if plan.get("schema") != FIXED_DAG_SCHEMA_VERSION:
        return False, "invalid_schema"
    if _contains_legacy_key(plan):
        return False, "legacy_dispatch_field_present"
    steps = _steps(plan)
    if not steps:
        return False, "steps_missing"
    valid, reason = _validate_step_identity(steps)
    if not valid:
        return valid, reason
    valid, reason = _validate_dependency_graph(steps)
    if not valid:
        return valid, reason
    valid, reason = _validate_dimension_dependencies(steps)
    if not valid:
        return valid, reason
    valid, reason = validate_fixed_dag_plan(plan)
    if not valid:
        return valid, reason
    return True, "ok"


def validate_dag_execution_result(result: Mapping[str, Any]) -> tuple[bool, str]:
    if result.get("schema_version") != "fixed_dag_execution_v1":
        return False, "invalid_schema_version"
    if result.get("status") not in {"complete", "partial", "degraded"}:
        return False, "invalid_status"
    if _contains_legacy_key(result):
        return False, "legacy_dispatch_field_present"
    execution_batches = result.get("execution_batches")
    if not isinstance(execution_batches, list) or not execution_batches:
        return False, "execution_batches_missing"
    step_results = result.get("step_results")
    if not isinstance(step_results, Mapping) or not step_results:
        return False, "step_results_missing"
    for item in step_results.values():
        if not isinstance(item, Mapping):
            return False, "invalid_step_result"
        valid, reason = validate_step_result(item)
        if not valid:
            return False, reason

    workflow = result.get("workflow_snapshot")
    expected_dimensions = set(DIMENSION_GROUPS)
    if isinstance(workflow, Mapping) and isinstance(workflow.get("dimensionGroups"), list):
        expected_dimensions = {
            str(item.get("id"))
            for item in workflow["dimensionGroups"]
            if isinstance(item, Mapping) and item.get("id")
        }
    dimension_results = result.get("dimension_results")
    if not isinstance(dimension_results, Mapping) or set(dimension_results) != expected_dimensions:
        return False, "dimension_results_missing"
    for item in dimension_results.values():
        if not isinstance(item, Mapping):
            return False, "invalid_dimension_result"
        valid, reason = validate_dimension_composite_result(item)
        if not valid:
            return False, reason
    decision = result.get("decision_result")
    if not isinstance(decision, Mapping) or decision.get("schema") != DECISION_RESULT_SCHEMA_VERSION:
        return False, "decision_result_missing"
    valid, reason = validate_decision_result(cast(Mapping[str, Any], decision))
    if not valid:
        return False, reason
    report = result.get("report_result")
    if not isinstance(report, Mapping) or report.get("schema") != REPORT_RESULT_SCHEMA_VERSION:
        return False, "report_result_missing"
    valid, reason = validate_report_result(cast(Mapping[str, Any], report))
    if not valid:
        return False, reason
    report_input_bundle = result.get("report_input_bundle")
    if not isinstance(report_input_bundle, Mapping):
        return False, "report_input_bundle_missing"
    valid, reason = validate_report_input_bundle(cast(Mapping[str, Any], report_input_bundle))
    if not valid:
        return False, reason
    if not isinstance(workflow, Mapping):
        return False, "workflow_snapshot_missing"
    valid, reason = validate_workflow_snapshot_v2(workflow)
    if not valid:
        return False, reason
    completed = set(workflow.get("completedSteps", []))
    executed = {
        step_id
        for step_id, item in step_results.items()
        if isinstance(item, Mapping) and item.get("status") in {"complete", "pending_implementation"}
    }
    if completed != executed:
        return False, "completed_steps_execution_mismatch"
    return True, "ok"


__all__ = [
    "validate_dag_execution_result",
    "validate_dag_steps",
    "validate_selected_dag_steps",
]
