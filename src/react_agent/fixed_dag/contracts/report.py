# ruff: noqa: D101, D103
"""Report input bundle, formatting, and report result builders.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, cast

from react_agent.fixed_dag.constants import (
    AGENT_DIMENSIONS,
    AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION,
    DEFAULT_AS_OF,
    DIMENSION_GROUPS,
    L2_CONCLUSION_AGENT_IDS,
    L3_COMPOSITE_AGENT_IDS,
    REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
    REPORT_RESULT_SCHEMA_VERSION,
    RESET_SOURCE,
)
from react_agent.fixed_dag.labels import AGENT_TITLE_LABELS, DIMENSION_TITLE_LABELS
from react_agent.fixed_dag.safety import (
    _contains_unsafe_report_key,
    _safe_public_detail_list,
    _safe_public_detail_mapping,
    _safe_public_detail_value,
    _safe_public_float,
    _safe_public_mapping,
    _safe_public_text,
    _safe_public_text_list,
)
from react_agent.fixed_dag.types import (
    AgentTask,
    ConclusionObject,
    ReportInputBundle,
    ReportResult,
)

# Lazy imports for cross-module references (avoid circular imports)
import importlib
def _plan_build_agent_task_summaries(agent_tasks):
    return importlib.import_module(
        'react_agent.fixed_dag.contracts.plan'
    ).build_agent_task_summaries(agent_tasks)
def _plan_bounded_task_value(value, depth=0):
    return importlib.import_module(
        'react_agent.fixed_dag.contracts.plan'
    )._bounded_task_value(value, depth=depth)

def _safe_evidence_summary(evidence: Any) -> str:
    if not isinstance(evidence, list):
        return ""
    for item in evidence:
        if not isinstance(item, Mapping):
            continue
        for key in ("fact", "summary", "note", "evidence"):
            text = _safe_public_text(item.get(key), limit=160)
            if text:
                return text
    return ""


def _l2_quality_notes(result: Mapping[str, Any]) -> list[str]:
    """Build bounded report-facing notes explaining thin external evidence."""
    notes: list[str] = []
    provenance = result.get("provenance", {})
    status = _safe_public_text(result.get("status"), limit=40)
    if isinstance(provenance, Mapping):
        reason = _safe_public_text(provenance.get("reason"), limit=120)
        external_status = _safe_public_text(provenance.get("external_status"), limit=80)
        if reason:
            notes.append(f"adapter_reason={reason}")
        if external_status and external_status != status:
            notes.append(f"external_status={external_status}")
        raw_keys = _safe_public_text_list(provenance.get("raw_output_keys"), limit=8)
        if raw_keys:
            notes.append(f"raw_output_keys={','.join(raw_keys)}")
        quality_keys = _safe_public_text_list(provenance.get("quality_keys"), limit=8)
        if quality_keys:
            notes.append(f"quality_keys={','.join(quality_keys)}")
        domain_metrics = _safe_public_detail_mapping(provenance.get("domain_metrics"), limit=8)
        if domain_metrics:
            notes.append(f"domain_metrics_count={len(domain_metrics)}")
        drivers = _safe_public_detail_list(provenance.get("drivers"), limit=6)
        if drivers:
            notes.append(f"drivers_count={len(drivers)}")
        data_quality = _safe_public_detail_mapping(provenance.get("data_quality"), limit=8)
        if data_quality:
            notes.append(f"data_quality_count={len(data_quality)}")
        if provenance.get("adapter_failure") is True:
            notes.append("adapter_failure=true")
    evidence = result.get("evidence")
    evidence_count = len(evidence) if isinstance(evidence, list) else 0
    if evidence_count == 0:
        notes.append("readable_evidence_count=0")
    if status in {"error", "partial"}:
        notes.append(f"service_status={status}")
    return notes[:10]


def _evidence_ref_summary(evidence_refs: Any) -> str:
    if not isinstance(evidence_refs, list) or not evidence_refs:
        return ""
    refs = [
        _safe_public_text(item, limit=80)
        for item in evidence_refs[:3]
        if _safe_public_text(item, limit=80)
    ]
    return "；".join(refs)


def _report_source_from_provenance(provenance: Any) -> str:
    if not isinstance(provenance, Mapping):
        return "fixed_dag_placeholder"
    runtime_source = _safe_public_text(provenance.get("runtime_source"), limit=80)
    if runtime_source:
        return runtime_source
    if provenance.get("adapter_source"):
        return "external_compute_demo"
    if provenance.get("runtime_path") == "internal_llm_placeholder":
        return "internal_llm_placeholder"
    return _safe_public_text(provenance.get("source"), limit=80) or "fixed_dag_placeholder"


def _l2_agent_summary(agent_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
    provenance = result.get("provenance", {})
    dimension = _safe_public_text(result.get("dimension") or AGENT_DIMENSIONS.get(agent_id), limit=40)
    risk_score = None
    if isinstance(provenance, Mapping) and provenance.get("risk_score") is not None:
        risk_score = _safe_public_float(provenance.get("risk_score"))
    detail_notes = _l2_quality_notes(result)
    summary = _safe_evidence_summary(result.get("evidence"))
    if not summary:
        detail = f"；诊断：{'；'.join(detail_notes[:3])}" if detail_notes else ""
        summary = (
            f"{AGENT_TITLE_LABELS.get(agent_id, agent_id)} 输出 "
            f"{_safe_public_text(result.get('stance') or 'not_evaluated', limit=80)} "
            f"信号，置信度 {_safe_public_float(result.get('confidence')):.2f}。"
            f"{detail}"
        )
    evidence = result.get("evidence")
    item: dict[str, Any] = {
        "agent_id": agent_id,
        "display_name": AGENT_TITLE_LABELS.get(agent_id, agent_id),
        "layer": "L2",
        "dimension": dimension,
        "status": _safe_public_text(result.get("status"), limit=40),
        "stance": _safe_public_text(result.get("stance") or "risk_gate_member", limit=80),
        "confidence": _safe_public_float(result.get("confidence")),
        "summary": summary,
        "as_of": _safe_public_text(result.get("as_of"), limit=40),
        "data_as_of": _safe_public_text(result.get("data_as_of"), limit=40),
        "source": _report_source_from_provenance(provenance),
        "evidence_count": len(evidence) if isinstance(evidence, list) else 0,
        "detail_notes": detail_notes,
    }
    if risk_score is not None:
        item["risk_score"] = risk_score
    return item


def _safe_member_summaries(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    provenance = result.get("provenance", {})
    raw_members = (
        provenance.get("member_weight_summary")
        if isinstance(provenance, Mapping)
        else None
    )
    members: list[dict[str, Any]] = []
    if isinstance(raw_members, list):
        for item in raw_members[:12]:
            if not isinstance(item, Mapping):
                continue
            agent_id = _safe_public_text(item.get("agent_id"), limit=80)
            if not agent_id:
                continue
            member = {
                "agent_id": agent_id,
                "display_name": AGENT_TITLE_LABELS.get(agent_id, agent_id),
                "stance": _safe_public_text(item.get("stance"), limit=80),
                "status": _safe_public_text(item.get("status"), limit=40),
                "summary": _safe_public_text(item.get("summary"), limit=160),
            }
            if "weight" in item and item.get("weight") is not None:
                member["weight"] = _safe_public_float(item.get("weight"))
            if "confidence" in item and item.get("confidence") is not None:
                member["confidence"] = _safe_public_float(item.get("confidence"))
            if "risk_score" in item and item.get("risk_score") is not None:
                member["risk_score"] = _safe_public_float(item.get("risk_score"))
            members.append(member)
    if members:
        return members
    contributing_agents = result.get("contributing_agents")
    if isinstance(contributing_agents, list):
        for agent_id_value in contributing_agents[:12]:
            agent_id = _safe_public_text(agent_id_value, limit=80)
            if not agent_id:
                continue
            members.append(
                {
                    "agent_id": agent_id,
                    "display_name": AGENT_TITLE_LABELS.get(agent_id, agent_id),
                }
            )
    return members


def _safe_evidence_detail_items(value: Any, *, limit: int = 8) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for raw in value[:limit]:
        if not isinstance(raw, Mapping):
            continue
        item: dict[str, Any] = {}
        for key in ("id", "fact", "source", "as_of", "data_as_of", "unit"):
            text = _safe_public_text(raw.get(key), limit=220 if key == "fact" else 80)
            if text:
                item[key] = text
        if raw.get("value") is not None:
            try:
                item["value"] = float(raw.get("value"))
            except (TypeError, ValueError):
                text = _safe_public_text(raw.get("value"), limit=80)
                if text:
                    item["value"] = text
        if item:
            items.append(item)
    return items


def _provenance_notes(provenance: Any) -> dict[str, Any]:
    if not isinstance(provenance, Mapping):
        return {}
    notes: dict[str, Any] = {}
    for key in (
        "reason",
        "external_status",
        "adapter_input_schema",
        "compute_envelope_status",
        "stance_source",
        "confidence_source",
    ):
        text = _safe_public_text(provenance.get(key), limit=120)
        if text:
            notes[key] = text
    for key in ("raw_output_keys", "quality_keys"):
        values = _safe_public_text_list(provenance.get(key), limit=10, item_limit=80)
        if values:
            notes[key] = values
    for key in ("contributing_agents", "missing_or_degraded_members"):
        values = _safe_public_text_list(provenance.get(key), limit=12, item_limit=120)
        if values:
            notes[key] = values
    member_summary = _safe_public_detail_list(provenance.get("member_weight_summary"), limit=12)
    if member_summary:
        notes["member_weight_summary"] = member_summary
    non_contributors = _safe_public_detail_list(provenance.get("non_contributor_members"), limit=12)
    if non_contributors:
        notes["non_contributor_members"] = non_contributors
    dropped_refs = _safe_public_detail_list(provenance.get("dropped_evidence_refs"), limit=12)
    if dropped_refs:
        notes["dropped_evidence_refs"] = dropped_refs
    domain_metrics = _safe_public_detail_mapping(provenance.get("domain_metrics"), limit=18)
    if domain_metrics:
        notes["domain_metrics"] = domain_metrics
    drivers = _safe_public_detail_list(provenance.get("drivers"), limit=10)
    if drivers:
        notes["drivers"] = drivers
    research_points = _safe_public_detail_list(provenance.get("research_points"), limit=8)
    if research_points:
        notes["research_points"] = research_points
    data_quality = _safe_public_detail_mapping(provenance.get("data_quality"), limit=14)
    if data_quality:
        notes["data_quality"] = data_quality
    if provenance.get("adapter_failure") is True:
        notes["adapter_failure"] = True
    if provenance.get("risk_score") is not None:
        notes["risk_score"] = _safe_public_float(provenance.get("risk_score"))
    return notes


def _l2_agent_evidence_detail(agent_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
    summary = _l2_agent_summary(agent_id, result)
    provenance = result.get("provenance", {})
    provenance_notes = _provenance_notes(provenance)
    detail: dict[str, Any] = {
        **summary,
        "received_output_schema": _safe_public_text(result.get("schema"), limit=80),
        "required_output_schema": "agent_conclusion_v1",
        "evidence_items": _safe_evidence_detail_items(result.get("evidence")),
        "provenance_notes": provenance_notes,
    }
    for key in ("domain_metrics", "drivers", "research_points", "data_quality"):
        if key in provenance_notes:
            detail[key] = provenance_notes[key]
    output_routes = result.get("output_routes")
    if isinstance(output_routes, list):
        detail["output_routes"] = _safe_public_text_list(output_routes, limit=6, item_limit=80)
    return detail


def _l3_composite_evidence_detail(result: Mapping[str, Any]) -> dict[str, Any]:
    summary = _l3_composite_summary(result)
    provenance = result.get("provenance", {})
    evidence_refs = result.get("evidence_refs")
    provenance_notes = _provenance_notes(provenance)
    detail: dict[str, Any] = {
        **summary,
        "received_output_schema": _safe_public_text(result.get("schema"), limit=80),
        "required_output_schema": {
            "value_composite": "dimension_conclusion_v1",
            "market_composite": "dimension_conclusion_v1",
            "risk_composite": "risk_conclusion_v1",
            "macro_composite": "macro_conclusion_v1",
        }.get(str(result.get("agent_id") or ""), "dimension_composite_result_v1"),
        "evidence_refs": [
            _safe_public_text(ref, limit=220)
            for ref in evidence_refs[:8]
            if _safe_public_text(ref, limit=220)
        ]
        if isinstance(evidence_refs, list)
        else [],
        "contributing_agents": _safe_public_text_list(
            result.get("contributing_agents"),
            limit=12,
            item_limit=120,
        ),
        "provenance_notes": provenance_notes,
    }
    for key in ("domain_metrics", "drivers", "research_points", "data_quality"):
        if key in provenance_notes:
            detail[key] = provenance_notes[key]
    return detail


def _l3_composite_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    agent_id = _safe_public_text(result.get("agent_id"), limit=80)
    dimension = _safe_public_text(result.get("dimension"), limit=40)
    provenance = result.get("provenance", {})
    evidence_refs = result.get("evidence_refs")
    detail_notes: list[str] = []
    if isinstance(evidence_refs, list):
        detail_notes.append(f"evidence_refs_count={len(evidence_refs)}")
    members_preview = _safe_member_summaries(result)
    if members_preview:
        detail_notes.append(f"member_count={len(members_preview)}")
    item: dict[str, Any] = {
        "agent_id": agent_id,
        "display_name": AGENT_TITLE_LABELS.get(agent_id, agent_id),
        "layer": "L3",
        "dimension": dimension,
        "status": _safe_public_text(result.get("status"), limit=40),
        "stance": _safe_public_text(result.get("stance"), limit=80),
        "confidence": _safe_public_float(result.get("confidence")),
        "summary": (
            _evidence_ref_summary(result.get("evidence_refs"))
            or f"{DIMENSION_TITLE_LABELS.get(dimension, dimension)} 已形成综合结果。"
        ),
        "members": members_preview,
        "detail_notes": detail_notes[:8],
        "as_of": _safe_public_text(result.get("as_of"), limit=40),
        "data_as_of": _safe_public_text(result.get("data_as_of"), limit=40),
        "source": _report_source_from_provenance(provenance),
    }
    for field in ("gate", "veto", "penalty", "risk_score", "regime", "risk_sensitivity"):
        if field in result:
            raw = result.get(field)
            item[field] = (
                bool(raw)
                if isinstance(raw, bool)
                else _safe_public_float(raw)
                if isinstance(raw, int | float)
                else _safe_public_text(raw, limit=80)
            )
    if isinstance(result.get("dimension_weights"), Mapping):
        item["dimension_weights"] = _safe_public_mapping(
            result.get("dimension_weights"),
            allowed_keys={"value", "market"},
        )
    return item


def _dimension_order() -> tuple[str, ...]:
    return ("value", "market", "risk", "macro")


def _selected_dimension_scope(selected_dimensions: list[str] | tuple[str, ...] | None) -> dict[str, Any]:
    selected = [
        dimension
        for dimension in _dimension_order()
        if selected_dimensions and dimension in set(selected_dimensions)
    ]
    if selected:
        mode = "selected"
    else:
        mode = "full_dag"
        selected = list(_dimension_order())
    unselected = [dimension for dimension in _dimension_order() if dimension not in set(selected)]
    return {
        "schema": "report_routing_context_v1",
        "routing_mode": mode,
        "route_granularity": "dimension" if mode == "selected" else "full_dag",
        "selected_dimensions": selected,
        "unselected_dimensions": unselected,
        "selected_dimension_count": len(selected),
        "unselected_dimension_count": len(unselected),
    }


def _coverage_by_dimension(
    *,
    l2_items: list[dict[str, Any]],
    l3_items: list[dict[str, Any]],
    routing_context: Mapping[str, Any],
) -> dict[str, Any]:
    selected_dimensions = set(_safe_public_text_list(routing_context.get("selected_dimensions")))
    l3_by_dimension = {
        str(item.get("dimension") or ""): item
        for item in l3_items
        if str(item.get("dimension") or "") in DIMENSION_GROUPS
    }
    coverage: dict[str, Any] = {}
    for dimension in _dimension_order():
        l2_for_dimension = [
            item for item in l2_items if str(item.get("dimension") or "") == dimension
        ]
        l3_item = l3_by_dimension.get(dimension, {})
        notes = (
            cast(Mapping[str, Any], l3_item.get("provenance_notes"))
            if isinstance(l3_item.get("provenance_notes"), Mapping)
            else {}
        )
        coverage[dimension] = {
            "selected": dimension in selected_dimensions,
            "l2_agent_ids": [
                _safe_public_text(item.get("agent_id"), limit=80)
                for item in l2_for_dimension
                if _safe_public_text(item.get("agent_id"), limit=80)
            ],
            "l2_total": len(l2_for_dimension),
            "l2_complete": sum(1 for item in l2_for_dimension if item.get("status") == "complete"),
            "l2_partial": sum(1 for item in l2_for_dimension if item.get("status") == "partial"),
            "l2_without_readable_evidence": sum(
                1 for item in l2_for_dimension if int(item.get("evidence_count") or 0) == 0
            ),
            "l3_agent_id": _safe_public_text(l3_item.get("agent_id"), limit=80),
            "l3_status": _safe_public_text(l3_item.get("status"), limit=40),
            "l3_confidence": _safe_public_float(l3_item.get("confidence")),
            "evidence_refs_count": len(_safe_public_text_list(l3_item.get("evidence_refs"), limit=20)),
            "true_contributors": _safe_public_text_list(
                l3_item.get("contributing_agents"),
                limit=12,
                item_limit=120,
            ),
            "excluded_contributors": _safe_public_detail_list(
                notes.get("non_contributor_members"),
                limit=12,
            ),
            "degraded_non_contributors": _safe_public_text_list(
                notes.get("missing_or_degraded_members"),
                limit=12,
                item_limit=120,
            ),
        }
    return coverage


def build_agent_evidence_bundle(
    *,
    question: str,
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
    decision_result: Mapping[str, Any],
    agent_tasks: Mapping[str, Any] | None = None,
    data_bundle: Mapping[str, Any] | None = None,
    entity_relation_bundle: Mapping[str, Any] | None = None,
    selected_dimensions: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Build the richer public-safe bundle consumed by demo report generation."""
    task_summaries = _plan_build_agent_task_summaries(agent_tasks)
    l2_items = [
        _l2_agent_evidence_detail(agent_id, cast(Mapping[str, Any], result))
        for agent_id, result in l2_conclusions.items()
        if agent_id in L2_CONCLUSION_AGENT_IDS and isinstance(result, Mapping)
    ]
    l3_items = [
        _l3_composite_evidence_detail(cast(Mapping[str, Any], result))
        for dimension, result in dimension_results.items()
        if dimension in DIMENSION_GROUPS and isinstance(result, Mapping)
    ]
    routing_context = _selected_dimension_scope(selected_dimensions)
    coverage_by_dimension = _coverage_by_dimension(
        l2_items=l2_items,
        l3_items=l3_items,
        routing_context=routing_context,
    )
    return {
        "schema": AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "schema_version": AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "question": _safe_public_text(question, limit=500),
        "routing_context": routing_context,
        "selected_scope": routing_context,
        "coverage_by_dimension": coverage_by_dimension,
        "l1_evidence": {
            "data_bundle_status": _safe_public_text(
                (data_bundle or {}).get("status") if isinstance(data_bundle, Mapping) else "",
                limit=40,
            ),
            "entity_relation_status": _safe_public_text(
                (entity_relation_bundle or {}).get("status")
                if isinstance(entity_relation_bundle, Mapping)
                else "",
                limit=40,
            ),
            "data_sources_count": len((data_bundle or {}).get("sources", []))
            if isinstance((data_bundle or {}).get("sources"), list)
            else 0,
            "entities_count": len((entity_relation_bundle or {}).get("entities", []))
            if isinstance((entity_relation_bundle or {}).get("entities"), list)
            else 0,
            "relations_count": len((entity_relation_bundle or {}).get("relations", []))
            if isinstance((entity_relation_bundle or {}).get("relations"), list)
            else 0,
        },
        "agent_tasks": task_summaries,
        "l2_agent_outputs": l2_items,
        "l3_composite_outputs": l3_items,
        "decision_output": _plan_bounded_task_value(decision_result or {}),
        "quality_summary": {
            "l2_total": len(l2_items),
            "l2_complete": sum(1 for item in l2_items if item.get("status") == "complete"),
            "l2_error": sum(1 for item in l2_items if item.get("status") == "error"),
            "l2_partial": sum(1 for item in l2_items if item.get("status") == "partial"),
            "l2_without_readable_evidence": sum(
                1 for item in l2_items if int(item.get("evidence_count") or 0) == 0
            ),
            "l3_total": len(l3_items),
            "l3_complete": sum(1 for item in l3_items if item.get("status") == "complete"),
            "l3_partial": sum(1 for item in l3_items if item.get("status") == "partial"),
            "l3_error": sum(1 for item in l3_items if item.get("status") == "error"),
            "l3_available": sum(
                1 for item in l3_items if item.get("status") in {"complete", "partial"}
            ),
            "selected_dimension_count": routing_context["selected_dimension_count"],
            "unselected_dimension_count": routing_context["unselected_dimension_count"],
            "coverage_dimensions_count": len(
                [
                    item
                    for item in coverage_by_dimension.values()
                    if item.get("l2_total") or item.get("l3_agent_id")
                ]
            ),
        },
        "provenance": {
            "source": "fixed_dag_agent_evidence_bundle",
            "provider_invoked": False,
            "external_invoked": False,
            "public_safe": True,
        },
    }


