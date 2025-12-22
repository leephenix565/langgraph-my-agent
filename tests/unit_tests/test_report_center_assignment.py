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


def test_a25_assignment_and_allow_search(monkeypatch) -> None:
    agent_id = "a25_report_center"
    tool = CaptureTool()
    monkeypatch.setitem(graph.AGENT_TOOLS, agent_id, tool)

    # Star branch path
    state = {
        "layer_plan": {"L4": ["a25_report_center"]},
        "layer_mode": {"L4": "Star"},
        "current_layer": "L4",
        "plan": ["a25_report_center"],
        "analyst_results": {},
        "messages": [],
        "current_question": "q?",
    }
    runtime = types.SimpleNamespace(context=Context())
    cmd = anyio.run(graph.manager_broadcast, state, runtime)  # type: ignore[arg-type]
    send = cmd.goto[0]
    assign_text = send.arg["messages"][-1].content  # type: ignore[index]
    assert "报告中心" in assign_text
    assert "请直接完成你的分析" not in assign_text

    # agent execution
    node = graph._build_agent_node(agent_id)
    res = anyio.run(node, send.arg, runtime)  # type: ignore[arg-type]
    assert tool.last_input is not None
    assert tool.last_input.get("tools_config", {}).get("allow_search") is False

