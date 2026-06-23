# ruff: noqa: D101, D102, D103, D107
"""Artifact path validation helpers for sync planner outputs."""

from __future__ import annotations

import json
import os
import shutil
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from react_agent.ops.sync_contracts import SyncPlannerError, file_sha256

DEFAULT_ARTIFACT_STORE_ROOT = Path("/sdb/dlut/ops-artifacts/agent-sync")


def _validate_entry_name(name: str, seen: set[str]) -> None:
    if "\\" in name:
        raise ValueError("archive_entry_not_posix")
    if name.startswith("/"):
        raise ValueError("archive_entry_absolute")
    posix = PurePosixPath(name)
    if any(part in {"", ".", ".."} for part in posix.parts):
        raise ValueError("archive_entry_path_traversal")
    normalized = posix.as_posix()
    if normalized in seen:
        raise ValueError("archive_entry_duplicate")
    seen.add(normalized)


def validate_archive_member_names(path: Path) -> dict[str, Any]:
    """Validate archive member names without extracting the archive."""
    seen: set[str] = set()
    entries: list[str] = []
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                _validate_entry_name(info.filename, seen)
                entries.append(info.filename)
    elif tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            for member in archive.getmembers():
                _validate_entry_name(member.name, seen)
                if member.issym() or member.islnk():
                    raise ValueError("archive_symlink_entry_blocked")
                entries.append(member.name)
    else:
        raise ValueError("unsupported_archive_type")
    return {
        "archive": str(path),
        "entry_count": len(entries),
        "all_archive_entries_posix": True,
        "entries": entries,
    }


def _safe_relative_path(path_text: str) -> PurePosixPath:
    if "\\" in path_text:
        raise SyncPlannerError("artifact_path_not_posix", exit_code=2)
    if path_text.startswith("/"):
        raise SyncPlannerError("artifact_path_absolute", exit_code=2)
    rel = PurePosixPath(path_text)
    if any(part in {"", ".", ".."} for part in rel.parts):
        raise SyncPlannerError("artifact_path_traversal", exit_code=2)
    return rel


def _fsync_parent(path: Path) -> None:
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _mode_text(path: Path) -> str:
    try:
        return oct(path.stat().st_mode & 0o777)
    except OSError:
        return ""


def _writable_by_mode(path: Path) -> bool:
    """Infer write readiness from ownership/mode only; do not create probe files."""
    try:
        st = path.stat()
    except OSError:
        return False
    uid = os.geteuid()
    gids = {os.getegid(), *os.getgroups()}
    mode = st.st_mode
    if st.st_uid == uid and mode & 0o200:
        return True
    if st.st_gid in gids and mode & 0o020:
        return True
    return bool(mode & 0o002)


