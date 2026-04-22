"""RP-1A embedding-first route-prior shadow helpers."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from react_agent.agents import AgentMetadata
from react_agent.route_prior_embeddings import SemanticMatch, retrieve_semantic_matches
from react_agent.route_profile_registry import build_route_profile_registry

NORMAL_BASE_SHORTLIST = 6
NORMAL_SHORTLIST_CAP = 8
WIDE_BASE_SHORTLIST = 8
WIDE_SHORTLIST_CAP = 10
WILDCARD_KEEP_MIN = 1
WILDCARD_KEEP_MAX = 2
SHORTLIST_TIE_EPSILON = 0.02
LOW_CONFIDENCE_MARGIN = 0.03
WIDE_SCORE_BAND = 0.05


def _cost_tiebreak_score(cost_tier: str) -> float:
    tier = str(cost_tier or "").strip().lower()
    if tier == "low":
        return 1.0
    if tier == "normal":
        return 0.5
    return 0.0


def _rank_matches(matches: Sequence[SemanticMatch]) -> list[SemanticMatch]:
    return sorted(
        matches,
        key=lambda match: (
            match.semantic_similarity_score,
            _cost_tiebreak_score(match.cost_tier),
            match.wildcard_flag,
            match.agent_id,
        ),
        reverse=True,
    )


def _classify_confidence_band(matches: Sequence[SemanticMatch]) -> str:
    if len(matches) < 2:
        return "low"
    if matches[0].semantic_similarity_score - matches[1].semantic_similarity_score < LOW_CONFIDENCE_MARGIN:
        return "low"
    if len(matches) >= 5 and (
        matches[0].semantic_similarity_score - matches[4].semantic_similarity_score
    ) <= WIDE_SCORE_BAND:
        return "wide"
    return "normal"


def _should_full_pool_fallback(matches: Sequence[SemanticMatch], enabled: bool) -> bool:
    if not enabled:
        return True
    if len(matches) < 2:
        return True
    return matches[0].semantic_similarity_score - matches[1].semantic_similarity_score < LOW_CONFIDENCE_MARGIN


def _select_ranked_shortlist(
    matches: Sequence[SemanticMatch],
    *,
    confidence_band: str,
) -> list[str]:
    if not matches:
        return []

    if confidence_band == "wide":
        base = min(WIDE_BASE_SHORTLIST, len(matches))
        cap = min(WIDE_SHORTLIST_CAP, len(matches))
    else:
        base = min(NORMAL_BASE_SHORTLIST, len(matches))
        cap = min(NORMAL_SHORTLIST_CAP, len(matches))

    cutoff = matches[base - 1].semantic_similarity_score
    selected = [
        match.agent_id
        for match in matches
        if match.semantic_similarity_score >= (cutoff - SHORTLIST_TIE_EPSILON)
    ]
    return selected[:cap]


def _apply_wildcard_guardrail(
    shortlist: list[str],
    wildcard_ids: Sequence[str],
    ranked_agent_ids: Sequence[str],
    *,
    cap: int,
) -> list[str]:
    kept = list(shortlist)
    desired = list(wildcard_ids[:WILDCARD_KEEP_MAX])
    for wildcard_id in desired[:WILDCARD_KEEP_MIN]:
        if wildcard_id in kept or wildcard_id not in ranked_agent_ids:
            continue
        if len(kept) < cap:
            kept.append(wildcard_id)
        elif kept:
            kept[-1] = wildcard_id
        else:
            kept.append(wildcard_id)

    deduped: list[str] = []
    seen = set()
    for agent_id in kept:
        if agent_id in seen:
            continue
        seen.add(agent_id)
        deduped.append(agent_id)
    return deduped[:cap]


def _build_reason_codes(
    *,
    retrieval_reason: str,
    confidence_band: str,
    low_confidence_fallback: bool,
    wildcard_injected: bool,
) -> list[str]:
    codes = [f"retrieval:{retrieval_reason}", f"band:{confidence_band}"]
    if low_confidence_fallback:
        codes.append("fallback:full_ordinary_pool")
    if wildcard_injected:
        codes.append("guardrail:wildcard_retained")
    return codes


def _build_semantic_summary(
    confidence_band: str,
    shortlist: Sequence[str],
    ranked_matches: Sequence[SemanticMatch],
) -> str:
    top_agents = ", ".join(match.agent_id for match in ranked_matches[:3]) or "none"
    return (
        f"RP-1A shadow band={confidence_band}; "
        f"shortlist={len(shortlist)}; "
        f"top_matches={top_agents}"
    )


async def compute_route_prior_shadow(
    question: str,
    metadata_by_id: Mapping[str, AgentMetadata],
) -> Dict[str, Any]:
    """Compute RP-1A shadow retrieval artifacts without mutating graph state."""
    registry = build_route_profile_registry(metadata_by_id)
    profiles = list(registry.values())
    ordinary_pool = list(registry.keys())
    wildcard_ids = [profile.agent_id for profile in profiles if profile.wildcard]

    retrieval = await retrieve_semantic_matches(question, profiles)
    ranked_matches = _rank_matches(retrieval.matches)
    ranked_agent_ids = [match.agent_id for match in ranked_matches]
    confidence_band = _classify_confidence_band(ranked_matches)
    low_confidence_fallback = _should_full_pool_fallback(ranked_matches, retrieval.enabled)

    wildcard_injected = False
    if low_confidence_fallback:
        shortlist = list(ordinary_pool)
        confidence_band = "low"
    else:
        shortlist = _select_ranked_shortlist(ranked_matches, confidence_band=confidence_band)
        cap = WIDE_SHORTLIST_CAP if confidence_band == "wide" else NORMAL_SHORTLIST_CAP
        guarded = _apply_wildcard_guardrail(
            shortlist,
            wildcard_ids,
            ranked_agent_ids,
            cap=cap,
        )
        wildcard_injected = any(
            agent_id not in shortlist for agent_id in guarded if agent_id in wildcard_ids
        )
        shortlist = guarded

    route_scores = [
        {
            "agent_id": match.agent_id,
            "semantic_similarity_score": match.semantic_similarity_score,
            "cost_tiebreak_score": _cost_tiebreak_score(match.cost_tier),
            "wildcard_flag": match.wildcard_flag,
            "confidence_band": confidence_band,
        }
        for match in ranked_matches
    ]
    top_profile_matches = [
        {
            "agent_id": match.agent_id,
            "semantic_similarity_score": match.semantic_similarity_score,
            "wildcard_flag": match.wildcard_flag,
        }
        for match in ranked_matches[:5]
    ]
    reason_codes = _build_reason_codes(
        retrieval_reason=retrieval.reason,
        confidence_band=confidence_band,
        low_confidence_fallback=low_confidence_fallback,
        wildcard_injected=wildcard_injected,
    )
    semantic_summary = _build_semantic_summary(confidence_band, shortlist, ranked_matches)

    return {
        "enabled": retrieval.enabled,
        "retrieval_reason": retrieval.reason,
        "route_semantics": {
            "semantic_query_text": question,
            "top_profile_matches": top_profile_matches,
            "similarity_confidence_band": confidence_band,
            "retrieval_notes": reason_codes,
        },
        "route_scores": route_scores,
        "awake_agents": shortlist,
        "routing_hint": {
            "semantic_summary": semantic_summary,
            "shortlist": shortlist,
            "ranked_items": route_scores[:10],
            "reason_codes": reason_codes,
            "confidence_band": confidence_band,
        },
        "ordinary_pool": ordinary_pool,
        "wildcard_agents": wildcard_ids,
        "low_confidence_fallback": low_confidence_fallback,
        "cache_hits": retrieval.cache_hits,
        "cache_misses": retrieval.cache_misses,
        "shadow_only": True,
    }
