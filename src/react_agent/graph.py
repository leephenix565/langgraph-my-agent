"""LangGraph: 4-layer Router -> Manager -> Agents -> Final summary."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command, Send

from react_agent import (
    contract_utils,
    prompts,
    router_parse,
)
from react_agent.agents import (
    AGENT_METADATA,
    AGENT_TOOLS,
    AgentOutput,
    format_agent_profile,
)
from react_agent.baseline_sidecar import run_baseline_sidecar
from react_agent.context import Context
from react_agent.graph_bootstrap import (
    bootstrap_agent_runtime,
    build_node_registry,
)
from react_agent.graph_bootstrap import (
    build_agent_catalog as _bootstrap_build_agent_catalog,
)
from react_agent.graph_entry import (
    compile_graph_variants,
    maybe_make_checkpointer,
    select_graph_for_invoke,
)
from react_agent.graph_observability import (
    _elapsed_ms,
    _log_node_latency,
    _model_trace_fields,
    _truncate,
)
from react_agent.graph_runtime_features import (
    _build_stable_evidence_index,
    _build_stable_finding_entry,
    _build_stable_summary,
    _build_thread_summary,
    _get_runtime_results_pool,
    _is_search_disabled_globally,
    _messages_window_enabled,
    _messages_window_size,
    _results_pools_enabled,
    _stable_consume_enabled,
    _stable_findings_max_items,
    _stable_summary_system_msg,
    _thread_summary_enabled,
    _thread_summary_system_msg,
    _window_messages,
)
from react_agent.run_logger import get_run_logger
from react_agent.state import InputState, State
from react_agent.utils import get_message_text, load_chat_model

LAYER_ORDER: List[str] = router_parse.LAYER_ORDER
DEFAULT_MODES: Dict[str, str] = router_parse.DEFAULT_MODES
FINAL_LAYER: str = LAYER_ORDER[-1]


def _router_provider_error_category(exc_type: str) -> str:
    """Return a coarse, non-sensitive provider error category."""
    lowered = exc_type.lower()
    if "timeout" in lowered:
        return "timeout"
    if any(token in lowered for token in ["auth", "permission", "unauthorized", "forbidden"]):
        return "authentication"
    if "rate" in lowered:
        return "rate_limit"
    if any(token in lowered for token in ["http", "connection", "network", "transport"]):
        return "transport"
    if any(token in lowered for token in ["value", "import", "config"]):
        return "configuration"
    return "provider"


def _catalog_agent_ids(agent_catalog: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    for layer_items in agent_catalog.values():
        if not isinstance(layer_items, list):
            continue
        for item in layer_items:
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict) and isinstance(item.get("id"), str):
                ids.append(item["id"])
    return ids


def _router_raw_text_shape(raw_text: str, agent_catalog: Dict[str, Any]) -> Dict[str, object]:
    """Build safe Router output shape telemetry without storing raw content."""
    text = raw_text or ""
    stripped = text.lstrip()
    known_ids = set(_catalog_agent_ids(agent_catalog))
    return {
        "router_raw_text_length": len(text),
        "router_raw_text_starts_with_json": stripped.startswith("{") or stripped.startswith("["),
        "router_raw_text_contains_layers": '"layers"' in text or "'layers'" in text,
        "router_raw_text_contains_fenced_json": "```" in text,
        "router_raw_text_contains_agent_ids": any(aid in text for aid in known_ids),
    }


async def _with_temp_openai_env(
    base_url: str, api_key: str, fn
) -> AIMessage:
    """Temporarily override OpenAI env vars for a single call."""
    had_base = "OPENAI_BASE_URL" in os.environ
    old_base = os.environ.get("OPENAI_BASE_URL")
    had_key = "OPENAI_API_KEY" in os.environ
    old_key = os.environ.get("OPENAI_API_KEY")
    if base_url:
        os.environ["OPENAI_BASE_URL"] = base_url
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    try:
        return await fn()
    finally:
        if base_url:
            if had_base:
                os.environ["OPENAI_BASE_URL"] = old_base
            else:
                os.environ.pop("OPENAI_BASE_URL", None)
        if api_key:
            if had_key:
                os.environ["OPENAI_API_KEY"] = old_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)
CONTRACT_SCHEMA_VERSION = contract_utils.CONTRACT_SCHEMA_VERSION
CONTRACT_REQUIRED_KEYS = contract_utils.CONTRACT_REQUIRED_KEYS
TASK_REQUIRED_KEYS = contract_utils.TASK_REQUIRED_KEYS


def _summarize_router_plan(layer_plan: Dict[str, List[str]], layer_mode: Dict[str, str], limit: int = 800) -> str:
    """Compact, readable summary like 'L2(Star): a03, a09' per line."""
    lines: List[str] = []
    for layer in LAYER_ORDER:
        mode = _normalize_mode(layer_mode.get(layer, DEFAULT_MODES.get(layer, "Star")))
        agents = layer_plan.get(layer, [])
        agent_str = ", ".join(agents) if agents else "none"
        lines.append(f"{layer}({mode}): {agent_str}")
    text = "\n".join(lines)
    # Truncate by lines to avoid breaking readability mid-line.
    if len(text) <= limit:
        return text
    truncated = []
    total = 0
    for line in lines:
        if total + len(line) + 1 > limit:
            break
        truncated.append(line)
        total += len(line) + 1
    return "\n".join(truncated) + "\n...[trunc]"


def _collect_selected_agents(layer_plan: Dict[str, List[str]]) -> List[str]:
    """Return ordered unique agent ids across all layers."""
    seen = set()
    ordered: List[str] = []
    for layer in LAYER_ORDER:
        for aid in layer_plan.get(layer, []):
            if aid not in seen:
                ordered.append(aid)
                seen.add(aid)
    return ordered


def _hash_contract(contract: Dict[str, Any]) -> str:
    return contract_utils.hash_contract(contract)


def _extract_contract(results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return contract_utils.extract_contract(results)


def _validate_contract(
    contract: Optional[Dict[str, Any]],
    selected_agents: List[str],
) -> Tuple[bool, str, Dict[str, Dict[str, Any]]]:
    return contract_utils.validate_contract(contract, selected_agents)


def _format_steps(steps: List[str]) -> str:
    return "\n".join(f"{idx + 1}. {step}" for idx, step in enumerate(steps))


def _build_assignment_from_contract(
    agent_id: str,
    task: Dict[str, Any],
    contract: Dict[str, Any],
    question: str,
    profile_label: str,
) -> Tuple[str, int, str]:
    steps = task.get("steps", [])
    constraints = "; ".join([c for c in contract.get("constraints", []) if isinstance(c, str)])
    output_spec = contract.get("output_spec", {})
    required_sections = output_spec.get("required_sections", [])
    output_spec_text = (
        f"required_sections: {', '.join(required_sections) if required_sections else 'none'}; "
        f"final_answer_format: {output_spec.get('final_answer_format', '')}"
    )
    assignment_text = prompts.MANAGER_ASSIGNMENT_CONTRACT.format(
        agent_id=agent_id,
        profile_label=profile_label,
        question=question,
        contract_objective=contract.get("objective", ""),
        task_id=task.get("task_id", ""),
        task_objective=task.get("objective", ""),
        steps=_format_steps(steps),
        agent_can_extend_steps=task.get("agent_can_extend_steps"),
        extension_policy=task.get("extension_policy", ""),
        constraints=constraints or "none",
        output_spec=output_spec_text,
    )
    return assignment_text, len(steps), str(task.get("task_id", ""))


def _agent_error_output(agent_id: str, exc: Exception) -> AgentOutput:
    """Construct a structured fail-soft AgentOutput for non-cancel errors."""
    summary = f"{type(exc).__name__}: {_truncate(str(exc), 500)}"
    return {
        "analysis": f"[AGENT_ERROR] {summary}",
        "key_points": [],
        "evidence": [],
        "confidence": 0.0,
        "parse_ok": False,
    }

bootstrap_agent_runtime()
include_disabled = os.environ.get("INCLUDE_DISABLED_AGENTS", "0") == "1"
AGENT_IDS_FOR_NODES, AGENT_NODE_NAMES = build_node_registry(include_disabled)
_maybe_make_checkpointer = maybe_make_checkpointer


def _get_latest_user_question(messages: List[AnyMessage]) -> str:
    """Return the most recent human question."""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return get_message_text(msg)
    return get_message_text(messages[-1]) if messages else ""


def _normalize_mode(mode: str) -> str:
    """Return a single valid mode (Star/Chain/Debate/Tree) with light tolerance."""
    return router_parse.normalize_mode(mode)


def _build_agent_catalog() -> Dict[str, List[Dict[str, Any]]]:
    return _bootstrap_build_agent_catalog(LAYER_ORDER)


def _default_layer_plan() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    return router_parse.default_layer_plan(_build_agent_catalog())


def _parse_router_layers(raw: str) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """Parse router JSON into layer_plan/layer_mode with compatibility fallback."""
    plan, modes, _stats = router_parse.parse_router_layers_with_stats(
        raw, agent_catalog=_build_agent_catalog()
    )
    return plan, modes


def _next_layer(current_layer: str) -> Optional[str]:
    if current_layer not in LAYER_ORDER:
        return None
    idx = LAYER_ORDER.index(current_layer)
    return LAYER_ORDER[idx + 1] if idx + 1 < len(LAYER_ORDER) else None


async def router_node(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Router: produce per-layer plan and modes."""
    node_started_at = time.perf_counter()
    question = _get_latest_user_question(list(state["messages"]))
    run_id = state.get("run_id") or runtime.context.run_id or uuid.uuid4().hex[:8]
    runtime.context.run_id = run_id
    logger = get_run_logger(run_id)
    agent_catalog = _build_agent_catalog()
    system_prompt = prompts.ROUTER_SYSTEM_PROMPT.format(
        system_time=datetime.now(tz=UTC).isoformat(),
        agent_catalog=json.dumps(agent_catalog, ensure_ascii=False),
    )
    msgs: List[Any] = [{"role": "system", "content": system_prompt}]
    stable_raw = state.get("stable_findings", [])
    stable_len = len(stable_raw) if isinstance(stable_raw, list) else 0
    stable_summary = ""
    stable_enabled = _stable_consume_enabled()
    if stable_enabled:
        stable_summary = _build_stable_summary(state)
        if stable_summary:
            msgs.append(_stable_summary_system_msg(stable_summary))
    logger.log_event(
        "stable_consume",
        node="router",
        enabled=1 if stable_enabled else 0,
        stable_len=stable_len,
        stable_summary_len=len(stable_summary),
    )
    thread_summary = state.get("thread_summary", "")
    if _thread_summary_enabled() and thread_summary:
        msgs.append(_thread_summary_system_msg(thread_summary))
    full_messages = list(state["messages"])
    window_enabled = _messages_window_enabled()
    window_size = _messages_window_size() if window_enabled else 0
    ctx_messages = _window_messages(full_messages) if window_enabled else full_messages
    logger.log_event(
        "router_ctx",
        window_enabled=1 if window_enabled else 0,
        window_size=window_size,
        ctx_messages_len=len(ctx_messages),
        full_messages_len=len(full_messages),
    )
    msgs.extend(ctx_messages)
    router_model_name = runtime.context.router_model or runtime.context.model
    fallback_model_name = runtime.context.model
    router_provider_error = False
    router_provider_error_type = ""
    router_provider_error_category = ""
    try:
        metadata = {
            "run_id": run_id,
            "layer": "L1",
            "mode": DEFAULT_MODES.get("L1", "Chain"),
            "node_name": "router",
            "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest()[:12] if question else "",
        }
        tags = ["react_agent", f"run_id:{run_id}", "layer:L1"]

        async def _invoke_router(model_name: str) -> AIMessage:
            model = load_chat_model(model_name)
            return await model.ainvoke(msgs, config={"metadata": metadata, "tags": tags})

        if runtime.context.router_openai_base_url:
            try:
                response = await _with_temp_openai_env(
                    runtime.context.router_openai_base_url,
                    runtime.context.router_openai_api_key,
                    lambda: _invoke_router(router_model_name),
                )
            except Exception as exc:
                router_provider_error = True
                router_provider_error_type = type(exc).__name__
                router_provider_error_category = _router_provider_error_category(
                    router_provider_error_type
                )
                logger.log_event(
                    "router_provider_fallback",
                    node="router",
                    router_model=router_model_name,
                    router_base_url=runtime.context.router_openai_base_url,
                    fallback_model=fallback_model_name,
                    elapsed_ms=_elapsed_ms(node_started_at),
                    exception_type=router_provider_error_type,
                    error_category=router_provider_error_category,
                    **_model_trace_fields(router_model_name, "router_model"),
                    **_model_trace_fields(fallback_model_name, "fallback_model"),
                )
                response = await _invoke_router(fallback_model_name)
        else:
            response = await _invoke_router(router_model_name)
        raw_text = get_message_text(response)
    except Exception as exc:
        router_provider_error = True
        router_provider_error_type = type(exc).__name__
        router_provider_error_category = _router_provider_error_category(
            router_provider_error_type
        )
        logger.log_event(
            "router_error",
            node="router",
            current_layer="L1",
            elapsed_ms=_elapsed_ms(node_started_at),
            exception_type=router_provider_error_type,
            error_category=router_provider_error_category,
            **_model_trace_fields(router_model_name, "router_model"),
            **_model_trace_fields(fallback_model_name, "fallback_model"),
        )
        response = AIMessage(content="[router fallback]")
        raw_text = ""
    raw_shape = _router_raw_text_shape(raw_text, agent_catalog)
    router_provider_telemetry: Dict[str, object] = {
        "router_provider_error": router_provider_error,
        "router_provider_error_type": router_provider_error_type,
        "router_provider_error_category": router_provider_error_category,
        **raw_shape,
    }
    layer_plan, layer_mode, parse_stats = router_parse.parse_router_layers_with_stats(
        raw_text, agent_catalog=agent_catalog
    )
    parse_stats.update(
        {
            **router_provider_telemetry,
            "router_parse_ok": bool(parse_stats.get("parse_ok")),
            "router_used_default_plan": bool(parse_stats.get("used_default_plan")),
            "router_fallback_reason": parse_stats.get("fallback_reason"),
        }
    )
    logger.log_event(
        "router_decision",
        question=_truncate(question),
        **parse_stats,
    )
    current_layer = LAYER_ORDER[0]
    logger.log_event(
        "run_start",
        question=_truncate(question),
        current_layer=current_layer,
        run_id=run_id,
        layer_plan=_truncate(layer_plan),
        layer_mode=layer_mode,
        router_parse_stats=parse_stats,
    )
    update: Dict[str, object] = {
        "messages": [response],
        "plan": layer_plan.get(current_layer, []),
        "layer_plan": layer_plan,
        "layer_mode": layer_mode,
        "current_layer": current_layer,
        "chain_cursor": 0,
        "fanout_targets": [],
        "current_question": question,
        "layer_done": {},
        "run_id": run_id,
        "is_last_step": False,
        "multi_agent_bundle": {},
        "mainline_status": "",
        "mainline_emit_payload": {},
        "final_answer_source": "",
        "judge_status": "",
        "fusion_verdict": {},
        "writer_status": "",
        "writer_output": {},
        "final_emit_payload": {},
        "emitted_bundle": {},
        "baseline_status": "",
        "baseline_bundle": {},
    }
    # Signal a fresh turn so downstream merges clear old analyst_results.
    update["analyst_results"] = {"__reset__": True}
    if _results_pools_enabled():
        update["ephemeral_results"] = {"__reset__": True}
        logger.log_event("ephemeral_reset", enabled=1)
    _log_node_latency(
        logger,
        "router",
        node_started_at,
        current_layer=current_layer,
        parse_ok=bool(parse_stats.get("parse_ok")),
        used_default_plan=bool(parse_stats.get("used_default_plan")),
    )
    return update


