# ruff: noqa: D103
"""Fixed-DAG execution runner boundary.

The public compatibility surface remains ``react_agent.fixed_dag_executor``.
This module owns the runner orchestration while keeping fixed-DAG execution
semantics unchanged.
"""

from __future__ import annotations

import time
from collections import deque as deque
from collections.abc import Mapping
from typing import Any, cast

from react_agent.fixed_dag.execution.constants import (
    COMPOSITE_DEPENDENCY_GROUPS as COMPOSITE_DEPENDENCY_GROUPS,
)
from react_agent.fixed_dag.execution.constants import (
    DIMENSION_STEP_IDS as DIMENSION_STEP_IDS,
)
from react_agent.fixed_dag.execution.constants import (
    FIXED_DAG_EXECUTION_SCHEMA_VERSION,
)
from react_agent.fixed_dag.execution.constants import (
    FIXED_DAG_STEP_RESULT_SCHEMA_VERSION as FIXED_DAG_STEP_RESULT_SCHEMA_VERSION,
)
from react_agent.fixed_dag.execution.constants import (
    L2_EVIDENCE_DEPS as L2_EVIDENCE_DEPS,
)
from react_agent.fixed_dag.execution.constants import (
    LEGAL_DIMENSIONS as LEGAL_DIMENSIONS,
)
from react_agent.fixed_dag.execution.constants import (
    LEGAL_STEP_STATUSES as LEGAL_STEP_STATUSES,
)
from react_agent.fixed_dag.execution.constants import (
    STAGE_ORDER_INDEX as STAGE_ORDER_INDEX,
)
from react_agent.fixed_dag.execution.step_results import (
    _attach_report_input_bundle_to_step_results,
    _output_ref_for_step,
    _status_for_step,
    _summary_for_step,
    build_step_result,
)
from react_agent.fixed_dag.execution.step_results import (
    build_initial_step_results as build_initial_step_results,
)
from react_agent.fixed_dag.execution.step_results import (
    validate_step_result as validate_step_result,
)
from react_agent.fixed_dag.execution.topology import (
    _deps as _deps,
)
from react_agent.fixed_dag.execution.topology import (
    _execution_batches,
    build_dag_step_index,
)
from react_agent.fixed_dag.execution.topology import (
    _l2_step_ids as _l2_step_ids,
)
from react_agent.fixed_dag.execution.topology import (
    _selected_dimension_step_ids as _selected_dimension_step_ids,
)
from react_agent.fixed_dag.execution.topology import (
    _steps as _steps,
)
from react_agent.fixed_dag.execution.topology import (
    _topological_batches_from_steps as _topological_batches_from_steps,
)
from react_agent.fixed_dag.execution.topology import (
    topological_batches as topological_batches,
)
from react_agent.fixed_dag.execution.topology import (
    topological_batches_for_selected_plan as topological_batches_for_selected_plan,
)
from react_agent.fixed_dag.execution.validation import (
    _step_by_agent as _step_by_agent,
)
from react_agent.fixed_dag.execution.validation import (
    _validate_dependency_graph as _validate_dependency_graph,
)
from react_agent.fixed_dag.execution.validation import (
    _validate_dimension_dependencies as _validate_dimension_dependencies,
)
from react_agent.fixed_dag.execution.validation import (
    _validate_selected_dimension_dependencies as _validate_selected_dimension_dependencies,
)
from react_agent.fixed_dag.execution.validation import (
    _validate_stage_and_dimension as _validate_stage_and_dimension,
)
from react_agent.fixed_dag.execution.validation import (
    _validate_step_identity as _validate_step_identity,
)
from react_agent.fixed_dag.execution.validation import (
    validate_dag_execution_result as validate_dag_execution_result,
)
from react_agent.fixed_dag.execution.validation import (
    validate_dag_steps,
    validate_selected_dag_steps,
)
from react_agent.fixed_dag.safety import _contains_legacy_key as _contains_legacy_key
from react_agent.fixed_dag_contracts import (
    DECISION_RESULT_SCHEMA_VERSION as DECISION_RESULT_SCHEMA_VERSION,
)
from react_agent.fixed_dag_contracts import (
    DIMENSION_COMPOSITE_AGENT_IDS as DIMENSION_COMPOSITE_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS as DIMENSION_GROUPS,
)
from react_agent.fixed_dag_contracts import (
    FIXED_DAG_SCHEMA_VERSION,
    SELECTED_FIXED_DAG_SCHEMA_VERSION,
    build_agent_task_summaries,
    build_agent_tasks_for_plan,
    build_data_bundle,
    build_decision_result,
    build_default_fixed_dag_plan,
    build_dimension_results,
    build_entity_relation_bundle,
    build_l2_conclusions,
    build_report_input_bundle,
    build_report_result,
    build_workflow_snapshot_v2,
    normalize_fixed_dag_plan,
    validate_report_input_bundle,
)
from react_agent.fixed_dag_contracts import (
    FIXED_DAG_STAGE_ORDER as FIXED_DAG_STAGE_ORDER,
)
from react_agent.fixed_dag_contracts import (
    L2_CONCLUSION_AGENT_IDS as L2_CONCLUSION_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    LEGACY_CONTRACT_KEYS as LEGACY_CONTRACT_KEYS,
)
from react_agent.fixed_dag_contracts import (
    MACRO_AGENT_IDS as MACRO_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    MARKET_AGENT_IDS as MARKET_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    REPORT_RESULT_SCHEMA_VERSION as REPORT_RESULT_SCHEMA_VERSION,
)
from react_agent.fixed_dag_contracts import (
    RESET_RUNTIME_AGENT_IDS as RESET_RUNTIME_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    RISK_AGENT_IDS as RISK_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    VALUE_AGENT_IDS as VALUE_AGENT_IDS,
)
from react_agent.fixed_dag_contracts import (
    validate_decision_result as validate_decision_result,
)
from react_agent.fixed_dag_contracts import (
    validate_dimension_composite_result as validate_dimension_composite_result,
)
from react_agent.fixed_dag_contracts import (
    validate_fixed_dag_plan as validate_fixed_dag_plan,
)
from react_agent.fixed_dag_contracts import (
    validate_report_result as validate_report_result,
)
from react_agent.fixed_dag_contracts import (
    validate_selected_fixed_dag_plan as validate_selected_fixed_dag_plan,
)
from react_agent.fixed_dag_contracts import (
    validate_workflow_snapshot_v2 as validate_workflow_snapshot_v2,
)
from react_agent.fixed_dag_llm_placeholders import (
    INTERNAL_LLM_PLACEHOLDER_SOURCE,
    build_l2_conclusions_with_internal_placeholders,
)
from react_agent.fixed_dag_runtime_registry import (
    annotate_step_result_with_binding as annotate_step_result_with_binding,
)
from react_agent.fixed_dag_runtime_registry import (
    binding_by_agent_id as binding_by_agent_id,
)
from react_agent.fixed_dag_runtime_registry import (
    external_compute_default_agent_ids,
)

__all__ = ["execute_fixed_dag_plan"]