def build_report_input_bundle(
    *,
    question: str,
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
    decision_result: Mapping[str, Any],
    agent_tasks: Mapping[str, Any] | None = None,
    data_bundle: Mapping[str, Any] | None = None,
    entity_relation_bundle: Mapping[str, Any] | None = None,
    selected_dimensions: list[str] | tuple[str, ...] | None = None,
) -> ReportInputBundle:
    l2_summaries = [
        _l2_agent_summary(agent_id, cast(Mapping[str, Any], result))
        for agent_id, result in l2_conclusions.items()
        if agent_id in L2_CONCLUSION_AGENT_IDS and isinstance(result, Mapping)
    ]
    l3_summaries = [
        _l3_composite_summary(cast(Mapping[str, Any], result))
        for dimension, result in dimension_results.items()
        if dimension in DIMENSION_GROUPS and isinstance(result, Mapping)
    ]
    risk_summary = next(
        (item for item in l3_summaries if item.get("dimension") == "risk"),
        {},
    )
    macro_summary = next(
        (item for item in l3_summaries if item.get("dimension") == "macro"),
        {},
    )
    routing_context = _selected_dimension_scope(selected_dimensions)
    agent_evidence_bundle = build_agent_evidence_bundle(
        question=question,
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
        decision_result=decision_result,
        agent_tasks=agent_tasks,
        data_bundle=data_bundle,
        entity_relation_bundle=entity_relation_bundle,
        selected_dimensions=selected_dimensions,
    )
    return {
        "schema": REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
        "schema_version": REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
        "question": _safe_public_text(question, limit=500),
        "status": "complete" if l2_summaries or l3_summaries else "pending_implementation",
        "routing_context": routing_context,
        "coverage_by_dimension": agent_evidence_bundle["coverage_by_dimension"],
        "agent_task_summaries": _plan_build_agent_task_summaries(agent_tasks),
        "agent_evidence_bundle": agent_evidence_bundle,
        "l2_agent_summaries": l2_summaries,
        "l3_composite_summaries": l3_summaries,
        "risk_gate": dict(risk_summary),
        "macro_regulator": dict(macro_summary),
        "decision_context": {
            "decision": _safe_public_text(decision_result.get("decision"), limit=80),
            "score": float(decision_result.get("score", 0.0) or 0.0),
            "confidence": _safe_public_float(decision_result.get("confidence")),
            "status": _safe_public_text(decision_result.get("status"), limit=40),
        },
        "limitations": [
            "报告输入包仅包含 public-safe 结构化摘要。",
            "不包含原始外部输出、接口地址、密钥、错误栈或内部推理草稿。",
        ],
        "provenance": {
            "source": "fixed_dag_report_input_bundle",
            "provider_invoked": False,
            "external_invoked": False,
        },
    }