async def manager_broadcast(
    state: State, runtime: Runtime[Context]
) -> Command:
    """Dispatch within the current layer according to its mode."""
    node_started_at = time.perf_counter()
    layer_plan = state.get("layer_plan", {})
    layer_mode = state.get("layer_mode", {})
    current_layer = state.get("current_layer") or LAYER_ORDER[0]
    selected = layer_plan.get(current_layer, [])
    mode = _normalize_mode(layer_mode.get(current_layer, DEFAULT_MODES.get(current_layer, "Star")))
    results = _get_runtime_results_pool(state)
    question = state.get("current_question") or _get_latest_user_question(list(state.get("messages", [])))
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)

    def _emit_latency(branch: str, dispatch_count: int) -> None:
        _log_node_latency(
            logger,
            "manager_broadcast",
            node_started_at,
            current_layer=current_layer,
            mode=mode,
            branch=branch,
            dispatch_count=dispatch_count,
        )

    remaining = [aid for aid in selected if aid not in results]
    debug_msgs: List[AIMessage] = []
    selected_all = _collect_selected_agents(layer_plan)
    contract = _extract_contract(results)
    contract_ok, contract_reason, contract_tasks = _validate_contract(contract, selected_all)
    contract_hash = _hash_contract(contract) if contract else ""
    if contract and not contract_ok:
        debug_msgs.append(
            AIMessage(content=f"[manager_broadcast] contract invalid -> {contract_reason}")
        )

    if not selected:
        debug_msgs.append(
            AIMessage(content=f"[manager_broadcast] layer {current_layer} empty -> skip")
        )
        _emit_latency("empty_skip", 0)
        return Command(
            goto="manager_summary",
            update={
                "messages": debug_msgs,
                "plan": selected,
                "fanout_targets": [],
            },
        )
    logger.log_event(
        "manager_broadcast",
        current_layer=current_layer,
        mode=mode,
        selected=selected,
        remaining=remaining,
        pending=[aid for aid in selected if aid not in results],
    )

    # Debate/Tree fallback to Star dispatch, but keep mode for visibility.
    effective_mode = "Star" if mode in {"Debate", "Tree"} else mode
    if effective_mode != mode:
        debug_msgs.append(
            AIMessage(content=f"[manager_broadcast] mode {mode} temporarily treated as Star for dispatch")
        )

    if effective_mode == "Chain":
        if not remaining:
            debug_msgs.append(
                AIMessage(content=f"[manager_broadcast] layer {current_layer} chain complete")
            )
            _emit_latency("chain_complete", 0)
            return Command(
                goto="manager_summary",
                update={"messages": debug_msgs, "plan": selected, "fanout_targets": []},
            )
        next_id = remaining[0]
        node_name = AGENT_NODE_NAMES.get(next_id)
        if not node_name:
            debug_msgs.append(
                AIMessage(content=f"[manager_broadcast] missing node for {next_id}, skipping")
            )
            _emit_latency("chain_missing_node", len(remaining))
            return Command(
                goto="manager_summary",
                update={"messages": debug_msgs, "plan": selected, "fanout_targets": remaining},
            )
        used_contract = False
        step_count = 0
        task_id = ""
        profile_label = (
            format_agent_profile(AGENT_METADATA[next_id])
            if next_id in AGENT_METADATA
            else next_id
        )
        if contract_ok and next_id in contract_tasks and contract:
            assignment_text, step_count, task_id = _build_assignment_from_contract(
                next_id, contract_tasks[next_id], contract, question, profile_label
            )
            used_contract = True
        elif next_id == "a01_cio_orchestrator":
            assignment_text = prompts.MANAGER_ASSIGNMENT_ORCHESTRATOR.format(
                question=question,
                router_plan_summary=_summarize_router_plan(layer_plan, layer_mode),
            )
        elif next_id == "a25_report_center":
            assignment_text = prompts.MANAGER_ASSIGNMENT_REPORT_CENTER.format(
                question=question,
                router_plan_summary=_summarize_router_plan(layer_plan, layer_mode),
            )
        else:
            assignment_text = prompts.MANAGER_ASSIGNMENT_USER.format(
                question=question,
                plan=", ".join(selected),
                finished=", ".join(results.keys()) or "none",
                next_id=next_id,
                profile_label=profile_label,
                layer=current_layer,
                mode=mode,
            )
        logger.log_event(
            "manager_assignment",
            agent_id=next_id,
            current_layer=current_layer,
            mode=mode,
            used_contract=used_contract,
            contract_hash=contract_hash,
            task_id=task_id,
            step_count=step_count,
        )
        branch_state = dict(state)
        branch_state["messages"] = [
            *state["messages"],
            HumanMessage(content=assignment_text),
        ]
        debug_msgs.append(
            AIMessage(content=f"[manager_broadcast] chain dispatch -> {next_id} (layer {current_layer})")
        )
        _emit_latency("chain_dispatch", 1)
        return Command(
            goto=[Send(node_name, branch_state)],
            update={
                "messages": debug_msgs,
                "plan": selected,
                "fanout_targets": [next_id],
                "chain_cursor": selected.index(next_id),
            },
        )

    # Star/Debate/Tree (treated as parallel) dispatch remaining agents.
    sends: List[Send] = []
    for agent_id in remaining:
        node_name = AGENT_NODE_NAMES.get(agent_id)
        if not node_name:
            continue
        used_contract = False
        step_count = 0
        task_id = ""
        profile_label = (
            format_agent_profile(AGENT_METADATA[agent_id])
            if agent_id in AGENT_METADATA
            else agent_id
        )
        if contract_ok and agent_id in contract_tasks and contract:
            assignment_text, step_count, task_id = _build_assignment_from_contract(
                agent_id, contract_tasks[agent_id], contract, question, profile_label
            )
            used_contract = True
        elif agent_id == "a01_cio_orchestrator":
            assignment_text = prompts.MANAGER_ASSIGNMENT_ORCHESTRATOR.format(
                question=question,
                router_plan_summary=_summarize_router_plan(layer_plan, layer_mode),
            )
        elif agent_id == "a25_report_center":
            assignment_text = prompts.MANAGER_ASSIGNMENT_REPORT_CENTER.format(
                question=question,
                router_plan_summary=_summarize_router_plan(layer_plan, layer_mode),
            )
        else:
            assignment_text = prompts.MANAGER_ASSIGNMENT_USER.format(
                question=question,
                plan=", ".join(selected),
                finished=", ".join(results.keys()) or "none",
                next_id=agent_id,
                profile_label=profile_label,
                layer=current_layer,
                mode=mode,
            )
        logger.log_event(
            "manager_assignment",
            agent_id=agent_id,
            current_layer=current_layer,
            mode=mode,
            used_contract=used_contract,
            contract_hash=contract_hash,
            task_id=task_id,
            step_count=step_count,
        )
        branch_state = dict(state)
        branch_state["messages"] = [
            *state["messages"],
            HumanMessage(content=assignment_text),
        ]
        sends.append(Send(node_name, branch_state))

    debug_msgs.append(
        AIMessage(
            content=f"[manager_broadcast] {mode} dispatch -> {', '.join(remaining) or 'none'} "
            f"(layer {current_layer})"
        )
    )
    _emit_latency("parallel_dispatch", len(sends))
    return Command(
        goto=sends or "manager_summary",
        update={"messages": debug_msgs, "plan": selected, "fanout_targets": remaining},
    )


