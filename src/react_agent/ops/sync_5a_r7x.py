# ruff: noqa: D101, D102, D103
"""SYNC-OPS-5A-R7X physical tree parity contracts."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from react_agent.ops.sync_5a_r1x import (
    RISK_FRAUD_AGENT_ID,
    RISK_FRAUD_HISTORICAL_ROOT,
    RISK_FRAUD_PROD_ROOT,
)
from react_agent.ops.sync_5a_r2x import expires_utc, now_utc
from react_agent.ops.sync_5a_r3x import build_source_package_provenance
from react_agent.ops.sync_5a_r5x import (
    PRODUCTION_PORT,
    R4X_CANARY_PATH,
    build_cutover_tree_descriptor,
    build_production_launch_authority_v1,
    build_real_readonly_preflight,
    build_source_loss_failure_policy_v5,
    build_source_loss_state_machine_v5,
    port_listening,
)
from react_agent.ops.sync_5a_r6x import (
    EXPECTED_SOURCE_DESCRIPTOR_DIGEST,
    EXPECTED_SOURCE_PROVENANCE_SHA256,
    V6_REQUIRED_CUTOVER_OPERATIONS,
    build_full_p2s_activation_template_v6,
    build_full_p2s_rebase_plan_v6,
    build_full_p2s_stage_request_v6,
    build_poststart_runtime_artifact_policy,
    build_projected_experiment_v6,
    build_source_action_metadata_ledger,
    validate_full_p2s_rebase_plan_v6,
    validate_source_loss_recovery_plan_v6,
)
from react_agent.ops.sync_contracts import canonical_sha256, file_sha256, stable_id
from react_agent.ops.sync_inventory import inventory_root
from react_agent.ops.sync_s2p import descriptor_from_inventory
from react_agent.ops.sync_security import (
    classify_file_type,
    normalize_safe_relative_path,
    validate_root_containment,
)

R7X_TOOL_VERSION = "sync_ops_5a_r7x_cutover_tree_digest_parity"
R7X_MATERIALIZER_VERSION = "source_loss_candidate_materializer_v2"
R6X_SUPERSESSION_REASON = "superseded_due_projection_materialization_digest_parity_failure"
R6X_PLAN_ID = "source_loss_recovery_v6_21987ac1d94c"
R6X_PLAN_SHA256 = "69e0483ceaef8bda0f69fcb4600fc70d75dd26f0425d0f4714cf79a6512d53b2"
R6X_PROJECTION_DIGEST = "04e9da04599ad91422df55c7fc321f012567fd0ec392caeeb62b0c588f2e5e00"
R6X_ACTUAL_MATERIALIZED_DIGEST = "f87e62ec18b6e2dbfc304dda47c14608fd1e7eda54d728ca5b70571f8785e203"


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mode(path: Path) -> str:
    return oct(stat.S_IMODE(path.lstat().st_mode))


def _source_descriptor(source_root: Path = RISK_FRAUD_HISTORICAL_ROOT) -> dict[str, Any]:
    return descriptor_from_inventory(
        inventory_root(RISK_FRAUD_AGENT_ID, source_root, root_role="source_loss_recovery_package"),
        scope="transaction_source_tree",
    )


def _clean_parent_dirs(actions: Sequence[Mapping[str, Any]]) -> list[str]:
    parents: set[str] = set()
    for action in actions:
        rel = normalize_safe_relative_path(str(action.get("relative_path") or ""))
        path = Path(rel)
        for parent in path.parents:
            text = parent.as_posix()
            if text and text != ".":
                parents.add(text)
    return sorted(parents)


def _physical_entry_digest(entries: Sequence[Mapping[str, Any]]) -> str:
    payload = [
        {
            "relative_path": entry["relative_path"],
            "entry_type": entry["entry_type"],
            "content_sha256": entry.get("content_sha256", ""),
            "mode": entry["mode"],
            "executable": bool(entry["executable"]),
            "safe_symlink_target": entry.get("safe_symlink_target", ""),
        }
        for entry in sorted(entries, key=lambda item: str(item["relative_path"]))
    ]
    return canonical_sha256(payload)


def _classification_digest(entries: Sequence[Mapping[str, Any]]) -> str:
    payload = [
        {
            "relative_path": entry["relative_path"],
            "classification": entry.get("classification", ""),
            "policy_rule": entry.get("policy_rule", ""),
        }
        for entry in sorted(entries, key=lambda item: str(item["relative_path"]))
    ]
    return canonical_sha256(payload)


def build_directory_mode_authority(
    *,
    file_actions: Sequence[Mapping[str, Any]],
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    canonical_root: Path = RISK_FRAUD_PROD_ROOT,
    canary_root: Path = R4X_CANARY_PATH,
) -> dict[str, Any]:
    parent_dirs = _clean_parent_dirs(file_actions)
    canonical_mode = _mode(canonical_root) if canonical_root.exists() else "0o775"
    source_root_mode = _mode(source_root)
    rows: list[dict[str, Any]] = [
        {
            "relative_path": ".",
            "source_mode": source_root_mode,
            "canonical_current_mode": canonical_mode,
            "candidate_pre_cutover_mode": canonical_mode,
            "canonical_post_cutover_mode": canonical_mode,
            "mode_transition_required": False,
            "reason": "root_uses_current_canonical_mode",
        }
    ]
    for rel in parent_dirs:
        source_mode = _mode(source_root / rel)
        rows.append(
            {
                "relative_path": rel,
                "source_mode": source_mode,
                "canonical_current_mode": "",
                "candidate_pre_cutover_mode": source_mode,
                "canonical_post_cutover_mode": source_mode,
                "mode_transition_required": False,
                "reason": "parent_directory_preserves_source_mode",
            }
        )
    payload: dict[str, Any] = {
        "schema_version": "agent_sync_directory_mode_authority_v1",
        "canonical_root": str(canonical_root),
        "canonical_root_mode": canonical_mode,
        "prod_parent": str(canonical_root.parent),
        "prod_parent_mode": _mode(canonical_root.parent),
        "prod_parent_device": canonical_root.parent.stat().st_dev,
        "source_root": str(source_root),
        "source_root_mode": source_root_mode,
        "canary_root": str(canary_root),
        "canary_root_mode": _mode(canary_root) if canary_root.exists() else "",
        "directory_count_including_root": len(rows),
        "directories": rows,
        "hidden_candidate_pre_cutover_root_mode": canonical_mode,
        "production_canonical_post_cutover_root_mode": canonical_mode,
        "root_mode_transition_required": False,
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def build_directory_action_ledger(plan_id: str, mode_authority: Mapping[str, Any]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    for row in mode_authority.get("directories") or []:
        if not isinstance(row, Mapping):
            continue
        rel = normalize_safe_relative_path(str(row.get("relative_path") or ".").replace(".", "__root__")) if row.get("relative_path") != "." else "."
        action = {
            "action_id": stable_id(
                "slrv7_dir",
                plan_id,
                str(row.get("relative_path") or ""),
                str(row.get("candidate_pre_cutover_mode") or ""),
                str(row.get("canonical_post_cutover_mode") or ""),
            ),
            "operation": "create_candidate_directory",
            "relative_path": "." if rel == "." else normalize_safe_relative_path(rel),
            "expected_before_state": "missing",
            "candidate_pre_cutover_mode": row.get("candidate_pre_cutover_mode"),
            "canonical_post_cutover_mode": row.get("canonical_post_cutover_mode"),
            "mode_transition_required": bool(row.get("mode_transition_required", False)),
            "follow_symlink": False,
            "hardlink_allowed": False,
            "classification": "root_directory" if row.get("relative_path") == "." else "directory",
            "policy_rule": str(row.get("reason") or ""),
        }
        action["action_semantics_sha256"] = action_semantics_sha256(action)
        actions.append(action)
    payload: dict[str, Any] = {
        "schema_version": "agent_sync_directory_action_ledger_v1",
        "plan_id": plan_id,
        "action_count": len(actions),
        "actions": actions,
        "root_action_count": sum(1 for action in actions if action["relative_path"] == "."),
        "parent_directory_action_count": sum(1 for action in actions if action["relative_path"] != "."),
        "mode_transition_action_count": sum(1 for action in actions if action["mode_transition_required"]),
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def action_semantics_payload(action: Mapping[str, Any]) -> dict[str, Any]:
    operation = str(action.get("operation") or "")
    if operation == "create_candidate_directory":
        return {
            "operation": operation,
            "relative_path": action.get("relative_path"),
            "expected_destination_type": "directory",
            "candidate_pre_cutover_mode": action.get("candidate_pre_cutover_mode"),
            "canonical_post_cutover_mode": action.get("canonical_post_cutover_mode"),
            "mode_transition_required": bool(action.get("mode_transition_required", False)),
            "classification": action.get("classification"),
            "policy_rule": action.get("policy_rule"),
            "follow_symlink": bool(action.get("follow_symlink", True)),
            "hardlink_allowed": bool(action.get("hardlink_allowed", True)),
        }
    return {
        "operation": operation,
        "source_sha256": action.get("source_sha256"),
        "source_file_type": action.get("source_file_type"),
        "source_mode": action.get("source_mode"),
        "source_executable": bool(action.get("source_executable", False)),
        "relative_path": action.get("relative_path"),
        "expected_destination_type": action.get("expected_destination_type"),
        "expected_destination_mode": action.get("expected_destination_mode"),
        "classification": action.get("classification"),
        "policy_rule": action.get("policy_rule", "source_file_action"),
        "follow_symlink": bool(action.get("follow_symlink", True)),
        "hardlink_allowed": bool(action.get("hardlink_allowed", True)),
    }


def action_semantics_sha256(action: Mapping[str, Any]) -> str:
    return canonical_sha256(action_semantics_payload(action))


def add_file_action_semantics(actions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for action in actions:
        item = dict(action)
        item["policy_rule"] = "source_file_action"
        item["action_semantics_sha256"] = action_semantics_sha256(item)
        enriched.append(item)
    return enriched


def physical_entry_manifest_from_actions(
    *,
    directory_actions: Sequence[Mapping[str, Any]],
    file_actions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for action in directory_actions:
        rel = str(action.get("relative_path") or "")
        entries.append(
            {
                "relative_path": rel,
                "entry_type": "root_directory" if rel == "." else "directory",
                "content_sha256": "",
                "mode": action.get("candidate_pre_cutover_mode"),
                "executable": True,
                "safe_symlink_target": "",
                "classification": action.get("classification"),
                "policy_rule": action.get("policy_rule"),
            }
        )
    for action in file_actions:
        entries.append(
            {
                "relative_path": action.get("relative_path"),
                "entry_type": "regular",
                "content_sha256": action.get("source_sha256"),
                "mode": action.get("expected_destination_mode"),
                "executable": bool(action.get("source_executable", False)),
                "safe_symlink_target": "",
                "classification": action.get("classification"),
                "policy_rule": action.get("policy_rule", "source_file_action"),
            }
        )
    manifest: dict[str, Any] = {
        "schema_version": "agent_sync_cutover_entry_manifest_v1",
        "entry_count": len(entries),
        "entries": sorted(entries, key=lambda item: str(item["relative_path"])),
        "physical_tree_digest": _physical_entry_digest(entries),
        "classification_manifest_sha256": _classification_digest(entries),
        "canonical_sha256": "",
    }
    manifest["canonical_sha256"] = canonical_sha256(manifest)
    return manifest


def build_physical_tree_descriptor_v2(manifest: Mapping[str, Any]) -> dict[str, Any]:
    entries = [entry for entry in manifest.get("entries") or [] if isinstance(entry, Mapping)]
    descriptor: dict[str, Any] = {
        "schema_version": "agent_sync_cutover_physical_tree_descriptor_v2",
        "algorithm": "sha256",
        "scope": "source_loss_cutover_physical_tree",
        "entry_contract_version": "cutover_physical_entry_v2",
        "root_relative_entry": ".",
        "physical_tree_digest": manifest.get("physical_tree_digest"),
        "classification_manifest_sha256": manifest.get("classification_manifest_sha256"),
        "entry_count": len(entries),
        "regular_file_count": sum(1 for entry in entries if entry.get("entry_type") == "regular"),
        "directory_count_including_root": sum(1 for entry in entries if entry.get("entry_type") in {"root_directory", "directory"}),
        "symlink_count": sum(1 for entry in entries if entry.get("entry_type") == "symlink"),
        "special_file_count": sum(1 for entry in entries if entry.get("entry_type") == "special"),
        "canonical_sha256": "",
    }
    descriptor["canonical_sha256"] = canonical_sha256(descriptor)
    return descriptor


def materialize_candidate_v2(root: Path, directory_actions: Sequence[Mapping[str, Any]], file_actions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    if root.exists():
        blockers.append("candidate_root_already_exists")
    copied = 0
    if not blockers:
        root.mkdir(parents=True, exist_ok=False)
        for action in sorted(directory_actions, key=lambda item: str(item.get("relative_path") or "")):
            rel = str(action.get("relative_path") or "")
            target = root if rel == "." else root / normalize_safe_relative_path(rel)
            validate_root_containment(root, target)
            target.mkdir(parents=True, exist_ok=True)
            os.chmod(target, int(str(action.get("candidate_pre_cutover_mode") or "0o755"), 8), follow_symlinks=False)
        for action in sorted(file_actions, key=lambda item: str(item.get("relative_path") or "")):
            rel = normalize_safe_relative_path(str(action.get("relative_path") or ""))
            src = Path(str(action.get("source_path") or ""))
            dest = root / rel
            validate_root_containment(root, dest)
            st = src.lstat()
            if classify_file_type(st.st_mode) != "regular" or src.is_symlink():
                blockers.append(f"source_not_regular:{rel}")
                continue
            if file_sha256(src) != action.get("source_sha256"):
                blockers.append(f"source_sha_mismatch:{rel}")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest, follow_symlinks=False)
            os.chmod(dest, int(str(action.get("expected_destination_mode") or "0o644"), 8), follow_symlinks=False)
            if dest.lstat().st_nlink != 1:
                blockers.append(f"hardlink_detected:{rel}")
            copied += 1
    return {
        "schema_version": "agent_sync_candidate_materializer_v2_result",
        "materializer_version": R7X_MATERIALIZER_VERSION,
        "candidate_root": str(root),
        "directory_action_count": len(directory_actions),
        "file_action_count": len(file_actions),
        "copied_file_count": copied,
        "blockers": blockers,
        "valid": not blockers and copied == len(file_actions) == 67 and len(directory_actions) == 11,
    }


def actual_physical_entry_manifest(root: Path, expected_manifest: Mapping[str, Any]) -> dict[str, Any]:
    expected_by_path = {str(entry.get("relative_path")): entry for entry in expected_manifest.get("entries") or [] if isinstance(entry, Mapping)}
    entries: list[dict[str, Any]] = []
    if root.exists():
        for path in sorted([root, *root.rglob("*")], key=lambda item: "" if item == root else normalize_safe_relative_path(item.relative_to(root))):
            st = path.lstat()
            rel = "." if path == root else normalize_safe_relative_path(path.relative_to(root))
            file_type = classify_file_type(st.st_mode)
            entry_type = "root_directory" if rel == "." else "directory" if file_type == "directory" else file_type if file_type in {"regular", "symlink"} else "special"
            content_sha = file_sha256(path) if entry_type == "regular" else ""
            expected = expected_by_path.get(rel, {})
            entries.append(
                {
                    "relative_path": rel,
                    "entry_type": entry_type,
                    "content_sha256": content_sha,
                    "mode": oct(stat.S_IMODE(st.st_mode)),
                    "executable": bool(st.st_mode & stat.S_IXUSR),
                    "safe_symlink_target": "",
                    "classification": expected.get("classification", "unknown_blocked"),
                    "policy_rule": expected.get("policy_rule", "actual_entry"),
                }
            )
    manifest: dict[str, Any] = {
        "schema_version": "agent_sync_cutover_entry_manifest_v1",
        "entry_count": len(entries),
        "entries": sorted(entries, key=lambda item: str(item["relative_path"])),
        "physical_tree_digest": _physical_entry_digest(entries),
        "classification_manifest_sha256": _classification_digest(entries),
        "canonical_sha256": "",
    }
    manifest["canonical_sha256"] = canonical_sha256(manifest)
    return manifest


def diff_entry_manifests(projected: Mapping[str, Any], actual: Mapping[str, Any]) -> dict[str, Any]:
    projected_entries = {str(entry.get("relative_path")): entry for entry in projected.get("entries") or [] if isinstance(entry, Mapping)}
    actual_entries = {str(entry.get("relative_path")): entry for entry in actual.get("entries") or [] if isinstance(entry, Mapping)}
    only_projected = sorted(set(projected_entries) - set(actual_entries))
    only_actual = sorted(set(actual_entries) - set(projected_entries))
    type_mismatch = []
    content_mismatch = []
    mode_mismatch = []
    executable_mismatch = []
    classification_mismatch = []
    for rel in sorted(set(projected_entries) & set(actual_entries)):
        p = projected_entries[rel]
        a = actual_entries[rel]
        if p.get("entry_type") != a.get("entry_type"):
            type_mismatch.append(rel)
        if p.get("content_sha256") != a.get("content_sha256"):
            content_mismatch.append(rel)
        if p.get("mode") != a.get("mode"):
            mode_mismatch.append(rel)
        if bool(p.get("executable")) != bool(a.get("executable")):
            executable_mismatch.append(rel)
        if p.get("classification") != a.get("classification"):
            classification_mismatch.append(rel)
    payload = {
        "schema_version": "agent_sync_projection_materialization_entry_diff_v1",
        "only_in_projection": only_projected,
        "only_in_actual": only_actual,
        "type_mismatch": type_mismatch,
        "content_mismatch": content_mismatch,
        "mode_mismatch": mode_mismatch,
        "executable_mismatch": executable_mismatch,
        "classification_mismatch": classification_mismatch,
        "physical_tree_digest_match": projected.get("physical_tree_digest") == actual.get("physical_tree_digest"),
        "classification_manifest_match": projected.get("classification_manifest_sha256") == actual.get("classification_manifest_sha256"),
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def run_offline_validation_physical_parity(root: Path, expected_manifest: Mapping[str, Any], *, include_pytest: bool = True) -> dict[str, Any]:
    before = actual_physical_entry_manifest(root, expected_manifest)
    temp_root = Path(tempfile.mkdtemp(prefix="lma-r7x-validation-cache-", dir="/tmp"))
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
    commands: list[list[str]] = []
    py_files = sorted(str(path.relative_to(root)) for path in root.rglob("*.py"))
    if py_files:
        commands.append([sys.executable, "-m", "py_compile", *py_files])
    tests = [path for path in ("tests/test_report_material.py", "tests/test_compute_core.py", "tests/test_protocol_contract.py") if (root / path).exists()]
    if include_pytest and tests:
        commands.append([sys.executable, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider", "--basetemp", str(temp_root / "pytest-basetemp")])
    results = []
    for command in commands:
        result = subprocess.run(command, cwd=root, env=env, check=False, capture_output=True, text=True)
        results.append({"argv_summary": [Path(command[0]).name, *command[1:3]], "returncode": result.returncode})
    after = actual_physical_entry_manifest(root, expected_manifest)
    payload = {
        "schema_version": "agent_sync_offline_validation_physical_parity_v1",
        "before_physical_tree_digest": before["physical_tree_digest"],
        "after_physical_tree_digest": after["physical_tree_digest"],
        "before_classification_manifest_sha256": before["classification_manifest_sha256"],
        "after_classification_manifest_sha256": after["classification_manifest_sha256"],
        "command_results": results,
        "hard_failure_count": sum(1 for item in results if item["returncode"] != 0),
        "physical_tree_unchanged": before["physical_tree_digest"] == after["physical_tree_digest"],
        "classification_manifest_unchanged": before["classification_manifest_sha256"] == after["classification_manifest_sha256"],
        "valid": before["physical_tree_digest"] == after["physical_tree_digest"]
        and before["classification_manifest_sha256"] == after["classification_manifest_sha256"]
        and all(item["returncode"] == 0 for item in results),
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def build_action_semantics_binding(
    *,
    rehearsal_directory_actions: Sequence[Mapping[str, Any]],
    rehearsal_file_actions: Sequence[Mapping[str, Any]],
    final_directory_actions: Sequence[Mapping[str, Any]],
    final_file_actions: Sequence[Mapping[str, Any]],
    approved_real_root: Path,
    temp_root: Path,
) -> dict[str, Any]:
    rehearsal_actions = [*rehearsal_directory_actions, *rehearsal_file_actions]
    final_actions = [*final_directory_actions, *final_file_actions]
    rehearsal_by_sem = {str(action.get("action_semantics_sha256")): action for action in rehearsal_actions}
    final_by_sem = {str(action.get("action_semantics_sha256")): action for action in final_actions}
    pairs = []
    for semantics in sorted(set(rehearsal_by_sem) & set(final_by_sem)):
        pairs.append(
            {
                "action_semantics_sha256": semantics,
                "rehearsal_action_id": rehearsal_by_sem[semantics].get("action_id"),
                "final_action_id": final_by_sem[semantics].get("action_id"),
                "relative_path": final_by_sem[semantics].get("relative_path"),
                "operation": final_by_sem[semantics].get("operation"),
            }
        )
    blockers = []
    if set(rehearsal_by_sem) != set(final_by_sem):
        blockers.append("action_semantics_set_mismatch")
    payload = {
        "schema_version": "agent_sync_action_semantics_binding_v1",
        "simulation_root_mapping": {"approved_real_root": str(approved_real_root), "temp_root": str(temp_root)},
        "rehearsal_action_count": len(rehearsal_actions),
        "final_action_count": len(final_actions),
        "bound_action_count": len(pairs),
        "binding_pairs": pairs,
        "action_semantics_set_sha256": canonical_sha256(sorted(set(final_by_sem))),
        "valid": not blockers and len(pairs) == len(final_actions) == 78,
        "blockers": blockers,
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def run_full_67_exact_action_temp_rehearsal(
    *,
    final_plan: Mapping[str, Any],
    temp_root: Path,
    include_pytest: bool = False,
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
) -> dict[str, Any]:
    temp_candidate = temp_root / "candidate"
    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir(parents=True, exist_ok=False)
    provenance = build_source_package_provenance(source_root)
    rehearsal_plan_id = f"rehearsal_{final_plan.get('plan_id')}"
    rehearsal_file_ledger = build_source_action_metadata_ledger(
        plan_id=rehearsal_plan_id,
        source_root=source_root,
        candidate_path=temp_candidate,
        provenance=provenance,
    )
    rehearsal_file_actions = add_file_action_semantics(rehearsal_file_ledger["actions"])
    mode_authority = _as_mapping(final_plan.get("directory_mode_authority"))
    rehearsal_directory_ledger = build_directory_action_ledger(rehearsal_plan_id, mode_authority)
    final_directory_actions = [action for action in final_plan.get("directory_actions") or [] if isinstance(action, Mapping)]
    final_file_actions = [action for action in final_plan.get("file_actions") or [] if isinstance(action, Mapping)]
    expected_manifest = physical_entry_manifest_from_actions(
        directory_actions=final_directory_actions,
        file_actions=final_file_actions,
    )
    materialized = materialize_candidate_v2(
        temp_candidate,
        rehearsal_directory_ledger["actions"],
        rehearsal_file_actions,
    )
    actual_after_materialization = actual_physical_entry_manifest(temp_candidate, expected_manifest)
    entry_diff = diff_entry_manifests(expected_manifest, actual_after_materialization)
    offline = run_offline_validation_physical_parity(temp_candidate, expected_manifest, include_pytest=include_pytest)
    binding = build_action_semantics_binding(
        rehearsal_directory_actions=rehearsal_directory_ledger["actions"],
        rehearsal_file_actions=rehearsal_file_actions,
        final_directory_actions=final_directory_actions,
        final_file_actions=final_file_actions,
        approved_real_root=Path(str(final_plan.get("fresh_cutover_candidate_path") or "")),
        temp_root=temp_candidate,
    )
    valid = bool(
        materialized["valid"]
        and binding["valid"]
        and entry_diff["physical_tree_digest_match"]
        and entry_diff["classification_manifest_match"]
        and offline["valid"]
        and expected_manifest["physical_tree_digest"] == actual_after_materialization["physical_tree_digest"] == offline["after_physical_tree_digest"]
    )
    payload: dict[str, Any] = {
        "schema_version": "agent_sync_full_67_exact_action_temp_rehearsal_v1",
        "materializer_version": R7X_MATERIALIZER_VERSION,
        "final_plan_id": final_plan.get("plan_id"),
        "temp_root": str(temp_root),
        "temp_candidate": str(temp_candidate),
        "expected_entry_manifest": expected_manifest,
        "materialization_result": materialized,
        "actual_after_materialization_entry_manifest": actual_after_materialization,
        "entry_diff": entry_diff,
        "offline_validation_physical_parity": offline,
        "action_semantics_binding": binding,
        "expected_physical_tree_digest": expected_manifest["physical_tree_digest"],
        "actual_after_materialization_physical_tree_digest": actual_after_materialization["physical_tree_digest"],
        "actual_after_offline_validation_physical_tree_digest": offline["after_physical_tree_digest"],
        "classification_manifest_sha256": expected_manifest["classification_manifest_sha256"],
        "action_semantics_set_sha256": binding["action_semantics_set_sha256"],
        "valid": valid,
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def validate_source_loss_recovery_plan_v6_for_v7(v6_plan: Mapping[str, Any]) -> dict[str, Any]:
    base = validate_source_loss_recovery_plan_v6(v6_plan)
    blockers = [
        "projection_materialization_physical_digest_mismatch",
        "projection_and_inventory_digest_contract_mismatch",
        "directory_mode_contract_missing",
        "exact_rehearsal_action_binding_missing",
    ]
    return {
        "schema_version": "agent_sync_source_loss_recovery_plan_v6_v7_validation",
        "plan_id": v6_plan.get("plan_id", ""),
        "plan_sha256": v6_plan.get("canonical_sha256", ""),
        "v6_original_valid": base["valid"],
        "valid": False,
        "blockers": blockers,
    }


def build_source_loss_recovery_plan_v7(
    *,
    final_head: str,
    precutover_closeout: Mapping[str, Any],
    runtime_identity: Mapping[str, Any],
    rehearsal_evidence: Mapping[str, Any],
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    canonical_target: Path = RISK_FRAUD_PROD_ROOT,
) -> dict[str, Any]:
    provenance = build_source_package_provenance(source_root)
    seed = stable_id("source_loss_recovery_v7_seed", final_head, provenance["canonical_sha256"], str(precutover_closeout.get("canonical_sha256") or ""))
    fresh = canonical_target.parent / f".agent-sync-risk-fraud-cutover-{seed}"
    file_ledger = build_source_action_metadata_ledger(plan_id=seed, source_root=source_root, candidate_path=fresh, provenance=provenance)
    file_actions = add_file_action_semantics(file_ledger["actions"])
    mode_authority = build_directory_mode_authority(file_actions=file_actions, source_root=source_root, canonical_root=canonical_target)
    dir_ledger = build_directory_action_ledger(seed, mode_authority)
    projected_manifest = physical_entry_manifest_from_actions(directory_actions=dir_ledger["actions"], file_actions=file_actions)
    descriptor = build_physical_tree_descriptor_v2(projected_manifest)
    plan_id = stable_id(
        "source_loss_recovery_v7",
        final_head,
        provenance["canonical_sha256"],
        projected_manifest["physical_tree_digest"],
        projected_manifest["classification_manifest_sha256"],
        str(precutover_closeout.get("canonical_sha256") or ""),
    )
    fresh = canonical_target.parent / f".agent-sync-risk-fraud-cutover-{plan_id}"
    archive = canonical_target.parent / f".agent-sync-archive-risk-fraud-{plan_id}"
    file_ledger = build_source_action_metadata_ledger(plan_id=plan_id, source_root=source_root, candidate_path=fresh, provenance=provenance)
    file_actions = add_file_action_semantics(file_ledger["actions"])
    mode_authority = build_directory_mode_authority(file_actions=file_actions, source_root=source_root, canonical_root=canonical_target)
    dir_ledger = build_directory_action_ledger(plan_id, mode_authority)
    projected_manifest = physical_entry_manifest_from_actions(directory_actions=dir_ledger["actions"], file_actions=file_actions)
    descriptor = build_physical_tree_descriptor_v2(projected_manifest)
    launch = build_production_launch_authority_v1(
        plan_id=plan_id,
        environment_profile_sha256=str(precutover_closeout.get("environment_profile_sha256") or ""),
        canonical_target=canonical_target,
    )
    cutover_actions = [
        {"action_id": stable_id("slrv7_action", plan_id, operation), "operation": operation, "requires_machine_approval": True}
        for operation in V6_REQUIRED_CUTOVER_OPERATIONS
    ]
    state_machine = build_source_loss_state_machine_v5()
    state_machine["schema_version"] = "agent_sync_source_loss_state_machine_v7"
    state_machine["canonical_sha256"] = ""
    state_machine["canonical_sha256"] = canonical_sha256(state_machine)
    failure_policy = build_source_loss_failure_policy_v5()
    failure_policy["schema_version"] = "agent_sync_source_loss_failure_policy_v7"
    failure_policy["canonical_sha256"] = ""
    failure_policy["canonical_sha256"] = canonical_sha256(failure_policy)
    action_ids = [action["action_id"] for action in dir_ledger["actions"]] + [action["action_id"] for action in file_actions] + [action["action_id"] for action in cutover_actions]
    plan = {
        "schema_version": "agent_sync_source_loss_recovery_plan_v7",
        "tool_version": R7X_TOOL_VERSION,
        "materializer_version": R7X_MATERIALIZER_VERSION,
        "plan_id": plan_id,
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "final_head_sha256": final_head,
        "source_provenance_sha256": provenance["canonical_sha256"],
        "precutover_canary_closeout_sha256": precutover_closeout.get("canonical_sha256"),
        "environment_profile_sha256": precutover_closeout.get("environment_profile_sha256"),
        "equivalence_result_sha256": precutover_closeout.get("equivalence_result_sha256"),
        "incumbent_capture_sha256": precutover_closeout.get("incumbent_capture_sha256"),
        "incumbent_identity": dict(runtime_identity),
        "incumbent_port": PRODUCTION_PORT,
        "canonical_target_path": str(canonical_target),
        "canonical_full_tree_descriptor": build_cutover_tree_descriptor(canonical_target, root_role="canonical_target_before_cutover_v7"),
        "fresh_cutover_candidate_path": str(fresh),
        "archive_path": str(archive),
        "directory_mode_authority": mode_authority,
        "directory_action_ledger": dir_ledger,
        "directory_actions": dir_ledger["actions"],
        "file_actions": file_actions,
        "projected_candidate_entry_manifest": projected_manifest,
        "physical_tree_descriptor_v2": descriptor,
        "expected_physical_tree_digest": descriptor["physical_tree_digest"],
        "classification_manifest_sha256": descriptor["classification_manifest_sha256"],
        "poststart_runtime_artifact_policy": build_poststart_runtime_artifact_policy(_source_descriptor(source_root)),
        "production_launch_authority": launch,
        "production_launch_authority_sha256": launch["canonical_sha256"],
        "temp_exact_action_rehearsal_evidence": dict(rehearsal_evidence),
        "temp_exact_action_rehearsal_evidence_sha256": rehearsal_evidence.get("canonical_sha256"),
        "action_semantics_set_sha256": rehearsal_evidence.get("action_semantics_set_sha256"),
        "cutover_actions": cutover_actions,
        "exact_requested_action_ids": action_ids,
        "state_machine": state_machine,
        "failure_policy": failure_policy,
        "requested_permissions": {
            "candidate_materialization": True,
            "directory_creation": True,
            "file_materialization": True,
            "incumbent_sigterm": True,
            "recovered_production_start": True,
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
            "actual_physical_tree_digest_must_equal_projected": True,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_source_loss_recovery_plan_v7(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if plan.get("schema_version") != "agent_sync_source_loss_recovery_plan_v7":
        blockers.append("schema_version_not_v7")
    dir_actions = [action for action in plan.get("directory_actions") or [] if isinstance(action, Mapping)]
    file_actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    cutover_actions = [action for action in plan.get("cutover_actions") or [] if isinstance(action, Mapping)]
    if len(dir_actions) != 11:
        blockers.append("directory_action_count_not_11")
    if len(file_actions) != 67:
        blockers.append("file_action_count_not_67")
    if len({action.get("action_semantics_sha256") for action in [*dir_actions, *file_actions]}) != 78:
        blockers.append("action_semantics_not_unique")
    descriptor = _as_mapping(plan.get("physical_tree_descriptor_v2"))
    if descriptor.get("schema_version") != "agent_sync_cutover_physical_tree_descriptor_v2":
        blockers.append("physical_descriptor_missing")
    if descriptor.get("physical_tree_digest") != plan.get("expected_physical_tree_digest"):
        blockers.append("expected_physical_digest_mismatch")
    if int(descriptor.get("regular_file_count") or 0) != 67 or int(descriptor.get("directory_count_including_root") or 0) != 11:
        blockers.append("physical_descriptor_counts_invalid")
    if not plan.get("temp_exact_action_rehearsal_evidence_sha256"):
        blockers.append("exact_rehearsal_action_binding_missing")
    rehearsal = _as_mapping(plan.get("temp_exact_action_rehearsal_evidence"))
    if rehearsal:
        if rehearsal.get("expected_physical_tree_digest") != plan.get("expected_physical_tree_digest"):
            blockers.append("rehearsal_expected_physical_digest_mismatch")
        if rehearsal.get("actual_after_materialization_physical_tree_digest") != plan.get("expected_physical_tree_digest"):
            blockers.append("rehearsal_materialized_physical_digest_mismatch")
        if rehearsal.get("actual_after_offline_validation_physical_tree_digest") != plan.get("expected_physical_tree_digest"):
            blockers.append("rehearsal_post_validation_physical_digest_mismatch")
        if rehearsal.get("classification_manifest_sha256") != plan.get("classification_manifest_sha256"):
            blockers.append("rehearsal_classification_manifest_mismatch")
        if rehearsal.get("action_semantics_set_sha256") != plan.get("action_semantics_set_sha256"):
            blockers.append("rehearsal_action_semantics_set_mismatch")
        if not rehearsal.get("valid"):
            blockers.append("exact_rehearsal_invalid")
    action_ids = [str(action.get("action_id") or "") for action in [*dir_actions, *file_actions, *cutover_actions]]
    if len(action_ids) != len(set(action_ids)):
        blockers.append("duplicate_action_ids")
    if list(plan.get("exact_requested_action_ids") or []) != action_ids:
        blockers.append("exact_requested_action_ids_mismatch")
    permissions = _as_mapping(plan.get("requested_permissions"))
    for forbidden in ("sigkill", "delete", "invoke", "provider", "p2s", "first_cycle"):
        if permissions.get(forbidden):
            blockers.append(f"forbidden_permission:{forbidden}")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_loss_recovery_plan_v7_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "directory_action_count": len(dir_actions),
        "file_action_count": len(file_actions),
        "cutover_action_count": len(cutover_actions),
        "exact_action_count": len(action_ids),
        "expected_physical_tree_digest": plan.get("expected_physical_tree_digest", ""),
        "classification_manifest_sha256": plan.get("classification_manifest_sha256", ""),
    }


def build_source_loss_cutover_approval_request_v7(plan: Mapping[str, Any]) -> dict[str, Any]:
    request = {
        "schema_version": "agent_sync_source_loss_cutover_approval_request_v7",
        "request_id": stable_id("source_loss_cutover_request_v7", str(plan.get("canonical_sha256") or "")),
        "status": "awaiting_machine_approval",
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("canonical_sha256"),
        "action_semantics_set_sha256": plan.get("action_semantics_set_sha256"),
        "expected_physical_tree_digest": plan.get("expected_physical_tree_digest"),
        "classification_manifest_sha256": plan.get("classification_manifest_sha256"),
        "directory_action_ids": [action.get("action_id") for action in plan.get("directory_actions") or []],
        "file_action_ids": [action.get("action_id") for action in plan.get("file_actions") or []],
        "cutover_action_ids": [action.get("action_id") for action in plan.get("cutover_actions") or []],
        "requested_action_ids": plan.get("exact_requested_action_ids", []),
        "source_provenance_sha256": plan.get("source_provenance_sha256"),
        "environment_profile_sha256": plan.get("environment_profile_sha256"),
        "equivalence_result_sha256": plan.get("equivalence_result_sha256"),
        "canonical_target_path": plan.get("canonical_target_path"),
        "fresh_cutover_candidate_path": plan.get("fresh_cutover_candidate_path"),
        "archive_path": plan.get("archive_path"),
        "production_launch_authority_sha256": plan.get("production_launch_authority_sha256"),
        "incumbent_identity": plan.get("incumbent_identity"),
        "incumbent_port": plan.get("incumbent_port"),
        "endpoint_scopes": {"incumbent_health": True, "incumbent_compute": True, "recovered_health": True, "recovered_compute": True, "adapter_mapping": True, "invoke": False, "provider": False},
        "permissions": {"sigterm": True, "sigkill": False, "delete": False, "irreversible_source_loss_acknowledgement": True, "p2s": False, "first_cycle": False},
        "approval_id": "",
        "approved_at": "",
        "expires_at": plan.get("expires_at"),
        "canonical_sha256": "",
    }
    request["canonical_sha256"] = canonical_sha256(request)
    return request


def validate_source_loss_cutover_approval_request_v7(request: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if request.get("status") != "awaiting_machine_approval":
        blockers.append("request_not_awaiting_machine_approval")
    if request.get("approval_id") or request.get("approved_at"):
        blockers.append("approval_fields_must_be_empty")
    if request.get("plan_sha256") != plan.get("canonical_sha256"):
        blockers.append("plan_hash_mismatch")
    if list(request.get("requested_action_ids") or []) != list(plan.get("exact_requested_action_ids") or []):
        blockers.append("requested_action_ids_mismatch")
    if _as_mapping(request.get("permissions")).get("sigkill") or _as_mapping(request.get("endpoint_scopes")).get("invoke"):
        blockers.append("forbidden_scope")
    if str(request.get("canonical_sha256") or "") != canonical_sha256(request):
        blockers.append("canonical_hash_mismatch")
    return {"schema_version": "agent_sync_source_loss_cutover_approval_request_v7_validation", "valid": not blockers, "blockers": blockers, "request_id": request.get("request_id", ""), "request_sha256": request.get("canonical_sha256", "")}


def build_full_p2s_rebase_plan_v7(recovery_v7: Mapping[str, Any]) -> dict[str, Any]:
    p2s = build_full_p2s_rebase_plan_v6(
        {
            **dict(recovery_v7),
            "clean_fresh_candidate_projection": {
                "source_descriptor": _source_descriptor(RISK_FRAUD_HISTORICAL_ROOT),
            },
        }
    )
    p2s["schema_version"] = "agent_sync_full_p2s_rebase_plan_v7"
    p2s["tool_version"] = R7X_TOOL_VERSION
    p2s["recovery_plan_gate"]["recovery_schema_version"] = "agent_sync_source_loss_recovery_plan_v7"
    p2s["recovery_plan_gate"]["recovery_plan_id"] = recovery_v7.get("plan_id")
    p2s["recovery_plan_gate"]["recovery_plan_sha256"] = recovery_v7.get("canonical_sha256")
    p2s["canonical_sha256"] = ""
    p2s["canonical_sha256"] = canonical_sha256(p2s)
    return p2s


def validate_full_p2s_rebase_plan_v7(plan: Mapping[str, Any]) -> dict[str, Any]:
    shim = dict(plan)
    shim["schema_version"] = "agent_sync_full_p2s_rebase_plan_v6"
    shim["recovery_plan_gate"] = {**dict(_as_mapping(plan.get("recovery_plan_gate"))), "recovery_schema_version": "agent_sync_source_loss_recovery_plan_v6"}
    shim["canonical_sha256"] = canonical_sha256(shim)
    base = validate_full_p2s_rebase_plan_v6(shim)
    blockers = list(base["blockers"])
    if plan.get("schema_version") != "agent_sync_full_p2s_rebase_plan_v7":
        blockers.append("schema_version_not_v7")
    if _as_mapping(plan.get("recovery_plan_gate")).get("recovery_schema_version") != "agent_sync_source_loss_recovery_plan_v7":
        blockers.append("recovery_gate_not_v7")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {"schema_version": "agent_sync_full_p2s_rebase_plan_v7_validation", "valid": not blockers, "blockers": blockers, "plan_id": plan.get("plan_id", ""), "plan_sha256": plan.get("canonical_sha256", ""), "physical_action_count": base["physical_action_count"]}


def _retag(payload: Mapping[str, Any], schema_version: str, id_prefix: str) -> dict[str, Any]:
    result = dict(payload)
    result["schema_version"] = schema_version
    if "request_id" in result:
        result["request_id"] = stable_id(id_prefix, str(result.get("plan_sha256") or result.get("canonical_sha256") or ""))
    result["canonical_sha256"] = ""
    result["canonical_sha256"] = canonical_sha256(result)
    return result


def build_full_p2s_stage_request_v7(p2s_v7: Mapping[str, Any]) -> dict[str, Any]:
    return _retag(build_full_p2s_stage_request_v6(p2s_v7), "agent_sync_full_p2s_stage_request_v7", "p2s_stage_request_v7")


def build_full_p2s_activation_template_v7(p2s_v7: Mapping[str, Any]) -> dict[str, Any]:
    return _retag(build_full_p2s_activation_template_v6(p2s_v7), "agent_sync_full_p2s_activation_template_v7", "p2s_activation_template_v7")


def build_projected_experiment_v7(selected: Mapping[str, Any], p2s_v7: Mapping[str, Any]) -> dict[str, Any]:
    return _retag(build_projected_experiment_v6(selected, p2s_v7), "agent_sync_projected_experiment_manifest_v7", "experiment_v7")


def build_first_real_cycle_plan_v7(selected: Mapping[str, Any], experiment_v7: Mapping[str, Any], p2s_v7: Mapping[str, Any]) -> dict[str, Any]:
    from react_agent.ops.sync_5a_r6x import build_first_real_cycle_plan_v6

    return _retag(build_first_real_cycle_plan_v6(selected, experiment_v7, p2s_v7), "agent_sync_first_real_cycle_plan_v7", "cycle_v7")


def build_conditional_approval_chain_v7(
    *,
    canary_closeout: Mapping[str, Any],
    recovery_v7: Mapping[str, Any],
    p2s_v7: Mapping[str, Any],
    experiment_v7: Mapping[str, Any],
    cycle_v7: Mapping[str, Any],
) -> dict[str, Any]:
    chain = {
        "schema_version": "agent_sync_conditional_approval_chain_v7",
        "chain_id": stable_id("approval_chain_v7", str(canary_closeout.get("canonical_sha256") or ""), str(recovery_v7.get("canonical_sha256") or "")),
        "supersedes": ["agent_sync_conditional_approval_chain_v6"],
        "broad_preapproval_forbidden": True,
        "nodes": [
            {"node": "precutover_canary", "status": "executed_and_closed", "closeout_sha256": canary_closeout.get("canonical_sha256")},
            {"node": "source_loss_cutover_v7", "status": "awaiting_machine_approval", "plan_id": recovery_v7.get("plan_id"), "plan_sha256": recovery_v7.get("canonical_sha256")},
            {"node": "recovery_settle", "status": "blocked_pending_real_cutover_closeout"},
            {"node": "p2s_stage_verify_v7", "status": "blocked_pending_recovery_settle", "plan_id": p2s_v7.get("plan_id"), "plan_sha256": p2s_v7.get("canonical_sha256")},
            {"node": "p2s_activate_rollback_v7", "status": "blocked_pending_real_stage_closeout", "plan_id": p2s_v7.get("plan_id"), "plan_sha256": p2s_v7.get("canonical_sha256")},
            {"node": "experiment_materialization_v7", "status": "blocked_pending_p2s_activation_closeout", "experiment_id": experiment_v7.get("experiment_id"), "experiment_sha256": experiment_v7.get("canonical_sha256")},
            {"node": "first_nonzero_cycle_v7", "status": "blocked_pending_experiment_validation", "cycle_id": cycle_v7.get("cycle_id"), "cycle_sha256": cycle_v7.get("canonical_sha256")},
        ],
        "canonical_sha256": "",
    }
    chain["canonical_sha256"] = canonical_sha256(chain)
    return chain


def validate_conditional_approval_chain_v7(chain: Mapping[str, Any]) -> dict[str, Any]:
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
    blockers = []
    if [node.get("status") for node in nodes] != expected:
        blockers.append("approval_chain_status_order_invalid")
    if not chain.get("broad_preapproval_forbidden"):
        blockers.append("broad_preapproval_not_forbidden")
    if str(chain.get("canonical_sha256") or "") != canonical_sha256(chain):
        blockers.append("canonical_hash_mismatch")
    return {"schema_version": "agent_sync_conditional_approval_chain_v7_validation", "valid": not blockers, "blockers": blockers, "chain_id": chain.get("chain_id", ""), "chain_sha256": chain.get("canonical_sha256", "")}


def build_real_readonly_preflight_v7(*, expected_runtime_identity: Mapping[str, Any], recovery_v7: Mapping[str, Any]) -> dict[str, Any]:
    preflight = build_real_readonly_preflight(expected_runtime_identity=expected_runtime_identity, recovery_v5=recovery_v7)
    preflight["schema_version"] = "agent_sync_real_readonly_source_loss_preflight_v7"
    preflight["listener_11013"] = port_listening(11013)
    preflight["canonical_physical_descriptor"] = build_cutover_tree_descriptor(RISK_FRAUD_PROD_ROOT, root_role="canonical_readonly_v7")
    preflight["source_descriptor"] = _source_descriptor(RISK_FRAUD_HISTORICAL_ROOT)
    preflight["source_descriptor_matches"] = preflight["source_descriptor"].get("digest") == EXPECTED_SOURCE_DESCRIPTOR_DIGEST
    preflight["source_provenance_sha256"] = build_source_package_provenance(RISK_FRAUD_HISTORICAL_ROOT)["canonical_sha256"]
    preflight["source_provenance_matches"] = preflight["source_provenance_sha256"] == EXPECTED_SOURCE_PROVENANCE_SHA256
    preflight["endpoint_calls"] = 0
    preflight["process_actions"] = 0
    preflight["canonical_writes"] = 0
    preflight["real_candidate_writes"] = 0
    preflight["valid"] = bool(preflight.get("valid")) and not preflight["listener_11013"] and preflight["source_descriptor_matches"] and preflight["source_provenance_matches"]
    preflight["canonical_sha256"] = canonical_sha256(preflight)
    return preflight
