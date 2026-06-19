# ruff: noqa: D101, D103
"""Fixed DAG runtime binding registry.

The registry records how each reset-skeleton agent may later bind to a local
deterministic seam, an external HTTP candidate, or a pending placeholder. It is
metadata only: loading and validating this file must never invoke a provider,
search backend, or external agent endpoint.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from react_agent.fixed_dag_catalog import (
    ANN_ID_PATTERN,
    EXPECTED_TOTAL_COUNT,
    FIXED_DAG_AGENT_CATALOG_SCHEMA_VERSION,
    FORBIDDEN_RESET_AGENT_IDS,
    fixed_dag_agent_by_id,
    fixed_dag_agent_ids,
    load_fixed_dag_catalog,
    validate_fixed_dag_catalog,
)

FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION = "fixed_dag_runtime_bindings_v1"
FIXED_DAG_RUNTIME_BINDINGS_SOURCE = "config/fixed_dag/runtime_bindings.json"
L4_RUNTIME_BINDING_DRY_RUN_SCHEMA_VERSION = "fixed_dag_l4_runtime_binding_dry_run_v1"
L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION = (
    "fixed_dag_l4_runtime_review_evidence_package_v1"
)
L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION = (
    "fixed_dag_l4_runtime_binding_phase_plan_v1"
)
FIXED_DAG_RUNTIME_BINDINGS_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "fixed_dag" / "runtime_bindings.json"
)
L4_RUNTIME_REVIEW_AGENT_IDS = ("decision_synthesizer", "report_generator")
L4_RUNTIME_REVIEW_REQUIREMENTS = (
    "provider_compute_pass",
    "transcript_safety_pass",
    "rollback_plan_ready",
    "operator_approval",
)
L4_RUNTIME_REVIEW_COMPUTE_TARGETS = {
    "decision_synthesizer": {
        "external_agent_id": "l4_decision_synthesizer",
        "compute_url": "http://127.0.0.1:10025/v1/agent/compute",
        "output_contract": "decision_result_v1",
    },
    "report_generator": {
        "external_agent_id": "l4_report_generator",
        "compute_url": "http://127.0.0.1:10026/v1/agent/compute",
        "output_contract": "report_result_v1",
    },
}
L4_REVIEW_EVIDENCE_SAFE_FIELDS = (
    "reference",
    "summary",
    "validated_by",
    "validated_at",
)
L4_RUNTIME_REVIEW_CANDIDATE_EVIDENCE = {
    "provider_compute_pass": {
        "passed": True,
        "reference": (
            "docs/CONTROLLED_READINESS_SMOKE_LOG.md"
            "#r8-13j-l4-provider-backed-controlled-compute-smoke"
        ),
        "summary": "production-source provider-backed L4 compute evidence recorded",
        "validated_by": "codex",
        "validated_at": "2026-06-19",
    },
    "transcript_safety_pass": {
        "passed": True,
        "reference": (
            "tests/unit_tests/test_fixed_dag_external_adapter.py"
            "::l4_provider_backed_safety_regression"
        ),
        "summary": "adapter rejects unsafe provider-backed L4 public payloads",
        "validated_by": "codex",
        "validated_at": "2026-06-19",
    },
    "rollback_plan_ready": {
        "passed": True,
        "reference": "docs/L4_RUNTIME_REVIEW_EVIDENCE_R8_13O.md#rollback-plan",
        "summary": "deterministic L4 fallback and config rollback plan documented",
        "validated_by": "codex",
        "validated_at": "2026-06-19",
    },
    "operator_approval": {
        "passed": True,
        "reference": "operator-approval:2026-06-19:l4-runtime-goal",
        "summary": "operator approved completing the L4 default runtime goal",
        "validated_by": "codex",
        "validated_at": "2026-06-19",
    },
}
_L4_REVIEW_UNSAFE_TOKENS = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "env",
    "endpoint",
    "default_url",
    "raw_response",
    "raw_provider_response",
    "raw_external_json",
    "traceback",
    "chain_of_thought",
    "chain-of-thought",
    "cot",
    "/v1/agent/invoke",
)
VALID_RUNTIME_KINDS = {
    "deterministic_system",
    "deterministic_l1_bundle",
    "deterministic_composite",
    "deterministic_decision",
    "deterministic_report",
    "external_compute_default",
    "external_http_candidate",
    "pending_placeholder",
}
VALID_IMPLEMENTATION_STATUSES = {
    "deterministic_skeleton",
    "external_compute_default_enabled",
    "external_candidate_disabled",
    "pending_implementation",
}
REQUIRED_BINDING_FIELDS = {
    "agent_id",
    "runtime_kind",
    "implementation_status",
    "invoke_enabled_by_default",
    "live_verified",
    "legacy_agent_id",
    "external_agent_id",
    "env_var",
    "default_url",
    "input_contract",
    "output_contract",
    "notes",
    "routes_to",
}
EXTERNAL_CANDIDATE_STATUS = "external_candidate_disabled"
EXTERNAL_COMPUTE_DEFAULT_STATUS = "external_compute_default_enabled"
PENDING_PLACEHOLDER_STATUS = "pending_implementation"
DETERMINISTIC_STATUS = "deterministic_skeleton"


class FixedDagRuntimeBinding(TypedDict):
    agent_id: str
    runtime_kind: str
    implementation_status: str
    invoke_enabled_by_default: bool
    live_verified: bool
    legacy_agent_id: str
    external_agent_id: str
    env_var: str
    default_url: str
    input_contract: str
    output_contract: str
    notes: str
    routes_to: list[str]


class FixedDagRuntimeBindings(TypedDict):
    schema_version: str
    catalog_schema_version: str
    catalog_source: str
    total_count: int
    default_external_invoke_enabled: bool
    bindings: list[FixedDagRuntimeBinding]
    provenance: NotRequired[dict[str, Any]]


def load_fixed_dag_runtime_bindings(path: Path | None = None) -> FixedDagRuntimeBindings:
    bindings_path = path or FIXED_DAG_RUNTIME_BINDINGS_PATH
    return cast(
        FixedDagRuntimeBindings,
        json.loads(bindings_path.read_text(encoding="utf-8")),
    )


def _raw_bindings(bindings: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
    raw = bindings.get("bindings")
    if not isinstance(raw, list):
        return None
    if not all(isinstance(item, Mapping) for item in raw):
        return None
    return [cast(Mapping[str, Any], item) for item in raw]


def _str_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        result.append(item.strip())
    return result


def _legacy_external_config() -> Mapping[str, Any]:
    # Imported lazily from a config-only module to avoid wrapper side effects.
    from react_agent.external_http_config import EXTERNAL_HTTP_AGENT_CONFIG

    return EXTERNAL_HTTP_AGENT_CONFIG


def _string_field(binding: Mapping[str, Any], field: str) -> str | None:
    value = binding.get(field)
    if not isinstance(value, str):
        return None
    return value


def _validate_field_types(binding: Mapping[str, Any]) -> tuple[bool, str]:
    agent_id = str(binding.get("agent_id") or "")
    missing = REQUIRED_BINDING_FIELDS - set(binding)
    if missing:
        return False, f"missing_binding_field:{agent_id}:{sorted(missing)[0]}"
    for field in (
        "agent_id",
        "runtime_kind",
        "implementation_status",
        "legacy_agent_id",
        "external_agent_id",
        "env_var",
        "default_url",
        "input_contract",
        "output_contract",
        "notes",
    ):
        if _string_field(binding, field) is None:
            return False, f"invalid_string_field:{agent_id}:{field}"
    if not isinstance(binding.get("invoke_enabled_by_default"), bool):
        return False, f"invalid_invoke_enabled:{agent_id}"
    if not isinstance(binding.get("live_verified"), bool):
        return False, f"invalid_live_verified:{agent_id}"
    if _str_list(binding.get("routes_to")) is None:
        return False, f"invalid_routes_to:{agent_id}"
    return True, "ok"


def _validate_runtime_kind(binding: Mapping[str, Any]) -> tuple[bool, str]:
    agent_id = str(binding.get("agent_id") or "")
    runtime_kind = str(binding.get("runtime_kind") or "")
    implementation_status = str(binding.get("implementation_status") or "")
    invoke_enabled = bool(binding.get("invoke_enabled_by_default"))
    live_verified = bool(binding.get("live_verified"))

    if runtime_kind not in VALID_RUNTIME_KINDS:
        return False, f"invalid_runtime_kind:{agent_id}"
    if implementation_status not in VALID_IMPLEMENTATION_STATUSES:
        return False, f"invalid_implementation_status:{agent_id}"
    if runtime_kind == "external_http_candidate":
        if implementation_status != EXTERNAL_CANDIDATE_STATUS:
            return False, f"external_status_mismatch:{agent_id}"
        if invoke_enabled:
            return False, f"external_candidate_invoke_enabled:{agent_id}"
        if live_verified:
            return False, f"external_candidate_live_verified:{agent_id}"
        for field in ("legacy_agent_id", "external_agent_id", "env_var", "default_url"):
            if not str(binding.get(field) or "").strip():
                return False, f"external_candidate_missing_{field}:{agent_id}"
    elif runtime_kind == "external_compute_default":
        if agent_id not in L4_RUNTIME_REVIEW_AGENT_IDS:
            return False, f"external_compute_default_not_l4:{agent_id}"
        if implementation_status != EXTERNAL_COMPUTE_DEFAULT_STATUS:
            return False, f"external_compute_default_status_mismatch:{agent_id}"
        if invoke_enabled:
            return False, f"external_compute_default_invoke_enabled:{agent_id}"
        if not live_verified:
            return False, f"external_compute_default_not_live_verified:{agent_id}"
        for field in ("external_agent_id", "env_var", "default_url"):
            if not str(binding.get(field) or "").strip():
                return False, f"external_compute_default_missing_{field}:{agent_id}"
        default_url = str(binding.get("default_url") or "").strip().lower()
        if "/v1/agent/compute" not in default_url or "/v1/agent/invoke" in default_url:
            return False, f"external_compute_default_url_not_compute:{agent_id}"
    elif runtime_kind == "pending_placeholder":
        if implementation_status != PENDING_PLACEHOLDER_STATUS:
            return False, f"pending_status_mismatch:{agent_id}"
        if invoke_enabled:
            return False, f"pending_placeholder_invoke_enabled:{agent_id}"
        if live_verified:
            return False, f"pending_placeholder_live_verified:{agent_id}"
        for field in ("external_agent_id", "env_var", "default_url"):
            if str(binding.get(field) or "").strip():
                return False, f"pending_placeholder_has_endpoint:{agent_id}"
    elif implementation_status != DETERMINISTIC_STATUS:
        return False, f"deterministic_status_mismatch:{agent_id}"
    return True, "ok"


def _validate_legacy_external_mapping(binding: Mapping[str, Any]) -> tuple[bool, str]:
    legacy_agent_id = str(binding.get("legacy_agent_id") or "").strip()
    if not legacy_agent_id:
        return True, "ok"
    config = _legacy_external_config().get(legacy_agent_id)
    if config is None:
        return True, "ok"
    agent_id = str(binding.get("agent_id") or "")
    expected = {
        "external_agent_id": getattr(config, "external_agent_id"),
        "env_var": getattr(config, "env_var"),
        "default_url": getattr(config, "default_url"),
    }
    for field, expected_value in expected.items():
        actual = str(binding.get(field) or "")
        if actual != expected_value:
            return False, f"legacy_external_mapping_mismatch:{agent_id}:{field}"
    return True, "ok"


def validate_fixed_dag_runtime_bindings(
    bindings: Mapping[str, Any],
    catalog: Mapping[str, Any] | None = None,
) -> tuple[bool, str]:
    if not isinstance(bindings, Mapping):
        return False, "bindings_not_mapping"
    if bindings.get("schema_version") != FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if bindings.get("catalog_schema_version") != FIXED_DAG_AGENT_CATALOG_SCHEMA_VERSION:
        return False, "invalid_catalog_schema_version"
    if bindings.get("catalog_source") != "config/fixed_dag/agent_catalog.json":
        return False, "invalid_catalog_source"
    if bindings.get("total_count") != EXPECTED_TOTAL_COUNT:
        return False, "total_count_mismatch"
    if bindings.get("default_external_invoke_enabled") is not False:
        return False, "default_external_invoke_not_disabled"

    loaded_catalog = load_fixed_dag_catalog() if catalog is None else catalog
    catalog_valid, catalog_reason = validate_fixed_dag_catalog(loaded_catalog)
    if not catalog_valid:
        return False, f"invalid_catalog:{catalog_reason}"
    catalog_ids = fixed_dag_agent_ids(loaded_catalog)
    catalog_by_id = fixed_dag_agent_by_id(loaded_catalog)

    raw = _raw_bindings(bindings)
    if raw is None:
        return False, "bindings_list_invalid"
    if len(raw) != EXPECTED_TOTAL_COUNT:
        return False, "bindings_count_mismatch"
    ids = [str(item.get("agent_id") or "") for item in raw]
    if len(set(ids)) != len(ids):
        return False, "duplicate_agent_id"
    for agent_id in ids:
        if not agent_id:
            return False, "empty_agent_id"
        if ANN_ID_PATTERN.match(agent_id):
            return False, f"legacy_ann_primary_id:{agent_id}"
        if agent_id in FORBIDDEN_RESET_AGENT_IDS:
            return False, f"forbidden_agent_id:{agent_id}"
        if agent_id == "value_financial_analysis":
            return False, "value_financial_analysis_present"
    if tuple(ids) != catalog_ids:
        return False, "binding_ids_do_not_match_catalog"

    for binding in raw:
        agent_id = str(binding.get("agent_id") or "")
        valid, reason = _validate_field_types(binding)
        if not valid:
            return valid, reason
        valid, reason = _validate_runtime_kind(binding)
        if not valid:
            return valid, reason
        valid, reason = _validate_legacy_external_mapping(binding)
        if not valid:
            return valid, reason
        catalog_agent = catalog_by_id[agent_id]
        if binding.get("input_contract") != catalog_agent["input_contract"]:
            return False, f"input_contract_mismatch:{agent_id}"
        if binding.get("output_contract") != catalog_agent["output_contract"]:
            return False, f"output_contract_mismatch:{agent_id}"
        if _str_list(binding.get("routes_to")) != catalog_agent["downstream"]:
            return False, f"routes_to_mismatch:{agent_id}"

    by_id = {str(item["agent_id"]): item for item in raw}
    sentiment = by_id.get("sentiment_company_radar")
    if sentiment is None:
        return False, "sentiment_company_radar_missing"
    if sentiment.get("routes_to") != ["market_composite"]:
        return False, "sentiment_routes_mismatch"
    if "risk_composite" in set(cast(list[str], sentiment.get("routes_to"))):
        return False, "sentiment_routes_to_risk"
    risk_composite = by_id.get("risk_composite")
    if risk_composite is None:
        return False, "risk_composite_missing"
    if "sentiment_company_radar" in set(catalog_by_id["risk_composite"]["upstream"]):
        return False, "risk_composite_reads_sentiment"
    return True, "ok"


def _validated_runtime_bindings(
    bindings: Mapping[str, Any] | None = None,
) -> FixedDagRuntimeBindings:
    loaded = load_fixed_dag_runtime_bindings() if bindings is None else bindings
    valid, reason = validate_fixed_dag_runtime_bindings(loaded)
    if not valid:
        raise ValueError(f"Invalid fixed DAG runtime bindings: {reason}")
    return cast(FixedDagRuntimeBindings, loaded)


def fixed_dag_runtime_bindings(
    bindings: Mapping[str, Any] | None = None,
) -> list[FixedDagRuntimeBinding]:
    return list(_validated_runtime_bindings(bindings)["bindings"])


def fixed_dag_runtime_binding_ids(
    bindings: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    return tuple(binding["agent_id"] for binding in fixed_dag_runtime_bindings(bindings))


def binding_by_agent_id(
    agent_id: str,
    bindings: Mapping[str, Any] | None = None,
) -> FixedDagRuntimeBinding:
    for binding in fixed_dag_runtime_bindings(bindings):
        if binding["agent_id"] == agent_id:
            return binding
    raise KeyError(f"unknown fixed DAG runtime binding: {agent_id}")


def external_candidate_bindings(
    bindings: Mapping[str, Any] | None = None,
) -> tuple[FixedDagRuntimeBinding, ...]:
    return tuple(
        binding
        for binding in fixed_dag_runtime_bindings(bindings)
        if binding["runtime_kind"] == "external_http_candidate"
    )


def external_compute_default_bindings(
    bindings: Mapping[str, Any] | None = None,
) -> tuple[FixedDagRuntimeBinding, ...]:
    return tuple(
        binding
        for binding in fixed_dag_runtime_bindings(bindings)
        if binding["runtime_kind"] == "external_compute_default"
    )


def external_compute_default_agent_ids(
    bindings: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    return tuple(binding["agent_id"] for binding in external_compute_default_bindings(bindings))


def runtime_binding_summary(bindings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    items = fixed_dag_runtime_bindings(bindings)
    return {
        "total_count": len(items),
        "runtime_kind_counts": dict(Counter(item["runtime_kind"] for item in items)),
        "implementation_status_counts": dict(
            Counter(item["implementation_status"] for item in items)
        ),
        "external_candidate_count": sum(
            item["runtime_kind"] == "external_http_candidate" for item in items
        ),
        "external_compute_default_count": sum(
            item["runtime_kind"] == "external_compute_default" for item in items
        ),
        "live_verified_count": sum(item["live_verified"] for item in items),
        "invoke_enabled_count": sum(item["invoke_enabled_by_default"] for item in items),
    }


def _l4_review_safe_string(value: Any, *, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if any(token in lowered for token in _L4_REVIEW_UNSAFE_TOKENS):
        return ""
    if re.search(r"https?://", lowered):
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _normalize_l4_review_evidence_item(
    requirement: str,
    raw: Any,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {
            "requirement": requirement,
            "status": "missing",
            "passed": False,
            "reason": "missing_evidence_record",
        }

    passed = raw.get("passed") is True or raw.get("status") == "pass"
    item: dict[str, Any] = {
        "requirement": requirement,
        "passed": False,
    }
    for field in L4_REVIEW_EVIDENCE_SAFE_FIELDS:
        text = _l4_review_safe_string(raw.get(field))
        if text:
            item[field] = text

    if not passed:
        item["status"] = "failed"
        item["reason"] = "evidence_not_passed"
        return item
    if not item.get("reference"):
        item["status"] = "invalid"
        item["reason"] = "missing_or_unsafe_reference"
        return item

    item["status"] = "pass"
    item["passed"] = True
    item["reason"] = "ok"
    return item


def build_l4_runtime_binding_dry_run(
    bindings: Mapping[str, Any] | None = None,
    *,
    provider_compute_pass: bool = False,
    transcript_safety_pass: bool = False,
    rollback_plan_ready: bool = False,
    operator_approval: bool = False,
) -> dict[str, Any]:
    """Build a metadata-only L4 runtime review plan without editing bindings."""
    readiness = {
        "provider_compute_pass": bool(provider_compute_pass),
        "transcript_safety_pass": bool(transcript_safety_pass),
        "rollback_plan_ready": bool(rollback_plan_ready),
        "operator_approval": bool(operator_approval),
    }
    blocking_reasons = [
        f"{key}_missing"
        for key, passed in readiness.items()
        if not passed
    ]
    agents = []
    for agent_id in L4_RUNTIME_REVIEW_AGENT_IDS:
        binding = binding_by_agent_id(agent_id, bindings)
        target = L4_RUNTIME_REVIEW_COMPUTE_TARGETS[agent_id]
        default_binding_currently_external = binding["runtime_kind"] == "external_compute_default"
        agents.append(
            {
                "agent_id": agent_id,
                "current_binding_scope": (
                    "external_l4_compute_default"
                    if default_binding_currently_external
                    else "deterministic_internal_l4_seam"
                ),
                "current_runtime_kind": binding["runtime_kind"],
                "current_implementation_status": binding["implementation_status"],
                "current_invoke_enabled_by_default": binding["invoke_enabled_by_default"],
                "current_live_verified": binding["live_verified"],
                "current_external_agent_id": binding["external_agent_id"],
                "current_env_var": binding["env_var"],
                "current_default_url": binding["default_url"],
                "proposed_external_agent_id": target["external_agent_id"],
                "proposed_compute_url": target["compute_url"],
                "proposed_output_contract": target["output_contract"],
                "proposed_external_invoke_enabled_by_default": False,
                "proposed_external_live_verified": not default_binding_currently_external,
                "binding_edit_required": not default_binding_currently_external,
                "default_binding_currently_external": default_binding_currently_external,
            }
        )
    ready = not blocking_reasons
    return {
        "schema_version": L4_RUNTIME_BINDING_DRY_RUN_SCHEMA_VERSION,
        "status": (
            "ready_for_runtime_binding_review"
            if ready
            else "blocked_pending_requirements"
        ),
        "runtime_bindings_changed": False,
        "default_runtime_enabled": any(
            item["default_binding_currently_external"] for item in agents
        ),
        "invoke_endpoint_required": False,
        "agents": agents,
        "readiness": readiness,
        "blocking_reasons": blocking_reasons,
        "recommended_next_action": (
            "open_explicit_runtime_binding_phase"
            if ready
            else "do_not_edit_runtime_bindings"
        ),
    }


def build_l4_runtime_review_evidence_package(
    bindings: Mapping[str, Any] | None = None,
    *,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a local L4 runtime review evidence package without side effects."""
    raw_evidence = evidence or {}
    evidence_items = [
        _normalize_l4_review_evidence_item(
            requirement,
            raw_evidence.get(requirement),
        )
        for requirement in L4_RUNTIME_REVIEW_REQUIREMENTS
    ]
    readiness = {
        item["requirement"]: bool(item["passed"])
        for item in evidence_items
    }
    dry_run = build_l4_runtime_binding_dry_run(
        bindings,
        provider_compute_pass=readiness["provider_compute_pass"],
        transcript_safety_pass=readiness["transcript_safety_pass"],
        rollback_plan_ready=readiness["rollback_plan_ready"],
        operator_approval=readiness["operator_approval"],
    )
    missing_evidence = [
        {
            "requirement": item["requirement"],
            "status": item["status"],
            "reason": item["reason"],
        }
        for item in evidence_items
        if item["status"] != "pass"
    ]
    ready = not missing_evidence
    return {
        "schema_version": L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION,
        "status": (
            "ready_for_explicit_runtime_binding_phase"
            if ready
            else "blocked_pending_evidence"
        ),
        "runtime_bindings_changed": False,
        "default_runtime_enabled": bool(dry_run.get("default_runtime_enabled")),
        "invoke_endpoint_required": False,
        "required_evidence": evidence_items,
        "missing_evidence": missing_evidence,
        "dry_run": dry_run,
        "non_actions": [
            "no_endpoint_call",
            "no_env_file_change",
            "no_runtime_bindings_edit",
            "no_live_flag_change",
            "no_invoke_default_change",
        ],
        "recommended_next_action": (
            "open_explicit_runtime_binding_phase"
            if ready
            else "collect_missing_l4_runtime_review_evidence"
        ),
    }


