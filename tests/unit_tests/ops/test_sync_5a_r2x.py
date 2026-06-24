"""SYNC-OPS-5A-R2X source-loss recovery tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from react_agent.ops.sync_5a_r2x import (
    DEFAULT_CANARY_PORT,
    build_final_compound_execution_approval_request_v2,
    build_final_compound_execution_plan_v2,
    build_first_real_cycle_plan_v2,
    build_full_p2s_rebase_plan_v2,
    build_projected_experiment_manifest_v2,
    build_source_loss_recovery_plan_v2,
    build_source_package_integrity,
    reselect_first_candidate,
    validate_final_compound_execution_plan_v2,
    validate_first_real_cycle_plan_v2,
    validate_full_p2s_rebase_plan_v2,
    validate_source_loss_recovery_plan_v2,
    validate_superseded_r1x_p2s_projection,
    validate_superseded_r1x_recovery_plan,
)
from react_agent.ops.sync_contracts import canonical_sha256, validate_by_schema_version

R1X = Path("/tmp/lma-sync-ops-5a-r1x-final-freeze-20260624T160554Z")


def _runtime(classification: str = "launch_authority_complete") -> dict[str, object]:
    return {
        "pid": "740899",
        "cwd": "/sdb/dlut/prod/财务造假风险智能体",
        "exe": "/usr/bin/python3.14",
        "argv": ["python3", "-u", "-m", "app.main"],
        "launch_authority_classification": classification,
    }


def _read(name: str) -> dict[str, object]:
    return json.loads((R1X / name).read_text(encoding="utf-8"))


def test_r1x_recovery_plan_is_superseded_as_irreversible_source_loss() -> None:
    result = validate_superseded_r1x_recovery_plan(_read("risk_fraud_prod_recovery_plan.json"))
    assert result["valid"] is False
    assert result["status"] == "superseded_due_irreversible_source_loss_recovery_gap"
    assert "in_place_current_cwd_file_actions" in result["rejection_reasons"]
    assert "backup_empty_tree_cannot_restore_old_runtime" in result["rejection_reasons"]


def test_r1x_p2s_projection_is_superseded_for_placeholders_and_missing_manifest() -> None:
    result = validate_superseded_r1x_p2s_projection(_read("risk_fraud_p2s_rebase_plan.json"))
    assert result["valid"] is False
    assert "stage_path_contains_placeholder" in result["rejection_reasons"]
    assert "full_materialization_manifest_missing" in result["rejection_reasons"]


def test_source_package_integrity_accepts_67_file_package() -> None:
    result = build_source_package_integrity()
    assert result["valid"] is True
    assert result["file_count"] == 67
    assert result["accepted_lineage_count"] >= 3
    assert result["startup_closure"]["complete"] is True
    assert not result["secret_findings"]


def test_source_loss_recovery_plan_requires_roll_forward_and_canary() -> None:
    plan = build_source_loss_recovery_plan_v2(runtime_audit=_runtime())
    validation = validate_source_loss_recovery_plan_v2(plan)
    assert validation["valid"] is True
    assert validation["action_count"] == 67
    assert validation["previous_runtime_restore_supported"] is False
    assert validation["cutover_semantics"] == "verified_roll_forward"
    assert plan["incident"]["empty_tree_restore_is_rollback"] is False
    assert plan["canary_contract"]["canary_port"] == DEFAULT_CANARY_PORT
    assert plan["requested_permissions"]["irreversible_source_loss_cutover_acknowledged"] is True
    assert all("target_path" not in action for action in plan["file_actions"])
    validate_by_schema_version(plan)


def test_launch_authority_unresolved_blocks_recovery_execution() -> None:
    plan = build_source_loss_recovery_plan_v2(runtime_audit=_runtime("restart_authority_unresolved"))
    validation = validate_source_loss_recovery_plan_v2(plan)
    assert validation["valid"] is False
    assert "launch_authority_invalid" in validation["blockers"]
    assert plan["launch_authority"]["classification"] == "restart_authority_unresolved"


def test_full_p2s_rebase_plan_has_concrete_paths_and_manifest() -> None:
    recovery = build_source_loss_recovery_plan_v2(runtime_audit=_runtime())
    p2s = build_full_p2s_rebase_plan_v2(recovery)
    validation = validate_full_p2s_rebase_plan_v2(p2s)
    assert validation["valid"] is True
    assert validation["agent_disposition_count"] == 26
    assert validation["physical_action_count"] > validation["risk_fraud_projected_file_count"]
    assert validation["risk_fraud_projected_file_count"] == 67
    for key in ["stage_root", "activation_candidate_path", "activation_archive_path"]:
        assert "<" not in p2s[key]
        assert ">" not in p2s[key]
    assert len(p2s["stage_approval_request"]["requested_action_ids"]) == validation["physical_action_count"]
    validate_by_schema_version(p2s)


def test_market_candidate_is_selected_as_tests_only_candidate() -> None:
    result = reselect_first_candidate()
    selected = result["selected_candidate"]
    assert result["valid"] is True
    assert selected["candidate_id"] == "candidate_market_capital_flow_chip_contract_test"
    assert selected["risk_class"] == "A_docs_tests_material"
    assert selected["process_required"] is False
    assert selected["live_required"] is False
    assert selected["delete_required"] is False
    assert selected["rollback_ready"] is True


def test_compound_plan_and_request_bind_all_phase_hashes() -> None:
    recovery = build_source_loss_recovery_plan_v2(runtime_audit=_runtime())
    p2s = build_full_p2s_rebase_plan_v2(recovery)
    selected = reselect_first_candidate()["selected_candidate"]
    experiment = build_projected_experiment_manifest_v2(selected, p2s)
    cycle = build_first_real_cycle_plan_v2(selected, experiment, p2s)
    compound = build_final_compound_execution_plan_v2(recovery, p2s, experiment, cycle)
    request = build_final_compound_execution_approval_request_v2(compound, selected, cycle)

    assert validate_first_real_cycle_plan_v2(cycle)["valid"] is True
    assert validate_final_compound_execution_plan_v2(compound)["valid"] is True
    assert compound["canonical_sha256"] == canonical_sha256(compound)
    assert request["status"] == "awaiting_machine_approval"
    assert request["approval_id"] == ""
    assert request["approved_at"] == ""
    assert request["recovery"]["irreversible_source_loss_cutover_acknowledged"] is True
    assert request["first_cycle"]["process_requested"] is False
    assert request["first_cycle"]["live_requested"] is False
    validate_by_schema_version(compound)
    validate_by_schema_version(request)


def test_source_loss_cli_fails_closed_on_unresolved_launch_authority() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "risk-fraud",
            "freeze-source-loss",
            "--old-recovery-plan",
            str(R1X / "risk_fraud_prod_recovery_plan.json"),
            "--old-p2s-plan",
            str(R1X / "risk_fraud_p2s_rebase_plan.json"),
            "--pid",
            "740899",
            "--cwd",
            "/sdb/dlut/prod/财务造假风险智能体",
            "--launch-authority-classification",
            "restart_authority_unresolved",
            "--stdout-json",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 7
    payload = json.loads(result.stdout)
    assert payload["source_loss_recovery_validation"]["valid"] is False
    assert payload["source_loss_recovery_plan"]["launch_authority"]["classification"] == "restart_authority_unresolved"
