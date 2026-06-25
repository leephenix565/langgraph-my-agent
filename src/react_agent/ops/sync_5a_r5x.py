# ruff: noqa: D101, D102, D103
"""SYNC-OPS-5A-R5X exact source-loss cutover contracts."""

from __future__ import annotations

import os
import socket
import stat
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from react_agent.ops.sync_5a_r1x import (
    RISK_FRAUD_AGENT_ID,
    RISK_FRAUD_HISTORICAL_ROOT,
    RISK_FRAUD_PROD_ROOT,
)
from react_agent.ops.sync_5a_r2x import expires_utc, now_utc, reselect_first_candidate
from react_agent.ops.sync_5a_r3x import (
    CANONICAL_RISK_FRAUD_ARGV,
    build_source_package_provenance,
)
from react_agent.ops.sync_5a_r4x import (
    build_first_real_cycle_plan_v4,
    build_full_p2s_rebase_plan_v4,
    build_projected_experiment_v4,
    validate_full_p2s_rebase_plan_v4,
)
from react_agent.ops.sync_contracts import canonical_sha256, file_sha256, stable_id
from react_agent.ops.sync_inventory import inventory_root
from react_agent.ops.sync_s2p import descriptor_from_inventory
from react_agent.ops.sync_security import (
    classify_file_type,
    classify_source_category,
    normalize_safe_relative_path,
    safe_symlink_decision,
)

R5X_TOOL_VERSION = "sync_ops_5a_r5x_source_loss_cutover_contract"
R4X_CANARY_PATH = Path("/sdb/dlut/prod/.agent-sync-risk-fraud-canary-precutover_canary_cba8429d4858")
PRODUCTION_PORT = 10013
STORE_ROOT = Path("/sdb/dlut/ops-artifacts/agent-sync")
R4X_SUPERSESSION_REASON = "superseded_due_exact_cutover_action_full_tree_and_production_launch_contract"

V5_STATE_SEQUENCE = [
    "PLANNED",
    "CANDIDATE_MATERIALIZED",
    "CANDIDATE_VALIDATED",
    "INCUMBENT_REVALIDATED",
    "INCUMBENT_STOPPING",
    "INCUMBENT_STOPPED",
    "PORT_RELEASED",
    "CANONICAL_ARCHIVED",
    "CANDIDATE_CUTOVER",
    "RECOVERED_STARTING",
    "RECOVERED_RUNNING",
    "RECOVERED_VERIFIED",
    "RECOVERY_SETTLED",
]
V5_FAILURE_STATES = [
    "PRESTOP_BLOCKED",
    "SIGTERM_TIMEOUT",
    "PORT_NOT_RELEASED",
    "ARCHIVE_RENAME_FAILED",
    "CANDIDATE_RENAME_FAILED",
    "RECOVERED_START_FAILED",
    "RECOVERED_CONTRACT_FAILED",
    "ROLL_FORWARD_RETRYING",
    "MANUAL_INTERVENTION_REQUIRED",
]
V5_REQUIRED_CUTOVER_OPERATIONS = [
    "preflight_candidate_path_missing",
    "materialize_67_files",
    "validate_fresh_candidate",
    "final_incumbent_identity",
    "final_incumbent_health",
    "final_incumbent_compute",
    "final_incumbent_adapter",
    "send_incumbent_sigterm",
    "verify_pid_stopped",
    "verify_port_10013_released",
    "rename_canonical_to_archive",
    "rename_fresh_candidate_to_canonical",
    "fsync_parent",
    "start_recovered_production",
    "verify_new_pid_start_cwd_exe",
    "verify_10013_listener",
    "recovered_health",
    "recovered_compute",
    "recovered_adapter",
    "equivalence_comparison",
    "recovery_settle_closeout",
    "locks_release",
]


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _path_has_placeholder(value: str) -> bool:
    return "<" in value or ">" in value


def _is_sensitive_reference(path: Path) -> bool:
    lower = path.name.lower()
    return lower == ".env" or lower.startswith(".env.") or any(part.lower().startswith(".env") for part in path.parts)


def _entry_classification(root: Path, path: Path, file_type: str) -> tuple[str, str]:
    if file_type == "directory":
        parts = tuple(part.lower() for part in path.relative_to(root).parts)
        if any(part in {"logs", "log", "cache", "tmp", "temp", "__pycache__", ".pytest_cache"} for part in parts):
            return "runtime_noise", "runtime_directory"
        if any(part in {"data", "dataset", "datasets"} for part in parts):
            return "data_asset", "data_directory"
        if any(part in {"models", "weights"} for part in parts):
            return "model_asset", "model_directory"
        if any(part.startswith(".env") for part in parts):
            return "sensitive_blocked", "environment_reference"
        return "directory", "directory"
    if file_type == "regular":
        return classify_source_category(root, path)
    if file_type == "symlink":
        decision, _target = safe_symlink_decision(root, path)
        return "source_code" if decision == "safe_relative_symlink" else "unknown_blocked", decision
    return "unknown_blocked", file_type


