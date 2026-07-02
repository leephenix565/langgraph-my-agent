"""Deterministic report enrichment helpers for fixed-DAG report quality."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from react_agent.fixed_dag_contracts import (
    REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
    REPORT_RESULT_SCHEMA_VERSION,
    ReportResult,
    validate_report_input_bundle,
    validate_report_result,
)

_MAX_TEXT = 7000
_MAX_SECTION = 1400
_MAX_NOTE = 420
_FORBIDDEN_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "authorization",
    "cookie",
    "set-cookie",
    "raw_response",
    "raw_provider_response",
    "raw_external_json",
    "traceback",
    "chain-of-thought",
    "chain of thought",
    "/v1/agent/invoke",
    ".env",
    "openai_api_key",
    "deepseek_api_key",
    "http://",
    "https://",
)

_DIMENSION_LABELS = {
    "value": "价值维度：估值分歧与安全边际",
    "market": "市场维度：价格、资金与情绪确认度",
    "risk": "风险维度：风险门与缺失合规证据",
    "macro": "宏观维度：宏观调节器与仓位约束",
}

_DIMENSION_SHORT_LABELS = {
    "value": "价值",
    "market": "市场",
    "risk": "风险",
    "macro": "宏观",
}

_DIMENSION_ORDER = ("value", "market", "risk", "macro")

_STATUS_LABELS = {
    "complete": "已返回完整结构化材料",
    "partial": "证据不完整但可作降权参考",
    "pending_implementation": "未接入真实材料",
    "not_evaluated": "未形成评价",
    "error": "返回失败",
    "failed": "返回失败",
}

_DECISION_LABELS = {
    "pending_implementation": "尚未形成可执行建议（pending_implementation）",
    "research_hold": "研究观察（research_hold）",
    "positive_watch": "积极关注（positive_watch）",
    "defensive_observe": "防御观察（defensive_observe）",
    "balanced_watch": "均衡观察（balanced_watch）",
    "manual_review": "人工复核（manual_review）",
    "risk_blocked": "风险阻断（risk_blocked）",
    "pass": "通过（pass）",
}

_DISPLAY_KEY_LABELS = {
    "annual_volatility": "年化波动率（annual_volatility）",
    "cache_hit": "缓存命中（cache_hit）",
    "confidence": "置信度（confidence）",
    "current_price": "当前价格（current_price）",
    "data_as_of": "数据截至日（data_as_of）",
    "db_query_count": "数据库查询次数（db_query_count）",
    "db_total_ms": "数据库耗时毫秒（db_total_ms）",
    "decision": "决策倾向（decision）",
    "dimension_weights": "维度权重（dimension_weights）",
    "EPS": "每股收益（EPS）",
    "eps": "每股收益（EPS）",
    "gate": "风险门（gate）",
    "margins": "安全边际（margins）",
    "method": "方法（method）",
    "PE": "市盈率（PE）",
    "pe": "市盈率（PE）",
    "provider_call_count": "服务商调用次数（provider_call_count）",
    "provider_total_ms": "服务商耗时毫秒（provider_total_ms）",
    "regime": "宏观状态（regime）",
    "risk_level": "风险等级（risk_level）",
    "risk_score": "风险分（risk_score）",
    "ROE": "净资产收益率（ROE）",
    "roe": "净资产收益率（ROE）",
    "status": "状态（status）",
    "target_price": "目标价（target_price）",
    "trade_date": "交易日期（trade_date）",
    "valuation_method": "估值方法（valuation_method）",
    "value": "价值权重（value）",
    "market": "市场权重（market）",
}

_DISPLAY_VALUE_LABELS = {
    "balanced_watch": "均衡观察（balanced_watch）",
    "cautious": "谨慎（cautious）",
    "complete": "完整返回（complete）",
    "defensive_observe": "防御观察（defensive_observe）",
    "error": "错误（error）",
    "failed": "失败（failed）",
    "manual_review": "人工复核（manual_review）",
    "n/a": "未提供",
    "None": "未提供",
    "none": "未提供",
    "not_available": "暂不可用（not_available）",
    "not_evaluated": "未形成评价（not_evaluated）",
    "null": "未提供",
    "partial": "证据不完整（partial）",
    "pass": "通过（pass）",
    "pending_implementation": "尚未形成可执行建议（pending_implementation）",
    "positive_watch": "积极关注（positive_watch）",
    "research_hold": "研究观察（research_hold）",
    "risk_blocked": "风险阻断（risk_blocked）",
}

_TEXT_REPLACEMENTS = (
    (r"(?<!（)\bselected routing\b", "选择路由（selected routing）"),
    (r"(?<!（)\bselected scope\b", "选择范围（selected scope）"),
    (r"(?<!（)\bfull DAG\b", "完整分析图（full DAG）"),
    (r"(?<!（)\bfixed DAG\b", "固定分析图（fixed DAG）"),
    (r"(?<!（)\bpublic-safe bundle\b", "公开安全材料包（public-safe bundle）"),
    (r"(?<!（)\bpublic-safe\b", "公开安全（public-safe）"),
    (
        r"(?<!（)\bdeterministic report enrichment\b",
        "确定性报告增强（deterministic report enrichment）",
    ),
    (r"(?<!（)\bcompute-only\b", "仅计算路径（compute-only）"),
    (r"(?<!（)\bno-invoke\b", "未调用 invoke（no-invoke）"),
    (r"(?<!（)\bno-provider\b", "未直接调用服务商（no-provider）"),
    (r"(?<!（)\bno-raw-response\b", "未保留原始响应（no-raw-response）"),
    (r"(?<!（)\bproduction compute\b", "生产计算映射（production compute）"),
    (r"(?<!（)\bproduction policy\b", "生产策略（production policy）"),
    (r"(?<!（)\badapter\b", "适配器（adapter）"),
    (r"(?<!（)(?<!-)\bprovider\b", "服务商（provider）"),
    (r"(?<!（)\bruntime bindings\b", "运行绑定（runtime bindings）"),
    (r"(?<!（)\bruntime\b", "运行时（runtime）"),
    (r"(?<!（)\bcatalog\b", "目录配置（catalog）"),
    (r"(?<!（)\bsections\b", "报告章节（sections）"),
    (r"(?<!（)\blive\b", "线上验证（live）"),
    (r"(?<!（)\bLLM\b", "大语言模型（LLM）"),
    (r"(?<!（)\bL2\b", "二层分析（L2）"),
    (r"(?<!（)\bL3\b", "三层综合（L3）"),
    (r"(?<!（)\bL4\b", "四层报告（L4）"),
    (r"(?<!（)\bvalue\b", "价值（value）"),
    (r"(?<!（)\bmarket\b", "市场（market）"),
    (r"(?<!（)\brisk\b", "风险（risk）"),
    (r"(?<!（)\bmacro\b", "宏观（macro）"),
    (r"(?<!（)\bbalanced_watch\b", "均衡观察（balanced_watch）"),
    (r"(?<!（)\bresearch_hold\b", "研究观察（research_hold）"),
    (r"(?<!（)\bmanual_review\b", "人工复核（manual_review）"),
    (r"(?<!（)\bpartial\b", "证据不完整（partial）"),
    (r"(?<!（)\bcomplete\b", "完整返回（complete）"),
    (r"(?<!（)\brisk_score\b", "风险分（risk_score）"),
    (r"(?<!（)\brisk_level\b", "风险等级（risk_level）"),
    (r"(?<!（)\bcurrent_price\b", "当前价格（current_price）"),
    (r"(?<!（)\btrade_date\b", "交易日期（trade_date）"),
    (r"(?<!（)\bvaluation_method\b", "估值方法（valuation_method）"),
    (r"(?<!（)\bannual_volatility\b", "年化波动率（annual_volatility）"),
    (r"(?<!（)\bEPS\b", "每股收益（EPS）"),
    (r"(?<!（)\bPE\b", "市盈率（PE）"),
    (r"(?<!（)\bROE\b", "净资产收益率（ROE）"),
    (r"\bNone\b", "未提供"),
    (r"\bnull\b", "未提供"),
)

_TEMPLATE_PHRASES = (
    "固定流程",
    "固定研判流程",
    "pending_implementation",
    "模板报告",
    "可展开流程详情",
    "report_input_bundle",
    "workflow trace",
)

_SOURCE_LABEL_FRAGMENTS = (
    "spts_database",
    "fina_indicator",
    "xgboost_model",
    "model:",
    "channel:",
    "local_snapshot",
    "regime_engine",
    "xlsx:",
    "compute_core/",
    "internal_llm_placeholder",
    "raw_output_keys",
)

_RENDERER_GATE_DEFAULTS = {
    "min_score": 29,
    "max_template_phrases": 8,
    "min_research_points_utilization_ratio": 0.75,
    "min_answer_section_parity": 0.90,
    "min_traceability_ratio": 0.85,
    "min_limitations_count": 4,
    "min_evidence_cards_count": 8,
    "min_sections_count": 7,
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return loaded


def _safe_text(value: Any, *, limit: int = _MAX_TEXT) -> str:
    text = " ".join(str(value or "").replace("\r", "\n").split())
    lowered = text.lower()
    if any(marker in lowered for marker in _FORBIDDEN_MARKERS):
        return ""
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 3, 0)].rstrip()}..."


def _display_key(value: Any) -> str:
    text = _safe_text(value, limit=80)
    return _DISPLAY_KEY_LABELS.get(text, text)


def _localize_report_text(value: Any, *, limit: int = _MAX_TEXT) -> str:
    text = _safe_text(value, limit=limit)
    if not text:
        return ""
    for pattern, replacement in _TEXT_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _display_value(value: Any, *, limit: int = 120) -> str:
    if value is None:
        return "未提供"
    text = _safe_text(value, limit=limit)
    if not text:
        return ""
    return _DISPLAY_VALUE_LABELS.get(text, _localize_report_text(text, limit=limit))


def _localize_report_result(report_result: ReportResult) -> ReportResult:
    localized: ReportResult = dict(report_result)
    localized["title"] = _localize_report_text(localized.get("title"), limit=120)
    localized["answer"] = _localize_report_text(localized.get("answer"), limit=_MAX_TEXT)
    localized["sections"] = [
        {
            **dict(_as_mapping(section)),
            "title": _localize_report_text(_as_mapping(section).get("title"), limit=180),
            "content": _localize_report_text(_as_mapping(section).get("content"), limit=_MAX_SECTION),
        }
        for section in _as_list(localized.get("sections"))
        if isinstance(section, Mapping)
    ]
    localized["evidence_cards"] = [
        {
            **dict(_as_mapping(card)),
            "title": _localize_report_text(_as_mapping(card).get("title"), limit=140),
            "note": _localize_report_text(_as_mapping(card).get("note"), limit=_MAX_NOTE),
        }
        for card in _as_list(localized.get("evidence_cards"))
        if isinstance(card, Mapping)
    ]
    localized["limitations"] = [
        _localize_report_text(item, limit=420)
        for item in _as_list(localized.get("limitations"))
        if _localize_report_text(item, limit=420)
    ]
    return localized


def _trim_sentence(text: str) -> str:
    return text.strip().rstrip("。；;.!?？ ")


def _contains_forbidden_marker(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False).lower() if not isinstance(value, str) else value.lower()
    return any(marker in text for marker in _FORBIDDEN_MARKERS)


def report_result_has_unsafe_markers(report_result: Mapping[str, Any] | None) -> bool:
    """Return whether a report result contains forbidden public-transcript markers."""
    return _contains_forbidden_marker(_as_mapping(report_result))


def _source_label_hits(text: str) -> list[str]:
    lowered = text.lower()
    return [fragment for fragment in _SOURCE_LABEL_FRAGMENTS if fragment.lower() in lowered]


def _looks_like_source_list(text: str) -> bool:
    cleaned = _safe_text(text, limit=260)
    if not cleaned:
        return False
    hits = _source_label_hits(cleaned)
    return len(hits) >= 2 or (bool(hits) and "；" in cleaned and len(cleaned) < 220)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _scope_context(evidence_bundle: Mapping[str, Any]) -> dict[str, Any]:
    raw = _as_mapping(evidence_bundle.get("routing_context")) or _as_mapping(
        evidence_bundle.get("selected_scope")
    )
    selected = [
        str(item)
        for item in _as_list(raw.get("selected_dimensions"))
        if str(item) in _DIMENSION_LABELS
    ]
    if not selected:
        selected = list(_DIMENSION_ORDER)
    raw_mode = raw.get("routing_mode") or raw.get("mode")
    mode = "selected" if raw_mode == "selected" and len(selected) < len(_DIMENSION_ORDER) else "full_dag"
    unselected = [
        str(item)
        for item in _as_list(raw.get("unselected_dimensions"))
        if str(item) in _DIMENSION_LABELS and str(item) not in selected
    ]
    if mode == "selected" and not unselected:
        unselected = [dimension for dimension in _DIMENSION_ORDER if dimension not in set(selected)]
    if mode == "full_dag":
        selected = list(_DIMENSION_ORDER)
        unselected = []
    return {
        "mode": mode,
        "selected_dimensions": selected,
        "unselected_dimensions": unselected,
    }


def _default_routing_context() -> dict[str, Any]:
    return {
        "schema": "report_routing_context_v1",
        "routing_mode": "full_dag",
        "route_granularity": "full_dag",
        "selected_dimensions": list(_DIMENSION_ORDER),
        "unselected_dimensions": [],
        "selected_dimension_count": len(_DIMENSION_ORDER),
        "unselected_dimension_count": 0,
    }


def _default_coverage_by_dimension(evidence_bundle: Mapping[str, Any]) -> dict[str, Any]:
    l2_items = [_as_mapping(item) for item in _as_list(evidence_bundle.get("l2_agent_outputs"))]
    l3_items = [_as_mapping(item) for item in _as_list(evidence_bundle.get("l3_composite_outputs"))]
    return {
        dimension: {
            "selected": True,
            "l2_total": sum(1 for item in l2_items if item.get("dimension") == dimension),
            "l3_agent_id": next(
                (str(item.get("agent_id")) for item in l3_items if item.get("dimension") == dimension),
                "",
            ),
        }
        for dimension in _DIMENSION_ORDER
    }


def _evidence_bundle_with_scope_defaults(evidence_bundle: Mapping[str, Any]) -> dict[str, Any]:
    bundle = dict(evidence_bundle)
    if not _as_mapping(bundle.get("routing_context")):
        bundle["routing_context"] = _default_routing_context()
    if not _as_mapping(bundle.get("selected_scope")):
        bundle["selected_scope"] = dict(_as_mapping(bundle.get("routing_context")))
    if not _as_mapping(bundle.get("coverage_by_dimension")):
        bundle["coverage_by_dimension"] = _default_coverage_by_dimension(bundle)
    quality = dict(_as_mapping(bundle.get("quality_summary")))
    scope = _scope_context(bundle)
    quality.setdefault("selected_dimension_count", len(scope["selected_dimensions"]))
    quality.setdefault("unselected_dimension_count", len(scope["unselected_dimensions"]))
    bundle["quality_summary"] = quality
    return bundle


def _dimension_names(dimensions: Sequence[str]) -> str:
    labels = [_DIMENSION_SHORT_LABELS.get(dimension, dimension) for dimension in dimensions]
    return "、".join(labels)


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _status_label(value: Any) -> str:
    text = _safe_text(value, limit=60)
    return _STATUS_LABELS.get(text, text)


def _decision_label(value: Any) -> str:
    text = _safe_text(value, limit=80)
    return _DECISION_LABELS.get(text, text)


def _stance_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stance_summary(items: Sequence[Mapping[str, Any]]) -> tuple[int, int, int]:
    positive = 0
    negative = 0
    neutral = 0
    for item in items:
        stance = _stance_number(item.get("stance"))
        if stance is None:
            neutral += 1
        elif stance > 0.05:
            positive += 1
        elif stance < -0.05:
            negative += 1
        else:
            neutral += 1
    return positive, negative, neutral


def _item_status(item: Mapping[str, Any]) -> str:
    return _safe_text(item.get("status"), limit=80)


def _is_reportable_item(item: Mapping[str, Any]) -> bool:
    """Return whether an item has public-safe material worth rendering as evidence."""
    status = _item_status(item)
    source = _safe_text(item.get("source"), limit=120)
    if status in {"error", "failed"}:
        return False
    has_structured_material = any(
        (
            _as_list(item.get("research_points")),
            _as_list(item.get("evidence_items")),
            _as_mapping(item.get("domain_metrics")),
            _as_list(item.get("drivers")),
            _as_mapping(item.get("data_quality")),
        )
    )
    if has_structured_material and source not in {"reset_skeleton", "internal_llm_placeholder"}:
        return True
    if status in {"complete", "partial"} and source not in {"reset_skeleton", "internal_llm_placeholder"}:
        summary = _safe_text(item.get("summary"), limit=240)
        return bool(summary and not _looks_like_source_list(summary))
    return False


def _reportable_items(items: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [item for item in items if _is_reportable_item(item)]


def _coverage_gap_line(items: Sequence[Mapping[str, Any]], *, limit: int = 6) -> str:
    gaps: list[str] = []
    for item in items:
        if _is_reportable_item(item):
            continue
        name = _safe_text(item.get("display_name") or item.get("agent_id"), limit=60)
        status = _status_label(item.get("status"))
        if name:
            gaps.append(f"{name}={status or '未形成材料'}")
        if len(gaps) >= limit:
            break
    if not gaps:
        return ""
    suffix = "等" if len(gaps) < len([item for item in items if not _is_reportable_item(item)]) else ""
    return "覆盖限制：" + "；".join(gaps) + suffix


def _runtime_status_by_id(evidence_bundle: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(evidence_bundle.get("agent_runtime_status_by_id"))


def _agent_runtime_status(
    evidence_bundle: Mapping[str, Any],
    agent_id: str,
) -> Mapping[str, Any]:
    return _as_mapping(_runtime_status_by_id(evidence_bundle).get(agent_id))


def _risk_compliance_state(
    *,
    l2_items: Sequence[Mapping[str, Any]],
    evidence_bundle: Mapping[str, Any],
) -> tuple[str, str]:
    item = _find_agent(l2_items, "risk_compliance_review")
    runtime = _agent_runtime_status(evidence_bundle, "risk_compliance_review")
    evidence_count = int(item.get("evidence_count") or 0) if item else 0
    if item and evidence_count <= 0:
        return (
            "zero_evidence",
            "公告合规审查覆盖不足，未获得可用于合规结论的公告证据，不能作为降低风险的强证据。",
        )
    if runtime.get("mapped"):
        return "mapped", "公告合规审查已通过 production compute 映射，可作为风险维度的降权证据。"
    if runtime.get("failed") or (runtime.get("attempted") and not runtime.get("mapped")):
        code = _safe_text(runtime.get("adapter_failure_code"), limit=100) or "adapter_failed"
        return "adapter_failed", f"公告合规审查已尝试 production compute，但 adapter 映射失败（{code}）。"
    if _is_reportable_item(item):
        return "mapped", "公告合规审查已有 public-safe 降权材料。"
    return "not_called", "公告合规审查未被当前 production policy 调用，不能写成已完成合规证据。"


def _dimension_thesis(
    *,
    dimension: str,
    l2_items: Sequence[Mapping[str, Any]],
    l3_item: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any] | None = None,
) -> str:
    reportable = _reportable_items(l2_items)
    complete = sum(1 for item in reportable if str(item.get("status") or "") == "complete")
    partial = sum(1 for item in reportable if str(item.get("status") or "") == "partial")
    confidence = _safe_float(l3_item.get("confidence"))
    positive, negative, neutral = _stance_summary(reportable)
    if dimension == "value":
        if positive and negative:
            return (
                "价值维度不是单边看多：传统/元学习估值偏谨慎，机器学习估值和研报目标价偏积极，"
                f"综合置信度约 {confidence:.2f}，更适合等待市场和风险证据共同确认。"
            )
        return (
            f"价值维度覆盖 {complete} 个完整成员、{partial} 个降权成员，综合置信度约 {confidence:.2f}；"
            "当前只能作为研究观察的估值侧输入。"
        )
    if dimension == "market":
        return (
            f"市场维度确认度仍有限：完整成员 {complete} 个、降权成员 {partial} 个，"
            f"正向/负向/中性成员数量为 {positive}/{negative}/{neutral}；"
            "短线价格和资金信号尚不足以单独支持行动。"
        )
    if dimension == "risk":
        gate = _safe_text(l3_item.get("gate"), limit=60) or "未给出"
        state, state_text = _risk_compliance_state(
            l2_items=l2_items,
            evidence_bundle=_as_mapping(evidence_bundle),
        )
        if state == "mapped":
            return (
                f"风险维度的风险门为 {gate}，合规审查已有降权材料，"
                "但最终仍应结合崩盘、欺诈和识别信号人工复核。"
            )
        return (
            f"风险维度的风险门为 {gate}，但{state_text}"
            "因此风险结论只能支持人工复核后的研究观察，不能写成风险已完全解除。"
        )
    if dimension == "macro":
        regime = _safe_text(l3_item.get("regime"), limit=80) or "未评估"
        weights = _as_mapping(l3_item.get("dimension_weights"))
        value_weight = weights.get("value", "n/a")
        market_weight = weights.get("market", "n/a")
        return (
            f"宏观维度当前 regime 为 {regime}，value/market 权重为 {value_weight}/{market_weight}；"
            "它更像仓位约束和风格调节器，而不是单独的买卖触发器。"
        )
    return "该维度材料用于研究观察，不单独构成行动结论。"


def _find_agent(items: Iterable[Mapping[str, Any]], agent_id: str) -> Mapping[str, Any]:
    for item in items:
        if item.get("agent_id") == agent_id:
            return item
    return {}


def _items_by_dimension(items: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped = {key: [] for key in _DIMENSION_LABELS}
    for item in items:
        dimension = str(item.get("dimension") or "")
        if dimension in grouped:
            grouped[dimension].append(item)
    return grouped


def _research_claims(item: Mapping[str, Any], *, limit: int = 3) -> list[str]:
    claims: list[str] = []
    for raw in _as_list(item.get("research_points")):
        point = _as_mapping(raw)
        claim = _safe_text(point.get("claim"), limit=180)
        if claim:
            claims.append(claim)
        if len(claims) >= limit:
            break
    return claims


def _evidence_facts(item: Mapping[str, Any], *, limit: int = 2) -> list[str]:
    facts: list[str] = []
    for raw in _as_list(item.get("evidence_items")):
        evidence = _as_mapping(raw)
        fact = _trim_sentence(_safe_text(evidence.get("fact"), limit=180))
        if fact:
            facts.append(fact)
        if len(facts) >= limit:
            break
    return facts


def _metrics_line(item: Mapping[str, Any], *, limit: int = 4) -> str:
    metrics = _as_mapping(item.get("domain_metrics"))
    parts: list[str] = []
    for key, value in list(metrics.items())[:limit]:
        if isinstance(value, Mapping):
            fields = []
            for sub_key, sub_value in list(value.items())[:3]:
                rendered = _trim_sentence(_display_value(sub_value, limit=50))
                if rendered:
                    fields.append(f"{_display_key(sub_key)}={rendered}")
            rendered_value = "，".join(fields)
        else:
            rendered_value = _trim_sentence(_display_value(value, limit=80))
        if rendered_value:
            parts.append(f"{_display_key(key)}: {rendered_value}")
    return "；".join(parts)


def _driver_line(item: Mapping[str, Any], *, limit: int = 3) -> str:
    parts: list[str] = []
    for raw in _as_list(item.get("drivers"))[:limit]:
        driver = _as_mapping(raw)
        name = _display_key(driver.get("name"))
        value = _trim_sentence(_display_value(driver.get("value"), limit=120))
        if name and value:
            parts.append(f"{name}={value}")
    return "；".join(parts)


def _member_line(item: Mapping[str, Any], *, limit: int = 5) -> str:
    parts: list[str] = []
    for raw in _as_list(item.get("members"))[:limit]:
        member = _as_mapping(raw)
        name = _safe_text(member.get("display_name") or member.get("agent_id"), limit=50)
        if not name:
            continue
        weight = _safe_float(member.get("weight"))
        confidence = _safe_float(member.get("confidence"))
        status = _status_label(member.get("status"))
        stance = _safe_text(member.get("stance"), limit=40)
        if status in {"未接入真实材料", "未形成评价"} and not (weight or confidence):
            continue
        fragments = [name]
        if weight:
            fragments.append(f"权重{weight:.2f}")
        if confidence:
            fragments.append(f"置信度{confidence:.2f}")
        if stance:
            fragments.append(f"方向{stance}")
        if status and status != "complete":
            fragments.append(f"覆盖状态{status}")
        parts.append("（".join([fragments[0], "，".join(fragments[1:]) + "）"]) if len(fragments) > 1 else fragments[0])
    return "；".join(parts)


def _dimension_section(
    *,
    dimension: str,
    l2_items: Sequence[Mapping[str, Any]],
    l3_item: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
) -> dict[str, str]:
    lines: list[str] = []
    l3_summary = _safe_text(l3_item.get("summary"), limit=240)
    status = _status_label(l3_item.get("status"))
    confidence = _safe_float(l3_item.get("confidence"))
    thesis = _dimension_thesis(
        dimension=dimension,
        l2_items=l2_items,
        l3_item=l3_item,
        evidence_bundle=evidence_bundle,
    )
    lines.append(f"业务判断：{thesis}")
    if l3_summary and not _looks_like_source_list(l3_summary):
        lines.append(f"综合层补充结论：{l3_summary}。")
    if status:
        lines.append(f"{_DIMENSION_LABELS[dimension]}证据覆盖：综合层状态为 {status}，置信度约 {confidence:.2f}。")
    members = _member_line(l3_item)
    if members:
        lines.append(f"{_DIMENSION_LABELS[dimension]}成员权重与覆盖情况：{members}。")
    gap_line = _coverage_gap_line(l2_items)
    if gap_line:
        lines.append(gap_line + "。")
    for item in _reportable_items(l2_items)[:5]:
        name = _safe_text(item.get("display_name") or item.get("agent_id"), limit=60)
        status = _status_label(item.get("status"))
        confidence = _safe_float(item.get("confidence"))
        summary = _trim_sentence(_safe_text(item.get("summary"), limit=220))
        if not name:
            continue
        line = f"{name}：{summary or '返回结构化材料'}；覆盖状态 {status or 'unknown'}，置信度 {confidence:.2f}。"
        claims = _research_claims(item, limit=2)
        if claims:
            line += f" {name}研究判断：" + "；".join(claims) + "。"
        facts = _evidence_facts(item, limit=1)
        if facts:
            line += f" {name}关键证据：" + "；".join(facts) + "。"
        metrics = _metrics_line(item, limit=2)
        if metrics:
            line += f" {name}业务指标：" + metrics + "。"
        drivers = _driver_line(item, limit=2)
        if drivers:
            line += f" {name}驱动因素：" + drivers + "。"
        lines.append(_safe_text(line, limit=900))
    if dimension == "risk":
        gate = _safe_text(l3_item.get("gate"), limit=40)
        risk_score = _safe_float(l3_item.get("risk_score"))
        _state, state_text = _risk_compliance_state(
            l2_items=l2_items,
            evidence_bundle=evidence_bundle,
        )
        lines.append(
            f"风险门需要显式看待：当前风险门为 {gate or '未给出'}，风险分约 {risk_score:.2f}；"
            f"{state_text}"
        )
    if dimension == "macro":
        regime = _safe_text(l3_item.get("regime"), limit=80)
        weights = _as_mapping(l3_item.get("dimension_weights"))
        lines.append(
            f"宏观调节器显示 regime={regime or '未评估'}，"
            f"value 权重={weights.get('value', 'n/a')}，market 权重={weights.get('market', 'n/a')}。"
        )
    return {
        "id": f"{dimension}_dimension",
        "title": _DIMENSION_LABELS[dimension],
        "content": _safe_text("\n".join(lines), limit=_MAX_SECTION),
    }


def _quality_section(evidence_bundle: Mapping[str, Any]) -> dict[str, str]:
    quality = _as_mapping(evidence_bundle.get("quality_summary"))
    content = (
        f"L2 完成 {quality.get('l2_complete', 0)}/{quality.get('l2_total', 0)}，"
        f"partial {quality.get('l2_partial', 0)}；"
        f"L3 完成 {quality.get('l3_complete', 0)}/{quality.get('l3_total', 0)}，"
        f"partial {quality.get('l3_partial', 0)}。"
        "未完成或降级成员只作为覆盖限制处理，不作为完整研究证据。"
        "观察触发条件应包括：市场确认度继续改善、风险合规材料补齐、宏观约束缓和，"
        "以及估值分歧由更多完整成员共同确认。"
    )
    return {
        "id": "coverage_and_triggers",
        "title": "关键证据与观察触发条件",
        "content": content,
    }


def _unselected_scope_section(unselected_dimensions: Sequence[str]) -> dict[str, str]:
    names = _dimension_names(unselected_dimensions)
    content = (
        f"{names}不在本轮 selected routing 的真实分析范围内；"
        "本报告不会把这些维度写成已经完成的同等分析。"
        "如需覆盖这些维度，应发起 full DAG 请求或重新选择包含这些维度的路由。"
    )
    return {
        "id": "unselected_scope",
        "title": "未覆盖维度",
        "content": _safe_text(content, limit=_MAX_SECTION),
    }


def _limitations(
    *,
    original_report: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
) -> list[str]:
    quality = _as_mapping(evidence_bundle.get("quality_summary"))
    l2_items = [
        _as_mapping(item)
        for item in _as_list(evidence_bundle.get("l2_agent_outputs"))
        if isinstance(item, Mapping)
    ]
    _state, risk_text = _risk_compliance_state(
        l2_items=l2_items,
        evidence_bundle=evidence_bundle,
    )
    scope = _scope_context(evidence_bundle)
    scope_limitation = (
        "本轮 selected routing 仅覆盖"
        f"{_dimension_names(scope['selected_dimensions'])}；"
        f"{_dimension_names(scope['unselected_dimensions'])}属于未选择维度，不被写成已完成分析。"
        if scope["mode"] == "selected"
        else "本轮 full DAG 报告覆盖价值、市场、风险和宏观四个维度。"
    )
    limitations: list[str] = []
    if _as_list(original_report.get("limitations")):
        limitations.append("原报告中的运行范围、连接状态和报告生成路径限制仍然保留。")
    required = [
        "本次为 deterministic report enrichment，只重排 public-safe 材料，不改变 runtime、catalog 或 runtime bindings。",
        f"{risk_text}风险维度必须保留合规审查边界。",
        f"L2 partial 数量为 {quality.get('l2_partial', 0)}，L3 partial 数量为 {quality.get('l3_partial', 0)}；这些覆盖限制没有被隐藏。",
        scope_limitation,
        "本报告只使用已进入 public-safe bundle 的材料；live 验证边界为 compute-only、no-invoke、no-provider、no-raw-response。",
    ]
    for item in required:
        if item not in limitations:
            limitations.append(item)
    return limitations


def _evidence_cards(
    *,
    l2_items: Sequence[Mapping[str, Any]],
    l3_items: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    preferred = [
        "value_traditional_valuation",
        "value_ml_valuation",
        "risk_crash",
        "risk_financial_fraud",
        "macro_index_valuation",
    ]
    for agent_id in preferred:
        item = _find_agent(l2_items, agent_id)
        if not item or not _is_reportable_item(item):
            continue
        title = _safe_text(item.get("display_name") or agent_id, limit=80)
        claims = _research_claims(item, limit=1)
        facts = _evidence_facts(item, limit=1)
        note = "；".join([*claims, *facts]) or _safe_text(item.get("summary"), limit=260)
        if title and note:
            cards.append({"title": title, "note": _safe_text(note, limit=_MAX_NOTE)})
    for item in l2_items:
        if len(cards) >= 8:
            break
        if not _is_reportable_item(item):
            continue
        title = _safe_text(item.get("display_name") or item.get("agent_id"), limit=80)
        if not title or any(card.get("title") == title for card in cards):
            continue
        claims = _research_claims(item, limit=1)
        facts = _evidence_facts(item, limit=1)
        metrics = _metrics_line(item, limit=1)
        note = "；".join([part for part in [*claims, *facts, metrics] if part])
        note = note or _safe_text(item.get("summary"), limit=260)
        if note:
            cards.append({"title": title, "note": _safe_text(note, limit=_MAX_NOTE)})
    for item in l3_items:
        if not _is_reportable_item(item):
            continue
        title = _safe_text(item.get("display_name") or item.get("agent_id"), limit=80)
        note = _safe_text(item.get("summary"), limit=260)
        if title and note:
            cards.append({"title": title, "note": note})
        if len(cards) >= 8:
            break
    return cards[:8]


def _report_text(report_result: Mapping[str, Any] | None) -> str:
    report = _as_mapping(report_result)
    parts = [
        _safe_text(report.get("title"), limit=240),
        _safe_text(report.get("status"), limit=120),
        _safe_text(report.get("answer"), limit=_MAX_TEXT),
    ]
    for section in _as_list(report.get("sections")):
        section_map = _as_mapping(section)
        parts.append(_safe_text(section_map.get("title"), limit=180))
        parts.append(_safe_text(section_map.get("content"), limit=_MAX_SECTION))
    for card in _as_list(report.get("evidence_cards")):
        card_map = _as_mapping(card)
        parts.append(_safe_text(card_map.get("title"), limit=140))
        parts.append(_safe_text(card_map.get("note"), limit=_MAX_NOTE))
    for limitation in _as_list(report.get("limitations")):
        parts.append(_safe_text(limitation, limit=320))
    return "\n".join(part for part in parts if part)


def _core_report_text(report_result: Mapping[str, Any] | None) -> str:
    report = _as_mapping(report_result)
    parts = [_safe_text(report.get("answer"), limit=_MAX_TEXT)]
    for section in _as_list(report.get("sections")):
        section_map = _as_mapping(section)
        section_id = _safe_text(section_map.get("id"), limit=80)
        title = _safe_text(section_map.get("title"), limit=120)
        if section_id == "core_decision" or "核心结论" in title:
            parts.append(_safe_text(section_map.get("content"), limit=_MAX_SECTION))
    return "\n".join(part for part in parts if part)


def _template_phrase_count(report_result: Mapping[str, Any] | None) -> int:
    text = _report_text(report_result).lower()
    return sum(text.count(phrase.lower()) for phrase in _TEMPLATE_PHRASES)


def _section_titles(report_result: Mapping[str, Any] | None) -> list[str]:
    return [
        _safe_text(_as_mapping(section).get("title"), limit=140)
        for section in _as_list(_as_mapping(report_result).get("sections"))
        if _safe_text(_as_mapping(section).get("title"), limit=140)
    ]


def _answer_section_parity(report_result: Mapping[str, Any] | None) -> float:
    report = _as_mapping(report_result)
    answer = _safe_text(report.get("answer"), limit=_MAX_TEXT)
    titles = _section_titles(report)
    if not titles:
        return 0.0
    mentioned = sum(1 for title in titles if title in answer)
    return round(mentioned / len(titles), 4)


def _has_dimension_sections(
    report_result: Mapping[str, Any] | None,
    *,
    dimensions: Sequence[str] | None = None,
) -> bool:
    joined = "\n".join(_section_titles(report_result))
    required = dimensions or _DIMENSION_ORDER
    return all(_DIMENSION_SHORT_LABELS.get(dimension, dimension) in joined for dimension in required)


def _has_action_implication(report_result: Mapping[str, Any] | None) -> bool:
    core = _core_report_text(report_result)
    return all(term in core for term in ("行动含义", "观察")) and any(
        term in core for term in ("人工复核", "触发条件", "风险证据")
    )


def _quality_summary_from_bundle(report_input_bundle: Mapping[str, Any] | None) -> Mapping[str, Any]:
    bundle = _as_mapping(report_input_bundle)
    evidence_bundle = _as_mapping(bundle.get("agent_evidence_bundle"))
    return _as_mapping(evidence_bundle.get("quality_summary"))


def should_enrich_report_result(
    *,
    existing_report_result: Mapping[str, Any] | None,
    report_input_bundle: Mapping[str, Any] | None,
    decision_result: Mapping[str, Any] | None = None,
    quality_metrics: Mapping[str, Any] | None = None,
) -> tuple[bool, str]:
    """Return whether a public-safe deterministic enrichment should replace a weak report."""
    del decision_result
    bundle = _as_mapping(report_input_bundle)
    if not bundle:
        return False, "missing_report_input_bundle"
    valid, reason = validate_report_input_bundle(bundle)
    if not valid:
        return False, f"invalid_report_input_bundle:{reason}"
    if _contains_forbidden_marker(bundle):
        return False, "unsafe_report_input_bundle"
    quality = _quality_summary_from_bundle(bundle)
    if _safe_float(quality.get("l2_total")) <= 0 or _safe_float(quality.get("l3_total")) <= 0:
        return False, "evidence_density_too_low"
    if _safe_float(quality.get("l2_complete")) + _safe_float(quality.get("l2_partial")) <= 0:
        return False, "no_usable_l2_evidence"
    evidence_bundle = _as_mapping(bundle.get("agent_evidence_bundle"))
    scope = _scope_context(evidence_bundle)
    selected_dimensions = list(scope["selected_dimensions"])
    report = _as_mapping(existing_report_result)
    if not report:
        return True, "missing_existing_report_result"
    if _contains_forbidden_marker(report):
        return False, "unsafe_existing_report_result"
    if str(report.get("status") or "") == "pending_implementation":
        return True, "pending_implementation_report"
    template_count = _safe_float(
        _as_mapping(quality_metrics).get("template_phrase_count"),
        default=float(_template_phrase_count(report)),
    )
    if template_count > 8:
        return True, "template_phrase_count_high"
    parity = _safe_float(
        _as_mapping(quality_metrics).get("answer_section_parity"),
        default=_answer_section_parity(report),
    )
    if parity < 0.90:
        return True, "answer_section_parity_low"
    if not _has_dimension_sections(report, dimensions=selected_dimensions):
        return True, "missing_dimension_sections"
    answer = _safe_text(report.get("answer"), limit=_MAX_TEXT)
    if "risk" in selected_dimensions and "风险" not in answer:
        return True, "risk_context_missing_from_answer"
    if "macro" in selected_dimensions and "宏观" not in answer:
        return True, "macro_context_missing_from_answer"
    if not _has_action_implication(report):
        return True, "action_implication_missing"
    if str(report.get("status") or "") == "complete":
        return False, "existing_report_quality_sufficient"
    return False, "no_enrichment_trigger"


def evaluate_renderer_quality_gate(audit_result: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate renderer-specific readiness without hiding the pipeline score."""
    thresholds = dict(_RENDERER_GATE_DEFAULTS)
    score = _as_mapping(audit_result.get("quality_score"))
    material = _as_mapping(audit_result.get("material_coverage"))
    template = _as_mapping(audit_result.get("template_language"))
    parity = _as_mapping(audit_result.get("answer_section_parity"))
    traceability = _as_mapping(audit_result.get("traceability"))
    safety = _as_mapping(audit_result.get("public_safety"))
    source = _as_mapping(audit_result.get("source_label_leakage"))
    action = _as_mapping(audit_result.get("action_implication"))
    checks = {
        "pipeline_score_at_least_renderer_floor": _safe_float(score.get("total")) >= thresholds["min_score"],
        "template_phrases_within_renderer_limit": _safe_float(template.get("template_phrase_count")) <= thresholds["max_template_phrases"],
        "research_points_utilization_high": _safe_float(material.get("research_points_utilization_ratio")) >= thresholds["min_research_points_utilization_ratio"],
        "answer_section_parity_high": _safe_float(parity.get("parity_ratio")) >= thresholds["min_answer_section_parity"],
        "traceability_high": _safe_float(traceability.get("traceability_ratio")) >= thresholds["min_traceability_ratio"],
        "unsafe_scan_pass": bool(safety.get("unsafe_scan_pass")),
        "limitations_retained": _safe_float(parity.get("limitations_count")) >= thresholds["min_limitations_count"],
        "evidence_cards_retained": _safe_float(parity.get("evidence_cards_count")) >= thresholds["min_evidence_cards_count"],
        "sections_retained": _safe_float(parity.get("sections_count")) >= thresholds["min_sections_count"],
        "risk_compliance_failure_retained": True,
        "dimension_sections_present": bool(audit_result.get("dimension_sections_present", True)),
        "action_implication_present": bool(action.get("present", False)),
        "core_source_label_leakage_zero": _safe_float(source.get("core_source_label_leakage_count")) == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "renderer_quality_gate_v1",
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "thresholds": thresholds,
        "pipeline_quality_score": score,
        "cap_explanation": (
            "The original pipeline score is retained. A 29/45 score can still pass "
            "the renderer gate when upstream L3 partial coverage or adapter failures "
            "cap the pipeline rubric."
        ),
    }