def _build_agent_node(agent_id: str):
    async def _node(state: State, runtime: Runtime[Context]) -> Dict[str, object]:
        tool = AGENT_TOOLS.get(agent_id)
        if not tool:
            return {}
        question = state.get("current_question") or _get_latest_user_question(list(state.get("messages", [])))
        subtask = get_message_text(state["messages"][-1]) if state.get("messages") else ""
        current_layer = state.get("current_layer") or ""
        mode = _normalize_mode(
            (state.get("layer_mode") or {}).get(current_layer, DEFAULT_MODES.get(current_layer, "Star"))
        )
        run_id = state.get("run_id") or runtime.context.run_id or ""
        logger = get_run_logger(run_id)
        node_started_at = time.perf_counter()
        logger.log_event(
            "agent_start",
            agent_id=agent_id,
            layer=current_layer,
            mode=mode,
            subtask=_truncate(subtask),
        )
        agent_input = {
            "question": question,
            "subtask": subtask,
            "shared_context": _get_runtime_results_pool(state),
            "history": [],
            "tools_config": {
                "allow_search": (
                    False
                    if _is_search_disabled_globally()
                    or agent_id in {"a01_cio_orchestrator", "a25_report_center"}
                    else True
                ),
                "mode": mode,
            },
            "router_plan_summary": _summarize_router_plan(
                state.get("layer_plan", {}), state.get("layer_mode", {})
            ),
        }
        metadata = {
            "run_id": run_id,
            "layer": current_layer,
            "mode": mode,
            "node_name": f"agent_{agent_id}_node",
            "agent_id": agent_id,
            "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest()[:12] if question else "",
        }
        tags = ["react_agent", f"run_id:{run_id}", f"layer:{current_layer}"]
        try:
            output: AgentOutput = await tool.ainvoke(agent_input, config={"metadata": metadata, "tags": tags})
        except asyncio.CancelledError as exc:
            logger.log_event("agent_cancelled", agent_id=agent_id, layer=current_layer, mode=mode)
            raise exc
        except Exception as exc:
            logger.log_event(
                "agent_error",
                node="agent",
                agent_id=agent_id,
                layer=current_layer,
                mode=mode,
                elapsed_ms=_elapsed_ms(node_started_at),
                exception_type=type(exc).__name__,
                exception_repr=repr(exc),
                error_type=type(exc).__name__,
                error=str(exc),
                **_model_trace_fields(runtime.context.model),
            )
            output = _agent_error_output(agent_id, exc)
        runtime_results = dict(_get_runtime_results_pool(state))
        runtime_results[agent_id] = output
        logger.log_event(
            "agent_end",
            agent_id=agent_id,
            layer=current_layer,
            mode=mode,
            parse_ok=output.get("parse_ok"),
            confidence=output.get("confidence"),
        )
        _log_node_latency(
            logger,
            "agent",
            node_started_at,
            agent_id=agent_id,
            layer=current_layer,
            mode=mode,
            parse_ok=output.get("parse_ok"),
            confidence=output.get("confidence"),
        )
        ai_msg = AIMessage(
            content=json.dumps({"agent_id": agent_id, "output": output}, ensure_ascii=False, indent=2)
        )
        if _results_pools_enabled():
            return {
                "messages": [ai_msg],
                "ephemeral_results": runtime_results,
                # Backward-compatible mirror for existing readers/tests during transition.
                "analyst_results": dict(runtime_results),
            }
        return {
            "messages": [ai_msg],
            "analyst_results": runtime_results,
        }

    _node.__name__ = f"{agent_id}_agent_node"
    return _node