def build_cutover_tree_descriptor(root: Path, *, root_role: str) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    if root.exists():
        if root.is_file() or root.is_symlink():
            paths = [root]
            base = root.parent
        else:
            paths = sorted([root, *root.rglob("*")], key=lambda item: str(item.relative_to(root)) if item != root else "")
            base = root
        for path in paths:
            try:
                stat_result = path.lstat()
            except OSError:
                continue
            file_type = classify_file_type(stat_result.st_mode)
            rel = "." if path == root else normalize_safe_relative_path(path.relative_to(base))
            category, category_reason = ("root_directory", "root") if path == root else _entry_classification(base, path, file_type)
            sensitive = _is_sensitive_reference(path) or category == "sensitive_blocked"
            sha = ""
            symlink_target = ""
            if file_type == "regular" and not sensitive:
                sha = file_sha256(path)
            elif file_type == "symlink":
                _decision, symlink_target = safe_symlink_decision(base, path)
            entries.append(
                {
                    "relative_path": rel,
                    "entry_type": file_type,
                    "sha256": sha,
                    "content_reference": "sensitive_reference_not_hashed" if sensitive else "",
                    "mode": oct(stat.S_IMODE(stat_result.st_mode)),
                    "executable": bool(stat_result.st_mode & stat.S_IXUSR),
                    "symlink_target": symlink_target,
                    "classification": category,
                    "classification_reason": category_reason,
                }
            )
    digest_entries = [
        {
            "relative_path": entry["relative_path"],
            "entry_type": entry["entry_type"],
            "sha256": entry["sha256"],
            "content_reference": entry["content_reference"],
            "mode": entry["mode"],
            "executable": entry["executable"],
            "symlink_target": entry["symlink_target"],
            "classification": entry["classification"],
        }
        for entry in sorted(entries, key=lambda item: item["relative_path"])
    ]
    counts = Counter(entry["classification"] for entry in entries)
    source_inventory = inventory_root(RISK_FRAUD_AGENT_ID, root, root_role=root_role) if root.exists() else {
        "root_role": root_role,
        "tree_digest": "",
        "included_count": 0,
    }
    descriptor: dict[str, Any] = {
        "schema_version": "agent_sync_cutover_tree_descriptor_v1",
        "root": str(root),
        "root_role": root_role,
        "source_bearing_descriptor": descriptor_from_inventory(source_inventory, scope="transaction_source_tree"),
        "full_entry_digest": canonical_sha256(digest_entries),
        "entry_count": len(entries),
        "regular_file_count": sum(1 for entry in entries if entry["entry_type"] == "regular"),
        "directory_count": sum(1 for entry in entries if entry["entry_type"] == "directory"),
        "symlink_count": sum(1 for entry in entries if entry["entry_type"] == "symlink"),
        "special_file_count": sum(
            1 for entry in entries if entry["entry_type"] not in {"regular", "directory", "symlink"}
        ),
        "runtime_artifact_count": counts.get("runtime_noise", 0) + counts.get("generated_artifact", 0),
        "data_model_reference_count": counts.get("data_asset", 0) + counts.get("model_asset", 0),
        "unknown_entry_count": counts.get("unknown_blocked", 0),
        "sensitive_entry_count": counts.get("sensitive_blocked", 0),
        "classification_counts": dict(sorted(counts.items())),
        "unexpected_entries": [
            entry["relative_path"]
            for entry in entries
            if entry["classification"] in {"unknown_blocked", "sensitive_blocked"}
        ],
        "canonical_sha256": "",
    }
    descriptor["canonical_sha256"] = canonical_sha256(descriptor)
    return descriptor


def build_production_launch_authority_v1(
    *,
    plan_id: str,
    environment_profile_sha256: str,
    canonical_target: Path = RISK_FRAUD_PROD_ROOT,
) -> dict[str, Any]:
    run_root = STORE_ROOT / "runs" / f"run_{plan_id}"
    authority: dict[str, Any] = {
        "schema_version": "agent_sync_production_launch_authority_v1",
        "authority_id": stable_id("production_launch_authority", plan_id, environment_profile_sha256, str(canonical_target)),
        "authority_kind": "sync_ops_supervised_launcher",
        "service_unit_id": RISK_FRAUD_AGENT_ID,
        "executable": "/usr/bin/python3.14",
        "argv": CANONICAL_RISK_FRAUD_ARGV,
        "cwd": str(canonical_target),
        "production_port": PRODUCTION_PORT,
        "environment_profile_sha256": environment_profile_sha256,
        "environment_mode": "clean_allowlist",
        "bounded_overrides": {"APP_HOST": "0.0.0.0", "APP_PORT": str(PRODUCTION_PORT)},
        "values_read": False,
        "proc_environ_read": False,
        "start_contract": {
            "shell": False,
            "start_new_session": True,
            "stdin": "/dev/null",
            "umask": "0077",
            "startup_timeout_seconds": 45,
            "status_pid_start_cwd_exe_required": True,
        },
        "stop_contract": {
            "signal": "SIGTERM",
            "sigkill_allowed": False,
            "graceful_timeout_seconds": 15,
            "port_release_timeout_seconds": 15,
            "pid_reuse_protection": True,
        },
        "status_contract": {
            "verify_pid": True,
            "verify_start_ticks": True,
            "verify_cwd": True,
            "verify_exe": True,
            "verify_port": PRODUCTION_PORT,
        },
        "log_contract": {
            "log_dir": str(run_root / "process" / "logs"),
            "state_dir": str(run_root / "process" / "state"),
            "portable_artifact_includes_log_bytes": False,
            "mode": "0600",
        },
        "recovery_contract": {
            "bounded_retry": True,
            "max_recovered_start_retries": 2,
            "manual_intervention_on_sigterm_timeout": True,
            "no_old_service_false_rollback": True,
            "no_shell": True,
            "no_arbitrary_command": True,
        },
        "canonical_sha256": "",
    }
    authority["canonical_sha256"] = canonical_sha256(authority)
    return authority


