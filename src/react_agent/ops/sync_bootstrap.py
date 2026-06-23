# ruff: noqa: D101, D103
"""Durable artifact-store bootstrap contracts and temp-safe executor."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from react_agent.ops.sync_artifacts import DEFAULT_ARTIFACT_STORE_ROOT
from react_agent.ops.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    file_sha256,
    read_json,
    stable_id,
    validate_by_schema_version,
)

BOOTSTRAP_PLAN_SCHEMA = "agent_sync_artifact_store_bootstrap_plan_v1"
BOOTSTRAP_ENV_SCHEMA = "agent_sync_artifact_store_bootstrap_environment_v1"
BOOTSTRAP_APPROVAL_SCHEMA = "agent_sync_artifact_store_bootstrap_approval_v1"
STORE_METADATA_SCHEMA = "agent_sync_artifact_store_metadata_v1"
BOOTSTRAP_TOOL_VERSION = "sync_ops_2a_r3_artifact_store_bootstrap"
DIRECTORY_SCHEMA_VERSION = "agent_sync_artifact_store_directory_layout_v1"
STORE_METADATA_FILENAME = "STORE_METADATA.json"
STORE_SUBDIRECTORIES = ("plans", "approvals", "runs", "locks", "baselines", "experiments", "backups", "indexes")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _future(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mode_text(path: Path) -> str:
    try:
        return format(path.lstat().st_mode & 0o7777, "04o")
    except OSError:
        return ""


def _nearest_existing_ancestor(path: Path) -> Path:
    current = path
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def _device_id(path: Path) -> str:
    try:
        return str(path.stat().st_dev)
    except OSError:
        return "unavailable"


def _free_bytes(path: Path) -> int | None:
    try:
        free = int(shutil.disk_usage(path).free)
        mib = 1024 * 1024
        return (free // mib) * mib
    except OSError:
        return None


def _operator_can_create(path: Path) -> bool:
    try:
        st = path.stat()
    except OSError:
        return False
    uid = os.geteuid()
    gids = {os.getegid(), *os.getgroups()}
    mode = st.st_mode
    if st.st_uid == uid:
        return bool(mode & 0o300 == 0o300)
    if st.st_gid in gids:
        return bool(mode & 0o030 == 0o030)
    return bool(mode & 0o003 == 0o003)


def _safe_absolute_path(path: Path, root: Path) -> None:
    if not path.is_absolute():
        raise SyncPlannerError("bootstrap_path_not_absolute", exit_code=2)
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise SyncPlannerError("bootstrap_path_escape", exit_code=2) from exc


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write_json(path: Path, payload: Mapping[str, Any], *, mode: int = 0o600) -> None:
    path.parent.mkdir(mode=0o700, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.chmod(tmp, mode)
    with tmp.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def bootstrap_plan_sha256(plan: Mapping[str, Any]) -> str:
    payload = json.loads(json.dumps(plan, ensure_ascii=False, allow_nan=False))
    if isinstance(payload, dict):
        payload.pop("canonical_sha256", None)
        payload.pop("environment_snapshot_sha256", None)
    return canonical_sha256(payload, exclude_hash_field=False)


def _exact_directory_actions(root: Path, *, parent_mode: str, root_mode: str, internal_mode: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    parent = root.parent
    if not parent.exists():
        actions.append(
            {
                "action_id": stable_id("mkdir", str(parent)),
                "path": str(parent),
                "operation": "mkdir_exact",
                "expected_state": "missing",
                "mode": parent_mode,
                "owner_strategy": "current_operator",
                "group_strategy": "normal_filesystem_inheritance",
                "allow_existing_matching_directory": True,
                "forbid_symlink": True,
                "forbid_special_file": True,
            }
        )
    actions.append(
        {
            "action_id": stable_id("mkdir", str(root)),
            "path": str(root),
            "operation": "mkdir_exact",
            "expected_state": "missing",
            "mode": root_mode,
            "owner_strategy": "current_operator",
            "group_strategy": "normal_filesystem_inheritance",
            "allow_existing_matching_directory": True,
            "forbid_symlink": True,
            "forbid_special_file": True,
        }
    )
    for name in STORE_SUBDIRECTORIES:
        child = root / name
        actions.append(
            {
                "action_id": stable_id("mkdir", str(child)),
                "path": str(child),
                "operation": "mkdir_exact",
                "expected_state": "missing",
                "mode": internal_mode,
                "owner_strategy": "current_operator",
                "group_strategy": "normal_filesystem_inheritance",
                "allow_existing_matching_directory": True,
                "forbid_symlink": True,
                "forbid_special_file": True,
            }
        )
    return actions


def build_artifact_store_permission_audit(root: Path = DEFAULT_ARTIFACT_STORE_ROOT) -> dict[str, Any]:
    nearest = _nearest_existing_ancestor(root)
    root_parent = root.parent
    parent_action_parent = _nearest_existing_ancestor(root_parent)
    nearest_stat = nearest.stat()
    return {
        "schema_version": "agent_sync_artifact_store_permission_audit_v1",
        "root": str(root),
        "parent": str(root_parent),
        "root_exists": root.exists(),
        "parent_exists": root_parent.exists(),
        "nearest_existing_ancestor": str(nearest),
        "nearest_existing_ancestor_realpath": str(nearest.resolve(strict=True)),
        "nearest_existing_ancestor_mode": _mode_text(nearest),
        "nearest_existing_ancestor_uid": nearest_stat.st_uid,
        "nearest_existing_ancestor_gid": nearest_stat.st_gid,
        "nearest_existing_ancestor_device": str(nearest_stat.st_dev),
        "operator_uid": os.geteuid(),
        "operator_gid": os.getegid(),
        "operator_groups": os.getgroups(),
        "operator_create_permission": _operator_can_create(parent_action_parent),
        "create_permission_basis": {
            "path": str(parent_action_parent),
            "mode": _mode_text(parent_action_parent),
            "uid": parent_action_parent.stat().st_uid,
            "gid": parent_action_parent.stat().st_gid,
        },
        "free_bytes": _free_bytes(nearest),
        "recommended_modes": {
            "parent": "0750",
            "root": "0700",
            "internal": "0700",
            "metadata": "0600",
        },
        "owner_strategy": "current_operator",
        "group_strategy": "normal_filesystem_inheritance",
        "chown_chgrp": "forbidden",
        "blockers": [] if _operator_can_create(parent_action_parent) else ["operator_lacks_create_permission"],
    }


def build_bootstrap_plan(root: Path = DEFAULT_ARTIFACT_STORE_ROOT) -> dict[str, Any]:
    root = root.resolve(strict=False)
    audit = build_artifact_store_permission_audit(root)
    plan_id = stable_id("bootstrap", str(root), _utc_now())
    directory_actions = _exact_directory_actions(root, parent_mode="0750", root_mode="0700", internal_mode="0700")
    plan: dict[str, Any] = {
        "schema_version": BOOTSTRAP_PLAN_SCHEMA,
        "tool_version": BOOTSTRAP_TOOL_VERSION,
        "plan_id": plan_id,
        "created_at": _utc_now(),
        "expires_at": _future(),
        "root": str(root),
        "parent": str(root.parent),
        "nearest_existing_ancestor": audit["nearest_existing_ancestor"],
        "environment_snapshot_sha256": "",
        "execution_status": "bootstrap_ready" if not audit["blockers"] else "blocked_permission",
        "preconditions": [
            "schema_valid",
            "canonical_hash_valid",
            "exact_machine_approval_required",
            "environment_snapshot_match_required",
            "nearest_existing_ancestor_unchanged",
            "exact_directory_actions_only",
            "no_chown_chgrp",
            "no_setuid_setgid",
        ],
        "directory_actions": directory_actions,
        "metadata_action": {
            "action_id": stable_id("metadata", str(root / STORE_METADATA_FILENAME)),
            "path": str(root / STORE_METADATA_FILENAME),
            "operation": "atomic_write_json",
            "mode": "0600",
            "schema_version": STORE_METADATA_SCHEMA,
            "temp_file_same_directory": True,
            "fsync_required": True,
        },
        "serialization": {
            "strategy": "atomic_mkdir_root",
            "root_action_id": stable_id("mkdir", str(root)),
            "stale_auto_delete": False,
            "normal_completion_releases_serialization_by_metadata_marker": True,
        },
        "verification": {
            "checks": [
                "root_realpath_matches",
                "directory_modes_match_plan",
                "metadata_exists",
                "metadata_mode_0600",
                "store_subdirectories_exist",
                "no_symlink_target",
                "no_special_file",
            ]
        },
        "rollback": {
            "policy": "remove_only_empty_paths_created_by_this_run",
            "delete_order": [str(action["path"]) for action in reversed(directory_actions)],
            "forbidden": ["non_empty_directory", "preexisting_directory", "other_run_artifact", "chown_chgrp"],
        },
        "blockers": audit["blockers"],
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = bootstrap_plan_sha256(plan)
    environment = build_bootstrap_environment_snapshot(plan)
    plan["environment_snapshot_sha256"] = environment["environment_snapshot_sha256"]
    plan["canonical_sha256"] = bootstrap_plan_sha256(plan)
    return plan


def build_bootstrap_environment_snapshot(plan: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(str(plan.get("root") or ""))
    nearest = Path(str(plan.get("nearest_existing_ancestor") or _nearest_existing_ancestor(root)))
    action_states = []
    for action in plan.get("directory_actions") or []:
        if not isinstance(action, Mapping):
            continue
        path = Path(str(action.get("path") or ""))
        action_states.append(
            {
                "action_id": str(action.get("action_id") or ""),
                "path": str(path),
                "expected_state": str(action.get("expected_state") or ""),
                "actual_exists": path.exists(),
                "actual_type": "directory" if path.is_dir() else ("symlink" if path.is_symlink() else ("file" if path.exists() else "missing")),
            }
        )
    try:
        st = nearest.stat()
        mode = _mode_text(nearest)
        uid = st.st_uid
        gid = st.st_gid
        device = str(st.st_dev)
        realpath = str(nearest.resolve(strict=True))
    except OSError:
        mode = ""
        uid = None
        gid = None
        device = "unavailable"
        realpath = ""
    snapshot: dict[str, Any] = {
        "schema_version": BOOTSTRAP_ENV_SCHEMA,
        "tool_version": BOOTSTRAP_TOOL_VERSION,
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": bootstrap_plan_sha256(plan),
        "root": str(root),
        "root_expected_state": "missing" if not root.exists() else "present",
        "root_exists": root.exists(),
        "parent": str(root.parent),
        "parent_exists": root.parent.exists(),
        "nearest_existing_ancestor": str(nearest),
        "nearest_existing_ancestor_realpath": realpath,
        "nearest_existing_ancestor_mode": mode,
        "nearest_existing_ancestor_uid": uid,
        "nearest_existing_ancestor_gid": gid,
        "nearest_existing_ancestor_device": device,
        "directory_action_states": action_states,
        "free_bytes": _free_bytes(nearest) if nearest.exists() else None,
        "operator_uid": os.geteuid(),
        "operator_gid": os.getegid(),
        "operator_groups": os.getgroups(),
        "generated_at": str(plan.get("created_at") or ""),
    }
    snapshot["environment_snapshot_sha256"] = canonical_sha256(snapshot)
    return snapshot


def validate_bootstrap_plan(plan: Mapping[str, Any], *, check_environment: bool = True) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate_by_schema_version(plan)
    except SyncPlannerError as exc:
        blockers.append(f"schema_{exc.reason}")
    if str(plan.get("canonical_sha256") or "") != bootstrap_plan_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    root = Path(str(plan.get("root") or ""))
    if not root.is_absolute():
        blockers.append("root_not_absolute")
    seen: set[str] = set()
    for action in plan.get("directory_actions") or []:
        if not isinstance(action, Mapping):
            blockers.append("directory_action_not_object")
            continue
        if action.get("operation") != "mkdir_exact":
            blockers.append("directory_action_not_mkdir_exact")
        path = Path(str(action.get("path") or ""))
        if str(path) in seen:
            blockers.append("duplicate_directory_action")
        seen.add(str(path))
        try:
            _safe_absolute_path(path, root.parent)
        except SyncPlannerError as exc:
            blockers.append(exc.reason)
        if "*" in str(path):
            blockers.append("directory_action_wildcard")
        if str(action.get("owner_strategy") or "") != "current_operator":
            blockers.append("owner_strategy_not_exact")
        if str(action.get("group_strategy") or "") != "normal_filesystem_inheritance":
            blockers.append("group_strategy_not_exact")
        mode = str(action.get("mode") or "")
        if mode not in {"2775", "0750", "0700"}:
            blockers.append("directory_mode_not_exact")
        if int(mode or "0", 8) & 0o6000:
            blockers.append("setuid_setgid_forbidden")
    metadata_action = plan.get("metadata_action") or {}
    if str(metadata_action.get("mode") or "") != "0600":
        blockers.append("metadata_mode_not_0600")
    if check_environment:
        environment = build_bootstrap_environment_snapshot(plan)
        if str(plan.get("environment_snapshot_sha256") or "") != str(environment.get("environment_snapshot_sha256") or ""):
            blockers.append("environment_snapshot_sha256_mismatch")
    return {
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "canonical_sha256": bootstrap_plan_sha256(plan),
        "stored_canonical_sha256": str(plan.get("canonical_sha256") or ""),
        "exit_code": 0 if not blockers else 3,
    }


def build_bootstrap_approval_request(plan: Mapping[str, Any], environment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "agent_sync_artifact_store_bootstrap_approval_request_v1",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "environment_snapshot_sha256": str(environment.get("environment_snapshot_sha256") or ""),
        "root": str(plan.get("root") or ""),
        "expires_at": str(plan.get("expires_at") or ""),
        "bootstrap_requested": True,
        "approved_action_ids": [str(action.get("action_id") or "") for action in plan.get("directory_actions") or [] if isinstance(action, Mapping)]
        + [str((plan.get("metadata_action") or {}).get("action_id") or "")],
        "requested_permissions": {
            "bootstrap": True,
            "mkdir_exact": True,
            "write_metadata": True,
            "chown_chgrp": False,
            "setuid_setgid": False,
        },
        "operator_action_required": True,
        "status": "awaiting_machine_approval",
        "approval_id": "",
        "approved_at": "",
    }


def build_temp_bootstrap_approval(plan: Mapping[str, Any], environment: Mapping[str, Any], *, rollback: bool = False) -> dict[str, Any]:
    return {
        "schema_version": BOOTSTRAP_APPROVAL_SCHEMA,
        "approval_id": stable_id("approval", str(plan.get("plan_id") or ""), str(plan.get("canonical_sha256") or ""), "bootstrap"),
        "status": "approved",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "environment_snapshot_sha256": str(environment.get("environment_snapshot_sha256") or ""),
        "approved_at": _utc_now(),
        "expires_at": _future(),
        "execution_phase": "SYNC-OPS-2B0",
        "bootstrap_approved": True,
        "rollback_approved": rollback,
        "approved_action_ids": [str(action.get("action_id") or "") for action in plan.get("directory_actions") or [] if isinstance(action, Mapping)]
        + [str((plan.get("metadata_action") or {}).get("action_id") or "")],
        "operator_reference": "temp-bootstrap-test",
        "notes": "temporary approval fixture for repo-external tests",
    }


def validate_bootstrap_approval(approval: Mapping[str, Any], plan: Mapping[str, Any], environment: Mapping[str, Any], *, require_rollback: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate_by_schema_version(approval)
    except SyncPlannerError as exc:
        blockers.append(f"schema_{exc.reason}")
    if approval.get("status") != "approved":
        blockers.append("approval_status_not_approved")
    if str(approval.get("plan_id") or "") != str(plan.get("plan_id") or ""):
        blockers.append("approval_plan_id_mismatch")
    if str(approval.get("plan_sha256") or "") != str(plan.get("canonical_sha256") or ""):
        blockers.append("approval_plan_sha256_mismatch")
    expected_environment_sha = str(plan.get("environment_snapshot_sha256") or environment.get("environment_snapshot_sha256") or "")
    if str(approval.get("environment_snapshot_sha256") or "") != expected_environment_sha:
        blockers.append("approval_environment_snapshot_sha256_mismatch")
    if approval.get("bootstrap_approved") is not True:
        blockers.append("bootstrap_permission_missing")
    if require_rollback and approval.get("rollback_approved") is not True:
        blockers.append("rollback_permission_missing")
    if not str(approval.get("operator_reference") or ""):
        blockers.append("approval_operator_reference_missing")
    requested = {str(action.get("action_id") or "") for action in plan.get("directory_actions") or [] if isinstance(action, Mapping)}
    requested.add(str((plan.get("metadata_action") or {}).get("action_id") or ""))
    actual = {str(item) for item in approval.get("approved_action_ids") or []}
    if actual != requested:
        blockers.append("approved_action_ids_not_exact")
    if any(keyword in json.dumps(approval, ensure_ascii=False).lower() for keyword in ("password", "api_key", "secret=", "token=")):
        blockers.append("approval_contains_sensitive_keyword")
    return {
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "exit_code": 0 if not blockers else 4,
    }


def _write_metadata(root: Path, plan: Mapping[str, Any], approval: Mapping[str, Any], created_dirs: list[str]) -> dict[str, Any]:
    root_stat = root.stat()
    payload = {
        "schema_version": STORE_METADATA_SCHEMA,
        "store_id": stable_id("store", str(root)),
        "status": "bootstrapped",
        "created_at": _utc_now(),
        "root": str(root),
        "root_realpath": str(root.resolve(strict=True)),
        "bootstrap_plan_id": str(plan.get("plan_id") or ""),
        "bootstrap_plan_sha256": str(plan.get("canonical_sha256") or ""),
        "bootstrap_run_id": stable_id("bootstrap-run", str(plan.get("plan_id") or ""), str(plan.get("canonical_sha256") or "")),
        "bootstrap_approval_id": str(approval.get("approval_id") or ""),
        "mode": _mode_text(root),
        "uid": root_stat.st_uid,
        "gid": root_stat.st_gid,
        "tool_version": BOOTSTRAP_TOOL_VERSION,
        "directory_schema_version": DIRECTORY_SCHEMA_VERSION,
        "created_directories": created_dirs,
        "no_secrets_declaration": True,
    }
    _atomic_write_json(root / STORE_METADATA_FILENAME, payload, mode=0o600)
    return payload


def verify_artifact_store(root: Path = DEFAULT_ARTIFACT_STORE_ROOT) -> dict[str, Any]:
    metadata_path = root / STORE_METADATA_FILENAME
    blockers: list[str] = []
    metadata: dict[str, Any] = {}
    if not root.exists():
        blockers.append("artifact_store_root_missing")
    elif root.is_symlink() or not root.is_dir():
        blockers.append("artifact_store_root_not_directory")
    if not metadata_path.exists():
        blockers.append("store_metadata_missing")
    else:
        raw = read_json(metadata_path)
        if isinstance(raw, dict):
            metadata = raw
        else:
            blockers.append("store_metadata_not_object")
    for name in STORE_SUBDIRECTORIES:
        path = root / name
        if not path.exists():
            blockers.append(f"store_subdirectory_missing:{name}")
        elif path.is_symlink() or not path.is_dir():
            blockers.append(f"store_subdirectory_invalid:{name}")
    if metadata:
        if metadata.get("schema_version") != STORE_METADATA_SCHEMA:
            blockers.append("store_metadata_schema_mismatch")
        if metadata.get("status") != "bootstrapped":
            blockers.append("store_metadata_status_not_bootstrapped")
        if str(metadata.get("root") or "") != str(root):
            blockers.append("store_metadata_root_mismatch")
    return {
        "schema_version": "agent_sync_artifact_store_verify_v1",
        "root": str(root),
        "metadata_path": str(metadata_path),
        "metadata_exists": metadata_path.exists(),
        "metadata_sha256": file_sha256(metadata_path) if metadata_path.exists() and metadata_path.is_file() else "",
        "bootstrapped": not blockers,
        "blockers": sorted(set(blockers)),
        "metadata": metadata,
        "exit_code": 0 if not blockers else 3,
    }


def bootstrap_artifact_store(plan: Mapping[str, Any], approval: Mapping[str, Any], *, execute: bool) -> dict[str, Any]:
    if not execute:
        raise SyncPlannerError("execute_required", exit_code=2)
    validation = validate_bootstrap_plan(plan, check_environment=False)
    if not validation["valid"]:
        raise SyncPlannerError("bootstrap_plan_invalid", exit_code=3, details={"blockers": validation["blockers"]})
    root = Path(str(plan.get("root") or ""))
    existing = verify_artifact_store(root)
    if existing["bootstrapped"]:
        return {"status": "noop_success", "root": str(root), "idempotent": True, "verify": existing}
    environment = build_bootstrap_environment_snapshot(plan)
    approval_result = validate_bootstrap_approval(approval, plan, environment)
    if not approval_result["valid"]:
        raise SyncPlannerError("bootstrap_approval_invalid", exit_code=4, details={"blockers": approval_result["blockers"]})
    created_dirs: list[str] = []
    for action in plan.get("directory_actions") or []:
        if not isinstance(action, Mapping):
            continue
        path = Path(str(action.get("path") or ""))
        mode = int(str(action.get("mode") or "0"), 8)
        if path.exists():
            if path.is_symlink() or not path.is_dir():
                raise SyncPlannerError("bootstrap_existing_path_not_directory", exit_code=7, details={"path": str(path)})
            continue
        if path.parent.exists() and path.parent.is_symlink():
            raise SyncPlannerError("bootstrap_parent_symlink", exit_code=7, details={"path": str(path.parent)})
        path.mkdir(mode=mode)
        os.chmod(path, mode)
        _fsync_dir(path.parent)
        created_dirs.append(str(path))
    metadata = _write_metadata(root, plan, approval, created_dirs)
    verify = verify_artifact_store(root)
    if not verify["bootstrapped"]:
        raise SyncPlannerError("bootstrap_verify_failed", exit_code=7, details={"blockers": verify["blockers"]})
    return {
        "schema_version": "agent_sync_artifact_store_bootstrap_result_v1",
        "status": "bootstrapped",
        "root": str(root),
        "created_directories": created_dirs,
        "metadata": metadata,
        "verify": verify,
    }


def rollback_bootstrap(plan: Mapping[str, Any], approval: Mapping[str, Any], *, execute: bool) -> dict[str, Any]:
    if not execute:
        raise SyncPlannerError("execute_required", exit_code=2)
    environment = build_bootstrap_environment_snapshot(plan)
    approval_result = validate_bootstrap_approval(approval, plan, environment, require_rollback=True)
    if not approval_result["valid"]:
        raise SyncPlannerError("bootstrap_rollback_approval_invalid", exit_code=4, details={"blockers": approval_result["blockers"]})
    root = Path(str(plan.get("root") or ""))
    metadata_path = root / STORE_METADATA_FILENAME
    blocked: list[str] = []
    if metadata_path.exists():
        metadata_path.unlink()
    removed: list[str] = []
    for action in reversed(plan.get("directory_actions") or []):
        if not isinstance(action, Mapping):
            continue
        path = Path(str(action.get("path") or ""))
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_dir():
            blocked.append(f"not_directory:{path}")
            continue
        try:
            path.rmdir()
            removed.append(str(path))
        except OSError:
            blocked.append(f"not_empty:{path}")
    return {
        "schema_version": "agent_sync_artifact_store_bootstrap_rollback_result_v1",
        "root": str(root),
        "removed_directories": removed,
        "blocked": blocked,
        "status": "rolled_back" if not blocked else "noop_not_safe_to_remove",
        "exit_code": 0 if not blocked else 7,
    }


def recover_bootstrap(plan: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(str(plan.get("root") or ""))
    verify = verify_artifact_store(root)
    if verify["bootstrapped"]:
        recommended = "noop_already_bootstrapped"
    elif root.exists() and root.is_dir() and any(root.iterdir()):
        recommended = "manual_intervention_required"
    elif root.exists():
        recommended = "rollback_empty_partial"
    else:
        recommended = "bootstrap_required"
    return {
        "schema_version": "agent_sync_artifact_store_bootstrap_recovery_v1",
        "root": str(root),
        "verify": verify,
        "recommended_action": recommended,
        "exit_code": 0 if recommended != "manual_intervention_required" else 7,
    }
