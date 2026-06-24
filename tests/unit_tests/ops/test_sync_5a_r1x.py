"""SYNC-OPS-5A-R1X source authority and final freeze tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from react_agent.ops.sync_5a_r1x import (
    OLD_REPAIR_REJECTION_REASONS,
    build_final_compound_execution_approval_request,
    build_final_compound_execution_plan,
    build_first_cycle_projection,
    build_projected_experiment_contract,
    build_risk_fraud_authority_decision,
    build_risk_fraud_p2s_rebase_plan,
    build_risk_fraud_prod_recovery_plan,
    build_risk_fraud_source_authority_matrix,
    requalify_financial_data_service_candidate,
    validate_final_compound_execution_plan,
    validate_old_risk_fraud_repair_plan,
    validate_risk_fraud_p2s_rebase_plan,
    validate_risk_fraud_prod_recovery_plan,
)
from react_agent.ops.sync_contracts import canonical_sha256, validate_by_schema_version


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _source_root(tmp_path: Path) -> Path:
    root = tmp_path / "historical" / "risk_financial_fraud"
    _write(root / "app/agent/core.py", "def compute_core():\n    return {'ok': True}\n")
    _write(root / "app/main.py", "from app.agent.core import compute_core\n")
    _write(root / "tests/test_report_material.py", "def test_material():\n    assert True\n")
    _write(root / "app/__init__.py", "")
    _write(root / "app/agent/__init__.py", "")
    return root


def test_old_67_action_repair_plan_is_rejected() -> None:
    plan = {
        "plan_id": "p2s_repair_risk_financial_fraud_20260624T151015Z",
        "planned_file_count": 67,
        "stage_path": "/sdb/dlut/sandbox/prod-baselines/<repair-run-id>/fixed-dag-services",
        "canonical_sha256": "b90944d61a6dd4d56dd14d79667b34a48852ba6835c4719f6561b5e076ed8343",
    }
    result = validate_old_risk_fraud_repair_plan(plan)
    assert result["valid"] is False
    for reason in OLD_REPAIR_REJECTION_REASONS:
        assert reason in result["rejection_reasons"]


def test_old_repair_cli_exits_validation_failure(tmp_path: Path) -> None:
    plan = {
        "plan_id": "p2s_repair_risk_financial_fraud_20260624T151015Z",
        "planned_file_count": 67,
        "stage_path": "/sdb/dlut/sandbox/prod-baselines/<repair-run-id>/fixed-dag-services",
        "canonical_sha256": "b90944d61a6dd4d56dd14d79667b34a48852ba6835c4719f6561b5e076ed8343",
    }
    plan_path = tmp_path / "old_repair_plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "risk-fraud",
            "validate-old-repair",
            "--plan",
            str(plan_path),
            "--stdout-json",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 7
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert "current_prod_after_state_projection_missing" in payload["rejection_reasons"]


def test_source_deleted_decision_and_recovery_plan(tmp_path: Path) -> None:
    prod = tmp_path / "prod" / "财务造假风险智能体"
    prod.mkdir(parents=True)
    source = _source_root(tmp_path)
    matrix = build_risk_fraud_source_authority_matrix(
        prod_root=prod,
        historical_root=source,
        owner_root=tmp_path / "owner",
        active_root=tmp_path / "missing-active",
        versioned_root=tmp_path / "missing-versioned",
    )
    for row in matrix["candidates"]:
        if row["role"] == "historical_baseline_20260623T050419Z":
            row["known_hash_matches"] = {"app/agent/core.py": True, "tests/test_report_material.py": True}
    runtime = {
        "listener_exists": True,
        "pid": "740899",
        "cwd": str(prod),
        "runtime_authority_unresolved": True,
        "source_deleted_process_still_alive": True,
    }
    decision = build_risk_fraud_authority_decision(matrix, runtime)
    assert decision["classification"] == "source_deleted_or_lost_but_service_should_exist"
    assert decision["valid"] is True

    plan = build_risk_fraud_prod_recovery_plan(source_root=source, target_root=prod, runtime_audit=runtime)
    validation = validate_risk_fraud_prod_recovery_plan(plan)
    assert validation["valid"] is True
    validate_by_schema_version(plan)
    assert validation["action_count"] == 5
    assert plan["process_contract"]["process_required"] is True
    assert plan["live_validation_contract"]["compute_required"] is True
    assert all(action["operation"] == "add" for action in plan["file_actions"])


def test_p2s_rebase_is_full_baseline_and_approval_split(tmp_path: Path) -> None:
    recovery = build_risk_fraud_prod_recovery_plan(source_root=_source_root(tmp_path), target_root=tmp_path / "prod")
    p2s = build_risk_fraud_p2s_rebase_plan(recovery)
    validation = validate_risk_fraud_p2s_rebase_plan(p2s)
    assert validation["valid"] is True
    validate_by_schema_version(p2s)
    assert validation["agent_disposition_count"] == 26
    assert validation["projected_file_count"] > validation["risk_fraud_projected_file_count"]
    assert p2s["stage_approval_request"]["activate_requested"] is False
    assert p2s["activation_request_template"]["activate_requested"] is True


def test_financial_candidate_runtime_wrapper_is_not_docs_only(tmp_path: Path) -> None:
    patch = tmp_path / "main.py.patch"
    rollback = tmp_path / "main.py.u0.patch"
    sandbox_test = tmp_path / "tests/test_fixed_dag_compute.py"
    _write(
        patch,
        """--- old/app/main.py