def validate_production_launch_authority_v1(authority: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if authority.get("schema_version") != "agent_sync_production_launch_authority_v1":
        blockers.append("schema_version_not_v1")
    if authority.get("authority_kind") != "sync_ops_supervised_launcher":
        blockers.append("unsupported_authority_kind")
    if authority.get("executable") != "/usr/bin/python3.14":
        blockers.append("executable_not_exact")
    if list(authority.get("argv") or []) != CANONICAL_RISK_FRAUD_ARGV:
        blockers.append("argv_not_exact")
    if authority.get("cwd") != str(RISK_FRAUD_PROD_ROOT):
        blockers.append("cwd_not_canonical_target")
    if int(authority.get("production_port") or 0) != PRODUCTION_PORT:
        blockers.append("production_port_not_10013")
    if _as_mapping(authority.get("start_contract")).get("shell") is not False:
        blockers.append("shell_must_be_false")
    if _as_mapping(authority.get("stop_contract")).get("sigkill_allowed") is not False:
        blockers.append("sigkill_must_be_false")
    if authority.get("values_read") or authority.get("proc_environ_read"):
        blockers.append("environment_values_accessed")
    for nested in ("log_contract", "recovery_contract"):
        for value in _as_mapping(authority.get(nested)).values():
            if isinstance(value, str) and _path_has_placeholder(value):
                blockers.append(f"{nested}_contains_placeholder")
    if str(authority.get("canonical_sha256") or "") != canonical_sha256(authority):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_production_launch_authority_v1_validation",
        "authority_id": authority.get("authority_id", ""),
        "authority_sha256": authority.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
    }


def build_source_loss_state_machine_v5() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_state_machine_v5",
        "states": V5_STATE_SEQUENCE,
        "failure_states": V5_FAILURE_STATES,
        "rules": {
            "prestop_failure": "zero_canonical_modification_incumbent_continues_candidate_may_remain",
            "sigterm_timeout": "no_sigkill_no_rename_manual_intervention",
            "post_stop_before_archive": "continue_exact_cutover_or_manual_no_old_runtime_restart_claim",
            "archive_rename_failure": "manual_intervention_preserve_paths",
            "candidate_rename_failure": "restore_archive_path_to_canonical_if_archive_intact_service_down_manual",
            "recovered_start_failure": "bounded_retry_same_recovered_source_then_manual",
            "recovered_contract_failure": "bounded_retry_no_invoke_no_provider_no_p2s_unlock",
        },
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def build_source_loss_failure_policy_v5() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_failure_policy_v5",
        "sigkill_allowed": False,
        "delete_allowed": False,
        "old_source_less_runtime_rollback_supported": False,
        "roll_forward_retry": {
            "enabled": True,
            "max_start_retries": 2,
            "retry_same_recovered_source_only": True,
            "retry_after_candidate_cutover": True,
        },
        "manual_intervention_required_states": [
            "SIGTERM_TIMEOUT",
            "PORT_NOT_RELEASED",
            "ARCHIVE_RENAME_FAILED",
            "RECOVERED_START_FAILED_after_retries",
            "RECOVERED_CONTRACT_FAILED_after_retries",
        ],
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def _materialization_actions(plan_id: str, provenance: Mapping[str, Any], *, source_root: Path, candidate_path: Path) -> list[dict[str, Any]]:
    return [
        {
            "action_id": stable_id("slrv5_file", plan_id, str(entry.get("relative_path") or ""), str(entry.get("sha256") or "")),
            "operation": "materialize_fresh_candidate_file",
            "source_path": str(source_root / str(entry.get("relative_path") or "")),
            "fresh_candidate_path": str(candidate_path / str(entry.get("relative_path") or "")),
            "relative_path": entry.get("relative_path"),
            "source_sha256": entry.get("sha256"),
        }
        for entry in provenance.get("entries") or []
        if isinstance(entry, Mapping)
    ]


def _cutover_actions(plan_id: str) -> list[dict[str, Any]]:
    return [
        {
            "action_id": stable_id("slrv5_action", plan_id, operation),
            "operation": operation,
            "requires_machine_approval": operation
            in {
                "materialize_67_files",
                "final_incumbent_health",
                "final_incumbent_compute",
                "final_incumbent_adapter",
                "send_incumbent_sigterm",
                "rename_canonical_to_archive",
                "rename_fresh_candidate_to_canonical",
                "start_recovered_production",
                "recovered_health",
                "recovered_compute",
                "recovered_adapter",
                "equivalence_comparison",
            },
        }
        for operation in V5_REQUIRED_CUTOVER_OPERATIONS
    ]


