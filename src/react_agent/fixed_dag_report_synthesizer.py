"""Default-off LLM report synthesis for fixed DAG evidence bundles.

This module is the R8-12D main-system fallback/demo seam. The dev main system
also has a default-off external ``report_generator`` compute handoff, but that
path still requires explicit allowlisting and controlled service evidence. This
local synthesizer remains the bounded fallback so demos can use the same
public-safe evidence bundle without changing runtime bindings or live flags.
"""

from __future__ import annotations

import json
import os
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
    provider_config: dict[str, Any]


def _provider_model_parts(model_name: str) -> tuple[str, str]:
    if "/" not in model_name:
        return "", model_name
    provider, model = model_name.split("/", maxsplit=1)
    return provider.strip().lower(), model.strip()


def provider_config_status(model_name: str) -> dict[str, Any]:
    """Return secret-free provider readiness metadata for report synthesis."""
    provider, model = _provider_model_parts(model_name)
    status: dict[str, Any] = {
        "provider": provider or "invalid",
        "model": model,
        "known_provider": provider in {"deepseek", "openai"},
        "credential_status": "not_checked",
        "base_url_status": "not_checked",
        "preflight_status": "ok",
    }
    if not provider:
        return {
            **status,
            "credential_status": "missing",
            "base_url_status": "not_checked",
            "preflight_status": "invalid_model_name",
        }
    if provider == "deepseek":
        credential_present = bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"))
        base_url_present = bool(os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL"))
        return {
            **status,
            "credential_status": "present" if credential_present else "missing",
            "base_url_status": "present" if base_url_present else "default",
            "preflight_status": "ok" if credential_present else "missing_credential",
        }
    if provider == "openai":
        credential_present = bool(os.getenv("OPENAI_API_KEY"))
        return {
            **status,
            "credential_status": "present" if credential_present else "missing",
            "base_url_status": "present" if os.getenv("OPENAI_BASE_URL") else "default",
            "preflight_status": "ok" if credential_present else "missing_credential",
        }
    return status


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
        "其中 agent_evidence_bundle_v1 是最重要的证据输入，包含每个 agent 收到的任务、"
        "L1 证据状态、L2 单体输出、L3 综合输出、证据条目、质量诊断和失败原因。"
        "对每个已完成或 partial 的真实 agent，优先读取并使用 research_points、"
        "evidence_items、domain_metrics、drivers、data_quality，而不是只复述 summary。"
        "research_points 是 agent 基于自身确定性材料生成的可报告化研究判断，"
        "包含 claim、support、interpretation、decision_implication 和 caveat；"
        "domain_metrics 是从外部 raw_output 中白名单抽取的 public-safe 业务指标；"
        "drivers 是 public-safe 的模型驱动/归因/成员解释；"
        "data_quality 是 public-safe 的覆盖率、校准、反前视、缓存或数据完整性说明。"
        "你需要理解各个 L2 单体智能体输入、L3 综合智能体输入、风险门、宏观调节和决策上下文。"
        "如果 L3 输出包含 composite_quality_v1，必须使用其中的 representativeness、coverage、"
        "complete_coverage、dominant_member_weight、blocking_caveats 来说明该维度是可用、"
        "带边界可用、证据薄，还是薄且被单一成员主导。"
        "如果 risk_composite 同时包含 aggregate_gate、member_override_gate、override_triggered、"
        "aggregate_risk_score 或 max_member_risk_score，必须区分加权综合风险和单成员 override："
        "不要把 aggregate_gate=pass 写成无条件低风险；若 member_override_gate=manual_review，"
        "必须说明触发成员和人工复核含义。"
        "每个主要维度至少引用两条可用的结构化证据；证据不足时说明缺口。"
        "报告必须解释 agent 之间的冲突、数据时点差异、权重/降权原因和 partial 对结论的影响。"
        "遇到 status=error、partial、placeholder 或证据为空时，必须在报告中明确说明其影响，"
        "不要把占位或失败输出当作强业务结论。"
        "最终报告面向业务用户，正文、sections、evidence_cards 和 limitations 不要直接暴露 "
        "stance/status/partial/placeholder/state=complete/report_input_bundle_v1 等 schema 字段名；"
        "应分别写成综合倾向、证据不完整、未接入真实数据的占位输出、已返回结构化结果、"
        "结构化报告输入包等自然中文。"
        "输出语言必须以中文为主；如果确实需要保留技术专有名词或合同词，必须先写中文解释，"
        "再用括号保留英文原词，例如“选择路由（selected routing）”、"
        "“完整分析图（full DAG）”、“风险分（risk_score）”、"
        "“仅计算路径（compute-only）”。"
        "不得在公开报告里裸露 selected routing、selected scope、balanced_watch、"
        "risk_score、current_price、trade_date、deterministic enrichment、"
        "compute-only、no-invoke、no-provider、no-raw-response 等未中文化词。"
        "也不要直接输出 positive_watch、research_hold、defensive_observe、manual_review、"
        "risk_blocked、pass 等枚举值；应写成积极关注、研究观察、防御观察、人工复核、"
        "风险阻断、通过等中文业务表达。"
        "如果 L1 金融数据服务未在本轮真实计算白名单中映射，不要写成“待实施”或"
        "“所有模型未使用数据”，应写成“本轮未纳入真实 L1 计算路径，L2 使用各自内部或快照数据”。"
        "compute-only、allowlist、default-off 等运行边界只在 limitations 中简要说明，不要写进主体研判。"
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
    provider_config: Mapping[str, Any] | None = None,
) -> LLMReportSynthesisOutcome:
    fallback = dict(fallback_report_result)
    limitations = list(fallback.get("limitations", []) or [])
    if reason.startswith("provider_configuration_missing"):
        notice = "大模型报告综合 provider 未配置或不可用，已回退到模板报告。"
    elif reason.startswith("invalid_report_input_bundle:"):
        notice = "大模型报告综合输入未通过校验，已回退到模板报告。"
    elif reason.startswith("synthesis_failed:"):
        notice = "大模型报告综合输出未通过解析或校验，已回退到模板报告。"
    else:
        notice = "大模型报告综合未完成，已回退到模板报告。"
    if notice not in limitations:
        limitations.append(notice)
    fallback["limitations"] = limitations
    return {
        "report_result": cast(ReportResult, fallback),
        "used_llm_report": False,
        "attempted": attempted,
        "provider_invoked": provider_invoked,
        "fallback_reason": reason,
        "provider_config": dict(provider_config or {}),
    }


