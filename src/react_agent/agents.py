"""Agent protocol, metadata, and registration helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import BaseTool
from typing_extensions import TypedDict


class AgentInput(Dict[str, Any]):
    """Lightweight dict-compatible AgentInput schema."""

    question: str
    subtask: str
    shared_context: Dict[str, Any]
    history: List[Dict[str, Any]]
    tools_config: Dict[str, Any]


class AgentOutput(TypedDict, total=False):
    """Dict-shaped Agent output surface used by runtime and Studio schema export.

    Runtime callers still pass and consume plain dict objects. This type surface
    only narrows the commonly-used keys so Pydantic / LangGraph can emit a JSON
    schema for Studio without changing the graph's dict-style behavior.
    """

    analysis: str
    key_points: List[str]
    evidence: List[str]
    confidence: float
    parse_ok: bool
    contract: Dict[str, Any] | str


@dataclass
class AgentMetadata:
    """Metadata used by Router / Manager."""

    id: str
    name: str
    description: str
    capabilities: List[str]
    input_type: str
    latency_level: str
    cost_level: str
    version: str
    layer: Optional[str] = None
    team: Optional[str] = None
    role_type: Optional[str] = None
    business_order: Optional[int] = None
    business_role: Optional[str] = None
    business_status: Optional[str] = None
    business_layer: Optional[str] = None
    business_category: Optional[str] = None
    business_subcategory: Optional[str] = None
    default_enabled: bool = True


# Runtime registries (includes built-ins + loaded metadata).
AGENT_METADATA: Dict[str, AgentMetadata] = {}
AGENT_TOOLS: Dict[str, BaseTool] = {}


def register_agent(metadata: AgentMetadata, tool: BaseTool) -> None:
    """Register a single agent's metadata and tool."""
    AGENT_METADATA[metadata.id] = metadata
    AGENT_TOOLS[metadata.id] = tool


def load_metadata_from_dir(path: Path) -> None:
    """Load agent_{id}.json from a directory into AGENT_METADATA."""
    for file in sorted(path.glob("agent_*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            meta = AgentMetadata(**data)
            if meta.id not in AGENT_METADATA:
                AGENT_METADATA[meta.id] = meta
        except Exception:
            continue


def agents_by_layer(layer: str) -> List[str]:
    """Return agent ids assigned to a given layer and enabled."""
    layer_upper = layer.upper()
    return [
        meta.id
        for meta in sorted(AGENT_METADATA.values(), key=agent_sort_key)
        if (meta.layer or "").upper() == layer_upper and meta.default_enabled
    ]


def agent_sort_key(meta: AgentMetadata) -> tuple[int, int, str]:
    """Sort formal business agents by business_order before legacy/historical ids."""
    if meta.business_order is not None:
        return (0, int(meta.business_order), meta.id)
    if meta.business_status == "legacy_retained":
        return (1, 0, meta.id)
    if not meta.default_enabled or meta.business_status == "disabled_historical":
        return (2, 0, meta.id)
    return (1, 1, meta.id)
