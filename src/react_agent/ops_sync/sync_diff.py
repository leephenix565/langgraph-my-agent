# ruff: noqa: D101, D103
"""B/S/P/D diff classification for read-only sync planning."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from react_agent.ops_sync.sync_inventory import FileInventoryRecord


def _included_map(root_inventory: Mapping[str, Any]) -> dict[str, FileInventoryRecord]:
    result: dict[str, FileInventoryRecord] = {}
    for record in root_inventory.get("files") or []:
        if not isinstance(record, Mapping) or not record.get("include"):
            continue
        result[str(record["relative_path"])] = record  # type: ignore[assignment]
    return result


def _record_map(root_inventory: Mapping[str, Any]) -> dict[str, FileInventoryRecord]:
    result: dict[str, FileInventoryRecord] = {}
    for record in root_inventory.get("files") or []:
        if not isinstance(record, Mapping):
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
    if prod is not None and not prod.get("include", True):
        decision = str(prod.get("include_decision") or prod.get("classification") or "")
        if decision == "excluded_backup_artifact" or prod.get("classification") == "excluded_backup_artifact":
            return "backup_runtime_noise"
        if prod.get("classification") == "large_asset_reference":
            return "binary_or_large_asset"
        if prod.get("classification") == "blocked_sensitive_source":
            if sanitized_derivative and sandbox is not None:
                return "sanitized_derivative"
            return "prod_blocked_sensitive_source"
        return "prod_non_source_runtime_artifact"
    if sandbox is not None and not sandbox.get("include", True):
        if str(sandbox.get("relative_path") or "") == "SANDBOX_SECRET_REQUIREMENTS.md":
            return "sandbox_generated_metadata"
        return "stale_sandbox_file"
    if sanitized_derivative and sandbox is not None and prod is not None and _sha(sandbox) != _sha(prod):
        return "sanitized_derivative"
    metadata_candidate = sandbox or baseline or prod
    if (
        metadata_candidate is not None
        and str(metadata_candidate.get("relative_path") or "") == "SANDBOX_SECRET_REQUIREMENTS.md"
        and prod is None
    ):
        return "sandbox_generated_metadata"
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
    all_baseline = _record_map(baseline_root)
    all_sandbox = _record_map(sandbox_root)
    all_prod = _record_map(prod_root)
    keys = sorted(set(all_baseline) | set(all_sandbox) | set(all_prod))
    rows: list[dict[str, Any]] = []
    for key in keys:
        classification = classify_file_delta(
            baseline=all_baseline.get(key),
            sandbox=all_sandbox.get(key),
            prod=all_prod.get(key),
            sanitized_derivative=bool(agent_inventory.get("sanitized_derivative")),
            semantic_placeholder=bool(agent_inventory.get("semantic_placeholder")),
        )
        baseline_record = all_baseline.get(key)
        sandbox_record = all_sandbox.get(key)
        prod_record = all_prod.get(key)
        rows.append(
            {
                "agent_id": agent_inventory["agent_id"],
                "unit_kind": "source_file",
                "relative_path": key,
                "classification": classification,
                "baseline_sha256": _sha(baseline_record if baseline_record and baseline_record.get("include") else None),
                "sandbox_sha256": _sha(sandbox_record if sandbox_record and sandbox_record.get("include") else None),
                "prod_sha256": _sha(prod_record if prod_record and prod_record.get("include") else None),
                "baseline_include": bool(baseline_record.get("include")) if baseline_record else False,
                "sandbox_include": bool(sandbox_record.get("include")) if sandbox_record else False,
                "prod_include": bool(prod_record.get("include")) if prod_record else False,
                "baseline_classification": str(baseline_record.get("classification") or "") if baseline_record else "missing",
                "sandbox_classification": str(sandbox_record.get("classification") or "") if sandbox_record else "missing",
                "prod_classification": str(prod_record.get("classification") or "") if prod_record else "missing",
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
