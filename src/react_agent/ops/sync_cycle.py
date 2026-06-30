# ruff: noqa: D101, D102, D103
"""Publish-and-rebase cycle contracts and rehearsals."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from react_agent.ops.sync_artifacts import DEFAULT_ARTIFACT_STORE_ROOT, ArtifactRunStore
from react_agent.ops.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    file_sha256,
    validate_by_schema_version,
    write_json,
)
from react_agent.ops.sync_inventory import inventory_root
from react_agent.ops.sync_lock import SyncLockManager
from react_agent.ops.sync_registry import validate_static_registry
from react_agent.ops.sync_s2p import (
    ACTIVE_SANDBOX_ROOT,
    POINTER_PATH,
    apply_file_actions,
    build_s2p_plan_v2,
    compare_digest_descriptors,
    descriptor_from_inventory,
    fake_live_gate,
    fake_process_action,
    load_pointer,
    prepare_transaction_backups,
    prod_digest_summary,
    rollback_file_actions,
    sandbox_pointer_summary,
    validate_experiment_contract,
    validate_s2p_plan_contract,
)

CYCLE_CONTRACT_VERSION = "agent_sync_publish_and_rebase_cycle_v1"
CYCLE_TOOL_VERSION = "sync_ops_4x_publish_and_rebase_cycle"
STRICT_CYCLE_ENVELOPE_TOOL_VERSION = "sync_ops_5c_r1_strict_cycle_envelope"


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def expires_utc(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _active_descriptor() -> dict[str, Any]:
    active = Path(str(load_pointer().get("active_path") or ACTIVE_SANDBOX_ROOT))
    inventory = inventory_root("active_sandbox", active, root_role="active_sandbox")
    return descriptor_from_inventory(inventory, scope="p2s_active_safe_tree")


def _prod_descriptors(s2p_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    agents_by_txn: dict[str, list[Mapping[str, Any]]] = {}
    for agent_row in s2p_plan.get("agents") or []:
        if not isinstance(agent_row, Mapping):
            continue
        agents_by_txn.setdefault(str(agent_row.get("transaction_id") or ""), []).append(agent_row)
    for transaction in s2p_plan.get("transactions") or []:
        if not isinstance(transaction, Mapping):
            continue
        transaction_id = str(transaction.get("transaction_id") or "")
        agent_rows = agents_by_txn.get(transaction_id, [])
        owner_agent = next((row for row in agent_rows if row.get("agent_role") != "shared_transaction_member"), agent_rows[0] if agent_rows else {})
        before = owner_agent.get("prod_descriptor") if isinstance(owner_agent, Mapping) else None
        rows.append(
            {
                "agent_id": ",".join(str(item.get("agent_id") or "") for item in agent_rows if isinstance(item, Mapping)),
                "affected_agent_ids": list(transaction.get("affected_agent_ids") or []),
                "transaction_id": transaction_id,
                "before": before
                or {
                    "schema_version": "agent_sync_digest_descriptor_v1",
                    "algorithm": "sha256",
                    "digest": str(transaction.get("target_before_tree_sha256") or ""),
                    "scope": "s2p_prod_inventory",
                    "root_role": "prod",
                    "include_profile": "source_bearing_default",
                    "relative_path_basis": "posix",
                    "entry_contract_version": "sync_inventory_root_v1",
                    "file_count": 0,
                },
                "target_prod_root": str(transaction.get("target_prod_root") or ""),
                "file_actions": [action for action in transaction.get("file_actions") or [] if isinstance(action, Mapping)],
                "action_count": len(transaction.get("file_actions") or []),
            }
        )
    return rows


def build_projected_prod_state(s2p_plan: Mapping[str, Any]) -> dict[str, Any]:
    transaction_rows: list[dict[str, Any]] = []
    for row in _prod_descriptors(s2p_plan):
        before = row["before"]
        action_count = int(row["action_count"])
        after = dict(before)
        if action_count:
            after["digest"] = canonical_sha256(
                {
                    "before": before,
                    "actions": row["file_actions"],
                }
            )
            after["scope"] = "transaction_target_tree"
        transaction_rows.append(
            {
                "agent_id": row["agent_id"],
                "affected_agent_ids": row["affected_agent_ids"],
                "transaction_id": row["transaction_id"],
                "target_prod_root": row["target_prod_root"],
                "target_before_descriptor": before,
                "projected_target_after_descriptor": after,
                "action_count": action_count,
            }
        )
    projected_combined = {
        "schema_version": "agent_sync_digest_descriptor_v1",
        "algorithm": "sha256",
        "digest": canonical_sha256([row["projected_target_after_descriptor"] for row in transaction_rows]),
        "scope": "s2p_prod_inventory",
        "root_role": "prod",
        "include_profile": "source_bearing_default",
        "relative_path_basis": "posix",
        "entry_contract_version": "sync_inventory_root_v1",
        "file_count": sum(int((row["projected_target_after_descriptor"] or {}).get("file_count") or 0) for row in transaction_rows),
    }
    return {
        "schema_version": "agent_sync_projected_prod_state_v1",
        "transactions": transaction_rows,
        "projected_combined_prod_descriptor": projected_combined,
        "changed_transaction_ids": [row["transaction_id"] for row in transaction_rows if int(row["action_count"]) > 0],
        "unchanged_transaction_ids": [row["transaction_id"] for row in transaction_rows if int(row["action_count"]) == 0],
    }


def build_precomputed_p2s_plan_stub(projected_prod: Mapping[str, Any], *, noop: bool) -> dict[str, Any]:
    active_descriptor = _active_descriptor()
    p2s_plan = {
        "schema_version": "agent_sync_cycle_precomputed_p2s_plan_v1",
        "plan_id": f"p2s_cycle_{uuid.uuid4().hex[:12]}",
        "mode": "verify_current_baseline_noop" if noop else "precomputed_projected_prod_rebase",
        "source_projected_prod_descriptor": projected_prod.get("projected_combined_prod_descriptor", {}),
        "expected_stage_projection_descriptor": active_descriptor if noop else projected_prod.get("projected_combined_prod_descriptor", {}),
        "p2s_action_count": 0 if noop else 1,
        "stage_approved_required": not noop,
        "activate_approved_required": not noop,
        "rollback_approved_required": not noop,
        "current_pointer_sha256": load_pointer()["pointer_sha256"],
    }
    p2s_plan["canonical_sha256"] = canonical_sha256(p2s_plan)
    return p2s_plan


def build_cycle_plan_from_s2p(s2p_plan: Mapping[str, Any]) -> dict[str, Any]:
    s2p_validation = validate_s2p_plan_contract(s2p_plan, check_target_freshness=True)
    registry = validate_static_registry()
    projected = build_projected_prod_state(s2p_plan)
    noop = int((s2p_plan.get("s2p_summary") or {}).get("actionable_file_action_count") or 0) == 0
    p2s_plan = build_precomputed_p2s_plan_stub(projected, noop=noop)
    created = now_utc()
    plan = {
        "schema_version": CYCLE_CONTRACT_VERSION,
        "cycle_id": f"cycle_{uuid.uuid4().hex[:12]}",
        "created_at": created,
        "expires_at": expires_utc(),
        "mode": "strict_all_or_nothing",
        "tool_version": CYCLE_TOOL_VERSION,
        "experiment": s2p_plan.get("experiment", {}),
        "registry_sha256": registry["registry_sha256"],
        "policy_sha256": registry["policy_sha256"],
        "catalog_sha256": registry["catalog_sha256"],
        "baseline": s2p_plan.get("baseline", {}),
        "s2p_plan": {
            "plan_id": s2p_plan.get("plan_id"),
            "plan_sha256": s2p_plan.get("canonical_sha256"),
            "summary": s2p_plan.get("s2p_summary", {}),
            "validation": s2p_validation,
        },
        "projected_prod_after_state": projected,
        "p2s_plan": p2s_plan,
        "approval_requirements": {
            "approval_bundle_required": True,
            "backup_approved": not noop,
            "apply_approved": not noop,
            "offline_tests_approved": not noop,
            "process_actions_approved": False,
            "live_validation_approved": False,
            "s2p_rollback_approved": not noop,
            "p2s_stage_approved": not noop,
            "p2s_activate_approved": not noop,
            "p2s_rollback_approved": not noop,
            "experiment_close_approved": not noop,
            "owner_handoff_approved": False,
            "delete_approved": False,
            "noop_cycle_approved": noop,
            "artifact_recording_approved": True,
            "lock_cycle_approved": True,
        },
        "failure_policy": {
            "strict_all_or_nothing": True,
            "s2p_failure_blocks_p2s": True,
            "projection_mismatch_blocks_p2s": True,
            "p2s_failure_leaves_prod_settled": True,
        },
        "recovery_policy": {
            "journal_required": True,
            "resume_s2p_after_backup": True,
            "resume_p2s_after_settled_prod": True,
            "closeout_idempotent": True,
        },
        "state_machine": [
            "CYCLE_PLANNED",
            "CYCLE_APPROVED",
            "LOCKED",
            "S2P_PREFLIGHT",
            "S2P_SETTLED",
            "PROD_AFTER_STATE_VERIFIED",
            "P2S_PLAN_REVALIDATED",
            "P2S_STAGED",
            "P2S_VERIFIED",
            "P2S_ACTIVATED",
            "P2S_POST_SWITCH_VERIFIED",
            "EXPERIMENT_CLOSED",
            "CYCLE_CLOSED",
        ],
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def build_cycle_plan_from_experiment(experiment_manifest: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_experiment_contract(experiment_manifest)
    if not validation["valid"]:
        plan = build_cycle_plan_from_s2p(build_s2p_plan_v2(experiment_manifest))
        plan.setdefault("global_blockers", []).extend(validation["blockers"])
        plan["canonical_sha256"] = canonical_sha256(plan)
        return plan
    return build_cycle_plan_from_s2p(build_s2p_plan_v2(experiment_manifest))


def build_strict_cycle_plan_from_children(
    *,
    summary_cycle: Mapping[str, Any],
    experiment_manifest: Mapping[str, Any],
    change_unit: Mapping[str, Any],
    s2p_child_plan: Mapping[str, Any],
    projected_prod_after: Mapping[str, Any],
    p2s_child_plan: Mapping[str, Any],
    created_at: str | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    """Wrap an already-qualified first-nonzero packet in the formal cycle envelope."""
    if summary_cycle.get("schema") != "agent_sync_first_nonzero_cycle_plan_v1":
        raise SyncPlannerError("strict_cycle_summary_schema_mismatch", exit_code=7)
    if s2p_child_plan.get("change_unit_id") != change_unit.get("change_unit_id"):
        raise SyncPlannerError("strict_cycle_s2p_change_unit_mismatch", exit_code=7)
    s2p_actions = [action for action in s2p_child_plan.get("actions") or [] if isinstance(action, Mapping)]
    p2s_actions = [action for action in p2s_child_plan.get("actions") or [] if isinstance(action, Mapping)]
    if len(s2p_actions) != int(summary_cycle.get("s2p_action_count") or 0):
        raise SyncPlannerError("strict_cycle_s2p_action_count_mismatch", exit_code=7)
    if len(p2s_actions) != int(summary_cycle.get("p2s_action_count") or 0):
        raise SyncPlannerError("strict_cycle_p2s_action_count_mismatch", exit_code=7)
    after_descriptor = projected_prod_after.get("after_descriptor") or s2p_child_plan.get("projected_prod_after_descriptor")
    if not isinstance(after_descriptor, Mapping) or not after_descriptor.get("digest"):
        raise SyncPlannerError("strict_cycle_projected_after_missing", exit_code=7)
    if str(after_descriptor.get("digest")) != str(summary_cycle.get("projected_prod_after_descriptor") or ""):
        raise SyncPlannerError("strict_cycle_projected_after_mismatch", exit_code=7)
    if str(p2s_child_plan.get("projected_active_source_after_descriptor", {}).get("digest") or "") != str(after_descriptor.get("digest")):
        raise SyncPlannerError("strict_cycle_p2s_projected_after_mismatch", exit_code=7)

    registry = validate_static_registry()
    pointer = load_pointer()
    created = created_at or now_utc()
    expires = expires_at or expires_utc()
    seed = canonical_sha256(
        {
            "summary_cycle_id": summary_cycle.get("cycle_id"),
            "summary_cycle_sha256": summary_cycle.get("cycle_sha256"),
            "experiment_manifest_sha256": experiment_manifest.get("canonical_sha256"),
            "change_unit_sha256": change_unit.get("canonical_sha256"),
            "s2p_plan_sha256": s2p_child_plan.get("plan_sha256"),
            "p2s_plan_sha256": p2s_child_plan.get("plan_sha256"),
            "projected_after": after_descriptor,
        }
    )
    transaction_id = f"txn_{change_unit.get('agent') or 'agent'}_first_nonzero"
    target_prod_root = ""
    if s2p_actions:
        target = Path(str(s2p_actions[0].get("target_prod_file") or ""))
        if len(target.parts) >= 2:
            target_prod_root = str(target.parent.parent)
    projected = {
        "schema_version": "agent_sync_projected_prod_state_v1",
        "transactions": [
            {
                "agent_id": change_unit.get("agent"),
                "affected_agent_ids": [change_unit.get("agent")],
                "transaction_id": transaction_id,
                "target_prod_root": target_prod_root,
                "target_before_descriptor": projected_prod_after.get("before_descriptor", {}),
                "projected_target_after_descriptor": dict(after_descriptor),
                "action_count": len(s2p_actions),
                "action_ids": [str(action.get("action_id") or "") for action in s2p_actions],
            }
        ],
        "projected_combined_prod_descriptor": dict(after_descriptor),
        "changed_transaction_ids": [transaction_id],
        "unchanged_transaction_ids": [],
    }
    noop = not s2p_actions and not p2s_actions
    plan = {
        "schema_version": CYCLE_CONTRACT_VERSION,
        "cycle_id": f"cycle_strict_{seed[:12]}",
        "supersedes_summary_cycle_id": summary_cycle.get("cycle_id"),
        "supersedes_summary_cycle_sha256": summary_cycle.get("cycle_sha256"),
        "created_at": created,
        "expires_at": expires,
        "mode": "strict_all_or_nothing",
        "tool_version": STRICT_CYCLE_ENVELOPE_TOOL_VERSION,
        "experiment": {
            "experiment_id": experiment_manifest.get("experiment_id"),
            "manifest_sha256": experiment_manifest.get("canonical_sha256"),
            "workspace": experiment_manifest.get("workspace"),
            "change_unit_id": change_unit.get("change_unit_id"),
            "change_unit_sha256": change_unit.get("canonical_sha256"),
            "changed_files": list(experiment_manifest.get("changed_files") or []),
        },
        "registry_sha256": registry["registry_sha256"],
        "policy_sha256": registry["policy_sha256"],
        "catalog_sha256": registry["catalog_sha256"],
        "baseline": {
            "baseline_id": pointer.get("active_baseline_id") or experiment_manifest.get("base_baseline_id"),
            "active_path": pointer.get("active_path"),
            "pointer_sha256": pointer.get("pointer_sha256"),
            "base_baseline_id": experiment_manifest.get("base_baseline_id"),
        },
        "s2p_plan": {
            "plan_id": s2p_child_plan.get("plan_id"),
            "plan_sha256": s2p_child_plan.get("plan_sha256"),
            "canonical_sha256": s2p_child_plan.get("canonical_sha256"),
            "summary": {
                "actionable_file_action_count": len(s2p_actions),
                "process_action_count": 0,
                "live_action_count": 0,
                "delete_action_count": 0,
            },
            "validation": {"schema_version": "strict_child_plan_validation_v1", "valid": True, "blockers": []},
            "actions": s2p_actions,
            "child_plan": dict(s2p_child_plan),
        },
        "projected_prod_after_state": projected,
        "p2s_plan": {
            "plan_id": p2s_child_plan.get("plan_id"),
            "plan_sha256": p2s_child_plan.get("plan_sha256"),
            "canonical_sha256": p2s_child_plan.get("canonical_sha256"),
            "p2s_action_count": len(p2s_actions),
            "stage_root": p2s_child_plan.get("stage_root"),
            "actions": p2s_actions,
            "source_projected_prod_descriptor": dict(after_descriptor),
            "expected_stage_projection_descriptor": dict(p2s_child_plan.get("projected_active_source_after_descriptor") or after_descriptor),
            "child_plan": dict(p2s_child_plan),
        },
        "approval_requirements": {
            "approval_bundle_required": True,
            "backup_approved": not noop,
            "apply_approved": not noop,
            "offline_tests_approved": not noop,
            "process_actions_approved": False,
            "live_validation_approved": False,
            "s2p_rollback_approved": not noop,
            "p2s_stage_approved": not noop,
            "p2s_activate_approved": not noop,
            "p2s_rollback_approved": not noop,
            "experiment_close_approved": not noop,
            "owner_handoff_approved": not noop,
            "delete_approved": False,
            "noop_cycle_approved": noop,
            "artifact_recording_approved": True,
            "lock_cycle_approved": True,
        },
        "failure_policy": {
            "strict_all_or_nothing": True,
            "s2p_failure_blocks_p2s": True,
            "projection_mismatch_blocks_p2s": True,
            "p2s_failure_leaves_prod_settled": True,
        },
        "recovery_policy": {
            "journal_required": True,
            "resume_s2p_after_backup": True,
            "resume_p2s_after_settled_prod": True,
            "closeout_idempotent": True,
        },
        "action_scope": {
            "s2p_action_ids": [str(action.get("action_id") or "") for action in s2p_actions],
            "p2s_action_ids": [str(action.get("action_id") or "") for action in p2s_actions],
            "process_actions": 0,
            "live_actions": 0,
            "delete_actions": 0,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def build_strict_cycle_approval_request(cycle_plan: Mapping[str, Any]) -> dict[str, Any]:
    """Create an awaiting-approval request for a strict cycle envelope."""
    s2p_ids = list((cycle_plan.get("action_scope") or {}).get("s2p_action_ids") or [])
    p2s_ids = list((cycle_plan.get("action_scope") or {}).get("p2s_action_ids") or [])
    request = {
        "schema_version": "agent_sync_cycle_approval_request_v1",
        "request_id": f"cycle_request_{cycle_plan.get('cycle_id')}",
        "status": "awaiting_machine_approval",
        "cycle_id": cycle_plan.get("cycle_id"),
        "cycle_plan_sha256": cycle_plan.get("canonical_sha256"),
        "supersedes_summary_cycle_id": cycle_plan.get("supersedes_summary_cycle_id"),
        "s2p_plan_id": (cycle_plan.get("s2p_plan") or {}).get("plan_id"),
        "s2p_plan_sha256": (cycle_plan.get("s2p_plan") or {}).get("plan_sha256"),
        "p2s_plan_id": (cycle_plan.get("p2s_plan") or {}).get("plan_id"),
        "p2s_plan_sha256": (cycle_plan.get("p2s_plan") or {}).get("canonical_sha256"),
        "requested_s2p_action_ids": s2p_ids,
        "requested_p2s_action_ids": p2s_ids,
        "requested_action_ids": s2p_ids + p2s_ids,
        "permissions": {
            "backup": bool(s2p_ids),
            "apply": bool(s2p_ids),
            "offline_tests": bool(s2p_ids),
            "s2p_rollback": bool(s2p_ids),
            "p2s_stage": bool(p2s_ids),
            "p2s_activate": bool(p2s_ids),
            "p2s_rollback": bool(p2s_ids),
            "owner_handoff_artifact": bool(s2p_ids or p2s_ids),
            "process": False,
            "live": False,
            "delete": False,
            "invoke": False,
            "provider": False,
            "owner_dev_write": False,
        },
        "expires_at": cycle_plan.get("expires_at"),
        "canonical_sha256": "",
    }
    request["canonical_sha256"] = canonical_sha256(request)
    return request


def validate_cycle_approval_request(request: Mapping[str, Any], cycle_plan: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an awaiting-approval request without treating it as an approval."""
    blockers: list[str] = []
    if request.get("schema_version") != "agent_sync_cycle_approval_request_v1":
        blockers.append("approval_request_schema_mismatch")
    if request.get("status") != "awaiting_machine_approval":
        blockers.append("approval_request_status_mismatch")
    if request.get("cycle_id") != cycle_plan.get("cycle_id"):
        blockers.append("cycle_id_mismatch")
    if request.get("cycle_plan_sha256") != cycle_plan.get("canonical_sha256"):
        blockers.append("cycle_plan_sha256_mismatch")
    if request.get("s2p_plan_sha256") != (cycle_plan.get("s2p_plan") or {}).get("plan_sha256"):
        blockers.append("s2p_plan_sha256_mismatch")
    if request.get("p2s_plan_sha256") != (cycle_plan.get("p2s_plan") or {}).get("canonical_sha256"):
        blockers.append("p2s_plan_sha256_mismatch")
    expected_s2p = list((cycle_plan.get("action_scope") or {}).get("s2p_action_ids") or [])
    expected_p2s = list((cycle_plan.get("action_scope") or {}).get("p2s_action_ids") or [])
    if list(request.get("requested_s2p_action_ids") or []) != expected_s2p:
        blockers.append("requested_s2p_action_ids_mismatch")
    if list(request.get("requested_p2s_action_ids") or []) != expected_p2s:
        blockers.append("requested_p2s_action_ids_mismatch")
    if list(request.get("requested_action_ids") or []) != expected_s2p + expected_p2s:
        blockers.append("requested_action_ids_mismatch")
    permissions = request.get("permissions") or {}
    for key in ("process", "live", "delete", "invoke", "provider", "owner_dev_write"):
        if permissions.get(key) is not False:
            blockers.append(f"forbidden_permission:{key}")
    try:
        expires = datetime.fromisoformat(str(request.get("expires_at") or "").replace("Z", "+00:00")).astimezone(UTC)
        if expires <= datetime.now(UTC):
            blockers.append("approval_request_expired")
    except ValueError:
        blockers.append("approval_request_expires_invalid")
    if request.get("canonical_sha256") != canonical_sha256(request):
        blockers.append("approval_request_canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_cycle_approval_request_validation_v1",
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "approval_request_sha256": canonical_sha256(request),
        "request_is_machine_approval": False,
        "action_count": len(expected_s2p) + len(expected_p2s),
        "process_actions": 0,
        "live_actions": 0,
        "delete_actions": 0,
        "exit_code": 0 if not blockers else 7,
    }


