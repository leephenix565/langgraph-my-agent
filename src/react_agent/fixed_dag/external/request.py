"""Request-envelope builders for fixed-DAG external compute."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from react_agent.fixed_dag.external.constants import (
    EXTERNAL_AGENT_REQUEST_SCHEMA_VERSION,
)
from react_agent.fixed_dag.external.safety import (
    _safe_context_mapping,
    _safe_upstream_outputs,
)
from react_agent.fixed_dag.external.types import ExternalComputeDemoEntry
from react_agent.fixed_dag_contracts import (
    AGENT_TASK_SCHEMA_VERSION,
    REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
    validate_agent_task,
    validate_report_input_bundle,
)


def normalize_demo_allowlist(value: Any) -> tuple[str, ...]:
    """Normalize comma-separated or iterable allowlist values into agent ids."""
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, tuple | list | set):
        raw_items = list(value)
    else:
        raw_items = []
    items: list[str] = []
    for raw in raw_items:
        agent_id = str(raw or "").strip()
        if agent_id and agent_id not in items:
            items.append(agent_id)
    return tuple(items)


def _steps(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_steps = plan.get("dag_steps", plan.get("steps", []))
    if not isinstance(raw_steps, list):
        return []
    return [step for step in raw_steps if isinstance(step, Mapping)]


def _target_for_entry(entry: ExternalComputeDemoEntry, question: str) -> str:
    if entry.default_target != "600519.SH":
        return entry.default_target
    match = re.search(r"\b\d{6}\.(?:SH|SZ|BJ)\b", question.upper())
    if match:
        return match.group(0)
    return entry.default_target


def _safe_report_input_bundle(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Preserve a validated report_input_bundle_v1 for L4 report services."""
    if not isinstance(value, Mapping):
        return {}
    valid, _reason = validate_report_input_bundle(value)
    if not valid:
        return {}
    if value.get("schema") != REPORT_INPUT_BUNDLE_SCHEMA_VERSION:
        return {}
    return dict(value)


def build_external_compute_request(
    entry: ExternalComputeDemoEntry,
    *,
    question: str,
    as_of: str,
    request_id: str,
    demo: bool = True,
    agent_task: Mapping[str, Any] | None = None,
    upstream_outputs: Mapping[str, Any] | None = None,
    dimension_results: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
    report_input_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a production compute request for an allowlisted external agent."""
    target = _target_for_entry(entry, question)
    safe_agent_task: dict[str, Any] | None = None
    if isinstance(agent_task, Mapping):
        valid_task, _task_reason = validate_agent_task(agent_task)
        if valid_task:
            safe_agent_task = dict(agent_task)
    request = {
        "schema_version": EXTERNAL_AGENT_REQUEST_SCHEMA_VERSION,
        "request_id": request_id,
        "agent_id": entry.agent_id,
        "external_agent_id": entry.external_agent_id,
        "target": target,
        "as_of": as_of,
        "as_of_date": as_of,
        "context": {
            "fixed_dag_id": entry.agent_id,
            "dimension": entry.dimension,
            "as_of": as_of,
            "as_of_date": as_of,
            "environment": "production",
            "demo": demo,
            "runtime_default": not demo,
            "user_question": question,
            "task_instruction": (
                safe_agent_task.get("task_instruction", "")
                if safe_agent_task is not None
                else ""
            ),
        },
        "options": {
            "smoke": False,
            "demo": demo,
            "environment": "production",
            "as_of": as_of,
            "as_of_date": as_of,
            "allow_llm": entry.agent_id in {"decision_synthesizer", "report_generator"},
            "return_tool_result": True,
        },
    }
    if safe_agent_task is not None:
        request["agent_task"] = safe_agent_task
        request["context"]["agent_task"] = safe_agent_task
        request["context"]["agent_task_schema_version"] = AGENT_TASK_SCHEMA_VERSION
    safe_upstream_outputs = _safe_upstream_outputs(upstream_outputs, safe_agent_task)
    if safe_upstream_outputs:
        request["context"]["upstream_outputs"] = safe_upstream_outputs
        request["context"]["upstream_output_schema"] = "fixed_dag_mapped_outputs_v1"
    if entry.agent_id == "decision_synthesizer":
        safe_dimensions = _safe_context_mapping(dimension_results)
        if safe_dimensions:
            request["context"]["dimension_results"] = safe_dimensions
            request["context"]["dimension_results_schema"] = "dimension_composite_result_map_v1"
    if entry.agent_id == "report_generator":
        safe_decision = _safe_context_mapping(decision_result)
        safe_report_input = _safe_report_input_bundle(report_input_bundle)
        if safe_decision:
            request["context"]["decision_result"] = safe_decision
        if safe_report_input:
            request["context"]["report_input_bundle"] = safe_report_input
    return request


__all__ = ["build_external_compute_request", "normalize_demo_allowlist"]
