"""Agent typing facade plus lazy legacy registry compatibility exports."""

from __future__ import annotations

from typing import Any

from react_agent.agent_types import AgentInput, AgentOutput

_LEGACY_EXPORTS = (
    "AgentMetadata",
    "AGENT_METADATA",
    "AGENT_TOOLS",
    "register_agent",
    "load_metadata_from_dir",
    "agents_by_layer",
    "agent_sort_key",
    "format_agent_profile",
)


def __getattr__(name: str) -> Any:
    if name in _LEGACY_EXPORTS:
        from react_agent import legacy_agent_registry

        return getattr(legacy_agent_registry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AgentInput",
    "AgentOutput",
    *_LEGACY_EXPORTS,
]