async def _run_final_summary(
    state: State,
    runtime: Runtime[Context],
    layer_done: Dict[str, bool],
    analyst_results: Dict[str, Any],
    filtered_results: Dict[str, Any],
    filtered_out: int,
    summary_source: str = "manager_summary",
) -> Dict[str, object]:
    """Run the final user-facing summary step and mark turn completion."""
    node_started_at = time.perf_counter()
    current_layer = state.get("current_layer") or LAYER_ORDER[0]
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)

    bundle, response = await _build_mainline_bundle(
        state=state,
        runtime=runtime,
        analyst_results=analyst_results,
        filtered_results=filtered_results,
        filtered_out=filtered_out,
        summary_source=summary_source,
        logger=logger,
        current_layer=current_layer,
        node_started_at=node_started_at,
    )
    update = _emit_final_answer(
        state=state,
        layer_done=layer_done,
        filtered_results=filtered_results,
        response=response,
        bundle=bundle,
        logger=logger,
    )
    _log_node_latency(
        logger,
        "summary",
        node_started_at,
        current_layer=current_layer,
        source=summary_source,
        filtered_out=filtered_out,
        result_count=len(filtered_results),
    )
    return update


async def _build_mainline_bundle(
    state: State,
    runtime: Runtime[Context],
    analyst_results: Dict[str, Any],
    filtered_results: Dict[str, Any],
    filtered_out: int,
    summary_source: str,
    logger,
    current_layer: str,
    node_started_at: float,
) -> Tuple[Dict[str, Any], AIMessage]:
    """Build the current mainline bundle and return the final response message."""
    layer_plan = state.get("layer_plan", {})
    layer_mode = state.get("layer_mode", {})
    run_id = state.get("run_id") or runtime.context.run_id or ""

    model = load_chat_model(runtime.context.model)
    system_prompt = runtime.context.system_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )
    question = state.get("current_question") or _get_latest_user_question(list(state.get("messages", [])))
    meta_note = ""
    if filtered_out > 0:
        meta_note = f"\n[meta] 本轮有 {filtered_out} 条输出因解析失败未参与汇总。\n"
    a25_output = filtered_results.get("a25_report_center")
    if a25_output is not None:
        try:
            a25_output = json.dumps(a25_output, ensure_ascii=False)
        except Exception:
            a25_output = str(a25_output)
    else:
        a25_output = ""
    user_msg = prompts.MANAGER_SUMMARY_USER.format(
        question=question,
        layer_plan=layer_plan,
        layer_mode=layer_mode,
        analyst_results=filtered_results,
        a25_output=a25_output,
    )
    user_msg = meta_note + user_msg
    base_msgs: List[Any] = [{"role": "system", "content": system_prompt}]
    stable_raw = state.get("stable_findings", [])
    stable_len = len(stable_raw) if isinstance(stable_raw, list) else 0
    stable_summary = ""
    stable_enabled = _stable_consume_enabled()
    if stable_enabled:
        stable_summary = _build_stable_summary(state)
        if stable_summary:
            base_msgs.append(_stable_summary_system_msg(stable_summary))
    logger.log_event(
        "stable_consume",
        node="manager_summary",
        enabled=1 if stable_enabled else 0,
        stable_len=stable_len,
        stable_summary_len=len(stable_summary),
    )
    thread_summary = state.get("thread_summary", "")
    if _thread_summary_enabled() and thread_summary:
        base_msgs.append(_thread_summary_system_msg(thread_summary))
    full_messages = list(state.get("messages", []))
    window_enabled = _messages_window_enabled()
    window_size = _messages_window_size() if window_enabled else 0
    ctx_messages = _window_messages(full_messages) if window_enabled else full_messages
    logger.log_event(
        "manager_ctx",
        window_enabled=1 if window_enabled else 0,
        window_size=window_size,
        ctx_messages_len=len(ctx_messages),
        full_messages_len=len(full_messages),
    )
    base_msgs.extend(ctx_messages)
    base_msgs.append({"role": "user", "content": user_msg})
    try:
        metadata = {
            "run_id": run_id,
            "layer": current_layer,
            "mode": layer_mode.get(current_layer, ""),
            "node_name": "manager_summary",
            "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest()[:12] if question else "",
        }
        tags = ["react_agent", f"run_id:{run_id}", f"layer:{current_layer}"]
        response: AIMessage = await model.ainvoke(base_msgs, config={"metadata": metadata, "tags": tags})
    except Exception as exc:
        logger.log_event(
            "summary_error",
            node="summary",
            current_layer=current_layer,
            elapsed_ms=_elapsed_ms(node_started_at),
            filtered_out=filtered_out,
            exception_type=type(exc).__name__,
            exception_repr=repr(exc),
            error=str(exc),
            **_model_trace_fields(runtime.context.model),
        )
        summary_text = json.dumps(
            {
                "question": question,
                "layer_plan": layer_plan,
                "layer_mode": layer_mode,
                "analyst_results": analyst_results,
                "warning": f"LLM summary failed: {exc}",
            },
            ensure_ascii=False,
            indent=2,
        )
        response = AIMessage(content=summary_text)
    answer_text = get_message_text(response)
    evidence_cards = _build_stable_evidence_index(filtered_results)
    bundle: Dict[str, Any] = {
        "question": question,
        "answer": answer_text,
        "layer_plan": layer_plan,
        "layer_mode": layer_mode,
        "a25_output": a25_output,
        "evidence_cards": evidence_cards,
        "filtered_out": filtered_out,
        "summary_source": summary_source,
        "process_health": {
            "filtered_out": filtered_out,
            "result_count": len(filtered_results),
            "a25_present": bool(a25_output),
            "summary_source": summary_source,
        },
    }
    logger.log_event(
        "summary_end",
        current_layer=current_layer,
        filtered_out=filtered_out,
        results=list(filtered_results.keys()),
        summary=_truncate(answer_text),
    )
    return bundle, response


def _stage_mainline_ready(
    *,
    bundle: Dict[str, Any],
    response: AIMessage,
    layer_done: Dict[str, bool],
    filtered_results: Dict[str, Any],
    summary_source: str,
) -> Dict[str, object]:
    """Stage the mainline answer for a later emit without changing closeout state."""
    return {
        "multi_agent_bundle": bundle,
        "mainline_status": "ready",
        "mainline_emit_payload": {
            "response_text": get_message_text(response),
            "layer_done": dict(layer_done),
            "filtered_results": dict(filtered_results),
            "summary_source": summary_source,
        },
    }


def _extract_json_object(text: str) -> str | None:
    try:
        json.loads(text)
        return text
    except Exception:
        match = re.search(r"\{.*\}", text, flags=re.S)
        return match.group(0) if match else None


