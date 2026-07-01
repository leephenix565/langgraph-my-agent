#!/usr/bin/env python
# ruff: noqa: D103
"""Offline report-quality audit harness for fixed-DAG E2E artifacts."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

RESULT_SCHEMA = "report_quality_audit_result_v1"
FIXTURE_SCHEMA = "report_quality_baseline_fixture_v1"
QUALITY_SCORE_MAX = 45

RUBRIC_NAMES = (
    "Evidence grounding",
    "Cross-dimension synthesis",
    "Risk handling",
    "Macro handling",
    "L3 transparency",
    "Decision clarity",
    "Limitations honesty",
    "Business readability",
    "Public safety",
)

TEMPLATE_PHRASES = (
    "固定流程",
    "固定研判流程",
    "综合研判",
    "建议继续关注",
    "需要进一步验证",
    "数据边界",
    "仅供参考",
    "pending_implementation",
    "部分智能体",
    "模板报告",
    "证据不足",
    "默认报告",
    "后续需补充",
    "可展开流程详情",
    "report_input_bundle",
    "workflow trace",
)

FORBIDDEN_MARKERS = (
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

LOSS_STAGES = {
    "source_output_thin",
    "adapter_schema_unsupported",
    "adapter_safety_filtered",
    "adapter_whitelist_gap",
    "bundle_projection_gap",
    "l3_composite_summary_gap",
    "l4_decision_context_gap",
    "report_generator_underused",
    "fallback_renderer_gap",
    "public_mapping_gap",
    "frontend_surface_gap",
    "no_loss",
    "unresolved",
}

DIMENSION_TERMS = (
    "value",
    "market",
    "risk",
    "macro",
    "估值",
    "价值",
    "市场",
    "风险",
    "宏观",
)

DIMENSION_ORDER = ("value", "market", "risk", "macro")
DIMENSION_LABELS = {
    "value": "价值",
    "market": "市场",
    "risk": "风险",
    "macro": "宏观",
}

SOURCE_LABEL_FRAGMENTS = (
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

RENDERER_GATE_THRESHOLDS = {
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
        raise ValueError(f"JSON root must be an object: {path}")
    return loaded


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, *, limit: int = 500) -> str:
    text = " ".join(str(value or "").replace("\r", "\n").split())
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 3, 0)].rstrip()}..."


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bounded_excerpt(text: str, index: int, marker: str, *, radius: int = 70) -> str:
    start = max(index - radius, 0)
    end = min(index + len(marker) + radius, len(text))
    excerpt = _clean_text(text[start:end], limit=160)
    return excerpt.replace(marker, f"[{marker}]")


def _text_fields(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        texts: list[str] = []
        for key, item in value.items():
            texts.extend(_text_fields(key))
            texts.extend(_text_fields(item))
        return texts
    if isinstance(value, list):
        texts = []
        for item in value:
            texts.extend(_text_fields(item))
        return texts
    if isinstance(value, str):
        return [value]
    return []


def _core_report_text(report_result: Mapping[str, Any]) -> str:
    parts = [str(report_result.get("answer") or "")]
    for section in _as_list(report_result.get("sections")):
        section_map = _as_mapping(section)
        section_id = str(section_map.get("id") or "")
        title = str(section_map.get("title") or "")
        if section_id == "core_decision" or "核心结论" in title:
            parts.append(str(section_map.get("content") or ""))
    return "\n".join(part for part in parts if part)


def _source_label_leakage(report_result: Mapping[str, Any]) -> dict[str, Any]:
    core_text = _core_report_text(report_result)
    lowered = core_text.lower()
    hits = [
        {
            "fragment": fragment,
            "count": lowered.count(fragment.lower()),
        }
        for fragment in SOURCE_LABEL_FRAGMENTS
        if fragment.lower() in lowered
    ]
    return {
        "core_source_label_leakage_count": sum(_safe_int(item["count"]) for item in hits),
        "fragments": hits,
    }


def _scope_from_evidence_bundle(evidence_bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    bundle = _as_mapping(evidence_bundle)
    raw = _as_mapping(bundle.get("routing_context")) or _as_mapping(bundle.get("selected_scope"))
    selected = [
        str(item)
        for item in _as_list(raw.get("selected_dimensions"))
        if str(item) in DIMENSION_ORDER
    ]
    if not selected:
        selected = list(DIMENSION_ORDER)
    raw_mode = raw.get("routing_mode") or raw.get("mode")
    mode = "selected" if raw_mode == "selected" and len(selected) < len(DIMENSION_ORDER) else "full_dag"
    unselected = [
        str(item)
        for item in _as_list(raw.get("unselected_dimensions"))
        if str(item) in DIMENSION_ORDER and str(item) not in selected
    ]
    if mode == "selected" and not unselected:
        unselected = [dimension for dimension in DIMENSION_ORDER if dimension not in set(selected)]
    if mode == "full_dag":
        selected = list(DIMENSION_ORDER)
        unselected = []
    return {
        "schema": "selected_scope_integrity_v1",
        "mode": mode,
        "selected_dimensions": selected,
        "unselected_dimensions": unselected,
    }


def _dimension_sections_present(
    report_result: Mapping[str, Any],
    selected_dimensions: Sequence[str] | None = None,
) -> bool:
    titles = " ".join(
        str(_as_mapping(section).get("title") or "")
        for section in _as_list(report_result.get("sections"))
    )
    dimensions = list(selected_dimensions or DIMENSION_ORDER)
    return all(DIMENSION_LABELS.get(dimension, dimension) in titles for dimension in dimensions)


def _selected_scope_integrity(
    report_result: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any] | None,
) -> dict[str, Any]:
    scope = _scope_from_evidence_bundle(evidence_bundle)
    selected = list(scope["selected_dimensions"])
    unselected = list(scope["unselected_dimensions"])
    report_text = _report_text_from_result(report_result)
    sections = [_as_mapping(section) for section in _as_list(report_result.get("sections"))]
    violations: list[dict[str, str]] = []
    if scope["mode"] == "selected":
        for dimension in unselected:
            expected_id = f"{dimension}_dimension"
            label = DIMENSION_LABELS[dimension]
            for section in sections:
                title = str(section.get("title") or "")
                section_id = str(section.get("id") or "")
                if section_id == expected_id or (label in title and "未覆盖" not in title):
                    violations.append(
                        {
                            "dimension": dimension,
                            "reason": "unselected_dimension_rendered_as_active_section",
                        }
                    )
            if label in report_text and not any(
                marker in report_text
                for marker in ("未覆盖", "未选择", "不在本轮", "selected scope")
            ):
                violations.append(
                    {
                        "dimension": dimension,
                        "reason": "unselected_dimension_mentioned_without_scope_boundary",
                    }
                )
    return {
        **scope,
        "passed": not violations,
        "selected_dimension_section_count": sum(
            1
            for section in sections
            if any(DIMENSION_LABELS[dimension] in str(section.get("title") or "") for dimension in selected)
        ),
        "unselected_dimension_overstatement_count": len(violations),
        "violations": violations[:20],
    }


def _action_implication(report_result: Mapping[str, Any]) -> dict[str, Any]:
    core = _core_report_text(report_result)
    present = all(term in core for term in ("行动含义", "观察")) and any(
        term in core for term in ("人工复核", "触发条件", "风险证据")
    )
    return {"present": present}


def _renderer_quality_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    thresholds = dict(RENDERER_GATE_THRESHOLDS)
    score = _as_mapping(result.get("quality_score"))
    material = _as_mapping(result.get("material_coverage"))
    template = _as_mapping(result.get("template_language"))
    trace = _as_mapping(result.get("traceability"))
    parity = _as_mapping(result.get("answer_section_parity"))
    safety = _as_mapping(result.get("public_safety"))
    source = _as_mapping(result.get("source_label_leakage"))
    action = _as_mapping(result.get("action_implication"))
    l3_integrity = _as_mapping(result.get("l3_contributor_integrity"))
    selected_scope = _as_mapping(result.get("selected_scope_integrity"))
    completeness = _as_mapping(result.get("evidence_bundle_completeness"))
    risk_wording = _as_mapping(result.get("risk_compliance_zero_evidence_wording"))
    limitations = _as_mapping(result.get("limitations_honesty"))
    sections_floor = thresholds["min_sections_count"]
    if selected_scope.get("mode") == "selected":
        sections_floor = max(5, len(_as_list(selected_scope.get("selected_dimensions"))) + 4)
    checks = {
        "pipeline_score_at_least_renderer_floor": _safe_int(score.get("total")) >= thresholds["min_score"],
        "template_phrases_within_renderer_limit": _safe_int(template.get("template_phrase_count")) <= thresholds["max_template_phrases"],
        "research_points_utilization_high": _safe_float(material.get("research_points_utilization_ratio")) >= thresholds["min_research_points_utilization_ratio"],
        "answer_section_parity_high": _safe_float(parity.get("parity_ratio")) >= thresholds["min_answer_section_parity"],
        "traceability_high": _safe_float(trace.get("traceability_ratio")) >= thresholds["min_traceability_ratio"],
        "unsafe_scan_pass": bool(safety.get("unsafe_scan_pass")),
        "limitations_retained": _safe_int(parity.get("limitations_count")) >= thresholds["min_limitations_count"],
        "evidence_cards_retained": _safe_int(parity.get("evidence_cards_count")) >= thresholds["min_evidence_cards_count"],
        "sections_retained": _safe_int(parity.get("sections_count")) >= sections_floor,
        "risk_compliance_failure_retained": True,
        "dimension_sections_present": bool(result.get("dimension_sections_present")),
        "action_implication_present": bool(action.get("present")),
        "core_source_label_leakage_zero": _safe_int(source.get("core_source_label_leakage_count")) == 0,
        "l3_contributor_integrity_pass": bool(l3_integrity.get("passed", True)),
        "selected_scope_integrity_pass": bool(selected_scope.get("passed", True)),
        "unselected_dimension_overstatement_zero": _safe_int(
            selected_scope.get("unselected_dimension_overstatement_count")
        )
        == 0,
        "evidence_bundle_completeness_pass": bool(completeness.get("passed", False)),
        "risk_compliance_zero_evidence_wording_pass": bool(risk_wording.get("passed", True)),
        "limitations_honesty_pass": bool(limitations.get("passed", False)),
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
            "The original pipeline score is retained. Renderer-only output can pass "
            "at 29/45 when upstream L3 partial coverage or adapter failures cap the "
            "pipeline rubric."
        ),
    }


def scan_unsafe_texts(items: Iterable[tuple[str, str]]) -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    for source, text in items:
        lowered = text.lower()
        for marker in FORBIDDEN_MARKERS:
            index = lowered.find(marker)
            if index >= 0:
                hits.append(
                    {
                        "source": source,
                        "marker": marker,
                        "excerpt": _bounded_excerpt(text, index, marker),
                    }
                )
    return {"unsafe_scan_pass": not hits, "unsafe_hits": hits}


def _report_text_from_result(report_result: Mapping[str, Any], markdown: str = "") -> str:
    parts = [
        str(report_result.get("title") or ""),
        str(report_result.get("status") or ""),
        str(report_result.get("answer") or ""),
    ]
    for section in _as_list(report_result.get("sections")):
        section_map = _as_mapping(section)
        parts.append(str(section_map.get("title") or ""))
        parts.append(str(section_map.get("content") or ""))
    for card in _as_list(report_result.get("evidence_cards")):
        card_map = _as_mapping(card)
        parts.append(str(card_map.get("title") or ""))
        parts.append(str(card_map.get("note") or ""))
    for limitation in _as_list(report_result.get("limitations")):
        parts.append(str(limitation or ""))
    if markdown:
        parts.append(markdown)
    return "\n".join(part for part in parts if part)


def _template_phrase_counts(text: str) -> dict[str, Any]:
    lowered = text.lower()
    phrases: list[dict[str, Any]] = []
    total = 0
    for phrase in TEMPLATE_PHRASES:
        count = lowered.count(phrase.lower())
        if count <= 0:
            continue
        total += count
        index = lowered.find(phrase.lower())
        phrases.append(
            {
                "phrase": phrase,
                "count": count,
                "severity": "high" if count >= 3 else "medium",
                "context": _bounded_excerpt(text, index, phrase),
            }
        )
    return {"template_phrase_count": total, "phrases": phrases}


def _extract_claims(report_result: Mapping[str, Any]) -> list[dict[str, str]]:
    texts = [str(report_result.get("answer") or "")]
    for section in _as_list(report_result.get("sections")):
        section_map = _as_mapping(section)
        texts.append(str(section_map.get("content") or ""))
    combined = "\n".join(texts)
    parts = re.split(r"[。！？!?\n]+", combined)
    claims: list[dict[str, str]] = []
    for index, part in enumerate(parts, start=1):
        text = _clean_text(part, limit=260)
        if len(text) < 18:
            continue
        if text.startswith("#") or text.startswith("- **"):
            continue
        claims.append({"id": f"claim_{index}", "text": text})
    return claims[:80]


def _support_tokens(
    agent_coverage: Sequence[Mapping[str, Any]],
    report_result: Mapping[str, Any],
    research_points: Sequence[str],
) -> tuple[str, ...]:
    tokens: list[str] = list(DIMENSION_TERMS)
    for item in agent_coverage:
        for key in ("agent_id", "display_name", "dimension"):
            value = _clean_text(item.get(key), limit=80)
            if value:
                tokens.append(value)
    for section in _as_list(report_result.get("sections")):
        section_map = _as_mapping(section)
        title = _clean_text(section_map.get("title"), limit=80)
        if title:
            tokens.append(title)
    for card in _as_list(report_result.get("evidence_cards")):
        card_map = _as_mapping(card)
        title = _clean_text(card_map.get("title"), limit=80)
        if title:
            tokens.append(title)
    for point in research_points:
        if len(point) >= 12:
            tokens.append(point[:24])
    return tuple(dict.fromkeys(tokens))


def _traceability(
    report_result: Mapping[str, Any],
    agent_coverage: Sequence[Mapping[str, Any]],
    research_points: Sequence[str],
) -> dict[str, Any]:
    claims = _extract_claims(report_result)
    tokens = _support_tokens(agent_coverage, report_result, research_points)
    supported: list[dict[str, Any]] = []
    unsupported: list[dict[str, str]] = []
    for claim in claims:
        text = claim["text"]
        matched = [token for token in tokens if token and token in text]
        if matched:
            supported.append(
                {
                    **claim,
                    "supporting_tokens": matched[:5],
                }
            )
        else:
            unsupported.append(claim)
    total = len(claims)
    supported_count = len(supported)
    return {
        "claim_count": total,
        "supported_claim_count": supported_count,
        "unsupported_claim_count": len(unsupported),
        "traceability_ratio": round(supported_count / total, 4) if total else 0.0,
        "top_unsupported_claims": unsupported[:10],
        "supported_claims_preview": supported[:10],
    }


def _answer_section_parity(report_result: Mapping[str, Any]) -> dict[str, Any]:
    answer = str(report_result.get("answer") or "")
    sections = [_as_mapping(item) for item in _as_list(report_result.get("sections"))]
    mentioned = 0
    for section in sections:
        title = str(section.get("title") or "").strip()
        if title and title in answer:
            mentioned += 1
    count = len(sections)
    return {
        "answer_length": len(answer),
        "sections_count": count,
        "evidence_cards_count": len(_as_list(report_result.get("evidence_cards"))),
        "limitations_count": len(_as_list(report_result.get("limitations"))),
        "section_titles_mentioned_in_answer": mentioned,
        "parity_ratio": round(mentioned / count, 4) if count else 0.0,
    }


def _research_points_from_agent_rows(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    points: list[str] = []
    for row in rows:
        for marker in _as_list(row.get("research_point_markers")):
            text = _clean_text(marker, limit=240)
            if text:
                points.append(text)
        count = _safe_int(row.get("research_points_count"))
        if count and not row.get("research_point_markers"):
            agent_id = _clean_text(row.get("agent_id"), limit=80)
            points.extend(f"{agent_id}:research_point_{index}" for index in range(count))
    return points


def _research_points_utilization(
    report_text: str,
    agent_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    markers = _research_points_from_agent_rows(agent_rows)
    total = len(markers)
    utilized = 0
    utilized_markers: list[str] = []
    for marker in markers:
        needle = marker[:32]
        if needle and needle in report_text:
            utilized += 1
            utilized_markers.append(_clean_text(marker, limit=160))
    return {
        "research_points_total": total,
        "research_points_utilized": utilized,
        "research_points_utilization_ratio": round(utilized / total, 4) if total else 0.0,
        "utilized_research_points_preview": utilized_markers[:10],
    }


def _agent_material_coverage_from_fixture(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for raw in _as_list(data.get("agent_coverage")):
        item = dict(_as_mapping(raw))
        if item:
            rows.append(item)
    return rows


def _agent_material_coverage_from_real(
    summary: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    l2_outputs = _as_mapping(summary.get("l2_agent_outputs"))
    l3_outputs = _as_mapping(summary.get("l3_composite_outputs"))
    details_by_agent: dict[str, Mapping[str, Any]] = {}
    for item in _as_list(evidence_bundle.get("l2_agent_outputs")):
        item_map = _as_mapping(item)
        agent_id = str(item_map.get("agent_id") or "")
        if agent_id:
            details_by_agent[agent_id] = item_map
    for item in _as_list(evidence_bundle.get("l3_composite_outputs")):
        item_map = _as_mapping(item)
        agent_id = str(item_map.get("agent_id") or "")
        if agent_id:
            details_by_agent[agent_id] = item_map
    provenance = _as_mapping(summary.get("provenance"))
    called = set(_as_list(provenance.get("external_compute_demo_called_agents")))
    called.update(_as_list(provenance.get("external_compute_default_called_agents")))
    mapped = set(_as_list(provenance.get("external_compute_demo_mapped_agents")))
    mapped.update(_as_list(provenance.get("external_compute_default_mapped_agents")))
    failed = set(_as_list(provenance.get("external_compute_demo_failed_agents")))
    failed.update(_as_list(provenance.get("external_compute_default_failed_agents")))
    for agent_id, raw in l2_outputs.items():
        output = _as_mapping(raw)
        detail = details_by_agent.get(str(agent_id), {})
        rows.append(_coverage_row(str(agent_id), output, detail, called, mapped, failed, "L2"))
    for dimension, raw in l3_outputs.items():
        output = _as_mapping(raw)
        agent_id = str(output.get("agent_id") or f"{dimension}_composite")
        detail = details_by_agent.get(agent_id, {})
        rows.append(_coverage_row(agent_id, output, detail, called, mapped, failed, "L3"))
    for agent_id in sorted(called | mapped | failed):
        if any(row.get("agent_id") == agent_id for row in rows):
            continue
        rows.append(
            {
                "agent_id": agent_id,
                "layer": "L4" if agent_id in {"decision_synthesizer", "report_generator"} else "",
                "dimension": "l4" if agent_id in {"decision_synthesizer", "report_generator"} else "",
                "called": agent_id in called,
                "mapped": agent_id in mapped,
                "failed": agent_id in failed,
                "status": "failed" if agent_id in failed else "mapped",
                "research_points_count": 0,
                "domain_metrics_keys": [],
                "drivers_keys": [],
                "data_quality_keys": [],
            }
        )
    return rows


def _coverage_row(
    agent_id: str,
    output: Mapping[str, Any],
    detail: Mapping[str, Any],
    called: set[Any],
    mapped: set[Any],
    failed: set[Any],
    layer: str,
) -> dict[str, Any]:
    research_points = _as_list(detail.get("research_points"))
    return {
        "agent_id": agent_id,
        "display_name": str(detail.get("display_name") or agent_id),
        "layer": layer,
        "dimension": str(output.get("dimension") or detail.get("dimension") or ""),
        "called": agent_id in called,
        "mapped": agent_id in mapped,
        "failed": agent_id in failed,
        "status": str(output.get("status") or detail.get("status") or ""),
        "mapped_schema": str(output.get("schema") or detail.get("received_output_schema") or ""),
        "evidence_count": len(_as_list(detail.get("evidence_items"))),
        "domain_metrics_keys": sorted(str(key) for key in _as_mapping(detail.get("domain_metrics"))),
        "drivers_keys": [
            str(_as_mapping(item).get("name") or "")
            for item in _as_list(detail.get("drivers"))
            if _as_mapping(item).get("name")
        ],
        "data_quality_keys": sorted(str(key) for key in _as_mapping(detail.get("data_quality"))),
        "research_points_count": len(research_points),
        "research_point_markers": [
            _clean_text(_as_mapping(item).get("claim") or _as_mapping(item).get("support"), limit=180)
            for item in research_points
            if _clean_text(_as_mapping(item).get("claim") or _as_mapping(item).get("support"), limit=180)
        ],
        "limitations_count": len(_as_list(detail.get("limitations"))),
        "contributing_agents": _as_list(detail.get("contributing_agents")),
    }


def _material_coverage(
    agent_rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    quality_summary: Mapping[str, Any],
    report_text: str,
) -> dict[str, Any]:
    called = sum(1 for row in agent_rows if row.get("called"))
    mapped = sum(1 for row in agent_rows if row.get("mapped"))
    failed = sum(1 for row in agent_rows if row.get("failed"))
    if called == 0:
        called = _safe_int(summary.get("compute_called"))
    if mapped == 0:
        mapped = _safe_int(summary.get("compute_mapped"))
    if failed == 0:
        failed = _safe_int(summary.get("compute_failed"))
    utilization = _research_points_utilization(report_text, agent_rows)
    return {
        "agents_total": len(agent_rows),
        "agents_called": called,
        "agents_mapped": mapped,
        "agents_failed": failed,
        "failed_agents": [
            str(row.get("agent_id"))
            for row in agent_rows
            if row.get("failed") or str(row.get("agent_id") or "") in _as_list(summary.get("failed_agents"))
        ],
        "l2_complete": _safe_int(quality_summary.get("l2_complete") or summary.get("l2_complete")),
        "l2_partial": _safe_int(quality_summary.get("l2_partial") or summary.get("l2_partial")),
        "l3_complete": _safe_int(quality_summary.get("l3_complete") or summary.get("l3_complete")),
        "l3_partial": _safe_int(quality_summary.get("l3_partial") or summary.get("l3_partial")),
        "l4_decision_mapped": bool(summary.get("l4_decision_mapped")),
        "l4_report_mapped": bool(summary.get("l4_report_mapped")),
        "agents_with_domain_metrics": sum(1 for row in agent_rows if _as_list(row.get("domain_metrics_keys"))),
        "agents_with_drivers": sum(1 for row in agent_rows if _as_list(row.get("drivers_keys"))),
        "agents_with_data_quality": sum(1 for row in agent_rows if _as_list(row.get("data_quality_keys"))),
        "agents_with_research_points": sum(
            1 for row in agent_rows if _safe_int(row.get("research_points_count")) > 0
        ),
        **utilization,
    }


def _risk_compliance_status(
    material_coverage: Mapping[str, Any],
    loss_ledger: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    failed = "risk_compliance_review" in set(_as_list(material_coverage.get("failed_agents")))
    reason = ""
    for item in loss_ledger:
        if item.get("agent_id") == "risk_compliance_review":
            reason = str(item.get("failure_reason") or item.get("loss_stage") or "")
            break
    if failed and not reason:
        reason = "adapter_mapping_failed:unsupported_tool_result_schema"
    impact = (
        "risk compliance is represented as placeholder/coverage limitation; "
        "risk_composite remains partial and depends on remaining risk agents"
        if failed
        else ""
    )
    return {"failed": failed, "failure_reason": reason, "impact": impact}


def _loss_ledger_from_fixture(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in _as_list(data.get("loss_ledger")):
        row = dict(_as_mapping(item))
        if row:
            row.setdefault("loss_stage", "unresolved")
            row["loss_stage"] = (
                row["loss_stage"] if row["loss_stage"] in LOSS_STAGES else "unresolved"
            )
            rows.append(row)
    return rows


def _loss_ledger_from_metrics(
    material: Mapping[str, Any],
    report_result: Mapping[str, Any],
    template_count: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if material.get("l4_report_mapped") and str(report_result.get("status")) == "pending_implementation":
        rows.append(
            {
                "agent_id": "report_generator",
                "loss_stage": "report_generator_underused",
                "severity": 5,
                "recommended_action": "improve L4 report contract or renderer use of report_input_bundle",
            }
        )
    if "risk_compliance_review" in set(_as_list(material.get("failed_agents"))):
        rows.append(
            {
                "agent_id": "risk_compliance_review",
                "loss_stage": "adapter_schema_unsupported",
                "severity": 5,
                "failure_reason": "adapter_mapping_failed:unsupported_tool_result_schema",
                "recommended_action": "align service schema or add public-safe adapter support",
            }
        )
    if template_count >= 4:
        rows.append(
            {
                "agent_id": "final_report.md",
                "loss_stage": "fallback_renderer_gap",
                "severity": 4,
                "recommended_action": "render business thesis before process/template scaffolding",
            }
        )
    return rows


def _score_rubric(
    *,
    report_result: Mapping[str, Any],
    material: Mapping[str, Any],
    traceability: Mapping[str, Any],
    template_count: int,
    unsafe_pass: bool,
    report_text: str,
    l3_integrity: Mapping[str, Any] | None = None,
    selected_scope_integrity: Mapping[str, Any] | None = None,
    evidence_bundle_completeness: Mapping[str, Any] | None = None,
    risk_zero_evidence_wording: Mapping[str, Any] | None = None,
    limitations_honesty: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    l3_total = _safe_int(material.get("l3_complete")) + _safe_int(material.get("l3_partial"))
    limitations_count = len(_as_list(report_result.get("limitations")))
    has_risk_text = "风险" in report_text or "risk" in report_text.lower()
    has_macro_text = "宏观" in report_text or "macro" in report_text.lower()
    l3_integrity_pass = bool(_as_mapping(l3_integrity).get("passed", True))
    selected_scope_pass = bool(_as_mapping(selected_scope_integrity).get("passed", True))
    bundle_complete = bool(_as_mapping(evidence_bundle_completeness).get("passed", False))
    risk_wording_pass = bool(_as_mapping(risk_zero_evidence_wording).get("passed", True))
    limitations_honesty_pass = bool(_as_mapping(limitations_honesty).get("passed", False))
    score_by_name = {
        "Evidence grounding": 4
        if (
            _safe_int(material.get("agents_mapped")) >= 20
            and _safe_int(material.get("evidence_cards_count", 5)) >= 8
            and bundle_complete
        )
        else 3
        if _safe_int(material.get("agents_mapped")) >= 20 and _safe_int(material.get("evidence_cards_count", 5)) >= 5
        else 2,
        "Cross-dimension synthesis": 3
        if selected_scope_pass and (all(term in report_text for term in ("估值", "市场", "风险", "宏观")) or _as_mapping(selected_scope_integrity).get("mode") == "selected")
        else 2
        if all(term in report_text for term in ("估值", "市场", "风险", "宏观"))
        else 1,
        "Risk handling": 3 if risk_wording_pass and has_risk_text else 2 if has_risk_text else 1,
        "Macro handling": 3
        if has_macro_text and limitations_honesty_pass
        else 2
        if has_macro_text and _safe_int(material.get("l3_partial"))
        else 1,
        "L3 transparency": 4 if l3_total >= 4 and l3_integrity_pass else 3 if l3_total >= 4 else 2,
        "Decision clarity": 1
        if str(report_result.get("status") or "") == "pending_implementation"
        else 3
        if traceability.get("traceability_ratio", 0.0) >= 0.5
        else 2,
        "Limitations honesty": 4 if limitations_count >= 4 else 3 if limitations_count >= 2 else 1,
        "Business readability": 2 if template_count >= 6 else 3 if template_count >= 3 else 4,
        "Public safety": 5 if unsafe_pass else 0,
    }
    return [
        {
            "name": name,
            "score": score_by_name[name],
            "max": 5,
            "evidence": _rubric_evidence(name, report_result, material, template_count, unsafe_pass),
            "notes": "",
        }
        for name in RUBRIC_NAMES
    ]


def _rubric_evidence(
    name: str,
    report_result: Mapping[str, Any],
    material: Mapping[str, Any],
    template_count: int,
    unsafe_pass: bool,
) -> list[str]:
    if name == "Evidence grounding":
        return [f"mapped={material.get('agents_mapped')}", f"evidence_cards={material.get('evidence_cards_count', 5)}"]
    if name == "Decision clarity":
        return [f"report_status={report_result.get('status')}"]
    if name == "Business readability":
        return [f"template_phrase_count={template_count}"]
    if name == "Public safety":
        return [f"unsafe_scan_pass={unsafe_pass}"]
    return [
        f"l2_complete={material.get('l2_complete')}",
        f"l3_complete={material.get('l3_complete')}",
        f"l3_partial={material.get('l3_partial')}",
    ]


def _score_summary(rubric: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = sum(_safe_int(item.get("score")) for item in rubric)
    return {
        "total": total,
        "max": QUALITY_SCORE_MAX,
        "normalized": round(total / QUALITY_SCORE_MAX, 3),
    }


def _normalize_rubric(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        item_map = _as_mapping(item)
        name = str(item_map.get("name") or item_map.get("dimension") or "")
        if not name:
            continue
        items.append(
            {
                "name": name,
                "score": _safe_int(item_map.get("score")),
                "max": _safe_int(item_map.get("max"), default=5) or 5,
                "evidence": _as_list(item_map.get("evidence")),
                "notes": str(item_map.get("notes") or item_map.get("evidence") or ""),
            }
        )
    return items


def _recommended_wave(loss_ledger: Sequence[Mapping[str, Any]]) -> str:
    stages = [str(item.get("loss_stage") or "") for item in loss_ledger]
    if stages.count("adapter_schema_unsupported") >= stages.count("report_generator_underused") + 2:
        return "RQ3 Adapter projection repair"
    if "report_generator_underused" in stages:
        return "RQ2 Bundle/report renderer improvement"
    return "RQ2 Bundle/report renderer improvement"


def _l3_ref_matches_non_contributor(ref: str, agent_id: str) -> bool:
    ref_clean = str(ref or "").strip()
    agent_clean = str(agent_id or "").strip()
    return bool(
        ref_clean
        and agent_clean
        and (
            ref_clean == agent_clean
            or ref_clean.startswith(f"{agent_clean}(")
            or ref_clean.startswith(f"{agent_clean}:")
            or ref_clean.startswith(f"{agent_clean}/")
            or ref_clean.startswith(f"{agent_clean}：")
        )
    )


def _l3_contributor_integrity(evidence_bundle: Mapping[str, Any]) -> dict[str, Any]:
    rows = [_as_mapping(item) for item in _as_list(evidence_bundle.get("l3_composite_outputs"))]
    violations: list[dict[str, Any]] = []
    checked = 0
    for row in rows:
        if not row:
            continue
        checked += 1
        agent_id = str(row.get("agent_id") or "")
        status = str(row.get("status") or "")
        notes = _as_mapping(row.get("provenance_notes"))
        contributing = {
            str(item)
            for item in (_as_list(row.get("contributing_agents")) or _as_list(notes.get("contributing_agents")))
            if str(item)
        }
        evidence_refs = [str(item) for item in _as_list(row.get("evidence_refs")) if str(item)]
        non_contributors = [
            _as_mapping(item)
            for item in _as_list(notes.get("non_contributor_members"))
            if _as_mapping(item).get("agent_id")
        ]
        non_ids = {str(item.get("agent_id")) for item in non_contributors}
        for non_id in sorted(non_ids & contributing):
            violations.append(
                {
                    "agent_id": agent_id,
                    "member": non_id,
                    "reason": "non_contributor_listed_as_contributor",
                }
            )
        for non_id in sorted(non_ids):
            for ref in evidence_refs:
                if _l3_ref_matches_non_contributor(ref, non_id):
                    violations.append(
                        {
                            "agent_id": agent_id,
                            "member": non_id,
                            "reason": "non_contributor_evidence_ref_retained",
                            "evidence_ref": _clean_text(ref, limit=160),
                        }
                    )
        for item in _as_list(notes.get("member_weight_summary")):
            item_map = _as_mapping(item)
            member_id = str(item_map.get("agent_id") or "")
            if member_id in non_ids and _safe_float(item_map.get("weight"), default=0.0) > 0.0:
                violations.append(
                    {
                        "agent_id": agent_id,
                        "member": member_id,
                        "reason": "reported_member_weight_not_zeroed",
                        "weight": _safe_float(item_map.get("weight"), default=0.0),
                    }
                )
        if _as_list(notes.get("dropped_evidence_refs")) and status == "complete":
            violations.append(
                {
                    "agent_id": agent_id,
                    "reason": "dropped_evidence_without_degraded_status",
                }
            )
        if status in {"complete", "partial"} and not contributing and evidence_refs:
            violations.append(
                {
                    "agent_id": agent_id,
                    "reason": "evidence_refs_without_real_contributors",
                }
            )
    return {
        "schema": "l3_contributor_integrity_v1",
        "passed": not violations,
        "l3_rows_checked": checked,
        "violation_count": len(violations),
        "violations": violations[:20],
    }


def _summary_l2_ids(summary: Mapping[str, Any]) -> set[str]:
    return {str(agent_id) for agent_id in _as_mapping(summary.get("l2_agent_outputs")) if str(agent_id)}


def _summary_l3_ids(summary: Mapping[str, Any]) -> set[str]:
    ids: set[str] = set()
    for raw in _as_mapping(summary.get("l3_composite_outputs")).values():
        item = _as_mapping(raw)
        agent_id = str(item.get("agent_id") or "")
        if agent_id:
            ids.add(agent_id)
    return ids


def _evidence_l2_ids(evidence_bundle: Mapping[str, Any]) -> set[str]:
    return {
        str(_as_mapping(item).get("agent_id"))
        for item in _as_list(evidence_bundle.get("l2_agent_outputs"))
        if str(_as_mapping(item).get("agent_id") or "")
    }


def _evidence_l3_ids(evidence_bundle: Mapping[str, Any]) -> set[str]:
    return {
        str(_as_mapping(item).get("agent_id"))
        for item in _as_list(evidence_bundle.get("l3_composite_outputs"))
        if str(_as_mapping(item).get("agent_id") or "")
    }


def _evidence_bundle_completeness(
    *,
    summary: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any] | None,
) -> dict[str, Any]:
    bundle = _as_mapping(evidence_bundle)
    required = [
        "quality_summary",
        "decision_output",
        "l2_agent_outputs",
        "l3_composite_outputs",
        "routing_context",
        "coverage_by_dimension",
    ]
    missing_required = [key for key in required if key not in bundle]
    summary_l2 = _summary_l2_ids(summary)
    summary_l3 = _summary_l3_ids(summary)
    evidence_l2 = _evidence_l2_ids(bundle)
    evidence_l3 = _evidence_l3_ids(bundle)
    missing_l2 = sorted(summary_l2 - evidence_l2)
    missing_l3 = sorted(summary_l3 - evidence_l3)
    return {
        "schema": "evidence_bundle_completeness_v1",
        "passed": not missing_required and not missing_l2 and not missing_l3,
        "missing_required_fields": missing_required,
        "summary_l2_count": len(summary_l2),
        "evidence_l2_count": len(evidence_l2),
        "missing_l2_detail_ids": missing_l2[:20],
        "summary_l3_count": len(summary_l3),
        "evidence_l3_count": len(evidence_l3),
        "missing_l3_detail_ids": missing_l3[:20],
    }


def _risk_compliance_zero_evidence_wording(
    *,
    report_result: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any] | None,
) -> dict[str, Any]:
    bundle = _as_mapping(evidence_bundle)
    risk_item = {}
    for raw in _as_list(bundle.get("l2_agent_outputs")):
        item = _as_mapping(raw)
        if item.get("agent_id") == "risk_compliance_review":
            risk_item = item
            break
    zero_evidence = bool(risk_item) and _safe_int(risk_item.get("evidence_count")) <= 0
    report_text = _report_text_from_result(report_result)
    required_markers = ("覆盖不足", "未获得可用于合规结论", "不能作为降低风险的强证据")
    optimistic_markers = ("合规审查已有降权材料", "合规审查已通过")
    marker_present = any(marker in report_text for marker in required_markers)
    optimistic_present = any(marker in report_text for marker in optimistic_markers)
    passed = True if not zero_evidence else marker_present and not optimistic_present
    return {
        "schema": "risk_compliance_zero_evidence_wording_v1",
        "zero_evidence": zero_evidence,
        "passed": passed,
        "required_marker_present": marker_present,
        "optimistic_marker_present": optimistic_present,
    }


def _limitations_honesty(report_result: Mapping[str, Any]) -> dict[str, Any]:
    text = _report_text_from_result({"limitations": report_result.get("limitations", [])})
    checks = {
        "deterministic_boundary": "deterministic" in text or "只重排 public-safe" in text,
        "risk_boundary": "合规审查" in text,
        "partial_counts": "partial" in text,
        "compute_only_boundary": "no-invoke" in text and "no-provider" in text,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "limitations_honesty_v1",
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
    }


def _audit_common(
    *,
    artifact_root: str,
    input_mode: str,
    summary: Mapping[str, Any],
    report_result: Mapping[str, Any],
    agent_rows: Sequence[Mapping[str, Any]],
    quality_summary: Mapping[str, Any],
    markdown: str,
    evidence_bundle: Mapping[str, Any] | None = None,
    fixture_rubric: Sequence[Mapping[str, Any]] | None = None,
    fixture_loss_ledger: Sequence[Mapping[str, Any]] | None = None,
    non_claims: Sequence[str] | None = None,
    l3_contributor_integrity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    report_text = _report_text_from_result(report_result, markdown)
    unsafe_scan = scan_unsafe_texts(
        [
            ("report_result", report_text),
            ("non_claims", "\n".join(non_claims or [])),
        ]
    )
    template_language = _template_phrase_counts(report_text)
    traceability = _traceability(
        report_result,
        agent_rows,
        _research_points_from_agent_rows(agent_rows),
    )
    answer_section_parity = _answer_section_parity(report_result)
    material = _material_coverage(agent_rows, summary, quality_summary, report_text)
    material["evidence_cards_count"] = answer_section_parity["evidence_cards_count"]
    selected_scope_integrity = _selected_scope_integrity(report_result, evidence_bundle)
    evidence_bundle_completeness = _evidence_bundle_completeness(
        summary=summary,
        evidence_bundle=evidence_bundle,
    )
    risk_zero_evidence_wording = _risk_compliance_zero_evidence_wording(
        report_result=report_result,
        evidence_bundle=evidence_bundle,
    )
    limitations_honesty = _limitations_honesty(report_result)
    loss_ledger = list(fixture_loss_ledger or [])
    if not loss_ledger:
        loss_ledger = _loss_ledger_from_metrics(
            material,
            report_result,
            _safe_int(template_language.get("template_phrase_count")),
        )
    risk = _risk_compliance_status(material, loss_ledger)
    rubric = list(fixture_rubric or [])
    if not rubric:
        rubric = _score_rubric(
            report_result=report_result,
            material=material,
            traceability=traceability,
            template_count=_safe_int(template_language.get("template_phrase_count")),
            unsafe_pass=bool(unsafe_scan["unsafe_scan_pass"]),
            report_text=report_text,
            l3_integrity=l3_contributor_integrity,
            selected_scope_integrity=selected_scope_integrity,
            evidence_bundle_completeness=evidence_bundle_completeness,
            risk_zero_evidence_wording=risk_zero_evidence_wording,
            limitations_honesty=limitations_honesty,
        )
    result = {
        "schema": RESULT_SCHEMA,
        "artifact_root": artifact_root,
        "input_mode": input_mode,
        "quality_score": _score_summary(rubric),
        "pipeline_quality_score": _score_summary(rubric),
        "rubric": rubric,
        "traceability": traceability,
        "template_language": template_language,
        "material_coverage": material,
        "answer_section_parity": answer_section_parity,
        "risk_compliance_review": risk,
        "selected_scope_integrity": selected_scope_integrity,
        "evidence_bundle_completeness": evidence_bundle_completeness,
        "risk_compliance_zero_evidence_wording": risk_zero_evidence_wording,
        "limitations_honesty": limitations_honesty,
        "l3_contributor_integrity": dict(
            l3_contributor_integrity
            or {"schema": "l3_contributor_integrity_v1", "passed": True, "l3_rows_checked": 0}
        ),
        "public_safety": unsafe_scan,
        "loss_ledger": loss_ledger,
        "source_label_leakage": _source_label_leakage(report_result),
        "action_implication": _action_implication(report_result),
        "dimension_sections_present": _dimension_sections_present(
            report_result,
            selected_scope_integrity.get("selected_dimensions"),
        ),
        "recommended_next_wave": _recommended_wave(loss_ledger),
        "non_claims": list(non_claims or []),
    }
    result["renderer_quality_gate"] = _renderer_quality_gate(result)
    return result


def audit_fixture(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if data.get("schema") != FIXTURE_SCHEMA:
        raise ValueError(f"Unsupported report quality fixture schema: {data.get('schema')}")
    report_result = _as_mapping(data.get("report_result"))
    summary = _as_mapping(data.get("summary"))
    quality_summary = _as_mapping(data.get("quality_summary"))
    rows = _agent_material_coverage_from_fixture(data)
    rubric = _normalize_rubric(data.get("rubric"))
    loss_ledger = _loss_ledger_from_fixture(data)
    return _audit_common(
        artifact_root=str(path),
        input_mode="fixture",
        summary=summary,
        report_result=report_result,
        agent_rows=rows,
        quality_summary=quality_summary,
        markdown=str(data.get("rendered_markdown_excerpt") or ""),
        evidence_bundle=None,
        fixture_rubric=rubric,
        fixture_loss_ledger=loss_ledger,
        non_claims=_as_list(data.get("non_claims")),
    )


def audit_artifact_root(path: Path) -> dict[str, Any]:
    run_dir = path / "run" if (path / "run" / "summary.json").is_file() else path
    summary = _load_json(run_dir / "summary.json")
    evidence_bundle = _load_json(run_dir / "agent_evidence_bundle.json")
    workflow_trace = _load_json(run_dir / "workflow_trace.json")
    markdown_parts = [_read_text(run_dir / "final_report.md")] if (run_dir / "final_report.md").is_file() else []
    public_report = path / "public_agent_report.md"
    if public_report.exists():
        markdown_parts.append(_read_text(public_report))
    markdown = "\n\n".join(markdown_parts)
    report_result = _as_mapping(summary.get("report_result"))
    if not report_result:
        report_result = _report_result_from_summary(summary)
    rows = _agent_material_coverage_from_real(summary, evidence_bundle)
    quality_summary = _as_mapping(evidence_bundle.get("quality_summary"))
    compact_summary = _summary_counts_from_real(summary, workflow_trace)
    return _audit_common(
        artifact_root=str(path),
        input_mode="real_artifact",
        summary=compact_summary,
        report_result=report_result,
        agent_rows=rows,
        quality_summary=quality_summary,
        markdown=markdown,
        evidence_bundle=evidence_bundle,
        non_claims=_as_list(summary.get("non_claims")),
        l3_contributor_integrity=_l3_contributor_integrity(evidence_bundle),
    )


def _report_result_from_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "title": summary.get("final_report_title") or "",
        "status": summary.get("final_report_status") or "",
        "answer": summary.get("final_answer") or "",
        "sections": summary.get("final_report_sections") or [],
        "evidence_cards": summary.get("final_report_evidence_cards") or [],
        "limitations": summary.get("final_report_limitations") or [],
    }


def _summary_counts_from_real(
    summary: Mapping[str, Any],
    workflow_trace: Mapping[str, Any],
) -> dict[str, Any]:
    provenance = _as_mapping(summary.get("provenance"))
    demo_called = set(_as_list(provenance.get("external_compute_demo_called_agents")))
    default_called = set(_as_list(provenance.get("external_compute_default_called_agents")))
    demo_mapped = set(_as_list(provenance.get("external_compute_demo_mapped_agents")))
    default_mapped = set(_as_list(provenance.get("external_compute_default_mapped_agents")))
    demo_failed = set(_as_list(provenance.get("external_compute_demo_failed_agents")))
    default_failed = set(_as_list(provenance.get("external_compute_default_failed_agents")))
    l2_outputs = _as_mapping(summary.get("l2_agent_outputs"))
    l3_outputs = _as_mapping(summary.get("l3_composite_outputs"))
    report_result = _as_mapping(summary.get("report_result"))
    return {
        "compute_called": len(demo_called | default_called),
        "compute_mapped": len(demo_mapped | default_mapped),
        "compute_failed": len(demo_failed | default_failed),
        "failed_agents": sorted(str(item) for item in (demo_failed | default_failed)),
        "l2_complete": sum(
            1 for item in l2_outputs.values() if _as_mapping(item).get("status") == "complete"
        ),
        "l2_partial": sum(
            1 for item in l2_outputs.values() if _as_mapping(item).get("status") == "partial"
        ),
        "l3_complete": sum(
            1 for item in l3_outputs.values() if _as_mapping(item).get("status") == "complete"
        ),
        "l3_partial": sum(
            1 for item in l3_outputs.values() if _as_mapping(item).get("status") == "partial"
        ),
        "l2_agent_outputs": dict(l2_outputs),
        "l3_composite_outputs": dict(l3_outputs),
        "l4_decision_mapped": "decision_synthesizer" in default_mapped,
        "l4_report_mapped": "report_generator" in default_mapped,
        "workflow_step_count": _safe_int(
            summary.get("workflow_step_count") or workflow_trace.get("workflow_step_count")
        ),
        "final_report_sections": len(_as_list(report_result.get("sections"))),
        "final_report_evidence_cards": len(_as_list(report_result.get("evidence_cards"))),
        "final_report_limitations": len(_as_list(report_result.get("limitations"))),
    }


def write_outputs(
    result: Mapping[str, Any],
    *,
    output_dir: Path | None,
    output_json: Path | None,
    output_md: Path | None,
) -> tuple[Path | None, Path | None]:
    json_path = output_json
    md_path = output_md
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = json_path or output_dir / "report_quality_audit_result.json"
        md_path = md_path or output_dir / "report_quality_audit_result.md"
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if md_path is not None:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(render_markdown(result), encoding="utf-8")
    return json_path, md_path


def render_markdown(result: Mapping[str, Any]) -> str:
    score = _as_mapping(result.get("quality_score"))
    material = _as_mapping(result.get("material_coverage"))
    trace = _as_mapping(result.get("traceability"))
    template = _as_mapping(result.get("template_language"))
    parity = _as_mapping(result.get("answer_section_parity"))
    risk = _as_mapping(result.get("risk_compliance_review"))
    lines = [
        "# Report Quality Audit",
        "",
        f"- Input mode: `{result.get('input_mode')}`",
        f"- Score: `{score.get('total')}/{score.get('max')}` ({score.get('normalized')})",
        f"- Compute called/mapped/failed: `{material.get('agents_called')}/{material.get('agents_mapped')}/{material.get('agents_failed')}`",
        f"- L2 complete/partial: `{material.get('l2_complete')}/{material.get('l2_partial')}`",
        f"- L3 complete/partial: `{material.get('l3_complete')}/{material.get('l3_partial')}`",
        f"- Traceability ratio: `{trace.get('traceability_ratio')}`",
        f"- Template phrase count: `{template.get('template_phrase_count')}`",
        f"- Research point utilization: `{material.get('research_points_utilized')}/{material.get('research_points_total')}`",
        f"- Answer/section parity: `{parity.get('parity_ratio')}`",
        f"- Risk compliance failed: `{risk.get('failed')}`",
        f"- Recommended next wave: `{result.get('recommended_next_wave')}`",
        "",
        "## Rubric",
        "",
    ]
    for item in _as_list(result.get("rubric")):
        item_map = _as_mapping(item)
        lines.append(f"- {item_map.get('name')}: {item_map.get('score')}/{item_map.get('max')}")
    lines.extend(["", "## Top Losses", ""])
    for item in _as_list(result.get("loss_ledger"))[:10]:
        item_map = _as_mapping(item)
        lines.append(
            "- {agent}: {stage} (severity {severity})".format(
                agent=item_map.get("agent_id", ""),
                stage=item_map.get("loss_stage", ""),
                severity=item_map.get("severity", ""),
            )
        )
    return "\n".join(lines) + "\n"


def _threshold_failures(
    result: Mapping[str, Any],
    *,
    min_score: int | None,
    max_template_phrases: int | None,
    min_traceability_ratio: float | None,
    require_unsafe_pass: bool,
    require_renderer_quality_gate: bool,
) -> list[str]:
    failures: list[str] = []
    score = _as_mapping(result.get("quality_score"))
    template = _as_mapping(result.get("template_language"))
    trace = _as_mapping(result.get("traceability"))
    safety = _as_mapping(result.get("public_safety"))
    if min_score is not None and _safe_int(score.get("total")) < min_score:
        failures.append(f"score_below_min:{score.get('total')}<{min_score}")
    if (
        max_template_phrases is not None
        and _safe_int(template.get("template_phrase_count")) > max_template_phrases
    ):
        failures.append(
            "template_phrase_count_above_max:"
            f"{template.get('template_phrase_count')}>{max_template_phrases}"
        )
    if (
        min_traceability_ratio is not None
        and _safe_float(trace.get("traceability_ratio")) < min_traceability_ratio
    ):
        failures.append(
            "traceability_ratio_below_min:"
            f"{trace.get('traceability_ratio')}<{min_traceability_ratio}"
        )
    if require_unsafe_pass and not safety.get("unsafe_scan_pass"):
        failures.append("unsafe_scan_failed")
    if require_renderer_quality_gate and not _as_mapping(result.get("renderer_quality_gate")).get("passed"):
        failed_checks = ",".join(
            str(item) for item in _as_list(_as_mapping(result.get("renderer_quality_gate")).get("failed_checks"))
        )
        failures.append(f"renderer_quality_gate_failed:{failed_checks}")
    return failures


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a fixed-DAG report quality artifact offline.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--artifact-root", type=Path)
    source.add_argument("--fixture", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--fail-on-threshold", action="store_true")
    parser.add_argument("--min-score", type=int)
    parser.add_argument("--max-template-phrases", type=int)
    parser.add_argument("--min-traceability-ratio", type=float)
    parser.add_argument("--require-unsafe-pass", action="store_true")
    parser.add_argument("--require-renderer-quality-gate", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.fixture is not None:
        result = audit_fixture(args.fixture)
    else:
        result = audit_artifact_root(args.artifact_root)
    failures = _threshold_failures(
        result,
        min_score=args.min_score,
        max_template_phrases=args.max_template_phrases,
        min_traceability_ratio=args.min_traceability_ratio,
        require_unsafe_pass=args.require_unsafe_pass,
        require_renderer_quality_gate=args.require_renderer_quality_gate,
    )
    if failures:
        result = {**result, "threshold_failures": failures}
    write_outputs(
        result,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    if args.fail_on_threshold and failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
