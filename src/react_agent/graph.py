"""LangGraph: 4-layer Router -> Manager -> Agents -> Final summary."""

from __future__ import annotations

import json
import os
import re
import uuid
import hashlib
import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command, Send

from react_agent import prompts
from react_agent.agents import (
    AGENT_METADATA,
    AGENT_TOOLS,
    AgentOutput,
    agents_by_layer,
    load_metadata_from_dir,
    register_agent,
)
from react_agent.context import Context
from react_agent.default_agents import _build_agent_tool, register_builtin_agents
from react_agent.generic_agent import build_generic_agent_tool
from react_agent.run_logger import get_run_logger
from react_agent.state import InputState, State
from react_agent.utils import get_message_text, load_chat_model

LAYER_ORDER: List[str] = ["L1", "L2", "L4", "L5"]
DEFAULT_MODES: Dict[str, str] = {"L1": "Chain", "L2": "Star", "L4": "Star", "L5": "Chain"}


def _truncate(text: str, limit: int = 4000) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text if len(text) <= limit else text[: limit - 8] + "...[trunc]"


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

# Register agents: config/agents as primary source; built-ins optional via env.
CONFIG_AGENT_DIR = Path(__file__).resolve().parents[2] / "config" / "agents"
enable_builtin = os.environ.get("ENABLE_BUILTIN_AGENTS", "0") == "1"
config_exists = CONFIG_AGENT_DIR.exists()
if enable_builtin or not config_exists:
    register_builtin_agents()
if config_exists:
    load_metadata_from_dir(CONFIG_AGENT_DIR)
for aid, meta in list(AGENT_METADATA.items()):
    if aid in AGENT_TOOLS:
        continue
    # Prefer LLM tool using description as profile; fallback to stub if missing description.
    desc = (meta.description or "").strip()
    if desc:
        if aid == "a01_cio_orchestrator":
            desc = (
                f"{desc}\n[Router alignment] 严格根据 router_plan_summary 执行任务拆解，"
                "不得新增/删除 agent，只能解释既定分工、补充验收点与风险门禁。"
            )
        tool = _build_agent_tool(aid, desc, default_allow_search=True)
    else:
        tool = build_generic_agent_tool(aid, meta.description)
    register_agent(meta, tool)

include_disabled = os.environ.get("INCLUDE_DISABLED_AGENTS", "0") == "1"
AGENT_IDS_FOR_NODES: List[str] = [
    aid for aid, meta in AGENT_METADATA.items() if include_disabled or meta.default_enabled
]
AGENT_NODE_NAMES: Dict[str, str] = {aid: f"agent_{aid}_node" for aid in AGENT_IDS_FOR_NODES}


def _get_latest_user_question(messages: List[AnyMessage]) -> str:
    """Return the most recent human question."""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return get_message_text(msg)
    return get_message_text(messages[-1]) if messages else ""


def _extract_json_str(text: str) -> Optional[str]:
    """Best-effort extract a JSON object string; return None if not parseable."""
    # First, try direct parse.
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # Heuristic: use the substring between first '{' and last '}'.
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None
    candidate = text[first : last + 1]
    try:
        json.loads(candidate)
        return candidate
    except Exception:
        return None


def _normalize_mode(mode: str) -> str:
    """Return a single valid mode (Star/Chain/Debate/Tree) with light tolerance."""
    allowed = {"star", "chain", "debate", "tree"}
    if not mode:
        return "Star"
    raw = str(mode).strip()
    # Split by common separators if user/LLM returns joined string.
    for sep in [",", ";", "|", "/"]:
        if sep in raw:
            raw = raw.split(sep)[0]
            break
    # Also handle accidental space-joined tokens.
    raw = raw.strip().split()[0]
    token = raw.lower()
    if token in allowed:
        return token.title()
    return "Star"


