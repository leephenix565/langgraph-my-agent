# ruff: noqa: D101, D103
"""Temp-only materialization checks for P2S plans."""

from __future__ import annotations

import hashlib
import os
import py_compile
import shutil
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from react_agent.ops.sync_contracts import SyncPlannerError, file_sha256
from react_agent.ops.sync_plan import stage_projection_digest_for_actions
from react_agent.ops.sync_registry import load_static_registry
from react_agent.ops.sync_security import (
    classify_sensitive_source,
    normalize_safe_relative_path,
)


def _require_tmp_root(root: Path) -> None:
    resolved = root.resolve(strict=False)
    tmp = Path("/tmp").resolve(strict=False)
    if tmp not in [resolved, *resolved.parents]:
        raise SyncPlannerError("temp_materialization_root_not_under_tmp", exit_code=2)


def _registry_agent_roots() -> dict[str, dict[str, str]]:
    registry = load_static_registry()
    return {
        str(agent["agent_id"]): {
            "active_root": str((agent.get("sandbox") or {}).get("active_root") or ""),
            "baseline_root": str((agent.get("sandbox") or {}).get("baseline_root") or ""),
        }
        for agent in registry["agents"]
    }


def _source_for_preserved_action(action: Mapping[str, Any], roots: Mapping[str, Mapping[str, str]]) -> Path:
    agent_id = str(action.get("agent_id") or "")
    rel = normalize_safe_relative_path(str(action.get("destination_relative_path") or ""))
    for root_key in ("active_root", "baseline_root"):
        root = Path(str(roots.get(agent_id, {}).get(root_key) or ""))
        candidate = root / rel
        if candidate.exists():
            return candidate
    raise SyncPlannerError("preserved_source_missing", exit_code=7, details={"agent_id": agent_id, "relative_path": rel})