def _execution_plan_or_fallback(
    plan: Mapping[str, Any],
    *,
    question: str,
    as_of: str,
) -> tuple[Mapping[str, Any], bool, str]:
    if plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION:
        valid, reason = validate_selected_dag_steps(plan)
    else:
        valid, reason = validate_dag_steps(plan)
    if valid:
        return plan, False, "ok"
    fallback = normalize_fixed_dag_plan(
        {
            "schema": FIXED_DAG_SCHEMA_VERSION,
            "plan_id": plan.get("plan_id") if isinstance(plan, Mapping) else "",
            "user_text": question,
            "as_of": as_of,
        }
    )
    fallback["provenance"] = {
        **fallback["provenance"],
        "source": "fallback_deterministic_fixed_dag_plan",
        "fallback_reason": reason,
        "selected_routing_requested": plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION,
        "selected_routing_fallback": plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION,
    }
    return fallback, True, reason


def _execution_plan_valid(plan: Mapping[str, Any]) -> tuple[bool, str]:
    if plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION:
        return validate_selected_dag_steps(plan)
    return validate_dag_steps(plan)


def _apply_external_compute_step_updates(
    step_results: dict[str, dict],
    *runs: Mapping[str, Any],
) -> None:
    for run in runs:
        updates = run.get("step_updates", {}) if isinstance(run, Mapping) else {}
        if not isinstance(updates, Mapping):
            continue
        for step_id, update in updates.items():
            if step_id not in step_results or not isinstance(update, Mapping):
                continue
            status = str(update.get("status") or "")
            if status:
                step_results[str(step_id)]["status"] = status
            summary = str(update.get("summary") or "")
            if summary:
                step_results[str(step_id)]["summary"] = summary
            warning = str(update.get("warning") or "")
            if warning and warning not in step_results[str(step_id)]["warnings"]:
                step_results[str(step_id)]["warnings"].append(warning)
            agent_task = update.get("agent_task")
            if isinstance(agent_task, Mapping):
                step_results[str(step_id)]["agent_task"] = {
                    key: agent_task[key]
                    for key in (
                        "schema",
                        "schema_version",
                        "agent_id",
                        "display_name",
                        "layer",
                        "dimension",
                        "task_instruction",
                        "target",
                        "as_of",
                        "required_output_schema",
                    )
                    if key in agent_task
                }


def _merge_production_external_compute_runs(*runs: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "fallback_agents": [],
        "skipped_agents": [],
        "warnings": [],
        "latency_ms_by_agent": {},
        "agent_telemetry_by_agent": {},
        "mapped_schema_by_agent": {},
        "mapped_status_by_agent": {},
        "required_failures": [],
        "optional_failures": [],
        "policy_enabled": False,
        "policy_version": "",
        "demo_suppressed": False,
        "rollback_disabled": False,
    }
    for run in runs:
        if not isinstance(run, Mapping):
            continue
        for key in (
            "called_agents",
            "mapped_agents",
            "failed_agents",
            "fallback_agents",
            "skipped_agents",
            "warnings",
            "required_failures",
            "optional_failures",
        ):
            raw_items = run.get(key, [])
            if not isinstance(raw_items, list):
                continue
            for item in raw_items:
                text = str(item or "")
                if text and text not in merged[key]:
                    merged[key].append(text)
        latencies = run.get("latency_ms_by_agent", {})
        if isinstance(latencies, Mapping):
            for agent_id, value in latencies.items():
                try:
                    merged["latency_ms_by_agent"][str(agent_id)] = int(value)
                except (TypeError, ValueError):
                    continue
        for key in (
            "agent_telemetry_by_agent",
            "mapped_schema_by_agent",
            "mapped_status_by_agent",
        ):
            raw_mapping = run.get(key, {})
            if not isinstance(raw_mapping, Mapping):
                continue
            for agent_id, value in raw_mapping.items():
                if key == "agent_telemetry_by_agent" and isinstance(value, Mapping):
                    merged[key][str(agent_id)] = dict(value)
                    continue
                text = str(value or "")
                if text:
                    merged[key][str(agent_id)] = text
        merged["policy_enabled"] = bool(merged["policy_enabled"] or run.get("policy_enabled"))
        merged["demo_suppressed"] = bool(merged["demo_suppressed"] or run.get("demo_suppressed"))
        merged["rollback_disabled"] = bool(
            merged["rollback_disabled"] or run.get("rollback_disabled")
        )
        if not merged["policy_version"] and run.get("policy_version"):
            merged["policy_version"] = str(run["policy_version"])
    return merged


def _safe_telemetry_int(value: Any, *, max_value: int = 86_400_000) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return min(parsed, max_value)


