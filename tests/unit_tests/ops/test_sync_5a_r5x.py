"""SYNC-OPS-5A-R5X exact source-loss cutover tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from react_agent.ops import sync_5a_r5x
from react_agent.ops.sync_5a_r2x import reselect_first_candidate
from react_agent.ops.sync_5a_r5x import (
    R4X_CANARY_PATH,
    build_conditional_approval_chain_v5,
    build_cutover_tree_descriptor,
    build_first_real_cycle_plan_v5,
    build_full_p2s_activation_template_v5,
    build_full_p2s_rebase_plan_v5,
    build_full_p2s_stage_request_v5,
    build_production_launch_authority_v1,
    build_projected_experiment_v5,
    build_real_readonly_preflight,
    build_source_loss_cutover_approval_request_v5,
    build_source_loss_recovery_plan_v5,
    port_listening,
    run_temp_source_loss_cutover_simulation,
    validate_conditional_approval_chain_v5,
    validate_full_p2s_rebase_plan_v5,
    validate_production_launch_authority_v1,
    validate_source_loss_cutover_approval_request_v5,
    validate_source_loss_recovery_plan_v5,
    validate_v4_cutover_plan_superseded,
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
        "candidate_path": str(R4X_CANARY_PATH),
        "candidate_descriptor": {
            "schema_version": "agent_sync_digest_descriptor_v1",
            "algorithm": "sha256",
            "digest": "e6f4d26e29074a59245ed809aadea1ebdf74bff5d1c2cea16b45a7a4e647b6e5",
            "scope": "transaction_source_tree",
            "root_role": "source_loss_recovery_candidate",
            "include_profile": "source_bearing_default",
            "relative_path_basis": "posix",
            "entry_contract_version": "sync_inventory_root_v1",
            "file_count": 67,
        },
        "source_provenance_sha256": "71832769e4c68d234aa7f9487e1c58b634da795aba7b6ca300f282f84ceac63f",
        "environment_profile_sha256": "c6ea8f94673814386cb030d37afc426d978347643809f1103cc348531342658a",
        "equivalence_result_sha256": "28d295870aed3433a020495dc183e4965bfa9fff2e40d5698814748c21d403ad",
        "incumbent_capture_sha256": "bc171af3929cb8a079380be69dc643d75896b5d7d3015b505e84b1b116bd4e42",
        "port_release_proof": {"port": 11013, "released": True},
    }
    closeout["canonical_sha256"] = canonical_sha256(closeout)
    return closeout


def test_v4_plan_is_superseded_for_missing_exact_cutover_fields() -> None:
    v4 = {
        "schema_version": "agent_sync_source_loss_recovery_plan_v4",
        "plan_id": "source_loss_recovery_v4_9204c6e90294",
        "candidate_path": str(R4X_CANARY_PATH),
        "candidate_descriptor": {"file_count": 67},
        "projected_prod_after_descriptor": {"file_count": 67},
        "requested_permissions": {"irreversible_source_loss_cutover_acknowledged": True, "sigkill": False},
        "canonical_sha256": "0" * 64,
    }
    result = validate_v4_cutover_plan_superseded(v4)
    assert result["valid_for_v5_execution"] is False
    assert result["supersession_reason"] == "superseded_due_exact_cutover_action_full_tree_and_production_launch_contract"
    assert "canonical_target_path" in result["missing_fields"]
    assert "fresh_cutover_candidate_path" in result["missing_fields"]
    assert "production_launch_authority" in result["missing_fields"]


def test_cutover_tree_descriptor_counts_runtime_without_reading_env(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    (root / "app").mkdir(parents=True)
    (root / "app" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "x.pyc").write_bytes(b"\x00\x00")
    (root / ".env").write_text("SECRET=value\n", encoding="utf-8")
    descriptor = build_cutover_tree_descriptor(root, root_role="test_tree")
    assert descriptor["runtime_artifact_count"] >= 1
    assert descriptor["sensitive_entry_count"] >= 1
    assert descriptor["source_bearing_descriptor"]["file_count"] == 1
    validate_by_schema_version(descriptor)


def test_production_launch_authority_is_exact_and_rejects_sigkill() -> None:
    authority = build_production_launch_authority_v1(
        plan_id="source_loss_recovery_v5_test",
        environment_profile_sha256="c6ea8f94673814386cb030d37afc426d978347643809f1103cc348531342658a",
    )
    validation = validate_production_launch_authority_v1(authority)
    assert validation["valid"] is True
    assert authority["cwd"] == "/sdb/dlut/prod/财务造假风险智能体"
    assert authority["production_port"] == 10013
    assert authority["stop_contract"]["sigkill_allowed"] is False
    validate_by_schema_version(authority)

    bad = dict(authority)
    bad["stop_contract"] = dict(authority["stop_contract"], sigkill_allowed=True)
    bad["canonical_sha256"] = canonical_sha256(bad)
    rejected = validate_production_launch_authority_v1(bad)
    assert rejected["valid"] is False
    assert "sigkill_must_be_false" in rejected["blockers"]


def test_recovery_v5_binds_fresh_candidate_full_tree_actions_and_request() -> None:
    plan = build_source_loss_recovery_plan_v5(
        final_head="c523280a77171ebbc81e6dccb40b2fc77cb74639",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
    )
    validation = validate_source_loss_recovery_plan_v5(plan)
    assert validation["valid"] is True
    assert validation["file_action_count"] == 67
    assert validation["cutover_action_count"] == 22
    assert validation["exact_action_count"] == 89
    assert plan["fresh_cutover_candidate_path"] != plan["canary_evidence_path"]
    assert plan["archive_path"].startswith("/sdb/dlut/prod/.agent-sync-archive-risk-fraud-")
    assert plan["fresh_candidate_expected_source_descriptor"]["file_count"] == 67
    assert plan["requested_permissions"]["sigkill"] is False
    validate_by_schema_version(plan)

    request = build_source_loss_cutover_approval_request_v5(plan)
    request_validation = validate_source_loss_cutover_approval_request_v5(request, plan)
    assert request_validation["valid"] is True
    assert request["status"] == "awaiting_machine_approval"
    assert request["approval_id"] == ""
    assert request["permissions"]["p2s"] is False
    assert request["endpoint_scopes"]["invoke"] is False
    validate_by_schema_version(request)


def test_dirty_canary_reuse_is_rejected() -> None:
    plan = build_source_loss_recovery_plan_v5(
        final_head="c523280a77171ebbc81e6dccb40b2fc77cb74639",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
    )
    plan["fresh_cutover_candidate_path"] = plan["canary_evidence_path"]
    plan["canonical_sha256"] = canonical_sha256(plan)
    validation = validate_source_loss_recovery_plan_v5(plan)
    assert validation["valid"] is False
    assert "dirty_canary_reuse_forbidden" in validation["blockers"]


def test_downstream_v5_chain_stays_blocked_after_cutover_request() -> None:
    recovery = build_source_loss_recovery_plan_v5(
        final_head="c523280a77171ebbc81e6dccb40b2fc77cb74639",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
    )
    p2s = build_full_p2s_rebase_plan_v5(recovery)
    p2s_validation = validate_full_p2s_rebase_plan_v5(p2s)
    assert p2s_validation["valid"] is True
    assert p2s["stage_request_status"] == "blocked_pending_recovery_settle"
    assert p2s["activation_template_status"] == "blocked_pending_real_stage_closeout"
    validate_by_schema_version(p2s)

    stage_request = build_full_p2s_stage_request_v5(p2s)
    activation_template = build_full_p2s_activation_template_v5(p2s)
    assert stage_request["activate"] is False
    assert activation_template["stage"] is False
    validate_by_schema_version(stage_request)
    validate_by_schema_version(activation_template)

    selected = reselect_first_candidate()["selected_candidate"]
    experiment = build_projected_experiment_v5(selected, p2s)
    cycle = build_first_real_cycle_plan_v5(selected, experiment, p2s)
    chain = build_conditional_approval_chain_v5(
        canary_closeout=_closeout(),
        recovery_v5=recovery,
        p2s_v5=p2s,
        experiment_v5=experiment,
        cycle_v5=cycle,
    )
    chain_validation = validate_conditional_approval_chain_v5(chain)
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


def test_temp_source_loss_simulation_covers_failure_and_recovery_paths(tmp_path: Path) -> None:
    normal, failures, recovery = run_temp_source_loss_cutover_simulation(tmp_path)
    assert normal["valid"] is True
    assert normal["dirty_canary_reused"] is False
    assert normal["sigkill_used"] is False
    assert "sigterm_timeout_manual_intervention" in failures["covered_cases"]
    assert "port_not_released_manual_intervention" in failures["covered_cases"]
    assert "candidate_rename_failure_restore_archive_path_service_down" in failures["covered_cases"]
    assert "RECOVERED_STARTING" in recovery["crash_recovery_states"]
    assert recovery["no_old_service_false_rollback"] is True


def test_source_loss_execute_requires_machine_approval(tmp_path: Path) -> None:
    plan = build_source_loss_recovery_plan_v5(
        final_head="c523280a77171ebbc81e6dccb40b2fc77cb74639",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
    )
    plan_path = tmp_path / "plan.json"
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


def test_readonly_preflight_reports_no_actions_with_fixture_runtime() -> None:
    recovery = build_source_loss_recovery_plan_v5(
        final_head="c523280a77171ebbc81e6dccb40b2fc77cb74639",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
    )
    preflight = build_real_readonly_preflight(expected_runtime_identity=_runtime(), recovery_v5=recovery)
    assert preflight["endpoint_calls"] == 0
    assert preflight["process_actions"] == 0
    assert preflight["canonical_writes"] == 0
    assert preflight["env_values_read"] is False


def test_port_listening_fails_closed_when_socket_probe_is_denied(monkeypatch) -> None:
    def deny_socket(*_args, **_kwargs):
        raise PermissionError("sandbox socket creation denied")

    monkeypatch.setattr(sync_5a_r5x.socket, "socket", deny_socket)

    assert port_listening(sync_5a_r5x.PRODUCTION_PORT) is False


def test_readonly_preflight_reuses_fail_closed_listener_probe(monkeypatch) -> None:
    calls: list[int] = []

    def denied_listener_probe(port: int) -> bool:
        calls.append(port)
        return False

    monkeypatch.setattr(sync_5a_r5x, "port_listening", denied_listener_probe)
    recovery = build_source_loss_recovery_plan_v5(
        final_head="c523280a77171ebbc81e6dccb40b2fc77cb74639",
        precutover_closeout=_closeout(),
        runtime_identity=_runtime(),
    )

    preflight = build_real_readonly_preflight(expected_runtime_identity=_runtime(), recovery_v5=recovery)

    assert calls == [sync_5a_r5x.PRODUCTION_PORT]
    assert preflight["listener_10013"] is False
    assert preflight["valid"] is False
    assert "production_port_not_listening" in preflight["blockers"]
    assert preflight["endpoint_calls"] == 0
    assert preflight["process_actions"] == 0
    assert preflight["canonical_writes"] == 0
    assert preflight["env_values_read"] is False
