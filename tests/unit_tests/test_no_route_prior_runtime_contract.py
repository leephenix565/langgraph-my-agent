from __future__ import annotations

import importlib
from pathlib import Path
import types

import anyio
from langchain_core.messages import AIMessage, HumanMessage

from react_agent.context import Context
from react_agent.public_contracts import HealthResponse, PublicTurn, WorkflowModel
from react_agent.public_runtime import _has_workflow_snapshot_signal
from react_agent.state import State


class _FakeRouterModel:
    async def ainvoke(self, _msgs, config=None):  # type: ignore[override]
        return AIMessage(
            content=(
                '{"layers":['
                '{"layer":"L1","mode":"Chain","selected":["a01_cio_orchestrator"]},'
                '{"layer":"L2","mode":"Star","selected":["a03_macro_industry_research"]},'
                '{"layer":"L3","mode":"Star","selected":["a20_compliance_review"]},'
                '{"layer":"L4","mode":"Chain","selected":["a25_report_center"]}'
                ']}'
            )
        )


class _CaptureLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def log_event(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))


def _reload_graph_with_legacy_route_prior_env(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("DISABLE_SEARCH", "1")
    monkeypatch.setenv("ROUTE_PRIOR_EMBEDDINGS_ENABLED", "1")
    monkeypatch.setenv("ROUTE_PRIOR_EMBEDDINGS_MODEL", "legacy-ignored")
    monkeypatch.setenv("ROUTE_PRIOR_OPENAI_BASE_URL", "http://127.0.0.1:65535/v1")
    monkeypatch.setenv("ROUTE_PRIOR_OPENAI_API_KEY", "legacy-ignored")
    monkeypatch.setenv("ROUTE_PRIOR_RELIABILITY_ENABLED", "1")
    monkeypatch.setenv("ROUTE_PRIOR_PROFILE_CARDS_DIR", "config/route_profiles")
    monkeypatch.setenv("ROUTE_PRIOR_RELIABILITY_TABLE", "tmp/route-prior-ignored.json")

    import react_agent.graph as graph_module

    return importlib.reload(graph_module)


def test_graph_import_and_router_run_without_route_prior_runtime_seam(monkeypatch) -> None:
    graph_module = _reload_graph_with_legacy_route_prior_env(monkeypatch)
    graph_source = Path(graph_module.__file__).read_text(encoding="utf-8")
    forbidden_source_snippets = {
        "compute_route_prior_shadow",
        "route_reliability.",
        "load_route_profile_cards",
        "route_prior_disabled",
        "route_prior_shadow",
        "route_prior_router_comparison",
    }
    for snippet in forbidden_source_snippets:
        assert snippet not in graph_source

    logger = _CaptureLogger()
    monkeypatch.setattr(graph_module, "get_run_logger", lambda _run_id: logger)
    monkeypatch.setattr(graph_module, "load_chat_model", lambda _name: _FakeRouterModel())

    state = {"messages": [HumanMessage(content="Need a market view")]}
    runtime = types.SimpleNamespace(context=Context(model="fake-model", router_model="fake-router"))

    output = anyio.run(graph_module.router_node, state, runtime)  # type: ignore[arg-type]

    event_names = [event for event, _fields in logger.events]
    assert "router_decision" in event_names
    assert "run_start" in event_names
    assert not any(event.startswith("route_prior") for event in event_names)
    assert "route_reliability_shadow" not in event_names

    assert output["layer_plan"]["L2"] == ["a03_macro_industry_research"]
    assert output["layer_plan"]["L3"] == ["a20_compliance_review"]
    assert output["current_layer"] == "L1"
    assert output["plan"] == ["a01_cio_orchestrator"]

    private_route_keys = {
        "route_prior",
        "route_reliability",
        "route_semantics",
        "route_scores",
        "route_prior_router_comparison",
        "awake_agents",
        "routing_hint",
    }
    assert private_route_keys.isdisjoint(output)
    assert hasattr(graph_module, "graph")


def test_public_contracts_still_do_not_expose_route_prior_fields() -> None:
    forbidden = {
        "route_prior",
        "route_reliability",
        "route_scores",
        "routePrior",
        "routeReliability",
        "routeScores",
        "reliabilityCards",
        "advisory",
    }

    assert forbidden.isdisjoint(WorkflowModel.model_fields)
    assert forbidden.isdisjoint(PublicTurn.model_fields)
    assert forbidden.isdisjoint(HealthResponse.model_fields)
    assert forbidden.isdisjoint(State.__annotations__)
    assert _has_workflow_snapshot_signal(
        {
            "route_prior": {"enabled": False},
            "route_reliability": {"enabled": False},
            "route_prior_router_comparison": {"router_overlap": 0.5},
        }
    ) is False