def _default_layer_plan() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    plan: Dict[str, List[str]] = {}
    modes: Dict[str, str] = {}
    for layer in LAYER_ORDER:
        ids = agents_by_layer(layer)
        modes[layer] = DEFAULT_MODES.get(layer, "Star")
        if not ids:
            plan[layer] = []
            continue
        if layer == "L1":
            plan[layer] = ids[:1]
        elif layer == "L2":
            plan[layer] = ids[: min(5, len(ids))]
        elif layer == "L4":
            plan[layer] = ids[: min(3, len(ids))]
        else:  # L5
            plan[layer] = ids[:1]
    return plan, modes


def _parse_router_layers(raw: str) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """Parse router JSON into layer_plan/layer_mode with compatibility fallback."""
    json_str = _extract_json_str(raw)
    if not json_str:
        return _default_layer_plan()
    try:
        parsed = json.loads(json_str)
    except Exception:
        return _default_layer_plan()

    if not isinstance(parsed, dict):
        return _default_layer_plan()

    # Compatibility: old format {"selected":[...]}
    if "layers" not in parsed and "selected" in parsed:
        plan, modes = _default_layer_plan()
        selected = [aid for aid in parsed.get("selected", []) if aid in agents_by_layer("L2")]
        plan["L2"] = selected or plan["L2"]
        modes["L2"] = "Star"
        return plan, modes

    layers_raw = parsed.get("layers")
    if not isinstance(layers_raw, list):
        return _default_layer_plan()

    default_plan, default_modes = _default_layer_plan()

    layer_plan: Dict[str, List[str]] = {}
    layer_mode: Dict[str, str] = {}
    for layer_entry in layers_raw:
        if not isinstance(layer_entry, dict):
            continue
        layer = layer_entry.get("layer")
        if not layer or layer not in LAYER_ORDER:
            continue
        mode = _normalize_mode(layer_entry.get("mode"))
        selected_raw = layer_entry.get("selected", []) or []
        selected: List[str] = []
        for aid in selected_raw:
            if aid in AGENT_METADATA and (AGENT_METADATA[aid].layer or "").upper() == layer and AGENT_METADATA[aid].default_enabled:
                selected.append(aid)
        # If router tried to pick names but all invalid, fall back to defaults for this layer.
        if selected_raw and not selected:
            selected = default_plan.get(layer, [])
        if layer == "L2" and len(selected) > 5:
            selected = selected[:5]
        layer_plan[layer] = selected
        layer_mode[layer] = mode

    for layer in LAYER_ORDER:
        layer_plan.setdefault(layer, default_plan.get(layer, []))
        layer_mode.setdefault(layer, default_modes.get(layer, "Star"))

    return layer_plan, layer_mode


def _next_layer(current_layer: str) -> Optional[str]:
    if current_layer not in LAYER_ORDER:
        return None
    idx = LAYER_ORDER.index(current_layer)
    return LAYER_ORDER[idx + 1] if idx + 1 < len(LAYER_ORDER) else None