def _write_action(action: Mapping[str, Any], temp_root: Path, roots: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    operation = str(action.get("operation") or "")
    if operation == "noop_shared_transaction_member":
        return {"operation": operation, "written": False, "reason": "noop_shared_transaction_member"}
    stage_rel = normalize_safe_relative_path(str(action.get("stage_relative_path") or ""))
    destination = temp_root / stage_rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    if operation in {"copy_from_prod", "snapshot_semantic_placeholder"}:
        source = Path(str(action.get("source_absolute_path") or ""))
        if not source.exists():
            raise SyncPlannerError("materialization_source_missing", exit_code=7, details={"path": str(source)})
        shutil.copyfile(source, destination)
        mode_text = str(action.get("source_mode") or "0o644")
        try:
            mode = int(mode_text, 8)
        except ValueError:
            mode = 0o644
        destination.chmod(stat.S_IMODE(mode))
    elif operation in {"preserve_sanitized_derivative", "preserve_sandbox_metadata"}:
        if action.get("source_absolute_path"):
            source = Path(str(action.get("source_absolute_path")))
        else:
            source = _source_for_preserved_action(action, roots)
        shutil.copyfile(source, destination)
        destination.chmod(0o644)
    else:
        return {"operation": operation, "written": False, "reason": "operation_not_materialized"}
    return {
        "operation": operation,
        "written": True,
        "stage_relative_path": stage_rel,
        "sha256": file_sha256(destination),
    }


def compute_stage_digest(root: Path, planned_actions: list[Mapping[str, Any]]) -> str:
    actual_actions: list[dict[str, Any]] = []
    for action in planned_actions:
        operation = str(action.get("operation") or "")
        if operation == "noop_shared_transaction_member":
            continue
        stage_rel = str(action.get("stage_relative_path") or "")
        if not stage_rel:
            continue
        path = root / normalize_safe_relative_path(stage_rel)
        if not path.exists():
            continue
        stat_result = path.lstat()
        actual = dict(action)
        if operation in {"copy_from_prod", "snapshot_semantic_placeholder"}:
            actual["source_sha256"] = file_sha256(path)
            actual["source_file_type"] = "regular"
            actual["source_executable"] = bool(stat_result.st_mode & stat.S_IXUSR)
            actual["source_symlink_target"] = ""
        elif operation == "preserve_sanitized_derivative":
            actual["derivative_sha256"] = file_sha256(path)
        elif operation == "preserve_sandbox_metadata":
            actual["metadata_sha256"] = file_sha256(path)
        actual_actions.append(actual)
    return stage_projection_digest_for_actions(actual_actions)


def secret_scan_stage(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "SANDBOX_SECRET_REQUIREMENTS.md":
            continue
        stat_result = path.stat()
        sensitive, lines = classify_sensitive_source(path, size=stat_result.st_size)
        if sensitive in {"blocked_env_file", "potential_secret_literal"}:
            findings.append({"relative_path": normalize_safe_relative_path(path.relative_to(root)), "classification": sensitive, "line_ranges": lines})
    return {"pass": not findings, "finding_count": len(findings), "findings": findings}


def compile_stage_with_profile(root: Path, profile: Mapping[str, str] | None = None) -> dict[str, Any]:
    py_files = sorted(path for path in root.rglob("*.py") if path.is_file())
    cache_root = Path("/tmp") / f"agent_sync_pycache_{os.getpid()}"
    previous = os.environ.get("PYTHONPYCACHEPREFIX")
    os.environ["PYTHONPYCACHEPREFIX"] = str(cache_root)
    hard_classes = {
        "runtime_required_python",
        "startup_required_python",
        "contract_test_python",
        "offline_test_python",
        "semantic_placeholder_python",
    }
    diagnostic_classes = {"legacy_reference_python", "archived_experiment_python", "excluded_python"}
    failures: list[dict[str, str]] = []
    diagnostics: list[dict[str, str]] = []
    try:
        for path in py_files:
            rel = normalize_safe_relative_path(path.relative_to(root))
            profile_class = str((profile or {}).get(rel) or "runtime_required_python")
            try:
                cache_target = cache_root / f"{hashlib.sha256(rel.encode('utf-8')).hexdigest()}.pyc"
                cache_target.parent.mkdir(parents=True, exist_ok=True)
                py_compile.compile(str(path), cfile=str(cache_target), doraise=True)
            except py_compile.PyCompileError as exc:
                row = {"relative_path": rel, "reason": exc.exc_type_name, "validation_profile": profile_class}
                if profile_class in diagnostic_classes:
                    diagnostics.append(row)
                elif profile_class in hard_classes:
                    failures.append(row)
                else:
                    failures.append(row)
    finally:
        if previous is None:
            os.environ.pop("PYTHONPYCACHEPREFIX", None)
        else:
            os.environ["PYTHONPYCACHEPREFIX"] = previous
        shutil.rmtree(cache_root, ignore_errors=True)
    return {
        "pass": not failures,
        "file_count": len(py_files),
        "failure_count": len(failures),
        "diagnostic_count": len(diagnostics),
        "failures": failures[:50],
        "diagnostics": diagnostics[:50],
    }


def materialize_stage(plan: Mapping[str, Any], stage_root: Path, *, validation_profile: Mapping[str, str] | None = None) -> dict[str, Any]:
    if stage_root.exists():
        raise SyncPlannerError("stage_root_already_exists", exit_code=5, details={"stage_root": str(stage_root)})
    stage_root.mkdir(parents=True)
    roots = _registry_agent_roots()
    actions = [
        action
        for agent in plan.get("agents") or []
        if isinstance(agent, Mapping)
        for action in agent.get("actions") or []
        if isinstance(action, Mapping)
    ]
    seen_destinations: set[str] = set()
    duplicate_destinations: list[str] = []
    writes: list[dict[str, Any]] = []
    for action in actions:
        stage_rel = str(action.get("stage_relative_path") or "")
        if stage_rel:
            normalized = normalize_safe_relative_path(stage_rel)
            if normalized in seen_destinations and str(action.get("operation") or "") != "noop_shared_transaction_member":
                duplicate_destinations.append(normalized)
            seen_destinations.add(normalized)
        before_source = Path(str(action.get("source_absolute_path") or ""))
        expected_sha = str(action.get("source_sha256") or "")
        if before_source.exists() and expected_sha and file_sha256(before_source) != expected_sha:
            raise SyncPlannerError("materialization_source_hash_drift", exit_code=5, details={"source": str(before_source)})
        writes.append(_write_action(action, stage_root, roots))
    expected_digest = str((plan.get("stage_materialization") or {}).get("expected_stage_projection_digest") or "")
    actual_digest = compute_stage_digest(stage_root, actions)
    secret_scan = secret_scan_stage(stage_root)
    py_compile_result = compile_stage_with_profile(stage_root, validation_profile)
    structural_pass = expected_digest == actual_digest and not duplicate_destinations and bool(secret_scan["pass"])
    return {
        "stage_root": str(stage_root),
        "expected_projection_digest": expected_digest,
        "actual_stage_digest": actual_digest,
        "digest_match": expected_digest == actual_digest,
        "structural_pass": structural_pass,
        "action_count": len(actions),
        "written_file_count": sum(1 for item in writes if item.get("written")),
        "duplicate_destination_count": len(duplicate_destinations),
        "duplicate_destinations": duplicate_destinations[:50],
        "secret_scan": secret_scan,
        "py_compile": py_compile_result,
    }


def reconstruct_temp_stage(plan: Mapping[str, Any], temp_root: Path) -> dict[str, Any]:
    _require_tmp_root(temp_root)
    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir(parents=True)
    roots = _registry_agent_roots()
    actions = [
        action
        for agent in plan.get("agents") or []
        if isinstance(agent, Mapping)
        for action in agent.get("actions") or []
        if isinstance(action, Mapping)
    ]
    seen_destinations: set[str] = set()
    duplicate_destinations: list[str] = []
    writes: list[dict[str, Any]] = []
    for action in actions:
        stage_rel = str(action.get("stage_relative_path") or "")
        if stage_rel:
            normalized = normalize_safe_relative_path(stage_rel)
            if normalized in seen_destinations and str(action.get("operation") or "") != "noop_shared_transaction_member":
                duplicate_destinations.append(normalized)
            seen_destinations.add(normalized)
        writes.append(_write_action(action, temp_root, roots))
    expected_digest = str((plan.get("stage_materialization") or {}).get("expected_stage_projection_digest") or "")
    actual_digest = compute_stage_digest(temp_root, actions)
    secret_scan = secret_scan_stage(temp_root)
    py_compile_result = compile_stage_with_profile(temp_root)
    structural_pass = expected_digest == actual_digest and not duplicate_destinations and bool(secret_scan["pass"])
    return {
        "temp_root": str(temp_root),
        "expected_projection_digest": expected_digest,
        "actual_temp_stage_digest": actual_digest,
        "digest_match": expected_digest == actual_digest,
        "structural_pass": structural_pass,
        "action_count": len(actions),
        "written_file_count": sum(1 for item in writes if item.get("written")),
        "duplicate_destination_count": len(duplicate_destinations),
        "duplicate_destinations": duplicate_destinations[:50],
        "secret_scan": secret_scan,
        "py_compile": py_compile_result,
    }
