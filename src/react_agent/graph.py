# ruff: noqa: D103
"""Fixed-DAG reset runtime graph.

Phase R3 replaces the previous mode-based Router/Manager/Fusion runtime with one
plan-driven deterministic skeleton DAG. The skeleton does not call a provider,
search, or any external agent endpoint; it only exercises the reset protocol and
execution seams.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    build_data_bundle,
    build_default_dimension_route_intent,
    build_default_fixed_dag_plan,
    build_emitted_bundle,
    build_entity_relation_bundle,
    build_final_emit_payload,
    build_reset_multi_agent_bundle,
    build_workflow_snapshot_v2,
    compile_selected_fixed_dag_plan,
)
from react_agent.fixed_dag_executor import execute_fixed_dag_plan
from react_agent.graph_entry import compile_graph_variants, select_graph_for_invoke
from react_agent.router_parse import parse_dimension_route_intent_json
from react_agent.router_provider import (
    ROUTER_PROVIDER_DIMENSIONS,
    ROUTER_PROVIDER_JSON_RESPONSE_FORMAT,
    RouterProviderInvocationOptions,
    RouterProviderPolicy,
    build_openai_compatible_chat_completions_url,
    build_router_provider_request_contract,
    normalize_router_provider_model_for_openai_compatible_api,
    router_provider_preflight,
)
from react_agent.state import InputState, State

_GRAPH_NAME = "Fixed DAG Reset Skeleton"
_ROUTER_TEXT_DIMENSION_RE = re.compile(r"\b(value|market|risk|macro)\b", re.IGNORECASE)
_ROUTER_TEXT_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_ROUTER_TEXT_JSONISH_RE = re.compile(r"[{}]")
_ROUTER_TEXT_URL_RE = re.compile(r"https?://", re.IGNORECASE)
_ROUTER_TEXT_DIMENSION_CUES: dict[str, tuple[str, ...]] = {
    "value": ("value", "valuation", "估值", "价值", "基本面", "财务"),
    "market": ("market", "technical", "trading", "flow", "sentiment", "市场", "交易", "技术", "资金", "情绪"),
    "risk": ("risk", "downside", "compliance", "fraud", "crash", "风险", "下行", "合规", "欺诈", "暴跌"),
    "macro": ("macro", "policy", "rate", "industry", "index", "宏观", "政策", "利率", "行业", "指数"),
}
_ROUTER_TEXT_NEGATION_MARKERS = (
    "unselected",
    "not selected",
    "not requested",
    "excluded",
    "exclude",
    "without",
    "no need",
    "不要",
    "不需要",
    "无需",
    "未选择",
    "未覆盖",
    "不包括",
    "排除",
)
_ROUTER_TEXT_FORBIDDEN_MARKERS = (
    "agent_id",
    "selected_agents",
    "endpoint",
    "api_key",
    "authorization",
    "bearer",
    "secret",
    "password",
    "raw_response",
    "raw_provider_response",
    "provider_payload",
    "sql",
    "prompt",
    "traceback",
    "chain-of-thought",
    "chain_of_thought",
)


@dataclass(frozen=True)
class _RouterProviderOutput:
    content: str | None
    invoked: bool
    error_code: str = ""
    attempt_count: int = 0
    elapsed_ms: int | None = None
    output_shape: str = ""
    retry_mode: str = ""
    parse_stage: str = ""


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


def _llm_dimension_router_mode(context: Context | None) -> str:
    raw = str(getattr(context, "llm_dimension_router_mode", "") or "").strip().lower()
    return "real" if raw == "real" else "fake"


def _provider_router_provenance(
    *,
    enabled: bool,
    mode: str = "fake",
    invoked: bool = False,
    parse_ok: bool = False,
    fallback_reason: str = "",
    selected_dimensions: list[str] | None = None,
    error_code: str = "",
    attempt_count: int | None = None,
    elapsed_ms: int | None = None,
    output_shape: str = "",
    retry_mode: str = "",
    parse_stage: str = "",
) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "provider_router_enabled": enabled,
        "provider_router_invoked": invoked,
        "provider_router_mode": mode if enabled else "",
        "provider_router_parse_ok": parse_ok,
        "provider_router_fallback_reason": fallback_reason,
        "provider_router_selected_dimensions": list(selected_dimensions or []),
        "provider_router_error_code": error_code,
    }
    if attempt_count is not None:
        provenance["provider_router_attempt_count"] = max(0, int(attempt_count))
    if elapsed_ms is not None:
        provenance["provider_router_elapsed_ms"] = max(0, int(elapsed_ms))
    if error_code:
        provenance["provider_router_last_error_code"] = error_code
    if output_shape:
        provenance["provider_router_output_shape"] = _safe_router_telemetry_code(
            output_shape,
            limit=60,
        )
    if retry_mode:
        provenance["provider_router_retry_mode"] = _safe_router_telemetry_code(
            retry_mode,
            limit=60,
        )
    if parse_stage:
        provenance["provider_router_parse_stage"] = _safe_router_telemetry_code(
            parse_stage,
            limit=60,
        )
    return provenance


def _safe_router_telemetry_code(value: Any, *, limit: int = 80) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return re.sub(r"[^a-zA-Z0-9_.:-]+", "_", text)[:limit]


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
) -> str | _RouterProviderOutput | None:
    """Invoke the explicitly enabled router provider without retaining raw output."""
    if _llm_dimension_router_mode(context) != "real":
        return None
    if context is None:
        return None

    options = RouterProviderInvocationOptions(timeout_seconds=8.0, retry_count=1, call_cap=2)
    preflight = router_provider_preflight(
        RouterProviderPolicy(
            real_provider_authorized=True,
            env_value_access_authorized=True,
            provider_call_authorized=True,
            options=options,
        ),
        selected_routing_enabled=bool(getattr(context, "enable_selected_routing", False)),
        llm_dimension_router_enabled=bool(
            getattr(context, "enable_llm_dimension_router", False)
        ),
    )
    if not preflight.ready:
        return None

    model_name = _router_config_value(
        context,
        "router_model",
        ("ROUTER_MODEL", "MODEL"),
    ) or str(getattr(context, "model", "") or "")
    api_key = _router_config_value(
        context,
        "router_openai_api_key",
        ("ROUTER_OPENAI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"),
    )
    base_url = _router_config_value(
        context,
        "router_openai_base_url",
        ("ROUTER_OPENAI_BASE_URL", "DEEPSEEK_BASE_URL", "OPENAI_BASE_URL"),
    )
    if not base_url and str(model_name).startswith("deepseek/"):
        base_url = "https://api.deepseek.com"
    if not model_name or not api_key or not base_url:
        return None

    normalized_model = normalize_router_provider_model_for_openai_compatible_api(
        model_name
    )
    endpoint = build_openai_compatible_chat_completions_url(base_url)
    if not endpoint.valid or not normalized_model.provider_api_model:
        return None

    body = {
        "model": normalized_model.provider_api_model,
        "messages": _build_live_dimension_router_messages(question),
        "temperature": 0,
        "max_tokens": int(options.max_tokens),
        "response_format": dict(ROUTER_PROVIDER_JSON_RESPONSE_FORMAT),
    }
    timeout_seconds = float(options.timeout_seconds)
    timeout = httpx.Timeout(
        timeout_seconds,
        connect=min(5.0, timeout_seconds),
        read=timeout_seconds,
        write=min(5.0, timeout_seconds),
        pool=min(5.0, timeout_seconds),
    )
    attempts = max(1, min(int(options.call_cap), int(options.retry_count) + 1))
    retry_mode = "json_then_dimension_text" if attempts > 1 else "json_only"
    last_error_code = "router_provider_missing_output"
    last_output_shape = "not_called"
    started = time.monotonic()

    def finish(
        *,
        content: str | None = None,
        invoked: bool = True,
        error_code: str = "",
        attempt_count: int = 0,
        output_shape: str = "",
        parse_stage: str = "",
    ) -> _RouterProviderOutput:
        return _RouterProviderOutput(
            content=content,
            invoked=invoked,
            error_code=error_code,
            attempt_count=attempt_count,
            elapsed_ms=max(0, int(round((time.monotonic() - started) * 1000))),
            output_shape=output_shape or last_output_shape,
            retry_mode=retry_mode,
            parse_stage=parse_stage,
        )

    try:
        client_cm = httpx.Client(timeout=timeout)
    except Exception:
        return finish(
            content=None,
            invoked=False,
            error_code="router_provider_client_init_failed",
            attempt_count=0,
            output_shape="client_init_failed",
        )
    with client_cm as client:
        for attempt in range(attempts):
            attempt_count = attempt + 1
            request_body = dict(body)
            if attempt > 0:
                request_body.pop("response_format", None)
                request_body["messages"] = _build_live_dimension_router_text_messages(
                    question
                )
            try:
                response = client.post(
                    endpoint.chat_completions_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
            except (TimeoutError, httpx.TimeoutException):
                last_error_code = "router_provider_timeout"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="timeout",
                )
            except httpx.ConnectError:
                last_error_code = "router_provider_connect_error"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="transport_error",
                )
            except httpx.RemoteProtocolError:
                last_error_code = "router_provider_protocol_error"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="protocol_error",
                )
            except httpx.RequestError:
                last_error_code = "router_provider_transport_error"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="transport_error",
                )
            if response.status_code < 200 or response.status_code >= 300:
                last_error_code = "router_provider_http_status"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="http_status_non_2xx",
                )
            try:
                payload = response.json()
            except ValueError:
                last_error_code = "router_provider_invalid_response_json"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="invalid_response_json",
                )
            choices = payload.get("choices") if isinstance(payload, dict) else None
            if not isinstance(choices, list) or not choices:
                last_error_code = "router_provider_no_choices"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="no_choices",
                )
            first = choices[0]
            if not isinstance(first, Mapping):
                last_error_code = "router_provider_invalid_choice"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="invalid_choice",
                )
            message = first.get("message")
            if not isinstance(message, Mapping):
                last_error_code = "router_provider_missing_message"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="missing_message",
                )
            content = _extract_router_message_content(message.get("content"))
            if content:
                last_output_shape = _classify_router_output_shape(content)
                if _router_provider_output_has_parseable_shape(content):
                    return finish(
                        content=content,
                        invoked=True,
                        error_code="",
                        attempt_count=attempt_count,
                        output_shape=last_output_shape,
                        parse_stage="provider_output_parseable",
                    )
                last_error_code = "router_provider_unparseable_content"
                if attempt + 1 < attempts:
                    continue
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape=last_output_shape,
                )
            last_error_code = _classify_router_missing_content(first, message)
            if attempt + 1 >= attempts:
                return finish(
                    content=None,
                    invoked=True,
                    error_code=last_error_code,
                    attempt_count=attempt_count,
                    output_shape="missing_content",
                )
    return finish(
        content=None,
        invoked=True,
        error_code=last_error_code,
        attempt_count=attempts,
        output_shape=last_output_shape,
    )


def _extract_router_message_content(content: Any) -> str | None:
    if isinstance(content, str):
        text = content.strip()
        return text or None
    if not isinstance(content, list):
        return None
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            if item.strip():
                parts.append(item.strip())
            continue
        if not isinstance(item, Mapping):
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
            continue
        nested = item.get("content")
        if isinstance(nested, str) and nested.strip():
            parts.append(nested.strip())
    joined = "\n".join(parts).strip()
    return joined or None


def _router_provider_output_has_parseable_shape(content: str) -> bool:
    text = str(content or "").strip()
    if not text:
        return False
    if "{" in text and "}" in text:
        match = _ROUTER_TEXT_JSON_BLOCK_RE.search(text)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return _route_intent_json_from_malformed_dimension_text(text) is not None
            return isinstance(parsed, Mapping)
    return _route_intent_json_from_plain_dimension_text(text) is not None


def _classify_router_output_shape(content: str) -> str:
    text = str(content or "").strip()
    if not text:
        return "empty"
    if "{" in text and "}" in text:
        match = _ROUTER_TEXT_JSON_BLOCK_RE.search(text)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return (
                    "malformed_dimension_text"
                    if _route_intent_json_from_malformed_dimension_text(text) is not None
                    else "malformed_json"
                )
            return "json_object" if isinstance(parsed, Mapping) else "json_non_object"
    if _route_intent_json_from_plain_dimension_text(text) is not None:
        return "plain_dimension_text"
    return "unparseable_text"


def _classify_router_missing_content(
    choice: Mapping[str, Any],
    message: Mapping[str, Any],
) -> str:
    finish_reason = str(choice.get("finish_reason") or "").strip().lower()
    if finish_reason == "length":
        return "router_provider_finish_length_no_content"
    if isinstance(message.get("refusal"), str) and str(message.get("refusal") or "").strip():
        return "router_provider_refusal"
    if "content" not in message:
        return "router_provider_missing_content"
    content = message.get("content")
    if isinstance(content, str) and not content.strip():
        return "router_provider_empty_content"
    if isinstance(content, list):
        return "router_provider_empty_content_parts"
    return "router_provider_unsupported_content_type"


def _collect_dimension_mentions_from_text(raw_output: str) -> list[str]:
    found: set[str] = set()
    text = str(raw_output or "").strip()
    for line in [line.strip() for line in text.splitlines() if line.strip()] or [text]:
        # Process semicolon-delimited include/exclude fragments independently so
        # provider text such as `include: value/risk; exclude: market` can be
        # repaired without accidentally selecting excluded dimensions.
        for segment in re.split(r"[;\n]+", line):
            segment_lower = segment.strip().lower()
            if not segment_lower:
                continue
            if any(marker in segment_lower for marker in _ROUTER_TEXT_NEGATION_MARKERS):
                continue
            found.update(
                match.group(1).lower()
                for match in _ROUTER_TEXT_DIMENSION_RE.finditer(segment)
            )
            for dimension, cues in _ROUTER_TEXT_DIMENSION_CUES.items():
                if any(cue.lower() in segment_lower for cue in cues):
                    found.add(dimension)
    return [dimension for dimension in ROUTER_PROVIDER_DIMENSIONS if dimension in found]


def _route_intent_json_from_dimension_mentions(raw_output: str) -> str | None:
    selected_dimensions = _collect_dimension_mentions_from_text(raw_output)
    if not selected_dimensions:
        return None
    payload = {
        "schema": "route_intent_v1",
        "schema_version": "route_intent_v1",
        "task_type": "general",
        "targets": [],
        "selected_dimensions": selected_dimensions,
        "route_confidence": 0.72,
        "needs_clarification": False,
        "clarification_question": "",
        "fallback_reason": "",
        "provenance": {
            "source": "live_llm_dimension_router_text_repair",
            "route_granularity": "dimension",
            "dimension_only": True,
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _route_intent_json_from_plain_dimension_text(raw_output: str) -> str | None:
    text = str(raw_output or "").strip()
    if not text or len(text) > 600:
        return None
    lowered = text.lower()
    if any(marker in lowered for marker in _ROUTER_TEXT_FORBIDDEN_MARKERS):
        return None
    if _ROUTER_TEXT_URL_RE.search(text) or _ROUTER_TEXT_JSONISH_RE.search(text):
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 8:
        return None
    return _route_intent_json_from_dimension_mentions(text)


def _route_intent_json_from_malformed_dimension_text(raw_output: str) -> str | None:
    text = str(raw_output or "").strip()
    if not text or len(text) > 1200:
        return None
    lowered = text.lower()
    if any(marker in lowered for marker in _ROUTER_TEXT_FORBIDDEN_MARKERS):
        return None
    if _ROUTER_TEXT_URL_RE.search(text):
        return None
    # Avoid repairing schemas that include non-dimension control surfaces or
    # merely list the allowed vocabulary instead of the selected dimensions.
    if any(
        marker in lowered
        for marker in (
            "selected_agents",
            "target_agent",
            "agent_id",
            "allowed_dimensions",
            "all_dimensions",
        )
    ):
        return None
    if not any(
        marker in lowered
        for marker in (
            "selected_dimensions",
            "dimensions",
            "selected",
            "include",
            "选择维度",
            "维度",
        )
    ):
        return None
    return _route_intent_json_from_dimension_mentions(text)


def _router_config_value(
    context: Context,
    attr_name: str,
    env_names: tuple[str, ...],
) -> str:
    direct = str(getattr(context, attr_name, "") or "").strip()
    if direct:
        return direct
    for env_name in env_names:
        value = str(os.environ.get(env_name, "") or "").strip()
        if value:
            return value
    return ""


def _build_live_dimension_router_messages(question: str) -> list[dict[str, str]]:
    contract = build_router_provider_request_contract()
    allowed = ", ".join(contract["allowed_dimensions"])
    user_question = str(question or "").strip() or "not provided"
    system = (
        "You are a strict fixed-DAG dimension router. Return only one JSON object. "
        "The first non-whitespace character should be { and the last non-whitespace "
        "character should be }. Do not include markdown, prose, selected agent ids, "
        "endpoints, prompts, secrets, SQL, or provider payloads."
    )
    user = (
        "Classify the user request into fixed-DAG dimensions. "
        f"Allowed dimensions: {allowed}. "
        "Use value for valuation/fundamental/financial questions, market for "
        "technical/trading/flow/sentiment questions, risk for downside/compliance/"
        "fraud/crash questions, and macro for macro/policy/rate/index/industry questions. "
        "For valuation plus downside risk, select exactly value and risk. "
        "For 估值 plus 下行风险, select exactly value and risk. "
        "If the request says not to analyze market trading, do not select market. "
        "Select only directly requested dimensions. If unclear, choose the minimal "
        "safe set and keep needs_clarification false unless the request is impossible. "
        "Return JSON with exactly these public fields: schema, schema_version, task_type, "
        "targets, selected_dimensions, route_confidence, needs_clarification, "
        "clarification_question, fallback_reason, provenance. "
        "Do not include selected_agents or any extra control fields. "
        "Use schema and schema_version route_intent_v1, task_type general, "
        "route_confidence between 0.70 and 1.0, fallback_reason as an empty string, "
        "and provenance.source live_llm_dimension_router. "
        "Examples: "
        '"Analyze valuation and downside risk for 600519.SH." -> '
        '"selected_dimensions":["value","risk"]. '
        '"分析 600519.SH 的估值和下行风险，不要分析市场交易面。" -> '
        '"selected_dimensions":["value","risk"]. '
        '"分析 000001.SZ 的短期市场交易面、资金和技术趋势。" -> '
        '"selected_dimensions":["market"]. '
        '"分析 CSI300 指数当前受宏观环境影响的主要方向。" -> '
        '"selected_dimensions":["macro"]. '
        "The JSON shape is: "
        '{"schema":"route_intent_v1","schema_version":"route_intent_v1",'
        '"task_type":"general","targets":["..."],'
        '"selected_dimensions":["value"],"route_confidence":0.95,'
        '"needs_clarification":false,"clarification_question":"",'
        '"fallback_reason":"","provenance":{"source":"live_llm_dimension_router",'
        '"route_granularity":"dimension","dimension_only":true}}. '
        f"User request: {user_question}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _build_live_dimension_router_text_messages(question: str) -> list[dict[str, str]]:
    allowed = ", ".join(ROUTER_PROVIDER_DIMENSIONS)
    user_question = str(question or "").strip() or "not provided"
    system = (
        "You are a strict fixed-DAG dimension router. Return only lower-case "
        "dimension ids from the allowed set, separated by commas. Do not return "
        "JSON, markdown, prose, explanations, endpoints, prompts, SQL, secrets, "
        "provider payloads, or agent ids."
    )
    user = (
        f"Allowed dimensions: {allowed}. "
        "Use value for valuation/fundamental/financial questions, market for "
        "technical/trading/flow/sentiment questions, risk for downside/compliance/"
        "fraud/crash questions, and macro for macro/policy/rate/index/industry questions. "
        "valuation + downside risk => value,risk. 估值 + 下行风险 => value,risk. "
        "If market/trading is explicitly excluded, do not include market. "
        "Select only directly requested dimensions and obey explicit exclusions. "
        "Return examples: value,risk or market or macro or value,market,risk. "
        "Never return selected_agents, JSON, labels, or explanation text. "
        f"User request: {user_question}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _route_intent_from_llm_dimension_provider(
    question: str,
    context: Context | None,
) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    mode = _llm_dimension_router_mode(context)
    meta = _provider_router_provenance(enabled=True, mode=mode)
    try:
        provider_output = _invoke_dimension_router_provider(question, context)
    except (TimeoutError, httpx.TimeoutException):
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

    output_error_code = "router_provider_missing_output"
    output_attempt_count: int | None = None
    output_elapsed_ms: int | None = None
    output_shape = ""
    output_retry_mode = ""
    output_parse_stage = ""
    output_invoked = False
    raw_output: str | None
    if isinstance(provider_output, _RouterProviderOutput):
        raw_output = provider_output.content
        output_error_code = (
            provider_output.error_code.strip()
            if isinstance(provider_output.error_code, str)
            else ""
        ) or output_error_code
        output_invoked = provider_output.invoked
        output_attempt_count = provider_output.attempt_count
        output_elapsed_ms = provider_output.elapsed_ms
        output_shape = provider_output.output_shape
        output_retry_mode = provider_output.retry_mode
        output_parse_stage = provider_output.parse_stage
    elif isinstance(provider_output, str):
        raw_output = provider_output
        output_invoked = True
    else:
        raw_output = None

    if not isinstance(raw_output, str) or not raw_output.strip():
        reason = output_error_code if output_invoked else "router_provider_unavailable"
        return None, {
            **meta,
            "provider_router_invoked": output_invoked,
            "provider_router_fallback_reason": reason,
            "provider_router_error_code": reason,
            "provider_router_last_error_code": reason,
            "provider_router_attempt_count": output_attempt_count or 0,
            "provider_router_elapsed_ms": output_elapsed_ms,
            "provider_router_output_shape": output_shape or "missing_output",
            "provider_router_retry_mode": output_retry_mode,
            "provider_router_parse_stage": output_parse_stage or "provider_unavailable",
        }
    route_intent, stats = parse_dimension_route_intent_json(
        raw_output,
        question=question,
    )
    parse_stage = "json_parse"
    if bool(stats.get("used_fallback")) and (
        stats.get("fallback_reason") == "missing_json"
        or str(stats.get("fallback_reason") or "").startswith("json_decode_error:")
    ):
        repaired_output = _route_intent_json_from_plain_dimension_text(raw_output)
        if repaired_output is not None:
            parse_stage = "plain_text_repair"
        else:
            repaired_output = _route_intent_json_from_malformed_dimension_text(raw_output)
            if repaired_output is not None:
                parse_stage = "malformed_text_repair"
        if repaired_output is not None:
            route_intent, stats = parse_dimension_route_intent_json(
                repaired_output,
                question=question,
            )
    if bool(stats.get("used_fallback")):
        parse_stage = "parse_failed"
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
            "provider_router_last_error_code": output_error_code or fallback_reason,
            "provider_router_attempt_count": output_attempt_count or 0,
            "provider_router_elapsed_ms": output_elapsed_ms,
            "provider_router_output_shape": output_shape,
            "provider_router_retry_mode": output_retry_mode,
            "provider_router_parse_stage": parse_stage,
        }
    route_intent = dict(route_intent)
    route_intent["provenance"] = {
        "source": f"{mode}_llm_dimension_router",
        "normalizer": f"{mode}_provider_dimension_router",
        "route_granularity": "dimension",
        "dimension_only": True,
        # `route_intent_v1` itself remains a pure planning contract. The outer
        # fixed-DAG plan/workflow provenance records real router invocation.
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
        "provider_router_attempt_count": output_attempt_count or 0,
        "provider_router_elapsed_ms": output_elapsed_ms,
        "provider_router_output_shape": output_shape,
        "provider_router_retry_mode": output_retry_mode,
        "provider_router_parse_stage": parse_stage,
        "provider_router_last_error_code": output_error_code,
    }


def _full_plan_with_selected_fallback_provenance(
    question: str,
    reason: str,
    *,
    as_of: str | None = None,
    provider_router: dict[str, Any] | None = None,
    route_planner_ms: int | None = None,
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
    if route_planner_ms is not None:
        plan["provenance"]["route_planner_ms"] = max(0, int(route_planner_ms))
    return plan


def _route_plan_for_context(question: str, context: Context | None) -> dict[str, Any]:
    route_started = time.monotonic()
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
        enabled=_is_llm_dimension_router_enabled(context),
        mode=_llm_dimension_router_mode(context),
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
                    route_planner_ms=max(
                        0,
                        int(round((time.monotonic() - route_started) * 1000)),
                    ),
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
            route_planner_ms=max(
                0,
                int(round((time.monotonic() - route_started) * 1000)),
            ),
        )
    plan["provenance"] = {
        **plan["provenance"],
        "selected_routing_requested": True,
        "selected_routing_fallback": False,
        "route_granularity": "dimension",
        "selected_dimensions": list(plan.get("selected_dimensions", []) or []),
        "expanded_agent_count": len(plan.get("target_agent_ids", []) or []),
        "route_planner_ms": max(0, int(round((time.monotonic() - route_started) * 1000))),
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


def run_l2_conclusions_node(
    state: State,
    runtime: Runtime[Context] | None = None,
) -> dict[str, Any]:
    from react_agent.fixed_dag.execution.runner import run_fixed_dag_l2_phase

    plan = state["fixed_dag_plan"]
    question = str(state.get("current_question", "") or "")
    as_of = str(plan.get("as_of") or "not_available")
    context = runtime.context if runtime is not None else None

    result = run_fixed_dag_l2_phase(plan, question=question, as_of=as_of, context=context)
    execution_plan = result.pop("_execution_plan", plan)
    result["_execution_plan"] = execution_plan
    result["fixed_dag_plan"] = execution_plan

    completed: list[str] = []
    for s in execution_plan.get("dag_steps", []):
        sid = str(s.get("id") or "")
        if s.get("stage") in ("planning", "evidence", "l2_analysis"):
            completed.append(sid)
    result["workflow_snapshot"] = build_workflow_snapshot_v2(
        plan=execution_plan,
        current_stage="l2_analysis",
        completed_steps=completed,
        step_results=result.get("_step_results") or result.get("dag_step_results"),
    )
    result["thread_summary"] = "L2 analysis completed with external compute overlay."
    return result


def run_dimension_composites_node(
    state: State,
    runtime: Runtime[Context] | None = None,
) -> dict[str, Any]:
    from react_agent.fixed_dag.execution.runner import run_fixed_dag_l3_phase

    plan = state.get("_execution_plan") or state.get("fixed_dag_plan", {})
    l2_conclusions = state.get("l2_conclusions", {})
    step_results = state.get("_step_results") or state.get("dag_step_results") or {}
    context = runtime.context if runtime is not None else None

    result = run_fixed_dag_l3_phase(plan, l2_conclusions, context=context, as_of=str(plan.get("as_of") or ""), step_results=step_results)

    completed: list[str] = []
    for s in plan.get("dag_steps", []):
        sid = str(s.get("id") or "")
        if s.get("stage") in ("planning", "evidence", "l2_analysis", "dimension_composite"):
            completed.append(sid)
    result["workflow_snapshot"] = build_workflow_snapshot_v2(
        plan=plan,
        current_stage="dimension_composite",
        completed_steps=completed,
        dimension_results=result.get("dimension_results", {}),
        step_results=result.get("_step_results") or step_results,
    )
    result["thread_summary"] = "L3 dimension composites completed."
    return result


def decision_synthesizer_node(
    state: State,
    runtime: Runtime[Context] | None = None,
) -> dict[str, Any]:
    from react_agent.fixed_dag.execution.runner import run_fixed_dag_l4_phase

    plan = state.get("_execution_plan") or state.get("fixed_dag_plan", {})
    l2_conclusions = state.get("l2_conclusions", {})
    dimension_results = state.get("dimension_results", {})
    step_results = state.get("_step_results") or state.get("dag_step_results") or {}
    question = str(state.get("current_question", "") or "")
    context = runtime.context if runtime is not None else None

    result = run_fixed_dag_l4_phase(
        plan, l2_conclusions, dimension_results,
        context=context, question=question, as_of=str(plan.get("as_of") or ""),
        step_results=step_results,
    )

    completed: list[str] = []
    for s in plan.get("dag_steps", []):
        sid = str(s.get("id") or "")
        if s.get("stage") in ("planning", "evidence", "l2_analysis", "dimension_composite", "decision", "report"):
            completed.append(sid)
    result["workflow_snapshot"] = build_workflow_snapshot_v2(
        plan=plan,
        current_stage="report",
        completed_steps=completed,
        dimension_results=result.get("dimension_results", {}),
        report_result=result.get("report_result", {}),
        step_results=result.get("_step_results") or step_results,
    )
    result["thread_summary"] = "L4 decision and report completed."
    return result


def report_generator_node(state: State) -> dict[str, Any]:
    """No-op: L4 phase is handled by decision_synthesizer_node in the split graph."""
    del state
    return {"thread_summary": "Report already generated by decision_synthesizer."}


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
builder.add_node("execute_fixed_dag", execute_fixed_dag_node)  # compat: legacy full-exec node
builder.add_node("run_l2_conclusions", run_l2_conclusions_node)
builder.add_node("run_dimension_composites", run_dimension_composites_node)
builder.add_node("decision_synthesizer", decision_synthesizer_node)
builder.add_node("report_generator", report_generator_node)
builder.add_node("final_emit", final_emit_node)
builder.add_node("memory_update", memory_update_node)

builder.add_edge(START, "route_planner")
builder.add_edge("route_planner", "prepare_l1_context")
builder.add_edge("prepare_l1_context", "run_l2_conclusions")
builder.add_edge("run_l2_conclusions", "run_dimension_composites")
builder.add_edge("run_dimension_composites", "decision_synthesizer")
builder.add_edge("decision_synthesizer", "final_emit")
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
