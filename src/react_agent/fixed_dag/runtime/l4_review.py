"""L4 runtime binding review evidence helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from react_agent.fixed_dag.runtime.bindings import (
    binding_by_agent_id,
    external_compute_default_agent_ids,
)
from react_agent.fixed_dag.runtime.constants import (
    _L4_REVIEW_UNSAFE_TOKENS,
    L4_REVIEW_EVIDENCE_SAFE_FIELDS,
    L4_RUNTIME_BINDING_DRY_RUN_SCHEMA_VERSION,
    L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION,
    L4_RUNTIME_REVIEW_AGENT_IDS,
    L4_RUNTIME_REVIEW_COMPUTE_TARGETS,
    L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION,
    L4_RUNTIME_REVIEW_REQUIREMENTS,
)

L4_RUNTIME_REVIEW_CANDIDATE_EVIDENCE = {
    "provider_compute_pass": {
        "passed": True,
        "reference": (
            "docs/history/misc/CONTROLLED_READINESS_SMOKE_LOG.md"
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
        "reference": "docs/history/r8/L4_RUNTIME_REVIEW_EVIDENCE_R8_13O.md#rollback-plan",
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


__all__ = [
    "L4_RUNTIME_REVIEW_CANDIDATE_EVIDENCE",
    "build_l4_runtime_binding_dry_run",
    "build_l4_runtime_binding_phase_plan",
    "build_l4_runtime_review_candidate_package",
    "build_l4_runtime_review_evidence_package",
]
