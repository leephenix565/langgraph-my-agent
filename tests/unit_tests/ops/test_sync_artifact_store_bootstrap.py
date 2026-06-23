"""Tests for SYNC-OPS-2A-R3 artifact-store bootstrap contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from react_agent.ops.sync_bootstrap import (
    bootstrap_artifact_store,
    build_artifact_store_permission_audit,
    build_bootstrap_approval_request,
    build_bootstrap_environment_snapshot,
    build_bootstrap_plan,
    build_temp_bootstrap_approval,
    rollback_bootstrap,
    validate_bootstrap_approval,
    validate_bootstrap_plan,
    verify_artifact_store,
)
from react_agent.ops.sync_contracts import SyncPlannerError, write_json
from react_agent.ops.sync_plan import build_p2s_plan


def _tree_listing(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


def test_bootstrap_plan_uses_exact_actions_and_hash(tmp_path: Path) -> None:
    root = tmp_path / "ops-artifacts" / "agent-sync"
    plan = build_bootstrap_plan(root)
    environment = build_bootstrap_environment_snapshot(plan)
    request = build_bootstrap_approval_request(plan, environment)
    validation = validate_bootstrap_plan(plan)

    assert validation["valid"] is True
    assert plan["root"] == str(root.resolve(strict=False))
    assert plan["serialization"]["strategy"] == "atomic_mkdir_root"
    assert plan["directory_actions"][0]["operation"] == "mkdir_exact"
    assert all(action["owner_strategy"] == "current_operator" for action in plan["directory_actions"])
    assert all(action["group_strategy"] == "normal_filesystem_inheritance" for action in plan["directory_actions"])
    assert {action["mode"] for action in plan["directory_actions"]} <= {"0750", "0700"}
    assert request["status"] == "awaiting_machine_approval"
    assert request["bootstrap_requested"] is True
    assert request["plan_sha256"] == plan["canonical_sha256"]
    assert request["environment_snapshot_sha256"] == environment["environment_snapshot_sha256"]
    assert "requested_action_ids" in request
    assert "approved_action_ids" not in request

    request_as_approval = validate_bootstrap_approval(request, plan, environment)
    assert request_as_approval["valid"] is False
    assert "approval_status_not_approved" in request_as_approval["blockers"]


def test_bootstrap_approval_execute_verify_idempotency_and_rollback(tmp_path: Path) -> None:
    root = tmp_path / "ops-artifacts" / "agent-sync"
    plan = build_bootstrap_plan(root)
    environment = build_bootstrap_environment_snapshot(plan)
    approval = build_temp_bootstrap_approval(plan, environment, rollback=True)

    assert validate_bootstrap_approval(approval, plan, environment)["valid"] is True
    result = bootstrap_artifact_store(plan, approval, execute=True)
    assert result["status"] == "bootstrapped"
    assert verify_artifact_store(root)["bootstrapped"] is True

    second = bootstrap_artifact_store(plan, approval, execute=True)
    assert second["status"] == "noop_success"

    rollback = rollback_bootstrap(plan, approval, execute=True)
    assert rollback["status"] == "rolled_back"
    assert not root.exists()


def test_bootstrap_rollback_refuses_non_empty_store(tmp_path: Path) -> None:
    root = tmp_path / "ops-artifacts" / "agent-sync"
    plan = build_bootstrap_plan(root)
    environment = build_bootstrap_environment_snapshot(plan)
    approval = build_temp_bootstrap_approval(plan, environment, rollback=True)
    bootstrap_artifact_store(plan, approval, execute=True)
    (root / "runs" / "keep.txt").write_text("owned by another run\n", encoding="utf-8")
    before = _tree_listing(root)

    rollback = rollback_bootstrap(plan, approval, execute=True)
    assert rollback["status"] == "noop_not_safe_to_remove"
    assert rollback["mutation_count"] == 0
    assert rollback["removed_directories"] == []
    assert rollback["removed_files"] == []
    assert root.exists()
    assert _tree_listing(root) == before
    assert "not_empty" in " ".join(rollback["blocked"])


def test_bootstrap_rollback_refuses_unknown_file_with_zero_mutation(tmp_path: Path) -> None:
    root = tmp_path / "ops-artifacts" / "agent-sync"
    plan = build_bootstrap_plan(root)
    environment = build_bootstrap_environment_snapshot(plan)
    approval = build_temp_bootstrap_approval(plan, environment, rollback=True)
    bootstrap_artifact_store(plan, approval, execute=True)
    (root / "unknown.txt").write_text("foreign\n", encoding="utf-8")
    before = _tree_listing(root)

    rollback = rollback_bootstrap(plan, approval, execute=True)

    assert rollback["status"] == "noop_not_safe_to_remove"
    assert rollback["mutation_count"] == 0
    assert rollback["removed_directories"] == []
    assert rollback["removed_files"] == []
    assert _tree_listing(root) == before
    assert "unknown_path" in " ".join(rollback["blocked"])


def test_bootstrap_rollback_cleans_empty_partial_bootstrap(tmp_path: Path) -> None:
    root = tmp_path / "ops-artifacts" / "agent-sync"
    plan = build_bootstrap_plan(root)
    environment = build_bootstrap_environment_snapshot(plan)
    approval = build_temp_bootstrap_approval(plan, environment, rollback=True)
    for action in plan["directory_actions"]:
        path = Path(action["path"])
        path.mkdir(mode=int(action["mode"], 8))

    rollback = rollback_bootstrap(plan, approval, execute=True)

    assert rollback["status"] == "rolled_back"
    assert rollback["mutation_count"] == len(plan["directory_actions"])
    assert not root.exists()


def test_bootstrap_rollback_repeated_after_full_rollback_is_noop(tmp_path: Path) -> None:
    root = tmp_path / "ops-artifacts" / "agent-sync"
    plan = build_bootstrap_plan(root)
    environment = build_bootstrap_environment_snapshot(plan)
    approval = build_temp_bootstrap_approval(plan, environment, rollback=True)
    bootstrap_artifact_store(plan, approval, execute=True)
    assert rollback_bootstrap(plan, approval, execute=True)["status"] == "rolled_back"

    second = rollback_bootstrap(plan, approval, execute=True)

    assert second["status"] == "noop_already_rolled_back"
    assert second["mutation_count"] == 0


def test_bootstrap_rollback_refuses_foreign_metadata_with_zero_mutation(tmp_path: Path) -> None:
    root = tmp_path / "ops-artifacts" / "agent-sync"
    plan = build_bootstrap_plan(root)
    environment = build_bootstrap_environment_snapshot(plan)
    approval = build_temp_bootstrap_approval(plan, environment, rollback=True)
    bootstrap_artifact_store(plan, approval, execute=True)
    metadata_path = root / "STORE_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["bootstrap_run_id"] = "bootstrap-run_foreign"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    before = _tree_listing(root)

    rollback = rollback_bootstrap(plan, approval, execute=True)

    assert rollback["status"] == "noop_not_safe_to_remove"
    assert rollback["mutation_count"] == 0
    assert _tree_listing(root) == before
    assert "foreign_metadata_run" in rollback["blocked"]


def test_bootstrap_rejects_existing_regular_file(tmp_path: Path) -> None:
    root = tmp_path / "ops-artifacts" / "agent-sync"
    root.parent.mkdir(parents=True)
    root.write_text("not a directory\n", encoding="utf-8")
    plan = build_bootstrap_plan(root)
    environment = build_bootstrap_environment_snapshot(plan)
    approval = build_temp_bootstrap_approval(plan, environment, rollback=True)

    with pytest.raises(SyncPlannerError) as exc:
        bootstrap_artifact_store(plan, approval, execute=True)
    assert exc.value.exit_code == 7
    assert exc.value.reason == "bootstrap_existing_path_not_directory"


def test_p2s_plan_is_blocked_until_artifact_store_bootstrapped(tmp_path: Path) -> None:
    missing_store = tmp_path / "missing-store"
    plan = build_p2s_plan(artifact_store_root=missing_store)

    assert plan["execution_status"] == "blocked_artifact_store_not_ready"
    assert "artifact_store_not_bootstrapped" in plan["global_blockers"]
    assert plan["approval_requirements"]["stage_approved"] is False

    bootstrap = build_bootstrap_plan(missing_store)
    environment = build_bootstrap_environment_snapshot(bootstrap)
    approval = build_temp_bootstrap_approval(bootstrap, environment)
    bootstrap_artifact_store(bootstrap, approval, execute=True)

    ready_plan = build_p2s_plan(artifact_store_root=missing_store)
    assert ready_plan["execution_status"] == "stage_ready"
    assert ready_plan["approval_requirements"]["stage_approved"] is True


def test_cli_bootstrap_commands_and_stage_guard(tmp_path: Path) -> None:
    plan_path = tmp_path / "bootstrap_plan.json"
    output_path = tmp_path / "bootstrap_payload.json"
    result = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "react_agent.ops.agent_syncctl",
            "artifact-store",
            "bootstrap-plan",
            "--root",
            str(tmp_path / "ops-artifacts" / "agent-sync"),
            "--output",
            str(plan_path),
            "--json-output",
            str(output_path),
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["approval_request"]["status"] == "awaiting_machine_approval"

    result = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "react_agent.ops.agent_syncctl",
            "artifact-store",
            "bootstrap-validate",
            "--plan",
            str(plan_path),
            "--stdout-json",
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["valid"] is True

    approval_path = tmp_path / "approval.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    environment = build_bootstrap_environment_snapshot(plan)
    write_json(approval_path, build_temp_bootstrap_approval(plan, environment))
    result = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "react_agent.ops.agent_syncctl",
            "artifact-store",
            "bootstrap",
            "--plan",
            str(plan_path),
            "--approval",
            str(approval_path),
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "execute_required" in result.stderr


def test_permission_audit_is_read_only(tmp_path: Path) -> None:
    root = tmp_path / "ops-artifacts" / "agent-sync"
    audit = build_artifact_store_permission_audit(root)
    assert audit["root_exists"] is False
    assert audit["parent_exists"] is False
    assert not root.exists()
