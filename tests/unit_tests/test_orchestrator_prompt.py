import types

import anyio
from langchain_core.messages import HumanMessage

from react_agent import graph
from react_agent.context import Context
from react_agent.default_agents import _build_agent_tool
from react_agent import prompts


class FakeModel:
    def __init__(self):
        self.last_msgs = None
        self.tool_calls = []

    def bind_tools(self, tool_list):
        return self

    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        self.last_msgs = msgs
        return types.SimpleNamespace(content='{"analysis":"ok","key_points":[],"evidence":[],"confidence":0.7}', tool_calls=[])


def test_orchestrator_uses_special_system_prompt(monkeypatch) -> None:
    fm = FakeModel()
    monkeypatch.setattr("react_agent.default_agents.load_chat_model", lambda name: fm)
    tool = _build_agent_tool("a01_cio_orchestrator", "profile text", default_allow_search=False)

    res = anyio.run(
        lambda: tool.ainvoke(
            question="q",
            subtask="s",
            shared_context={},
            history=[],
            tools_config={},
            router_plan_summary="L1(Chain): a01_cio_orchestrator\nL2(Star): a03",
        )
    )

    assert res.get("analysis") == "ok"
    assert fm.last_msgs is not None
    system_msg = fm.last_msgs[0]["content"]
    assert prompts.ORCHESTRATOR_SYSTEM_PROMPT in system_msg
    user_payload = fm.last_msgs[1]["content"]
    assert "router_plan_summary" in user_payload


def test_manager_assignment_for_a01_is_decomposition(monkeypatch) -> None:
    # Ensure manager_broadcast uses the orchestrator assignment template.
    state = {
        "layer_plan": {"L1": ["a01_cio_orchestrator"], "L2": ["a03_macro_policy"], "L4": [], "L5": []},
        "layer_mode": {"L1": "Chain", "L2": "Star", "L4": "Star", "L5": "Chain"},
        "current_layer": "L1",
        "plan": ["a01_cio_orchestrator"],
        "analyst_results": {},
        "messages": [],
    }
    runtime = types.SimpleNamespace(context=Context())
    cmd = anyio.run(graph.manager_broadcast, state, runtime)  # type: ignore[arg-type]
    send = cmd.goto[0]
    assign_text = send.arg["messages"][-1].content  # type: ignore[index]
    assert "任务拆解" in assign_text or "验收设计" in assign_text
    assert "router_plan_summary" in assign_text
    assert "直接完成你的分析" not in assign_text