def _coerce_string_list(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    values: List[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            values.append(text)
    return values


def _coerce_card_list(raw: Any) -> List[Any]:
    if not isinstance(raw, list):
        return []
    values: List[Any] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text:
                values.append(text)
            continue
        if isinstance(item, dict):
            cleaned: Dict[str, Any] = {}
            for key, value in item.items():
                norm_key = str(key).strip()
                if not norm_key:
                    continue
                if isinstance(value, str):
                    norm_value = value.strip()
                    if norm_value:
                        cleaned[norm_key] = norm_value
                elif isinstance(value, int | float | bool) or value is None:
                    cleaned[norm_key] = value
                else:
                    norm_value = str(value).strip()
                    if norm_value:
                        cleaned[norm_key] = norm_value
            if cleaned:
                values.append(cleaned)
            continue
        text = str(item).strip()
        if text:
            values.append(text)
    return values


def _coerce_string_map(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    values: Dict[str, str] = {}
    for key, value in raw.items():
        norm_key = str(key).strip()
        norm_value = str(value).strip()
        if norm_key and norm_value:
            values[norm_key] = norm_value
    return values


def _normalize_fusion_verdict(
    parsed: Any,
    *,
    fallback_decision: str,
    fallback_reason: str,
) -> Dict[str, Any]:
    parsed = parsed if isinstance(parsed, dict) else {}
    decision = str(parsed.get("decision", fallback_decision) or fallback_decision).strip().lower()
    if decision not in {"mainline", "baseline", "fused"}:
        decision = fallback_decision
    decision_reason = str(parsed.get("decision_reason", fallback_reason) or fallback_reason).strip()
    if not decision_reason:
        decision_reason = fallback_reason
    confidence_raw = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    return {
        "decision": decision,
        "decision_reason": decision_reason,
        "winner_by_dimension": _coerce_string_map(parsed.get("winner_by_dimension", {})),
        "rewrite_plan": _coerce_string_list(parsed.get("rewrite_plan", [])),
        "accepted_cards": _coerce_card_list(parsed.get("accepted_cards", [])),
        "must_keep_facts": _coerce_string_list(parsed.get("must_keep_facts", [])),
        "must_drop_facts": _coerce_string_list(parsed.get("must_drop_facts", [])),
        "confidence": confidence,
    }


def _build_degraded_fusion_verdict(
    *,
    baseline_status: str,
    reason: str,
) -> Dict[str, Any]:
    return _normalize_fusion_verdict(
        {
            "decision": "mainline",
            "decision_reason": reason,
            "winner_by_dimension": {"overall": "mainline"},
            "rewrite_plan": [],
            "accepted_cards": [],
            "must_keep_facts": [],
            "must_drop_facts": [],
            "confidence": 0.5 if baseline_status == "disabled" else 0.4,
        },
        fallback_decision="mainline",
        fallback_reason=reason,
    )


def _normalize_writer_output(
    parsed: Any,
    *,
    fallback_answer: str,
    fallback_selected_source: str,
    fallback_note: str,
    fallback_accepted_cards: List[Any],
) -> Dict[str, Any]:
    parsed = parsed if isinstance(parsed, dict) else {}
    selected_source = str(parsed.get("selected_source", fallback_selected_source) or fallback_selected_source).strip().lower()
    if selected_source not in {"mainline", "baseline", "fused"}:
        selected_source = fallback_selected_source
    proposed_answer = str(parsed.get("proposed_answer", fallback_answer) or fallback_answer).strip()
    if not proposed_answer:
        proposed_answer = fallback_answer
    note = str(parsed.get("note", fallback_note) or fallback_note).strip()
    if not note:
        note = fallback_note
    accepted_cards = _coerce_card_list(parsed.get("accepted_cards", fallback_accepted_cards))
    if not accepted_cards:
        accepted_cards = list(fallback_accepted_cards)
    return {
        "proposed_answer": proposed_answer,
        "selected_source": selected_source,
        "accepted_cards": accepted_cards,
        "dropped_cards": _coerce_card_list(parsed.get("dropped_cards", [])),
        "note": note,
    }


def _build_degraded_writer_output(
    *,
    mainline_bundle: Dict[str, Any],
    fusion_verdict: Dict[str, Any],
    baseline_status: str,
    reason: str,
) -> Dict[str, Any]:
    fallback_answer = str(mainline_bundle.get("answer", "") or "").strip()
    return _normalize_writer_output(
        {
            "proposed_answer": fallback_answer,
            "selected_source": "mainline",
            "accepted_cards": fusion_verdict.get("accepted_cards", []),
            "dropped_cards": [],
            "note": reason if baseline_status in {"error", "disabled"} else "writer degraded to mainline",
        },
        fallback_answer=fallback_answer,
        fallback_selected_source="mainline",
        fallback_note=reason,
        fallback_accepted_cards=_coerce_card_list(fusion_verdict.get("accepted_cards", [])),
    )


def _normalize_selected_source(raw: Any, default: str = "mainline") -> str:
    value = str(raw or default).strip().lower()
    if value not in {"mainline", "baseline", "fused"}:
        return default
    return value


def _select_final_source(
    *,
    state: State,
    source_switch_enabled: bool,
    writer_output: Optional[Dict[str, Any]] = None,
    writer_status: Optional[str] = None,
    fusion_verdict: Optional[Dict[str, Any]] = None,
    judge_status: Optional[str] = None,
) -> str:
    if not source_switch_enabled:
        return "mainline"

    writer_output = writer_output if isinstance(writer_output, dict) else state.get("writer_output", {})
    writer_output = writer_output if isinstance(writer_output, dict) else {}
    fusion_verdict = fusion_verdict if isinstance(fusion_verdict, dict) else state.get("fusion_verdict", {})
    fusion_verdict = fusion_verdict if isinstance(fusion_verdict, dict) else {}
    writer_status = str(writer_status if writer_status is not None else state.get("writer_status", "") or "")
    judge_status = str(judge_status if judge_status is not None else state.get("judge_status", "") or "")

    selected_source = "mainline"
    if writer_status == "ready":
        selected_source = _normalize_selected_source(writer_output.get("selected_source", "mainline"))
    elif judge_status == "ready":
        selected_source = _normalize_selected_source(fusion_verdict.get("decision", "mainline"))

    mainline_bundle = state.get("multi_agent_bundle", {})
    mainline_bundle = mainline_bundle if isinstance(mainline_bundle, dict) else {}
    mainline_payload = state.get("mainline_emit_payload", {})
    mainline_payload = mainline_payload if isinstance(mainline_payload, dict) else {}
    baseline_status = str(state.get("baseline_status", "") or "")
    baseline_bundle = state.get("baseline_bundle", {})
    baseline_bundle = baseline_bundle if isinstance(baseline_bundle, dict) else {}

    if selected_source == "baseline":
        if baseline_status != "ready" or not str(baseline_bundle.get("answer", "") or "").strip():
            return "mainline"
        return "baseline"

    if selected_source == "fused":
        if writer_status != "ready" or not str(writer_output.get("proposed_answer", "") or "").strip():
            return "mainline"
        return "fused"

    if str(mainline_bundle.get("answer", "") or "").strip() or str(mainline_payload.get("response_text", "") or "").strip():
        return "mainline"
    return "mainline"


def _build_final_emit_payload(
    *,
    state: State,
    mainline_bundle: Dict[str, Any],
    selected_source: str = "mainline",
    source_switch_enabled: bool = False,
    writer_output: Optional[Dict[str, Any]] = None,
    writer_status: Optional[str] = None,
    fusion_verdict: Optional[Dict[str, Any]] = None,
    judge_status: Optional[str] = None,
) -> Dict[str, Any]:
    mainline_payload = state.get("mainline_emit_payload", {})
    mainline_payload = mainline_payload if isinstance(mainline_payload, dict) else {}
    layer_done_raw = mainline_payload.get("layer_done", {})
    filtered_results_raw = mainline_payload.get("filtered_results", {})
    if not source_switch_enabled:
        return {
            "selected_source": selected_source if selected_source in {"mainline", "baseline", "fused"} else "mainline",
            "response_text": str(
                mainline_bundle.get("answer", "")
                or mainline_payload.get("response_text", "")
                or ""
            ),
            "bundle": dict(mainline_bundle),
            "summary_source": str(
                mainline_payload.get("summary_source", "")
                or mainline_bundle.get("summary_source", "")
                or ""
            ),
            "layer_done": dict(layer_done_raw) if isinstance(layer_done_raw, dict) else {},
            "filtered_results": dict(filtered_results_raw) if isinstance(filtered_results_raw, dict) else {},
        }

    selected_source = _select_final_source(
        state=state,
        source_switch_enabled=source_switch_enabled,
        writer_output=writer_output,
        writer_status=writer_status,
        fusion_verdict=fusion_verdict,
        judge_status=judge_status,
    )
    baseline_bundle = state.get("baseline_bundle", {})
    baseline_bundle = baseline_bundle if isinstance(baseline_bundle, dict) else {}
    writer_output = writer_output if isinstance(writer_output, dict) else state.get("writer_output", {})
    writer_output = writer_output if isinstance(writer_output, dict) else {}
    fusion_verdict = fusion_verdict if isinstance(fusion_verdict, dict) else state.get("fusion_verdict", {})
    fusion_verdict = fusion_verdict if isinstance(fusion_verdict, dict) else {}
    question = str(
        mainline_bundle.get("question", "")
        or baseline_bundle.get("question", "")
        or state.get("current_question", "")
        or ""
    ).strip()

    response_text = str(
        mainline_bundle.get("answer", "")
        or mainline_payload.get("response_text", "")
        or ""
    ).strip()
    bundle: Dict[str, Any] = dict(mainline_bundle)
    summary_source = str(
        mainline_payload.get("summary_source", "")
        or mainline_bundle.get("summary_source", "")
        or ""
    )

    if selected_source == "baseline":
        response_text = str(baseline_bundle.get("answer", "") or "").strip()
        bundle = dict(baseline_bundle)
        if question and not str(bundle.get("question", "") or "").strip():
            bundle["question"] = question
        bundle["answer"] = response_text
        summary_source = str(bundle.get("summary_source", "") or "baseline_sidecar")
        bundle["summary_source"] = summary_source
    elif selected_source == "fused":
        response_text = str(writer_output.get("proposed_answer", "") or "").strip()
        accepted_cards = _coerce_card_list(
            writer_output.get("accepted_cards", fusion_verdict.get("accepted_cards", []))
        )
        confidence_raw = fusion_verdict.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        summary_source = "fusion_writer_shadow"
        bundle = {
            "question": question,
            "answer": response_text,
            "accepted_cards": accepted_cards,
            "note": str(writer_output.get("note", "") or "").strip(),
            "confidence": confidence,
            "summary_source": summary_source,
            "evidence_cards": list(accepted_cards),
        }

    return {
        "selected_source": selected_source,
        "response_text": response_text,
        "bundle": dict(bundle),
        "summary_source": summary_source,
        "layer_done": dict(layer_done_raw) if isinstance(layer_done_raw, dict) else {},
        "filtered_results": dict(filtered_results_raw) if isinstance(filtered_results_raw, dict) else {},
    }


def _emit_final_answer(
    state: State,
    layer_done: Dict[str, bool],
    filtered_results: Dict[str, Any],
    response: AIMessage,
    bundle: Dict[str, Any],
    logger,
    *,
    selected_source: str = "mainline",
) -> Dict[str, object]:
    """Write the final answer into graph state without changing closeout semantics."""
    selected_source = selected_source if selected_source in {"mainline", "baseline", "fused"} else "mainline"
    update: Dict[str, object] = {
        "messages": [response],
        "is_last_step": True,
        "layer_done": layer_done,
        "final_answer_source": selected_source,
        "emitted_bundle": dict(bundle),
    }
    if selected_source == "mainline":
        update["multi_agent_bundle"] = bundle
        update["mainline_status"] = "emitted"
    if _results_pools_enabled():
        raw_stable = state.get("stable_findings", [])
        coerced_prev_type = ""
        if isinstance(raw_stable, list):
            stable = list(raw_stable)
        else:
            stable = []
            coerced_prev_type = type(raw_stable).__name__
        entry = _build_stable_finding_entry(
            question=str(bundle.get("question", "")),
            final_answer_text=str(bundle.get("answer", "")),
            filtered_results=filtered_results,
            state=state,
        )
        stable.append(entry)
        max_items = _stable_findings_max_items()
        if len(stable) > max_items:
            stable = stable[-max_items:]
        update["stable_findings"] = stable
        if coerced_prev_type:
            logger.log_event(
                "stable_findings_coerce",
                prev_type=coerced_prev_type,
                stable_len_after=len(stable),
            )
        logger.log_event(
            "stable_findings_update",
            stable_len=len(stable),
            evidence_count=len(entry.get("evidence", [])),
        )
    return update


def _resolve_final_emit_payload(state: State) -> Optional[Dict[str, Any]]:
    payload = state.get("final_emit_payload", {})
    payload = payload if isinstance(payload, dict) else {}
    mainline_payload = state.get("mainline_emit_payload", {})
    mainline_payload = mainline_payload if isinstance(mainline_payload, dict) else {}

    selected_source = str(payload.get("selected_source", "") or "mainline").strip().lower()
    if selected_source not in {"mainline", "baseline", "fused"}:
        selected_source = "mainline"

    response_text = str(
        payload.get("response_text", "")
        or mainline_payload.get("response_text", "")
        or ""
    ).strip()
    bundle = payload.get("bundle", {})
    if not isinstance(bundle, dict) or not bundle:
        bundle = state.get("multi_agent_bundle", {})
    if not isinstance(bundle, dict) or not bundle or not response_text:
        return None

    layer_done_raw = payload.get("layer_done", {})
    if not isinstance(layer_done_raw, dict) or not layer_done_raw:
        layer_done_raw = mainline_payload.get("layer_done", {})
    filtered_results_raw = payload.get("filtered_results", {})
    if not isinstance(filtered_results_raw, dict) or not filtered_results_raw:
        filtered_results_raw = mainline_payload.get("filtered_results", {})

    return {
        "selected_source": selected_source,
        "response_text": response_text,
        "bundle": dict(bundle),
        "summary_source": str(
            payload.get("summary_source", "")
            or mainline_payload.get("summary_source", "")
            or bundle.get("summary_source", "")
            or ""
        ),
        "layer_done": dict(layer_done_raw) if isinstance(layer_done_raw, dict) else {},
        "filtered_results": dict(filtered_results_raw) if isinstance(filtered_results_raw, dict) else {},
    }


async def manager_summary(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Integrate AgentOutputs, advance layers, and answer on the final layer."""
    node_started_at = time.perf_counter()
    layer_plan = state.get("layer_plan", {})
    current_layer = state.get("current_layer") or LAYER_ORDER[0]
    selected = layer_plan.get(current_layer, state.get("plan", []))
    analyst_results = _get_runtime_results_pool(state)
    filtered_results = {
        aid: res for aid, res in analyst_results.items() if not isinstance(res, dict) or res.get("parse_ok", True)
    }
    filtered_out = len(analyst_results) - len(filtered_results)
    pending = [aid for aid in selected if aid not in analyst_results]
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)

    def _emit_latency(path: str) -> None:
        _log_node_latency(
            logger,
            "manager_summary",
            node_started_at,
            current_layer=current_layer,
            path=path,
            pending_count=len(pending),
            result_count=len(filtered_results),
            filtered_out=filtered_out,
        )

    logger.log_event(
        "summary_start",
        current_layer=current_layer,
        pending=pending,
        results=list(filtered_results.keys()),
        filtered_out=filtered_out,
    )

    base_update: Dict[str, object] = {"plan": selected}

    if selected and pending:
        # Chain: dispatch next; Star: wait.
        chain_cursor = len(selected) - len(pending)
        _emit_latency("pending_wait")
        return {**base_update, "chain_cursor": chain_cursor}

    # Mark current layer done and advance if not final.
    layer_done = dict(state.get("layer_done", {}))
    layer_done[current_layer] = True
    next_layer = _next_layer(current_layer)
    if next_layer:
        debug_msg = AIMessage(
            content=f"[manager_summary] layer {current_layer} done -> advance to {next_layer}"
        )
        logger.log_event(
            "summary_end",
            current_layer=current_layer,
            filtered_out=filtered_out,
            results=list(filtered_results.keys()),
            next_layer=next_layer,
        )
        _emit_latency("advance_layer")
        return {
            "messages": [debug_msg],
            "layer_done": layer_done,
            "current_layer": next_layer,
            "plan": layer_plan.get(next_layer, []),
            "chain_cursor": 0,
            "fanout_targets": [],
        }

    # Final layer completed: produce user-facing summary.
    if runtime.context.enable_fair_fusion:
        summary_started_at = time.perf_counter()
        bundle, response = await _build_mainline_bundle(
            state=state,
            runtime=runtime,
            analyst_results=analyst_results,
            filtered_results=filtered_results,
            filtered_out=filtered_out,
            summary_source="manager_summary",
            logger=logger,
            current_layer=current_layer,
            node_started_at=summary_started_at,
        )
        _log_node_latency(
            logger,
            "summary",
            summary_started_at,
            current_layer=current_layer,
            source="manager_summary",
            filtered_out=filtered_out,
            result_count=len(filtered_results),
        )
        _emit_latency("stage_mainline_ready")
        return _stage_mainline_ready(
            bundle=bundle,
            response=response,
            layer_done=layer_done,
            filtered_results=filtered_results,
            summary_source="manager_summary",
        )

    result = await _run_final_summary(
        state=state,
        runtime=runtime,
        layer_done=layer_done,
        analyst_results=analyst_results,
        filtered_results=filtered_results,
        filtered_out=filtered_out,
        summary_source="manager_summary",
    )
    _emit_latency("final_summary")
    return result


async def finalize_summary(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Fallback finalizer: force a final summary when FINAL_LAYER has no pending agents."""
    node_started_at = time.perf_counter()
    current_layer = state.get("current_layer") or LAYER_ORDER[0]
    layer_done = dict(state.get("layer_done", {}))
    layer_done[current_layer] = True
    analyst_results = _get_runtime_results_pool(state)
    filtered_results = {
        aid: res for aid, res in analyst_results.items() if not isinstance(res, dict) or res.get("parse_ok", True)
    }
    filtered_out = len(analyst_results) - len(filtered_results)
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)
    if runtime.context.enable_fair_fusion:
        summary_started_at = time.perf_counter()
        bundle, response = await _build_mainline_bundle(
            state=state,
            runtime=runtime,
            analyst_results=analyst_results,
            filtered_results=filtered_results,
            filtered_out=filtered_out,
            summary_source="finalize_summary",
            logger=logger,
            current_layer=current_layer,
            node_started_at=summary_started_at,
        )
        _log_node_latency(
            logger,
            "summary",
            summary_started_at,
            current_layer=current_layer,
            source="finalize_summary",
            filtered_out=filtered_out,
            result_count=len(filtered_results),
        )
        result = _stage_mainline_ready(
            bundle=bundle,
            response=response,
            layer_done=layer_done,
            filtered_results=filtered_results,
            summary_source="finalize_summary",
        )
        _log_node_latency(
            logger,
            "finalize_summary",
            node_started_at,
            current_layer=current_layer,
            filtered_out=filtered_out,
            result_count=len(filtered_results),
        )
        return result

    result = await _run_final_summary(
        state=state,
        runtime=runtime,
        layer_done=layer_done,
        analyst_results=analyst_results,
        filtered_results=filtered_results,
        filtered_out=filtered_out,
        summary_source="finalize_summary",
    )
    _log_node_latency(
        logger,
        "finalize_summary",
        node_started_at,
        current_layer=current_layer,
        filtered_out=filtered_out,
        result_count=len(filtered_results),
    )
    return result


async def fusion_gate(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Judge-ready seam: side-effect-free gate that waits for both branches to settle."""
    return {}


async def fusion_judge_shadow(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Run a shadow-only fusion judge without changing the final answer source."""
    if state.get("judge_status") in {"ready", "error"}:
        return {}

    mainline_bundle = state.get("multi_agent_bundle", {})
    if not isinstance(mainline_bundle, dict) or not mainline_bundle:
        return {}

    baseline_status = str(state.get("baseline_status", "") or "")
    baseline_bundle = state.get("baseline_bundle", {})
    if baseline_status not in {"ready", "error", "disabled"}:
        return {}
    if baseline_status == "ready" and (not isinstance(baseline_bundle, dict) or not baseline_bundle):
        return {}

    question = str(
        mainline_bundle.get("question", "")
        or state.get("current_question", "")
    ).strip()
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)
    node_started_at = time.perf_counter()

    if baseline_status in {"error", "disabled"}:
        verdict = _build_degraded_fusion_verdict(
            baseline_status=baseline_status,
            reason=f"Baseline {baseline_status}; shadow verdict falls back to mainline.",
        )
        _log_node_latency(
            logger,
            "fusion_judge_shadow",
            node_started_at,
            baseline_status=baseline_status,
            decision=verdict["decision"],
            path="degraded",
        )
        return {"judge_status": "ready", "fusion_verdict": verdict}

    msgs: List[Dict[str, str]] = [
        {"role": "system", "content": prompts.FUSION_JUDGE_SHADOW_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "question": question,
                    "multi_agent_bundle": mainline_bundle,
                    "baseline_status": baseline_status,
                    "baseline_bundle": baseline_bundle if isinstance(baseline_bundle, dict) else {},
                },
                ensure_ascii=False,
            ),
        },
    ]
    metadata = {
        "run_id": run_id,
        "node_name": "fusion_judge_shadow",
        "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest()[:12] if question else "",
    }
    tags = ["react_agent", "fusion_judge_shadow"] + ([f"run_id:{run_id}"] if run_id else [])
    try:
        model = load_chat_model(runtime.context.model)
        response: AIMessage = await model.ainvoke(msgs, config={"metadata": metadata, "tags": tags})
        raw_text = get_message_text(response)
        json_text = _extract_json_object(raw_text)
        if not json_text:
            raise ValueError("fusion judge did not return a JSON object")
        parsed = json.loads(json_text)
        verdict = _normalize_fusion_verdict(
            parsed,
            fallback_decision="mainline",
            fallback_reason="Shadow judge returned an incomplete verdict; falling back to mainline.",
        )
        _log_node_latency(
            logger,
            "fusion_judge_shadow",
            node_started_at,
            baseline_status=baseline_status,
            decision=verdict["decision"],
            path="ready",
        )
        return {"judge_status": "ready", "fusion_verdict": verdict}
    except Exception as exc:
        verdict = _build_degraded_fusion_verdict(
            baseline_status="error",
            reason=f"Judge shadow failed: {type(exc).__name__}: {exc}",
        )
        _log_node_latency(
            logger,
            "fusion_judge_shadow",
            node_started_at,
            baseline_status=baseline_status,
            decision=verdict["decision"],
            path="error",
        )
        return {"judge_status": "error", "fusion_verdict": verdict}


async def fusion_writer_shadow(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Run a shadow-only fusion writer and stage a source-neutral final emit payload."""
    if state.get("writer_status") in {"ready", "error"}:
        return {}

    fusion_verdict = state.get("fusion_verdict", {})
    if not isinstance(fusion_verdict, dict) or not fusion_verdict:
        return {}

    mainline_bundle = state.get("multi_agent_bundle", {})
    if not isinstance(mainline_bundle, dict) or not mainline_bundle:
        return {}

    baseline_status = str(state.get("baseline_status", "") or "")
    baseline_bundle = state.get("baseline_bundle", {})
    if baseline_status not in {"ready", "error", "disabled"}:
        return {}
    if baseline_status == "ready" and (not isinstance(baseline_bundle, dict) or not baseline_bundle):
        return {}

    question = str(
        mainline_bundle.get("question", "")
        or state.get("current_question", "")
    ).strip()
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)
    node_started_at = time.perf_counter()

    if baseline_status in {"error", "disabled"}:
        writer_output = _build_degraded_writer_output(
            mainline_bundle=mainline_bundle,
            fusion_verdict=fusion_verdict,
            baseline_status=baseline_status,
            reason=f"Baseline {baseline_status}; writer shadow keeps mainline output.",
        )
        _log_node_latency(
            logger,
            "fusion_writer_shadow",
            node_started_at,
            baseline_status=baseline_status,
            selected_source=writer_output["selected_source"],
            path="degraded",
        )
        return {
            "writer_status": "ready",
            "writer_output": writer_output,
            "final_emit_payload": _build_final_emit_payload(
                state=state,
                mainline_bundle=mainline_bundle,
                selected_source="mainline",
                source_switch_enabled=runtime.context.enable_fair_fusion_source_switch,
                writer_output=writer_output,
                writer_status="ready",
                fusion_verdict=fusion_verdict,
                judge_status=state.get("judge_status", ""),
            ),
        }

    msgs: List[Dict[str, str]] = [
        {"role": "system", "content": prompts.FUSION_WRITER_SHADOW_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "question": question,
                    "fusion_verdict": fusion_verdict,
                    "multi_agent_bundle": mainline_bundle,
                    "baseline_status": baseline_status,
                    "baseline_bundle": baseline_bundle if isinstance(baseline_bundle, dict) else {},
                },
                ensure_ascii=False,
            ),
        },
    ]
    metadata = {
        "run_id": run_id,
        "node_name": "fusion_writer_shadow",
        "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest()[:12] if question else "",
    }
    tags = ["react_agent", "fusion_writer_shadow"] + ([f"run_id:{run_id}"] if run_id else [])
    fallback_accepted_cards = _coerce_card_list(fusion_verdict.get("accepted_cards", []))
    fallback_answer = str(mainline_bundle.get("answer", "") or "").strip()
    try:
        model = load_chat_model(runtime.context.model)
        response: AIMessage = await model.ainvoke(msgs, config={"metadata": metadata, "tags": tags})
        raw_text = get_message_text(response)
        json_text = _extract_json_object(raw_text)
        if not json_text:
            raise ValueError("fusion writer did not return a JSON object")
        parsed = json.loads(json_text)
        writer_output = _normalize_writer_output(
            parsed,
            fallback_answer=fallback_answer,
            fallback_selected_source="mainline",
            fallback_note="Shadow writer returned an incomplete output; falling back to mainline.",
            fallback_accepted_cards=fallback_accepted_cards,
        )
        _log_node_latency(
            logger,
            "fusion_writer_shadow",
            node_started_at,
            baseline_status=baseline_status,
            selected_source=writer_output["selected_source"],
            path="ready",
        )
        return {
            "writer_status": "ready",
            "writer_output": writer_output,
            "final_emit_payload": _build_final_emit_payload(
                state=state,
                mainline_bundle=mainline_bundle,
                selected_source="mainline",
                source_switch_enabled=runtime.context.enable_fair_fusion_source_switch,
                writer_output=writer_output,
                writer_status="ready",
                fusion_verdict=fusion_verdict,
                judge_status=state.get("judge_status", ""),
            ),
        }
    except Exception as exc:
        writer_output = _build_degraded_writer_output(
            mainline_bundle=mainline_bundle,
            fusion_verdict=fusion_verdict,
            baseline_status="error",
            reason=f"Writer shadow failed: {type(exc).__name__}: {exc}",
        )
        _log_node_latency(
            logger,
            "fusion_writer_shadow",
            node_started_at,
            baseline_status=baseline_status,
            selected_source=writer_output["selected_source"],
            path="error",
        )
        return {
            "writer_status": "error",
            "writer_output": writer_output,
            "final_emit_payload": _build_final_emit_payload(
                state=state,
                mainline_bundle=mainline_bundle,
                selected_source="mainline",
                source_switch_enabled=runtime.context.enable_fair_fusion_source_switch,
                writer_output=writer_output,
                writer_status="error",
                fusion_verdict=fusion_verdict,
                judge_status=state.get("judge_status", ""),
            ),
        }


async def final_emit(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Emit the staged final answer from a source-neutral payload without changing closeout semantics."""
    if state.get("final_answer_source") or state.get("is_last_step"):
        return {}
    payload = _resolve_final_emit_payload(state)
    if payload is None:
        return {}
    response_text = str(payload.get("response_text", "") or "")
    bundle = payload.get("bundle", {})
    layer_done = dict(payload.get("layer_done", {})) if isinstance(payload.get("layer_done", {}), dict) else {}
    filtered_results = (
        dict(payload.get("filtered_results", {}))
        if isinstance(payload.get("filtered_results", {}), dict)
        else {}
    )
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)
    node_started_at = time.perf_counter()
    response = AIMessage(content=response_text)
    update = _emit_final_answer(
        state=state,
        layer_done=layer_done,
        filtered_results=filtered_results,
        response=response,
        bundle=bundle,
        logger=logger,
        selected_source=str(payload.get("selected_source", "mainline") or "mainline"),
    )
    _log_node_latency(
        logger,
        "final_emit",
        node_started_at,
        current_layer=state.get("current_layer") or LAYER_ORDER[0],
        summary_source=str(payload.get("summary_source", "")),
        selected_source=str(payload.get("selected_source", "mainline") or "mainline"),
        result_count=len(filtered_results),
    )
    return update


async def mainline_emit(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Compatibility wrapper that delegates to the source-neutral final emit seam."""
    return await final_emit(state, runtime)


async def memory_update(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Update optional per-thread extractive summary after a completed turn."""
    if not _thread_summary_enabled():
        return {}
    if not state.get("is_last_step"):
        return {}
    new_summary = _build_thread_summary(state)
    if not new_summary:
        return {}
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)
    logger.log_event(
        "thread_summary_update",
        thread_summary_len=len(new_summary),
    )
    return {"thread_summary": new_summary}


def route_from_manager_summary(state: State) -> str:
    """Route based on layer completion, chain mode, and finality."""
    if state.get("is_last_step") and _thread_summary_enabled():
        return "memory_update"
    if state.get("is_last_step"):
        return "__end__"
    if state.get("mainline_status") == "ready":
        return "fusion_gate"

    current_layer = state.get("current_layer") or LAYER_ORDER[0]
    layer_plan = state.get("layer_plan", {})
    layer_mode = state.get("layer_mode", {})
    analyst_results = _get_runtime_results_pool(state)
    selected = state.get("plan", layer_plan.get(current_layer, []))
    pending = [aid for aid in selected if aid not in analyst_results]
    mode = _normalize_mode(layer_mode.get(current_layer, DEFAULT_MODES.get(current_layer, "Star")))

    if pending:
        if mode == "Chain":
            return "manager_broadcast"
        # For Star/Debate/Tree: broadcast once, then wait (noop) for parallel results.
        already_fanned_out = bool(state.get("fanout_targets"))
        return "noop" if already_fanned_out else "manager_broadcast"

    # No pending in current layer: if not final layer, proceed to next dispatch.
    if current_layer != FINAL_LAYER:
        return "manager_broadcast"
    return "finalize_summary"


def route_after_finalize(state: State) -> str:
    """After forced finalization, keep existing memory_update/end behavior."""
    if state.get("is_last_step") and _thread_summary_enabled():
        return "memory_update"
    if state.get("is_last_step"):
        return "__end__"
    if state.get("mainline_status") == "ready":
        return "fusion_gate"
    return "__end__"


def route_after_fusion_gate(state: State) -> str:
    """Route from the branch-safe fan-in seam without assuming barrier semantics."""
    if state.get("final_answer_source") or state.get("is_last_step"):
        return "__end__"
    if state.get("mainline_status") != "ready":
        return "__end__"
    payload = state.get("mainline_emit_payload", {})
    bundle = state.get("multi_agent_bundle", {})
    if not isinstance(payload, dict) or not payload:
        return "__end__"
    if not isinstance(bundle, dict) or not bundle:
        return "__end__"
    baseline_status = state.get("baseline_status", "")
    baseline_bundle = state.get("baseline_bundle", {})
    if baseline_status == "ready" and (not isinstance(baseline_bundle, dict) or not baseline_bundle):
        return "__end__"
    if baseline_status not in {"ready", "error", "disabled"}:
        return "__end__"
    judge_status = state.get("judge_status", "")
    if judge_status == "":
        return "fusion_judge_shadow"
    writer_status = state.get("writer_status", "")
    if judge_status in {"ready", "error"} and writer_status == "":
        return "fusion_writer_shadow"
    if writer_status in {"ready", "error"}:
        return "final_emit"
    return "__end__"


def route_after_fusion_judge(state: State) -> str:
    """After the shadow judge, continue into the shadow writer before final emit."""
    if state.get("final_answer_source") or state.get("is_last_step"):
        return "__end__"
    writer_status = state.get("writer_status", "")
    if state.get("judge_status") in {"ready", "error"} and writer_status == "":
        return "fusion_writer_shadow"
    if writer_status in {"ready", "error"}:
        return "final_emit"
    return "__end__"


def route_after_fusion_writer(state: State) -> str:
    """After the shadow writer, continue to final emit once writer state is terminal."""
    if state.get("final_answer_source") or state.get("is_last_step"):
        return "__end__"
    if state.get("writer_status") in {"ready", "error"}:
        return "final_emit"
    return "__end__"


def route_after_final_emit(state: State) -> str:
    """After staged final emit, preserve the existing memory_update/end behavior."""
    if state.get("is_last_step") and _thread_summary_enabled():
        return "memory_update"
    return "__end__"


def route_after_mainline_emit(state: State) -> str:
    """Compatibility wrapper for the legacy route name."""
    return route_after_final_emit(state)


async def noop(state: State, runtime: Runtime[Context]) -> Dict[str, object]:
    """No-op placeholder when waiting for parallel results."""
    return {}


builder = StateGraph(State, input_schema=InputState, context_schema=Context)

builder.add_node("router", router_node)
builder.add_node("baseline_sidecar", run_baseline_sidecar)
builder.add_node("fusion_gate", fusion_gate)
builder.add_node("fusion_judge_shadow", fusion_judge_shadow)
builder.add_node("fusion_writer_shadow", fusion_writer_shadow)
builder.add_node("manager_broadcast", manager_broadcast)
builder.add_node("manager_summary", manager_summary)
builder.add_node("finalize_summary", finalize_summary)
builder.add_node("final_emit", final_emit)
builder.add_node("mainline_emit", mainline_emit)
builder.add_node("memory_update", memory_update)
builder.add_node("noop", noop)

for agent_id, node_name in AGENT_NODE_NAMES.items():
    builder.add_node(node_name, _build_agent_node(agent_id))

builder.add_edge("__start__", "router")
builder.add_edge("router", "manager_broadcast")
builder.add_edge("router", "baseline_sidecar")
builder.add_edge("baseline_sidecar", "fusion_gate")

for node_name in AGENT_NODE_NAMES.values():
    builder.add_edge(node_name, "manager_summary")

builder.add_edge("memory_update", "__end__")

builder.add_conditional_edges(
    "manager_summary",
    route_from_manager_summary,
    {
        "__end__": "__end__",
        "memory_update": "memory_update",
        "fusion_gate": "fusion_gate",
        "finalize_summary": "finalize_summary",
        "noop": "noop",
        "manager_broadcast": "manager_broadcast",
    },
)

builder.add_conditional_edges(
    "finalize_summary",
    route_after_finalize,
    {
        "__end__": "__end__",
        "fusion_gate": "fusion_gate",
        "memory_update": "memory_update",
    },
)

builder.add_conditional_edges(
    "fusion_gate",
    route_after_fusion_gate,
    {
        "__end__": "__end__",
        "fusion_judge_shadow": "fusion_judge_shadow",
        "fusion_writer_shadow": "fusion_writer_shadow",
        "final_emit": "final_emit",
    },
)

builder.add_conditional_edges(
    "fusion_judge_shadow",
    route_after_fusion_judge,
    {
        "__end__": "__end__",
        "fusion_writer_shadow": "fusion_writer_shadow",
        "final_emit": "final_emit",
    },
)

builder.add_conditional_edges(
    "fusion_writer_shadow",
    route_after_fusion_writer,
    {
        "__end__": "__end__",
        "final_emit": "final_emit",
    },
)

builder.add_conditional_edges(
    "final_emit",
    route_after_final_emit,
    {
        "__end__": "__end__",
        "memory_update": "memory_update",
    },
)

builder.add_conditional_edges(
    "mainline_emit",
    route_after_mainline_emit,
    {
        "__end__": "__end__",
        "memory_update": "memory_update",
    },
)

_GRAPH_NAME = "Layered Router-Manager-Agent Demo (L1-L2-L3-L4)"

# Default export for Studio/CLI and existing callers: no business-layer checkpointer.
graph, graph_persistent = compile_graph_variants(builder, _GRAPH_NAME)


def get_graph_for_invoke(thread_id: Optional[str] = None):
    """Return persistent graph only when both a thread_id and an enabled checkpointer exist."""
    return select_graph_for_invoke(thread_id, graph, graph_persistent)
