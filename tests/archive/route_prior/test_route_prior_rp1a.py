import importlib
import sys
import types

import anyio
from langchain_core.messages import AIMessage, HumanMessage

from react_agent import route_prior as route_prior_module
from react_agent.agents import AgentMetadata
from react_agent.context import Context
from react_agent.route_prior_embeddings import SemanticMatch, SemanticRetrievalResult


def _meta(
    agent_id: str,
    *,
    description: str,
    capabilities: list[str],
    input_type: str,
    layer: str,
    team: str,
    cost_level: str = "normal",
    default_enabled: bool = True,
) -> AgentMetadata:
    return AgentMetadata(
        id=agent_id,
        name=agent_id,
        description=description,
        capabilities=capabilities,
        input_type=input_type,
        latency_level="medium",
        cost_level=cost_level,
        version="v0.2",
        layer=layer,
        team=team,
        role_type="system",
        default_enabled=default_enabled,
    )


def _metadata_fixture() -> dict[str, AgentMetadata]:
    return {
        "a01_cio_orchestrator": _meta(
            "a01_cio_orchestrator",
            description="Orchestrator",
            capabilities=["plan"],
            input_type="management",
            layer="L1",
            team="management",
        ),
        "a02_task_router": _meta(
            "a02_task_router",
            description="Reserved router",
            capabilities=["route"],
            input_type="management",
            layer="L1",
            team="management",
            default_enabled=False,
        ),
        "a03_macro_industry_research": _meta(
            "a03_macro_industry_research",
            description="Macro policy analyst.",
            capabilities=["macro", "policy"],
            input_type="macro",
            layer="L2",
            team="research",
        ),
        "a04_commodity_hedging": _meta(
            "a04_commodity_hedging",
            description="Industry layout analyst.",
            capabilities=["industry", "competition"],
            input_type="industry",
            layer="L2",
            team="research",
        ),
        "a05_annual_report_analysis": _meta(
            "a05_annual_report_analysis",
            description="Product pricing analyst.",
            capabilities=["pricing", "inventory"],
            input_type="commodity",
            layer="L2",
            team="research",
        ),
        "a06_financial_statement_analysis": _meta(
            "a06_financial_statement_analysis",
            description="Financial report analyst.",
            capabilities=["filing", "guidance"],
            input_type="finance",
            layer="L2",
            team="research",
        ),
        "a06_financial_statement_analysis": _meta(
            "a06_financial_statement_analysis",
            description="Financial modeling analyst.",
            capabilities=["valuation", "ratios"],
            input_type="finance",
            layer="L2",
            team="research",
            cost_level="low",
        ),
        "a08_industry_hotspot": _meta(
            "a08_industry_hotspot",
            description="Technology due diligence analyst.",
            capabilities=["technology", "moat"],
            input_type="technology",
            layer="L2",
            team="research",
        ),
        "a07_macro_sentiment": _meta(
            "a07_macro_sentiment",
            description="Macro sentiment monitor.",
            capabilities=["macro", "sentiment"],
            input_type="macro",
            layer="L2",
            team="research",
        ),
        "a08_industry_hotspot": _meta(
            "a08_industry_hotspot",
            description="Industry sentiment monitor.",
            capabilities=["industry", "sentiment"],
            input_type="industry",
            layer="L2",
            team="research",
        ),
        "a15_entity_relation_extraction": _meta(
            "a15_entity_relation_extraction",
            description="Cross-domain synthesis and consensus ranking.",
            capabilities=["synthesis", "scenario", "narrative"],
            input_type="research",
            layer="L2",
            team="research",
        ),
        "a20_compliance_review": _meta(
            "a20_compliance_review",
            description="Regulatory compliance review.",
            capabilities=["compliance", "regulatory"],
            input_type="compliance",
            layer="L3",
            team="compliance",
            cost_level="low",
        ),
        "a20_compliance_review": _meta(
            "a20_compliance_review",
            description="Suitability review for client-product risk.",
            capabilities=["suitability", "risk"],
            input_type="compliance",
            layer="L3",
            team="compliance",
            cost_level="low",
        ),
        "a21_portfolio_manager": _meta(
            "a21_portfolio_manager",
            description="Portfolio optimization analyst.",
            capabilities=["allocation", "hedging"],
            input_type="portfolio",
            layer="L3",
            team="portfolio",
        ),
        "a25_report_center": _meta(
            "a25_report_center",
            description="Final answer writer.",
            capabilities=["report", "synthesis"],
            input_type="report",
            layer="L4",
            team="reporting",
        ),
        "a16_ml_valuation": _meta(
            "a16_ml_valuation",
            description="Science and technology valuation analyst.",
            capabilities=["valuation", "technology"],
            input_type="technology",
            layer="L3",
            team="research",
        ),
    }


