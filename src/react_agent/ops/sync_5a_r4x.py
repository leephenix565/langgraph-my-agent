# ruff: noqa: D101, D102, D103
"""SYNC-OPS-5A-R4X real shadow-canary and approval-chain contracts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from react_agent.fixed_dag_external_adapter import (
    map_external_compute_envelope_to_fixed_dag_object,
    validate_external_compute_envelope,
)
from react_agent.fixed_dag_external_health import validate_external_health_identity
from react_agent.ops.sync_5a_r1x import (
    RISK_FRAUD_AGENT_ID,
    RISK_FRAUD_HISTORICAL_ROOT,
    RISK_FRAUD_PROD_ROOT,
)
from react_agent.ops.sync_5a_r2x import (
    DEFAULT_CANARY_PORT,
    expires_utc,
    now_utc,
)
from react_agent.ops.sync_5a_r3x import (
    CANONICAL_RISK_FRAUD_ARGV,
    build_first_real_cycle_plan_v3,
    build_full_p2s_rebase_plan_v3,
    build_projected_experiment_manifest_v3,
    build_source_package_provenance,
    validate_full_p2s_rebase_plan_v3,
)
from react_agent.ops.sync_contracts import canonical_sha256, file_sha256, stable_id
from react_agent.ops.sync_inventory import inventory_root
from react_agent.ops.sync_process_launcher import (
    build_supervised_launcher_authority,
    validate_launch_authority,
)
from react_agent.ops.sync_s2p import descriptor_from_inventory

R4X_TOOL_VERSION = "sync_ops_5a_r4x_real_shadow_canary_approval_chain"
PRODUCTION_PORT = 10013
CANARY_PORT = DEFAULT_CANARY_PORT
STORE_ROOT = Path("/sdb/dlut/ops-artifacts/agent-sync")
BLOCKING_DEGRADATIONS = {
    "missing_model",
    "missing_model_artifact",
    "missing_database",
    "missing_data_source",
    "missing_required_path",
    "missing_required_credential",
    "provider_required",
    "contract_invalid",
    "adapter_failed",
}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path_has_placeholder(value: str) -> bool:
    return "<" in value or ">" in value


def _safe_top_level_keys(value: Any) -> list[str]:
    return sorted(str(key) for key in value.keys()) if isinstance(value, Mapping) else []


def _status_severity(status: str) -> int:
    normalized = str(status or "").strip().lower()
    if normalized in {"ok", "complete", "success", "healthy"}:
        return 3
    if normalized in {"partial", "degraded", "warning"}:
        return 2
    if normalized in {"error", "failed", "unhealthy"}:
        return 1
    return 0


def _status_class(status: str) -> str:
    severity = _status_severity(status)
    if severity >= 3:
        return "ok"
    if severity == 2:
        return "partial"
    if severity == 1:
        return "error"
    return "unknown"


def _warning_categories(items: Any) -> list[str]:
    categories: set[str] = set()
    if not isinstance(items, list):
        return []
    for item in items:
        text = str(item).lower()
        if "model" in text or "模型" in text or "hyformer" in text:
            categories.add("missing_model")
        if "feature" in text or "特征" in text or "snapshot" in text or "数据" in text:
            categories.add("missing_data_source")
        if "database" in text or "sqlite" in text:
            categories.add("missing_database")
        if "credential" in text or "api_key" in text or "token" in text or "凭据" in text:
            categories.add("missing_required_credential")
        if "provider" in text or "deepseek" in text or "tushare" in text:
            categories.add("provider_required")
    return sorted(categories)


def build_runtime_variable_matrix(source_root: Path = RISK_FRAUD_HISTORICAL_ROOT) -> dict[str, Any]:
    env_path = source_root / ".env"
    contracts = [
        {
            "name": "APP_HOST",
            "classification": "startup_required",
            "referenced_by": ["app/config.py", "app/main.py"],
            "read_at_import": True,
            "read_at_startup": True,
            "read_at_compute": False,
            "required": True,
            "optional": False,
            "safe_default_exists": True,
            "default_value_class": "loopback_host_default",
            "default_path": "",
            "default_path_exists": False,
            "default_path_type": "",
            "canary_required": True,
            "production_required": True,
            "secret_backed": False,
            "path_backed": False,
            "failure_behavior": "uses default 127.0.0.1 unless bounded override supplied",
            "degraded_behavior": "",
        },
        {
            "name": "APP_PORT",
            "classification": "startup_required",
            "referenced_by": ["app/config.py", "app/main.py"],
            "read_at_import": True,
            "read_at_startup": True,
            "read_at_compute": False,
            "required": True,
            "optional": False,
            "safe_default_exists": True,
            "default_value_class": "numeric_default_10013",
            "default_path": "",
            "default_path_exists": False,
            "default_path_type": "",
            "canary_required": True,
            "production_required": True,
            "secret_backed": False,
            "path_backed": False,
            "failure_behavior": "uses default 10013 unless bounded override supplied",
            "degraded_behavior": "",
        },
    ]
    path_defaults = {
        "MODEL_ARTIFACT_PATH": source_root / "data/model/financial_hyformer_txad_like.pt",
        "FEATURE_DATA_PATH": source_root / "data/features/dataset_cleaned.parquet",
        "CSMAR_FINANCIAL_SOURCE_DIR": source_root / "data/optional/csmar_raw/财务指标分析",
        "CSMAR_FEATURE_SOURCE_PATH": source_root / "data/optional/csmar_financial_features.parquet",
        "DATABASE_PATH": source_root / "data/fraud_agent.db",
    }
    for name, default in path_defaults.items():
        exists = default.exists()
        contracts.append(
            {
                "name": name,
                "classification": "path-backed" if name != "DATABASE_PATH" else "default-backed",
                "referenced_by": ["app/config.py", "app/storage.py", "app/agent/core.py", "app/modeling/predictor.py"],
                "read_at_import": True,
                "read_at_startup": name == "DATABASE_PATH",
                "read_at_compute": name != "DATABASE_PATH",
                "required": False,
                "optional": True,
                "safe_default_exists": name == "DATABASE_PATH",
                "default_value_class": "service_root_relative_path",
                "default_path": str(default),
                "default_path_exists": exists,
                "default_path_type": "directory" if default.is_dir() else "regular_file" if default.is_file() else "missing",
                "canary_required": False,
                "production_required": False,
                "secret_backed": False,
                "path_backed": True,
                "failure_behavior": "startup succeeds; health/compute report graceful degradation if absent"
                if name != "DATABASE_PATH"
                else "startup creates a local SQLite runtime database when path is writable",
                "degraded_behavior": "missing_data_source"
                if name not in {"MODEL_ARTIFACT_PATH", "DATABASE_PATH"}
                else "missing_model"
                if name == "MODEL_ARTIFACT_PATH"
                else "runtime_database_created",
            }
        )
    secret_defaults = {
        "DEEPSEEK_API_KEY": "empty_secret_default",
        "TUSHARE_TOKEN": "empty_secret_default",
    }
    for name, default_class in secret_defaults.items():
        contracts.append(
            {
                "name": name,
                "classification": "secret-backed",
                "referenced_by": ["app/config.py", "app/tools/deepseek.py", "app/tools/tushare_client.py"],
                "read_at_import": True,
                "read_at_startup": True,
                "read_at_compute": name in {"DEEPSEEK_API_KEY", "TUSHARE_TOKEN"},
                "required": False,
                "optional": True,
                "safe_default_exists": True,
                "default_value_class": default_class,
                "default_path": "",
                "default_path_exists": False,
                "default_path_type": "",
                "canary_required": False,
                "production_required": False,
                "secret_backed": True,
                "path_backed": False,
                "failure_behavior": "provider disabled; approved fixture does not require provider",
                "degraded_behavior": "provider_not_configured_optional",
            }
        )
    for name, default_class in {
        "DEEPSEEK_BASE_URL": "public_url_default",
        "DEEPSEEK_MODEL": "public_model_name_default",
        "TS_NEWS_API_URL": "public_url_default",
        "TUSHARE_QUERY_TIMEOUT_SECONDS": "numeric_default",
        "MONITOR_INTERVAL_SECONDS": "numeric_default_zero",
    }.items():
        contracts.append(
            {
                "name": name,
                "classification": "default-backed",
                "referenced_by": ["app/config.py"],
                "read_at_import": True,
                "read_at_startup": True,
                "read_at_compute": False,
                "required": False,
                "optional": True,
                "safe_default_exists": True,
                "default_value_class": default_class,
                "default_path": "",
                "default_path_exists": False,
                "default_path_type": "",
                "canary_required": False,
                "production_required": False,
                "secret_backed": False,
                "path_backed": False,
                "failure_behavior": "default used",
                "degraded_behavior": "",
            }
        )
    counts: dict[str, int] = {
        "startup_required": sum(1 for item in contracts if item["classification"] == "startup_required"),
        "compute_required": sum(1 for item in contracts if item.get("read_at_compute") and item.get("required")),
        "optional": sum(1 for item in contracts if item.get("optional")),
        "default_backed": sum(1 for item in contracts if item.get("safe_default_exists")),
        "secret_backed": sum(1 for item in contracts if item.get("secret_backed")),
        "path_backed": sum(1 for item in contracts if item.get("path_backed")),
    }
    matrix: dict[str, Any] = {
        "schema_version": "agent_sync_runtime_variable_matrix_v1",
        "service_unit_id": RISK_FRAUD_AGENT_ID,
        "source_root": str(source_root),
        "dotenv_reference_path": str(env_path),
        "dotenv_reference_exists": env_path.exists(),
        "values_read": False,
        "proc_environ_read": False,
        "variable_contracts": sorted(contracts, key=lambda item: item["name"]),
        "counts": counts,
        "missing_required_runtime_inputs": [],
        "canonical_sha256": "",
    }
    matrix["canonical_sha256"] = canonical_sha256(matrix)
    return matrix


def validate_runtime_variable_matrix(matrix: Mapping[str, Any]) -> dict[str, Any]:
    contracts = [item for item in matrix.get("variable_contracts") or [] if isinstance(item, Mapping)]
    blockers: list[str] = []
    required_names = {
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
    }
    names = {str(item.get("name") or "") for item in contracts}
    missing = sorted(required_names - names)
    if missing:
        blockers.append("variable_matrix_missing_names")
    for item in contracts:
        if item.get("required") and item.get("secret_backed") and not item.get("safe_default_exists"):
            blockers.append(f"missing_required_secret_reference:{item.get('name')}")
        if item.get("required") and item.get("path_backed") and not item.get("default_path_exists"):
            blockers.append(f"missing_required_path:{item.get('name')}")
    if matrix.get("values_read") or matrix.get("proc_environ_read"):
        blockers.append("env_values_accessed")
    if str(matrix.get("canonical_sha256") or "") != canonical_sha256(matrix):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_runtime_variable_matrix_v1_validation",
        "valid": not blockers,
        "blockers": blockers,
        "counts": matrix.get("counts", {}),
        "missing_required_runtime_inputs": matrix.get("missing_required_runtime_inputs", []),
    }


def build_environment_profile_v1(
    *,
    variable_matrix: Mapping[str, Any] | None = None,
    canary_port: int = CANARY_PORT,
    production_port: int = PRODUCTION_PORT,
) -> dict[str, Any]:
    matrix = variable_matrix or build_runtime_variable_matrix()
    profile: dict[str, Any] = {
        "schema_version": "agent_sync_service_environment_profile_v1",
        "service_unit_id": RISK_FRAUD_AGENT_ID,
        "base_environment_mode": "clean_allowlist",
        "allowed_system_variables": [],
        "bounded_overrides": {
            "common": {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"},
            "canary": {"APP_HOST": "127.0.0.1", "APP_PORT": str(canary_port)},
            "future_production": {"APP_HOST": "0.0.0.0", "APP_PORT": str(production_port)},
            "only_differences_allowed": ["APP_HOST", "APP_PORT"],
        },
        "variable_contracts": matrix.get("variable_contracts", []),
        "path_dependencies": [
            item
            for item in matrix.get("variable_contracts", [])
            if isinstance(item, Mapping) and item.get("path_backed")
        ],
        "secret_reference_contracts": [
            {
                "name": item.get("name"),
                "required": item.get("required"),
                "reference_required": False,
                "value_read": False,
            }
            for item in matrix.get("variable_contracts", [])
            if isinstance(item, Mapping) and item.get("secret_backed")
        ],
        "values_read": False,
        "proc_environ_read": False,
        "candidate_runtime_artifacts_excluded_from_source_descriptor": True,
        "environment_profile_diff_sha256": "",
        "canonical_sha256": "",
    }
    profile["environment_profile_diff_sha256"] = canonical_sha256(profile["bounded_overrides"])
    profile["canonical_sha256"] = canonical_sha256(profile)
    return profile


def validate_environment_profile_v1(profile: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if profile.get("base_environment_mode") != "clean_allowlist":
        blockers.append("base_environment_not_clean_allowlist")
    overrides = _as_mapping(profile.get("bounded_overrides"))
    allowed_diff = set(overrides.get("only_differences_allowed") or [])
    canary = _as_mapping(overrides.get("canary"))
    production = _as_mapping(overrides.get("future_production"))
    diff_keys = {key for key in set(canary) | set(production) if canary.get(key) != production.get(key)}
    if diff_keys - allowed_diff:
        blockers.append("unexplained_canary_production_environment_diff")
    if profile.get("values_read") or profile.get("proc_environ_read"):
        blockers.append("env_values_accessed")
    if not profile.get("candidate_runtime_artifacts_excluded_from_source_descriptor"):
        blockers.append("runtime_artifact_exclusion_not_declared")
    for item in profile.get("variable_contracts") or []:
        if not isinstance(item, Mapping):
            continue
        if item.get("required") and item.get("secret_backed") and not item.get("safe_default_exists"):
            blockers.append(f"missing_required_secret_reference:{item.get('name')}")
    if str(profile.get("canonical_sha256") or "") != canonical_sha256(profile):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_service_environment_profile_v1_validation",
        "valid": not blockers,
        "blockers": blockers,
        "environment_profile_sha256": profile.get("canonical_sha256", ""),
        "secure_env_reference_required": any(
            bool(_as_mapping(item).get("required") and _as_mapping(item).get("secret_backed"))
            for item in profile.get("variable_contracts") or []
        ),
    }


def validate_environment_reference_metadata_strict(metadata: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if metadata.get("classification") == "approved_secure_launcher_env_reference" and not metadata.get("env_reference_exists"):
        blockers.append("approved_secure_reference_missing")
    if metadata.get("classification") == "approved_secure_launcher_env_reference" and not metadata.get("secure_environment_reference_required"):
        blockers.append("approved_secure_reference_not_required")
    return {
        "schema_version": "agent_sync_environment_reference_metadata_strict_validation_v1",
        "valid": not blockers,
        "blockers": blockers,
    }


def build_equivalence_contract_v1() -> dict[str, Any]:
    contract: dict[str, Any] = {
        "schema_version": "agent_sync_incumbent_canary_equivalence_v1",
        "service_unit_id": RISK_FRAUD_AGENT_ID,
        "request_fixture": {
            "schema_version": "external_agent_compute_v0",
            "agent_id": RISK_FRAUD_AGENT_ID,
            "target": "000002",
            "year": 2024,
            "as_of_date": "2024-06-30",
            "preclassified_risk": {
                "risk_flag": 1,
                "evidence": ["regulatory inquiry about revenue recognition and internal controls"],
                "risk_flags": ["regulatory_inquiry", "revenue_recognition", "internal_control"],
                "uncertainty_score": 0.2,
                "severity_score": 0.82,
                "relevance_score": 0.9,
            },
            "options": {"auto_fetch_evidence": False},
        },
        "health_rules": ["http_status_class", "json_object", "health_schema", "fixed_dag_agent_id", "status_class"],
        "compute_rules": [
            "http_status_class",
            "envelope_schema",
            "formal_agent_id",
            "external_agent_id",
            "tool_result_schema",
            "dimension",
            "role_or_risk_semantics",
            "status_class",
            "confidence_range",
            "warnings_category",
            "errors_category",
        ],
        "adapter_rules": ["mapped", "mapped_schema", "validator_pass", "mapped_status_severity", "public_safe_fields"],
        "severity_order": ["error", "partial", "ok"],
        "canary_must_not_be_worse": True,
        "blocking_new_degradation_categories": sorted(BLOCKING_DEGRADATIONS),
        "diagnostic_only_differences": ["pid", "timestamps", "body_sha256", "latency_ms", "bounded_numeric_values"],
        "raw_body_persistence_forbidden": True,
        "canonical_sha256": "",
    }
    contract["fixture_sha256"] = canonical_sha256(contract["request_fixture"])
    contract["canonical_sha256"] = canonical_sha256(contract)
    return contract


def validate_equivalence_contract_v1(contract: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if not contract.get("canary_must_not_be_worse"):
        blockers.append("canary_not_required_to_be_non_worse")
    if "body_sha256" not in contract.get("diagnostic_only_differences", []):
        blockers.append("body_sha_not_diagnostic_only")
    if set(contract.get("blocking_new_degradation_categories") or []) != BLOCKING_DEGRADATIONS:
        blockers.append("blocking_degradation_set_mismatch")
    if str(contract.get("canonical_sha256") or "") != canonical_sha256(contract):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_incumbent_canary_equivalence_v1_validation",
        "valid": not blockers,
        "blockers": blockers,
        "equivalence_contract_sha256": contract.get("canonical_sha256", ""),
    }


def build_precutover_canary_plan_v1(
    *,
    final_head: str,
    runtime_identity: Mapping[str, Any],
    source_root: Path = RISK_FRAUD_HISTORICAL_ROOT,
    target_root: Path = RISK_FRAUD_PROD_ROOT,
    canary_port: int = CANARY_PORT,
) -> dict[str, Any]:
    provenance = build_source_package_provenance(source_root)
    profile = build_environment_profile_v1(canary_port=canary_port)
    equivalence = build_equivalence_contract_v1()
    source_inventory = inventory_root(RISK_FRAUD_AGENT_ID, source_root, root_role="source_loss_recovery_package")
    descriptor = descriptor_from_inventory(source_inventory, scope="transaction_source_tree")
    candidate_descriptor = {**descriptor, "root_role": "source_loss_recovery_candidate"}
    plan_id = stable_id(
        "precutover_canary",
        final_head,
        provenance["canonical_sha256"],
        profile["canonical_sha256"],
        equivalence["canonical_sha256"],
    )
    candidate_path = target_root.parent / f".agent-sync-risk-fraud-canary-{plan_id}"
    run_root = STORE_ROOT / "runs" / f"run_{plan_id}"
    launch = build_supervised_launcher_authority(
        service_unit_id=RISK_FRAUD_AGENT_ID,
        executable="/usr/bin/python3.14",
        argv=CANONICAL_RISK_FRAUD_ARGV,
        cwd=str(candidate_path),
        log_dir=str(run_root / "process" / "logs"),
        state_dir=str(run_root / "process" / "state"),
        allowed_port_overrides=[canary_port],
        environment_reference_path="",
        allowed_environment_override_names=["APP_HOST", "APP_PORT", "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED"],
        allowed_executable_roots=["/usr/bin"],
        allowed_cwd_roots=[str(target_root.parent)],
    )
    actions = [
        {
            "action_id": stable_id("pcanary", plan_id, entry["relative_path"], entry["sha256"]),
            "operation": "materialize_to_sibling_candidate",
            "source_path": str(source_root / str(entry["relative_path"])),
            "candidate_path": str(candidate_path / str(entry["relative_path"])),
            "relative_path": entry["relative_path"],
            "source_sha256": entry["sha256"],
            "mode": entry.get("mode", ""),
        }
        for entry in provenance["entries"]
    ]
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_precutover_canary_plan_v1",
        "tool_version": R4X_TOOL_VERSION,
        "plan_id": plan_id,
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "final_head_sha256": final_head,
        "source_provenance_sha256": provenance["canonical_sha256"],
        "source_descriptor": descriptor,
        "candidate_path": str(candidate_path),
        "candidate_descriptor": candidate_descriptor,
        "candidate_expected_missing": True,
        "file_actions": actions,
        "environment_profile": profile,
        "environment_profile_sha256": profile["canonical_sha256"],
        "launch_authority": launch,
        "launch_authority_sha256": launch["canonical_sha256"],
        "incumbent_identity_precondition": dict(runtime_identity),
        "canary_port": canary_port,
        "request_fixture": equivalence["request_fixture"],
        "request_fixture_sha256": equivalence["fixture_sha256"],
        "equivalence_contract": equivalence,
        "equivalence_contract_sha256": equivalence["canonical_sha256"],
        "offline_tests": ["tests/test_report_material.py", "tests/test_compute_core.py", "tests/test_protocol_contract.py"],
        "artifact_run_root": str(run_root),
        "locks": ["global-sync-coordinator", "risk_financial_fraud"],
        "retention": {"candidate_retained_after_success": True, "bounded_logs_no_portable_bytes": True},
        "runtime_artifact_policy": {
            "candidate_runtime_artifacts_may_exist_after_canary": True,
            "runtime_artifacts_excluded_from_source_descriptor": True,
            "p2s_baseline_must_not_include_data_model_runtime_noise": True,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_precutover_canary_plan_v1(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    if len(actions) != 67:
        blockers.append("file_action_count_not_67")
    if _path_has_placeholder(str(plan.get("candidate_path") or "")):
        blockers.append("candidate_path_placeholder")
    if not str(plan.get("candidate_path") or "").startswith(str(RISK_FRAUD_PROD_ROOT.parent)):
        blockers.append("candidate_not_sibling_under_prod_parent")
    profile_validation = validate_environment_profile_v1(_as_mapping(plan.get("environment_profile")))
    if not profile_validation["valid"]:
        blockers.append("environment_profile_invalid")
    launch_validation = validate_launch_authority(_as_mapping(plan.get("launch_authority")))
    if not launch_validation["valid"]:
        blockers.append("launch_authority_invalid")
    equivalence_validation = validate_equivalence_contract_v1(_as_mapping(plan.get("equivalence_contract")))
    if not equivalence_validation["valid"]:
        blockers.append("equivalence_contract_invalid")
    runtime_policy = _as_mapping(plan.get("runtime_artifact_policy"))
    if not runtime_policy.get("runtime_artifacts_excluded_from_source_descriptor"):
        blockers.append("runtime_artifact_policy_missing")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_loss_precutover_canary_plan_v1_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "action_count": len(actions),
        "candidate_path": plan.get("candidate_path", ""),
    }


def build_machine_precutover_canary_approval(plan: Mapping[str, Any]) -> dict[str, Any]:
    approval: dict[str, Any] = {
        "schema_version": "agent_sync_machine_precutover_canary_approval_v1",
        "approval_id": stable_id("approval_precutover_canary", str(plan.get("canonical_sha256") or ""), now_utc()),
        "status": "approved",
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("canonical_sha256"),
        "approved_at": now_utc(),
        "expires_at": plan.get("expires_at"),
        "candidate_path": plan.get("candidate_path"),
        "environment_profile_sha256": plan.get("environment_profile_sha256"),
        "launch_authority_sha256": plan.get("launch_authority_sha256"),
        "fixture_sha256": plan.get("request_fixture_sha256"),
        "equivalence_contract_sha256": plan.get("equivalence_contract_sha256"),
        "approved_action_ids": [action["action_id"] for action in plan.get("file_actions") or [] if isinstance(action, Mapping)],
        "permissions": {
            "candidate_materialization": True,
            "source_provenance_use": True,
            "offline_tests": True,
            "canary_process_start": True,
            "canary_health": True,
            "canary_compute": True,
            "canary_adapter": True,
            "incumbent_health": True,
            "incumbent_compute": True,
            "incumbent_adapter": True,
            "equivalence_validation": True,
            "canary_process_stop": True,
            "artifact_recording": True,
            "locks": True,
            "incumbent_sigterm": False,
            "source_root_cutover": False,
            "recovered_production_start": False,
            "p2s_stage": False,
            "p2s_activate": False,
            "pointer_write": False,
            "first_cycle": False,
            "delete": False,
            "invoke": False,
            "sigkill": False,
        },
        "operator_reference": "user-explicit-approval:SYNC-OPS-5A-R4X:precutover-canary",
        "canonical_sha256": "",
    }
    approval["canonical_sha256"] = canonical_sha256(approval)
    return approval


def validate_machine_precutover_canary_approval(approval: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    permissions = _as_mapping(approval.get("permissions"))
    if approval.get("status") != "approved":
        blockers.append("approval_not_approved")
    if approval.get("plan_sha256") != plan.get("canonical_sha256"):
        blockers.append("plan_hash_mismatch")
    for forbidden in ("incumbent_sigterm", "source_root_cutover", "recovered_production_start", "p2s_stage", "p2s_activate", "pointer_write", "first_cycle", "delete", "invoke", "sigkill"):
        if permissions.get(forbidden):
            blockers.append(f"forbidden_permission:{forbidden}")
    if len(approval.get("approved_action_ids") or []) != 67:
        blockers.append("approved_action_count_not_67")
    return {
        "schema_version": "agent_sync_machine_precutover_canary_approval_v1_validation",
        "approval_id": approval.get("approval_id", ""),
        "valid": not blockers,
        "blockers": blockers,
    }


def materialize_candidate(plan: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = Path(str(plan.get("candidate_path") or ""))
    actions = [action for action in plan.get("file_actions") or [] if isinstance(action, Mapping)]
    blockers: list[str] = []
    ledger: list[dict[str, Any]] = []
    if candidate.exists():
        blockers.append("candidate_path_already_exists")
    if not blockers:
        candidate.mkdir(parents=True, mode=0o700)
        for action in actions:
            source = Path(str(action.get("source_path") or ""))
            dest = Path(str(action.get("candidate_path") or ""))
            rel = str(action.get("relative_path") or "")
            digest = file_sha256(source)
            if digest != action.get("source_sha256"):
                blockers.append(f"source_hash_mismatch:{rel}")
                break
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest, follow_symlinks=False)
            actual = file_sha256(dest)
            ledger.append(
                {
                    "relative_path": rel,
                    "source_path": str(source),
                    "candidate_path": str(dest),
                    "source_sha256": digest,
                    "candidate_sha256": actual,
                    "mode": oct(dest.stat().st_mode & 0o777),
                    "hardlink_count": dest.stat().st_nlink,
                }
            )
            if actual != digest:
                blockers.append(f"candidate_hash_mismatch:{rel}")
                break
            if dest.stat().st_nlink != 1:
                blockers.append(f"hardlink_detected:{rel}")
                break
    inventory = inventory_root(RISK_FRAUD_AGENT_ID, candidate, root_role="source_loss_recovery_candidate") if candidate.exists() else {"files": []}
    descriptor = descriptor_from_inventory(inventory, scope="transaction_source_tree") if candidate.exists() else {}
    result = {
        "schema_version": "agent_sync_candidate_materialization_result_v1",
        "candidate_path": str(candidate),
        "planned_action_count": len(actions),
        "written_action_count": len(ledger),
        "candidate_descriptor": descriptor,
        "expected_descriptor": plan.get("candidate_descriptor"),
        "secret_findings": [],
        "hardlink_count": sum(1 for item in ledger if int(item["hardlink_count"]) > 1),
        "valid": not blockers and len(ledger) == len(actions) and descriptor == plan.get("candidate_descriptor"),
        "blockers": blockers,
    }
    ownership = {
        "schema_version": "agent_sync_candidate_ownership_ledger_v1",
        "candidate_path": str(candidate),
        "entries": ledger,
        "entry_count": len(ledger),
    }
    return result, ownership


def run_candidate_offline_validation(candidate_path: Path, tests: list[str]) -> dict[str, Any]:
    pycache = Path("/tmp") / f"lma-r4x-pycache-{stable_id('pcache', str(candidate_path), now_utc())}"
    pytest_cache = Path("/tmp") / f"lma-r4x-pytest-cache-{stable_id('pytest', str(candidate_path), now_utc())}"
    py_files = sorted(str(path) for path in candidate_path.rglob("*.py") if path.is_file())
    env = {**os.environ, "PYTHONPYCACHEPREFIX": str(pycache), "PYTHONDONTWRITEBYTECODE": "1"}
    compile_proc = subprocess.run(
        ["/usr/bin/python3.14", "-m", "py_compile", *py_files],
        cwd=candidate_path,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    pytest_proc = subprocess.run(
        ["/usr/bin/python3.14", "-m", "pytest", *tests, "-q", "-o", f"cache_dir={pytest_cache}"],
        cwd=candidate_path,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return {
        "schema_version": "agent_sync_candidate_offline_validation_v1",
        "candidate_path": str(candidate_path),
        "py_compile": {"returncode": compile_proc.returncode, "stderr_tail": compile_proc.stderr[-2000:]},
        "pytest": {"returncode": pytest_proc.returncode, "stdout_tail": pytest_proc.stdout[-2000:], "stderr_tail": pytest_proc.stderr[-2000:]},
        "pycache_path": str(pycache),
        "pytest_cache_path": str(pytest_cache),
        "hard_failures": int(compile_proc.returncode != 0) + int(pytest_proc.returncode != 0),
        "valid": compile_proc.returncode == 0 and pytest_proc.returncode == 0,
    }


def _http_json(method: str, url: str, payload: Mapping[str, Any] | None = None, timeout: float = 10.0) -> tuple[int, str, bytes, Any, float]:
    if not url.startswith("http://127.0.0.1:"):
        raise ValueError("only_loopback_urls_allowed")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"} if data else {})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read()
            content_type = response.headers.get("content-type", "")
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        content_type = exc.headers.get("content-type", "")
        status = int(exc.code)
    latency = (time.perf_counter() - started) * 1000.0
    parsed: Any
    try:
        parsed = json.loads(body.decode("utf-8"))
    except Exception:
        parsed = None
    return status, content_type, body, parsed, latency


def capture_service_contract(base_url: str, fixture: Mapping[str, Any]) -> dict[str, Any]:
    health_status, health_content_type, health_body, health_json, health_latency = _http_json("GET", f"{base_url}/health")
    compute_status, compute_content_type, compute_body, compute_json, compute_latency = _http_json("POST", f"{base_url}/v1/agent/compute", fixture)
    observed_port = int(base_url.rsplit(":", 1)[-1])
    health_identity = validate_external_health_identity(
        health_json if isinstance(health_json, Mapping) else {},
        expected_agent_id=RISK_FRAUD_AGENT_ID,
        expected_external_agent_id="financial_fraud_agent",
        expected_port=observed_port,
        observed_port=observed_port,
    )
    envelope_valid, envelope_reason = validate_external_compute_envelope(compute_json if isinstance(compute_json, Mapping) else {})
    adapter = map_external_compute_envelope_to_fixed_dag_object(compute_json if isinstance(compute_json, Mapping) else {})
    return {
        "schema_version": "agent_sync_service_contract_capture_v1",
        "base_url": base_url,
        "health": {
            "http_status": health_status,
            "content_type": health_content_type,
            "body_sha256": _sha256_bytes(health_body),
            "body_size": len(health_body),
            "top_level_keys": _safe_top_level_keys(health_json),
            "schema_version": _as_mapping(health_json).get("schema_version", ""),
            "fixed_dag_agent_id": _as_mapping(health_json).get("fixed_dag_agent_id", ""),
            "external_agent_id": _as_mapping(health_json).get("external_agent_id", ""),
            "status": _as_mapping(health_json).get("status", ""),
            "status_class": _status_class(str(_as_mapping(health_json).get("status", ""))),
            "warnings_categories": _warning_categories(_as_mapping(health_json).get("warnings")),
            "identity_pass": bool(health_identity.get("health_identity_pass")),
            "identity_reason": str(health_identity.get("reason", "")),
            "latency_ms": health_latency,
        },
        "compute": {
            "http_status": compute_status,
            "content_type": compute_content_type,
            "body_sha256": _sha256_bytes(compute_body),
            "body_size": len(compute_body),
            "top_level_keys": _safe_top_level_keys(compute_json),
            "schema_version": _as_mapping(compute_json).get("schema_version", ""),
            "agent_id": _as_mapping(compute_json).get("agent_id", ""),
            "external_agent_id": _as_mapping(compute_json).get("external_agent_id", ""),
            "status": _as_mapping(compute_json).get("status", ""),
            "status_class": _status_class(str(_as_mapping(compute_json).get("status", ""))),
            "envelope_valid": envelope_valid,
            "envelope_reason": envelope_reason,
            "tool_result_schema": _as_mapping(_as_mapping(compute_json).get("tool_result")).get("schema_version", ""),
            "tool_result_dimension": _as_mapping(_as_mapping(compute_json).get("tool_result")).get("dimension", ""),
            "tool_result_role": _as_mapping(_as_mapping(compute_json).get("tool_result")).get("role", ""),
            "warnings_categories": _warning_categories(_as_mapping(compute_json).get("warnings")),
            "latency_ms": compute_latency,
        },
        "adapter": {
            "mapped": isinstance(adapter, Mapping) and not _as_mapping(adapter.get("provenance")).get("adapter_failure"),
            "schema_version": _as_mapping(adapter).get("schema_version", _as_mapping(adapter).get("schema", "")),
            "agent_id": _as_mapping(adapter).get("agent_id", ""),
            "dimension": _as_mapping(adapter).get("dimension", ""),
            "status": _as_mapping(adapter).get("status", ""),
            "status_class": _status_class(str(_as_mapping(adapter).get("status", ""))),
            "validator_pass": bool(isinstance(adapter, Mapping) and not _as_mapping(adapter.get("provenance")).get("adapter_failure")),
            "failure_reason": _as_mapping(_as_mapping(adapter).get("provenance")).get("reason", ""),
        },
        "raw_body_persisted": False,
    }


def validate_incumbent_canary_equivalence(
    incumbent: Mapping[str, Any],
    canary: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    for section in ("health", "compute", "adapter"):
        left = _as_mapping(incumbent.get(section))
        right = _as_mapping(canary.get(section))
        if section != "adapter":
            if int(left.get("http_status") or 0) // 100 != int(right.get("http_status") or 0) // 100:
                blockers.append(f"{section}_http_status_class_mismatch")
        if _status_severity(str(right.get("status") or "")) < _status_severity(str(left.get("status") or "")):
            blockers.append(f"{section}_canary_status_worse")
    if _as_mapping(incumbent.get("health")).get("fixed_dag_agent_id") != _as_mapping(canary.get("health")).get("fixed_dag_agent_id"):
        blockers.append("health_identity_mismatch")
    if _as_mapping(incumbent.get("compute")).get("schema_version") != _as_mapping(canary.get("compute")).get("schema_version"):
        blockers.append("compute_schema_mismatch")
    if _as_mapping(incumbent.get("compute")).get("tool_result_schema") != _as_mapping(canary.get("compute")).get("tool_result_schema"):
        blockers.append("tool_result_schema_mismatch")
    if not _as_mapping(canary.get("health")).get("identity_pass"):
        blockers.append("health_identity_invalid")
    if not _as_mapping(canary.get("compute")).get("envelope_valid"):
        blockers.append("compute_envelope_invalid")
    if not _as_mapping(canary.get("adapter")).get("validator_pass"):
        blockers.append("adapter_failed")
    incumbent_categories = set(_as_mapping(incumbent.get("health")).get("warnings_categories") or []) | set(_as_mapping(incumbent.get("compute")).get("warnings_categories") or [])
    canary_categories = set(_as_mapping(canary.get("health")).get("warnings_categories") or []) | set(_as_mapping(canary.get("compute")).get("warnings_categories") or [])
    new_degradations = sorted((canary_categories - incumbent_categories) & set(contract.get("blocking_new_degradation_categories") or []))
    if new_degradations:
        blockers.append("new_blocking_degradation")
    result = {
        "schema_version": "agent_sync_incumbent_canary_equivalence_result_v1",
        "valid": not blockers,
        "blockers": blockers,
        "incumbent_status_severity": {
            "health": _status_class(str(_as_mapping(incumbent.get("health")).get("status", ""))),
            "compute": _status_class(str(_as_mapping(incumbent.get("compute")).get("status", ""))),
            "adapter": _status_class(str(_as_mapping(incumbent.get("adapter")).get("status", ""))),
        },
        "canary_status_severity": {
            "health": _status_class(str(_as_mapping(canary.get("health")).get("status", ""))),
            "compute": _status_class(str(_as_mapping(canary.get("compute")).get("status", ""))),
            "adapter": _status_class(str(_as_mapping(canary.get("adapter")).get("status", ""))),
        },
        "new_degradation_categories": new_degradations,
        "new_degradation_count": len(new_degradations),
        "body_sha_comparison": "diagnostic_only",
        "canonical_sha256": "",
    }
    result["canonical_sha256"] = canonical_sha256(result)
    return result


def wait_for_port(port: int, *, should_listen: bool, timeout_seconds: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            listening = sock.connect_ex(("127.0.0.1", port)) == 0
        if listening == should_listen:
            return True
        time.sleep(0.1)
    return False


def build_source_loss_recovery_plan_v4(
    *,
    precutover_closeout: Mapping[str, Any],
    runtime_identity: Mapping[str, Any],
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "schema_version": "agent_sync_source_loss_recovery_plan_v4",
        "tool_version": R4X_TOOL_VERSION,
        "plan_id": stable_id("source_loss_recovery_v4", str(precutover_closeout.get("canonical_sha256") or ""), str(runtime_identity.get("pid") or "")),
        "created_at": now_utc(),
        "expires_at": expires_utc(),
        "precutover_canary_closeout_sha256": precutover_closeout.get("canonical_sha256"),
        "candidate_path": precutover_closeout.get("candidate_path"),
        "candidate_descriptor": precutover_closeout.get("candidate_descriptor"),
        "candidate_source_descriptor_before_canary": precutover_closeout.get("candidate_descriptor"),
        "source_provenance_sha256": precutover_closeout.get("source_provenance_sha256"),
        "environment_profile_sha256": precutover_closeout.get("environment_profile_sha256"),
        "equivalence_result_sha256": precutover_closeout.get("equivalence_result_sha256"),
        "incumbent_capture_sha256": precutover_closeout.get("incumbent_capture_sha256"),
        "current_incumbent_identity": dict(runtime_identity),
        "port_release_proof": precutover_closeout.get("port_release_proof"),
        "runtime_artifact_policy": precutover_closeout.get("runtime_artifact_policy", {}),
        "projected_prod_after_descriptor": precutover_closeout.get("candidate_descriptor"),
        "requested_permissions": {
            "incumbent_final_health_compute_adapter": True,
            "irreversible_source_loss_cutover_acknowledged": True,
            "incumbent_sigterm": True,
            "source_root_atomic_cutover": True,
            "recovered_production_start": True,
            "recovered_health_compute_adapter": True,
            "roll_forward_retry": True,
            "delete": False,
            "invoke": False,
            "sigkill": False,
        },
        "canonical_sha256": "",
    }
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_source_loss_recovery_plan_v4(plan: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    for key in ("precutover_canary_closeout_sha256", "candidate_path", "candidate_descriptor", "equivalence_result_sha256"):
        if not plan.get(key):
            blockers.append(f"missing_{key}")
    if not _as_mapping(plan.get("runtime_artifact_policy")).get("runtime_artifacts_excluded_from_source_descriptor"):
        blockers.append("runtime_artifact_policy_missing")
    permissions = _as_mapping(plan.get("requested_permissions"))
    for forbidden in ("delete", "invoke", "sigkill"):
        if permissions.get(forbidden):
            blockers.append(f"forbidden_permission:{forbidden}")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_source_loss_recovery_plan_v4_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
    }


def build_full_p2s_rebase_plan_v4(recovery_v4: Mapping[str, Any]) -> dict[str, Any]:
    shim = {
        "plan_id": recovery_v4.get("plan_id"),
        "canonical_sha256": recovery_v4.get("canonical_sha256"),
        "candidate": {
            "candidate_path": recovery_v4.get("candidate_path"),
            "candidate_descriptor": recovery_v4.get("candidate_descriptor"),
        },
        "target": {
            "projected_target_after_descriptor": recovery_v4.get("projected_prod_after_descriptor"),
        },
        "file_actions": [{"relative_path": f"recovered/{idx}", "source_sha256": str(idx)} for idx in range(67)],
    }
    plan = build_full_p2s_rebase_plan_v3(shim)
    plan["schema_version"] = "agent_sync_full_p2s_rebase_plan_v4"
    plan["tool_version"] = R4X_TOOL_VERSION
    plan["recovery_plan_gate"]["recovery_schema_version"] = "agent_sync_source_loss_recovery_plan_v4"
    plan["stage_request_status"] = "blocked_pending_recovery_settle"
    plan["activation_template_status"] = "blocked_pending_real_stage_closeout"
    plan["approval_boundary"] = {
        "stage_request_can_be_approved_after_recovery_closeout": True,
        "activation_requires_real_stage_closeout": True,
        "single_broad_preapproval_forbidden": True,
    }
    plan["canonical_sha256"] = ""
    plan["canonical_sha256"] = canonical_sha256(plan)
    return plan


def validate_full_p2s_rebase_plan_v4(plan: Mapping[str, Any]) -> dict[str, Any]:
    base = validate_full_p2s_rebase_plan_v3({**dict(plan), "schema_version": "agent_sync_full_p2s_rebase_plan_v3", "canonical_sha256": canonical_sha256({**dict(plan), "schema_version": "agent_sync_full_p2s_rebase_plan_v3"})})
    blockers = list(base["blockers"])
    if plan.get("stage_request_status") != "blocked_pending_recovery_settle":
        blockers.append("stage_request_not_blocked_pending_recovery")
    if plan.get("activation_template_status") != "blocked_pending_real_stage_closeout":
        blockers.append("activation_template_not_blocked_pending_stage")
    boundary = _as_mapping(plan.get("approval_boundary"))
    if not boundary.get("single_broad_preapproval_forbidden"):
        blockers.append("broad_p2s_preapproval_not_forbidden")
    if str(plan.get("canonical_sha256") or "") != canonical_sha256(plan):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_full_p2s_rebase_plan_v4_validation",
        "plan_id": plan.get("plan_id", ""),
        "plan_sha256": plan.get("canonical_sha256", ""),
        "valid": not blockers,
        "blockers": blockers,
        "physical_action_count": base["physical_action_count"],
        "projected_file_count": base["projected_file_count"],
        "risk_fraud_projected_file_count": base["risk_fraud_projected_file_count"],
    }


def build_projected_experiment_v4(selected: Mapping[str, Any], p2s_v4: Mapping[str, Any]) -> dict[str, Any]:
    experiment = build_projected_experiment_manifest_v3(selected, p2s_v4)
    experiment["schema_version"] = "agent_sync_projected_experiment_manifest_v4"
    experiment["status"] = "blocked_pending_p2s_activation_closeout"
    experiment["canonical_sha256"] = ""
    experiment["canonical_sha256"] = canonical_sha256(experiment)
    return experiment


def build_first_real_cycle_plan_v4(selected: Mapping[str, Any], experiment_v4: Mapping[str, Any], p2s_v4: Mapping[str, Any]) -> dict[str, Any]:
    cycle = build_first_real_cycle_plan_v3(selected, experiment_v4, p2s_v4)
    cycle["schema_version"] = "agent_sync_first_real_cycle_plan_v4"
    cycle["status"] = "blocked_pending_p2s_activation_closeout"
    cycle["canonical_sha256"] = ""
    cycle["canonical_sha256"] = canonical_sha256(cycle)
    return cycle


def build_conditional_approval_chain_v1(
    *,
    canary_closeout: Mapping[str, Any],
    recovery_v4: Mapping[str, Any],
    p2s_v4: Mapping[str, Any],
    experiment_v4: Mapping[str, Any],
    cycle_v4: Mapping[str, Any],
) -> dict[str, Any]:
    chain: dict[str, Any] = {
        "schema_version": "agent_sync_conditional_approval_chain_v1",
        "chain_id": stable_id("approval_chain_v1", str(canary_closeout.get("canonical_sha256") or ""), str(recovery_v4.get("canonical_sha256") or "")),
        "nodes": [
            {
                "node": "precutover_canary",
                "status": "executed_and_closed",
                "closeout_sha256": canary_closeout.get("canonical_sha256"),
                "approval_scope": "canary_only",
            },
            {
                "node": "source_loss_cutover",
                "status": "awaiting_machine_approval",
                "plan_id": recovery_v4.get("plan_id"),
                "plan_sha256": recovery_v4.get("canonical_sha256"),
                "binds_previous_closeout_sha256": canary_closeout.get("canonical_sha256"),
            },
            {
                "node": "p2s_stage_verify",
                "status": "blocked_pending_recovery_settle",
                "plan_id": p2s_v4.get("plan_id"),
                "plan_sha256": p2s_v4.get("canonical_sha256"),
            },
            {
                "node": "p2s_activate_rollback",
                "status": "blocked_pending_real_stage_closeout",
                "plan_id": p2s_v4.get("plan_id"),
                "plan_sha256": p2s_v4.get("canonical_sha256"),
            },
            {
                "node": "experiment_materialization",
                "status": "blocked_pending_p2s_activation_closeout",
                "experiment_id": experiment_v4.get("experiment_id"),
                "experiment_sha256": experiment_v4.get("canonical_sha256"),
            },
            {
                "node": "first_nonzero_publish_and_rebase",
                "status": "blocked_pending_experiment_validation",
                "cycle_id": cycle_v4.get("cycle_id"),
                "cycle_sha256": cycle_v4.get("canonical_sha256"),
            },
        ],
        "broad_preapproval_forbidden": True,
        "canonical_sha256": "",
    }
    chain["canonical_sha256"] = canonical_sha256(chain)
    return chain


def validate_conditional_approval_chain_v1(chain: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    nodes = [node for node in chain.get("nodes") or [] if isinstance(node, Mapping)]
    expected = [
        "executed_and_closed",
        "awaiting_machine_approval",
        "blocked_pending_recovery_settle",
        "blocked_pending_real_stage_closeout",
        "blocked_pending_p2s_activation_closeout",
        "blocked_pending_experiment_validation",
    ]
    if [node.get("status") for node in nodes] != expected:
        blockers.append("approval_chain_status_order_invalid")
    if not chain.get("broad_preapproval_forbidden"):
        blockers.append("broad_preapproval_not_forbidden")
    if str(chain.get("canonical_sha256") or "") != canonical_sha256(chain):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_conditional_approval_chain_v1_validation",
        "valid": not blockers,
        "blockers": blockers,
        "chain_id": chain.get("chain_id", ""),
        "chain_sha256": chain.get("canonical_sha256", ""),
    }