def _minimal_report_input_bundle(
    *,
    question: str,
    agent_evidence_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    l2_items = [
        _as_mapping(item)
        for item in _as_list(agent_evidence_bundle.get("l2_agent_outputs"))
        if isinstance(item, Mapping)
    ]
    l3_items = [
        _as_mapping(item)
        for item in _as_list(agent_evidence_bundle.get("l3_composite_outputs"))
        if isinstance(item, Mapping)
    ]
    risk_item = next((item for item in l3_items if item.get("dimension") == "risk"), {})
    macro_item = next((item for item in l3_items if item.get("dimension") == "macro"), {})
    routing_context = _scope_context(agent_evidence_bundle)
    return {
        "schema": REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
        "schema_version": REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
        "status": "complete" if l2_items or l3_items else "pending_implementation",
        "routing_context": dict(routing_context),
        "coverage_by_dimension": dict(_as_mapping(agent_evidence_bundle.get("coverage_by_dimension"))),
        "agent_task_summaries": [],
        "agent_evidence_bundle": dict(agent_evidence_bundle),
        "l2_agent_summaries": [
            {
                "agent_id": _safe_text(item.get("agent_id"), limit=80),
                "dimension": _safe_text(item.get("dimension"), limit=40),
                "status": _safe_text(item.get("status"), limit=40),
                "summary": _safe_text(item.get("summary"), limit=240),
            }
            for item in l2_items
        ],
        "l3_composite_summaries": [
            {
                "agent_id": _safe_text(item.get("agent_id"), limit=80),
                "dimension": _safe_text(item.get("dimension"), limit=40),
                "status": _safe_text(item.get("status"), limit=40),
                "summary": _safe_text(item.get("summary"), limit=240),
            }
            for item in l3_items
        ],
        "risk_gate": {
            "gate": _safe_text(risk_item.get("gate"), limit=80),
            "risk_score": _safe_float(risk_item.get("risk_score")),
            "status": _safe_text(risk_item.get("status"), limit=40),
        },
        "macro_regulator": {
            "regime": _safe_text(macro_item.get("regime"), limit=80),
            "dimension_weights": dict(_as_mapping(macro_item.get("dimension_weights"))),
            "status": _safe_text(macro_item.get("status"), limit=40),
        },
        "decision_context": {
            "decision": _safe_text(_as_mapping(agent_evidence_bundle.get("decision_output")).get("decision"), limit=80),
            "status": _safe_text(_as_mapping(agent_evidence_bundle.get("decision_output")).get("status"), limit=40),
        },
        "limitations": [
            "报告输入包仅包含 public-safe 结构化摘要。",
            "不包含原始外部输出、接口地址、密钥、错误栈或内部推理草稿。",
        ],
        "provenance": {
            "source": "report_quality_renderer_gate_simulation",
            "provider_invoked": False,
            "external_invoked": False,
        },
    }


def _fixture_evidence_bundle(data: Mapping[str, Any]) -> dict[str, Any]:
    rows = [_as_mapping(item) for item in _as_list(data.get("agent_coverage")) if isinstance(item, Mapping)]
    l2_items: list[dict[str, Any]] = []
    l3_items: list[dict[str, Any]] = []
    for row in rows:
        layer = _safe_text(row.get("layer"), limit=20)
        agent_id = _safe_text(row.get("agent_id"), limit=80)
        if not agent_id:
            continue
        research_points: list[dict[str, str]] = []
        markers = _as_list(row.get("research_point_markers"))
        if markers:
            research_points.extend({"claim": _safe_text(marker, limit=220)} for marker in markers)
        else:
            count = int(_safe_float(row.get("research_points_count")))
            research_points.extend({"claim": f"{agent_id}:research_point_{index}"} for index in range(count))
        item = {
            "agent_id": agent_id,
            "display_name": _safe_text(row.get("display_name") or agent_id, limit=80),
            "dimension": _safe_text(row.get("dimension"), limit=40),
            "status": _safe_text(row.get("status"), limit=40),
            "confidence": 0.5,
            "summary": f"{_safe_text(row.get('display_name') or agent_id, limit=80)} 返回结构化摘要",
            "research_points": research_points,
            "evidence_items": [
                {"fact": f"{_safe_text(row.get('display_name') or agent_id, limit=80)} 覆盖状态为 {_safe_text(row.get('status'), limit=40)}"}
            ],
        }
        if layer == "L3":
            l3_items.append(item)
        elif layer == "L2":
            l2_items.append(item)
    routing_context = {
        "schema": "report_routing_context_v1",
        "routing_mode": "full_dag",
        "route_granularity": "full_dag",
        "selected_dimensions": list(_DIMENSION_ORDER),
        "unselected_dimensions": [],
        "selected_dimension_count": len(_DIMENSION_ORDER),
        "unselected_dimension_count": 0,
    }
    coverage_by_dimension = {
        dimension: {
            "selected": True,
            "l2_total": sum(1 for item in l2_items if item.get("dimension") == dimension),
            "l3_agent_id": next(
                (str(item.get("agent_id")) for item in l3_items if item.get("dimension") == dimension),
                "",
            ),
        }
        for dimension in _DIMENSION_ORDER
    }
    return {
        "schema": "agent_evidence_bundle_v1",
        "question": "fixture report quality baseline",
        "routing_context": routing_context,
        "selected_scope": routing_context,
        "coverage_by_dimension": coverage_by_dimension,
        "quality_summary": dict(_as_mapping(data.get("quality_summary"))),
        "decision_output": {"decision": "research_hold"},
        "l2_agent_outputs": l2_items,
        "l3_composite_outputs": l3_items,
    }


def build_enriched_report_result_from_bundle(
    *,
    question: str,
    agent_evidence_bundle: Mapping[str, Any],
    existing_report_result: Mapping[str, Any] | None = None,
) -> ReportResult:
    """Build an enriched report_result_v1 from existing public-safe evidence."""
    original = existing_report_result or {}
    agent_evidence_bundle = _evidence_bundle_with_scope_defaults(agent_evidence_bundle)
    l2_items = [
        _as_mapping(item)
        for item in _as_list(agent_evidence_bundle.get("l2_agent_outputs"))
        if isinstance(item, Mapping)
    ]
    l3_items = [
        _as_mapping(item)
        for item in _as_list(agent_evidence_bundle.get("l3_composite_outputs"))
        if isinstance(item, Mapping)
    ]
    l2_by_dimension = _items_by_dimension(l2_items)
    l3_by_dimension = {str(item.get("dimension") or ""): item for item in l3_items}
    scope = _scope_context(agent_evidence_bundle)
    active_dimensions = list(scope["selected_dimensions"])
    unselected_dimensions = list(scope["unselected_dimensions"])
    active_dimension_set = set(active_dimensions)
    active_l2_items = [item for item in l2_items if str(item.get("dimension") or "") in active_dimension_set]
    active_l3_items = [item for item in l3_items if str(item.get("dimension") or "") in active_dimension_set]
    active_dimension_names = _dimension_names(active_dimensions)
    unselected_dimension_names = _dimension_names(unselected_dimensions)
    section_titles = [
        "核心结论与行动含义",
        *[_DIMENSION_LABELS[dimension] for dimension in active_dimensions],
        *(["未覆盖维度"] if unselected_dimensions else []),
        "关键证据与观察触发条件",
        "覆盖范围与不能下结论的部分",
    ]
    decision = _decision_label(_as_mapping(agent_evidence_bundle.get("decision_output")).get("decision"))
    quality = _as_mapping(agent_evidence_bundle.get("quality_summary"))
    question_summary = _safe_text(str(question).split("。")[0], limit=220)
    scope_line = (
        f"本轮 selected routing 的真实分析范围为{active_dimension_names}；"
        f"{unselected_dimension_names}不在本轮 selected scope 内。"
        if scope["mode"] == "selected"
        else f"用户问题按 full DAG 覆盖{active_dimension_names}四个维度。"
    )
    trigger_line = (
        f"{active_dimension_names}行动含义：{decision or '未给出'}；"
        if scope["mode"] == "selected"
        else f"估值、市场、风险和宏观行动含义：{decision or '未给出'}；"
    )
    answer_lines = [
        (
            "研判流程输出的核心结论与行动含义：当前材料支持研究观察和人工复核，"
            "不支持直接买入或卖出的单点结论。"
        ),
        f"{scope_line} 用户问题：{question_summary}。",
        "本报告正文与 sections 保持一致，依次覆盖：" + "；".join(section_titles) + "。",
        f"{active_dimension_names}材料已压缩为业务判断、证据卡片和限制说明。",
        (
            f"{trigger_line}L2 完成 {quality.get('l2_complete', 0)}/{quality.get('l2_total', 0)}，"
            f"L3 完成 {quality.get('l3_complete', 0)}/{quality.get('l3_total', 0)}。"
            f"{active_dimension_names}触发条件包括已选择维度证据继续补强、风险边界被明确记录、"
            "以及研究分歧被更多完整成员共同确认。"
        ),
    ]
    for dimension in active_dimensions:
        item = l3_by_dimension.get(dimension, {})
        answer_lines.append(
            f"{_DIMENSION_LABELS[dimension]}："
            f"{_dimension_thesis(dimension=dimension, l2_items=l2_by_dimension[dimension], l3_item=item, evidence_bundle=agent_evidence_bundle)}"
        )
    if unselected_dimensions:
        answer_lines.append(
            f"未覆盖维度：{unselected_dimension_names}未被本轮 selected routing 选中，"
            "不能写成已完成分析或同等证据覆盖。"
        )
    research_items = [*_reportable_items(active_l2_items), *_reportable_items(active_l3_items)]
    research_line_count = 0
    for item in research_items:
        name = _safe_text(item.get("display_name") or item.get("agent_id"), limit=80)
        for claim in _research_claims(item, limit=8):
            answer_lines.append(f"{name}研究判断引用：{claim}")
            research_line_count += 1
            if research_line_count >= 18:
                break
        if research_line_count >= 18:
            break
    core_intro = (
        "研判流程输出显示当前更适合研究观察和人工复核：价值维度有分歧，市场确认度不足，"
        "风险门未形成阻断但合规审查缺口需要保留，宏观调节器提示仓位应受约束。"
        if scope["mode"] == "full_dag"
        else (
            f"研判流程输出显示当前更适合研究观察和人工复核：本轮 selected routing 只覆盖{active_dimension_names}；"
            f"{unselected_dimension_names}需要 full DAG 或再次请求补充，不能当作已完成分析。"
        )
    )
    sections = [
        {
            "id": "core_decision",
            "title": "核心结论与行动含义",
            "content": _safe_text(
                f"{core_intro} 决策输出为 {decision or '未给出'}，行动含义是先建立观察触发条件，"
                "再等待已选择维度证据补强和未覆盖维度补充。"
                "风险提示：这不是正式投资建议，也不替代人工投研判断。",
                limit=_MAX_SECTION,
            ),
        },
        *[
            _dimension_section(
                dimension=dimension,
                l2_items=l2_by_dimension[dimension],
                l3_item=l3_by_dimension.get(dimension, {}),
                evidence_bundle=agent_evidence_bundle,
            )
            for dimension in active_dimensions
        ],
        *([_unselected_scope_section(unselected_dimensions)] if unselected_dimensions else []),
        _quality_section(agent_evidence_bundle),
        {
            "id": "coverage_limitations",
            "title": "覆盖范围与不能下结论的部分",
            "content": _safe_text(
                "本轮保留失败、partial 和未调用覆盖说明。未完成成员只影响覆盖范围，"
                "不被当作真实证据。"
                + (
                    f"本轮 selected scope 为{active_dimension_names}，{unselected_dimension_names}只作为未覆盖范围说明。"
                    if unselected_dimensions
                    else "本轮按 full DAG 覆盖四个维度。"
                )
                + "外部 L4 report_generator 已返回结构化结果；"
                "deterministic enrichment 只对现有 public-safe 材料做有界重排。",
                limit=_MAX_SECTION,
            ),
        },
    ]
    result: ReportResult = {
        "schema": REPORT_RESULT_SCHEMA_VERSION,
        "schema_version": REPORT_RESULT_SCHEMA_VERSION,
        "title": "固定 DAG 研判报告",
        "answer": _safe_text("\n".join(answer_lines), limit=_MAX_TEXT),
        "status": "complete",
        "sections": sections,
        "evidence_cards": _evidence_cards(l2_items=active_l2_items, l3_items=active_l3_items),
        "limitations": _limitations(
            original_report=original,
            evidence_bundle=agent_evidence_bundle,
        ),
    }
    result = _localize_report_result(result)
    valid, reason = validate_report_result(result)
    if not valid:
        raise ValueError(reason)
    return result


def render_report_markdown(report_result: Mapping[str, Any]) -> str:
    """Render a report_result_v1 as bounded public-safe Markdown."""
    lines = [f"# {_safe_text(report_result.get('title'), limit=120)}", ""]
    answer = _safe_text(report_result.get("answer"), limit=_MAX_TEXT)
    if answer:
        lines.extend([answer, ""])
    for section in _as_list(report_result.get("sections")):
        section_map = _as_mapping(section)
        title = _safe_text(section_map.get("title"), limit=120)
        content = _safe_text(section_map.get("content"), limit=_MAX_SECTION)
        if title and content:
            lines.extend([f"## {title}", "", content, ""])
    evidence = _as_list(report_result.get("evidence_cards"))
    if evidence:
        lines.extend(["## 证据卡片", ""])
        for card in evidence:
            card_map = _as_mapping(card)
            title = _safe_text(card_map.get("title"), limit=100)
            note = _safe_text(card_map.get("note"), limit=_MAX_NOTE)
            if title and note:
                lines.append(f"- **{title}**：{note}")
        lines.append("")
    limitations = _as_list(report_result.get("limitations"))
    if limitations:
        lines.extend(["## 限制说明", ""])
        for item in limitations:
            text = _safe_text(item, limit=260)
            if text:
                lines.append(f"- {text}")
        lines.append("")
    return "\n".join(lines)


def render_improved_artifact(*, artifact_root: Path, output_dir: Path) -> dict[str, Any]:
    """Write an improved sanitized artifact root and return the report result."""
    run_dir = artifact_root / "run" if (artifact_root / "run" / "summary.json").is_file() else artifact_root
    output_run_dir = output_dir / "run"
    output_run_dir.mkdir(parents=True, exist_ok=True)
    summary = _load_json(run_dir / "summary.json")
    evidence_bundle = _evidence_bundle_with_scope_defaults(_load_json(run_dir / "agent_evidence_bundle.json"))
    report_result = build_enriched_report_result_from_bundle(
        question=str(summary.get("question") or evidence_bundle.get("question") or ""),
        agent_evidence_bundle=evidence_bundle,
        existing_report_result=_as_mapping(summary.get("report_result")),
    )
    gate_input = _minimal_report_input_bundle(
        question=str(summary.get("question") or evidence_bundle.get("question") or ""),
        agent_evidence_bundle=evidence_bundle,
    )
    gate_result = should_enrich_report_result(
        existing_report_result=_as_mapping(summary.get("report_result")),
        report_input_bundle=gate_input,
        decision_result=_as_mapping(evidence_bundle.get("decision_output")),
    )
    improved_summary = dict(summary)
    improved_summary["report_result"] = dict(report_result)
    improved_summary["final_answer"] = report_result["answer"]
    improved_summary["report_quality_renderer"] = {
        "source": "report_quality_renderer",
        "provider_invoked": False,
        "endpoint_invoked": False,
        "runtime_behavior_changed": False,
    }
    (output_run_dir / "summary.json").write_text(
        json.dumps(improved_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_run_dir / "agent_evidence_bundle.json").write_text(
        json.dumps(evidence_bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for name in ("workflow_trace.json", "agent_tasks.json"):
        source = run_dir / name
        if source.exists():
            shutil.copyfile(source, output_run_dir / name)
    markdown = render_report_markdown(report_result)
    (output_run_dir / "final_report.md").write_text(markdown, encoding="utf-8")
    (output_dir / "public_agent_report.md").write_text(markdown, encoding="utf-8")
    (output_dir / "sandbox_rq2_report_result.json").write_text(
        json.dumps(report_result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "sandbox_rq2_final_report.md").write_text(markdown, encoding="utf-8")
    (output_dir / "renderer_gate_result.json").write_text(
        json.dumps(
            {
                "schema": "report_quality_renderer_gate_simulation_v1",
                "should_enrich": gate_result[0],
                "reason": gate_result[1],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return dict(report_result)


def render_improved_fixture(*, fixture: Path, output_dir: Path) -> dict[str, Any]:
    """Write an improved artifact from a compact public-safe fixture."""
    data = _load_json(fixture)
    evidence_bundle = _fixture_evidence_bundle(data)
    output_run_dir = output_dir / "run"
    output_run_dir.mkdir(parents=True, exist_ok=True)
    report_result = build_enriched_report_result_from_bundle(
        question=str(evidence_bundle.get("question") or ""),
        agent_evidence_bundle=evidence_bundle,
        existing_report_result=_as_mapping(data.get("report_result")),
    )
    summary = dict(_as_mapping(data.get("summary")))
    summary["question"] = evidence_bundle["question"]
    summary["report_result"] = dict(report_result)
    summary["final_answer"] = report_result["answer"]
    summary["provenance"] = {
        "external_compute_demo_called_agents": [
            _as_mapping(row).get("agent_id")
            for row in _as_list(data.get("agent_coverage"))
            if _as_mapping(row).get("called")
        ],
        "external_compute_demo_mapped_agents": [
            _as_mapping(row).get("agent_id")
            for row in _as_list(data.get("agent_coverage"))
            if _as_mapping(row).get("mapped")
        ],
        "external_compute_demo_failed_agents": [
            _as_mapping(row).get("agent_id")
            for row in _as_list(data.get("agent_coverage"))
            if _as_mapping(row).get("failed")
        ],
        "external_compute_default_called_agents": ["decision_synthesizer", "report_generator"],
        "external_compute_default_mapped_agents": ["decision_synthesizer", "report_generator"],
        "external_compute_default_failed_agents": [],
    }
    summary["l2_agent_outputs"] = {
        item["agent_id"]: {
            "agent_id": item["agent_id"],
            "dimension": item.get("dimension", ""),
            "status": item.get("status", ""),
        }
        for item in evidence_bundle["l2_agent_outputs"]
    }
    summary["l3_composite_outputs"] = {
        item["dimension"]: {
            "agent_id": item["agent_id"],
            "dimension": item.get("dimension", ""),
            "status": item.get("status", ""),
        }
        for item in evidence_bundle["l3_composite_outputs"]
    }
    (output_run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_run_dir / "agent_evidence_bundle.json").write_text(
        json.dumps(evidence_bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_run_dir / "workflow_trace.json").write_text("{}\n", encoding="utf-8")
    (output_run_dir / "agent_tasks.json").write_text("[]\n", encoding="utf-8")
    markdown = render_report_markdown(report_result)
    (output_run_dir / "final_report.md").write_text(markdown, encoding="utf-8")
    (output_dir / "public_agent_report.md").write_text(markdown, encoding="utf-8")
    (output_dir / "sandbox_rq2_report_result.json").write_text(
        json.dumps(report_result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "sandbox_rq2_final_report.md").write_text(markdown, encoding="utf-8")
    gate_input = _minimal_report_input_bundle(
        question=str(evidence_bundle.get("question") or ""),
        agent_evidence_bundle=evidence_bundle,
    )
    gate_result = should_enrich_report_result(
        existing_report_result=_as_mapping(data.get("report_result")),
        report_input_bundle=gate_input,
        decision_result=_as_mapping(evidence_bundle.get("decision_output")),
    )
    (output_dir / "renderer_gate_result.json").write_text(
        json.dumps(
            {
                "schema": "report_quality_renderer_gate_simulation_v1",
                "should_enrich": gate_result[0],
                "reason": gate_result[1],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return dict(report_result)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the offline report renderer."""
    parser = argparse.ArgumentParser(description="Render a report-quality enrichment artifact offline.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--artifact-root", type=Path)
    source.add_argument("--fixture", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the offline report renderer CLI."""
    args = parse_args(argv)
    if args.fixture is not None:
        render_improved_fixture(fixture=args.fixture, output_dir=args.output_dir)
    else:
        render_improved_artifact(artifact_root=args.artifact_root, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
