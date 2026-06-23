"""Tests for read-only sync plans and CLI behavior."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from react_agent.ops.sync_plan import (
    build_cycle_plan,
    build_experiment_template,
    build_p2s_plan,
    build_s2p_plan,
    validate_plan,
)


def test_p2s_plan_is_executable_contract_and_hash_valid() -> None:
    plan = build_p2s_plan()
    validation = validate_plan(plan, check_target_freshness=False)
    assert validation["valid"] is True
    assert plan["direction"] == "p2s"
    assert "read_only_plan_only" not in plan["global_preconditions"]
    assert plan["execution_contract"]["schema_version"] == "agent_sync_p2s_execution_contract_v1"
    assert plan["rollback_plan"]["executable"] is True
    assert plan["approval_requirements"]["stage_approved"] is True
    assert plan["approval_requirements"]["verify_approved"] is True
    assert plan["approval_requirements"]["activate_approved"] is False
    assert plan["approval_requirements"]["rollback_approved"] is False
    assert plan["agents"]
    assert plan["canonical_sha256"] == validation["canonical_sha256"]
    assert all(agent["process_actions"] == [] for agent in plan["agents"])


def test_active_baseline_is_rejected_as_s2p_experiment() -> None:
    manifest = build_experiment_template(output_root="/sdb/dlut/sandbox/r8-13a/services/prod")
    manifest["agents"] = [{"agent_id": "value_ml_valuation"}]
    plan = build_s2p_plan(manifest)
    assert "blocked_active_baseline_not_experiment" in plan["global_blockers"]


def test_cycle_plan_defers_rebase() -> None:
    manifest = build_experiment_template(output_root="/tmp/sync-ops-test-experiment")
    manifest["agents"] = [{"agent_id": "value_ml_valuation"}]
    plan = build_s2p_plan(manifest)
    cycle = build_cycle_plan(plan)
    assert cycle["direction"] == "publish_and_rebase"
    assert cycle["deferred_rebase"]["p2s_plan_generation"] == "deferred_until_all_started_s2p_transactions_settled"
    assert all(not agent["actions"] for agent in cycle["agents"])


def test_cli_unsupported_write_command_returns_2() -> None:
    result = subprocess.run(
        [".venv/bin/python", "scripts/ops/agent_syncctl.py", "s2p", "apply"],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "command_not_available_before_sync_ops_2" in result.stderr


def test_cli_json_output_path_is_explicit(tmp_path: Path) -> None:
    output = tmp_path / "status.json"
    result = subprocess.run(
        [".venv/bin/python", "-m", "react_agent.ops.agent_syncctl", "status", "--json-output", str(output)],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["registry"]["formal_external_agent_count"] == 26


def test_cli_p2s_coverage_uses_explicit_plan_file(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    coverage_path = tmp_path / "coverage.json"
    plan = build_p2s_plan()
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "react_agent.ops.agent_syncctl",
            "p2s",
            "coverage",
            "--plan",
            str(plan_path),
            "--json-output",
            str(coverage_path),
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert payload["historical_parity"]["unresolved_count"] == 0
    assert payload["current_prod_coverage"]["safe_source_coverage_ratio"] == 1.0


def test_cli_artifact_store_preflight_and_execution_explain(tmp_path: Path) -> None:
    preflight_path = tmp_path / "preflight.json"
    result = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "react_agent.ops.agent_syncctl",
            "artifact-store",
            "preflight",
            "--root",
            str(tmp_path / "missing-store"),
            "--json-output",
            str(preflight_path),
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 3
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    assert preflight["creation_required"] is True

    plan_path = tmp_path / "plan.json"
    explain_path = tmp_path / "explain.json"
    plan = build_p2s_plan()
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "react_agent.ops.agent_syncctl",
            "plan",
            "explain-execution",
            "--plan",
            str(plan_path),
            "--json-output",
            str(explain_path),
        ],
        cwd="/sdb/dlut/dev/langgraph-my-agent",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    explain = json.loads(explain_path.read_text(encoding="utf-8"))
    assert explain["writer_contract_version"] == plan["execution_contract"]["writer_contract_version"]
    assert explain["required_permissions"]["activate_approved"] is False
