# ruff: noqa: D101, D103
"""Filesystem safety helpers for read-only sync planning."""

from __future__ import annotations

import os
import re
import stat
import tokenize
import unicodedata
from io import BytesIO
from pathlib import Path
from typing import Literal, TypedDict

from react_agent.ops.sync_contracts import SyncPlannerError

MAX_SOURCE_FILE_BYTES = 25 * 1024 * 1024
EXCLUDED_DIR_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    ".claude",
    ".history",
    ".cache",
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
    "tmp",
    "temp",
    "output",
    "outputs",
    "runs",
    "artifacts",
    "results",
    "reports",
    "dist",
    "build",
    "backups",
    "backup",
    "data",
    "dataset",
    "datasets",
    "models",
    "weights",
    "sample_requests.bak_v22_20260607_082218",
    "tests.bak_v22_20260607_082218",
}
EXCLUDED_FILE_NAMES = {".env", ".env.local", ".env.production", ".env.dev"}
EDITOR_LOCAL_DIR_NAMES = {".idea", ".vscode", ".claude", ".history"}
GENERATED_DIR_NAMES = {"artifacts", "output", "outputs", "runs", "reports"}
EXPERIMENT_RESULT_DIR_NAMES = {"results"}
RUNTIME_NOISE_DIR_NAMES = {"logs", "log", "cache", "caches", "tmp", "temp"}
DATA_ASSET_DIR_NAMES = {"data", "dataset", "datasets"}
MODEL_ASSET_DIR_NAMES = {"models", "weights"}
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
    ".html",
    ".css",
    ".jsonl",
    ".vue",
    ".bat",
}
SOURCE_BASENAMES = {
    ".gitignore",
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
PACKAGE_LOCKFILE_BASENAMES = {
    "Cargo.lock",
    "pdm.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}
SECRET_NAME_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|passwd|token|credential|private[_-]?key|dsn)"
)
SECRET_CONTENT_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|passwd|token|credential|private[_-]?key|dsn)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
)
BACKUP_FILE_RE = re.compile(
    r"(?i)(\.?[^/]*\.bak($|[._-].*)|\.?[^/]*\.backup($|\..*)|\.?[^/]*bak_[^/]*|\.?[^/]*_bak_[^/]*|"
    r"\.?opt_bak_[^/]*|\.?snapshot_bak_[^/]*|_backup_[^/]*|backup_[^/]*|.*_predeploy_.*|"
    r".*\.orig($|\..*)|.*\.rej($|\..*)|.*~$|.*\.swp$|\.DS_Store$)"
)
MATERIALIZABLE_SOURCE_CATEGORIES = {
    "source_code",
    "schema_protocol",
    "contract_test",
    "offline_test",
    "documentation",
    "startup_runbook",
    "package_metadata",
}
EXPLICIT_ASSET_SOURCE_CATEGORIES = {"runtime_static_asset", "test_fixture", "legacy_reference"}
NON_MATERIALIZABLE_SOURCE_CATEGORIES = {
    "generated_artifact",
    "experiment_result",
    "data_asset",
    "model_asset",
    "backup_artifact",
    "editor_local_metadata",
    "runtime_noise",
    "sensitive_blocked",
    "unknown_blocked",
}


class FileSafety(TypedDict):
    include: bool
    classification: str
    sensitive_classification: str
    large_asset_classification: str
    source_category: str
    source_category_reason: str
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
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    if not sample:
        return True
    textish = sum(1 for byte in sample if byte in b"\t\n\r" or 32 <= byte <= 126 or byte >= 128)
    return textish / len(sample) >= 0.85
    return False


def _relative_parts(root: Path, path: Path) -> tuple[str, ...]:
    try:
        return path.relative_to(root).parts
    except ValueError:
        return path.parts


def _has_dir(parts: tuple[str, ...], names: set[str]) -> bool:
    return any(part in names for part in parts[:-1])


def _has_generated_dir(parts: tuple[str, ...]) -> bool:
    for part in parts[:-1]:
        if part in GENERATED_DIR_NAMES or "output" in part or part.endswith("_out"):
            return True
    return False


def _has_backup_dir(parts: tuple[str, ...]) -> bool:
    return any(BACKUP_FILE_RE.match(part) for part in parts)