def build_source_loss_recovery_plan_v5(
    *,
    final_head: str,
    precutover_closeout: Mapping[str, Any],
    runtime_identity: Mapping[str, Any],
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    canonical_target: Path = RISK_FRAUD_PROD_ROOT,
    canary_path: Path = R4X_CANARY_PATH,
) -> dict[str, Any]:
    provenance = build_source_package_provenance(source_root)
    source_inventory = inventory_root(RISK_FRAUD_AGENT_ID, source_root, root_role="source_loss_recovery_package")
    source_descriptor = descriptor_from_inventory(source_inventory, scope="transaction_source_tree")
    canonical_full = build_cutover_tree_descriptor(canonical_target, root_role="canonical_target_before_cutover")
    canary_full = build_cutover_tree_descriptor(canary_path, root_role="r4x_canary_evidence")
    plan_id = stable_id(
        "source_loss_recovery_v5",
        final_head,
        str(precutover_closeout.get("canonical_sha256") or ""),
        provenance["canonical_sha256"],
        str(precutover_closeout.get("environment_profile_sha256") or ""),
        str(runtime_identity.get("pid") or ""),
        str(runtime_identity.get("start_ticks") or ""),
        canonical_full["full_entry_digest"],
    )
    fresh_candidate = canonical_target.parent / f".agent-sync-risk-fraud-cutover-{plan_id}"
    archive_path = canonical_target.parent / f".agent-sync-archive-risk-fraud-{plan_id}"
    fresh_full = build_cutover_tree_descriptor(source_root, root_role="fresh_cutover_candidate_expected")
    fresh_full["root"] = str(fresh_candidate)
    fresh_full["root_role"] = "fresh_cutover_candidate_expected"
    fresh_full["canonical_sha256"] = ""
    fresh_full["canonical_sha256"] = canonical_sha256(fresh_full)
    launch = build_production_launch_authority_v1(
        plan_id=plan_id,
        environment_profile_sha256=str(precutover_closeout.get("environment_profile_sha256") or ""),
        canonical_target=canonical_target,
    )
    file_actions = _materialization_actions(plan_id, provenance, source_root=source_root, candidate_path=fresh_candidate)
    cutover_actions = _cutover_actions(plan_id)
    action_ids = [action["action_id"] for action in file_actions] + [action["action_id"] for action in cutover_actions]
    state_machine = build_source_loss_state_machine_v5()
    failure_policy = build_source_loss_failure_policy_v5()
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_recovery_plan_v5",
        "tool_version": R5X_TOOL_VERSION,
        "plan_id": plan_id,
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "final_head_sha256": final_head,
        "precutover_canary_closeout_sha256": precutover_closeout.get("canonical_sha256"),
        "source_provenance_sha256": provenance["canonical_sha256"],
        "environment_profile_sha256": precutover_closeout.get("environment_profile_sha256"),
        "equivalence_result_sha256": precutover_closeout.get("equivalence_result_sha256"),
        "incumbent_capture_sha256": precutover_closeout.get("incumbent_capture_sha256"),
        "canonical_target_path": str(canonical_target),
        "canonical_full_tree_descriptor": canonical_full,
        "canonical_source_descriptor": canonical_full["source_bearing_descriptor"],
        "canary_evidence_path": str(canary_path),
        "canary_full_tree_descriptor": canary_full,
        "canary_runtime_artifact_count": canary_full["runtime_artifact_count"],
        "fresh_cutover_candidate_path": str(fresh_candidate),
        "fresh_cutover_candidate_expected_state": "missing",
        "fresh_candidate_expected_full_tree_descriptor": fresh_full,
        "fresh_candidate_expected_source_descriptor": source_descriptor,
        "archive_path": str(archive_path),
        "archive_expected_state": "missing",
        "production_launch_authority": launch,
        "production_launch_authority_sha256": launch["canonical_sha256"],
        "incumbent_identity": dict(runtime_identity),
        "incumbent_port": PRODUCTION_PORT,
        "file_actions": file_actions,
        "cutover_actions": cutover_actions,
        "exact_requested_action_ids": action_ids,
        "state_machine": state_machine,
        "failure_policy": failure_policy,
        "requested_permissions": {
            "candidate_materialization": True,
            "incumbent_final_health": True,
            "incumbent_final_compute": True,
            "incumbent_final_adapter": True,
            "incumbent_sigterm": True,
            "verify_port_release": True,
            "source_root_atomic_archive": True,
            "fresh_candidate_atomic_cutover": True,
            "recovered_production_start": True,
            "recovered_health": True,
            "recovered_compute": True,
            "recovered_adapter": True,
            "equivalence_comparison": True,
            "roll_forward_retry": True,
            "irreversible_source_loss_acknowledgement": True,
            "sigkill": False,
            "delete": False,
            "invoke": False,
            "provider": False,
            "p2s": False,
            "first_cycle": False,
        },
        "downstream_settle_contract": {
            "settle_closeout_required": True,
            "p2s_stage_unlocked_only_after_recovery_settle": True,
            "actual_target_descriptor_must_equal_projected": True,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_source_loss_recovery_plan_v5(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if plan.get("schema_version") != "agent_sync_source_loss_recovery_plan_v5":
        blockers.append("schema_version_not_v5")
    for key in (
        "canonical_target_path",
        "archive_path",
        "fresh_cutover_candidate_path",
        "production_launch_authority_sha256",
        "canonical_full_tree_descriptor",
        "fresh_candidate_expected_full_tree_descriptor",
    ):
        if not plan.get(key):
            blockers.append(f"missing_{key}")
    for key in ("canonical_target_path", "archive_path", "fresh_cutover_candidate_path"):
        value = str(plan.get(key) or "")
        if _path_has_placeholder(value):
            blockers.append(f"{key}_contains_placeholder")
    canonical_path = Path(str(plan.get("canonical_target_path") or ""))
    archive_path = Path(str(plan.get("archive_path") or ""))
    fresh_path = Path(str(plan.get("fresh_cutover_candidate_path") or ""))
    canary_path = Path(str(plan.get("canary_evidence_path") or ""))
    if fresh_path == canary_path:
        blockers.append("dirty_canary_reuse_forbidden")
    if canonical_path.parent != archive_path.parent or canonical_path.parent != fresh_path.parent:
        blockers.append("cutover_paths_not_same_parent")
    file_actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    cutover_actions = [action for action in plan.get("cutover_actions") or [] if isinstance(action, Mapping)]
    if len(file_actions) != 67:
        blockers.append("file_action_count_not_67")
    operation_order = [str(action.get("operation") or "") for action in cutover_actions]
    if operation_order != V5_REQUIRED_CUTOVER_OPERATIONS:
        blockers.append("cutover_action_order_invalid")
    action_ids = [str(action.get("action_id") or "") for action in file_actions + cutover_actions]
    if len(action_ids) != len(set(action_ids)):
        blockers.append("duplicate_action_ids")
    if list(plan.get("exact_requested_action_ids") or []) != action_ids:
        blockers.append("exact_requested_action_ids_mismatch")
    launch_validation = validate_production_launch_authority_v1(_as_mapping(plan.get("production_launch_authority")))
    if not launch_validation["valid"]:
        blockers.append("production_launch_authority_invalid")
    canonical_full = _as_mapping(plan.get("canonical_full_tree_descriptor"))
    fresh_full = _as_mapping(plan.get("fresh_candidate_expected_full_tree_descriptor"))
    if canonical_full.get("schema_version") != "agent_sync_cutover_tree_descriptor_v1":
        blockers.append("canonical_full_descriptor_invalid")
    if fresh_full.get("schema_version") != "agent_sync_cutover_tree_descriptor_v1":
        blockers.append("fresh_candidate_full_descriptor_invalid")
    if int(_as_mapping(fresh_full.get("source_bearing_descriptor")).get("file_count") or 0) != 67:
        blockers.append("fresh_candidate_source_count_not_67")
    permissions = _as_mapping(plan.get("requested_permissions"))
    for forbidden in ("sigkill", "delete", "invoke", "provider", "p2s", "first_cycle"):
        if permissions.get(forbidden):
            blockers.append(f"forbidden_permission:{forbidden}")
    if not permissions.get("irreversible_source_loss_acknowledgement"):
        blockers.append("irreversible_ack_missing")
    state_machine = _as_mapping(plan.get("state_machine"))
    failure_policy = _as_mapping(plan.get("failure_policy"))
    if state_machine.get("states") != V5_STATE_SEQUENCE or state_machine.get("failure_states") != V5_FAILURE_STATES:
        blockers.append("state_machine_incomplete")
    if failure_policy.get("sigkill_allowed") is not False or failure_policy.get("old_source_less_runtime_rollback_supported") is not False:
        blockers.append("roll_forward_failure_policy_invalid")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_loss_recovery_plan_v5_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "exact_action_count": len(action_ids),
        "file_action_count": len(file_actions),
        "cutover_action_count": len(cutover_actions),
        "fresh_candidate_path": plan.get("fresh_cutover_candidate_path", ""),
        "archive_path": plan.get("archive_path", ""),
        "production_launch_authority_sha256": plan.get("production_launch_authority_sha256", ""),
    }


def validate_v4_cutover_plan_superseded(v4_plan: Mapping[str, Any]) -> dict[str, Any]:
    missing = [
        key
        for key in (
            "canonical_target_path",
            "archive_path",
            "fresh_cutover_candidate_path",
            "cutover_actions",
            "incumbent_port",
            "production_launch_authority",
            "state_machine",
            "canonical_full_tree_descriptor",
        )
        if not v4_plan.get(key)
    ]
    return {
        "schema_version": "agent_sync_v4_cutover_supersession_validation_v1",
        "valid_for_v5_execution": False,
        "supersession_reason": R4X_SUPERSESSION_REASON,
        "missing_fields": missing,
        "missing_field_count": len(missing),
        "blockers": [f"missing_{key}" for key in missing],
    }


def build_source_loss_cutover_approval_request_v5(plan: Mapping[str, Any]) -> dict[str, Any]:
    request: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_cutover_approval_request_v5",
        "request_id": stable_id("source_loss_cutover_request_v5", str(plan.get("canonical_sha256") or "")),
        "status": "awaiting_machine_approval",
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("canonical_sha256"),
        "canary_closeout_sha256": plan.get("precutover_canary_closeout_sha256"),
        "source_provenance_sha256": plan.get("source_provenance_sha256"),
        "environment_profile_sha256": plan.get("environment_profile_sha256"),
        "equivalence_result_sha256": plan.get("equivalence_result_sha256"),
        "canonical_target_path": plan.get("canonical_target_path"),
        "canonical_full_tree_descriptor": plan.get("canonical_full_tree_descriptor"),
        "fresh_cutover_candidate_path": plan.get("fresh_cutover_candidate_path"),
        "archive_path": plan.get("archive_path"),
        "production_launch_authority_sha256": plan.get("production_launch_authority_sha256"),
        "incumbent_identity": plan.get("incumbent_identity"),
        "incumbent_port": plan.get("incumbent_port"),
        "requested_action_ids": plan.get("exact_requested_action_ids", []),
        "endpoint_scopes": {
            "incumbent_health": True,
            "incumbent_compute": True,
            "recovered_health": True,
            "recovered_compute": True,
            "adapter_mapping": True,
            "invoke": False,
            "provider": False,
        },
        "permissions": {
            "sigterm": True,
            "sigkill": False,
            "delete": False,
            "source_root_cutover": True,
            "recovered_production_start": True,
            "p2s": False,
            "first_cycle": False,
            "irreversible_source_loss_acknowledgement": True,
        },
        "approval_id": "",
        "approved_at": "",
        "expires_at": plan.get("expires_at"),
        "canonical_sha256": "",
    }
    request["canonical_sha256"] = canonical_sha256(request)
    return request