def _match(agent_id: str, score: float, *, wildcard: bool = False, cost_tier: str = "normal") -> SemanticMatch:
    return SemanticMatch(
        agent_id=agent_id,
        semantic_similarity_score=score,
        wildcard_flag=wildcard,
        cost_tier=cost_tier,
        profile_text=f"profile: {agent_id}",
    )


async def _run_shadow(monkeypatch, matches: tuple[SemanticMatch, ...]) -> dict[str, object]:
    async def _fake_retrieve(question, profiles):
        return SemanticRetrievalResult(
            enabled=True,
            reason="ok",
            backend_signature="test",
            matches=matches,
            cache_hits=1,
            cache_misses=2,
        )

    monkeypatch.setattr(route_prior_module, "retrieve_semantic_matches", _fake_retrieve)
    return await route_prior_module.compute_route_prior_shadow(
        "Need route-prior shadow retrieval.",
        _metadata_fixture(),
    )


def test_route_prior_normal_shortlist_keeps_wildcard(monkeypatch) -> None:
    matches = (
        _match("a03_macro_industry_research", 0.95),
        _match("a04_commodity_hedging", 0.90),
        _match("a05_annual_report_analysis", 0.84),
        _match("a06_financial_statement_analysis", 0.78),
        _match("a06_financial_statement_analysis", 0.72, cost_tier="low"),
        _match("a08_industry_hotspot", 0.67),
        _match("a07_macro_sentiment", 0.61),
        _match("a08_industry_hotspot", 0.59),
        _match("a15_entity_relation_extraction", 0.57, wildcard=True),
        _match("a20_compliance_review", 0.50, cost_tier="low"),
    )

    shadow = anyio.run(_run_shadow, monkeypatch, matches)

    assert shadow["low_confidence_fallback"] is False
    assert 6 <= len(shadow["awake_agents"]) <= 8
    assert "a15_entity_relation_extraction" in shadow["awake_agents"]
    assert shadow["routing_hint"]["confidence_band"] == "normal"
    assert set(shadow["routing_hint"].keys()) == {
        "semantic_summary",
        "shortlist",
        "ranked_items",
        "reason_codes",
        "confidence_band",
    }


def test_route_prior_wide_shortlist_expands_to_eight_to_ten(monkeypatch) -> None:
    matches = (
        _match("a03_macro_industry_research", 0.95),
        _match("a04_commodity_hedging", 0.915),
        _match("a05_annual_report_analysis", 0.91),
        _match("a06_financial_statement_analysis", 0.905),
        _match("a06_financial_statement_analysis", 0.90, cost_tier="low"),
        _match("a08_industry_hotspot", 0.88),
        _match("a07_macro_sentiment", 0.87),
        _match("a08_industry_hotspot", 0.86),
        _match("a15_entity_relation_extraction", 0.85, wildcard=True),
        _match("a20_compliance_review", 0.84, cost_tier="low"),
    )

    shadow = anyio.run(_run_shadow, monkeypatch, matches)

    assert shadow["low_confidence_fallback"] is False
    assert shadow["routing_hint"]["confidence_band"] == "wide"
    assert 8 <= len(shadow["awake_agents"]) <= 10


def test_route_prior_low_confidence_falls_back_to_full_ordinary_pool(monkeypatch) -> None:
    matches = (
        _match("a03_macro_industry_research", 0.80),
        _match("a04_commodity_hedging", 0.79),
        _match("a15_entity_relation_extraction", 0.78, wildcard=True),
    )

    shadow = anyio.run(_run_shadow, monkeypatch, matches)

    assert shadow["low_confidence_fallback"] is True
    assert shadow["routing_hint"]["confidence_band"] == "low"
    assert shadow["awake_agents"] == shadow["ordinary_pool"]