async def router_node(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Router: produce per-layer plan and modes."""
    model = load_chat_model(runtime.context.model)
    question = _get_latest_user_question(list(state["messages"]))
    run_id = state.get("run_id") or runtime.context.run_id or uuid.uuid4().hex[:8]
    runtime.context.run_id = run_id
    logger = get_run_logger(run_id)
    agent_catalog = {layer: agents_by_layer(layer) for layer in LAYER_ORDER}
    system_prompt = prompts.ROUTER_SYSTEM_PROMPT.format(
        system_time=datetime.now(tz=UTC).isoformat(),
        agent_catalog=json.dumps(agent_catalog, ensure_ascii=False),
    )
    msgs = [{"role": "system", "content": system_prompt}, *state["messages"]]
    try:
        metadata = {
            "run_id": run_id,
            "layer": "L1",
            "mode": DEFAULT_MODES.get("L1", "Chain"),
            "node_name": "router",
            "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest()[:12] if question else "",
        }
        tags = ["react_agent", f"run_id:{run_id}", "layer:L1"]
        response: AIMessage = await model.ainvoke(msgs, config={"metadata": metadata, "tags": tags})
        raw_text = get_message_text(response)
    except Exception as exc:
        response = AIMessage(content=f"[router fallback] {exc}")
        raw_text = "{}"
    print("[ROUTER RAW OUTPUT]", raw_text)
    logger.log_event(
        "router_decision",
        question=_truncate(question),
        raw=_truncate(raw_text),
    )
    layer_plan, layer_mode = _parse_router_layers(raw_text)
    current_layer = LAYER_ORDER[0]
    logger.log_event(
        "run_start",
        question=_truncate(question),
        current_layer=current_layer,
        run_id=run_id,
        layer_plan=_truncate(layer_plan),
        layer_mode=layer_mode,
    )
    return {
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
        # Signal a fresh turn so downstream merges clear old analyst_results.
        "analyst_results": {"__reset__": True},
    }


async def manager_broadcast(
    state: State, runtime: Runtime[Context]
) -> Command:
    """Manager: dispatch within current layer according to mode."""
    layer_plan = state.get("layer_plan", {})
    layer_mode = state.get("layer_mode", {})
    current_layer = state.get("current_layer") or LAYER_ORDER[0]
    selected = layer_plan.get(current_layer, [])
    mode = _normalize_mode(layer_mode.get(current_layer, DEFAULT_MODES.get(current_layer, "Star")))
    results = state.get("analyst_results", {})
    question = state.get("current_question") or _get_latest_user_question(list(state.get("messages", [])))
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)

    remaining = [aid for aid in selected if aid not in results]
    debug_msgs: List[AIMessage] = []

    if not selected:
        debug_msgs.append(
            AIMessage(content=f"[manager_broadcast] layer {current_layer} empty -> skip")
        )
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
            return Command(
                goto="manager_summary",
                update={"messages": debug_msgs, "plan": selected, "fanout_targets": remaining},
            )
        if next_id == "a01_cio_orchestrator":
            assignment_text = prompts.MANAGER_ASSIGNMENT_ORCHESTRATOR.format(
                question=question,
                router_plan_summary=_summarize_router_plan(layer_plan, layer_mode),
            )
        else:
            assignment_text = prompts.MANAGER_ASSIGNMENT_USER.format(
                question=question,
                plan=", ".join(selected),
                finished=", ".join(results.keys()) or "none",
                next_id=next_id,
                profile_label=AGENT_METADATA.get(next_id, None).description if next_id in AGENT_METADATA else next_id,
                layer=current_layer,
                mode=mode,
            )
        branch_state = dict(state)
        branch_state["messages"] = [
            *state["messages"],
            HumanMessage(content=assignment_text),
        ]
        debug_msgs.append(
            AIMessage(content=f"[manager_broadcast] chain dispatch -> {next_id} (layer {current_layer})")
        )
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
        if agent_id == "a01_cio_orchestrator":
            assignment_text = prompts.MANAGER_ASSIGNMENT_ORCHESTRATOR.format(
                question=question,
                router_plan_summary=_summarize_router_plan(layer_plan, layer_mode),
            )
        else:
            assignment_text = prompts.MANAGER_ASSIGNMENT_USER.format(
                question=question,
                plan=", ".join(selected),
                finished=", ".join(results.keys()) or "none",
                next_id=agent_id,
                profile_label=AGENT_METADATA.get(agent_id, None).description
                if agent_id in AGENT_METADATA
                else agent_id,
                layer=current_layer,
                mode=mode,
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
            "shared_context": state.get("analyst_results", {}),
            "history": [],
            "tools_config": {
                "allow_search": False if agent_id == "a01_cio_orchestrator" else True,
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
                agent_id=agent_id,
                layer=current_layer,
                mode=mode,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            output = _agent_error_output(agent_id, exc)
        analyst_results = dict(state.get("analyst_results", {}))
        analyst_results[agent_id] = output
        logger.log_event(
            "agent_end",
            agent_id=agent_id,
            layer=current_layer,
            mode=mode,
            parse_ok=output.get("parse_ok"),
            confidence=output.get("confidence"),
        )
        ai_msg = AIMessage(
            content=json.dumps({"agent_id": agent_id, "output": output}, ensure_ascii=False, indent=2)
        )
        return {
            "messages": [ai_msg],
            "analyst_results": analyst_results,
        }

    _node.__name__ = f"{agent_id}_agent_node"
    return _node


async def manager_summary(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Manager: integrate AgentOutputs; advance layers; only answer at L5."""
    layer_plan = state.get("layer_plan", {})
    layer_mode = state.get("layer_mode", {})
    current_layer = state.get("current_layer") or LAYER_ORDER[0]
    selected = layer_plan.get(current_layer, state.get("plan", []))
    analyst_results = state.get("analyst_results", {})
    filtered_results = {
        aid: res for aid, res in analyst_results.items() if not isinstance(res, dict) or res.get("parse_ok", True)
    }
    filtered_out = len(analyst_results) - len(filtered_results)
    pending = [aid for aid in selected if aid not in analyst_results]
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)
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
        return {
            "messages": [debug_msg],
            "layer_done": layer_done,
            "current_layer": next_layer,
            "plan": layer_plan.get(next_layer, []),
            "chain_cursor": 0,
            "fanout_targets": [],
        }

    # Final layer (L5) completed: produce user-facing summary.
    model = load_chat_model(runtime.context.model)
    system_prompt = runtime.context.system_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )
    question = state.get("current_question") or _get_latest_user_question(list(state.get("messages", [])))
    meta_note = ""
    if filtered_out > 0:
        meta_note = f"\n[meta] 本轮有 {filtered_out} 条输出因解析失败未参与汇总。\n"
    user_msg = prompts.MANAGER_SUMMARY_USER.format(
        question=question,
        layer_plan=layer_plan,
        layer_mode=layer_mode,
        analyst_results=filtered_results,
    )
    user_msg = meta_note + user_msg
    base_msgs = [
        {"role": "system", "content": system_prompt},
        *state.get("messages", []),
        {"role": "user", "content": user_msg},
    ]
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
    logger.log_event(
        "summary_end",
        current_layer=current_layer,
        filtered_out=filtered_out,
        results=list(filtered_results.keys()),
        summary=_truncate(get_message_text(response)),
    )
    return {"messages": [response], "is_last_step": True, "layer_done": layer_done}


