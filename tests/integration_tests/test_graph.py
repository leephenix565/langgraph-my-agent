"""Blocking runtime graph smoke for the active reset quality gate."""

import pytest

import react_agent.graph as graph_module
from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    validate_decision_result,
    validate_dimension_composite_result,
    validate_fixed_dag_plan,
    validate_report_result,
    validate_workflow_snapshot_v2,
)

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
    valid, reason = validate_fixed_dag_plan(res["fixed_dag_plan"])
    assert valid, reason
    assert len(res["fixed_dag_plan"]["target_agent_ids"]) == 27
    assert res["workflow_snapshot"]["schema"] == "workflow_snapshot_v2"
    valid, reason = validate_workflow_snapshot_v2(res["workflow_snapshot"])
    assert valid, reason
    assert res["report_result"]["schema"] == "report_result_v1"
    valid, reason = validate_report_result(res["report_result"])
    assert valid, reason
    valid, reason = validate_decision_result(res["decision_result"])
    assert valid, reason
    assert set(res["dimension_results"]) == set(DIMENSION_GROUPS)
    for item in res["dimension_results"].values():
        valid, reason = validate_dimension_composite_result(item)
        assert valid, reason
    assert len(res["workflow_snapshot"]["dagSteps"]) == len(res["fixed_dag_plan"]["steps"])
    assert len(res["workflow_snapshot"]["dimensionGroups"]) == 4
    assert res["emitted_bundle"]["provider_invoked"] is False
    assert res["emitted_bundle"]["external_invoked"] is False
    assert res["multi_agent_bundle"]["schema"] == "fixed_dag_reset_bundle_v1"
    assert res.get("messages")
    assert "Fixed DAG reset skeleton is active" in res["messages"][-1].content
    assert "layer_plan" not in res
    assert "fusion_verdict" not in res
    assert "contract" not in graph_module.__dict__
    assert "news" not in graph_module.AGENT_METADATA
