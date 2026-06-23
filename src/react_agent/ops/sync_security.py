# ruff: noqa: D101, D103
"""Filesystem safety helpers for read-only sync planning."""

from __future__ import annotations

import os
import re
import stat
import unicodedata
from pathlib import Path
from typing import Literal, TypedDict

from react_agent.ops.sync_contracts import SyncPlannerError

MAX_SOURCE_FILE_BYTES = 25 * 1024 * 1024
EXCLUDED_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "logs",
    "log",
    "cache",
    "caches",
    "output",
    "outputs",
    "dist",
    "build",
    "backups",
    "backup",
    "data",
    "dataset",
    "datasets",
    "models",
    "weights",
}
EXCLUDED_FILE_NAMES = {".env", ".env.local", ".env.production", ".env.dev"}
SOURCE_EXTENSIONS = {
    ".py",
    ".pyi",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".md",
    ".txt",
    ".sh",
    ".ps1",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
}
SOURCE_BASENAMES = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "README",
    "README.md",
}
SECRET_NAME_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|passwd|token|credential|private[_-]?key|dsn)"
)
SECRET_CONTENT_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|passwd|token|credential|private[_-]?key|dsn)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
)


class FileSafety(TypedDict):
    include: bool
    classification: str
    sensitive_classification: str
    large_asset_classification: str
    reason: str


def normalize_safe_relative_path(path: str | Path) -> str:
    raw = os.fspath(path)
    if "\x00" in raw:
        raise SyncPlannerError("unsafe_path_nul", exit_code=2)
    normalized = unicodedata.normalize("NFC", raw.replace("\\", "/"))
    candidate = Path(normalized)
    if candidate.is_absolute():
        raise SyncPlannerError("unsafe_path_absolute", exit_code=2)
    parts = candidate.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise SyncPlannerError("unsafe_path_traversal", exit_code=2)
    return "/".join(parts)


def validate_root_containment(root: Path, path: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise SyncPlannerError("root_escape", exit_code=2) from exc


def is_allowed_root(path: Path) -> bool:
    text = str(path)
    return text.startswith(("/sdb/dlut/prod", "/sdb/dlut/sandbox", "/sdb/dlut/dev", "/tmp/"))


def classify_file_type(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "regular"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISCHR(mode):
        return "character_device"
    if stat.S_ISBLK(mode):
        return "block_device"
    return "unknown_special"


def safe_symlink_decision(root: Path, link_path: Path) -> tuple[str, str]:
    target = os.readlink(link_path)
    if "\x00" in target:
        return "blocked", "symlink_target_nul"
    target_path = Path(target)
    if target_path.is_absolute():
        return "blocked", "external_symlink_absolute"
    resolved = (link_path.parent / target_path).resolve(strict=False)
    try:
        resolved.relative_to(root.resolve(strict=False))
    except ValueError:
        return "blocked", "external_symlink_escape"
    return "safe_relative_symlink", target.replace("\\", "/")


def _looks_text(path: Path, size: int) -> bool:
    if size > MAX_SOURCE_FILE_BYTES:
        return False
    if path.name in SOURCE_BASENAMES or path.suffix in SOURCE_EXTENSIONS:
        return True
    return False


def _line_ranges_for_secret(content: str) -> list[str]:
    ranges: list[str] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if SECRET_CONTENT_RE.search(line):
            ranges.append(str(lineno))
    return ranges[:20]


def classify_sensitive_source(path: Path, *, size: int) -> tuple[str, list[str]]:
    name = path.name
    if name in EXCLUDED_FILE_NAMES or name.startswith(".env."):
        return "blocked_env_file", []
    if SECRET_NAME_RE.search(name):
        return "sensitive_name", []
    if not _looks_text(path, size):
        return "not_scanned", []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "unreadable", []
    ranges = _line_ranges_for_secret(content)
    if ranges:
        return "potential_secret_literal", ranges
    return "none", []


def classify_large_asset(path: Path, *, size: int) -> str:
    if size > MAX_SOURCE_FILE_BYTES:
        return "reference_only_large_asset"
    if path.suffix.lower() in {".db", ".sqlite", ".parquet", ".pkl", ".pt", ".bin", ".onnx", ".safetensors"}:
        return "reference_only_binary_or_data"
    return "not_large_asset"


def should_include_source_file(root: Path, path: Path) -> FileSafety:
    rel = path.relative_to(root)
    rel_parts = rel.parts
    if any(part in EXCLUDED_DIR_NAMES for part in rel_parts[:-1]):
        return {
            "include": False,
            "classification": "excluded_directory",
            "sensitive_classification": "not_scanned",
            "large_asset_classification": "not_large_asset",
            "reason": "excluded_directory",
        }
    stat_result = path.lstat()
    file_type = classify_file_type(stat_result.st_mode)
    if stat_result.st_mode & (stat.S_ISUID | stat.S_ISGID):
        return {
            "include": False,
            "classification": "blocked_setuid_setgid",
            "sensitive_classification": "not_scanned",
            "large_asset_classification": "not_large_asset",
            "reason": "setuid_setgid",
        }
    if file_type == "symlink":
        decision, reason = safe_symlink_decision(root, path)
        return {
            "include": decision == "safe_relative_symlink",
            "classification": decision,
            "sensitive_classification": "not_scanned",
            "large_asset_classification": "not_large_asset",
            "reason": reason,
        }
    if file_type != "regular":
        return {
            "include": False,
            "classification": f"blocked_{file_type}",
            "sensitive_classification": "not_scanned",
            "large_asset_classification": "not_large_asset",
            "reason": file_type,
        }
    large = classify_large_asset(path, size=stat_result.st_size)
    sensitive, _ranges = classify_sensitive_source(path, size=stat_result.st_size)
    if sensitive in {"blocked_env_file", "potential_secret_literal"}:
        return {
            "include": False,
            "classification": "blocked_sensitive_source",
            "sensitive_classification": sensitive,
            "large_asset_classification": large,
            "reason": sensitive,
        }
    if large != "not_large_asset":
        return {
            "include": False,
            "classification": "large_asset_reference",
            "sensitive_classification": sensitive,
            "large_asset_classification": large,
            "reason": large,
        }
    if path.name in SOURCE_BASENAMES or path.suffix in SOURCE_EXTENSIONS:
        return {
            "include": True,
            "classification": "source_bearing",
            "sensitive_classification": sensitive,
            "large_asset_classification": large,
            "reason": "included_source_bearing",
        }
    return {
        "include": False,
        "classification": "excluded_non_source",
        "sensitive_classification": sensitive,
        "large_asset_classification": large,
        "reason": "extension_not_in_include_profile",
    }


def detect_unicode_collision(paths: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for path in paths:
        normalized = unicodedata.normalize("NFC", path)
        previous = seen.get(normalized)
        if previous is not None and previous != path:
            collisions.append(normalized)
        seen[normalized] = path
    return collisions


Operation = Literal["add", "replace", "delete", "omit", "sanitize", "noop"]

