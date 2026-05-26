import anyio

from react_agent import route_prior_embeddings as embeddings_module
from react_agent.route_profile_registry import RouteProfile


def _profiles() -> list[RouteProfile]:
    return [
        RouteProfile(
            agent_id="a03_macro_industry_research",
            wildcard=False,
            profile_text="description: Macro policy analyst\ncapabilities: macro, policy\ninput_type: macro\nteam: research",
            cost_tier="normal",
            layer="L2",
            team="research",
            input_type="macro",
            capabilities=("macro", "policy"),
        ),
        RouteProfile(
            agent_id="a20_compliance_review",
            wildcard=False,
            profile_text="description: Regulatory and compliance rule review\ncapabilities: compliance, regulatory\ninput_type: compliance\nteam: compliance",
            cost_tier="low",
            layer="L3",
            team="compliance",
            input_type="compliance",
            capabilities=("compliance", "regulatory"),
        ),
    ]


def test_embedding_backend_disabled_fails_open(monkeypatch) -> None:
    monkeypatch.delenv("ROUTE_PRIOR_EMBEDDINGS_ENABLED", raising=False)
    result = anyio.run(
        embeddings_module.retrieve_semantic_matches,
        "Need a quick view",
        _profiles(),
    )
    assert result.enabled is False
    assert result.reason == "disabled_flag_off"
    assert result.matches == ()


def test_profile_embedding_cache_hits_and_misses(monkeypatch) -> None:
    monkeypatch.setenv("ROUTE_PRIOR_EMBEDDINGS_ENABLED", "1")
    monkeypatch.setenv("ROUTE_PRIOR_EMBEDDINGS_MODEL", "text-embedding-test")
    monkeypatch.setenv("ROUTE_PRIOR_OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("ROUTE_PRIOR_OPENAI_BASE_URL", raising=False)
    embeddings_module.reset_profile_embedding_cache()

    call_log: list[tuple[str, ...]] = []

    async def _fake_fetch(texts, config):
        call_log.append(tuple(texts))
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "quick view" in lowered:
                vectors.append((1.0, 0.0))
            elif "macro" in lowered:
                vectors.append((1.0, 0.0))
            else:
                vectors.append((0.0, 1.0))
        return tuple(vectors)

    monkeypatch.setattr(embeddings_module, "fetch_embedding_vectors", _fake_fetch)

    first = anyio.run(
        embeddings_module.retrieve_semantic_matches,
        "Need a quick view",
        _profiles(),
    )
    second = anyio.run(
        embeddings_module.retrieve_semantic_matches,
        "Need a quick view",
        _profiles(),
    )

    assert first.enabled is True
    assert first.cache_hits == 0
    assert first.cache_misses == 2
    assert second.cache_hits == 2
    assert second.cache_misses == 0
    assert len(call_log) == 3
    assert embeddings_module.cached_profile_count() == 2
    assert first.matches[0].agent_id == "a03_macro_industry_research"