def validate_report_input_bundle(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != REPORT_INPUT_BUNDLE_SCHEMA_VERSION:
        return False, "invalid_schema"
    if obj.get("schema_version", REPORT_INPUT_BUNDLE_SCHEMA_VERSION) != REPORT_INPUT_BUNDLE_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if "agent_task_summaries" in obj and not isinstance(obj.get("agent_task_summaries"), list):
        return False, "agent_task_summaries_invalid"
    if "agent_evidence_bundle" in obj:
        bundle = obj.get("agent_evidence_bundle")
        if not isinstance(bundle, Mapping):
            return False, "agent_evidence_bundle_invalid"
        if bundle.get("schema") != AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION:
            return False, "agent_evidence_bundle_invalid_schema"
    if not isinstance(obj.get("l2_agent_summaries"), list):
        return False, "l2_agent_summaries_missing"
    if not isinstance(obj.get("l3_composite_summaries"), list):
        return False, "l3_composite_summaries_missing"
    if not isinstance(obj.get("risk_gate"), Mapping):
        return False, "risk_gate_missing"
    if not isinstance(obj.get("macro_regulator"), Mapping):
        return False, "macro_regulator_missing"
    if _contains_unsafe_report_key(obj):
        return False, "unsafe_report_input_present"
    provenance = obj.get("provenance", {})
    if not isinstance(provenance, Mapping):
        return False, "invalid_provenance"
    if provenance.get("provider_invoked") or provenance.get("external_invoked"):
        return False, "live_invocation_claim_present"
    return True, "ok"

def _summaries_by_dimension(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {dimension: [] for dimension in DIMENSION_GROUPS}
    for item in items:
        dimension = str(item.get("dimension") or "")
        if dimension in result:
            result[dimension].append(item)
    return result


def _format_confidence(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "n/a"


def _format_public_detail_value(value: Any, *, limit: int = 160) -> str:
    if isinstance(value, int | float | bool):
        return str(value)
    if isinstance(value, Mapping | list):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value or "")
    return _safe_public_text(text, limit=limit)


def _format_public_detail_mapping(
    value: Any,
    *,
    limit: int = 5,
    value_limit: int = 80,
) -> str:
    if not isinstance(value, Mapping):
        return ""
    parts: list[str] = []
    for key, raw in list(value.items())[:limit]:
        key_text = _safe_public_text(key, limit=40)
        value_text = _format_public_detail_value(raw, limit=value_limit)
        if key_text and value_text:
            parts.append(f"{key_text}={value_text}")
    return "；".join(parts)


def _format_driver_details(value: Any, *, limit: int = 3) -> str:
    if not isinstance(value, list):
        return ""
    parts: list[str] = []
    for raw in value[:limit]:
        if isinstance(raw, Mapping):
            name = _safe_public_text(raw.get("name"), limit=40)
            driver_value = _format_public_detail_value(raw.get("value"), limit=120)
            if name and driver_value:
                parts.append(f"{name}={driver_value}")
        else:
            text = _format_public_detail_value(raw, limit=120)
            if text:
                parts.append(text)
    return "；".join(parts)


def _format_evidence_items(value: Any, *, limit: int = 3) -> str:
    if not isinstance(value, list):
        return ""
    facts: list[str] = []
    for raw in value[:limit]:
        if not isinstance(raw, Mapping):
            continue
        fact = _safe_public_text(raw.get("fact"), limit=180)
        source = _safe_public_text(raw.get("source"), limit=60)
        data_as_of = _safe_public_text(raw.get("data_as_of"), limit=40)
        if not fact:
            continue
        suffix_parts = []
        if source:
            suffix_parts.append(source)
        if data_as_of:
            suffix_parts.append(data_as_of)
        suffix = f"（{', '.join(suffix_parts)}）" if suffix_parts else ""
        facts.append(f"{fact}{suffix}")
    return "；".join(facts)


def _format_research_points(value: Any, *, limit: int = 3) -> str:
    if not isinstance(value, list):
        return ""
    points: list[str] = []
    for raw in value[:limit]:
        if not isinstance(raw, Mapping):
            continue
        fragments: list[str] = []
        claim = _safe_public_text(raw.get("claim"), limit=180)
        support = _safe_public_text(raw.get("support"), limit=220)
        interpretation = _safe_public_text(raw.get("interpretation"), limit=220)
        decision_implication = _safe_public_text(raw.get("decision_implication"), limit=220)
        caveat = _safe_public_text(raw.get("caveat"), limit=220)
        if claim:
            fragments.append(f"判断：{claim}")
        if support:
            fragments.append(f"依据：{support}")
        if interpretation:
            fragments.append(f"解释：{interpretation}")
        if decision_implication:
            fragments.append(f"含义：{decision_implication}")
        if caveat:
            fragments.append(f"边界：{caveat}")
        if fragments:
            points.append("；".join(fragments))
    return " | ".join(points)


def _format_business_context(item: Mapping[str, Any]) -> str:
    parts: list[str] = []
    research_text = _format_research_points(item.get("research_points"), limit=3)
    if research_text:
        parts.append(f"研究判断：{research_text}")
    evidence_text = _format_evidence_items(item.get("evidence_items"), limit=3)
    if evidence_text:
        parts.append(f"关键证据：{evidence_text}")
    metrics_text = _format_public_detail_mapping(item.get("domain_metrics"), limit=5)
    if metrics_text:
        parts.append(f"核心指标：{metrics_text}")
    drivers_text = _format_driver_details(item.get("drivers"), limit=3)
    if drivers_text:
        parts.append(f"驱动因素：{drivers_text}")
    quality_text = _format_public_detail_mapping(
        item.get("data_quality"),
        limit=5,
        value_limit=60,
    )
    if quality_text:
        parts.append(f"数据质量：{quality_text}")
    return " ".join(parts)


def _format_l2_summary_line(item: Mapping[str, Any]) -> str:
    display_name = _safe_public_text(item.get("display_name"), limit=80)
    stance = _safe_public_text(item.get("stance") or "not_evaluated", limit=80)
    confidence = _format_confidence(item.get("confidence"))
    summary = _safe_public_text(item.get("summary"), limit=140)
    detail_notes = item.get("detail_notes")
    note_text = ""
    if isinstance(detail_notes, list) and detail_notes:
        notes = [
            _safe_public_text(note, limit=80)
            for note in detail_notes[:3]
            if _safe_public_text(note, limit=80)
        ]
        if notes:
            note_text = f" 证据质量：{'；'.join(notes)}。"
    business_context = _format_business_context(item)
    business_text = f" {business_context}" if business_context else ""
    return f"- {display_name}：信号 {stance}，置信度 {confidence}。{summary}{note_text}{business_text}"


def _format_l3_member_preview(value: Any, *, limit: int = 4) -> str:
    if not isinstance(value, list):
        return ""
    parts: list[str] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        status = _safe_public_text(raw.get("status"), limit=40).lower()
        if status in {
            "error",
            "failed",
            "missing",
            "not_available",
            "pending",
            "pending_implementation",
            "skipped",
            "unavailable",
        }:
            continue
        if "confidence" in raw and _safe_public_float(raw.get("confidence")) <= 0.0:
            continue
        if "weight" in raw and _safe_public_float(raw.get("weight")) <= 0.0:
            continue
        name = _safe_public_text(raw.get("display_name") or raw.get("agent_id"), limit=60)
        if not name:
            continue
        fragments = [name]
        if "weight" in raw and raw.get("weight") is not None:
            weight = _safe_public_float(raw.get("weight"))
            fragments.append(f"w={weight}")
        stance = _safe_public_text(raw.get("stance"), limit=50)
        if "risk_score" in raw and raw.get("risk_score") is not None:
            risk_score = _safe_public_float(raw.get("risk_score"))
            fragments.append(f"risk={risk_score}")
        elif stance:
            fragments.append(f"stance={stance}")
        if "confidence" in raw and raw.get("confidence") is not None:
            confidence = _safe_public_float(raw.get("confidence"))
            fragments.append(f"conf={confidence}")
        status = _safe_public_text(raw.get("status"), limit=40)
        if status:
            fragments.append(f"status={status}")
        if len(fragments) > 1:
            parts.append(f"{fragments[0]}({','.join(fragments[1:])})")
        else:
            parts.append(fragments[0])
        if len(parts) >= limit:
            break
    return "；".join(parts)


def _format_l3_summary_line(item: Mapping[str, Any]) -> str:
    display_name = _safe_public_text(item.get("display_name"), limit=80)
    dimension = _safe_public_text(item.get("dimension"), limit=40)
    confidence = _format_confidence(item.get("confidence"))
    detail_notes = item.get("detail_notes")
    note_text = ""
    if isinstance(detail_notes, list) and detail_notes:
        notes = [
            _safe_public_text(note, limit=80)
            for note in detail_notes[:2]
            if _safe_public_text(note, limit=80)
        ]
        if notes:
            note_text = f" 证据质量：{'；'.join(notes)}。"
    members = item.get("members", [])
    member_count = len(members) if isinstance(members, list) else 0
    member_text = _format_l3_member_preview(members)
    member_context = f" 主要成员：{member_text}。" if member_text else ""
    if dimension == "risk":
        business_context = _format_business_context(item)
        business_text = f" {business_context}" if business_context else ""
        return (
            f"- {display_name}：风险门 {item.get('gate', 'not_evaluated')}，"
            f"风险分 {_format_confidence(item.get('risk_score'))}，置信度 {confidence}。"
            f"{note_text}{member_context}{business_text}"
        )
    if dimension == "macro":
        weights = item.get("dimension_weights", {})
        weight_text = ""
        if isinstance(weights, Mapping):
            weight_text = "，".join(
                f"{key}={value}" for key, value in weights.items() if key in {"value", "market"}
            )
        business_context = _format_business_context(item)
        business_text = f" {business_context}" if business_context else ""
        return (
            f"- {display_name}：宏观状态 {item.get('regime', 'not_evaluated')}，"
            f"value/market 权重 {weight_text or 'n/a'}，置信度 {confidence}。"
            f"{note_text}{member_context}{business_text}"
        )
    stance = _safe_public_text(item.get("stance") or "not_evaluated", limit=80)
    business_context = _format_business_context(item)
    business_text = f" {business_context}" if business_context else ""
    return (
        f"- {display_name}：综合信号 {stance}，成员 {member_count} 个，"
        f"置信度 {confidence}。{note_text}{member_context}{business_text}"
    )


def _format_agent_task_summary_line(item: Mapping[str, Any]) -> str:
    display_name = _safe_public_text(item.get("display_name"), limit=80)
    required_schema = _safe_public_text(item.get("required_output_schema"), limit=80)
    instruction = _safe_public_text(item.get("task_instruction"), limit=180)
    upstream = item.get("upstream_agent_ids", [])
    upstream_count = len(upstream) if isinstance(upstream, list) else 0
    return (
        f"- {display_name}：要求输出 {required_schema}；"
        f"上游输入 {upstream_count} 个；任务：{instruction}"
    )


def _count_task_layers(task_items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"L2": 0, "L3": 0, "L4": 0}
    for item in task_items:
        layer = _safe_public_text(item.get("layer"), limit=20)
        if layer in counts:
            counts[layer] += 1
    return counts


def _format_agent_task_overview(task_items: list[dict[str, Any]]) -> str:
    counts = _count_task_layers(task_items)
    total = counts["L2"] + counts["L3"] + counts["L4"]
    if total <= 0:
        return "本轮没有可展示的 agent_task_v1 任务摘要。"
    return (
        "本轮生成 agent_task_v1："
        f"L2 {counts['L2']} 个，L3 {counts['L3']} 个，L4 {counts['L4']} 个。"
        "每个任务携带 target、as_of、required_output_schema 和 public-safe upstream 摘要；"
        "完整任务保留在 report_input_bundle/workflow trace 中，fallback 报告不逐条展开模板化任务指令。"
    )


def _has_report_material(item: Mapping[str, Any]) -> bool:
    for key in ("research_points", "evidence_items", "domain_metrics", "drivers"):
        value = item.get(key)
        if isinstance(value, Mapping) and value:
            return True
        if isinstance(value, list) and value:
            return True
    if _safe_public_float(item.get("evidence_count")) > 0:
        return True
    return _safe_public_text(item.get("status"), limit=40) == "error"


def _placeholder_l2_notice(
    *,
    visible_items: list[dict[str, Any]],
    all_items: list[dict[str, Any]],
) -> str:
    hidden = [item for item in all_items if item not in visible_items]
    if not hidden:
        return ""
    by_dimension: dict[str, int] = {}
    for item in hidden:
        dimension = _safe_public_text(item.get("dimension") or "unknown", limit=40)
        by_dimension[dimension] = by_dimension.get(dimension, 0) + 1
    labels = {
        "value": "估值维",
        "market": "市场维",
        "risk": "风险维",
        "macro": "宏观维",
        "unknown": "未知维",
    }
    parts = [
        f"{labels.get(dimension, dimension)}{count} 个"
        for dimension, count in by_dimension.items()
        if count > 0
    ]
    return (
        f"未展开无可读证据的 L2：{len(hidden)} 个"
        f"（{'，'.join(parts)}）。"
        "这些 agent 仍保留在 report_input_bundle 中，但不在最终报告中伪装成真实研究材料。"
    )


def _report_bundle_sections(report_input_bundle: Mapping[str, Any]) -> list[dict[str, str]]:
    task_items = [
        cast(dict[str, Any], item)
        for item in report_input_bundle.get("agent_task_summaries", [])
        if isinstance(item, Mapping)
    ]
    l2_items = [
        cast(dict[str, Any], item)
        for item in report_input_bundle.get("l2_agent_summaries", [])
        if isinstance(item, Mapping)
    ]
    l3_items = [
        cast(dict[str, Any], item)
        for item in report_input_bundle.get("l3_composite_summaries", [])
        if isinstance(item, Mapping)
    ]
    evidence_bundle = report_input_bundle.get("agent_evidence_bundle", {})
    routing_context = (
        report_input_bundle.get("routing_context")
        if isinstance(report_input_bundle.get("routing_context"), Mapping)
        else {}
    )
    if isinstance(evidence_bundle, Mapping):
        if not routing_context and isinstance(evidence_bundle.get("routing_context"), Mapping):
            routing_context = cast(Mapping[str, Any], evidence_bundle.get("routing_context"))
        l2_detail_items = evidence_bundle.get("l2_agent_outputs")
        if isinstance(l2_detail_items, list):
            l2_items = [
                cast(dict[str, Any], item)
                for item in l2_detail_items
                if isinstance(item, Mapping)
            ]
        l3_detail_items = evidence_bundle.get("l3_composite_outputs")
        if isinstance(l3_detail_items, list):
            l3_items = [
                cast(dict[str, Any], item)
                for item in l3_detail_items
                if isinstance(item, Mapping)
            ]
    quality_summary = (
        evidence_bundle.get("quality_summary", {})
        if isinstance(evidence_bundle, Mapping)
        else {}
    )
    visible_l2_items = [item for item in l2_items if _has_report_material(item)]
    by_dimension = _summaries_by_dimension(visible_l2_items)
    l2_lines: list[str] = []
    for dimension, label in (
        ("value", "估值维"),
        ("market", "市场维"),
        ("risk", "风险维"),
        ("macro", "宏观维"),
    ):
        if not by_dimension[dimension]:
            continue
        l2_lines.append(f"{label}单体智能体：")
        l2_lines.extend(_format_l2_summary_line(item) for item in by_dimension[dimension])
    placeholder_notice = _placeholder_l2_notice(
        visible_items=visible_l2_items,
        all_items=l2_items,
    )
    if placeholder_notice:
        l2_lines.append(placeholder_notice)
    l3_lines = [_format_l3_summary_line(item) for item in l3_items]
    quality_lines: list[str] = []
    if isinstance(quality_summary, Mapping):
        l2_complete = int(quality_summary.get("l2_complete") or 0)
        l2_partial = int(quality_summary.get("l2_partial") or 0)
        l2_total = int(quality_summary.get("l2_total") or 0)
        l2_with_data = l2_complete + l2_partial
        quality_lines.append(
            "L2 已获取 {with_data}/{total} 个 agent 数据（{complete} 完全完成 + {partial} 降级参考），"
            "无可读证据 {thin}；"
            "L3 输出 {l3_available}/{l3_total}。".format(
                with_data=l2_with_data,
                total=l2_total,
                complete=l2_complete,
                partial=l2_partial,
                thin=int(quality_summary.get("l2_without_readable_evidence") or 0),
                l3_available=int(quality_summary.get("l3_available") or 0),
                l3_total=int(quality_summary.get("l3_total") or 0),
            )
        )
    sections: list[dict[str, str]] = []
    if (
        isinstance(routing_context, Mapping)
        and routing_context.get("routing_mode") == "selected"
    ):
        selected = _safe_public_text_list(
            routing_context.get("selected_dimensions"),
            limit=4,
            item_limit=40,
        )
        unselected = _safe_public_text_list(
            routing_context.get("unselected_dimensions"),
            limit=4,
            item_limit=40,
        )
        if unselected:
            sections.append(
                {
                    "id": "unselected_scope",
                    "title": "未覆盖维度",
                    "content": (
                        f"本轮 selected routing 仅覆盖 {', '.join(selected)}；"
                        f"{', '.join(unselected)} 不在本轮 selected scope 内，"
                        "不得写成已完成分析或同等证据覆盖。"
                    ),
                }
            )
    sections.extend(
        [
        {
            "id": "evidence_quality",
            "title": "证据质量诊断",
            "content": "\n".join(quality_lines) or "本轮没有可展示的证据质量统计。",
        },
        {
            "id": "agent_task_orchestration",
            "title": "智能体任务编排(agent_task_v1)",
            "content": _format_agent_task_overview(task_items),
        },
        {
            "id": "l2_agent_evidence",
            "title": "单体智能体输入",
            "content": "\n".join(l2_lines) or "本轮没有可展示的单体智能体结构化输入。",
        },
        {
            "id": "l3_composite_evidence",
            "title": "综合智能体输入",
            "content": "\n".join(l3_lines) or "本轮没有可展示的综合智能体结构化输入。",
        },
        ]
    )
    return sections


def build_report_result(
    decision_result: Mapping[str, Any],
    *,
    question: str = "",
    report_input_bundle: Mapping[str, Any] | None = None,
) -> ReportResult:
    answer = (
        "已完成本轮研判流程。系统按照固定研判流程组织本轮分析，包括问题理解、"
        "信息整理、并行分析、维度综合与报告生成；可展开分析路径查看过程记录。"
    )
    if question:
        answer = f"{answer}\n\n收到的问题：{question}"
    sections = [
        {
            "id": "runtime_scope",
            "title": "分析框架",
            "content": "系统按照固定研判流程组织本轮分析。",
        },
        {
            "id": "implementation_status",
            "title": "流程记录",
            "content": "如需查看过程，可展开分析路径。",
        },
    ]
    evidence_cards = [
        {
            "title": "分析框架",
            "note": "系统按照固定研判流程组织本轮分析，包括问题理解、信息整理、并行分析、维度综合与报告生成。",
        },
        {
            "title": "用户问题",
            "note": "围绕你提出的问题进行结构化梳理。",
        },
        {
            "title": "流程记录",
            "note": "如需查看过程，可展开分析路径。",
        },
    ]
    if isinstance(report_input_bundle, Mapping):
        valid_bundle, _bundle_reason = validate_report_input_bundle(report_input_bundle)
        if valid_bundle:
            detail_sections = _report_bundle_sections(report_input_bundle)
            sections.extend(detail_sections)
            detail_text = "\n\n".join(
                f"{section['title']}：\n{section['content']}"
                for section in detail_sections
            )
            answer = (
                f"{answer}\n\n报告生成输入摘要：\n{detail_text}\n\n"
                "最终结论：以上单体智能体和综合智能体输入用于解释本轮固定 DAG 演示报告；"
                "结论仍需结合业务 owner 复核。"
            )
            evidence_cards.append(
                {
                    "title": "报告生成输入",
                    "note": (
                        f"纳入 {len(report_input_bundle.get('l2_agent_summaries', []) or [])} 个单体智能体摘要和 "
                        f"{len(report_input_bundle.get('l3_composite_summaries', []) or [])} 个综合智能体摘要。"
                    ),
                }
            )
    decision = _safe_public_text(decision_result.get("decision"), limit=80)
    if decision and decision != "pending_implementation":
        evidence_cards.append({"title": "决策上下文", "note": f"决策状态：{decision}。"})
    return {
        "schema": REPORT_RESULT_SCHEMA_VERSION,
        "schema_version": REPORT_RESULT_SCHEMA_VERSION,
        "title": "研判流程",
        "answer": answer,
        "status": "pending_implementation",
        "sections": sections,
        "evidence_cards": evidence_cards,
        "limitations": [
            "当前为本地固定流程模式。",
            "高级连接状态可在设置诊断中查看。",
        ],
    }



def validate_report_result(obj: Mapping[str, Any]) -> tuple[bool, str]:
    if obj.get("schema") != REPORT_RESULT_SCHEMA_VERSION:
        return False, "invalid_schema"
    if obj.get("schema_version", REPORT_RESULT_SCHEMA_VERSION) != REPORT_RESULT_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    answer = str(obj.get("answer") or "")
    if not answer:
        return False, "answer_missing"
    if "研判流程" not in answer:
        return False, "reset_scope_missing"
    if not isinstance(obj.get("sections"), list):
        return False, "sections_missing"
    if not isinstance(obj.get("evidence_cards"), list):
        return False, "evidence_cards_missing"
    limitations = obj.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        return False, "limitations_missing"
    forbidden_claims = (
        "provider verified",
        "external service verified",
        "live analysis complete",
        "provider/live ready",
        "外部服务已全部验证",
        "真实业务智能体已全部上线",
    )
    lowered = answer.lower()
    if any(claim in lowered for claim in forbidden_claims):
        return False, "live_claim_present"
    return True, "ok"