def artifact_store_preflight(root: Path = DEFAULT_ARTIFACT_STORE_ROOT) -> dict[str, Any]:
    """Return a read-only artifact-store readiness summary."""
    parent = root.parent
    root_exists = root.exists()
    parent_exists = parent.exists()
    probe = root if root_exists else parent
    try:
        stat_result = probe.stat() if probe.exists() else None
    except OSError:
        stat_result = None
    try:
        usage = shutil.disk_usage(probe if probe.exists() else parent)
        free_bytes = usage.free
    except OSError:
        free_bytes = None
    blockers: list[str] = []
    if not root_exists:
        blockers.append("root_missing")
    if not parent_exists:
        blockers.append("parent_missing")
    if root_exists and not _writable_by_mode(root):
        blockers.append("root_not_writable_by_mode")
    if not root_exists and parent_exists and not _writable_by_mode(parent):
        blockers.append("parent_not_writable_by_mode")
    if stat_result is None:
        blockers.append("device_unavailable")
    payload = {
        "schema_version": "agent_sync_artifact_store_preflight_v1",
        "root": str(root),
        "parent": str(parent),
        "root_exists": root_exists,
        "parent_exists": parent_exists,
        "root_realpath": str(root.resolve(strict=False)) if root_exists else "",
        "parent_realpath": str(parent.resolve(strict=False)) if parent_exists else "",
        "root_mode": _mode_text(root) if root_exists else "",
        "parent_mode": _mode_text(parent) if parent_exists else "",
        "root_uid": root.stat().st_uid if root_exists else None,
        "root_gid": root.stat().st_gid if root_exists else None,
        "parent_uid": parent.stat().st_uid if parent_exists else None,
        "parent_gid": parent.stat().st_gid if parent_exists else None,
        "filesystem_device_id": str(stat_result.st_dev) if stat_result is not None else "unavailable",
        "free_bytes": free_bytes,
        "root_write_ready_by_mode": _writable_by_mode(root) if root_exists else False,
        "parent_write_ready_by_mode": _writable_by_mode(parent) if parent_exists else False,
        "creation_required": not root_exists,
        "expected_root_state": "present" if root_exists else "missing",
        "creation_deferred": True,
        "ready": root_exists and not blockers,
        "blockers": blockers,
        "fs_policy": {
            "expected_root_state": "present" if root_exists else "missing",
            "creation_deferred": True,
            "same_filesystem_required": True,
        },
        "init_action": {
            "required": not root_exists,
            "approval_required": not root_exists,
            "creates": ["runs/<run_id>"],
            "mode": "0700_for_run_subdirectories",
            "journal_event": "run_initialized",
        },
    }
    return payload


class ArtifactRunStore:
    """Durable run artifact helper for writer phases."""

    def __init__(self, root: Path, run_id: str):
        self.root = root
        self.run_id = run_id
        self.run_root = root / "runs" / run_id
        self.events_path = self.run_root / "journal" / "events.jsonl"
        self._artifacts: list[dict[str, Any]] = []

    def initialize(self) -> dict[str, Any]:
        for name in (
            "input",
            "plan",
            "approval",
            "environment",
            "locks",
            "stage",
            "validation",
            "activation",
            "rollback",
            "journal",
            "closeout",
        ):
            (self.run_root / name).mkdir(parents=True, mode=0o700, exist_ok=True)
        self.append_event("run_initialized", {})
        return {"run_id": self.run_id, "run_root": str(self.run_root), "initialized": True}

    def resolve(self, relative_path: str) -> Path:
        rel = _safe_relative_path(relative_path)
        path = self.run_root / rel.as_posix()
        try:
            path.resolve(strict=False).relative_to(self.run_root.resolve(strict=False))
        except ValueError as exc:
            raise SyncPlannerError("artifact_path_escape", exit_code=2) from exc
        return path

    def atomic_write_text(self, relative_path: str, content: str) -> Path:
        path = self.resolve(relative_path)
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        tmp.write_text(content, encoding="utf-8")
        with tmp.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        _fsync_parent(path)
        self._artifacts.append(
            {
                "relative_path": str(_safe_relative_path(relative_path)),
                "sha256": file_sha256(path),
                "size": path.stat().st_size,
            }
        )
        return path

    def write_json(self, relative_path: str, value: Any) -> Path:
        rendered = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        return self.atomic_write_text(relative_path, rendered)

    def append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        record = {"event_type": event_type, "payload": payload}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def read_events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                events.append(item)
        return events

    def finalize(self) -> dict[str, Any]:
        sha_rows: list[str] = []
        for path in sorted(self.run_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(self.run_root).as_posix()
            if rel in {"sha256sums.txt", "artifact_index.json"}:
                continue
            sha_rows.append(f"{file_sha256(path)}  {rel}")
        index = {
            "schema_version": "agent_sync_artifact_index_v1",
            "run_id": self.run_id,
            "artifacts": self._artifacts,
            "sha256sums": sha_rows,
        }
        self.write_json("artifact_index.json", index)
        self.atomic_write_text("sha256sums.txt", "\n".join(sha_rows) + "\n")
        return index
