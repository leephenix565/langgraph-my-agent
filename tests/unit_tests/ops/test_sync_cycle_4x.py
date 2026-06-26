"""Focused publish-and-rebase cycle tests."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
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
    build_cycle_plan_from_s2p,
    build_strict_cycle_approval_request,
    build_strict_cycle_plan_from_children,
    recover_cycle,
    run_cycle_nonzero_strict,
    run_cycle_noop,
    run_temp_cycle_compensation,
    run_temp_multi_transaction_cycle,
    run_temp_nonzero_cycle,
    validate_cycle_approval_bundle,
    validate_cycle_approval_request,
    validate_cycle_plan,
)
from react_agent.ops.sync_s2p import (
    build_experiment_fork,
    build_s2p_plan_v2,
    compare_digest_descriptors,
    digest_descriptor,
    validate_s2p_plan_contract,
)


def _future_cycle_expiry() -> str:
    return (datetime.now(UTC) + timedelta(days=7)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _expired_cycle_expiry() -> str:
    return (datetime.now(UTC) - timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_s2p_mapping_accepts_recovered_risk_fraud_and_shared_members(tmp_path: Path) -> None:
    manifest = build_experiment_fork(workspace_root=tmp_path / "experiment", experiment_id="exp_cycle_mapping")
    plan = build_s2p_plan_v2(manifest)

    fraud = next(agent for agent in plan["agents"] if agent["agent_id"] == "risk_financial_fraud")
    assert fraud["baseline_tree_sha256"] == fraud["experiment_tree_sha256"]
    assert fraud["experiment_tree_sha256"]
    assert fraud["baseline_descriptor"]["file_count"] == 67
    assert fraud["experiment_descriptor"]["file_count"] == 67
    assert fraud["mapping_status"] == "complete"
    assert fraud["mapping_blockers"] == []
    validation = validate_s2p_plan_contract(plan)
    assert validation["valid"] is True
    assert validation["blockers"] == []

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
    assert validation["blockers"] == []
    assert cycle["schema_version"] == "agent_sync_publish_and_rebase_cycle_v1"
    assert cycle["mode"] == "strict_all_or_nothing"
    assert cycle["projected_prod_after_state"]["projected_combined_prod_descriptor"]["scope"] == "s2p_prod_inventory"
    transaction_ids = [row["transaction_id"] for row in cycle["projected_prod_after_state"]["transactions"]]
    assert len(transaction_ids) == len(set(transaction_ids))
    assert cycle["p2s_plan"]["canonical_sha256"]
    assert cycle["p2s_plan"]["p2s_action_count"] == 0


def test_cycle_approval_bundle_rejects_noop_action_scope(tmp_path: Path) -> None:
    cycle, _unused = _minimal_noop_cycle(tmp_path)
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


def test_multi_transaction_cycle_and_shared_member_rehearsal(tmp_path: Path) -> None:
    result = run_temp_multi_transaction_cycle(tmp_path / "multi-cycle")
    assert result["valid"] is True
    assert result["independent_transaction_count"] >= 2
    assert result["shared_member_count"] == 1
    assert result["owner_transaction_id"] == "txn_market_composite"
    assert result["duplicate_target_count"] == 0
    assert result["actual_matches_projection"] is True
    assert result["cycle_status"] == "closed"


def test_cycle_compensates_earlier_transactions_when_later_transaction_fails(tmp_path: Path) -> None:
    result = run_temp_cycle_compensation(tmp_path / "compensation-cycle")
    assert result["valid"] is True
    assert result["transaction_a_apply"]["status"] == "applied_and_verified"
    assert result["transaction_b_apply"]["status"] == "rolled_back"
    assert result["compensation_order"] == ["txn_agent_b", "txn_agent_a"]
    assert result["compensated_transaction_count"] == 2
    assert result["prod_restored"] is True
    assert result["p2s_action_count"] == 0
    assert result["cycle_status"] == "s2p_cycle_compensated_rolled_back"


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


def _strict_first_nonzero_children() -> tuple[dict, dict, dict, dict, dict, dict]:
    after_descriptor = {
        "schema": "agent_source_descriptor_v1",
        "scope": "prod_source_after_projected_first_cycle",
        "agent": "risk_financial_fraud",
        "file_count": 67,
        "digest": "f6ed15e1c7c3d7b739b03dd90a7821b9e3baf5a2a56bf3213e4c13351b4133db",
        "records_sha256": "records-after",
    }
    before_descriptor = {
        **after_descriptor,
        "scope": "prod_source_before_first_cycle",
        "digest": "0ab2df6bf051476ee110cb7073828ed396d67b84a205dd0b6bd10414a11c7720",
        "records_sha256": "records-before",
    }
    summary = {
        "schema": "agent_sync_first_nonzero_cycle_plan_v1",
        "cycle_id": "cycle_bb73bb471272",
        "cycle_sha256": "07d09a6e9b2c0e8d666b2d25b58ef0c1f04b4578a7bfc9d3b18db7ddab910a35",
        "experiment_id": "first_nonzero_risk_fraud_report_contract_3e3a071",
        "experiment_manifest_sha256": "1806e2c957afc2604f4fe7aee516edb5eda8754c2953866e10517a05186c191f",
        "change_unit_id": "cu_792c2d1b0262",
        "change_unit_sha256": "abdffb31f57e9aafdb7e6a5124a8ede3a08871910d96deea78096acb41b2e37c",
        "s2p_plan_id": "s2p_first_0abdfb4f91a4",
        "s2p_plan_sha256": "2cce1f6d838e886cec3feffe33d8bead1c977e6eb85d3d9c593d6892762f55bb",
        "s2p_action_count": 1,
        "p2s_plan_id": "p2s_first_52d75b56543f",
        "p2s_plan_sha256": "c8e3d41f376abda96f498386d628ad6ecfc23264486f4f21fb8f093133cf86f3",
        "p2s_action_count": 1,
        "projected_prod_after_descriptor": after_descriptor["digest"],
        "process_actions": 0,
        "live_endpoint_calls": 0,
        "delete_actions": 0,
        "owner_dev_write": False,
        "status": "awaiting_machine_approval",
    }
    experiment = {
        "experiment_id": "first_nonzero_risk_fraud_report_contract_3e3a071",
        "canonical_sha256": "1806e2c957afc2604f4fe7aee516edb5eda8754c2953866e10517a05186c191f",
        "workspace": "/tmp/experiment/fixed-dag-services",
        "base_baseline_id": "risk-fraud-rebase-full_p2s_rebase_9f7f07553392",
        "changed_files": ["risk_financial_fraud/tests/test_report_material.py"],
        "registered_change_units": ["cu_792c2d1b0262"],
        "unregistered_changes": 0,
    }
    change = {
        "change_unit_id": "cu_792c2d1b0262",
        "canonical_sha256": "abdffb31f57e9aafdb7e6a5124a8ede3a08871910d96deea78096acb41b2e37c",
        "agent": "risk_financial_fraud",
        "file": "risk_financial_fraud/tests/test_report_material.py",
        "risk_class": "A_docs_tests_material",
    }
    s2p = {
        "schema": "agent_sync_s2p_plan_v1",
        "plan_id": "s2p_first_0abdfb4f91a4",
        "plan_sha256": "2cce1f6d838e886cec3feffe33d8bead1c977e6eb85d3d9c593d6892762f55bb",
        "canonical_sha256": "07ae6e98c7e428f1a56731eed0cc76854b44cbfc132dec4e555c0de37066c172",
        "change_unit_id": "cu_792c2d1b0262",
        "actions": [
            {
                "action_id": "s2p_e1d56522098d",
                "operation": "atomic_replace_one_file",
                "source_experiment_file": "/tmp/experiment/fixed-dag-services/risk_financial_fraud/tests/test_report_material.py",
                "target_prod_file": "/sdb/dlut/prod/财务造假风险智能体/tests/test_report_material.py",
                "before_sha256": "7f5677195a289a15debcf5b3c55a6c2d421fb1f097be65162c85873712142b5e",
                "after_sha256": "021b6060dfe22924762039f7b53c51c1874e880abae52147f468381232696fe3",
                "backup_required": True,
                "offline_tests_required": True,
                "process_required": False,
                "live_required": False,
                "delete_required": False,
            }
        ],
        "projected_prod_after_descriptor": after_descriptor,
    }
    projected = {"before_descriptor": before_descriptor, "after_descriptor": after_descriptor}
    p2s = {
        "schema": "agent_sync_first_cycle_p2s_plan_v1",
        "plan_id": "p2s_first_52d75b56543f",
        "plan_sha256": "c8e3d41f376abda96f498386d628ad6ecfc23264486f4f21fb8f093133cf86f3",
        "canonical_sha256": "ef0d6ef02aae16e4d49835555e60ec8ecad5656b95c294a46f0f57fb55d7d21f",
        "stage_root": "/tmp/stage/fixed-dag-services",
        "actions": [
            {
                "action_id": "p2s_5d09bb73bb47",
                "operation": "copy_settled_prod_file_to_new_baseline_stage",
                "source_prod_file": "/sdb/dlut/prod/财务造假风险智能体/tests/test_report_material.py",
                "target_baseline_file": "/tmp/stage/fixed-dag-services/risk_financial_fraud/tests/test_report_material.py",
                "expected_source_sha256": "021b6060dfe22924762039f7b53c51c1874e880abae52147f468381232696fe3",
                "expected_target_sha256": "021b6060dfe22924762039f7b53c51c1874e880abae52147f468381232696fe3",
                "process_required": False,
                "live_required": False,
                "delete_required": False,
            }
        ],
        "projected_active_source_after_descriptor": after_descriptor,
    }
    return summary, experiment, change, s2p, projected, p2s


def test_summary_first_nonzero_cycle_is_not_formal_cycle_plan() -> None:
    summary, _experiment, _change, _s2p, _projected, _p2s = _strict_first_nonzero_children()
    result = validate_cycle_plan(summary)
    assert result["valid"] is False
    assert "not_cycle_plan" in result["blockers"]
    assert "cycle_not_strict_all_or_nothing" in result["blockers"]
    assert "projected_prod_after_state_missing" in result["blockers"]
    assert "precomputed_p2s_plan_missing" in result["blockers"]


def test_strict_cycle_builder_binds_frozen_children_and_actions() -> None:
    summary, experiment, change, s2p, projected, p2s = _strict_first_nonzero_children()
    plan = build_strict_cycle_plan_from_children(
        summary_cycle=summary,
        experiment_manifest=experiment,
        change_unit=change,
        s2p_child_plan=s2p,
        projected_prod_after=projected,
        p2s_child_plan=p2s,
        created_at="2026-06-25T00:00:00Z",
        expires_at=_future_cycle_expiry(),
    )

    assert plan["schema_version"] == "agent_sync_publish_and_rebase_cycle_v1"
    assert plan["mode"] == "strict_all_or_nothing"
    assert plan["supersedes_summary_cycle_id"] == "cycle_bb73bb471272"
    assert plan["s2p_plan"]["plan_id"] == "s2p_first_0abdfb4f91a4"
    assert plan["s2p_plan"]["summary"]["actionable_file_action_count"] == 1
    assert plan["p2s_plan"]["plan_id"] == "p2s_first_52d75b56543f"
    assert plan["p2s_plan"]["p2s_action_count"] == 1
    assert plan["action_scope"]["s2p_action_ids"] == ["s2p_e1d56522098d"]
    assert plan["action_scope"]["p2s_action_ids"] == ["p2s_5d09bb73bb47"]
    assert plan["projected_prod_after_state"]["projected_combined_prod_descriptor"]["digest"] == summary["projected_prod_after_descriptor"]
    validation = validate_cycle_plan(plan)
    assert validation["valid"] is True
    assert validation["blockers"] == []


def test_strict_cycle_approval_request_is_not_machine_approval() -> None:
    summary, experiment, change, s2p, projected, p2s = _strict_first_nonzero_children()
    plan = build_strict_cycle_plan_from_children(
        summary_cycle=summary,
        experiment_manifest=experiment,
        change_unit=change,
        s2p_child_plan=s2p,
        projected_prod_after=projected,
        p2s_child_plan=p2s,
        created_at="2026-06-25T00:00:00Z",
        expires_at=_future_cycle_expiry(),
    )
    request = build_strict_cycle_approval_request(plan)

    request_validation = validate_cycle_approval_request(request, plan)
    assert request_validation["valid"] is True
    assert request_validation["request_is_machine_approval"] is False
    assert request_validation["action_count"] == 2
    assert request["requested_action_ids"] == ["s2p_e1d56522098d", "p2s_5d09bb73bb47"]
    assert validate_cycle_approval_bundle(request, plan)["valid"] is False

    request["s2p_plan_sha256"] = "changed"
    drift = validate_cycle_approval_request(request, plan)
    assert drift["valid"] is False
    assert "s2p_plan_sha256_mismatch" in drift["blockers"]


def test_strict_cycle_approval_request_expired_fails_closed() -> None:
    summary, experiment, change, s2p, projected, p2s = _strict_first_nonzero_children()
    plan = build_strict_cycle_plan_from_children(
        summary_cycle=summary,
        experiment_manifest=experiment,
        change_unit=change,
        s2p_child_plan=s2p,
        projected_prod_after=projected,
        p2s_child_plan=p2s,
        created_at="2026-06-25T00:00:00Z",
        expires_at=_expired_cycle_expiry(),
    )
    request = build_strict_cycle_approval_request(plan)

    request_validation = validate_cycle_approval_request(request, plan)
    assert request_validation["valid"] is False
    assert "approval_request_expired" in request_validation["blockers"]
    assert validate_cycle_approval_bundle(request, plan)["valid"] is False


def test_cli_publish_and_rebase_dry_run_accepts_strict_request(tmp_path: Path) -> None:
    summary, experiment, change, s2p, projected, p2s = _strict_first_nonzero_children()
    plan = build_strict_cycle_plan_from_children(
        summary_cycle=summary,
        experiment_manifest=experiment,
        change_unit=change,
        s2p_child_plan=s2p,
        projected_prod_after=projected,
        p2s_child_plan=p2s,
        created_at="2026-06-25T00:00:00Z",
        expires_at=_future_cycle_expiry(),
    )
    request = build_strict_cycle_approval_request(plan)
    plan_path = tmp_path / "strict_cycle_plan.json"
    request_path = tmp_path / "strict_cycle_request.json"
    result_path = tmp_path / "dry_run.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            ".venv/bin/python",
            "scripts/ops/agent_syncctl.py",
            "cycle",
            "publish-and-rebase",
            "--cycle-plan",
            str(plan_path),
            "--approval-bundle",
            str(request_path),
            "--json-output",
            str(result_path),
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ready_for_machine_approval"
    assert payload["action_count"] == 2
    assert payload["process_actions"] == 0
    assert payload["live_actions"] == 0
    assert payload["delete_actions"] == 0


def test_strict_nonzero_cycle_executes_one_file_publish_and_rebase(tmp_path: Path) -> None:
    summary, experiment, change, s2p, projected, p2s = _strict_first_nonzero_children()
    prod_root = tmp_path / "prod" / "risk_financial_fraud"
    experiment_root = tmp_path / "experiment" / "fixed-dag-services" / "risk_financial_fraud"
    active_root = tmp_path / "sandbox" / "prod"
    pointer_path = tmp_path / "sandbox" / "PROD_BASELINE_POINTER.json"
    stage_root = tmp_path / "baselines" / "first-cycle-p2s_52d75b56543f" / "fixed-dag-services"
    rel = Path("risk_financial_fraud/tests/test_report_material.py")
    before = "def test_report_material_before():\n    assert 'before'\n"
    after = "def test_report_material_after():\n    assert 'after'\n"
    for root, content in ((prod_root, before), (experiment_root, after), (active_root / "risk_financial_fraud", before)):
        target = root / "tests" / "test_report_material.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        (root / "README.md").write_text("stable\n", encoding="utf-8")
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(
        json.dumps(
            {
                "schema_version": "fixed_dag_prod_sandbox_baseline_pointer_v1",
                "active_baseline_id": "risk-fraud-rebase-full_p2s_rebase_9f7f07553392",
                "active_path": str(active_root),
                "versioned_baseline_path": str(tmp_path / "baseline" / "fixed-dag-services"),
                "manifest_hashes": {},
            }
        ),
        encoding="utf-8",
    )
    before_sha = file_sha256(prod_root / "tests" / "test_report_material.py")
    after_sha = file_sha256(experiment_root / "tests" / "test_report_material.py")
    s2p["actions"][0].update(
        {
            "source_experiment_file": str(experiment_root / "tests" / "test_report_material.py"),
            "target_prod_file": str(prod_root / "tests" / "test_report_material.py"),
            "before_sha256": before_sha,
            "after_sha256": after_sha,
        }
    )
    p2s["stage_root"] = str(stage_root)
    p2s["actions"][0].update(
        {
            "source_prod_file": str(prod_root / "tests" / "test_report_material.py"),
            "target_baseline_file": str(stage_root / rel),
            "expected_source_sha256": after_sha,
            "expected_target_sha256": after_sha,
        }
    )
    projected["before_descriptor"]["digest"] = "before-temp"
    projected["after_descriptor"]["digest"] = "after-temp"
    p2s["projected_active_source_after_descriptor"] = dict(projected["after_descriptor"])
    summary["projected_prod_after_descriptor"] = "after-temp"
    plan = build_strict_cycle_plan_from_children(
        summary_cycle=summary,
        experiment_manifest=experiment,
        change_unit=change,
        s2p_child_plan=s2p,
        projected_prod_after=projected,
        p2s_child_plan=p2s,
        created_at="2026-06-25T00:00:00Z",
        expires_at=_future_cycle_expiry(),
    )
    plan["baseline"].update(
        {
            "active_path": str(active_root),
            "pointer_path": str(pointer_path),
            "pointer_sha256": file_sha256(pointer_path),
        }
    )
    plan["canonical_sha256"] = canonical_sha256(plan)
    approval = build_cycle_approval_bundle(plan, operator_reference="unit-test", approve_nonzero=True)

    result = run_cycle_nonzero_strict(plan, approval, tmp_path / "artifacts")

    assert result["valid"] is True
    assert result["status"] == "terminal_publish_and_rebase_chain_complete"
    assert result["s2p_action_count"] == 1
    assert result["p2s_action_count"] == 1
    assert result["endpoint_call_count"] == 0
    assert result["process_action_count"] == 0
    assert file_sha256(prod_root / "tests" / "test_report_material.py") == after_sha
    assert file_sha256(active_root / rel) == after_sha
    assert file_sha256(stage_root / rel) == after_sha
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    assert pointer["active_baseline_id"] == "first-cycle-p2s_52d75b56543f"
    assert Path(result["old_active_archive"]).exists()
