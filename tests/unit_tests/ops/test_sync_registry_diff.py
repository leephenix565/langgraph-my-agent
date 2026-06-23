"""Tests for static sync registry and B/S/P/D diff semantics."""

from __future__ import annotations

from copy import deepcopy

from react_agent.ops.sync_diff import classify_file_delta
from react_agent.ops.sync_registry import (
    external_catalog_ids,
    load_static_registry,
    validate_static_registry,
)


def _record(sha: str, *, include: bool = True, classification: str = "source_bearing") -> dict[str, str | bool]:
    return {"sha256": sha, "include": include, "classification": classification}


def test_static_registry_matches_catalog_and_keeps_review_warnings_nonfatal() -> None:
    registry = load_static_registry()
    validation = validate_static_registry(registry)
    assert validation["valid"] is True
    assert validation["formal_external_agent_count"] == 26
    assert {agent["agent_id"] for agent in registry["agents"]} == external_catalog_ids()
    assert not validation["fatal_conflicts"]
    assert validation["review_warnings"]


def test_registry_rejects_duplicate_and_sentiment_risk_route() -> None:
    registry = load_static_registry()
    broken = deepcopy(registry)
    broken["agents"][0]["agent_id"] = broken["agents"][1]["agent_id"]
    assert validate_static_registry(broken)["fatal_conflicts"]

    broken = deepcopy(registry)
    sentiment = next(agent for agent in broken["agents"] if agent["agent_id"] == "sentiment_company_radar")
    sentiment["routes_to"] = ["risk_composite"]
    reasons = {item["reason"] for item in validate_static_registry(broken)["fatal_conflicts"]}
    assert "sentiment_route_to_risk" in reasons


def test_diff_classifications_cover_core_cases() -> None:
    assert classify_file_delta(baseline=_record("a"), sandbox=_record("a"), prod=_record("a")) == "unchanged_all"
    assert classify_file_delta(baseline=_record("a"), sandbox=_record("b"), prod=_record("a")) == "changed_in_sandbox_only"
    assert classify_file_delta(baseline=_record("a"), sandbox=_record("a"), prod=_record("b")) == "changed_in_prod_only"
    assert classify_file_delta(baseline=_record("a"), sandbox=_record("b"), prod=_record("b")) == "sandbox_and_prod_same_change"
    assert classify_file_delta(baseline=_record("a"), sandbox=_record("b"), prod=_record("c")) == "sandbox_and_prod_diverged"
    assert classify_file_delta(
        baseline=_record("a"),
        sandbox=_record("b"),
        prod=_record("c"),
        sanitized_derivative=True,
    ) == "sanitized_derivative"
    assert (
        classify_file_delta(
            baseline=_record("a"),
            sandbox=_record("b"),
            prod=_record("", include=False, classification="blocked_sensitive_source"),
            sanitized_derivative=True,
        )
        == "sanitized_derivative"
    )
    assert (
        classify_file_delta(
            baseline=_record("a"),
            sandbox=_record("a"),
            prod=_record("", include=False, classification="excluded_backup_artifact"),
        )
        == "backup_runtime_noise"
    )
    assert classify_file_delta(baseline=_record("a"), sandbox=_record("b"), prod=_record("c"), semantic_placeholder=True) == "semantic_placeholder"
