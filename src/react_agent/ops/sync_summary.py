# ruff: noqa: D101, D103
"""Structured summary helpers for executable sync plans."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any


def p2s_summary_from_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Build the single authoritative P2S count summary for plan/results."""
    actions = [
        action
        for agent in plan.get("agents") or []
        if isinstance(agent, Mapping)
        for action in agent.get("actions") or []
        if isinstance(action, Mapping)
    ]
    operations = Counter(str(action.get("operation") or "") for action in actions)
    coverage = plan.get("coverage") or {}
    source_selection = plan.get("source_selection") or {}
    shared_noop_total = int(operations.get("noop_shared_transaction_member", 0))
    materialization_total = len(actions)
    return {
        "schema_version": "agent_sync_p2s_summary_v1",
        "recursive_inventory_total": int(coverage.get("recursive_inventory_file_count") or 0),
        "safe_source_total": materialization_total,
        "materialization_total": materialization_total,
        "physical_write_total": materialization_total - shared_noop_total,
        "shared_noop_total": shared_noop_total,
        "derivative_count": int(operations.get("preserve_sanitized_derivative", 0)),
        "metadata_count": int(operations.get("preserve_sandbox_metadata", 0)),
        "placeholder_count": int(operations.get("snapshot_semantic_placeholder", 0)),
        "excluded_count": int(coverage.get("explicitly_excluded_file_count") or 0),
        "runtime_asset_count": int((source_selection or {}).get("runtime_asset_count") or 0),
        "unresolved_count": int(coverage.get("unresolved_file_count") or 0),
        "coverage_ratio": float(coverage.get("coverage_ratio") or 0.0),
        "operation_counts": dict(sorted(operations.items())),
    }


def summary_consistency(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Compare embedded plan summary with the derived summary."""
    derived = p2s_summary_from_plan(plan)
    raw_summary = plan.get("summary")
    embedded: Mapping[str, Any] = raw_summary if isinstance(raw_summary, Mapping) else {}
    return {
        "schema_version": "agent_sync_summary_consistency_v1",
        "consistent": dict(embedded) == derived,
        "plan_summary": dict(embedded),
        "derived_summary": derived,
    }
