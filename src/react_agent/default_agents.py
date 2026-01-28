"""Built-in analyst agent tools and registrations."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from langgraph.runtime import get_runtime

from react_agent import prompts
from react_agent.agents import AgentMetadata, AgentOutput, register_agent
from react_agent.context import Context
from react_agent.tools import build_tavily_search, tavily_search
from react_agent.utils import get_message_text, load_chat_model


async def _call_with_tools(tool_list: List[BaseTool], messages: List[Dict[str, Any]]) -> AIMessage:
    """Run the tool-calling loop until no tool_calls remain."""
    runtime = get_runtime(Context)
    run_id = ""
    model_name = ""
    if runtime and getattr(runtime, "context", None):
        run_id = getattr(runtime.context, "run_id", "") or ""
        model_name = runtime.context.model
    base_metadata = {"run_id": run_id, "node_name": "agent_tool"}
    base_tags = ["react_agent"] + ([f"run_id:{run_id}"] if run_id else [])
    model = load_chat_model(model_name).bind_tools(tool_list)
    msgs: List[Any] = list(messages)
    while True:
        ai_msg: AIMessage = await model.ainvoke(msgs, config={"metadata": base_metadata, "tags": base_tags})
        if not ai_msg.tool_calls:
            return ai_msg
        tool_messages: List[ToolMessage] = []
        for tc in ai_msg.tool_calls:
            tool_obj = next((t for t in tool_list if getattr(t, "name", "") == tc["name"]), None)
            if not tool_obj:
                return ai_msg
            result = await tool_obj.ainvoke(tc["args"], config={"metadata": base_metadata, "tags": base_tags})
            tool_messages.append(
                ToolMessage(content=str(result), name=tc["name"], tool_call_id=tc["id"])
            )
        msgs.append(ai_msg)
        msgs.extend(tool_messages)


def _parse_agent_output(raw: str) -> AgentOutput:
    """Parse Agent output JSON with a tolerant fallback."""

    def _extract_json(text: str) -> str | None:
        try:
            json.loads(text)
            return text
        except Exception:
            match = re.search(r"\{.*?\}", text, flags=re.S)
            return match.group(0) if match else None

    json_str = _extract_json(raw) or ""
    default: AgentOutput = {
        "analysis": f"[PARSE_FALLBACK] {raw.strip()}",
        "key_points": [],
        "evidence": [],
        "confidence": 0.5,
        "parse_ok": False,
    }
    if not json_str:
        return default
    try:
        parsed = json.loads(json_str)
        try:
            confidence = float(parsed.get("confidence", default["confidence"]))
        except Exception:
            confidence = default["confidence"]
        parse_ok_val = parsed.get("parse_ok", True)
        parse_ok = parse_ok_val if isinstance(parse_ok_val, bool) else True
        output: AgentOutput = {
            "analysis": parsed.get("analysis", default["analysis"]),
            "key_points": parsed.get("key_points", default["key_points"]),
            "evidence": parsed.get("evidence", default["evidence"]),
            "confidence": confidence,
            "parse_ok": parse_ok,
        }
        for key, value in parsed.items():
            if key not in output:
                output[key] = value
        return output
    except Exception:
        return default


def _build_agent_tool(agent_id: str, profile: str, *, default_allow_search: bool = False) -> BaseTool:
    """Build a tool that conforms to AgentInput/Output."""

    @tool(f"agent_{agent_id}")
    async def _agent_tool(
        question: str,
        subtask: str,
        shared_context: Dict[str, Any] | None = None,
        history: List[Dict[str, Any]] | None = None,
        tools_config: Dict[str, Any] | None = None,
        router_plan_summary: str | None = None,
    ) -> AgentOutput:
        """Handle AgentInput and emit AgentOutput."""

        shared_context = shared_context or {}
        history = history or []
        tools_config = tools_config or {}

        if agent_id == "a01_cio_orchestrator":
            system_prompt = prompts.ORCHESTRATOR_SYSTEM_PROMPT
        elif agent_id == "a25_report_center":
            system_prompt = prompts.REPORT_CENTER_SYSTEM_PROMPT
        else:
            system_prompt = prompts.ANALYST_SYSTEM_PROMPT.format(profile=profile)
            system_prompt += "\n请使用 JSON 输出，包含 analysis(str), key_points(list[str]), evidence(list[str]), confidence(float,0~1)"

        prefix = (
            "Following is your task context in JSON. Read the question and subtask, use shared_context if helpful.\n"
            "- Do NOT repeat the subtask verbatim; provide your own analysis.\n"
            "- Output exactly one JSON object with analysis/key_points/evidence/confidence.\n\n"
        )
        user_content = prefix + json.dumps(
            {
                "question": question,
                "subtask": subtask,
                "shared_context": shared_context,
                "history": history,
                "tools_config": tools_config,
                "router_plan_summary": router_plan_summary,
            },
            ensure_ascii=False,
        )

        base_msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        allow_search = tools_config.get("allow_search", default_allow_search)
        tool_list: List[BaseTool] = []
        if allow_search:
            max_results = tools_config.get("max_search_results")
            if max_results is None:
                runtime = get_runtime(Context)
                if runtime and getattr(runtime, "context", None):
                    max_results = getattr(runtime.context, "max_search_results", None)
            try:
                max_results_int = int(max_results) if max_results is not None else None
            except (TypeError, ValueError):
                max_results_int = None
            if max_results_int and max_results_int > 0:
                tool_list = [build_tavily_search(max_results_int)]
            else:
                tool_list = [tavily_search]
        response = await _call_with_tools(tool_list or [], base_msgs)
        first_parsed = _parse_agent_output(get_message_text(response))
        if first_parsed.get("parse_ok", True):
            return first_parsed

        # Retry once with a strict JSON-only prompt.
        retry_prompt = (
            "只返回合法 JSON 对象，禁止解释或多余文字，键必须是 "
            '{"analysis","key_points","evidence","confidence"}，值保持原语种内容。'
        )
        retry_msgs = [
            {"role": "system", "content": retry_prompt},
            {"role": "user", "content": user_content},
        ]
        retry_resp = await _call_with_tools(tool_list or [], retry_msgs)
        retry_parsed = _parse_agent_output(get_message_text(retry_resp))
        return retry_parsed

    return _agent_tool


def register_builtin_agents() -> None:
    """Register the four built-in analyst Agents (legacy default set)."""
    for agent_id, profile in prompts.ANALYST_PROFILES.items():
        tool = _build_agent_tool(agent_id, profile)
        meta = AgentMetadata(
            id=agent_id,
            name=f"{agent_id.title()} Agent",
            description=profile[:60] + "...",
            capabilities=[agent_id],
            input_type="security|macro|industry",
            latency_level="medium",
            cost_level="normal",
            version="v0.1",
            layer="L2",
            team="builtin",
            role_type="system",
            default_enabled=True,
        )
        register_agent(meta, tool)