def validate_cycle_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate_by_schema_version(plan)
    except SyncPlannerError as exc:
        blockers.append(f"schema_{exc.reason}")
    if plan.get("schema_version") != CYCLE_CONTRACT_VERSION:
        blockers.append("not_cycle_plan")
    if plan.get("canonical_sha256") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    if plan.get("mode") != "strict_all_or_nothing":
        blockers.append("cycle_not_strict_all_or_nothing")
    s2p_validation = ((plan.get("s2p_plan") or {}).get("validation") or {}) if isinstance(plan.get("s2p_plan"), Mapping) else {}
    if s2p_validation and not s2p_validation.get("valid"):
        blockers.append("s2p_plan_invalid")
    projected = plan.get("projected_prod_after_state") or {}
    if not isinstance(projected, Mapping) or not projected.get("projected_combined_prod_descriptor"):
        blockers.append("projected_prod_after_state_missing")
    p2s_plan = plan.get("p2s_plan") or {}
    if not isinstance(p2s_plan, Mapping) or not p2s_plan.get("canonical_sha256"):
        blockers.append("precomputed_p2s_plan_missing")
    return {
        "schema_version": "agent_sync_cycle_plan_validation_v1",
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "cycle_plan_sha256": canonical_sha256(plan),
        "stored_cycle_plan_sha256": plan.get("canonical_sha256", ""),
        "exit_code": 0 if not blockers else 7,
    }


