# ruff: noqa: D101, D102, D103
"""SYNC-OPS-5A-R2X source-loss recovery and final freeze contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from react_agent.ops_sync.sync_5a_r1x import (
    RISK_FRAUD_AGENT_ID,
    RISK_FRAUD_HISTORICAL_ROOT,
    RISK_FRAUD_KNOWN_HASHES,
    RISK_FRAUD_PROD_ROOT,
)
from react_agent.ops_sync.sync_contracts import canonical_sha256, file_sha256, stable_id
from react_agent.ops_sync.sync_inventory import inventory_root
from react_agent.ops_sync.sync_registry import load_static_registry
from react_agent.ops_sync.sync_s2p import descriptor_from_inventory, load_pointer

R2X_TOOL_VERSION = "sync_ops_5a_r2x_source_loss_recovery_final_freeze"
SOURCE_LOSS_INCIDENT_CLASS = "source_deleted_process_still_alive"
SOURCE_LOSS_CUTOVER = "verified_roll_forward"
DEFAULT_CANARY_PORT = 11013
MARKET_CANDIDATE_ID = "candidate_market_capital_flow_chip_contract_test"
MARKET_PATCH = Path(
    "/sdb/dlut/sandbox/backups/p2s_pre_refresh_20260623T050419Z/per_agent_patches/"
    "market_capital_flow_chip/tests__test_domain_contract_v1.py.patch"
)
MARKET_REVERSE_PATCH = Path(
    "/sdb/dlut/sandbox/backups/p2s_pre_refresh_20260623T050419Z/per_agent_patches/"
    "market_capital_flow_chip/tests__test_domain_contract_v1.py.u0.patch"
)
FINANCIAL_PATCH = Path(
    "/sdb/dlut/sandbox/backups/p2s_pre_refresh_20260623T050419Z/per_agent_patches/"
    "financial_data_service/pg-ops-agent__backend__app__main.py.patch"
)
MACRO_PATCH = Path(
    "/sdb/dlut/sandbox/backups/p2s_pre_refresh_20260623T050419Z/per_agent_patches/"
    "macro_commodity_pricing/agent协议__fixed_dag_compute.py.patch"
)


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def expires_utc(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def _path_has_placeholder(value: str) -> bool:
    return "<" in value or ">" in value


def _secret_like_findings(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    pattern = re.compile(r"(?i)(api[_-]?key|secret|token)\s*=\s*['\"]([A-Za-z0-9_./+=-]{16,})['\"]")
    for path in _safe_files(root):
        if path.suffix not in {".py", ".md", ".json", ".txt", ".env", ".sample", ".yml", ".yaml"}:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in pattern.finditer(text):
            findings.append({"path": rel, "kind": match.group(1).lower()})
    return findings


def build_source_package_integrity(source_root: Path = RISK_FRAUD_HISTORICAL_ROOT) -> dict[str, Any]:
    inventory = inventory_root(RISK_FRAUD_AGENT_ID, source_root, root_role="source_loss_recovery_package")
    files = [record for record in inventory.get("files") or [] if isinstance(record, Mapping) and record.get("include")]
    manifest = [
        {
            "relative_path": str(record.get("relative_path") or ""),
            "sha256": str(record.get("sha256") or ""),
            "mode": str(record.get("mode") or ""),
            "type": "file",
        }
        for record in files
    ]
    manifest_by_path = {item["relative_path"]: item for item in manifest}
    proven = [
        rel
        for rel, digest in {
            **RISK_FRAUD_KNOWN_HASHES,
            "app/main.py": "db147a2417e33edf606adb108d1e906f11dc55982490228e203090764011023b",
        }.items()
        if manifest_by_path.get(rel, {}).get("sha256") == digest
    ]
    startup_files = ["app/main.py", "app/config.py", "app/agent/core.py", "app/schemas.py"]
    test_files = ["tests/test_report_material.py", "tests/test_compute_core.py", "tests/test_protocol_contract.py"]
    secret_findings = _secret_like_findings(source_root)
    blockers: list[str] = []
    if len(manifest) != 67:
        blockers.append("source_package_file_count_not_67")
    for rel in startup_files:
        if rel not in manifest_by_path:
            blockers.append(f"startup_file_missing:{rel}")
    for rel in RISK_FRAUD_KNOWN_HASHES:
        if rel not in proven:
            blockers.append(f"known_hash_mismatch:{rel}")
    if secret_findings:
        blockers.append("secret_like_source_package_content")
    return {
        "schema_version": "agent_sync_5a_r2x_source_package_integrity_v1",
        "source_root": str(source_root),
        "descriptor": descriptor_from_inventory(inventory, scope="transaction_source_tree"),
        "file_count": len(manifest),
        "manifest_sha256": canonical_sha256(manifest),
        "manifest": manifest,
        "accepted_lineage_paths": proven,
        "accepted_lineage_count": len(proven),
        "unproven_lineage_count": max(0, len(manifest) - len(proven)),
        "startup_closure": {"required_files": startup_files, "complete": all(rel in manifest_by_path for rel in startup_files)},
        "test_closure": {"required_files": test_files, "present": [rel for rel in test_files if rel in manifest_by_path]},
        "secret_findings": secret_findings,
        "backup_runtime_data_model_exclusions": {
            "backup_files_included": 0,
            "runtime_cache_files_included": 0,
            "model_weight_files_included": 0,
            "data_snapshot_files_included": 0,
        },
        "valid": not blockers,
        "blockers": blockers,
    }


def build_launch_authority_audit(
    *,
    pid: str,
    cwd: str,
    exe: str = "/usr/bin/python3.14",
    argv: list[str] | None = None,
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    canary_port: int = DEFAULT_CANARY_PORT,
    classification_override: str = "",
) -> dict[str, Any]:
    argv_list = argv or ["python3", "-u", "-m", "app.main"]
    config_text = (source_root / "app/config.py").read_text(encoding="utf-8", errors="replace") if (source_root / "app/config.py").exists() else ""
    app_port_supported = "APP_PORT" in config_text
    dotenv_reference = "load_dotenv(SERVICE_ROOT / \".env\")" in config_text
    required_names = sorted(
        set(re.findall(r"_from_env\(\"([A-Z0-9_]+)\"", config_text))
        | set(re.findall(r"os\.getenv\(\"([A-Z0-9_]+)\"", config_text))
    )
    classification = classification_override or ("launch_authority_complete" if app_port_supported else "canary_port_override_missing")
    blockers: list[str] = []
    if not pid:
        blockers.append("current_process_pid_missing")
    if not app_port_supported:
        blockers.append("canary_port_override_missing")
    if classification in {"restart_authority_unresolved", "environment_source_unreproducible"}:
        blockers.append(classification)
    return {
        "schema_version": "agent_sync_5a_r2x_launch_authority_audit_v1",
        "classification": classification,
        "process_manager": "manual_exact_argv",
        "pid": pid,
        "cwd": cwd,
        "exe": exe,
        "safe_argv": argv_list,
        "port_configuration_method": "APP_PORT environment variable with default 10013" if app_port_supported else "default_only",
        "canary_port": canary_port,
        "canary_supported": app_port_supported,
        "canary_port_override_supported": app_port_supported,
        "environment_source": {
            "status": "reconstructable_without_reading_values",
            "dotenv_reference_path": ".env" if dotenv_reference else "",
            "required_variable_names": required_names,
            "values_optional_or_defaulted": True,
            "values_read": False,
            "proc_environ_read": False,
        },
        "graceful_stop_method": "approved 5B operator stop via process manager or bounded SIGTERM; not executed in 5A-R2X",
        "startup_timeout_seconds": 45,
        "listener_release_timeout_seconds": 15,
        "blockers": blockers,
        "valid": not blockers,
    }


def build_canary_contract(
    *,
    plan_id: str,
    candidate_path: Path,
    canary_port: int = DEFAULT_CANARY_PORT,
    python_exe: str = "/usr/bin/python3.14",
) -> dict[str, Any]:
    request_fixture = {
        "schema_version": "external_agent_compute_v0",
        "agent_id": RISK_FRAUD_AGENT_ID,
        "target": "600519.SH",
        "as_of": "2024-12-31",
    }
    return {
        "schema_version": "agent_sync_5a_r2x_canary_contract_v1",
        "plan_id": plan_id,
        "canary_port": canary_port,
        "loopback_only": True,
        "candidate_cwd": str(candidate_path),
        "argv": [python_exe, "-u", "-m", "app.main"],
        "environment_overrides": {"APP_PORT": str(canary_port)},
        "startup_timeout_seconds": 45,
        "graceful_stop_method": "bounded SIGTERM after canary validation",
        "health_url": f"http://127.0.0.1:{canary_port}/health",
        "compute_url": f"http://127.0.0.1:{canary_port}/v1/agent/compute",
        "invoke_forbidden": True,
        "external_network_forbidden": True,
        "raw_response_persistence_forbidden": True,
        "request_fixture_sha256": canonical_sha256(request_fixture),
        "adapter_expected_contract": "external_agent_compute_v0_to_internal_contract",
        "comparison_rules": [
            "http_status_class",
            "health_schema",
            "fixed_dag_agent_id",
            "compute_envelope_schema",
            "tool_result_schema",
            "adapter_validator",
            "public_safe_top_level_contract",
        ],
    }


def validate_superseded_r1x_recovery_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    target_root = str(plan.get("target_prod_root") or "")
    actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    rejection_reasons = [
        "superseded_due_irreversible_source_loss_semantics",
        "previous_runtime_restore_supported_false_missing",
        "empty_tree_restore_is_not_runtime_rollback",
        "candidate_sibling_path_missing",
        "shadow_canary_contract_missing",
        "irreversible_acknowledgement_missing",
        "source_loss_archive_path_missing",
    ]
    if any(str(action.get("target_path") or "").startswith(target_root) for action in actions):
        rejection_reasons.append("in_place_current_cwd_file_actions")
    process = _as_mapping(plan.get("process_contract"))
    if process.get("process_required") and not process.get("launcher"):
        rejection_reasons.append("process_required_but_exact_launcher_missing")
    rollback = _as_mapping(plan.get("rollback_contract"))
    if rollback.get("restore_from_backup"):
        rejection_reasons.append("backup_empty_tree_cannot_restore_old_runtime")
    return {
        "schema_version": "agent_sync_5a_r2x_superseded_recovery_plan_v1",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": False,
        "status": "superseded_due_irreversible_source_loss_recovery_gap",
        "rejection_reasons": rejection_reasons,
    }


def validate_superseded_r1x_p2s_projection(plan: Mapping[str, Any]) -> dict[str, Any]:
    stage = _as_mapping(plan.get("stage"))
    candidate = _as_mapping(plan.get("candidate_archive_pointer_contract"))
    reasons = [
        "superseded_due_exact_full_rebase_contract_gap",
        "full_materialization_manifest_missing",
        "stage_action_ids_missing",
        "activation_template_not_bound_to_real_stage_closeout",
    ]
    for key, value in {
        "stage_path_contains_placeholder": str(stage.get("stage_root") or ""),
        "candidate_path_contains_placeholder": str(candidate.get("candidate_path") or ""),
        "archive_path_contains_placeholder": str(candidate.get("archive_path") or ""),
    }.items():
        if _path_has_placeholder(value):
            reasons.append(key)
    return {
        "schema_version": "agent_sync_5a_r2x_superseded_p2s_projection_v1",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": False,
        "status": "superseded_due_concrete_full_rebase_contract_gap",
        "rejection_reasons": reasons,
    }


def build_source_loss_recovery_plan_v2(
    *,
    runtime_audit: Mapping[str, Any],
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    target_root: Path = RISK_FRAUD_PROD_ROOT,
    canary_port: int = DEFAULT_CANARY_PORT,
) -> dict[str, Any]:
    integrity = build_source_package_integrity(source_root)
    launch = build_launch_authority_audit(
        pid=str(runtime_audit.get("pid") or ""),
        cwd=str(runtime_audit.get("cwd") or target_root),
        exe=str(runtime_audit.get("exe") or "/usr/bin/python3.14"),
        argv=list(runtime_audit.get("argv") or ["python3", "-u", "-m", "app.main"]),
        source_root=source_root,
        canary_port=canary_port,
        classification_override=str(runtime_audit.get("launch_authority_classification") or ""),
    )
    plan_id = stable_id("source_loss_recovery", integrity["manifest_sha256"], str(target_root), str(canary_port))
    candidate_path = target_root.parent / f".agent-sync-risk-fraud-recovery-{plan_id}"
    archive_path = target_root.parent / f".agent-sync-risk-fraud-source-loss-evidence-{plan_id}"
    canary = build_canary_contract(plan_id=plan_id, candidate_path=candidate_path, canary_port=canary_port, python_exe=str(runtime_audit.get("exe") or "/usr/bin/python3.14"))
    actions = [
        {
            "action_id": stable_id("slr", plan_id, item["relative_path"], item["sha256"]),
            "operation": "materialize_to_sibling_candidate",
            "source_path": str(source_root / item["relative_path"]),
            "candidate_path": str(candidate_path / item["relative_path"]),
            "relative_path": item["relative_path"],
            "source_sha256": item["sha256"],
            "mode": item["mode"],
        }
        for item in integrity["manifest"]
    ]
    target_before = inventory_root(RISK_FRAUD_AGENT_ID, target_root, root_role="prod_before_source_loss")
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_recovery_plan_v2",
        "tool_version": R2X_TOOL_VERSION,
        "plan_id": plan_id,
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "incident": {
            "incident_class": SOURCE_LOSS_INCIDENT_CLASS,
            "previous_runtime_restore_supported": False,
            "cutover_semantics": SOURCE_LOSS_CUTOVER,
            "empty_tree_restore_is_rollback": False,
            "irreversible_cutover_acknowledgement_required": True,
        },
        "source_authority": {
            "root": str(source_root),
            "descriptor": integrity["descriptor"],
            "manifest_sha256": integrity["manifest_sha256"],
            "integrity_valid": integrity["valid"],
        },
        "target": {
            "target_root": str(target_root),
            "target_before_descriptor": descriptor_from_inventory(target_before, scope="transaction_target_tree"),
            "target_expected_empty_source_tree": True,
        },
        "candidate": {
            "candidate_path": str(candidate_path),
            "candidate_path_expected_missing": True,
            "candidate_descriptor": integrity["descriptor"],
            "no_hardlinks": True,
            "no_symlink_parents": True,
        },
        "source_loss_evidence_archive": {
            "archive_path": str(archive_path),
            "archive_path_expected_missing": True,
            "preserve_after_cutover": True,
        },
        "file_actions": actions,
        "process_identity_precondition": {
            "port": 10013,
            "pid": str(runtime_audit.get("pid") or ""),
            "start_time": str(runtime_audit.get("start_time") or ""),
            "cwd": str(runtime_audit.get("cwd") or ""),
            "exe": str(runtime_audit.get("exe") or ""),
            "argv": list(runtime_audit.get("argv") or ["python3", "-u", "-m", "app.main"]),
        },
        "launch_authority": launch,
        "environment_source_contract": launch["environment_source"],
        "canary_contract": canary,
        "offline_tests": ["tests/test_report_material.py", "tests/test_compute_core.py", "tests/test_protocol_contract.py"],
        "cutover_sequence": ["precheck", "candidate", "shadow_canary", "final_cutover_precheck", "cutover", "settle"],
        "rollback_semantics": {
            "restore_empty_tree_forbidden": True,
            "post_stop_recovery": "roll_forward_to_verified_candidate_or_manual_intervention",
            "manual_intervention_on_roll_forward_failure": True,
        },
        "requested_permissions": {
            "candidate_materialization": True,
            "shadow_canary_process": True,
            "incumbent_health_compute_adapter": True,
            "canary_health_compute_adapter": True,
            "incumbent_graceful_stop": True,
            "source_root_atomic_cutover": True,
            "recovered_service_startup": True,
            "post_cutover_health_compute_adapter": True,
            "irreversible_source_loss_cutover_acknowledged": True,
            "roll_forward_recovery": True,
            "delete": False,
            "invoke": False,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_source_loss_recovery_plan_v2(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    incident = _as_mapping(plan.get("incident"))
    candidate = _as_mapping(plan.get("candidate"))
    archive = _as_mapping(plan.get("source_loss_evidence_archive"))
    canary = _as_mapping(plan.get("canary_contract"))
    target_root = str(_as_mapping(plan.get("target")).get("target_root") or "")
    actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    if incident.get("previous_runtime_restore_supported") is not False:
        blockers.append("previous_runtime_restore_must_be_false")
    if incident.get("empty_tree_restore_is_rollback") is not False:
        blockers.append("empty_tree_restore_must_not_be_rollback")
    if not incident.get("irreversible_cutover_acknowledgement_required"):
        blockers.append("irreversible_acknowledgement_required")
    for path_key, path_value in {
        "candidate_path": str(candidate.get("candidate_path") or ""),
        "archive_path": str(archive.get("archive_path") or ""),
    }.items():
        if not path_value or _path_has_placeholder(path_value):
            blockers.append(f"{path_key}_not_concrete")
    if not canary.get("canary_port") or not canary.get("argv"):
        blockers.append("canary_contract_missing")
    if any(str(action.get("candidate_path") or "").startswith(target_root + "/") for action in actions):
        blockers.append("in_place_target_write_detected")
    if any("target_path" in action for action in actions):
        blockers.append("target_path_actions_forbidden_before_cutover")
    if not actions:
        blockers.append("file_actions_missing")
    if not _as_mapping(plan.get("launch_authority")).get("valid"):
        blockers.append("launch_authority_invalid")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_loss_recovery_plan_v2_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "action_count": len(actions),
        "previous_runtime_restore_supported": incident.get("previous_runtime_restore_supported"),
        "cutover_semantics": incident.get("cutover_semantics"),
    }


def build_full_p2s_rebase_plan_v2(recovery_plan: Mapping[str, Any]) -> dict[str, Any]:
    pointer = load_pointer()
    active_root = Path(str(pointer.get("active_path") or ""))
    active_inventory = inventory_root("active_sandbox", active_root, root_role="active_sandbox")
    active_descriptor = descriptor_from_inventory(active_inventory, scope="p2s_active_safe_tree")
    recovered_descriptor = _as_mapping(_as_mapping(recovery_plan.get("candidate")).get("candidate_descriptor"))
    p2s_id = stable_id("full_p2s_rebase", str(recovery_plan.get("canonical_sha256") or ""))
    baseline_id = f"risk-fraud-rebase-{p2s_id}"
    stage_root = Path(f"/sdb/dlut/sandbox/prod-baselines/{baseline_id}/fixed-dag-services")
    candidate_path = Path(f"/sdb/dlut/sandbox/r8-13a/services/.prod-candidate-{baseline_id}")
    archive_path = Path(f"/sdb/dlut/sandbox/r8-13a/services/prod-pre-{baseline_id}")
    active_files = [
        record
        for record in active_inventory.get("files") or []
        if isinstance(record, Mapping) and record.get("include")
    ]
    recovered_actions = [
        {
            "action_id": stable_id("p2s-risk", p2s_id, action["relative_path"], action["source_sha256"]),
            "operation": "copy_recovered_prod_file_to_stage",
            "relative_path": f"risk_financial_fraud/{action['relative_path']}",
            "source_after_recovery_path": str(Path(str(_as_mapping(recovery_plan.get("target")).get("target_root") or "")) / action["relative_path"]),
            "stage_path": str(stage_root / "risk_financial_fraud" / action["relative_path"]),
            "sha256": action["source_sha256"],
        }
        for action in recovery_plan.get("file_actions") or []
        if isinstance(action, Mapping)
    ]
    clone_actions = [
        {
            "action_id": stable_id("p2s-clone", p2s_id, str(record.get("relative_path") or ""), str(record.get("sha256") or "")),
            "operation": "clone_current_active_file_to_stage",
            "relative_path": str(record.get("relative_path") or ""),
            "source_active_path": str(active_root / str(record.get("relative_path") or "")),
            "stage_path": str(stage_root / str(record.get("relative_path") or "")),
            "sha256": str(record.get("sha256") or ""),
        }
        for record in active_files
    ]
    materialization_manifest = clone_actions + recovered_actions
    registry = load_static_registry()
    agent_dispositions = [
        {
            "agent_id": str(agent.get("agent_id") or ""),
            "disposition": "replace_from_recovered_prod" if str(agent.get("agent_id") or "") == RISK_FRAUD_AGENT_ID else "clone_from_current_active_baseline",
        }
        for agent in registry.get("agents") or []
        if isinstance(agent, Mapping)
    ]
    expected_descriptor = {
        "schema_version": "agent_sync_digest_descriptor_v1",
        "algorithm": "sha256",
        "digest": canonical_sha256({"active": active_descriptor, "recovered": recovered_descriptor, "manifest": materialization_manifest}),
        "scope": "p2s_stage_projection",
        "root_role": "stage",
        "include_profile": "source_bearing_default",
        "relative_path_basis": "posix",
        "entry_contract_version": "sync_inventory_root_v1",
        "file_count": len(materialization_manifest),
    }
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_full_p2s_rebase_plan_v2",
        "tool_version": R2X_TOOL_VERSION,
        "plan_id": p2s_id,
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "recovery_plan_gate": {
            "recovery_plan_id": recovery_plan.get("plan_id"),
            "recovery_plan_sha256": recovery_plan.get("canonical_sha256"),
            "actual_prod_after_must_equal": recovered_descriptor,
        },
        "baseline_id": baseline_id,
        "stage_root": str(stage_root),
        "stage_root_expected_missing": True,
        "activation_candidate_path": str(candidate_path),
        "activation_archive_path": str(archive_path),
        "active_preconditions": {
            "active_path": pointer.get("active_path"),
            "pointer_sha256": pointer.get("pointer_sha256"),
            "active_descriptor": active_descriptor,
        },
        "agent_dispositions": agent_dispositions,
        "materialization_manifest": materialization_manifest,
        "expected_full_stage_descriptor": expected_descriptor,
        "risk_fraud_expected_file_count": len(recovered_actions),
        "stage_approval_request": {
            "status": "awaiting_machine_approval_after_recovery",
            "stage_requested": True,
            "verify_requested": True,
            "activate_requested": False,
            "rollback_requested": False,
            "requested_action_ids": [action["action_id"] for action in materialization_manifest],
        },
        "activation_request_template": {
            "status": "blocked_pending_real_stage_closeout",
            "stage_requested": False,
            "verify_requested": True,
            "activate_requested": True,
            "rollback_requested": True,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_full_p2s_rebase_plan_v2(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    materialization = [action for action in plan.get("materialization_manifest") or [] if isinstance(action, Mapping)]
    dispositions = [row for row in plan.get("agent_dispositions") or [] if isinstance(row, Mapping)]
    for key in ["stage_root", "activation_candidate_path", "activation_archive_path"]:
        value = str(plan.get(key) or "")
        if not value or _path_has_placeholder(value):
            blockers.append(f"{key}_not_concrete")
    if len(dispositions) != 26:
        blockers.append("agent_disposition_count_not_26")
    if not materialization:
        blockers.append("materialization_manifest_missing")
    if int(plan.get("risk_fraud_expected_file_count") or 0) != 67:
        blockers.append("risk_fraud_file_count_not_67")
    stage_request = _as_mapping(plan.get("stage_approval_request"))
    if stage_request.get("activate_requested") or stage_request.get("rollback_requested"):
        blockers.append("stage_approval_not_split")
    if len(stage_request.get("requested_action_ids") or []) != len(materialization):
        blockers.append("stage_request_action_scope_mismatch")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_full_p2s_rebase_plan_v2_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "physical_action_count": len(materialization),
        "agent_disposition_count": len(dispositions),
        "projected_file_count": int(_as_mapping(plan.get("expected_full_stage_descriptor")).get("file_count") or 0),
        "risk_fraud_projected_file_count": int(plan.get("risk_fraud_expected_file_count") or 0),
    }


def reselect_first_candidate() -> dict[str, Any]:
    candidates = [
        {
            "candidate_id": "candidate_financial_data_service_fixed_dag_compute_material",
            "agent_id": "financial_data_service",
            "risk_class": "B_protocol_wrapper",
            "files": ["pg-ops-agent/backend/app/main.py", "pg-ops-agent/backend/tests/test_fixed_dag_compute.py"],
            "process_required": True,
            "live_required": True,
            "delete_required": False,
            "superseded": True,
            "selection_status": "rejected_superseded_runtime_wrapper",
            "patch_path": str(FINANCIAL_PATCH),
        },
        {
            "candidate_id": MARKET_CANDIDATE_ID,
            "agent_id": "market_capital_flow_chip",
            "risk_class": "A_docs_tests_material",
            "files": ["tests/test_domain_contract_v1.py"],
            "process_required": False,
            "live_required": False,
            "delete_required": False,
            "superseded": False,
            "already_in_prod": False,
            "owner_boundary": "user_sandbox",
            "patch_path": str(MARKET_PATCH),
            "patch_sha256": file_sha256(MARKET_PATCH) if MARKET_PATCH.exists() else "",
            "reverse_patch_path": str(MARKET_REVERSE_PATCH),
            "reverse_patch_sha256": file_sha256(MARKET_REVERSE_PATCH) if MARKET_REVERSE_PATCH.exists() else "",
            "focused_tests": ["tests/test_domain_contract_v1.py"],
            "rollback_ready": MARKET_REVERSE_PATCH.exists(),
            "selection_status": "selected",
        },
        {
            "candidate_id": "candidate_macro_commodity_pricing_protocol_wrapper",
            "agent_id": "macro_commodity_pricing",
            "risk_class": "B_protocol_wrapper",
            "files": ["agent协议/fixed_dag_compute.py", "agent协议/service.py", "agent协议/tests/test_compute_contract.py", "index.html"],
            "process_required": True,
            "live_required": True,
            "delete_required": False,
            "superseded": False,
            "selection_status": "rejected_higher_risk_protocol_wrapper",
            "patch_path": str(MACRO_PATCH),
        },
    ]
    selected = next(candidate for candidate in candidates if candidate["candidate_id"] == MARKET_CANDIDATE_ID)
    return {
        "schema_version": "agent_sync_5a_r2x_candidate_reselection_v1",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "selected_candidate_id": selected["candidate_id"],
        "selected_candidate": selected,
        "valid": selected["risk_class"] == "A_docs_tests_material" and not selected["process_required"] and not selected["live_required"],
        "blockers": [],
    }


def build_projected_experiment_manifest_v2(candidate: Mapping[str, Any], p2s_plan: Mapping[str, Any]) -> dict[str, Any]:
    experiment_id = stable_id("first_nonzero", str(candidate.get("agent_id") or ""), str(candidate.get("patch_sha256") or ""))
    manifest: dict[str, Any] = {
        "schema_version": "agent_sync_projected_experiment_manifest_v2",
        "experiment_id": experiment_id,
        "workspace_root": f"/sdb/dlut/sandbox/experiments/{experiment_id}/fixed-dag-services",
        "base_baseline_id": p2s_plan.get("baseline_id"),
        "base_descriptor": p2s_plan.get("expected_full_stage_descriptor"),
        "change_unit": {
            "change_unit_id": stable_id("cu", str(candidate.get("candidate_id") or ""), str(candidate.get("patch_sha256") or "")),
            "candidate_id": candidate.get("candidate_id"),
            "agent_id": candidate.get("agent_id"),
            "risk_class": candidate.get("risk_class"),
            "files": candidate.get("files"),
            "patch_sha256": candidate.get("patch_sha256"),
            "rollback_patch_sha256": candidate.get("reverse_patch_sha256"),
            "process_required": candidate.get("process_required"),
            "live_required": candidate.get("live_required"),
        },
        "status": "projected_not_materialized",
        "canonical_sha256": "",
    }
    manifest["canonical_sha256"] = canonical_sha256(manifest)
    return manifest


def build_first_real_cycle_plan_v2(candidate: Mapping[str, Any], experiment: Mapping[str, Any], p2s_plan: Mapping[str, Any]) -> dict[str, Any]:
    s2p_action_id = stable_id("s2p", str(candidate.get("agent_id") or ""), ",".join(candidate.get("files") or []), str(candidate.get("patch_sha256") or ""))
    p2s_action_id = stable_id("p2s", str(candidate.get("agent_id") or ""), ",".join(candidate.get("files") or []), str(candidate.get("patch_sha256") or ""))
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_first_real_cycle_plan_v2",
        "cycle_id": stable_id("cycle", str(experiment.get("canonical_sha256") or "")),
        "experiment_id": experiment.get("experiment_id"),
        "experiment_sha256": experiment.get("canonical_sha256"),
        "baseline_id": p2s_plan.get("baseline_id"),
        "selected_change_unit": experiment.get("change_unit"),
        "s2p_plan": {
            "plan_id": stable_id("s2p_first", s2p_action_id),
            "action_ids": [s2p_action_id],
            "action_count": 1,
            "backup_required": True,
            "offline_tests_required": True,
            "process_required": candidate.get("process_required"),
            "live_required": candidate.get("live_required"),
            "delete_required": False,
        },
        "projected_prod_after_descriptor": {
            "schema_version": "agent_sync_digest_descriptor_v1",
            "algorithm": "sha256",
            "digest": canonical_sha256({"candidate": candidate, "base": p2s_plan.get("expected_full_stage_descriptor")}),
            "scope": "s2p_prod_inventory",
            "root_role": "prod_after_projection",
            "include_profile": "source_bearing_default",
            "relative_path_basis": "posix",
            "entry_contract_version": "first_real_cycle_plan_v2",
            "file_count": int(_as_mapping(p2s_plan.get("expected_full_stage_descriptor")).get("file_count") or 0),
        },
        "p2s_plan": {
            "plan_id": stable_id("p2s_first", p2s_action_id),
            "action_ids": [p2s_action_id],
            "action_count": 1,
            "stage_root": f"/sdb/dlut/sandbox/prod-baselines/{stable_id('first-cycle-p2s', p2s_action_id)}/fixed-dag-services",
            "activate_requested": True,
            "rollback_requested": True,
        },
        "strict_compensation": True,
        "canonical_sha256": "",
    }
    plan["s2p_plan"]["canonical_sha256"] = canonical_sha256(plan["s2p_plan"])
    plan["p2s_plan"]["canonical_sha256"] = canonical_sha256(plan["p2s_plan"])
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_first_real_cycle_plan_v2(plan: Mapping[str, Any]) -> dict[str, Any]:
    s2p = _as_mapping(plan.get("s2p_plan"))
    p2s = _as_mapping(plan.get("p2s_plan"))
    blockers: list[str] = []
    if int(s2p.get("action_count") or 0) <= 0:
        blockers.append("s2p_actions_missing")
    if int(p2s.get("action_count") or 0) <= 0:
        blockers.append("p2s_actions_missing")
    if s2p.get("delete_required"):
        blockers.append("delete_forbidden")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_first_real_cycle_plan_v2_validation",
        "cycle_id": plan.get("cycle_id", ""),
        "cycle_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "s2p_action_count": int(s2p.get("action_count") or 0),
        "p2s_action_count": int(p2s.get("action_count") or 0),
    }


def build_final_compound_execution_plan_v2(
    recovery_plan: Mapping[str, Any],
    p2s_plan: Mapping[str, Any],
    experiment: Mapping[str, Any],
    cycle_plan: Mapping[str, Any],
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_final_compound_execution_plan_v2",
        "tool_version": R2X_TOOL_VERSION,
        "compound_plan_id": stable_id(
            "compound_v2",
            str(recovery_plan.get("canonical_sha256") or ""),
            str(p2s_plan.get("canonical_sha256") or ""),
            str(cycle_plan.get("canonical_sha256") or ""),
        ),
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "mode": "strict_after_state_gates",
        "phases": [
            {
                "phase": "risk_fraud_source_loss_recovery",
                "plan_id": recovery_plan.get("plan_id"),
                "plan_sha256": recovery_plan.get("canonical_sha256"),
                "action_ids": [action["action_id"] for action in recovery_plan.get("file_actions") or [] if isinstance(action, Mapping)],
                "projected_after_descriptor": _as_mapping(_as_mapping(recovery_plan.get("candidate")).get("candidate_descriptor")),
                "permissions": recovery_plan.get("requested_permissions"),
                "stop_on_failure": True,
            },
            {
                "phase": "risk_fraud_full_p2s_rebase",
                "plan_id": p2s_plan.get("plan_id"),
                "plan_sha256": p2s_plan.get("canonical_sha256"),
                "action_ids": [action["action_id"] for action in p2s_plan.get("materialization_manifest") or [] if isinstance(action, Mapping)],
                "projected_after_descriptor": p2s_plan.get("expected_full_stage_descriptor"),
                "requires_previous_actual_equals_projection": True,
                "stop_on_failure": True,
            },
            {
                "phase": "first_real_experiment_materialization",
                "experiment_id": experiment.get("experiment_id"),
                "experiment_sha256": experiment.get("canonical_sha256"),
                "requires_previous_actual_equals_projection": True,
                "stop_on_failure": True,
            },
            {
                "phase": "first_real_nonzero_publish_and_rebase",
                "cycle_id": cycle_plan.get("cycle_id"),
                "cycle_sha256": cycle_plan.get("canonical_sha256"),
                "requires_previous_actual_equals_projection": True,
                "stop_on_failure": True,
            },
        ],
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_final_compound_execution_plan_v2(plan: Mapping[str, Any]) -> dict[str, Any]:
    phases = [phase for phase in plan.get("phases") or [] if isinstance(phase, Mapping)]
    blockers: list[str] = []
    if len(phases) != 4:
        blockers.append("phase_count_not_4")
    if any(not phase.get("stop_on_failure") for phase in phases):
        blockers.append("phase_stop_condition_missing")
    if any(not phase.get("requires_previous_actual_equals_projection") for phase in phases[1:]):
        blockers.append("after_state_gate_missing")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_final_compound_execution_plan_v2_validation",
        "compound_plan_id": plan.get("compound_plan_id", ""),
        "compound_plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
    }


def build_final_compound_execution_approval_request_v2(plan: Mapping[str, Any], candidate: Mapping[str, Any], cycle_plan: Mapping[str, Any]) -> dict[str, Any]:
    phases = [phase for phase in plan.get("phases") or [] if isinstance(phase, Mapping)]
    recovery = phases[0] if phases else {}
    p2s = phases[1] if len(phases) > 1 else {}
    s2p = _as_mapping(cycle_plan.get("s2p_plan"))
    cycle_p2s = _as_mapping(cycle_plan.get("p2s_plan"))
    return {
        "schema_version": "agent_sync_final_compound_execution_approval_request_v2",
        "request_id": stable_id("compound_v2_request", str(plan.get("canonical_sha256") or "")),
        "status": "awaiting_machine_approval",
        "compound_plan_id": plan.get("compound_plan_id"),
        "compound_plan_sha256": plan.get("canonical_sha256"),
        "recovery": {
            "plan_id": recovery.get("plan_id"),
            "plan_sha256": recovery.get("plan_sha256"),
            "action_ids": recovery.get("action_ids", []),
            "candidate_materialization_requested": True,
            "shadow_canary_process_requested": True,
            "incumbent_health_compute_adapter_requested": True,
            "canary_health_compute_adapter_requested": True,
            "incumbent_graceful_stop_requested": True,
            "source_root_atomic_cutover_requested": True,
            "recovered_service_startup_requested": True,
            "post_cutover_health_compute_adapter_requested": True,
            "irreversible_source_loss_cutover_acknowledged": True,
            "roll_forward_recovery_requested": True,
            "delete_requested": False,
            "invoke_requested": False,
        },
        "p2s_rebase": {
            "plan_id": p2s.get("plan_id"),
            "plan_sha256": p2s.get("plan_sha256"),
            "stage_requested": True,
            "verify_requested": True,
            "activate_requested": True,
            "rollback_requested": True,
        },
        "experiment": {
            "materialize_requested": True,
            "validate_requested": True,
            "close_requested": True,
        },
        "first_cycle": {
            "backup_requested": True,
            "apply_requested": True,
            "offline_tests_requested": True,
            "process_requested": bool(candidate.get("process_required")),
            "live_requested": bool(candidate.get("live_required")),
            "s2p_rollback_requested": True,
            "p2s_stage_requested": True,
            "p2s_activate_requested": True,
            "p2s_rollback_requested": True,
            "owner_handoff_requested": False,
            "delete_requested": False,
            "s2p_action_ids": s2p.get("action_ids", []),
            "p2s_action_ids": cycle_p2s.get("action_ids", []),
        },
        "approval_id": "",
        "approved_at": "",
    }
