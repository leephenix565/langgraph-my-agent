"""Tests for SYNC-OPS-1R2 coverage and temp stage reconstruction."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from react_agent.ops.sync_coverage import (
    build_baseline_parity_ledger,
    build_current_prod_coverage_ledger,
)
from react_agent.ops.sync_materialize import reconstruct_temp_stage
from react_agent.ops.sync_plan import build_p2s_plan, validate_plan


@lru_cache(maxsize=1)
def _plan() -> dict[str, object]:
    return build_p2s_plan()


def test_current_environment_parity_and_coverage_are_fully_resolved() -> None:
    plan = _plan()
    assert validate_plan(plan, check_target_freshness=False)["valid"] is True
    historical = build_baseline_parity_ledger(plan=plan)
    current = build_current_prod_coverage_ledger(plan=plan)
    assert historical["row_count"] == 1625
    assert historical["unresolved_count"] == 0
    assert current["unresolved_count"] == 0
    assert current["safe_source_unresolved_count"] == 0
    assert current["safe_source_coverage_ratio"] == 1.0
    assert current["coverage_counts"]["shared_transaction_materialized_elsewhere"] > 0


def test_temp_stage_reconstruction_matches_projection_digest(tmp_path: Path) -> None:
    plan = _plan()
    result = reconstruct_temp_stage(plan, tmp_path / "stage")
    assert result["digest_match"] is True
    assert result["structural_pass"] is True
    assert result["duplicate_destination_count"] == 0
    assert result["secret_scan"]["pass"] is True
