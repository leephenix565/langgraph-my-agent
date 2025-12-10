"""Agent protocol, metadata, and registration helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import BaseTool


class AgentInput(Dict[str, Any]):
    """Lightweight dict-compatible AgentInput schema."""

    question: str
    subtask: str
    shared_context: Dict[str, Any]
    history: List[Dict[str, Any]]
    tools_config: Dict[str, Any]


class AgentOutput(Dict[str, Any]):
    """Agent standard output fields."""

    analysis: str
    key_points: List[str]
    evidence: List[str]
    confidence: float


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
    for file in path.glob("agent_*.json"):
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
        aid
        for aid, meta in AGENT_METADATA.items()
        if (meta.layer or "").upper() == layer_upper and meta.default_enabled
    ]
