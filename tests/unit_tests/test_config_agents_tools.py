import types

import pytest

from react_agent import graph
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
    _ = graph  # access module to ensure registration run
    tool = graph.AGENT_TOOLS.get("a03_macro_policy")
    assert tool is not None
    assert not getattr(tool, "is_stub", False)


def test_stub_fallback_when_description_missing(monkeypatch) -> None:
    """If description is empty, fallback to stub."""
    from react_agent.agents import AgentMetadata
    from react_agent.graph import register_agent, AGENT_TOOLS
    from react_agent.generic_agent import build_generic_agent_tool

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
