# ruff: noqa: D101, D103
"""Artifact path validation helpers for sync planner outputs."""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import PurePosixPath
from pathlib import Path
from typing import Any


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