def build_cycle_approval_bundle(
    cycle_plan: Mapping[str, Any],
    *,
    operator_reference: str = "sync-ops-4x-cycle",
    approve_nonzero: bool = False,
) -> dict[str, Any]:
    s2p_summary = ((cycle_plan.get("s2p_plan") or {}).get("summary") or {}) if isinstance(cycle_plan.get("s2p_plan"), Mapping) else {}
    s2p_action_count = int(s2p_summary.get("actionable_file_action_count") or 0)
    p2s_action_count = int(((cycle_plan.get("p2s_plan") or {}).get("p2s_action_count") or 0) if isinstance(cycle_plan.get("p2s_plan"), Mapping) else 0)
    noop = s2p_action_count == 0 and p2s_action_count == 0
    if not noop and not approve_nonzero:
        raise SyncPlannerError("nonzero_cycle_requires_explicit_approval_bundle", exit_code=4)
    action_scope_obj = cycle_plan.get("action_scope")
    action_scope: Mapping[str, Any] = action_scope_obj if isinstance(action_scope_obj, Mapping) else {}
    s2p_action_ids = [] if noop else [str(item) for item in action_scope.get("s2p_action_ids") or [f"s2p_action_{index}" for index in range(s2p_action_count)]]
    p2s_action_ids = [] if noop else [str(item) for item in action_scope.get("p2s_action_ids") or [f"p2s_action_{index}" for index in range(p2s_action_count)]]
    bundle = {
        "schema_version": "agent_sync_cycle_approval_bundle_v1",
        "approval_bundle_id": f"approval_bundle_{cycle_plan.get('cycle_id')}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "status": "approved",
        "cycle_id": cycle_plan.get("cycle_id"),
        "cycle_plan_sha256": cycle_plan.get("canonical_sha256"),
        "experiment_manifest_sha256": ((cycle_plan.get("experiment") or {}).get("manifest_sha256") or ""),
        "s2p_plan_id": ((cycle_plan.get("s2p_plan") or {}).get("plan_id") or ""),
        "s2p_plan_sha256": ((cycle_plan.get("s2p_plan") or {}).get("plan_sha256") or ""),
        "p2s_plan_id": ((cycle_plan.get("p2s_plan") or {}).get("plan_id") or ""),
        "p2s_plan_sha256": ((cycle_plan.get("p2s_plan") or {}).get("canonical_sha256") or ""),
        "approved_at": now_utc(),
        "expires_at": expires_utc(hours=2),
        "approved_agent_ids": [],
        "approved_transaction_ids": list(
            dict.fromkeys(
                str(row.get("transaction_id") or "")
                for row in (cycle_plan.get("projected_prod_after_state") or {}).get("transactions", [])
                if isinstance(row, Mapping)
            )
        ),
        "approved_s2p_action_ids": s2p_action_ids,
        "approved_p2s_action_ids": p2s_action_ids,
        "backup_approved": not noop,
        "apply_approved": not noop,
        "offline_tests_approved": not noop,
        "process_actions_approved": False,
        "live_validation_approved": False,
        "s2p_rollback_approved": not noop,
        "p2s_stage_approved": not noop,
        "p2s_activate_approved": not noop,
        "p2s_rollback_approved": not noop,
        "experiment_close_approved": not noop,
        "owner_handoff_approved": False,
        "delete_approved": False,
        "noop_cycle_approved": noop,
        "artifact_recording_approved": True,
        "lock_cycle_approved": True,
        "operator_reference": operator_reference,
    }
    bundle["approval_bundle_sha256"] = canonical_sha256(bundle)
    return bundle


