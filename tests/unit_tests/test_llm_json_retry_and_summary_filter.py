import anyio
from langchain_core.messages import AIMessage

from react_agent.default_agents import _build_agent_tool
from react_agent.fixed_dag_contracts import (
    build_decision_result,
    build_deterministic_fixed_dag_plan,
    build_dimension_results,
    build_l2_conclusions,
)
from react_agent.graph import final_emit_node, report_generator_node


class FakeModelRetry:
    def __init__(self):
        self.call_count = 0

    def bind_tools(self, tool_list):
        return self

    async def ainvoke(self, msgs, config=None):  # type: ignore[override]
        self.call_count += 1
        if self.call_count == 1:
            return AIMessage(content="not json", tool_calls=[])
        return AIMessage(content='{"analysis":"ok","key_points":[],"evidence":[],"confidence":0.8}', tool_calls=[])


def test_llm_json_retry_success(monkeypatch) -> None:
    fm = FakeModelRetry()
    monkeypatch.setattr("react_agent.default_agents.load_chat_model", lambda name: fm)
    tool = _build_agent_tool("retry_agent", "profile text", default_allow_search=False)
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
    assert res.get("parse_ok") is True
    assert res.get("analysis") == "ok"


def test_reset_report_and_final_emit_do_not_need_manager_summary() -> None:
    plan = build_deterministic_fixed_dag_plan("q")
    l2 = build_l2_conclusions()
    dimensions = build_dimension_results(l2)
    state = {
        "current_question": "q",
        "fixed_dag_plan": plan,
        "l2_conclusions": l2,
        "dimension_results": dimensions,
        "decision_result": build_decision_result(),
    }

    report_update = report_generator_node(state)  # type: ignore[arg-type]
    final_update = final_emit_node({**state, **report_update})  # type: ignore[arg-type]
    assert final_update["is_last_step"] is True
    assert final_update["final_answer_source"] == "reset_skeleton"
    assert "固定 DAG 研判流程" in final_update["emitted_bundle"]["answer"]
