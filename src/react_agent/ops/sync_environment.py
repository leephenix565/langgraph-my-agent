# ruff: noqa: D101, D103
"""Environment snapshot binding for sync writer phases."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from react_agent.ops.sync_contracts import canonical_sha256


def _device_id(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    probe = path.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        stat_result = probe.stat()
    except OSError:
        return "unavailable"
    return str(stat_result.st_dev)


def build_environment_snapshot(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Build a stable, non-sensitive environment snapshot for a plan."""
    target_snapshot = plan.get("target_snapshot") or {}
    stage = plan.get("stage_materialization") or {}
    activation = plan.get("activation") or {}
    execution_contract = plan.get("execution_contract") or {}
    artifact_store = execution_contract.get("artifact_store") if isinstance(execution_contract, Mapping) else {}
    artifact_initialization = plan.get("artifact_store_initialization") or {}
    raw_preconditions = activation.get("preconditions") if isinstance(activation, Mapping) else {}
    preconditions: Mapping[str, Any] = raw_preconditions if isinstance(raw_preconditions, Mapping) else {}
    transaction_digests = [
        {
            "agent_id": str(agent.get("agent_id") or ""),
            "transaction_id": str(agent.get("transaction_id") or ""),
            "prod_tree_sha256": str(agent.get("prod_tree_sha256") or ""),
            "active_tree_sha256": str(agent.get("active_tree_sha256") or agent.get("target_before_tree_sha256") or ""),
            "projection_digest": str(agent.get("projection_digest") or ""),
        }
        for agent in plan.get("agents") or []
        if isinstance(agent, Mapping)
    ]
    stage_root = str(stage.get("stage_root") or "")
    active_path = str(target_snapshot.get("active_sandbox_path") or preconditions.get("old_active_path") or "")
    snapshot: dict[str, Any] = {
        "schema_version": "agent_sync_environment_snapshot_v1",
        "registry_sha256": str(plan.get("registry_sha256") or ""),
        "policy_sha256": str(plan.get("policy_sha256") or ""),
        "catalog_sha256": str(plan.get("catalog_sha256") or ""),
        "active_pointer_sha256": str(target_snapshot.get("active_sandbox_pointer_sha256") or preconditions.get("active_pointer_sha256") or ""),
        "active_baseline_tree_sha256": str(target_snapshot.get("active_baseline_tree_sha256") or preconditions.get("active_baseline_tree_sha256") or ""),
        "current_prod_per_transaction_digests": sorted(transaction_digests, key=lambda item: item["transaction_id"]),
        "stage_path": stage_root,
        "stage_path_expected_state": str(stage.get("expected_stage_root_state") or preconditions.get("expected_stage_root_state") or ""),
        "allowed_root_namespace": "/sdb/dlut/sandbox/prod-baselines" if stage_root.startswith("/sdb/dlut/") else "/tmp",
        "filesystem_device_ids": {
            "stage_parent": _device_id(stage_root),
            "active_parent": _device_id(active_path),
        },
        "tool_version": str(plan.get("tool_version") or ""),
        "writer_contract_version": str((execution_contract or {}).get("writer_contract_version") or ""),
        "artifact_store": {
            "root": str((artifact_store or {}).get("root") or artifact_initialization.get("root") or ""),
            "expected_root_state": str(artifact_initialization.get("expected_root_state") or ""),
            "initialization_required": bool(artifact_initialization.get("required")),
        },
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "generated_at": str(plan.get("created_at") or ""),
    }
    snapshot["environment_snapshot_sha256"] = canonical_sha256(snapshot)
    return snapshot


def validate_environment_snapshot(plan: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_environment_snapshot(plan)
    blockers: list[str] = []
    if snapshot.get("environment_snapshot_sha256") != expected["environment_snapshot_sha256"]:
        blockers.append("environment_snapshot_sha256_mismatch")
    for field in ("registry_sha256", "policy_sha256", "catalog_sha256", "active_pointer_sha256", "active_baseline_tree_sha256", "plan_id", "plan_sha256"):
        if str(snapshot.get(field) or "") != str(expected.get(field) or ""):
            blockers.append(f"environment_{field}_mismatch")
    return {
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "expected_environment_snapshot_sha256": expected["environment_snapshot_sha256"],
        "provided_environment_snapshot_sha256": str(snapshot.get("environment_snapshot_sha256") or ""),
        "exit_code": 0 if not blockers else 5,
    }


def same_filesystem(path_a: Path, path_b: Path) -> bool:
    try:
        probe_a = path_a if path_a.exists() else path_a.parent
        probe_b = path_b if path_b.exists() else path_b.parent
        return os.stat(probe_a).st_dev == os.stat(probe_b).st_dev
    except OSError:
        return False
