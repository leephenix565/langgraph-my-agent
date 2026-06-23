# ruff: noqa: D103
"""Production non-L4 external compute orchestration.

The production non-L4 path is independent from the demo bridge switches and
from the L4 `external_compute_default` runtime bindings.  It reuses the same
request builder, transport, adapter, temporal guard, and result applier as the
demo bridge, but it is configured by a source-controlled production policy and
never reads demo URL overrides.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any, cast

from react_agent.fixed_dag_external_compute_bridge import (
    Transport,
    apply_mapped_external_compute_result,
    invoke_external_compute,
)
from react_agent.fixed_dag_non_l4_runtime_registry import (
    NonL4ExternalComputePolicyAgent,
    load_non_l4_external_compute_policy,
    non_l4_external_compute_entries,
    non_l4_policy_agent_by_id,
    validate_non_l4_external_compute_policy,
)

PRODUCTION_EXTERNAL_COMPUTE_STEP_WARNING = "production_external_compute"
PRODUCTION_EXTERNAL_COMPUTE_FAILED_PREFIX = "production_external_compute_failed"
PRODUCTION_EXTERNAL_COMPUTE_POLICY_SKIP_PREFIX = "production_external_compute_skipped"


def _steps(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_steps = plan.get("dag_steps", plan.get("steps", []))
    if not isinstance(raw_steps, list):
        return []
    return [step for step in raw_steps if isinstance(step, Mapping)]


def _safe_code(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "external_compute_failure"
    normalized = []
    for char in text[:120]:
        if char.isalnum() or char in {"_", "-", ":"}:
            normalized.append(char)
        else:
            normalized.append("_")
    return "".join(normalized).strip("_") or "external_compute_failure"


def _stage_policy_rows(
    plan: Mapping[str, Any],
    *,
    stage: str,
    policy_agents: Mapping[str, NonL4ExternalComputePolicyAgent],
) -> list[tuple[str, Mapping[str, Any], NonL4ExternalComputePolicyAgent]]:
    rows: list[tuple[str, Mapping[str, Any], NonL4ExternalComputePolicyAgent]] = []
    for step in _steps(plan):
        if str(step.get("stage") or "") != stage:
            continue
        agent_id = str(step.get("agent_id") or "")
        row = policy_agents.get(agent_id)
        if row is not None:
            rows.append((str(step.get("id") or agent_id), step, row))
    return rows


def _stage_concurrency(policy: Mapping[str, Any], stage: str) -> int:
    raw = policy.get("max_concurrency_by_stage", {})
    mapping = raw if isinstance(raw, Mapping) else {}
    key = "l3" if stage == "dimension_composite" else "l2"
    try:
        value = int(mapping.get(key, 1))
    except (TypeError, ValueError):
        value = 1
    return max(1, min(value, 8))


def _stage_deadline_seconds(
    rows: list[tuple[str, Mapping[str, Any], NonL4ExternalComputePolicyAgent]],
    *,
    max_workers: int,
) -> float:
    if not rows:
        return 0.0
    max_timeout = max(float(row["timeout_seconds"]) for _step_id, _step, row in rows)
    waves = max(1, math.ceil(len(rows) / max_workers))
    return (max_timeout * waves) + 5.0


def _empty_result(
    *,
    l2_conclusions: Mapping[str, Any],
    data_bundle: Mapping[str, Any] | None,
    entity_relation_bundle: Mapping[str, Any] | None,
    dimension_results: Mapping[str, Any] | None,
    decision_result: Mapping[str, Any] | None,
    report_result: Mapping[str, Any] | None,
    policy_enabled: bool,
    rollback_disabled: bool,
    demo_suppressed: bool,
    policy_version: str,
) -> dict[str, Any]:
    return {
        "data_bundle": dict(data_bundle) if isinstance(data_bundle, Mapping) else {},
        "entity_relation_bundle": (
            dict(entity_relation_bundle)
            if isinstance(entity_relation_bundle, Mapping)
            else {}
        ),
        "l2_conclusions": {
            str(agent_id): dict(value)
            for agent_id, value in l2_conclusions.items()
            if isinstance(value, Mapping)
        },
        "dimension_results": {
            str(dimension): dict(value)
            for dimension, value in (dimension_results or {}).items()
            if isinstance(value, Mapping)
        },
        "decision_result": dict(decision_result or {}),
        "report_result": dict(report_result or {}),
        "step_updates": {},
        "called_agents": [],
        "mapped_agents": [],
        "failed_agents": [],
        "fallback_agents": [],
        "skipped_agents": [],
        "warnings": [],
        "latency_ms_by_agent": {},
        "required_failures": [],
        "optional_failures": [],
        "policy_enabled": policy_enabled,
        "policy_version": policy_version,
        "demo_suppressed": demo_suppressed,
        "rollback_disabled": rollback_disabled,
    }


def _normalize_warning(agent_id: str, mapped_result: Mapping[str, Any]) -> str:
    code = _safe_code(mapped_result.get("failure_code") or "mapping_failed")
    return f"{PRODUCTION_EXTERNAL_COMPUTE_FAILED_PREFIX}:{agent_id}:{code}"


def _with_production_runtime_source(mapped: Mapping[str, Any]) -> dict[str, Any]:
    """Tag mapped objects so report/evidence projection does not label them as demo."""
    copied = dict(mapped)
    provenance = copied.get("provenance")
    copied["provenance"] = {
        **(dict(provenance) if isinstance(provenance, Mapping) else {}),
        "runtime_source": PRODUCTION_EXTERNAL_COMPUTE_STEP_WARNING,
    }
    return copied


def _invoke_one(
    *,
    row: NonL4ExternalComputePolicyAgent,
    entry_registry: Mapping[str, Any],
    question: str,
    as_of: str,
    agent_task: Mapping[str, Any] | None,
    upstream_outputs: Mapping[str, Any] | None,
    transport: Transport | None,
) -> dict[str, Any]:
    entry = entry_registry[row["agent_id"]]
    started = time.monotonic()
    mapped_result = invoke_external_compute(
        entry,
        question=question,
        as_of=as_of,
        request_id=f"production-non-l4-{row['agent_id']}",
        timeout_seconds=float(row["timeout_seconds"]),
        demo=False,
        agent_task=agent_task,
        upstream_outputs=upstream_outputs,
        transport=transport,
    )
    elapsed_ms = int(round((time.monotonic() - started) * 1000))
    return {
        "agent_id": row["agent_id"],
        "required_or_optional": row["required_or_optional"],
        "failure_policy": row["failure_policy"],
        "mapped_result": mapped_result,
        "latency_ms": elapsed_ms,
    }


def _run_stage(
    *,
    stage: str,
    rows: list[tuple[str, Mapping[str, Any], NonL4ExternalComputePolicyAgent]],
    question: str,
    as_of: str,
    agent_tasks: Mapping[str, Any] | None,
    upstream_outputs: Mapping[str, Any] | None,
    entry_registry: Mapping[str, Any],
    policy: Mapping[str, Any],
    transport: Transport | None,
) -> list[dict[str, Any]]:
    if not rows:
        return []
    max_workers = min(_stage_concurrency(policy, stage), len(rows))
    deadline = _stage_deadline_seconds(rows, max_workers=max_workers)
    outcomes_by_agent: dict[str, dict[str, Any]] = {}
    future_by_agent: dict[Future[dict[str, Any]], str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for step_id, _step, row in rows:
            raw_task: Mapping[str, Any] | None = None
            if isinstance(agent_tasks, Mapping):
                candidate = agent_tasks.get(step_id) or agent_tasks.get(row["agent_id"])
                if isinstance(candidate, Mapping):
                    raw_task = candidate
            future = executor.submit(
                _invoke_one,
                row=row,
                entry_registry=entry_registry,
                question=question,
                as_of=as_of,
                agent_task=raw_task,
                upstream_outputs=upstream_outputs,
                transport=transport,
            )
            future_by_agent[future] = row["agent_id"]
        end_time = time.monotonic() + deadline
        for future, agent_id in list(future_by_agent.items()):
            remaining = max(0.0, end_time - time.monotonic())
            try:
                outcome = future.result(timeout=remaining)
            except FuturesTimeout:
                future.cancel()
                outcome = {
                    "agent_id": agent_id,
                    "required_or_optional": next(
                        row["required_or_optional"]
                        for _sid, _step, row in rows
                        if row["agent_id"] == agent_id
                    ),
                    "failure_policy": next(
                        row["failure_policy"]
                        for _sid, _step, row in rows
                        if row["agent_id"] == agent_id
                    ),
                    "mapped_result": {
                        "agent_id": agent_id,
                        "status": "failed",
                        "mapped": None,
                        "failure_code": "stage_deadline_timeout",
                        "warning": "external_compute_failed:stage_deadline_timeout",
                    },
                    "latency_ms": int(round(deadline * 1000)),
                }
            outcomes_by_agent[agent_id] = outcome
    return [
        outcomes_by_agent[row["agent_id"]]
        for _step_id, _step, row in rows
        if row["agent_id"] in outcomes_by_agent
    ]


def run_production_external_compute_for_plan(
    plan: Mapping[str, Any],
    *,
    question: str,
    as_of: str,
    context: Any,
    l2_conclusions: Mapping[str, Any],
    data_bundle: Mapping[str, Any] | None = None,
    entity_relation_bundle: Mapping[str, Any] | None = None,
    dimension_results: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
    report_result: Mapping[str, Any] | None = None,
    agent_tasks: Mapping[str, Any] | None = None,
    stages: tuple[str, ...] = ("l2_analysis", "dimension_composite"),
    include_optional_canary: tuple[str, ...] = (),
    policy: Mapping[str, Any] | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    loaded_policy = load_non_l4_external_compute_policy() if policy is None else policy
    valid, reason = validate_non_l4_external_compute_policy(loaded_policy)
    result = _empty_result(
        l2_conclusions=l2_conclusions,
        data_bundle=data_bundle,
        entity_relation_bundle=entity_relation_bundle,
        dimension_results=dimension_results,
        decision_result=decision_result,
        report_result=report_result,
        policy_enabled=False,
        rollback_disabled=bool(getattr(context, "disable_non_l4_external_compute_default", False)),
        demo_suppressed=bool(getattr(context, "enable_external_compute_demo", False)),
        policy_version=str(loaded_policy.get("schema_version") or ""),
    )
    if not valid:
        result["warnings"].append(f"{PRODUCTION_EXTERNAL_COMPUTE_POLICY_SKIP_PREFIX}:{reason}")
        return result
    if not bool(loaded_policy.get("enabled_by_default")):
        result["skipped_agents"].append("policy_disabled")
        return result
    if bool(getattr(context, "disable_non_l4_external_compute_default", False)):
        result["skipped_agents"].append("rollback_disabled")
        return result
    if bool(getattr(context, "enable_external_compute_demo", False)):
        result["skipped_agents"].append("demo_suppressed")
        result["demo_suppressed"] = True
        return result

    include_optional = set(include_optional_canary)
    entries = non_l4_external_compute_entries(loaded_policy, include_disabled=True)
    policy_rows = {
        agent_id: row
        for agent_id, row in non_l4_policy_agent_by_id(
            loaded_policy,
            include_disabled=True,
        ).items()
        if row["enabled"]
        or (row["required_or_optional"] == "optional" and agent_id in include_optional)
    }
    result["policy_enabled"] = True
    for stage in stages:
        rows = _stage_policy_rows(plan, stage=stage, policy_agents=policy_rows)
        upstream_outputs = result["l2_conclusions"] if stage == "dimension_composite" else None
        stage_outcomes = _run_stage(
            stage=stage,
            rows=rows,
            question=question,
            as_of=as_of,
            agent_tasks=agent_tasks,
            upstream_outputs=upstream_outputs,
            entry_registry=entries,
            policy=loaded_policy,
            transport=transport,
        )
        for outcome in stage_outcomes:
            agent_id = str(outcome.get("agent_id") or "")
            mapped_result = outcome.get("mapped_result")
            if not isinstance(mapped_result, Mapping):
                mapped_result = {}
            result["called_agents"].append(agent_id)
            result["latency_ms_by_agent"][agent_id] = int(outcome.get("latency_ms") or 0)
            mapped = mapped_result.get("mapped")
            if mapped_result.get("status") != "pass" or not isinstance(mapped, Mapping):
                warning = _normalize_warning(agent_id, mapped_result)
                result["warnings"].append(warning)
                result["failed_agents"].append(agent_id)
                result["fallback_agents"].append(agent_id)
                if outcome.get("required_or_optional") == "optional":
                    result["optional_failures"].append(agent_id)
                else:
                    result["required_failures"].append(agent_id)
                step_id = next(
                    (
                        sid
                        for sid, _step, row in rows
                        if row["agent_id"] == agent_id
                    ),
                    agent_id,
                )
                result["step_updates"][step_id] = {"warning": warning}
                continue

            applied, apply_reason = apply_mapped_external_compute_result(
                agent_id=agent_id,
                mapped=_with_production_runtime_source(cast(Mapping[str, Any], mapped)),
                data_bundle=result["data_bundle"],
                entity_relation_bundle=result["entity_relation_bundle"],
                l2_conclusions=result["l2_conclusions"],
                dimension_results=result["dimension_results"],
                decision_result=result["decision_result"],
                report_result=result["report_result"],
            )
            if not applied:
                warning = (
                    f"{PRODUCTION_EXTERNAL_COMPUTE_FAILED_PREFIX}:"
                    f"{agent_id}:{_safe_code(apply_reason)}"
                )
                result["warnings"].append(warning)
                result["failed_agents"].append(agent_id)
                result["fallback_agents"].append(agent_id)
                if outcome.get("required_or_optional") == "optional":
                    result["optional_failures"].append(agent_id)
                else:
                    result["required_failures"].append(agent_id)
                continue

            result["mapped_agents"].append(agent_id)
            step_id = next(
                (
                    sid
                    for sid, _step, row in rows
                    if row["agent_id"] == agent_id
                ),
                agent_id,
            )
            summary = (
                "生产 non-L4 /compute 默认编排已返回结构化结果并完成固定 DAG 适配映射。"
            )
            result["step_updates"][step_id] = {
                "status": "complete",
                "summary": summary,
                "warning": PRODUCTION_EXTERNAL_COMPUTE_STEP_WARNING,
            }
    return result


__all__ = [
    "PRODUCTION_EXTERNAL_COMPUTE_FAILED_PREFIX",
    "PRODUCTION_EXTERNAL_COMPUTE_STEP_WARNING",
    "run_production_external_compute_for_plan",
]
