"""Route-prior registry helpers for RP-1A embedding-first shadow retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple

from react_agent.agents import AgentMetadata

ORDINARY_LAYERS: Tuple[str, ...] = ("L2", "L3")
ORDINARY_EXCLUDED = {
    "a01_cio_orchestrator",
    "a02_task_router",
    "a25_report_center",
}
_REGISTRY_OVERRIDES: Dict[str, Dict[str, object]] = {
    "a15_research_synthesis": {
        "wildcard": True,
    }
}


@dataclass(frozen=True)
class RouteProfile:
    """Text-first ordinary-agent profile used for RP-1A shadow retrieval."""

    agent_id: str
    wildcard: bool
    profile_text: str
    cost_tier: str
    layer: str
    team: str
    input_type: str
    capabilities: Tuple[str, ...]


def _normalize_capabilities(values: Iterable[object]) -> Tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


def build_profile_text(
    meta: AgentMetadata,
    *,
    profile_text_override: str | None = None,
) -> str:
    """Build a stable labeled profile text from tracked agent metadata."""
    if profile_text_override:
        return profile_text_override.strip()

    capabilities = _normalize_capabilities(meta.capabilities or [])
    parts = []
    if meta.description:
        parts.append(f"description: {meta.description.strip()}")
    if capabilities:
        parts.append(f"capabilities: {', '.join(capabilities)}")
    if meta.input_type:
        parts.append(f"input_type: {meta.input_type.strip()}")
    if meta.team:
        parts.append(f"team: {meta.team.strip()}")
    if not parts:
        parts.append(f"agent_id: {meta.id}")
    return "\n".join(parts)


def _is_ordinary_agent(agent_id: str, meta: AgentMetadata) -> bool:
    layer = (meta.layer or "").upper()
    return (
        meta.default_enabled
        and layer in ORDINARY_LAYERS
        and agent_id not in ORDINARY_EXCLUDED
    )


def build_route_profile_registry(
    metadata_by_id: Mapping[str, AgentMetadata],
) -> Dict[str, RouteProfile]:
    """Build the tracked RP-1A route-profile registry from agent metadata."""
    registry: Dict[str, RouteProfile] = {}
    for agent_id, meta in sorted(metadata_by_id.items()):
        if not _is_ordinary_agent(agent_id, meta):
            continue
        override = _REGISTRY_OVERRIDES.get(agent_id, {})
        profile_text_override = str(override.get("profile_text_override") or "").strip() or None
        registry[agent_id] = RouteProfile(
            agent_id=agent_id,
            wildcard=bool(override.get("wildcard", False)),
            profile_text=build_profile_text(
                meta,
                profile_text_override=profile_text_override,
            ),
            cost_tier=str(meta.cost_level or "").strip().lower(),
            layer=str(meta.layer or "").strip(),
            team=str(meta.team or "").strip(),
            input_type=str(meta.input_type or "").strip(),
            capabilities=_normalize_capabilities(meta.capabilities or []),
        )
    return registry


def ordinary_pool_ids(metadata_by_id: Mapping[str, AgentMetadata]) -> list[str]:
    """Return the tracked ordinary pool ids in deterministic order."""
    return list(build_route_profile_registry(metadata_by_id).keys())
