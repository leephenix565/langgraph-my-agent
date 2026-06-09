# ruff: noqa: D103
"""Fixed-DAG reset runtime graph.

Phase R3 replaces the previous mode-based Router/Manager/Fusion runtime with one
plan-driven deterministic skeleton DAG. The skeleton does not call a provider,
search, or any external agent endpoint; it only exercises the reset protocol and
execution seams.
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    build_data_bundle,
    build_decision_result,
    build_default_fixed_dag_plan,
    build_default_route_intent,
    build_dimension_results,
    build_emitted_bundle,
    build_entity_relation_bundle,
    build_final_emit_payload,
    build_l2_conclusions,
    build_report_result,
    build_reset_multi_agent_bundle,
    build_workflow_snapshot_v2,
    compile_selected_fixed_dag_plan,
)
from react_agent.fixed_dag_executor import execute_fixed_dag_plan
from react_agent.graph_entry import compile_graph_variants, select_graph_for_invoke
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


def _full_plan_with_selected_fallback_provenance(question: str, reason: str) -> dict[str, Any]:
    plan = build_default_fixed_dag_plan(question)
    plan["provenance"] = {
        **plan["provenance"],
        "selected_routing_requested": True,
        "selected_routing_fallback": True,
        "fallback_reason": reason,
        "provider_invoked": False,
        "external_invoked": False,
    }
    return plan


def _route_plan_for_context(question: str, context: Context | None) -> dict[str, Any]:
    if context is None or not context.enable_selected_routing:
        return build_default_fixed_dag_plan(question)
    try:
        route_intent = build_default_route_intent(question)
        plan = compile_selected_fixed_dag_plan(route_intent, user_text=question)
    except Exception as exc:
        return _full_plan_with_selected_fallback_provenance(
            question,
            f"selected_routing_compile_failed:{type(exc).__name__}",
        )
    plan["provenance"] = {
        **plan["provenance"],
        "selected_routing_requested": True,
        "selected_routing_fallback": False,
        "provider_invoked": False,
        "external_invoked": False,
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
    dimension_results = state.get("dimension_results", {})
    decision = state.get("decision_result", build_decision_result(dimension_results))
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
    )
    return {
        "report_result": report,
        "workflow_snapshot": build_workflow_snapshot_v2(
            plan=plan,
            current_stage="report",
            completed_steps=completed,
            dimension_results=dimension_results,
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
