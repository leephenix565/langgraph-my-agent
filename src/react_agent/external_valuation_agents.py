"""HTTP wrappers for the external valuation agents used by Agent Catalog v2."""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Mapping
from typing import Any, Dict, List

import httpx
from langchain_core.tools import BaseTool, tool

from react_agent.agents import AgentOutput


EXTERNAL_VALUATION_AGENT_CONFIG: Dict[str, Dict[str, str]] = {
    "a16_ml_valuation": {
        "external_agent_id": "valuation_ml",
        "env_var": "VALUATION_ML_AGENT_URL",
        "default_url": "http://127.0.0.1:8102/v1/agent/invoke",
    },
    "a17_traditional_valuation": {
        "external_agent_id": "valuation_traditional",
        "env_var": "VALUATION_TRADITIONAL_AGENT_URL",
        "default_url": "http://127.0.0.1:8101/v1/agent/invoke",
    },
    "a18_meta_valuation": {
        "external_agent_id": "valuation_meta",
        "env_var": "VALUATION_META_AGENT_URL",
        "default_url": "http://127.0.0.1:8103/v1/agent/invoke",
    },
}

SUCCESS_STATUSES = {"ok", "partial", "needs_clarification"}
ERROR_ANALYSIS = "外部估值服务不可用或返回错误，已跳过该外部结果。"


def external_valuation_agent_ids() -> set[str]:
    """Return the main-system ids that must stay bound to HTTP wrappers."""
    return set(EXTERNAL_VALUATION_AGENT_CONFIG)


def _timeout_seconds() -> float:
    raw = os.environ.get("EXTERNAL_AGENT_TIMEOUT_SECONDS", "90")
    try:
        timeout = float(raw)
    except (TypeError, ValueError):
        return 90.0
    return timeout if timeout > 0 else 90.0


def _endpoint_for(agent_id: str) -> str:
    config = EXTERNAL_VALUATION_AGENT_CONFIG[agent_id]
    return os.environ.get(config["env_var"], config["default_url"])


def _truncate(value: Any, *, limit: int = 500) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _safe_context(
    *,
    agent_id: str,
    external_agent_id: str,
    subtask: str,
    shared_context: Mapping[str, Any],
    router_plan_summary: str | None,
) -> Dict[str, Any]:
    """Build a compact context payload without raw graph state or messages."""
    safe_keys = [
        "layer_plan",
        "layer_mode",
        "current_layer",
        "thread_summary",
        "stable_findings",
    ]
    context_summary: Dict[str, Any] = {}
    for key in safe_keys:
        if key in shared_context:
            context_summary[key] = _truncate(shared_context.get(key), limit=800)
    return {
        "main_agent_id": agent_id,
        "external_agent_id": external_agent_id,
        "subtask": _truncate(subtask, limit=800),
        "shared_context_summary": context_summary,
        "router_plan_summary": _truncate(router_plan_summary, limit=1200),
    }


def build_external_agent_request(
    *,
    agent_id: str,
    question: str,
    subtask: str,
    shared_context: Mapping[str, Any] | None = None,
    router_plan_summary: str | None = None,
) -> Dict[str, Any]:
    """Build the request accepted by the local valuation FastAPI services."""
    config = EXTERNAL_VALUATION_AGENT_CONFIG[agent_id]
    external_agent_id = config["external_agent_id"]
    language = "zh" if any("\u4e00" <= ch <= "\u9fff" for ch in question) else "en"
    timeout = _timeout_seconds()
    return {
        "schema_version": "external_agent_request_v0",
        "request_id": f"{agent_id}-{uuid.uuid4().hex}",
        "question": question,
        "language": language,
        "context": _safe_context(
            agent_id=agent_id,
            external_agent_id=external_agent_id,
            subtask=subtask,
            shared_context=shared_context or {},
            router_plan_summary=router_plan_summary,
        ),
        "options": {
            "timeout_seconds": timeout,
            "external_agent_id": external_agent_id,
        },
    }