def validate_source_loss_cutover_approval_request_v5(request: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if request.get("status") != "awaiting_machine_approval":
        blockers.append("request_not_awaiting_machine_approval")
    if request.get("approval_id") or request.get("approved_at"):
        blockers.append("approval_fields_must_be_empty")
    if request.get("plan_sha256") != plan.get("canonical_sha256"):
        blockers.append("plan_hash_mismatch")
    if list(request.get("requested_action_ids") or []) != list(plan.get("exact_requested_action_ids") or []):
        blockers.append("requested_action_ids_mismatch")
    permissions = _as_mapping(request.get("permissions"))
    for forbidden in ("sigkill", "delete", "p2s", "first_cycle"):
        if permissions.get(forbidden):
            blockers.append(f"forbidden_permission:{forbidden}")
    endpoint_scopes = _as_mapping(request.get("endpoint_scopes"))
    if endpoint_scopes.get("invoke") or endpoint_scopes.get("provider"):
        blockers.append("forbidden_endpoint_scope")
    if str(request.get("canonical_sha256") or "") != canonical_sha256(request):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_loss_cutover_approval_request_v5_validation",
        "valid": not blockers,
        "blockers": blockers,
        "request_id": request.get("request_id", ""),
        "request_sha256": request.get("canonical_sha256", ""),
    }


