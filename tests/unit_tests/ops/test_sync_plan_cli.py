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


def test_p2s_plan_is_read_only_and_hash_valid() -> None:
    plan = build_p2s_plan()
    validation = validate_plan(plan, check_target_freshness=False)
    assert validation["valid"] is True
    assert plan["direction"] == "p2s"
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
    assert "command_not_available_in_sync_ops_1r" in result.stderr


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
