"""Focused publish-and-rebase cycle tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from react_agent.ops.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    file_sha256,
)
from react_agent.ops.sync_cycle import (
    archive_policy_summary,
    build_cycle_approval_bundle,
    build_cycle_plan_from_experiment,
    build_cycle_plan_from_s2p,
    recover_cycle,
    run_cycle_noop,
    run_temp_nonzero_cycle,
    validate_cycle_approval_bundle,
    validate_cycle_plan,
)
from react_agent.ops.sync_s2p import (
    build_experiment_fork,
    build_s2p_plan_v2,
    compare_digest_descriptors,
    digest_descriptor,
)


def test_s2p_mapping_repairs_empty_and_shared_members(tmp_path: Path) -> None:
    manifest = build_experiment_fork(workspace_root=tmp_path / "experiment", experiment_id="exp_cycle_mapping")
    plan = build_s2p_plan_v2(manifest)

    fraud = next(agent for agent in plan["agents"] if agent["agent_id"] == "risk_financial_fraud")
    assert fraud["baseline_tree_sha256"]
    assert fraud["experiment_tree_sha256"]
    assert fraud["baseline_descriptor"]["file_count"] == 0
    assert fraud["experiment_descriptor"]["file_count"] == 0

    fund = next(agent for agent in plan["agents"] if agent["agent_id"] == "market_fund_manager_behavior")
    market = next(agent for agent in plan["agents"] if agent["agent_id"] == "market_composite")
    assert fund["agent_role"] == "shared_transaction_member"
    assert fund["owner_agent_id"] == "market_composite"
    assert fund["owner_transaction_id"] == market["transaction_id"]
    assert fund["independent_apply"] is False
    assert fund["baseline_tree_sha256"]
    assert fund["experiment_tree_sha256"]
    assert plan["s2p_summary"]["transaction_count"] == 25


def test_digest_descriptor_rejects_scope_mismatch() -> None:
    left = digest_descriptor(digest="abc", scope="p2s_stage_projection", root_role="stage")
    right = digest_descriptor(digest="abc", scope="p2s_active_safe_tree", root_role="active")
    assert compare_digest_descriptors(left, left)["match"] is True
    mismatch = compare_digest_descriptors(left, right)
    assert mismatch["compatible"] is False
    assert mismatch["reason"] == "digest_scope_mismatch"


def test_cycle_plan_embeds_projection_and_precomputed_p2s(tmp_path: Path) -> None:
    manifest = build_experiment_fork(workspace_root=tmp_path / "experiment", experiment_id="exp_cycle_plan")
    s2p = build_s2p_plan_v2(manifest)
    cycle = build_cycle_plan_from_s2p(s2p)
    validation = validate_cycle_plan(cycle)

    assert validation["valid"] is True
    assert cycle["schema_version"] == "agent_sync_publish_and_rebase_cycle_v1"
    assert cycle["mode"] == "strict_all_or_nothing"
    assert cycle["projected_prod_after_state"]["projected_combined_prod_descriptor"]["scope"] == "s2p_prod_inventory"
    transaction_ids = [row["transaction_id"] for row in cycle["projected_prod_after_state"]["transactions"]]
    assert len(transaction_ids) == len(set(transaction_ids))
    assert cycle["p2s_plan"]["canonical_sha256"]
    assert cycle["p2s_plan"]["p2s_action_count"] == 0


def test_cycle_approval_bundle_rejects_noop_action_scope(tmp_path: Path) -> None:
    manifest = build_experiment_fork(workspace_root=tmp_path / "experiment", experiment_id="exp_cycle_bundle")
    cycle = build_cycle_plan_from_experiment(manifest)
    bundle = build_cycle_approval_bundle(cycle, operator_reference="unit-test")
    assert validate_cycle_approval_bundle(bundle, cycle, require_noop=True)["valid"] is True

    bundle["approved_s2p_action_ids"] = ["unexpected"]
    result = validate_cycle_approval_bundle(bundle, cycle, require_noop=True)
    assert result["valid"] is False
    assert "noop_bundle_s2p_action_scope_not_empty" in result["blockers"]


def _minimal_noop_cycle(tmp_path: Path) -> tuple[dict, dict]:
    prod = tmp_path / "prod" / "agent"
    prod.mkdir(parents=True)
    (prod / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
    descriptor = digest_descriptor(
        digest=file_sha256(prod / "service.py"),
        scope="s2p_prod_inventory",
        root_role="prod",
        file_count=1,
    )
    cycle = {
        "schema_version": "agent_sync_publish_and_rebase_cycle_v1",
        "cycle_id": "cycle_unit_noop",
        "created_at": "2026-06-24T00:00:00Z",
        "expires_at": "2026-06-25T00:00:00Z",
        "mode": "strict_all_or_nothing",
        "experiment": {"manifest_sha256": "experiment-sha"},
        "registry_sha256": "registry",
        "policy_sha256": "policy",
        "catalog_sha256": "catalog",
        "baseline": {},
        "s2p_plan": {
            "plan_id": "s2p_unit",
            "plan_sha256": "s2p-sha",
            "summary": {"actionable_file_action_count": 0},
            "validation": {"valid": True},
        },
        "projected_prod_after_state": {
            "schema_version": "agent_sync_projected_prod_state_v1",
            "transactions": [
                {
                    "agent_id": "agent",
                    "transaction_id": "txn_agent",
                    "target_prod_root": str(prod),
                    "target_before_descriptor": descriptor,
                    "projected_target_after_descriptor": descriptor,
                    "action_count": 0,
                }
            ],
            "projected_combined_prod_descriptor": descriptor,
        },
        "p2s_plan": {
            "plan_id": "p2s_unit",
            "canonical_sha256": "p2s-sha",
            "p2s_action_count": 0,
        },
        "approval_requirements": {"noop_cycle_approved": True},
        "failure_policy": {"strict_all_or_nothing": True},
        "recovery_policy": {"journal_required": True},
        "canonical_sha256": "",
    }
    cycle["canonical_sha256"] = canonical_sha256(cycle)
    bundle = build_cycle_approval_bundle(cycle, operator_reference="unit-test")
    return cycle, bundle


def test_cycle_noop_run_records_no_writes(tmp_path: Path) -> None:
    cycle, bundle = _minimal_noop_cycle(tmp_path)
    result = run_cycle_noop(cycle, bundle, tmp_path / "artifact-store")
    assert result["valid"] is True
    assert result["s2p_action_count"] == 0
    assert result["p2s_action_count"] == 0
    assert result["prod_unchanged"] is True
    assert result["pointer_unchanged"] is True


def test_cycle_nonzero_rehearsal_and_recovery(tmp_path: Path) -> None:
    result = run_temp_nonzero_cycle(tmp_path / "cycle")
    assert result["valid"] is True
    assert result["s2p_action_count"] == 2
    assert result["actual_matches_projection"] is True
    assert result["p2s_stage"] == "passed"
    assert result["p2s_activate"] == "passed"
    assert result["failure_results"]["recovery"]["status"] == "rollback_required"
    assert recover_cycle([{"event_type": "prod_after_state_verified"}])["recommended_action"] == "resume_p2s"


def test_nonzero_bundle_requires_explicit_approval(tmp_path: Path) -> None:
    cycle, _bundle = _minimal_noop_cycle(tmp_path)
    cycle["s2p_plan"]["summary"]["actionable_file_action_count"] = 1
    cycle["p2s_plan"]["p2s_action_count"] = 1
    cycle["canonical_sha256"] = canonical_sha256(cycle)
    with pytest.raises(SyncPlannerError) as exc:
        build_cycle_approval_bundle(cycle, operator_reference="unit-test")
    assert exc.value.reason == "nonzero_cycle_requires_explicit_approval_bundle"


def test_archive_policy_rejects_nonportable_and_workspace_entries() -> None:
    valid = archive_policy_summary(["manifests/result.json", "hashes/sha256sums.txt"])
    assert valid["valid"] is True
    invalid = archive_policy_summary(["workspace\\raw.py", "/absolute.json", "../escape.json", "current_noop_experiment_workspace/file.py"])
    assert invalid["valid"] is False
    assert invalid["backslash_entry_count"] == 1
    assert invalid["absolute_entry_count"] == 1
    assert invalid["traversal_entry_count"] == 1
    assert invalid["raw_workspace_entry_count"] == 2
