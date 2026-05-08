"""Deterministic RP-2B/RP-2C route reliability helpers."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from react_agent.agents import AgentMetadata
from react_agent.route_profile_registry import RouteProfileCard

JsonDict = dict[str, Any]
JsonMapping = Mapping[str, Any]

ALGORITHM = "rarp_v0"
SHADOW_SCHEMA_VERSION = "route_reliability_shadow_v0"
ROUTER_COMPARISON_SCHEMA_VERSION = "route_prior_router_comparison_v0"
RELIABILITY_ENABLED_ENV = "ROUTE_PRIOR_RELIABILITY_ENABLED"
PROFILE_CARDS_DIR_ENV = "ROUTE_PRIOR_PROFILE_CARDS_DIR"
RELIABILITY_TABLE_ENV = "ROUTE_PRIOR_RELIABILITY_TABLE"
TRACE_TOP_CARDS_ENV = "ROUTE_PRIOR_TRACE_TOP_CARDS"
COLD_START_RELIABILITY = 0.50
COLD_START_UNCERTAINTY = 1.00
QUERY_TYPE_PRIOR = 0.50
WILDCARD_BONUS = 0.00
SMOOTHING_ALPHA = 2.0
SMOOTHING_BETA = 2.0

COST_PENALTY = {
    "low": 0.0,
    "normal": 0.5,
    "medium": 0.5,
    "high": 1.0,
    "unknown": 0.5,
    "": 0.5,
}
_TRUTHY = {"1", "true", "yes", "on"}
_COMPARISON_GROUP_KEYS = (
    "strongly_recommended",
    "candidate",
    "wildcard",
    "deprioritized",
)


@dataclass(frozen=True)
class ReliabilityStats:
    """Historical route reliability values for one agent."""

    reliability: float = COLD_START_RELIABILITY
    uncertainty: float = COLD_START_UNCERTAINTY
    source: str = "cold_start"


@dataclass(frozen=True)
class RuntimeReliabilityConfig:
    """Private runtime config for RP-2C shadow tracing."""

    enabled: bool = False
    profile_cards_dir: str = ""
    reliability_table_path: str = ""
    trace_top_cards: int = 5


def _env_flag(value: object) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


def _env_positive_int(value: object, *, default: int) -> int:
    try:
        parsed = int(str(value or "").strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def runtime_reliability_config_from_env(
    environ: Mapping[str, str] | None = None,
) -> RuntimeReliabilityConfig:
    """Return env-gated private RP-2C runtime config without touching health."""
    env = environ if environ is not None else os.environ
    return RuntimeReliabilityConfig(
        enabled=_env_flag(env.get(RELIABILITY_ENABLED_ENV)),
        profile_cards_dir=str(env.get(PROFILE_CARDS_DIR_ENV, "") or "").strip(),
        reliability_table_path=str(env.get(RELIABILITY_TABLE_ENV, "") or "").strip(),
        trace_top_cards=_env_positive_int(env.get(TRACE_TOP_CARDS_ENV), default=5),
    )


def _clamp(value: object, *, default: float, lower: float = 0.0, upper: float = 1.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(lower, min(upper, parsed))


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _as_mapping(value: object) -> JsonMapping:
    return value if isinstance(value, Mapping) else {}


def _ordered_unique(values: Sequence[object]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def load_reliability_table(path: Path | str | None) -> JsonDict:
    """Load an optional internal reliability table."""
    if path is None:
        return {}
    raw_path = Path(path)
    if not raw_path.exists():
        return {}
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def cost_penalty_for_level(cost_level: str) -> float:
    """Return the deterministic RP-2B cost penalty for a metadata cost level."""
    normalized = str(cost_level or "").strip().lower()
    return COST_PENALTY.get(normalized, COST_PENALTY["unknown"])


def score_band(score: float) -> str:
    """Return high/medium/low score band for one combined route score."""
    if score >= 0.75:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def priority_for_score(
    score: float,
    *,
    historical_uncertainty: float,
    low_confidence_fallback: bool,
) -> str:
    """Return RP-2B priority group for one route card."""
    if score >= 0.75 and historical_uncertainty <= 0.35 and not low_confidence_fallback:
        return "strong"
    if score >= 0.55:
        return "candidate"
    if score >= 0.35:
        return "deprioritized"
    return "hidden"


def _stats_from_payload(payload: JsonMapping) -> ReliabilityStats:
    if "historical_reliability" in payload or "historical_uncertainty" in payload:
        return ReliabilityStats(
            reliability=_clamp(
                payload.get("historical_reliability"),
                default=COLD_START_RELIABILITY,
            ),
            uncertainty=_clamp(
                payload.get("historical_uncertainty"),
                default=COLD_START_UNCERTAINTY,
            ),
            source="table",
        )

    trials = _clamp(payload.get("trials"), default=0.0, lower=0.0, upper=1_000_000.0)
    successes = _clamp(payload.get("successes"), default=0.0, lower=0.0, upper=trials)
    if trials <= 0:
        return ReliabilityStats()
    denominator = trials + SMOOTHING_ALPHA + SMOOTHING_BETA
    return ReliabilityStats(
        reliability=(successes + SMOOTHING_ALPHA) / denominator,
        uncertainty=1.0 / math.sqrt(denominator),
        source="table_smoothed",
    )


def reliability_stats_for_agent(
    agent_id: str,
    reliability_table: JsonMapping | None,
    *,
    task_type: str = "",
) -> ReliabilityStats:
    """Return table-backed or cold-start reliability stats for one agent."""
    table = reliability_table or {}
    by_task_type = _as_mapping(table.get("by_task_type"))
    if task_type:
        task_bucket = _as_mapping(by_task_type.get(task_type))
        task_payload = _as_mapping(task_bucket.get(agent_id))
        if task_payload:
            return _stats_from_payload(task_payload)

    global_payload = _as_mapping(_as_mapping(table.get("global")).get(agent_id))
    if global_payload:
        return _stats_from_payload(global_payload)
    return ReliabilityStats()


def _score_items(route_scores: Sequence[JsonMapping]) -> list[JsonMapping]:
    return [item for item in route_scores if isinstance(item, Mapping)]


def _metadata_cost(agent_id: str, metadata_by_id: Mapping[str, AgentMetadata]) -> str:
    meta = metadata_by_id.get(agent_id)
    return str(getattr(meta, "cost_level", "") or "").strip().lower()


def _reason_codes(
    *,
    semantic_relevance: float,
    stats: ReliabilityStats,
    wildcard_flag: bool,
    cost_penalty: float,
    priority: str,
    profile_card_present: bool,
) -> list[str]:
    if semantic_relevance >= 0.75:
        semantic_code = "semantic:high"
    elif semantic_relevance >= 0.55:
        semantic_code = "semantic:medium"
    else:
        semantic_code = "semantic:low"
    history_code = "history:cold_start" if stats.source == "cold_start" else "history:table"
    cost_code = "cost:high" if cost_penalty >= 1.0 else "cost:normal"
    if cost_penalty <= 0:
        cost_code = "cost:low"
    codes = [
        semantic_code,
        history_code,
        cost_code,
        f"priority:{priority}",
        "profile_card:present" if profile_card_present else "profile_card:metadata_fallback",
    ]
    if wildcard_flag:
        codes.append("guardrail:wildcard")
    return codes


def _selection_hint(priority: str) -> str:
    if priority == "strong":
        return "recommended"
    if priority == "candidate":
        return "candidate"
    if priority == "deprioritized":
        return "deprioritized"
    return "hidden"


def build_reliability_cards(
    *,
    route_scores: Sequence[JsonMapping],
    metadata_by_id: Mapping[str, AgentMetadata],
    reliability_table: JsonMapping | None = None,
    profile_cards: Mapping[str, RouteProfileCard] | None = None,
    low_confidence_fallback: bool = False,
    task_type: str = "",
) -> list[JsonDict]:
    """Build deterministic internal route reliability cards from RP-1A scores."""
    cards: list[JsonDict] = []
    for item in _score_items(route_scores):
        agent_id = str(item.get("agent_id", "") or "").strip()
        if not agent_id:
            continue
        semantic_relevance = _clamp(
            item.get("semantic_similarity_score"),
            default=0.0,
        )
        profile_match = semantic_relevance
        stats = reliability_stats_for_agent(
            agent_id,
            reliability_table,
            task_type=task_type,
        )
        cost_penalty = cost_penalty_for_level(_metadata_cost(agent_id, metadata_by_id))
        wildcard_flag = bool(item.get("wildcard_flag", False))
        combined = (
            0.45 * semantic_relevance
            + 0.20 * profile_match
            + 0.20 * stats.reliability
            + 0.05 * QUERY_TYPE_PRIOR
            + 0.05 * WILDCARD_BONUS
            - 0.10 * stats.uncertainty
            - 0.05 * cost_penalty
        )
        combined = _clamp(combined, default=0.0)
        priority = priority_for_score(
            combined,
            historical_uncertainty=stats.uncertainty,
            low_confidence_fallback=low_confidence_fallback,
        )
        profile_card_present = bool(profile_cards and agent_id in profile_cards)
        cards.append(
            {
                "agent_id": agent_id,
                "priority": priority,
                "score_band": score_band(combined),
                "combined_route_score": round(combined, 6),
                "semantic_relevance": round(semantic_relevance, 6),
                "profile_match": round(profile_match, 6),
                "historical_reliability": round(stats.reliability, 6),
                "historical_uncertainty": round(stats.uncertainty, 6),
                "cost_penalty": round(cost_penalty, 6),
                "wildcard_flag": wildcard_flag,
                "reason_codes": _reason_codes(
                    semantic_relevance=semantic_relevance,
                    stats=stats,
                    wildcard_flag=wildcard_flag,
                    cost_penalty=cost_penalty,
                    priority=priority,
                    profile_card_present=profile_card_present,
                ),
                "selection_hint": _selection_hint(priority),
            }
        )
    return sorted(
        cards,
        key=lambda card: (
            -float(card["combined_route_score"]),
            -float(card["semantic_relevance"]),
            str(card["agent_id"]),
        ),
    )


def group_reliability_cards(cards: Sequence[JsonMapping]) -> JsonDict:
    """Group reliability cards into RP-2B route-prior advisory buckets."""
    groups: JsonDict = {
        "strongly_recommended": [],
        "candidate": [],
        "wildcard": [],
        "deprioritized": [],
    }
    for card in cards:
        agent_id = str(card.get("agent_id", "") or "")
        if not agent_id:
            continue
        priority = str(card.get("priority", "") or "")
        if priority == "strong":
            groups["strongly_recommended"].append(agent_id)
        elif priority == "candidate":
            groups["candidate"].append(agent_id)
        elif priority == "deprioritized":
            groups["deprioritized"].append(agent_id)
        if bool(card.get("wildcard_flag", False)):
            groups["wildcard"].append(agent_id)
    return groups


def _card_list(shadow: JsonMapping) -> list[JsonMapping]:
    cards = shadow.get("cards")
    if not isinstance(cards, list):
        return []
    return [card for card in cards if isinstance(card, Mapping)]


def _group_ids(groups: JsonMapping, key: str) -> list[str]:
    return _ordered_unique(_as_str_list(groups.get(key)))


def compact_reliability_trace_payload(
    shadow: JsonMapping,
    *,
    top_n: int = 5,
) -> JsonDict:
    """Return a compact no-text/no-embedding runtime trace payload."""
    safe_shadow = _as_mapping(shadow)
    groups = _as_mapping(safe_shadow.get("groups"))
    cards = _card_list(safe_shadow)
    top_cards = cards[: max(0, top_n)]
    compact_groups = {
        key: _group_ids(groups, key)
        for key in _COMPARISON_GROUP_KEYS
    }
    return {
        "schema_version": str(safe_shadow.get("schema_version") or SHADOW_SCHEMA_VERSION),
        "algorithm": str(safe_shadow.get("algorithm") or ALGORITHM),
        "shadow_only": 1 if bool(safe_shadow.get("shadow_only", True)) else 0,
        "confidence_band": str(safe_shadow.get("confidence_band", "") or ""),
        "low_confidence_fallback": 1 if bool(safe_shadow.get("low_confidence_fallback")) else 0,
        "ordinary_pool_size": int(safe_shadow.get("ordinary_pool_size", 0) or 0),
        "card_count": len(cards),
        "group_counts": {key: len(ids) for key, ids in compact_groups.items()},
        "groups": compact_groups,
        "top_card_ids": [
            str(card.get("agent_id", "") or "")
            for card in top_cards
            if str(card.get("agent_id", "") or "").strip()
        ],
        "score_bands": {
            str(card.get("agent_id", "") or ""): str(card.get("score_band", "") or "")
            for card in top_cards
            if str(card.get("agent_id", "") or "").strip()
        },
        "reason_codes_by_agent": {
            str(card.get("agent_id", "") or ""): _as_str_list(card.get("reason_codes"))
            for card in top_cards
            if str(card.get("agent_id", "") or "").strip()
        },
    }


def _flatten_layer_plan(layer_plan: JsonMapping) -> list[str]:
    selected: list[str] = []
    for value in layer_plan.values():
        if isinstance(value, list):
            selected.extend(value)
    return _ordered_unique(selected)


def _comparison_overlap(prior_ids: list[str], router_ids: list[str]) -> float:
    prior = set(prior_ids)
    router = set(router_ids)
    union = prior | router
    if not union:
        return 0.0
    return round(len(prior & router) / len(union), 6)


def _overlap_reason(overlap: float, *, has_universe: bool) -> str:
    if not has_universe:
        return "overlap:none"
    if overlap >= 0.8:
        return "overlap:high"
    if overlap >= 0.5:
        return "overlap:medium"
    return "overlap:low"


def compare_route_prior_to_router(
    reliability_shadow: JsonMapping | None,
    layer_plan: JsonMapping | None,
) -> JsonDict:
    """Compare RP-2C reliability shadow to parsed Router output without mutation."""
    shadow = _as_mapping(reliability_shadow)
    groups = _as_mapping(shadow.get("groups"))
    cards = _card_list(shadow)
    card_ids = _ordered_unique([card.get("agent_id") for card in cards])
    if not card_ids:
        card_ids = _ordered_unique(
            [
                agent_id
                for key in _COMPARISON_GROUP_KEYS
                for agent_id in _group_ids(groups, key)
            ]
        )

    strong_ids = _group_ids(groups, "strongly_recommended")
    deprioritized_ids = _group_ids(groups, "deprioritized")
    prior_ids = _ordered_unique(
        [
            agent_id
            for key in _COMPARISON_GROUP_KEYS
            for agent_id in _group_ids(groups, key)
        ]
    )
    router_selected = _flatten_layer_plan(_as_mapping(layer_plan))
    card_id_set = set(card_ids)
    router_ordinary = [
        agent_id for agent_id in router_selected
        if card_id_set and agent_id in card_id_set
    ]

    prior_set = set(prior_ids)
    router_set = set(router_ordinary)
    prior_only = [agent_id for agent_id in prior_ids if agent_id not in router_set]
    router_only = [agent_id for agent_id in router_ordinary if agent_id not in prior_set]
    omitted_strong = [agent_id for agent_id in strong_ids if agent_id not in router_set]
    selected_deprioritized = [
        agent_id for agent_id in deprioritized_ids if agent_id in router_set
    ]
    overlap = _comparison_overlap(prior_ids, router_ordinary)
    has_universe = bool(prior_ids or router_ordinary)
    if omitted_strong or selected_deprioritized:
        disagreement_band = "high"
    elif prior_only or router_only:
        disagreement_band = "medium"
    else:
        disagreement_band = "low"

    reason_codes = [_overlap_reason(overlap, has_universe=has_universe)]
    if omitted_strong:
        reason_codes.append(f"omitted_strong_recommended:{len(omitted_strong)}")
    if selected_deprioritized:
        reason_codes.append(f"selected_deprioritized:{len(selected_deprioritized)}")
    if prior_only:
        reason_codes.append(f"prior_only:{len(prior_only)}")
    if router_only:
        reason_codes.append(f"router_only:{len(router_only)}")

    return {
        "schema_version": ROUTER_COMPARISON_SCHEMA_VERSION,
        "prior_confidence_band": str(shadow.get("confidence_band", "") or ""),
        "router_overlap": overlap,
        "prior_only_agents": prior_only,
        "router_only_agents": router_only,
        "omitted_strong_recommended": omitted_strong,
        "selected_deprioritized": selected_deprioritized,
        "disagreement_band": disagreement_band,
        "reason_codes": reason_codes,
    }


def build_route_reliability_shadow(
    *,
    route_scores: Sequence[JsonMapping],
    metadata_by_id: Mapping[str, AgentMetadata],
    ordinary_pool: Sequence[str],
    wildcard_agents: Sequence[str],
    reliability_table: JsonMapping | None = None,
    profile_cards: Mapping[str, RouteProfileCard] | None = None,
    low_confidence_fallback: bool = False,
    confidence_band: str = "",
    task_type: str = "",
) -> JsonDict:
    """Build an internal RP-2B reliability shadow object."""
    cards = build_reliability_cards(
        route_scores=route_scores,
        metadata_by_id=metadata_by_id,
        reliability_table=reliability_table,
        profile_cards=profile_cards,
        low_confidence_fallback=low_confidence_fallback,
        task_type=task_type,
    )
    return {
        "schema_version": SHADOW_SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "shadow_only": True,
        "enabled": True,
        "confidence_band": confidence_band,
        "low_confidence_fallback": low_confidence_fallback,
        "ordinary_pool_size": len(list(ordinary_pool)),
        "wildcard_agents": _as_str_list(list(wildcard_agents)),
        "card_count": len(cards),
        "profile_card_count": len(profile_cards or {}),
        "cards": cards,
        "groups": group_reliability_cards(cards),
    }
