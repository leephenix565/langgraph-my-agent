import types

import anyio
from langchain_core.messages import HumanMessage

from react_agent import graph
from react_agent.context import Context


class CaptureTool:
    def __init__(self):
        self.last_input = None

    async def ainvoke(self, agent_input, config=None):  # type: ignore[override]
        self.last_input = agent_input
        return {
            "analysis": "ok",
            "key_points": [],
            "evidence": [],
            "confidence": 0.8,
            "parse_ok": True,
        }


def test_router_plan_summary_passed_to_a01(monkeypatch) -> None:
    agent_id = "a01_cio_orchestrator"
    tool = CaptureTool()
    monkeypatch.setitem(graph.AGENT_TOOLS, agent_id, tool)

    state = {
        "messages": [HumanMessage(content="subtask text")],
        "analyst_results": {},
        "current_layer": "L1",
        "layer_mode": {"L1": "Chain"},
        "layer_plan": {"L1": ["a01_cio_orchestrator"], "L2": ["a03"], "L3": [], "L4": []},
        "current_question": "q?",
    }
    runtime = types.SimpleNamespace(context=Context())

    node = graph._build_agent_node(agent_id)
    _ = anyio.run(node, state, runtime)  # type: ignore[arg-type]

    assert tool.last_input is not None
    assert "router_plan_summary" in tool.last_input
    summary = tool.last_input["router_plan_summary"]
    assert "L1(Chain)" in summary
    assert "L2(Star)" in summary
    assert "a01_cio_orchestrator" in summary
