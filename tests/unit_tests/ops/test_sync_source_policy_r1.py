"""Regression tests for SYNC-OPS-2A-R1 source selection policy."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from react_agent.ops.agent_syncctl import _plan_source_audit
from react_agent.ops.sync_contracts import file_sha256, stable_id, write_json
from react_agent.ops.sync_inventory import inventory_root
from react_agent.ops.sync_p2s import run_full_scale_p2s_rehearsal
from react_agent.ops.sync_plan import (
    P2S_TOOL_VERSION,
    build_p2s_plan,
    executable_plan_contract,
    executable_rollback_contract,
    stage_projection_digest_for_actions,
    validate_plan,
)
from react_agent.ops.sync_registry import load_static_registry
from react_agent.ops.sync_security import should_include_source_file
from react_agent.ops.sync_summary import p2s_summary_from_plan

OLD_PLAN_2A = Path("/tmp/lma-sync-ops-2a-p2s-writer-20260623T125001Z/new_current_p2s_plan.json")


def _current_actions(plan: dict[str, object]) -> list[dict[str, object]]:
    return [
        action
        for agent in plan.get("agents", [])
        if isinstance(agent, dict)
        for action in agent.get("actions", [])
        if isinstance(action, dict)
    ]


def test_old_2a_plan_has_source_policy_defects_when_artifact_available() -> None:
    if not OLD_PLAN_2A.exists():
        return
    old_plan = json.loads(OLD_PLAN_2A.read_text(encoding="utf-8"))
    audit = _plan_source_audit(old_plan)
    assert audit["not_scanned_copy_count"] > 0
    paths = {
        str(action.get("stage_relative_path") or "")
        for action in _current_actions(old_plan)
        if action.get("operation") == "copy_from_prod"
    }
    assert any(".claude/settings.local.json" in path for path in paths)
    assert any(".idea/.gitignore" in path for path in paths)
    assert any("/artifacts/" in path or "/results/" in path for path in paths)


def test_source_policy_excludes_hidden_backup_generated_and_runtime_noise(tmp_path: Path) -> None:
    samples = {
        ".claude/settings.local.json": "editor_local_metadata",
        ".idea/.gitignore": "editor_local_metadata",
        ".opt_bak_20260604_022333/main.py": "backup_artifact",
        ".snapshot_bak_1780465286/main.py": "backup_artifact",
        "crash_risk_model/_backup_49/artifacts/report.json": "backup_artifact",
        "part2_baselineExp/results/result.json": "experiment_result",
        "artifacts/report.json": "generated_artifact",
        "reports/report.json": "generated_artifact",
        "run.log": "runtime_noise",
        "service.pid": "runtime_noise",
        "artifacts/.gitkeep": "generated_artifact",
    }
    for relative, category in samples.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        safety = should_include_source_file(tmp_path, path)
        assert safety["include"] is False
        assert safety["source_category"] == category


def test_source_policy_treats_known_lockfiles_as_package_metadata(tmp_path: Path) -> None:
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("# lock metadata\n", encoding="utf-8")
    safety = should_include_source_file(tmp_path, lockfile)
    assert safety["include"] is True
    assert safety["source_category"] == "package_metadata"
    assert safety["source_category_reason"] == "package_lockfile_metadata"

    arbitrary_lock = tmp_path / "service.lock"
    arbitrary_lock.write_text("not a package-manager lockfile\n", encoding="utf-8")
    arbitrary_safety = should_include_source_file(tmp_path, arbitrary_lock)
    assert arbitrary_safety["include"] is False
    assert arbitrary_safety["source_category"] == "unknown_blocked"


def test_extensionless_text_is_scanned_and_classified(tmp_path: Path) -> None:
    text = tmp_path / "指令"
    text.write_text("safe text only\n", encoding="utf-8")
    safety = should_include_source_file(tmp_path, text)
    assert safety["include"] is True
    assert safety["source_category"] == "documentation"
    assert safety["sensitive_classification"] == "none"

    binary = tmp_path / "opaque"
    binary.write_bytes(b"\x00\x01\x02")
    binary_safety = should_include_source_file(tmp_path, binary)
    assert binary_safety["include"] is False
    assert binary_safety["source_category"] == "unknown_blocked"


def test_inventory_prunes_generated_dirs(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "agent.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "artifacts").mkdir()
    (tmp_path / "pkg" / "artifacts" / "report.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "quant_output").mkdir()
    (tmp_path / "quant_output" / "out.json").write_text("{}\n", encoding="utf-8")
    inventory = inventory_root("agent", tmp_path, root_role="test")
    paths = {record["relative_path"] for record in inventory["files"]}
    assert "pkg/agent.py" in paths
    assert "pkg/artifacts/report.json" not in paths
    assert "quant_output/out.json" not in paths


def test_current_plan_has_no_not_scanned_or_non_materializable_copy_actions() -> None:
    plan = build_p2s_plan()
    validation = validate_plan(plan, check_target_freshness=False)
    assert validation["valid"] is True
    audit = _plan_source_audit(plan)
    assert audit["not_scanned_copy_count"] == 0
    assert audit["non_materializable_copy_count"] == 0
    assert plan["source_selection"]["unknown_blocked_count"] == 0


def _small_rehearsal_plan(tmp_path: Path) -> dict[str, object]:
    prod = tmp_path / "prod"
    active = tmp_path / "active"
    pointer = tmp_path / "PROD_BASELINE_POINTER.json"
    prod.mkdir(parents=True)
    active.mkdir(parents=True)
    pointer.write_text("{}\n", encoding="utf-8")
    source = prod / "agent.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    action = {
        "action_id": stable_id("mat", "copy", "agent.py"),
        "operation": "copy_from_prod",
        "agent_id": "financial_data_service",
        "affected_agent_ids": ["financial_data_service"],
        "transaction_root": str(prod),
        "source_path": "agent.py",
        "source_absolute_path": str(source),
        "source_sha256": file_sha256(source),
        "source_mode": "0o644",
        "source_file_type": "regular",
        "source_executable": False,
        "source_symlink_target": "",
        "destination_relative_path": "agent.py",
        "stage_relative_path": "financial_data_service/agent.py",
        "sensitive_classification": "none",
        "large_asset_classification": "not_large_asset",
        "source_category": "source_code",
        "source_category_reason": "source_extension",
    }
    digest = stage_projection_digest_for_actions([action])
    agents: list[dict[str, object]] = []
    transactions: list[dict[str, object]] = []
    for registry_agent in load_static_registry()["agents"]:
        agent_id = str(registry_agent["agent_id"])
        actions = [action] if agent_id == "financial_data_service" else []
        projection = stage_projection_digest_for_actions(actions)
        txn_id = f"txn-r1-{agent_id}"
        agents.append(
            {
                "agent_id": agent_id,
                "transaction_id": txn_id,
                "source_root": "prod",
                "target_root": str(tmp_path / "stage" / agent_id),
                "target_before_tree_sha256": "active",
                "active_tree_sha256": "active",
                "prod_tree_sha256": "prod",
                "projection_digest": projection,
                "disposition": "stage_from_prod" if actions else "already_equal_but_rematerialized",
                "actions": actions,
                "blocked_actions": [],
                "rollback": {
                    "transaction_rollback_id": stable_id("rollback", txn_id),
                    "contract_ref": "execution_contract.rollback",
                },
                "expected_status": "stage_ready",
            }
        )
        transactions.append(
            {
                "transaction_id": txn_id,
                "agent_id": agent_id,
                "disposition": "stage_from_prod" if actions else "already_equal_but_rematerialized",
                "actions": actions,
                "blocked_actions": [],
            }
        )
    plan = {
        "schema_version": "agent_sync_plan_v1",
        "tool_version": P2S_TOOL_VERSION,
        "test_only_temp_roots": True,
        "plan_id": "p2s-r1-test",
        "direction": "p2s",
        "created_at": "2026-06-23T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "registry_sha256": "r" * 64,
        "policy_sha256": "p" * 64,
        "catalog_sha256": "c" * 64,
        "baseline": {"active_baseline_id": "old", "active_path": str(active), "versioned_baseline_path": str(tmp_path / "old-versioned")},
        "experiment": {},
        "target_snapshot": {
            "active_sandbox_path": str(active),
            "active_sandbox_pointer_sha256": file_sha256(pointer),
            "active_baseline_tree_sha256": "active",
            "versioned_baseline_tree_sha256": "old",
        },
        "observed_diff": {"summary": {}},
        "stage_materialization": {
            "baseline_id": "temp-r1",
            "stage_root": str(tmp_path / "stage"),
            "expected_stage_root_state": "missing",
            "transactions": transactions,
            "action_counts": {"copy_from_prod": 1},
            "expected_stage_projection_digest": digest,
        },
        "activation": {
            "old_active_sandbox_archive_path": str(tmp_path / "archive"),
            "new_versioned_baseline_path": str(tmp_path / "stage"),
            "pointer_candidate": {"path": str(pointer), "active_baseline_id": "temp-r1", "active_path": str(active), "versioned_baseline_path": str(tmp_path / "stage")},
            "preconditions": {"active_pointer_sha256": file_sha256(pointer), "active_baseline_tree_sha256": "active", "old_active_path": str(active), "expected_stage_root_state": "missing"},
            "rollback": {"restore_old_active_path": str(active)},
        },
        "artifact_store_initialization": {
            "required": True,
            "root": str(tmp_path / "artifact-store"),
            "parent": str(tmp_path),
            "expected_root_state": "missing",
            "recommended_mode": "inherit_parent_policy_or_0o770_if_parent_policy_absent",
            "owner_strategy": "inherit_operator_or_parent_policy",
            "group_strategy": "inherit_parent_or_recorded_ops_group",
            "create_parents": False,
            "approval_required": True,
            "rollback": "remove_only_if_empty_and_created_by_this_run",
        },
        "execution_contract": executable_plan_contract(
            plan_id="p2s-r1-test",
            stage_root=tmp_path / "stage",
            active_path=str(active),
            preflight={"root": str(tmp_path / "artifact-store"), "parent": str(tmp_path), "root_exists": False, "parent_exists": True},
        ),
        "coverage": {"unresolved_file_count": 0, "coverage_ratio": 1.0},
        "source_selection": {"not_scanned_copy_count": 0, "unknown_blocked_count": 0, "sensitive_copy_count": 0},
        "agents": agents,
        "global_preconditions": ["plan_schema_valid", "canonical_hash_valid", "exact_machine_approval_required", "stage_root_missing"],
        "global_blockers": [],
        "approval_requirements": {
            "stage_approved": True,
            "verify_approved": True,
            "artifact_store_initialize_approved": True,
            "activate_approved": False,
            "rollback_approved": False,
        },
        "rollback_plan": executable_rollback_contract("p2s-r1-test"),
        "canonical_sha256": "",
    }
    from react_agent.ops.sync_contracts import canonical_sha256

    plan["summary"] = p2s_summary_from_plan(plan)
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def test_temp_rehearsal_rejects_real_roots_and_runs_on_tmp(tmp_path: Path) -> None:
    plan = _small_rehearsal_plan(tmp_path)
    result = run_full_scale_p2s_rehearsal(plan, tmp_path / "rehearsal")
    assert result["stage"]["digest_match"] is True
    assert result["verify"]["valid"] is True
    assert result["activate"]["post_switch_validated"] is True
    assert result["rollback"]["archive_restored"] is True
    assert result["hardlink_count"] == 0


def test_cli_source_audit_and_rehearse_use_temp_roots(tmp_path: Path) -> None:
    plan = _small_rehearsal_plan(tmp_path / "fixture")
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    audit = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "react_agent.ops.agent_syncctl",
            "p2s",
            "source-audit",
            "--plan",
            str(plan_path),
            "--stdout-json",
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert audit.returncode == 0
    assert "not_scanned_copy_count" in audit.stdout

    rehearse = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "react_agent.ops.agent_syncctl",
            "p2s",
            "rehearse",
            "--plan",
            str(plan_path),
            "--temp-root",
            str(tmp_path / "cli-rehearsal"),
            "--stdout-json",
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert rehearse.returncode == 0
    assert "hardlink_count" in rehearse.stdout