def _string_items(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        items: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                items.append(item.strip())
            elif isinstance(item, Mapping):
                label = item.get("title") or item.get("name") or item.get("source") or "item"
                detail = item.get("detail") or item.get("url") or item.get("metric") or item
                items.append(_truncate(f"{label}: {detail}", limit=220))
        return items
    if isinstance(value, Mapping):
        return [_truncate(value, limit=220)]
    return [_truncate(value, limit=220)]


def _extract_confidence(payload: Mapping[str, Any], status: str) -> float:
    candidates = [
        payload.get("confidence"),
        (payload.get("tool_result") or {}).get("confidence")
        if isinstance(payload.get("tool_result"), Mapping)
        else None,
        (payload.get("tool_result") or {}).get("score")
        if isinstance(payload.get("tool_result"), Mapping)
        else None,
    ]
    tool_result = payload.get("tool_result")
    if isinstance(tool_result, Mapping):
        valuation_result = tool_result.get("valuation_result")
        if isinstance(valuation_result, Mapping):
            candidates.append(valuation_result.get("confidence"))
    for candidate in candidates:
        try:
            confidence = float(candidate)
        except (TypeError, ValueError):
            continue
        return max(0.0, min(1.0, confidence))
    if status == "ok":
        return 0.6
    if status in {"partial", "needs_clarification"}:
        return 0.4
    return 0.0


def _summarize_tool_result(tool_result: Any) -> List[str]:
    if not isinstance(tool_result, Mapping):
        return []
    points: List[str] = []
    for key in [
        "valuation_result",
        "valuation_results",
        "target_price",
        "intrinsic_value",
        "valuation_range",
        "scenario_results",
        "method",
        "model",
    ]:
        if key in tool_result and len(points) < 5:
            points.append(_truncate(f"{key}: {tool_result[key]}", limit=240))
    return points


def _extract_evidence(payload: Mapping[str, Any]) -> List[str]:
    evidence: List[str] = []
    tool_result = payload.get("tool_result")
    if isinstance(tool_result, Mapping):
        for key in [
            "evidence",
            "data_sources",
            "data_source",
            "source",
            "method_details",
            "valuation_result",
            "valuation_results",
        ]:
            for item in _string_items(tool_result.get(key)):
                if len(evidence) < 8:
                    evidence.append(item)
        warnings = tool_result.get("warnings")
        for item in _string_items(warnings):
            if len(evidence) < 8:
                evidence.append(f"warning: {item}")
    for item in _string_items(payload.get("warnings")):
        if len(evidence) < 8:
            evidence.append(f"warning: {item}")
    return evidence


def map_external_response_to_agent_output(payload: Mapping[str, Any]) -> AgentOutput:
    """Map an external valuation response into the runtime AgentOutput surface."""
    status = str(payload.get("status") or "").strip().lower()
    if not status:
        return _fail_soft_output("missing_status")
    parse_ok = status in SUCCESS_STATUSES
    analysis = str(payload.get("answer") or payload.get("native_answer") or "").strip()
    if not analysis:
        analysis = ERROR_ANALYSIS if not parse_ok else "外部估值服务未返回可展示答案。"
    tool_points = _summarize_tool_result(payload.get("tool_result"))
    key_points = tool_points[:5]
    if not key_points and parse_ok:
        key_points = [_truncate(analysis, limit=220)] if analysis else []
    errors = _string_items(payload.get("errors"))
    evidence = _extract_evidence(payload)
    if errors:
        evidence.extend(f"error: {_truncate(error, limit=180)}" for error in errors[:3])
    return {
        "analysis": analysis,
        "key_points": key_points,
        "evidence": evidence[:8],
        "confidence": _extract_confidence(payload, status),
        "parse_ok": parse_ok,
    }


def _fail_soft_output(reason: str) -> AgentOutput:
    safe_reason = _truncate(reason.replace("\n", " "), limit=160)
    return {
        "analysis": ERROR_ANALYSIS,
        "key_points": [],
        "evidence": [f"external_valuation_error: {safe_reason}"] if safe_reason else [],
        "confidence": 0.0,
        "parse_ok": False,
    }


def build_external_valuation_tool(agent_id: str) -> BaseTool:
    """Build a LangChain tool that invokes one external valuation service."""
    if agent_id not in EXTERNAL_VALUATION_AGENT_CONFIG:
        raise ValueError(f"unknown external valuation agent: {agent_id}")
    config = EXTERNAL_VALUATION_AGENT_CONFIG[agent_id]
    external_agent_id = config["external_agent_id"]

    @tool(f"agent_{agent_id}")
    async def _external_valuation_agent(
        question: str,
        subtask: str,
        shared_context: Dict[str, Any] | None = None,
        history: List[Dict[str, Any]] | None = None,
        tools_config: Dict[str, Any] | None = None,
        router_plan_summary: str | None = None,
    ) -> AgentOutput:
        """Invoke the configured external valuation FastAPI service."""
        del history, tools_config
        request = build_external_agent_request(
            agent_id=agent_id,
            question=question,
            subtask=subtask,
            shared_context=shared_context or {},
            router_plan_summary=router_plan_summary,
        )
        timeout = _timeout_seconds()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(_endpoint_for(agent_id), json=request)
            if response.status_code < 200 or response.status_code >= 300:
                return _fail_soft_output(f"http_status_{response.status_code}")
            try:
                payload = response.json()
            except ValueError:
                return _fail_soft_output("invalid_json")
            if not isinstance(payload, Mapping):
                return _fail_soft_output("invalid_schema: response_root_not_object")
            returned_agent_id = str(payload.get("agent_id") or "").strip()
            output = map_external_response_to_agent_output(payload)
            if returned_agent_id and returned_agent_id != external_agent_id:
                output.setdefault("evidence", [])
                output["evidence"].append(
                    f"warning: returned_agent_id={returned_agent_id}, expected={external_agent_id}"
                )
            return output
        except (httpx.TimeoutException, asyncio.TimeoutError):
            return _fail_soft_output("timeout")
        except httpx.HTTPError as exc:
            return _fail_soft_output(f"http_error:{type(exc).__name__}")
        except Exception as exc:
            return _fail_soft_output(f"unexpected_error:{type(exc).__name__}")

    object.__setattr__(_external_valuation_agent, "is_external_valuation_wrapper", True)
    object.__setattr__(_external_valuation_agent, "external_agent_id", external_agent_id)
    object.__setattr__(_external_valuation_agent, "is_stub", False)
    return _external_valuation_agent


def register_external_valuation_agents(metadata_by_id: Mapping[str, Any]) -> Dict[str, BaseTool]:
    """Return wrapper tools for external valuation agents present in metadata."""
    wrappers: Dict[str, BaseTool] = {}
    for agent_id in EXTERNAL_VALUATION_AGENT_CONFIG:
        if agent_id in metadata_by_id:
            wrappers[agent_id] = build_external_valuation_tool(agent_id)
    return wrappers
