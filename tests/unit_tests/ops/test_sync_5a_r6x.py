"""SYNC-OPS-5A-R6X clean source-loss cutover candidate tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from react_agent.ops.sync_5a_r2x import reselect_first_candidate
from react_agent.ops.sync_5a_r5x import (
    build_source_loss_recovery_plan_v5,
)
from react_agent.ops.sync_5a_r6x import (
    EXPECTED_SOURCE_DESCRIPTOR_DIGEST,
    RISK_FRAUD_HISTORICAL_ROOT,
    build_canary_postrun_delta_ledger,
    build_clean_candidate_projection,
    build_conditional_approval_chain_v6,
    build_first_real_cycle_plan_v6,
    build_full_p2s_activation_template_v6,
    build_full_p2s_rebase_plan_v6,
    build_full_p2s_stage_request_v6,
    build_poststart_runtime_artifact_policy,
    build_projected_experiment_v6,
    build_source_action_metadata_ledger,
    build_source_loss_cutover_approval_request_v6,
    build_source_loss_recovery_plan_v6,
    materialize_clean_candidate_from_actions,
    run_offline_validation_nonmutating,
    validate_clean_candidate_projection,
    validate_conditional_approval_chain_v6,
    validate_full_p2s_rebase_plan_v6,
    validate_portable_archive_entries,
    validate_poststart_runtime_artifact_policy,
    validate_source_loss_cutover_approval_request_v6,
    validate_source_loss_recovery_plan_v5_strict,
    validate_source_loss_recovery_plan_v6,
)
from react_agent.ops.sync_contracts import (
    canonical_sha256,
    validate_by_schema_version,
    write_json,
)
from react_agent.ops.sync_inventory import inventory_root
from react_agent.ops.sync_s2p import descriptor_from_inventory


def _runtime() -> dict[str, object]:
    return {
        "pid": "740899",
        "start_ticks": "12455435",
        "cwd": "/sdb/dlut/prod/财务造假风险智能体",
        "exe": "/usr/bin/python3.14",
        "argv": ["python3", "-u", "-m", "app.main"],
    }


def _closeout() -> dict[str, object]:
    closeout = {
        "canonical_sha256": "f" * 64,
        "source_provenance_sha256": "71832769e4c68d234aa7f9487e1c58b634da795aba7b6ca300f282f84ceac63f",
        "environment_profile_sha256": "c6ea8f94673814386cb030d37afc426d978347643809f1103cc348531342658a",
        "equivalence_result_sha256": "28d295870aed3433a020495dc183e4965bfa9fff2e40d5698814748c21d403ad",
        "incumbent_capture_sha256": "bc171af3929cb8a079380be69dc643d75896b5d7d3015b505e84b1b116bd4e42",
    }
    closeout["canonical_sha256"] = canonical_sha256(closeout)
    return closeout


def _qualification() -> dict[str, object]:
    payload = {
        "schema_version": "agent_sync_r6x_test_qualification_v1",
        "full_materialization": {"valid": True},
        "offline_nonmutation": {"valid": True},
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def _source_descriptor() -> dict[str, object]:
    return descriptor_from_inventory(
        inventory_root("risk_financial_fraud", RISK_FRAUD_HISTORICAL_ROOT, root_role="source_loss_recovery_package"),
        scope="transaction_source_tree",
    )


def test_v5_projection_with_runtime_noise_is_rejected_fail_closed() -> None:
    plan = build_source_loss_recovery_plan_v5(
        final_head="e4ff990d2669fda8897249906f4e6a00964653e7",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
    )
    validation = validate_source_loss_recovery_plan_v5_strict(plan)
    assert validation["valid"] is False
    assert "fresh_candidate_projection_file_count_mismatch" in validation["blockers"]
    assert "fresh_candidate_projection_contains_runtime_noise" in validation["blockers"]
    assert "fresh_candidate_projection_contains_unknown_entries" in validation["blockers"]
    assert "fresh_candidate_projection_contains_unexpected_entries" in validation["blockers"]
    assert "file_action_metadata_incomplete" in validation["blockers"]


def test_clean_projection_counts_are_derived_from_67_actions(tmp_path: Path) -> None:
    ledger = build_source_action_metadata_ledger(
        plan_id="source_loss_recovery_v6_test",
        candidate_path=tmp_path / "candidate",
    )
    projection = build_clean_candidate_projection(
        root=tmp_path / "candidate",
        actions=ledger["actions"],
        source_descriptor=_source_descriptor(),
    )
    validation = validate_clean_candidate_projection(projection, ledger["actions"])
    assert ledger["metadata_complete"] is True
    assert projection["regular_file_count"] == 67
    assert projection["parent_directory_count"] == 10
    assert projection["directory_count_including_root"] == 11
    assert projection["projected_entry_count"] == 78
    assert projection["runtime_artifact_count"] == 0
    assert projection["unknown_entry_count"] == 0
    assert projection["unexpected_entries"] == []
    assert projection["source_descriptor"]["digest"] == EXPECTED_SOURCE_DESCRIPTOR_DIGEST
    assert validation["valid"] is True
    validate_by_schema_version(projection)


def test_full_67_file_materialization_and_offline_validation_are_nonmutating(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    ledger = build_source_action_metadata_ledger(plan_id="source_loss_recovery_v6_test", candidate_path=candidate)
    materialized = materialize_clean_candidate_from_actions(candidate, ledger["actions"])
    assert materialized["valid"] is True
    assert materialized["regular_file_count"] == 67
    assert materialized["entry_count"] == 78
    offline = run_offline_validation_nonmutating(candidate, include_pytest=False)
    assert offline["valid"] is True
    assert offline["before_full_entry_digest"] == offline["after_full_entry_digest"]
    assert offline["candidate_mutation_count"] == 0
    assert offline["cache_pollution_count"] == 0


def test_poststart_runtime_policy_classifies_delta_without_relaxing_prestart(tmp_path: Path) -> None:
    root = tmp_path / "canary"
    (root / "app").mkdir(parents=True)
    (root / "app" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "app" / "__pycache__").mkdir()
    (root / "app" / "__pycache__" / "main.cpython-314.pyc").write_bytes(b"pyc")
    (root / "data").mkdir()
    (root / "data" / "fraud_agent.db").write_text("", encoding="utf-8")
    clean = {
        "projected_paths": ["app/main.py"],
        "parent_directories": ["app"],
    }
    policy = build_poststart_runtime_artifact_policy({"digest": "a" * 64})
    delta = build_canary_postrun_delta_ledger(canary_root=root, clean_projection=clean, policy=policy)
    validation = validate_poststart_runtime_artifact_policy(policy, delta)
    assert delta["blocked_delta_count"] == 0
    assert delta["classification_counts"]["runtime_noise"] >= 2
    assert delta["classification_counts"]["data_asset"] >= 2
    assert validation["valid"] is True
    validate_by_schema_version(policy)


def test_v6_plan_request_and_downstream_chain_are_valid() -> None:
    plan = build_source_loss_recovery_plan_v6(
        final_head="e4ff990d2669fda8897249906f4e6a00964653e7",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
        qualification_evidence=_qualification(),
    )
    validation = validate_source_loss_recovery_plan_v6(plan)
    assert validation["valid"] is True
    assert validation["exact_action_count"] == 89
    assert validation["file_action_count"] == 67
    assert plan["clean_fresh_candidate_projection"]["entry_count"] == 78
    assert plan["clean_fresh_candidate_projection"]["runtime_artifact_count"] == 0
    validate_by_schema_version(plan)

    request = build_source_loss_cutover_approval_request_v6(plan)
    request_validation = validate_source_loss_cutover_approval_request_v6(request, plan)
    assert request_validation["valid"] is True
    assert request["status"] == "awaiting_machine_approval"
    assert request["approval_id"] == ""
    assert request["permissions"]["p2s"] is False
    validate_by_schema_version(request)

    p2s = build_full_p2s_rebase_plan_v6(plan)
    p2s_validation = validate_full_p2s_rebase_plan_v6(p2s)
    assert p2s_validation["valid"] is True
    stage = build_full_p2s_stage_request_v6(p2s)
    activation = build_full_p2s_activation_template_v6(p2s)
    assert stage["status"] == "blocked_pending_recovery_settle"
    assert activation["status"] == "blocked_pending_real_stage_closeout"
    validate_by_schema_version(p2s)
    validate_by_schema_version(stage)
    validate_by_schema_version(activation)

    selected = reselect_first_candidate()["selected_candidate"]
    experiment = build_projected_experiment_v6(selected, p2s)
    cycle = build_first_real_cycle_plan_v6(selected, experiment, p2s)
    chain = build_conditional_approval_chain_v6(
        canary_closeout=_closeout(),
        recovery_v6=plan,
        p2s_v6=p2s,
        experiment_v6=experiment,
        cycle_v6=cycle,
    )
    chain_validation = validate_conditional_approval_chain_v6(chain)
    assert chain_validation["valid"] is True
    assert [node["status"] for node in chain["nodes"]] == [
        "executed_and_closed",
        "awaiting_machine_approval",
        "blocked_pending_real_cutover_closeout",
        "blocked_pending_recovery_settle",
        "blocked_pending_real_stage_closeout",
        "blocked_pending_p2s_activation_closeout",
        "blocked_pending_experiment_validation",
    ]
    validate_by_schema_version(experiment)
    validate_by_schema_version(cycle)
    validate_by_schema_version(chain)


def test_archive_portability_rejects_backslash_and_raw_fixture_entries() -> None:
    rejected = validate_portable_archive_entries(
        [
            "contracts\\source_loss_recovery_plan_v6.json",
            "temp_source_loss_fixture/canonical/runtime.db",
            "risk_financial_fraud/app/main.py",
        ]
    )
    assert rejected["valid"] is False
    assert rejected["backslash_entry_count"] == 1
    assert rejected["raw_temp_fixture_entry_count"] == 1
    assert rejected["raw_source_entry_count"] == 1

    accepted = validate_portable_archive_entries(
        [
            "sync_ops_5a_r6x_closeout.json",
            "source_loss_recovery_plan_v6.json",
            "test_results.json",
        ]
    )
    assert accepted["valid"] is True
    assert accepted["backslash_entry_count"] == 0
    assert accepted["raw_temp_fixture_entry_count"] == 0


def test_cli_rejects_v5_projection_before_approval_check(tmp_path: Path) -> None:
    plan = build_source_loss_recovery_plan_v5(
        final_head="e4ff990d2669fda8897249906f4e6a00964653e7",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
    )
    plan_path = tmp_path / "plan_v5.json"
    write_json(plan_path, plan)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "source-loss",
            "execute",
            "--plan",
            str(plan_path),
            "--execute",
            "--stdout-json",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 7
    payload = json.loads(result.stdout)
    assert payload["reason"] == "fresh_candidate_projection_invalid"


def test_cli_rejects_valid_v6_without_machine_approval(tmp_path: Path) -> None:
    plan = build_source_loss_recovery_plan_v6(
        final_head="e4ff990d2669fda8897249906f4e6a00964653e7",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
        qualification_evidence=_qualification(),
    )
    plan_path = tmp_path / "plan_v6.json"
    write_json(plan_path, plan)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "source-loss",
            "execute",
            "--plan",
            str(plan_path),
            "--execute",
            "--stdout-json",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 4
    payload = json.loads(result.stdout)
    assert payload["reason"] == "machine_approval_missing"
