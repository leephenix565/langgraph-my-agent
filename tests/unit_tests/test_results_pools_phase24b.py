import importlib
import sys
import types

import anyio
from langchain_core.messages import AIMessage, HumanMessage

from react_agent.context import Context


def _load_env_for_import(monkeypatch) -> None:
    # Avoid import-time Tavily validation failures in test envs without a real key.
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    if "langchain_community.tools.tavily_search" in sys.modules:
        return

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

    if "langchain.chat_models" in sys.modules:
        return

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
        return AIMessage(content='{"layers": []}')


class _FakeSummaryModel:
    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        return AIMessage(content="final answer text")


class _FakeTool:
    async def ainvoke(self, *args, **kwargs):  # type: ignore[override]
        return {
            "analysis": "ok",
            "key_points": ["kp1"],
            "evidence": ["ev1"],
            "confidence": 0.8,
            "parse_ok": True,
        }


def test_router_reset_keeps_legacy_behavior_when_results_pools_disabled(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "0")
    monkeypatch.setattr(graph_module, "load_chat_model", lambda name: _FakeRouterModel())

    state = {"messages": [HumanMessage(content="hello")]}
    runtime = types.SimpleNamespace(context=Context())
    out = anyio.run(graph_module.router_node, state, runtime)  # type: ignore[arg-type]

    assert out["analyst_results"] == {"__reset__": True}
    assert "ephemeral_results" not in out


def test_router_reset_adds_ephemeral_pool_when_enabled(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    monkeypatch.setattr(graph_module, "load_chat_model", lambda name: _FakeRouterModel())

    state = {"messages": [HumanMessage(content="hello")]}
    runtime = types.SimpleNamespace(context=Context())
    out = anyio.run(graph_module.router_node, state, runtime)  # type: ignore[arg-type]

    assert out["analyst_results"] == {"__reset__": True}
    assert out["ephemeral_results"] == {"__reset__": True}


def test_runtime_results_pool_switches_by_env(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    state = {
        "analyst_results": {"legacy_agent": {"analysis": "legacy"}},
        "ephemeral_results": {"ephemeral_agent": {"analysis": "ephemeral"}},
    }

    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "0")
    assert "legacy_agent" in graph_module._get_runtime_results_pool(state)

    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    assert "ephemeral_agent" in graph_module._get_runtime_results_pool(state)

    del state["ephemeral_results"]
    assert "legacy_agent" in graph_module._get_runtime_results_pool(state)


def test_agent_node_writes_ephemeral_and_legacy_mirror_when_enabled(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("REACT_AGENT_RESULTS_POOLS", "1")
    agent_id = "a03_macro_industry_research"
    monkeypatch.setitem(graph_module.AGENT_TOOLS, agent_id, _FakeTool())

    node = graph_module._build_agent_node(agent_id)
    state = {
        "messages": [HumanMessage(content="subtask text")],
        "ephemeral_results": {},
        "analyst_results": {},
        "current_layer": "L2",
        "layer_mode": {"L2": "Star"},
        "current_question": "q?",
    }
    runtime = types.SimpleNamespace(context=Context())
    out = anyio.run(node, state, runtime)  # type: ignore[arg-type]

    assert agent_id in out["ephemeral_results"]
    assert out["analyst_results"] == out["ephemeral_results"]


def test_manager_summary_appends_stable_findings_only_when_enabled(monkeypatch) -> None:
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
        "layer_plan": {"L4": ["a25_report_center"]},
        "layer_mode": {"L4": "Chain"},
        "current_layer": "L4",
        "plan": ["a25_report_center"],
        "ephemeral_results": {"a25_report_center": result},
        "analyst_results": {"a25_report_center": result},
        "messages": [],
        "current_question": "q",
        "layer_done": {},
        "stable_findings": [],
        "run_id": "test-run",
    }
    runtime = types.SimpleNamespace(context=Context())

    out = anyio.run(graph_module.manager_summary, state, runtime)  # type: ignore[arg-type]

    assert out["is_last_step"] is True
    assert "stable_findings" in out
    assert len(out["stable_findings"]) == 1
    entry = out["stable_findings"][0]
    assert entry["kind"] == "final_answer"
    assert entry["question"] == "q"
    assert entry["final_answer"].startswith("final answer text")
    assert entry["run_id"] == "test-run"
    assert entry["evidence"]


def test_manager_summary_coerces_non_list_stable_findings(monkeypatch) -> None:
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
        "layer_plan": {"L4": ["a25_report_center"]},
        "layer_mode": {"L4": "Chain"},
        "current_layer": "L4",
        "plan": ["a25_report_center"],
        "ephemeral_results": {"a25_report_center": result},
        "analyst_results": {"a25_report_center": result},
        "messages": [],
        "current_question": "q",
        "layer_done": {},
        "stable_findings": "bad_state_shape",
        "run_id": "test-run",
    }
    runtime = types.SimpleNamespace(context=Context())

    out = anyio.run(graph_module.manager_summary, state, runtime)  # type: ignore[arg-type]

    assert isinstance(out["stable_findings"], list)
    assert len(out["stable_findings"]) == 1