+++ new/app/main.py
+@app.post(\"/v1/agent/compute\")
+def compute():
+    return {\"feature_bundle\": {}, \"data_bundle\": {}}
+app.mount(\"/static/docs\", StaticFiles(directory=str(settings.doc_storage_path)), name=\"docs\")
""",
    )
    _write(rollback, "reverse patch\n")
    _write(sandbox_test, "def test_compute():\n    assert True\n")
    result = requalify_financial_data_service_candidate(
        patch_path=patch,
        rollback_patch_path=rollback,
        sandbox_test_path=sandbox_test,
    )
    assert result["risk_class"] == "B_protocol_wrapper"
    assert result["process_required"] is True
    assert result["live_required"] is True
    assert result["superseded"] is True
    assert result["unsafe_as_first_nonzero_candidate"] is True
    assert result["delete_required"] is False


def test_compound_plan_binds_phase_hashes_and_request_permissions(tmp_path: Path) -> None:
    runtime = {"listener_exists": True, "pid": "740899", "cwd": str(tmp_path / "prod")}
    recovery = build_risk_fraud_prod_recovery_plan(source_root=_source_root(tmp_path), target_root=tmp_path / "prod", runtime_audit=runtime)
    p2s = build_risk_fraud_p2s_rebase_plan(recovery)
    patch = tmp_path / "main.patch"
    rollback = tmp_path / "main.u0.patch"
    _write(patch, "+feature_bundle\n+StaticFiles\n")
    _write(rollback, "-feature_bundle\n")
    candidate = requalify_financial_data_service_candidate(
        patch_path=patch,
        rollback_patch_path=rollback,
        sandbox_test_path=tmp_path / "tests/test_fixed_dag_compute.py",
    )
    projected_experiment = build_projected_experiment_contract(candidate, p2s)
    first_cycle = build_first_cycle_projection(candidate, projected_experiment)
    compound = build_final_compound_execution_plan(recovery, p2s, projected_experiment, first_cycle)
    assert compound["canonical_sha256"] == canonical_sha256(compound)
    assert validate_final_compound_execution_plan(compound)["valid"] is True
    validate_by_schema_version(compound)
    request = build_final_compound_execution_approval_request(compound)
    validate_by_schema_version(request)
    assert request["status"] == "awaiting_machine_approval"
    assert request["process_action_requested"] is True
    assert request["first_cycle_process_requested"] is True
    assert request["delete_requested"] is False
    assert request["approval_id"] == ""
