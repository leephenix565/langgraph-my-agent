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
BOOTSTRAP_ENV_V2_SCHEMA = "agent_sync_execution_environment_v2"
BOOTSTRAP_APPROVAL_SCHEMA = "agent_sync_artifact_store_bootstrap_approval_v1"
STORE_METADATA_SCHEMA = "agent_sync_artifact_store_metadata_v1"
BOOTSTRAP_TOOL_VERSION = "sync_ops_2a_r5_stable_environment_binding"
DIRECTORY_SCHEMA_VERSION = "agent_sync_artifact_store_directory_layout_v1"
OWNERSHIP_LEDGER_SCHEMA = "agent_sync_artifact_store_bootstrap_ownership_ledger_v1"
STORE_METADATA_FILENAME = "STORE_METADATA.json"
STORE_SUBDIRECTORIES = ("plans", "approvals", "runs", "locks", "baselines", "experiments", "backups", "indexes")
MINIMUM_BOOTSTRAP_FREE_BYTES = 64 * 1024 * 1024
ESTIMATED_BOOTSTRAP_REQUIRED_BYTES = 1024 * 1024
BOOTSTRAP_FREE_SPACE_MARGIN_BYTES = MINIMUM_BOOTSTRAP_FREE_BYTES - ESTIMATED_BOOTSTRAP_REQUIRED_BYTES


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _future(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(UTC)


def _mode_text(path: Path) -> str:
    try:
        return format(path.lstat().st_mode & 0o7777, "04o")
    except OSError:
        return ""


def _nearest_existing_ancestor(path: Path) -> Path:
    current = path
    while current.exists() and not current.is_dir() and current != current.parent:
        current = current.parent
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


def _access_basis(path: Path) -> dict[str, Any]:
    try:
        st = path.stat()
    except OSError:
        return {"access_basis": "none", "operator_can_create": False, "blockers": ["ancestor_missing"]}
    uid = os.geteuid()
    egid = os.getegid()
    groups = set(os.getgroups()) | {egid}
    mode = st.st_mode
    has_acl = _has_unmodeled_posix_acl(path)
    blockers: list[str] = []
    if has_acl:
        blockers.append("unmodeled_posix_acl")
    if st.st_uid == uid and mode & 0o300 == 0o300:
        basis = "owner"
    elif st.st_gid in groups and mode & 0o030 == 0o030:
        basis = "group"
    elif mode & 0o003 == 0o003:
        basis = "other"
    else:
        basis = "none"
        blockers.append("operator_lacks_create_permission")
    return {
        "access_basis": basis,
        "operator_can_create": basis != "none" and not has_acl,
        "relevant_gid": st.st_gid if basis == "group" else None,
        "operator_euid": uid,
        "operator_egid": egid,
        "operator_groups": sorted(groups),
        "ancestor_uid": st.st_uid,
        "ancestor_gid": st.st_gid,
        "ancestor_mode": format(st.st_mode & 0o7777, "04o"),
        "acl_modeled": not has_acl,
        "blockers": blockers,
    }


def _has_unmodeled_posix_acl(path: Path) -> bool:
    try:
        return "system.posix_acl_access" in os.listxattr(path)
    except OSError:
        return False


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


def _path_identity(path: Path) -> dict[str, Any]:
    try:
        st = path.lstat()
    except OSError:
        return {"exists": False}
    return {
        "exists": True,
        "mode": format(st.st_mode & 0o7777, "04o"),
        "uid": st.st_uid,
        "gid": st.st_gid,
        "device": st.st_dev,
        "inode": st.st_ino,
        "type": "symlink" if path.is_symlink() else ("directory" if path.is_dir() else ("file" if path.is_file() else "special")),
    }


def _bootstrap_run_id(plan: Mapping[str, Any]) -> str:
    return stable_id("bootstrap-run", str(plan.get("plan_id") or ""), str(plan.get("canonical_sha256") or ""))


def _directory_action_by_path(plan: Mapping[str, Any]) -> dict[str, str]:
    by_path: dict[str, str] = {}
    for action in plan.get("directory_actions") or []:
        if isinstance(action, Mapping):
            by_path[str(Path(str(action.get("path") or "")).resolve(strict=False))] = str(action.get("action_id") or "")
    return by_path


def _planned_directory_paths(plan: Mapping[str, Any]) -> set[str]:
    return set(_directory_action_by_path(plan))


def _metadata_path(plan: Mapping[str, Any]) -> Path:
    root = Path(str(plan.get("root") or ""))
    return root / STORE_METADATA_FILENAME


def bootstrap_plan_sha256(plan: Mapping[str, Any]) -> str:
    payload = json.loads(json.dumps(plan, ensure_ascii=False, allow_nan=False))
    if isinstance(payload, dict):
        payload.pop("canonical_sha256", None)
        payload.pop("environment_snapshot_sha256", None)
        payload.pop("environment_binding_sha256", None)
        payload.pop("environment_observation_reference", None)
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
    access = _access_basis(parent_action_parent)
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
        "operator_create_permission": access["operator_can_create"],
        "access_basis": access["access_basis"],
        "acl_modeled": access["acl_modeled"],
        "create_permission_basis": {
            "path": str(parent_action_parent),
            "mode": _mode_text(parent_action_parent),
            "uid": parent_action_parent.stat().st_uid,
            "gid": parent_action_parent.stat().st_gid,
            "access_basis": access["access_basis"],
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
        "blockers": access["blockers"],
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
        "environment_contract_version": BOOTSTRAP_ENV_V2_SCHEMA,
        "environment_binding_sha256": "",
        "execution_constraints": {
            "estimated_required_bytes": ESTIMATED_BOOTSTRAP_REQUIRED_BYTES,
            "safety_margin_bytes": BOOTSTRAP_FREE_SPACE_MARGIN_BYTES,
            "minimum_free_bytes": MINIMUM_BOOTSTRAP_FREE_BYTES,
            "required_access": ["write", "execute"],
            "no_unmodeled_acl": True,
            "plan_not_expired": True,
            "path_state_drift_forbidden": True,
        },
        "environment_observation_reference": {},
        "execution_status": "bootstrap_ready" if not audit["blockers"] else "blocked_permission",
        "preconditions": [
            "schema_valid",
            "canonical_hash_valid",
            "exact_machine_approval_required",
            "environment_binding_match_required",
            "execution_constraints_pass_required",
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
    plan["environment_binding_sha256"] = environment["environment_binding_sha256"]
    plan["environment_snapshot_sha256"] = environment["environment_binding_sha256"]
    plan["environment_observation_reference"] = {
        "schema_version": "agent_sync_environment_observation_reference_v1",
        "observations_sha256": environment["observations_sha256"],
        "diagnostic_only": True,
    }
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
        inode = st.st_ino
        realpath = str(nearest.resolve(strict=True))
    except OSError:
        mode = ""
        uid = None
        gid = None
        device = "unavailable"
        inode = None
        realpath = ""
    access = _access_basis(nearest) if nearest.exists() else {"access_basis": "none", "operator_can_create": False, "blockers": ["ancestor_missing"]}
    constraints = dict(plan.get("execution_constraints") or {})
    current_free = _free_bytes(nearest) if nearest.exists() else None
    approval_binding: dict[str, Any] = {
        "schema_version": "agent_sync_execution_environment_approval_binding_v2",
        "tool_version": BOOTSTRAP_TOOL_VERSION,
        "operation": "artifact_store_bootstrap",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": bootstrap_plan_sha256(plan),
        "root": str(root),
        "parent": str(root.parent),
        "nearest_existing_ancestor": str(nearest),
        "nearest_existing_ancestor_realpath": realpath,
        "nearest_existing_ancestor_device": device,
        "nearest_existing_ancestor_inode": inode,
        "nearest_existing_ancestor_uid": uid,
        "nearest_existing_ancestor_mode": mode,
        "operator_euid": os.geteuid(),
        "operator_primary_gid": os.getegid(),
        "access_basis": access.get("access_basis"),
        "relevant_gid": access.get("relevant_gid"),
        "directory_action_states": action_states,
        "directory_action_contracts": [
            {
                "action_id": str(action.get("action_id") or ""),
                "path": str(action.get("path") or ""),
                "operation": str(action.get("operation") or ""),
                "expected_state": str(action.get("expected_state") or ""),
                "mode": str(action.get("mode") or ""),
                "forbid_symlink": bool(action.get("forbid_symlink")),
                "forbid_special_file": bool(action.get("forbid_special_file")),
            }
            for action in plan.get("directory_actions") or []
            if isinstance(action, Mapping)
        ],
        "metadata_action": {
            "action_id": str((plan.get("metadata_action") or {}).get("action_id") or ""),
            "path": str((plan.get("metadata_action") or {}).get("path") or ""),
            "mode": str((plan.get("metadata_action") or {}).get("mode") or ""),
            "operation": str((plan.get("metadata_action") or {}).get("operation") or ""),
        },
        "target_root_expected_state": "missing",
    }
    if access.get("access_basis") == "group":
        operator_group_values = access.get("operator_groups")
        operator_groups = set(operator_group_values) if isinstance(operator_group_values, list) else set()
        approval_binding["operator_relevant_group_member"] = access.get("relevant_gid") in operator_groups
    observations = {
        "schema_version": "agent_sync_execution_environment_observations_v2",
        "generated_at": _utc_now(),
        "current_free_bytes": current_free,
        "nearest_existing_ancestor_gid": gid,
        "operator_gid": os.getegid(),
        "operator_groups": os.getgroups(),
        "access_basis_diagnostics": access,
        "free_space_floor": constraints.get("minimum_free_bytes", MINIMUM_BOOTSTRAP_FREE_BYTES),
    }
    binding_sha = canonical_sha256(approval_binding)
    observations_sha = canonical_sha256(observations)
    snapshot: dict[str, Any] = {
        "schema_version": BOOTSTRAP_ENV_V2_SCHEMA,
        "tool_version": BOOTSTRAP_TOOL_VERSION,
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": bootstrap_plan_sha256(plan),
        "approval_binding": approval_binding,
        "execution_constraints": constraints,
        "observations": observations,
        "environment_binding_sha256": binding_sha,
        "observations_sha256": observations_sha,
        # Compatibility fields retained for older CLI/report code. This value
        # is the stable binding hash, not a full observation snapshot hash.
        "environment_snapshot_sha256": binding_sha,
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
        "free_bytes": current_free,
        "operator_uid": os.geteuid(),
        "operator_gid": os.getegid(),
        "operator_groups": os.getgroups(),
        "generated_at": str(plan.get("created_at") or ""),
    }
    return snapshot


def validate_bootstrap_environment_contract(plan: Mapping[str, Any], environment: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    diagnostics: list[str] = []
    if plan.get("environment_contract_version") != BOOTSTRAP_ENV_V2_SCHEMA:
        blockers.append("legacy_volatile_environment_snapshot_contract")
    expected_binding = str(plan.get("environment_binding_sha256") or plan.get("environment_snapshot_sha256") or "")
    actual_binding = str(environment.get("environment_binding_sha256") or environment.get("environment_snapshot_sha256") or "")
    if expected_binding != actual_binding:
        blockers.append("environment_binding_sha256_mismatch")
    constraints_raw = environment.get("execution_constraints")
    constraints: Mapping[str, Any] = constraints_raw if isinstance(constraints_raw, Mapping) else {}
    observations_raw = environment.get("observations")
    observations: Mapping[str, Any] = observations_raw if isinstance(observations_raw, Mapping) else {}
    minimum_free = int(constraints.get("minimum_free_bytes") or MINIMUM_BOOTSTRAP_FREE_BYTES)
    current_free = observations.get("current_free_bytes")
    if current_free is None or int(current_free) < minimum_free:
        blockers.append("insufficient_free_space")
    access_diag_raw = observations.get("access_basis_diagnostics")
    access_diag: Mapping[str, Any] = access_diag_raw if isinstance(access_diag_raw, Mapping) else {}
    if access_diag.get("operator_can_create") is not True:
        blockers.extend(str(item) for item in access_diag.get("blockers") or ["operator_lacks_create_permission"])
    if access_diag.get("acl_modeled") is False:
        blockers.append("unmodeled_posix_acl")
    try:
        if _parse_utc(str(plan.get("expires_at") or "")) <= datetime.now(UTC):
            blockers.append("plan_expired")
    except ValueError:
        blockers.append("invalid_plan_expiry")
    if environment.get("observations_sha256") != canonical_sha256(observations):
        diagnostics.append("observations_sha256_changed_or_missing")
    return {
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "diagnostics": sorted(set(diagnostics)),
        "environment_binding_sha256": actual_binding,
        "minimum_free_bytes": minimum_free,
        "current_free_bytes": current_free,
        "exit_code": 0 if not blockers else (5 if "environment_binding_sha256_mismatch" in blockers else 3),
    }


def validate_bootstrap_plan(plan: Mapping[str, Any], *, check_environment: bool = True) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate_by_schema_version(plan)
    except SyncPlannerError as exc:
        blockers.append(f"schema_{exc.reason}")
    if str(plan.get("canonical_sha256") or "") != bootstrap_plan_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    if plan.get("environment_contract_version") != BOOTSTRAP_ENV_V2_SCHEMA:
        blockers.append("legacy_volatile_environment_snapshot_contract")
    if not str(plan.get("environment_binding_sha256") or ""):
        blockers.append("environment_binding_sha256_missing")
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
        contract = validate_bootstrap_environment_contract(plan, environment)
        blockers.extend(contract["blockers"])
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
        "environment_binding_sha256": str(environment.get("environment_binding_sha256") or ""),
        "environment_snapshot_sha256": str(environment.get("environment_binding_sha256") or ""),
        "root": str(plan.get("root") or ""),
        "expires_at": str(plan.get("expires_at") or ""),
        "bootstrap_requested": True,
        "requested_action_ids": [str(action.get("action_id") or "") for action in plan.get("directory_actions") or [] if isinstance(action, Mapping)]
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
        "type_note": "approval request only; not a machine approval",
    }


def build_temp_bootstrap_approval(plan: Mapping[str, Any], environment: Mapping[str, Any], *, rollback: bool = False) -> dict[str, Any]:
    return {
        "schema_version": BOOTSTRAP_APPROVAL_SCHEMA,
        "approval_id": stable_id("approval", str(plan.get("plan_id") or ""), str(plan.get("canonical_sha256") or ""), "bootstrap"),
        "status": "approved",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "environment_binding_sha256": str(environment.get("environment_binding_sha256") or ""),
        "environment_snapshot_sha256": str(environment.get("environment_binding_sha256") or ""),
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


def validate_bootstrap_approval(
    approval: Mapping[str, Any],
    plan: Mapping[str, Any],
    environment: Mapping[str, Any],
    *,
    require_rollback: bool = False,
    check_environment_contract: bool = True,
) -> dict[str, Any]:
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
    expected_binding_sha = str(plan.get("environment_binding_sha256") or environment.get("environment_binding_sha256") or "")
    if not str(approval.get("environment_binding_sha256") or ""):
        blockers.append("approval_environment_binding_sha256_missing")
    elif str(approval.get("environment_binding_sha256") or "") != expected_binding_sha:
        blockers.append("approval_environment_binding_sha256_mismatch")
    if check_environment_contract:
        contract = validate_bootstrap_environment_contract(plan, environment)
        blockers.extend(contract["blockers"])
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


def _build_ownership_ledger(
    root: Path,
    plan: Mapping[str, Any],
    created_dirs: list[str],
    *,
    metadata_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    action_by_path = _directory_action_by_path(plan)
    created_paths: list[dict[str, Any]] = []
    for path_text in created_dirs:
        path = Path(path_text)
        created_paths.append(
            {
                "path": str(path),
                "type": "directory",
                "action_id": action_by_path.get(str(path.resolve(strict=False)), ""),
                "created_by_this_run": True,
                "preexisting_before_run": False,
                "post_create_identity": _path_identity(path),
            }
        )
    metadata_path = root / STORE_METADATA_FILENAME
    created_paths.append(
        {
            "path": str(metadata_path),
            "type": "file",
            "action_id": str((plan.get("metadata_action") or {}).get("action_id") or ""),
            "created_by_this_run": True,
            "preexisting_before_run": False,
            "post_create_identity": dict(metadata_identity or _path_identity(metadata_path)),
        }
    )
    return {
        "schema_version": OWNERSHIP_LEDGER_SCHEMA,
        "run_id": _bootstrap_run_id(plan),
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "created_paths": created_paths,
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
        "bootstrap_environment_binding_sha256": str(plan.get("environment_binding_sha256") or ""),
        "bootstrap_environment_contract_version": str(plan.get("environment_contract_version") or ""),
        "bootstrap_run_id": _bootstrap_run_id(plan),
        "bootstrap_approval_id": str(approval.get("approval_id") or ""),
        "mode": _mode_text(root),
        "uid": root_stat.st_uid,
        "gid": root_stat.st_gid,
        "tool_version": BOOTSTRAP_TOOL_VERSION,
        "directory_schema_version": DIRECTORY_SCHEMA_VERSION,
        "created_directories": created_dirs,
        "no_secrets_declaration": True,
    }
    metadata_path = root / STORE_METADATA_FILENAME
    tmp = metadata_path.with_name(f".{metadata_path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    os.chmod(tmp, 0o600)
    payload["ownership_ledger"] = _build_ownership_ledger(root, plan, created_dirs, metadata_identity=_path_identity(tmp))
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with tmp.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(tmp, metadata_path)
    _fsync_dir(metadata_path.parent)
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
        if not str(metadata.get("bootstrap_environment_binding_sha256") or ""):
            blockers.append("store_metadata_environment_binding_missing")
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
    environment_contract = validate_bootstrap_environment_contract(plan, environment)
    if not environment_contract["valid"]:
        reason = "bootstrap_environment_binding_mismatch" if environment_contract["exit_code"] == 5 else "bootstrap_environment_constraint_failed"
        raise SyncPlannerError(reason, exit_code=environment_contract["exit_code"], details={"blockers": environment_contract["blockers"]})
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


def _read_metadata_for_rollback(metadata_path: Path) -> dict[str, Any] | None:
    if not metadata_path.exists():
        return None
    try:
        payload = read_json(metadata_path)
    except (OSError, json.JSONDecodeError):
        return {"_invalid": True}
    return payload if isinstance(payload, dict) else {"_invalid": True}


def _relative_descendants(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir() or root.is_symlink():
        return []
    return sorted(root.rglob("*"), key=lambda path: path.as_posix())


def preflight_bootstrap_rollback(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Preflight bootstrap rollback without mutating the filesystem."""
    root = Path(str(plan.get("root") or ""))
    metadata_path = _metadata_path(plan)
    planned_dirs = _planned_directory_paths(plan)
    result: dict[str, Any] = {
        "schema_version": "agent_sync_artifact_store_bootstrap_rollback_preflight_v1",
        "root": str(root),
        "safe_to_remove": False,
        "owned_paths": [],
        "preexisting_paths": [],
        "nonempty_paths": [],
        "unknown_paths": [],
        "foreign_paths": [],
        "metadata_state": "",
        "delete_candidates": [],
        "blocked": [],
        "mutations_performed": 0,
    }
    if not root.exists():
        result.update({"status": "noop_already_rolled_back", "metadata_state": "root_missing"})
        return result
    if root.is_symlink() or not root.is_dir():
        result["blocked"].append(f"root_not_directory:{root}")
        result.update({"status": "noop_not_safe_to_remove", "metadata_state": "root_invalid"})
        return result

    metadata = _read_metadata_for_rollback(metadata_path)
    if metadata is None:
        # Partial bootstrap before metadata write: only exact, empty plan dirs may be removed.
        existing = {path for path in planned_dirs if Path(path).exists()}
        existing.update(str(path.resolve(strict=False)) for path in _relative_descendants(root))
        unknown = sorted(existing - planned_dirs)
        for planned in sorted(existing & planned_dirs):
            path = Path(planned)
            if path.is_dir():
                for child in path.iterdir():
                    child_resolved = str(child.resolve(strict=False))
                    if child_resolved not in planned_dirs and child_resolved not in existing:
                        unknown.append(child_resolved)
        nonempty = [
            str(Path(path))
            for path in existing & planned_dirs
            if Path(path).is_dir()
            and any(str(child.resolve(strict=False)) not in planned_dirs for child in Path(path).iterdir())
        ]
        result["metadata_state"] = "missing_partial_bootstrap"
        result["unknown_paths"] = unknown
        result["nonempty_paths"] = nonempty
        result["blocked"] = [f"unknown_path:{path}" for path in unknown] + [f"not_empty:{path}" for path in nonempty]
        if not result["blocked"]:
            candidates = sorted(existing & planned_dirs, key=lambda item: len(Path(item).parts), reverse=True)
            result.update(
                {
                    "safe_to_remove": True,
                    "status": "safe_to_remove",
                    "owned_paths": candidates,
                    "delete_candidates": [{"path": item, "type": "directory"} for item in candidates],
                }
            )
        else:
            result["status"] = "noop_not_safe_to_remove"
        return result

    if metadata.get("_invalid"):
        result["blocked"].append("metadata_invalid")
        result.update({"status": "noop_not_safe_to_remove", "metadata_state": "invalid"})
        return result
    if metadata.get("bootstrap_plan_id") != plan.get("plan_id") or metadata.get("bootstrap_plan_sha256") != plan.get("canonical_sha256"):
        result["blocked"].append("foreign_metadata_plan")
        result["foreign_paths"].append(str(metadata_path))
    if metadata.get("bootstrap_run_id") != _bootstrap_run_id(plan):
        result["blocked"].append("foreign_metadata_run")
        result["foreign_paths"].append(str(metadata_path))
    ledger = metadata.get("ownership_ledger")
    if not isinstance(ledger, Mapping):
        result["blocked"].append("ownership_ledger_missing")
    elif ledger.get("run_id") != _bootstrap_run_id(plan):
        result["blocked"].append("ownership_ledger_foreign_run")
    elif ledger.get("plan_id") != plan.get("plan_id") or ledger.get("plan_sha256") != plan.get("canonical_sha256"):
        result["blocked"].append("ownership_ledger_plan_mismatch")

    ledger_candidates: list[dict[str, Any]] = []
    if isinstance(ledger, Mapping):
        for item in ledger.get("created_paths") or []:
            if not isinstance(item, Mapping):
                result["blocked"].append("ownership_ledger_entry_invalid")
                continue
            path = Path(str(item.get("path") or ""))
            if item.get("created_by_this_run") is True:
                ledger_candidates.append({"path": str(path), "type": str(item.get("type") or "")})
                result["owned_paths"].append(str(path))
            else:
                result["preexisting_paths"].append(str(path))

    allowed_root_children = {STORE_METADATA_FILENAME, *STORE_SUBDIRECTORIES}
    for child in root.iterdir():
        if child.name not in allowed_root_children:
            result["unknown_paths"].append(str(child))
            result["blocked"].append(f"unknown_path:{child}")
    for name in STORE_SUBDIRECTORIES:
        path = root / name
        if path.exists() and (path.is_symlink() or not path.is_dir()):
            result["foreign_paths"].append(str(path))
            result["blocked"].append(f"standard_path_not_directory:{path}")
        elif path.exists() and any(path.iterdir()):
            result["nonempty_paths"].append(str(path))
            result["blocked"].append(f"not_empty:{path}")

    if result["blocked"]:
        result.update({"status": "noop_not_safe_to_remove", "metadata_state": "owned_metadata_with_blockers"})
        result["safe_to_remove"] = False
        result["delete_candidates"] = []
        return result

    ordered = sorted(
        ledger_candidates,
        key=lambda item: (0 if item["type"] == "file" else 1, -len(Path(str(item["path"])).parts)),
    )
    result.update(
        {
            "safe_to_remove": True,
            "status": "safe_to_remove",
            "metadata_state": "owned_metadata",
            "delete_candidates": ordered,
        }
    )
    return result


def rollback_bootstrap(plan: Mapping[str, Any], approval: Mapping[str, Any], *, execute: bool) -> dict[str, Any]:
    if not execute:
        raise SyncPlannerError("execute_required", exit_code=2)
    environment = build_bootstrap_environment_snapshot(plan)
    approval_result = validate_bootstrap_approval(approval, plan, environment, require_rollback=True, check_environment_contract=False)
    if not approval_result["valid"]:
        raise SyncPlannerError("bootstrap_rollback_approval_invalid", exit_code=4, details={"blockers": approval_result["blockers"]})
    root = Path(str(plan.get("root") or ""))
    preflight = preflight_bootstrap_rollback(plan)
    if preflight["status"] == "noop_already_rolled_back":
        return {
            "schema_version": "agent_sync_artifact_store_bootstrap_rollback_result_v1",
            "root": str(root),
            "preflight": preflight,
            "removed_files": [],
            "removed_directories": [],
            "mutation_count": 0,
            "blocked": [],
            "status": "noop_already_rolled_back",
            "exit_code": 0,
        }
    if not preflight["safe_to_remove"]:
        return {
            "schema_version": "agent_sync_artifact_store_bootstrap_rollback_result_v1",
            "root": str(root),
            "preflight": preflight,
            "removed_files": [],
            "removed_directories": [],
            "mutation_count": 0,
            "blocked": preflight["blocked"],
            "status": "noop_not_safe_to_remove",
            "exit_code": 7,
        }
    removed_files: list[str] = []
    removed: list[str] = []
    blocked: list[str] = []
    mutation_count = 0
    for candidate in preflight["delete_candidates"]:
        path = Path(str(candidate.get("path") or ""))
        kind = str(candidate.get("type") or "")
        try:
            if not path.exists():
                continue
            if path.is_symlink():
                blocked.append(f"symlink_replaced:{path}")
                break
            if kind == "file":
                if not path.is_file():
                    blocked.append(f"not_file:{path}")
                    break
                path.unlink()
                _fsync_dir(path.parent)
                removed_files.append(str(path))
                mutation_count += 1
            elif kind == "directory":
                if not path.is_dir():
                    blocked.append(f"not_directory:{path}")
                    break
                if any(path.iterdir()):
                    blocked.append(f"not_empty:{path}")
                    break
                path.rmdir()
                if path.parent.exists():
                    _fsync_dir(path.parent)
                removed.append(str(path))
                mutation_count += 1
            else:
                blocked.append(f"unknown_candidate_type:{path}")
                break
        except OSError as exc:
            blocked.append(f"rollback_exception:{path}:{exc.__class__.__name__}")
            break
    return {
        "schema_version": "agent_sync_artifact_store_bootstrap_rollback_result_v1",
        "root": str(root),
        "preflight": preflight,
        "removed_files": removed_files,
        "removed_directories": removed,
        "mutation_count": mutation_count,
        "blocked": blocked,
        "status": "rolled_back" if not blocked else "rollback_failed",
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
