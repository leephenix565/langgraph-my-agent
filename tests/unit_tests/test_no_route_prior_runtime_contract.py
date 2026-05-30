from __future__ import annotations

import importlib
import json
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


class _StaticRouterModel:
    def __init__(self, content: str) -> None:
        self.content = content

    async def ainvoke(self, _msgs, config=None):  # type: ignore[override]
        return AIMessage(content=self.content)


class _RaisingRouterModel:
    async def ainvoke(self, _msgs, config=None):  # type: ignore[override]
        raise Exception("boom")


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


def _flatten_selected(layer_plan: dict[str, list[str]]) -> list[str]:
    return [
        agent_id
        for layer in ("L1", "L2", "L3", "L4")
        for agent_id in layer_plan.get(layer, [])
    ]


def _router_parse_stats(logger: _CaptureLogger) -> dict[str, object]:
    for event, fields in logger.events:
        if event == "run_start":
            stats = fields.get("router_parse_stats")
            if isinstance(stats, dict):
                return stats
    raise AssertionError("run_start router_parse_stats not captured")


def _assert_no_raw_router_payload_in_logs(logger: _CaptureLogger, forbidden: str) -> None:
    for _event, fields in logger.events:
        assert "raw" not in fields
        assert forbidden not in json.dumps(fields, ensure_ascii=False)


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


def test_provider_exception_records_safe_telemetry_and_fails_closed(monkeypatch) -> None:
    graph_module = _reload_graph_with_legacy_route_prior_env(monkeypatch)
    logger = _CaptureLogger()
    monkeypatch.setattr(graph_module, "get_run_logger", lambda _run_id: logger)
    monkeypatch.setattr(graph_module, "load_chat_model", lambda _name: _RaisingRouterModel())

    state = {"messages": [HumanMessage(content="Need a market view")]}
    runtime = types.SimpleNamespace(context=Context(model="fake-model", router_model="fake-router"))

    output = anyio.run(graph_module.router_node, state, runtime)  # type: ignore[arg-type]
    stats = _router_parse_stats(logger)

    assert _flatten_selected(output["layer_plan"]) == ["a01_cio_orchestrator", "a25_report_center"]
    assert stats["router_provider_error"] is True
    assert stats["router_provider_error_type"] == "Exception"
    assert stats["router_provider_error_category"] == "provider"
    assert stats["router_raw_text_length"] == 0
    assert stats["router_parse_ok"] is False
    assert stats["router_used_default_plan"] is True
    assert stats["router_fallback_reason"] == "parse_failed"
    assert "boom" not in output["messages"][0].content
    _assert_no_raw_router_payload_in_logs(logger, "boom")


def test_invalid_router_output_records_shape_telemetry_and_fails_closed(monkeypatch) -> None:
    graph_module = _reload_graph_with_legacy_route_prior_env(monkeypatch)
    logger = _CaptureLogger()
    monkeypatch.setattr(graph_module, "get_run_logger", lambda _run_id: logger)
    monkeypatch.setattr(graph_module, "load_chat_model", lambda _name: _StaticRouterModel("not json"))

    state = {"messages": [HumanMessage(content="Need a market view")]}
    runtime = types.SimpleNamespace(context=Context(model="fake-model", router_model="fake-router"))

    output = anyio.run(graph_module.router_node, state, runtime)  # type: ignore[arg-type]
    stats = _router_parse_stats(logger)

    assert _flatten_selected(output["layer_plan"]) == ["a01_cio_orchestrator", "a25_report_center"]
    assert stats["router_provider_error"] is False
    assert stats["router_raw_text_length"] == len("not json")
    assert stats["router_raw_text_starts_with_json"] is False
    assert stats["router_raw_text_contains_layers"] is False
    assert stats["router_raw_text_contains_fenced_json"] is False
    assert stats["router_parse_ok"] is False
    assert stats["router_used_default_plan"] is True
    assert stats["router_fallback_reason"] == "parse_failed"
    _assert_no_raw_router_payload_in_logs(logger, "not json")


def test_valid_router_output_no_provider_error_and_preserves_selection(monkeypatch) -> None:
    graph_module = _reload_graph_with_legacy_route_prior_env(monkeypatch)
    logger = _CaptureLogger()
    payload = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": ["a01_cio_orchestrator"]},
            {"layer": "L2", "mode": "Star", "selected": ["a03_macro_industry_research"]},
            {"layer": "L3", "mode": "Star", "selected": []},
            {"layer": "L4", "mode": "Chain", "selected": ["a25_report_center"]},
        ]
    }
    monkeypatch.setattr(graph_module, "get_run_logger", lambda _run_id: logger)
    monkeypatch.setattr(
        graph_module,
        "load_chat_model",
        lambda _name: _StaticRouterModel(json.dumps(payload)),
    )

    state = {"messages": [HumanMessage(content="Need a macro view")]}
    runtime = types.SimpleNamespace(context=Context(model="fake-model", router_model="fake-router"))

    output = anyio.run(graph_module.router_node, state, runtime)  # type: ignore[arg-type]
    stats = _router_parse_stats(logger)

    assert _flatten_selected(output["layer_plan"]) == [
        "a01_cio_orchestrator",
        "a03_macro_industry_research",
        "a25_report_center",
    ]
    assert stats["router_provider_error"] is False
    assert stats["router_parse_ok"] is True
    assert stats["router_used_default_plan"] is False
    assert stats["router_raw_text_starts_with_json"] is True
    assert stats["router_raw_text_contains_layers"] is True


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
