# ruff: noqa: D101, D103
"""Workflow snapshot v2, final emit, and multi-agent bundle builders.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from react_agent.fixed_dag.constants import (
    AGENT_DIMENSIONS,
    CONCLUSION_OBJECT_SCHEMA_VERSION,
    DECISION_RESULT_SCHEMA_VERSION,
    DEFAULT_AS_OF,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_COMPOSITE_SCHEMA_VERSION,
    DIMENSION_GROUPS,
    EXECUTED_STEP_STATUSES,
    FIXED_DAG_SCHEMA_VERSION,
    FIXED_DAG_STAGE_ORDER,
    L2_CONCLUSION_AGENT_IDS,
    L3_COMPOSITE_AGENT_IDS,
    L4_AGENT_IDS,
    REPORT_RESULT_SCHEMA_VERSION,
    RESET_SOURCE,
    WORKFLOW_SNAPSHOT_SCHEMA_VERSION,
)
from react_agent.fixed_dag.labels import (
    AGENT_TITLE_LABELS,
    DIMENSION_TITLE_LABELS,
    STAGE_TITLE_LABELS,
)
from react_agent.fixed_dag.safety import (
    _contains_legacy_key,
    _safe_public_text,
)
from react_agent.fixed_dag.types import (
    FixedDagPlan,
    FixedDagStage,
    FixedDagStep,
)

# Lazy import to avoid circular deps
import importlib
def _plan_validate_fixed_dag_plan(plan):
    return importlib.import_module(
        'react_agent.fixed_dag.contracts.plan'
    ).validate_fixed_dag_plan(plan)
def _plan_validate_selected_fixed_dag_plan(plan):
    return importlib.import_module(
        'react_agent.fixed_dag.contracts.plan'
    ).validate_selected_fixed_dag_plan(plan)

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


def _dimension_group_summary(
    dimension: str,
    result: Mapping[str, Any] | None,
) -> str:
    """Build a public-safe dimension group summary from dimension result data.

    The summary must not contain tokens listed in the frontend's
    USER_COPY_FORBIDDEN_TOKENS (e.g. \"置信度\", \"买入\", \"目标价\")
    so it passes isPublicSafeCopy and can be rendered in the thought-chain
    dimension area.
    """
    if not isinstance(result, Mapping):
        return "维度综合尚未开始。"
    contributing = result.get("contributing_agents")
    if isinstance(contributing, list):
        total = len(contributing)
    else:
        total = 0
    stance = result.get("stance")
    stance_text = str(stance).strip() if isinstance(stance, str) and stance.strip() else "not_evaluated"
    status = str(result.get("status") or "").strip()
    if status in ("pending_implementation", ""):
        if total > 0:
            return f"综合{stance_text}，基于 {total} 个成员分析线索。"
        return f"当前{stance_text}，等待维度成员完成分析。"
    if total > 0:
        return f"综合{stance_text}，基于 {total} 个成员分析线索。"
    if dimension == "risk":
        gate = result.get("gate") or result.get("stance") or "pass"
        return f"风险门 {gate}。"
    if dimension == "macro":
        regime = result.get("regime") or "not_evaluated"
        return f"宏观状态 {regime}。"
    return f"综合{stance_text}。"


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
    plan_valid, _plan_reason = _plan_validate_fixed_dag_plan(plan)
    selected_plan_valid, _selected_plan_reason = _plan_validate_selected_fixed_dag_plan(plan)
    normalized_plan = (
        cast(FixedDagPlan, plan)
        if plan_valid or selected_plan_valid
        else normalize_fixed_dag_plan(plan)
    )
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
    dimension_group_ids = [
        dimension
        for dimension in DIMENSION_GROUPS
        if dimension in normalized_plan.get("dimension_groups", {})
    ]
    plan_provenance = normalized_plan.get("provenance", {})
    plan_provenance = plan_provenance if isinstance(plan_provenance, Mapping) else {}
    execution_provenance = (
        dag_execution.get("provenance", {})
        if isinstance(dag_execution, Mapping)
        and isinstance(dag_execution.get("provenance"), Mapping)
        else {}
    )
    performance_telemetry = (
        dict(execution_provenance.get("performance_telemetry", {}))
        if isinstance(execution_provenance.get("performance_telemetry"), Mapping)
        and execution_provenance.get("performance_telemetry")
        else {}
    )
    if isinstance(plan_provenance.get("route_planner_ms"), int):
        performance_telemetry["routePlannerMs"] = max(
            0,
            int(plan_provenance.get("route_planner_ms")),
        )
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
        "summary": _dimension_group_summary(
            dimension,
            dimension_results.get(dimension) if isinstance(dimension_results, Mapping) else None,
        ),
            }
            for dimension in dimension_group_ids
        ],
        "currentStage": stage,
        "completedSteps": completed,
        "executionBatches": execution_batches or [],
        "stepResults": dict(step_results or {}),
        "provenance": {
            "source": RESET_SOURCE,
            "providerInvoked": bool(
                execution_provenance.get("provider_invoked")
            )
            if execution_provenance
            else False,
            "externalInvoked": bool(
                execution_provenance.get("external_invoked")
            )
            if execution_provenance
            else False,
            "executionStatus": str(dag_execution.get("status"))
            if isinstance(dag_execution, Mapping) and dag_execution.get("status")
            else "not_started",
            "fallbackUsed": bool(dag_execution.get("fallback_used"))
            if isinstance(dag_execution, Mapping)
            else False,
            "limitations": list(dag_execution.get("limitations", []) or [])
            if isinstance(dag_execution, Mapping)
            else [],
            "selectedRoutingRequested": bool(
                plan_provenance.get("selected_routing_requested")
            ),
            "selectedRoutingFallback": bool(
                plan_provenance.get("selected_routing_fallback")
            ),
            "fallbackReason": _safe_public_text(
                plan_provenance.get("fallback_reason"),
                limit=120,
            ),
            "routeGranularity": _safe_public_text(
                plan_provenance.get("route_granularity"),
                limit=40,
            ),
            "selectedDimensions": [
                dimension
                for dimension in plan_provenance.get(
                    "selected_dimensions",
                    normalized_plan.get("selected_dimensions", []),
                )
                if isinstance(dimension, str) and dimension in DIMENSION_GROUPS
            ],
            "expandedAgentCount": (
                int(plan_provenance.get("expanded_agent_count"))
                if isinstance(plan_provenance.get("expanded_agent_count"), int)
                else len(normalized_plan.get("target_agent_ids", []) or [])
            ),
            "providerRouterEnabled": bool(
                plan_provenance.get("provider_router_enabled")
            ),
            "providerRouterInvoked": bool(
                plan_provenance.get("provider_router_invoked")
            ),
            "providerRouterMode": _safe_public_text(
                plan_provenance.get("provider_router_mode"),
                limit=40,
            ),
            "providerRouterParseOk": bool(
                plan_provenance.get("provider_router_parse_ok")
            ),
            "providerRouterFallbackReason": _safe_public_text(
                plan_provenance.get("provider_router_fallback_reason"),
                limit=120,
            ),
            "providerRouterErrorCode": _safe_public_text(
                plan_provenance.get("provider_router_error_code"),
                limit=80,
            ),
            "providerRouterSelectedDimensions": [
                dimension
                for dimension in plan_provenance.get(
                    "provider_router_selected_dimensions",
                    [],
                )
                if isinstance(dimension, str) and dimension in DIMENSION_GROUPS
            ],
            "providerRouterAttemptCount": (
                int(plan_provenance.get("provider_router_attempt_count"))
                if isinstance(plan_provenance.get("provider_router_attempt_count"), int)
                else None
            ),
            "providerRouterLastErrorCode": _safe_public_text(
                plan_provenance.get("provider_router_last_error_code"),
                limit=80,
            ),
            "providerRouterOutputShape": _safe_public_text(
                plan_provenance.get("provider_router_output_shape"),
                limit=60,
            ),
            "providerRouterElapsedMs": (
                int(plan_provenance.get("provider_router_elapsed_ms"))
                if isinstance(plan_provenance.get("provider_router_elapsed_ms"), int)
                else None
            ),
            "providerRouterRetryMode": _safe_public_text(
                plan_provenance.get("provider_router_retry_mode"),
                limit=60,
            ),
            "providerRouterParseStage": _safe_public_text(
                plan_provenance.get("provider_router_parse_stage"),
                limit=60,
            ),
            "performanceTelemetry": performance_telemetry or None,
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
    if provenance.get("externalInvoked"):
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
    return {
        "source": RESET_SOURCE,
        "status": "complete",
        "answer": answer,
        "sections": list(report_result.get("sections", []) or []),
        "evidence_cards": list(report_result.get("evidence_cards", []) or []),
        "limitations": list(report_result.get("limitations", []) or []),
    }


def build_emitted_bundle(report_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "answer": str(report_result.get("answer") or ""),
        "summary_source": RESET_SOURCE,
        "confidence": 0.0,
        "sections": list(report_result.get("sections", []) or []),
        "evidence_cards": list(report_result.get("evidence_cards", []) or []),
        "limitations": list(report_result.get("limitations", []) or []),
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
    report_input_bundle: Mapping[str, Any] | None = None,
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
        "report_input_bundle": dict(report_input_bundle or {}),
        "report_result": dict(report_result),
    }


__all__ = sorted(
    name
    for name in globals()
    if not name.startswith("_")
    and name
    not in {
        "Any",
        "Mapping",
        "cast",
        "json",
        "re",
    }
)
