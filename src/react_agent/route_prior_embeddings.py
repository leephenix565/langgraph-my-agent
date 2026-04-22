"""Embedding backend seam and profile cache for RP-1A route-prior shadowing."""

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

import httpx

from react_agent.route_profile_registry import RouteProfile

OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_PROFILE_EMBEDDING_CACHE: Dict[Tuple[str, str, str], Tuple[float, ...]] = {}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name, "") or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EmbeddingBackendConfig:
    """Private env-backed embedding backend config for RP-1A shadow retrieval."""

    enabled: bool
    reason: str
    model: str = ""
    base_url: str = ""
    api_key: str = ""

    @property
    def signature(self) -> str:
        """Return a stable backend signature for cache partitioning."""
        if not self.enabled:
            return ""
        return f"{self.base_url}|{self.model}"


@dataclass(frozen=True)
class SemanticMatch:
    """A similarity-scored ordinary-agent match produced by the embedding seam."""

    agent_id: str
    semantic_similarity_score: float
    wildcard_flag: bool
    cost_tier: str
    profile_text: str


@dataclass(frozen=True)
class SemanticRetrievalResult:
    """The fail-open retrieval result returned to the RP-1A shadow helper."""

    enabled: bool
    reason: str
    backend_signature: str
    matches: Tuple[SemanticMatch, ...]
    cache_hits: int = 0
    cache_misses: int = 0


def resolve_embedding_backend_config() -> EmbeddingBackendConfig:
    """Resolve the private RP-1A embedding backend config from env."""
    if not _env_flag("ROUTE_PRIOR_EMBEDDINGS_ENABLED", default=False):
        return EmbeddingBackendConfig(enabled=False, reason="disabled_flag_off")

    model = str(os.environ.get("ROUTE_PRIOR_EMBEDDINGS_MODEL", "") or "").strip()
    if not model:
        return EmbeddingBackendConfig(enabled=False, reason="missing_model")

    base_url = (
        str(os.environ.get("ROUTE_PRIOR_OPENAI_BASE_URL", "") or "").strip()
        or str(os.environ.get("OPENAI_BASE_URL", "") or "").strip()
        or OPENAI_DEFAULT_BASE_URL
    ).rstrip("/")
    api_key = (
        str(os.environ.get("ROUTE_PRIOR_OPENAI_API_KEY", "") or "").strip()
        or str(os.environ.get("OPENAI_API_KEY", "") or "").strip()
    )
    if not api_key:
        return EmbeddingBackendConfig(enabled=False, reason="missing_api_key")

    return EmbeddingBackendConfig(
        enabled=True,
        reason="ok",
        model=model,
        base_url=base_url,
        api_key=api_key,
    )


async def fetch_embedding_vectors(
    texts: Sequence[str],
    config: EmbeddingBackendConfig,
) -> Tuple[Tuple[float, ...], ...]:
    """Fetch embeddings from an OpenAI-compatible embeddings endpoint."""
    if not config.enabled:
        raise RuntimeError("embedding backend is disabled")
    payload = {
        "model": config.model,
        "input": list(texts),
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{config.base_url}/embeddings",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    raw_items = body.get("data")
    if not isinstance(raw_items, list):
        raise ValueError("embedding response missing data list")
    ordered = sorted(raw_items, key=lambda item: int(item.get("index", 0)))
    vectors = []
    for item in ordered:
        vector = item.get("embedding")
        if not isinstance(vector, list) or not vector:
            raise ValueError("embedding response missing vector")
        vectors.append(tuple(float(value) for value in vector))
    if len(vectors) != len(texts):
        raise ValueError("embedding response count mismatch")
    return tuple(vectors)


def reset_profile_embedding_cache() -> None:
    """Reset the in-process profile embedding cache."""
    _PROFILE_EMBEDDING_CACHE.clear()


def _profile_cache_key(signature: str, profile: RouteProfile) -> Tuple[str, str, str]:
    text_hash = hashlib.sha256(profile.profile_text.encode("utf-8")).hexdigest()
    return (signature, profile.agent_id, text_hash)


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("embedding dimensions must match and be non-empty")
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


async def retrieve_semantic_matches(
    query_text: str,
    profiles: Sequence[RouteProfile],
) -> SemanticRetrievalResult:
    """Return similarity-ranked ordinary-agent matches for RP-1A shadow retrieval."""
    config = resolve_embedding_backend_config()
    if not config.enabled:
        return SemanticRetrievalResult(
            enabled=False,
            reason=config.reason,
            backend_signature=config.signature,
            matches=(),
        )
    if not profiles:
        return SemanticRetrievalResult(
            enabled=False,
            reason="empty_ordinary_pool",
            backend_signature=config.signature,
            matches=(),
        )

    try:
        query_vectors = await fetch_embedding_vectors([query_text], config)
        query_vector = query_vectors[0]

        cache_hits = 0
        cache_misses = 0
        missing_profiles = []
        missing_texts = []
        profile_vectors: Dict[str, Tuple[float, ...]] = {}

        for profile in profiles:
            cache_key = _profile_cache_key(config.signature, profile)
            cached = _PROFILE_EMBEDDING_CACHE.get(cache_key)
            if cached is not None:
                cache_hits += 1
                profile_vectors[profile.agent_id] = cached
                continue
            cache_misses += 1
            missing_profiles.append((profile, cache_key))
            missing_texts.append(profile.profile_text)

        if missing_texts:
            new_vectors = await fetch_embedding_vectors(missing_texts, config)
            for (profile, cache_key), vector in zip(missing_profiles, new_vectors):
                _PROFILE_EMBEDDING_CACHE[cache_key] = vector
                profile_vectors[profile.agent_id] = vector

        matches = []
        for profile in profiles:
            vector = profile_vectors.get(profile.agent_id)
            if vector is None:
                continue
            matches.append(
                SemanticMatch(
                    agent_id=profile.agent_id,
                    semantic_similarity_score=_cosine_similarity(query_vector, vector),
                    wildcard_flag=profile.wildcard,
                    cost_tier=profile.cost_tier,
                    profile_text=profile.profile_text,
                )
            )
        matches.sort(
            key=lambda item: (
                item.semantic_similarity_score,
                item.wildcard_flag,
                item.agent_id,
            ),
            reverse=True,
        )
        return SemanticRetrievalResult(
            enabled=True,
            reason="ok",
            backend_signature=config.signature,
            matches=tuple(matches),
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )
    except httpx.HTTPError:
        return SemanticRetrievalResult(
            enabled=False,
            reason="backend_http_error",
            backend_signature=config.signature,
            matches=(),
        )
    except Exception:
        return SemanticRetrievalResult(
            enabled=False,
            reason="backend_error",
            backend_signature=config.signature,
            matches=(),
        )


def cache_key_for_profile(signature: str, profile: RouteProfile) -> Tuple[str, str, str]:
    """Expose the cache key shape for tests only."""
    return _profile_cache_key(signature, profile)


def cached_profile_count() -> int:
    """Expose the current cache size for tests only."""
    return len(_PROFILE_EMBEDDING_CACHE)
