"""LangGraph: Router -> Manager (broadcast) -> Parallel Agents -> Manager summary."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Dict, List, Optional

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command, Send

from react_agent import prompts
from react_agent.agents import AGENT_METADATA, AGENT_TOOLS, AgentOutput
from react_agent.context import Context
from react_agent.default_agents import register_builtin_agents
from react_agent.state import InputState, State
from react_agent.utils import get_message_text, load_chat_model

# Register builtin agents (news/filing/data/ecc). Extendable via scanning.
register_builtin_agents()

AGENT_IDS: List[str] = list(AGENT_METADATA.keys())
AGENT_NODE_NAMES: Dict[str, str] = {aid: f"agent_{aid}_node" for aid in AGENT_IDS}
DEFAULT_PLAN: List[str] = [aid for aid in ["news", "data", "ecc", "filing"] if aid in AGENT_IDS] or AGENT_IDS[:3]


def _get_latest_user_question(messages: List[AnyMessage]) -> str:
    """Return the most recent human question."""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return get_message_text(msg)
    return get_message_text(messages[-1]) if messages else ""


def _parse_router_plan(raw: str) -> List[str]:
    """Parse router JSON, tolerate extra text/code blocks, ensure non-empty plan."""

    def _extract_json_str(text: str) -> Optional[str]:
        try:
            json.loads(text)
            return text
        except Exception:
            match = re.search(r"\{.*?\}", text, flags=re.S)
            return match.group(0) if match else None

    json_str = _extract_json_str(raw)
    if not json_str:
        return DEFAULT_PLAN
    try:
        parsed = json.loads(json_str)
        selected = parsed.get("selected", [])
    except Exception:
        return DEFAULT_PLAN

    cleaned: List[str] = []
    for agent_id in selected:
        if agent_id in AGENT_IDS and agent_id not in cleaned:
            cleaned.append(agent_id)
    return cleaned or DEFAULT_PLAN


async def router_node(
    state: State, runtime: Runtime[Context]
) -> Dict[str, object]:
    """Router: produce plan only."""
    model = load_chat_model(runtime.context.model)
    question = _get_latest_user_question(list(state["messages"]))
    system_prompt = prompts.ROUTER_SYSTEM_PROMPT.format(
        analyst_ids=", ".join(AGENT_IDS),
        system_time=datetime.now(tz=UTC).isoformat(),
    )
    msgs = [{"role": "system", "content": system_prompt}, *state["messages"]]
    response: AIMessage = await model.ainvoke(msgs)
    raw_text = get_message_text(response)
    print("[ROUTER RAW OUTPUT]", raw_text)
    plan = _parse_router_plan(raw_text) or DEFAULT_PLAN
    return {
        "messages": [response],
        "plan": plan,
        "current_question": question,
        # Signal a fresh turn so downstream merges clear old analyst_results.
        "analyst_results": {"__reset__": True},
    }


async def manager_broadcast(
    state: State, runtime: Runtime[Context]
) -> Command:
    """Manager: fan-out tasks to all agents in plan."""
    plan = state.get("plan", [])
    question = state.get("current_question") or _get_latest_user_question(list(state["messages"]))
    if not plan:
        debug_msg = AIMessage(content="[manager_broadcast] no agents selected, skipping fan-out")
        return Command(
            goto="manager_summary",
            update={"messages": [debug_msg], "fanout_targets": plan},
        )

    sends: List[Send] = []
    debug_msg = AIMessage(content=f"[manager_broadcast] fan-out -> {', '.join(plan)}")
    for agent_id in plan:
        node_name = AGENT_NODE_NAMES.get(agent_id)
        if not node_name:
            continue
        assignment_text = prompts.MANAGER_ASSIGNMENT_USER.format(
            question=question,
            plan=", ".join(plan),
            finished=", ".join(state.get("analyst_results", {}).keys()) or "none",
            next_id=agent_id,
            profile_label=AGENT_METADATA.get(agent_id, None).description
            if agent_id in AGENT_METADATA
            else agent_id,
        )
        branch_state = dict(state)
        branch_state["messages"] = [
            *state["messages"],
            HumanMessage(content=assignment_text),
        ]
        sends.append(Send(node_name, branch_state))

    return Command(
        goto=sends or "manager_summary",
        update={"messages": [debug_msg], "fanout_targets": plan},
    )


def _build_agent_node(agent_id: str):
    async def _node(state: State, runtime: Runtime[Context]) -> Dict[str, object]:
        tool = AGENT_TOOLS.get(agent_id)
        if not tool:
            return {}
        question = state.get("current_question") or _get_latest_user_question(list(state.get("messages", [])))
        subtask = get_message_text(state["messages"][-1]) if state.get("messages") else ""
        agent_input = {
            "question": question,
            "subtask": subtask,
            "shared_context": state.get("analyst_results", {}),
            "history": [],
            "tools_config": {"allow_search": True},
        }
        output: AgentOutput = await tool.ainvoke(agent_input)
        analyst_results = dict(state.get("analyst_results", {}))
        analyst_results[agent_id] = output
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
    """Manager: integrate AgentOutputs; only answer when all done."""
    plan = state.get("plan", [])
    analyst_results = state.get("analyst_results", {})
    if len(analyst_results) < len(plan):
        return {}

    model = load_chat_model(runtime.context.model)
    system_prompt = runtime.context.system_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )
    question = state.get("current_question") or _get_latest_user_question(list(state.get("messages", [])))
    user_msg = prompts.MANAGER_SUMMARY_USER.format(
        question=question,
        plan=", ".join(plan),
        analyst_results=analyst_results,
    )
    base_msgs = [
        {"role": "system", "content": system_prompt},
        *state.get("messages", []),
        {"role": "user", "content": user_msg},
    ]
    response: AIMessage = await model.ainvoke(base_msgs)
    return {"messages": [response], "is_last_step": True}


def route_from_manager_summary(state: State) -> str:
    """Route to noop until all planned agents have reported back."""
    plan_len = len(state.get("plan", []))
    result_len = len(state.get("analyst_results", {}))
    if plan_len == 0:
        return "__end__"
    return "__end__" if result_len >= plan_len else "noop"


async def noop(state: State, runtime: Runtime[Context]) -> Dict[str, object]:
    """No-op placeholder when summary is invoked too early."""
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
    {"__end__": "__end__", "noop": "noop"},
)

graph = builder.compile(name="Router-Manager-Agent Demo (Parallel)")
