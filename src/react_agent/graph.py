"""LangGraph: 4-layer Router -> Manager -> Agents -> Final summary."""

from __future__ import annotations

import json
import os
import re
import uuid
import hashlib
import asyncio
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command, Send

from react_agent import contract_utils, prompts
from react_agent import router_parse
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

LAYER_ORDER: List[str] = router_parse.LAYER_ORDER
DEFAULT_MODES: Dict[str, str] = router_parse.DEFAULT_MODES
FINAL_LAYER: str = LAYER_ORDER[-1]


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


def _is_search_disabled_globally() -> bool:
    """Read DISABLE_SEARCH at call time so long-lived processes can reflect env updates."""
    return os.environ.get("DISABLE_SEARCH", "0") == "1"


def _maybe_make_checkpointer():
    """Optionally create a checkpointer from env without changing default behavior."""
    mode = (os.environ.get("REACT_AGENT_CHECKPOINTER", "none") or "none").strip().lower()
    if mode in {"", "none", "off", "0"}:
        return None

    if mode == "memory":
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except Exception as exc:
            warnings.warn(
                f"REACT_AGENT_CHECKPOINTER=memory requested but MemorySaver is unavailable: {exc}",
                RuntimeWarning,
            )
            return None
        return MemorySaver()

    if mode == "sqlite":
        db_path = (os.environ.get("REACT_AGENT_CHECKPOINT_DB", "checkpoints.db") or "checkpoints.db").strip()
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except Exception as exc:
            warnings.warn(
                "REACT_AGENT_CHECKPOINTER=sqlite requested but sqlite saver dependency is unavailable "
                f"(REACT_AGENT_CHECKPOINT_DB={db_path}): {exc}",
                RuntimeWarning,
            )
            return None
        try:
            if hasattr(SqliteSaver, "from_conn_string"):
                return SqliteSaver.from_conn_string(db_path)
            return SqliteSaver(db_path)  # type: ignore[call-arg]
        except Exception as exc:
            warnings.warn(
                f"Failed to initialize sqlite checkpointer (REACT_AGENT_CHECKPOINT_DB={db_path}): {exc}",
                RuntimeWarning,
            )
            return None

    warnings.warn(
        f"Unknown REACT_AGENT_CHECKPOINTER='{mode}', expected one of: none, memory, sqlite. "
        "Falling back to no checkpointer.",
        RuntimeWarning,
    )
    return None


