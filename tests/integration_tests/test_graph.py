"""Blocking runtime graph smoke for the active reset quality gate."""

import pytest

import react_agent.graph as graph_module
from react_agent.context import Context

pytestmark = pytest.mark.anyio


async def test_react_agent_fixed_dag_skeleton_passthrough(monkeypatch) -> None:
    def fail_provider(*args, **kwargs):
        raise AssertionError("provider should not be called by R1-B skeleton")

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_provider)

    res = await graph_module.graph.ainvoke(
        {"messages": [("user", "Demo question: give a quick market view")]},  # type: ignore[arg-type]
        context=Context(model="deepseek/deepseek-chat", system_prompt="inactive"),
    )

    assert res["fixed_dag_plan"]["schema"] == "fixed_dag_plan_v1"
    assert len(res["fixed_dag_plan"]["target_agent_ids"]) == 28
    assert res["workflow_snapshot"]["schema"] == "workflow_snapshot_v2"
    assert res["report_result"]["schema"] == "report_result_v1"
    assert res.get("messages")
    assert "Fixed DAG reset skeleton is active" in res["messages"][-1].content
    assert "layer_plan" not in res
    assert "fusion_verdict" not in res
    assert "contract" not in graph_module.__dict__
    assert "news" not in graph_module.AGENT_METADATA
