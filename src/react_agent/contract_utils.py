"""Shared utilities for validating a01 contract schema v0."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Tuple

CONTRACT_SCHEMA_VERSION = "a01_contract_v0"
CONTRACT_REQUIRED_KEYS = {
    "schema_version",
    "objective",
    "constraints",
    "selected_agents",
    "tasks",
    "aggregation",
    "budget",
    "output_spec",
}
TASK_REQUIRED_KEYS = {
    "agent_id",
    "task_id",
    "objective",
    "steps",
    "agent_can_extend_steps",
    "extension_policy",
}


def hash_contract(contract: Dict[str, Any]) -> str:
    """Return a stable hash for an A01 contract mapping."""
    try:
        payload = json.dumps(contract, ensure_ascii=False, sort_keys=True)
    except Exception:
        return ""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_contract(results: Dict[str, Any]) -> Dict[str, Any] | None:
    """Extract a parsed A01 contract from agent results when present."""
    a01 = results.get("a01_cio_orchestrator")
    if not isinstance(a01, dict):
        return None
    contract = a01.get("contract")
    if isinstance(contract, dict):
        return contract
    if isinstance(contract, str):
        try:
            parsed = json.loads(contract)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def validate_contract(
    contract: Dict[str, Any] | None,
    selected_agents: List[str],
    *,
    steps_min: int = 2,
    steps_max: int | None = 6,
) -> Tuple[bool, str, Dict[str, Dict[str, Any]]]:
    """Validate the legacy A01 contract shape retained for compatibility."""
    if not isinstance(contract, dict):
        return False, "missing_contract", {}
    if contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        return False, "schema_version_mismatch", {}
    contract_keys = set(contract.keys())
    if contract_keys != CONTRACT_REQUIRED_KEYS:
        return False, "contract_keys_mismatch", {}

    if not isinstance(contract.get("objective"), str):
        return False, "invalid_objective", {}
    constraints = contract.get("constraints")
    if not isinstance(constraints, list) or any(not isinstance(c, str) for c in constraints):
        return False, "invalid_constraints", {}
    selected = contract.get("selected_agents")
    if not isinstance(selected, list) or any(not isinstance(a, str) for a in selected):
        return False, "invalid_selected_agents", {}
    if "a01_cio_orchestrator" not in selected_agents:
        return False, "missing_a01", {}
    if set(selected) != set(selected_agents):
        return False, "selected_agents_mismatch", {}

    aggregation = contract.get("aggregation")
    if not isinstance(aggregation, dict):
        return False, "invalid_aggregation", {}
    budget = contract.get("budget")
    if not isinstance(budget, dict):
        return False, "invalid_budget", {}
    output_spec = contract.get("output_spec")
    if not isinstance(output_spec, dict):
        return False, "invalid_output_spec", {}
    req_sections = output_spec.get("required_sections")
    if not isinstance(req_sections, list) or any(not isinstance(s, str) for s in req_sections):
        return False, "invalid_output_spec_sections", {}
    if not isinstance(output_spec.get("final_answer_format"), str):
        return False, "invalid_output_spec_format", {}

    tasks = contract.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return False, "invalid_tasks", {}
    tasks_by_agent: Dict[str, Dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            return False, "invalid_task_type", {}
        if not TASK_REQUIRED_KEYS.issubset(task.keys()):
            return False, "missing_task_keys", {}
        agent_id = task.get("agent_id")
        if not isinstance(agent_id, str) or agent_id not in selected_agents:
            return False, "task_agent_mismatch", {}
        if agent_id in tasks_by_agent:
            return False, "duplicate_task_agent", {}
        if not isinstance(task.get("task_id"), str):
            return False, "invalid_task_id", {}
        if not isinstance(task.get("objective"), str):
            return False, "invalid_task_objective", {}
        steps = task.get("steps")
        if not isinstance(steps, list) or not steps or any(not isinstance(s, str) for s in steps):
            return False, "invalid_steps", {}
        if steps_min and len(steps) < steps_min:
            return False, "invalid_steps", {}
        if steps_max is not None and len(steps) > steps_max:
            return False, "invalid_steps", {}
        if task.get("agent_can_extend_steps") is not True:
            return False, "invalid_extension_flag", {}
        if not isinstance(task.get("extension_policy"), str):
            return False, "invalid_extension_policy", {}
        tasks_by_agent[agent_id] = task

    if set(tasks_by_agent.keys()) != set(selected_agents):
        return False, "tasks_cover_mismatch", {}
    return True, "", tasks_by_agent
