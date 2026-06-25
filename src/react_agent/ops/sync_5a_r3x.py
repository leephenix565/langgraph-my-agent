# ruff: noqa: D101, D102, D103
"""SYNC-OPS-5A-R3X launch-authority and final freeze contracts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from react_agent.ops.sync_5a_r1x import (
    RISK_FRAUD_AGENT_ID,
    RISK_FRAUD_HISTORICAL_ROOT,
    RISK_FRAUD_KNOWN_HASHES,
    RISK_FRAUD_PROD_ROOT,
)
from react_agent.ops.sync_5a_r2x import (
    DEFAULT_CANARY_PORT,
    SOURCE_LOSS_CUTOVER,
    SOURCE_LOSS_INCIDENT_CLASS,
    build_first_real_cycle_plan_v2,
    build_full_p2s_rebase_plan_v2,
    build_projected_experiment_manifest_v2,
    build_source_package_integrity,
    expires_utc,
    now_utc,
)
from react_agent.ops.sync_contracts import canonical_sha256, stable_id
from react_agent.ops.sync_inventory import inventory_root
from react_agent.ops.sync_process_launcher import (
    build_supervised_launcher_authority,
    validate_launch_authority,
)
from react_agent.ops.sync_s2p import descriptor_from_inventory

R3X_TOOL_VERSION = "sync_ops_5a_r3x_approved_launch_authority_final_freeze"
P2S_REFRESH = Path("/tmp/lma-prod-to-sandbox-agent-refresh-20260623T050419Z")
P2S_SENSITIVE = Path("/tmp/lma-p2s-sensitive-closure-20260623T060342Z")
CANONICAL_RISK_FRAUD_ARGV = ["/usr/bin/python3.14", "-u", "-m", "app.main"]


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _read_json(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _path_has_placeholder(value: str) -> bool:
    return "<" in value or ">" in value


def _risk_fraud_manifest_rows() -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for path in (P2S_REFRESH / "file_sync_manifest.json", P2S_SENSITIVE / "final_file_sync_manifest.json"):
        if not path.exists():
            continue
        for row in _read_json(path):
            if isinstance(row, Mapping) and row.get("agent_id") == RISK_FRAUD_AGENT_ID:
                rows[str(row.get("relative_path") or "")] = row
    return rows


def build_source_package_provenance(source_root: Path = RISK_FRAUD_HISTORICAL_ROOT) -> dict[str, Any]:
    package = build_source_package_integrity(source_root)
    manifest_rows = _risk_fraud_manifest_rows()
    entries: list[dict[str, Any]] = []
    unresolved: list[str] = []
    direct_lineage = {
        **RISK_FRAUD_KNOWN_HASHES,
        "app/main.py": "db147a2417e33edf606adb108d1e906f11dc55982490228e203090764011023b",
    }
    for item in package["manifest"]:
        rel = str(item["relative_path"])
        sha = str(item["sha256"])
        row = manifest_rows.get(rel)
        manifest_match = bool(row and row.get("prod_sha256") == sha and row.get("staged_sha256") == sha)
        accepted_match = direct_lineage.get(rel) == sha
        sources: list[str] = []
        if manifest_match:
            sources.append("prod_snapshot_provenance_at_20260623")
        if accepted_match:
            sources.append("accepted_bg_hash_provenance")
        classification = "exact_prod_baseline_manifest_provenance" if manifest_match else "accepted_bg_hash_provenance" if accepted_match else "unresolved"
        resolved = classification != "unresolved"
        if not resolved:
            unresolved.append(rel)
        entries.append(
            {
                "relative_path": rel,
                "sha256": sha,
                "authority_sources": sources,
                "prod_baseline_manifest_reference": {
                    "manifest_paths": [
                        str(P2S_REFRESH / "file_sync_manifest.json"),
                        str(P2S_SENSITIVE / "final_file_sync_manifest.json"),
                    ],
                    "prod_source_path": str(row.get("prod_source_path") or "") if row else "",
                    "prod_sha256": str(row.get("prod_sha256") or "") if row else "",
                    "staged_sha256": str(row.get("staged_sha256") or "") if row else "",
                    "matches": manifest_match,
                    "snapshot": "2026-06-23",
                },
                "accepted_lineage_reference": {
                    "known_hash": direct_lineage.get(rel, ""),
                    "matches": accepted_match,
                },
                "owner_reference": {
                    "classification": "owner_authority_unresolved_no_patch",
                    "matches": False,
                },
                "classification": classification,
                "resolved": resolved,
            }
        )
    payload: dict[str, Any] = {
        "schema_version": "agent_sync_source_package_provenance_v1",
        "source_root": str(source_root),
        "source_descriptor": package["descriptor"],
        "manifest_sha256": package["manifest_sha256"],
        "source_file_count": package["file_count"],
        "entries": entries,
        "resolved_count": sum(1 for entry in entries if entry["resolved"]),
        "unresolved_count": len(unresolved),
        "manifest_hash_match_count": sum(1 for entry in entries if entry["prod_baseline_manifest_reference"]["matches"]),
        "accepted_direct_lineage_count": sum(1 for entry in entries if entry["accepted_lineage_reference"]["matches"]),
        "classification_counts": {
            "exact_prod_baseline_manifest_provenance": sum(1 for entry in entries if entry["classification"] == "exact_prod_baseline_manifest_provenance"),
            "accepted_bg_hash_provenance_overlap": sum(1 for entry in entries if entry["accepted_lineage_reference"]["matches"]),
            "unresolved": len(unresolved),
        },
        "secret_findings": package["secret_findings"],
        "runtime_data_model_backup_noise_count": 0,
        "valid": package["file_count"] == 67 and not unresolved and not package["secret_findings"],
        "blockers": [f"unresolved_provenance:{rel}" for rel in unresolved],
        "canonical_sha256": "",
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def validate_source_package_provenance(provenance: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if int(provenance.get("source_file_count") or 0) != 67:
        blockers.append("source_file_count_not_67")
    if int(provenance.get("resolved_count") or 0) != 67:
        blockers.append("resolved_count_not_67")
    if int(provenance.get("unresolved_count") or 0) != 0:
        blockers.append("unresolved_provenance")
    if int(provenance.get("manifest_hash_match_count") or 0) != 67:
        blockers.append("manifest_hash_match_count_not_67")
    if provenance.get("secret_findings"):
        blockers.append("secret_findings_present")
    if str(provenance.get("canonical_sha256") or "") != canonical_sha256(provenance):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_package_provenance_v1_validation",
        "valid": not blockers,
        "blockers": blockers,
        "resolved_count": int(provenance.get("resolved_count") or 0),
        "unresolved_count": int(provenance.get("unresolved_count") or 0),
        "accepted_direct_lineage_count": int(provenance.get("accepted_direct_lineage_count") or 0),
        "baseline_manifest_provenance_count": int(provenance.get("manifest_hash_match_count") or 0),
    }


def build_environment_reference_metadata(target_root: Path = RISK_FRAUD_PROD_ROOT, source_root: Path = RISK_FRAUD_HISTORICAL_ROOT) -> dict[str, Any]:
    config_text = (source_root / "app/config.py").read_text(encoding="utf-8", errors="replace")
    target_env = target_root / ".env"
    return {
        "schema_version": "agent_sync_environment_reference_metadata_v1",
        "classification": "approved_secure_launcher_env_reference",
        "service_self_loads_dotenv": "load_dotenv(SERVICE_ROOT / \".env\")" in config_text,
        "dotenv_reference_path": str(target_env),
        "env_reference_exists": target_env.exists(),
        "env_reference_type": "regular_file" if target_env.is_file() and not target_env.is_symlink() else "missing",
        "env_reference_mode": oct(target_env.stat().st_mode & 0o777) if target_env.exists() else "",
        "env_reference_realpath": str(target_env.resolve()) if target_env.exists() else "",
        "launcher_reads_env_values": False,
        "control_plane_observes_env_values": False,
        "proc_environ_read": False,
        "secure_environment_reference_required": False,
        "bounded_public_overrides": {
            "production": {"APP_HOST": "0.0.0.0", "APP_PORT": "10013"},
            "canary": {"APP_HOST": "127.0.0.1", "APP_PORT": "11013"},
        },
        "production_port_source": "approved bounded APP_HOST/APP_PORT override 0.0.0.0:10013",
        "canary_port_source": "approved bounded APP_HOST/APP_PORT override 127.0.0.1:11013",
        "required_variable_names": [
            "APP_HOST",
            "APP_PORT",
            "CSMAR_FEATURE_SOURCE_PATH",
            "CSMAR_FINANCIAL_SOURCE_DIR",
            "DATABASE_PATH",
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_BASE_URL",
            "DEEPSEEK_MODEL",
            "FEATURE_DATA_PATH",
            "MODEL_ARTIFACT_PATH",
            "MONITOR_INTERVAL_SECONDS",
            "TS_NEWS_API_URL",
            "TUSHARE_QUERY_TIMEOUT_SECONDS",
            "TUSHARE_TOKEN",
        ],
        "valid": True,
        "blockers": [],
    }


def build_risk_fraud_launch_authority(
    *,
    target_root: Path = RISK_FRAUD_PROD_ROOT,
    canary_port: int = DEFAULT_CANARY_PORT,
) -> dict[str, Any]:
    return build_supervised_launcher_authority(
        service_unit_id=RISK_FRAUD_AGENT_ID,
        executable="/usr/bin/python3.14",
        argv=CANONICAL_RISK_FRAUD_ARGV,
        cwd=str(target_root),
        log_dir="/sdb/dlut/ops-artifacts/agent-sync/runs/source-loss-recovery-v3-risk-financial-fraud/process/logs",
        state_dir="/sdb/dlut/ops-artifacts/agent-sync/runs/source-loss-recovery-v3-risk-financial-fraud/process/state",
        allowed_port_overrides=[10013, canary_port],
        environment_reference_path="",
        allowed_environment_override_names=["APP_HOST", "APP_PORT"],
        allowed_executable_roots=["/usr/bin"],
        allowed_cwd_roots=["/sdb/dlut/prod"],
    )


def build_source_loss_recovery_plan_v3(
    *,
    pid: str,
    start_ticks: str,
    cwd: str,
    exe: str,
    argv: list[str],
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    target_root: Path = RISK_FRAUD_PROD_ROOT,
    canary_port: int = DEFAULT_CANARY_PORT,
) -> dict[str, Any]:
    provenance = build_source_package_provenance(source_root)
    launch = build_risk_fraud_launch_authority(target_root=target_root, canary_port=canary_port)
    environment = build_environment_reference_metadata(target_root=target_root, source_root=source_root)
    source_inventory = inventory_root(RISK_FRAUD_AGENT_ID, source_root, root_role="source_loss_recovery_package")
    descriptor = descriptor_from_inventory(source_inventory, scope="transaction_source_tree")
    plan_id = stable_id("source_loss_recovery_v3", provenance["canonical_sha256"], launch["canonical_sha256"], str(canary_port))
    candidate_path = target_root.parent / f".agent-sync-risk-fraud-recovery-{plan_id}"
    archive_path = target_root.parent / f".agent-sync-risk-fraud-source-loss-evidence-{plan_id}"
    actions = [
        {
            "action_id": stable_id("slrv3", plan_id, entry["relative_path"], entry["sha256"]),
            "operation": "materialize_to_sibling_candidate",
            "source_path": str(source_root / str(entry["relative_path"])),
            "candidate_path": str(candidate_path / str(entry["relative_path"])),
            "relative_path": entry["relative_path"],
            "source_sha256": entry["sha256"],
        }
        for entry in provenance["entries"]
    ]
    request_fixture = {
        "schema_version": "external_agent_compute_v0",
        "agent_id": RISK_FRAUD_AGENT_ID,
        "target": "600519.SH",
        "as_of": "2024-12-31",
    }
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_recovery_plan_v3",
        "tool_version": R3X_TOOL_VERSION,
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
        "source_provenance": {
            "provenance_sha256": provenance["canonical_sha256"],
            "resolved_count": provenance["resolved_count"],
            "unresolved_count": provenance["unresolved_count"],
        },
        "source_authority": {
            "root": str(source_root),
            "descriptor": descriptor,
            "manifest_sha256": provenance["manifest_sha256"],
        },
        "target": {
            "target_root": str(target_root),
            "target_expected_empty_source_tree": True,
            "projected_target_after_descriptor": descriptor,
        },
        "candidate": {
            "candidate_path": str(candidate_path),
            "candidate_path_expected_missing": True,
            "candidate_descriptor": descriptor,
            "no_hardlinks": True,
        },
        "source_loss_evidence_archive": {
            "archive_path": str(archive_path),
            "archive_path_expected_missing": True,
            "preserve_after_cutover": True,
        },
        "launch_authority": launch,
        "launch_authority_sha256": launch["canonical_sha256"],
        "environment_contract": environment,
        "environment_contract_sha256": canonical_sha256(environment),
        "canary_contract": {
            "canary_port": canary_port,
            "production_port": 10013,
            "candidate_cwd": str(candidate_path),
            "argv": CANONICAL_RISK_FRAUD_ARGV,
        "environment_overrides": {"APP_HOST": "127.0.0.1", "APP_PORT": str(canary_port)},
        "production_environment_overrides": {"APP_HOST": "0.0.0.0", "APP_PORT": "10013"},
            "health_url": f"http://127.0.0.1:{canary_port}/health",
            "compute_url": f"http://127.0.0.1:{canary_port}/v1/agent/compute",
            "invoke_forbidden": True,
            "raw_response_persistence_forbidden": True,
            "request_fixture_sha256": canonical_sha256(request_fixture),
        },
        "process_identity_precondition": {
            "port": 10013,
            "pid": pid,
            "start_ticks": start_ticks,
            "cwd": cwd,
            "exe": exe,
            "argv": argv,
            "pid_reuse_protection": True,
        },
        "file_actions": actions,
        "offline_tests": ["tests/test_report_material.py", "tests/test_compute_core.py", "tests/test_protocol_contract.py"],
        "cutover_sequence": ["precheck", "candidate", "shadow_canary", "incumbent_capture", "final_cutover_precheck", "cutover", "settle"],
        "roll_forward_recovery": {
            "restore_empty_tree_forbidden": True,
            "post_stop_recovery": "roll_forward_to_verified_candidate_or_manual_intervention",
            "sigkill_allowed": False,
        },
        "requested_permissions": {
            "candidate_materialization": True,
            "source_provenance_use": True,
            "secure_environment_reference_use": False,
            "shadow_canary_start": True,
            "shadow_canary_stop": True,
            "incumbent_health": True,
            "incumbent_compute": True,
            "incumbent_adapter": True,
            "canary_health": True,
            "canary_compute": True,
            "canary_adapter": True,
            "incumbent_sigterm": True,
            "source_root_atomic_cutover": True,
            "recovered_production_start": True,
            "recovered_health_compute_adapter": True,
            "roll_forward_retry": True,
            "irreversible_source_loss_cutover_acknowledged": True,
            "delete": False,
            "invoke": False,
            "sigkill": False,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_source_loss_recovery_plan_v3(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    launch = _as_mapping(plan.get("launch_authority"))
    launch_validation = validate_launch_authority(launch)
    env = _as_mapping(plan.get("environment_contract"))
    incident = _as_mapping(plan.get("incident"))
    candidate = _as_mapping(plan.get("candidate"))
    archive = _as_mapping(plan.get("source_loss_evidence_archive"))
    provenance = _as_mapping(plan.get("source_provenance"))
    if launch_validation["valid"] is not True:
        blockers.append("launch_authority_invalid")
    for nested in ("log_contract", "state_contract"):
        for value in _as_mapping(launch.get(nested)).values():
            if isinstance(value, str) and _path_has_placeholder(value):
                blockers.append(f"{nested}_contains_placeholder")
    if int(provenance.get("resolved_count") or 0) != 67 or int(provenance.get("unresolved_count") or 0) != 0:
        blockers.append("source_provenance_not_resolved")
    if env.get("control_plane_observes_env_values") or env.get("proc_environ_read"):
        blockers.append("environment_value_access_forbidden")
    if incident.get("previous_runtime_restore_supported") is not False:
        blockers.append("previous_runtime_restore_must_be_false")
    if incident.get("empty_tree_restore_is_rollback") is not False:
        blockers.append("empty_tree_restore_must_not_be_rollback")
    for key, value in {
        "candidate_path": str(candidate.get("candidate_path") or ""),
        "archive_path": str(archive.get("archive_path") or ""),
    }.items():
        if not value or _path_has_placeholder(value):
            blockers.append(f"{key}_not_concrete")
    if len(actions) != 67:
        blockers.append("file_action_count_not_67")
    if any("target_path" in action for action in actions):
        blockers.append("in_place_target_write_detected")
    permissions = _as_mapping(plan.get("requested_permissions"))
    if permissions.get("delete") or permissions.get("invoke") or permissions.get("sigkill"):
        blockers.append("forbidden_permission_requested")
    if not permissions.get("irreversible_source_loss_cutover_acknowledged"):
        blockers.append("irreversible_ack_missing")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_loss_recovery_plan_v3_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "action_count": len(actions),
        "launch_authority_sha256": plan.get("launch_authority_sha256", ""),
        "provenance_resolved_count": int(provenance.get("resolved_count") or 0),
    }


def build_full_p2s_rebase_plan_v3(recovery_plan_v3: Mapping[str, Any]) -> dict[str, Any]:
    shim: dict[str, Any] = {
        "plan_id": recovery_plan_v3.get("plan_id"),
        "canonical_sha256": recovery_plan_v3.get("canonical_sha256"),
        "candidate": recovery_plan_v3.get("candidate"),
        "target": recovery_plan_v3.get("target"),
        "file_actions": recovery_plan_v3.get("file_actions"),
    }
    plan = build_full_p2s_rebase_plan_v2(shim)
    plan["schema_version"] = "agent_sync_full_p2s_rebase_plan_v3"
    plan["tool_version"] = R3X_TOOL_VERSION
    plan["recovery_plan_gate"]["recovery_schema_version"] = "agent_sync_source_loss_recovery_plan_v3"
    plan["canonical_sha256"] = ""
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_full_p2s_rebase_plan_v3(plan: Mapping[str, Any]) -> dict[str, Any]:
    from react_agent.ops.sync_5a_r2x import validate_full_p2s_rebase_plan_v2

    shim = dict(plan)
    shim["schema_version"] = "agent_sync_full_p2s_rebase_plan_v2"
    shim["canonical_sha256"] = canonical_sha256(shim)
    base = validate_full_p2s_rebase_plan_v2(shim)
    blockers = list(base["blockers"])
    if plan.get("schema_version") != "agent_sync_full_p2s_rebase_plan_v3":
        blockers.append("schema_version_not_v3")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_full_p2s_rebase_plan_v3_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "physical_action_count": base["physical_action_count"],
        "agent_disposition_count": base["agent_disposition_count"],
        "projected_file_count": base["projected_file_count"],
        "risk_fraud_projected_file_count": base["risk_fraud_projected_file_count"],
    }


def build_projected_experiment_manifest_v3(candidate: Mapping[str, Any], p2s_plan_v3: Mapping[str, Any]) -> dict[str, Any]:
    manifest = build_projected_experiment_manifest_v2(candidate, p2s_plan_v3)
    manifest["schema_version"] = "agent_sync_projected_experiment_manifest_v3"
    manifest["tool_version"] = R3X_TOOL_VERSION
    manifest["canonical_sha256"] = ""
    manifest["canonical_sha256"] = canonical_sha256(manifest)
    return manifest


def build_first_real_cycle_plan_v3(candidate: Mapping[str, Any], experiment: Mapping[str, Any], p2s_plan_v3: Mapping[str, Any]) -> dict[str, Any]:
    plan = build_first_real_cycle_plan_v2(candidate, experiment, p2s_plan_v3)
    plan["schema_version"] = "agent_sync_first_real_cycle_plan_v3"
    plan["tool_version"] = R3X_TOOL_VERSION
    plan["canonical_sha256"] = ""
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_first_real_cycle_plan_v3(plan: Mapping[str, Any]) -> dict[str, Any]:
    s2p = _as_mapping(plan.get("s2p_plan"))
    p2s = _as_mapping(plan.get("p2s_plan"))
    blockers: list[str] = []
    if int(s2p.get("action_count") or 0) != 1:
        blockers.append("s2p_action_count_not_1")
    if int(p2s.get("action_count") or 0) != 1:
        blockers.append("p2s_action_count_not_1")
    if s2p.get("process_required") or s2p.get("live_required") or s2p.get("delete_required"):
        blockers.append("candidate_permissions_not_low_risk")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_first_real_cycle_plan_v3_validation",
        "cycle_id": plan.get("cycle_id", ""),
        "cycle_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "s2p_action_count": int(s2p.get("action_count") or 0),
        "p2s_action_count": int(p2s.get("action_count") or 0),
    }


def build_final_compound_execution_plan_v3(
    recovery: Mapping[str, Any],
    p2s: Mapping[str, Any],
    experiment: Mapping[str, Any],
    cycle: Mapping[str, Any],
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_final_compound_execution_plan_v3",
        "tool_version": R3X_TOOL_VERSION,
        "compound_plan_id": stable_id(
            "compound_v3",
            str(recovery.get("canonical_sha256") or ""),
            str(p2s.get("canonical_sha256") or ""),
            str(cycle.get("canonical_sha256") or ""),
        ),
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "mode": "strict_after_state_gates",
        "phases": [
            {
                "phase": "risk_fraud_source_loss_recovery_v3",
                "plan_id": recovery.get("plan_id"),
                "plan_sha256": recovery.get("canonical_sha256"),
                "input_descriptor": _as_mapping(recovery.get("target")),
                "projected_after_descriptor": _as_mapping(recovery.get("target")).get("projected_target_after_descriptor"),
                "action_ids": [action["action_id"] for action in recovery.get("file_actions") or [] if isinstance(action, Mapping)],
                "requested_permissions": recovery.get("requested_permissions"),
                "roll_forward": recovery.get("roll_forward_recovery"),
                "stop_on_failure": True,
            },
            {
                "phase": "risk_fraud_full_p2s_rebase",
                "plan_id": p2s.get("plan_id"),
                "plan_sha256": p2s.get("canonical_sha256"),
                "input_descriptor": _as_mapping(p2s.get("recovery_plan_gate")).get("actual_prod_after_must_equal"),
                "projected_after_descriptor": p2s.get("expected_full_stage_descriptor"),
                "action_ids": [action["action_id"] for action in p2s.get("materialization_manifest") or [] if isinstance(action, Mapping)],
                "requested_permissions": {"stage": True, "verify": True, "activate": True, "rollback": True},
                "requires_previous_actual_equals_projection": True,
                "stop_on_failure": True,
            },
            {
                "phase": "market_capital_flow_chip_experiment_materialization",
                "experiment_id": experiment.get("experiment_id"),
                "experiment_sha256": experiment.get("canonical_sha256"),
                "input_descriptor": experiment.get("base_descriptor"),
                "projected_after_descriptor": {"digest": experiment.get("canonical_sha256"), "scope": "s2p_workspace_inventory"},
                "requires_previous_actual_equals_projection": True,
                "stop_on_failure": True,
            },
            {
                "phase": "first_real_nonzero_publish_and_rebase",
                "cycle_id": cycle.get("cycle_id"),
                "cycle_sha256": cycle.get("canonical_sha256"),
                "input_descriptor": cycle.get("baseline_id"),
                "projected_after_descriptor": cycle.get("projected_prod_after_descriptor"),
                "requires_previous_actual_equals_projection": True,
                "stop_on_failure": True,
            },
        ],
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_final_compound_execution_plan_v3(plan: Mapping[str, Any]) -> dict[str, Any]:
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
        "schema_version": "agent_sync_final_compound_execution_plan_v3_validation",
        "compound_plan_id": plan.get("compound_plan_id", ""),
        "compound_plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
    }


def build_final_compound_execution_approval_request_v3(
    *,
    compound: Mapping[str, Any],
    recovery: Mapping[str, Any],
    p2s: Mapping[str, Any],
    experiment: Mapping[str, Any],
    cycle: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "schema_version": "agent_sync_final_compound_execution_approval_request_v3",
        "request_id": stable_id("compound_v3_request", str(compound.get("canonical_sha256") or "")),
        "status": "awaiting_machine_approval",
        "final_head_sha256": "",
        "source_provenance_sha256": provenance.get("canonical_sha256"),
        "launch_authority_sha256": recovery.get("launch_authority_sha256"),
        "environment_contract_sha256": recovery.get("environment_contract_sha256"),
        "recovery_plan_id": recovery.get("plan_id"),
        "recovery_plan_sha256": recovery.get("canonical_sha256"),
        "p2s_plan_id": p2s.get("plan_id"),
        "p2s_plan_sha256": p2s.get("canonical_sha256"),
        "experiment_id": experiment.get("experiment_id"),
        "experiment_sha256": experiment.get("canonical_sha256"),
        "first_cycle_id": cycle.get("cycle_id"),
        "first_cycle_sha256": cycle.get("canonical_sha256"),
        "compound_plan_id": compound.get("compound_plan_id"),
        "compound_plan_sha256": compound.get("canonical_sha256"),
        "approved_at": "",
        "approval_id": "",
        "requested_permissions": {
            "candidate_materialization": True,
            "source_provenance_use": True,
            "secure_environment_reference_use": False,
            "shadow_canary_start": True,
            "shadow_canary_stop": True,
            "incumbent_health": True,
            "incumbent_compute": True,
            "incumbent_adapter": True,
            "canary_health": True,
            "canary_compute": True,
            "canary_adapter": True,
            "incumbent_sigterm": True,
            "source_root_atomic_cutover": True,
            "recovered_production_start": True,
            "recovered_health_compute_adapter": True,
            "roll_forward_retry": True,
            "irreversible_source_loss_cutover_acknowledged": True,
            "p2s_stage": True,
            "p2s_verify": True,
            "p2s_activate": True,
            "p2s_rollback": True,
            "first_cycle_backup": True,
            "first_cycle_apply": True,
            "first_cycle_offline_tests": True,
            "first_cycle_process": False,
            "first_cycle_live": False,
            "delete": False,
            "invoke": False,
            "sigkill": False,
        },
        "action_ids": {
            "recovery": [action["action_id"] for action in recovery.get("file_actions") or [] if isinstance(action, Mapping)],
            "p2s": [action["action_id"] for action in p2s.get("materialization_manifest") or [] if isinstance(action, Mapping)],
            "first_cycle_s2p": _as_mapping(cycle.get("s2p_plan")).get("action_ids", []),
            "first_cycle_p2s": _as_mapping(cycle.get("p2s_plan")).get("action_ids", []),
        },
        "expires_at": compound.get("expires_at"),
        "canonical_sha256": "",
    }
    request["canonical_sha256"] = canonical_sha256(request)
    return request