def route_from_manager_summary(state: State) -> str:
    """Route based on layer completion, chain mode, and finality."""
    if state.get("is_last_step"):
        return "__end__"

    current_layer = state.get("current_layer") or LAYER_ORDER[0]
    layer_plan = state.get("layer_plan", {})
    layer_mode = state.get("layer_mode", {})
    analyst_results = state.get("analyst_results", {})
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
    if current_layer != "L5":
        return "manager_broadcast"
    return "__end__"


async def noop(state: State, runtime: Runtime[Context]) -> Dict[str, object]:
    """No-op placeholder when waiting for parallel results."""
    return {}


builder = StateGraph(State, input_schema=InputState, context_schema=Context)

builder.add_node("router", router_node)
builder.add_node("manager_broadcast", manager_broadcast)
builder.add_node("manager_summary", manager_summary)
builder.add_node("noop", noop)

for agent_id, node_name in AGENT_NODE_NAMES.items():
    builder.add_node(node_name, _build_agent_node(agent_id))

builder.add_edge("__start__", "router")
builder.add_edge("router", "manager_broadcast")

for node_name in AGENT_NODE_NAMES.values():
    builder.add_edge(node_name, "manager_summary")

builder.add_conditional_edges(
    "manager_summary",
    route_from_manager_summary,
    {"__end__": "__end__", "noop": "noop", "manager_broadcast": "manager_broadcast"},
)

graph = builder.compile(name="Layered Router-Manager-Agent Demo (L1-L2-L4-L5)")
