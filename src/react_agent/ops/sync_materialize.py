# ruff: noqa: D101, D103
"""Temp-only materialization checks for P2S plans."""

from __future__ import annotations

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
from react_agent.ops.sync_security import classify_sensitive_source, normalize_safe_relative_path


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


def _secret_scan_temp(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "SANDBOX_SECRET_REQUIREMENTS.md":
            continue
        stat_result = path.stat()
        sensitive, lines = classify_sensitive_source(path, size=stat_result.st_size)
        if sensitive in {"blocked_env_file", "potential_secret_literal"}:
            findings.append({"relative_path": normalize_safe_relative_path(path.relative_to(root)), "classification": sensitive, "line_ranges": lines})
    return {"pass": not findings, "finding_count": len(findings), "findings": findings}


def _py_compile_temp(root: Path) -> dict[str, Any]:
    py_files = sorted(path for path in root.rglob("*.py") if path.is_file())
    cache_root = Path("/tmp") / f"agent_sync_pycache_{os.getpid()}"
    previous = os.environ.get("PYTHONPYCACHEPREFIX")
    os.environ["PYTHONPYCACHEPREFIX"] = str(cache_root)
    failures: list[dict[str, str]] = []
    try:
        for path in py_files:
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                failures.append({"relative_path": normalize_safe_relative_path(path.relative_to(root)), "reason": exc.exc_type_name})
    finally:
        if previous is None:
            os.environ.pop("PYTHONPYCACHEPREFIX", None)
        else:
            os.environ["PYTHONPYCACHEPREFIX"] = previous
        shutil.rmtree(cache_root, ignore_errors=True)
    return {"pass": not failures, "file_count": len(py_files), "failure_count": len(failures), "failures": failures[:50]}


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
    secret_scan = _secret_scan_temp(temp_root)
    py_compile_result = _py_compile_temp(temp_root)
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
