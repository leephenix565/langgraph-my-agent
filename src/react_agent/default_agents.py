"""Built-in analyst agent tools and registrations."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from langgraph.runtime import get_runtime

from react_agent import prompts
from react_agent.agents import AgentMetadata, AgentOutput, register_agent
from react_agent.context import Context
from react_agent.run_logger import get_run_logger
from react_agent.tools import build_tavily_search, tavily_search
from react_agent.utils import get_message_text, load_chat_model


SPECIAL_RUNTIME_AGENT_IDS = {"a01_cio_orchestrator", "a25_report_center"}
PLACEHOLDER_SOURCE_TYPE = "source_type=llm_search_placeholder"
TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}


def _safe_runtime_context() -> Context | None:
    """Return the current LangGraph runtime context when invoked inside a graph."""
    try:
        runtime = get_runtime(Context)
    except Exception:
        return None
    if runtime and getattr(runtime, "context", None):
        return runtime.context
    return None


def _is_truthy_env(name: str) -> bool:
    return str(os.environ.get(name, "") or "").strip().lower() in TRUTHY_ENV_VALUES


def _effective_model_name() -> str:
    """Resolve a model name for direct AGENT_TOOLS calls as well as graph calls."""
    context = _safe_runtime_context()
    if context and getattr(context, "model", ""):
        return context.model
    try:
        return Context().model
    except Exception:
        return os.environ.get("MODEL", "deepseek/deepseek-chat")


def _is_placeholder_agent(agent_id: str, default_allow_search: bool) -> bool:
    return default_allow_search and agent_id not in SPECIAL_RUNTIME_AGENT_IDS


def _placeholder_evidence(
    *,
    search_status: str,
    error_type: str = "",
) -> str:
    parts = [PLACEHOLDER_SOURCE_TYPE, f"search_status={search_status}"]
    if error_type:
        parts.append(f"error_type={error_type}")
    return "; ".join(parts)


def _safe_runtime_error_type(exc: Exception) -> str:
    """Map environment/provider failures to public-safe categories."""
    if isinstance(exc, ImportError):
        return "provider_dependency_missing"
    error_type = type(exc).__name__
    message = str(exc).lower()
    if "api key" in message or "api_key" in message:
        return "provider_configuration_missing"
    if error_type in {"ValidationError", "ValueError"} and "key" in message:
        return "provider_configuration_missing"
    return error_type


def _annotate_placeholder_output(
    output: AgentOutput,
    *,
    agent_id: str,
    default_allow_search: bool,
    search_status: str,
) -> AgentOutput:
    """Mark generic internal-agent outputs as main-system LLM/search placeholders."""
    if not _is_placeholder_agent(agent_id, default_allow_search):
        return output
    evidence = list(output.get("evidence") or [])
    marker = _placeholder_evidence(search_status=search_status)
    if not any(PLACEHOLDER_SOURCE_TYPE in str(item) for item in evidence):
        evidence.append(marker)
    output["evidence"] = evidence
    output.setdefault("answer", output.get("analysis", ""))
    output["runtime_path"] = "INTERNAL_LLM_SEARCH_PLACEHOLDER"
    return output


def _placeholder_fail_soft_output(
    *,
    agent_id: str,
    exc: Exception,
    search_status: str,
    default_allow_search: bool,
) -> AgentOutput:
    """Return a structured placeholder failure instead of crashing direct calls."""
    error_type = _safe_runtime_error_type(exc)
    if not _is_placeholder_agent(agent_id, default_allow_search):
        return {
            "analysis": f"[AGENT_FAIL_SOFT] {agent_id} could not complete.",
            "key_points": [],
            "evidence": [f"source_type=internal_runtime_agent; error_type={error_type}"],
            "confidence": 0.0,
            "parse_ok": False,
        }
    return {
        "answer": "主系统内部 LLM+search 占位能力暂时无法完成调用。",
        "analysis": (
            f"[INTERNAL_LLM_SEARCH_PLACEHOLDER_FAIL_SOFT] {agent_id} "
            "placeholder could not complete; graph execution may continue with degraded evidence."
        ),
        "key_points": [
            "该结果来自主系统 generic placeholder，不等同于外部专属智能体已上线。",
            "provider 或搜索工具不可用时，结果会降级并标记 parse_ok=false。",
        ],
        "evidence": [
            _placeholder_evidence(search_status=search_status, error_type=error_type)
        ],
        "confidence": 0.3,
        "parse_ok": False,
        "runtime_path": "INTERNAL_LLM_SEARCH_PLACEHOLDER",
    }


def _model_trace_fields(model_spec: str) -> Dict[str, str]:
    spec = str(model_spec or "")
    provider = ""
    name = spec
    if "/" in spec:
        provider, name = spec.split("/", maxsplit=1)
    return {
        "model_spec": spec,
        "model_provider": provider,
        "model_name": name,
    }


async def _call_with_tools(tool_list: List[BaseTool], messages: List[Dict[str, Any]]) -> AIMessage:
    """Run the tool-calling loop until no tool_calls remain."""
    context = _safe_runtime_context()
    run_id = ""
    model_name = _effective_model_name()
    if context:
        run_id = getattr(context, "run_id", "") or ""
        model_name = getattr(context, "model", "") or model_name
    logger = get_run_logger(run_id) if run_id else None
    base_metadata = {"run_id": run_id, "node_name": "agent_tool"}
    base_tags = ["react_agent"] + ([f"run_id:{run_id}"] if run_id else [])
    model = load_chat_model(model_name).bind_tools(tool_list)
    msgs: List[Any] = list(messages)
    while True:
        invoke_started_at = time.perf_counter()
        try:
            ai_msg: AIMessage = await model.ainvoke(msgs, config={"metadata": base_metadata, "tags": base_tags})
        except Exception as exc:
            if logger:
                logger.log_event(
                    "agent_model_error",
                    node="agent_tool",
                    phase="model_ainvoke",
                    elapsed_ms=round((time.perf_counter() - invoke_started_at) * 1000.0, 3),
                    message_count=len(msgs),
                    tool_count=len(tool_list),
                    exception_type=type(exc).__name__,
                    exception_repr=repr(exc),
                    error=str(exc),
                    **_model_trace_fields(model_name),
                )
            raise
        if not ai_msg.tool_calls:
            return ai_msg
        tool_messages: List[ToolMessage] = []
        for tc in ai_msg.tool_calls:
            tool_obj = next((t for t in tool_list if getattr(t, "name", "") == tc["name"]), None)
            if not tool_obj:
                return ai_msg
            tool_started_at = time.perf_counter()
            try:
                result = await tool_obj.ainvoke(tc["args"], config={"metadata": base_metadata, "tags": base_tags})
            except Exception as exc:
                if logger:
                    logger.log_event(
                        "agent_tool_error",
                        node="agent_tool",
                        phase="tool_ainvoke",
                        tool_name=str(tc.get("name") or ""),
                        elapsed_ms=round((time.perf_counter() - tool_started_at) * 1000.0, 3),
                        message_count=len(msgs),
                        tool_count=len(tool_list),
                        exception_type=type(exc).__name__,
                        exception_repr=repr(exc),
                        error=str(exc),
                        **_model_trace_fields(model_name),
                    )
                raise
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
        search_disabled = _is_truthy_env("DISABLE_SEARCH")
        allow_search = False if search_disabled else tools_config.get(
            "allow_search", default_allow_search
        )
        search_status = "disabled" if not allow_search else "enabled"
        tool_list: List[BaseTool] = []
        if allow_search:
            max_results = tools_config.get("max_search_results")
            if max_results is None:
                context = _safe_runtime_context()
                if context:
                    max_results = getattr(context, "max_search_results", None)
            try:
                max_results_int = int(max_results) if max_results is not None else None
            except (TypeError, ValueError):
                max_results_int = None
            try:
                if max_results_int and max_results_int > 0:
                    tool_list = [build_tavily_search(max_results_int)]
                else:
                    tool_list = [tavily_search]
            except Exception:
                search_status = "unavailable"
                tool_list = []
        try:
            response = await _call_with_tools(tool_list or [], base_msgs)
        except Exception as exc:
            status = "failed" if allow_search else search_status
            return _placeholder_fail_soft_output(
                agent_id=agent_id,
                exc=exc,
                search_status=status,
                default_allow_search=default_allow_search,
            )
        first_parsed = _parse_agent_output(get_message_text(response))
        if first_parsed.get("parse_ok", True):
            return _annotate_placeholder_output(
                first_parsed,
                agent_id=agent_id,
                default_allow_search=default_allow_search,
                search_status=search_status,
            )

        # Retry once with a strict JSON-only prompt.
        retry_prompt = (
            "只返回合法 JSON 对象，禁止解释或多余文字，键必须是 "
            '{"analysis","key_points","evidence","confidence"}，值保持原语种内容。'
        )
        retry_msgs = [
            {"role": "system", "content": retry_prompt},
            {"role": "user", "content": user_content},
        ]
        try:
            retry_resp = await _call_with_tools(tool_list or [], retry_msgs)
        except Exception as exc:
            status = "failed" if allow_search else search_status
            return _placeholder_fail_soft_output(
                agent_id=agent_id,
                exc=exc,
                search_status=status,
                default_allow_search=default_allow_search,
            )
        retry_parsed = _parse_agent_output(get_message_text(retry_resp))
        return _annotate_placeholder_output(
            retry_parsed,
            agent_id=agent_id,
            default_allow_search=default_allow_search,
            search_status=search_status,
        )

    object.__setattr__(
        _agent_tool,
        "is_llm_search_placeholder",
        _is_placeholder_agent(agent_id, default_allow_search),
    )
    if _is_placeholder_agent(agent_id, default_allow_search):
        object.__setattr__(_agent_tool, "runtime_path", "INTERNAL_LLM_SEARCH_PLACEHOLDER")
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
