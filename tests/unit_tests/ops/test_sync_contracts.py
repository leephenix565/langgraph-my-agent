"""Tests for sync planner contracts and canonical hashes."""

from __future__ import annotations

import json

import pytest

from react_agent.ops.sync_contracts import (
    EXAMPLES_DIR,
    SCHEMAS_DIR,
    SyncPlannerError,
    canonical_sha256,
    read_json,
    validate_by_schema_version,
    validate_schema_meta,
)


def test_all_sync_schemas_are_real_draft_2020_12() -> None:
    for path in SCHEMAS_DIR.glob("*.schema.json"):
        schema = read_json(path)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        validate_schema_meta(schema)


def test_examples_validate_against_schemas() -> None:
    for path in EXAMPLES_DIR.glob("*.json"):
        if path.name == "canonical_hash_test_vectors.json":
            continue
        instance = read_json(path)
        if isinstance(instance, dict) and "schema_version" in instance:
            validate_by_schema_version(instance)


def test_invalid_schema_payload_fails() -> None:
    with pytest.raises(SyncPlannerError) as exc:
        validate_by_schema_version({"schema_version": "agent_sync_plan_v1", "direction": "invalid"})
    assert exc.value.reason == "json_schema_validation_failed"


def test_canonical_hash_freeze_vectors() -> None:
    vectors = json.loads((EXAMPLES_DIR / "canonical_hash_test_vectors.json").read_text(encoding="utf-8"))
    for vector in vectors:
        assert canonical_sha256(vector["input"]) == vector["canonical_sha256"]


def test_canonical_hash_stability_and_mutation() -> None:
    left = {"b": 2, "a": 1, "canonical_sha256": "old"}
    right = {"canonical_sha256": "new", "a": 1, "b": 2}
    assert canonical_sha256(left) == canonical_sha256(right)
    assert canonical_sha256({"path": "中文路径/a.py"}) == canonical_sha256({"path": "中文路径/a.py"})
    assert canonical_sha256({"items": ["a", "b"]}) != canonical_sha256({"items": ["b", "a"]})
    assert canonical_sha256({"timestamp": "2026-06-23T00:00:00Z"}) != canonical_sha256(
        {"timestamp": "2026-06-23T00:00:01Z"}
    )
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})


def test_canonical_hash_rejects_nan() -> None:
    with pytest.raises(SyncPlannerError) as exc:
        canonical_sha256({"bad": float("nan")})
    assert exc.value.reason == "non_finite_json_number"

