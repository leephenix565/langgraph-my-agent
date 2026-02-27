import importlib
import sys
import types

import anyio
from langchain_core.messages import AIMessage

from react_agent.context import Context


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


class _FakeSummaryModel:
    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        return AIMessage(content="final answer text")


def test_route_from_manager_summary_final_layer_without_pending_routes_to_finalize(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    state = {
        "is_last_step": False,
        "current_layer": graph_module.FINAL_LAYER,
        "layer_plan": {graph_module.FINAL_LAYER: []},
        "layer_mode": {graph_module.FINAL_LAYER: "Star"},
        "plan": [],
        "analyst_results": {},
    }

    assert graph_module.route_from_manager_summary(state) == "finalize_summary"


def test_finalize_summary_sets_last_step_and_writes_message(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    monkeypatch.setattr(graph_module, "load_chat_model", lambda name: _FakeSummaryModel())

    result = {
        "analysis": "from a25",
        "key_points": ["k1"],
        "evidence": ["e1"],
        "confidence": 0.9,
        "parse_ok": True,
    }
    state = {
        "layer_plan": {"L4": []},
        "layer_mode": {"L4": "Star"},
        "current_layer": "L4",
        "plan": [],
        "ephemeral_results": {"a25_report_center": result},
        "analyst_results": {"a25_report_center": result},
        "messages": [],
        "current_question": "q",
        "layer_done": {"L1": True, "L2": True, "L3": True},
        "stable_findings": [],
        "run_id": "test-run",
    }
    runtime = types.SimpleNamespace(context=Context(run_id="test-run"))

    out = anyio.run(graph_module.finalize_summary, state, runtime)  # type: ignore[arg-type]

    assert out["is_last_step"] is True
    assert out["messages"]
    assert isinstance(out["messages"][0], AIMessage)
    assert out["layer_done"]["L4"] is True
    assert len(out["stable_findings"]) == 1


def test_route_after_finalize_respects_thread_summary_toggle(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    state = {"is_last_step": True}

    monkeypatch.setenv("REACT_AGENT_THREAD_SUMMARY", "1")
    assert graph_module.route_after_finalize(state) == "memory_update"

    monkeypatch.setenv("REACT_AGENT_THREAD_SUMMARY", "0")
    assert graph_module.route_after_finalize(state) == "__end__"
