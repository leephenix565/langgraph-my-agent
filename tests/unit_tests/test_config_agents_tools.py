import types

import pytest

import react_agent.graph as graph_module
from react_agent.generic_agent import build_generic_agent_tool


def test_config_agents_default_to_llm_tools(monkeypatch) -> None:
    """Config agents should register with LLM tools (non-stub) when description exists."""

    class FakeModel:
        tool_calls = []

        async def ainvoke(self, msgs):
            return types.SimpleNamespace(content='{"analysis":"ok","key_points":[],"evidence":[],"confidence":0.7}')

        def bind_tools(self, tool_list):
            return self

    # Monkeypatch to avoid real LLM calls.
    monkeypatch.setattr("react_agent.default_agents.load_chat_model", lambda name: FakeModel())
    monkeypatch.setattr("react_agent.utils.load_chat_model", lambda name: FakeModel())

    # Rebuild graph to trigger registration with LLM tools.
    _ = graph_module  # access module to ensure registration run
    tool = graph_module.AGENT_TOOLS.get("a03_macro_industry_research")
    assert tool is not None
    assert not getattr(tool, "is_stub", False)
    assert not getattr(tool, "is_external_valuation_wrapper", False)


def test_external_valuation_agents_are_not_default_llm_tools() -> None:
    for agent_id, external_agent_id in {
        "a16_ml_valuation": "valuation_ml",
        "a17_traditional_valuation": "valuation_traditional",
        "a18_meta_valuation": "valuation_meta",
    }.items():
        tool = graph_module.AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert getattr(tool, "is_external_valuation_wrapper", False)
        assert getattr(tool, "external_agent_id", "") == external_agent_id
        assert not getattr(tool, "is_stub", False)


def test_non_valuation_l3_agents_still_use_default_llm_tools() -> None:
    for agent_id in ["a19_risk_identification", "a20_compliance_review", "a21_portfolio_manager"]:
        tool = graph_module.AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert not getattr(tool, "is_external_valuation_wrapper", False)
        assert not getattr(tool, "is_stub", False)


def test_stub_fallback_when_description_missing(monkeypatch) -> None:
    """If description is empty, fallback to stub."""
    from react_agent.agents import AGENT_METADATA, AGENT_TOOLS, AgentMetadata, register_agent

    previous_metadata = dict(AGENT_METADATA)
    previous_tools = dict(AGENT_TOOLS)
    try:
        # Register a temp agent with empty description.
        meta = AgentMetadata(
            id="tmp_no_desc",
            name="tmp",
            description="",
            capabilities=[],
            input_type="",
            latency_level="",
            cost_level="",
            version="",
            layer="L2",
        )
        tool = build_generic_agent_tool(meta.id, meta.description)
        register_agent(meta, tool)
        assert getattr(AGENT_TOOLS[meta.id], "is_stub", False)
    finally:
        AGENT_METADATA.clear()
        AGENT_METADATA.update(previous_metadata)
        AGENT_TOOLS.clear()
        AGENT_TOOLS.update(previous_tools)
