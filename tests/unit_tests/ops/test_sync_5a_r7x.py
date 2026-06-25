"""SYNC-OPS-5A-R7X cutover tree parity tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from react_agent.ops.sync_5a_r2x import reselect_first_candidate
from react_agent.ops.sync_5a_r6x import (
    build_source_loss_recovery_plan_v6,
)
from react_agent.ops.sync_5a_r7x import (
    R6X_ACTUAL_MATERIALIZED_DIGEST,
    R6X_PROJECTION_DIGEST,
    action_semantics_sha256,
    actual_physical_entry_manifest,
    build_conditional_approval_chain_v7,
    build_first_real_cycle_plan_v7,
    build_full_p2s_activation_template_v7,
    build_full_p2s_rebase_plan_v7,
    build_full_p2s_stage_request_v7,
    build_physical_tree_descriptor_v2,
    build_projected_experiment_v7,
    build_source_loss_cutover_approval_request_v7,
    build_source_loss_recovery_plan_v7,
    diff_entry_manifests,
    materialize_candidate_v2,
    physical_entry_manifest_from_actions,
    run_full_67_exact_action_temp_rehearsal,
    validate_conditional_approval_chain_v7,
    validate_full_p2s_rebase_plan_v7,
    validate_source_loss_cutover_approval_request_v7,
    validate_source_loss_recovery_plan_v6_for_v7,
    validate_source_loss_recovery_plan_v7,
)
from react_agent.ops.sync_contracts import (
    canonical_sha256,
    validate_by_schema_version,
    write_json,
)


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


def _build_valid_v7(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    draft = build_source_loss_recovery_plan_v7(
        final_head="aa9a13f09671c1ed63c21f105abe1d423de0a06e",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
        rehearsal_evidence={},
    )
    rehearsal = run_full_67_exact_action_temp_rehearsal(
        final_plan=draft,
        temp_root=tmp_path / "full67-rehearsal",
        include_pytest=False,
    )
    plan = build_source_loss_recovery_plan_v7(
        final_head="aa9a13f09671c1ed63c21f105abe1d423de0a06e",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
        rehearsal_evidence=rehearsal,
    )
    return plan, rehearsal


def test_v6_projection_materialization_digest_mismatch_is_rejected() -> None:
    v6 = build_source_loss_recovery_plan_v6(
        final_head="e4ff990d2669fda8897249906f4e6a00964653e7",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
        qualification_evidence=_qualification(),
    )
    validation = validate_source_loss_recovery_plan_v6_for_v7(v6)
    assert validation["valid"] is False
    assert R6X_PROJECTION_DIGEST != R6X_ACTUAL_MATERIALIZED_DIGEST
    assert "projection_materialization_physical_digest_mismatch" in validation["blockers"]
    assert "directory_mode_contract_missing" in validation["blockers"]
    assert "exact_rehearsal_action_binding_missing" in validation["blockers"]


def test_physical_digest_is_path_independent_and_policy_digest_is_separate(tmp_path: Path) -> None:
    file_action = {
        "operation": "materialize_fresh_candidate_file",
        "source_sha256": "a" * 64,
        "source_file_type": "regular",
        "source_mode": "0o644",
        "source_executable": False,
        "relative_path": "app/main.py",
        "expected_destination_type": "regular",
        "expected_destination_mode": "0o644",
        "classification": "source_code",
        "policy_rule": "source_file_action",
        "follow_symlink": False,
        "hardlink_allowed": False,
    }
    directory_action = {
        "operation": "create_candidate_directory",
        "relative_path": ".",
        "candidate_pre_cutover_mode": "0o755",
        "canonical_post_cutover_mode": "0o755",
        "mode_transition_required": False,
        "classification": "root_directory",
        "policy_rule": "root",
        "follow_symlink": False,
        "hardlink_allowed": False,
    }
    manifest_a = physical_entry_manifest_from_actions(directory_actions=[directory_action], file_actions=[file_action])
    manifest_b = physical_entry_manifest_from_actions(directory_actions=[dict(directory_action)], file_actions=[{**file_action, "classification": "documentation"}])
    assert manifest_a["physical_tree_digest"] == manifest_b["physical_tree_digest"]
    assert manifest_a["classification_manifest_sha256"] != manifest_b["classification_manifest_sha256"]
    descriptor = build_physical_tree_descriptor_v2(manifest_a)
    validate_by_schema_version(descriptor)

    changed_mode = physical_entry_manifest_from_actions(
        directory_actions=[{**directory_action, "candidate_pre_cutover_mode": "0o775"}],
        file_actions=[file_action],
    )
    assert manifest_a["physical_tree_digest"] != changed_mode["physical_tree_digest"]
    assert action_semantics_sha256(file_action) == action_semantics_sha256({**file_action, "destination_path": str(tmp_path / "ignored")})


def test_directory_mode_ledger_and_full67_materializer_parity(tmp_path: Path) -> None:
    plan, rehearsal = _build_valid_v7(tmp_path)
    assert rehearsal["valid"] is True
    assert rehearsal["expected_physical_tree_digest"] == rehearsal["actual_after_materialization_physical_tree_digest"]
    assert rehearsal["expected_physical_tree_digest"] == rehearsal["actual_after_offline_validation_physical_tree_digest"]
    assert rehearsal["action_semantics_binding"]["bound_action_count"] == 78
    assert plan["directory_action_ledger"]["action_count"] == 11
    assert len(plan["file_actions"]) == 67
    assert plan["physical_tree_descriptor_v2"]["entry_count"] == 78
    assert plan["physical_tree_descriptor_v2"]["regular_file_count"] == 67
    assert plan["physical_tree_descriptor_v2"]["directory_count_including_root"] == 11
    validate_by_schema_version(plan["physical_tree_descriptor_v2"])
    validate_by_schema_version(plan["directory_mode_authority"])
    validate_by_schema_version(plan["directory_action_ledger"])
    validate_by_schema_version(rehearsal["action_semantics_binding"])


def test_entry_diff_lists_mode_and_classification_mismatches(tmp_path: Path) -> None:
    plan, _rehearsal = _build_valid_v7(tmp_path)
    expected = plan["projected_candidate_entry_manifest"]
    candidate = tmp_path / "diff-candidate"
    materialized = materialize_candidate_v2(candidate, plan["directory_actions"], plan["file_actions"])
    assert materialized["valid"] is True
    actual = actual_physical_entry_manifest(candidate, expected)
    assert diff_entry_manifests(expected, actual)["physical_tree_digest_match"] is True
    first_dir = next(entry for entry in actual["entries"] if entry["entry_type"] == "directory")
    first_dir["mode"] = "0o700"
    first_dir["classification"] = "changed"
    diff = diff_entry_manifests(expected, actual)
    assert first_dir["relative_path"] in diff["mode_mismatch"]
    assert first_dir["relative_path"] in diff["classification_mismatch"]


def test_v7_plan_request_downstream_chain_are_valid(tmp_path: Path) -> None:
    plan, _rehearsal = _build_valid_v7(tmp_path)
    validation = validate_source_loss_recovery_plan_v7(plan)
    assert validation["valid"] is True
    assert validation["exact_action_count"] == 100
    validate_by_schema_version(plan)

    request = build_source_loss_cutover_approval_request_v7(plan)
    request_validation = validate_source_loss_cutover_approval_request_v7(request, plan)
    assert request_validation["valid"] is True
    assert request["status"] == "awaiting_machine_approval"
    assert request["permissions"]["sigkill"] is False
    assert request["permissions"]["p2s"] is False
    validate_by_schema_version(request)

    p2s = build_full_p2s_rebase_plan_v7(plan)
    p2s_validation = validate_full_p2s_rebase_plan_v7(p2s)
    assert p2s_validation["valid"] is True
    assert p2s["recovery_plan_gate"]["recovery_schema_version"] == "agent_sync_source_loss_recovery_plan_v7"
    validate_by_schema_version(p2s)
    stage = build_full_p2s_stage_request_v7(p2s)
    activation = build_full_p2s_activation_template_v7(p2s)
    assert stage["status"] == "blocked_pending_recovery_settle"
    assert activation["status"] == "blocked_pending_real_stage_closeout"
    validate_by_schema_version(stage)
    validate_by_schema_version(activation)

    selected = reselect_first_candidate()["selected_candidate"]
    experiment = build_projected_experiment_v7(selected, p2s)
    cycle = build_first_real_cycle_plan_v7(selected, experiment, p2s)
    chain = build_conditional_approval_chain_v7(
        canary_closeout=_closeout(),
        recovery_v7=plan,
        p2s_v7=p2s,
        experiment_v7=experiment,
        cycle_v7=cycle,
    )
    chain_validation = validate_conditional_approval_chain_v7(chain)
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


def test_cli_rejects_v6_and_valid_v7_without_machine_approval(tmp_path: Path) -> None:
    v6 = build_source_loss_recovery_plan_v6(
        final_head="e4ff990d2669fda8897249906f4e6a00964653e7",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
        qualification_evidence=_qualification(),
    )
    v6_path = tmp_path / "plan_v6.json"
    write_json(v6_path, v6)
    v6_result = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "source-loss",
            "execute",
            "--plan",
            str(v6_path),
            "--execute",
            "--stdout-json",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    assert v6_result.returncode == 7
    assert json.loads(v6_result.stdout)["reason"] == "projection_materialization_digest_mismatch"

    v7, _rehearsal = _build_valid_v7(tmp_path)
    v7_path = tmp_path / "plan_v7.json"
    write_json(v7_path, v7)
    v7_result = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "source-loss",
            "execute",
            "--plan",
            str(v7_path),
            "--execute",
            "--stdout-json",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    assert v7_result.returncode == 4
    assert json.loads(v7_result.stdout)["reason"] == "machine_approval_missing"