def classify_source_category(root: Path, path: Path, *, explicit_asset: bool = False) -> tuple[str, str]:
    """Classify a source candidate into a single sync role."""
    rel_parts = _relative_parts(root, path)
    lower_parts = tuple(part.lower() for part in rel_parts)
    suffix = path.suffix.lower()
    name = path.name
    lower_name = name.lower()
    if name in EXCLUDED_FILE_NAMES or lower_name.startswith(".env") or suffix == ".env":
        return "sensitive_blocked", "env_or_secret_file"
    if _has_backup_dir(rel_parts):
        return "backup_artifact", "backup_name_pattern"
    if _has_dir(lower_parts, EDITOR_LOCAL_DIR_NAMES) or any(part.startswith(".") for part in lower_parts[:-1]):
        return "editor_local_metadata", "editor_or_local_tool_directory"
    if _has_dir(lower_parts, RUNTIME_NOISE_DIR_NAMES):
        return "runtime_noise", "runtime_noise_directory"
    if _has_generated_dir(lower_parts):
        return ("runtime_static_asset", "explicit_runtime_asset_manifest") if explicit_asset else ("generated_artifact", "generated_artifact_directory")
    if _has_dir(lower_parts, EXPERIMENT_RESULT_DIR_NAMES):
        return ("test_fixture", "explicit_test_fixture_manifest") if explicit_asset else ("experiment_result", "experiment_result_directory")
    if _has_dir(lower_parts, DATA_ASSET_DIR_NAMES):
        return ("test_fixture", "explicit_test_fixture_manifest") if explicit_asset else ("data_asset", "data_asset_directory")
    if _has_dir(lower_parts, MODEL_ASSET_DIR_NAMES) or suffix in {".pkl", ".pt", ".pth", ".onnx", ".safetensors", ".joblib", ".model"}:
        return "model_asset", "model_asset"
    if lower_name in {".docx", ".pdf", ".xlsx"}:
        return "generated_artifact", "hidden_document_artifact"
    if lower_name == ".gitkeep":
        return "runtime_noise", "empty_directory_marker"
    if suffix in {".log", ".pid", ".flag", ".tsbuildinfo", ".tfevents"}:
        return "runtime_noise", "runtime_noise_extension"
    if suffix in {".parquet", ".csv", ".tsv", ".xlsx"}:
        return ("test_fixture", "explicit_test_fixture_manifest") if explicit_asset else ("data_asset", "tabular_data_asset")
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".docx"}:
        return "generated_artifact", "report_or_figure_artifact"
    if suffix in {".zip", ".rar", ".tgz", ".tar", ".gz"}:
        return "generated_artifact", "archive_artifact"
    if name in PACKAGE_LOCKFILE_BASENAMES or lower_name in {item.lower() for item in PACKAGE_LOCKFILE_BASENAMES}:
        return "package_metadata", "package_lockfile_metadata"
    if name in SOURCE_BASENAMES or lower_name in {item.lower() for item in SOURCE_BASENAMES}:
        if "runbook" in lower_name or "startup" in lower_name:
            return "startup_runbook", "startup_or_runbook_basename"
        return "package_metadata", "package_or_repo_metadata"
    if suffix in {".py", ".pyi", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".sh", ".ps1", ".vue", ".bat"}:
        if any(part in {"tests", "test"} for part in lower_parts[:-1]):
            return "contract_test", "test_source_path"
        return "source_code", "source_extension"
    if suffix in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}:
        if any(part in {"schemas", "schema", "protocol", "protocols"} for part in lower_parts[:-1]) or "schema" in lower_name:
            return "schema_protocol", "schema_or_protocol_path"
        if any(part in {"tests", "fixtures", "fixture"} for part in lower_parts[:-1]):
            return "test_fixture", "test_fixture_path"
        if "config" in lower_name or any(part in {"config", "configs"} for part in lower_parts[:-1]):
            return "schema_protocol", "configuration_file"
        return "schema_protocol", "structured_configuration"
    if suffix in {".md", ".rst", ".txt", ".jsonl"}:
        if "runbook" in lower_name or "startup" in lower_name:
            return "startup_runbook", "startup_or_runbook_document"
        if any(part in {"tests", "fixtures", "fixture"} for part in lower_parts[:-1]):
            return "test_fixture", "test_fixture_path"
        return "documentation", "documentation_or_text_resource"
    if not suffix and _looks_text(path, path.lstat().st_size):
        return "documentation", "extensionless_safe_text"
    return "unknown_blocked", "unknown_file_type_or_binary"


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