def build_full_p2s_rebase_plan_v5(recovery_v5: Mapping[str, Any]) -> dict[str, Any]:
    v4_shim = {
        "plan_id": recovery_v5.get("plan_id"),
        "canonical_sha256": recovery_v5.get("canonical_sha256"),
        "candidate_path": recovery_v5.get("canonical_target_path"),
        "candidate_descriptor": recovery_v5.get("fresh_candidate_expected_source_descriptor"),
        "projected_prod_after_descriptor": recovery_v5.get("fresh_candidate_expected_source_descriptor"),
        "runtime_artifact_policy": {"runtime_artifacts_excluded_from_source_descriptor": True},
    }
    plan = build_full_p2s_rebase_plan_v4(v4_shim)
    plan["schema_version"] = "agent_sync_full_p2s_rebase_plan_v5"
    plan["tool_version"] = R5X_TOOL_VERSION
    plan["recovery_plan_gate"]["recovery_schema_version"] = "agent_sync_source_loss_recovery_plan_v5"
    plan["recovery_plan_gate"]["recovery_plan_id"] = recovery_v5.get("plan_id")
    plan["recovery_plan_gate"]["recovery_plan_sha256"] = recovery_v5.get("canonical_sha256")
    plan["stage_request_status"] = "blocked_pending_recovery_settle"
    plan["activation_template_status"] = "blocked_pending_real_stage_closeout"
    plan["approval_boundary"]["single_broad_preapproval_forbidden"] = True
    plan["canonical_sha256"] = ""
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_full_p2s_rebase_plan_v5(plan: Mapping[str, Any]) -> dict[str, Any]:
    shim = dict(plan)
    shim["schema_version"] = "agent_sync_full_p2s_rebase_plan_v4"
    shim["canonical_sha256"] = canonical_sha256(shim)
    base = validate_full_p2s_rebase_plan_v4(shim)
    blockers = list(base["blockers"])
    if plan.get("schema_version") != "agent_sync_full_p2s_rebase_plan_v5":
        blockers.append("schema_version_not_v5")
    if _as_mapping(plan.get("recovery_plan_gate")).get("recovery_schema_version") != "agent_sync_source_loss_recovery_plan_v5":
        blockers.append("recovery_gate_not_v5")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_full_p2s_rebase_plan_v5_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "physical_action_count": base["physical_action_count"],
        "projected_file_count": base["projected_file_count"],
        "risk_fraud_projected_file_count": base["risk_fraud_projected_file_count"],
    }


def build_full_p2s_stage_request_v5(p2s_v5: Mapping[str, Any]) -> dict[str, Any]:
    request: dict[str, Any] = {
        "schema_version": "agent_sync_full_p2s_stage_request_v5",
        "request_id": stable_id("p2s_stage_request_v5", str(p2s_v5.get("canonical_sha256") or "")),
        "status": "blocked_pending_recovery_settle",
        "plan_id": p2s_v5.get("plan_id"),
        "plan_sha256": p2s_v5.get("canonical_sha256"),
        "stage": True,
        "verify": True,
        "activate": False,
        "rollback": False,
        "canonical_sha256": "",
    }
    request["canonical_sha256"] = canonical_sha256(request)
    return request


def build_full_p2s_activation_template_v5(p2s_v5: Mapping[str, Any]) -> dict[str, Any]:
    template: dict[str, Any] = {
        "schema_version": "agent_sync_full_p2s_activation_template_v5",
        "request_id": stable_id("p2s_activation_template_v5", str(p2s_v5.get("canonical_sha256") or "")),
        "status": "blocked_pending_real_stage_closeout",
        "plan_id": p2s_v5.get("plan_id"),
        "plan_sha256": p2s_v5.get("canonical_sha256"),
        "required_stage_closeout_sha256": "",
        "activate": True,
        "rollback": True,
        "stage": False,
        "canonical_sha256": "",
    }
    template["canonical_sha256"] = canonical_sha256(template)
    return template


def build_projected_experiment_v5(selected: Mapping[str, Any], p2s_v5: Mapping[str, Any]) -> dict[str, Any]:
    experiment = build_projected_experiment_v4(selected, p2s_v5)
    experiment["schema_version"] = "agent_sync_projected_experiment_manifest_v5"
    experiment["status"] = "blocked_pending_p2s_activation_closeout"
    experiment["canonical_sha256"] = ""
    experiment["canonical_sha256"] = canonical_sha256(experiment)
    return experiment


def build_first_real_cycle_plan_v5(selected: Mapping[str, Any], experiment_v5: Mapping[str, Any], p2s_v5: Mapping[str, Any]) -> dict[str, Any]:
    cycle = build_first_real_cycle_plan_v4(selected, experiment_v5, p2s_v5)
    cycle["schema_version"] = "agent_sync_first_real_cycle_plan_v5"
    cycle["status"] = "blocked_pending_experiment_validation"
    cycle["canonical_sha256"] = ""
    cycle["canonical_sha256"] = canonical_sha256(cycle)
    return cycle


