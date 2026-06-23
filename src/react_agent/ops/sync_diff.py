# ruff: noqa: D101, D103
"""B/S/P/D diff classification for read-only sync planning."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from react_agent.ops.sync_inventory import FileInventoryRecord


def _included_map(root_inventory: Mapping[str, Any]) -> dict[str, FileInventoryRecord]:
    result: dict[str, FileInventoryRecord] = {}
    for record in root_inventory.get("files") or []:
        if not isinstance(record, Mapping) or not record.get("include"):
            continue
        result[str(record["relative_path"])] = record  # type: ignore[assignment]
    return result


def _sha(record: FileInventoryRecord | None) -> str:
    if record is None:
        return ""
    return str(record.get("sha256") or "")


def classify_file_delta(
    *,
    baseline: FileInventoryRecord | None,
    sandbox: FileInventoryRecord | None,
    prod: FileInventoryRecord | None,
    owner: FileInventoryRecord | None = None,
    sanitized_derivative: bool = False,
    semantic_placeholder: bool = False,
) -> str:
    if semantic_placeholder:
        return "semantic_placeholder"
    if sanitized_derivative and sandbox is not None and prod is not None and _sha(sandbox) != _sha(prod):
        return "sanitized_derivative"
    if baseline is None and sandbox is not None:
        return "added_in_sandbox"
    if baseline is None and prod is not None:
        return "added_in_prod"
    if baseline is None:
        return "unresolved_authority"
    b = _sha(baseline)
    s = _sha(sandbox)
    p = _sha(prod)
    d = _sha(owner)
    if sandbox is None and prod is not None and p == b:
        return "sandbox_deleted_prod_unchanged"
    if prod is None and sandbox is not None and s != b:
        return "prod_deleted_sandbox_changed"
    if s == b and p == b and (not d or d == b):
        return "unchanged_all"
    if s != b and p == b:
        return "changed_in_sandbox_only"
    if s == b and p != b:
        return "changed_in_prod_only"
    if d and s == b and p == b and d != b:
        return "changed_in_owner_only"
    if s != b and p != b and s == p:
        return "sandbox_and_prod_same_change"
    if s != b and p != b and s != p:
        return "sandbox_and_prod_diverged"
    if d and p == d and p != b:
        return "prod_and_owner_same"
    return "unresolved_authority"


def diff_agent_roots(agent_inventory: Mapping[str, Any]) -> dict[str, Any]:
    roots = agent_inventory.get("roots") or {}
    baseline_root = roots.get("baseline") or {}
    sandbox_root = roots.get("active_sandbox") or {}
    prod_root = roots.get("prod") or {}
    baseline = _included_map(baseline_root)
    sandbox = _included_map(sandbox_root)
    prod = _included_map(prod_root)
    keys = sorted(set(baseline) | set(sandbox) | set(prod))
    rows: list[dict[str, Any]] = []
    for key in keys:
        classification = classify_file_delta(
            baseline=baseline.get(key),
            sandbox=sandbox.get(key),
            prod=prod.get(key),
            sanitized_derivative=bool(agent_inventory.get("sanitized_derivative")),
            semantic_placeholder=bool(agent_inventory.get("semantic_placeholder")),
        )
        rows.append(
            {
                "agent_id": agent_inventory["agent_id"],
                "unit_kind": "source_file",
                "relative_path": key,
                "classification": classification,
                "baseline_sha256": _sha(baseline.get(key)),
                "sandbox_sha256": _sha(sandbox.get(key)),
                "prod_sha256": _sha(prod.get(key)),
            }
        )
    return {
        "agent_id": agent_inventory["agent_id"],
        "rows": rows,
        "counts": {name: sum(1 for row in rows if row["classification"] == name) for name in sorted({row["classification"] for row in rows})},
    }


def diff_inventory(inventory: Mapping[str, Any]) -> dict[str, Any]:
    agent_diffs = [diff_agent_roots(agent) for agent in inventory.get("agents") or []]
    totals: dict[str, int] = {}
    for agent in agent_diffs:
        for name, count in agent["counts"].items():
            totals[name] = totals.get(name, 0) + int(count)
    return {
        "schema_version": "agent_sync_bspd_diff_v1",
        "registry_sha256": inventory.get("registry_sha256", ""),
        "policy_sha256": inventory.get("policy_sha256", ""),
        "agent_count": len(agent_diffs),
        "agents": agent_diffs,
        "totals": totals,
    }