def _step_metadata_by_agent(plan: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    for step in _steps(plan):
        agent_id = str(step.get("agent_id") or "")
        if not agent_id:
            continue
        metadata[agent_id] = {
            "stage": str(step.get("stage") or ""),
            "dimension": str(step.get("dimension") or ""),
        }
    return metadata


def _telemetry_sum(rows: list[dict[str, Any]], key: str) -> int | None:
    total = 0
    seen = False
    for row in rows:
        value = _safe_telemetry_int(row.get(key))
        if value is None:
            continue
        total += value
        seen = True
    return total if seen else None


def _performance_rows_for_summary(
    summary: Mapping[str, Any],
    *,
    runtime_source: str,
    step_metadata: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    called = [str(item) for item in summary.get("called_agents", []) if str(item)]
    failed = {str(item) for item in summary.get("failed_agents", []) if str(item)}
    fallback = {str(item) for item in summary.get("fallback_agents", []) if str(item)}
    latencies = summary.get("latency_ms_by_agent", {})
    latencies = latencies if isinstance(latencies, Mapping) else {}
    service_telemetry = summary.get("agent_telemetry_by_agent", {})
    service_telemetry = service_telemetry if isinstance(service_telemetry, Mapping) else {}
    schema_by_agent = summary.get("mapped_schema_by_agent", {})
    schema_by_agent = schema_by_agent if isinstance(schema_by_agent, Mapping) else {}
    status_by_agent = summary.get("mapped_status_by_agent", {})
    status_by_agent = status_by_agent if isinstance(status_by_agent, Mapping) else {}
    rows: list[dict[str, Any]] = []
    for agent_id in called:
        meta = step_metadata.get(agent_id, {})
        telemetry = service_telemetry.get(agent_id, {})
        telemetry = telemetry if isinstance(telemetry, Mapping) else {}
        elapsed = _safe_telemetry_int(latencies.get(agent_id))
        row: dict[str, Any] = {
            "agentId": agent_id,
            "stage": str(meta.get("stage") or "") or None,
            "dimension": str(meta.get("dimension") or "") or None,
            "runtimeSource": runtime_source,
            "elapsedMs": elapsed,
            "httpStatusClass": "2xx" if agent_id not in failed else None,
            "mappedSchema": str(schema_by_agent.get(agent_id) or "") or None,
            "mappedStatus": str(status_by_agent.get(agent_id) or "") or None,
            "fallback": agent_id in fallback,
            "degraded": agent_id in failed or agent_id in fallback,
            "timeout": str(telemetry.get("timeout_flag")).lower() == "true",
        }
        for source_key, target_key in (
            ("provider_call_count", "providerCallCount"),
            ("provider_total_ms", "providerTotalMs"),
            ("db_query_count", "dbQueryCount"),
            ("db_total_ms", "dbTotalMs"),
        ):
            value = _safe_telemetry_int(telemetry.get(source_key))
            if value is not None:
                row[target_key] = value
        if isinstance(telemetry.get("cache_hit"), bool):
            row["cacheHit"] = bool(telemetry["cache_hit"])
        reason = str(telemetry.get("telemetry_unavailable_reason") or "").strip()
        if reason:
            row["telemetryUnavailableReason"] = reason[:80]
        rows.append(row)
    return rows


def _build_performance_telemetry(
    *,
    plan: Mapping[str, Any],
    execute_started: float,
    production_non_l4_summary: Mapping[str, Any],
    external_l4_compute_default_summary: Mapping[str, Any],
    external_demo_summary: Mapping[str, Any],
) -> dict[str, Any]:
    step_metadata = _step_metadata_by_agent(plan)
    rows = [
        *_performance_rows_for_summary(
            production_non_l4_summary,
            runtime_source="production_external_compute",
            step_metadata=step_metadata,
        ),
        *_performance_rows_for_summary(
            external_l4_compute_default_summary,
            runtime_source="external_compute_default",
            step_metadata=step_metadata,
        ),
        *_performance_rows_for_summary(
            external_demo_summary,
            runtime_source="external_compute_demo",
            step_metadata=step_metadata,
        ),
    ]
    if not rows:
        return {}
    gaps = []
    if any(row.get("providerCallCount") is None for row in rows):
        gaps.append("provider_timing_not_reported_by_some_services")
    if any(row.get("dbQueryCount") is None for row in rows):
        gaps.append("db_timing_not_reported_by_some_services")
    return {
        "graphTotalMs": max(0, int(round((time.monotonic() - execute_started) * 1000))),
        "executeFixedDagMs": max(0, int(round((time.monotonic() - execute_started) * 1000))),
        "computeCallCount": len(rows),
        "providerCallCount": _telemetry_sum(rows, "providerCallCount"),
        "providerTotalMs": _telemetry_sum(rows, "providerTotalMs"),
        "dbQueryCount": _telemetry_sum(rows, "dbQueryCount"),
        "dbTotalMs": _telemetry_sum(rows, "dbTotalMs"),
        "perAgentCompute": rows,
        "instrumentationGaps": gaps,
    }


def _safe_report_value(value: Any, *, limit: int = 80) -> str:
    text = str(value or "").strip()
    text = text.replace("\n", " ").replace("\r", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _dimension_demo_line(label: str, result: Mapping[str, Any] | None) -> str:
    if not isinstance(result, Mapping):
        return f"{label}：本轮没有可用的外部 compute 映射结果。"
    confidence = result.get("confidence", 0.0)
    try:
        confidence_text = f"{float(confidence):.2f}"
    except (TypeError, ValueError):
        confidence_text = "n/a"
    if result.get("dimension") == "risk":
        gate = _safe_report_value(result.get("gate") or result.get("stance") or "risk_gate")
        risk_score = result.get("risk_score", 0.0)
        try:
            risk_text = f"{float(risk_score):.2f}"
        except (TypeError, ValueError):
            risk_text = "n/a"
        return f"{label}：风险门为 {gate}，风险分 {risk_text}，置信度 {confidence_text}。"
    if result.get("dimension") == "macro":
        regime = _safe_report_value(result.get("regime") or result.get("stance") or "macro_regulator")
        weights = result.get("dimension_weights", {})
        if isinstance(weights, Mapping):
            weight_text = ", ".join(
                f"{_safe_report_value(key)}={value}"
                for key, value in weights.items()
                if key in {"value", "market"}
            )
        else:
            weight_text = "n/a"
        return f"{label}：宏观状态 {regime}，value/market 权重 {weight_text}，置信度 {confidence_text}。"
    stance = _safe_report_value(result.get("stance") or "not_evaluated")
    contributors = result.get("contributing_agents", [])
    contributor_text = len(contributors) if isinstance(contributors, list) else 0
    return f"{label}：综合 stance={stance}，参与成员 {contributor_text} 个，置信度 {confidence_text}。"


def _l2_demo_summary_lines(l2_conclusions: Mapping[str, Any]) -> list[str]:
    labels = {
        "value": "估值信号",
        "market": "市场信号",
        "risk": "风险成员",
        "macro": "宏观成员",
    }
    lines: list[str] = []
    for dimension in ("value", "market", "risk", "macro"):
        items = [
            item
            for item in l2_conclusions.values()
            if isinstance(item, Mapping)
            and item.get("dimension") == dimension
            and item.get("status") in {"complete", "partial"}
            and isinstance(item.get("provenance"), Mapping)
            and item["provenance"].get("adapter_source")
        ]
        if not items:
            continue
        sample = items[:3]
        text = "；".join(
            f"{_safe_report_value(item.get('agent_id'))}: "
            f"{_safe_report_value(item.get('stance'))}, "
            f"confidence={item.get('confidence', 0.0)}"
            for item in sample
        )
        suffix = "；..." if len(items) > len(sample) else ""
        lines.append(f"{labels[dimension]}：{text}{suffix}")
    return lines


def _augment_report_with_external_compute_demo(
    report_result: Mapping[str, Any],
    *,
    l2_conclusions: Mapping[str, Any],
    dimension_results: Mapping[str, Any],
    demo_summary: Mapping[str, Any],
) -> dict[str, Any]:
    mapped_agents = [
        str(agent_id)
        for agent_id in demo_summary.get("mapped_agents", [])
        if str(agent_id or "")
    ]
    if not mapped_agents:
        return dict(report_result)

    dimension_lines = [
        _dimension_demo_line("估值综合", cast(Mapping[str, Any] | None, dimension_results.get("value"))),
        _dimension_demo_line("市场综合", cast(Mapping[str, Any] | None, dimension_results.get("market"))),
        _dimension_demo_line("风险闸门", cast(Mapping[str, Any] | None, dimension_results.get("risk"))),
        _dimension_demo_line("宏观调节", cast(Mapping[str, Any] | None, dimension_results.get("macro"))),
    ]
    l2_lines = _l2_demo_summary_lines(l2_conclusions)
    demo_body = "\n".join(
        [
            "本次研判使用固定 DAG 流程，并在演示模式下读取了若干已通过生产 compute smoke 的外部智能体结构化结果。",
            "这些结果只用于演示默认关闭的结构化接入，不代表默认启用或正式生产接入承诺。",
            *l2_lines,
            *dimension_lines,
            "综合结论：当前页面展示的是结构化接入链路和审慎研判框架，仍需业务 owner 对结果含义负责。",
        ]
    )
    answer = str(report_result.get("answer") or "")
    if demo_body not in answer:
        answer = f"{answer}\n\n外部计算演示摘要：\n{demo_body}"
    sections = list(report_result.get("sections", []) or [])
    sections.append(
        {
            "id": "external_compute_demo",
            "title": "外部计算演示",
            "content": demo_body,
        }
    )
    evidence_cards = list(report_result.get("evidence_cards", []) or [])
    evidence_cards.append(
        {
            "title": "外部 compute 演示来源",
            "note": f"本轮映射 {len(mapped_agents)} 个 allowlist agent；未调用 invoke 接口。",
        }
    )
    limitations = list(report_result.get("limitations", []) or [])
    limitation = (
        "外部 compute demo 为显式开关 + allowlist 模式，不改变默认运行配置。"
    )
    if limitation not in limitations:
        limitations.append(limitation)
    return {
        **dict(report_result),
        "answer": answer,
        "status": "partial",
        "sections": sections,
        "evidence_cards": evidence_cards,
        "limitations": limitations,
    }


def _attach_agent_runtime_status_to_report_input_bundle(
    report_input_bundle: dict[str, Any],
    *,
    production_non_l4_summary: Mapping[str, Any],
    external_l4_compute_default_summary: Mapping[str, Any],
    external_demo_summary: Mapping[str, Any],
) -> None:
    evidence_bundle = report_input_bundle.get("agent_evidence_bundle")
    if not isinstance(evidence_bundle, dict):
        return
    status_by_id: dict[str, dict[str, Any]] = {}

    def merge_run(summary: Mapping[str, Any], runtime_source: str) -> None:
        called = {str(agent_id) for agent_id in summary.get("called_agents", [])}
        mapped = {str(agent_id) for agent_id in summary.get("mapped_agents", [])}
        failed = {str(agent_id) for agent_id in summary.get("failed_agents", [])}
        fallback = {str(agent_id) for agent_id in summary.get("fallback_agents", [])}
        for agent_id in sorted(called | mapped | failed | fallback):
            row = status_by_id.setdefault(agent_id, {"agent_id": agent_id})
            row["runtime_source"] = runtime_source
            row["attempted"] = bool(row.get("attempted")) or agent_id in called
            row["mapped"] = bool(row.get("mapped")) or agent_id in mapped
            row["failed"] = bool(row.get("failed")) or agent_id in failed
            row["fallback"] = bool(row.get("fallback")) or agent_id in fallback
        for warning in summary.get("warnings", []):
            text = str(warning or "")
            parts = text.split(":")
            if len(parts) < 3:
                continue
            agent_id = parts[1]
            row = status_by_id.setdefault(agent_id, {"agent_id": agent_id})
            row.setdefault("runtime_source", runtime_source)
            row["adapter_failure_code"] = parts[-1][:120]

    merge_run(production_non_l4_summary, "production_external_compute")
    merge_run(external_l4_compute_default_summary, "external_compute_default")
    merge_run(external_demo_summary, "external_compute_demo")
    if status_by_id:
        evidence_bundle["agent_runtime_status_by_id"] = status_by_id


def _maybe_enrich_weak_report_result(
    report_result: dict[str, Any],
    *,
    question: str,
    report_input_bundle: Mapping[str, Any],
    decision_result: Mapping[str, Any],
) -> dict[str, Any]:
    from react_agent.fixed_dag.report_quality_renderer import (  # noqa: PLC0415
        build_enriched_report_result_from_bundle,
        report_result_has_unsafe_markers,
        should_enrich_report_result,
    )

    should_enrich, _reason = should_enrich_report_result(
        existing_report_result=report_result,
        report_input_bundle=report_input_bundle,
        decision_result=decision_result,
    )
    if not should_enrich:
        return report_result
    evidence_bundle = report_input_bundle.get("agent_evidence_bundle")
    if not isinstance(evidence_bundle, Mapping):
        return report_result
    try:
        enriched = build_enriched_report_result_from_bundle(
            question=question,
            agent_evidence_bundle=evidence_bundle,
            existing_report_result=report_result,
        )
    except (TypeError, ValueError):
        return report_result
    valid, _validate_reason = validate_report_result(enriched)
    if not valid or report_result_has_unsafe_markers(enriched):
        return report_result
    return dict(enriched)


def _agent_provider_call_count(
    summary: Mapping[str, Any],
    agent_id: str,
) -> int:
    telemetry_by_agent = summary.get("agent_telemetry_by_agent")
    if not isinstance(telemetry_by_agent, Mapping):
        return 0
    telemetry = telemetry_by_agent.get(agent_id)
    if not isinstance(telemetry, Mapping):
        return 0
    try:
        return max(int(telemetry.get("provider_call_count") or 0), 0)
    except (TypeError, ValueError):
        return 0


def execute_fixed_dag_plan(
    plan: Mapping[str, Any],
    *,
    question: str,
    as_of: str,
    context: Any | None = None,
) -> dict:
    """Execute a fixed DAG plan without external agent calls."""
    execute_started = time.monotonic()
    execution_plan, fallback_used, fallback_reason = _execution_plan_or_fallback(
        plan,
        question=question,
        as_of=as_of,
    )
    valid, reason = _execution_plan_valid(execution_plan)
    if not valid:
        execution_plan = build_default_fixed_dag_plan(question, as_of=as_of)
        fallback_used = True
        fallback_reason = reason

    batches = _execution_batches(execution_plan)
    step_index = build_dag_step_index(execution_plan)
    step_results: dict[str, dict] = {}
    for batch in batches:
        for step_id in batch:
            step = step_index[step_id]
            step_results[step_id] = build_step_result(
                step,
                status=_status_for_step(step),
                output_ref=_output_ref_for_step(step),
                summary=_summary_for_step(step),
            )

    data_bundle = build_data_bundle(execution_plan)
    entity_relation_bundle = build_entity_relation_bundle(execution_plan)
    l2_agent_tasks = build_agent_tasks_for_plan(
        execution_plan,
        question=question,
        as_of=as_of,
        data_bundle=data_bundle,
        entity_relation_bundle=entity_relation_bundle,
    )
    internal_placeholders_enabled = bool(
        getattr(context, "enable_internal_llm_placeholders", False)
    )
    if internal_placeholders_enabled:
        l2_conclusions = build_l2_conclusions_with_internal_placeholders(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            agent_tasks=l2_agent_tasks,
        )
    else:
        l2_conclusions = build_l2_conclusions(execution_plan, as_of=as_of)

    external_compute_demo_enabled = bool(
        getattr(context, "enable_external_compute_demo", False)
    )
    external_compute_default_disabled = context is None or bool(
        getattr(context, "disable_external_compute_default", False)
    )
    external_compute_default_ids = (
        set()
        if external_compute_default_disabled
        else set(external_compute_default_agent_ids())
    )
    l4_compute_default_ids = external_compute_default_ids & {
        "decision_synthesizer",
        "report_generator",
    }
    external_l4_compute_default_enabled = bool(l4_compute_default_ids)
    llm_report_synthesis_enabled = bool(
        getattr(context, "enable_llm_report_synthesis", False)
    )
    llm_l3_explanation_enabled = bool(
        getattr(context, "enable_llm_l3_explanation", False)
    )
    external_l1_run: Mapping[str, Any] = {}
    external_l2_run: Mapping[str, Any] = {}
    external_l3_run: Mapping[str, Any] = {}
    external_l4_decision_run: Mapping[str, Any] = {}
    external_l4_report_run: Mapping[str, Any] = {}
    production_l2_run: Mapping[str, Any] = {}
    production_l3_run: Mapping[str, Any] = {}
    production_non_l4_summary: Mapping[str, Any] = {
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "fallback_agents": [],
        "skipped_agents": [],
        "warnings": [],
        "latency_ms_by_agent": {},
        "required_failures": [],
        "optional_failures": [],
        "policy_enabled": False,
        "policy_version": "",
        "demo_suppressed": external_compute_demo_enabled,
        "rollback_disabled": bool(
            getattr(context, "disable_non_l4_external_compute_default", False)
        ),
    }
    external_l4_compute_default_summary: Mapping[str, Any] = {
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "warnings": [],
    }
    external_demo_summary: Mapping[str, Any] = {
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "warnings": [],
    }
    if external_compute_demo_enabled:
        from react_agent.fixed_dag_external_compute_bridge import (  # noqa: PLC0415
            merge_external_compute_demo_runs,
            run_external_compute_for_plan,
        )

        l1_agent_tasks = build_agent_tasks_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
        )
        external_l1_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            l2_conclusions={},
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            agent_tasks=l1_agent_tasks,
            stages=("evidence",),
        )
        data_bundle = cast(dict[str, Any], external_l1_run["data_bundle"])
        entity_relation_bundle = cast(
            dict[str, Any],
            external_l1_run["entity_relation_bundle"],
        )
        l2_agent_tasks = build_agent_tasks_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
        )
        external_l2_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            l2_conclusions=l2_conclusions,
            agent_tasks=l2_agent_tasks,
            stages=("l2_analysis",),
        )
        l2_conclusions = cast(dict[str, Any], external_l2_run["l2_conclusions"])
    if not external_compute_demo_enabled:
        from react_agent.fixed_dag_production_external_compute import (  # noqa: PLC0415
            run_production_external_compute_for_plan,
        )

        production_l2_run = run_production_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            agent_tasks=l2_agent_tasks,
            stages=("l2_analysis",),
        )
        l2_conclusions = cast(dict[str, Any], production_l2_run["l2_conclusions"])
    dimension_results = build_dimension_results(l2_conclusions, as_of=as_of)
    if external_compute_demo_enabled:
        l3_agent_tasks = build_agent_tasks_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
        )
        external_l3_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            agent_tasks=l3_agent_tasks,
            stages=("dimension_composite",),
        )
        l2_conclusions = cast(dict[str, Any], external_l3_run["l2_conclusions"])
        dimension_results = cast(dict[str, Any], external_l3_run["dimension_results"])
        _apply_external_compute_step_updates(
            step_results,
            external_l1_run,
            external_l2_run,
            external_l3_run,
        )
        external_demo_summary = merge_external_compute_demo_runs(
            external_l1_run,
            external_l2_run,
            external_l3_run,
        )
    else:
        l3_agent_tasks = build_agent_tasks_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
        )
        include_optional_canary = tuple(
            str(item)
            for item in getattr(
                context,
                "non_l4_external_compute_optional_canary_allowlist",
                (),
            )
            if str(item)
        )
        production_l3_run = run_production_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            l2_conclusions=l2_conclusions,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            dimension_results=dimension_results,
            agent_tasks=l3_agent_tasks,
            stages=("dimension_composite",),
            include_optional_canary=include_optional_canary,
        )
        l2_conclusions = cast(dict[str, Any], production_l3_run["l2_conclusions"])
        dimension_results = cast(dict[str, Any], production_l3_run["dimension_results"])
        _apply_external_compute_step_updates(
            step_results,
            production_l2_run,
            production_l3_run,
        )
        production_non_l4_summary = _merge_production_external_compute_runs(
            production_l2_run,
            production_l3_run,
        )
    llm_l3_explanation_used = False
    llm_l3_explanation_attempted = False
    llm_l3_explanation_provider_invoked = False
    llm_l3_explanation_fallback_reason = ""
    llm_l3_explanation_provider_config: dict[str, Any] = {}
    if llm_l3_explanation_enabled:
        from react_agent.fixed_dag_l3_explanation_synthesizer import (  # noqa: PLC0415
            synthesize_l3_explanations,
        )

        l3_explanation_outcome = synthesize_l3_explanations(
            question=question,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            context=context,
        )
        dimension_results = cast(dict[str, Any], l3_explanation_outcome["dimension_results"])
        llm_l3_explanation_used = bool(l3_explanation_outcome["used_llm_explanation"])
        llm_l3_explanation_attempted = bool(l3_explanation_outcome["attempted"])
        llm_l3_explanation_provider_invoked = bool(l3_explanation_outcome["provider_invoked"])
        llm_l3_explanation_fallback_reason = str(l3_explanation_outcome["fallback_reason"])
        llm_l3_explanation_provider_config = dict(l3_explanation_outcome["provider_config"])
    decision_result = build_decision_result(dimension_results, as_of=as_of)
    agent_tasks = build_agent_tasks_for_plan(
        execution_plan,
        question=question,
        as_of=as_of,
        data_bundle=data_bundle,
        entity_relation_bundle=entity_relation_bundle,
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
        decision_result=decision_result,
    )
    if "decision_synthesizer" in l4_compute_default_ids:
        from react_agent.fixed_dag_external_compute_bridge import (  # noqa: PLC0415
            EXTERNAL_COMPUTE_DEFAULT_SOURCE,
            merge_external_compute_demo_runs,
            run_external_compute_for_plan,
            runtime_compute_entries_from_bindings,
        )

        external_l4_decision_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            decision_result=decision_result,
            agent_tasks=agent_tasks,
            stages=("decision",),
            allowlist_override=("decision_synthesizer",),
            entry_registry=runtime_compute_entries_from_bindings(),
            runtime_source=EXTERNAL_COMPUTE_DEFAULT_SOURCE,
        )
        decision_result = cast(
            dict[str, Any],
            external_l4_decision_run.get("decision_result") or decision_result,
        )
        _apply_external_compute_step_updates(step_results, external_l4_decision_run)
        external_l4_compute_default_summary = merge_external_compute_demo_runs(
            external_l4_compute_default_summary,
            external_l4_decision_run,
        )
        agent_tasks = build_agent_tasks_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            decision_result=decision_result,
        )
    elif external_compute_demo_enabled:
        external_l4_decision_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            decision_result=decision_result,
            agent_tasks=agent_tasks,
            stages=("decision",),
        )
        decision_result = cast(
            dict[str, Any],
            external_l4_decision_run.get("decision_result") or decision_result,
        )
        agent_tasks = build_agent_tasks_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            decision_result=decision_result,
        )
    report_input_bundle = build_report_input_bundle(
        question=question,
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
        decision_result=decision_result,
        agent_tasks=agent_tasks,
        data_bundle=data_bundle,
        entity_relation_bundle=entity_relation_bundle,
        selected_dimensions=list(execution_plan.get("selected_dimensions") or [])
        if execution_plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION
        else None,
    )
    _attach_agent_runtime_status_to_report_input_bundle(
        report_input_bundle,
        production_non_l4_summary=production_non_l4_summary,
        external_l4_compute_default_summary=external_l4_compute_default_summary,
        external_demo_summary=external_demo_summary,
    )
    valid_report_input_bundle, _report_input_bundle_reason = validate_report_input_bundle(
        report_input_bundle
    )
    if valid_report_input_bundle:
        _attach_report_input_bundle_to_step_results(step_results, report_input_bundle)
    report_result = build_report_result(
        decision_result,
        question=question,
        report_input_bundle=report_input_bundle,
    )
    if "report_generator" in l4_compute_default_ids:
        from react_agent.fixed_dag_external_compute_bridge import (  # noqa: PLC0415
            EXTERNAL_COMPUTE_DEFAULT_SOURCE,
            merge_external_compute_demo_runs,
            run_external_compute_for_plan,
            runtime_compute_entries_from_bindings,
        )

        external_l4_report_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            decision_result=decision_result,
            report_result=report_result,
            report_input_bundle=report_input_bundle,
            agent_tasks=agent_tasks,
            stages=("report",),
            allowlist_override=("report_generator",),
            entry_registry=runtime_compute_entries_from_bindings(),
            runtime_source=EXTERNAL_COMPUTE_DEFAULT_SOURCE,
        )
        report_result = cast(
            dict[str, Any],
            external_l4_report_run.get("report_result") or report_result,
        )
        _apply_external_compute_step_updates(step_results, external_l4_report_run)
        external_l4_compute_default_summary = merge_external_compute_demo_runs(
            external_l4_compute_default_summary,
            external_l4_report_run,
        )
    elif external_compute_demo_enabled:
        report_result = _augment_report_with_external_compute_demo(
            report_result,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            demo_summary=external_demo_summary,
        )
        external_l4_report_run = run_external_compute_for_plan(
            execution_plan,
            question=question,
            as_of=as_of,
            context=context,
            data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions,
            dimension_results=dimension_results,
            decision_result=decision_result,
            report_result=report_result,
            report_input_bundle=report_input_bundle,
            agent_tasks=agent_tasks,
            stages=("report",),
        )
        report_result = cast(
            dict[str, Any],
            external_l4_report_run.get("report_result") or report_result,
        )
        _apply_external_compute_step_updates(
            step_results,
            external_l4_decision_run,
            external_l4_report_run,
        )
        external_demo_summary = merge_external_compute_demo_runs(
            external_demo_summary,
            external_l4_decision_run,
            external_l4_report_run,
        )
    llm_report_synthesis_used = False
    llm_report_synthesis_attempted = False
    llm_report_synthesis_provider_invoked = False
    llm_report_synthesis_fallback_reason = ""
    llm_report_synthesis_provider_config: dict[str, Any] = {}
    external_l4_report_mapped = (
        isinstance(external_l4_report_run, Mapping)
        and "report_generator" in set(external_l4_report_run.get("mapped_agents", []))
    )
    external_l4_report_provider_invoked = (
        _agent_provider_call_count(external_l4_report_run, "report_generator") > 0
    )
    if valid_report_input_bundle and not external_l4_report_provider_invoked:
        report_result = _maybe_enrich_weak_report_result(
            report_result,
            question=question,
            report_input_bundle=report_input_bundle,
            decision_result=decision_result,
        )
    if llm_report_synthesis_enabled and not external_l4_report_mapped:
        from react_agent.fixed_dag_report_synthesizer import (  # noqa: PLC0415
            synthesize_report_result_with_llm,
        )

        synthesis_outcome = synthesize_report_result_with_llm(
            question=question,
            report_input_bundle=report_input_bundle,
            fallback_report_result=report_result,
            context=context,
        )
        report_result = synthesis_outcome["report_result"]
        llm_report_synthesis_used = bool(synthesis_outcome["used_llm_report"])
        llm_report_synthesis_attempted = bool(synthesis_outcome["attempted"])
        llm_report_synthesis_provider_invoked = bool(synthesis_outcome["provider_invoked"])
        llm_report_synthesis_fallback_reason = str(synthesis_outcome["fallback_reason"])
        llm_report_synthesis_provider_config = dict(synthesis_outcome["provider_config"])
    internal_placeholder_count = sum(
        1
        for item in l2_conclusions.values()
        if isinstance(item, Mapping)
        and isinstance(item.get("provenance"), Mapping)
        and item["provenance"].get("runtime_path") == INTERNAL_LLM_PLACEHOLDER_SOURCE
    )
    limitations = [
        "当前为本地固定流程模式。",
        "高级连接状态可在设置诊断中查看。",
    ]
    if external_compute_demo_enabled:
        if external_demo_summary.get("mapped_agents"):
            limitations.append(
                "已在显式演示开关 + allowlist 下读取部分生产 /compute 结构化结果；"
                "这不是默认运行配置变更。"
            )
        else:
            limitations.append(
                "external compute demo 演示开关已开启，但没有 allowlist agent 完成映射；"
                "执行已回退到本地固定流程。"
            )
    if llm_report_synthesis_enabled:
        if llm_report_synthesis_used:
            limitations.append(
                "已在显式演示开关下使用大模型读取结构化报告输入包生成最终报告；"
                "这不是默认运行配置变更。"
            )
        elif external_l4_report_mapped:
            limitations.append(
                "外部 L4 report_generator 已在显式 compute allowlist 下生成报告；"
                "主系统内置 LLM report synthesizer 未重复覆盖该结果。"
            )
        else:
            limitations.append(
                "大模型报告综合开关已开启，但未生成有效报告，已回退到模板报告。"
            )
    if external_l4_compute_default_enabled:
        if external_l4_compute_default_summary.get("mapped_agents"):
            limitations.append(
                "L4 决策/报告已通过 runtime binding 默认 /compute 路径生成；"
                "未调用外部智能体 invoke 接口。"
            )
        else:
            limitations.append(
                "L4 runtime binding 默认 /compute 路径已启用，但未完成有效映射；"
                "执行已回退到确定性 L4 结果。"
            )
    if production_non_l4_summary.get("policy_enabled"):
        mapped_agents = list(production_non_l4_summary.get("mapped_agents", []))
        required_failures = list(production_non_l4_summary.get("required_failures", []))
        if mapped_agents:
            limitations.append(
                "已通过 production non-L4 /compute 默认编排读取部分 L2/L3 外部结构化结果；"
                "L1 仍使用本地确定性输入，未调用 /invoke。"
            )
        if required_failures:
            limitations.append(
                "部分 required non-L4 外部 compute 未完成映射，已按固定 DAG 合同回退到本地 pending/确定性结果。"
            )
    elif production_non_l4_summary.get("rollback_disabled"):
        limitations.append(
            "production non-L4 默认编排已被回滚开关关闭；L4 默认 compute 不受影响。"
        )
    elif production_non_l4_summary.get("demo_suppressed"):
        limitations.append(
            "显式 external compute demo 模式开启时，production non-L4 默认编排不会重复调用。"
        )
    if llm_l3_explanation_enabled:
        if llm_l3_explanation_used:
            limitations.append(
                "已在显式演示开关下使用大模型补充 L3 综合解释；"
                "该解释不覆盖确定性 L3 stance、gate、risk_score、权重或状态。"
            )
        else:
            limitations.append(
                "L3 大模型解释开关已开启，但未生成有效解释，已保留确定性 L3 结果。"
            )
    if fallback_used:
        limitations.append(f"无效计划已回退到确定性默认计划：{fallback_reason}。")

    production_required_failures = list(
        production_non_l4_summary.get("required_failures", [])
        if isinstance(production_non_l4_summary, Mapping)
        else []
    )
    execution_core = {
        "schema_version": FIXED_DAG_EXECUTION_SCHEMA_VERSION,
        "plan_id": str(execution_plan.get("plan_id") or "reset-fixed-dag-plan-v1"),
        "status": "degraded" if fallback_used or production_required_failures else "complete",
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason if fallback_used else "",
        "execution_batches": batches,
        "step_results": step_results,
        "data_bundle": data_bundle,
        "entity_relation_bundle": entity_relation_bundle,
        "l2_conclusions": l2_conclusions,
        "dimension_results": dimension_results,
        "decision_result": decision_result,
        "agent_task_summaries": build_agent_task_summaries(agent_tasks),
        "report_input_bundle": report_input_bundle,
        "report_result": report_result,
        "limitations": limitations,
        "provenance": {
            "source": "fixed_dag_executor",
            "provider_invoked": (
                llm_report_synthesis_provider_invoked
                or llm_l3_explanation_provider_invoked
                or external_l4_report_provider_invoked
            ),
            "external_invoked": False,
            "production_external_compute_enabled": bool(
                production_non_l4_summary.get("policy_enabled")
            ),
            "production_external_compute_policy_version": str(
                production_non_l4_summary.get("policy_version") or ""
            ),
            "production_external_compute_called_agents": list(
                production_non_l4_summary.get("called_agents", [])
            ),
            "production_external_compute_mapped_agents": list(
                production_non_l4_summary.get("mapped_agents", [])
            ),
            "production_external_compute_failed_agents": list(
                production_non_l4_summary.get("failed_agents", [])
            ),
            "production_external_compute_fallback_agents": list(
                production_non_l4_summary.get("fallback_agents", [])
            ),
            "production_external_compute_skipped_agents": list(
                production_non_l4_summary.get("skipped_agents", [])
            ),
            "production_external_compute_latency_ms_by_agent": dict(
                production_non_l4_summary.get("latency_ms_by_agent", {})
            ),
            "production_external_compute_required_failures": list(
                production_non_l4_summary.get("required_failures", [])
            ),
            "production_external_compute_optional_failures": list(
                production_non_l4_summary.get("optional_failures", [])
            ),
            "production_external_compute_demo_suppressed": bool(
                production_non_l4_summary.get("demo_suppressed")
            ),
            "production_external_compute_rollback_disabled": bool(
                production_non_l4_summary.get("rollback_disabled")
            ),
            "external_compute_default_disabled": external_compute_default_disabled,
            "external_compute_default_enabled": external_l4_compute_default_enabled,
            "external_compute_default_called_agents": list(
                external_l4_compute_default_summary.get("called_agents", [])
            ),
            "external_compute_default_mapped_agents": list(
                external_l4_compute_default_summary.get("mapped_agents", [])
            ),
            "external_compute_default_failed_agents": list(
                external_l4_compute_default_summary.get("failed_agents", [])
            ),
            "internal_llm_placeholders_enabled": internal_placeholders_enabled,
            "internal_llm_placeholder_conclusions": internal_placeholder_count,
            "external_compute_demo_enabled": external_compute_demo_enabled,
            "external_compute_demo_called_agents": list(
                external_demo_summary.get("called_agents", [])
            ),
            "external_compute_demo_mapped_agents": list(
                external_demo_summary.get("mapped_agents", [])
            ),
            "external_compute_demo_failed_agents": list(
                external_demo_summary.get("failed_agents", [])
            ),
            "llm_report_synthesis_enabled": llm_report_synthesis_enabled,
            "llm_report_synthesis_attempted": llm_report_synthesis_attempted,
            "llm_report_synthesis_used": llm_report_synthesis_used,
            "llm_report_synthesis_fallback_reason": llm_report_synthesis_fallback_reason,
            "llm_report_synthesis_provider_config": llm_report_synthesis_provider_config,
            "llm_l3_explanation_enabled": llm_l3_explanation_enabled,
            "llm_l3_explanation_attempted": llm_l3_explanation_attempted,
            "llm_l3_explanation_used": llm_l3_explanation_used,
            "llm_l3_explanation_fallback_reason": llm_l3_explanation_fallback_reason,
            "llm_l3_explanation_provider_config": llm_l3_explanation_provider_config,
            "performance_telemetry": _build_performance_telemetry(
                plan=execution_plan,
                execute_started=execute_started,
                production_non_l4_summary=production_non_l4_summary,
                external_l4_compute_default_summary=external_l4_compute_default_summary,
                external_demo_summary=external_demo_summary,
            ),
        },
    }
    workflow_snapshot = build_workflow_snapshot_v2(
        plan=execution_plan,
        l2_conclusions=l2_conclusions,
        dimension_results=dimension_results,
        decision_result=decision_result,
        report_result=report_result,
        dag_execution=execution_core,
        step_results=step_results,
        execution_batches=batches,
        current_stage="report",
    )
    return {**execution_core, "workflow_snapshot": workflow_snapshot}
