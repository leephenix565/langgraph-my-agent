"""Default-off LLM report synthesis for fixed DAG evidence bundles."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, TypedDict, cast

from react_agent.fixed_dag_contracts import (
    REPORT_RESULT_SCHEMA_VERSION,
    ReportResult,
    validate_report_input_bundle,
    validate_report_result,
)
from react_agent.utils import load_chat_model

LLM_REPORT_SYNTHESIS_SOURCE = "llm_report_synthesis"
_MAX_TEXT_LENGTH = 7000
_MAX_SECTION_LENGTH = 1400
_MAX_SECTIONS = 8
_MAX_CARDS = 8
_FORBIDDEN_OUTPUT_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "authorization",
    "cookie",
    "set-cookie",
    "traceback",
    "raw_response",
    "raw_provider_response",
    "raw_external_json",
    "chain-of-thought",
    "chain of thought",
    "http://",
    "https://",
    ".env",
    "openai_api_key",
    "deepseek_api_key",
)


class LLMReportSynthesisOutcome(TypedDict):
    """Result metadata for a default-off LLM report synthesis attempt."""

    report_result: ReportResult
    used_llm_report: bool
    attempted: bool
    provider_invoked: bool
    fallback_reason: str


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


def _contains_forbidden_output(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key).lower() in _FORBIDDEN_OUTPUT_MARKERS
            or _contains_forbidden_output(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_output(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in _FORBIDDEN_OUTPUT_MARKERS)
    return False


def _safe_text(value: Any, *, limit: int = _MAX_TEXT_LENGTH) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if _contains_forbidden_output(text):
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) > limit:
        return f"{text[:limit].rstrip()}..."
    return text


def _safe_slug(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip().lower()
    allowed = "".join(ch for ch in text if ch.isalnum() or ch in {"_", "-"})
    return allowed[:80] or fallback


def _safe_sections(value: Any, fallback_sections: Any) -> list[dict[str, str]]:
    raw_items = value if isinstance(value, list) else fallback_sections
    sections: list[dict[str, str]] = []
    if not isinstance(raw_items, list):
        return sections
    for index, item in enumerate(raw_items[:_MAX_SECTIONS]):
        if not isinstance(item, Mapping):
            continue
        title = _safe_text(item.get("title"), limit=80)
        content = _safe_text(item.get("content"), limit=_MAX_SECTION_LENGTH)
        if not title or not content:
            continue
        sections.append(
            {
                "id": _safe_slug(item.get("id"), fallback=f"section_{index + 1}"),
                "title": title,
                "content": content,
            }
        )
    return sections


def _safe_evidence_cards(value: Any, fallback_cards: Any) -> list[dict[str, str]]:
    raw_items = value if isinstance(value, list) else fallback_cards
    cards: list[dict[str, str]] = []
    if isinstance(raw_items, list):
        for item in raw_items[:_MAX_CARDS]:
            if not isinstance(item, Mapping):
                continue
            title = _safe_text(item.get("title"), limit=80)
            note = _safe_text(item.get("note"), limit=260)
            if title and note:
                cards.append({"title": title, "note": note})
    cards.append(
        {
            "title": "报告生成方式",
            "note": "本轮由默认关闭的大模型报告综合器读取结构化输入包后生成。",
        }
    )
    return cards


def build_llm_report_prompt(
    *,
    question: str,
    report_input_bundle: Mapping[str, Any],
) -> str:
    """Build the bounded JSON-only prompt for report synthesis."""
    bundle_json = json.dumps(report_input_bundle, ensure_ascii=False, sort_keys=True)
    return (
        "你是固定 DAG 主系统的报告生成智能体。"
        "请只基于 report_input_bundle_v1 中的结构化输入写最终中文研判报告。"
        "你需要理解各个 L2 单体智能体输入、L3 综合智能体输入、风险门、宏观调节和决策上下文。"
        "不要编造未给出的实时数据、目标价、收益率、财报数字、新闻或外部来源。"
        "不要输出接口地址、密钥、错误栈、原始外部响应或内部推理草稿。"
        "请输出一个 JSON 对象，字段必须为 title、answer、sections、evidence_cards、limitations。"
        "answer 必须是自然中文报告，包含估值、市场、风险、宏观、综合研判和注意事项。"
        "sections 为数组，每项包含 id、title、content。"
        "evidence_cards 为数组，每项包含 title、note。"
        "limitations 为数组，说明这是显式开关下的报告综合，不代表默认生产调用。"
        f"\n用户问题：{question}"
        f"\nreport_input_bundle_v1：{bundle_json}"
    )


def _report_from_parsed(
    parsed: Mapping[str, Any],
    *,
    fallback_report_result: Mapping[str, Any],
) -> ReportResult:
    if _contains_forbidden_output(parsed):
        raise ValueError("unsafe_model_output")
    title = _safe_text(parsed.get("title"), limit=80) or "固定 DAG 研判报告"
    answer = _safe_text(parsed.get("answer"), limit=_MAX_TEXT_LENGTH)
    if not answer:
        raise ValueError("answer_missing")
    if "研判流程" not in answer:
        answer = f"研判流程报告：\n{answer}"
    sections = _safe_sections(parsed.get("sections"), fallback_report_result.get("sections"))
    if not sections:
        raise ValueError("sections_missing")
    evidence_cards = _safe_evidence_cards(
        parsed.get("evidence_cards"),
        fallback_report_result.get("evidence_cards"),
    )
    limitations = [
        _safe_text(item, limit=220)
        for item in parsed.get("limitations", [])
        if _safe_text(item, limit=220)
    ] if isinstance(parsed.get("limitations"), list) else []
    limitation = "大模型报告综合为显式开关路径，不改变默认运行配置。"
    if limitation not in limitations:
        limitations.append(limitation)
    result: ReportResult = {
        "schema": REPORT_RESULT_SCHEMA_VERSION,
        "schema_version": REPORT_RESULT_SCHEMA_VERSION,
        "title": title,
        "answer": answer,
        "status": "complete",
        "sections": sections,
        "evidence_cards": evidence_cards,
        "limitations": limitations,
    }
    valid, reason = validate_report_result(result)
    if not valid:
        raise ValueError(reason)
    return result


def _fallback_outcome(
    *,
    fallback_report_result: Mapping[str, Any],
    attempted: bool,
    provider_invoked: bool,
    reason: str,
) -> LLMReportSynthesisOutcome:
    fallback = dict(fallback_report_result)
    limitations = list(fallback.get("limitations", []) or [])
    notice = "大模型报告综合未通过校验，已回退到模板报告。"
    if notice not in limitations:
        limitations.append(notice)
    fallback["limitations"] = limitations
    return {
        "report_result": cast(ReportResult, fallback),
        "used_llm_report": False,
        "attempted": attempted,
        "provider_invoked": provider_invoked,
        "fallback_reason": reason,
    }


def synthesize_report_result_with_llm(
    *,
    question: str,
    report_input_bundle: Mapping[str, Any],
    fallback_report_result: Mapping[str, Any],
    context: Any,
) -> LLMReportSynthesisOutcome:
    """Generate a final report from report_input_bundle_v1 behind an explicit flag."""
    valid, reason = validate_report_input_bundle(report_input_bundle)
    if not valid:
        return _fallback_outcome(
            fallback_report_result=fallback_report_result,
            attempted=False,
            provider_invoked=False,
            reason=f"invalid_report_input_bundle:{reason}",
        )
    model_name = str(
        getattr(context, "llm_report_synthesis_model", "")
        or getattr(context, "model", "")
        or "deepseek/deepseek-chat"
    )
    try:
        model = load_chat_model(model_name)
    except Exception:
        return _fallback_outcome(
            fallback_report_result=fallback_report_result,
            attempted=True,
            provider_invoked=False,
            reason="provider_configuration_missing",
        )
    prompt = build_llm_report_prompt(
        question=question,
        report_input_bundle=report_input_bundle,
    )
    provider_invoked = True
    try:
        raw_text = _content_from_model_response(model.invoke(prompt))
        parsed = _json_object_from_text(raw_text)
        report = _report_from_parsed(
            parsed,
            fallback_report_result=fallback_report_result,
        )
    except Exception as exc:
        return _fallback_outcome(
            fallback_report_result=fallback_report_result,
            attempted=True,
            provider_invoked=provider_invoked,
            reason=f"synthesis_failed:{type(exc).__name__}",
        )
    return {
        "report_result": report,
        "used_llm_report": True,
        "attempted": True,
        "provider_invoked": provider_invoked,
        "fallback_reason": "",
    }
