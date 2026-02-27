import importlib

from langchain_core.messages import HumanMessage


def _load_env_for_import(monkeypatch) -> None:
    # Avoid import-time Tavily validation failures in test envs without a real key.
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")


def _reload_graph(monkeypatch):
    _load_env_for_import(monkeypatch)
    import react_agent.graph as graph_module

    return importlib.reload(graph_module)


def test_window_messages_returns_full_when_disabled(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.delenv("REACT_AGENT_MESSAGES_WINDOW", raising=False)
    msgs = [HumanMessage(content=f"m{i}") for i in range(5)]
    out = graph_module._window_messages(msgs)
    assert [m.content for m in out] == [f"m{i}" for i in range(5)]


def test_window_messages_returns_tail_when_enabled(monkeypatch) -> None:
    graph_module = _reload_graph(monkeypatch)
    monkeypatch.setenv("REACT_AGENT_MESSAGES_WINDOW", "1")
    monkeypatch.setenv("REACT_AGENT_MESSAGES_WINDOW_SIZE", "3")
    msgs = [HumanMessage(content=f"m{i}") for i in range(6)]
    out = graph_module._window_messages(msgs)
    assert [m.content for m in out] == ["m3", "m4", "m5"]