def synthesize_report_result_with_llm(
    *,
    question: str,
    report_input_bundle: Mapping[str, Any],
    fallback_report_result: Mapping[str, Any],
    context: Any,
) -> LLMReportSynthesisOutcome:
    """Generate a final report from report_input_bundle_v1 behind an explicit flag.

    The explicit flag keeps this helper out of the default graph path. It can be
    replaced by, or kept as fallback for, a future external report-generator
    agent once that service exposes the same bounded input/output schemas.
    """
    valid, reason = validate_report_input_bundle(report_input_bundle)
    if not valid:
        return _fallback_outcome(
            fallback_report_result=fallback_report_result,
            attempted=False,
            provider_invoked=False,
            reason=f"invalid_report_input_bundle:{reason}",
            provider_config={},
        )
    model_name = str(
        getattr(context, "llm_report_synthesis_model", "")
        or getattr(context, "model", "")
        or "deepseek/deepseek-chat"
    )
    config_status = provider_config_status(model_name)
    if config_status.get("preflight_status") in {"invalid_model_name", "missing_credential"}:
        return _fallback_outcome(
            fallback_report_result=fallback_report_result,
            attempted=True,
            provider_invoked=False,
            reason=f"provider_configuration_missing:{config_status['preflight_status']}",
            provider_config=config_status,
        )
    try:
        model = load_chat_model(model_name)
    except Exception:
        return _fallback_outcome(
            fallback_report_result=fallback_report_result,
            attempted=True,
            provider_invoked=False,
            reason="provider_configuration_missing:loader_error",
            provider_config={**config_status, "preflight_status": "loader_error"},
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
            provider_config=config_status,
        )
    return {
        "report_result": report,
        "used_llm_report": True,
        "attempted": True,
        "provider_invoked": provider_invoked,
        "fallback_reason": "",
        "provider_config": config_status,
    }
