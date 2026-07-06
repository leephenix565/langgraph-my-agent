# ruff: noqa: D101, D103
"""Production non-L4 external compute policy registry.

This registry is intentionally separate from both the demo bridge allowlist and
the L4 `external_compute_default` runtime bindings.  It enables a reviewed
subset of non-L4 `/v1/agent/compute` services for the normal graph path without
editing `runtime_bindings.json` or using demo URL overrides.

(Moved from ``fixed_dag_non_l4_runtime_registry.py`` during Phase 1
consolidation.)
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from react_agent.fixed_dag.catalog import (
    fixed_dag_agent_by_id,
    load_fixed_dag_catalog,
    validate_fixed_dag_catalog,
)
from react_agent.fixed_dag.external.compute_bridge import (
    COMPUTE_PATH,
    DEMO_COMPUTE_SERVICE_REGISTRY,
    ExternalComputeDemoEntry,
    validate_demo_entry,
)

NON_L4_EXTERNAL_COMPUTE_POLICY_SCHEMA_VERSION = (
    "fixed_dag_non_l4_external_compute_policy_v1"
)
NON_L4_EXTERNAL_COMPUTE_POLICY_PATH = (
    Path(__file__).resolve().parents[4]
    / "config"
    / "fixed_dag"
    / "non_l4_external_compute_policy.json"
)
NON_L4_EXTERNAL_COMPUTE_POLICY_SOURCE = (
    "config/fixed_dag/non_l4_external_compute_policy.json"
)
NON_L4_EXTERNAL_COMPUTE_DISABLE_ENV_VAR = "DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT"
NON_L4_EXTERNAL_COMPUTE_SOURCE = "production_external_compute"
NON_L4_REQUIRED_AGENT_IDS = (
    "value_traditional_valuation",
    "value_ml_valuation",
    "value_meta_valuation",
    "market_ipo_investor_behavior",
    "market_capital_flow_chip",
    "risk_crash",
    "macro_analysis",
    "macro_index_valuation",
    "value_composite",
)
NON_L4_OPTIONAL_AGENT_IDS = (
    "value_research_synthesis",
    "market_stock_technical",
    "sentiment_company_radar",
    "risk_financial_fraud",
    "risk_identification",
    "risk_compliance_review",
    "macro_commodity_pricing",
    "market_composite",
    "risk_composite",
    "macro_composite",
)
NON_L4_EXCLUDED_AGENT_IDS = (
    "entity_relation_extractor",
    "market_fund_manager_behavior",
    "macro_sentiment",
    "macro_industry_hotspot",
    "financial_data_service",
    "decision_synthesizer",
    "report_generator",
)
NON_L4_ALLOWED_FAILURE_POLICIES = {
    "fail_soft_to_pending_l2",
    "fail_soft_to_deterministic_l3",
    "fail_soft_zero_weight_or_deterministic_l3",
}
NON_L4_ALLOWED_LAYER_BY_STAGE = {
    "l2_analysis": "L2",
    "dimension_composite": "L3",
}
NON_L4_COMPOSITE_DIMENSION_BY_AGENT = {
    "value_composite": "value",
    "market_composite": "market",
    "risk_composite": "risk",
    "macro_composite": "macro",
}
NON_L4_ACTIVATION_SOURCE_ARTIFACT = "production_activation_candidate_set.json"
NON_L4_ACTIVATION_SOURCE_SHA256 = (
    "a605fbcaf195af33bfba5c5058b64142397a467c4d713ef2df17504e1c7288f3"
)


class NonL4ExternalComputePolicyAgent(TypedDict):
    agent_id: str
    enabled: bool
    layer: str
    dimension: str
    required_or_optional: str
    timeout_seconds: int | float
    failure_policy: str
    port: int
    compute_path: str
    service_registry_ref: str
    external_agent_id: str
    expected_payload: str
    provenance_source: str
    canary_candidate: NotRequired[bool]


class NonL4ExternalComputePolicy(TypedDict):
    schema_version: str
    enabled_by_default: bool
    disable_env_var: str
    demo_precedence: str
    activation_source: dict[str, str]
    max_concurrency_by_stage: dict[str, int]
    agents: list[NonL4ExternalComputePolicyAgent]


def load_non_l4_external_compute_policy(
    path: Path | None = None,
) -> NonL4ExternalComputePolicy:
    policy_path = path or NON_L4_EXTERNAL_COMPUTE_POLICY_PATH
    return cast(
        NonL4ExternalComputePolicy,
        json.loads(policy_path.read_text(encoding="utf-8")),
    )


def _raw_agents(policy: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
    raw = policy.get("agents")
    if not isinstance(raw, list):
        return None
    if not all(isinstance(item, Mapping) for item in raw):
        return None
    return [cast(Mapping[str, Any], item) for item in raw]


def _agent_expected_dimension(agent_id: str, catalog_agent: Mapping[str, Any]) -> str:
    if agent_id in NON_L4_COMPOSITE_DIMENSION_BY_AGENT:
        return NON_L4_COMPOSITE_DIMENSION_BY_AGENT[agent_id]
    return str(catalog_agent.get("dimension") or "")


def _validate_agent_row(
    row: Mapping[str, Any],
    *,
    catalog_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[bool, str]:
    agent_id = str(row.get("agent_id") or "")
    if not agent_id:
        return False, "agent_id_missing"
    if agent_id in NON_L4_EXCLUDED_AGENT_IDS:
        return False, f"excluded_agent_present:{agent_id}"
    if agent_id not in catalog_by_id:
        return False, f"unknown_agent:{agent_id}"
    if agent_id in {"decision_synthesizer", "report_generator"}:
        return False, f"l4_agent_present:{agent_id}"
    template = DEMO_COMPUTE_SERVICE_REGISTRY.get(str(row.get("service_registry_ref") or ""))
    if template is None or template.agent_id != agent_id:
        return False, f"service_registry_ref_mismatch:{agent_id}"

    catalog_agent = catalog_by_id[agent_id]
    if row.get("layer") != catalog_agent.get("layer"):
        return False, f"layer_mismatch:{agent_id}"
    if str(row.get("layer") or "") not in {"L2", "L3"}:
        return False, f"non_l4_layer_invalid:{agent_id}"
    expected_dimension = _agent_expected_dimension(agent_id, catalog_agent)
    if row.get("dimension") != expected_dimension:
        return False, f"dimension_mismatch:{agent_id}"
    if row.get("required_or_optional") not in {"required", "optional"}:
        return False, f"required_or_optional_invalid:{agent_id}"
    if not isinstance(row.get("enabled"), bool):
        return False, f"enabled_invalid:{agent_id}"
    if row.get("failure_policy") not in NON_L4_ALLOWED_FAILURE_POLICIES:
        return False, f"failure_policy_invalid:{agent_id}"
    if row.get("compute_path") != COMPUTE_PATH:
        return False, f"compute_path_invalid:{agent_id}"
    if str(row.get("compute_path") or "").lower().find("invoke") >= 0:
        return False, f"invoke_path_present:{agent_id}"
    if row.get("external_agent_id") != template.external_agent_id:
        return False, f"external_agent_id_mismatch:{agent_id}"
    if row.get("expected_payload") != template.expected_payload:
        return False, f"expected_payload_mismatch:{agent_id}"
    if row.get("provenance_source") != NON_L4_EXTERNAL_COMPUTE_SOURCE:
        return False, f"provenance_source_invalid:{agent_id}"
    try:
        timeout = float(row.get("timeout_seconds"))
    except (TypeError, ValueError):
        return False, f"timeout_invalid:{agent_id}"
    if timeout < 1 or timeout > 60:
        return False, f"timeout_out_of_bounds:{agent_id}"
    port = row.get("port")
    if not isinstance(port, int) or port <= 0 or port > 65535:
        return False, f"port_invalid:{agent_id}"

    entry = external_compute_entry_from_policy_row(cast(NonL4ExternalComputePolicyAgent, row))
    valid, reason = validate_demo_entry(entry)
    if not valid:
        return False, f"entry_invalid:{agent_id}:{reason}"
    return True, "ok"


def validate_non_l4_external_compute_policy(
    policy: Mapping[str, Any],
    *,
    catalog: Mapping[str, Any] | None = None,
) -> tuple[bool, str]:
    if not isinstance(policy, Mapping):
        return False, "policy_not_mapping"
    if policy.get("schema_version") != NON_L4_EXTERNAL_COMPUTE_POLICY_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if not isinstance(policy.get("enabled_by_default"), bool):
        return False, "enabled_by_default_invalid"
    if policy.get("disable_env_var") != NON_L4_EXTERNAL_COMPUTE_DISABLE_ENV_VAR:
        return False, "disable_env_var_mismatch"
    if policy.get("demo_precedence") != "demo_suppresses_production_non_l4":
        return False, "demo_precedence_invalid"
    activation_source = policy.get("activation_source")
    if not isinstance(activation_source, Mapping):
        return False, "activation_source_invalid"
    if activation_source.get("artifact") != NON_L4_ACTIVATION_SOURCE_ARTIFACT:
        return False, "activation_source_artifact_mismatch"
    if activation_source.get("sha256") != NON_L4_ACTIVATION_SOURCE_SHA256:
        return False, "activation_source_sha256_mismatch"
    max_concurrency = policy.get("max_concurrency_by_stage")
    if not isinstance(max_concurrency, Mapping):
        return False, "max_concurrency_invalid"
    if int(max_concurrency.get("l2", 0) or 0) < 1:
        return False, "l2_concurrency_invalid"
    if int(max_concurrency.get("l3", 0) or 0) < 1:
        return False, "l3_concurrency_invalid"

    loaded_catalog = load_fixed_dag_catalog() if catalog is None else catalog
    catalog_valid, catalog_reason = validate_fixed_dag_catalog(loaded_catalog)
    if not catalog_valid:
        return False, f"invalid_catalog:{catalog_reason}"
    catalog_by_id = fixed_dag_agent_by_id(cast(Mapping[str, Any], loaded_catalog))

    raw = _raw_agents(policy)
    if raw is None:
        return False, "agents_invalid"
    ids = [str(item.get("agent_id") or "") for item in raw]
    if len(ids) != len(set(ids)):
        return False, "duplicate_agent_id"
    for row in raw:
        valid, reason = _validate_agent_row(row, catalog_by_id=catalog_by_id)
        if not valid:
            return valid, reason

    required_ids = tuple(
        str(item.get("agent_id"))
        for item in raw
        if item.get("required_or_optional") == "required"
    )
    if required_ids != NON_L4_REQUIRED_AGENT_IDS:
        return False, "required_agent_set_mismatch"
    optional_ids = tuple(
        str(item.get("agent_id"))
        for item in raw
        if item.get("required_or_optional") == "optional"
    )
    if optional_ids != NON_L4_OPTIONAL_AGENT_IDS:
        return False, "optional_agent_set_mismatch"
    return True, "ok"


def _validated_policy(
    policy: Mapping[str, Any] | None = None,
) -> NonL4ExternalComputePolicy:
    loaded = load_non_l4_external_compute_policy() if policy is None else policy
    valid, reason = validate_non_l4_external_compute_policy(loaded)
    if not valid:
        raise ValueError(f"Invalid non-L4 external compute policy: {reason}")
    return cast(NonL4ExternalComputePolicy, loaded)


def non_l4_policy_agents(
    policy: Mapping[str, Any] | None = None,
    *,
    include_disabled: bool = False,
) -> tuple[NonL4ExternalComputePolicyAgent, ...]:
    loaded = _validated_policy(policy)
    agents = loaded["agents"]
    if include_disabled:
        return tuple(agents)
    return tuple(agent for agent in agents if agent["enabled"])


def non_l4_policy_enabled_agent_ids(policy: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    return tuple(agent["agent_id"] for agent in non_l4_policy_agents(policy))


def non_l4_policy_summary(policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    loaded = _validated_policy(policy)
    agents = loaded["agents"]
    return {
        "schema_version": loaded["schema_version"],
        "enabled_by_default": loaded["enabled_by_default"],
        "disable_env_var": loaded["disable_env_var"],
        "activation_source": dict(loaded["activation_source"]),
        "agent_count": len(agents),
        "enabled_agent_ids": [agent["agent_id"] for agent in agents if agent["enabled"]],
        "required_agent_ids": [
            agent["agent_id"]
            for agent in agents
            if agent["required_or_optional"] == "required"
        ],
        "optional_agent_ids": [
            agent["agent_id"]
            for agent in agents
            if agent["required_or_optional"] == "optional"
        ],
        "counts_by_layer": dict(Counter(agent["layer"] for agent in agents)),
        "counts_by_requirement": dict(Counter(agent["required_or_optional"] for agent in agents)),
    }


def external_compute_entry_from_policy_row(
    row: NonL4ExternalComputePolicyAgent,
) -> ExternalComputeDemoEntry:
    template = DEMO_COMPUTE_SERVICE_REGISTRY[row["service_registry_ref"]]
    return ExternalComputeDemoEntry(
        agent_id=row["agent_id"],
        base_url=f"http://127.0.0.1:{int(row['port'])}",
        compute_path=COMPUTE_PATH,
        expected_payload=row["expected_payload"],
        dimension=row["dimension"],
        external_agent_id=row["external_agent_id"],
        default_target=template.default_target,
        timeout_seconds=float(row["timeout_seconds"]),
    )


def non_l4_external_compute_entries(
    policy: Mapping[str, Any] | None = None,
    *,
    include_disabled: bool = False,
) -> dict[str, ExternalComputeDemoEntry]:
    return {
        row["agent_id"]: external_compute_entry_from_policy_row(row)
        for row in non_l4_policy_agents(policy, include_disabled=include_disabled)
    }


def non_l4_policy_agent_by_id(
    policy: Mapping[str, Any] | None = None,
    *,
    include_disabled: bool = False,
) -> dict[str, NonL4ExternalComputePolicyAgent]:
    return {
        row["agent_id"]: row
        for row in non_l4_policy_agents(policy, include_disabled=include_disabled)
    }


__all__ = [
    "NON_L4_ACTIVATION_SOURCE_SHA256",
    "NON_L4_EXTERNAL_COMPUTE_DISABLE_ENV_VAR",
    "NON_L4_EXTERNAL_COMPUTE_POLICY_PATH",
    "NON_L4_EXTERNAL_COMPUTE_POLICY_SCHEMA_VERSION",
    "NON_L4_EXTERNAL_COMPUTE_POLICY_SOURCE",
    "NON_L4_EXTERNAL_COMPUTE_SOURCE",
    "NON_L4_EXCLUDED_AGENT_IDS",
    "NON_L4_OPTIONAL_AGENT_IDS",
    "NON_L4_REQUIRED_AGENT_IDS",
    "external_compute_entry_from_policy_row",
    "load_non_l4_external_compute_policy",
    "non_l4_external_compute_entries",
    "non_l4_policy_agent_by_id",
    "non_l4_policy_agents",
    "non_l4_policy_enabled_agent_ids",
    "non_l4_policy_summary",
    "validate_non_l4_external_compute_policy",
]