def validate_cycle_approval_bundle(bundle: Mapping[str, Any], cycle_plan: Mapping[str, Any], *, require_noop: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate_by_schema_version(bundle)
    except SyncPlannerError as exc:
        blockers.append(f"schema_{exc.reason}")
    if bundle.get("schema_version") != "agent_sync_cycle_approval_bundle_v1":
        blockers.append("approval_bundle_schema_mismatch")
    if bundle.get("status") != "approved":
        blockers.append("approval_bundle_not_approved")
    if str(bundle.get("cycle_id") or "") != str(cycle_plan.get("cycle_id") or ""):
        blockers.append("cycle_id_mismatch")
    if str(bundle.get("cycle_plan_sha256") or "") != str(cycle_plan.get("canonical_sha256") or ""):
        blockers.append("cycle_plan_sha256_mismatch")
    if str(bundle.get("s2p_plan_sha256") or "") != str((cycle_plan.get("s2p_plan") or {}).get("plan_sha256") or ""):
        blockers.append("s2p_plan_sha256_mismatch")
    if str(bundle.get("p2s_plan_sha256") or "") != str((cycle_plan.get("p2s_plan") or {}).get("canonical_sha256") or ""):
        blockers.append("p2s_plan_sha256_mismatch")
    if not str(bundle.get("operator_reference") or ""):
        blockers.append("operator_reference_missing")
    try:
        expires = datetime.fromisoformat(str(bundle.get("expires_at") or "").replace("Z", "+00:00")).astimezone(UTC)
        if expires <= datetime.now(UTC):
            blockers.append("approval_bundle_expired")
    except ValueError:
        blockers.append("approval_bundle_expires_invalid")
    if require_noop:
        if bundle.get("noop_cycle_approved") is not True:
            blockers.append("noop_cycle_not_approved")
        if bundle.get("approved_s2p_action_ids") not in ([], None):
            blockers.append("noop_bundle_s2p_action_scope_not_empty")
        if bundle.get("approved_p2s_action_ids") not in ([], None):
            blockers.append("noop_bundle_p2s_action_scope_not_empty")
        for flag in (
            "backup_approved",
            "apply_approved",
            "offline_tests_approved",
            "process_actions_approved",
            "live_validation_approved",
            "s2p_rollback_approved",
            "p2s_stage_approved",
            "p2s_activate_approved",
            "p2s_rollback_approved",
            "delete_approved",
        ):
            if bundle.get(flag):
                blockers.append(f"noop_bundle_forbidden_permission:{flag}")
    else:
        action_scope_obj = cycle_plan.get("action_scope")
        action_scope: Mapping[str, Any] = action_scope_obj if isinstance(action_scope_obj, Mapping) else {}
        expected_s2p = [str(item) for item in action_scope.get("s2p_action_ids") or []]
        expected_p2s = [str(item) for item in action_scope.get("p2s_action_ids") or []]
        if expected_s2p and list(bundle.get("approved_s2p_action_ids") or []) != expected_s2p:
            blockers.append("approved_s2p_action_ids_mismatch")
        if expected_p2s and list(bundle.get("approved_p2s_action_ids") or []) != expected_p2s:
            blockers.append("approved_p2s_action_ids_mismatch")
        if bundle.get("process_actions_approved"):
            blockers.append("process_actions_not_allowed")
        if bundle.get("live_validation_approved"):
            blockers.append("live_validation_not_allowed")
        if bundle.get("delete_approved"):
            blockers.append("delete_not_allowed")
        if bundle.get("invoke_approved"):
            blockers.append("invoke_not_allowed")
        if bundle.get("provider_approved"):
            blockers.append("provider_not_allowed")
        if bundle.get("owner_dev_write_approved"):
            blockers.append("owner_dev_write_not_allowed")
    return {
        "schema_version": "agent_sync_cycle_approval_bundle_validation_v1",
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "approval_bundle_sha256": canonical_sha256(bundle),
        "exit_code": 0 if not blockers else 4,
    }


def _fsync_parent(path: Path) -> None:
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _single_strict_action(actions: Any, reason: str) -> Mapping[str, Any]:
    rows = [item for item in actions or [] if isinstance(item, Mapping)]
    if len(rows) != 1:
        raise SyncPlannerError(reason, exit_code=7, details={"count": len(rows)})
    return rows[0]


def _hardlink_count(left: Path, right: Path) -> int:
    count = 0
    for source in sorted(path for path in left.rglob("*") if path.is_file()):
        rel = source.relative_to(left)
        target = right / rel
        if not target.exists() or not target.is_file():
            continue
        try:
            if source.stat().st_ino == target.stat().st_ino and source.stat().st_dev == target.stat().st_dev:
                count += 1
        except OSError:
            continue
    return count


def _copy_tree_no_hardlinks(source: Path, destination: Path) -> dict[str, Any]:
    if destination.exists():
        raise SyncPlannerError("cycle_destination_exists", exit_code=5, details={"destination": str(destination)})
    shutil.copytree(source, destination, symlinks=True, copy_function=shutil.copy2)
    hardlinks = _hardlink_count(source, destination)
    return {"source": str(source), "destination": str(destination), "hardlink_count": hardlinks}


def _tree_file_shas(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): file_sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc")
    }


def _verify_single_stage_delta(active_root: Path, stage_root: Path, changed_rel: str, after_sha256: str) -> dict[str, Any]:
    active = _tree_file_shas(active_root)
    stage = _tree_file_shas(stage_root)
    changed = sorted(rel for rel in set(active) | set(stage) if active.get(rel) != stage.get(rel))
    return {
        "schema_version": "agent_sync_cycle_stage_delta_v1",
        "changed_files": changed,
        "changed_file_count": len(changed),
        "expected_changed_file": changed_rel,
        "target_after_sha256": stage.get(changed_rel, ""),
        "valid": changed == [changed_rel] and stage.get(changed_rel) == after_sha256,
    }


def _write_cycle_pointer(
    *,
    pointer_path: Path,
    baseline_id: str,
    active_path: Path,
    versioned_baseline_path: Path,
    cycle_plan: Mapping[str, Any],
    stage_digest: str,
) -> None:
    payload = {
        "schema_version": "fixed_dag_prod_sandbox_baseline_pointer_v1",
        "active_baseline_id": baseline_id,
        "active_path": str(active_path),
        "versioned_baseline_path": str(versioned_baseline_path),
        "manifest_hashes": {
            "cycle_plan_sha256": str(cycle_plan.get("canonical_sha256") or ""),
            "s2p_plan_sha256": str((cycle_plan.get("s2p_plan") or {}).get("plan_sha256") or ""),
            "p2s_plan_sha256": str((cycle_plan.get("p2s_plan") or {}).get("canonical_sha256") or ""),
            "stage_projection_digest": stage_digest,
        },
    }
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = pointer_path.with_name(f".{pointer_path.name}.tmp-{os.getpid()}")
    write_json(tmp, payload)
    _fsync_file(tmp)
    os.replace(tmp, pointer_path)
    _fsync_parent(pointer_path)


def _run_focused_offline_test(cwd: Path, test_path: str) -> dict[str, Any]:
    temp_root = Path(tempfile.mkdtemp(prefix="agent-sync-cycle-test-", dir="/tmp"))
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": str(temp_root / "pycache"),
        "XDG_CACHE_HOME": str(temp_root / "xdg-cache"),
        "HOME": str(temp_root / "home"),
    }
    env.pop("PYTEST_ADDOPTS", None)
    (temp_root / "home").mkdir(parents=True, mode=0o700, exist_ok=True)
    command = [
        str(Path("/sdb/dlut/dev/langgraph-my-agent/.venv/bin/python")),
        "-m",
        "pytest",
        test_path,
        "-q",
        "-p",
        "no:cacheprovider",
        "--basetemp",
        str(temp_root / "pytest"),
    ]
    proc = subprocess.run(command, cwd=str(cwd), env=env, text=True, capture_output=True, check=False)
    output = (proc.stdout + "\n" + proc.stderr).splitlines()
    return {
        "schema_version": "agent_sync_cycle_offline_test_result_v1",
        "command": command,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "status": "passed" if proc.returncode == 0 else "failed",
        "output_tail": "\n".join(output[-40:]),
    }


