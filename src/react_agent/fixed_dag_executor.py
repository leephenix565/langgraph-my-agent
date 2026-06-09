# ruff: noqa: D103
"""Plan-driven deterministic fixed-DAG executor.

The Phase R3 executor is an orchestration seam only. It validates and walks the
fixed DAG plan, emits deterministic placeholder outputs, and never calls a
provider, search backend, or external agent endpoint.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from typing import Any, cast

from react_agent.fixed_dag_contracts import (
    DECISION_RESULT_SCHEMA_VERSION,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_GROUPS,
    FIXED_DAG_SCHEMA_VERSION,
    FIXED_DAG_STAGE_ORDER,
    L2_CONCLUSION_AGENT_IDS,
    LEGACY_CONTRACT_KEYS,
    MACRO_AGENT_IDS,
    MARKET_AGENT_IDS,
    REPORT_RESULT_SCHEMA_VERSION,
    RESET_RUNTIME_AGENT_IDS,
    RISK_AGENT_IDS,
    SELECTED_FIXED_DAG_SCHEMA_VERSION,
    VALUE_AGENT_IDS,
    build_decision_result,
    build_default_fixed_dag_plan,
    build_dimension_results,
    build_l2_conclusions,
    build_report_result,
    build_workflow_snapshot_v2,
    normalize_fixed_dag_plan,
    validate_decision_result,
    validate_dimension_composite_result,
    validate_fixed_dag_plan,
    validate_report_result,
    validate_selected_fixed_dag_plan,
    validate_workflow_snapshot_v2,
)
from react_agent.fixed_dag_runtime_registry import (
    annotate_step_result_with_binding,
    binding_by_agent_id,
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


def _contains_legacy_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in LEGACY_CONTRACT_KEYS or _contains_legacy_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_legacy_key(item) for item in value)
    return False


def _steps(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_steps = plan.get("dag_steps", plan.get("steps", []))
    if not isinstance(raw_steps, list):
        return []
    return [step for step in raw_steps if isinstance(step, Mapping)]


def _deps(step: Mapping[str, Any]) -> list[str]:
    raw = step.get("depends_on", [])
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item)]


def _l2_step_ids(agent_ids: tuple[str, ...]) -> set[str]:
    return {f"l2:{agent_id}" for agent_id in agent_ids}


def build_dag_step_index(plan: Mapping[str, Any]) -> dict[str, dict]:
    """Return plan steps by id without normalizing away invalid shapes."""
    index: dict[str, dict] = {}
    for step in _steps(plan):
        step_id = str(step.get("id") or "")
        if step_id:
            index[step_id] = dict(step)
    return index


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


def _selected_dimension_step_ids(plan: Mapping[str, Any]) -> list[str]:
    dimension_groups = cast(Mapping[str, list[str]], plan.get("dimension_groups", {}))
    return [
        DIMENSION_STEP_IDS[dimension]
        for dimension in plan.get("selected_dimensions", [])
        if dimension in DIMENSION_STEP_IDS and dimension_groups.get(str(dimension))
    ]


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


def _topological_batches_from_steps(steps: list[Mapping[str, Any]]) -> list[list[str]]:
    order = [str(step.get("id")) for step in steps]
    by_id = {str(step.get("id")): step for step in steps}
    indegree = {step_id: 0 for step_id in order}
    children: dict[str, list[str]] = {step_id: [] for step_id in order}
    for step in steps:
        step_id = str(step.get("id"))
        for dep_id in _deps(step):
            if dep_id not in indegree:
                continue
            indegree[step_id] += 1
            children[dep_id].append(step_id)

    ready = deque(step_id for step_id in order if indegree[step_id] == 0)
    batches: list[list[str]] = []
    visited: set[str] = set()
    while ready:
        batch = [step_id for step_id in order if step_id in ready and step_id not in visited]
        ready.clear()
        if not batch:
            break
        batches.append(batch)
        for step_id in batch:
            visited.add(step_id)
            for child_id in children[step_id]:
                if child_id not in by_id:
                    continue
                indegree[child_id] -= 1
                if indegree[child_id] == 0:
                    ready.append(child_id)
    return batches


def topological_batches(plan: Mapping[str, Any]) -> list[list[str]]:
    valid, _reason = validate_dag_steps(plan)
    if not valid:
        return []
    return _topological_batches_from_steps(_steps(plan))


def topological_batches_for_selected_plan(plan: Mapping[str, Any]) -> list[list[str]]:
    valid, _reason = validate_selected_dag_steps(plan)
    if not valid:
        return []
    return _topological_batches_from_steps(_steps(plan))


def build_step_result(
    step: Mapping[str, Any],
    *,
    status: str,
    output_ref: str = "",
    summary: str = "",
) -> dict:
    result = {
        "schema_version": FIXED_DAG_STEP_RESULT_SCHEMA_VERSION,
        "step_id": str(step.get("id") or ""),
        "agent_id": str(step.get("agent_id") or ""),
        "stage": str(step.get("stage") or ""),
        "dimension": str(step.get("dimension") or ""),
        "status": status,
        "depends_on": _deps(step),
        "output_ref": output_ref,
        "summary": summary,
        "warnings": [],
    }
    return annotate_step_result_with_binding(result)


def validate_step_result(result: Mapping[str, Any]) -> tuple[bool, str]:
    if result.get("schema_version") != FIXED_DAG_STEP_RESULT_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if not str(result.get("step_id") or ""):
        return False, "step_id_missing"
    if result.get("agent_id") not in RESET_RUNTIME_AGENT_IDS:
        return False, "invalid_agent_id"
    if result.get("stage") not in STAGE_ORDER_INDEX:
        return False, "invalid_stage"
    if result.get("dimension") not in LEGAL_DIMENSIONS:
        return False, "invalid_dimension"
    if result.get("status") not in LEGAL_STEP_STATUSES:
        return False, "invalid_status"
    if not isinstance(result.get("depends_on"), list):
        return False, "invalid_dependencies"
    if not isinstance(result.get("warnings"), list):
        return False, "invalid_warnings"
    for field in (
        "runtime_kind",
        "implementation_status",
        "binding_source",
        "legacy_agent_id",
        "external_agent_id",
        "invoke_enabled",
        "live_verified",
    ):
        if field not in result:
            return False, f"missing_{field}"
    if not isinstance(result.get("invoke_enabled"), bool):
        return False, "invalid_invoke_enabled"
    if not isinstance(result.get("live_verified"), bool):
        return False, "invalid_live_verified"
    binding = binding_by_agent_id(str(result["agent_id"]))
    expected = {
        "runtime_kind": binding["runtime_kind"],
        "implementation_status": binding["implementation_status"],
        "legacy_agent_id": binding["legacy_agent_id"],
        "external_agent_id": binding["external_agent_id"],
        "invoke_enabled": binding["invoke_enabled_by_default"],
        "live_verified": binding["live_verified"],
    }
    for field, expected_value in expected.items():
        if result.get(field) != expected_value:
            return False, f"binding_metadata_mismatch:{field}"
    return True, "ok"


def build_initial_step_results(plan: Mapping[str, Any]) -> dict[str, dict]:
    return {
        str(step["id"]): build_step_result(
            step,
            status="blocked",
            summary="此步骤尚未进入本轮研判流程。",
        )
        for step in _steps(plan)
        if step.get("id")
    }


def _output_ref_for_step(step: Mapping[str, Any]) -> str:
    agent_id = str(step.get("agent_id") or "")
    stage = str(step.get("stage") or "")
    dimension = str(step.get("dimension") or "")
    if agent_id == "route_planner":
        return "fixed_dag_plan"
    if agent_id == "entity_relation_extractor":
        return "entity_relation_bundle"
    if agent_id == "financial_data_service":
        return "data_bundle"
    if stage == "l2_analysis":
        return f"l2_conclusions.{agent_id}"
    if stage == "dimension_composite":
        return f"dimension_results.{dimension}"
    if agent_id == "decision_synthesizer":
        return "decision_result"
    if agent_id == "report_generator":
        return "report_result"
    return ""


def _status_for_step(step: Mapping[str, Any]) -> str:
    return "complete" if step.get("agent_id") == "route_planner" else "pending_implementation"


def _summary_for_step(step: Mapping[str, Any]) -> str:
    if step.get("agent_id") == "route_planner":
        return "已组织本轮研判流程。"
    return "已按本地固定流程记录本轮处理结果。"


def _execution_plan_or_fallback(
    plan: Mapping[str, Any],
    *,
    question: str,
    as_of: str,
) -> tuple[Mapping[str, Any], bool, str]:
    valid, reason = validate_dag_steps(plan)
    if valid:
        return plan, False, "ok"
    fallback = normalize_fixed_dag_plan(
        {
            "schema": FIXED_DAG_SCHEMA_VERSION,
            "plan_id": plan.get("plan_id") if isinstance(plan, Mapping) else "",
            "user_text": question,
            "as_of": as_of,
        }
    )
    fallback["provenance"] = {
        **fallback["provenance"],
        "source": "fallback_deterministic_fixed_dag_plan",
        "fallback_reason": reason,
    }
    return fallback, True, reason


def execute_fixed_dag_plan(
    plan: Mapping[str, Any],
    *,
    question: str,
    as_of: str,
) -> dict:
    """Execute a fixed DAG plan deterministically without live agent calls."""
    execution_plan, fallback_used, fallback_reason = _execution_plan_or_fallback(
        plan,
        question=question,
        as_of=as_of,
    )
    valid, reason = validate_dag_steps(execution_plan)
    if not valid:
        execution_plan = build_default_fixed_dag_plan(question, as_of=as_of)
        fallback_used = True
        fallback_reason = reason

    batches = topological_batches(execution_plan)
    step_index = build_dag_step_index(execution_plan)
    step_results: dict[str, dict] = {}
    for batch in batches:
        for step_id in batch:
            step = step_index[step_id]
            step_results[step_id] = build_step_result(
                step,
                status=_status_for_step(step),
                output_ref=_output_ref_for_step(step),
                summary=_summary_for_step(step),
            )

    l2_conclusions = build_l2_conclusions(execution_plan, as_of=as_of)
    dimension_results = build_dimension_results(l2_conclusions, as_of=as_of)
    decision_result = build_decision_result(dimension_results, as_of=as_of)
    report_result = build_report_result(decision_result, question=question)
    limitations = [
        "当前为本地固定流程模式。",
        "高级连接状态可在设置诊断中查看。",
    ]
    if fallback_used:
        limitations.append(f"无效计划已回退到确定性默认计划：{fallback_reason}。")

    execution_core = {
        "schema_version": FIXED_DAG_EXECUTION_SCHEMA_VERSION,
        "plan_id": str(execution_plan.get("plan_id") or "reset-fixed-dag-plan-v1"),
        "status": "degraded" if fallback_used else "complete",
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason if fallback_used else "",
        "execution_batches": batches,
        "step_results": step_results,
        "l2_conclusions": l2_conclusions,
        "dimension_results": dimension_results,
        "decision_result": decision_result,
        "report_result": report_result,
        "limitations": limitations,
        "provenance": {
            "source": "fixed_dag_executor",
            "provider_invoked": False,
            "external_invoked": False,
        },
    }
    workflow_snapshot = build_workflow_snapshot_v2(
        plan=execution_plan,
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
        decision_result=decision_result,
        report_result=report_result,
        dag_execution=execution_core,
        step_results=step_results,
        execution_batches=batches,
        current_stage="report",
    )
    return {**execution_core, "workflow_snapshot": workflow_snapshot}


def validate_dag_execution_result(result: Mapping[str, Any]) -> tuple[bool, str]:
    if result.get("schema_version") != FIXED_DAG_EXECUTION_SCHEMA_VERSION:
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

    dimension_results = result.get("dimension_results")
    if not isinstance(dimension_results, Mapping) or set(dimension_results) != set(DIMENSION_GROUPS):
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
    workflow = result.get("workflow_snapshot")
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
