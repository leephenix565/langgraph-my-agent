from __future__ import annotations

import importlib
import json
import sys
import types

import anyio
from langchain_core.messages import AIMessage, HumanMessage

from react_agent.context import Context
from react_agent.public_contracts import HealthResponse, PublicTurn, WorkflowModel
from react_agent.public_runtime import _has_workflow_snapshot_signal


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
            content=(
                '{"layers":['
                '{"layer":"L1","mode":"Chain","selected":["a01_cio_orchestrator"]},'
                '{"layer":"L2","mode":"Star","selected":["a03_macro_policy"]},'
                '{"layer":"L3","mode":"Star","selected":["a21_reg_compliance"]},'
                '{"layer":"L4","mode":"Chain","selected":["a25_report_center"]}'
                ']}'
            )
        )


class _CaptureLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def log_event(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))


def _route_prior_shadow() -> dict[str, object]:
    return {
        "enabled": True,
        "shadow_only": True,
        "retrieval_reason": "ok",
        "routing_hint": {
            "confidence_band": "normal",
            "reason_codes": ["semantic:normal"],
        },
        "low_confidence_fallback": False,
        "ordinary_pool": [
            "a03_macro_policy",
            "a21_reg_compliance",
            "a23_portfolio_opt",
        ],
        "awake_agents": ["a03_macro_policy", "a21_reg_compliance"],
        "wildcard_agents": [],
        "route_scores": [
            {
                "agent_id": "a03_macro_policy",
                "semantic_similarity_score": 0.95,
                "wildcard_flag": False,
            },
            {
                "agent_id": "a21_reg_compliance",
                "semantic_similarity_score": 0.9,
                "wildcard_flag": False,
            },
            {
                "agent_id": "a23_portfolio_opt",
                "semantic_similarity_score": 0.45,
                "wildcard_flag": False,
            },
        ],
        "cache_hits": 0,
        "cache_misses": 3,
    }


async def _fake_route_prior_shadow(_question, _metadata):
    return _route_prior_shadow()


def _run_router_node(graph_module, logger: _CaptureLogger, monkeypatch):
    monkeypatch.setattr(graph_module, "get_run_logger", lambda _run_id: logger)
    monkeypatch.setattr(graph_module, "load_chat_model", lambda _name: _FakeRouterModel())
    monkeypatch.setattr(
        graph_module.route_prior,
        "compute_route_prior_shadow",
        _fake_route_prior_shadow,
    )
    state = {"messages": [HumanMessage(content="Need a market compliance view")]}
    runtime = types.SimpleNamespace(
        context=Context(model="fake-model", router_model="fake-router")
    )
    return anyio.run(graph_module.router_node, state, runtime)  # type: ignore[arg-type]


def test_default_env_does_not_emit_reliability_trace_or_change_output(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.delenv("ROUTE_PRIOR_RELIABILITY_ENABLED", raising=False)
    logger = _CaptureLogger()

    output = _run_router_node(graph_module, logger, monkeypatch)

    event_names = [event for event, _fields in logger.events]
    assert "route_prior_shadow" in event_names
    assert "route_reliability_shadow" not in event_names
    assert "route_prior_router_comparison" not in event_names
    assert output["layer_plan"]["L2"] == ["a03_macro_policy"]
    assert output["layer_mode"]["L2"] == "Star"
    assert output["current_layer"] == "L1"
    assert output["plan"] == ["a01_cio_orchestrator"]
    assert "route_reliability" not in output
    assert "route_prior_router_comparison" not in output


def test_enabled_reliability_shadow_is_trace_only_and_compact(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("ROUTE_PRIOR_RELIABILITY_ENABLED", "1")
    monkeypatch.setenv("ROUTE_PRIOR_TRACE_TOP_CARDS", "2")
    logger = _CaptureLogger()

    output = _run_router_node(graph_module, logger, monkeypatch)

    assert output["layer_plan"]["L2"] == ["a03_macro_policy"]
    assert output["layer_plan"]["L3"] == ["a21_reg_compliance"]
    assert output["layer_mode"]["L3"] == "Star"
    assert output["current_layer"] == "L1"
    assert "route_reliability" not in output
    trace = dict(logger.events)["route_reliability_shadow"]
    comparison = dict(logger.events)["route_prior_router_comparison"]

    assert trace["schema_version"] == "route_reliability_shadow_v0"
    assert trace["algorithm"] == "rarp_v0"
    assert trace["shadow_only"] == 1
    assert trace["confidence_band"] == "normal"
    assert trace["top_card_ids"] == ["a03_macro_policy", "a21_reg_compliance"]
    assert comparison["schema_version"] == "route_prior_router_comparison_v0"

    encoded_trace = json.dumps(trace, ensure_ascii=False).lower()
    assert "profile_text" not in encoded_trace
    assert "embedding" not in encoded_trace
    assert "cards" not in trace


def test_reliability_scorer_error_fails_open(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("ROUTE_PRIOR_RELIABILITY_ENABLED", "1")

    def _raise_scorer(**_kwargs):
        raise RuntimeError("scorer exploded")

    monkeypatch.setattr(
        graph_module.route_reliability,
        "build_route_reliability_shadow",
        _raise_scorer,
    )
    logger = _CaptureLogger()

    output = _run_router_node(graph_module, logger, monkeypatch)

    assert output["layer_plan"]["L2"] == ["a03_macro_policy"]
    assert output["current_layer"] == "L1"
    events = dict(logger.events)
    assert "route_reliability_error" in events
    assert events["route_reliability_error"]["fail_open"] == 1
    assert "route_prior_router_comparison" not in events


def test_public_contract_workflow_health_do_not_gain_route_prior_fields() -> None:
    forbidden = {
        "routePrior",
        "routeReliability",
        "routeScores",
        "reliabilityCards",
        "advisory",
    }

    assert forbidden.isdisjoint(WorkflowModel.model_fields)
    assert forbidden.isdisjoint(PublicTurn.model_fields)
    assert forbidden.isdisjoint(HealthResponse.model_fields)
    assert _has_workflow_snapshot_signal(
        {
            "route_prior": {"enabled": True},
            "route_reliability": {"enabled": True},
            "route_prior_router_comparison": {"router_overlap": 0.5},
        }
    ) is False
