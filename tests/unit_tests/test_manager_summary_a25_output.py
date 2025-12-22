import types

import anyio
from langchain_core.messages import AIMessage

from react_agent.graph import manager_summary
from react_agent.context import Context
from react_agent import graph


class FakeModel:
    def __init__(self):
        self.last_msgs = None

    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        self.last_msgs = msgs
        return AIMessage(content="manager final")


def _mk_state(parse_ok: bool = True) -> dict:
    return {
        "layer_plan": {"L4": ["a25_report_center"]},
        "layer_mode": {"L4": "Chain"},
        "current_layer": "L4",
        "plan": ["a25_report_center"],
        "analyst_results": {
            "a25_report_center": {
                "analysis": "from a25",
                "key_points": ["k1"],
                "evidence": ["e1"],
                "confidence": 0.9,
                "parse_ok": parse_ok,
            }
        },
        "messages": [],
        "current_question": "q",
        "layer_done": {},
    }


def test_manager_summary_always_uses_manager_llm_even_when_a25_ok(monkeypatch) -> None:
    fm = FakeModel()
    monkeypatch.setattr("react_agent.graph.load_chat_model", lambda name: fm)
    state = _mk_state(parse_ok=True)
    runtime = types.SimpleNamespace(context=Context())

    res = anyio.run(manager_summary, state, runtime)  # type: ignore[arg-type]
    assert res["is_last_step"] is True
    assert res["messages"][0].content == "manager final"
    assert fm.last_msgs is not None
    user_msg = fm.last_msgs[-1].content  # HumanMessage.content
    assert "a25_report_center" in user_msg
    assert "L4 Draft" in user_msg or "L4" in user_msg


def test_manager_summary_fallback_when_a25_invalid(monkeypatch) -> None:
    fm = FakeModel()
    monkeypatch.setattr("react_agent.graph.load_chat_model", lambda name: fm)
    state = _mk_state(parse_ok=False)
    runtime = types.SimpleNamespace(context=Context())

    res = anyio.run(manager_summary, state, runtime)  # type: ignore[arg-type]
    assert res["messages"][0].content == "manager final"
