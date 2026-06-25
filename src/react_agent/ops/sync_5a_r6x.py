# ruff: noqa: D101, D102, D103
"""SYNC-OPS-5A-R6X clean source-loss cutover candidate contracts."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from react_agent.ops.sync_5a_r1x import (
    RISK_FRAUD_AGENT_ID,
    RISK_FRAUD_HISTORICAL_ROOT,
    RISK_FRAUD_PROD_ROOT,
)
from react_agent.ops.sync_5a_r2x import expires_utc, now_utc, reselect_first_candidate
from react_agent.ops.sync_5a_r3x import build_source_package_provenance
from react_agent.ops.sync_5a_r5x import (
    PRODUCTION_PORT,
    R4X_CANARY_PATH,
    build_cutover_tree_descriptor,
    build_full_p2s_activation_template_v5,
    build_full_p2s_rebase_plan_v5,
    build_full_p2s_stage_request_v5,
    build_production_launch_authority_v1,
    build_real_readonly_preflight,
    build_source_loss_failure_policy_v5,
    build_source_loss_state_machine_v5,
    port_listening,
    validate_full_p2s_rebase_plan_v5,
    validate_production_launch_authority_v1,
)
from react_agent.ops.sync_contracts import canonical_sha256, file_sha256, stable_id
from react_agent.ops.sync_inventory import inventory_root
from react_agent.ops.sync_s2p import descriptor_from_inventory
from react_agent.ops.sync_security import (
    classify_file_type,
    classify_source_category,
    normalize_safe_relative_path,
    validate_root_containment,
)

R6X_TOOL_VERSION = "sync_ops_5a_r6x_clean_cutover_candidate_projection"
R6X_SUPERSESSION_REASON = "superseded_due_contaminated_fresh_candidate_projection_and_incomplete_file_metadata"
R5X_PLAN_ID = "source_loss_recovery_v5_39ac9e888867"
R5X_PLAN_SHA256 = "49d1e84b06f93b20b0dd3230c84e7bb1a6f9389a370765cc57df74c285212081"
R5X_APPROVAL_REQUEST_ID = "source_loss_cutover_request_v5_16fa53986cee"
EXPECTED_SOURCE_DESCRIPTOR_DIGEST = "e6f4d26e29074a59245ed809aadea1ebdf74bff5d1c2cea16b45a7a4e647b6e5"
EXPECTED_SOURCE_PROVENANCE_SHA256 = "71832769e4c68d234aa7f9487e1c58b634da795aba7b6ca300f282f84ceac63f"

V6_REQUIRED_CUTOVER_OPERATIONS = [
    "preflight_candidate_path_missing",
    "materialize_67_files",
    "validate_clean_fresh_candidate",
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


def _source_descriptor(source_root: Path = RISK_FRAUD_HISTORICAL_ROOT) -> dict[str, Any]:
    inventory = inventory_root(RISK_FRAUD_AGENT_ID, source_root, root_role="source_loss_recovery_package")
    return descriptor_from_inventory(inventory, scope="transaction_source_tree")


def _relative_parent_dirs(relative_paths: Iterable[str]) -> list[str]:
    parents: set[str] = set()
    for rel in relative_paths:
        path = PurePosixPath(normalize_safe_relative_path(rel))
        for parent in path.parents:
            text = parent.as_posix()
            if text and text != ".":
                parents.add(text)
    return sorted(parents)


def _entry_digest(entries: Sequence[Mapping[str, Any]]) -> str:
    digest_entries = [
        {
            "relative_path": entry["relative_path"],
            "entry_type": entry["entry_type"],
            "sha256": entry.get("sha256", ""),
            "mode": entry.get("mode", ""),
            "executable": bool(entry.get("executable", False)),
            "symlink_target": entry.get("symlink_target", ""),
            "classification": entry["classification"],
        }
        for entry in sorted(entries, key=lambda item: str(item["relative_path"]))
    ]
    return canonical_sha256(digest_entries)


def build_source_action_metadata_ledger(
    *,
    plan_id: str,
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    candidate_path: Path,
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    provenance = provenance or build_source_package_provenance(source_root)
    actions: list[dict[str, Any]] = []
    blockers: list[str] = []
    destinations: set[str] = set()
    for entry in provenance.get("entries") or []:
        if not isinstance(entry, Mapping):
            continue
        rel = normalize_safe_relative_path(str(entry.get("relative_path") or ""))
        src = source_root / rel
        dest = candidate_path / rel
        try:
            stat_result = src.lstat()
        except OSError:
            blockers.append(f"missing_source:{rel}")
            continue
        file_type = classify_file_type(stat_result.st_mode)
        mode_text = oct(stat.S_IMODE(stat_result.st_mode))
        executable = bool(stat_result.st_mode & stat.S_IXUSR)
        actual_sha = file_sha256(src) if file_type == "regular" else ""
        expected_sha = str(entry.get("sha256") or "")
        if file_type != "regular":
            blockers.append(f"source_not_regular:{rel}")
        if actual_sha != expected_sha:
            blockers.append(f"source_sha_drift:{rel}")
        if str(dest) in destinations:
            blockers.append(f"duplicate_destination:{rel}")
        destinations.add(str(dest))
        validate_root_containment(candidate_path, dest)
        actions.append(
            {
                "action_id": stable_id("slrv6_file", plan_id, rel, expected_sha, mode_text, str(executable)),
                "operation": "materialize_fresh_candidate_file",
                "source_path": str(src),
                "source_sha256": expected_sha,
                "source_file_type": file_type,
                "source_mode": mode_text,
                "source_executable": executable,
                "relative_path": rel,
                "destination_path": str(dest),
                "expected_destination_type": "regular",
                "expected_destination_mode": mode_text,
                "follow_symlink": False,
                "hardlink_allowed": False,
                "classification": classify_source_category(source_root, src)[0],
            }
        )
    payload: dict[str, Any] = {
        "schema_version": "agent_sync_source_action_metadata_ledger_v1",
        "plan_id": plan_id,
        "source_root": str(source_root),
        "candidate_path": str(candidate_path),
        "action_count": len(actions),
        "actions": sorted(actions, key=lambda item: item["relative_path"]),
        "metadata_complete": not blockers and len(actions) == 67,
        "blockers": blockers,
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def build_clean_candidate_projection(
    *,
    root: Path,
    actions: list[Mapping[str, Any]],
    source_descriptor: Mapping[str, Any],
) -> dict[str, Any]:
    relative_paths = [normalize_safe_relative_path(str(action.get("relative_path") or "")) for action in actions]
    parent_dirs = _relative_parent_dirs(relative_paths)
    entries: list[dict[str, Any]] = [
        {
            "relative_path": ".",
            "entry_type": "directory",
            "sha256": "",
            "mode": "0o755",
            "executable": True,
            "symlink_target": "",
            "classification": "root_directory",
        }
    ]
    entries.extend(
        {
            "relative_path": parent,
            "entry_type": "directory",
            "sha256": "",
            "mode": "0o755",
            "executable": True,
            "symlink_target": "",
            "classification": "directory",
        }
        for parent in parent_dirs
    )
    for action in sorted(actions, key=lambda item: str(item.get("relative_path") or "")):
        entries.append(
            {
                "relative_path": normalize_safe_relative_path(str(action.get("relative_path") or "")),
                "entry_type": str(action.get("expected_destination_type") or ""),
                "sha256": str(action.get("source_sha256") or ""),
                "mode": str(action.get("expected_destination_mode") or ""),
                "executable": bool(action.get("source_executable", False)),
                "symlink_target": "",
                "classification": str(action.get("classification") or "source_code"),
            }
        )
    counts = Counter(entry["classification"] for entry in entries)
    projection: dict[str, Any] = {
        "schema_version": "agent_sync_clean_cutover_candidate_projection_v1",
        "root": str(root),
        "source_action_count": len(actions),
        "regular_file_count": sum(1 for entry in entries if entry["entry_type"] == "regular"),
        "parent_directory_count": len(parent_dirs),
        "root_entry_count": 1,
        "directory_count_including_root": len(parent_dirs) + 1,
        "root_included": True,
        "projected_entry_count": len(entries),
        "entry_count": len(entries),
        "symlink_count": 0,
        "special_file_count": 0,
        "runtime_artifact_count": 0,
        "data_model_reference_count": 0,
        "unknown_entry_count": 0,
        "sensitive_entry_count": 0,
        "unexpected_entries": [],
        "source_descriptor": dict(source_descriptor),
        "classification_counts": dict(sorted(counts.items())),
        "projected_paths": sorted(relative_paths),
        "parent_directories": parent_dirs,
        "full_entry_digest": _entry_digest(entries),
        "canonical_sha256": "",
    }
    projection["canonical_sha256"] = canonical_sha256(projection)
    return projection


def validate_clean_candidate_projection(projection: Mapping[str, Any], actions: list[Mapping[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    action_paths = sorted(normalize_safe_relative_path(str(action.get("relative_path") or "")) for action in actions)
    if projection.get("schema_version") != "agent_sync_clean_cutover_candidate_projection_v1":
        blockers.append("schema_version_not_clean_projection_v1")
    if int(projection.get("regular_file_count") or 0) != len(actions):
        blockers.append("fresh_candidate_projection_file_count_mismatch")
    if int(_as_mapping(projection.get("source_descriptor")).get("file_count") or 0) != len(actions):
        blockers.append("source_descriptor_file_count_mismatch")
    if int(projection.get("runtime_artifact_count") or 0) != 0:
        blockers.append("fresh_candidate_projection_contains_runtime_noise")
    if int(projection.get("data_model_reference_count") or 0) != 0:
        blockers.append("fresh_candidate_projection_contains_data_model_reference")
    if int(projection.get("unknown_entry_count") or 0) != 0:
        blockers.append("fresh_candidate_projection_contains_unknown_entries")
    if int(projection.get("sensitive_entry_count") or 0) != 0:
        blockers.append("fresh_candidate_projection_contains_sensitive_entries")
    if int(projection.get("special_file_count") or 0) != 0 or int(projection.get("symlink_count") or 0) != 0:
        blockers.append("fresh_candidate_projection_contains_non_regular_entries")
    if projection.get("unexpected_entries"):
        blockers.append("fresh_candidate_projection_contains_unexpected_entries")
    entry_count = int(projection.get("entry_count") or projection.get("projected_entry_count") or 0)
    computed_entry_count = (
        int(projection.get("regular_file_count") or 0)
        + int(projection.get("directory_count_including_root") or 0)
        + int(projection.get("symlink_count") or 0)
        + int(projection.get("special_file_count") or 0)
    )
    if entry_count != computed_entry_count:
        blockers.append("descriptor_entry_count_invariant_failed")
    class_sum = sum(int(value) for value in _as_mapping(projection.get("classification_counts")).values())
    if class_sum != entry_count:
        blockers.append("descriptor_classification_count_invariant_failed")
    if sorted(projection.get("projected_paths") or []) != action_paths:
        blockers.append("projected_paths_action_mismatch")
    if str(projection.get("canonical_sha256") or "") != canonical_sha256(projection):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_clean_cutover_candidate_projection_v1_validation",
        "valid": not blockers,
        "blockers": blockers,
        "regular_file_count": int(projection.get("regular_file_count") or 0),
        "parent_directory_count": int(projection.get("parent_directory_count") or 0),
        "projected_entry_count": entry_count,
        "full_entry_digest": projection.get("full_entry_digest", ""),
    }


def _action_metadata_missing(action: Mapping[str, Any]) -> bool:
    required = (
        "source_file_type",
        "source_mode",
        "source_executable",
        "expected_destination_type",
        "expected_destination_mode",
        "follow_symlink",
        "hardlink_allowed",
    )
    return any(key not in action for key in required)


def validate_source_loss_recovery_plan_v5_strict(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if plan.get("schema_version") != "agent_sync_source_loss_recovery_plan_v5":
        blockers.append("schema_version_not_v5")
    file_actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    fresh = _as_mapping(plan.get("fresh_candidate_expected_full_tree_descriptor"))
    if int(fresh.get("regular_file_count") or 0) != len(file_actions):
        blockers.append("fresh_candidate_projection_file_count_mismatch")
    if int(fresh.get("runtime_artifact_count") or 0) != 0:
        blockers.append("fresh_candidate_projection_contains_runtime_noise")
    if int(fresh.get("unknown_entry_count") or 0) != 0:
        blockers.append("fresh_candidate_projection_contains_unknown_entries")
    if fresh.get("unexpected_entries"):
        blockers.append("fresh_candidate_projection_contains_unexpected_entries")
    if any(_action_metadata_missing(action) for action in file_actions):
        blockers.append("file_action_metadata_incomplete")
    return {
        "schema_version": "agent_sync_source_loss_recovery_plan_v5_strict_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "expected_fail_closed": bool(blockers),
    }


def materialize_clean_candidate_from_actions(candidate_root: Path, actions: list[Mapping[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    if candidate_root.exists():
        blockers.append("candidate_root_already_exists")
    else:
        candidate_root.mkdir(parents=True)
    copied = 0
    for action in sorted(actions, key=lambda item: str(item.get("relative_path") or "")):
        rel = normalize_safe_relative_path(str(action.get("relative_path") or ""))
        src = Path(str(action.get("source_path") or ""))
        dest = candidate_root / rel
        try:
            stat_result = src.lstat()
        except OSError:
            blockers.append(f"missing_source:{rel}")
            continue
        if classify_file_type(stat_result.st_mode) != "regular" or src.is_symlink():
            blockers.append(f"source_not_regular:{rel}")
            continue
        if file_sha256(src) != action.get("source_sha256"):
            blockers.append(f"source_sha_drift:{rel}")
            continue
        if oct(stat.S_IMODE(stat_result.st_mode)) != action.get("source_mode"):
            blockers.append(f"source_mode_drift:{rel}")
            continue
        if bool(stat_result.st_mode & stat.S_IXUSR) != bool(action.get("source_executable")):
            blockers.append(f"source_executable_drift:{rel}")
            continue
        validate_root_containment(candidate_root, dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest, follow_symlinks=False)
        os.chmod(dest, stat.S_IMODE(stat_result.st_mode), follow_symlinks=False)
        copied += 1
        dest_stat = dest.lstat()
        if dest_stat.st_nlink != 1:
            blockers.append(f"hardlink_detected:{rel}")
        if file_sha256(dest) != action.get("source_sha256"):
            blockers.append(f"destination_sha_mismatch:{rel}")
    descriptor = build_cutover_tree_descriptor(candidate_root, root_role="temp_clean_candidate_materialized")
    return {
        "schema_version": "agent_sync_full_67_file_temp_materialization_result_v1",
        "candidate_root": str(candidate_root),
        "file_action_count": len(actions),
        "copied_file_count": copied,
        "descriptor": descriptor,
        "regular_file_count": descriptor["regular_file_count"],
        "directory_count": descriptor["directory_count"],
        "entry_count": descriptor["entry_count"],
        "runtime_artifact_count": descriptor["runtime_artifact_count"],
        "unknown_entry_count": descriptor["unknown_entry_count"],
        "unexpected_entry_count": len(descriptor["unexpected_entries"]),
        "hardlink_detected": any(blocker.startswith("hardlink_detected") for blocker in blockers),
        "symlink_count": descriptor["symlink_count"],
        "special_file_count": descriptor["special_file_count"],
        "valid": copied == len(actions) == 67
        and not blockers
        and descriptor["regular_file_count"] == 67
        and descriptor["entry_count"] == 78
        and descriptor["runtime_artifact_count"] == 0
        and descriptor["unknown_entry_count"] == 0
        and not descriptor["unexpected_entries"],
        "blockers": blockers,
        "canonical_sha256": "",
    }


def _candidate_cache_counts(candidate_root: Path) -> dict[str, int]:
    counts = {
        "pycache_dir_count": 0,
        "pyc_file_count": 0,
        "pytest_cache_count": 0,
        "runtime_temp_log_db_count": 0,
    }
    for path in candidate_root.rglob("*"):
        rel_parts = {part.lower() for part in path.relative_to(candidate_root).parts}
        name = path.name.lower()
        if path.is_dir() and name == "__pycache__":
            counts["pycache_dir_count"] += 1
        if path.is_file() and name.endswith(".pyc"):
            counts["pyc_file_count"] += 1
        if ".pytest_cache" in rel_parts:
            counts["pytest_cache_count"] += 1
        if name.endswith((".db", ".sqlite", ".sqlite3", ".log", ".pid", ".sock")) or rel_parts & {"tmp", "temp", "logs", "log"}:
            counts["runtime_temp_log_db_count"] += 1
    return counts


def run_offline_validation_nonmutating(
    candidate_root: Path,
    *,
    python_executable: str | None = None,
    include_pytest: bool = True,
) -> dict[str, Any]:
    python = python_executable or os.environ.get("PYTHON", "") or sys.executable
    before = build_cutover_tree_descriptor(candidate_root, root_role="candidate_before_offline_validation")
    before_cache = _candidate_cache_counts(candidate_root)
    temp_root = Path(tempfile.mkdtemp(prefix="lma-r6x-validation-cache-", dir="/tmp"))
    env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": str(temp_root / "pycache"),
        "XDG_CACHE_HOME": str(temp_root / "xdg-cache"),
        "HOME": str(temp_root / "home"),
    }
    (temp_root / "home").mkdir(parents=True, exist_ok=True)
    py_files = sorted(str(path.relative_to(candidate_root)) for path in candidate_root.rglob("*.py"))
    commands: list[list[str]] = []
    if py_files:
        commands.append([python, "-m", "py_compile", *py_files])
    tests = [path for path in ("tests/test_report_material.py", "tests/test_compute_core.py", "tests/test_protocol_contract.py") if (candidate_root / path).exists()]
    if include_pytest and tests:
        commands.append([python, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider", "--basetemp", str(temp_root / "pytest-basetemp")])
    command_results: list[dict[str, Any]] = []
    for command in commands:
        result = subprocess.run(command, cwd=candidate_root, env=env, check=False, capture_output=True, text=True)
        command_results.append(
            {
                "argv_summary": [Path(command[0]).name, *command[1:3]],
                "returncode": result.returncode,
                "stdout_sha256": canonical_sha256(result.stdout),
                "stderr_sha256": canonical_sha256(result.stderr),
            }
        )
    after = build_cutover_tree_descriptor(candidate_root, root_role="candidate_after_offline_validation")
    after_cache = _candidate_cache_counts(candidate_root)
    mutated = before["full_entry_digest"] != after["full_entry_digest"]
    hard_failures = [item for item in command_results if item["returncode"] != 0]
    payload: dict[str, Any] = {
        "schema_version": "agent_sync_offline_validation_nonmutation_result_v1",
        "candidate_root": str(candidate_root),
        "before_descriptor": before,
        "after_descriptor": after,
        "before_full_entry_digest": before["full_entry_digest"],
        "after_full_entry_digest": after["full_entry_digest"],
        "candidate_mutation_count": 1 if mutated else 0,
        "before_cache_counts": before_cache,
        "after_cache_counts": after_cache,
        "command_results": command_results,
        "hard_failure_count": len(hard_failures),
        "tree_nonmutating": not mutated,
        "cache_pollution_count": sum(after_cache.values()),
        "valid": not mutated and not hard_failures and sum(after_cache.values()) == 0,
        "blockers": [],
    }
    if mutated:
        payload["blockers"].append("candidate_offline_validation_mutated_tree")
    if hard_failures:
        payload["blockers"].append("candidate_offline_validation_command_failed")
    if sum(after_cache.values()):
        payload["blockers"].append("candidate_offline_validation_cache_pollution")
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def build_poststart_runtime_artifact_policy(source_descriptor: Mapping[str, Any]) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "schema_version": "agent_sync_poststart_runtime_artifact_policy_v1",
        "allowed_paths": [
            "data/**",
            "__pycache__/**",
            "app/**/__pycache__/**",
            "agent协议/**/__pycache__/**",
            "tests/**/__pycache__/**",
        ],
        "allowed_classes": ["runtime_noise", "data_asset", "model_asset"],
        "forbidden_paths": [".env", ".env.*", "*.pyc_in_clean_prestart"],
        "source_descriptor_must_remain": source_descriptor.get("digest", ""),
        "unknown_runtime_artifacts_allowed": False,
        "raw_runtime_bytes_in_portable_artifact": False,
        "canonical_sha256": "",
    }
    policy["canonical_sha256"] = canonical_sha256(policy)
    return policy


def _actual_tree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not root.exists():
        return entries
    for path in sorted([root, *root.rglob("*")], key=lambda item: "" if item == root else normalize_safe_relative_path(item.relative_to(root))):
        try:
            stat_result = path.lstat()
        except OSError:
            continue
        file_type = classify_file_type(stat_result.st_mode)
        rel = "." if path == root else normalize_safe_relative_path(path.relative_to(root))
        descriptor = build_cutover_tree_descriptor(path if path == root else root, root_role="delta_scan")
        del descriptor
        if path == root:
            classification = "root_directory"
            reason = "root"
        else:
            parts = {part.lower() for part in path.relative_to(root).parts}
            if "__pycache__" in parts or ".pytest_cache" in parts or path.name.endswith(".pyc"):
                classification, reason = "runtime_noise", "poststart_python_cache"
            elif parts & {"data", "dataset", "datasets"}:
                classification, reason = "data_asset", "poststart_data_reference"
            elif parts & {"models", "weights"}:
                classification, reason = "model_asset", "poststart_model_reference"
            else:
                from react_agent.ops.sync_5a_r5x import (
                    _entry_classification,  # local import avoids exporting private helper
                )

                classification, reason = _entry_classification(root, path, file_type)
        entries.append(
            {
                "relative_path": rel,
                "entry_type": file_type,
                "mode": oct(stat.S_IMODE(stat_result.st_mode)),
                "executable": bool(stat_result.st_mode & stat.S_IXUSR),
                "classification": classification,
                "classification_reason": reason,
            }
        )
    return entries


def build_canary_postrun_delta_ledger(
    *,
    canary_root: Path = R4X_CANARY_PATH,
    clean_projection: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    source_paths = set(str(path) for path in clean_projection.get("projected_paths") or [])
    source_paths.update(str(path) for path in clean_projection.get("parent_directories") or [])
    source_paths.add(".")
    entries = _actual_tree_entries(canary_root)
    delta = []
    blocked = []
    allowed_classes = set(str(item) for item in policy.get("allowed_classes") or [])
    for entry in entries:
        rel = entry["relative_path"]
        if rel in source_paths:
            continue
        allowed = entry["classification"] in allowed_classes
        if not allowed:
            blocked.append(rel)
        delta.append({**entry, "source_projection_member": False, "allowed_by_poststart_policy": allowed})
    counts = Counter(item["classification"] for item in delta)
    ledger: dict[str, Any] = {
        "schema_version": "agent_sync_canary_postrun_delta_ledger_v1",
        "canary_root": str(canary_root),
        "delta_entries": delta,
        "delta_entry_count": len(delta),
        "classification_counts": dict(sorted(counts.items())),
        "blocked_delta_entries": blocked,
        "blocked_delta_count": len(blocked),
        "policy_sha256": policy.get("canonical_sha256", ""),
        "valid": len(blocked) == 0,
        "canonical_sha256": "",
    }
    ledger["canonical_sha256"] = canonical_sha256(ledger)
    return ledger


def validate_poststart_runtime_artifact_policy(policy: Mapping[str, Any], delta: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if policy.get("schema_version") != "agent_sync_poststart_runtime_artifact_policy_v1":
        blockers.append("schema_version_not_poststart_policy_v1")
    if policy.get("unknown_runtime_artifacts_allowed") is not False:
        blockers.append("unknown_runtime_artifacts_must_be_forbidden")
    if int(delta.get("blocked_delta_count") or 0) != 0:
        blockers.append("blocked_poststart_runtime_artifact_authority")
    if str(policy.get("canonical_sha256") or "") != canonical_sha256(policy):
        blockers.append("policy_canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_poststart_runtime_artifact_policy_v1_validation",
        "valid": not blockers,
        "blockers": blockers,
        "policy_sha256": policy.get("canonical_sha256", ""),
        "delta_entry_count": delta.get("delta_entry_count", 0),
    }


def _cutover_actions_v6(plan_id: str) -> list[dict[str, Any]]:
    return [
        {
            "action_id": stable_id("slrv6_action", plan_id, operation),
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
        for operation in V6_REQUIRED_CUTOVER_OPERATIONS
    ]


def build_source_loss_recovery_plan_v6(
    *,
    final_head: str,
    precutover_closeout: Mapping[str, Any],
    runtime_identity: Mapping[str, Any],
    qualification_evidence: Mapping[str, Any],
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    canonical_target: Path = RISK_FRAUD_PROD_ROOT,
    canary_path: Path = R4X_CANARY_PATH,
) -> dict[str, Any]:
    provenance = build_source_package_provenance(source_root)
    source_descriptor = _source_descriptor(source_root)
    plan_seed = stable_id(
        "source_loss_recovery_v6_seed",
        final_head,
        provenance["canonical_sha256"],
        source_descriptor["digest"],
        str(precutover_closeout.get("canonical_sha256") or ""),
        str(runtime_identity.get("pid") or ""),
        str(runtime_identity.get("start_ticks") or ""),
    )
    fresh_candidate = canonical_target.parent / f".agent-sync-risk-fraud-cutover-{plan_seed}"
    archive_path = canonical_target.parent / f".agent-sync-archive-risk-fraud-{plan_seed}"
    action_ledger = build_source_action_metadata_ledger(
        plan_id=plan_seed,
        source_root=source_root,
        candidate_path=fresh_candidate,
        provenance=provenance,
    )
    clean_projection = build_clean_candidate_projection(
        root=fresh_candidate,
        actions=action_ledger["actions"],
        source_descriptor=source_descriptor,
    )
    poststart_policy = build_poststart_runtime_artifact_policy(source_descriptor)
    plan_id = stable_id(
        "source_loss_recovery_v6",
        final_head,
        clean_projection["canonical_sha256"],
        poststart_policy["canonical_sha256"],
        str(qualification_evidence.get("canonical_sha256") or ""),
    )
    fresh_candidate = canonical_target.parent / f".agent-sync-risk-fraud-cutover-{plan_id}"
    archive_path = canonical_target.parent / f".agent-sync-archive-risk-fraud-{plan_id}"
    action_ledger = build_source_action_metadata_ledger(
        plan_id=plan_id,
        source_root=source_root,
        candidate_path=fresh_candidate,
        provenance=provenance,
    )
    clean_projection = build_clean_candidate_projection(
        root=fresh_candidate,
        actions=action_ledger["actions"],
        source_descriptor=source_descriptor,
    )
    launch = build_production_launch_authority_v1(
        plan_id=plan_id,
        environment_profile_sha256=str(precutover_closeout.get("environment_profile_sha256") or ""),
        canonical_target=canonical_target,
    )
    cutover_actions = _cutover_actions_v6(plan_id)
    action_ids = [action["action_id"] for action in action_ledger["actions"]] + [action["action_id"] for action in cutover_actions]
    state_machine = build_source_loss_state_machine_v5()
    state_machine["schema_version"] = "agent_sync_source_loss_state_machine_v6"
    state_machine["canonical_sha256"] = ""
    state_machine["canonical_sha256"] = canonical_sha256(state_machine)
    failure_policy = build_source_loss_failure_policy_v5()
    failure_policy["schema_version"] = "agent_sync_source_loss_failure_policy_v6"
    failure_policy["canonical_sha256"] = ""
    failure_policy["canonical_sha256"] = canonical_sha256(failure_policy)
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_recovery_plan_v6",
        "tool_version": R6X_TOOL_VERSION,
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
        "canonical_full_tree_descriptor": build_cutover_tree_descriptor(canonical_target, root_role="canonical_target_before_cutover_v6"),
        "canonical_source_descriptor": build_cutover_tree_descriptor(canonical_target, root_role="canonical_target_before_cutover_v6")["source_bearing_descriptor"],
        "canary_evidence_path": str(canary_path),
        "clean_fresh_candidate_path": str(fresh_candidate),
        "fresh_cutover_candidate_path": str(fresh_candidate),
        "clean_fresh_candidate_expected_state": "missing",
        "clean_fresh_candidate_projection": clean_projection,
        "poststart_runtime_artifact_policy": poststart_policy,
        "archive_path": str(archive_path),
        "archive_expected_state": "missing",
        "production_launch_authority": launch,
        "production_launch_authority_sha256": launch["canonical_sha256"],
        "incumbent_identity": dict(runtime_identity),
        "incumbent_port": PRODUCTION_PORT,
        "file_actions": action_ledger["actions"],
        "cutover_actions": cutover_actions,
        "exact_requested_action_ids": action_ids,
        "state_machine": state_machine,
        "failure_policy": failure_policy,
        "qualification_evidence": dict(qualification_evidence),
        "validation_requirements": {
            "clean_projection_valid": True,
            "offline_validation_nonmutating": True,
            "full_materialization_pass": True,
            "runtime_artifacts_prestart": 0,
            "unknown_entries": 0,
            "unexpected_entries": 0,
            "file_action_metadata_complete": True,
        },
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


def validate_source_loss_recovery_plan_v6(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if plan.get("schema_version") != "agent_sync_source_loss_recovery_plan_v6":
        blockers.append("schema_version_not_v6")
    file_actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    if len(file_actions) != 67:
        blockers.append("file_action_count_not_67")
    if any(_action_metadata_missing(action) for action in file_actions):
        blockers.append("file_action_metadata_incomplete")
    clean = _as_mapping(plan.get("clean_fresh_candidate_projection"))
    clean_validation = validate_clean_candidate_projection(clean, file_actions)
    if not clean_validation["valid"]:
        blockers.extend(clean_validation["blockers"])
    evidence = _as_mapping(plan.get("qualification_evidence"))
    if not _as_mapping(evidence.get("full_materialization")).get("valid"):
        blockers.append("full_materialization_not_proven")
    if not _as_mapping(evidence.get("offline_nonmutation")).get("valid"):
        blockers.append("offline_validation_nonmutating_not_proven")
    if int(clean.get("runtime_artifact_count") or 0) != 0:
        blockers.append("runtime_artifacts_prestart_nonzero")
    if int(clean.get("unknown_entry_count") or 0) != 0:
        blockers.append("unknown_entries_prestart_nonzero")
    if clean.get("unexpected_entries"):
        blockers.append("unexpected_entries_prestart_nonzero")
    cutover_actions = [action for action in plan.get("cutover_actions") or [] if isinstance(action, Mapping)]
    if [str(action.get("operation") or "") for action in cutover_actions] != V6_REQUIRED_CUTOVER_OPERATIONS:
        blockers.append("cutover_action_order_invalid")
    action_ids = [str(action.get("action_id") or "") for action in file_actions + cutover_actions]
    if len(action_ids) != len(set(action_ids)):
        blockers.append("duplicate_action_ids")
    if list(plan.get("exact_requested_action_ids") or []) != action_ids:
        blockers.append("exact_requested_action_ids_mismatch")
    launch_validation = validate_production_launch_authority_v1(_as_mapping(plan.get("production_launch_authority")))
    if not launch_validation["valid"]:
        blockers.append("production_launch_authority_invalid")
    permissions = _as_mapping(plan.get("requested_permissions"))
    for forbidden in ("sigkill", "delete", "invoke", "provider", "p2s", "first_cycle"):
        if permissions.get(forbidden):
            blockers.append(f"forbidden_permission:{forbidden}")
    if not permissions.get("irreversible_source_loss_acknowledgement"):
        blockers.append("irreversible_ack_missing")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_loss_recovery_plan_v6_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "exact_action_count": len(action_ids),
        "file_action_count": len(file_actions),
        "cutover_action_count": len(cutover_actions),
        "clean_projection_valid": clean_validation["valid"],
        "offline_validation_nonmutating": bool(_as_mapping(evidence.get("offline_nonmutation")).get("valid")),
        "full_materialization_pass": bool(_as_mapping(evidence.get("full_materialization")).get("valid")),
        "fresh_candidate_path": plan.get("fresh_cutover_candidate_path", ""),
        "archive_path": plan.get("archive_path", ""),
    }


def build_source_loss_cutover_approval_request_v6(plan: Mapping[str, Any]) -> dict[str, Any]:
    request: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_cutover_approval_request_v6",
        "request_id": stable_id("source_loss_cutover_request_v6", str(plan.get("canonical_sha256") or "")),
        "status": "awaiting_machine_approval",
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("canonical_sha256"),
        "source_provenance_sha256": plan.get("source_provenance_sha256"),
        "precutover_canary_closeout_sha256": plan.get("precutover_canary_closeout_sha256"),
        "environment_profile_sha256": plan.get("environment_profile_sha256"),
        "equivalence_result_sha256": plan.get("equivalence_result_sha256"),
        "canonical_target_path": plan.get("canonical_target_path"),
        "canonical_full_tree_descriptor": plan.get("canonical_full_tree_descriptor"),
        "clean_fresh_candidate_path": plan.get("clean_fresh_candidate_path"),
        "clean_fresh_candidate_projection": plan.get("clean_fresh_candidate_projection"),
        "poststart_runtime_artifact_policy_sha256": _as_mapping(plan.get("poststart_runtime_artifact_policy")).get("canonical_sha256"),
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


def validate_source_loss_cutover_approval_request_v6(request: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if request.get("schema_version") != "agent_sync_source_loss_cutover_approval_request_v6":
        blockers.append("schema_version_not_v6_request")
    if request.get("status") != "awaiting_machine_approval":
        blockers.append("request_not_awaiting_machine_approval")
    if request.get("approval_id") or request.get("approved_at"):
        blockers.append("approval_fields_must_be_empty")
    if request.get("plan_sha256") != plan.get("canonical_sha256"):
        blockers.append("plan_hash_mismatch")
    if list(request.get("requested_action_ids") or []) != list(plan.get("exact_requested_action_ids") or []):
        blockers.append("requested_action_ids_mismatch")
    if _as_mapping(request.get("permissions")).get("sigkill"):
        blockers.append("sigkill_forbidden")
    if _as_mapping(request.get("endpoint_scopes")).get("invoke") or _as_mapping(request.get("endpoint_scopes")).get("provider"):
        blockers.append("forbidden_endpoint_scope")
    if str(request.get("canonical_sha256") or "") != canonical_sha256(request):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_loss_cutover_approval_request_v6_validation",
        "valid": not blockers,
        "blockers": blockers,
        "request_id": request.get("request_id", ""),
        "request_sha256": request.get("canonical_sha256", ""),
    }


def build_full_p2s_rebase_plan_v6(recovery_v6: Mapping[str, Any]) -> dict[str, Any]:
    p2s = build_full_p2s_rebase_plan_v5(
        {
            **dict(recovery_v6),
            "fresh_candidate_expected_source_descriptor": _as_mapping(recovery_v6.get("clean_fresh_candidate_projection")).get("source_descriptor"),
        }
    )
    p2s["schema_version"] = "agent_sync_full_p2s_rebase_plan_v6"
    p2s["tool_version"] = R6X_TOOL_VERSION
    p2s["recovery_plan_gate"]["recovery_schema_version"] = "agent_sync_source_loss_recovery_plan_v6"
    p2s["recovery_plan_gate"]["recovery_plan_id"] = recovery_v6.get("plan_id")
    p2s["recovery_plan_gate"]["recovery_plan_sha256"] = recovery_v6.get("canonical_sha256")
    p2s["canonical_sha256"] = ""
    p2s["canonical_sha256"] = canonical_sha256(p2s)
    return p2s


def validate_full_p2s_rebase_plan_v6(plan: Mapping[str, Any]) -> dict[str, Any]:
    shim = dict(plan)
    shim["schema_version"] = "agent_sync_full_p2s_rebase_plan_v5"
    shim["recovery_plan_gate"] = {
        **dict(_as_mapping(plan.get("recovery_plan_gate"))),
        "recovery_schema_version": "agent_sync_source_loss_recovery_plan_v5",
    }
    shim["canonical_sha256"] = canonical_sha256(shim)
    base = validate_full_p2s_rebase_plan_v5(shim)
    blockers = list(base["blockers"])
    if plan.get("schema_version") != "agent_sync_full_p2s_rebase_plan_v6":
        blockers.append("schema_version_not_v6")
    if _as_mapping(plan.get("recovery_plan_gate")).get("recovery_schema_version") != "agent_sync_source_loss_recovery_plan_v6":
        blockers.append("recovery_gate_not_v6")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_full_p2s_rebase_plan_v6_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "physical_action_count": base["physical_action_count"],
        "projected_file_count": base["projected_file_count"],
        "risk_fraud_projected_file_count": base["risk_fraud_projected_file_count"],
    }


def build_full_p2s_stage_request_v6(p2s_v6: Mapping[str, Any]) -> dict[str, Any]:
    request = build_full_p2s_stage_request_v5(p2s_v6)
    request["schema_version"] = "agent_sync_full_p2s_stage_request_v6"
    request["request_id"] = stable_id("p2s_stage_request_v6", str(p2s_v6.get("canonical_sha256") or ""))
    request["canonical_sha256"] = ""
    request["canonical_sha256"] = canonical_sha256(request)
    return request


def build_full_p2s_activation_template_v6(p2s_v6: Mapping[str, Any]) -> dict[str, Any]:
    template = build_full_p2s_activation_template_v5(p2s_v6)
    template["schema_version"] = "agent_sync_full_p2s_activation_template_v6"
    template["request_id"] = stable_id("p2s_activation_template_v6", str(p2s_v6.get("canonical_sha256") or ""))
    template["canonical_sha256"] = ""
    template["canonical_sha256"] = canonical_sha256(template)
    return template


def build_projected_experiment_v6(selected: Mapping[str, Any], p2s_v6: Mapping[str, Any]) -> dict[str, Any]:
    from react_agent.ops.sync_5a_r5x import build_projected_experiment_v5

    experiment = build_projected_experiment_v5(selected, p2s_v6)
    experiment["schema_version"] = "agent_sync_projected_experiment_manifest_v6"
    experiment["status"] = "blocked_pending_p2s_activation_closeout"
    experiment["canonical_sha256"] = ""
    experiment["canonical_sha256"] = canonical_sha256(experiment)
    return experiment


def build_first_real_cycle_plan_v6(selected: Mapping[str, Any], experiment_v6: Mapping[str, Any], p2s_v6: Mapping[str, Any]) -> dict[str, Any]:
    from react_agent.ops.sync_5a_r5x import build_first_real_cycle_plan_v5

    cycle = build_first_real_cycle_plan_v5(selected, experiment_v6, p2s_v6)
    cycle["schema_version"] = "agent_sync_first_real_cycle_plan_v6"
    cycle["status"] = "blocked_pending_experiment_validation"
    cycle["canonical_sha256"] = ""
    cycle["canonical_sha256"] = canonical_sha256(cycle)
    return cycle


def build_conditional_approval_chain_v6(
    *,
    canary_closeout: Mapping[str, Any],
    recovery_v6: Mapping[str, Any],
    p2s_v6: Mapping[str, Any],
    experiment_v6: Mapping[str, Any],
    cycle_v6: Mapping[str, Any],
) -> dict[str, Any]:
    chain: dict[str, Any] = {
        "schema_version": "agent_sync_conditional_approval_chain_v6",
        "chain_id": stable_id("approval_chain_v6", str(canary_closeout.get("canonical_sha256") or ""), str(recovery_v6.get("canonical_sha256") or "")),
        "supersedes": ["agent_sync_conditional_approval_chain_v5"],
        "broad_preapproval_forbidden": True,
        "nodes": [
            {"node": "precutover_canary", "status": "executed_and_closed", "closeout_sha256": canary_closeout.get("canonical_sha256")},
            {
                "node": "source_loss_cutover_v6",
                "status": "awaiting_machine_approval",
                "plan_id": recovery_v6.get("plan_id"),
                "plan_sha256": recovery_v6.get("canonical_sha256"),
                "binds_previous_closeout_sha256": canary_closeout.get("canonical_sha256"),
            },
            {"node": "recovery_settle", "status": "blocked_pending_real_cutover_closeout"},
            {"node": "p2s_stage_verify_v6", "status": "blocked_pending_recovery_settle", "plan_id": p2s_v6.get("plan_id"), "plan_sha256": p2s_v6.get("canonical_sha256")},
            {"node": "p2s_activate_rollback_v6", "status": "blocked_pending_real_stage_closeout", "plan_id": p2s_v6.get("plan_id"), "plan_sha256": p2s_v6.get("canonical_sha256")},
            {"node": "experiment_materialization_v6", "status": "blocked_pending_p2s_activation_closeout", "experiment_id": experiment_v6.get("experiment_id"), "experiment_sha256": experiment_v6.get("canonical_sha256")},
            {"node": "first_nonzero_cycle_v6", "status": "blocked_pending_experiment_validation", "cycle_id": cycle_v6.get("cycle_id"), "cycle_sha256": cycle_v6.get("canonical_sha256")},
        ],
        "canonical_sha256": "",
    }
    chain["canonical_sha256"] = canonical_sha256(chain)
    return chain


def validate_conditional_approval_chain_v6(chain: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    expected = [
        "executed_and_closed",
        "awaiting_machine_approval",
        "blocked_pending_real_cutover_closeout",
        "blocked_pending_recovery_settle",
        "blocked_pending_real_stage_closeout",
        "blocked_pending_p2s_activation_closeout",
        "blocked_pending_experiment_validation",
    ]
    nodes = [node for node in chain.get("nodes") or [] if isinstance(node, Mapping)]
    if [node.get("status") for node in nodes] != expected:
        blockers.append("approval_chain_status_order_invalid")
    if not chain.get("broad_preapproval_forbidden"):
        blockers.append("broad_preapproval_not_forbidden")
    if str(chain.get("canonical_sha256") or "") != canonical_sha256(chain):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_conditional_approval_chain_v6_validation",
        "valid": not blockers,
        "blockers": blockers,
        "chain_id": chain.get("chain_id", ""),
        "chain_sha256": chain.get("canonical_sha256", ""),
    }


def build_v6_projection_bundle(
    *,
    final_head: str,
    precutover_closeout: Mapping[str, Any],
    runtime_identity: Mapping[str, Any],
    qualification_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    selected = reselect_first_candidate()["selected_candidate"]
    recovery = build_source_loss_recovery_plan_v6(
        final_head=final_head,
        precutover_closeout=precutover_closeout,
        runtime_identity=runtime_identity,
        qualification_evidence=qualification_evidence,
    )
    request = build_source_loss_cutover_approval_request_v6(recovery)
    p2s = build_full_p2s_rebase_plan_v6(recovery)
    stage = build_full_p2s_stage_request_v6(p2s)
    activation = build_full_p2s_activation_template_v6(p2s)
    experiment = build_projected_experiment_v6(selected, p2s)
    cycle = build_first_real_cycle_plan_v6(selected, experiment, p2s)
    chain = build_conditional_approval_chain_v6(
        canary_closeout=precutover_closeout,
        recovery_v6=recovery,
        p2s_v6=p2s,
        experiment_v6=experiment,
        cycle_v6=cycle,
    )
    return {
        "source_loss_recovery_plan_v6": recovery,
        "source_loss_cutover_approval_request_v6": request,
        "full_p2s_rebase_plan_v6": p2s,
        "full_p2s_stage_request_v6": stage,
        "full_p2s_activation_template_v6": activation,
        "selected_change_unit_v6": selected,
        "projected_experiment_v6": experiment,
        "first_real_cycle_plan_v6": cycle,
        "conditional_approval_chain_v6": chain,
    }


def validate_portable_archive_entries(entry_names: Iterable[str]) -> dict[str, Any]:
    names = list(entry_names)
    normalized: list[str] = []
    blockers: list[str] = []
    for name in names:
        if "\\" in name:
            blockers.append(f"backslash_entry:{name}")
        path = PurePosixPath(name.replace("\\", "/"))
        if path.is_absolute():
            blockers.append(f"absolute_entry:{name}")
        if any(part in {"..", ""} for part in path.parts):
            blockers.append(f"traversal_entry:{name}")
        if "temp_source_loss_fixture" in path.parts or any(part.startswith("lma-r6x-materialize") for part in path.parts):
            blockers.append(f"raw_temp_fixture_entry:{name}")
        if "risk_financial_fraud" in path.parts and ("app" in path.parts or "tests" in path.parts):
            blockers.append(f"raw_source_entry:{name}")
        normalized.append(path.as_posix())
    duplicates = sorted(name for name, count in Counter(normalized).items() if count > 1)
    blockers.extend(f"duplicate_normalized_entry:{name}" for name in duplicates)
    return {
        "schema_version": "agent_sync_archive_portability_result_v1",
        "entry_count": len(names),
        "backslash_entry_count": sum(1 for name in names if "\\" in name),
        "raw_temp_fixture_entry_count": sum(1 for name in names if "temp_source_loss_fixture" in name or "lma-r6x-materialize" in name),
        "raw_source_entry_count": sum(1 for name in normalized if "risk_financial_fraud/app/" in name or "risk_financial_fraud/tests/" in name),
        "absolute_entry_count": sum(1 for name in names if PurePosixPath(name.replace("\\", "/")).is_absolute()),
        "traversal_entry_count": sum(1 for name in names if ".." in PurePosixPath(name.replace("\\", "/")).parts),
        "duplicate_normalized_entry_count": len(duplicates),
        "symlink_entry_count": 0,
        "valid": not blockers,
        "blockers": blockers,
        "canonical_sha256": "",
    }


def build_real_readonly_preflight_v6(
    *,
    expected_runtime_identity: Mapping[str, Any],
    recovery_v6: Mapping[str, Any],
) -> dict[str, Any]:
    preflight = build_real_readonly_preflight(expected_runtime_identity=expected_runtime_identity, recovery_v5=recovery_v6)
    preflight["schema_version"] = "agent_sync_real_readonly_source_loss_preflight_v6"
    preflight["listener_11013"] = port_listening(11013)
    preflight["frozen_source_descriptor"] = _source_descriptor(RISK_FRAUD_HISTORICAL_ROOT)
    preflight["frozen_source_descriptor_matches"] = preflight["frozen_source_descriptor"].get("digest") == EXPECTED_SOURCE_DESCRIPTOR_DIGEST
    preflight["source_provenance_sha256"] = build_source_package_provenance(RISK_FRAUD_HISTORICAL_ROOT)["canonical_sha256"]
    preflight["source_provenance_matches"] = preflight["source_provenance_sha256"] == EXPECTED_SOURCE_PROVENANCE_SHA256
    preflight["real_fresh_candidate_writes"] = 0
    preflight["endpoint_calls"] = 0
    preflight["process_actions"] = 0
    preflight["canonical_writes"] = 0
    preflight["valid"] = bool(preflight.get("valid")) and not preflight["listener_11013"] and preflight["frozen_source_descriptor_matches"] and preflight["source_provenance_matches"]
    preflight["canonical_sha256"] = canonical_sha256(preflight)
    return preflight
