# ruff: noqa: D103
"""Topology helpers for fixed-DAG execution plans."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from typing import Any

from react_agent.fixed_dag.constants import SELECTED_FIXED_DAG_SCHEMA_VERSION
from react_agent.fixed_dag.execution.constants import DIMENSION_STEP_IDS


def _steps(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_steps = plan.get("dag_steps", plan.get("steps", []))
    if not isinstance(raw_steps, list):
        return []
    return [step for step in raw_steps if isinstance(step, Mapping)]


def _deps(step: Mapping[str, Any]) -> list[str]:
    raw = step.get("depends_on", [])
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item)]


def _l2_step_ids(agent_ids: tuple[str, ...]) -> set[str]:
    return {f"l2:{agent_id}" for agent_id in agent_ids}


def build_dag_step_index(plan: Mapping[str, Any]) -> dict[str, dict]:
    """Return plan steps by id without normalizing away invalid shapes."""
    index: dict[str, dict] = {}
    for step in _steps(plan):
        step_id = str(step.get("id") or "")
        if step_id:
            index[step_id] = dict(step)
    return index


def _topological_batches_from_steps(steps: list[Mapping[str, Any]]) -> list[list[str]]:
    order = [str(step.get("id")) for step in steps]
    by_id = {str(step.get("id")): step for step in steps}
    indegree = {step_id: 0 for step_id in order}
    children: dict[str, list[str]] = {step_id: [] for step_id in order}
    for step in steps:
        step_id = str(step.get("id"))
        for dep_id in _deps(step):
            if dep_id not in indegree:
                continue
            indegree[step_id] += 1
            children[dep_id].append(step_id)

    ready = deque(step_id for step_id in order if indegree[step_id] == 0)
    batches: list[list[str]] = []
    visited: set[str] = set()
    while ready:
        batch = [step_id for step_id in order if step_id in ready and step_id not in visited]
        ready.clear()
        if not batch:
            break
        batches.append(batch)
        for step_id in batch:
            visited.add(step_id)
            for child_id in children[step_id]:
                if child_id not in by_id:
                    continue
                indegree[child_id] -= 1
                if indegree[child_id] == 0:
                    ready.append(child_id)
    return batches


def topological_batches(plan: Mapping[str, Any]) -> list[list[str]]:
    from react_agent.fixed_dag.execution.validation import validate_dag_steps

    valid, _reason = validate_dag_steps(plan)
    if not valid:
        return []
    return _topological_batches_from_steps(_steps(plan))


def topological_batches_for_selected_plan(plan: Mapping[str, Any]) -> list[list[str]]:
    from react_agent.fixed_dag.execution.validation import validate_selected_dag_steps

    valid, _reason = validate_selected_dag_steps(plan)
    if not valid:
        return []
    return _topological_batches_from_steps(_steps(plan))


def _execution_batches(plan: Mapping[str, Any]) -> list[list[str]]:
    if plan.get("schema") == SELECTED_FIXED_DAG_SCHEMA_VERSION:
        return topological_batches_for_selected_plan(plan)
    return topological_batches(plan)


def _selected_dimension_step_ids(plan: Mapping[str, Any]) -> list[str]:
    dimension_groups = plan.get("dimension_groups", {})
    if not isinstance(dimension_groups, Mapping):
        dimension_groups = {}
    return [
        DIMENSION_STEP_IDS[dimension]
        for dimension in plan.get("selected_dimensions", [])
        if dimension in DIMENSION_STEP_IDS and dimension_groups.get(str(dimension))
    ]


__all__ = [
    "build_dag_step_index",
    "topological_batches",
    "topological_batches_for_selected_plan",
]
