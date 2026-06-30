# ruff: noqa: D103
"""Fixed-DAG reset runtime graph.

Phase R3 replaces the previous mode-based Router/Manager/Fusion runtime with one
plan-driven deterministic skeleton DAG. The skeleton does not call a provider,
search, or any external agent endpoint; it only exercises the reset protocol and
execution seams.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    build_data_bundle,
    build_decision_result,
    build_default_dimension_route_intent,
    build_default_fixed_dag_plan,
    build_dimension_results,
    build_emitted_bundle,
    build_entity_relation_bundle,
    build_final_emit_payload,
    build_l2_conclusions,
    build_report_input_bundle,
    build_report_result,
    build_reset_multi_agent_bundle,
    build_workflow_snapshot_v2,
    compile_selected_fixed_dag_plan,
)
from react_agent.fixed_dag_executor import execute_fixed_dag_plan
from react_agent.graph_entry import compile_graph_variants, select_graph_for_invoke
from react_agent.router_parse import parse_dimension_route_intent_json
from react_agent.state import InputState, State

_GRAPH_NAME = "Fixed DAG Reset Skeleton"


def _message_text(message: Any) -> str:
    if isinstance(message, tuple) and len(message) >= 2:
        return str(message[1] or "").strip()
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return "\n".join(parts).strip()
    return str(content or "").strip()


def _is_user_message(message: Any) -> bool:
    if isinstance(message, tuple) and len(message) >= 1:
        return str(message[0]).lower() in {"user", "human"}
    role = getattr(message, "type", None) or getattr(message, "role", None)
    return str(role).lower() in {"human", "user"}


def _latest_user_question(state: State) -> str:
    messages = list(state.get("messages", []) or [])
    for message in reversed(messages):
        if _is_user_message(message):
            return _message_text(message)
    for message in reversed(messages):
        text = _message_text(message)
        if text:
            return text
    return ""


def _completed_from_stage(plan: dict[str, Any], stage_key: str) -> list[str]:
    return [
        str(step.get("id"))
        for step in plan.get("steps", [])
        if str(step.get("stage")) == stage_key and step.get("id")
    ]


def _context_fixed_dag_as_of(context: Context | None) -> str | None:
    if context is None:
        return None
    text = str(getattr(context, "fixed_dag_as_of", "") or "").strip()
    return text or None


def _is_llm_dimension_router_enabled(context: Context | None) -> bool:
    return bool(
        context is not None
        and getattr(context, "enable_llm_dimension_router", False)
    )


def _provider_router_provenance(
    *,
    enabled: bool,
    invoked: bool = False,
    parse_ok: bool = False,
    fallback_reason: str = "",
    selected_dimensions: list[str] | None = None,
    error_code: str = "",
) -> dict[str, Any]:
    return {
        "provider_router_enabled": enabled,
        "provider_router_invoked": invoked,
        "provider_router_mode": "fake" if enabled else "",
        "provider_router_parse_ok": parse_ok,
        "provider_router_fallback_reason": fallback_reason,
        "provider_router_selected_dimensions": list(selected_dimensions or []),
        "provider_router_error_code": error_code,
    }


def _safe_provider_router_reason(stats_reason: str | None) -> str:
    reason = str(stats_reason or "").strip()
    if not reason:
        return "router_provider_parse_failed"
    if reason.startswith("json_decode_error:"):
        return "router_provider_invalid_json"
    if reason == "missing_json":
        return "router_provider_missing_output"
    if reason == "not_object":
        return "router_provider_non_object"
    return reason


def _invoke_dimension_router_provider(
    question: str,
    context: Context | None,
) -> str | None:
    """Fake-provider seam for tests; real provider wiring is intentionally absent."""
    del question, context
    return None


def _route_intent_from_llm_dimension_provider(
    question: str,
    context: Context | None,
) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    meta = _provider_router_provenance(enabled=True)
    try:
        raw_output = _invoke_dimension_router_provider(question, context)
    except TimeoutError:
        return None, {
            **meta,
            "provider_router_invoked": True,
            "provider_router_fallback_reason": "router_provider_timeout",
            "provider_router_error_code": "router_provider_timeout",
        }
    except Exception:
        return None, {
            **meta,
            "provider_router_invoked": True,
            "provider_router_fallback_reason": "router_provider_exception",
            "provider_router_error_code": "router_provider_exception",
        }

    if not isinstance(raw_output, str) or not raw_output.strip():
        return None, {
            **meta,
            "provider_router_invoked": bool(raw_output is not None),
            "provider_router_fallback_reason": "router_provider_missing_output",
            "provider_router_error_code": "router_provider_unavailable"
            if raw_output is None
            else "router_provider_missing_output",
        }
    stripped = raw_output.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return None, {
            **meta,
            "provider_router_invoked": True,
            "provider_router_fallback_reason": "router_provider_invalid_json",
            "provider_router_error_code": "router_provider_invalid_json",
        }

    route_intent, stats = parse_dimension_route_intent_json(
        stripped,
        question=question,
    )
    parse_ok = bool(stats.get("parse_ok") and not stats.get("used_fallback"))
    selected_dimensions = [
        str(item)
        for item in stats.get("selected_dimensions", [])
        if isinstance(item, str)
    ]
    fallback_reason = _safe_provider_router_reason(stats.get("fallback_reason"))
    if not parse_ok or route_intent.get("needs_clarification"):
        return None, {
            **meta,
            "provider_router_invoked": True,
            "provider_router_parse_ok": False,
            "provider_router_fallback_reason": fallback_reason,
            "provider_router_selected_dimensions": selected_dimensions,
            "provider_router_error_code": fallback_reason,
        }
    route_intent = dict(route_intent)
    route_intent["provenance"] = {
        "source": "fake_llm_dimension_router",
        "normalizer": "m1d_fake_provider_dimension_router",
        "route_granularity": "dimension",
        "dimension_only": True,
        "provider_invoked": False,
        "external_invoked": False,
    }
    return route_intent, {
        **meta,
        "provider_router_invoked": True,
        "provider_router_parse_ok": True,
        "provider_router_selected_dimensions": list(
            route_intent.get("selected_dimensions", []) or []
        ),
    }


def _full_plan_with_selected_fallback_provenance(
    question: str,
    reason: str,
    *,
    as_of: str | None = None,
    provider_router: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = build_default_fixed_dag_plan(question, as_of=as_of)
    plan["provenance"] = {
        **plan["provenance"],
        "selected_routing_requested": True,
        "selected_routing_fallback": True,
        "fallback_reason": reason,
        "route_granularity": "dimension",
        "selected_dimensions": [],
        "expanded_agent_count": len(plan.get("target_agent_ids", []) or []),
        "provider_invoked": False,
        "external_invoked": False,
        **dict(provider_router or {}),
    }
    return plan


def _route_plan_for_context(question: str, context: Context | None) -> dict[str, Any]:
    as_of = _context_fixed_dag_as_of(context)
    if context is None or not context.enable_selected_routing:
        plan = build_default_fixed_dag_plan(question, as_of=as_of)
        if _is_llm_dimension_router_enabled(context):
            plan["provenance"] = {
                **plan["provenance"],
                **_provider_router_provenance(
                    enabled=True,
                    fallback_reason="selected_routing_disabled",
                ),
            }
        return plan
    provider_router = _provider_router_provenance(
        enabled=_is_llm_dimension_router_enabled(context)
    )
    try:
        if _is_llm_dimension_router_enabled(context):
            route_intent, provider_router = _route_intent_from_llm_dimension_provider(
                question,
                context,
            )
            if route_intent is None:
                return _full_plan_with_selected_fallback_provenance(
                    question,
                    str(
                        provider_router.get("provider_router_fallback_reason")
                        or "router_provider_unavailable"
                    ),
                    as_of=as_of,
                    provider_router=provider_router,
                )
        else:
            route_intent = build_default_dimension_route_intent(question)
        plan = compile_selected_fixed_dag_plan(route_intent, user_text=question, as_of=as_of)
    except Exception as exc:
        return _full_plan_with_selected_fallback_provenance(
            question,
            f"selected_routing_compile_failed:{type(exc).__name__}",
            as_of=as_of,
            provider_router=provider_router,
        )
    plan["provenance"] = {
        **plan["provenance"],
        "selected_routing_requested": True,
        "selected_routing_fallback": False,
        "route_granularity": "dimension",
        "selected_dimensions": list(plan.get("selected_dimensions", []) or []),
        "expanded_agent_count": len(plan.get("target_agent_ids", []) or []),
        "provider_invoked": False,
        "external_invoked": False,
        **provider_router,
    }
    return plan


def route_planner_node(
    state: State,
    runtime: Runtime[Context] | None = None,
) -> dict[str, Any]:
    question = _latest_user_question(state)
    plan = _route_plan_for_context(question, runtime.context if runtime is not None else None)
    completed = _completed_from_stage(plan, "planning")
    return {
        "run_id": str(state.get("run_id") or uuid.uuid4()),
        "current_question": question,
        "fixed_dag_plan": plan,
        "workflow_snapshot": build_workflow_snapshot_v2(
            plan=plan,
            current_stage="planning",
            completed_steps=completed,
        ),
        "thread_summary": "Fixed DAG reset skeleton planning completed.",
        "stable_findings": [],
    }


def prepare_l1_context_node(state: State) -> dict[str, Any]:
    plan = state["fixed_dag_plan"]
    completed = [
        *_completed_from_stage(plan, "planning"),
        *_completed_from_stage(plan, "evidence"),
    ]
    return {
        "entity_relation_bundle": build_entity_relation_bundle(plan),
        "data_bundle": build_data_bundle(plan),
        "workflow_snapshot": build_workflow_snapshot_v2(
            plan=plan,
            current_stage="evidence",
            completed_steps=completed,
        ),
        "thread_summary": "L1 evidence seams prepared as reset placeholders.",
    }


def execute_fixed_dag_node(
    state: State,
    runtime: Runtime[Context] | None = None,
) -> dict[str, Any]:
    plan = state["fixed_dag_plan"]
    execution = execute_fixed_dag_plan(
        plan,
        question=str(state.get("current_question", "") or ""),
        as_of=str(plan.get("as_of") or "not_available"),
        context=runtime.context if runtime is not None else None,
    )
    return {
        "dag_execution": execution,
        "dag_step_results": execution["step_results"],
        "execution_batches": execution["execution_batches"],
        "l2_conclusions": execution["l2_conclusions"],
        "dimension_results": execution["dimension_results"],
        "decision_result": execution["decision_result"],
        "report_input_bundle": execution["report_input_bundle"],
        "report_result": execution["report_result"],
        "workflow_snapshot": execution["workflow_snapshot"],
        "thread_summary": "Fixed DAG executor completed deterministic topological orchestration.",
    }


def run_l2_conclusions_node(state: State) -> dict[str, Any]:
    plan = state["fixed_dag_plan"]
    completed = [
        *_completed_from_stage(plan, "planning"),
        *_completed_from_stage(plan, "evidence"),
        *_completed_from_stage(plan, "l2_analysis"),
    ]
    conclusions = build_l2_conclusions(plan)
    return {
        "l2_conclusions": conclusions,
        "workflow_snapshot": build_workflow_snapshot_v2(
            plan=plan,
            current_stage="l2_analysis",
            completed_steps=completed,
        ),
        "thread_summary": "L2 conclusion placeholders completed.",
    }


def run_dimension_composites_node(state: State) -> dict[str, Any]:
    plan = state["fixed_dag_plan"]
    conclusions = state.get("l2_conclusions", {})
    dimension_results = build_dimension_results(conclusions, as_of=plan.get("as_of"))
    completed = [
        *_completed_from_stage(plan, "planning"),
        *_completed_from_stage(plan, "evidence"),
        *_completed_from_stage(plan, "l2_analysis"),
        *_completed_from_stage(plan, "dimension_composite"),
    ]
    return {
        "dimension_results": dimension_results,
        "workflow_snapshot": build_workflow_snapshot_v2(
            plan=plan,
            current_stage="dimension_composite",
            completed_steps=completed,
            dimension_results=dimension_results,
        ),
        "thread_summary": "L3 dimension composites completed as deterministic placeholders.",
    }


def decision_synthesizer_node(state: State) -> dict[str, Any]:
    plan = state["fixed_dag_plan"]
    dimension_results = state.get("dimension_results", {})
    completed = [
        *_completed_from_stage(plan, "planning"),
        *_completed_from_stage(plan, "evidence"),
        *_completed_from_stage(plan, "l2_analysis"),
        *_completed_from_stage(plan, "dimension_composite"),
        *_completed_from_stage(plan, "decision"),
    ]
    decision = build_decision_result(dimension_results, as_of=plan.get("as_of"))
    return {
        "decision_result": decision,
        "workflow_snapshot": build_workflow_snapshot_v2(
            plan=plan,
            current_stage="decision",
            completed_steps=completed,
            dimension_results=dimension_results,
        ),
        "thread_summary": "Decision synthesizer placeholder completed.",
    }


def report_generator_node(state: State) -> dict[str, Any]:
    plan = state["fixed_dag_plan"]
    l2_conclusions = state.get("l2_conclusions", {})
    dimension_results = state.get("dimension_results", {})
    decision = state.get("decision_result", build_decision_result(dimension_results))
    report_input_bundle = build_report_input_bundle(
        question=str(state.get("current_question", "") or ""),
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
        decision_result=decision,
    )
    completed = [
        *_completed_from_stage(plan, "planning"),
        *_completed_from_stage(plan, "evidence"),
        *_completed_from_stage(plan, "l2_analysis"),
        *_completed_from_stage(plan, "dimension_composite"),
        *_completed_from_stage(plan, "decision"),
        *_completed_from_stage(plan, "report"),
    ]
    report = build_report_result(
        decision,
        question=str(state.get("current_question", "") or ""),
        report_input_bundle=report_input_bundle,
    )
    return {
        "report_input_bundle": report_input_bundle,
        "report_result": report,
        "workflow_snapshot": build_workflow_snapshot_v2(
            plan=plan,
            current_stage="report",
            completed_steps=completed,
            dimension_results=dimension_results,
            report_result=report,
        ),
        "thread_summary": "Report generator placeholder completed.",
    }


def final_emit_node(state: State) -> dict[str, Any]:
    report = state.get("report_result", {})
    answer = str(report.get("answer", "") or "").strip()
    if not answer:
        answer = "研判流程已完成，但没有报告正文。"
    report = {**report, "answer": answer}
    return {
        "final_emit_payload": build_final_emit_payload(report),
        "emitted_bundle": build_emitted_bundle(report),
        "multi_agent_bundle": build_reset_multi_agent_bundle(
            fixed_dag_plan=state.get("fixed_dag_plan", {}),
            data_bundle=state.get("data_bundle", {}),
            entity_relation_bundle=state.get("entity_relation_bundle", {}),
            dag_execution=state.get("dag_execution", {}),
            dag_step_results=state.get("dag_step_results", {}),
            execution_batches=state.get("execution_batches", []),
            l2_conclusions=state.get("l2_conclusions", {}),
            dimension_results=state.get("dimension_results", {}),
            decision_result=state.get("decision_result", {}),
            report_input_bundle=state.get("report_input_bundle", {}),
            report_result=report,
        ),
        "final_answer_source": "reset_skeleton",
        "messages": [AIMessage(content=answer)],
        "is_last_step": True,
        "thread_summary": "Fixed DAG reset skeleton final answer emitted.",
    }


def memory_update_node(state: State) -> dict[str, Any]:
    del state
    return {}


builder = StateGraph(State, input_schema=InputState, context_schema=Context)
builder.add_node("route_planner", route_planner_node)
builder.add_node("prepare_l1_context", prepare_l1_context_node)
builder.add_node("execute_fixed_dag", execute_fixed_dag_node)
builder.add_node("final_emit", final_emit_node)
builder.add_node("memory_update", memory_update_node)

builder.add_edge(START, "route_planner")
builder.add_edge("route_planner", "prepare_l1_context")
builder.add_edge("prepare_l1_context", "execute_fixed_dag")
builder.add_edge("execute_fixed_dag", "final_emit")
builder.add_edge("final_emit", "memory_update")
builder.add_edge("memory_update", END)

graph, graph_persistent = compile_graph_variants(builder, _GRAPH_NAME)


def get_graph_for_invoke(thread_id: str | None = None) -> Any:
    return select_graph_for_invoke(thread_id, graph, graph_persistent)


__all__ = [
    "builder",
    "graph",
    "graph_persistent",
    "get_graph_for_invoke",
    "route_planner_node",
    "prepare_l1_context_node",
    "execute_fixed_dag_node",
    "run_l2_conclusions_node",
    "run_dimension_composites_node",
    "decision_synthesizer_node",
    "report_generator_node",
    "final_emit_node",
]