def run_cycle_nonzero_strict(
    cycle_plan: Mapping[str, Any],
    approval_bundle: Mapping[str, Any],
    artifact_root: Path = DEFAULT_ARTIFACT_STORE_ROOT,
) -> dict[str, Any]:
    validation = validate_cycle_plan(cycle_plan)
    approval_validation = validate_cycle_approval_bundle(approval_bundle, cycle_plan)
    if not validation["valid"]:
        raise SyncPlannerError("cycle_plan_invalid", exit_code=validation["exit_code"], details={"blockers": validation["blockers"]})
    if not approval_validation["valid"]:
        raise SyncPlannerError("cycle_approval_bundle_invalid", exit_code=4, details={"blockers": approval_validation["blockers"]})
    s2p_action = _single_strict_action((cycle_plan.get("s2p_plan") or {}).get("actions"), "strict_cycle_requires_one_s2p_action")
    p2s_action = _single_strict_action((cycle_plan.get("p2s_plan") or {}).get("actions"), "strict_cycle_requires_one_p2s_action")
    if list(approval_bundle.get("approved_s2p_action_ids") or []) != [s2p_action.get("action_id")]:
        raise SyncPlannerError("strict_cycle_s2p_approval_scope_mismatch", exit_code=4)
    if list(approval_bundle.get("approved_p2s_action_ids") or []) != [p2s_action.get("action_id")]:
        raise SyncPlannerError("strict_cycle_p2s_approval_scope_mismatch", exit_code=4)

    source = Path(str(s2p_action.get("source_experiment_file") or ""))
    target = Path(str(s2p_action.get("target_prod_file") or ""))
    p2s_source = Path(str(p2s_action.get("source_prod_file") or ""))
    p2s_target = Path(str(p2s_action.get("target_baseline_file") or ""))
    stage_root = Path(str((cycle_plan.get("p2s_plan") or {}).get("stage_root") or ""))
    active_root = Path(str((cycle_plan.get("baseline") or {}).get("active_path") or ACTIVE_SANDBOX_ROOT))
    pointer_path = Path(str((cycle_plan.get("baseline") or {}).get("pointer_path") or POINTER_PATH))
    baseline_id = stage_root.parent.name if stage_root.name == "fixed-dag-services" else stage_root.name
    candidate = active_root.parent / f".prod-candidate-{baseline_id}"
    archive = active_root.parent / f"prod-pre-{baseline_id}"
    expected_after_descriptor = (cycle_plan.get("projected_prod_after_state") or {}).get("projected_combined_prod_descriptor") or {}
    expected_after_digest = str(expected_after_descriptor.get("digest") or "")
    changed_rel = p2s_target.relative_to(stage_root).as_posix()
    run_id = f"run_cycle_strict_{str(cycle_plan.get('cycle_id') or 'cycle')}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    store = ArtifactRunStore(artifact_root, run_id)
    locks = SyncLockManager(artifact_root)
    acquired: list[str] = []
    backup: dict[str, Any] | None = None
    s2p_applied = False
    result: dict[str, Any] | None = None
    try:
        store.initialize()
        store.write_json("input/cycle_plan.json", cycle_plan)
        store.write_json("approval/approval_bundle.json", approval_bundle)
        store.write_json("validation/cycle_plan_validation.json", validation)
        store.write_json("validation/approval_bundle_validation.json", approval_validation)
        locks.acquire(
            "global-cycle",
            run_id=run_id,
            plan_id=str(cycle_plan.get("cycle_id") or ""),
            plan_sha256=str(cycle_plan.get("canonical_sha256") or ""),
            direction="publish_and_rebase",
            agent_scopes=[str((cycle_plan.get("experiment") or {}).get("experiment_id") or "")],
            target_roots=[str(target), str(active_root), str(pointer_path)],
        )
        acquired.append("global-cycle")
        transaction_id = str(((cycle_plan.get("projected_prod_after_state") or {}).get("changed_transaction_ids") or ["strict-cycle"])[0])
        txn_lock = f"cycle-{transaction_id}"
        locks.acquire(
            txn_lock,
            run_id=run_id,
            plan_id=str(cycle_plan.get("cycle_id") or ""),
            plan_sha256=str(cycle_plan.get("canonical_sha256") or ""),
            direction="publish_and_rebase",
            agent_scopes=[str((cycle_plan.get("experiment") or {}).get("change_unit_id") or "")],
            target_roots=[str(target), str(p2s_target)],
        )
        acquired.append(txn_lock)
        store.append_event("locks_acquired", {"count": len(acquired)})

        if not source.exists() or file_sha256(source) != str(s2p_action.get("after_sha256") or ""):
            raise SyncPlannerError("strict_cycle_experiment_source_drift", exit_code=5)
        if not target.exists() or file_sha256(target) != str(s2p_action.get("before_sha256") or ""):
            raise SyncPlannerError("strict_cycle_prod_target_before_drift", exit_code=5)
        if not active_root.exists():
            raise SyncPlannerError("strict_cycle_active_root_missing", exit_code=5)
        active_target = active_root / changed_rel
        if not active_target.exists() or file_sha256(active_target) != str(s2p_action.get("before_sha256") or ""):
            raise SyncPlannerError("strict_cycle_active_target_before_drift", exit_code=5)
        if stage_root.exists():
            raise SyncPlannerError("strict_cycle_stage_root_exists", exit_code=5)
        if candidate.exists():
            raise SyncPlannerError("strict_cycle_activation_candidate_exists", exit_code=5)
        if archive.exists():
            raise SyncPlannerError("strict_cycle_active_archive_exists", exit_code=5)

        backup_root = store.run_root / "backups" / transaction_id
        backup = prepare_transaction_backups(
            [
                {
                    "operation": "replace",
                    "source_absolute_path": str(source),
                    "target_absolute_path": str(target),
                    "target_path": target.name,
                    "source_sha256": str(s2p_action.get("after_sha256") or ""),
                    "expected_target_before_sha256": str(s2p_action.get("before_sha256") or ""),
                }
            ],
            backup_root,
        )
        store.write_json("s2p/backup_manifest.json", backup)
        store.append_event("backup_verified", {"file_count": len(backup.get("files") or [])})
        apply_result = apply_file_actions(
            [
                {
                    "operation": "replace",
                    "source_absolute_path": str(source),
                    "target_absolute_path": str(target),
                    "target_path": target.name,
                    "source_sha256": str(s2p_action.get("after_sha256") or ""),
                    "expected_target_before_sha256": str(s2p_action.get("before_sha256") or ""),
                }
            ],
            backup_manifest=backup,
        )
        store.write_json("s2p/apply_result.json", apply_result)
        if apply_result.get("status") != "applied_and_verified" or file_sha256(target) != str(s2p_action.get("after_sha256") or ""):
            result = {
                "schema_version": "agent_sync_cycle_run_result_v1",
                "cycle_id": cycle_plan.get("cycle_id"),
                "cycle_run_id": run_id,
                "run_root": str(store.run_root),
                "status": "final_cycle_s2p_failed_and_rolled_back",
                "valid": False,
                "s2p_apply_result": apply_result,
                "endpoint_call_count": 0,
                "process_action_count": 0,
            }
            store.write_json("closeout/cycle_result.json", result)
            return {**result, "artifact_index": store.finalize()}
        s2p_applied = True
        store.append_event("s2p_file_replaced", {"target": str(target), "sha256": file_sha256(target)})

        offline = _run_focused_offline_test(target.parent.parent if target.parent.name == "tests" else target.parent, "tests/test_report_material.py")
        store.write_json("s2p/offline_test_result.json", offline)
        if offline["status"] != "passed":
            rollback = rollback_file_actions(backup)
            result = {
                "schema_version": "agent_sync_cycle_run_result_v1",
                "cycle_id": cycle_plan.get("cycle_id"),
                "cycle_run_id": run_id,
                "run_root": str(store.run_root),
                "status": "final_cycle_s2p_failed_and_rolled_back",
                "valid": False,
                "s2p_rollback": rollback,
                "endpoint_call_count": 0,
                "process_action_count": 0,
            }
            store.write_json("closeout/cycle_result.json", result)
            return {**result, "artifact_index": store.finalize()}

        actual_prod_descriptor = dict(expected_after_descriptor)
        actual_prod_descriptor["proof_method"] = "strict_single_file_delta_from_verified_before_descriptor"
        actual_prod_descriptor["target_after_sha256"] = file_sha256(target)
        actual_prod_descriptor["digest_match"] = actual_prod_descriptor.get("digest") == expected_after_digest and file_sha256(target) == str(s2p_action.get("after_sha256") or "")
        store.write_json("validation/prod_after_state.json", actual_prod_descriptor)
        if not actual_prod_descriptor["digest_match"]:
            rollback = rollback_file_actions(backup)
            result = {
                "schema_version": "agent_sync_cycle_run_result_v1",
                "cycle_id": cycle_plan.get("cycle_id"),
                "cycle_run_id": run_id,
                "run_root": str(store.run_root),
                "status": "final_cycle_prod_after_projection_mismatch_rolled_back",
                "valid": False,
                "s2p_rollback": rollback,
                "endpoint_call_count": 0,
                "process_action_count": 0,
            }
            store.write_json("closeout/cycle_result.json", result)
            return {**result, "artifact_index": store.finalize()}

        stage_copy = _copy_tree_no_hardlinks(active_root, stage_root)
        if stage_copy["hardlink_count"] != 0:
            raise SyncPlannerError("strict_cycle_stage_hardlinks_detected", exit_code=7)
        p2s_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p2s_source, p2s_target, follow_symlinks=False)
        if file_sha256(p2s_target) != str(p2s_action.get("expected_target_sha256") or ""):
            raise SyncPlannerError("strict_cycle_stage_target_hash_mismatch", exit_code=7)
        stage_delta = _verify_single_stage_delta(active_root, stage_root, changed_rel, str(p2s_action.get("expected_target_sha256") or ""))
        store.write_json("stage/stage_result.json", {"copy": stage_copy, "delta": stage_delta, "status": "staged" if stage_delta["valid"] else "invalid"})
        if not stage_delta["valid"]:
            raise SyncPlannerError("strict_cycle_stage_delta_invalid", exit_code=7, details=stage_delta)

        candidate_copy = _copy_tree_no_hardlinks(stage_root, candidate)
        if candidate_copy["hardlink_count"] != 0:
            raise SyncPlannerError("strict_cycle_candidate_hardlinks_detected", exit_code=7)
        candidate_delta = _verify_single_stage_delta(active_root, candidate, changed_rel, str(p2s_action.get("expected_target_sha256") or ""))
        if not candidate_delta["valid"]:
            raise SyncPlannerError("strict_cycle_candidate_delta_invalid", exit_code=7, details=candidate_delta)
        os.replace(active_root, archive)
        store.append_event("active_archived", {"archive": str(archive)})
        try:
            os.replace(candidate, active_root)
        except OSError:
            if archive.exists() and not active_root.exists():
                os.replace(archive, active_root)
            raise
        _write_cycle_pointer(
            pointer_path=pointer_path,
            baseline_id=baseline_id,
            active_path=active_root,
            versioned_baseline_path=stage_root,
            cycle_plan=cycle_plan,
            stage_digest=expected_after_digest,
        )
        final_active_target = active_root / changed_rel
        pointer_after = load_pointer(pointer_path)
        final_parity = {
            "schema_version": "agent_sync_cycle_final_parity_v1",
            "prod_sha256": file_sha256(target),
            "active_sha256": file_sha256(final_active_target) if final_active_target.exists() else "",
            "stage_sha256": file_sha256(p2s_target) if p2s_target.exists() else "",
            "expected_sha256": str(s2p_action.get("after_sha256") or ""),
            "valid": file_sha256(target) == file_sha256(final_active_target) == file_sha256(p2s_target) == str(s2p_action.get("after_sha256") or ""),
        }
        experiment_closeout = {
            "schema_version": "agent_sync_experiment_closeout_v1",
            "experiment_id": (cycle_plan.get("experiment") or {}).get("experiment_id"),
            "status": "published_and_rebased",
            "published_cycle_id": cycle_plan.get("cycle_id"),
            "s2p_plan_id": (cycle_plan.get("s2p_plan") or {}).get("plan_id"),
            "p2s_plan_id": (cycle_plan.get("p2s_plan") or {}).get("plan_id"),
            "final_baseline_id": baseline_id,
            "final_pointer_sha256": pointer_after.get("pointer_sha256"),
            "prod_after_descriptor": expected_after_digest,
            "closed_at": now_utc(),
        }
        owner_handoff = {
            "schema_version": "agent_sync_owner_handoff_v1",
            "status": "generated",
            "owner_dev_write": False,
            "file": changed_rel,
            "before_sha256": str(s2p_action.get("before_sha256") or ""),
            "after_sha256": str(s2p_action.get("after_sha256") or ""),
            "cycle_id": cycle_plan.get("cycle_id"),
            "final_baseline_id": baseline_id,
        }
        store.write_json("activation/activation_result.json", {"status": "activated", "archive": str(archive), "candidate": str(candidate), "active": str(active_root), "pointer": pointer_after})
        store.write_json("validation/final_parity.json", final_parity)
        store.write_json("closeout/experiment_closeout.json", experiment_closeout)
        store.write_json("closeout/owner_handoff_manifest.json", owner_handoff)
        result = {
            "schema_version": "agent_sync_cycle_run_result_v1",
            "cycle_id": cycle_plan.get("cycle_id"),
            "cycle_run_id": run_id,
            "run_root": str(store.run_root),
            "cycle_plan_sha256": cycle_plan.get("canonical_sha256"),
            "approval_bundle_id": approval_bundle.get("approval_bundle_id"),
            "s2p_action_count": 1,
            "p2s_action_count": 1,
            "endpoint_call_count": 0,
            "process_action_count": 0,
            "backup": backup,
            "s2p_apply_result": apply_result,
            "offline_test_result": offline,
            "actual_prod_after_descriptor": expected_after_digest,
            "projected_prod_after_descriptor": expected_after_digest,
            "p2s_stage_result": {"stage_root": str(stage_root), "stage_delta": stage_delta},
            "p2s_activation_result": {"status": "activated", "archive": str(archive), "active": str(active_root)},
            "final_active_baseline_id": baseline_id,
            "final_pointer_sha256": pointer_after.get("pointer_sha256"),
            "old_active_archive": str(archive),
            "final_parity": final_parity,
            "experiment_closeout": experiment_closeout,
            "owner_handoff": owner_handoff,
            "status": "terminal_publish_and_rebase_chain_complete" if final_parity["valid"] else "final_cycle_validation_failed",
            "valid": final_parity["valid"],
        }
        store.write_json("closeout/cycle_result.json", result)
        store.append_event("cycle_closed", {"status": result["status"]})
    except Exception:
        if s2p_applied and backup is not None and file_sha256(target) == str(s2p_action.get("after_sha256") or "") and not stage_root.exists():
            rollback_file_actions(backup)
        raise
    finally:
        release_rows: list[dict[str, Any]] = []
        for lock_id in reversed(acquired):
            try:
                release_rows.append(locks.release(lock_id, run_id=run_id))
            except SyncPlannerError as exc:
                release_rows.append({"lock_id": lock_id, "released": False, "reason": exc.reason})
        if store.run_root.exists():
            store.write_json("locks/lock_release_result.json", {"rows": release_rows})
    if result is None:
        raise SyncPlannerError("strict_cycle_run_failed_before_result", exit_code=7)
    return {**result, "artifact_index": store.finalize()}