def _build_fixed_dag_setup(plan, question, as_of):
    """Shared setup: validate plan, build batches, step_results, data + entity bundles."""
    execution_plan, fallback_used, fallback_reason = _execution_plan_or_fallback(
        plan, question=question, as_of=as_of,
    )
    valid, reason = _execution_plan_valid(execution_plan)
    if not valid:
        execution_plan = build_default_fixed_dag_plan(question, as_of=as_of)
        fallback_used, fallback_reason = True, reason
    batches = _execution_batches(execution_plan)
    step_index = build_dag_step_index(execution_plan)
    step_results: dict[str, dict] = {}
    for batch in batches:
        for step_id in batch:
            step = step_index[step_id]
            step_results[step_id] = build_step_result(
                step,
                status=_status_for_step(step),
                output_ref=_output_ref_for_step(step),
                summary=_summary_for_step(step),
            )
    data_bundle = build_data_bundle(execution_plan)
    entity_relation_bundle = build_entity_relation_bundle(execution_plan)
    return execution_plan, batches, step_results, data_bundle, entity_relation_bundle, fallback_used, fallback_reason


def run_fixed_dag_l2_phase(
    plan,
    *,
    question,
    as_of,
    context = None,
):
    """Execute L2 phase: plan validation + build conclusions + external compute overlay."""
    execution_plan, batches, step_results, data_bundle, entity_relation_bundle, fallback_used, fallback_reason = (
        _build_fixed_dag_setup(plan, question, as_of)
    )
    l2_agent_tasks = build_agent_tasks_for_plan(
        execution_plan, question=question, as_of=as_of,
        data_bundle=data_bundle, entity_relation_bundle=entity_relation_bundle,
    )
    internal_placeholders_enabled = bool(
        getattr(context, "enable_internal_llm_placeholders", False)
    )
    if internal_placeholders_enabled:
        l2_conclusions = build_l2_conclusions_with_internal_placeholders(
            execution_plan, question=question, as_of=as_of,
            context=context, agent_tasks=l2_agent_tasks,
        )
    else:
        l2_conclusions = build_l2_conclusions(execution_plan, as_of=as_of)

    if bool(getattr(context, "enable_external_compute_demo", False)):
        from react_agent.fixed_dag_external_compute_bridge import (
            run_external_compute_for_plan,
        )
        l1_tasks = build_agent_tasks_for_plan(
            execution_plan, question=question, as_of=as_of,
            data_bundle=data_bundle, entity_relation_bundle=entity_relation_bundle,
        )
        ext_l1 = run_external_compute_for_plan(
            execution_plan, question=question, as_of=as_of, context=context,
            l2_conclusions={}, data_bundle=data_bundle,
            entity_relation_bundle=entity_relation_bundle, agent_tasks=l1_tasks,
            stages=("evidence",),
        )
        data_bundle = dict(ext_l1.get("data_bundle") or data_bundle)
        entity_relation_bundle = dict(ext_l1.get("entity_relation_bundle") or entity_relation_bundle)
        l2_tasks = build_agent_tasks_for_plan(
            execution_plan, question=question, as_of=as_of,
            data_bundle=data_bundle, entity_relation_bundle=entity_relation_bundle,
        )
        ext_l2 = run_external_compute_for_plan(
            execution_plan, question=question, as_of=as_of, context=context,
            l2_conclusions=l2_conclusions, agent_tasks=l2_tasks,
            stages=("l2_analysis",),
        )
        l2_conclusions = dict(ext_l2.get("l2_conclusions") or l2_conclusions)
    else:
        from react_agent.fixed_dag_production_external_compute import (
            run_production_external_compute_for_plan,
        )
        prod_l2 = run_production_external_compute_for_plan(
            execution_plan, question=question, as_of=as_of, context=context,
            data_bundle=data_bundle, entity_relation_bundle=entity_relation_bundle,
            l2_conclusions=l2_conclusions, agent_tasks=l2_agent_tasks,
            stages=("l2_analysis",),
        )
        l2_conclusions = dict(prod_l2.get("l2_conclusions") or l2_conclusions)

    return {
        "_execution_plan": execution_plan,
        "_batches": batches,
        "_step_results": step_results,
        "_fallback_used": fallback_used,
        "_fallback_reason": fallback_reason,
        "dag_step_results": step_results,
        "execution_batches": batches,
        "data_bundle": data_bundle,
        "entity_relation_bundle": entity_relation_bundle,
        "l2_conclusions": l2_conclusions,
    }


