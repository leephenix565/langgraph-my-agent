"""Default-off LLM explanation layer for fixed-DAG L3 composites.

This seam is intentionally narrower than report synthesis. It may add
public-safe language explanations to L3 composite provenance, but it must not
change deterministic fusion fields such as stance, confidence, gate,
risk_score, dimension_weights, member weights, or status.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, TypedDict

from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    validate_dimension_composite_result,
)
from react_agent.fixed_dag_report_synthesizer import provider_config_status
from react_agent.utils import load_chat_model

LLM_L3_EXPLANATION_SOURCE = "llm_l3_explanation"
_MAX_TEXT_LENGTH = 900
_MAX_PROMPT_JSON_CHARS = 26000
_MAX_POINTS_PER_DIMENSION = 4
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
_STABLE_FUSION_FIELDS = (
    "stance",
    "confidence",
    "status",
    "gate",
    "veto",
    "penalty",
    "risk_score",
    "regime",
    "risk_sensitivity",
    "dimension_weights",
    "contributing_agents",
)


class L3ExplanationOutcome(TypedDict):
    """Result metadata for the default-off L3 explanation attempt."""

    dimension_results: dict[str, Any]
    used_llm_explanation: bool
    attempted: bool
    provider_invoked: bool
    fallback_reason: str
    provider_config: dict[str, Any]


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
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if _contains_forbidden_output(text):
        return ""
    if len(text) > limit:
        return f"{text[:limit].rstrip()}..."
    return text


def _safe_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 3:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        return _safe_text(value, limit=240) or None
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, raw in list(value.items())[:12]:
            text_key = _safe_text(key, limit=80)
            if not text_key:
                continue
            bounded = _safe_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                result[text_key] = bounded
        return result or None
    if isinstance(value, list):
        items: list[Any] = []
        for raw in value[:8]:
            bounded = _safe_value(raw, depth=depth + 1)
            if bounded not in (None, "", [], {}):
                items.append(bounded)
        return items or None
    return _safe_text(value, limit=160) or None


def _safe_list(value: Any, *, limit: int = 6) -> list[Any]:
    if not isinstance(value, list):
        return []
    result: list[Any] = []
    for raw in value[:limit]:
        bounded = _safe_value(raw)
        if bounded not in (None, "", [], {}):
            result.append(bounded)
    return result


def _safe_mapping(value: Any, *, limit: int = 8) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key, raw in list(value.items())[:limit]:
        text_key = _safe_text(key, limit=80)
        if not text_key:
            continue
        bounded = _safe_value(raw)
        if bounded not in (None, "", [], {}):
            result[text_key] = bounded
    return result


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


def _compact_evidence(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    facts: list[str] = []
    for item in value[:4]:
        if not isinstance(item, Mapping):
            continue
        for key in ("fact", "summary", "note"):
            text = _safe_text(item.get(key), limit=180)
            if text:
                facts.append(text)
                break
    return facts


def _compact_l2_conclusions(l2_conclusions: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for agent_id, raw in l2_conclusions.items():
        if not isinstance(raw, Mapping):
            continue
        provenance = raw.get("provenance", {})
        item: dict[str, Any] = {
            "agent_id": str(agent_id),
            "dimension": _safe_text(raw.get("dimension"), limit=40),
            "status": _safe_text(raw.get("status"), limit=40),
            "stance": _safe_text(raw.get("stance"), limit=80),
            "confidence": raw.get("confidence") if isinstance(raw.get("confidence"), int | float) else 0.0,
            "evidence": _compact_evidence(raw.get("evidence")),
        }
        if isinstance(provenance, Mapping):
            for key in ("domain_metrics", "drivers", "research_points", "data_quality"):
                bounded = (
                    _safe_mapping(provenance.get(key), limit=8)
                    if isinstance(provenance.get(key), Mapping)
                    else _safe_list(provenance.get(key), limit=5)
                )
                if bounded:
                    item[key] = bounded
            if provenance.get("risk_score") is not None:
                item["risk_score"] = provenance.get("risk_score")
        items.append(item)
    return items


def _compact_dimension_results(dimension_results: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for dimension, raw in dimension_results.items():
        if not isinstance(raw, Mapping):
            continue
        provenance = raw.get("provenance", {})
        item: dict[str, Any] = {
            "dimension": str(dimension),
            "agent_id": _safe_text(raw.get("agent_id"), limit=80),
            "status": _safe_text(raw.get("status"), limit=40),
            "stance": _safe_text(raw.get("stance"), limit=80),
            "confidence": raw.get("confidence") if isinstance(raw.get("confidence"), int | float) else 0.0,
            "evidence_refs": _safe_list(raw.get("evidence_refs"), limit=6),
        }
        for field in ("gate", "risk_score", "regime", "dimension_weights"):
            if field in raw:
                item[field] = _safe_value(raw.get(field))
        if isinstance(provenance, Mapping):
            for key in ("member_weight_summary", "domain_metrics", "drivers", "research_points", "data_quality"):
                bounded = (
                    _safe_mapping(provenance.get(key), limit=8)
                    if isinstance(provenance.get(key), Mapping)
                    else _safe_list(provenance.get(key), limit=6)
                )
                if bounded:
                    item[key] = bounded
        items.append(item)
    return items


def build_l3_explanation_prompt(
    *,
    question: str,
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
) -> str:
    """Build the bounded JSON-only L3 explanation prompt."""
    payload = {
        "question": _safe_text(question, limit=500),
        "l2_conclusions": _compact_l2_conclusions(l2_conclusions),
        "dimension_results": _compact_dimension_results(dimension_results),
    }
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(payload_json) > _MAX_PROMPT_JSON_CHARS:
        payload_json = f"{payload_json[:_MAX_PROMPT_JSON_CHARS].rstrip()}..."
    return (
        "你是 fixed DAG 的 L3 综合解释层。请只基于输入中的 L2 单体输出和"
        " deterministic L3 综合结果，生成中文冲突归纳、成员贡献解释和缺口说明。"
        "你只能补充语言解释，不得修改或重算 stance、confidence、gate、risk_score、"
        "dimension_weights、member weights、status 或 contributing_agents。"
        "如果某个维度是 partial 或成员缺失，必须说明缺口影响，不能把 placeholder "
        "当成真实 evidence。不要编造输入中不存在的数据、目标价、新闻或外部来源。"
        "不要输出接口地址、密钥、错误栈、原始外部响应或内部推理草稿。"
        "请输出 JSON 对象，格式为："
        '{"dimensions":[{"dimension":"value","research_points":[{"claim":"...",'
        '"support":"...","interpretation":"...","decision_implication":"...",'
        '"caveat":"..."}],"notes":["..."]}]}。'
        "dimension 只能是 value、market、risk、macro。"
        f"\n输入：{payload_json}"
    )


def _safe_research_points(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    points: list[dict[str, str]] = []
    for raw in value[:_MAX_POINTS_PER_DIMENSION]:
        if not isinstance(raw, Mapping):
            continue
        point: dict[str, str] = {}
        for key, limit in (
            ("claim", 180),
            ("support", 260),
            ("interpretation", 260),
            ("decision_implication", 260),
            ("caveat", 260),
        ):
            text = _safe_text(raw.get(key), limit=limit)
            if text:
                point[key] = text
        if point.get("claim") or point.get("support"):
            points.append(point)
    return points


def _parse_explanations(parsed: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if _contains_forbidden_output(parsed):
        raise ValueError("unsafe_model_output")
    raw_dimensions = parsed.get("dimensions")
    if not isinstance(raw_dimensions, list):
        raise ValueError("dimensions_missing")
    explanations: dict[str, dict[str, Any]] = {}
    for raw in raw_dimensions:
        if not isinstance(raw, Mapping):
            continue
        dimension = _safe_text(raw.get("dimension"), limit=20)
        if dimension not in DIMENSION_GROUPS:
            continue
        points = _safe_research_points(raw.get("research_points"))
        notes = [
            _safe_text(item, limit=180)
            for item in raw.get("notes", [])
            if _safe_text(item, limit=180)
        ] if isinstance(raw.get("notes"), list) else []
        if points or notes:
            explanations[dimension] = {
                "research_points": points,
                "notes": notes[:4],
            }
    if not explanations:
        raise ValueError("explanations_missing")
    return explanations


def _apply_explanations(
    dimension_results: Mapping[str, Any],
    explanations: Mapping[str, Mapping[str, Any]],
    *,
    model_name: str,
    provider_config: Mapping[str, Any],
) -> dict[str, Any]:
    updated: dict[str, Any] = {}
    for dimension, raw in dimension_results.items():
        result = dict(raw) if isinstance(raw, Mapping) else raw
        if not isinstance(result, dict):
            updated[str(dimension)] = result
            continue
        explanation = explanations.get(str(dimension))
        if not isinstance(explanation, Mapping):
            updated[str(dimension)] = result
            continue
        stable_before = {field: result.get(field) for field in _STABLE_FUSION_FIELDS if field in result}
        provenance = dict(result.get("provenance") or {})
        existing_points = provenance.get("research_points", [])
        merged_points = []
        if isinstance(explanation.get("research_points"), list):
            merged_points.extend(explanation["research_points"][:_MAX_POINTS_PER_DIMENSION])
        if isinstance(existing_points, list):
            merged_points.extend(existing_points[: max(0, 8 - len(merged_points))])
        if merged_points:
            provenance["research_points"] = merged_points[:8]
        provenance["llm_explanation"] = {
            "source": LLM_L3_EXPLANATION_SOURCE,
            "provider_invoked": True,
            "language_only": True,
            "fusion_fields_overridden": False,
            "model": _safe_text(model_name, limit=120),
            "provider": _safe_text(provider_config.get("provider"), limit=40),
            "notes": explanation.get("notes", [])[:4]
            if isinstance(explanation.get("notes"), list)
            else [],
        }
        raw_data_quality = provenance.get("data_quality")
        data_quality = dict(raw_data_quality) if isinstance(raw_data_quality, Mapping) else {}
        data_quality["llm_explanation_boundary"] = "language_only_no_fusion_override"
        provenance["data_quality"] = data_quality
        result["provenance"] = provenance
        for field, value in stable_before.items():
            result[field] = value
        valid, reason = validate_dimension_composite_result(result)
        if not valid:
            raise ValueError(f"invalid_dimension_after_explanation:{reason}")
        updated[str(dimension)] = result
    return updated


def _fallback_outcome(
    *,
    dimension_results: Mapping[str, Any],
    attempted: bool,
    provider_invoked: bool,
    reason: str,
    provider_config: Mapping[str, Any] | None = None,
) -> L3ExplanationOutcome:
    return {
        "dimension_results": {str(key): dict(value) if isinstance(value, Mapping) else value for key, value in dimension_results.items()},
        "used_llm_explanation": False,
        "attempted": attempted,
        "provider_invoked": provider_invoked,
        "fallback_reason": reason,
        "provider_config": dict(provider_config or {}),
    }


def synthesize_l3_explanations(
    *,
    question: str,
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
    context: Any,
) -> L3ExplanationOutcome:
    """Add bounded LLM explanations to L3 provenance behind an explicit flag."""
    model_name = str(
        getattr(context, "llm_l3_explanation_model", "")
        or getattr(context, "model", "")
        or "deepseek/deepseek-v4-flash"
    )
    config_status = provider_config_status(model_name)
    if config_status.get("preflight_status") in {"invalid_model_name", "missing_credential"}:
        return _fallback_outcome(
            dimension_results=dimension_results,
            attempted=True,
            provider_invoked=False,
            reason=f"provider_configuration_missing:{config_status['preflight_status']}",
            provider_config=config_status,
        )
    try:
        model = load_chat_model(model_name)
    except Exception:
        return _fallback_outcome(
            dimension_results=dimension_results,
            attempted=True,
            provider_invoked=False,
            reason="provider_configuration_missing:loader_error",
            provider_config={**config_status, "preflight_status": "loader_error"},
        )
    prompt = build_l3_explanation_prompt(
        question=question,
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
    )
    provider_invoked = True
    try:
        raw_text = _content_from_model_response(model.invoke(prompt))
        parsed = _json_object_from_text(raw_text)
        explanations = _parse_explanations(parsed)
        updated = _apply_explanations(
            dimension_results,
            explanations,
            model_name=model_name,
            provider_config=config_status,
        )
    except Exception as exc:
        return _fallback_outcome(
            dimension_results=dimension_results,
            attempted=True,
            provider_invoked=provider_invoked,
            reason=f"synthesis_failed:{type(exc).__name__}",
            provider_config=config_status,
        )
    return {
        "dimension_results": updated,
        "used_llm_explanation": True,
        "attempted": True,
        "provider_invoked": provider_invoked,
        "fallback_reason": "",
        "provider_config": config_status,
    }


__all__ = [
    "LLM_L3_EXPLANATION_SOURCE",
    "build_l3_explanation_prompt",
    "synthesize_l3_explanations",
]