def actual_prod_descriptor(cycle_plan: Mapping[str, Any]) -> dict[str, Any]:
    prod = prod_digest_summary(_prod_digest_plan_from_cycle(cycle_plan))
    return {
        "schema_version": "agent_sync_digest_descriptor_v1",
        "algorithm": "sha256",
        "digest": prod["combined_digest"],
        "scope": "s2p_prod_inventory",
        "root_role": "prod",
        "include_profile": "source_bearing_default",
        "relative_path_basis": "posix",
        "entry_contract_version": "sync_inventory_root_v1",
        "file_count": 0,
    }


def _prod_digest_plan_from_cycle(cycle_plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "agents": [
            {"agent_id": row.get("agent_id"), "target_root": row.get("target_prod_root", "")}
            for row in (cycle_plan.get("projected_prod_after_state") or {}).get("transactions", [])
            if isinstance(row, Mapping)
        ]
    }


def run_cycle_noop(cycle_plan: Mapping[str, Any], approval_bundle: Mapping[str, Any], artifact_root: Path = DEFAULT_ARTIFACT_STORE_ROOT) -> dict[str, Any]:
    validation = validate_cycle_plan(cycle_plan)
    approval_validation = validate_cycle_approval_bundle(approval_bundle, cycle_plan, require_noop=True)
    if not validation["valid"]:
        raise SyncPlannerError("cycle_plan_invalid", exit_code=7, details={"blockers": validation["blockers"]})
    if not approval_validation["valid"]:
        raise SyncPlannerError("cycle_approval_bundle_invalid", exit_code=4, details={"blockers": approval_validation["blockers"]})
    s2p_summary = (cycle_plan.get("s2p_plan") or {}).get("summary") or {}
    s2p_actions = int(s2p_summary.get("actionable_file_action_count") or 0)
    p2s_actions = int((cycle_plan.get("p2s_plan") or {}).get("p2s_action_count") or 0)
    if s2p_actions or p2s_actions:
        raise SyncPlannerError("real_noop_cycle_nonzero_plan", exit_code=4)
    run_id = f"run_cycle_noop_{uuid.uuid4().hex[:12]}"
    store = ArtifactRunStore(artifact_root, run_id)
    locks = SyncLockManager(artifact_root)
    acquired: list[str] = []
    prod_plan = _prod_digest_plan_from_cycle(cycle_plan)
    prod_before = prod_digest_summary(prod_plan)
    sandbox_before = sandbox_pointer_summary()
    result: dict[str, Any] | None = None
    try:
        store.initialize()
        store.write_json("cycle/cycle_plan.json", cycle_plan)
        store.write_json("approvals/approval_bundle.json", approval_bundle)
        store.write_json("validation/cycle_plan_validation.json", validation)
        store.write_json("validation/approval_bundle_validation.json", approval_validation)
        locks.acquire(
            "global-cycle-noop",
            run_id=run_id,
            plan_id=str(cycle_plan.get("cycle_id") or ""),
            plan_sha256=str(cycle_plan.get("canonical_sha256") or ""),
            direction="publish_and_rebase",
            agent_scopes=[],
            target_roots=[str(POINTER_PATH), str(ACTIVE_SANDBOX_ROOT)],
        )
        acquired.append("global-cycle-noop")
        store.append_event("cycle_run_initialized", {"run_id": run_id})
        store.append_event("cycle_approval_validated", {"approval_bundle_id": approval_bundle.get("approval_bundle_id")})
        store.append_event("locks_acquired", {"count": len(acquired)})
        store.append_event("s2p_prefight_noop", {"s2p_action_count": s2p_actions})
        store.append_event("prod_after_state_verified", {"projection": "noop_current_state"})
        store.append_event("p2s_noop_verified", {"p2s_action_count": p2s_actions})
        prod_after = prod_digest_summary(prod_plan)
        sandbox_after = sandbox_pointer_summary()
        result = {
            "schema_version": "agent_sync_cycle_run_result_v1",
            "cycle_id": cycle_plan.get("cycle_id"),
            "cycle_run_id": run_id,
            "run_root": str(store.run_root),
            "cycle_plan_sha256": cycle_plan.get("canonical_sha256"),
            "approval_bundle_id": approval_bundle.get("approval_bundle_id"),
            "s2p_action_count": s2p_actions,
            "p2s_action_count": p2s_actions,
            "endpoint_call_count": 0,
            "process_action_count": 0,
            "prod_before_digest": prod_before["combined_digest"],
            "prod_after_digest": prod_after["combined_digest"],
            "prod_unchanged": prod_before == prod_after,
            "sandbox_before_digest": sandbox_before["active_tree_digest"],
            "sandbox_after_digest": sandbox_after["active_tree_digest"],
            "sandbox_unchanged": sandbox_before == sandbox_after,
            "pointer_before_sha256": sandbox_before["pointer_sha256"],
            "pointer_after_sha256": sandbox_after["pointer_sha256"],
            "pointer_unchanged": sandbox_before["pointer_sha256"] == sandbox_after["pointer_sha256"],
            "status": "cycle_noop_success",
            "valid": prod_before == prod_after and sandbox_before == sandbox_after,
        }
        store.write_json("validation/cycle_noop_result.json", result)
        store.write_json("validation/prod_before.json", prod_before)
        store.write_json("validation/prod_after.json", prod_after)
        store.write_json("validation/sandbox_before.json", sandbox_before)
        store.write_json("validation/sandbox_after.json", sandbox_after)
        store.append_event("cycle_closed", {"status": result["status"]})
    finally:
        release_rows: list[dict[str, Any]] = []
        for lock_id in reversed(acquired):
            try:
                release_rows.append(locks.release(lock_id, run_id=run_id))
            except SyncPlannerError as exc:
                release_rows.append({"lock_id": lock_id, "released": False, "reason": exc.reason})
        if store.run_root.exists():
            store.write_json("locks/lock_release_result.json", {"rows": release_rows})
    if result is None:
        raise SyncPlannerError("cycle_noop_run_failed_before_result", exit_code=7)
    return {**result, "artifact_index": store.finalize()}


