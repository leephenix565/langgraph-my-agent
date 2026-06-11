"""Legacy aNN agent registry retained as migration/readiness input.

The fixed-DAG reset runtime does not use this registry as an execution source.
It remains for compatibility tests, external-wrapper readiness work, and
historical config/agents metadata migration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from langchain_core.tools import BaseTool


@dataclass
class AgentMetadata:
    """Legacy metadata loaded from config/agents/*.json."""

    id: str
    name: str
    description: str
    capabilities: List[str]
    input_type: str
    latency_level: str
    cost_level: str
    version: str
    layer: str | None = None
    team: str | None = None
    role_type: str | None = None
    business_order: int | None = None
    business_role: str | None = None
    business_status: str | None = None
    business_layer: str | None = None
    business_category: str | None = None
    business_subcategory: str | None = None
    profile_summary: str | None = None
    when_to_use: str | None = None
    when_not_to_use: str | None = None
    required_inputs: str | None = None
    missing_input_policy: str | None = None
    owner: str | None = None
    profile_source: str | None = None
    profile_updated_from_excel: str | None = None
    default_enabled: bool = True


def format_agent_profile(meta: AgentMetadata) -> str:
    """Return the structured legacy profile used by compatibility tools."""
    lines = [
        f"name: {meta.name}",
        f"business_layer: {meta.business_layer or ''}",
        f"business_category: {meta.business_category or ''}",
        f"profile_summary: {meta.profile_summary or meta.description}",
        f"when_to_use: {meta.when_to_use or ''}",
        f"when_not_to_use: {meta.when_not_to_use or ''}",
        f"required_inputs: {meta.required_inputs or ''}",
        f"missing_input_policy: {meta.missing_input_policy or ''}",
    ]
    return "\n".join(lines)


AGENT_METADATA: Dict[str, AgentMetadata] = {}
AGENT_TOOLS: Dict[str, BaseTool] = {}


def register_agent(metadata: AgentMetadata, tool: BaseTool) -> None:
    """Register a single legacy agent metadata/tool pair."""
    AGENT_METADATA[metadata.id] = metadata
    AGENT_TOOLS[metadata.id] = tool


def load_metadata_from_dir(path: Path) -> None:
    """Load agent_{id}.json files into the legacy metadata registry."""
    for file in sorted(path.glob("agent_*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            meta = AgentMetadata(**data)
            if meta.id not in AGENT_METADATA:
                AGENT_METADATA[meta.id] = meta
        except Exception:
            continue


def agents_by_layer(layer: str) -> List[str]:
    """Return legacy enabled agent ids assigned to a layer."""
    layer_upper = layer.upper()
    return [
        meta.id
        for meta in sorted(AGENT_METADATA.values(), key=agent_sort_key)
        if (meta.layer or "").upper() == layer_upper and meta.default_enabled
    ]


def agent_sort_key(meta: AgentMetadata) -> tuple[int, int, str]:
    """Sort formal business agents before retained and disabled legacy ids."""
    if meta.business_order is not None:
        return (0, int(meta.business_order), meta.id)
    if meta.business_status == "legacy_retained":
        return (1, 0, meta.id)
    if not meta.default_enabled or meta.business_status == "disabled_historical":
        return (2, 0, meta.id)
    return (1, 1, meta.id)
