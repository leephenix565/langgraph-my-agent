"""Route-prior registry helpers for RP-1A/RP-2B shadow retrieval."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

from react_agent.agents import AgentMetadata

ORDINARY_LAYERS: Tuple[str, ...] = ("L2", "L3")
PROFILE_CARD_SCHEMA_VERSION = "route_profile_card_v0"
PROFILE_CARD_TEXT_FIELDS: Tuple[str, ...] = (
    "positive_examples",
    "negative_examples",
    "when_to_use",
    "when_not_to_use",
    "evidence_expectations",
    "common_misroutes",
    "routing_keywords",
    "risk_tags",
)
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


@dataclass(frozen=True)
class RouteProfileCard:
    """Internal optional RP-2B route profile card."""

    schema_version: str
    agent_id: str
    positive_examples: Tuple[str, ...] = ()
    negative_examples: Tuple[str, ...] = ()
    when_to_use: Tuple[str, ...] = ()
    when_not_to_use: Tuple[str, ...] = ()
    evidence_expectations: Tuple[str, ...] = ()
    common_misroutes: Tuple[str, ...] = ()
    routing_keywords: Tuple[str, ...] = ()
    risk_tags: Tuple[str, ...] = ()
    profile_version: str = ""


@dataclass(frozen=True)
class RouteProfileCardIssue:
    """Deterministic issue record for ignored or invalid profile cards."""

    path: str
    agent_id: str
    reason: str

    def as_dict(self) -> Dict[str, str]:
        """Return a JSON-serializable issue record."""
        return {
            "path": self.path,
            "agent_id": self.agent_id,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RouteProfileCardLoadResult:
    """Loaded internal profile cards plus deterministic load diagnostics."""

    cards: Dict[str, RouteProfileCard]
    invalid_cards: Tuple[RouteProfileCardIssue, ...] = ()
    ignored_cards: Tuple[RouteProfileCardIssue, ...] = ()
    missing_dir: bool = False

    def summary(self) -> Dict[str, object]:
        """Return a compact summary without leaking card text."""
        return {
            "schema_version": PROFILE_CARD_SCHEMA_VERSION,
            "loaded_count": len(self.cards),
            "loaded_agent_ids": sorted(self.cards),
            "invalid_count": len(self.invalid_cards),
            "ignored_count": len(self.ignored_cards),
            "missing_dir": self.missing_dir,
            "invalid_cards": [issue.as_dict() for issue in self.invalid_cards],
            "ignored_cards": [issue.as_dict() for issue in self.ignored_cards],
        }


def _normalize_capabilities(values: Iterable[object]) -> Tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


def _normalize_card_strings(value: object) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError("must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError("must be a list of strings")
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        items.append(normalized)
        seen.add(normalized)
    return tuple(items)


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


def build_card_profile_text(meta: AgentMetadata, card: RouteProfileCard) -> str:
    """Build internal profile text from metadata plus one optional profile card."""
    parts = [build_profile_text(meta)]
    for field_name in PROFILE_CARD_TEXT_FIELDS:
        values = getattr(card, field_name)
        if values:
            parts.append(f"{field_name}: {', '.join(values)}")
    if card.profile_version:
        parts.append(f"profile_version: {card.profile_version}")
    return "\n".join(parts)


def _is_ordinary_agent(agent_id: str, meta: AgentMetadata) -> bool:
    layer = (meta.layer or "").upper()
    return (
        meta.default_enabled
        and layer in ORDINARY_LAYERS
        and agent_id not in ORDINARY_EXCLUDED
    )


def _profile_card_from_payload(payload: Mapping[str, Any]) -> RouteProfileCard:
    schema_version = payload.get("schema_version")
    if schema_version != PROFILE_CARD_SCHEMA_VERSION:
        raise ValueError("invalid schema_version")
    agent_id = payload.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("missing agent_id")
    kwargs: Dict[str, Any] = {
        "schema_version": PROFILE_CARD_SCHEMA_VERSION,
        "agent_id": agent_id.strip(),
    }
    for field_name in PROFILE_CARD_TEXT_FIELDS:
        raw_value = payload.get(field_name, [])
        kwargs[field_name] = _normalize_card_strings(raw_value)
    profile_version = payload.get("profile_version")
    kwargs["profile_version"] = (
        profile_version.strip() if isinstance(profile_version, str) else ""
    )
    return RouteProfileCard(**kwargs)


def load_route_profile_cards(
    cards_dir: Path | str | None,
    metadata_by_id: Mapping[str, AgentMetadata],
) -> RouteProfileCardLoadResult:
    """Load optional internal route profile cards without changing defaults."""
    if cards_dir is None:
        return RouteProfileCardLoadResult(cards={}, missing_dir=True)
    root = Path(cards_dir)
    if not root.exists() or not root.is_dir():
        return RouteProfileCardLoadResult(cards={}, missing_dir=True)

    cards: Dict[str, RouteProfileCard] = {}
    invalid: list[RouteProfileCardIssue] = []
    ignored: list[RouteProfileCardIssue] = []
    for path in sorted(root.glob("*.json")):
        agent_id = ""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("card root must be an object")
            card = _profile_card_from_payload(payload)
            agent_id = card.agent_id
        except Exception as exc:
            invalid.append(
                RouteProfileCardIssue(
                    path=str(path),
                    agent_id=agent_id,
                    reason=f"invalid_card:{type(exc).__name__}:{exc}",
                )
            )
            continue

        meta = metadata_by_id.get(card.agent_id)
        if meta is None:
            ignored.append(
                RouteProfileCardIssue(
                    path=str(path),
                    agent_id=card.agent_id,
                    reason="unknown_agent",
                )
            )
            continue
        if not _is_ordinary_agent(card.agent_id, meta):
            ignored.append(
                RouteProfileCardIssue(
                    path=str(path),
                    agent_id=card.agent_id,
                    reason="non_ordinary_agent",
                )
            )
            continue
        if card.agent_id in cards:
            ignored.append(
                RouteProfileCardIssue(
                    path=str(path),
                    agent_id=card.agent_id,
                    reason="duplicate_agent",
                )
            )
            continue
        cards[card.agent_id] = card
    return RouteProfileCardLoadResult(
        cards=cards,
        invalid_cards=tuple(invalid),
        ignored_cards=tuple(ignored),
    )


def build_route_profile_registry(
    metadata_by_id: Mapping[str, AgentMetadata],
    *,
    profile_cards: Mapping[str, RouteProfileCard] | None = None,
) -> Dict[str, RouteProfile]:
    """Build the tracked RP-1A route-profile registry from agent metadata."""
    registry: Dict[str, RouteProfile] = {}
    for agent_id, meta in sorted(metadata_by_id.items()):
        if not _is_ordinary_agent(agent_id, meta):
            continue
        override = _REGISTRY_OVERRIDES.get(agent_id, {})
        profile_text_override = str(override.get("profile_text_override") or "").strip() or None
        if profile_text_override is None and profile_cards and agent_id in profile_cards:
            profile_text_override = build_card_profile_text(meta, profile_cards[agent_id])
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
