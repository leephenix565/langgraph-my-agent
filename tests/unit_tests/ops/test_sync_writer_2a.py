"""Tests for SYNC-OPS-2A P2S writer contracts in temp roots."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from react_agent.ops.sync_approval import validate_approval
from react_agent.ops.sync_artifacts import ArtifactRunStore
from react_agent.ops.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    file_sha256,
    stable_id,
    write_json,
)
from react_agent.ops.sync_environment import build_environment_snapshot
from react_agent.ops.sync_lock import SyncLockManager
from react_agent.ops.sync_p2s import (
    p2s_activate,
    p2s_recover,
    p2s_rollback,
    p2s_stage,
    p2s_verify,
)
from react_agent.ops.sync_plan import stage_projection_digest_for_actions, validate_plan
from react_agent.ops.sync_registry import load_static_registry


def _future(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _temp_plan(tmp_path: Path) -> dict[str, object]:
    registry = load_static_registry()
    prod = tmp_path / "prod"
    active = tmp_path / "active"
    pointer = tmp_path / "PROD_BASELINE_POINTER.json"
    stage_root = tmp_path / "versioned" / "fixed-dag-services"
    active.mkdir()
    pointer.write_text("{}\n", encoding="utf-8")
    agents: list[dict[str, object]] = []
    transactions: list[dict[str, object]] = []
    all_actions: list[dict[str, object]] = []
    for index, agent in enumerate(registry["agents"]):
        agent_id = str(agent["agent_id"])
        source_dir = prod / agent_id
        source_dir.mkdir(parents=True)
        if agent_id == "risk_crash":
            rel = "part3_panelExp/core/base_funces/skmodels.py"
            source = source_dir / rel
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("BROKEN =\n", encoding="utf-8")
        else:
            rel = "service.py"
            source = source_dir / rel
            source.write_text(f"VALUE_{index} = {index}\n", encoding="utf-8")
        source_sha = file_sha256(source)
        action = {
            "action_id": stable_id("mat", agent_id, rel),
            "operation": "copy_from_prod",
            "agent_id": agent_id,
            "affected_agent_ids": [agent_id],
            "transaction_root": str(source_dir),
            "source_path": rel,
            "source_absolute_path": str(source),
            "source_sha256": source_sha,
            "source_mode": "0o644",
            "source_file_type": "regular",
            "source_executable": False,
            "source_symlink_target": "",
            "destination_relative_path": rel,
            "stage_relative_path": f"{agent_id}/{rel}",
            "sensitive_classification": "none",
            "large_asset_classification": "not_large_asset",
        }
        txn_id = stable_id("stage", agent_id, str(source_dir))
        agents.append(
            {
                "agent_id": agent_id,
                "transaction_id": txn_id,
                "source_root": "prod",
                "target_root": str(stage_root / agent_id),
                "target_before_tree_sha256": "active-digest",
                "active_tree_sha256": "active-digest",
                "prod_tree_sha256": source_sha,
                "projection_digest": stage_projection_digest_for_actions([action]),
                "disposition": "stage_from_prod",
                "actions": [action],
                "blocked_actions": [],
                "backup": {},
                "offline_tests": [],
                "process_preflight": {},
                "process_actions": [],
                "live_validation": [],
                "rollback": {},
                "expected_status": "stage_ready",
            }
        )
        transactions.append(
            {
                "transaction_id": txn_id,
                "transaction_root": str(source_dir),
                "agent_id": agent_id,
                "affected_agent_ids": [agent_id],
                "disposition": "stage_from_prod",
                "projection_digest": stage_projection_digest_for_actions([action]),
                "actions": [action],
                "blocked_actions": [],
            }
        )
        all_actions.append(action)
    plan: dict[str, object] = {
        "schema_version": "agent_sync_plan_v1",
        "tool_version": "sync_ops_2a_writer_contract_planner_test",
        "test_only_temp_roots": True,
        "plan_id": "p2s-temp-e2e",
        "direction": "p2s",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "expires_at": _future(),
        "registry_sha256": "r" * 64,
        "policy_sha256": "p" * 64,
        "catalog_sha256": "c" * 64,
        "baseline": {"versioned_baseline_path": str(tmp_path / "old-versioned")},
        "experiment": {},
        "target_snapshot": {
            "active_sandbox_path": str(active),
            "active_sandbox_pointer_sha256": file_sha256(pointer),
            "active_baseline_tree_sha256": "active-tree",
            "versioned_baseline_tree_sha256": "old-tree",
        },
        "observed_diff": {"summary": {}},
        "stage_materialization": {
            "baseline_id": "temp-baseline",
            "stage_root": str(stage_root),
            "expected_stage_root_state": "missing",
            "transactions": transactions,
            "action_counts": {"copy_from_prod": len(all_actions)},
            "expected_stage_projection_digest": stage_projection_digest_for_actions(all_actions),
        },
        "activation": {
            "old_active_sandbox_archive_path": str(tmp_path / "active-pre-syncops-temp"),
            "new_versioned_baseline_path": str(stage_root),
            "pointer_candidate": {
                "path": str(pointer),
                "active_baseline_id": "temp-baseline",
                "active_path": str(active),
                "versioned_baseline_path": str(stage_root),
            },
            "preconditions": {
                "active_pointer_sha256": file_sha256(pointer),
                "active_baseline_tree_sha256": "active-tree",
                "old_active_path": str(active),
                "expected_stage_root_state": "missing",
            },
            "rollback": {"restore_old_active_path": str(active)},
        },
        "coverage": {"unresolved_file_count": 0, "coverage_ratio": 1.0},
        "validation_profile": {"risk_crash/part3_panelExp/core/base_funces/skmodels.py": "legacy_reference_python"},
        "agents": agents,
        "global_preconditions": [],
        "global_blockers": [],
        "approval_requirements": {
            "approval_record_required": True,
            "environment_snapshot_required": True,
            "stage_approved": True,
            "activate_approved": True,
            "rollback_approved": True,
            "delete_actions_approved": False,
            "process_actions_approved": False,
            "live_validation_approved": False,
            "publish_and_rebase_approved": False,
        },
        "rollback_plan": {},
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def _approval(plan: dict[str, object], *, stage: bool = True, activate: bool = True, rollback: bool = True) -> dict[str, object]:
    env = build_environment_snapshot(plan)
    return {
        "schema_version": "agent_sync_approval_v1",
        "approval_id": "approval-temp",
        "status": "approved",
        "plan_id": plan["plan_id"],
        "plan_sha256": plan["canonical_sha256"],
        "environment_snapshot_sha256": env["environment_snapshot_sha256"],
        "approved_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "expires_at": _future(),
        "execution_phase": "SYNC-OPS-2B",
        "approved_agent_ids": [agent["agent_id"] for agent in plan["agents"]],  # type: ignore[index]
        "approved_transaction_ids": [agent["transaction_id"] for agent in plan["agents"]],  # type: ignore[index]
        "approved_action_ids": [
            action["action_id"]
            for agent in plan["agents"]  # type: ignore[union-attr]
            for action in agent["actions"]  # type: ignore[index]
        ],
        "stage_approved": stage,
        "activate_approved": activate,
        "rollback_approved": rollback,
        "delete_approved": False,
        "process_action_approved": False,
        "live_validation_approved": False,
        "partial_success_rebase_approved": False,
        "operator_reference": "sync-ops-2a-test",
        "notes": "temp fixture",
    }


def test_approval_exact_plan_environment_and_permissions(tmp_path: Path) -> None:
    plan = _temp_plan(tmp_path)
    approval = _approval(plan)
    result = validate_approval(approval, plan, environment_snapshot=build_environment_snapshot(plan), require_stage=True)
    assert result["valid"] is True
    wrong = dict(approval)
    wrong["plan_sha256"] = "0" * 64
    assert validate_approval(wrong, plan, environment_snapshot=build_environment_snapshot(plan))["valid"] is False
    denied = _approval(plan, stage=False)
    assert "approval_stage_not_approved" in validate_approval(
        denied,
        plan,
        environment_snapshot=build_environment_snapshot(plan),
        require_stage=True,
    )["blockers"]


def test_lock_manager_conflict_and_release(tmp_path: Path) -> None:
    manager = SyncLockManager(tmp_path / "artifacts")
    manager.acquire(
        "global-cycle",
        run_id="run-1",
        plan_id="plan",
        plan_sha256="a" * 64,
        direction="p2s",
        agent_scopes=["a"],
        target_roots=["/tmp/a"],
    )
    with pytest.raises(SyncPlannerError, match="lock_conflict"):
        manager.acquire(
            "global-cycle",
            run_id="run-2",
            plan_id="plan",
            plan_sha256="a" * 64,
            direction="p2s",
            agent_scopes=["a"],
            target_roots=["/tmp/a"],
        )
    with pytest.raises(SyncPlannerError, match="lock_owner_mismatch"):
        manager.release("global-cycle", run_id="wrong")
    manager.release("global-cycle", run_id="run-1")
    assert manager.inspect()["lock_count"] == 0


def test_artifact_store_rejects_path_traversal_and_hashes(tmp_path: Path) -> None:
    store = ArtifactRunStore(tmp_path / "artifacts", "run-1")
    store.initialize()
    store.write_json("validation/result.json", {"ok": True})
    with pytest.raises(SyncPlannerError, match="artifact_path_traversal"):
        store.write_json("../escape.json", {})
    index = store.finalize()
    assert index["schema_version"] == "agent_sync_artifact_index_v1"
    assert (store.run_root / "sha256sums.txt").exists()


def test_temp_p2s_stage_verify_activate_rollback_and_recover(tmp_path: Path) -> None:
    plan = _temp_plan(tmp_path)
    assert validate_plan(plan, check_target_freshness=False)["valid"] is True
    approval = _approval(plan)
    plan_path = tmp_path / "plan.json"
    approval_path = tmp_path / "approval.json"
    write_json(plan_path, plan)
    write_json(approval_path, approval)
    artifact_root = tmp_path / "artifact-store"

    stage = p2s_stage(plan_path, approval_path, artifact_root, execute=True)
    assert stage["stage"]["digest_match"] is True
    assert stage["stage"]["py_compile"]["pass"] is True
    assert stage["stage"]["py_compile"]["diagnostic_count"] == 1

    verify = p2s_verify(plan_path, approval_path, artifact_root, execute=True)
    assert verify["valid"] is True

    activate = p2s_activate(plan_path, approval_path, artifact_root, execute=True)
    assert activate["hardlink_count"] == 0
    assert activate["versioned_stage_preserved"] is True
    assert activate["post_switch_validated"] is True

    recover = p2s_recover(artifact_root, str(stage["run_id"]))
    assert recover["recommended_action"] in {"resume_safe", "rollback_required"}

    rollback = p2s_rollback(plan_path, approval_path, artifact_root, execute=True)
    assert rollback["archive_restored"] is True
    assert rollback["failed_baseline_retained"] is True


def test_p2s_write_commands_require_execute(tmp_path: Path) -> None:
    plan = _temp_plan(tmp_path)
    approval = _approval(plan)
    plan_path = tmp_path / "plan.json"
    approval_path = tmp_path / "approval.json"
    write_json(plan_path, plan)
    write_json(approval_path, approval)
    with pytest.raises(SyncPlannerError, match="execute_required"):
        p2s_stage(plan_path, approval_path, tmp_path / "artifact-store", execute=False)

    result = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "react_agent.ops.agent_syncctl",
            "p2s",
            "stage",
            "--plan",
            str(plan_path),
            "--approval",
            str(approval_path),
            "--artifact-root",
            str(tmp_path / "artifact-store-cli"),
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "execute_required" in result.stderr
