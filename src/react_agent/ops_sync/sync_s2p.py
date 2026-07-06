# ruff: noqa: D101, D102, D103
"""Sandbox-to-prod experiment, plan, transaction, and rehearsal helpers."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from react_agent.ops_sync.sync_artifacts import (
    DEFAULT_ARTIFACT_STORE_ROOT,
    ArtifactRunStore,
    artifact_store_preflight,
)
from react_agent.ops_sync.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    file_sha256,
    read_json,
    stable_id,
    validate_by_schema_version,
    write_json,
)
from react_agent.ops_sync.sync_diff import diff_inventory
from react_agent.ops_sync.sync_inventory import inventory_root
from react_agent.ops_sync.sync_lock import SyncLockManager
from react_agent.ops_sync.sync_registry import load_static_registry, validate_static_registry
from react_agent.ops_sync.sync_security import normalize_safe_relative_path

POINTER_PATH = Path("/sdb/dlut/sandbox/r8-13a/services/PROD_BASELINE_POINTER.json")
PROD_ROOT = Path("/sdb/dlut/prod")
ACTIVE_SANDBOX_ROOT = Path("/sdb/dlut/sandbox/r8-13a/services/prod")
S2P_TOOL_VERSION = "sync_ops_3x_s2p_transaction_writer"
S2P_CONTRACT_VERSION = "agent_sync_s2p_execution_contract_v1"
EMPTY_TREE_DIGEST = canonical_sha256([])
READ_ONLY_PLAN_MARKERS = {
    "read_only_plan_only",
    "plan_only",
    "future_write_only",
    "writer_not_available",
}
AUTO_RISK_CLASSES = {"A_docs_tests_material", "B_protocol_wrapper"}
MANUAL_RISK_CLASSES = {"C_data_dependency"}
BLOCKED_RISK_CLASSES = {"D_business_core", "S_security_deployment"}
REPO_ROOT = Path(__file__).resolve().parents[3]


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def expires_utc(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def load_pointer(path: Path = POINTER_PATH) -> dict[str, Any]:
    pointer = read_json(path)
    active = pointer.get("active_path") or pointer.get("active_baseline_path")
    baseline = pointer.get("versioned_baseline_path") or active
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


def _require_tmp_path(path: Path, reason: str) -> None:
    resolved = path.resolve(strict=False)
    tmp = Path("/tmp").resolve(strict=False)
    if tmp not in [resolved, *resolved.parents]:
        raise SyncPlannerError(reason, exit_code=2, details={"path": str(path)})


def _safe_copy_tree(source: Path, destination: Path) -> dict[str, Any]:
    if destination.exists():
        raise SyncPlannerError("experiment_destination_exists", exit_code=2, details={"destination": str(destination)})
    if source.resolve(strict=True) == destination.resolve(strict=False):
        raise SyncPlannerError("experiment_source_equals_destination", exit_code=2)
    copied_files = 0
    copied_dirs = 0
    destination.mkdir(parents=True, mode=0o700)
    copied_dirs += 1
    for current, dirnames, filenames in os.walk(source, topdown=True, followlinks=False):
        current_path = Path(current)
        rel_dir = current_path.relative_to(source)
        target_dir = destination / rel_dir
        target_dir.mkdir(mode=0o700, exist_ok=True)
        for dirname in sorted(dirnames):
            src_dir = current_path / dirname
            if src_dir.is_symlink():
                raise SyncPlannerError("experiment_source_symlink_rejected", exit_code=7, details={"path": str(src_dir)})
            (target_dir / dirname).mkdir(mode=0o700, exist_ok=True)
            copied_dirs += 1
        for filename in sorted(filenames):
            src_file = current_path / filename
            if src_file.is_symlink():
                raise SyncPlannerError("experiment_source_symlink_rejected", exit_code=7, details={"path": str(src_file)})
            if not src_file.is_file():
                continue
            dst_file = target_dir / filename
            shutil.copy2(src_file, dst_file, follow_symlinks=False)
            if src_file.stat().st_nlink > 1 and dst_file.stat().st_ino == src_file.stat().st_ino:
                raise SyncPlannerError("experiment_hardlink_rejected", exit_code=7)
            copied_files += 1
    return {"copied_file_count": copied_files, "copied_directory_count": copied_dirs}


def _registry_by_id() -> dict[str, Mapping[str, Any]]:
    return {str(agent["agent_id"]): agent for agent in load_static_registry()["agents"]}


def _stage_prefix(agent: Mapping[str, Any]) -> str:
    sandbox = agent.get("sandbox") or {}
    return str(sandbox.get("stage_prefix") or agent.get("agent_id") or "")


def digest_descriptor(
    *,
    digest: str,
    scope: str,
    root_role: str,
    include_profile: str = "source_bearing_default",
    file_count: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": "agent_sync_digest_descriptor_v1",
        "algorithm": "sha256",
        "digest": digest,
        "scope": scope,
        "root_role": root_role,
        "include_profile": include_profile,
        "relative_path_basis": "posix",
        "entry_contract_version": "sync_inventory_root_v1",
        "file_count": file_count,
    }


def descriptor_from_inventory(inventory: Mapping[str, Any], *, scope: str, include_profile: str = "source_bearing_default") -> dict[str, Any]:
    return digest_descriptor(
        digest=str(inventory.get("tree_digest") or ""),
        scope=scope,
        root_role=str(inventory.get("root_role") or ""),
        include_profile=include_profile,
        file_count=int(inventory.get("included_count") or 0),
    )


def compare_digest_descriptors(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    compatible_fields = ("algorithm", "scope", "include_profile", "relative_path_basis", "entry_contract_version")
    mismatched = [field for field in compatible_fields if str(left.get(field) or "") != str(right.get(field) or "")]
    if mismatched:
        return {
            "schema_version": "agent_sync_digest_comparison_v1",
            "compatible": False,
            "match": False,
            "reason": "digest_scope_mismatch",
            "mismatched_fields": mismatched,
        }
    return {
        "schema_version": "agent_sync_digest_comparison_v1",
        "compatible": True,
        "match": str(left.get("digest") or "") == str(right.get("digest") or ""),
        "reason": "match" if str(left.get("digest") or "") == str(right.get("digest") or "") else "digest_value_mismatch",
        "mismatched_fields": [],
    }


def _empty_registered_inventory(agent_id: str, root: Path, *, root_role: str) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "root_role": root_role,
        "root": str(root),
        "root_exists": False,
        "registered_empty_tree": True,
        "tree_digest": EMPTY_TREE_DIGEST,
        "files": [],
        "included_count": 0,
        "excluded_count": 0,
        "unicode_collisions": [],
    }


def _inventory_or_registered_empty(agent_id: str, root: Path, *, root_role: str, allow_registered_empty: bool) -> dict[str, Any]:
    if root.exists():
        return inventory_root(agent_id, root, root_role=root_role)
    if allow_registered_empty:
        return _empty_registered_inventory(agent_id, root, root_role=root_role)
    return inventory_root(agent_id, root, root_role=root_role)


def _agent_allows_empty_mapping(agent: Mapping[str, Any]) -> bool:
    sync = agent.get("sync") or {}
    sandbox = agent.get("sandbox") or {}
    return bool(sync.get("registered_empty_tree") or sandbox.get("semantic_placeholder"))


def _source_mapping_blockers(
    *,
    agent_id: str,
    agent: Mapping[str, Any],
    roots: Mapping[str, Mapping[str, Any]],
    is_shared_member: bool,
) -> list[str]:
    if is_shared_member or _agent_allows_empty_mapping(agent):
        return []
    blockers: list[str] = []
    for role in ("baseline", "active_sandbox", "prod"):
        root = roots[role]
        if root.get("root_exists") is False or int(root.get("included_count") or 0) <= 0:
            blockers.append(f"blocked_baseline_source_mapping_missing:{agent_id}:{role}")
    return blockers


def _shared_owner(agent: Mapping[str, Any], registry: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    prod_root_text = str((agent.get("prod") or {}).get("root") or "")
    if not prod_root_text:
        return None
    prod_root = Path(prod_root_text)
    for service_unit in agent.get("service_units") or []:
        if not isinstance(service_unit, Mapping) or service_unit.get("type") != "support_subroot":
            continue
        owner_root_text = str(service_unit.get("root") or "")
        if not owner_root_text:
            continue
        owner_root = Path(owner_root_text).resolve(strict=False)
        for candidate in registry:
            if candidate is agent:
                continue
            candidate_root_text = str((candidate.get("prod") or {}).get("root") or "")
            if candidate_root_text and Path(candidate_root_text).resolve(strict=False) == owner_root:
                try:
                    prod_root.resolve(strict=False).relative_to(owner_root)
                except ValueError:
                    return None
                return candidate
    return None


def _stage_subpath(agent: Mapping[str, Any], registry: Sequence[Mapping[str, Any]]) -> tuple[str, Mapping[str, Any] | None]:
    owner = _shared_owner(agent, registry)
    if owner is None:
        return _stage_prefix(agent), None
    prod_root = Path(str((agent.get("prod") or {}).get("root") or ""))
    owner_root = Path(str((owner.get("prod") or {}).get("root") or ""))
    try:
        rel = prod_root.resolve(strict=False).relative_to(owner_root.resolve(strict=False)).as_posix()
    except ValueError:
        return _stage_prefix(agent), None
    return f"{_stage_prefix(owner)}/{rel}", owner


def _change_unit_files(unit: Mapping[str, Any], agent: Mapping[str, Any]) -> set[str]:
    prefix = _stage_prefix(agent)
    files: set[str] = set()
    for item in unit.get("files") or []:
        text = normalize_safe_relative_path(str(item))
        if text.startswith(f"{prefix}/"):
            text = text[len(prefix) + 1 :]
        files.add(text)
    return files


def build_experiment_fork(*, workspace_root: Path, experiment_id: str | None = None, copy_files: bool = True) -> dict[str, Any]:
    _require_tmp_path(workspace_root, "experiment_workspace_must_be_under_tmp")
    pointer = load_pointer()
    baseline_root = Path(str(pointer["versioned_baseline_path"]))
    if not baseline_root.exists():
        raise SyncPlannerError("baseline_root_missing", exit_code=5, details={"baseline_root": str(baseline_root)})
    forbidden = {
        Path(str(pointer["active_path"])).resolve(strict=False),
        baseline_root.resolve(strict=False),
        PROD_ROOT.resolve(strict=False),
    }
    if workspace_root.resolve(strict=False) in forbidden:
        raise SyncPlannerError("experiment_workspace_forbidden_root", exit_code=2)
    copy_result = _safe_copy_tree(baseline_root, workspace_root) if copy_files else {"copied_file_count": 0, "copied_directory_count": 0}
    registry = load_static_registry()
    for agent in registry["agents"]:
        stage_subpath, _owner = _stage_subpath(agent, registry["agents"])
        (workspace_root / stage_subpath).mkdir(parents=True, mode=0o700, exist_ok=True)
    agents = [
        {
            "agent_id": agent["agent_id"],
            "stage_prefix": _stage_subpath(agent, registry["agents"])[0],
            "workspace_root": str(workspace_root / _stage_subpath(agent, registry["agents"])[0]),
            "prod_root": str((agent.get("prod") or {}).get("root") or ""),
            "transaction_root": str((agent.get("sync") or {}).get("transaction_root") or (agent.get("prod") or {}).get("root") or ""),
        }
        for agent in registry["agents"]
    ]
    manifest = {
        "schema_version": "agent_sync_experiment_v1",
        "experiment_id": experiment_id or f"exp_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:6]}",
        "created_at": now_utc(),
        "base_baseline_id": pointer["active_baseline_id"],
        "base_baseline_manifest_sha256": canonical_sha256(
            {
                "baseline_id": pointer["active_baseline_id"],
                "versioned_baseline_path": pointer["versioned_baseline_path"],
                "manifest_hashes": pointer.get("manifest_hashes", {}),
            }
        ),
        "base_active_pointer_sha256": pointer["pointer_sha256"],
        "workspace_root": str(workspace_root),
        "agents": agents,
        "change_units": [],
        "allowed_paths": [str(workspace_root)],
        "forbidden_paths": [str(pointer["active_path"]), str(pointer["versioned_baseline_path"]), str(PROD_ROOT)],
        "global_non_goals": ["no direct prod writes", "no active baseline mutation", "no owner-dev mutation"],
        "owner_boundaries": ["owner-dev roots are read-only unless separately approved"],
        "test_plan": [],
        "status": "open",
        "fork_result": copy_result,
    }
    write_json(workspace_root / "EXPERIMENT_MANIFEST.json", manifest)
    return manifest


def validate_experiment_contract(manifest: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate_by_schema_version(manifest)
    except SyncPlannerError as exc:
        blockers.append(f"schema_{exc.reason}")
    pointer = load_pointer()
    workspace = Path(str(manifest.get("workspace_root") or ""))
    if str(manifest.get("base_baseline_id") or "") != str(pointer.get("active_baseline_id") or ""):
        blockers.append("base_baseline_id_mismatch")
    if str(manifest.get("status") or "") not in {"draft", "open", "closed", "aborted"}:
        blockers.append("invalid_experiment_status")
    for forbidden in (pointer.get("active_path"), pointer.get("versioned_baseline_path"), str(PROD_ROOT)):
        if forbidden and workspace.resolve(strict=False) == Path(str(forbidden)).resolve(strict=False):
            blockers.append("workspace_is_forbidden_root")
    if workspace.exists():
        for forbidden in manifest.get("forbidden_paths") or []:
            forbidden_path = Path(str(forbidden)).resolve(strict=False)
            if workspace.resolve(strict=False) == forbidden_path:
                blockers.append("workspace_matches_forbidden_path")
    unit_ids: list[str] = []
    for unit in manifest.get("change_units") or []:
        if not isinstance(unit, Mapping):
            blockers.append("change_unit_not_mapping")
            continue
        unit_id = str(unit.get("change_unit_id") or "")
        unit_ids.append(unit_id)
        if unit.get("risk_class") in BLOCKED_RISK_CLASSES and not unit.get("owner_review_required"):
            blockers.append(f"owner_review_required:{unit_id}")
        if not unit.get("files"):
            blockers.append(f"change_unit_files_missing:{unit_id}")
        if not unit.get("intended_behavior"):
            blockers.append(f"change_unit_intended_behavior_missing:{unit_id}")
        if not unit.get("rollback_expectation"):
            blockers.append(f"change_unit_rollback_expectation_missing:{unit_id}")
    if len(unit_ids) != len(set(unit_ids)):
        blockers.append("duplicate_change_unit_id")
    return {
        "schema_version": "agent_sync_experiment_validation_v1",
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "active_baseline_id": pointer["active_baseline_id"],
        "exit_code": 0 if not blockers else 7,
    }


def _experiment_agent_ids(manifest: Mapping[str, Any]) -> set[str]:
    ids = {str(agent.get("agent_id") or "") for agent in manifest.get("agents") or [] if isinstance(agent, Mapping)}
    ids |= {str(unit.get("agent_id") or "") for unit in manifest.get("change_units") or [] if isinstance(unit, Mapping)}
    return {agent_id for agent_id in ids if agent_id}


def _classify_s2p_action(
    row: Mapping[str, Any],
    *,
    unit: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    classification = str(row.get("classification") or "")
    rel = str(row.get("relative_path") or "")
    disposition = {
        "relative_path": rel,
        "classification": classification,
        "s2p_disposition": "diagnostic_only",
    }
    if classification in {
        "unchanged_all",
        "changed_in_prod_only",
        "added_in_prod",
        "changed_in_owner_only",
        "prod_and_owner_same",
        "prod_non_source_runtime_artifact",
        "backup_runtime_noise",
        "binary_or_large_asset",
        "prod_blocked_sensitive_source",
        "semantic_placeholder",
    }:
        disposition["s2p_disposition"] = "preserve_prod_only" if classification in {"changed_in_prod_only", "added_in_prod"} else "noop"
        return None, None, disposition
    if classification == "sandbox_and_prod_same_change":
        disposition["s2p_disposition"] = "already_in_prod"
        return None, None, disposition
    if classification in {"sanitized_derivative", "sandbox_generated_metadata"}:
        if unit is None or row.get("baseline_sha256") == row.get("sandbox_sha256"):
            disposition["s2p_disposition"] = "noop_sandbox_derivative_not_published"
            return None, None, disposition
        disposition["s2p_disposition"] = "blocked_sanitized_derivative_publish"
        return None, {"relative_path": rel, "reason": "blocked_sanitized_derivative_publish"}, disposition
    if classification in {"sandbox_deleted_prod_unchanged", "deleted_in_sandbox"}:
        disposition["s2p_disposition"] = "blocked_delete_disabled"
        return None, {"relative_path": rel, "reason": "blocked_delete_disabled"}, disposition
    if classification == "sandbox_and_prod_diverged":
        disposition["s2p_disposition"] = "blocked_manual_merge"
        return None, {"relative_path": rel, "reason": "blocked_manual_merge"}, disposition
    if classification not in {"changed_in_sandbox_only", "added_in_sandbox", "prod_deleted_sandbox_changed"}:
        disposition["s2p_disposition"] = f"blocked_{classification}"
        return None, {"relative_path": rel, "reason": f"blocked_{classification}"}, disposition
    if unit is None:
        disposition["s2p_disposition"] = "blocked_unregistered_experiment_change"
        return None, {"relative_path": rel, "reason": "blocked_unregistered_experiment_change"}, disposition
    risk = str(unit.get("risk_class") or "")
    if risk in MANUAL_RISK_CLASSES:
        disposition["s2p_disposition"] = "blocked_manual_review_required"
        return None, {"relative_path": rel, "reason": "blocked_manual_review_required", "risk_class": risk}, disposition
    if risk in BLOCKED_RISK_CLASSES:
        disposition["s2p_disposition"] = "blocked_high_risk_change_unit"
        return None, {"relative_path": rel, "reason": "blocked_high_risk_change_unit", "risk_class": risk}, disposition
    operation = "add" if classification in {"added_in_sandbox", "prod_deleted_sandbox_changed"} else "replace"
    action = {
        "operation": operation,
        "relative_path": rel,
        "source_path": rel,
        "target_path": rel,
        "source_sha256": row.get("sandbox_sha256", ""),
        "expected_target_before_sha256": row.get("prod_sha256", ""),
        "expected_target_state": "missing" if operation == "add" else "present",
        "change_unit_id": str(unit.get("change_unit_id") or ""),
        "risk_class": risk,
        "approval_scope": "s2p_change_unit",
        "rollback_source": "planned_backup",
        "classification": classification,
        "owner_provenance": str(unit.get("owner_provenance") or "owner_authority_unresolved"),
    }
    disposition["s2p_disposition"] = "safe_sandbox_change"
    return action, None, disposition


def build_s2p_plan_v2(experiment_manifest: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_experiment_contract(experiment_manifest)
    pointer = load_pointer()
    registry_validation = validate_static_registry()
    registry = load_static_registry()
    registry_by_id = _registry_by_id()
    workspace = Path(str(experiment_manifest.get("workspace_root") or ""))
    created = now_utc()
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_plan_v1",
        "tool_version": S2P_TOOL_VERSION,
        "main_system_dev_head": _git_head(),
        "plan_id": f"s2p_{uuid.uuid4().hex[:12]}",
        "direction": "s2p",
        "created_at": created,
        "expires_at": expires_utc(),
        "registry_sha256": registry_validation["registry_sha256"],
        "policy_sha256": registry_validation["policy_sha256"],
        "catalog_sha256": registry_validation["catalog_sha256"],
        "baseline": pointer,
        "experiment": {
            "experiment_id": experiment_manifest.get("experiment_id", ""),
            "workspace_root": str(workspace),
            "base_baseline_id": experiment_manifest.get("base_baseline_id", ""),
            "manifest_sha256": canonical_sha256(experiment_manifest),
        },
        "target_snapshot": {
            "prod_root": str(PROD_ROOT),
            "active_sandbox_path": pointer["active_path"],
            "active_sandbox_pointer_sha256": pointer["pointer_sha256"],
            "active_baseline_tree_sha256": str((pointer.get("manifest_hashes") or {}).get("stage_tree_digest") or ""),
            "artifact_store_metadata_sha256": artifact_store_preflight(DEFAULT_ARTIFACT_STORE_ROOT).get("metadata_sha256", ""),
        },
        "agents": [],
        "transactions": [],
        "global_preconditions": [
            "plan_schema_valid",
            "canonical_hash_valid",
            "exact_machine_approval_required",
            "artifact_store_ready",
            "global_lock_available",
            "transaction_locks_available",
            "target_snapshot_not_stale",
            "change_unit_gate_passed",
            "backup_before_apply",
            "offline_validation_before_process",
            "process_and_live_independently_approved",
        ],
        "global_blockers": list(validation["blockers"]),
        "approval_requirements": {
            "approval_record_required": True,
            "environment_snapshot_required": True,
            "backup_approved": False,
            "apply_approved": False,
            "offline_tests_approved": False,
            "process_actions_approved": False,
            "live_validation_approved": False,
            "rollback_approved": False,
            "owner_handoff_generation_approved": False,
            "delete_approved": False,
            "publish_and_rebase_approved": False,
            "noop_run_approved": False,
            "artifact_recording_approved": False,
            "lock_cycle_approved": False,
        },
        "execution_contract": {
            "schema_version": S2P_CONTRACT_VERSION,
            "writer_contract_version": S2P_TOOL_VERSION,
            "execution_enabled": True,
            "artifact_store": {
                "root": str(DEFAULT_ARTIFACT_STORE_ROOT),
                "backup_root": str(DEFAULT_ARTIFACT_STORE_ROOT / "backups"),
                "write_artifacts_for_noop": True,
            },
            "lock_requirements": {
                "global_lock_required": True,
                "transaction_locks_required": True,
                "stale_lock_auto_delete": False,
            },
            "backup": {"required_before_replace": True, "backup_root": "backups/<run_id>/<transaction_id>"},
            "apply": {"temporary_replacements_same_filesystem": True, "os_replace": True, "hardlinks_forbidden": True},
            "offline_validation": {"before_process": True, "endpoint_calls_forbidden": True},
            "process": {"requires_process_actions_approved": True, "default_real_process_action_count": 0},
            "live_gate": {"requires_live_validation_approved": True, "invoke_forbidden": True},
            "rollback": {"journaled": True, "per_transaction": True, "restore_backup": True},
            "crash_recovery": {
                "journal_required": True,
                "events": [
                    "s2p_run_initialized",
                    "backup_started",
                    "backup_file_verified",
                    "temp_file_prepared",
                    "apply_started",
                    "file_replaced",
                    "target_verified",
                    "offline_test_started",
                    "offline_test_finished",
                    "process_action_started",
                    "live_gate_started",
                    "rollback_started",
                    "file_restored",
                    "transaction_closed",
                    "run_closed",
                ],
            },
        },
        "rollback_plan": {"executable": True, "journaled": True, "per_transaction": True, "skeleton_only": False},
        "s2p_summary": {},
        "canonical_sha256": "",
    }
    store = artifact_store_preflight(DEFAULT_ARTIFACT_STORE_ROOT)
    if not store.get("ready"):
        plan["global_blockers"].append("artifact_store_not_ready")
    selected_ids = _experiment_agent_ids(experiment_manifest)
    if not selected_ids:
        selected_ids = {str(agent["agent_id"]) for agent in registry["agents"]}
    units_by_agent_file: dict[tuple[str, str], Mapping[str, Any]] = {}
    unit_files_by_id: dict[str, set[str]] = {}
    for unit in experiment_manifest.get("change_units") or []:
        if not isinstance(unit, Mapping):
            continue
        agent = registry_by_id.get(str(unit.get("agent_id") or ""))
        if not agent:
            plan["global_blockers"].append(f"unknown_change_unit_agent:{unit.get('agent_id')}")
            continue
        files = _change_unit_files(unit, agent)
        unit_files_by_id[str(unit.get("change_unit_id") or "")] = files
        for rel in files:
            key = (str(unit.get("agent_id") or ""), rel)
            if key in units_by_agent_file:
                plan["global_blockers"].append(f"change_unit_file_overlap:{key[0]}:{rel}")
            units_by_agent_file[key] = unit
    action_total = 0
    blocked_total = 0
    noop_disposition_count = 0
    prod_preserved_count = 0
    shared_members_by_owner_txn: dict[str, list[str]] = {}
    transaction_ids_by_agent: dict[str, str] = {}
    for agent in registry["agents"]:
        agent_id = str(agent["agent_id"])
        prod_root = Path(str((agent.get("prod") or {}).get("root") or ""))
        transaction_ids_by_agent[agent_id] = stable_id("s2ptxn", agent_id, str((agent.get("sync") or {}).get("transaction_root") or prod_root))
    for agent in registry["agents"]:
        agent_id = str(agent["agent_id"])
        if agent_id not in selected_ids:
            continue
        prefix, shared_owner = _stage_subpath(agent, registry["agents"])
        owner_agent_id = str(shared_owner.get("agent_id") or "") if shared_owner is not None else ""
        is_shared_member = shared_owner is not None
        baseline_root = Path(str(pointer["versioned_baseline_path"])) / prefix
        experiment_root = workspace / prefix
        prod_root = Path(str((agent.get("prod") or {}).get("root") or ""))
        prod_inventory = inventory_root(agent_id, prod_root, root_role="prod") if prod_root.exists() else inventory_root(agent_id, prod_root, root_role="prod")
        allow_registered_empty = _agent_allows_empty_mapping(agent) and not is_shared_member
        roots = {
            "baseline": _inventory_or_registered_empty(agent_id, baseline_root, root_role="baseline", allow_registered_empty=allow_registered_empty),
            "active_sandbox": _inventory_or_registered_empty(agent_id, experiment_root, root_role="experiment", allow_registered_empty=allow_registered_empty),
            "prod": prod_inventory,
        }
        mapping_blockers = _source_mapping_blockers(agent_id=agent_id, agent=agent, roots=roots, is_shared_member=is_shared_member)
        agent_inventory = {
            "agent_id": agent_id,
            "roots": roots,
            "sanitized_derivative": bool((agent.get("sandbox") or {}).get("sanitized_derivative")),
            "semantic_placeholder": bool((agent.get("sandbox") or {}).get("semantic_placeholder")),
        }
        diff = diff_inventory({"agents": [agent_inventory], "registry_sha256": "", "policy_sha256": ""})["agents"][0]
        actions: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        dispositions: list[dict[str, Any]] = []
        for row in diff["rows"]:
            rel = str(row.get("relative_path") or "")
            unit = units_by_agent_file.get((agent_id, rel))
            action, blocked_action, disposition = _classify_s2p_action(row, unit=unit)
            dispositions.append(disposition)
            if disposition["s2p_disposition"] == "noop":
                noop_disposition_count += 1
            if disposition["s2p_disposition"] == "preserve_prod_only":
                prod_preserved_count += 1
            if action and not is_shared_member:
                source_abs = experiment_root / normalize_safe_relative_path(rel)
                target_abs = prod_root / normalize_safe_relative_path(rel)
                action.update(
                    {
                        "action_id": stable_id("s2pact", agent_id, str(unit.get("change_unit_id") if unit else ""), rel, action["operation"]),
                        "agent_id": agent_id,
                        "transaction_root": str((agent.get("sync") or {}).get("transaction_root") or prod_root),
                        "service_unit_id": str((agent.get("sync") or {}).get("process_group_key") or agent_id),
                        "source_absolute_path": str(source_abs),
                        "target_absolute_path": str(target_abs),
                        "source_mode": roots["active_sandbox"]["files"][0]["mode"] if False else "",
                    }
                )
                actions.append(action)
            if blocked_action:
                blocked_action.update({"action_id": stable_id("s2pblk", agent_id, rel, blocked_action["reason"]), "agent_id": agent_id})
                blocked.append(blocked_action)
        for unit_id, files in unit_files_by_id.items():
            unit = next(
                (item for item in experiment_manifest.get("change_units") or [] if isinstance(item, Mapping) and str(item.get("change_unit_id") or "") == unit_id),
                {},
            )
            if str(unit.get("agent_id") or "") == agent_id:
                present = {str(row.get("relative_path") or "") for row in diff["rows"]}
                for rel in sorted(files - present):
                    blocked.append(
                        {
                            "action_id": stable_id("s2pblk", agent_id, rel, "change_unit_file_missing"),
                            "agent_id": agent_id,
                            "relative_path": rel,
                            "reason": "change_unit_file_missing_from_bspd_roots",
                        }
                    )
        for reason in mapping_blockers:
            blocked.append(
                {
                    "action_id": stable_id("s2pblk", agent_id, reason),
                    "agent_id": agent_id,
                    "relative_path": "",
                    "reason": reason,
                }
            )
        transaction_id = transaction_ids_by_agent.get(owner_agent_id, "") if is_shared_member else transaction_ids_by_agent[agent_id]
        if is_shared_member and not transaction_id:
            plan["global_blockers"].append(f"shared_owner_transaction_missing:{agent_id}")
            transaction_id = transaction_ids_by_agent[agent_id]
        transaction = {
            "transaction_id": transaction_id,
            "service_unit_id": str((agent.get("sync") or {}).get("process_group_key") or agent_id),
            "affected_agent_ids": [owner_agent_id, agent_id] if is_shared_member and owner_agent_id else [agent_id],
            "source_experiment_root": str(experiment_root),
            "target_prod_root": str(prod_root),
            "target_before_tree_sha256": roots["prod"]["tree_digest"],
            "file_actions": actions,
            "backup_contract": {"required": bool(actions), "root": "backups/<run_id>/<transaction_id>"},
            "offline_validation": list((agent.get("prod") or {}).get("focused_tests") or []),
            "process_contract": {
                "requires_restart_after_source_change": bool((agent.get("sync") or {}).get("restart_required_after_source_change", True)),
                "process_group_key": str((agent.get("sync") or {}).get("process_group_key") or ""),
                "process_action_requires_approval": True,
            },
            "live_validation_contract": {
                "health_path": str((agent.get("prod") or {}).get("health_path") or ""),
                "compute_path": str((agent.get("prod") or {}).get("compute_path") or ""),
                "requires_live_validation_approved": True,
            },
            "rollback_contract": {"journaled_restore": True, "rollback_approved_required": True},
            "owner_handoff_contract": {"generation_requires_approval": True},
            "blockers": [item["reason"] for item in blocked],
        }
        action_total += len(actions)
        blocked_total += len(blocked)
        if not is_shared_member:
            plan["transactions"].append(transaction)
        elif transaction_id:
            shared_members_by_owner_txn.setdefault(transaction_id, []).append(agent_id)
        plan["agents"].append(
            {
                "agent_id": agent_id,
                "agent_role": "shared_transaction_member" if is_shared_member else "independent_transaction",
                "owner_agent_id": owner_agent_id,
                "owner_transaction_id": transaction_id if is_shared_member else "",
                "independent_materialization": not is_shared_member,
                "independent_apply": not is_shared_member,
                "transaction_id": transaction_id,
                "source_root": str(experiment_root),
                "target_root": str(prod_root),
                "target_before_tree_sha256": roots["prod"]["tree_digest"],
                "baseline_tree_sha256": roots["baseline"]["tree_digest"],
                "experiment_tree_sha256": roots["active_sandbox"]["tree_digest"],
                "baseline_descriptor": descriptor_from_inventory(roots["baseline"], scope="s2p_workspace_inventory"),
                "experiment_descriptor": descriptor_from_inventory(roots["active_sandbox"], scope="s2p_workspace_inventory"),
                "prod_descriptor": descriptor_from_inventory(roots["prod"], scope="s2p_prod_inventory"),
                "baseline_registered_empty_tree": bool(roots["baseline"].get("registered_empty_tree")),
                "experiment_registered_empty_tree": bool(roots["active_sandbox"].get("registered_empty_tree")),
                "prod_registered_empty_tree": bool(roots["prod"].get("registered_empty_tree")),
                "mapping_status": "blocked" if mapping_blockers else "complete",
                "mapping_blockers": mapping_blockers,
                "semantic_placeholder": bool((agent.get("sandbox") or {}).get("semantic_placeholder")),
                "actions": actions,
                "blocked_actions": blocked,
                "bspd_dispositions": dispositions,
                "backup": transaction["backup_contract"],
                "offline_tests": transaction["offline_validation"],
                "process_preflight": transaction["process_contract"],
                "process_actions": [],
                "live_validation": [],
                "rollback": transaction["rollback_contract"],
                "expected_status": "planned" if actions and not blocked else ("noop" if not actions and not blocked else "blocked"),
            }
        )
    for transaction in plan["transactions"]:
        transaction_id = str(transaction.get("transaction_id") or "")
        members = shared_members_by_owner_txn.get(transaction_id, [])
        if members:
            affected = list(dict.fromkeys([*(transaction.get("affected_agent_ids") or []), *members]))
            transaction["affected_agent_ids"] = affected
            transaction["shared_transaction_members"] = members
    if blocked_total:
        plan["global_blockers"].append("s2p_blocked_actions_present")
    plan["s2p_summary"] = {
        "agent_count": len(plan["agents"]),
        "transaction_count": len(plan["transactions"]),
        "actionable_file_action_count": action_total,
        "blocked_action_count": blocked_total,
        "delete_action_count": 0,
        "process_action_count": 0,
        "live_gate_count": 0,
        "noop_disposition_count": noop_disposition_count,
        "prod_only_preserved_count": prod_preserved_count,
        "coverage_ratio": 1.0 if blocked_total == 0 else 0.0,
    }
    plan["diff_summary"] = {
        "actionable_file_action_count": action_total,
        "blocked_action_count": blocked_total,
        "prod_only_preserved_count": prod_preserved_count,
        "noop_disposition_count": noop_disposition_count,
    }
    plan["approval_requirements"]["noop_run_approved"] = action_total == 0 and blocked_total == 0
    plan["approval_requirements"]["artifact_recording_approved"] = action_total == 0 and blocked_total == 0
    plan["approval_requirements"]["lock_cycle_approved"] = action_total == 0 and blocked_total == 0
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def iter_s2p_actions(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        action
        for agent in plan.get("agents") or []
        if isinstance(agent, Mapping)
        for action in agent.get("actions") or []
        if isinstance(action, Mapping)
    ]


def validate_s2p_plan_contract(plan: Mapping[str, Any], *, check_target_freshness: bool = True) -> dict[str, Any]:
    blockers: list[str] = []
    if plan.get("direction") != "s2p":
        blockers.append("not_s2p_plan")
    if plan.get("canonical_sha256") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    if any(str(item) in READ_ONLY_PLAN_MARKERS for item in plan.get("global_preconditions") or []):
        blockers.append("legacy_read_only_global_precondition")
    contract = plan.get("execution_contract") or {}
    if not isinstance(contract, Mapping) or contract.get("schema_version") != S2P_CONTRACT_VERSION:
        blockers.append("s2p_execution_contract_missing")
    rollback = plan.get("rollback_plan") or {}
    if not isinstance(rollback, Mapping) or rollback.get("executable") is not True or rollback.get("skeleton_only") is True:
        blockers.append("s2p_rollback_contract_not_executable")
    if plan.get("global_blockers"):
        blockers.extend(str(item) for item in plan.get("global_blockers") or [])
    action_targets: set[tuple[str, str]] = set()
    for agent in plan.get("agents") or []:
        if not isinstance(agent, Mapping):
            blockers.append("agent_plan_not_mapping")
            continue
        if not str(agent.get("transaction_id") or ""):
            blockers.append("s2p_transaction_id_missing")
        for field in ("baseline_tree_sha256", "experiment_tree_sha256", "target_before_tree_sha256"):
            if not str(agent.get(field) or ""):
                blockers.append(f"s2p_agent_{field}_missing:{agent.get('agent_id')}")
        for field in ("baseline_descriptor", "experiment_descriptor", "prod_descriptor"):
            descriptor = agent.get(field)
            if not isinstance(descriptor, Mapping):
                blockers.append(f"s2p_agent_{field}_missing:{agent.get('agent_id')}")
            elif not str(descriptor.get("digest") or ""):
                blockers.append(f"s2p_agent_{field}_digest_missing:{agent.get('agent_id')}")
        if (
            agent.get("agent_role") != "shared_transaction_member"
            and not agent.get("semantic_placeholder")
            and not agent.get("baseline_registered_empty_tree")
            and not agent.get("experiment_registered_empty_tree")
        ):
            for field in ("baseline_descriptor", "experiment_descriptor", "prod_descriptor"):
                descriptor = agent.get(field)
                if isinstance(descriptor, Mapping) and int(descriptor.get("file_count") or 0) <= 0:
                    blockers.append(f"s2p_agent_empty_inventory_not_registered:{agent.get('agent_id')}:{field}")
        if agent.get("agent_role") == "shared_transaction_member":
            if not str(agent.get("owner_agent_id") or ""):
                blockers.append(f"shared_member_owner_missing:{agent.get('agent_id')}")
            if not str(agent.get("owner_transaction_id") or ""):
                blockers.append(f"shared_member_owner_transaction_missing:{agent.get('agent_id')}")
            if agent.get("independent_apply") is not False:
                blockers.append(f"shared_member_independent_apply_not_false:{agent.get('agent_id')}")
        if (agent.get("backup") or {}).get("required_future_phase") is True:
            blockers.append("s2p_backup_skeleton")
        if (agent.get("rollback") or {}).get("skeleton_only") is True:
            blockers.append("s2p_rollback_skeleton")
        for blocked_action in agent.get("blocked_actions") or []:
            if isinstance(blocked_action, Mapping) and blocked_action.get("reason"):
                blockers.append(str(blocked_action["reason"]))
        for action in agent.get("actions") or []:
            if not isinstance(action, Mapping):
                blockers.append("action_not_mapping")
                continue
            operation = str(action.get("operation") or "")
            action_target = (str(agent.get("transaction_id") or ""), str(action.get("target_path") or ""))
            if action_target in action_targets:
                blockers.append("duplicate_action_target")
            action_targets.add(action_target)
            if operation not in {"add", "replace", "noop", "blocked", "delete"}:
                blockers.append(f"s2p_unknown_operation:{operation}")
            if operation in {"add", "replace"}:
                if not str(action.get("change_unit_id") or ""):
                    blockers.append("s2p_nonnoop_action_missing_change_unit")
                if not str(action.get("source_sha256") or ""):
                    blockers.append("s2p_action_source_sha_missing")
                if operation == "replace" and not str(action.get("expected_target_before_sha256") or ""):
                    blockers.append("s2p_replace_missing_target_before_sha")
            if operation == "delete":
                blockers.append("blocked_delete_disabled")
    if check_target_freshness:
        for agent in plan.get("agents") or []:
            if not isinstance(agent, Mapping):
                continue
            target = Path(str(agent.get("target_root") or ""))
            if not target.exists():
                continue
            current = inventory_root(str(agent.get("agent_id") or ""), target, root_role="prod")
            if str(agent.get("target_before_tree_sha256") or "") != str(current.get("tree_digest") or ""):
                blockers.append("target_snapshot_stale")
                break
    return {
        "schema_version": "agent_sync_s2p_plan_validation_v1",
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "canonical_sha256": canonical_sha256(plan),
        "stored_canonical_sha256": plan.get("canonical_sha256", ""),
        "exit_code": 0 if not blockers else (5 if "target_snapshot_stale" in blockers else 7),
    }


def build_s2p_noop_approval(plan: Mapping[str, Any], *, operator_reference: str = "sync-ops-3x-noop-rehearsal") -> dict[str, Any]:
    if int((plan.get("s2p_summary") or {}).get("actionable_file_action_count") or 0) != 0:
        raise SyncPlannerError("noop_approval_requires_zero_actions", exit_code=4)
    return {
        "schema_version": "agent_sync_s2p_approval_v1",
        "approval_id": f"approval_{plan.get('plan_id')}_noop_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "status": "approved",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "approved_at": now_utc(),
        "expires_at": expires_utc(hours=2),
        "execution_phase": "SYNC-OPS-3X",
        "approved_agent_ids": [str(agent.get("agent_id") or "") for agent in plan.get("agents") or [] if isinstance(agent, Mapping)],
        "approved_transaction_ids": [str(txn.get("transaction_id") or "") for txn in plan.get("transactions") or [] if isinstance(txn, Mapping)],
        "approved_action_ids": [],
        "noop_run_approved": True,
        "artifact_recording_approved": True,
        "lock_cycle_approved": True,
        "backup_approved": False,
        "apply_approved": False,
        "offline_tests_approved": False,
        "process_actions_approved": False,
        "live_validation_approved": False,
        "rollback_approved": False,
        "owner_handoff_generation_approved": False,
        "delete_approved": False,
        "publish_and_rebase_approved": False,
        "operator_reference": operator_reference,
        "notes": "Approved only for zero-action S2P rehearsal; no prod writes, process actions, or live endpoint calls.",
    }


def validate_s2p_approval(approval: Mapping[str, Any], plan: Mapping[str, Any], *, require_noop: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate_by_schema_version(approval)
    except SyncPlannerError as exc:
        blockers.append(f"schema_{exc.reason}")
    if approval.get("schema_version") != "agent_sync_s2p_approval_v1":
        blockers.append("approval_schema_not_s2p")
    if approval.get("status") != "approved":
        blockers.append("approval_status_not_approved")
    if str(approval.get("plan_id") or "") != str(plan.get("plan_id") or ""):
        blockers.append("approval_plan_id_mismatch")
    if str(approval.get("plan_sha256") or "") != str(plan.get("canonical_sha256") or ""):
        blockers.append("approval_plan_sha256_mismatch")
    if str(approval.get("execution_phase") or "") != "SYNC-OPS-3X":
        blockers.append("approval_execution_phase_not_allowed")
    if not str(approval.get("operator_reference") or ""):
        blockers.append("approval_operator_reference_missing")
    try:
        expires = datetime.fromisoformat(str(approval.get("expires_at") or "").replace("Z", "+00:00")).astimezone(UTC)
        if expires <= datetime.now(UTC):
            blockers.append("approval_expired")
    except ValueError:
        blockers.append("approval_expires_invalid")
    allowed_agents = {str(agent.get("agent_id") or "") for agent in plan.get("agents") or [] if isinstance(agent, Mapping)}
    allowed_txns = {str(txn.get("transaction_id") or "") for txn in plan.get("transactions") or [] if isinstance(txn, Mapping)}
    allowed_actions = {str(action.get("action_id") or "") for action in iter_s2p_actions(plan)}
    if set(str(item) for item in approval.get("approved_agent_ids") or []) - allowed_agents:
        blockers.append("approved_agent_ids_outside_plan_scope")
    if set(str(item) for item in approval.get("approved_transaction_ids") or []) - allowed_txns:
        blockers.append("approved_transaction_ids_outside_plan_scope")
    if set(str(item) for item in approval.get("approved_action_ids") or []) - allowed_actions:
        blockers.append("approved_action_ids_outside_plan_scope")
    if require_noop:
        summary = plan.get("s2p_summary") or {}
        if int(summary.get("actionable_file_action_count") or 0) != 0:
            blockers.append("noop_plan_has_actions")
        if approval.get("noop_run_approved") is not True:
            blockers.append("noop_run_not_approved")
        if approval.get("artifact_recording_approved") is not True:
            blockers.append("artifact_recording_not_approved")
        if approval.get("lock_cycle_approved") is not True:
            blockers.append("lock_cycle_not_approved")
        if approval.get("approved_action_ids") not in ([], None):
            blockers.append("noop_approval_action_scope_not_empty")
    for forbidden in (
        "backup_approved",
        "apply_approved",
        "offline_tests_approved",
        "process_actions_approved",
        "live_validation_approved",
        "delete_approved",
        "publish_and_rebase_approved",
    ):
        if require_noop and approval.get(forbidden):
            blockers.append(f"noop_approval_forbidden_permission:{forbidden}")
    if any(keyword in str(approval).lower() for keyword in ("password", "api_key", "secret=", "token=")):
        blockers.append("approval_contains_sensitive_keyword")
    return {
        "schema_version": "agent_sync_s2p_approval_validation_v1",
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "approval_sha256": canonical_sha256(approval),
        "exit_code": 0 if not blockers else 4,
    }


def prod_digest_summary(plan: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for agent in plan.get("agents") or []:
        if not isinstance(agent, Mapping):
            continue
        target = Path(str(agent.get("target_root") or ""))
        digest = inventory_root(str(agent.get("agent_id") or ""), target, root_role="prod")["tree_digest"] if target.exists() else ""
        rows.append({"agent_id": agent.get("agent_id"), "target_root": str(target), "tree_digest": digest})
    return {"rows": rows, "combined_digest": canonical_sha256(rows)}


def sandbox_pointer_summary() -> dict[str, Any]:
    pointer = load_pointer()
    active = Path(str(pointer.get("active_path") or ""))
    active_digest = inventory_root("active_sandbox", active, root_role="active_sandbox")["tree_digest"] if active.exists() else ""
    return {
        "pointer_sha256": pointer["pointer_sha256"],
        "active_path": str(active),
        "active_tree_digest": active_digest,
        "active_baseline_id": pointer["active_baseline_id"],
    }


def run_s2p_noop(plan: Mapping[str, Any], approval: Mapping[str, Any], artifact_root: Path = DEFAULT_ARTIFACT_STORE_ROOT) -> dict[str, Any]:
    validation = validate_s2p_plan_contract(plan, check_target_freshness=True)
    approval_validation = validate_s2p_approval(approval, plan, require_noop=True)
    if not validation["valid"]:
        raise SyncPlannerError("s2p_plan_invalid", exit_code=validation["exit_code"], details={"blockers": validation["blockers"]})
    if not approval_validation["valid"]:
        raise SyncPlannerError("s2p_approval_invalid", exit_code=4, details={"blockers": approval_validation["blockers"]})
    if int((plan.get("s2p_summary") or {}).get("actionable_file_action_count") or 0) != 0:
        raise SyncPlannerError("real_noop_rehearsal_nonzero_plan", exit_code=4)
    run_id = f"run_s2p_noop_{uuid.uuid4().hex[:12]}"
    store = ArtifactRunStore(artifact_root, run_id)
    lock_manager = SyncLockManager(artifact_root)
    acquired: list[str] = []
    prod_before = prod_digest_summary(plan)
    sandbox_before = sandbox_pointer_summary()
    result: dict[str, Any] | None = None
    try:
        store.initialize()
        store.write_json("input/plan.json", plan)
        store.write_json("approval/approval.json", approval)
        store.write_json("validation/plan_validation.json", validation)
        store.write_json("validation/approval_validation.json", approval_validation)
        global_lock = lock_manager.acquire(
            "global-s2p-noop",
            run_id=run_id,
            plan_id=str(plan.get("plan_id") or ""),
            plan_sha256=str(plan.get("canonical_sha256") or ""),
            direction="s2p",
            agent_scopes=[str(agent.get("agent_id") or "") for agent in plan.get("agents") or [] if isinstance(agent, Mapping)],
            target_roots=[str(PROD_ROOT)],
        )
        acquired.append("global-s2p-noop")
        store.append_event("s2p_run_initialized", {"run_id": run_id, "mode": "real_noop"})
        store.append_event("locks_acquired", {"global": global_lock["lock_id"]})
        txn_lock_ids: list[str] = []
        for txn in plan.get("transactions") or []:
            if not isinstance(txn, Mapping):
                continue
            lock_id = f"s2p-{txn.get('transaction_id')}"
            lock_manager.acquire(
                lock_id,
                run_id=run_id,
                plan_id=str(plan.get("plan_id") or ""),
                plan_sha256=str(plan.get("canonical_sha256") or ""),
                direction="s2p",
                agent_scopes=[str(item) for item in txn.get("affected_agent_ids") or []],
                target_roots=[str(txn.get("target_prod_root") or "")],
            )
            acquired.append(lock_id)
            txn_lock_ids.append(lock_id)
        store.append_event("transaction_locks_acquired", {"count": len(txn_lock_ids)})
        store.append_event("noop_verified", {"action_count": 0, "process_action_count": 0, "endpoint_call_count": 0})
        prod_after = prod_digest_summary(plan)
        sandbox_after = sandbox_pointer_summary()
        result = {
            "schema_version": "agent_sync_s2p_noop_run_result_v1",
            "run_id": run_id,
            "run_root": str(store.run_root),
            "plan_id": plan.get("plan_id"),
            "plan_sha256": plan.get("canonical_sha256"),
            "action_count": 0,
            "approved_action_count": 0,
            "process_action_count": 0,
            "endpoint_call_count": 0,
            "prod_before_digest": prod_before["combined_digest"],
            "prod_after_digest": prod_after["combined_digest"],
            "prod_unchanged": prod_before == prod_after,
            "sandbox_before_digest": sandbox_before["active_tree_digest"],
            "sandbox_after_digest": sandbox_after["active_tree_digest"],
            "sandbox_unchanged": sandbox_before == sandbox_after,
            "pointer_before_sha256": sandbox_before["pointer_sha256"],
            "pointer_after_sha256": sandbox_after["pointer_sha256"],
            "pointer_unchanged": sandbox_before["pointer_sha256"] == sandbox_after["pointer_sha256"],
            "status": "noop_success",
            "valid": prod_before == prod_after and sandbox_before == sandbox_after,
        }
        store.write_json("validation/noop_run_result.json", result)
        store.write_json("validation/prod_before.json", prod_before)
        store.write_json("validation/prod_after.json", prod_after)
        store.write_json("validation/sandbox_before.json", sandbox_before)
        store.write_json("validation/sandbox_after.json", sandbox_after)
        store.append_event("run_closed", {"status": result["status"]})
    finally:
        release_rows: list[dict[str, Any]] = []
        for lock_id in reversed(acquired):
            try:
                release_rows.append(lock_manager.release(lock_id, run_id=run_id))
            except SyncPlannerError as exc:
                release_rows.append({"lock_id": lock_id, "released": False, "reason": exc.reason})
        if store.run_root.exists():
            store.write_json("locks/lock_release_result.json", {"released_count": sum(1 for row in release_rows if row.get("state") == "released"), "rows": release_rows})
    if result is None:
        raise SyncPlannerError("s2p_noop_run_failed_before_result", exit_code=7)
    return {**result, "artifact_index": store.finalize()}


def prepare_transaction_backups(actions: Sequence[Mapping[str, Any]], backup_root: Path) -> dict[str, Any]:
    backup_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for action in actions:
        if str(action.get("operation") or "") not in {"replace", "add"}:
            continue
        target = Path(str(action.get("target_absolute_path") or ""))
        rel = normalize_safe_relative_path(str(action.get("target_path") or target.name))
        backup_path = backup_root / rel
        backup_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if target.exists():
            shutil.copy2(target, backup_path, follow_symlinks=False)
            rows.append(
                {
                    "relative_path": rel,
                    "target_absolute_path": str(target),
                    "exists_before": True,
                    "target_sha256": file_sha256(target),
                    "backup_sha256": file_sha256(backup_path),
                    "mode": oct(stat.S_IMODE(target.stat().st_mode)),
                    "restore_action": "replace_from_backup",
                }
            )
        else:
            rows.append(
                {
                    "relative_path": rel,
                    "target_absolute_path": str(target),
                    "exists_before": False,
                    "backup_sha256": "",
                    "restore_action": "delete_created_file",
                }
            )
    return {"schema_version": "agent_sync_s2p_backup_manifest_v1", "backup_root": str(backup_root), "files": rows}


def apply_file_actions(actions: Sequence[Mapping[str, Any]], *, backup_manifest: Mapping[str, Any], fail_after: int | None = None) -> dict[str, Any]:
    replaced: list[dict[str, Any]] = []
    try:
        for index, action in enumerate(actions, start=1):
            operation = str(action.get("operation") or "")
            if operation not in {"replace", "add"}:
                continue
            source = Path(str(action.get("source_absolute_path") or ""))
            target = Path(str(action.get("target_absolute_path") or ""))
            if not source.exists():
                raise SyncPlannerError("s2p_source_missing", exit_code=8, details={"source": str(source)})
            expected_source = str(action.get("source_sha256") or "")
            if expected_source and file_sha256(source) != expected_source:
                raise SyncPlannerError("s2p_source_hash_drift", exit_code=5, details={"source": str(source)})
            if operation == "replace":
                if not target.exists():
                    raise SyncPlannerError("s2p_target_missing_for_replace", exit_code=5, details={"target": str(target)})
                expected_before = str(action.get("expected_target_before_sha256") or "")
                if expected_before and file_sha256(target) != expected_before:
                    raise SyncPlannerError("s2p_target_hash_drift", exit_code=5, details={"target": str(target)})
            if target.exists() and target.is_symlink():
                raise SyncPlannerError("s2p_target_symlink_rejected", exit_code=8, details={"target": str(target)})
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(f".{target.name}.s2p-tmp-{os.getpid()}")
            shutil.copy2(source, tmp, follow_symlinks=False)
            if tmp.stat().st_ino == source.stat().st_ino:
                raise SyncPlannerError("s2p_hardlink_rejected", exit_code=8)
            os.replace(tmp, target)
            replaced.append({"target": str(target), "operation": operation, "sha256": file_sha256(target)})
            if fail_after is not None and index >= fail_after:
                raise SyncPlannerError("simulated_apply_failure", exit_code=8)
        return {"schema_version": "agent_sync_s2p_apply_result_v1", "status": "applied_and_verified", "replaced": replaced, "rollback": None}
    except SyncPlannerError as exc:
        rollback = rollback_file_actions(backup_manifest)
        return {
            "schema_version": "agent_sync_s2p_apply_result_v1",
            "status": "rolled_back" if rollback["valid"] else "rollback_failed",
            "error": exc.reason,
            "replaced": replaced,
            "rollback": rollback,
        }


def rollback_file_actions(backup_manifest: Mapping[str, Any]) -> dict[str, Any]:
    backup_root = Path(str(backup_manifest.get("backup_root") or ""))
    restored: list[dict[str, Any]] = []
    for row in backup_manifest.get("files") or []:
        if not isinstance(row, Mapping):
            continue
        rel = normalize_safe_relative_path(str(row.get("relative_path") or ""))
        target_text = str(row.get("target_absolute_path") or "")
        if target_text:
            target = Path(target_text)
        else:
            # Temp fixtures use backup_root sibling prod by embedding target paths in files when needed.
            target = Path(str(backup_manifest.get("target_root") or "")) / rel
        if row.get("exists_before"):
            backup = backup_root / rel
            if not backup.exists():
                return {"schema_version": "agent_sync_s2p_rollback_result_v1", "valid": False, "reason": "backup_missing", "restored": restored}
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target, follow_symlinks=False)
            restored.append({"relative_path": rel, "restore_action": "replace_from_backup", "sha256": file_sha256(target)})
        elif target.exists():
            target.unlink()
            restored.append({"relative_path": rel, "restore_action": "delete_created_file"})
    return {"schema_version": "agent_sync_s2p_rollback_result_v1", "valid": True, "restored": restored}


def fake_process_action(transaction_id: str, *, approved: bool) -> dict[str, Any]:
    if not approved:
        return {"schema_version": "agent_sync_s2p_process_action_result_v1", "transaction_id": transaction_id, "executed": False, "reason": "process_action_not_approved"}
    return {
        "schema_version": "agent_sync_s2p_process_action_result_v1",
        "transaction_id": transaction_id,
        "executed": True,
        "controller": "fake_process_controller",
        "old_pid_recorded": True,
        "new_pid_recorded": True,
        "raw_cmdline_persisted": False,
    }


def fake_live_gate(transaction_id: str, *, approved: bool, fail: bool = False) -> dict[str, Any]:
    if not approved:
        return {"schema_version": "agent_sync_s2p_live_gate_result_v1", "transaction_id": transaction_id, "executed": False, "reason": "live_validation_not_approved"}
    return {
        "schema_version": "agent_sync_s2p_live_gate_result_v1",
        "transaction_id": transaction_id,
        "executed": True,
        "health": {"status_code": 200, "body_hash": canonical_sha256({"ok": True})},
        "compute": {"status_code": 200 if not fail else 500, "body_hash": canonical_sha256({"ok": not fail})},
        "adapter": {"passed": not fail},
        "raw_body_persisted": False,
        "valid": not fail,
    }


def recover_s2p_journal(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    names = [str(event.get("event_type") or "") for event in events]
    if not names:
        action = "manual_intervention_required"
    elif "rollback_started" in names and "rollback_verified" not in names:
        action = "manual_intervention_required"
    elif "file_replaced" in names and "transaction_closed" not in names:
        action = "rollback_required"
    elif names[-1] in {"backup_file_verified", "temp_file_prepared", "offline_test_started"}:
        action = "resume_safe"
    else:
        action = "resume_safe"
    return {"schema_version": "agent_sync_s2p_recovery_v1", "event_count": len(names), "recommended_action": action, "events": names}


def historical_change_units() -> list[dict[str, Any]]:
    dispositions = (
        ["exact_byte_replay"] * 6
        + ["patch_replay"] * 21
        + ["contract_equivalent_fixture"] * 4
    )
    units: list[dict[str, Any]] = []
    for index, disposition in enumerate(dispositions, start=1):
        units.append(
            {
                "change_unit_id": f"historical_backfill_{index:02d}",
                "agent_id": "historical_multi_agent" if index > 6 else "risk_crash",
                "disposition": disposition,
                "evidence_level": disposition,
                "before_after_exact": disposition == "exact_byte_replay",
            }
        )
    return units


def run_temp_historical_replay(temp_root: Path) -> dict[str, Any]:
    _require_tmp_path(temp_root, "s2p_rehearsal_temp_root_required")
    if temp_root.exists():
        shutil.rmtree(temp_root)
    baseline = temp_root / "baseline" / "demo_agent"
    sandbox = temp_root / "sandbox" / "demo_agent"
    prod = temp_root / "prod" / "demo_agent"
    backup_root = temp_root / "artifact-store" / "backups" / "run_replay" / "txn_demo"
    for root in (baseline, sandbox, prod):
        root.mkdir(parents=True)
    (baseline / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
    (prod / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
    (sandbox / "service.py").write_text("VALUE = 2\n", encoding="utf-8")
    action = {
        "operation": "replace",
        "source_absolute_path": str(sandbox / "service.py"),
        "target_absolute_path": str(prod / "service.py"),
        "target_path": "service.py",
        "source_sha256": file_sha256(sandbox / "service.py"),
        "expected_target_before_sha256": file_sha256(prod / "service.py"),
    }
    backup = prepare_transaction_backups([action], backup_root)
    backup["target_root"] = str(prod)
    for row in backup["files"]:
        row["target_absolute_path"] = str(prod / row["relative_path"])
    apply_result = apply_file_actions([action], backup_manifest=backup)
    restart = fake_process_action("txn_demo", approved=True)
    smoke = fake_live_gate("txn_demo", approved=True)
    rollback = rollback_file_actions(backup)
    restored = file_sha256(prod / "service.py") == file_sha256(baseline / "service.py")
    smoke_fail = fake_live_gate("txn_demo_smoke_fail", approved=True, fail=True)
    recovery = recover_s2p_journal(
        [
            {"event_type": "backup_started"},
            {"event_type": "backup_file_verified"},
            {"event_type": "file_replaced"},
        ]
    )
    units = historical_change_units()
    counter = Counter(unit["disposition"] for unit in units)
    return {
        "schema_version": "agent_sync_s2p_historical_replay_v1",
        "temp_root": str(temp_root),
        "imported_change_unit_count": len(units),
        "disposition_counts": dict(counter),
        "exact_byte_replay_count": counter["exact_byte_replay"],
        "patch_replay_count": counter["patch_replay"],
        "contract_equivalent_fixture_count": counter["contract_equivalent_fixture"],
        "unavailable_count": counter["unavailable"],
        "backup_result": backup,
        "apply_result": apply_result,
        "fake_restart_result": restart,
        "fake_smoke_result": smoke,
        "smoke_failure_rollback_exercised": smoke_fail["valid"] is False,
        "rollback_result": rollback,
        "restoration_proof": {"restored_to_baseline": restored},
        "crash_recovery_result": recovery,
        "representative_shapes": [
            "risk_crash",
            "risk_compliance_review",
            "risk_financial_fraud",
            "macro_index_valuation",
            "value_valuation_wrapper",
            "market_composite_shared_root",
        ],
        "valid": restored and apply_result["status"] == "applied_and_verified" and rollback["valid"] and recovery["recommended_action"] == "rollback_required",
    }


def build_s2p_approval_request(plan: Mapping[str, Any]) -> dict[str, Any]:
    actions = iter_s2p_actions(plan)
    return {
        "schema_version": "agent_sync_s2p_approval_request_v1",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "status": "awaiting_machine_approval",
        "requested_agent_scopes": [str(agent.get("agent_id") or "") for agent in plan.get("agents") or [] if isinstance(agent, Mapping)],
        "requested_transaction_scopes": [str(txn.get("transaction_id") or "") for txn in plan.get("transactions") or [] if isinstance(txn, Mapping)],
        "requested_action_scopes": [str(action.get("action_id") or "") for action in actions],
        "action_count": len(actions),
        "backup_requested": bool(actions),
        "apply_requested": bool(actions),
        "offline_tests_requested": bool(actions),
        "process_action_requested": False,
        "live_requested": False,
        "rollback_requested": bool(actions),
        "owner_handoff_requested": False,
        "delete_requested": False,
        "publish_and_rebase_requested": False,
        "operator_action_required": bool(actions),
        "approval_id": "",
        "approved_at": "",
    }
