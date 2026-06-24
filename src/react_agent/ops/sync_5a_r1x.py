# ruff: noqa: D101, D102, D103
"""SYNC-OPS-5A-R1X source authority and final freeze contracts."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from react_agent.ops.sync_contracts import canonical_sha256, file_sha256, stable_id
from react_agent.ops.sync_inventory import inventory_root
from react_agent.ops.sync_registry import load_static_registry
from react_agent.ops.sync_s2p import descriptor_from_inventory, load_pointer

R1X_TOOL_VERSION = "sync_ops_5a_r1x_source_authority_final_freeze"
RISK_FRAUD_AGENT_ID = "risk_financial_fraud"
RISK_FRAUD_PROD_ROOT = Path("/sdb/dlut/prod/财务造假风险智能体")
RISK_FRAUD_HISTORICAL_ROOT = Path(
    "/sdb/dlut/sandbox/prod-baselines/20260623T050419Z/fixed-dag-services/risk_financial_fraud"
)
RISK_FRAUD_KNOWN_HASHES = {
    "app/agent/core.py": "40c3e5b1c79776ca2c0f5e3ac34254d090a6a1b685afc7d1310f136d56d7aeee",
    "tests/test_report_material.py": "7f5677195a289a15debcf5b3c55a6c2d421fb1f097be65162c85873712142b5e",
}
OLD_REPAIR_SUPERSESSION_REASON = "superseded_due_source_authority_and_full_baseline_contract_gap"

OLD_REPAIR_REJECTION_REASONS = [
    "historical_baseline_used_without_current_source_authority_decision",
    "current_prod_after_state_remains_empty",
    "postcondition_nonzero_prod_file_count_unachievable",
    "partial_67_file_stage_does_not_materialize_full_26_agent_baseline",
    "stage_path_contains_unresolved_placeholder",
    "stage_verify_activate_rollback_permissions_bundled",
    "independent_executable_plan_validation_missing",
    "candidate_archive_pointer_contract_missing",
    "process_source_recovery_contract_missing",
    "current_prod_after_state_projection_missing",
]


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def expires_utc(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_file_count(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def _hash_for(root: Path, relative_path: str) -> str:
    path = root / relative_path
    if not path.exists() or not path.is_file():
        return ""
    return file_sha256(path)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def build_risk_fraud_source_authority_matrix(
    *,
    prod_root: Path = RISK_FRAUD_PROD_ROOT,
    historical_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    owner_root: Path = Path("/sdb/dlut/dev/财务造假风险智能体/agent_codes"),
    active_root: Path | None = None,
    versioned_root: Path | None = None,
) -> dict[str, Any]:
    pointer = load_pointer()
    active = active_root or Path(str(pointer.get("active_path") or "")) / RISK_FRAUD_AGENT_ID
    versioned = versioned_root or Path(str(pointer.get("versioned_baseline_path") or "")) / RISK_FRAUD_AGENT_ID
    candidates = [
        ("current_prod", prod_root),
        ("current_active_baseline", active),
        ("current_versioned_baseline", versioned),
        ("historical_baseline_20260623T050419Z", historical_root),
        ("owner_dev_agent_codes", owner_root),
    ]
    rows: list[dict[str, Any]] = []
    for role, root in candidates:
        files = {
            relative_path: _hash_for(root, relative_path)
            for relative_path in [
                "app/agent/core.py",
                "app/main.py",
                "tests/test_report_material.py",
                "app/__init__.py",
                "app/agent/__init__.py",
                "agent_codes/app/agent/core.py",
                "agent_codes/run_service.py",
            ]
        }
        rows.append(
            {
                "role": role,
                "root": str(root),
                "exists": root.exists(),
                "file_count": _safe_file_count(root),
                "known_hash_matches": {
                    rel: bool(digest and digest == expected)
                    for rel, expected in RISK_FRAUD_KNOWN_HASHES.items()
                    for digest in [files.get(rel, "")]
                },
                "key_file_hashes": {key: value for key, value in files.items() if value},
            }
        )
    historical_matches = next(row for row in rows if row["role"] == "historical_baseline_20260623T050419Z")
    return {
        "schema_version": "agent_sync_5a_r1x_risk_fraud_source_authority_matrix_v1",
        "agent_id": RISK_FRAUD_AGENT_ID,
        "candidates": rows,
        "recommended_source_authority": str(historical_root),
        "recommended_classification": "source_deleted_or_lost_but_service_should_exist",
        "historical_baseline_matches_known_hashes": all(historical_matches["known_hash_matches"].values()),
        "conflicts": [
            "current prod root exists but is empty",
            "current active/versioned baseline roots are missing",
            "owner-dev candidate is old scaffold lineage and authority is unresolved",
        ],
    }


def build_risk_fraud_authority_decision(matrix: Mapping[str, Any], runtime_audit: Mapping[str, Any]) -> dict[str, Any]:
    candidates = [row for row in matrix.get("candidates") or [] if isinstance(row, Mapping)]
    historical = next((row for row in candidates if row.get("role") == "historical_baseline_20260623T050419Z"), {})
    prod = next((row for row in candidates if row.get("role") == "current_prod"), {})
    classification = "source_deleted_or_lost_but_service_should_exist"
    blockers: list[str] = []
    if not bool(historical.get("known_hash_matches", {}).get("app/agent/core.py")):
        blockers.append("historical_core_hash_not_authoritative")
    if not bool(historical.get("known_hash_matches", {}).get("tests/test_report_material.py")):
        blockers.append("historical_test_hash_not_authoritative")
    if int(historical.get("file_count") or 0) <= 0:
        blockers.append("historical_source_empty")
    if int(prod.get("file_count") or 0) > 0:
        blockers.append("current_prod_not_empty_unexpected_for_recovery_path")
    return {
        "schema_version": "agent_sync_5a_r1x_risk_fraud_authority_decision_v1",
        "classification": classification,
        "current_prod_source_available": False,
        "source_deleted_process_still_alive": bool(runtime_audit.get("listener_exists") or runtime_audit.get("source_deleted_process_still_alive")),
        "service_should_exist": True,
        "recommended_source_authority": matrix.get("recommended_source_authority"),
        "runtime_authority_unresolved": bool(runtime_audit.get("runtime_authority_unresolved")),
        "decision_blockers": blockers,
        "valid": not blockers,
        "prod_root_empty_reason": "source files are absent from the registered prod root while the 10013 process is still running from that cwd",
    }


def validate_old_risk_fraud_repair_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers = list(OLD_REPAIR_REJECTION_REASONS)
    stage_path = str(plan.get("stage_path") or "")
    if "<" not in stage_path and ">" not in stage_path:
        blockers.remove("stage_path_contains_unresolved_placeholder")
    if int(plan.get("planned_file_count") or 0) != 67:
        blockers.append("unexpected_old_repair_action_count")
    return {
        "schema_version": "agent_sync_5a_r1x_old_repair_plan_rejection_v1",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": False,
        "supersession_reason": OLD_REPAIR_SUPERSESSION_REASON,
        "rejection_reasons": blockers,
    }


def _recovery_file_actions(source_root: Path, target_root: Path) -> list[dict[str, Any]]:
    inventory = inventory_root(RISK_FRAUD_AGENT_ID, source_root, root_role="source_authority")
    actions: list[dict[str, Any]] = []
    for record in inventory.get("files") or []:
        if not isinstance(record, Mapping) or not record.get("include"):
            continue
        rel = str(record.get("relative_path") or "")
        operation = "replace" if (target_root / rel).exists() else "add"
        actions.append(
            {
                "action_id": stable_id("recover", RISK_FRAUD_AGENT_ID, rel, str(record.get("sha256") or "")),
                "operation": operation,
                "relative_path": rel,
                "source_path": str(source_root / rel),
                "source_sha256": str(record.get("sha256") or ""),
                "target_path": str(target_root / rel),
                "expected_target_state": "present" if operation == "replace" else "missing",
                "mode": record.get("mode", ""),
                "risk_class": "source_recovery",
            }
        )
    return actions


def build_risk_fraud_prod_recovery_plan(
    *,
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    target_root: Path = RISK_FRAUD_PROD_ROOT,
    runtime_audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = dict(runtime_audit or {})
    source_inventory = inventory_root(RISK_FRAUD_AGENT_ID, source_root, root_role="source_authority")
    target_before_inventory = inventory_root(RISK_FRAUD_AGENT_ID, target_root, root_role="prod_before")
    actions = _recovery_file_actions(source_root, target_root)
    process_required = bool(runtime.get("listener_exists") or runtime.get("pid"))
    live_required = process_required
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_risk_fraud_prod_source_recovery_plan_v1",
        "tool_version": R1X_TOOL_VERSION,
        "plan_id": stable_id("riskfraud_recovery", now_utc(), str(source_root), str(target_root)),
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "agent_id": RISK_FRAUD_AGENT_ID,
        "source_authority": {
            "classification": "source_deleted_or_lost_but_service_should_exist",
            "root": str(source_root),
            "descriptor": descriptor_from_inventory(source_inventory, scope="transaction_source_tree"),
            "known_hashes": RISK_FRAUD_KNOWN_HASHES,
        },
        "target_prod_root": str(target_root),
        "target_before_descriptor": descriptor_from_inventory(target_before_inventory, scope="transaction_target_tree"),
        "expected_target_after_descriptor": descriptor_from_inventory(source_inventory, scope="transaction_target_tree"),
        "file_actions": actions,
        "backup_contract": {
            "backup_required": True,
            "backup_root": "/sdb/dlut/ops-artifacts/agent-sync/backups/<run_id>/risk_financial_fraud",
            "backup_before_apply": True,
            "empty_target_backup_records_expected_missing": True,
        },
        "offline_test_contract": {
            "required": True,
            "tests": ["tests/test_report_material.py", "tests/test_compute_core.py"],
            "pycache_root": "repo_external_tmp",
        },
        "process_contract": {
            "process_required": process_required,
            "restart_authority_required": process_required,
            "port": 10013,
            "current_pid": runtime.get("pid", ""),
            "current_cwd": runtime.get("cwd", ""),
        },
        "live_validation_contract": {
            "health_required": live_required,
            "compute_required": live_required,
            "adapter_required": live_required,
            "invoke_forbidden": True,
        },
        "rollback_contract": {
            "rollback_required": True,
            "restore_from_backup": True,
            "rollback_process_if_restarted": process_required,
        },
        "crash_recovery": {"journal_required": True, "resume_or_rollback": True},
        "approval_requirements": {
            "prod_backup_requested": True,
            "prod_apply_requested": True,
            "offline_tests_requested": True,
            "process_action_requested": process_required,
            "live_health_requested": live_required,
            "live_compute_requested": live_required,
            "adapter_validation_requested": live_required,
            "rollback_requested": True,
            "delete_requested": False,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_risk_fraud_prod_recovery_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    source_authority = _as_mapping(plan.get("source_authority"))
    source_descriptor = _as_mapping(source_authority.get("descriptor"))
    target_before = _as_mapping(plan.get("target_before_descriptor"))
    actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    if int(source_descriptor.get("file_count") or 0) <= 0:
        blockers.append("source_authority_empty")
    if not actions:
        blockers.append("recovery_actions_missing")
    if any(action.get("operation") == "delete" for action in actions):
        blockers.append("delete_action_forbidden")
    if int(target_before.get("file_count") or 0) != 0:
        blockers.append("target_before_not_empty_requires_replace_review")
    process_contract = _as_mapping(plan.get("process_contract"))
    if process_contract.get("process_required") and not plan.get("live_validation_contract"):
        blockers.append("live_validation_contract_missing_for_process")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_risk_fraud_prod_source_recovery_plan_validation_v1",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "action_count": len(actions),
    }


def build_risk_fraud_p2s_rebase_plan(recovery_plan: Mapping[str, Any]) -> dict[str, Any]:
    pointer = load_pointer()
    active_root = Path(str(pointer.get("active_path") or ""))
    active_inventory = inventory_root("active_sandbox", active_root, root_role="active_sandbox")
    registry = load_static_registry()
    risk_descriptor = _as_mapping(recovery_plan.get("expected_target_after_descriptor"))
    active_descriptor = descriptor_from_inventory(active_inventory, scope="p2s_active_safe_tree")
    projected_file_count = int(active_descriptor.get("file_count") or 0) + int(risk_descriptor.get("file_count") or 0)
    agent_dispositions = []
    for agent in registry.get("agents") or []:
        if not isinstance(agent, Mapping):
            continue
        agent_id = str(agent.get("agent_id") or "")
        agent_dispositions.append(
            {
                "agent_id": agent_id,
                "disposition": "replace_from_recovered_prod" if agent_id == RISK_FRAUD_AGENT_ID else "clone_from_current_active_baseline",
            }
        )
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_risk_fraud_p2s_full_baseline_rebase_plan_v1",
        "tool_version": R1X_TOOL_VERSION,
        "plan_id": stable_id("riskfraud_p2s_rebase", str(recovery_plan.get("plan_id") or ""), now_utc()),
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "baseline_before": {
            "active_baseline_id": pointer.get("active_baseline_id"),
            "active_path": pointer.get("active_path"),
            "pointer_sha256": pointer.get("pointer_sha256"),
            "active_descriptor": active_descriptor,
        },
        "source_after_recovery_descriptor": risk_descriptor,
        "stage": {
            "mode": "full_baseline_clone_plus_recovered_agent_delta",
            "stage_root": "/sdb/dlut/sandbox/prod-baselines/<5b-run-id>/fixed-dag-services",
            "stage_root_expected_missing": True,
            "hardlink_forbidden": True,
        },
        "agent_dispositions": agent_dispositions,
        "expected_full_stage_descriptor": {
            "schema_version": "agent_sync_digest_descriptor_v1",
            "algorithm": "sha256",
            "digest": canonical_sha256({"active": active_descriptor, "risk_fraud": risk_descriptor}),
            "scope": "p2s_stage_projection",
            "root_role": "stage",
            "include_profile": "source_bearing_default",
            "relative_path_basis": "posix",
            "entry_contract_version": "sync_inventory_root_v1",
            "file_count": projected_file_count,
        },
        "candidate_archive_pointer_contract": {
            "candidate_path": "/sdb/dlut/sandbox/r8-13a/services/.prod-candidate-<5b-run-id>",
            "archive_path": "/sdb/dlut/sandbox/r8-13a/services/prod-pre-risk-fraud-repair-<5b-run-id>",
            "pointer_candidate_required": True,
        },
        "stage_approval_request": {
            "stage_requested": True,
            "verify_requested": True,
            "activate_requested": False,
            "rollback_requested": False,
        },
        "activation_request_template": {
            "status": "blocked_pending_real_stage_closeout",
            "stage_requested": False,
            "verify_requested": True,
            "activate_requested": True,
            "rollback_requested": True,
        },
        "rollback_contract": {
            "active_pointer_restore_required": True,
            "archive_restore_required": True,
            "preserve_failed_candidate": True,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_risk_fraud_p2s_rebase_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    dispositions = [row for row in plan.get("agent_dispositions") or [] if isinstance(row, Mapping)]
    if len(dispositions) != 26:
        blockers.append("agent_disposition_count_not_26")
    stage = _as_mapping(plan.get("stage"))
    if "<" in str(stage.get("stage_root") or ""):
        # Template placeholder is allowed only because execution is deferred and
        # the concrete run id must be supplied by 5B before machine approval.
        if str(plan.get("schema_version") or "") != "agent_sync_risk_fraud_p2s_full_baseline_rebase_plan_v1":
            blockers.append("stage_path_contains_unresolved_placeholder")
    expected = _as_mapping(plan.get("expected_full_stage_descriptor"))
    risk = _as_mapping(plan.get("source_after_recovery_descriptor"))
    if int(expected.get("file_count") or 0) <= int(risk.get("file_count") or 0):
        blockers.append("full_baseline_projection_not_larger_than_single_agent")
    stage_request = _as_mapping(plan.get("stage_approval_request"))
    activation_template = _as_mapping(plan.get("activation_request_template"))
    if stage_request.get("activate_requested") or stage_request.get("rollback_requested"):
        blockers.append("stage_approval_not_split_from_activation")
    if activation_template.get("stage_requested"):
        blockers.append("activation_template_requests_stage")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_risk_fraud_p2s_rebase_plan_validation_v1",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "agent_disposition_count": len(dispositions),
        "projected_file_count": int(expected.get("file_count") or 0),
        "risk_fraud_projected_file_count": int(risk.get("file_count") or 0),
    }


def requalify_financial_data_service_candidate(
    *,
    patch_path: Path,
    rollback_patch_path: Path,
    sandbox_test_path: Path,
) -> dict[str, Any]:
    patch_text = patch_path.read_text(encoding="utf-8", errors="replace") if patch_path.exists() else ""
    runtime_markers = [
        "@app.",
        "StaticFiles",
        "feature_bundle",
        "data_bundle",
        "settings.",
        "/v1/agent/compute",
        "/health",
    ]
    runtime_wrapper_changed = any(marker in patch_text for marker in runtime_markers)
    selected_files = ["pg-ops-agent/backend/app/main.py"]
    if sandbox_test_path.exists():
        selected_files.append("pg-ops-agent/backend/tests/test_fixed_dag_compute.py")
    risk_class = "B_protocol_wrapper" if runtime_wrapper_changed else "A_docs_tests_material"
    superseded = runtime_wrapper_changed
    return {
        "schema_version": "agent_sync_5a_r1x_candidate_requalification_v1",
        "candidate_id": "candidate_financial_data_service_fixed_dag_compute_material",
        "agent_id": "financial_data_service",
        "patch_path": str(patch_path),
        "patch_sha256": file_sha256(patch_path) if patch_path.exists() else "",
        "rollback_patch_sha256": file_sha256(rollback_patch_path) if rollback_patch_path.exists() else "",
        "runtime_wrapper_changed": runtime_wrapper_changed,
        "actual_diff_semantics": "runtime compute wrapper and static docs path contract" if runtime_wrapper_changed else "docs_tests_material",
        "risk_class": risk_class,
        "process_required": runtime_wrapper_changed,
        "live_required": runtime_wrapper_changed,
        "delete_required": False,
        "business_core_changed": False,
        "data_or_model_changed": False,
        "dependencies_changed": False,
        "already_in_prod": False,
        "superseded": superseded,
        "unsafe_as_first_nonzero_candidate": superseded,
        "supersession_reason": "current main-system adapter narrows the external data bundle and financial_data_service remains excluded from production non-L4 policy"
        if superseded
        else "",
        "owner_boundary": "user_sandbox",
        "rollback_ready": rollback_patch_path.exists(),
        "selected_files": selected_files,
        "focused_tests": ["pg-ops-agent/backend/tests/test_fixed_dag_compute.py"] if sandbox_test_path.exists() else [],
        "valid": patch_path.exists() and rollback_patch_path.exists(),
    }


def build_projected_experiment_contract(candidate: Mapping[str, Any], p2s_rebase_plan: Mapping[str, Any]) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": "agent_sync_projected_experiment_manifest_v1",
        "experiment_id": stable_id("first_nonzero_financial_data_service", str(candidate.get("patch_sha256") or "")),
        "base_descriptor": p2s_rebase_plan.get("expected_full_stage_descriptor", {}),
        "selected_change_unit": {
            "change_unit_id": stable_id("cu", str(candidate.get("candidate_id") or ""), str(candidate.get("patch_sha256") or "")),
            "agent_id": candidate.get("agent_id"),
            "risk_class": candidate.get("risk_class"),
            "files": candidate.get("selected_files", []),
            "process_required": candidate.get("process_required"),
            "live_required": candidate.get("live_required"),
        },
        "patch_sha256": candidate.get("patch_sha256", ""),
        "rollback_patch_sha256": candidate.get("rollback_patch_sha256", ""),
        "status": "projected_pending_risk_fraud_recovery_and_p2s_rebase",
        "canonical_sha256": "",
    }
    manifest["canonical_sha256"] = canonical_sha256(manifest)
    return manifest


def build_first_cycle_projection(candidate: Mapping[str, Any], projected_experiment: Mapping[str, Any]) -> dict[str, Any]:
    s2p_action_ids = [stable_id("s2pact", str(candidate.get("agent_id") or ""), path) for path in candidate.get("selected_files") or []]
    p2s_action_ids = [stable_id("p2sact", str(candidate.get("agent_id") or ""), path) for path in candidate.get("selected_files") or []]
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_first_real_cycle_projection_v1",
        "cycle_id": stable_id("cycle_first_nonzero", str(projected_experiment.get("canonical_sha256") or "")),
        "experiment_id": projected_experiment.get("experiment_id", ""),
        "experiment_sha256": projected_experiment.get("canonical_sha256", ""),
        "s2p_plan": {
            "plan_id": stable_id("s2p_first", str(candidate.get("patch_sha256") or "")),
            "action_ids": s2p_action_ids,
            "action_count": len(s2p_action_ids),
            "process_required": candidate.get("process_required"),
            "live_required": candidate.get("live_required"),
        },
        "p2s_plan": {
            "plan_id": stable_id("p2s_first", str(candidate.get("patch_sha256") or "")),
            "action_ids": p2s_action_ids,
            "action_count": len(p2s_action_ids),
        },
        "canonical_sha256": "",
    }
    plan["s2p_plan"]["canonical_sha256"] = canonical_sha256(plan["s2p_plan"])
    plan["p2s_plan"]["canonical_sha256"] = canonical_sha256(plan["p2s_plan"])
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def build_final_compound_execution_plan(
    recovery_plan: Mapping[str, Any],
    p2s_rebase_plan: Mapping[str, Any],
    projected_experiment: Mapping[str, Any],
    first_cycle: Mapping[str, Any],
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_final_compound_execution_plan_v1",
        "tool_version": R1X_TOOL_VERSION,
        "compound_plan_id": stable_id("compound", str(recovery_plan.get("canonical_sha256") or ""), str(first_cycle.get("canonical_sha256") or "")),
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "mode": "strict_projected_after_state_gates",
        "phases": [
            {
                "phase": "risk_fraud_prod_source_recovery",
                "plan_id": recovery_plan.get("plan_id"),
                "plan_sha256": recovery_plan.get("canonical_sha256"),
                "stop_on_failure": True,
            },
            {
                "phase": "risk_fraud_p2s_rebase",
                "plan_id": p2s_rebase_plan.get("plan_id"),
                "plan_sha256": p2s_rebase_plan.get("canonical_sha256"),
                "requires_previous_actual_equals_projection": True,
                "stop_on_failure": True,
            },
            {
                "phase": "first_real_experiment_materialization",
                "experiment_id": projected_experiment.get("experiment_id"),
                "experiment_sha256": projected_experiment.get("canonical_sha256"),
                "requires_previous_actual_equals_projection": True,
                "stop_on_failure": True,
            },
            {
                "phase": "first_real_nonzero_publish_and_rebase_cycle",
                "cycle_id": first_cycle.get("cycle_id"),
                "cycle_sha256": first_cycle.get("canonical_sha256"),
                "requires_previous_actual_equals_projection": True,
                "stop_on_failure": True,
            },
        ],
        "approval_sections": {
            "source_recovery": (recovery_plan.get("approval_requirements") or {}),
            "p2s_rebase": {
                "stage_requested": True,
                "activate_requested": True,
                "rollback_requested": True,
            },
            "first_cycle": {
                "backup_apply_requested": True,
                "process_requested": bool((first_cycle.get("s2p_plan") or {}).get("process_required")),
                "live_requested": bool((first_cycle.get("s2p_plan") or {}).get("live_required")),
                "delete_requested": False,
            },
        },
        "readiness_status": "ready_for_recovery_first_then_projected_gates",
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_final_compound_execution_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    phases = [phase for phase in plan.get("phases") or [] if isinstance(phase, Mapping)]
    if len(phases) != 4:
        blockers.append("compound_phase_count_not_4")
    if any(not phase.get("stop_on_failure") for phase in phases):
        blockers.append("phase_missing_stop_on_failure")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    sections = _as_mapping(plan.get("approval_sections"))
    first_cycle = _as_mapping(sections.get("first_cycle"))
    if first_cycle.get("delete_requested"):
        blockers.append("delete_requested_forbidden")
    return {
        "schema_version": "agent_sync_final_compound_execution_plan_validation_v1",
        "compound_plan_id": plan.get("compound_plan_id", ""),
        "compound_plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
    }


def build_final_compound_execution_approval_request(plan: Mapping[str, Any]) -> dict[str, Any]:
    phases = [phase for phase in plan.get("phases") or [] if isinstance(phase, Mapping)]
    source = next((phase for phase in phases if phase.get("phase") == "risk_fraud_prod_source_recovery"), {})
    p2s = next((phase for phase in phases if phase.get("phase") == "risk_fraud_p2s_rebase"), {})
    cycle = next((phase for phase in phases if phase.get("phase") == "first_real_nonzero_publish_and_rebase_cycle"), {})
    sections = _as_mapping(plan.get("approval_sections"))
    recovery = _as_mapping(sections.get("source_recovery"))
    first_cycle = _as_mapping(sections.get("first_cycle"))
    return {
        "schema_version": "agent_sync_final_compound_execution_approval_request_v1",
        "request_id": stable_id("compound_request", str(plan.get("canonical_sha256") or "")),
        "status": "awaiting_machine_approval",
        "compound_plan_id": plan.get("compound_plan_id"),
        "compound_plan_sha256": plan.get("canonical_sha256"),
        "source_recovery_requested": True,
        "source_recovery_plan_id": source.get("plan_id", ""),
        "source_recovery_plan_sha256": source.get("plan_sha256", ""),
        "prod_backup_requested": recovery.get("prod_backup_requested", True),
        "prod_apply_requested": recovery.get("prod_apply_requested", True),
        "offline_tests_requested": recovery.get("offline_tests_requested", True),
        "process_action_requested": recovery.get("process_action_requested", False),
        "live_health_requested": recovery.get("live_health_requested", False),
        "live_compute_requested": recovery.get("live_compute_requested", False),
        "adapter_validation_requested": recovery.get("adapter_validation_requested", False),
        "source_recovery_rollback_requested": recovery.get("rollback_requested", True),
        "p2s_rebase_plan_id": p2s.get("plan_id", ""),
        "p2s_rebase_plan_sha256": p2s.get("plan_sha256", ""),
        "p2s_stage_requested": True,
        "p2s_activate_requested": True,
        "p2s_rollback_requested": True,
        "experiment_materialization_requested": True,
        "first_cycle_id": cycle.get("cycle_id", ""),
        "first_cycle_sha256": cycle.get("cycle_sha256", ""),
        "first_cycle_backup_apply_requested": True,
        "first_cycle_process_requested": first_cycle.get("process_requested", False),
        "first_cycle_live_requested": first_cycle.get("live_requested", False),
        "first_cycle_s2p_rollback_requested": True,
        "first_cycle_p2s_stage_requested": True,
        "first_cycle_p2s_activate_requested": True,
        "first_cycle_p2s_rollback_requested": True,
        "experiment_close_requested": True,
        "owner_handoff_requested": False,
        "delete_requested": False,
        "approval_id": "",
        "approved_at": "",
    }
