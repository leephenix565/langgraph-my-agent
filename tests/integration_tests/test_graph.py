"""Blocking runtime graph smoke for the active reset quality gate."""

import pytest

import react_agent.graph as graph_module
from react_agent.context import Context
from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    RESET_RUNTIME_AGENT_IDS,
    validate_decision_result,
    validate_dimension_composite_result,
    validate_fixed_dag_plan,
    validate_report_result,
    validate_selected_fixed_dag_plan,
    validate_workflow_snapshot_v2,
)
from react_agent.fixed_dag_executor import (
    validate_dag_execution_result,
    validate_selected_dag_steps,
)

pytestmark = pytest.mark.anyio


async def test_selected_routing_context_defaults_off_and_env_can_enable(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_SELECTED_ROUTING", raising=False)
    assert Context().enable_selected_routing is False

    monkeypatch.setenv("ENABLE_SELECTED_ROUTING", "1")
    assert Context().enable_selected_routing is True


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
    assert "研判流程" in res["messages"][-1].content
    assert "layer_plan" not in res
    assert "fusion_verdict" not in res
    assert "contract" not in graph_module.__dict__
    assert "AGENT_METADATA" not in graph_module.__dict__
    assert "AGENT_TOOLS" not in graph_module.__dict__


async def test_selected_routing_flag_builds_and_executes_selected_plan(monkeypatch) -> None:
    def fail_provider(*args, **kwargs):
        raise AssertionError("provider should not be called by selected routing flag")

    def fail_external_client(*args, **kwargs):
        raise AssertionError("external HTTP should not be called by selected routing flag")

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_provider)
    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", fail_external_client)

    res = await graph_module.graph.ainvoke(
        {"messages": [("user", "Explain discounted cash flow in simple terms.")]},  # type: ignore[arg-type]
        context=Context(enable_selected_routing=True),
    )

    assert res["fixed_dag_plan"]["schema"] == "selected_fixed_dag_plan_v1"
    assert len(res["fixed_dag_plan"]["steps"]) < len(RESET_RUNTIME_AGENT_IDS)
    valid, reason = validate_selected_fixed_dag_plan(res["fixed_dag_plan"])
    assert valid, reason
    valid, reason = validate_selected_dag_steps(res["fixed_dag_plan"])
    assert valid, reason
    valid, reason = validate_dag_execution_result(res["dag_execution"])
    assert valid, reason
    assert res["fixed_dag_plan"]["provenance"]["selected_routing_requested"] is True
    assert res["fixed_dag_plan"]["provenance"]["selected_routing_fallback"] is False
    assert res["dag_execution"]["provenance"]["provider_invoked"] is False
    assert res["dag_execution"]["provenance"]["external_invoked"] is False
    assert set(res["dag_step_results"]) == {step["id"] for step in res["fixed_dag_plan"]["steps"]}
    assert "decision_synthesizer" not in res["dag_step_results"]
    assert set(res["workflow_snapshot"]["completedSteps"]) == set(res["dag_step_results"])
    assert {item["id"] for item in res["workflow_snapshot"]["dimensionGroups"]} == {"value"}


async def test_selected_routing_failure_falls_back_to_full_dag(monkeypatch) -> None:
    def fail_compile(*args, **kwargs):
        raise ValueError("forced selected compiler failure")

    monkeypatch.setattr(graph_module, "compile_selected_fixed_dag_plan", fail_compile)

    res = await graph_module.graph.ainvoke(
        {"messages": [("user", "Explain discounted cash flow in simple terms.")]},  # type: ignore[arg-type]
        context=Context(enable_selected_routing=True),
    )

    plan = res["fixed_dag_plan"]
    assert plan["schema"] == "fixed_dag_plan_v1"
    assert len(plan["steps"]) == len(RESET_RUNTIME_AGENT_IDS)
    valid, reason = validate_fixed_dag_plan(plan)
    assert valid, reason
    assert plan["provenance"]["selected_routing_requested"] is True
    assert plan["provenance"]["selected_routing_fallback"] is True
    assert plan["provenance"]["fallback_reason"] == "selected_routing_compile_failed:ValueError"
    assert plan["provenance"]["provider_invoked"] is False
    assert plan["provenance"]["external_invoked"] is False
    assert "provider" not in plan["provenance"]["fallback_reason"]
    valid, reason = validate_dag_execution_result(res["dag_execution"])
    assert valid, reason