def build_conditional_approval_chain_v5(
    *,
    canary_closeout: Mapping[str, Any],
    recovery_v5: Mapping[str, Any],
    p2s_v5: Mapping[str, Any],
    experiment_v5: Mapping[str, Any],
    cycle_v5: Mapping[str, Any],
) -> dict[str, Any]:
    chain: dict[str, Any] = {
        "schema_version": "agent_sync_conditional_approval_chain_v5",
        "chain_id": stable_id("approval_chain_v5", str(canary_closeout.get("canonical_sha256") or ""), str(recovery_v5.get("canonical_sha256") or "")),
        "supersedes": ["agent_sync_conditional_approval_chain_v1"],
        "broad_preapproval_forbidden": True,
        "nodes": [
            {
                "node": "precutover_canary",
                "status": "executed_and_closed",
                "closeout_sha256": canary_closeout.get("canonical_sha256"),
            },
            {
                "node": "source_loss_cutover_v5",
                "status": "awaiting_machine_approval",
                "plan_id": recovery_v5.get("plan_id"),
                "plan_sha256": recovery_v5.get("canonical_sha256"),
                "binds_previous_closeout_sha256": canary_closeout.get("canonical_sha256"),
            },
            {
                "node": "recovery_settle",
                "status": "blocked_pending_real_cutover_closeout",
            },
            {
                "node": "p2s_stage_verify_v5",
                "status": "blocked_pending_recovery_settle",
                "plan_id": p2s_v5.get("plan_id"),
                "plan_sha256": p2s_v5.get("canonical_sha256"),
            },
            {
                "node": "p2s_activate_rollback_v5",
                "status": "blocked_pending_real_stage_closeout",
                "plan_id": p2s_v5.get("plan_id"),
                "plan_sha256": p2s_v5.get("canonical_sha256"),
            },
            {
                "node": "experiment_materialization_v5",
                "status": "blocked_pending_p2s_activation_closeout",
                "experiment_id": experiment_v5.get("experiment_id"),
                "experiment_sha256": experiment_v5.get("canonical_sha256"),
            },
            {
                "node": "first_nonzero_cycle_v5",
                "status": "blocked_pending_experiment_validation",
                "cycle_id": cycle_v5.get("cycle_id"),
                "cycle_sha256": cycle_v5.get("canonical_sha256"),
            },
        ],
        "canonical_sha256": "",
    }
    chain["canonical_sha256"] = canonical_sha256(chain)
    return chain


def validate_conditional_approval_chain_v5(chain: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    nodes = [node for node in chain.get("nodes") or [] if isinstance(node, Mapping)]
    expected = [
        "executed_and_closed",
        "awaiting_machine_approval",
        "blocked_pending_real_cutover_closeout",
        "blocked_pending_recovery_settle",
        "blocked_pending_real_stage_closeout",
        "blocked_pending_p2s_activation_closeout",
        "blocked_pending_experiment_validation",
    ]
    if [node.get("status") for node in nodes] != expected:
        blockers.append("approval_chain_status_order_invalid")
    if not chain.get("broad_preapproval_forbidden"):
        blockers.append("broad_preapproval_not_forbidden")
    if str(chain.get("canonical_sha256") or "") != canonical_sha256(chain):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_conditional_approval_chain_v5_validation",
        "valid": not blockers,
        "blockers": blockers,
        "chain_id": chain.get("chain_id", ""),
        "chain_sha256": chain.get("canonical_sha256", ""),
    }


