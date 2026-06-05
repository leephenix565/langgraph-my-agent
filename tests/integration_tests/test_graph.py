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
from react_agent.fixed_dag_executor import validate_dag_execution_result

pytestmark = pytest.mark.anyio


async def test_react_agent_fixed_dag_skeleton_passthrough(monkeypatch) -> None:
    def fail_provider(*args, **kwargs):
        raise AssertionError("provider should not be called by R3 skeleton")

    def fail_external_client(*args, **kwargs):
        raise AssertionError("external HTTP should not be called by fixed DAG skeleton")

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_provider)
    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", fail_external_client)

    res = await graph_module.graph.ainvoke(
        {"messages": [("user", "Demo question: give a quick market view")]},  # type: ignore[arg-type]
        context=Context(model="deepseek/deepseek-chat", system_prompt="inactive"),
    )

    assert res["fixed_dag_plan"]["schema"] == "fixed_dag_plan_v1"
    valid, reason = validate_fixed_dag_plan(res["fixed_dag_plan"])
    assert valid, reason
    valid, reason = validate_dag_execution_result(res["dag_execution"])
    assert valid, reason
    assert res["dag_execution"]["provenance"]["provider_invoked"] is False
    assert res["dag_execution"]["provenance"]["external_invoked"] is False
    assert res["execution_batches"] == res["dag_execution"]["execution_batches"]
    assert res["dag_step_results"] == res["dag_execution"]["step_results"]
    assert res["dag_step_results"]["financial_data_service"]["runtime_kind"] == "external_http_candidate"
    assert res["dag_step_results"]["financial_data_service"]["invoke_enabled"] is False
    assert res["dag_step_results"]["financial_data_service"]["live_verified"] is False
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
    assert res["workflow_snapshot"]["executionBatches"] == res["execution_batches"]
    assert res["workflow_snapshot"]["stepResults"] == res["dag_step_results"]
    assert len(res["workflow_snapshot"]["dimensionGroups"]) == 4
    assert res["emitted_bundle"]["provider_invoked"] is False
    assert res["emitted_bundle"]["external_invoked"] is False
    assert res["multi_agent_bundle"]["schema"] == "fixed_dag_reset_bundle_v1"
    assert res["multi_agent_bundle"]["dag_execution"]["schema_version"] == "fixed_dag_execution_v1"
    assert res.get("messages")
    assert "固定 DAG 研判流程" in res["messages"][-1].content
    assert "layer_plan" not in res
    assert "fusion_verdict" not in res
    assert "contract" not in graph_module.__dict__
    assert "AGENT_METADATA" not in graph_module.__dict__
    assert "AGENT_TOOLS" not in graph_module.__dict__
