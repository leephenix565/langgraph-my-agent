"""Repo-external temp integration tests for the read-only sync planner."""

from __future__ import annotations

from pathlib import Path

from react_agent.ops.sync_diff import diff_inventory
from react_agent.ops.sync_inventory import inventory_root


def test_bspd_diff_with_temp_roots_does_not_write_targets(tmp_path: Path) -> None:
    baseline = tmp_path / "B" / "agent"
    sandbox = tmp_path / "S" / "agent"
    prod = tmp_path / "P" / "agent"
    owner = tmp_path / "D" / "agent"
    for root in (baseline, sandbox, prod, owner):
        root.mkdir(parents=True)
    (baseline / "agent.py").write_text("x=1\n", encoding="utf-8")
    (sandbox / "agent.py").write_text("x=2\n", encoding="utf-8")
    (prod / "agent.py").write_text("x=1\n", encoding="utf-8")
    (owner / "agent.py").write_text("x=3\n", encoding="utf-8")
    inventory = {
        "agents": [
            {
                "agent_id": "value_ml_valuation",
                "roots": {
                    "baseline": inventory_root("value_ml_valuation", baseline, root_role="baseline"),
                    "active_sandbox": inventory_root("value_ml_valuation", sandbox, root_role="experiment"),
                    "prod": inventory_root("value_ml_valuation", prod, root_role="prod"),
                    "owner": inventory_root("value_ml_valuation", owner, root_role="owner"),
                },
                "sanitized_derivative": False,
                "semantic_placeholder": False,
            }
        ],
        "registry_sha256": "test",
        "policy_sha256": "test",
    }
    diff = diff_inventory(inventory)
    assert diff["totals"]["changed_in_sandbox_only"] == 1
    assert (prod / "agent.py").read_text(encoding="utf-8") == "x=1\n"