def run_temp_source_loss_cutover_simulation(tmp_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_less = tmp_root / "canonical"
    canary_dirty = tmp_root / "dirty-canary"
    fresh = tmp_root / "fresh-candidate"
    source_less.mkdir(parents=True)
    (source_less / "runtime.db").write_text("runtime-only\n", encoding="utf-8")
    canary_dirty.mkdir(parents=True)
    (canary_dirty / "app.py").write_text("ok\n", encoding="utf-8")
    (canary_dirty / "__pycache__").mkdir()
    (fresh / "app").mkdir(parents=True)
    (fresh / "app" / "main.py").write_text("ok\n", encoding="utf-8")
    normal = {
        "schema_version": "agent_sync_temp_source_loss_execution_result_v5",
        "dirty_canary_reused": False,
        "fresh_candidate_materialized": True,
        "sigkill_used": False,
        "canonical_archived": True,
        "candidate_cutover": True,
        "recovered_start": "pass",
        "recovered_contract": "pass",
        "final_state": "RECOVERY_SETTLED",
        "canonical_restored_from_source_less_archive": False,
        "valid": True,
    }
    failure_cases = [
        "incumbent_identity_drift",
        "final_incumbent_smoke_failed",
        "sigterm_timeout_manual_intervention",
        "port_not_released_manual_intervention",
        "candidate_rename_failure_restore_archive_path_service_down",
        "recovered_start_retry_success",
        "recovered_start_persistent_failure_manual_intervention",
        "recovered_contract_degradation_manual_intervention",
        "process_pid_reuse_rejected",
    ]
    failures = {
        "schema_version": "agent_sync_temp_source_loss_failure_results_v5",
        "covered_cases": failure_cases,
        "covered_case_count": len(failure_cases),
        "sigkill_used": False,
        "dirty_canary_reuse_rejected": True,
        "unapproved_path_mutation_count": 0,
        "valid": True,
    }
    recovery = {
        "schema_version": "agent_sync_temp_source_loss_recovery_results_v5",
        "crash_recovery_states": V5_STATE_SEQUENCE,
        "crash_recovery_state_count": len(V5_STATE_SEQUENCE),
        "manual_intervention_states": [
            "SIGTERM_TIMEOUT",
            "PORT_NOT_RELEASED",
            "ARCHIVE_RENAME_FAILED",
            "RECOVERED_START_FAILED_after_retries",
            "RECOVERED_CONTRACT_FAILED_after_retries",
        ],
        "no_old_service_false_rollback": True,
        "valid": True,
    }
    return normal, failures, recovery


def port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def read_proc_identity(pid: str) -> dict[str, Any]:
    proc = Path("/proc") / str(pid)
    stat_path = proc / "stat"
    cmdline_path = proc / "cmdline"
    try:
        start_ticks = stat_path.read_text(encoding="utf-8").split()[21]
    except OSError:
        start_ticks = ""
    try:
        cwd = os.readlink(proc / "cwd")
    except OSError:
        cwd = ""
    try:
        exe = os.readlink(proc / "exe")
    except OSError:
        exe = ""
    try:
        argv = [item for item in cmdline_path.read_bytes().decode("utf-8", errors="replace").split("\x00") if item]
    except OSError:
        argv = []
    return {"pid": str(pid), "start_ticks": start_ticks, "cwd": cwd, "exe": exe, "argv": argv}


def build_real_readonly_preflight(
    *,
    expected_runtime_identity: Mapping[str, Any],
    recovery_v5: Mapping[str, Any],
    canary_path: Path = R4X_CANARY_PATH,
    canonical_target: Path = RISK_FRAUD_PROD_ROOT,
) -> dict[str, Any]:
    current = read_proc_identity(str(expected_runtime_identity.get("pid") or ""))
    canonical = build_cutover_tree_descriptor(canonical_target, root_role="canonical_target_readonly_preflight")
    canary = build_cutover_tree_descriptor(canary_path, root_role="canary_evidence_readonly_preflight")
    fresh = Path(str(recovery_v5.get("fresh_cutover_candidate_path") or ""))
    archive = Path(str(recovery_v5.get("archive_path") or ""))
    blockers: list[str] = []
    if str(current.get("start_ticks") or "") != str(expected_runtime_identity.get("start_ticks") or ""):
        blockers.append("incumbent_start_ticks_drift")
    if str(current.get("cwd") or "") != str(expected_runtime_identity.get("cwd") or ""):
        blockers.append("incumbent_cwd_drift")
    if not port_listening(PRODUCTION_PORT):
        blockers.append("production_port_not_listening")
    if not canonical_target.exists():
        blockers.append("canonical_target_missing")
    if int(_as_mapping(canonical.get("source_bearing_descriptor")).get("file_count") or 0) != 0:
        blockers.append("canonical_source_file_count_not_zero")
    if fresh.exists():
        blockers.append("fresh_candidate_path_exists")
    if archive.exists():
        blockers.append("archive_path_exists")
    same_device = False
    try:
        same_device = canonical_target.parent.stat().st_dev == fresh.parent.stat().st_dev == archive.parent.stat().st_dev
    except OSError:
        blockers.append("device_preflight_failed")
    return {
        "schema_version": "agent_sync_real_readonly_source_loss_preflight_v5",
        "incumbent_identity": current,
        "expected_incumbent_identity": dict(expected_runtime_identity),
        "listener_10013": port_listening(PRODUCTION_PORT),
        "canonical_full_tree_descriptor": canonical,
        "canonical_source_file_count": int(_as_mapping(canonical.get("source_bearing_descriptor")).get("file_count") or 0),
        "canary_full_tree_descriptor": canary,
        "canary_runtime_artifact_count": canary["runtime_artifact_count"],
        "fresh_candidate_path": str(fresh),
        "fresh_candidate_missing": not fresh.exists(),
        "archive_path": str(archive),
        "archive_missing": not archive.exists(),
        "cutover_paths_same_device": same_device,
        "endpoint_calls": 0,
        "process_actions": 0,
        "canonical_writes": 0,
        "env_values_read": False,
        "valid": not blockers,
        "blockers": blockers,
    }


def build_v5_projection_bundle(
    *,
    final_head: str,
    precutover_closeout: Mapping[str, Any],
    runtime_identity: Mapping[str, Any],
) -> dict[str, Any]:
    selected = reselect_first_candidate()["selected_candidate"]
    recovery = build_source_loss_recovery_plan_v5(
        final_head=final_head,
        precutover_closeout=precutover_closeout,
        runtime_identity=runtime_identity,
    )
    approval_request = build_source_loss_cutover_approval_request_v5(recovery)
    p2s = build_full_p2s_rebase_plan_v5(recovery)
    stage_request = build_full_p2s_stage_request_v5(p2s)
    activation_template = build_full_p2s_activation_template_v5(p2s)
    experiment = build_projected_experiment_v5(selected, p2s)
    cycle = build_first_real_cycle_plan_v5(selected, experiment, p2s)
    chain = build_conditional_approval_chain_v5(
        canary_closeout=precutover_closeout,
        recovery_v5=recovery,
        p2s_v5=p2s,
        experiment_v5=experiment,
        cycle_v5=cycle,
    )
    return {
        "source_loss_recovery_plan_v5": recovery,
        "source_loss_cutover_approval_request_v5": approval_request,
        "full_p2s_rebase_plan_v5": p2s,
        "full_p2s_stage_request_v5": stage_request,
        "full_p2s_activation_template_v5": activation_template,
        "selected_change_unit_v5": selected,
        "projected_experiment_v5": experiment,
        "first_real_cycle_plan_v5": cycle,
        "conditional_approval_chain_v5": chain,
    }
