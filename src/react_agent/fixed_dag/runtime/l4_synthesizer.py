"""Default-off LLM decision synthesis for the fixed-DAG L4 decision agent.

This module is the main-system helper shared by the sandbox L4
``decision_synthesizer`` service and tests.  It intentionally does not change
runtime bindings or the default graph path: callers must opt in explicitly and
must keep ``build_decision_result`` as fallback.

(Originally at ``fixed_dag_l4_decision_synthesizer.py``, moved here during
Phase 1 consolidation.)
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, TypedDict, cast

from react_agent.fixed_dag_contracts import (
    DECISION_RESULT_SCHEMA_VERSION,
    DIMENSION_GROUPS,
    DecisionResult,
    build_decision_result,
    validate_decision_result,
)
from react_agent.fixed_dag.report_synthesizer import provider_config_status
from react_agent.utils import load_chat_model

LLM_DECISION_SYNTHESIS_SOURCE = "llm_l4_decision_synthesis"
_MAX_PROMPT_JSON_LENGTH = 24_000
_MAX_TEXT_LENGTH = 700
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
_REQUIRED_TRACE_STAGES = (
    "dimension_induction",
    "macro_risk_adjustment",
    "conflict_resolution",
)
_ALLOWED_DECISIONS = {
    "positive_watch",
    "research_hold",
    "neutral_watch",
    "balanced_watch",
    "defensive_observe",
    "manual_review",
    "risk_blocked",
    "conservative_pending",
    "needs_more_evidence",
}


class LLMDecisionSynthesisOutcome(TypedDict):
    """Result metadata for one default-off L4 decision synthesis attempt."""

    decision_result: DecisionResult
    used_llm_decision: bool
    attempted: bool
    provider_invoked: bool
    fallback_reason: str
    provider_config: dict[str, Any]


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
    text = str(value or "").strip().replace("\r\n", "\n").replace("\r", "\n")
    if not text or _contains_forbidden_output(text):
        return ""
    if len(text) > limit:
        return f"{text[:limit].rstrip()}..."
    return text


def _safe_code(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip().lower()
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch in {"_", "-"})
    return cleaned[:80] or fallback


def _bounded_score(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(-1.0, min(1.0, number))


def _bounded_confidence(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _safe_target_price_range(value: Any) -> dict[str, float | None]:
    if not isinstance(value, Mapping):
        return {"low": None, "mid": None, "high": None}
    result: dict[str, float | None] = {}
    for key in ("low", "mid", "high"):
        raw = value.get(key)
        if raw is None or raw == "":
            result[key] = None
            continue
        try:
            result[key] = float(raw)
        except (TypeError, ValueError):
            result[key] = None
    return result


def _dimension_view_from_result(result: Mapping[str, Any]) -> dict[str, Any]:
    view = {
        "stance": _safe_text(result.get("stance") or "not_evaluated", limit=100),
        "confidence": _bounded_confidence(result.get("confidence")),
        "status": _safe_code(result.get("status"), fallback="partial"),
    }
    for key in ("gate", "risk_score", "regime", "dimension_weights", "risk_sensitivity"):
        if key in result:
            raw = result.get(key)
            if isinstance(raw, int | float):
                view[key] = raw
            elif isinstance(raw, Mapping):
                view[key] = {
                    _safe_text(k, limit=40): _bounded_score(v)
                    if isinstance(v, int | float | str)
                    else _safe_text(v, limit=80)
                    for k, v in list(raw.items())[:8]
                    if _safe_text(k, limit=40)
                }
            else:
                text = _safe_text(raw, limit=120)
                if text:
                    view[key] = text
    return {key: value for key, value in view.items() if value not in ("", {}, [])}


def _safe_dimension_views(
    parsed_views: Any,
    dimension_results: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    views: dict[str, dict[str, Any]] = {}
    if isinstance(parsed_views, Mapping):
        for dimension, raw in parsed_views.items():
            key = _safe_code(dimension, fallback="")
            if key not in DIMENSION_GROUPS or not isinstance(raw, Mapping):
                continue
            view = {
                "stance": _safe_text(raw.get("stance") or "not_evaluated", limit=120),
                "confidence": _bounded_confidence(raw.get("confidence")),
                "status": _safe_code(raw.get("status"), fallback="partial"),
            }
            summary = _safe_text(raw.get("summary"), limit=260)
            if summary:
                view["summary"] = summary
            views[key] = view
    for dimension, result in dimension_results.items():
        if dimension in DIMENSION_GROUPS and isinstance(result, Mapping) and dimension not in views:
            views[dimension] = _dimension_view_from_result(result)
    return views


def _safe_reasoning_trace(value: Any) -> list[dict[str, str]]:
    trace: list[dict[str, str]] = []
    if isinstance(value, list):
        for item in value[:8]:
            if not isinstance(item, Mapping):
                continue
            stage = _safe_code(item.get("stage"), fallback="")
            summary = _safe_text(item.get("summary"), limit=420)
            if stage and summary:
                trace.append({"stage": stage, "summary": summary})
    existing = {item["stage"] for item in trace}
    fallback_summaries = {
        "dimension_induction": "已读取估值、市场、风险、宏观四个综合结果，并比较其方向、置信度和证据完整性。",
        "macro_risk_adjustment": "宏观调节和风险闸门作为硬约束参与最终判断，风险 veto 或人工复核信号不得被语言模型覆盖。",
        "conflict_resolution": "当估值、市场、风险或宏观信号冲突时，最终结论必须保守表达，并说明证据不完整或缺失成员对置信度的影响。",
    }
    for stage in _REQUIRED_TRACE_STAGES:
        if stage not in existing:
            trace.append({"stage": stage, "summary": fallback_summaries[stage]})
    return trace


def _dimension_status_summary(dimension_results: Mapping[str, Any]) -> tuple[bool, bool]:
    saw_partial = False
    saw_error = False
    for result in dimension_results.values():
        if not isinstance(result, Mapping):
            continue
        status = str(result.get("status") or "").strip().lower()
        if status in {"partial", "needs_clarification"}:
            saw_partial = True
        elif status == "error":
            saw_error = True
    return saw_partial, saw_error


def _risk_guard_state(dimension_results: Mapping[str, Any]) -> tuple[str, str]:
    risk = dimension_results.get("risk", {})
    if not isinstance(risk, Mapping):
        return "missing", ""
    gate = str(risk.get("gate") or "").strip().lower()
    provenance = risk.get("provenance")
    override_gate = ""
    if isinstance(provenance, Mapping):
        override_gate = str(
            provenance.get("member_override_gate")
            or provenance.get("aggregate_gate")
            or ""
        ).strip().lower()
    text = f"{gate} {override_gate}"
    if bool(risk.get("veto")) or any(token in text for token in ("veto", "blocked", "block")):
        return "risk_blocked", gate or override_gate
    if "manual_review" in text or "review" in text:
        return "manual_review", gate or override_gate
    if gate:
        return gate, gate
    return "available", ""


def _calibrate_decision_label_and_score(result: DecisionResult) -> DecisionResult:
    calibrated: DecisionResult = cast(DecisionResult, dict(result))
    decision = str(calibrated.get("decision") or "").strip().lower()
    score = _bounded_score(calibrated.get("score"), default=0.0)
    confidence = _bounded_confidence(calibrated.get("confidence"), default=0.0)
    if decision == "strong_buy":
        decision = "positive_watch"
    if decision not in _ALLOWED_DECISIONS:
        decision = "research_hold"
    if decision == "positive_watch" and score < 0.15:
        decision = "research_hold" if score >= -0.1 else "defensive_observe"
    elif decision in {"research_hold", "neutral_watch", "balanced_watch"}:
        if score >= 0.25:
            decision = "positive_watch"
        elif score <= -0.15:
            decision = "defensive_observe"
        elif decision == "balanced_watch":
            decision = "research_hold"
    elif decision == "defensive_observe" and score > 0.1:
        decision = "research_hold"
    if decision == "manual_review":
        score = min(score, 0.0)
        confidence = min(confidence, 0.55)
    elif decision == "risk_blocked":
        score = min(score, -0.5)
        confidence = min(confidence, 0.75)
    elif decision == "research_hold":
        score = max(-0.2, min(0.2, score))
    calibrated["decision"] = decision
    calibrated["score"] = score
    calibrated["confidence"] = confidence
    return calibrated


def _apply_hard_guards(
    result: DecisionResult,
    *,
    dimension_results: Mapping[str, Any],
) -> DecisionResult:
    guarded: DecisionResult = cast(DecisionResult, dict(result))
    saw_partial, saw_error = _dimension_status_summary(dimension_results)
    risk_state, risk_gate = _risk_guard_state(dimension_results)
    trace = list(guarded["reasoning_trace"])
    if risk_state == "risk_blocked":
        guarded["decision"] = "risk_blocked"
        guarded["score"] = min(float(guarded["score"]), -0.5)
        guarded["confidence"] = min(float(guarded["confidence"]), 0.75)
        guarded["status"] = "partial" if saw_partial or saw_error else guarded["status"]
        trace.append(
            {
                "stage": "risk_guard",
                "summary": f"风险综合给出阻断信号 {risk_gate or 'veto'}，L4 决策不能被大模型改写为正向结论。",
            }
        )
    elif risk_state == "manual_review":
        guarded["decision"] = "manual_review"
        guarded["score"] = min(float(guarded["score"]), 0.0)
        guarded["confidence"] = min(float(guarded["confidence"]), 0.55)
        guarded["status"] = "partial"
        trace.append(
            {
                "stage": "risk_guard",
                "summary": f"风险综合触发人工复核信号 {risk_gate or 'manual_review'}，最终结论只能表达为待复核。",
            }
        )
    if saw_error:
        guarded["status"] = "partial"
        guarded["confidence"] = min(float(guarded["confidence"]), 0.5)
    elif saw_partial:
        guarded["status"] = "partial"
        guarded["confidence"] = min(float(guarded["confidence"]), 0.65)
    guarded["reasoning_trace"] = _safe_reasoning_trace(trace)
    return _calibrate_decision_label_and_score(guarded)


def build_llm_decision_prompt(
    *,
    question: str,
    dimension_results: Mapping[str, Any],
    fallback_decision_result: Mapping[str, Any],
) -> str:
    """Build the bounded JSON-only prompt for L4 decision synthesis."""
    input_bundle = {
        "question": question,
        "dimension_results": dimension_results,
        "fallback_decision_result": fallback_decision_result,
        "hard_constraints": [
            "只输出 decision_result_v1 JSON，不输出解释性正文或 markdown。",
            "不得编造未给出的实时数据、目标价、收益率、新闻或外部来源。",
            "risk veto、risk blocked 或 manual_review 信号不得被改写为正向结论。",
            "partial、error、placeholder 或缺失证据必须降低 status/confidence，并写入 reasoning_trace。",
            "decision 只能是研究辅助语义，不得输出 strong_buy 或强交易指令。",
            "reasoning_trace.summary 必须使用自然中文，不要直接复述 stance/status/partial/placeholder 字段名。",
        ],
    }
    bundle_json = json.dumps(input_bundle, ensure_ascii=False, sort_keys=True)
    if len(bundle_json) > _MAX_PROMPT_JSON_LENGTH:
        bundle_json = f"{bundle_json[:_MAX_PROMPT_JSON_LENGTH].rstrip()}..."
    return (
        "你是 fixed DAG 的 L4 决策融合智能体 decision_synthesizer。"
        "你的任务是阅读四个 L3 composite 的结构化结果，用大模型理解能力做跨维度融合，"
        "但必须服从风险门控、证据缺口和 public-safe 输出边界。"
        "请输出 JSON 对象，字段必须为 schema、schema_version、decision、score、"
        "target_price_range、dimension_views、reasoning_trace、confidence、status、as_of。"
        "reasoning_trace 至少包含 dimension_induction、macro_risk_adjustment、"
        "conflict_resolution 三个 stage。"
        "如果目标价口径不统一，target_price_range 的 low/mid/high 必须为 null。"
        f"\n输入：{bundle_json}"
    )


def _decision_from_parsed(
    parsed: Mapping[str, Any],
    *,
    fallback_decision_result: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
    as_of: str,
) -> DecisionResult:
    if _contains_forbidden_output(parsed):
        raise ValueError("unsafe_model_output")
    decision = _safe_code(parsed.get("decision"), fallback="balanced_watch")
    if decision == "strong_buy":
        decision = "positive_watch"
    fallback_status = str(fallback_decision_result.get("status") or "partial")
    result: DecisionResult = {
        "schema": DECISION_RESULT_SCHEMA_VERSION,
        "schema_version": DECISION_RESULT_SCHEMA_VERSION,
        "decision": decision,
        "score": _bounded_score(parsed.get("score"), default=0.0),
        "target_price_range": _safe_target_price_range(parsed.get("target_price_range")),
        "dimension_views": _safe_dimension_views(
            parsed.get("dimension_views"),
            dimension_results,
        ),
        "reasoning_trace": _safe_reasoning_trace(parsed.get("reasoning_trace")),
        "confidence": _bounded_confidence(parsed.get("confidence"), default=0.0),
        "status": _safe_code(parsed.get("status"), fallback=fallback_status),
        "as_of": _safe_text(parsed.get("as_of") or as_of, limit=40),
    }
    result = _apply_hard_guards(result, dimension_results=dimension_results)
    valid, reason = validate_decision_result(result)
    if not valid:
        raise ValueError(reason)
    return result


def _fallback_outcome(
    *,
    fallback_decision_result: Mapping[str, Any],
    attempted: bool,
    provider_invoked: bool,
    reason: str,
    provider_config: Mapping[str, Any] | None = None,
) -> LLMDecisionSynthesisOutcome:
    return {
        "decision_result": cast(DecisionResult, dict(fallback_decision_result)),
        "used_llm_decision": False,
        "attempted": attempted,
        "provider_invoked": provider_invoked,
        "fallback_reason": reason,
        "provider_config": dict(provider_config or {}),
    }


def synthesize_decision_result_with_llm(
    *,
    question: str,
    dimension_results: Mapping[str, Any],
    fallback_decision_result: Mapping[str, Any] | None = None,
    context: Any,
    as_of: str | None = None,
) -> LLMDecisionSynthesisOutcome:
    """Generate a decision_result_v1 behind an explicit L4 agent path."""
    fallback = (
        dict(fallback_decision_result)
        if isinstance(fallback_decision_result, Mapping)
        else build_decision_result(dimension_results, as_of=as_of)
    )
    valid_fallback, fallback_reason = validate_decision_result(fallback)
    if not valid_fallback:
        fallback = build_decision_result(dimension_results, as_of=as_of)
        valid_fallback, fallback_reason = validate_decision_result(fallback)
    if not valid_fallback:
        raise ValueError(f"invalid_fallback_decision:{fallback_reason}")

    model_name = str(
        getattr(context, "llm_l4_decision_synthesis_model", "")
        or getattr(context, "llm_report_synthesis_model", "")
        or getattr(context, "model", "")
        or "deepseek/deepseek-v4-flash"
    )
    config_status = provider_config_status(model_name)
    if config_status.get("preflight_status") in {"invalid_model_name", "missing_credential"}:
        return _fallback_outcome(
            fallback_decision_result=fallback,
            attempted=True,
            provider_invoked=False,
            reason=f"provider_configuration_missing:{config_status['preflight_status']}",
            provider_config=config_status,
        )
    try:
        model = load_chat_model(model_name)
    except Exception:
        return _fallback_outcome(
            fallback_decision_result=fallback,
            attempted=True,
            provider_invoked=False,
            reason="provider_configuration_missing:loader_error",
            provider_config={**config_status, "preflight_status": "loader_error"},
        )

    prompt = build_llm_decision_prompt(
        question=question,
        dimension_results=dimension_results,
        fallback_decision_result=fallback,
    )
    provider_invoked = True
    try:
        raw_text = _content_from_model_response(model.invoke(prompt))
        parsed = _json_object_from_text(raw_text)
        decision = _decision_from_parsed(
            parsed,
            fallback_decision_result=fallback,
            dimension_results=dimension_results,
            as_of=str(as_of or fallback.get("as_of") or ""),
        )
    except Exception as exc:
        return _fallback_outcome(
            fallback_decision_result=fallback,
            attempted=True,
            provider_invoked=provider_invoked,
            reason=f"synthesis_failed:{type(exc).__name__}",
            provider_config=config_status,
        )
    return {
        "decision_result": decision,
        "used_llm_decision": True,
        "attempted": True,
        "provider_invoked": provider_invoked,
        "fallback_reason": "",
        "provider_config": config_status,
    }
