# ruff: noqa: D101, D102, D103, D107
"""Artifact path validation helpers for sync planner outputs."""

from __future__ import annotations

import json
import os
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from react_agent.ops.sync_contracts import SyncPlannerError, file_sha256


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
