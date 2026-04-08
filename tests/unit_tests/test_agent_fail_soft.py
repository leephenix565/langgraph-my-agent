import types

import anyio
from langchain_core.messages import HumanMessage

import react_agent.graph as graph_module
from react_agent.context import Context


class ErrorTool:
    async def ainvoke(self, *args, **kwargs):  # pragma: no cover - behavior under test
        raise RuntimeError("boom error for fail-soft")


def test_agent_fail_soft_on_exception(monkeypatch) -> None:
    agent_id = "a03_macro_policy"
    monkeypatch.setitem(graph_module.AGENT_TOOLS, agent_id, ErrorTool())

    node = graph_module._build_agent_node(agent_id)
    state = {
        "messages": [HumanMessage(content="subtask text")],
        "analyst_results": {},
        "current_layer": "L2",
        "layer_mode": {"L2": "Star"},
        "current_question": "q?",
    }
    runtime = types.SimpleNamespace(context=Context())

    res = anyio.run(node, state, runtime)  # type: ignore[arg-type]

    output = res["analyst_results"][agent_id]
    assert output.get("parse_ok") is False
    assert output.get("confidence") == 0.0
    assert output.get("key_points") == []
    assert output.get("evidence") == []
    assert "[AGENT_ERROR]" in output.get("analysis", "")
    # Should also emit an AIMessage carrying the structured output.
    assert res["messages"]
