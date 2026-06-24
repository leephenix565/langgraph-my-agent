"""Focused S2P transaction and rehearsal tests."""

from __future__ import annotations

from pathlib import Path

from react_agent.ops.sync_contracts import file_sha256
from react_agent.ops.sync_s2p import (
    apply_file_actions,
    build_s2p_noop_approval,
    fake_live_gate,
    fake_process_action,
    prepare_transaction_backups,
    recover_s2p_journal,
    run_temp_historical_replay,
    validate_s2p_approval,
)


def _minimal_noop_plan() -> dict:
    return {
        "plan_id": "s2p_test_noop",
        "canonical_sha256": "abc123",
        "agents": [{"agent_id": "agent_a", "transaction_id": "txn_a", "actions": []}],
        "transactions": [{"transaction_id": "txn_a", "affected_agent_ids": ["agent_a"]}],
        "s2p_summary": {"actionable_file_action_count": 0},
    }


def test_s2p_noop_approval_has_empty_action_scope() -> None:
    plan = _minimal_noop_plan()
    approval = build_s2p_noop_approval(plan, operator_reference="unit-test")
    result = validate_s2p_approval(approval, plan, require_noop=True)
    assert result["valid"] is True
    assert approval["approved_action_ids"] == []
    assert approval["noop_run_approved"] is True
    assert approval["process_actions_approved"] is False
    assert approval["live_validation_approved"] is False


def test_s2p_noop_approval_rejects_nonempty_action_scope() -> None:
    plan = _minimal_noop_plan()
    approval = build_s2p_noop_approval(plan, operator_reference="unit-test")
    approval["approved_action_ids"] = ["unexpected-action"]
    result = validate_s2p_approval(approval, plan, require_noop=True)
    assert result["valid"] is False
    assert "approved_action_ids_outside_plan_scope" in result["blockers"]
    assert "noop_approval_action_scope_not_empty" in result["blockers"]


def test_transaction_apply_failure_rolls_back_target(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    target = tmp_path / "prod" / "source.py"
    target.parent.mkdir()
    source.write_text("VALUE = 2\n", encoding="utf-8")
    target.write_text("VALUE = 1\n", encoding="utf-8")
    before = file_sha256(target)
    action = {
        "operation": "replace",
        "source_absolute_path": str(source),
        "target_absolute_path": str(target),
        "target_path": "source.py",
        "source_sha256": file_sha256(source),
        "expected_target_before_sha256": before,
    }
    backup = prepare_transaction_backups([action], tmp_path / "backup")
    result = apply_file_actions([action], backup_manifest=backup, fail_after=1)
    assert result["status"] == "rolled_back"
    assert file_sha256(target) == before
    assert result["rollback"]["valid"] is True


def test_fake_process_and_live_gate_are_separate_permissions() -> None:
    assert fake_process_action("txn", approved=False)["executed"] is False
    assert fake_live_gate("txn", approved=False)["executed"] is False
    assert fake_process_action("txn", approved=True)["raw_cmdline_persisted"] is False
    failed_smoke = fake_live_gate("txn", approved=True, fail=True)
    assert failed_smoke["executed"] is True
    assert failed_smoke["valid"] is False
    assert failed_smoke["raw_body_persisted"] is False


def test_recovery_classifies_partial_apply_as_rollback_required() -> None:
    result = recover_s2p_journal(
        [
            {"event_type": "backup_started"},
            {"event_type": "backup_file_verified"},
            {"event_type": "file_replaced"},
        ]
    )
    assert result["recommended_action"] == "rollback_required"


def test_temp_historical_replay_uses_nonzero_fixture_and_restores(tmp_path: Path) -> None:
    result = run_temp_historical_replay(tmp_path / "replay")
    assert result["valid"] is True
    assert result["imported_change_unit_count"] == 31
    assert result["exact_byte_replay_count"] == 6
    assert result["patch_replay_count"] == 21
    assert result["contract_equivalent_fixture_count"] == 4
    assert result["apply_result"]["status"] == "applied_and_verified"
    assert result["rollback_result"]["valid"] is True
    assert result["restoration_proof"]["restored_to_baseline"] is True
    assert result["fake_restart_result"]["executed"] is True
    assert result["fake_smoke_result"]["executed"] is True
