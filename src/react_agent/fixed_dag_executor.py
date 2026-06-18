# ruff: noqa: D103
"""Plan-driven deterministic fixed-DAG executor.

The Phase R3 executor is an orchestration seam only. It validates and walks the
fixed DAG plan and emits deterministic placeholder outputs by default. R8-12
adds an explicit default-off demo bridge for production `/v1/agent/compute`
calls; the bridge is not loaded or used unless the demo flag and allowlist are
set. R8-12D adds default-off LLM report synthesis from the public-safe
report_input_bundle_v1.
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
    build_agent_task_summaries,
    build_agent_tasks_for_plan,
    build_data_bundle,
    build_decision_result,
    build_default_fixed_dag_plan,
    build_dimension_results,
    build_entity_relation_bundle,
    build_l2_conclusions,
    build_report_input_bundle,
    build_report_result,
    build_workflow_snapshot_v2,
    normalize_fixed_dag_plan,
    validate_decision_result,
    validate_dimension_composite_result,
    validate_fixed_dag_plan,
    validate_report_input_bundle,
    validate_report_result,
    validate_selected_fixed_dag_plan,
    validate_workflow_snapshot_v2,
)
from react_agent.fixed_dag_llm_placeholders import (
    INTERNAL_LLM_PLACEHOLDER_SOURCE,
    build_l2_conclusions_with_internal_placeholders,
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
    if plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION:
        valid, reason = validate_selected_dag_steps(plan)
    else:
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
        "selected_routing_requested": plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION,
        "selected_routing_fallback": plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION,
    }
    return fallback, True, reason


def _execution_plan_valid(plan: Mapping[str, Any]) -> tuple[bool, str]:
    if plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION:
        return validate_selected_dag_steps(plan)
    return validate_dag_steps(plan)


def _execution_batches(plan: Mapping[str, Any]) -> list[list[str]]:
    if plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION:
        return topological_batches_for_selected_plan(plan)
    return topological_batches(plan)


def _apply_external_compute_step_updates(
    step_results: dict[str, dict],
    *runs: Mapping[str, Any],
) -> None:
    for run in runs:
        updates = run.get("step_updates", {}) if isinstance(run, Mapping) else {}
        if not isinstance(updates, Mapping):
            continue
        for step_id, update in updates.items():
            if step_id not in step_results or not isinstance(update, Mapping):
                continue
            status = str(update.get("status") or "")
            if status:
                step_results[str(step_id)]["status"] = status
            summary = str(update.get("summary") or "")
            if summary:
                step_results[str(step_id)]["summary"] = summary
            warning = str(update.get("warning") or "")
            if warning and warning not in step_results[str(step_id)]["warnings"]:
                step_results[str(step_id)]["warnings"].append(warning)
            agent_task = update.get("agent_task")
            if isinstance(agent_task, Mapping):
                step_results[str(step_id)]["agent_task"] = {
                    key: agent_task[key]
                    for key in (
                        "schema",
                        "schema_version",
                        "agent_id",
                        "display_name",
                        "layer",
                        "dimension",
                        "task_instruction",
                        "target",
                        "as_of",
                        "required_output_schema",
                    )
                    if key in agent_task
                }


def _attach_report_input_bundle_to_step_results(
    step_results: dict[str, dict],
    report_input_bundle: Mapping[str, Any],
) -> None:
    evidence_bundle = report_input_bundle.get("agent_evidence_bundle", {})
    if isinstance(evidence_bundle, Mapping):
        l1_evidence = evidence_bundle.get("l1_evidence", {})
        if isinstance(l1_evidence, Mapping):
            if "financial_data_service" in step_results:
                step_results["financial_data_service"]["agent_evidence"] = {
                    "schema": "agent_evidence_bundle_v1.l1_evidence",
                    "agent_id": "financial_data_service",
                    "status": l1_evidence.get("data_bundle_status", ""),
                    "sources_count": l1_evidence.get("data_sources_count", 0),
                    "summary": "L1 金融数据证据输入状态。",
                }
            if "entity_relation_extractor" in step_results:
                step_results["entity_relation_extractor"]["agent_evidence"] = {
                    "schema": "agent_evidence_bundle_v1.l1_evidence",
                    "agent_id": "entity_relation_extractor",
                    "status": l1_evidence.get("entity_relation_status", ""),
                    "entities_count": l1_evidence.get("entities_count", 0),
                    "relations_count": l1_evidence.get("relations_count", 0),
                    "summary": "L1 实体关系证据输入状态。",
                }
    task_items = report_input_bundle.get("agent_task_summaries", [])
    if isinstance(task_items, list):
        for item in task_items:
            if not isinstance(item, Mapping):
                continue
            step_id = str(item.get("step_id") or "")
            if step_id in step_results:
                step_results[step_id]["agent_task"] = {
                    key: item[key]
                    for key in (
                        "schema",
                        "agent_id",
                        "display_name",
                        "layer",
                        "dimension",
                        "task_instruction",
                        "target",
                        "as_of",
                        "required_output_schema",
                        "upstream_agent_ids",
                        "has_l1_data_bundle",
                        "has_l1_entity_relation_bundle",
                    )
                    if key in item
                }
    l2_items = report_input_bundle.get("l2_agent_summaries", [])
    if isinstance(evidence_bundle, Mapping) and isinstance(
        evidence_bundle.get("l2_agent_outputs"), list
    ):
        l2_items = evidence_bundle["l2_agent_outputs"]
    if isinstance(l2_items, list):
        for item in l2_items:
            if not isinstance(item, Mapping):
                continue
            agent_id = str(item.get("agent_id") or "")
            step_id = f"l2:{agent_id}"
            if step_id in step_results:
                step_results[step_id]["agent_evidence"] = {
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
                        "as_of",
                        "data_as_of",
                        "source",
                        "risk_score",
                        "evidence_count",
                        "detail_notes",
                        "evidence_items",
                        "domain_metrics",
                        "drivers",
                        "research_points",
                        "data_quality",
                        "provenance_notes",
                        "required_output_schema",
                        "received_output_schema",
                    )
                    if key in item
                }
    l3_items = report_input_bundle.get("l3_composite_summaries", [])
    if isinstance(evidence_bundle, Mapping) and isinstance(
        evidence_bundle.get("l3_composite_outputs"), list
    ):
        l3_items = evidence_bundle["l3_composite_outputs"]
    if isinstance(l3_items, list):
        for item in l3_items:
            if not isinstance(item, Mapping):
                continue
            dimension = str(item.get("dimension") or "")
            step_id = f"dimension:{dimension}"
            if step_id in step_results:
                step_results[step_id]["composite_evidence"] = {
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
                        "veto",
                        "penalty",
                        "risk_score",
                        "regime",
                        "dimension_weights",
                        "risk_sensitivity",
                        "as_of",
                        "data_as_of",
                        "source",
                        "evidence_refs",
                        "detail_notes",
                        "domain_metrics",
                        "drivers",
                        "research_points",
                        "data_quality",
                        "provenance_notes",
                        "required_output_schema",
                        "received_output_schema",
                    )
                    if key in item
                }


def _safe_report_value(value: Any, *, limit: int = 80) -> str:
    text = str(value or "").strip()
    text = text.replace("\n", " ").replace("\r", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _dimension_demo_line(label: str, result: Mapping[str, Any] | None) -> str:
    if not isinstance(result, Mapping):
        return f"{label}：本轮没有可用的外部 compute 映射结果。"
    confidence = result.get("confidence", 0.0)
    try:
        confidence_text = f"{float(confidence):.2f}"
    except (TypeError, ValueError):
        confidence_text = "n/a"
    if result.get("dimension") == "risk":
        gate = _safe_report_value(result.get("gate") or result.get("stance") or "risk_gate")
        risk_score = result.get("risk_score", 0.0)
        try:
            risk_text = f"{float(risk_score):.2f}"
        except (TypeError, ValueError):
            risk_text = "n/a"
        return f"{label}：风险门为 {gate}，风险分 {risk_text}，置信度 {confidence_text}。"
    if result.get("dimension") == "macro":
        regime = _safe_report_value(result.get("regime") or result.get("stance") or "macro_regulator")
        weights = result.get("dimension_weights", {})
        if isinstance(weights, Mapping):
            weight_text = ", ".join(
                f"{_safe_report_value(key)}={value}"
                for key, value in weights.items()
                if key in {"value", "market"}
            )
        else:
            weight_text = "n/a"
        return f"{label}：宏观状态 {regime}，value/market 权重 {weight_text}，置信度 {confidence_text}。"
    stance = _safe_report_value(result.get("stance") or "not_evaluated")
    contributors = result.get("contributing_agents", [])
    contributor_text = len(contributors) if isinstance(contributors, list) else 0
    return f"{label}：综合 stance={stance}，参与成员 {contributor_text} 个，置信度 {confidence_text}。"


def _l2_demo_summary_lines(l2_conclusions: Mapping[str, Any]) -> list[str]:
    labels = {
        "value": "估值信号",
        "market": "市场信号",
        "risk": "风险成员",
        "macro": "宏观成员",
    }
    lines: list[str] = []
    for dimension in ("value", "market", "risk", "macro"):
        items = [
            item
            for item in l2_conclusions.values()
            if isinstance(item, Mapping)
            and item.get("dimension") == dimension
            and item.get("status") in {"complete", "partial"}
            and isinstance(item.get("provenance"), Mapping)
            and item["provenance"].get("adapter_source")
        ]
        if not items:
            continue
        sample = items[:3]
        text = "；".join(
            f"{_safe_report_value(item.get('agent_id'))}: "
            f"{_safe_report_value(item.get('stance'))}, "
            f"confidence={item.get('confidence', 0.0)}"
            for item in sample
        )
        suffix = "；..." if len(items) > len(sample) else ""
        lines.append(f"{labels[dimension]}：{text}{suffix}")
    return lines


def _augment_report_with_external_compute_demo(
    report_result: Mapping[str, Any],
    *,
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
    demo_summary: Mapping[str, Any],
) -> dict[str, Any]:
    mapped_agents = [
        str(agent_id)
        for agent_id in demo_summary.get("mapped_agents", [])
        if str(agent_id or "")
    ]
    if not mapped_agents:
        return dict(report_result)

    dimension_lines = [
        _dimension_demo_line("估值综合", cast(Mapping[str, Any] | None, dimension_results.get("value"))),
        _dimension_demo_line("市场综合", cast(Mapping[str, Any] | None, dimension_results.get("market"))),
        _dimension_demo_line("风险闸门", cast(Mapping[str, Any] | None, dimension_results.get("risk"))),
        _dimension_demo_line("宏观调节", cast(Mapping[str, Any] | None, dimension_results.get("macro"))),
    ]
    l2_lines = _l2_demo_summary_lines(l2_conclusions)
    demo_body = "\n".join(
        [
            "本次研判使用固定 DAG 流程，并在演示模式下读取了若干已通过生产 compute smoke 的外部智能体结构化结果。",
            "这些结果只用于演示默认关闭的结构化接入，不代表默认启用或正式生产接入承诺。",
            *l2_lines,
            *dimension_lines,
            "综合结论：当前页面展示的是结构化接入链路和审慎研判框架，仍需业务 owner 对结果含义负责。",
        ]
    )
    answer = str(report_result.get("answer") or "")
    if demo_body not in answer:
        answer = f"{answer}\n\n外部计算演示摘要：\n{demo_body}"
    sections = list(report_result.get("sections", []) or [])
    sections.append(
        {
            "id": "external_compute_demo",
            "title": "外部计算演示",
            "content": demo_body,
        }
    )
    evidence_cards = list(report_result.get("evidence_cards", []) or [])
    evidence_cards.append(
        {
            "title": "外部 compute 演示来源",
            "note": f"本轮映射 {len(mapped_agents)} 个 allowlist agent；未调用 invoke 接口。",
        }
    )
    limitations = list(report_result.get("limitations", []) or [])
    limitation = (
        "外部 compute demo 为显式开关 + allowlist 模式，不改变默认运行配置。"
    )
    if limitation not in limitations:
        limitations.append(limitation)
    return {
        **dict(report_result),
        "answer": answer,
        "status": "partial",
        "sections": sections,
        "evidence_cards": evidence_cards,
        "limitations": limitations,
    }


def execute_fixed_dag_plan(
    plan: Mapping[str, Any],
    *,
    question: str,
    as_of: str,
    context: Any | None = None,
) -> dict:
    """Execute a fixed DAG plan without external agent calls."""
    execution_plan, fallback_used, fallback_reason = _execution_plan_or_fallback(
        plan,
        question=question,
        as_of=as_of,
    )
    valid, reason = _execution_plan_valid(execution_plan)
    if not valid:
        execution_plan = build_default_fixed_dag_plan(question, as_of=as_of)
        fallback_used = True
        fallback_reason = reason

    batches = _execution_batches(execution_plan)
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

    data_bundle = build_data_bundle(execution_plan)
    entity_relation_bundle = build_entity_relation_bundle(execution_plan)
    l2_agent_tasks = build_agent_tasks_for_plan(
        execution_plan,
        question=question,
        as_of=as_of,
        data_bundle=data_bundle,
        entity_relation_bundle=entity_relation_bundle,
    )
    internal_placeholders_enabled = bool(
        getattr(context, "enable_internal_llm_placeholders", False)
    )
    if internal_placeholders_enabled:
        l2_conclusions = build_l2_conclusions_with_internal_placeholders(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            agent_tasks=l2_agent_tasks,
        )
    else:
        l2_conclusions = build_l2_conclusions(execution_plan, as_of=as_of)

    external_compute_demo_enabled = bool(
        getattr(context, "enable_external_compute_demo", False)
    )
    llm_report_synthesis_enabled = bool(
        getattr(context, "enable_llm_report_synthesis", False)
    )
    llm_l3_explanation_enabled = bool(
        getattr(context, "enable_llm_l3_explanation", False)
    )
    external_l1_run: Mapping[str, Any] = {}
    external_l2_run: Mapping[str, Any] = {}
    external_l3_run: Mapping[str, Any] = {}
    external_demo_summary: Mapping[str, Any] = {
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "warnings": [],
    }
    if external_compute_demo_enabled:
        from react_agent.fixed_dag_external_compute_bridge import (  # noqa: PLC0415
            merge_external_compute_demo_runs,
            run_external_compute_for_plan,
        )

        l1_agent_tasks = build_agent_tasks_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
        )
        external_l1_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            l2_conclusions={},
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            agent_tasks=l1_agent_tasks,
            stages=("evidence",),
        )
        data_bundle = cast(dict[str, Any], external_l1_run["data_bundle"])
        entity_relation_bundle = cast(
            dict[str, Any],
            external_l1_run["entity_relation_bundle"],
        )
        l2_agent_tasks = build_agent_tasks_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
        )
        external_l2_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            l2_conclusions=l2_conclusions,
            agent_tasks=l2_agent_tasks,
            stages=("l2_analysis",),
        )
        l2_conclusions = cast(dict[str, Any], external_l2_run["l2_conclusions"])
    dimension_results = build_dimension_results(l2_conclusions, as_of=as_of)
    if external_compute_demo_enabled:
        l3_agent_tasks = build_agent_tasks_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
        )
        external_l3_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            agent_tasks=l3_agent_tasks,
            stages=("dimension_composite",),
        )
        l2_conclusions = cast(dict[str, Any], external_l3_run["l2_conclusions"])
        dimension_results = cast(dict[str, Any], external_l3_run["dimension_results"])
        _apply_external_compute_step_updates(
            step_results,
            external_l1_run,
            external_l2_run,
            external_l3_run,
        )
        external_demo_summary = merge_external_compute_demo_runs(
            external_l1_run,
            external_l2_run,
            external_l3_run,
        )
    llm_l3_explanation_used = False
    llm_l3_explanation_attempted = False
    llm_l3_explanation_provider_invoked = False
    llm_l3_explanation_fallback_reason = ""
    llm_l3_explanation_provider_config: dict[str, Any] = {}
    if llm_l3_explanation_enabled:
        from react_agent.fixed_dag_l3_explanation_synthesizer import (  # noqa: PLC0415
            synthesize_l3_explanations,
        )

        l3_explanation_outcome = synthesize_l3_explanations(
            question=question,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            context=context,
        )
        dimension_results = cast(dict[str, Any], l3_explanation_outcome["dimension_results"])
        llm_l3_explanation_used = bool(l3_explanation_outcome["used_llm_explanation"])
        llm_l3_explanation_attempted = bool(l3_explanation_outcome["attempted"])
        llm_l3_explanation_provider_invoked = bool(l3_explanation_outcome["provider_invoked"])
        llm_l3_explanation_fallback_reason = str(l3_explanation_outcome["fallback_reason"])
        llm_l3_explanation_provider_config = dict(l3_explanation_outcome["provider_config"])
    decision_result = build_decision_result(dimension_results, as_of=as_of)
    agent_tasks = build_agent_tasks_for_plan(
        execution_plan,
        question=question,
        as_of=as_of,
        data_bundle=data_bundle,
        entity_relation_bundle=entity_relation_bundle,
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
        decision_result=decision_result,
    )
    report_input_bundle = build_report_input_bundle(
        question=question,
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
        decision_result=decision_result,
        agent_tasks=agent_tasks,
        data_bundle=data_bundle,
        entity_relation_bundle=entity_relation_bundle,
    )
    valid_report_input_bundle, _report_input_bundle_reason = validate_report_input_bundle(
        report_input_bundle
    )
    if valid_report_input_bundle:
        _attach_report_input_bundle_to_step_results(step_results, report_input_bundle)
    report_result = build_report_result(
        decision_result,
        question=question,
        report_input_bundle=report_input_bundle,
    )
    if external_compute_demo_enabled:
        report_result = _augment_report_with_external_compute_demo(
            report_result,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            demo_summary=external_demo_summary,
        )
    llm_report_synthesis_used = False
    llm_report_synthesis_attempted = False
    llm_report_synthesis_provider_invoked = False
    llm_report_synthesis_fallback_reason = ""
    llm_report_synthesis_provider_config: dict[str, Any] = {}
    if llm_report_synthesis_enabled:
        from react_agent.fixed_dag_report_synthesizer import (  # noqa: PLC0415
            synthesize_report_result_with_llm,
        )

        synthesis_outcome = synthesize_report_result_with_llm(
            question=question,
            report_input_bundle=report_input_bundle,
            fallback_report_result=report_result,
            context=context,
        )
        report_result = synthesis_outcome["report_result"]
        llm_report_synthesis_used = bool(synthesis_outcome["used_llm_report"])
        llm_report_synthesis_attempted = bool(synthesis_outcome["attempted"])
        llm_report_synthesis_provider_invoked = bool(synthesis_outcome["provider_invoked"])
        llm_report_synthesis_fallback_reason = str(synthesis_outcome["fallback_reason"])
        llm_report_synthesis_provider_config = dict(synthesis_outcome["provider_config"])
    internal_placeholder_count = sum(
        1
        for item in l2_conclusions.values()
        if isinstance(item, Mapping)
        and isinstance(item.get("provenance"), Mapping)
        and item["provenance"].get("runtime_path") == INTERNAL_LLM_PLACEHOLDER_SOURCE
    )
    limitations = [
        "当前为本地固定流程模式。",
        "高级连接状态可在设置诊断中查看。",
    ]
    if external_compute_demo_enabled:
        if external_demo_summary.get("mapped_agents"):
            limitations.append(
                "已在显式演示开关 + allowlist 下读取部分生产 /compute 结构化结果；"
                "这不是默认运行配置变更。"
            )
        else:
            limitations.append(
                "external compute demo 演示开关已开启，但没有 allowlist agent 完成映射；"
                "执行已回退到本地固定流程。"
            )
    if llm_report_synthesis_enabled:
        if llm_report_synthesis_used:
            limitations.append(
                "已在显式演示开关下使用大模型读取结构化报告输入包生成最终报告；"
                "这不是默认运行配置变更。"
            )
        else:
            limitations.append(
                "大模型报告综合开关已开启，但未生成有效报告，已回退到模板报告。"
            )
    if llm_l3_explanation_enabled:
        if llm_l3_explanation_used:
            limitations.append(
                "已在显式演示开关下使用大模型补充 L3 综合解释；"
                "该解释不覆盖确定性 L3 stance、gate、risk_score、权重或状态。"
            )
        else:
            limitations.append(
                "L3 大模型解释开关已开启，但未生成有效解释，已保留确定性 L3 结果。"
            )
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
        "data_bundle": data_bundle,
        "entity_relation_bundle": entity_relation_bundle,
        "l2_conclusions": l2_conclusions,
        "dimension_results": dimension_results,
        "decision_result": decision_result,
        "agent_task_summaries": build_agent_task_summaries(agent_tasks),
        "report_input_bundle": report_input_bundle,
        "report_result": report_result,
        "limitations": limitations,
        "provenance": {
            "source": "fixed_dag_executor",
            "provider_invoked": (
                llm_report_synthesis_provider_invoked
                or llm_l3_explanation_provider_invoked
            ),
            "external_invoked": False,
            "internal_llm_placeholders_enabled": internal_placeholders_enabled,
            "internal_llm_placeholder_conclusions": internal_placeholder_count,
            "external_compute_demo_enabled": external_compute_demo_enabled,
            "external_compute_demo_called_agents": list(
                external_demo_summary.get("called_agents", [])
            ),
            "external_compute_demo_mapped_agents": list(
                external_demo_summary.get("mapped_agents", [])
            ),
            "external_compute_demo_failed_agents": list(
                external_demo_summary.get("failed_agents", [])
            ),
            "llm_report_synthesis_enabled": llm_report_synthesis_enabled,
            "llm_report_synthesis_attempted": llm_report_synthesis_attempted,
            "llm_report_synthesis_used": llm_report_synthesis_used,
            "llm_report_synthesis_fallback_reason": llm_report_synthesis_fallback_reason,
            "llm_report_synthesis_provider_config": llm_report_synthesis_provider_config,
            "llm_l3_explanation_enabled": llm_l3_explanation_enabled,
            "llm_l3_explanation_attempted": llm_l3_explanation_attempted,
            "llm_l3_explanation_used": llm_l3_explanation_used,
            "llm_l3_explanation_fallback_reason": llm_l3_explanation_fallback_reason,
            "llm_l3_explanation_provider_config": llm_l3_explanation_provider_config,
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
