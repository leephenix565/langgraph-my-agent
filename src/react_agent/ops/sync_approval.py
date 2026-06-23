# ruff: noqa: D101, D103
"""Machine approval validation for sync writer phases."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from react_agent.ops.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    read_json,
    validate_by_schema_version,
)
from react_agent.ops.sync_environment import (
    build_environment_snapshot,
    validate_environment_snapshot,
)


def _parse_timestamp(value: str) -> datetime:
    if not value.endswith("Z"):
        raise SyncPlannerError("invalid_approval_timestamp", exit_code=2)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def load_approval(path: Path) -> dict[str, Any]:
    approval = read_json(path)
    if not isinstance(approval, dict):
        raise SyncPlannerError("approval_not_object", exit_code=2)
    validate_by_schema_version(approval)
    return approval


def approval_canonical_sha256(approval: Mapping[str, Any]) -> str:
    return canonical_sha256(approval, exclude_hash_field=True)


def _scope_ids(plan: Mapping[str, Any]) -> tuple[set[str], set[str], set[str]]:
    agent_ids: set[str] = set()
    transaction_ids: set[str] = set()
    action_ids: set[str] = set()
    for agent in plan.get("agents") or []:
        if not isinstance(agent, Mapping):
            continue
        agent_ids.add(str(agent.get("agent_id") or ""))
        transaction_ids.add(str(agent.get("transaction_id") or ""))
        for action in agent.get("actions") or []:
            if isinstance(action, Mapping):
                action_ids.add(str(action.get("action_id") or ""))
    return agent_ids, transaction_ids, action_ids


def _list_subset(values: object, allowed: set[str], reason: str, blockers: list[str]) -> None:
    if not isinstance(values, list):
        blockers.append(f"{reason}_not_list")
        return
    unknown = sorted({str(item) for item in values} - allowed)
    if unknown:
        blockers.append(f"{reason}_outside_plan_scope")


def _list_exact(values: object, allowed: set[str], reason: str, blockers: list[str]) -> None:
    if not isinstance(values, list):
        blockers.append(f"{reason}_not_list")
        return
    actual = {str(item) for item in values}
    if actual != allowed:
        blockers.append(f"{reason}_not_full_plan_scope")


def validate_approval(
    approval: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    environment_snapshot: Mapping[str, Any] | None = None,
    require_stage: bool = False,
    require_verify: bool = False,
    require_artifact_store_initialize: bool = False,
    require_activate: bool = False,
    require_rollback: bool = False,
    require_full_scope: bool = True,
    allow_execution_phase: str = "SYNC-OPS-2B",
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate_by_schema_version(approval)
    except SyncPlannerError as exc:
        blockers.append(f"schema_{exc.reason}")
    if approval.get("status") != "approved":
        blockers.append("approval_status_not_approved")
    if str(approval.get("plan_id") or "") != str(plan.get("plan_id") or ""):
        blockers.append("approval_plan_id_mismatch")
    if str(approval.get("plan_sha256") or "") != str(plan.get("canonical_sha256") or ""):
        blockers.append("approval_plan_sha256_mismatch")
    if str(approval.get("execution_phase") or "") != allow_execution_phase:
        blockers.append("approval_execution_phase_not_allowed")
    if not str(approval.get("operator_reference") or ""):
        blockers.append("approval_operator_reference_missing")
    now = datetime.now(UTC)
    try:
        if _parse_timestamp(str(plan.get("expires_at") or "")) <= now:
            blockers.append("approval_plan_expired")
    except SyncPlannerError:
        blockers.append("approval_plan_expires_invalid")
    try:
        if _parse_timestamp(str(approval.get("expires_at") or "")) <= now:
            blockers.append("approval_expired")
    except SyncPlannerError:
        blockers.append("approval_expires_invalid")
    expected_env = environment_snapshot or build_environment_snapshot(plan)
    if str(approval.get("environment_snapshot_sha256") or "") != str(expected_env.get("environment_snapshot_sha256") or ""):
        blockers.append("approval_environment_snapshot_sha256_mismatch")
    env_result = validate_environment_snapshot(plan, expected_env)
    if not env_result["valid"]:
        blockers.extend(str(item) for item in env_result["blockers"])
    agent_ids, transaction_ids, action_ids = _scope_ids(plan)
    _list_subset(approval.get("approved_agent_ids"), agent_ids, "approved_agent_ids", blockers)
    _list_subset(approval.get("approved_transaction_ids"), transaction_ids, "approved_transaction_ids", blockers)
    _list_subset(approval.get("approved_action_ids"), action_ids, "approved_action_ids", blockers)
    if require_full_scope and (require_stage or require_verify or require_activate or require_rollback):
        _list_exact(approval.get("approved_agent_ids"), agent_ids, "approved_agent_ids", blockers)
        _list_exact(approval.get("approved_transaction_ids"), transaction_ids, "approved_transaction_ids", blockers)
        _list_exact(approval.get("approved_action_ids"), action_ids, "approved_action_ids", blockers)
    if require_stage and approval.get("stage_approved") is not True:
        blockers.append("approval_stage_not_approved")
        blockers.append("stage_permission_missing")
    if require_verify and approval.get("verify_approved") is not True:
        blockers.append("approval_verify_not_approved")
        blockers.append("verify_permission_missing")
    if require_artifact_store_initialize and approval.get("artifact_store_initialize_approved") is not True:
        blockers.append("approval_artifact_store_initialize_not_approved")
        blockers.append("artifact_store_initialize_permission_missing")
    if require_activate and approval.get("activate_approved") is not True:
        blockers.append("approval_activate_not_approved")
        blockers.append("activate_permission_missing")
    if require_rollback and approval.get("rollback_approved") is not True:
        blockers.append("approval_rollback_not_approved")
        blockers.append("rollback_permission_missing")
    if approval.get("delete_approved"):
        blockers.append("approval_delete_not_supported_for_p2s")
    if approval.get("process_action_approved"):
        blockers.append("approval_process_action_not_supported_for_p2s")
    if approval.get("live_validation_approved"):
        blockers.append("approval_live_validation_not_supported_for_p2s")
    if any(keyword in str(approval).lower() for keyword in ("password", "api_key", "secret=", "token=")):
        blockers.append("approval_contains_sensitive_keyword")
    return {
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "approval_sha256": approval_canonical_sha256(approval),
        "environment_snapshot_sha256": str(expected_env.get("environment_snapshot_sha256") or ""),
        "exit_code": 0 if not blockers else 4,
    }


def build_stage_approval_request(plan: Mapping[str, Any], environment_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    init_required = bool((plan.get("artifact_store_initialization") or {}).get("required"))
    return {
        "schema_version": "agent_sync_p2s_approval_request_v1",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "environment_snapshot_sha256": str(environment_snapshot.get("environment_snapshot_sha256") or ""),
        "artifact_store_root": str(((plan.get("execution_contract") or {}).get("artifact_store") or {}).get("root") or ""),
        "stage_root": str((plan.get("stage_materialization") or {}).get("stage_root") or ""),
        "expires_at": str(plan.get("expires_at") or ""),
        "requested_agent_scopes": [str(agent.get("agent_id") or "") for agent in plan.get("agents") or [] if isinstance(agent, Mapping)],
        "requested_transaction_scopes": [str(agent.get("transaction_id") or "") for agent in plan.get("agents") or [] if isinstance(agent, Mapping)],
        "requested_action_scopes": [
            str(action.get("action_id") or "")
            for agent in plan.get("agents") or []
            if isinstance(agent, Mapping)
            for action in agent.get("actions") or []
            if isinstance(action, Mapping)
        ],
        "artifact_store_initialize_requested": init_required,
        "stage_requested": True,
        "verify_requested": True,
        "activate_requested": False,
        "rollback_requested": False,
        "post_rollback_reactivate_requested": False,
        "requested_stage_permission": True,
        "requested_activate_permission": False,
        "requested_rollback_permission": False,
        "delete_requested": False,
        "process_action_requested": False,
        "live_requested": False,
        "operator_action_required": True,
        "status": "awaiting_machine_approval",
        "approval_id": "",
        "approved_at": "",
    }


def build_activation_approval_request_template(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "agent_sync_p2s_activation_approval_request_template_v1",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "status": "blocked_pending_real_stage_closeout",
        "artifact_store_root": str(((plan.get("execution_contract") or {}).get("artifact_store") or {}).get("root") or ""),
        "missing_real_stage_fields": [
            "stage_run_id",
            "stage_artifact_index_sha256",
            "stage_tree_digest",
            "stage_validation_sha256",
            "current_active_pointer_sha256",
            "current_active_tree_sha256",
            "candidate_path",
            "archive_path",
        ],
        "activate_requested": True,
        "rollback_requested": True,
        "post_rollback_reactivate_requested": False,
        "approval_id": "",
        "approved_at": "",
    }


def build_approval_request(plan: Mapping[str, Any], environment_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Backward-compatible request builder now returns the stage-only request."""
    return build_stage_approval_request(plan, environment_snapshot)
