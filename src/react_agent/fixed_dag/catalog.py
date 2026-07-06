# ruff: noqa: D101, D103
"""Fixed DAG reset agent catalog loader and public projection.

This module is stdlib-only by design so ``fixed_dag.contracts`` can import it
without creating provider, external-service, or public API dependency cycles.
(Originally at ``fixed_dag_catalog.py``, moved here during Phase 1
consolidation.)
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

FIXED_DAG_AGENT_CATALOG_SCHEMA_VERSION = "fixed_dag_agent_catalog_v1"
FIXED_DAG_CATALOG_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "fixed_dag" / "agent_catalog.json"
)
FIXED_DAG_LAYER_ORDER = ("L1", "L2", "L3", "L4")
FIXED_DAG_DIMENSION_ORDER = ("l1", "value", "market", "risk", "macro", "composite", "l4")
FIXED_DAG_STAGE_ORDER = (
    "planning",
    "evidence",
    "l2_analysis",
    "dimension_composite",
    "decision",
    "report",
)
EXPECTED_LAYER_COUNTS = {"L1": 3, "L2": 18, "L3": 4, "L4": 2}
EXPECTED_DIMENSION_COUNTS = {
    "l1": 3,
    "value": 4,
    "market": 5,
    "risk": 4,
    "macro": 5,
    "composite": 4,
    "l4": 2,
}
EXPECTED_TOTAL_COUNT = 27
FORBIDDEN_RESET_AGENT_IDS = {
    "value_financial_analysis",
    "financial_metrics_analyzer",
    "fixed_dag_executor",
    "main_dag_executor",
    "monitoring_dashboard",
    "workflow_inspector",
}
ANN_ID_PATTERN = re.compile(r"^a\d{2}_")


class FixedDagAgentMetadata(TypedDict):
    id: str
    display_name: str
    layer: str
    dimension: str
    role_type: str
    stage: str
    default_enabled: bool
    implementation_status: str
    description: str
    input_contract: str
    output_contract: str
    upstream: list[str]
    downstream: list[str]


class FixedDagCatalog(TypedDict):
    schema_version: str
    source: str
    total_count: int
    layer_counts: dict[str, int]
    dimension_counts: dict[str, int]
    agents: list[FixedDagAgentMetadata]
    provenance: NotRequired[dict[str, Any]]


def load_fixed_dag_catalog(path: Path | None = None) -> FixedDagCatalog:
    catalog_path = path or FIXED_DAG_CATALOG_PATH
    return cast(
        FixedDagCatalog,
        json.loads(catalog_path.read_text(encoding="utf-8")),
    )


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _str_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        normalized.append(item.strip())
    return normalized


def _count_by(items: list[Mapping[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(item.get(key) or "") for item in items))


def validate_fixed_dag_catalog(catalog: Mapping[str, Any]) -> tuple[bool, str]:
    if not isinstance(catalog, Mapping):
        return False, "catalog_not_mapping"
    if catalog.get("schema_version") != FIXED_DAG_AGENT_CATALOG_SCHEMA_VERSION:
        return False, "invalid_schema_version"
    if catalog.get("total_count") != EXPECTED_TOTAL_COUNT:
        return False, "total_count_mismatch"
    if dict(catalog.get("layer_counts", {})) != EXPECTED_LAYER_COUNTS:
        return False, "layer_counts_mismatch"
    if dict(catalog.get("dimension_counts", {})) != EXPECTED_DIMENSION_COUNTS:
        return False, "dimension_counts_mismatch"

    raw_agents = _as_list(catalog.get("agents"))
    if len(raw_agents) != EXPECTED_TOTAL_COUNT:
        return False, "agents_count_mismatch"
    if not all(isinstance(item, Mapping) for item in raw_agents):
        return False, "agent_not_mapping"
    agents = [cast(Mapping[str, Any], item) for item in raw_agents]

    ids = [str(item.get("id") or "") for item in agents]
    if len(set(ids)) != len(ids):
        return False, "duplicate_agent_id"
    known_ids = set(ids)
    for forbidden in FORBIDDEN_RESET_AGENT_IDS:
        if forbidden in known_ids:
            return False, f"forbidden_agent_id:{forbidden}"

    for agent in agents:
        agent_id = str(agent.get("id") or "")
        if not agent_id:
            return False, "empty_agent_id"
        if ANN_ID_PATTERN.match(agent_id):
            return False, f"legacy_ann_id:{agent_id}"
        if not str(agent.get("display_name") or "").strip():
            return False, f"display_name_missing:{agent_id}"
        if str(agent.get("layer") or "") not in FIXED_DAG_LAYER_ORDER:
            return False, f"invalid_layer:{agent_id}"
        if str(agent.get("dimension") or "") not in FIXED_DAG_DIMENSION_ORDER:
            return False, f"invalid_dimension:{agent_id}"
        if str(agent.get("stage") or "") not in FIXED_DAG_STAGE_ORDER:
            return False, f"invalid_stage:{agent_id}"
        if not str(agent.get("role_type") or "").strip():
            return False, f"role_type_missing:{agent_id}"
        if not isinstance(agent.get("default_enabled"), bool):
            return False, f"default_enabled_not_bool:{agent_id}"
        if not str(agent.get("implementation_status") or "").strip():
            return False, f"implementation_status_missing:{agent_id}"
        if not str(agent.get("description") or "").strip():
            return False, f"description_missing:{agent_id}"
        if not str(agent.get("input_contract") or "").strip():
            return False, f"input_contract_missing:{agent_id}"
        if not str(agent.get("output_contract") or "").strip():
            return False, f"output_contract_missing:{agent_id}"
        upstream = _str_list(agent.get("upstream"))
        downstream = _str_list(agent.get("downstream"))
        if upstream is None:
            return False, f"invalid_upstream:{agent_id}"
        if downstream is None:
            return False, f"invalid_downstream:{agent_id}"
        unknown_upstream = set(upstream) - known_ids
        if unknown_upstream:
            return False, f"unknown_upstream:{agent_id}"
        unknown_downstream = set(downstream) - known_ids
        if unknown_downstream:
            return False, f"unknown_downstream:{agent_id}"

    if _count_by(agents, "layer") != EXPECTED_LAYER_COUNTS:
        return False, "actual_layer_counts_mismatch"
    if _count_by(agents, "dimension") != EXPECTED_DIMENSION_COUNTS:
        return False, "actual_dimension_counts_mismatch"

    by_id = {str(item["id"]): item for item in agents}
    sentiment = by_id.get("sentiment_company_radar")
    if sentiment is None:
        return False, "sentiment_company_radar_missing"
    if sentiment.get("layer") != "L2" or sentiment.get("dimension") != "market":
        return False, "sentiment_dimension_mismatch"
    if sentiment.get("downstream") != ["market_composite"]:
        return False, "sentiment_downstream_mismatch"
    risk_composite = by_id.get("risk_composite")
    if risk_composite is None:
        return False, "risk_composite_missing"
    if "sentiment_company_radar" in set(_str_list(risk_composite.get("upstream")) or []):
        return False, "risk_composite_reads_sentiment"

    return True, "ok"


def _validated_catalog(catalog: Mapping[str, Any] | None = None) -> FixedDagCatalog:
    loaded = load_fixed_dag_catalog() if catalog is None else catalog
    valid, reason = validate_fixed_dag_catalog(loaded)
    if not valid:
        raise ValueError(f"Invalid fixed DAG catalog: {reason}")
    return cast(FixedDagCatalog, loaded)


def fixed_dag_agents(catalog: Mapping[str, Any] | None = None) -> list[FixedDagAgentMetadata]:
    return list(_validated_catalog(catalog)["agents"])


def fixed_dag_agent_ids(catalog: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    return tuple(agent["id"] for agent in fixed_dag_agents(catalog))


def fixed_dag_agents_by_layer(
    catalog: Mapping[str, Any] | None = None,
) -> dict[str, tuple[str, ...]]:
    agents = fixed_dag_agents(catalog)
    return {
        layer: tuple(agent["id"] for agent in agents if agent["layer"] == layer)
        for layer in FIXED_DAG_LAYER_ORDER
    }


def fixed_dag_agents_by_dimension(
    catalog: Mapping[str, Any] | None = None,
) -> dict[str, tuple[str, ...]]:
    agents = fixed_dag_agents(catalog)
    return {
        dimension: tuple(agent["id"] for agent in agents if agent["dimension"] == dimension)
        for dimension in FIXED_DAG_DIMENSION_ORDER
    }


def fixed_dag_agent_by_id(
    catalog: Mapping[str, Any] | None = None,
) -> dict[str, FixedDagAgentMetadata]:
    return {agent["id"]: agent for agent in fixed_dag_agents(catalog)}


def fixed_dag_public_agent_catalog(
    catalog: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    loaded = _validated_catalog(catalog)
    agents = loaded["agents"]
    enabled = [agent for agent in agents if agent["default_enabled"]]
    disabled = [agent for agent in agents if not agent["default_enabled"]]

    def public_agent(agent: FixedDagAgentMetadata) -> dict[str, Any]:
        return {
            "id": agent["id"],
            "name": agent["display_name"],
            "description": (
                f"{agent['description']} "
                f"实现状态：{agent['implementation_status']}。"
            ),
            "capabilities": [
                agent["stage"],
                agent["dimension"],
                agent["implementation_status"],
            ],
            "layer": agent["layer"],
            "team": agent["dimension"],
            "roleType": agent["role_type"],
            "defaultEnabled": agent["default_enabled"],
        }

    return {
        "totals": {
            "configCount": loaded["total_count"],
            "runtimeCount": len(enabled),
            "disabledIds": [agent["id"] for agent in disabled],
        },
        "layers": [
            {
                "layer": layer,
                "agents": [public_agent(agent) for agent in agents if agent["layer"] == layer],
            }
            for layer in FIXED_DAG_LAYER_ORDER
        ],
        "disabledAgents": [public_agent(agent) for agent in disabled],
    }