def redacted_structural_fingerprint(path: Path) -> dict[str, object]:
    """Return a secret-safe structural fingerprint for a source file."""
    try:
        data = path.read_bytes()
    except OSError:
        return {
            "algorithm": "redacted_python_token_fingerprint_v1",
            "status": "manual_sanitized_derivative_refresh_required",
            "finding_category_count": 0,
            "safe_line_ranges": [],
            "redacted_source_sha256": "",
        }
    text = data.decode("utf-8", errors="ignore")
    safe_lines = _line_ranges_for_secret(text)
    if not safe_lines and SECRET_NAME_RE.search(path.name):
        safe_lines = ["filename"]
    sensitive_lines = {int(item) for item in safe_lines if item.isdigit()}
    pieces: list[str] = []
    status = "ok"
    try:
        tokens = tokenize.tokenize(BytesIO(data).readline)
        for token in tokens:
            if token.type in {tokenize.ENCODING, tokenize.ENDMARKER}:
                continue
            if token.type == tokenize.STRING and token.start[0] in sensitive_lines:
                pieces.append("<REDACTED_SECRET_LITERAL>")
            else:
                pieces.append(token.string)
    except tokenize.TokenError:
        status = "manual_sanitized_derivative_refresh_required"
        for lineno, line in enumerate(text.splitlines(), start=1):
            if lineno in sensitive_lines:
                pieces.append("<REDACTED_SECRET_LITERAL>")
            else:
                pieces.append(line)
    normalized = unicodedata.normalize("NFC", "\n".join(pieces).replace("\r\n", "\n").replace("\r", "\n"))
    import hashlib

    return {
        "algorithm": "redacted_python_token_fingerprint_v1",
        "status": status,
        "finding_category_count": len(safe_lines),
        "safe_line_ranges": safe_lines,
        "redacted_source_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    }


def classify_large_asset(path: Path, *, size: int) -> str:
    if size > MAX_SOURCE_FILE_BYTES:
        return "reference_only_large_asset"
    if path.suffix.lower() in {".db", ".sqlite", ".parquet", ".pkl", ".pt", ".bin", ".onnx", ".safetensors"}:
        return "reference_only_binary_or_data"
    return "not_large_asset"


def should_include_source_file(root: Path, path: Path, *, explicit_asset: bool = False) -> FileSafety:
    rel = path.relative_to(root)
    rel_parts = rel.parts
    source_category, source_category_reason = classify_source_category(root, path, explicit_asset=explicit_asset)
    if any(part in EXCLUDED_DIR_NAMES for part in rel_parts[:-1]):
        return {
            "include": False,
            "classification": "excluded_directory",
            "sensitive_classification": "not_scanned",
            "large_asset_classification": "not_large_asset",
            "source_category": source_category,
            "source_category_reason": source_category_reason,
            "reason": "excluded_directory",
        }
    if BACKUP_FILE_RE.match(path.name):
        return {
            "include": False,
            "classification": "excluded_backup_artifact",
            "sensitive_classification": "not_scanned",
            "large_asset_classification": "not_large_asset",
            "source_category": "backup_artifact",
            "source_category_reason": "backup_name_pattern",
            "reason": "backup_runtime_noise",
        }
    stat_result = path.lstat()
    file_type = classify_file_type(stat_result.st_mode)
    if stat_result.st_mode & (stat.S_ISUID | stat.S_ISGID):
        return {
            "include": False,
            "classification": "blocked_setuid_setgid",
            "sensitive_classification": "not_scanned",
            "large_asset_classification": "not_large_asset",
            "source_category": source_category,
            "source_category_reason": source_category_reason,
            "reason": "setuid_setgid",
        }
    if file_type == "symlink":
        decision, reason = safe_symlink_decision(root, path)
        return {
            "include": decision == "safe_relative_symlink",
            "classification": decision,
            "sensitive_classification": "not_scanned",
            "large_asset_classification": "not_large_asset",
            "source_category": source_category,
            "source_category_reason": source_category_reason,
            "reason": reason,
        }
    if file_type != "regular":
        return {
            "include": False,
            "classification": f"blocked_{file_type}",
            "sensitive_classification": "not_scanned",
            "large_asset_classification": "not_large_asset",
            "source_category": source_category,
            "source_category_reason": source_category_reason,
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
            "source_category": "sensitive_blocked",
            "source_category_reason": sensitive,
            "reason": sensitive,
        }
    if large != "not_large_asset":
        return {
            "include": False,
            "classification": "large_asset_reference",
            "sensitive_classification": sensitive,
            "large_asset_classification": large,
            "source_category": source_category,
            "source_category_reason": source_category_reason,
            "reason": large,
        }
    if source_category in MATERIALIZABLE_SOURCE_CATEGORIES or (explicit_asset and source_category in EXPLICIT_ASSET_SOURCE_CATEGORIES):
        return {
            "include": True,
            "classification": "source_bearing",
            "sensitive_classification": sensitive,
            "large_asset_classification": large,
            "source_category": source_category,
            "source_category_reason": source_category_reason,
            "reason": f"included_{source_category}",
        }
    return {
        "include": False,
        "classification": f"excluded_{source_category}",
        "sensitive_classification": sensitive,
        "large_asset_classification": large,
        "source_category": source_category,
        "source_category_reason": source_category_reason,
        "reason": source_category_reason,
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
