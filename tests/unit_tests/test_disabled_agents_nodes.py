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
    assert "a02_task_router" not in graph_module.AGENT_TOOLS
    assert all(
        aid != "a02_task_router" for aid in graph_module.AGENT_NODE_NAMES.keys()
    ), "disabled agent should not have a node by default"
    for agent_id in ["a05_annual_report_analysis", "a21_portfolio_manager"]:
        assert agent_id in graph_module.AGENT_METADATA
        assert graph_module.AGENT_METADATA[agent_id].default_enabled is False
        assert agent_id not in graph_module.AGENT_NODE_NAMES
        assert agent_id not in graph_module.AGENT_TOOLS


def test_include_disabled_agents_env_does_not_resurrect_disabled_runtime(monkeypatch) -> None:
    # Disabled metadata remains visible for catalog history, but is not callable.
    monkeypatch.setenv("INCLUDE_DISABLED_AGENTS", "1")
    import importlib

    reloaded = importlib.reload(graph_module)
    assert "a02_task_router" not in reloaded.AGENT_NODE_NAMES
    assert "a02_task_router" not in reloaded.AGENT_TOOLS
    for agent_id in ["a05_annual_report_analysis", "a21_portfolio_manager"]:
        assert agent_id in reloaded.AGENT_METADATA
        assert reloaded.AGENT_METADATA[agent_id].default_enabled is False
        assert agent_id not in reloaded.AGENT_NODE_NAMES
        assert agent_id not in reloaded.AGENT_TOOLS
    assert len(reloaded.AGENT_NODE_NAMES) == 25
