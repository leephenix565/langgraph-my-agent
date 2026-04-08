import types

import pytest

import anyio

from react_agent.default_agents import _build_agent_tool


class FakeModel:
    def __init__(self, content: str):
        self._content = content

    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        return types.SimpleNamespace(content=self._content, tool_calls=[])

    def bind_tools(self, tool_list):
        return self


def test_agent_parse_fallback_flagged(monkeypatch) -> None:
    # Fake model returns non-JSON, should trigger parse fallback with prefix.
    monkeypatch.setattr("react_agent.default_agents.load_chat_model", lambda name: FakeModel("not json"))

    tool = _build_agent_tool("test_agent", "profile text", default_allow_search=False)
    res = anyio.run(
        lambda: tool.ainvoke(
            {
                "question": "q",
                "subtask": "s",
                "shared_context": {},
                "history": [],
                "tools_config": {},
            }
        )
    )
    assert res["analysis"].startswith("[PARSE_FALLBACK]")
    assert res.get("parse_ok") is False
