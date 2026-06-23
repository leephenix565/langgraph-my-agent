# ruff: noqa: D101, D103
"""Read-only sync plan builders and validators."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from react_agent.ops.sync_artifacts import (
    DEFAULT_ARTIFACT_STORE_ROOT,
    artifact_store_preflight,
)
from react_agent.ops.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    file_sha256,
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
from react_agent.ops.sync_security import (
    NON_MATERIALIZABLE_SOURCE_CATEGORIES,
    redacted_structural_fingerprint,
)
from react_agent.ops.sync_summary import p2s_summary_from_plan, summary_consistency

POINTER_PATH = Path("/sdb/dlut/sandbox/r8-13a/services/PROD_BASELINE_POINTER.json")
DEFAULT_PROD_ROOT = Path("/sdb/dlut/prod")
DEFAULT_ACTIVE_SANDBOX = Path("/sdb/dlut/sandbox/r8-13a/services/prod")
DEFAULT_VERSIONED_BASELINE = Path("/sdb/dlut/sandbox/prod-baselines/20260623T050419Z/fixed-dag-services")
P2S_EXECUTION_CONTRACT_VERSION = "sync_ops_2a_r3_p2s_execution_contract_v1"
P2S_TOOL_VERSION = "sync_ops_2a_r3_executable_p2s_plan"
READ_ONLY_PLAN_MARKERS = {
    "read_only_plan_only",
    "plan_only",
    "future_write_only",
    "writer_not_available",
}
EXECUTABLE_P2S_PRECONDITIONS = [
    "plan_schema_valid",
    "canonical_hash_valid",
    "plan_not_expired",
    "exact_machine_approval_required",
    "environment_snapshot_match_required",
    "registry_hash_match_required",
    "policy_hash_match_required",
    "catalog_hash_match_required",
    "artifact_store_bootstrapped_or_plan_blocked",
    "global_lock_available",
    "transaction_locks_available",
    "stage_root_missing",
    "active_pointer_unchanged",
    "active_baseline_tree_unchanged",
]
KNOWN_LEGACY_DIAGNOSTIC_PYTHON = {
    "risk_crash/part3_panelExp/core/base_funces/skmodels.py": "legacy_reference_python"
}


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


def _baseline_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _stage_root_for(baseline_id: str) -> Path:
    return Path(f"/sdb/dlut/sandbox/prod-baselines/{baseline_id}/fixed-dag-services")


def _combined_agent_tree_digest(inventory: Mapping[str, Any], root_role: str) -> str:
    items = []
    for agent in inventory.get("agents") or []:
        if not isinstance(agent, Mapping):
            continue
        roots = agent.get("roots") or {}
        root = roots.get(root_role) or {}
        items.append(
            {
                "agent_id": agent.get("agent_id", ""),
                "root_role": root_role,
                "tree_digest": root.get("tree_digest", ""),
                "root_exists": root.get("root_exists", False),
            }
        )
    return canonical_sha256(sorted(items, key=lambda item: str(item["agent_id"])))


def _included_files(root_inventory: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for record in root_inventory.get("files") or []:
        if isinstance(record, Mapping) and record.get("include"):
            result[str(record.get("relative_path") or "")] = record
    return result


def _all_files(root_inventory: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for record in root_inventory.get("files") or []:
        if isinstance(record, Mapping):
            result[str(record.get("relative_path") or "")] = record
    return result


def _source_category_counts(records: Sequence[Mapping[str, Any]], *, include: bool | None = None) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        if include is not None and bool(record.get("include")) is not include:
            continue
        category = str(record.get("source_category") or "unknown_blocked")
        counter[category] += 1
    return dict(sorted(counter.items()))


def _copy_action(
    *,
    agent_id: str,
    affected_agent_ids: list[str],
    transaction_root: str,
    record: Mapping[str, Any],
    source_root_digest: str,
) -> dict[str, Any]:
    rel = str(record.get("relative_path") or "")
    return {
        "action_id": stable_id("mat", "copy_from_prod", transaction_root, rel),
        "operation": "copy_from_prod",
        "agent_id": agent_id,
        "affected_agent_ids": affected_agent_ids,
        "transaction_root": transaction_root,
        "source_path": rel,
        "source_sha256": str(record.get("sha256") or ""),
        "source_mode": str(record.get("mode") or ""),
        "source_file_type": str(record.get("file_type") or ""),
        "source_absolute_path": str(record.get("raw_path") or ""),
        "source_executable": bool(record.get("executable")),
        "source_symlink_target": str(record.get("symlink_target") or ""),
        "source_root_digest": source_root_digest,
        "destination_relative_path": rel,
        "stage_relative_path": f"{agent_id}/{rel}",
        "sensitive_classification": str(record.get("sensitive_classification") or ""),
        "large_asset_classification": str(record.get("large_asset_classification") or ""),
        "source_category": str(record.get("source_category") or ""),
        "source_category_reason": str(record.get("source_category_reason") or ""),
    }


def _preserve_derivative_action(
    *,
    agent_id: str,
    rel: str,
    derivative_record: Mapping[str, Any] | None,
    prod_record: Mapping[str, Any] | None,
    metadata_doc_present: bool,
) -> dict[str, Any]:
    prod_path = Path(str(prod_record.get("raw_path") or "")) if prod_record else None
    fingerprint = (
        redacted_structural_fingerprint(prod_path)
        if prod_path is not None and str(prod_path)
        else {
            "algorithm": "redacted_python_token_fingerprint_v1",
            "status": "manual_sanitized_derivative_refresh_required",
            "finding_category_count": 0,
            "safe_line_ranges": [],
            "redacted_source_sha256": "",
        }
    )
    return {
        "action_id": stable_id("mat", "preserve_sanitized_derivative", agent_id, rel),
        "operation": "preserve_sanitized_derivative",
        "agent_id": agent_id,
        "affected_agent_ids": [agent_id],
        "baseline_derivative_path": rel,
        "destination_relative_path": rel,
        "stage_relative_path": f"{agent_id}/{rel}",
        "derivative_sha256": str((derivative_record or {}).get("sha256") or ""),
        "derivative_manifest_reference": "active_registry_and_baseline_sanitized_derivative_files",
        "derivative_state": "preserve" if derivative_record else "manual_review",
        "redacted_source_fingerprint": fingerprint,
        "safe_line_ranges": fingerprint.get("safe_line_ranges", []),
        "environment_variable_names_only": True,
        "metadata_doc_present": metadata_doc_present,
        "runtime_equivalence": "sanitized_runtime_equivalent_if_redacted_fingerprint_unchanged",
        "ordinary_copy_allowed": False,
    }


def _preserve_metadata_action(
    *,
    agent_id: str,
    rel: str,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "action_id": stable_id("mat", "preserve_sandbox_metadata", agent_id, rel),
        "operation": "preserve_sandbox_metadata",
        "agent_id": agent_id,
        "affected_agent_ids": [agent_id],
        "baseline_metadata_path": rel,
        "destination_relative_path": rel,
        "stage_relative_path": f"{agent_id}/{rel}",
        "metadata_sha256": str(record.get("sha256") or ""),
        "generated_from": "P2S-CLOSE-R1",
    }


def _agent_disposition(agent: Mapping[str, Any], actions: Sequence[Mapping[str, Any]], blocked: Sequence[Mapping[str, Any]]) -> str:
    if blocked:
        return "blocked_sensitive_derivative_refresh"
    sandbox = agent.get("sandbox") or {}
    if isinstance(sandbox, Mapping) and sandbox.get("semantic_placeholder"):
        return "semantic_placeholder_snapshot"
    if agent.get("agent_id") == "market_fund_manager_behavior":
        return "shared_transaction_member"
    if isinstance(sandbox, Mapping) and sandbox.get("sanitized_derivative"):
        return "stage_from_prod_with_preserved_derivative"
    if not actions:
        return "no_source_bearing_files"
    if all(action.get("operation") == "copy_from_prod" for action in actions):
        return "stage_from_prod"
    return "already_equal_but_rematerialized"


def _action_projection_item(action: Mapping[str, Any]) -> dict[str, Any] | None:
    operation = str(action.get("operation") or "")
    if operation in {"copy_from_prod", "snapshot_semantic_placeholder"}:
        return {
            "stage_relative_path": str(action.get("stage_relative_path") or ""),
            "operation": operation,
            "file_type": str(action.get("source_file_type") or ""),
            "sha256": str(action.get("source_sha256") or ""),
            "executable": bool(action.get("source_executable")),
            "symlink_target": str(action.get("source_symlink_target") or ""),
        }
    if operation == "preserve_sanitized_derivative":
        return {
            "stage_relative_path": str(action.get("stage_relative_path") or ""),
            "operation": operation,
            "file_type": "regular",
            "sha256": str(action.get("derivative_sha256") or ""),
            "executable": False,
            "symlink_target": "",
        }
    if operation == "preserve_sandbox_metadata":
        return {
            "stage_relative_path": str(action.get("stage_relative_path") or ""),
            "operation": operation,
            "file_type": "regular",
            "sha256": str(action.get("metadata_sha256") or ""),
            "executable": False,
            "symlink_target": "",
        }
    return None


def stage_projection_digest_for_actions(actions: Sequence[Mapping[str, Any]]) -> str:
    items = [item for action in actions if (item := _action_projection_item(action)) is not None]
    return canonical_sha256(sorted(items, key=lambda item: str(item["stage_relative_path"])))


def artifact_store_initialization_contract(preflight: Mapping[str, Any]) -> dict[str, Any]:
    bootstrap_required = not bool(preflight.get("ready"))
    return {
        "required": False,
        "bootstrap_required": bootstrap_required,
        "root": str(preflight.get("root") or DEFAULT_ARTIFACT_STORE_ROOT),
        "parent": str(preflight.get("parent") or DEFAULT_ARTIFACT_STORE_ROOT.parent),
        "expected_root_state": "missing" if not bool(preflight.get("root_exists")) else "present",
        "recommended_parent_mode": "0750",
        "recommended_root_mode": "0700",
        "recommended_internal_mode": "0700",
        "owner_strategy": "current_operator",
        "group_strategy": "normal_filesystem_inheritance",
        "create_parents": False,
        "approval_required": False,
        "bootstrap_plan_required": bootstrap_required,
        "rollback": "handled_by_artifact_store_bootstrap_contract",
    }


def executable_rollback_contract(plan_id: str) -> dict[str, Any]:
    return {
        "schema_version": "agent_sync_p2s_rollback_contract_v1",
        "plan_id": plan_id,
        "executable": True,
        "cases": [
            {
                "case_id": "stage_failure",
                "trigger": "stage_or_verify_failure_before_activation",
                "actions": ["preserve_failed_stage", "release_locks", "close_run_as_stage_failed"],
                "active_sandbox": "unchanged",
                "pointer": "unchanged",
                "idempotence": "repeat_returns_noop_if_stage_already_marked_failed",
            },
            {
                "case_id": "activation_failure_before_archive",
                "trigger": "candidate_build_or_validation_failure_before_active_archive",
                "actions": ["preserve_failed_candidate", "release_locks"],
                "active_sandbox": "unchanged",
                "pointer": "unchanged",
                "idempotence": "repeat_keeps_active_sandbox_unchanged",
            },
            {
                "case_id": "activation_failure_after_active_archived",
                "trigger": "active_archived_before_candidate_active",
                "actions": ["restore_archive_to_active", "restore_pointer", "preserve_candidate_or_failed_baseline"],
                "active_sandbox": "restored_from_archive",
                "pointer": "restored_to_previous",
                "idempotence": "already_restored_returns_noop_success",
            },
            {
                "case_id": "activation_failure_after_candidate_activated",
                "trigger": "candidate_active_before_or_after_pointer_update",
                "actions": ["move_candidate_active_to_failed_path", "restore_archive", "restore_pointer", "post_rollback_digest"],
                "active_sandbox": "restored_from_archive",
                "pointer": "restored_to_previous",
                "idempotence": "already_rolled_back_returns_noop_success",
            },
            {
                "case_id": "wrong_run_plan_or_approval",
                "trigger": "rollback_request_not_bound_to_run_plan_or_approval",
                "actions": ["fail_closed"],
                "active_sandbox": "unchanged",
                "pointer": "unchanged",
                "idempotence": "repeat_fails_closed_until_correct_binding",
            },
        ],
    }


def executable_plan_contract(
    *,
    plan_id: str,
    stage_root: Path,
    active_path: str,
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    initialization = artifact_store_initialization_contract(preflight)
    return {
        "schema_version": "agent_sync_p2s_execution_contract_v1",
        "writer_contract_version": P2S_EXECUTION_CONTRACT_VERSION,
        "minimum_tool_version": P2S_TOOL_VERSION,
        "execution_enabled": True,
        "artifact_store": {
            "root": str(preflight.get("root") or DEFAULT_ARTIFACT_STORE_ROOT),
            "preflight": dict(preflight),
            "initialization": initialization,
            "bootstrap_required": bool(initialization["bootstrap_required"]),
            "ready": bool(preflight.get("ready")),
            "metadata_sha256": str(preflight.get("metadata_sha256") or ""),
            "initialization_requires_approval": False,
        },
        "lock_requirements": {
            "global_lock": "global-cycle",
            "transaction_lock_prefix": "txn-",
            "lock_root": "artifact_store_root/locks",
            "stage_requires_locks": True,
            "activate_requires_locks": True,
            "rollback_requires_locks": True,
        },
        "stage": {
            "permission": "stage_approved",
            "verify_permission": "verify_approved",
            "stage_root": str(stage_root),
            "expected_stage_root_state": "missing",
            "active_sandbox_mutation_allowed": False,
            "pointer_mutation_allowed": False,
        },
        "verify": {
            "permission": "verify_approved",
            "requires_existing_stage": True,
            "checks": ["file_hashes", "projection_digest", "secret_scan", "validation_profile", "agent_roots"],
        },
        "activation": {
            "permission": "activate_approved",
            "requires_real_stage_closeout": True,
            "stage_only_approval_cannot_activate": True,
            "active_path": active_path,
            "archive_strategy": "atomic_rename_active_then_candidate",
            "candidate_strategy": "copy_or_reflink_without_hardlinks",
        },
        "rollback": executable_rollback_contract(plan_id),
        "crash_recovery": {
            "journal_required": True,
            "recoverable_events": [
                "stage_started",
                "stage_validated",
                "candidate_built",
                "active_archived",
                "candidate_activated",
                "pointer_updated",
                "rollback_started",
                "rollback_finished",
            ],
        },
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
            "environment_snapshot_required": direction == "p2s",
            "stage_approved": False,
            "activate_approved": False,
            "rollback_approved": False,
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


def build_p2s_plan(*, artifact_store_root: Path = DEFAULT_ARTIFACT_STORE_ROOT) -> dict[str, Any]:
    inventory = build_runtime_inventory(include_files=True)
    diff = diff_inventory(inventory)
    pointer = load_baseline_pointer()
    new_baseline_id = _baseline_id()
    stage_root = _stage_root_for(new_baseline_id)
    store_preflight = artifact_store_preflight(artifact_store_root)
    store_ready = bool(store_preflight.get("ready"))
    plan = _base_plan("p2s")
    plan["tool_version"] = P2S_TOOL_VERSION
    plan["execution_status"] = "stage_ready" if store_ready else "blocked_artifact_store_not_ready"
    plan["global_preconditions"] = list(EXECUTABLE_P2S_PRECONDITIONS)
    plan["approval_requirements"]["stage_approved"] = store_ready
    plan["approval_requirements"]["verify_approved"] = store_ready
    plan["approval_requirements"]["artifact_store_initialize_approved"] = False
    plan["approval_requirements"]["activate_approved"] = False
    plan["approval_requirements"]["rollback_approved"] = False
    plan["approval_requirements"]["post_rollback_reactivate_approved"] = False
    plan["baseline"] = pointer
    plan["target_snapshot"] = {
        "active_sandbox_path": pointer["active_path"],
        "active_sandbox_pointer_sha256": pointer["pointer_sha256"],
        "active_baseline_tree_sha256": _combined_agent_tree_digest(inventory, "active_sandbox"),
        "versioned_baseline_tree_sha256": _combined_agent_tree_digest(inventory, "baseline"),
    }
    plan["observed_diff"] = {
        "description": "current prod vs current active/versioned sandbox baseline; explanatory only",
        "summary": diff["totals"],
        "agents": diff["agents"],
    }
    plan["stage_materialization"] = {
        "baseline_id": new_baseline_id,
        "stage_root": str(stage_root),
        "expected_stage_root_state": "missing",
        "stage_root_must_not_equal_active_sandbox": True,
        "stage_root_must_not_equal_current_versioned_baseline": True,
        "transactions": [],
        "action_counts": {},
        "writer_contract": {
            "approval_required": True,
            "environment_snapshot_required": True,
            "global_lock_required": True,
            "transaction_locks_required": True,
            "artifact_store_required": True,
            "validation_profile_required": True,
        },
    }
    plan["artifact_store_preflight"] = store_preflight
    plan["artifact_store_initialization"] = artifact_store_initialization_contract(store_preflight)
    plan["execution_contract"] = executable_plan_contract(
        plan_id=plan["plan_id"],
        stage_root=stage_root,
        active_path=str(pointer["active_path"]),
        preflight=store_preflight,
    )
    plan["rollback_plan"] = executable_rollback_contract(plan["plan_id"])
    plan["activation"] = {
        "old_active_sandbox_archive_path": f"/sdb/dlut/sandbox/r8-13a/services/prod-pre-syncops-{new_baseline_id}",
        "new_versioned_baseline_path": str(stage_root),
        "pointer_candidate": {
            "path": "/sdb/dlut/sandbox/r8-13a/services/PROD_BASELINE_POINTER.json",
            "active_baseline_id": new_baseline_id,
            "active_path": "/sdb/dlut/sandbox/r8-13a/services/prod",
            "versioned_baseline_path": str(stage_root),
        },
        "preconditions": {
            "active_pointer_sha256": pointer["pointer_sha256"],
            "active_baseline_tree_sha256": plan["target_snapshot"]["active_baseline_tree_sha256"],
            "old_active_path": pointer["active_path"],
            "expected_stage_root_state": "missing",
            "registry_sha256": plan["registry_sha256"],
            "policy_sha256": plan["policy_sha256"],
            "catalog_sha256": plan["catalog_sha256"],
        },
        "post_switch_verification": ["pointer_sha256_changed", "26_agent_roots_present", "source_tree_digest_matches_stage"],
        "rollback": {
            "contract_ref": "execution_contract.rollback",
            "restore_old_active_path": pointer["active_path"],
            "preserve_failed_stage": True,
            "requires_rollback_approval": True,
        },
    }
    plan["activation_approval_boundary"] = {
        "stage_only_approval_cannot_activate": True,
        "activation_request_status_before_real_stage": "blocked_pending_real_stage_closeout",
        "required_real_stage_fields": [
            "stage_run_id",
            "stage_artifact_index_sha256",
            "stage_tree_digest",
            "stage_validation_sha256",
            "current_active_pointer_sha256",
            "current_active_tree_sha256",
            "candidate_path",
            "archive_path",
        ],
    }
    agent_plans: list[dict[str, Any]] = []
    registry = load_static_registry()
    inventory_by_id = {agent["agent_id"]: agent for agent in inventory["agents"]}
    diff_by_id = {agent["agent_id"]: agent for agent in diff["agents"]}
    transactions: list[dict[str, Any]] = []
    action_counts: dict[str, int] = {}
    shared_transaction_targets: set[tuple[str, str, str]] = set()
    for registry_agent in registry["agents"]:
        agent_id = registry_agent["agent_id"]
        agent_inventory = inventory_by_id[agent_id]
        roots = agent_inventory["roots"]
        prod_root = roots["prod"]
        active_root = roots["active_sandbox"]
        baseline_root = roots["baseline"]
        prod_files = _included_files(prod_root)
        prod_all = _all_files(prod_root)
        prod_records = [record for record in prod_root.get("files") or [] if isinstance(record, Mapping)]
        active_files = _included_files(active_root)
        baseline_files = _included_files(baseline_root)
        sandbox = registry_agent.get("sandbox") or {}
        derivative_files = set(sandbox.get("sanitized_derivative_files") or []) if isinstance(sandbox, Mapping) else set()
        actions: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        affected = [agent_id]
        transaction_root = str(registry_agent.get("sync", {}).get("transaction_root") or registry_agent["prod"]["root"])
        if agent_id == "market_fund_manager_behavior":
            affected = ["market_composite", "market_fund_manager_behavior"]
            actions.append(
                {
                    "action_id": stable_id("mat", "noop_shared_transaction_member", agent_id),
                    "operation": "noop_shared_transaction_member",
                    "agent_id": agent_id,
                    "affected_agent_ids": affected,
                    "transaction_root": transaction_root,
                    "destination_relative_path": "",
                    "reason": "materialized_by_market_composite_shared_root",
                }
            )
        elif isinstance(sandbox, Mapping) and sandbox.get("semantic_placeholder"):
            for rel, record in sorted(prod_files.items()):
                action = _copy_action(
                    agent_id=agent_id,
                    affected_agent_ids=[agent_id],
                    transaction_root=transaction_root,
                    record=record,
                    source_root_digest=prod_root["tree_digest"],
                )
                action["operation"] = "snapshot_semantic_placeholder"
                actions.append(action)
        else:
            for rel, record in sorted(prod_files.items()):
                if rel in derivative_files:
                    continue
                key = (transaction_root, f"{agent_id}/{rel}", "copy_from_prod")
                if key in shared_transaction_targets:
                    blocked.append({"reason": "duplicate_stage_destination", "relative_path": rel})
                    continue
                shared_transaction_targets.add(key)
                actions.append(
                    _copy_action(
                        agent_id=agent_id,
                        affected_agent_ids=affected,
                        transaction_root=transaction_root,
                        record=record,
                        source_root_digest=prod_root["tree_digest"],
                    )
                )
            for rel in sorted(derivative_files):
                derivative_record = active_files.get(rel) or baseline_files.get(rel)
                prod_record = prod_all.get(rel)
                if derivative_record is None:
                    blocked.append({"reason": "blocked_manual_derivative_refresh", "relative_path": rel})
                    continue
                actions.append(
                    _preserve_derivative_action(
                        agent_id=agent_id,
                        rel=rel,
                        derivative_record=derivative_record,
                        prod_record=prod_record,
                        metadata_doc_present="SANDBOX_SECRET_REQUIREMENTS.md" in active_files
                        or "SANDBOX_SECRET_REQUIREMENTS.md" in baseline_files,
                    )
                )
            for rel, record in sorted(active_files.items()):
                if rel == "SANDBOX_SECRET_REQUIREMENTS.md":
                    actions.append(_preserve_metadata_action(agent_id=agent_id, rel=rel, record=record))
        disposition = _agent_disposition(registry_agent, actions, blocked)
        materialization_ops = {
            "copy_from_prod",
            "preserve_sanitized_derivative",
            "preserve_sandbox_metadata",
            "snapshot_semantic_placeholder",
        }
        materialized_count = sum(1 for action in actions if action.get("operation") in materialization_ops)
        derivative_count = sum(1 for action in actions if action.get("operation") == "preserve_sanitized_derivative")
        metadata_count = sum(1 for action in actions if action.get("operation") == "preserve_sandbox_metadata")
        placeholder_count = sum(1 for action in actions if action.get("operation") == "snapshot_semantic_placeholder")
        agent_projection_digest = stage_projection_digest_for_actions(actions)
        shared_file_count = int(prod_root.get("included_count") or 0) if disposition == "shared_transaction_member" else 0
        for action in actions:
            op = str(action.get("operation") or "")
            action_counts[op] = action_counts.get(op, 0) + 1
        transactions.append(
            {
                "transaction_id": stable_id("stage", agent_id, transaction_root),
                "transaction_root": transaction_root,
                "agent_id": agent_id,
                "affected_agent_ids": affected,
                "disposition": disposition,
                "projection_digest": agent_projection_digest,
                "actions": actions,
                "blocked_actions": blocked,
            }
        )
        agent_plans.append(
            {
                "agent_id": agent_id,
                "transaction_id": stable_id("stage", agent_id, transaction_root),
                "source_root": "prod",
                "target_root": str(stage_root / agent_id),
                "target_before_tree_sha256": active_root["tree_digest"],
                "active_tree_sha256": active_root["tree_digest"],
                "prod_tree_sha256": prod_root["tree_digest"],
                "baseline_tree_sha256": baseline_root["tree_digest"],
                "disposition": disposition,
                "recursive_inventory_file_count": len(prod_root.get("files") or []),
                "current_safe_source_file_count": int(prod_root.get("included_count") or 0),
                "planned_materialization_file_count": materialized_count,
                "derivative_file_count": derivative_count,
                "metadata_file_count": metadata_count,
                "placeholder_file_count": placeholder_count,
                "shared_transaction_file_count": shared_file_count,
                "explicitly_excluded_file_count": int(prod_root.get("excluded_count") or 0),
                "source_category_counts": _source_category_counts(prod_records),
                "materialized_source_category_counts": _source_category_counts(prod_records, include=True),
                "excluded_source_category_counts": _source_category_counts(prod_records, include=False),
                "removed_from_prod_count": 0,
                "unresolved_file_count": len(blocked),
                "coverage_ratio": 1.0 if not blocked else 0.0,
                "projection_digest": agent_projection_digest,
                "actions": actions,
                "blocked_actions": blocked,
                "observed_diff_counts": diff_by_id.get(agent_id, {}).get("counts", {}),
                "backup": {
                    "active_archive_created_during_activation": True,
                    "stage_failure_preserves_failed_stage": True,
                    "no_backup_created_during_stage_only": True,
                },
                "offline_tests": [],
                "process_preflight": {"required": False},
                "process_actions": [],
                "live_validation": [],
                "rollback": {
                    "transaction_rollback_id": stable_id("rollback", stable_id("stage", agent_id, transaction_root)),
                    "contract_ref": "execution_contract.rollback",
                },
                "expected_status": "stage_ready" if not blocked else "blocked_manual_review",
            }
        )
    plan["agents"] = agent_plans
    plan["stage_materialization"]["transactions"] = transactions
    plan["stage_materialization"]["action_counts"] = action_counts
    all_stage_actions = [
        action
        for agent in agent_plans
        for action in agent["actions"]
        if isinstance(action, Mapping)
    ]
    plan["stage_materialization"]["expected_stage_projection_digest"] = stage_projection_digest_for_actions(all_stage_actions)
    plan["diff_summary"] = diff["totals"]
    total_unresolved = sum(int(agent.get("unresolved_file_count") or 0) for agent in agent_plans)
    current_safe_total = sum(int(agent.get("current_safe_source_file_count") or 0) for agent in agent_plans)
    materialized_total = sum(int(agent.get("planned_materialization_file_count") or 0) for agent in agent_plans)
    shared_file_total = sum(int(agent.get("shared_transaction_file_count") or 0) for agent in agent_plans)
    plan["coverage"] = {
        "recursive_inventory_file_count": sum(int(agent.get("recursive_inventory_file_count") or 0) for agent in agent_plans),
        "current_safe_source_file_count": current_safe_total,
        "planned_materialization_file_count": materialized_total,
        "derivative_file_count": sum(int(agent.get("derivative_file_count") or 0) for agent in agent_plans),
        "metadata_file_count": sum(int(agent.get("metadata_file_count") or 0) for agent in agent_plans),
        "placeholder_file_count": sum(int(agent.get("placeholder_file_count") or 0) for agent in agent_plans),
        "shared_transaction_file_count": shared_file_total,
        "explicitly_excluded_file_count": sum(int(agent.get("explicitly_excluded_file_count") or 0) for agent in agent_plans),
        "removed_from_prod_count": 0,
        "unresolved_file_count": total_unresolved,
        "coverage_ratio": 1.0 if total_unresolved == 0 else 0.0,
    }
    source_category_counter: Counter[str] = Counter()
    materialized_category_counter: Counter[str] = Counter()
    excluded_category_counter: Counter[str] = Counter()
    for agent in agent_plans:
        source_category_counter.update(agent.get("source_category_counts") or {})
        materialized_category_counter.update(agent.get("materialized_source_category_counts") or {})
        excluded_category_counter.update(agent.get("excluded_source_category_counts") or {})
    plan["source_selection"] = {
        "schema_version": "agent_sync_source_selection_summary_v1",
        "source_category_counts": dict(sorted(source_category_counter.items())),
        "materialized_source_category_counts": dict(sorted(materialized_category_counter.items())),
        "excluded_source_category_counts": dict(sorted(excluded_category_counter.items())),
        "runtime_asset_count": int(materialized_category_counter.get("runtime_static_asset", 0) + materialized_category_counter.get("test_fixture", 0)),
        "not_scanned_copy_count": sum(
            1
            for action in all_stage_actions
            if action.get("operation") in {"copy_from_prod", "snapshot_semantic_placeholder"}
            and str(action.get("sensitive_classification") or "") == "not_scanned"
        ),
        "unknown_blocked_count": int(source_category_counter.get("unknown_blocked", 0)),
        "sensitive_copy_count": sum(
            1
            for action in all_stage_actions
            if action.get("operation") in {"copy_from_prod", "snapshot_semantic_placeholder"}
            and str(action.get("sensitive_classification") or "") in {"potential_secret_literal", "blocked_env_file", "sensitive_name"}
        ),
    }
    plan["summary"] = p2s_summary_from_plan(plan)
    stage_rel_paths = {
        str(action.get("stage_relative_path") or "")
        for agent in agent_plans
        for action in agent.get("actions") or []
        if isinstance(action, Mapping)
    }
    validation_profile = {
        path: profile
        for path, profile in KNOWN_LEGACY_DIAGNOSTIC_PYTHON.items()
        if path in stage_rel_paths
    }
    if validation_profile:
        plan["validation_profile"] = validation_profile
    if any(agent["blocked_actions"] for agent in agent_plans):
        plan["global_blockers"].append("p2s_blocked_actions_present")
    if not store_ready:
        plan["global_blockers"].append("artifact_store_not_bootstrapped")
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


def validate_plan(
    plan: Mapping[str, Any],
    *,
    check_target_freshness: bool = True,
    allow_existing_stage: bool = False,
) -> dict[str, Any]:
    expected = canonical_sha256(plan)
    blockers: list[str] = []
    try:
        validate_by_schema_version(plan)
    except SyncPlannerError as exc:
        blockers.append(f"schema_{exc.reason}")
    if plan.get("canonical_sha256") != expected:
        blockers.append("canonical_hash_mismatch")
    try:
        parse_utc(str(plan.get("expires_at") or ""))
    except SyncPlannerError:
        blockers.append("invalid_expires_at")
    direction = str(plan.get("direction") or "")
    action_targets: set[tuple[str, str, str]] = set()
    if direction == "p2s":
        target_snapshot = plan.get("target_snapshot") or {}
        stage_materialization = plan.get("stage_materialization") or {}
        activation = plan.get("activation") or {}
        execution_contract = plan.get("execution_contract") or {}
        rollback_plan = plan.get("rollback_plan") or {}
        approval_requirements = plan.get("approval_requirements") or {}
        artifact_initialization = plan.get("artifact_store_initialization") or {}
        read_only_markers = {
            str(item)
            for item in plan.get("global_preconditions") or []
            if str(item) in READ_ONLY_PLAN_MARKERS or any(marker in str(item) for marker in READ_ONLY_PLAN_MARKERS)
        }
        if read_only_markers:
            blockers.append("legacy_read_only_global_precondition")
        if not isinstance(execution_contract, Mapping) or execution_contract.get("schema_version") != "agent_sync_p2s_execution_contract_v1":
            blockers.append("p2s_execution_contract_missing")
        elif execution_contract.get("execution_enabled") is not True:
            blockers.append("p2s_execution_contract_disabled")
        if not isinstance(rollback_plan, Mapping) or rollback_plan.get("executable") is not True:
            blockers.append("rollback_contract_not_executable")
        if rollback_plan.get("skeleton_only") is True or str(rollback_plan.get("execution") or "").startswith("not_available"):
            blockers.append("rollback_contract_not_executable")
        if isinstance(activation, Mapping) and isinstance(activation.get("rollback"), Mapping):
            if activation["rollback"].get("requires_future_phase_execution") is True:
                blockers.append("activation_rollback_not_executable")
        if (
            approval_requirements.get("stage_approved") is True
            and approval_requirements.get("activate_approved") is True
            and approval_requirements.get("rollback_approved") is True
        ):
            blockers.append("approval_phase_scope_too_broad")
        if (
            isinstance(artifact_initialization, Mapping)
            and artifact_initialization.get("required") is True
            and artifact_initialization.get("create_parents") is False
            and (plan.get("artifact_store_preflight") or {}).get("parent_exists") is False
        ):
            blockers.append("artifact_store_init_parent_missing_without_bootstrap")
        if plan.get("summary"):
            if not summary_consistency(plan)["consistent"]:
                blockers.append("p2s_summary_mismatch")
        active_path = str(target_snapshot.get("active_sandbox_path") or "")
        stage_root = str(stage_materialization.get("stage_root") or "")
        if not stage_materialization:
            blockers.append("p2s_stage_materialization_missing")
        if not activation:
            blockers.append("p2s_activation_missing")
        if not str(target_snapshot.get("active_sandbox_pointer_sha256") or ""):
            blockers.append("p2s_active_pointer_sha256_missing")
        if not str(target_snapshot.get("active_baseline_tree_sha256") or ""):
            blockers.append("p2s_active_baseline_tree_sha256_missing")
        if stage_root:
            stage_path = Path(stage_root).resolve(strict=False)
            active_resolved = Path(active_path).resolve(strict=False) if active_path else None
            current_versioned = Path(str(plan.get("baseline", {}).get("versioned_baseline_path") or "")).resolve(strict=False)
            allowed_root = Path("/sdb/dlut/sandbox/prod-baselines").resolve(strict=False)
            temp_root = Path("/tmp").resolve(strict=False)
            if active_resolved and stage_path == active_resolved:
                blockers.append("p2s_stage_root_is_active_sandbox")
            if stage_path == current_versioned:
                blockers.append("p2s_stage_root_is_current_versioned_baseline")
            if allowed_root not in [stage_path, *stage_path.parents] and not (
                plan.get("test_only_temp_roots") is True and temp_root in [stage_path, *stage_path.parents]
            ):
                blockers.append("p2s_stage_root_outside_allowed_namespace")
            if stage_materialization.get("expected_stage_root_state") == "missing" and stage_path.exists() and not allow_existing_stage:
                blockers.append("blocked_stage_path_exists")
        elif stage_materialization:
            blockers.append("p2s_stage_root_missing")
        if activation and not activation.get("preconditions"):
            blockers.append("p2s_activation_preconditions_missing")
        expected_projection = str(stage_materialization.get("expected_stage_projection_digest") or "")
        stage_actions = [
            action
            for txn in stage_materialization.get("transactions") or []
            if isinstance(txn, Mapping)
            for action in txn.get("actions") or []
            if isinstance(action, Mapping)
        ]
        if not expected_projection:
            blockers.append("p2s_stage_projection_digest_missing")
        elif expected_projection != stage_projection_digest_for_actions(stage_actions):
            blockers.append("p2s_stage_projection_digest_mismatch")
        coverage = plan.get("coverage") or {}
        source_selection = plan.get("source_selection") or {}
        if not coverage:
            blockers.append("p2s_coverage_missing")
        else:
            if int(coverage.get("unresolved_file_count") or 0) != 0:
                blockers.append("p2s_coverage_unresolved_files")
            if float(coverage.get("coverage_ratio") or 0.0) != 1.0:
                blockers.append("p2s_coverage_ratio_not_one")
        if source_selection:
            if int(source_selection.get("not_scanned_copy_count") or 0) != 0:
                blockers.append("p2s_not_scanned_copy_present")
            if int(source_selection.get("unknown_blocked_count") or 0) != 0:
                blockers.append("p2s_unknown_blocked_files_present")
            if int(source_selection.get("sensitive_copy_count") or 0) != 0:
                blockers.append("p2s_sensitive_copy_present")
        stage_transaction_action_ids = {
            str(action.get("action_id") or "")
            for txn in stage_materialization.get("transactions") or []
            if isinstance(txn, Mapping)
            for action in txn.get("actions") or []
            if isinstance(action, Mapping)
        }
        if stage_materialization and not stage_transaction_action_ids:
            blockers.append("p2s_stage_materialization_actions_missing")
        transaction_actions_by_id = {
            str(action.get("action_id") or ""): action
            for txn in stage_materialization.get("transactions") or []
            if isinstance(txn, Mapping)
            for action in txn.get("actions") or []
            if isinstance(action, Mapping)
        }
        agent_actions_by_id = {
            str(action.get("action_id") or ""): action
            for agent in plan.get("agents") or []
            if isinstance(agent, Mapping)
            for action in agent.get("actions") or []
            if isinstance(action, Mapping)
        }
        if set(transaction_actions_by_id) != set(agent_actions_by_id):
            blockers.append("transaction_action_parity_mismatch")
        else:
            for action_id, action in agent_actions_by_id.items():
                if action != transaction_actions_by_id[action_id]:
                    blockers.append("transaction_action_parity_mismatch")
                    break
        if len(plan.get("agents") or []) != 26:
            blockers.append("p2s_agent_disposition_count_not_26")
    for agent in plan.get("agents") or []:
        if not isinstance(agent, Mapping):
            blockers.append("agent_plan_not_mapping")
            continue
        if direction == "p2s":
            target_root = str(agent.get("target_root") or "")
            if not str(agent.get("disposition") or ""):
                blockers.append("p2s_agent_disposition_missing")
            if target_root == "active_sandbox" or target_root == str(plan.get("target_snapshot", {}).get("active_sandbox_path") or ""):
                blockers.append("p2s_agent_active_sandbox_target_root")
            if not str(agent.get("target_before_tree_sha256") or ""):
                blockers.append("p2s_agent_target_before_tree_sha256_missing")
            if str(agent.get("projection_digest") or "") != stage_projection_digest_for_actions(
                [action for action in agent.get("actions") or [] if isinstance(action, Mapping)]
            ):
                blockers.append("p2s_agent_projection_digest_mismatch")
            rollback = agent.get("rollback") or {}
            if isinstance(rollback, Mapping) and (
                rollback.get("skeleton_only") is True
                or rollback.get("stage_rollback_only_future_phase") is True
                or not str(rollback.get("transaction_rollback_id") or "")
            ):
                blockers.append("per_agent_rollback_skeleton")
            backup = agent.get("backup") or {}
            if isinstance(backup, Mapping) and (
                backup.get("required_future_phase") is True or backup.get("not_executed_in_sync_ops_1r") is True
            ):
                blockers.append("per_agent_backup_skeleton")
        for action in agent.get("actions") or []:
            if not isinstance(action, Mapping):
                blockers.append("action_not_mapping")
                continue
            operation = str(action.get("operation") or "")
            if direction == "p2s":
                destination = str(action.get("destination_relative_path") or action.get("target_path") or "")
                target = (str(action.get("transaction_root") or agent.get("transaction_id")), destination, operation)
                if target in action_targets and operation not in {"noop", "noop_shared_transaction_member"}:
                    blockers.append("duplicate_action_target")
                action_targets.add(target)
                if operation in {"add", "replace"}:
                    blockers.append("p2s_legacy_add_replace_action")
                    if not str(action.get("source_sha256") or ""):
                        blockers.append("p2s_copy_source_sha256_missing")
                if operation in {"copy_from_prod", "snapshot_semantic_placeholder"}:
                    if not str(action.get("source_sha256") or ""):
                        blockers.append("p2s_copy_source_sha256_missing")
                    if not str(action.get("source_mode") or ""):
                        blockers.append("p2s_copy_source_mode_missing")
                    if not str(action.get("source_file_type") or ""):
                        blockers.append("p2s_copy_source_file_type_missing")
                    sensitive = str(action.get("sensitive_classification") or "")
                    source_category = str(action.get("source_category") or "")
                    if sensitive in {"potential_secret_literal", "blocked_env_file"}:
                        blockers.append("p2s_sensitive_source_used_as_copy")
                    if sensitive == "not_scanned":
                        blockers.append("p2s_copy_sensitive_not_scanned")
                    if source_category in NON_MATERIALIZABLE_SOURCE_CATEGORIES:
                        blockers.append(f"p2s_non_materializable_source_category:{source_category}")
                    if not source_category:
                        blockers.append("p2s_copy_source_category_missing")
                    rel = destination or str(action.get("source_path") or "")
                    if ".bak_" in rel or rel.endswith(".bak") or "_predeploy_" in rel:
                        blockers.append("p2s_backup_runtime_noise_used_as_copy")
                elif operation == "preserve_sanitized_derivative":
                    if not str(action.get("derivative_sha256") or ""):
                        blockers.append("p2s_derivative_sha256_missing")
                    fingerprint = action.get("redacted_source_fingerprint") or {}
                    if not isinstance(fingerprint, Mapping) or not str(fingerprint.get("redacted_source_sha256") or ""):
                        blockers.append("p2s_derivative_redacted_fingerprint_missing")
                    if action.get("source_sha256"):
                        blockers.append("p2s_derivative_has_raw_source_sha")
                elif operation == "preserve_sandbox_metadata":
                    if str(action.get("destination_relative_path") or "") != "SANDBOX_SECRET_REQUIREMENTS.md":
                        blockers.append("p2s_unregistered_sandbox_metadata")
                    if not str(action.get("metadata_sha256") or ""):
                        blockers.append("p2s_metadata_sha256_missing")
                elif operation == "omit_unreachable_sensitive":
                    if not action.get("reachability_evidence"):
                        blockers.append("p2s_omission_reachability_missing")
                elif operation == "reference_large_asset":
                    if action.get("copied") is not False:
                        blockers.append("p2s_large_asset_must_not_copy")
                if stage_transaction_action_ids and str(action.get("action_id") or "") not in stage_transaction_action_ids:
                    blockers.append("p2s_agent_action_missing_from_stage_materialization")
            else:
                target = (str(agent.get("transaction_id")), str(action.get("target_path") or ""), operation)
                if target in action_targets and operation != "noop":
                    blockers.append("duplicate_action_target")
                action_targets.add(target)
            if operation == "delete" and not plan.get("approval_requirements", {}).get("delete_actions_approved"):
                blockers.append("delete_action_without_approval_requirement")
            if operation == "sanitize":
                blockers.append("sanitize_action_not_publishable_in_sync_ops_1")
    if check_target_freshness and plan.get("direction") == "s2p":
        for agent in plan.get("agents") or []:
            if not isinstance(agent, Mapping):
                continue
            target_root_path = Path(str(agent.get("target_root") or ""))
            if not target_root_path.exists():
                continue
            current = inventory_root(str(agent.get("agent_id") or ""), target_root_path, root_role="target")
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
    plan = read_json(path)
    if not isinstance(plan, dict):
        raise SyncPlannerError("plan_not_object", exit_code=2)
    return plan
