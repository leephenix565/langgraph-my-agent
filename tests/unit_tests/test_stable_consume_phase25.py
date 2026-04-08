import importlib
import sys
import types

from langchain_core.messages import AIMessage


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


def test_build_stable_summary_empty_when_missing_or_non_list(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)

    assert graph_module._build_stable_summary({}) == ""
    assert graph_module._build_stable_summary({"stable_findings": "bad"}) == ""


def test_build_stable_summary_respects_max_items_and_max_chars(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("REACT_AGENT_STABLE_SUMMARY_MAX_ITEMS", "2")
    monkeypatch.setenv("REACT_AGENT_STABLE_SUMMARY_MAX_CHARS", "220")

    state = {
        "stable_findings": [
            {
                "kind": "final_answer",
                "question": "Q1 older",
                "final_answer": "A1 older answer",
                "evidence": [{"agent_id": "a01", "kind": "evidence", "text": "E1"}],
                "run_id": "r1",
            },
            {
                "kind": "final_answer",
                "question": "Q2 newer",
                "final_answer": "A2 newer answer",
                "evidence": [{"agent_id": "a02", "kind": "evidence", "text": "E2"}],
                "run_id": "r2",
            },
            {
                "kind": "final_answer",
                "question": "Q3 newest",
                "final_answer": "A3 newest answer",
                "evidence": [{"agent_id": "a03", "kind": "evidence", "text": "E3"}],
                "run_id": "r3",
            },
        ]
    }

    summary = graph_module._build_stable_summary(state)

    assert summary
    assert len(summary) <= 220
    assert "Q1 older" not in summary
    assert "Q2 newer" in summary or "Q3 newest" in summary
