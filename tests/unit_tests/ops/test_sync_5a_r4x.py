"""SYNC-OPS-5A-R4X real canary and approval-chain tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from react_agent.ops.sync_5a_r2x import reselect_first_candidate
from react_agent.ops.sync_5a_r3x import build_environment_reference_metadata
from react_agent.ops.sync_5a_r4x import (
    build_conditional_approval_chain_v1,
    build_environment_profile_v1,
    build_equivalence_contract_v1,
    build_first_real_cycle_plan_v4,
    build_full_p2s_rebase_plan_v4,
    build_machine_precutover_canary_approval,
    build_precutover_canary_plan_v1,
    build_projected_experiment_v4,
    build_runtime_variable_matrix,
    build_source_loss_recovery_plan_v4,
    materialize_candidate,
    validate_conditional_approval_chain_v1,
    validate_environment_profile_v1,
    validate_environment_reference_metadata_strict,
    validate_equivalence_contract_v1,
    validate_full_p2s_rebase_plan_v4,
    validate_incumbent_canary_equivalence,
    validate_machine_precutover_canary_approval,
    validate_precutover_canary_plan_v1,
    validate_runtime_variable_matrix,
    validate_source_loss_recovery_plan_v4,
)
from react_agent.ops.sync_contracts import canonical_sha256, validate_by_schema_version


def _runtime() -> dict[str, object]:
    return {
        "pid": "740899",
        "start_ticks": "12455435",
        "cwd": "/sdb/dlut/prod/财务造假风险智能体",
        "exe": "/usr/bin/python3.14",
        "argv": ["python3", "-u", "-m", "app.main"],
    }


def _capture(*, status: str = "ok", warnings: list[str] | None = None, body_sha: str = "0" * 64) -> dict[str, object]:
    warning_list = warnings or []
    return {
        "schema_version": "agent_sync_service_contract_capture_v1",
        "health": {
            "http_status": 200,
            "body_sha256": body_sha,
            "fixed_dag_agent_id": "risk_financial_fraud",
            "external_agent_id": "financial_fraud_agent",
            "status": status,
            "status_class": status,
            "warnings_categories": warning_list,
            "identity_pass": True,
        },
        "compute": {
            "http_status": 200,
            "body_sha256": body_sha,
            "schema_version": "external_agent_compute_v0",
            "agent_id": "risk_financial_fraud",
            "external_agent_id": "financial_fraud_agent",
            "status": status,
            "status_class": status,
            "envelope_valid": True,
            "tool_result_schema": "agent_conclusion_v1",
            "warnings_categories": warning_list,
        },
        "adapter": {
            "mapped": True,
            "schema_version": "conclusion_object_v1",
            "agent_id": "risk_financial_fraud",
            "dimension": "risk",
            "status": "complete" if status == "ok" else status,
            "status_class": status,
            "validator_pass": True,
        },
        "raw_body_persisted": False,
    }


def _closeout(plan: dict[str, object], equivalence_sha: str) -> dict[str, object]:
    closeout = {
        "canonical_sha256": "1" * 64,
        "candidate_path": plan["candidate_path"],
        "candidate_descriptor": plan["candidate_descriptor"],
        "source_provenance_sha256": plan["source_provenance_sha256"],
        "environment_profile_sha256": plan["environment_profile_sha256"],
        "equivalence_result_sha256": equivalence_sha,
        "incumbent_capture_sha256": plan["request_fixture_sha256"],
        "port_release_proof": {"port": plan["canary_port"], "released": True},
        "runtime_artifact_policy": plan["runtime_artifact_policy"],
    }
    closeout["canonical_sha256"] = canonical_sha256(closeout)
    return closeout


def test_r3x_environment_reference_contradiction_is_rejected() -> None:
    metadata = build_environment_reference_metadata()
    strict = validate_environment_reference_metadata_strict(metadata)
    assert strict["valid"] is False
    assert "approved_secure_reference_missing" in strict["blockers"]
    assert "approved_secure_reference_not_required" in strict["blockers"]


def test_environment_matrix_and_profile_are_complete_without_env_value_access() -> None:
    matrix = build_runtime_variable_matrix()
    matrix_validation = validate_runtime_variable_matrix(matrix)
    assert matrix_validation["valid"] is True
    assert matrix_validation["counts"]["startup_required"] == 2
    assert matrix_validation["counts"]["optional"] == 12
    assert matrix["values_read"] is False
    assert matrix["proc_environ_read"] is False
    validate_by_schema_version(matrix)

    profile = build_environment_profile_v1(variable_matrix=matrix)
    profile_validation = validate_environment_profile_v1(profile)
    assert profile_validation["valid"] is True
    assert profile_validation["secure_env_reference_required"] is False
    assert profile["base_environment_mode"] == "clean_allowlist"
    assert profile["bounded_overrides"]["only_differences_allowed"] == ["APP_HOST", "APP_PORT"]
    assert profile["candidate_runtime_artifacts_excluded_from_source_descriptor"] is True
    validate_by_schema_version(profile)


def test_environment_profile_rejects_unexplained_canary_production_difference() -> None:
    profile = build_environment_profile_v1()
    profile["bounded_overrides"]["future_production"]["DATABASE_PATH"] = "/tmp/prod.db"
    profile["canonical_sha256"] = canonical_sha256(profile)
    validation = validate_environment_profile_v1(profile)
    assert validation["valid"] is False
    assert "unexplained_canary_production_environment_diff" in validation["blockers"]


def test_equivalence_allows_body_hash_difference_but_blocks_new_degradation() -> None:
    contract = build_equivalence_contract_v1()
    assert validate_equivalence_contract_v1(contract)["valid"] is True
    validate_by_schema_version(contract)

    incumbent = _capture(warnings=["missing_model"], body_sha="a" * 64)
    canary_same_shape = _capture(warnings=["missing_model"], body_sha="b" * 64)
    ok = validate_incumbent_canary_equivalence(incumbent, canary_same_shape, contract)
    assert ok["valid"] is True
    assert ok["body_sha_comparison"] == "diagnostic_only"

    canary_worse = _capture(warnings=["missing_model", "missing_database"], body_sha="c" * 64)
    worse = validate_incumbent_canary_equivalence(incumbent, canary_worse, contract)
    assert worse["valid"] is False
    assert "new_blocking_degradation" in worse["blockers"]
    assert worse["new_degradation_categories"] == ["missing_database"]


def test_precutover_canary_plan_and_approval_are_canary_only() -> None:
    plan = build_precutover_canary_plan_v1(final_head="52e93c4811f17f41e847aed1e544f89e28156ecd", runtime_identity=_runtime())
    validation = validate_precutover_canary_plan_v1(plan)
    assert validation["valid"] is True
    assert validation["action_count"] == 67
    assert plan["runtime_artifact_policy"]["runtime_artifacts_excluded_from_source_descriptor"] is True
    validate_by_schema_version(plan)

    approval = build_machine_precutover_canary_approval(plan)
    approval_validation = validate_machine_precutover_canary_approval(approval, plan)
    assert approval_validation["valid"] is True
    assert approval["permissions"]["canary_process_start"] is True
    assert approval["permissions"]["canary_process_stop"] is True
    assert approval["permissions"]["incumbent_sigterm"] is False
    assert approval["permissions"]["source_root_cutover"] is False
    assert approval["permissions"]["p2s_stage"] is False
    assert approval["permissions"]["first_cycle"] is False
    validate_by_schema_version(approval)

    request_like = dict(approval)
    request_like["status"] = "awaiting_machine_approval"
    request_like["canonical_sha256"] = canonical_sha256(request_like)
    rejected = validate_machine_precutover_canary_approval(request_like, plan)
    assert rejected["valid"] is False
    assert "approval_not_approved" in rejected["blockers"]


def test_candidate_materialization_uses_no_hardlinks_in_temp_root(tmp_path: Path) -> None:
    plan = build_precutover_canary_plan_v1(
        final_head="52e93c4811f17f41e847aed1e544f89e28156ecd",
        runtime_identity=_runtime(),
        target_root=tmp_path / "canonical",
    )
    result, ledger = materialize_candidate(plan)
    assert result["valid"] is True
    assert result["written_action_count"] == 67
    assert result["hardlink_count"] == 0
    assert ledger["entry_count"] == 67


def test_recovery_p2s_cycle_and_conditional_approval_chain_are_blocked_in_order() -> None:
    plan = build_precutover_canary_plan_v1(final_head="52e93c4811f17f41e847aed1e544f89e28156ecd", runtime_identity=_runtime())
    contract = build_equivalence_contract_v1()
    closeout = _closeout(plan, contract["canonical_sha256"])
    recovery = build_source_loss_recovery_plan_v4(precutover_closeout=closeout, runtime_identity=_runtime())
    recovery_validation = validate_source_loss_recovery_plan_v4(recovery)
    assert recovery_validation["valid"] is True
    assert recovery["requested_permissions"]["irreversible_source_loss_cutover_acknowledged"] is True
    validate_by_schema_version(recovery)

    p2s = build_full_p2s_rebase_plan_v4(recovery)
    p2s_validation = validate_full_p2s_rebase_plan_v4(p2s)
    assert p2s_validation["valid"] is True
    assert p2s_validation["physical_action_count"] >= 1640
    assert p2s_validation["risk_fraud_projected_file_count"] == 67
    assert p2s["stage_request_status"] == "blocked_pending_recovery_settle"
    assert p2s["activation_template_status"] == "blocked_pending_real_stage_closeout"
    validate_by_schema_version(p2s)

    selected = reselect_first_candidate()["selected_candidate"]
    experiment = build_projected_experiment_v4(selected, p2s)
    cycle = build_first_real_cycle_plan_v4(selected, experiment, p2s)
    assert experiment["status"] == "blocked_pending_p2s_activation_closeout"
    assert cycle["status"] == "blocked_pending_p2s_activation_closeout"
    validate_by_schema_version(experiment)
    validate_by_schema_version(cycle)

    chain = build_conditional_approval_chain_v1(
        canary_closeout=closeout,
        recovery_v4=recovery,
        p2s_v4=p2s,
        experiment_v4=experiment,
        cycle_v4=cycle,
    )
    chain_validation = validate_conditional_approval_chain_v1(chain)
    assert chain_validation["valid"] is True
    assert [node["status"] for node in chain["nodes"]] == [
        "executed_and_closed",
        "awaiting_machine_approval",
        "blocked_pending_recovery_settle",
        "blocked_pending_real_stage_closeout",
        "blocked_pending_p2s_activation_closeout",
        "blocked_pending_experiment_validation",
    ]
    validate_by_schema_version(chain)

    broad = dict(chain)
    broad["nodes"] = [dict(node, status="awaiting_machine_approval") for node in chain["nodes"]]
    broad["canonical_sha256"] = canonical_sha256(broad)
    rejected = validate_conditional_approval_chain_v1(broad)
    assert rejected["valid"] is False
    assert "approval_chain_status_order_invalid" in rejected["blockers"]


def test_risk_fraud_v4_cli_freezes_precutover_only() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "risk-fraud",
            "freeze-source-loss-v4",
            "--final-head",
            "52e93c4811f17f41e847aed1e544f89e28156ecd",
            "--pid",
            "740899",
            "--start-ticks",
            "12455435",
            "--cwd",
            "/sdb/dlut/prod/财务造假风险智能体",
            "--exe",
            "/usr/bin/python3.14",
            "--argv-json",
            "[\"python3\", \"-u\", \"-m\", \"app.main\"]",
            "--stdout-json",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["precutover_canary_plan_validation"]["valid"] is True
    assert payload["precutover_canary_approval_validation"]["valid"] is True
    assert payload["conditional_approval_chain_validation"]["valid"] is True
    permissions = payload["machine_precutover_canary_approval"]["permissions"]
    assert permissions["incumbent_sigterm"] is False
    assert permissions["p2s_stage"] is False