def _thread_summary_enabled() -> bool:
    """Read thread summary toggle at call time to support long-lived processes."""
    raw = (os.environ.get("REACT_AGENT_THREAD_SUMMARY", "0") or "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def _thread_summary_max_chars() -> int:
    raw = (os.environ.get("REACT_AGENT_THREAD_SUMMARY_MAX_CHARS", "2000") or "2000").strip()
    try:
        val = int(raw)
    except Exception:
        warnings.warn(
            f"Invalid REACT_AGENT_THREAD_SUMMARY_MAX_CHARS='{raw}', using default 2000.",
            RuntimeWarning,
        )
        return 2000
    if val <= 0:
        warnings.warn(
            f"Invalid REACT_AGENT_THREAD_SUMMARY_MAX_CHARS='{raw}', using default 2000.",
            RuntimeWarning,
        )
        return 2000
    return val


def _latest_ai_message_text(messages: List[AnyMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return get_message_text(msg)
    return ""


def _build_thread_summary(state: State) -> str:
    """Build an extractive per-thread summary from explicit text only (no extra LLM call)."""
    msgs = list(state.get("messages", []))
    latest_question = state.get("current_question") or _get_latest_user_question(msgs)
    latest_final_answer = _latest_ai_message_text(msgs)
    if not latest_question and not latest_final_answer:
        return ""

    max_chars = _thread_summary_max_chars()
    # Reserve more space for final answer while guaranteeing bounded output.
    q_cap = max(120, min(600, max_chars // 3))
    a_cap = max(240, max_chars - q_cap - 80)
    parts: List[str] = []
    if latest_question:
        parts.append(f"Recent user question:\n{_truncate(latest_question, q_cap)}")
    if latest_final_answer:
        parts.append(f"Recent final answer:\n{_truncate(latest_final_answer, a_cap)}")
    summary = _truncate("\n\n".join(parts), max_chars)
    # _truncate() is shared legacy behavior; enforce a strict hard cap here for thread_summary.
    return summary[:max_chars]


def _thread_summary_system_msg(thread_summary: str) -> Dict[str, str]:
    return {
        "role": "system",
        "content": (
            "THREAD SUMMARY (extractive, prior-turn context; use only as supporting context):\n"
            f"{thread_summary}"
        ),
    }


def _messages_window_enabled() -> bool:
    """Read messages-window toggle at call time to support long-lived processes."""
    raw = (os.environ.get("REACT_AGENT_MESSAGES_WINDOW", "0") or "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def _messages_window_size() -> int:
    raw = (os.environ.get("REACT_AGENT_MESSAGES_WINDOW_SIZE", "20") or "20").strip()
    try:
        val = int(raw)
    except Exception:
        warnings.warn(
            f"Invalid REACT_AGENT_MESSAGES_WINDOW_SIZE='{raw}', using default 20.",
            RuntimeWarning,
        )
        return 20
    if val <= 0:
        warnings.warn(
            f"Invalid REACT_AGENT_MESSAGES_WINDOW_SIZE='{raw}', clamping to 1.",
            RuntimeWarning,
        )
        return 1
    return val


def _window_messages(full_messages: List[AnyMessage]) -> List[AnyMessage]:
    """Return a tail window of messages when enabled; otherwise return full messages."""
    if not _messages_window_enabled():
        return full_messages
    size = _messages_window_size()
    if len(full_messages) <= size:
        return full_messages
    return full_messages[-size:]


def _results_pools_enabled() -> bool:
    """Enable ephemeral/stable result pools via env; default off for backward compatibility."""
    raw = (os.environ.get("REACT_AGENT_RESULTS_POOLS", "0") or "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def _read_positive_int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = (os.environ.get(name, str(default)) or str(default)).strip()
    try:
        value = int(raw)
    except Exception:
        warnings.warn(
            f"Invalid {name}='{raw}', using default {default}.",
            RuntimeWarning,
        )
        return default
    if value < minimum:
        warnings.warn(
            f"Invalid {name}='{raw}', clamping to {minimum}.",
            RuntimeWarning,
        )
        return minimum
    return value


def _stable_findings_max_items() -> int:
    return _read_positive_int_env("REACT_AGENT_STABLE_FINDINGS_MAX_ITEMS", 50)


def _evidence_max_items() -> int:
    return _read_positive_int_env("REACT_AGENT_EVIDENCE_MAX_ITEMS", 20)


def _evidence_max_chars() -> int:
    return _read_positive_int_env("REACT_AGENT_EVIDENCE_MAX_CHARS", 500)


def _stable_text_max_chars() -> int:
    return _read_positive_int_env("REACT_AGENT_STABLE_TEXT_MAX_CHARS", 2000)


def _get_runtime_results_pool(state: State) -> Dict[str, AgentOutput]:
    """Return current-turn result pool; phase-guarded to keep default behavior unchanged."""
    if _results_pools_enabled():
        ep = state.get("ephemeral_results")
        if isinstance(ep, dict):
            return ep
    legacy = state.get("analyst_results", {})
    return legacy if isinstance(legacy, dict) else {}


def _build_stable_evidence_index(filtered_results: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract bounded evidence/index cards from filtered agent outputs."""
    max_items = _evidence_max_items()
    max_chars = _evidence_max_chars()
    cards: List[Dict[str, str]] = []
    for agent_id, result in filtered_results.items():
        if not isinstance(result, dict):
            continue
        evidence = result.get("evidence")
        if isinstance(evidence, list):
            for item in evidence:
                if not isinstance(item, str):
                    continue
                text = _truncate(item, max_chars).strip()
                if not text:
                    continue
                cards.append({"agent_id": str(agent_id), "kind": "evidence", "text": text})
                if len(cards) >= max_items:
                    return cards
        key_points = result.get("key_points")
        if isinstance(key_points, list):
            for item in key_points:
                if not isinstance(item, str):
                    continue
                text = _truncate(item, max_chars).strip()
                if not text:
                    continue
                cards.append({"agent_id": str(agent_id), "kind": "key_point", "text": text})
                if len(cards) >= max_items:
                    return cards
    return cards


def _build_stable_finding_entry(
    question: str,
    final_answer_text: str,
    filtered_results: Dict[str, Any],
    state: State,
) -> Dict[str, Any]:
    """Build a bounded stable finding entry from explicit final-turn artifacts."""
    text_cap = _stable_text_max_chars()
    return {
        "kind": "final_answer",
        "question": _truncate(question, text_cap),
        "final_answer": _truncate(final_answer_text, text_cap),
        "evidence": _build_stable_evidence_index(filtered_results),
        "run_id": str(state.get("run_id") or ""),
    }


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


def _normalize_mode(mode: str) -> str:
    """Return a single valid mode (Star/Chain/Debate/Tree) with light tolerance."""
    return router_parse.normalize_mode(mode)


def _build_agent_catalog() -> Dict[str, List[str]]:
    return {layer: agents_by_layer(layer) for layer in LAYER_ORDER}


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
                logger.log_event(
                    "router_provider_fallback",
                    router_model=router_model_name,
                    router_base_url=runtime.context.router_openai_base_url,
                    fallback_model=fallback_model_name,
                    error=str(exc),
                )
                response = await _invoke_router(fallback_model_name)
        else:
            response = await _invoke_router(router_model_name)
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
    layer_plan, layer_mode, parse_stats = router_parse.parse_router_layers_with_stats(
        raw_text, agent_catalog=agent_catalog
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
    }
    # Signal a fresh turn so downstream merges clear old analyst_results.
    update["analyst_results"] = {"__reset__": True}
    if _results_pools_enabled():
        update["ephemeral_results"] = {"__reset__": True}
        logger.log_event("ephemeral_reset", enabled=1)
    return update


async def manager_broadcast(
    state: State, runtime: Runtime[Context]
) -> Command:
    """Manager: dispatch within current layer according to mode."""
    layer_plan = state.get("layer_plan", {})
    layer_mode = state.get("layer_mode", {})
    current_layer = state.get("current_layer") or LAYER_ORDER[0]
    selected = layer_plan.get(current_layer, [])
    mode = _normalize_mode(layer_mode.get(current_layer, DEFAULT_MODES.get(current_layer, "Star")))
    results = _get_runtime_results_pool(state)
    question = state.get("current_question") or _get_latest_user_question(list(state.get("messages", [])))
    run_id = state.get("run_id") or runtime.context.run_id or ""
    logger = get_run_logger(run_id)

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
        used_contract = False
        step_count = 0
        task_id = ""
        profile_label = AGENT_METADATA.get(next_id, None).description if next_id in AGENT_METADATA else next_id
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
        profile_label = AGENT_METADATA.get(agent_id, None).description if agent_id in AGENT_METADATA else agent_id
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
                agent_id=agent_id,
                layer=current_layer,
                mode=mode,
                error_type=type(exc).__name__,
                error=str(exc),
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


async def manager_summary(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Manager: integrate AgentOutputs; advance layers; only answer at final layer."""
    layer_plan = state.get("layer_plan", {})
    layer_mode = state.get("layer_mode", {})
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

    # Final layer completed: produce user-facing summary.
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
    update: Dict[str, object] = {"messages": [response], "is_last_step": True, "layer_done": layer_done}
    if _results_pools_enabled():
        raw_stable = state.get("stable_findings", [])
        coerced_prev_type = ""
        if isinstance(raw_stable, list):
            stable = list(raw_stable)
        else:
            stable = []
            coerced_prev_type = type(raw_stable).__name__
        entry = _build_stable_finding_entry(
            question=question,
            final_answer_text=get_message_text(response),
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
    return "__end__"


async def noop(state: State, runtime: Runtime[Context]) -> Dict[str, object]:
    """No-op placeholder when waiting for parallel results."""
    return {}


builder = StateGraph(State, input_schema=InputState, context_schema=Context)

builder.add_node("router", router_node)
builder.add_node("manager_broadcast", manager_broadcast)
builder.add_node("manager_summary", manager_summary)
builder.add_node("memory_update", memory_update)
builder.add_node("noop", noop)

for agent_id, node_name in AGENT_NODE_NAMES.items():
    builder.add_node(node_name, _build_agent_node(agent_id))

builder.add_edge("__start__", "router")
builder.add_edge("router", "manager_broadcast")

for node_name in AGENT_NODE_NAMES.values():
    builder.add_edge(node_name, "manager_summary")

builder.add_edge("memory_update", "__end__")

builder.add_conditional_edges(
    "manager_summary",
    route_from_manager_summary,
    {
        "__end__": "__end__",
        "memory_update": "memory_update",
        "noop": "noop",
        "manager_broadcast": "manager_broadcast",
    },
)

_GRAPH_NAME = "Layered Router-Manager-Agent Demo (L1-L2-L3-L4)"

# Default export for Studio/CLI and existing callers: no business-layer checkpointer.
graph = builder.compile(name=_GRAPH_NAME)

# Optional Python/self-hosted variant with checkpointer (explicit opt-in via env + thread_id).
_checkpointer = _maybe_make_checkpointer()
graph_persistent = builder.compile(name=_GRAPH_NAME, checkpointer=_checkpointer) if _checkpointer is not None else None


def get_graph_for_invoke(thread_id: Optional[str] = None):
    """Return persistent graph only when both a thread_id and an enabled checkpointer exist."""
    if thread_id and graph_persistent is not None:
        return graph_persistent
    return graph
