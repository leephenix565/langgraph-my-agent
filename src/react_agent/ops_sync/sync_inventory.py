# ruff: noqa: D101, D103
"""Read-only filesystem inventory for agent sync planning."""

from __future__ import annotations

import hashlib
import os
import stat
from collections import Counter
from pathlib import Path
from typing import Any, TypedDict

from react_agent.ops_sync.sync_contracts import canonical_sha256, file_sha256
from react_agent.ops_sync.sync_registry import load_static_registry, validate_static_registry
from react_agent.ops_sync.sync_runtime_assets import is_explicit_runtime_asset
from react_agent.ops_sync.sync_security import (
    BACKUP_FILE_RE,
    EXCLUDED_DIR_NAMES,
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
    source_category: str
    source_category_reason: str
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


def _file_record(
    agent_id: str,
    root: Path,
    path: Path,
    root_role: str,
    *,
    relative_base: Path | None = None,
) -> FileInventoryRecord:
    stat_result = path.lstat()
    file_type = classify_file_type(stat_result.st_mode)
    base = relative_base or root
    relative_path = normalize_safe_relative_path(path.relative_to(base))
    sha = ""
    normalized_sha = ""
    line_ending = ""
    symlink_target = ""
    sensitive = "not_scanned"
    sensitive_lines: list[str] = []
    large = "not_large_asset"
    source_category = "unknown_blocked"
    source_category_reason = "not_source_bearing"
    include = False
    include_decision = "excluded"
    reason = "not_source_bearing"
    if file_type == "regular":
        explicit_asset = is_explicit_runtime_asset(agent_id, relative_path)
        safety = should_include_source_file(root, path, explicit_asset=explicit_asset)
        include = safety["include"]
        include_decision = safety["classification"]
        reason = safety["reason"]
        sensitive, sensitive_lines = classify_sensitive_source(path, size=stat_result.st_size)
        large = safety["large_asset_classification"]
        source_category = safety["source_category"]
        source_category_reason = safety["source_category_reason"]
        if include:
            sha = file_sha256(path)
            normalized_sha, line_ending = _normalized_text_sha(path, stat_result.st_size)
    elif file_type == "symlink":
        include_decision, symlink_target = safe_symlink_decision(root, path)
        include = include_decision == "safe_relative_symlink"
        reason = include_decision
        source_category = "source_code"
        source_category_reason = "safe_relative_symlink"
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
        "source_category": source_category,
        "source_category_reason": source_category_reason,
        "include": include,
        "include_decision": include_decision,
        "reason": reason,
    }


def inventory_root(agent_id: str, root: Path, *, root_role: str, relative_base: Path | None = None) -> dict[str, Any]:
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
    if root.is_file() or root.is_symlink():
        record = _file_record(agent_id, root.parent, root, root_role, relative_base=relative_base or root.parent)
        included = [record] if record["include"] else []
        digest_items = [
            {
                "relative_path": item["relative_path"],
                "file_type": item["file_type"],
                "sha256": item["sha256"],
                "executable": item["executable"],
                "symlink_target": item["symlink_target"],
            }
            for item in included
        ]
        return {
            "agent_id": agent_id,
            "root_role": root_role,
            "root": str(root),
            "root_exists": True,
            "tree_digest": canonical_sha256(digest_items),
            "files": [record],
            "included_count": len(included),
            "excluded_count": 0 if included else 1,
            "unicode_collisions": [],
        }
    records: list[FileInventoryRecord] = []
    visited_dirs: set[tuple[int, int]] = set()
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        try:
            current_stat = current_path.lstat()
        except OSError:
            dirnames[:] = []
            continue
        current_key = (current_stat.st_dev, current_stat.st_ino)
        if current_key in visited_dirs:
            dirnames[:] = []
            continue
        visited_dirs.add(current_key)
        kept_dirs: list[str] = []
        for dirname in dirnames:
            candidate = current_path / dirname
            lower_dirname = dirname.lower()
            if (
                dirname in EXCLUDED_DIR_NAMES
                or dirname.startswith(".")
                or "output" in lower_dirname
                or lower_dirname.endswith("_out")
                or BACKUP_FILE_RE.match(dirname)
            ):
                continue
            try:
                stat_result = candidate.lstat()
            except OSError:
                continue
            if stat.S_ISLNK(stat_result.st_mode):
                continue
            if not stat.S_ISDIR(stat_result.st_mode):
                records.append(_file_record(agent_id, root, candidate, root_role, relative_base=relative_base))
                continue
            kept_dirs.append(dirname)
        dirnames[:] = sorted(kept_dirs)
        for filename in sorted(filenames):
            path = current_path / filename
            try:
                records.append(_file_record(agent_id, root, path, root_role, relative_base=relative_base))
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


def inventory_source_roots(agent_id: str, logical_root: Path, source_roots: list[Path], *, root_role: str) -> dict[str, Any]:
    records: list[FileInventoryRecord] = []
    root_exists = logical_root.exists()
    missing_roots: list[str] = []
    for source_root in source_roots:
        if not source_root.exists():
            missing_roots.append(str(source_root))
            continue
        try:
            source_root.resolve(strict=False).relative_to(logical_root.resolve(strict=False))
        except ValueError:
            missing_roots.append(f"outside_logical_root:{source_root}")
            continue
        relative_base = logical_root.parent if logical_root.is_file() else logical_root
        sub_inventory = inventory_root(agent_id, source_root, root_role=root_role, relative_base=relative_base)
        records.extend(sub_inventory["files"])
    included = [record for record in records if record["include"]]
    path_counts = Counter(record["relative_path"] for record in records)
    duplicate_paths = [path for path, count in path_counts.items() if count > 1]
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
        "root": str(logical_root),
        "source_roots": [str(path) for path in source_roots],
        "missing_source_roots": missing_roots,
        "root_exists": root_exists,
        "tree_digest": canonical_sha256(digest_items),
        "files": records,
        "included_count": len(included),
        "excluded_count": len(records) - len(included),
        "unicode_collisions": detect_unicode_collision([record["relative_path"] for record in records]),
        "duplicate_relative_paths": sorted(set(duplicate_paths)),
    }


def build_runtime_inventory(*, include_files: bool = True) -> dict[str, Any]:
    registry = load_static_registry()
    validation = validate_static_registry(registry)
    agent_rows: list[dict[str, Any]] = []
    for agent in registry["agents"]:
        prod_root = Path(agent["prod"]["root"])
        sandbox_root = Path(agent["sandbox"]["active_root"])
        baseline_root = Path(agent["sandbox"]["baseline_root"])
        prod_source_roots = [
            Path(str(path))
            for path in agent.get("prod", {}).get("source_subroots", [])
            if str(path)
        ] or [prod_root]
        root_results = {
            "prod": inventory_source_roots(agent["agent_id"], prod_root, prod_source_roots, root_role="prod"),
            "active_sandbox": inventory_root(agent["agent_id"], sandbox_root, root_role="active_sandbox"),
            "baseline": inventory_root(agent["agent_id"], baseline_root, root_role="baseline"),
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
