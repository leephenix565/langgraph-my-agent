import pytest

from langchain_core.messages import AIMessage

import react_agent.default_agents as default_agents
import react_agent.graph as graph_module
from react_agent.context import Context

pytestmark = pytest.mark.anyio


async def test_react_agent_simple_passthrough(monkeypatch) -> None:
    class FakeModel:
        def bind_tools(self, tool_list):
            return self

        async def ainvoke(self, msgs, config=None):  # type: ignore[override]
            return AIMessage(content='{"analysis":"ok","key_points":[],"evidence":[],"confidence":0.7}', tool_calls=[])

    fm = FakeModel()
    monkeypatch.setattr(graph_module, "load_chat_model", lambda name: fm)
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: fm)

    res = await graph_module.graph.ainvoke(
        {"messages": [("user", "Demo question: give a quick market view")]},  # type: ignore
        context=Context(model="deepseek/deepseek-chat", system_prompt="You are a helpful AI assistant."),
    )

    # Should have layered plans and a final message.
    assert set(res.get("layer_plan", {}).keys()) == {"L1", "L2", "L3", "L4"}
    assert res.get("messages")
    # By default (config exists, builtin disabled) old built-ins should not be present.
    assert "news" not in graph_module.AGENT_METADATA
