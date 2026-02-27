import asyncio
import importlib

from langchain_core.messages import AIMessage, HumanMessage


def _load_env_for_import(monkeypatch) -> None:
    # Avoid import-time Tavily validation failures in test envs without a real key.
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")


def _reload_graph(monkeypatch):
    _load_env_for_import(monkeypatch)
    import react_agent.graph as graph_module

    return importlib.reload(graph_module)


def test_build_thread_summary_is_extractive_and_bounded(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("REACT_AGENT_THREAD_SUMMARY_MAX_CHARS", "220")
    state = {
        "current_question": "我叫小明。请记住这个名字，并在下一轮提醒我。",
        "messages": [
            HumanMessage(content="我叫小明。请记住这个名字。"),
            AIMessage(content="这是最终回答。" + (" 很长内容" * 200)),
        ],
    }

    summary = graph_module._build_thread_summary(state)

    assert summary
    assert "Recent user question:" in summary
    assert "Recent final answer:" in summary
    assert len(summary) <= 220
    assert "这是最终回答。" in summary


def test_route_from_manager_summary_uses_memory_update_only_when_enabled(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    state = {"is_last_step": True}

    monkeypatch.setenv("REACT_AGENT_THREAD_SUMMARY", "1")
    assert graph_module.route_from_manager_summary(state) == "memory_update"

    monkeypatch.setenv("REACT_AGENT_THREAD_SUMMARY", "0")
    assert graph_module.route_from_manager_summary(state) == "__end__"


def test_memory_update_only_updates_on_final_when_enabled(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)

    class _Ctx:
        run_id = "test-run"

    class _Runtime:
        context = _Ctx()

    final_state = {
        "is_last_step": True,
        "current_question": "我刚才叫什么？",
        "messages": [
            HumanMessage(content="我叫小明"),
            AIMessage(content="你刚才叫小明。"),
        ],
        "run_id": "test-run",
    }

    monkeypatch.setenv("REACT_AGENT_THREAD_SUMMARY", "0")
    assert asyncio.run(graph_module.memory_update(final_state, _Runtime())) == {}

    monkeypatch.setenv("REACT_AGENT_THREAD_SUMMARY", "1")
    out = asyncio.run(graph_module.memory_update(final_state, _Runtime()))
    assert "thread_summary" in out
    assert "Recent user question:" in out["thread_summary"]
    assert "Recent final answer:" in out["thread_summary"]

    non_final = dict(final_state)
    non_final["is_last_step"] = False
    assert asyncio.run(graph_module.memory_update(non_final, _Runtime())) == {}
