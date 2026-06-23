# ruff: noqa: D101, D103
"""Read-only filesystem inventory for agent sync planning."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any, TypedDict

from react_agent.ops.sync_contracts import canonical_sha256, file_sha256
from react_agent.ops.sync_registry import load_static_registry, validate_static_registry
from react_agent.ops.sync_security import (
    classify_file_type,
    classify_sensitive_source,
    detect_unicode_collision,
    normalize_safe_relative_path,
    safe_symlink_decision,
    should_include_source_file,
)


class FileInventoryRecord(TypedDict):
    agent_id: str
    unit_kind: str
    root_role: str
    relative_path: str
    raw_path: str
    file_type: str
    size: int
    mode: str
    executable: bool
    sha256: str
    normalized_text_sha256: str
    line_ending: str
    symlink_target: str
    link_count: int
    sensitive_classification: str
    sensitive_line_ranges: list[str]
    large_asset_classification: str
    include: bool
    include_decision: str
    reason: str


def _normalized_text_sha(path: Path, size: int) -> tuple[str, str]:
    if size > 25 * 1024 * 1024:
        return "", "not_text_or_large"
    try:
        data = path.read_bytes()
    except OSError:
        return "", "unreadable"
    if b"\x00" in data[:4096]:
        return "", "binary"
    if b"\r\n" in data:
        line_ending = "CRLF"
    elif b"\r" in data:
        line_ending = "CR"
    else:
        line_ending = "LF"
    text = data.decode("utf-8", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), line_ending


def _file_record(agent_id: str, root: Path, path: Path, root_role: str) -> FileInventoryRecord:
    stat_result = path.lstat()
    file_type = classify_file_type(stat_result.st_mode)
    relative_path = normalize_safe_relative_path(path.relative_to(root))
    sha = ""
    normalized_sha = ""
    line_ending = ""
    symlink_target = ""
    sensitive = "not_scanned"
    sensitive_lines: list[str] = []
    large = "not_large_asset"
    include = False
    include_decision = "excluded"
    reason = "not_source_bearing"
    if file_type == "regular":
        safety = should_include_source_file(root, path)
        include = safety["include"]
        include_decision = safety["classification"]
        reason = safety["reason"]
        sensitive, sensitive_lines = classify_sensitive_source(path, size=stat_result.st_size)
        large = safety["large_asset_classification"]
        if include:
            sha = file_sha256(path)
            normalized_sha, line_ending = _normalized_text_sha(path, stat_result.st_size)
    elif file_type == "symlink":
        include_decision, symlink_target = safe_symlink_decision(root, path)
        include = include_decision == "safe_relative_symlink"
        reason = include_decision
    else:
        include_decision = f"blocked_{file_type}"
        reason = file_type
    return {
        "agent_id": agent_id,
        "unit_kind": "source_file",
        "root_role": root_role,
        "relative_path": relative_path,
        "raw_path": str(path),
        "file_type": file_type,
        "size": stat_result.st_size,
        "mode": oct(stat.S_IMODE(stat_result.st_mode)),
        "executable": bool(stat_result.st_mode & stat.S_IXUSR),
        "sha256": sha,
        "normalized_text_sha256": normalized_sha,
        "line_ending": line_ending,
        "symlink_target": symlink_target,
        "link_count": stat_result.st_nlink,
        "sensitive_classification": sensitive,
        "sensitive_line_ranges": sensitive_lines,
        "large_asset_classification": large,
        "include": include,
        "include_decision": include_decision,
        "reason": reason,
    }


def inventory_root(agent_id: str, root: Path, *, root_role: str) -> dict[str, Any]:
    if not root.exists():
        return {
            "agent_id": agent_id,
            "root_role": root_role,
            "root": str(root),
            "root_exists": False,
            "tree_digest": "",
            "files": [],
            "included_count": 0,
            "excluded_count": 0,
            "unicode_collisions": [],
        }
    records: list[FileInventoryRecord] = []
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for dirname in dirnames:
            candidate = current_path / dirname
            try:
                record = _file_record(agent_id, root, candidate, root_role)
            except OSError:
                continue
            if record["include_decision"].startswith("blocked") or record["reason"] == "excluded_directory":
                continue
            if dirname in {
                ".git",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                ".venv",
                "venv",
                "node_modules",
                "logs",
                "cache",
                "data",
                "datasets",
                "models",
                "weights",
                "backups",
            }:
                continue
            kept_dirs.append(dirname)
        dirnames[:] = sorted(kept_dirs)
        for filename in sorted(filenames):
            path = current_path / filename
            try:
                records.append(_file_record(agent_id, root, path, root_role))
            except (OSError, ValueError):
                continue
    included = [record for record in records if record["include"]]
    digest_items = [
        {
            "relative_path": item["relative_path"],
            "file_type": item["file_type"],
            "sha256": item["sha256"],
            "executable": item["executable"],
            "symlink_target": item["symlink_target"],
        }
        for item in sorted(included, key=lambda record: record["relative_path"])
    ]
    return {
        "agent_id": agent_id,
        "root_role": root_role,
        "root": str(root),
        "root_exists": True,
        "tree_digest": canonical_sha256(digest_items),
        "files": records,
        "included_count": len(included),
        "excluded_count": len(records) - len(included),
        "unicode_collisions": detect_unicode_collision([record["relative_path"] for record in records]),
    }


def build_runtime_inventory(*, include_files: bool = True) -> dict[str, Any]:
    registry = load_static_registry()
    validation = validate_static_registry(registry)
    agent_rows: list[dict[str, Any]] = []
    for agent in registry["agents"]:
        prod_root = Path(agent["prod"]["root"])
        sandbox_root = Path(agent["sandbox"]["active_root"])
        baseline_root = Path(agent["sandbox"]["baseline_root"])
        roots = {
            "prod": prod_root,
            "active_sandbox": sandbox_root,
            "baseline": baseline_root,
        }
        root_results = {
            role: inventory_root(agent["agent_id"], path, root_role=role)
            for role, path in roots.items()
        }
        if not include_files:
            for result in root_results.values():
                result["files"] = []
        agent_rows.append(
            {
                "agent_id": agent["agent_id"],
                "layer": agent["layer"],
                "dimension": agent["dimension"],
                "roots": root_results,
                "sanitized_derivative": agent["sandbox"].get("sanitized_derivative", False),
                "semantic_placeholder": agent["sandbox"].get("semantic_placeholder", False),
            }
        )
    return {
        "schema_version": "agent_sync_runtime_inventory_snapshot_v1",
        "registry_sha256": validation["registry_sha256"],
        "policy_sha256": validation["policy_sha256"],
        "catalog_sha256": validation["catalog_sha256"],
        "agent_count": len(agent_rows),
        "agents": agent_rows,
        "static_registry_valid": validation["valid"],
        "fatal_conflict_count": len(validation["fatal_conflicts"]),
        "review_warning_count": len(validation["review_warnings"]),
    }

