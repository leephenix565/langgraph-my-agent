# ruff: noqa: D103
"""Step-result helpers for fixed-DAG execution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from react_agent.fixed_dag.constants import RESET_RUNTIME_AGENT_IDS
from react_agent.fixed_dag.execution.constants import (
    FIXED_DAG_STEP_RESULT_SCHEMA_VERSION,
    LEGAL_DIMENSIONS,
    LEGAL_STEP_STATUSES,
    STAGE_ORDER_INDEX,
)
from react_agent.fixed_dag.execution.topology import _deps, _steps
from react_agent.fixed_dag_runtime_registry import (
    annotate_step_result_with_binding,
    binding_by_agent_id,
)


def build_step_result(
    step: Mapping[str, Any],
    *,
    status: str,
    output_ref: str = "",
    summary: str = "",
) -> dict:
    result = {
        "schema_version": FIXED_DAG_STEP_RESULT_SCHEMA_VERSION,
        "step_id": str(step.get("id") or ""),
        "agent_id": str(step.get("agent_id") or ""),
        "stage": str(step.get("stage") or ""),
        "dimension": str(step.get("dimension") or ""),
        "status": status,
        "depends_on": _deps(step),
        "output_ref": output_ref,
        "summary": summary,
        "warnings": [],
    }
    return annotate_step_result_with_binding(result)


def validate_step_result(result: Mapping[str, Any]) -> tuple[bool, str]:
    if result.get("schema_version") != FIXED_DAG_STEP_RESULT_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if not str(result.get("step_id") or ""):
        return False, "step_id_missing"
    if result.get("agent_id") not in RESET_RUNTIME_AGENT_IDS:
        return False, "invalid_agent_id"
    if result.get("stage") not in STAGE_ORDER_INDEX:
        return False, "invalid_stage"
    if result.get("dimension") not in LEGAL_DIMENSIONS:
        return False, "invalid_dimension"
    if result.get("status") not in LEGAL_STEP_STATUSES:
        return False, "invalid_status"
    if not isinstance(result.get("depends_on"), list):
        return False, "invalid_dependencies"
    if not isinstance(result.get("warnings"), list):
        return False, "invalid_warnings"
    for field in (
        "runtime_kind",
        "implementation_status",
        "binding_source",
        "legacy_agent_id",
        "external_agent_id",
        "invoke_enabled",
        "live_verified",
    ):
        if field not in result:
            return False, f"missing_{field}"
    if not isinstance(result.get("invoke_enabled"), bool):
        return False, "invalid_invoke_enabled"
    if not isinstance(result.get("live_verified"), bool):
        return False, "invalid_live_verified"
    binding = binding_by_agent_id(str(result["agent_id"]))
    expected = {
        "runtime_kind": binding["runtime_kind"],
        "implementation_status": binding["implementation_status"],
        "legacy_agent_id": binding["legacy_agent_id"],
        "external_agent_id": binding["external_agent_id"],
        "invoke_enabled": binding["invoke_enabled_by_default"],
        "live_verified": binding["live_verified"],
    }
    for field, expected_value in expected.items():
        if result.get(field) != expected_value:
            return False, f"binding_metadata_mismatch:{field}"
    return True, "ok"


def build_initial_step_results(plan: Mapping[str, Any]) -> dict[str, dict]:
    return {
        str(step["id"]): build_step_result(
            step,
            status="blocked",
            summary="此步骤尚未进入本轮研判流程。",
        )
        for step in _steps(plan)
        if step.get("id")
    }


def _output_ref_for_step(step: Mapping[str, Any]) -> str:
    agent_id = str(step.get("agent_id") or "")
    stage = str(step.get("stage") or "")
    dimension = str(step.get("dimension") or "")
    if agent_id == "route_planner":
        return "fixed_dag_plan"
    if agent_id == "entity_relation_extractor":
        return "entity_relation_bundle"
    if agent_id == "financial_data_service":
        return "data_bundle"
    if stage == "l2_analysis":
        return f"l2_conclusions.{agent_id}"
    if stage == "dimension_composite":
        return f"dimension_results.{dimension}"
    if agent_id == "decision_synthesizer":
        return "decision_result"
    if agent_id == "report_generator":
        return "report_result"
    return ""


def _status_for_step(step: Mapping[str, Any]) -> str:
    return "complete" if step.get("agent_id") == "route_planner" else "pending_implementation"


def _summary_for_step(step: Mapping[str, Any]) -> str:
    if step.get("agent_id") == "route_planner":
        return "已组织本轮研判流程。"
    return "已按本地固定流程记录本轮处理结果。"


def _attach_report_input_bundle_to_step_results(
    step_results: dict[str, dict],
    report_input_bundle: Mapping[str, Any],
) -> None:
    evidence_bundle = report_input_bundle.get("agent_evidence_bundle", {})
    if isinstance(evidence_bundle, Mapping):
        l1_evidence = evidence_bundle.get("l1_evidence", {})
        if isinstance(l1_evidence, Mapping):
            if "financial_data_service" in step_results:
                step_results["financial_data_service"]["agent_evidence"] = {
                    "schema": "agent_evidence_bundle_v1.l1_evidence",
                    "agent_id": "financial_data_service",
                    "status": l1_evidence.get("data_bundle_status", ""),
                    "sources_count": l1_evidence.get("data_sources_count", 0),
                    "summary": "L1 金融数据证据输入状态。",
                }
            if "entity_relation_extractor" in step_results:
                step_results["entity_relation_extractor"]["agent_evidence"] = {
                    "schema": "agent_evidence_bundle_v1.l1_evidence",
                    "agent_id": "entity_relation_extractor",
                    "status": l1_evidence.get("entity_relation_status", ""),
                    "entities_count": l1_evidence.get("entities_count", 0),
                    "relations_count": l1_evidence.get("relations_count", 0),
                    "summary": "L1 实体关系证据输入状态。",
                }
    task_items = report_input_bundle.get("agent_task_summaries", [])
    if isinstance(task_items, list):
        for item in task_items:
            if not isinstance(item, Mapping):
                continue
            step_id = str(item.get("step_id") or "")
            if step_id in step_results:
                step_results[step_id]["agent_task"] = {
                    key: item[key]
                    for key in (
                        "schema",
                        "agent_id",
                        "display_name",
                        "layer",
                        "dimension",
                        "task_instruction",
                        "target",
                        "as_of",
                        "required_output_schema",
                        "upstream_agent_ids",
                        "has_l1_data_bundle",
                        "has_l1_entity_relation_bundle",
                    )
                    if key in item
                }
    l2_items = report_input_bundle.get("l2_agent_summaries", [])
    if isinstance(evidence_bundle, Mapping) and isinstance(
        evidence_bundle.get("l2_agent_outputs"), list
    ):
        l2_items = evidence_bundle["l2_agent_outputs"]
    if isinstance(l2_items, list):
        for item in l2_items:
            if not isinstance(item, Mapping):
                continue
            agent_id = str(item.get("agent_id") or "")
            step_id = f"l2:{agent_id}"
            if step_id in step_results:
                step_results[step_id]["agent_evidence"] = {
                    key: item[key]
                    for key in (
                        "agent_id",
                        "display_name",
                        "layer",
                        "dimension",
                        "status",
                        "stance",
                        "confidence",
                        "summary",
                        "as_of",
                        "data_as_of",
                        "source",
                        "risk_score",
                        "evidence_count",
                        "detail_notes",
                        "evidence_items",
                        "domain_metrics",
                        "drivers",
                        "research_points",
                        "data_quality",
                        "provenance_notes",
                        "required_output_schema",
                        "received_output_schema",
                    )
                    if key in item
                }
    l3_items = report_input_bundle.get("l3_composite_summaries", [])
    if isinstance(evidence_bundle, Mapping) and isinstance(
        evidence_bundle.get("l3_composite_outputs"), list
    ):
        l3_items = evidence_bundle["l3_composite_outputs"]
    if isinstance(l3_items, list):
        for item in l3_items:
            if not isinstance(item, Mapping):
                continue
            dimension = str(item.get("dimension") or "")
            step_id = f"dimension:{dimension}"
            if step_id in step_results:
                step_results[step_id]["composite_evidence"] = {
                    key: item[key]
                    for key in (
                        "agent_id",
                        "display_name",
                        "layer",
                        "dimension",
                        "status",
                        "stance",
                        "confidence",
                        "summary",
                        "members",
                        "gate",
                        "veto",
                        "penalty",
                        "risk_score",
                        "regime",
                        "dimension_weights",
                        "risk_sensitivity",
                        "as_of",
                        "data_as_of",
                        "source",
                        "evidence_refs",
                        "detail_notes",
                        "domain_metrics",
                        "drivers",
                        "research_points",
                        "data_quality",
                        "provenance_notes",
                        "required_output_schema",
                        "received_output_schema",
                    )
                    if key in item
                }


__all__ = [
    "build_initial_step_results",
    "build_step_result",
    "validate_step_result",
]