def _load_env_for_import(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    if "langchain_community.tools.tavily_search" not in sys.modules:
        lc_pkg = types.ModuleType("langchain_community")
        tools_pkg = types.ModuleType("langchain_community.tools")
        tavily_mod = types.ModuleType("langchain_community.tools.tavily_search")

        class _DummyTavilySearchResults:
            def __init__(self, max_results=5, search_depth="basic", **kwargs):
                self.max_results = max_results
                self.search_depth = search_depth
                self.name = "tavily_search"

            async def ainvoke(self, *_args, **_kwargs):
                return []

            def invoke(self, *_args, **_kwargs):
                return []

        tavily_mod.TavilySearchResults = _DummyTavilySearchResults
        sys.modules["langchain_community"] = lc_pkg
        sys.modules["langchain_community.tools"] = tools_pkg
        sys.modules["langchain_community.tools.tavily_search"] = tavily_mod

    if "langchain.chat_models" not in sys.modules:
        langchain_pkg = types.ModuleType("langchain")
        chat_models_mod = types.ModuleType("langchain.chat_models")

        def _dummy_init_chat_model(*_args, **_kwargs):
            class _DummyModel:
                async def ainvoke(self, *_a, **_k):
                    return AIMessage(content="{}")

            return _DummyModel()

        chat_models_mod.init_chat_model = _dummy_init_chat_model
        sys.modules["langchain"] = langchain_pkg
        sys.modules["langchain.chat_models"] = chat_models_mod


def _reload_graph(monkeypatch):
    _load_env_for_import(monkeypatch)
    import react_agent.graph as graph_module

    return importlib.reload(graph_module)


class _FakeRouterModel:
    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        return AIMessage(
            content='{"layers":[{"layer":"L1","mode":"Chain","selected":["a01_cio_orchestrator"]},{"layer":"L2","mode":"Star","selected":["a03_macro_industry_research"]},{"layer":"L3","mode":"Star","selected":["a20_compliance_review"]},{"layer":"L4","mode":"Chain","selected":["a25_report_center"]}]}'
        )


def test_router_node_committed_outputs_do_not_change_when_route_prior_enabled(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setattr(graph_module, "load_chat_model", lambda name: _FakeRouterModel())

    state = {"messages": [HumanMessage(content="Need a market view")]}
    runtime_off = types.SimpleNamespace(context=Context(model="fake-model", router_model="fake-router"))
    monkeypatch.setenv("ROUTE_PRIOR_EMBEDDINGS_ENABLED", "0")
    out_off = anyio.run(graph_module.router_node, state, runtime_off)  # type: ignore[arg-type]

    async def _fake_retrieve(question, profiles):
        return SemanticRetrievalResult(
            enabled=True,
            reason="ok",
            backend_signature="test",
            matches=(
                _match("a03_macro_industry_research", 0.90),
                _match("a15_entity_relation_extraction", 0.70, wildcard=True),
            ),
            cache_hits=0,
            cache_misses=max(len(profiles), 1),
        )

    monkeypatch.setenv("ROUTE_PRIOR_EMBEDDINGS_ENABLED", "1")
    monkeypatch.setenv("ROUTE_PRIOR_EMBEDDINGS_MODEL", "text-embedding-test")
    monkeypatch.setenv("ROUTE_PRIOR_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(graph_module.route_prior, "retrieve_semantic_matches", _fake_retrieve)

    runtime_on = types.SimpleNamespace(context=Context(model="fake-model", router_model="fake-router"))
    out_on = anyio.run(graph_module.router_node, state, runtime_on)  # type: ignore[arg-type]

    assert out_off["layer_plan"] == out_on["layer_plan"]
    assert out_off["layer_mode"] == out_on["layer_mode"]
    assert out_off["current_layer"] == out_on["current_layer"]
    assert out_off["plan"] == out_on["plan"]
    assert "route_semantics" not in out_on
    assert "route_scores" not in out_on
    assert "awake_agents" not in out_on
    assert "routing_hint" not in out_on
