import pytest

from react_agent.graph_bootstrap import (
    bootstrap_legacy_agent_runtime,
    build_legacy_node_registry,
)
from react_agent.legacy_agent_registry import AGENT_METADATA, AGENT_TOOLS


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("INCLUDE_DISABLED_AGENTS", raising=False)
    yield
    monkeypatch.delenv("INCLUDE_DISABLED_AGENTS", raising=False)


def test_disabled_agents_not_in_nodes_by_default(monkeypatch) -> None:
    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()
    bootstrap_legacy_agent_runtime()
    _agent_ids, node_names = build_legacy_node_registry(include_disabled=False)
    assert "a02_task_router" not in node_names
    assert "a02_task_router" not in AGENT_TOOLS
    assert all(aid != "a02_task_router" for aid in node_names)
    for agent_id in ["a05_annual_report_analysis", "a21_portfolio_manager"]:
        assert agent_id in AGENT_METADATA
        assert AGENT_METADATA[agent_id].default_enabled is False
        assert agent_id not in node_names
        assert agent_id not in AGENT_TOOLS
    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()


def test_include_disabled_agents_env_does_not_resurrect_disabled_runtime(monkeypatch) -> None:
    # Disabled metadata remains visible for catalog history, but is not callable.
    monkeypatch.setenv("INCLUDE_DISABLED_AGENTS", "1")

    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()
    bootstrap_legacy_agent_runtime()
    _agent_ids, node_names = build_legacy_node_registry(include_disabled=False)
    assert "a02_task_router" not in node_names
    assert "a02_task_router" not in AGENT_TOOLS
    for agent_id in ["a05_annual_report_analysis", "a21_portfolio_manager"]:
        assert agent_id in AGENT_METADATA
        assert AGENT_METADATA[agent_id].default_enabled is False
        assert agent_id not in node_names
        assert agent_id not in AGENT_TOOLS
    assert len(node_names) == 25
    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()