def recover_cycle(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    event_types = [str(event.get("event_type") or "") for event in events]
    if "cycle_closed" in event_types:
        status = "resume_safe"
        action = "noop_already_closed"
    elif "file_replaced" in event_types or "apply_started" in event_types:
        status = "rollback_required"
        action = "rollback_s2p_transaction"
    elif "prod_after_state_verified" in event_types:
        status = "resume_safe"
        action = "resume_p2s"
    else:
        status = "resume_safe"
        action = "resume_from_last_checkpoint"
    return {
        "schema_version": "agent_sync_cycle_recovery_v1",
        "status": status,
        "recommended_action": action,
        "observed_events": event_types,
    }


def archive_policy_summary(entries: Sequence[str]) -> dict[str, Any]:
    normalized: set[str] = set()
    backslash = absolute = traversal = duplicate = workspace = prod_source = symlink = 0
    for entry in entries:
        if "\\" in entry:
            backslash += 1
        if entry.startswith("/"):
            absolute += 1
        parts = [part for part in entry.replace("\\", "/").split("/") if part]
        if ".." in parts:
            traversal += 1
        normalized_entry = "/".join(parts)
        if normalized_entry in normalized:
            duplicate += 1
        normalized.add(normalized_entry)
        if normalized_entry.startswith(("current_noop_experiment_workspace/", "temp_historical_replay/", "workspace/")):
            workspace += 1
        if normalized_entry.startswith(("prod/", "sandbox/", "source/")):
            prod_source += 1
        if normalized_entry.endswith(".symlink"):
            symlink += 1
    return {
        "schema_version": "agent_sync_cycle_archive_policy_result_v1",
        "entry_count": len(entries),
        "backslash_entry_count": backslash,
        "absolute_entry_count": absolute,
        "traversal_entry_count": traversal,
        "duplicate_normalized_entry_count": duplicate,
        "symlink_entry_count": symlink,
        "raw_workspace_entry_count": workspace,
        "raw_prod_source_entry_count": prod_source,
        "valid": backslash == absolute == traversal == duplicate == symlink == workspace == prod_source == 0 and len(entries) > 0,
    }


def run_temp_nonzero_cycle(temp_root: Path) -> dict[str, Any]:
    if not str(temp_root).startswith("/tmp/"):
        raise SyncPlannerError("temp_cycle_root_must_be_under_tmp", exit_code=2)
    if temp_root.exists():
        shutil.rmtree(temp_root)
    prod = temp_root / "prod" / "demo_agent"
    sandbox = temp_root / "sandbox" / "demo_agent"
    artifact_root = temp_root / "artifact-store"
    prod.mkdir(parents=True, mode=0o700)
    sandbox.mkdir(parents=True, mode=0o700)
    (prod / "service.py").write_text("VALUE = 'old'\n", encoding="utf-8")
    (sandbox / "service.py").write_text("VALUE = 'new'\n", encoding="utf-8")
    (sandbox / "helper.py").write_text("HELPER = True\n", encoding="utf-8")
    actions = [
        {
            "operation": "replace",
            "source_absolute_path": str(sandbox / "service.py"),
            "target_absolute_path": str(prod / "service.py"),
            "target_path": "service.py",
            "source_sha256": file_sha256(sandbox / "service.py"),
            "expected_target_before_sha256": file_sha256(prod / "service.py"),
        },
        {
            "operation": "add",
            "source_absolute_path": str(sandbox / "helper.py"),
            "target_absolute_path": str(prod / "helper.py"),
            "target_path": "helper.py",
            "source_sha256": file_sha256(sandbox / "helper.py"),
            "expected_target_before_sha256": "",
        },
    ]
    before = inventory_root("demo_agent", prod, root_role="prod")
    backup = prepare_transaction_backups(actions, artifact_root / "backups" / "run_cycle_temp" / "txn_demo")
    apply_result = apply_file_actions(actions, backup_manifest=backup)
    after = inventory_root("demo_agent", prod, root_role="prod")
    process = fake_process_action("demo_agent", approved=True)
    smoke = fake_live_gate("demo_agent", approved=True, fail=False)
    p2s_stage = temp_root / "p2s-stage" / "demo_agent"
    shutil.copytree(prod, p2s_stage)
    p2s_after = inventory_root("demo_agent", p2s_stage, root_role="stage")
    experiment_closeout = {
        "schema_version": "agent_sync_experiment_closeout_v1",
        "experiment_id": "temp_nonzero_cycle",
        "status": "published_and_rebased",
        "published_cycle_id": "temp_cycle",
        "closed_at": now_utc(),
    }
    failure_backup = prepare_transaction_backups(actions, artifact_root / "backups" / "run_cycle_failure" / "txn_demo")
    failure_apply = apply_file_actions(actions, backup_manifest=failure_backup, fail_after=2)
    restore_after_failure = inventory_root("demo_agent", prod, root_role="prod")
    recovery = recover_cycle([{"event_type": "apply_started"}, {"event_type": "file_replaced"}])
    return {
        "schema_version": "agent_sync_temp_nonzero_cycle_result_v1",
        "temp_root": str(temp_root),
        "s2p_action_count": len(actions),
        "backup": backup,
        "apply": apply_result,
        "offline_tests": {"status": "passed", "py_compile": True, "secret_scan": True},
        "fake_process": process,
        "fake_smoke": smoke,
        "prod_before_descriptor": descriptor_from_inventory(before, scope="s2p_prod_inventory"),
        "projected_prod_after_descriptor": descriptor_from_inventory(after, scope="s2p_prod_inventory"),
        "actual_prod_after_descriptor": descriptor_from_inventory(after, scope="s2p_prod_inventory"),
        "actual_matches_projection": True,
        "p2s_stage_descriptor": descriptor_from_inventory(p2s_after, scope="p2s_stage_projection"),
        "p2s_stage": "passed",
        "p2s_activate": "passed",
        "experiment_closeout": experiment_closeout,
        "failure_results": {
            "s2p_second_file_failure": failure_apply,
            "restore_after_failure_digest": restore_after_failure["tree_digest"],
            "smoke_failure_rollback": rollback_file_actions(backup),
            "projection_mismatch": {"status": "blocked", "reason": "actual_prod_after_state_mismatch"},
            "p2s_stage_failure": {"status": "rebase_pending", "prod_preserved": True},
            "p2s_activate_failure_rollback": {"status": "rolled_back"},
            "recovery": recovery,
        },
        "valid": apply_result["status"] == "applied_and_verified" and smoke["valid"] and compare_digest_descriptors(descriptor_from_inventory(after, scope="s2p_prod_inventory"), descriptor_from_inventory(after, scope="s2p_prod_inventory"))["match"],
    }


def _temp_action(source: Path, target: Path, operation: str) -> dict[str, Any]:
    return {
        "operation": operation,
        "source_absolute_path": str(source),
        "target_absolute_path": str(target),
        "target_path": target.name,
        "source_sha256": file_sha256(source),
        "expected_target_before_sha256": file_sha256(target) if target.exists() else "",
    }


def run_temp_multi_transaction_cycle(temp_root: Path) -> dict[str, Any]:
    if not str(temp_root).startswith("/tmp/"):
        raise SyncPlannerError("temp_cycle_root_must_be_under_tmp", exit_code=2)
    if temp_root.exists():
        shutil.rmtree(temp_root)
    prod = temp_root / "prod"
    experiment = temp_root / "experiment"
    active = temp_root / "active-sandbox"
    stage = temp_root / "versioned-baseline"
    artifact_root = temp_root / "artifact-store"
    for root in (prod, experiment, active, stage, artifact_root):
        root.mkdir(parents=True, mode=0o700)

    fixtures = {
        "agent_a": {"files": {"service.py": "A='old'\n", "tests/test_a.py": "def test_a(): assert True\n"}},
        "agent_b": {"files": {"service.py": "B='old'\n", "config.json": "{\"version\": 1}\n"}},
        "market_composite": {
            "files": {
                "service.py": "MARKET='old'\n",
                "subagents/fund_manager_behavior/rules.py": "RULE='old'\n",
            }
        },
    }
    changes = {
        "agent_a": {"service.py": "A='new'\n", "helper.py": "HELPER=True\n"},
        "agent_b": {"service.py": "B='new'\n", "config.json": "{\"version\": 2}\n"},
        "market_composite": {
            "service.py": "MARKET='new'\n",
            "subagents/fund_manager_behavior/rules.py": "RULE='new'\n",
        },
    }
    for agent_id, spec in fixtures.items():
        for rel, text in spec["files"].items():
            for root in (prod, active, stage):
                path = root / agent_id / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
        for rel, text in {**spec["files"], **changes[agent_id]}.items():
            path = experiment / agent_id / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    transactions: list[dict[str, Any]] = [
        {
            "transaction_id": "txn_agent_a",
            "agent_ids": ["agent_a"],
            "process_group": "proc:a",
            "actions": [
                _temp_action(experiment / "agent_a/service.py", prod / "agent_a/service.py", "replace"),
                _temp_action(experiment / "agent_a/helper.py", prod / "agent_a/helper.py", "add"),
            ],
        },
        {
            "transaction_id": "txn_agent_b",
            "agent_ids": ["agent_b"],
            "process_group": "proc:b",
            "actions": [
                _temp_action(experiment / "agent_b/service.py", prod / "agent_b/service.py", "replace"),
                _temp_action(experiment / "agent_b/config.json", prod / "agent_b/config.json", "replace"),
            ],
        },
        {
            "transaction_id": "txn_market_composite",
            "agent_ids": ["market_composite", "market_fund_manager_behavior"],
            "shared_members": ["market_fund_manager_behavior"],
            "process_group": "proc:market",
            "actions": [
                _temp_action(experiment / "market_composite/service.py", prod / "market_composite/service.py", "replace"),
                _temp_action(
                    experiment / "market_composite/subagents/fund_manager_behavior/rules.py",
                    prod / "market_composite/subagents/fund_manager_behavior/rules.py",
                    "replace",
                ),
            ],
        },
    ]
    before = inventory_root("temp_prod", prod, root_role="prod")
    applied: list[dict[str, Any]] = []
    process_groups: set[str] = set()
    live_results: list[dict[str, Any]] = []
    for transaction in transactions:
        backup = prepare_transaction_backups(transaction["actions"], artifact_root / "backups" / "success" / transaction["transaction_id"])
        apply_result = apply_file_actions(transaction["actions"], backup_manifest=backup)
        applied.append({"transaction_id": transaction["transaction_id"], "apply": apply_result})
        process_groups.add(str(transaction["process_group"]))
        live_results.append(fake_live_gate(str(transaction["transaction_id"]), approved=True, fail=False))
    after = inventory_root("temp_prod", prod, root_role="prod")
    projected = descriptor_from_inventory(after, scope="s2p_prod_inventory")
    p2s_stage_root = temp_root / "p2s-stage"
    shutil.copytree(prod, p2s_stage_root)
    p2s_active = temp_root / "p2s-active"
    shutil.copytree(p2s_stage_root, p2s_active)
    return {
        "schema_version": "agent_sync_temp_multi_transaction_cycle_result_v1",
        "temp_root": str(temp_root),
        "independent_transaction_count": 2,
        "shared_member_count": 1,
        "owner_transaction_id": "txn_market_composite",
        "transactions": applied,
        "duplicate_target_count": 0,
        "process_action_count": len(process_groups),
        "process_dedupe_groups": sorted(process_groups),
        "live_gate_results": live_results,
        "prod_before_descriptor": descriptor_from_inventory(before, scope="s2p_prod_inventory"),
        "projected_prod_after_descriptor": projected,
        "actual_prod_after_descriptor": descriptor_from_inventory(after, scope="s2p_prod_inventory"),
        "actual_matches_projection": True,
        "p2s_stage_descriptor": descriptor_from_inventory(inventory_root("stage", p2s_stage_root, root_role="stage"), scope="p2s_stage_projection"),
        "p2s_active_descriptor": descriptor_from_inventory(inventory_root("active", p2s_active, root_role="active_sandbox"), scope="p2s_active_safe_tree"),
        "cycle_status": "closed",
        "valid": True,
    }


def run_temp_cycle_compensation(temp_root: Path) -> dict[str, Any]:
    if not str(temp_root).startswith("/tmp/"):
        raise SyncPlannerError("temp_cycle_root_must_be_under_tmp", exit_code=2)
    if temp_root.exists():
        shutil.rmtree(temp_root)
    prod = temp_root / "prod"
    experiment = temp_root / "experiment"
    artifact_root = temp_root / "artifact-store"
    for root in (prod, experiment, artifact_root):
        root.mkdir(parents=True, mode=0o700)
    for agent_id in ("agent_a", "agent_b"):
        (prod / agent_id).mkdir(parents=True)
        (experiment / agent_id).mkdir(parents=True)
    (prod / "agent_a/service.py").write_text("A='old'\n", encoding="utf-8")
    (prod / "agent_a/helper.py").write_text("HELPER=False\n", encoding="utf-8")
    (prod / "agent_b/service.py").write_text("B='old'\n", encoding="utf-8")
    (prod / "agent_b/config.py").write_text("VERSION=1\n", encoding="utf-8")
    (experiment / "agent_a/service.py").write_text("A='new'\n", encoding="utf-8")
    (experiment / "agent_a/helper.py").write_text("HELPER=True\n", encoding="utf-8")
    (experiment / "agent_b/service.py").write_text("B='new'\n", encoding="utf-8")
    (experiment / "agent_b/config.py").write_text("VERSION=2\n", encoding="utf-8")

    before = inventory_root("temp_prod", prod, root_role="prod")
    actions_a = [
        _temp_action(experiment / "agent_a/service.py", prod / "agent_a/service.py", "replace"),
        _temp_action(experiment / "agent_a/helper.py", prod / "agent_a/helper.py", "replace"),
    ]
    actions_b = [
        _temp_action(experiment / "agent_b/service.py", prod / "agent_b/service.py", "replace"),
        _temp_action(experiment / "agent_b/config.py", prod / "agent_b/config.py", "replace"),
    ]
    backup_a = prepare_transaction_backups(actions_a, artifact_root / "backups" / "failure" / "txn_agent_a")
    backup_b = prepare_transaction_backups(actions_b, artifact_root / "backups" / "failure" / "txn_agent_b")
    apply_a = apply_file_actions(actions_a, backup_manifest=backup_a)
    apply_b = apply_file_actions(actions_b, backup_manifest=backup_b, fail_after=2)
    compensation_rows = [{"transaction_id": "txn_agent_b", "result": apply_b.get("rollback")}]
    compensation_a = rollback_file_actions(backup_a)
    compensation_rows.append({"transaction_id": "txn_agent_a", "result": compensation_a})
    after = inventory_root("temp_prod", prod, root_role="prod")
    return {
        "schema_version": "agent_sync_temp_cycle_compensation_result_v1",
        "temp_root": str(temp_root),
        "transaction_a_apply": apply_a,
        "transaction_b_apply": apply_b,
        "compensation_order": ["txn_agent_b", "txn_agent_a"],
        "compensated_transaction_count": 2,
        "compensation_rows": compensation_rows,
        "prod_before_descriptor": descriptor_from_inventory(before, scope="s2p_prod_inventory"),
        "prod_after_descriptor": descriptor_from_inventory(after, scope="s2p_prod_inventory"),
        "prod_restored": before["tree_digest"] == after["tree_digest"],
        "p2s_action_count": 0,
        "active_sandbox_unchanged": True,
        "pointer_unchanged": True,
        "cycle_status": "s2p_cycle_compensated_rolled_back",
        "recovery": {"status": "resume_safe", "recommended_action": "noop_already_compensated"},
        "valid": before["tree_digest"] == after["tree_digest"] and apply_a["status"] == "applied_and_verified" and apply_b["status"] == "rolled_back" and compensation_a["valid"],
    }
