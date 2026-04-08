import os

import pytest

import react_agent.graph as graph_module


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("INCLUDE_DISABLED_AGENTS", raising=False)
    yield
    monkeypatch.delenv("INCLUDE_DISABLED_AGENTS", raising=False)


def test_disabled_agents_not_in_nodes_by_default(monkeypatch) -> None:
    assert "a02_task_router" not in graph_module.AGENT_NODE_NAMES
    assert all(
        aid != "a02_task_router" for aid in graph_module.AGENT_NODE_NAMES.keys()
    ), "disabled agent should not have a node by default"


def test_include_disabled_agents_env(monkeypatch) -> None:
    # Reload module with env set
    monkeypatch.setenv("INCLUDE_DISABLED_AGENTS", "1")
    import importlib

    reloaded = importlib.reload(graph_module)
    assert "a02_task_router" in reloaded.AGENT_NODE_NAMES

