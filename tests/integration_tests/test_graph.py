import pytest

from react_agent import graph
from react_agent.context import Context

pytestmark = pytest.mark.anyio


async def test_react_agent_simple_passthrough() -> None:
    res = await graph.ainvoke(
        {"messages": [("user", "Demo question: give a quick market view")]},  # type: ignore
        context=Context(model="deepseek/deepseek-chat", system_prompt="You are a helpful AI assistant."),
    )

    # Should have layered plans and a final message.
    assert set(res.get("layer_plan", {}).keys()) == {"L1", "L2", "L4", "L5"}
    assert res.get("messages")
    # By default (config exists, builtin disabled) old built-ins should not be present.
    assert "news" not in graph.AGENT_IDS
