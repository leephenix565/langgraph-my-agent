"""Regression tests for SYNC-OPS-1R P2S write-safety planning."""

from __future__ import annotations

import json
import zipfile
from functools import lru_cache
from pathlib import Path

import pytest

from react_agent.ops.sync_artifacts import (
    create_posix_zip_archive,
    validate_archive_member_names,
)
from react_agent.ops.sync_plan import build_p2s_plan, validate_plan
from react_agent.ops.sync_security import should_include_source_file

OLD_PLAN = Path("/tmp/lma-sync-ops-1-planner-mvp-20260623T090531Z/current_p2s_plan.json")


@lru_cache(maxsize=1)
def _current_plan() -> dict[str, object]:
    return build_p2s_plan()


def _actions(plan: dict[str, object]) -> list[dict[str, object]]:
    return [
        action
        for agent in plan.get("agents", [])
        if isinstance(agent, dict)
        for action in agent.get("actions", [])
        if isinstance(action, dict)
    ]


def test_old_p2s_plan_is_rejected_with_bounded_reasons() -> None:
    old_plan = json.loads(OLD_PLAN.read_text(encoding="utf-8"))
    result = validate_plan(old_plan, check_target_freshness=False)
    assert result["valid"] is False
    blockers = set(result["blockers"])
    assert "p2s_stage_materialization_missing" in blockers
    assert "p2s_activation_missing" in blockers
    assert "p2s_agent_active_sandbox_target_root" in blockers
    assert "p2s_agent_target_before_tree_sha256_missing" in blockers
    assert "p2s_copy_source_sha256_missing" in blockers


def test_repaired_p2s_plan_has_no_active_sandbox_targets_or_empty_copy_hashes() -> None:
    plan = _current_plan()
    result = validate_plan(plan, check_target_freshness=False)
    assert result["valid"] is True
    actions = _actions(plan)
    assert not [agent for agent in plan["agents"] if agent["target_root"] == "active_sandbox"]
    assert not [
        action
        for action in actions
        if action["operation"] == "copy_from_prod" and not action.get("source_sha256")
    ]
    assert not [
        action
        for action in actions
        if str(action.get("destination_relative_path", "")).endswith(".bak")
        or ".bak_" in str(action.get("destination_relative_path", ""))
        or "predeploy" in str(action.get("destination_relative_path", ""))
    ]


def test_repaired_p2s_plan_preserves_derivatives_and_metadata() -> None:
    plan = _current_plan()
    actions = _actions(plan)
    derivative_actions = [
        action for action in actions if action["operation"] == "preserve_sanitized_derivative"
    ]
    assert {action["agent_id"] for action in derivative_actions} == {
        "value_research_synthesis",
        "macro_index_valuation",
    }
    ordinary_sensitive = [
        action
        for action in actions
        if action.get("agent_id") in {"value_research_synthesis", "macro_index_valuation"}
        and action.get("destination_relative_path") in {"main5.py", "config.py"}
        and action.get("operation") == "copy_from_prod"
    ]
    assert ordinary_sensitive == []
    metadata = [
        action
        for action in actions
        if action["operation"] == "preserve_sandbox_metadata"
        and action.get("destination_relative_path") == "SANDBOX_SECRET_REQUIREMENTS.md"
    ]
    assert {action["agent_id"] for action in metadata} == {
        "value_research_synthesis",
        "macro_index_valuation",
    }


def test_repaired_p2s_plan_has_26_dispositions_and_shared_member() -> None:
    plan = _current_plan()
    dispositions = {agent["agent_id"]: agent["disposition"] for agent in plan["agents"]}
    assert len(dispositions) == 26
    assert all(dispositions.values())
    assert dispositions["market_fund_manager_behavior"] == "shared_transaction_member"
    assert dispositions["macro_sentiment"] == "semantic_placeholder_snapshot"
    assert dispositions["macro_industry_hotspot"] == "semantic_placeholder_snapshot"
    assert all(agent["target_before_tree_sha256"] for agent in plan["agents"])


def test_recursive_p2s_plan_repairs_previous_no_source_misclassifications() -> None:
    plan = _current_plan()
    by_id = {agent["agent_id"]: agent for agent in plan["agents"]}
    assert by_id["financial_data_service"]["current_safe_source_file_count"] > 0
    assert by_id["entity_relation_extractor"]["current_safe_source_file_count"] > 0
    assert by_id["sentiment_company_radar"]["current_safe_source_file_count"] > 0
    assert by_id["risk_crash"]["current_safe_source_file_count"] > 100
    assert plan["coverage"]["coverage_ratio"] == 1.0
    assert plan["coverage"]["shared_transaction_file_count"] > 0
    assert plan["stage_materialization"]["expected_stage_projection_digest"]


def test_backup_filename_policy_excludes_runtime_noise(tmp_path: Path) -> None:
    backup = tmp_path / "opt_pe_model.bak_predeploy_20260620_085255.json"
    backup.write_text('{"x": 1}\n', encoding="utf-8")
    legit = tmp_path / "schema_versioned_fixture.json"
    legit.write_text('{"x": 1}\n', encoding="utf-8")
    assert should_include_source_file(tmp_path, backup)["classification"] == "excluded_backup_artifact"
    assert should_include_source_file(tmp_path, legit)["include"] is True


def test_archive_member_names_must_be_posix(tmp_path: Path) -> None:
    good_zip = tmp_path / "good.zip"
    with zipfile.ZipFile(good_zip, "w") as archive:
        archive.writestr("a/b.txt", "ok")
    assert validate_archive_member_names(good_zip)["all_archive_entries_posix"] is True

    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as archive:
        archive.writestr("a\\b.txt", "bad")
    with pytest.raises(ValueError, match="archive_entry_not_posix"):
        validate_archive_member_names(bad_zip)


def test_posix_zip_archive_helper_normalizes_nested_entries(tmp_path: Path) -> None:
    source = tmp_path / "source"
    nested = source / "guard_inputs"
    nested.mkdir(parents=True)
    (nested / "blocked_p2s_plan.json").write_text("{}\n", encoding="utf-8")
    (nested / "blocked_p2s_approval.json").write_text("{}\n", encoding="utf-8")
    archive = tmp_path / "artifact.zip"

    result = create_posix_zip_archive(source, archive)

    assert result["entry_count"] == 2
    assert result["backslash_entry_count"] == 0
    assert result["absolute_entry_count"] == 0
    assert result["traversal_entry_count"] == 0
    assert result["duplicate_normalized_entry_count"] == 0
    assert sorted(result["entries"]) == [
        "guard_inputs/blocked_p2s_approval.json",
        "guard_inputs/blocked_p2s_plan.json",
    ]

    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    with pytest.raises(ValueError, match="archive_entry_root_escape"):
        create_posix_zip_archive(source, tmp_path / "bad.zip", members=[outside])
