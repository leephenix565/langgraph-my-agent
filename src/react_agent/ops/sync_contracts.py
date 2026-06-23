# ruff: noqa: D101, D103
"""Contracts and canonical JSON helpers for read-only agent sync planning."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_OPS_DIR = REPO_ROOT / "config" / "ops"
SCHEMAS_DIR = CONFIG_OPS_DIR / "schemas"
EXAMPLES_DIR = CONFIG_OPS_DIR / "examples"
REGISTRY_PATH = CONFIG_OPS_DIR / "agent_service_registry.json"
SYNC_POLICY_PATH = CONFIG_OPS_DIR / "agent_sync_policy.json"
CATALOG_PATH = REPO_ROOT / "config" / "fixed_dag" / "agent_catalog.json"

SCHEMA_FILES = {
    "agent_service_registry_v1": "agent_service_registry_v1.schema.json",
    "agent_sync_policy_v1": "sync_policy_v1.schema.json",
    "agent_sandbox_baseline_v1": "baseline_manifest_v1.schema.json",
    "agent_sync_experiment_v1": "experiment_manifest_v1.schema.json",
    "agent_sync_change_unit_v1": "change_unit_v1.schema.json",
    "agent_sync_plan_v1": "sync_plan_v1.schema.json",
    "agent_sync_approval_v1": "approval_record_v1.schema.json",
    "agent_sync_result_v1": "sync_result_v1.schema.json",
    "agent_sync_lock_v1": "sync_lock_v1.schema.json",
    "agent_sync_artifact_index_v1": "artifact_index_v1.schema.json",
}

READ_ONLY_UNSUPPORTED_COMMANDS = {
    ("s2p", "apply"),
    ("s2p", "smoke"),
    ("s2p", "rollback"),
    ("cycle", "publish-and-rebase"),
    ("lock", "force-release"),
}


class SyncPlannerError(RuntimeError):
    """Raised for planner validation and command errors."""

    def __init__(self, reason: str, *, exit_code: int = 2, details: Mapping[str, Any] | None = None):
        """Initialize an error with a stable CLI reason and exit code."""
        super().__init__(reason)
        self.reason = reason
        self.exit_code = exit_code
        self.details = dict(details or {})


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _normalize_for_json(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise SyncPlannerError("non_finite_json_number", exit_code=2)
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value).replace("\\", "/")
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, list):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, tuple) or isinstance(value, set):
        raise SyncPlannerError("unordered_or_unsupported_json_sequence", exit_code=2)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise SyncPlannerError("non_string_json_key", exit_code=2)
            normalized[unicodedata.normalize("NFC", key)] = _normalize_for_json(item)
        return normalized
    raise SyncPlannerError(f"unsupported_json_value:{type(value).__name__}", exit_code=2)


def canonical_json_bytes(value: Any, *, exclude_hash_field: bool = True) -> bytes:
    normalized = _normalize_for_json(value)
    if exclude_hash_field and isinstance(normalized, dict):
        normalized = {key: item for key, item in normalized.items() if key != "canonical_sha256"}
    rendered = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return rendered.encode("utf-8")


def canonical_sha256(value: Any, *, exclude_hash_field: bool = True) -> str:
    return hashlib.sha256(canonical_json_bytes(value, exclude_hash_field=exclude_hash_field)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonschema_module() -> Any:
    try:
        jsonschema = importlib.import_module("jsonschema")
        Draft202012Validator = getattr(jsonschema, "Draft202012Validator")
    except ImportError as exc:
        # Some reset hosts keep jsonschema in the system Python dist-packages
        # while the project .venv is editable-only. This still uses the real
        # Draft 2020-12 validator; if it is absent, planning fails closed.
        import sys

        system_dist = Path("/usr/lib/python3/dist-packages")
        if system_dist.exists() and str(system_dist) not in sys.path:
            sys.path.append(str(system_dist))
        try:
            jsonschema = importlib.import_module("jsonschema")
            Draft202012Validator = getattr(jsonschema, "Draft202012Validator")
        except ImportError:
            raise SyncPlannerError(
                "schema_validator_unavailable",
                exit_code=2,
                details={"dependency": "jsonschema", "required_validator": "Draft202012Validator"},
            ) from exc
    return jsonschema, Draft202012Validator


def validate_schema_meta(schema: Mapping[str, Any]) -> None:
    _jsonschema, validator_cls = _jsonschema_module()
    validator_cls.check_schema(schema)


def validate_instance(instance: Any, schema: Mapping[str, Any]) -> None:
    _jsonschema, validator_cls = _jsonschema_module()
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        path = ".".join(str(item) for item in first.path) or "$"
        raise SyncPlannerError(
            "json_schema_validation_failed",
            exit_code=2,
            details={"path": path, "message": first.message},
        )


def schema_for_version(schema_version: str) -> dict[str, Any]:
    filename = SCHEMA_FILES.get(schema_version)
    if not filename:
        raise SyncPlannerError(f"unknown_schema_version:{schema_version}", exit_code=2)
    schema = read_json(SCHEMAS_DIR / filename)
    if not isinstance(schema, dict):
        raise SyncPlannerError("schema_not_object", exit_code=2)
    return schema


def validate_by_schema_version(instance: Mapping[str, Any]) -> None:
    schema_version = str(instance.get("schema_version") or "")
    schema = schema_for_version(schema_version)
    validate_schema_meta(schema)
    validate_instance(instance, schema)


def load_and_validate(path: Path) -> Any:
    instance = read_json(path)
    if isinstance(instance, Mapping) and "schema_version" in instance:
        validate_by_schema_version(instance)
    return instance


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def parse_utc(value: str) -> str:
    if not value.endswith("Z") or "T" not in value:
        raise SyncPlannerError("invalid_utc_timestamp", exit_code=2)
    return value


def ensure_output_path(path_text: str | None) -> Path | None:
    if not path_text:
        return None
    path = Path(path_text)
    if path.exists() and path.is_dir():
        raise SyncPlannerError("output_path_is_directory", exit_code=2)
    return path


def maybe_write_json(path: Path | None, value: Any) -> None:
    if path is not None:
        write_json(path, value)


def render_summary(title: str, rows: Sequence[str]) -> str:
    body = "\n".join(f"- {row}" for row in rows)
    return f"{title}\n{body}\n"


def print_or_json(args: argparse.Namespace, payload: Mapping[str, Any], human_rows: Sequence[str]) -> int:
    output = ensure_output_path(getattr(args, "json_output", None))
    if output:
        write_json(output, payload)
    if getattr(args, "stdout_json", False):
        import sys

        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    else:
        import sys

        sys.stdout.write(render_summary(str(payload.get("summary_title") or "agent-sync"), human_rows))
    return int(payload.get("exit_code", 0) or 0)
