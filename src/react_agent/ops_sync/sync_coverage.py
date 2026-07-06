# ruff: noqa: D101, D103
"""Read-only P2S coverage and baseline parity helpers."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from react_agent.ops_sync.sync_contracts import read_json
from react_agent.ops_sync.sync_inventory import build_runtime_inventory
from react_agent.ops_sync.sync_plan import build_p2s_plan, load_plan

PREVIOUS_P2S_CLOSEOUT_DIR = Path("/tmp/lma-p2s-sensitive-closure-20260623T060342Z")
PREVIOUS_FILE_SYNC_MANIFEST = PREVIOUS_P2S_CLOSEOUT_DIR / "final_file_sync_manifest.json"
PREVIOUS_AGENT_SYNC_MATRIX = PREVIOUS_P2S_CLOSEOUT_DIR / "final_agent_sync_matrix.json"


def load_previous_file_sync_manifest(path: Path = PREVIOUS_FILE_SYNC_MANIFEST) -> list[dict[str, Any]]:
    value = read_json(path)
    if not isinstance(value, list):
        raise ValueError("previous_file_sync_manifest_not_list")
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _load_previous_agent_matrix(path: Path = PREVIOUS_AGENT_SYNC_MATRIX) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    value = read_json(path)
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _action_maps(plan: Mapping[str, Any]) -> tuple[dict[tuple[str, str], Mapping[str, Any]], dict[tuple[str, str], Mapping[str, Any]]]:
    direct: dict[tuple[str, str], Mapping[str, Any]] = {}
    shared: dict[tuple[str, str], Mapping[str, Any]] = {}
    for agent in plan.get("agents") or []:
        if not isinstance(agent, Mapping):
            continue
        agent_id = str(agent.get("agent_id") or "")
        for action in agent.get("actions") or []:
            if not isinstance(action, Mapping):
                continue
            rel = str(action.get("destination_relative_path") or action.get("source_path") or "")
            if rel:
                direct[(agent_id, rel)] = action
            stage_rel = str(action.get("stage_relative_path") or "")
            prefix = "market_composite/subagents/fund_manager_behavior/"
            if stage_rel.startswith(prefix):
                shared_rel = stage_rel[len(prefix) :]
                shared[("market_fund_manager_behavior", shared_rel)] = action
    return direct, shared


def _inventory_maps(inventory: Mapping[str, Any]) -> dict[str, dict[str, Mapping[str, Any]]]:
    result: dict[str, dict[str, Mapping[str, Any]]] = {}
    for agent in inventory.get("agents") or []:
        if not isinstance(agent, Mapping):
            continue
        agent_id = str(agent.get("agent_id") or "")
        files = {}
        root = (agent.get("roots") or {}).get("prod") or {}
        for record in root.get("files") or []:
            if isinstance(record, Mapping):
                files[str(record.get("relative_path") or "")] = record
        result[agent_id] = files
    return result


def _root_maps(inventory: Mapping[str, Any], root_role: str) -> dict[str, dict[str, Mapping[str, Any]]]:
    result: dict[str, dict[str, Mapping[str, Any]]] = {}
    for agent in inventory.get("agents") or []:
        if not isinstance(agent, Mapping):
            continue
        agent_id = str(agent.get("agent_id") or "")
        files = {}
        root = (agent.get("roots") or {}).get(root_role) or {}
        for record in root.get("files") or []:
            if isinstance(record, Mapping):
                files[str(record.get("relative_path") or "")] = record
        result[agent_id] = files
    return result


def _disposition_for_action(action: Mapping[str, Any]) -> str:
    operation = str(action.get("operation") or "")
    if operation in {"copy_from_prod", "snapshot_semantic_placeholder"}:
        return "materialized_from_current_prod"
    if operation == "preserve_sanitized_derivative":
        return "preserved_sanitized_derivative"
    if operation == "preserve_sandbox_metadata":
        return "preserved_baseline_metadata"
    if operation == "noop_shared_transaction_member":
        return "shared_transaction_member"
    return "unresolved"


def _excluded_disposition(record: Mapping[str, Any] | None) -> tuple[str, str]:
    if record is None:
        return "removed_from_current_prod", "current_prod_record_missing"
    decision = str(record.get("include_decision") or "")
    sensitive = str(record.get("sensitive_classification") or "")
    large = str(record.get("large_asset_classification") or "")
    if decision == "excluded_backup_artifact":
        return "excluded_backup_artifact", "backup_runtime_noise"
    if decision == "large_asset_reference" or large != "not_large_asset":
        if large == "reference_only_binary_or_data":
            return "excluded_data_or_model", large
        return "excluded_large_asset", large
    if decision == "blocked_sensitive_source" or sensitive in {"blocked_env_file", "potential_secret_literal"}:
        return "blocked_sensitive_source", sensitive or decision
    if decision == "excluded_directory":
        return "excluded_runtime_noise", decision
    if not bool(record.get("include")):
        return "excluded_runtime_noise", decision or "excluded_non_source"
    return "unresolved", "included_record_without_action"


def build_baseline_parity_ledger(
    *,
    plan: Mapping[str, Any] | None = None,
    inventory: Mapping[str, Any] | None = None,
    previous_manifest: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    plan = plan or build_p2s_plan()
    inventory = inventory or build_runtime_inventory(include_files=True)
    previous_manifest = previous_manifest or load_previous_file_sync_manifest()
    direct, shared = _action_maps(plan)
    prod_files = _inventory_maps(inventory)
    active_files = _root_maps(inventory, "active_sandbox")
    baseline_files = _root_maps(inventory, "baseline")
    rows: list[dict[str, Any]] = []
    for entry in previous_manifest:
        agent_id = str(entry.get("agent_id") or "")
        rel = str(entry.get("relative_path") or "")
        action = direct.get((agent_id, rel))
        shared_action = shared.get((agent_id, rel))
        prod_record = prod_files.get(agent_id, {}).get(rel)
        disposition = "unresolved"
        reason = "no_terminal_mapping"
        plan_action_id = ""
        plan_operation = ""
        if action is not None:
            disposition = _disposition_for_action(action)
            reason = "matched_direct_plan_action"
            plan_action_id = str(action.get("action_id") or "")
            plan_operation = str(action.get("operation") or "")
        elif shared_action is not None:
            disposition = "shared_transaction_materialized_elsewhere"
            reason = "matched_shared_transaction_action"
            plan_action_id = str(shared_action.get("action_id") or "")
            plan_operation = str(shared_action.get("operation") or "")
        elif prod_record is None and (rel in active_files.get(agent_id, {}) or rel in baseline_files.get(agent_id, {})):
            disposition = "stale_sandbox_only"
            reason = "current_prod_missing_but_baseline_or_active_has_file"
        else:
            excluded, excluded_reason = _excluded_disposition(prod_record)
            if excluded != "unresolved":
                disposition = excluded
                reason = excluded_reason
            else:
                disposition = "removed_from_current_prod"
                reason = "missing_from_current_prod_active_and_baseline"
        sensitive_blocked = disposition == "blocked_sensitive_source"
        rows.append(
            {
                "agent_id": agent_id,
                "historical_relative_path": rel,
                "historical_sha256": "" if sensitive_blocked else str(entry.get("prod_sha256") or entry.get("staged_sha256") or ""),
                "current_prod_relative_path": rel if prod_record is not None else "",
                "current_prod_sha256": "" if sensitive_blocked else str((prod_record or {}).get("sha256") or ""),
                "new_plan_action_id": plan_action_id,
                "plan_operation": plan_operation,
                "disposition": disposition,
                "reason": reason,
                "policy_rule": reason,
                "resolved": disposition != "unresolved",
            }
        )
    omitted = sum(
        len((row.get("validation") or {}).get("omitted_sensitive_unreachable_files") or [])
        for row in _load_previous_agent_matrix()
        if isinstance(row.get("validation"), Mapping)
    )
    counts = Counter(str(row["disposition"]) for row in rows)
    return {
        "schema_version": "previous_baseline_to_new_plan_parity_v1",
        "historical_sources": {
            "final_file_sync_manifest": str(PREVIOUS_FILE_SYNC_MANIFEST),
            "final_agent_sync_matrix": str(PREVIOUS_AGENT_SYNC_MATRIX),
        },
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "row_count": len(rows),
        "agent_count": len({row["agent_id"] for row in rows}),
        "declared_omitted_outside_manifest_count": omitted,
        "disposition_counts": dict(sorted(counts.items())),
        "unresolved_count": int(counts.get("unresolved", 0)),
        "coverage_ratio": 1.0 if not rows else (len(rows) - int(counts.get("unresolved", 0))) / len(rows),
        "rows": rows,
    }


def build_current_prod_coverage_ledger(
    *,
    plan: Mapping[str, Any] | None = None,
    inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    plan = plan or build_p2s_plan()
    inventory = inventory or build_runtime_inventory(include_files=True)
    direct, shared = _action_maps(plan)
    rows: list[dict[str, Any]] = []
    for agent in inventory.get("agents") or []:
        if not isinstance(agent, Mapping):
            continue
        agent_id = str(agent.get("agent_id") or "")
        root = (agent.get("roots") or {}).get("prod") or {}
        for record in root.get("files") or []:
            if not isinstance(record, Mapping):
                continue
            rel = str(record.get("relative_path") or "")
            action = direct.get((agent_id, rel))
            shared_action = shared.get((agent_id, rel))
            if action is not None:
                disposition = _disposition_for_action(action)
                plan_operation = str(action.get("operation") or "")
                plan_action_id = str(action.get("action_id") or "")
                blocker = ""
            elif shared_action is not None:
                disposition = "shared_transaction_materialized_elsewhere"
                plan_operation = str(shared_action.get("operation") or "")
                plan_action_id = str(shared_action.get("action_id") or "")
                blocker = ""
            else:
                disposition, blocker = _excluded_disposition(record)
                plan_operation = ""
                plan_action_id = ""
            safe_authority = bool(record.get("include")) or disposition in {
                "preserved_sanitized_derivative",
                "shared_transaction_materialized_elsewhere",
            }
            rows.append(
                {
                    "agent_id": agent_id,
                    "relative_path": rel,
                    "current_prod_include_decision": str(record.get("include_decision") or ""),
                    "current_prod_sensitive_classification": str(record.get("sensitive_classification") or ""),
                    "coverage_disposition": disposition,
                    "plan_operation": plan_operation,
                    "plan_action_id": plan_action_id,
                    "shared_transaction": shared_action is not None,
                    "safe_authority_file": safe_authority,
                    "blocker_code": blocker,
                    "resolved": disposition != "unresolved",
                }
            )
    counts = Counter(str(row["coverage_disposition"]) for row in rows)
    safe_rows = [row for row in rows if row["safe_authority_file"]]
    unresolved = int(counts.get("unresolved", 0))
    safe_unresolved = sum(1 for row in safe_rows if row["coverage_disposition"] == "unresolved")
    return {
        "schema_version": "current_prod_to_new_plan_coverage_v1",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "row_count": len(rows),
        "safe_source_file_count": len(safe_rows),
        "coverage_counts": dict(sorted(counts.items())),
        "unresolved_count": unresolved,
        "safe_source_unresolved_count": safe_unresolved,
        "coverage_ratio": 1.0 if not rows else (len(rows) - unresolved) / len(rows),
        "safe_source_coverage_ratio": 1.0 if not safe_rows else (len(safe_rows) - safe_unresolved) / len(safe_rows),
        "rows": rows,
    }


def validate_baseline_parity_ledger(ledger: Mapping[str, Any]) -> dict[str, Any]:
    unresolved = int(ledger.get("unresolved_count") or 0)
    return {
        "valid": unresolved == 0,
        "unresolved_count": unresolved,
        "row_count": int(ledger.get("row_count") or 0),
    }


def load_plan_and_build_ledgers(plan_path: Path) -> dict[str, Any]:
    plan = load_plan(plan_path)
    inventory = build_runtime_inventory(include_files=True)
    return {
        "historical_parity": build_baseline_parity_ledger(plan=plan, inventory=inventory),
        "current_prod_coverage": build_current_prod_coverage_ledger(plan=plan, inventory=inventory),
    }
