import types

import anyio
from langchain_core.messages import AIMessage

from react_agent.default_agents import _build_agent_tool
from react_agent.graph import manager_summary
from react_agent.context import Context


class FakeModelRetry:
    def __init__(self):
        self.call_count = 0

    def bind_tools(self, tool_list):
        return self

    async def ainvoke(self, msgs):
        self.call_count += 1
        if self.call_count == 1:
            return AIMessage(content="not json", tool_calls=[])
        return AIMessage(content='{"analysis":"ok","key_points":[],"evidence":[],"confidence":0.8}', tool_calls=[])


class FakeModelSummary:
    def __init__(self):
        self.last_msgs = None

    async def ainvoke(self, msgs):
        self.last_msgs = msgs
        return AIMessage(content="summary")


def test_llm_json_retry_success(monkeypatch) -> None:
    monkeypatch.setattr("react_agent.default_agents.load_chat_model", lambda name: FakeModelRetry())
    tool = _build_agent_tool("retry_agent", "profile text", default_allow_search=False)
    res = anyio.run(
        lambda: tool.ainvoke(
            question="q",
            subtask="s",
            shared_context={},
            history=[],
            tools_config={},
        )
    )
    assert res.get("parse_ok") is True
    assert res.get("analysis") == "ok"


def test_summary_filters_parse_fail(monkeypatch) -> None:
    fm = FakeModelSummary()
    monkeypatch.setattr("react_agent.utils.load_chat_model", lambda name: fm)

    state = {
        "layer_plan": {"L4": []},
        "layer_mode": {"L4": "Chain"},
        "current_layer": "L4",
        "plan": [],
        "analyst_results": {
            "ok": {"analysis": "keep", "key_points": [], "evidence": [], "confidence": 0.9, "parse_ok": True},
            "bad": {"analysis": "drop", "key_points": [], "evidence": [], "confidence": 0.1, "parse_ok": False},
        },
        "messages": [],
        "current_question": "q",
    }
    res = anyio.run(manager_summary, state, types.SimpleNamespace(context=Context()))
    # Fake model returns "summary", but we inspect the inputs it received.
    user_msg = fm.last_msgs[-1]["content"]
    assert "bad" not in user_msg
    assert "ok" in user_msg
    assert "解析失败" in user_msg
