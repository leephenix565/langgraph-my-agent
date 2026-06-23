# ruff: noqa: D101, D103
"""Read-only sync plan builders and validators."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from react_agent.ops.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    file_sha256,
    load_and_validate,
    parse_utc,
    read_json,
    stable_id,
    validate_by_schema_version,
)
from react_agent.ops.sync_diff import diff_inventory
from react_agent.ops.sync_inventory import build_runtime_inventory, inventory_root
from react_agent.ops.sync_registry import (
    load_static_registry,
    validate_static_registry,
)

POINTER_PATH = Path("/sdb/dlut/sandbox/r8-13a/services/PROD_BASELINE_POINTER.json")
DEFAULT_PROD_ROOT = Path("/sdb/dlut/prod")
DEFAULT_ACTIVE_SANDBOX = Path("/sdb/dlut/sandbox/r8-13a/services/prod")
DEFAULT_VERSIONED_BASELINE = Path("/sdb/dlut/sandbox/prod-baselines/20260623T050419Z/fixed-dag-services")


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def expires_utc(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_baseline_pointer(path: Path = POINTER_PATH) -> dict[str, Any]:
    pointer = read_json(path)
    active = pointer.get("active_path") or pointer.get("active_baseline_path")
    baseline = pointer.get("versioned_baseline_path") or pointer.get("active_path")
    return {
        "schema_version": pointer.get("schema", pointer.get("schema_version", "fixed_dag_prod_sandbox_baseline_pointer_v1")),
        "active_baseline_id": pointer.get("active_baseline_id") or pointer.get("baseline_id", ""),
        "active_path": active,
        "versioned_baseline_path": baseline,
        "manifest_hashes": pointer.get("manifest_hashes", {}),
        "pointer_path": str(path),
        "pointer_sha256": file_sha256(path),
        "active_exists": Path(str(active)).exists() if active else False,
        "versioned_baseline_exists": Path(str(baseline)).exists() if baseline else False,
    }


def build_experiment_template(*, output_root: str = "/tmp/agent-sync-experiment") -> dict[str, Any]:
    pointer = load_baseline_pointer()
    return {
        "schema_version": "agent_sync_experiment_v1",
        "experiment_id": f"exp_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "created_at": now_utc(),
        "base_baseline_id": pointer["active_baseline_id"],
        "base_baseline_manifest_sha256": str(pointer.get("manifest_hashes", {}).get("final_agent_sync_matrix", "")),
        "workspace_root": output_root,
        "agents": [],
        "change_units": [],
        "allowed_paths": [output_root],
        "forbidden_paths": [str(DEFAULT_ACTIVE_SANDBOX), str(DEFAULT_VERSIONED_BASELINE), str(DEFAULT_PROD_ROOT)],
        "global_non_goals": ["no direct prod writes", "no active baseline mutation"],
        "owner_boundaries": ["owner-dev roots are read-only unless separately approved"],
        "test_plan": [],
        "status": "draft",
    }


def validate_experiment_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    validate_by_schema_version(manifest)
    pointer = load_baseline_pointer()
    workspace = Path(str(manifest.get("workspace_root") or ""))
    blockers: list[str] = []
    if str(manifest.get("base_baseline_id") or "") != str(pointer.get("active_baseline_id") or ""):
        blockers.append("base_baseline_id_mismatch")
    for forbidden in (pointer.get("active_path"), pointer.get("versioned_baseline_path"), str(DEFAULT_PROD_ROOT)):
        if forbidden and workspace.resolve(strict=False) == Path(str(forbidden)).resolve(strict=False):
            blockers.append("workspace_is_forbidden_root")
    change_units = manifest.get("change_units") or []
    ids = [str(item.get("change_unit_id") or "") for item in change_units if isinstance(item, Mapping)]
    if len(ids) != len(set(ids)):
        blockers.append("duplicate_change_unit_id")
    for unit in change_units:
        if not isinstance(unit, Mapping):
            blockers.append("change_unit_not_mapping")
            continue
        if unit.get("risk_class") in {"D_business_core", "S_security_deployment"} and not unit.get("owner_review_required"):
            blockers.append(f"owner_review_required:{unit.get('change_unit_id')}")
    return {
        "valid": not blockers,
        "blockers": blockers,
        "active_baseline_id": pointer["active_baseline_id"],
    }


def _base_plan(direction: str) -> dict[str, Any]:
    validation = validate_static_registry()
    created = now_utc()
    return {
        "schema_version": "agent_sync_plan_v1",
        "tool_version": "sync_ops_1_read_only_planner",
        "plan_id": f"{direction}_{uuid.uuid4().hex[:12]}",
        "direction": direction,
        "created_at": created,
        "expires_at": expires_utc(),
        "registry_sha256": validation["registry_sha256"],
        "policy_sha256": validation["policy_sha256"],
        "catalog_sha256": validation["catalog_sha256"],
        "baseline": {},
        "experiment": {},
        "target_snapshot": {},
        "agents": [],
        "global_preconditions": ["read_only_plan_only", "approval_required_before_future_write"],
        "global_blockers": [],
        "approval_requirements": {
            "approval_record_required": True,
            "delete_actions_approved": False,
            "process_actions_approved": False,
            "live_validation_approved": False,
            "publish_and_rebase_approved": False,
        },
        "rollback_plan": {"execution": "not_available_in_sync_ops_1", "skeleton_only": True},
        "canonical_sha256": "",
    }


def _file_actions_from_diff(agent_diff: Mapping[str, Any], *, direction: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actions: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for row in agent_diff.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        classification = str(row.get("classification") or "")
        rel = str(row.get("relative_path") or "")
        action_id = stable_id("action", direction, str(row.get("agent_id") or ""), rel, classification)
        if direction == "p2s":
            if classification in {"changed_in_prod_only", "added_in_prod", "sandbox_and_prod_diverged"}:
                actions.append(
                    {
                        "action_id": action_id,
                        "operation": "replace" if classification != "added_in_prod" else "add",
                        "source_path": rel,
                        "target_path": rel,
                        "source_sha256": row.get("prod_sha256", ""),
                        "expected_target_before_sha256": row.get("sandbox_sha256", ""),
                        "expected_mode": "",
                        "sensitive_classification": "",
                        "change_unit_id": "",
                        "approval_scope": "p2s_snapshot_refresh",
                        "rollback_source": "old_sandbox_archive",
                        "classification": classification,
                    }
                )
            elif classification == "unchanged_all":
                actions.append(
                    {
                        "action_id": action_id,
                        "operation": "noop",
                        "source_path": rel,
                        "target_path": rel,
                        "source_sha256": row.get("prod_sha256", ""),
                        "expected_target_before_sha256": row.get("sandbox_sha256", ""),
                        "classification": classification,
                    }
                )
            elif classification == "sanitized_derivative":
                blocked.append({"action_id": action_id, "relative_path": rel, "reason": "sanitized_derivative_requires_resolution"})
        else:
            if classification == "changed_in_sandbox_only":
                actions.append(
                    {
                        "action_id": action_id,
                        "operation": "replace",
                        "source_path": rel,
                        "target_path": rel,
                        "source_sha256": row.get("sandbox_sha256", ""),
                        "expected_target_before_sha256": row.get("prod_sha256", ""),
                        "expected_mode": "",
                        "sensitive_classification": "",
                        "change_unit_id": "",
                        "approval_scope": "s2p_change_unit",
                        "rollback_source": "planned_backup",
                        "classification": classification,
                    }
                )
            elif classification == "added_in_sandbox":
                actions.append(
                    {
                        "action_id": action_id,
                        "operation": "add",
                        "source_path": rel,
                        "target_path": rel,
                        "source_sha256": row.get("sandbox_sha256", ""),
                        "expected_target_before_sha256": "",
                        "expected_mode": "",
                        "sensitive_classification": "",
                        "change_unit_id": "",
                        "approval_scope": "s2p_change_unit",
                        "rollback_source": "planned_backup",
                        "classification": classification,
                    }
                )
            elif classification == "sanitized_derivative":
                blocked.append({"action_id": action_id, "relative_path": rel, "reason": "blocked_sanitized_derivative_publish"})
            elif classification in {"sandbox_and_prod_diverged", "prod_deleted_sandbox_changed"}:
                blocked.append({"action_id": action_id, "relative_path": rel, "reason": f"blocked_{classification}"})
            elif classification == "unchanged_all":
                actions.append({"action_id": action_id, "operation": "noop", "source_path": rel, "target_path": rel, "classification": classification})
    return actions, blocked


def build_p2s_plan() -> dict[str, Any]:
    inventory = build_runtime_inventory(include_files=True)
    diff = diff_inventory(inventory)
    pointer = load_baseline_pointer()
    plan = _base_plan("p2s")
    plan["baseline"] = pointer
    plan["target_snapshot"] = {
        "active_sandbox_path": pointer["active_path"],
        "active_sandbox_pointer_sha256": pointer["pointer_sha256"],
    }
    agent_plans: list[dict[str, Any]] = []
    for agent in diff["agents"]:
        actions, blocked = _file_actions_from_diff(agent, direction="p2s")
        agent_plans.append(
            {
                "agent_id": agent["agent_id"],
                "transaction_id": stable_id("txn", "p2s", agent["agent_id"]),
                "source_root": "prod",
                "target_root": "active_sandbox",
                "target_before_tree_sha256": "",
                "actions": actions,
                "blocked_actions": blocked,
                "backup": {"required_future_phase": True},
                "offline_tests": [],
                "process_preflight": {"required": False},
                "process_actions": [],
                "live_validation": [],
                "rollback": {"skeleton_only": True},
                "expected_status": "planned" if not blocked else "planned_with_blockers",
            }
        )
    plan["agents"] = agent_plans
    plan["diff_summary"] = diff["totals"]
    if any(agent["blocked_actions"] for agent in agent_plans):
        plan["global_blockers"].append("p2s_blocked_actions_present")
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def build_s2p_plan(experiment_manifest: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_experiment_manifest(experiment_manifest)
    plan = _base_plan("s2p")
    pointer = load_baseline_pointer()
    workspace = Path(str(experiment_manifest.get("workspace_root") or ""))
    plan["baseline"] = pointer
    plan["experiment"] = {
        "experiment_id": experiment_manifest.get("experiment_id", ""),
        "workspace_root": str(workspace),
        "base_baseline_id": experiment_manifest.get("base_baseline_id", ""),
    }
    if validation["blockers"]:
        plan["global_blockers"].extend(validation["blockers"])
    if workspace.resolve(strict=False) in {
        Path(str(pointer["active_path"])).resolve(strict=False),
        Path(str(pointer["versioned_baseline_path"])).resolve(strict=False),
    }:
        plan["global_blockers"].append("blocked_active_baseline_not_experiment")
    registry = load_static_registry()
    agent_ids = {str(agent.get("agent_id")) for agent in experiment_manifest.get("agents") or [] if isinstance(agent, Mapping)}
    if not agent_ids:
        agent_ids = {str(unit.get("agent_id")) for unit in experiment_manifest.get("change_units") or [] if isinstance(unit, Mapping)}
    agent_plans: list[dict[str, Any]] = []
    for agent in registry["agents"]:
        if agent_ids and agent["agent_id"] not in agent_ids:
            continue
        baseline_root = Path(agent["sandbox"]["baseline_root"])
        prod_root = Path(agent["prod"]["root"])
        exp_root = workspace / agent["agent_id"]
        agent_inventory = {
            "agent_id": agent["agent_id"],
            "roots": {
                "baseline": inventory_root(agent["agent_id"], baseline_root, root_role="baseline"),
                "active_sandbox": inventory_root(agent["agent_id"], exp_root, root_role="experiment"),
                "prod": inventory_root(agent["agent_id"], prod_root, root_role="prod"),
            },
            "sanitized_derivative": agent["sandbox"].get("sanitized_derivative", False),
            "semantic_placeholder": agent["sandbox"].get("semantic_placeholder", False),
        }
        diff = diff_inventory({"agents": [agent_inventory], "registry_sha256": "", "policy_sha256": ""})
        actions, blocked = _file_actions_from_diff(diff["agents"][0], direction="s2p")
        for action in actions:
            if action.get("operation") == "delete":
                blocked.append({"action_id": action.get("action_id"), "reason": "delete_disabled_by_policy"})
        agent_plans.append(
            {
                "agent_id": agent["agent_id"],
                "transaction_id": stable_id("txn", "s2p", agent["agent_id"], str(workspace)),
                "source_root": str(exp_root),
                "target_root": str(prod_root),
                "target_before_tree_sha256": agent_inventory["roots"]["prod"]["tree_digest"],
                "actions": actions,
                "blocked_actions": blocked,
                "backup": {"required_future_phase": True},
                "offline_tests": agent["prod"].get("focused_tests", []),
                "process_preflight": {"planned_only": True},
                "process_actions": [],
                "live_validation": [],
                "rollback": {"skeleton_only": True},
                "expected_status": "planned" if not blocked else "blocked",
            }
        )
    plan["agents"] = agent_plans
    if any(agent["blocked_actions"] for agent in agent_plans):
        plan["global_blockers"].append("s2p_blocked_actions_present")
    plan["approval_requirements"]["process_actions_approved"] = False
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def build_cycle_plan(s2p_plan: Mapping[str, Any]) -> dict[str, Any]:
    validate_plan(s2p_plan, check_target_freshness=False)
    plan = _base_plan("publish_and_rebase")
    plan["experiment"] = {"s2p_plan_id": s2p_plan.get("plan_id"), "s2p_plan_sha256": s2p_plan.get("canonical_sha256")}
    plan["agents"] = [
        {
            "agent_id": agent.get("agent_id"),
            "transaction_id": stable_id("cycle", str(agent.get("agent_id")), str(s2p_plan.get("plan_id"))),
            "source_root": "s2p_plan",
            "target_root": "deferred_p2s_after_settled_prod",
            "target_before_tree_sha256": "",
            "actions": [],
            "blocked_actions": [],
            "backup": {},
            "offline_tests": [],
            "process_preflight": {},
            "process_actions": [],
            "live_validation": [],
            "rollback": {},
            "expected_status": "deferred_rebase_after_s2p_settled",
        }
        for agent in s2p_plan.get("agents", [])
    ]
    plan["deferred_rebase"] = {
        "p2s_plan_generation": "deferred_until_all_started_s2p_transactions_settled",
        "reads": "real_prod_after_state",
        "rollback_failed_blocks_rebase": True,
        "requires_publish_and_rebase_approval": True,
    }
    plan["approval_requirements"]["publish_and_rebase_approved"] = True
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_plan(plan: Mapping[str, Any], *, check_target_freshness: bool = True) -> dict[str, Any]:
    validate_by_schema_version(plan)
    expected = canonical_sha256(plan)
    blockers: list[str] = []
    if plan.get("canonical_sha256") != expected:
        blockers.append("canonical_hash_mismatch")
    try:
        parse_utc(str(plan.get("expires_at") or ""))
    except SyncPlannerError:
        blockers.append("invalid_expires_at")
    action_targets: set[tuple[str, str]] = set()
    for agent in plan.get("agents") or []:
        if not isinstance(agent, Mapping):
            blockers.append("agent_plan_not_mapping")
            continue
        for action in agent.get("actions") or []:
            if not isinstance(action, Mapping):
                blockers.append("action_not_mapping")
                continue
            target = (str(agent.get("transaction_id")), str(action.get("target_path") or ""))
            if target in action_targets and action.get("operation") != "noop":
                blockers.append("duplicate_action_target")
            action_targets.add(target)
            if action.get("operation") == "delete" and not plan.get("approval_requirements", {}).get("delete_actions_approved"):
                blockers.append("delete_action_without_approval_requirement")
            if action.get("operation") == "sanitize":
                blockers.append("sanitize_action_not_publishable_in_sync_ops_1")
    if check_target_freshness and plan.get("direction") == "s2p":
        for agent in plan.get("agents") or []:
            if not isinstance(agent, Mapping):
                continue
            target_root = Path(str(agent.get("target_root") or ""))
            if not target_root.exists():
                continue
            current = inventory_root(str(agent.get("agent_id") or ""), target_root, root_role="target")
            if agent.get("target_before_tree_sha256") and current["tree_digest"] != agent.get("target_before_tree_sha256"):
                blockers.append("target_snapshot_stale")
                break
    return {
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "canonical_sha256": expected,
        "stored_canonical_sha256": plan.get("canonical_sha256", ""),
        "exit_code": 0 if not blockers else (5 if "target_snapshot_stale" in blockers else 3),
    }


def load_plan(path: Path) -> dict[str, Any]:
    plan = load_and_validate(path)
    if not isinstance(plan, dict):
        raise SyncPlannerError("plan_not_object", exit_code=2)
    return plan

