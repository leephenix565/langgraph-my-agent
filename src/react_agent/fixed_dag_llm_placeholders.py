"""Default-off internal LLM placeholders for fixed-DAG L2 conclusions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from react_agent.fixed_dag_contracts import (
    AGENT_DIMENSIONS,
    AGENT_TITLE_LABELS,
    CONCLUSION_OBJECT_SCHEMA_VERSION,
    L2_CONCLUSION_AGENT_IDS,
    SELECTED_FIXED_DAG_SCHEMA_VERSION,
    SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES,
    ConclusionObject,
    build_l2_conclusions,
    build_pending_conclusion,
)
from react_agent.utils import load_chat_model

INTERNAL_LLM_PLACEHOLDER_SOURCE = "internal_llm_placeholder"
MAX_PLACEHOLDER_CONFIDENCE = 0.4
_MAX_TEXT_LENGTH = 700
_MAX_LIST_ITEMS = 5
_SAFE_FALLBACK_REASON = "provider_unavailable"
_FORBIDDEN_TEXT_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "traceback",
    "endpoint",
    "raw_response",
    "chain-of-thought",
    "chain of thought",
    "http://",
    "https://",
    ".env",
    "deepseek_api_key",
    "openai_api_key",
)
_KNOWN_DEPLOYED_BUT_DEFERRED_L2_AGENT_IDS = {
    "sentiment_company_radar",
    "macro_commodity_pricing",
    "macro_sentiment",
    "macro_industry_hotspot",
    "value_research_synthesis",
    "risk_crash",
    "value_meta_valuation",
    "macro_index_valuation",
    "risk_financial_fraud",
    "value_traditional_valuation",
    "value_ml_valuation",
    "market_stock_technical",
    "risk_compliance_review",
    "macro_analysis",
    "market_ipo_investor_behavior",
    "market_capital_flow_chip",
}


def _agent_ids_for_plan(plan: Mapping[str, Any] | None) -> list[str]:
    selected_l2_agent_ids = set(L2_CONCLUSION_AGENT_IDS)
    if isinstance(plan, Mapping) and plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION:
        selected_l2_agent_ids = {
            str(agent_id)
            for agent_id in plan.get("target_agent_ids", [])
            if str(agent_id) in L2_CONCLUSION_AGENT_IDS
        }
    return [agent_id for agent_id in L2_CONCLUSION_AGENT_IDS if agent_id in selected_l2_agent_ids]


def _safe_reason(exc: Exception) -> str:
    if isinstance(exc, ImportError):
        return "provider_dependency_missing"
    text = str(exc).lower()
    if "api key" in text or "api_key" in text or ("key" in text and type(exc).__name__ == "ValueError"):
        return "provider_configuration_missing"
    if isinstance(exc, TimeoutError):
        return "provider_timeout"
    if isinstance(exc, (json.JSONDecodeError, KeyError, TypeError, ValueError)):
        return "parse_failed"
    return _SAFE_FALLBACK_REASON


def _safe_text(value: Any, *, default: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    lowered = text.lower()
    if any(marker in lowered for marker in _FORBIDDEN_TEXT_MARKERS):
        return "内容已脱敏；该占位不保留原始模型输出。"
    if len(text) > _MAX_TEXT_LENGTH:
        return f"{text[:_MAX_TEXT_LENGTH].rstrip()}..."
    return text


def _safe_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value[:_MAX_LIST_ITEMS]:
        text = _safe_text(item)
        if text:
            items.append(text)
    return items


def _safe_agent_task_prompt_context(agent_task: Mapping[str, Any] | None) -> str:
    """Render a bounded task context for the internal L2 placeholder prompt."""
    if not isinstance(agent_task, Mapping):
        return "agent_task_present: false"
    upstream = agent_task.get("upstream_agent_ids", [])
    if isinstance(upstream, list):
        upstream_ids = ", ".join(_safe_text(item) for item in upstream[:_MAX_LIST_ITEMS])
    else:
        upstream_results = agent_task.get("upstream_results", {})
        upstream_ids = (
            ", ".join(str(key) for key in list(upstream_results)[:_MAX_LIST_ITEMS])
            if isinstance(upstream_results, Mapping)
            else ""
        )
    has_l1_data = bool(agent_task.get("has_l1_data_bundle") or agent_task.get("data_bundle"))
    has_l1_entity = bool(
        agent_task.get("has_l1_entity_relation_bundle")
        or agent_task.get("entity_relation_bundle")
    )
    return "\n".join(
        [
            "agent_task_present: true",
            f"agent_task_schema: {_safe_text(agent_task.get('schema'))}",
            f"agent_task_instruction: {_safe_text(agent_task.get('task_instruction'))}",
            f"required_output_schema: {_safe_text(agent_task.get('required_output_schema'))}",
            f"has_l1_data_bundle: {has_l1_data}",
            f"has_l1_entity_relation_bundle: {has_l1_entity}",
            f"upstream_agent_ids: {upstream_ids}",
        ]
    )


def _safe_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.2
    return max(0.0, min(MAX_PLACEHOLDER_CONFIDENCE, confidence))


def _content_from_model_response(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, Mapping):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content or "")


def _json_object_from_text(text: str) -> Mapping[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("json_object_missing")
    parsed = json.loads(stripped[start : end + 1])
    if not isinstance(parsed, Mapping):
        raise TypeError("json_root_not_object")
    return parsed


def build_l2_placeholder_prompt(
    *,
    question: str,
    agent_id: str,
    dimension: str,
    agent_label: str,
    plan: Mapping[str, Any] | None,
    as_of: str,
    agent_task: Mapping[str, Any] | None = None,
) -> str:
    """Build the bounded JSON-only prompt for one L2 placeholder slot."""
    plan_schema = str(plan.get("schema") or "") if isinstance(plan, Mapping) else ""
    plan_id = str(plan.get("plan_id") or "") if isinstance(plan, Mapping) else ""
    selected = plan_schema == SELECTED_FIXED_DAG_SCHEMA_VERSION
    task_context = _safe_agent_task_prompt_context(agent_task)
    return (
        "你是 langgraph-my-agent 主系统内部 fixed-DAG L2 占位能力。"
        "你不是服务器上的真实外部专属智能体，不得声称调用了真实 agent、HTTP 服务、实时数据库或搜索。"
        "不要编造实时数据、目标价、收益率、回测结果、财报数字或已验证事实。"
        "必须优先理解 agent_task_v1 中的中文任务指令、L1 证据是否存在、"
        "以及该 agent 的 required_output_schema。"
        "只能输出该功能位正式接入前应关注的分析框架、需补数据和初步非结论性观察。"
        "不要输出 chain-of-thought、密钥、端点、traceback、raw provider response。"
        "仅输出 JSON 对象，字段为 analysis、key_points、evidence、confidence。"
        f"\nquestion: {question}"
        f"\nagent_id: {agent_id}"
        f"\nagent_label: {agent_label}"
        f"\ndimension: {dimension}"
        f"\nas_of: {as_of}"
        f"\nplan_schema: {plan_schema}"
        f"\nplan_id: {plan_id}"
        f"\nselected_plan: {selected}"
        f"\n{task_context}"
    )


def parse_l2_placeholder_response(raw_text: str) -> dict[str, Any]:
    """Parse and sanitize the bounded L2 placeholder JSON response."""
    parsed = _json_object_from_text(raw_text)
    evidence: list[dict[str, Any]] = []
    raw_evidence = parsed.get("evidence", [])
    if isinstance(raw_evidence, list):
        for item in raw_evidence[:_MAX_LIST_ITEMS]:
            if isinstance(item, Mapping):
                fact = _safe_text(item.get("fact") or item.get("summary") or item.get("text"))
            else:
                fact = _safe_text(item)
            if fact:
                evidence.append(
                    {
                        "fact": fact,
                        "source": INTERNAL_LLM_PLACEHOLDER_SOURCE,
                    }
                )
    return {
        "analysis": _safe_text(parsed.get("analysis"), default="该功能位处于内部 LLM 占位状态。"),
        "key_points": _safe_text_list(parsed.get("key_points")),
        "evidence": evidence,
        "confidence": _safe_confidence(parsed.get("confidence")),
    }


def _fallback_conclusion(
    *,
    agent_id: str,
    dimension: str,
    as_of: str,
    reason: str,
) -> ConclusionObject:
    conclusion = build_pending_conclusion(
        agent_id,
        dimension,
        as_of=as_of,
        reason="业务智能体实现仍处于 R3 阶段待完成状态。",
    )
    conclusion["provenance"] = {
        **conclusion["provenance"],
        "runtime_path": "deterministic_pending_conclusion",
        "internal_llm_placeholder_requested": True,
        "internal_llm_placeholder_fallback": True,
        "fallback_reason": reason,
    }
    return conclusion


def build_internal_llm_placeholder_conclusion(
    *,
    question: str,
    agent_id: str,
    plan: Mapping[str, Any] | None,
    as_of: str,
    model: Any,
    agent_task: Mapping[str, Any] | None = None,
) -> ConclusionObject:
    """Build one public-safe L2 internal LLM placeholder conclusion."""
    dimension = AGENT_DIMENSIONS[agent_id]
    prompt = build_l2_placeholder_prompt(
        question=question,
        agent_id=agent_id,
        dimension=dimension,
        agent_label=AGENT_TITLE_LABELS.get(agent_id, agent_id),
        plan=plan,
        as_of=as_of,
        agent_task=agent_task,
    )
    try:
        raw_text = _content_from_model_response(model.invoke(prompt))
        parsed = parse_l2_placeholder_response(raw_text)
    except Exception as exc:
        return _fallback_conclusion(
            agent_id=agent_id,
            dimension=dimension,
            as_of=as_of,
            reason=_safe_reason(exc),
        )

    conclusion: ConclusionObject = {
        "schema": CONCLUSION_OBJECT_SCHEMA_VERSION,
        "schema_version": CONCLUSION_OBJECT_SCHEMA_VERSION,
        "agent_id": agent_id,
        "dimension": dimension,
        "stance": "placeholder_neutral",
        "confidence": parsed["confidence"],
        "status": "partial",
        "evidence": [
            {
                **item,
                "as_of": as_of,
            }
            for item in parsed["evidence"]
        ],
        "as_of": as_of,
        "data_as_of": as_of,
        "event_flags": [],
        "analysis": parsed["analysis"],
        "key_points": parsed["key_points"],
        "provenance": {
            "source": INTERNAL_LLM_PLACEHOLDER_SOURCE,
            "runtime_path": INTERNAL_LLM_PLACEHOLDER_SOURCE,
            "provider_invoked": True,
            "external_invoked": False,
            "deployed_but_deferred": agent_id in _KNOWN_DEPLOYED_BUT_DEFERRED_L2_AGENT_IDS,
            "raw_model_output_stored": False,
            "agent_task_schema": _safe_text(agent_task.get("schema"))
            if isinstance(agent_task, Mapping)
            else "",
            "required_output_schema": _safe_text(agent_task.get("required_output_schema"))
            if isinstance(agent_task, Mapping)
            else "",
        },
    }
    if agent_id == "sentiment_company_radar":
        conclusion["output_routes"] = list(SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES)
    return conclusion


def build_l2_conclusions_with_internal_placeholders(
    plan: Mapping[str, Any] | None = None,
    *,
    question: str,
    as_of: str,
    context: Any,
    agent_tasks: Mapping[str, Any] | None = None,
) -> dict[str, ConclusionObject]:
    """Build selected/full L2 conclusions through the internal placeholder seam."""
    deterministic = build_l2_conclusions(plan, as_of=as_of)
    agent_ids = _agent_ids_for_plan(plan)
    try:
        model = load_chat_model(str(getattr(context, "model", "") or "deepseek/deepseek-v4-flash"))
    except Exception as exc:
        reason = _safe_reason(exc)
        return {
            agent_id: _fallback_conclusion(
                agent_id=agent_id,
                dimension=AGENT_DIMENSIONS[agent_id],
                as_of=as_of,
                reason=reason,
            )
            for agent_id in agent_ids
            if agent_id in deterministic
        }
    return {
        agent_id: build_internal_llm_placeholder_conclusion(
            question=question,
            agent_id=agent_id,
            plan=plan,
            as_of=as_of,
            model=model,
            agent_task=agent_tasks.get(f"l2:{agent_id}") or agent_tasks.get(agent_id)
            if isinstance(agent_tasks, Mapping)
            else None,
        )
        for agent_id in agent_ids
        if agent_id in deterministic
    }