def run_fixed_dag_l3_phase(
    plan,
    l2_conclusions,
    *,
    context = None,
    as_of = "",
):
    """Execute L3 phase: build dimension composites + external compute overlay + explanation."""
    l2 = dict(l2_conclusions)
    execution_plan = plan
    as_of_val = as_of or str(plan.get("as_of") or "")
    dimension_results = build_dimension_results(l2, as_of=as_of_val)
    if bool(getattr(context, "enable_external_compute_demo", False)):
        from react_agent.fixed_dag_external_compute_bridge import (
            run_external_compute_for_plan,
        )
        l3_tasks = build_agent_tasks_for_plan(
            execution_plan, question=str(plan.get("user_text") or ""), as_of=as_of_val,
            l2_conclusions=l2, dimension_results=dimension_results,
        )
        ext_l3 = run_external_compute_for_plan(
            execution_plan, question=str(plan.get("user_text") or ""), as_of=as_of_val,
            context=context, l2_conclusions=l2,
            dimension_results=dimension_results, agent_tasks=l3_tasks,
            stages=("dimension_composite",),
        )
        l2 = dict(ext_l3.get("l2_conclusions") or l2)
        dimension_results = dict(ext_l3.get("dimension_results") or dimension_results)
    else:
        from react_agent.fixed_dag_production_external_compute import (
            run_production_external_compute_for_plan,
        )
        l3_tasks = build_agent_tasks_for_plan(
            execution_plan, question=str(plan.get("user_text") or ""), as_of=as_of_val,
            l2_conclusions=l2, dimension_results=dimension_results,
        )
        prod_l3 = run_production_external_compute_for_plan(
            execution_plan, question=str(plan.get("user_text") or ""), as_of=as_of_val,
            context=context, l2_conclusions=l2,
            dimension_results=dimension_results, agent_tasks=l3_tasks,
            stages=("dimension_composite",),
        )
        l2 = dict(prod_l3.get("l2_conclusions") or l2)
        dimension_results = dict(prod_l3.get("dimension_results") or dimension_results)

    if bool(getattr(context, "enable_llm_l3_explanation", False)):
        from react_agent.fixed_dag_l3_explanation_synthesizer import (
            synthesize_l3_explanations,
        )
        l3_outcome = synthesize_l3_explanations(
            question=str(plan.get("user_text") or ""),
            l2_conclusions=l2,
            dimension_results=dimension_results,
            context=context,
        )
        dimension_results = dict(l3_outcome.get("dimension_results") or dimension_results)

    return {"l2_conclusions": l2, "dimension_results": dimension_results}