def build_l4_runtime_review_candidate_package(
    bindings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the current repo-recorded L4 runtime review candidate package."""
    return build_l4_runtime_review_evidence_package(
        bindings,
        evidence=L4_RUNTIME_REVIEW_CANDIDATE_EVIDENCE,
    )


def build_l4_runtime_binding_phase_plan(
    bindings: Mapping[str, Any] | None = None,
    *,
    evidence_package: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a non-mutating plan for a future external-L4 binding phase."""
    package = (
        build_l4_runtime_review_candidate_package(bindings)
        if evidence_package is None
        else dict(evidence_package)
    )
    missing_evidence = list(package.get("missing_evidence") or [])
    ready_package = package.get("status") == "ready_for_explicit_runtime_binding_phase"
    planned_agent_changes = []
    configured_default_ids = set(external_compute_default_agent_ids(bindings))
    for agent_id in L4_RUNTIME_REVIEW_AGENT_IDS:
        binding = binding_by_agent_id(agent_id, bindings)
        target = L4_RUNTIME_REVIEW_COMPUTE_TARGETS[agent_id]
        configured_default = agent_id in configured_default_ids
        planned_agent_changes.append(
            {
                "agent_id": agent_id,
                "current_runtime_kind": binding["runtime_kind"],
                "target_runtime_kind": "external_compute_default",
                "target_endpoint_kind": "compute_only",
                "target_external_agent_id": target["external_agent_id"],
                "target_compute_url": target["compute_url"],
                "target_output_contract": target["output_contract"],
                "already_configured": configured_default,
                "requires_runtime_schema_extension": not configured_default,
                "requires_executor_default_path": not configured_default,
                "binding_edit_required": not configured_default,
                "invoke_endpoint_required": False,
            }
        )

    if not ready_package:
        return {
            "schema_version": L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION,
            "status": "blocked_pending_evidence",
            "runtime_bindings_changed": False,
            "config_edit_allowed": False,
            "current_schema_allows_external_l4_default": True,
            "missing_evidence": missing_evidence,
            "planned_agent_changes": planned_agent_changes,
            "required_work": ["operator_approval"],
            "recommended_next_action": "collect_missing_l4_runtime_review_evidence",
        }

    if set(L4_RUNTIME_REVIEW_AGENT_IDS).issubset(configured_default_ids):
        return {
            "schema_version": L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION,
            "status": "runtime_binding_configured_pending_smoke",
            "runtime_bindings_changed": False,
            "config_edit_allowed": False,
            "current_schema_allows_external_l4_default": True,
            "missing_evidence": [],
            "planned_agent_changes": planned_agent_changes,
            "required_work": ["run_default_l4_compute_runtime_smoke"],
            "recommended_next_action": "run_default_l4_compute_runtime_smoke",
        }

    return {
        "schema_version": L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION,
        "status": "ready_for_runtime_binding_config_edit",
        "runtime_bindings_changed": False,
        "config_edit_allowed": True,
        "current_schema_allows_external_l4_default": True,
        "missing_evidence": [],
        "planned_agent_changes": planned_agent_changes,
        "required_work": [
            "edit_runtime_bindings_json",
            "run_default_l4_compute_runtime_smoke",
        ],
        "recommended_next_action": "edit_runtime_bindings_json",
    }


def annotate_step_result_with_binding(
    step_result: Mapping[str, Any],
    bindings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = dict(step_result)
    binding = binding_by_agent_id(str(result.get("agent_id") or ""), bindings)
    result.update(
        {
            "runtime_kind": binding["runtime_kind"],
            "implementation_status": binding["implementation_status"],
            "binding_source": FIXED_DAG_RUNTIME_BINDINGS_SOURCE,
            "legacy_agent_id": binding["legacy_agent_id"],
            "external_agent_id": binding["external_agent_id"],
            "invoke_enabled": binding["invoke_enabled_by_default"],
            "live_verified": binding["live_verified"],
        }
    )
    return result
