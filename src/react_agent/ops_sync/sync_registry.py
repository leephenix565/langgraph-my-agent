# ruff: noqa: D101, D103
"""Static agent service registry validation for sync planning."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict, cast

from react_agent.fixed_dag.catalog import fixed_dag_agent_by_id, load_fixed_dag_catalog
from react_agent.ops_sync.sync_contracts import (
    CATALOG_PATH,
    REGISTRY_PATH,
    SYNC_POLICY_PATH,
    SyncPlannerError,
    file_sha256,
    read_json,
    validate_by_schema_version,
)
from react_agent.ops_sync.sync_security import is_allowed_root

EXTERNAL_FORMAL_COUNT = 26
INTERNAL_AGENT_IDS = {"route_planner"}
NONFATAL_CONFLICT_TOPICS = {
    "sanitized derivative",
    "shared support root",
    "placeholder service",
    "historical source durability vs current P2S",
    "owner patch conflict",
}
FATAL_CONFLICT_REASONS = {
    "duplicate_formal_id",
    "catalog_mismatch",
    "sentiment_route_to_risk",
    "unsafe_root_escape",
    "duplicate_action_target_without_shared_service_unit",
    "external_id_conflict",
}


class RegistryValidation(TypedDict):
    valid: bool
    formal_external_agent_count: int
    fatal_conflicts: list[dict[str, Any]]
    review_warnings: list[dict[str, Any]]
    unverified: list[dict[str, Any]]
    catalog_sha256: str
    registry_sha256: str
    policy_sha256: str


def load_static_registry(path: Path | None = None) -> dict[str, Any]:
    registry = cast(dict[str, Any], read_json(path or REGISTRY_PATH))
    validate_by_schema_version(registry)
    return registry


def load_sync_policy(path: Path | None = None) -> dict[str, Any]:
    policy = cast(dict[str, Any], read_json(path or SYNC_POLICY_PATH))
    validate_by_schema_version(policy)
    return policy


def external_catalog_ids() -> set[str]:
    catalog = load_fixed_dag_catalog()
    return {agent["id"] for agent in catalog["agents"] if agent["id"] not in INTERNAL_AGENT_IDS}


def _classify_registry_conflict(conflict: Mapping[str, Any]) -> str:
    reason = str(conflict.get("reason") or conflict.get("topic") or "")
    if reason in FATAL_CONFLICT_REASONS:
        return "fatal"
    topic = str(conflict.get("topic") or "")
    if topic in NONFATAL_CONFLICT_TOPICS:
        return "review_warning"
    if "sanitized" in topic or "placeholder" in topic or "historical" in topic:
        return "review_warning"
    return "review_warning"


def validate_static_registry(registry: Mapping[str, Any] | None = None) -> RegistryValidation:
    loaded = load_static_registry() if registry is None else registry
    catalog_by_id = fixed_dag_agent_by_id()
    expected_ids = external_catalog_ids()
    agents = loaded.get("agents")
    if not isinstance(agents, list):
        raise SyncPlannerError("registry_agents_invalid", exit_code=2)
    ids = [str(agent.get("agent_id") or "") for agent in agents if isinstance(agent, Mapping)]
    fatal: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if len(ids) != len(set(ids)):
        fatal.append({"reason": "duplicate_formal_id"})
    if set(ids) != expected_ids:
        fatal.append(
            {
                "reason": "catalog_mismatch",
                "expected_only": sorted(expected_ids - set(ids)),
                "registry_only": sorted(set(ids) - expected_ids),
            }
        )
    for raw_agent in agents:
        if not isinstance(raw_agent, Mapping):
            fatal.append({"reason": "agent_not_mapping"})
            continue
        agent_id = str(raw_agent.get("agent_id") or "")
        catalog_agent = catalog_by_id.get(agent_id)
        if catalog_agent is None:
            continue
        if raw_agent.get("layer") != catalog_agent.get("layer"):
            fatal.append({"agent_id": agent_id, "reason": "catalog_mismatch", "field": "layer"})
        if raw_agent.get("dimension") != catalog_agent.get("dimension"):
            fatal.append({"agent_id": agent_id, "reason": "catalog_mismatch", "field": "dimension"})
        if list(raw_agent.get("routes_to") or []) != list(catalog_agent.get("downstream") or []):
            if agent_id == "sentiment_company_radar" and "risk_composite" in list(raw_agent.get("routes_to") or []):
                fatal.append({"agent_id": agent_id, "reason": "sentiment_route_to_risk"})
            else:
                warnings.append({"agent_id": agent_id, "reason": "routes_differ_from_catalog"})
        for section in ("prod", "sandbox"):
            root = str(cast(Mapping[str, Any], raw_agent.get(section) or {}).get("root") or "")
            active = str(cast(Mapping[str, Any], raw_agent.get(section) or {}).get("active_root") or "")
            baseline = str(cast(Mapping[str, Any], raw_agent.get(section) or {}).get("baseline_root") or "")
            for value in (root, active, baseline):
                if value and not is_allowed_root(Path(value)):
                    fatal.append({"agent_id": agent_id, "reason": "unsafe_root_escape", "path": value})
        sandbox = cast(Mapping[str, Any], raw_agent.get("sandbox") or {})
        if sandbox.get("sanitized_derivative"):
            warnings.append({"agent_id": agent_id, "reason": "sanitized_derivative_non_publishable"})
        if sandbox.get("semantic_placeholder"):
            warnings.append({"agent_id": agent_id, "reason": "semantic_placeholder_snapshot"})
        owner = cast(Mapping[str, Any], raw_agent.get("owner_dev") or {})
        if owner.get("authority_status") in {"owner_authority_unresolved", "", None}:
            warnings.append({"agent_id": agent_id, "reason": "owner_authority_unresolved"})
    for conflict in loaded.get("conflicts") or []:
        if not isinstance(conflict, Mapping):
            continue
        if _classify_registry_conflict(conflict) == "fatal":
            fatal.append(dict(conflict))
        else:
            warnings.append(dict(conflict))
    return {
        "valid": not fatal,
        "formal_external_agent_count": len(ids),
        "fatal_conflicts": fatal,
        "review_warnings": warnings,
        "unverified": list(loaded.get("unverified") or []),
        "catalog_sha256": file_sha256(CATALOG_PATH),
        "registry_sha256": file_sha256(REGISTRY_PATH),
        "policy_sha256": file_sha256(SYNC_POLICY_PATH),
    }