def run_fixed_dag_l4_phase(
    plan,
    l2_conclusions,
    dimension_results,
    *,
    context = None,
    question = "",
    as_of = "",
):
    """Execute L4 phase: decision + report_input_bundle + report + external compute + enrichment."""
    l2 = dict(l2_conclusions)
    dims = dict(dimension_results)
    execution_plan = plan
    as_of_val = as_of or str(plan.get("as_of") or "")
    q = question or str(plan.get("user_text") or "")

    from react_agent.fixed_dag_runtime_registry import (
        external_compute_default_agent_ids,
    )
    external_compute_default_disabled = context is None or bool(
        getattr(context, "disable_external_compute_default", False)
    )
    external_compute_default_ids = (
        set()
        if external_compute_default_disabled
        else set(external_compute_default_agent_ids())
    )
    l4_ids = external_compute_default_ids & {"decision_synthesizer", "report_generator"}

    decision_result = build_decision_result(dims, as_of=as_of_val)
    agent_tasks = build_agent_tasks_for_plan(
        execution_plan, question=q, as_of=as_of_val,
        l2_conclusions=l2, dimension_results=dims,
        decision_result=decision_result,
    )
    if "decision_synthesizer" in l4_ids:
        from react_agent.fixed_dag_external_compute_bridge import (
            EXTERNAL_COMPUTE_DEFAULT_SOURCE,
            run_external_compute_for_plan,
            runtime_compute_entries_from_bindings,
        )
        ext_decision = run_external_compute_for_plan(
            execution_plan, question=q, as_of=as_of_val, context=context,
            l2_conclusions=l2, dimension_results=dims,
            decision_result=decision_result, agent_tasks=agent_tasks,
            stages=("decision",), allowlist_override=("decision_synthesizer",),
            entry_registry=runtime_compute_entries_from_bindings(),
            runtime_source=EXTERNAL_COMPUTE_DEFAULT_SOURCE,
        )
        decision_result = dict(ext_decision.get("decision_result") or decision_result)
        agent_tasks = build_agent_tasks_for_plan(
            execution_plan, question=q, as_of=as_of_val,
            l2_conclusions=l2, dimension_results=dims,
            decision_result=decision_result,
        )

    report_input_bundle = build_report_input_bundle(
        question=q, l2_conclusions=l2, dimension_results=dims,
        decision_result=decision_result, agent_tasks=agent_tasks,
    )
    report_result = build_report_result(decision_result, question=q, report_input_bundle=report_input_bundle)

    if "report_generator" in l4_ids:
        from react_agent.fixed_dag_external_compute_bridge import (
            EXTERNAL_COMPUTE_DEFAULT_SOURCE,
            run_external_compute_for_plan,
            runtime_compute_entries_from_bindings,
        )
        ext_report = run_external_compute_for_plan(
            execution_plan, question=q, as_of=as_of_val, context=context,
            l2_conclusions=l2, dimension_results=dims,
            decision_result=decision_result, report_result=report_result,
            report_input_bundle=report_input_bundle, agent_tasks=agent_tasks,
            stages=("report",), allowlist_override=("report_generator",),
            entry_registry=runtime_compute_entries_from_bindings(),
            runtime_source=EXTERNAL_COMPUTE_DEFAULT_SOURCE,
        )
        report_result = dict(ext_report.get("report_result") or report_result)

    try:
        from react_agent.fixed_dag.execution.validation import (
            validate_report_input_bundle,
        )
        valid_rb, _ = validate_report_input_bundle(report_input_bundle)
        if valid_rb:
            report_result = _maybe_enrich_weak_report_result(
                report_result, question=q, report_input_bundle=report_input_bundle,
                decision_result=decision_result,
            )
    except Exception:
        pass

    return {
        "l2_conclusions": l2,
        "dimension_results": dims,
        "decision_result": decision_result,
        "report_input_bundle": report_input_bundle,
        "report_result": report_result,
    }
