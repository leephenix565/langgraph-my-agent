import pytest

import react_agent.graph as graph_module
from react_agent.context import Context
from react_agent.fixed_dag_contracts import DIMENSION_GROUPS
from react_agent.fixed_dag_executor import validate_dag_execution_result

pytestmark = pytest.mark.anyio


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def test_graph_skeleton_invokes_without_provider_or_external(monkeypatch) -> None:
    def fail_load_model(*args, **kwargs):
        raise AssertionError("provider should not be called")

    def fail_external_client(*args, **kwargs):
        raise AssertionError("external HTTP should not be called")

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_load_model)
    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", fail_external_client)

    result = graph_module.graph.invoke(
        {"messages": [("user", "Demo question")]},
        context=Context(
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )

    assert result["fixed_dag_plan"]["schema"] == "fixed_dag_plan_v1"
    valid, reason = validate_dag_execution_result(result["dag_execution"])
    assert valid, reason
    assert result["dag_execution"]["schema_version"] == "fixed_dag_execution_v1"
    assert result["execution_batches"] == result["dag_execution"]["execution_batches"]
    assert result["dag_step_results"] == result["dag_execution"]["step_results"]
    assert result["dag_step_results"]["financial_data_service"]["runtime_kind"] == "external_http_candidate"
    assert result["dag_step_results"]["financial_data_service"]["invoke_enabled"] is False
    assert result["dag_step_results"]["financial_data_service"]["live_verified"] is False
    assert result["workflow_snapshot"]["schema"] == "workflow_snapshot_v2"
    assert result["workflow_snapshot"]["executionBatches"] == result["execution_batches"]
    assert result["workflow_snapshot"]["stepResults"] == result["dag_step_results"]
    assert result["report_result"]["schema"] == "report_result_v1"
    assert result["final_answer_source"] == "reset_skeleton"
    assert result["is_last_step"] is True
    assert result["final_emit_payload"]["source"] == "reset_skeleton"
    assert result["emitted_bundle"]["provider_invoked"] is False
    assert result["emitted_bundle"]["external_invoked"] is False
    assert result["multi_agent_bundle"]["schema"] == "fixed_dag_reset_bundle_v1"
    assert result["multi_agent_bundle"]["dag_execution"] == result["dag_execution"]
    assert result["multi_agent_bundle"]["dag_step_results"] == result["dag_step_results"]
    assert result["multi_agent_bundle"]["execution_batches"] == result["execution_batches"]
    assert set(DIMENSION_GROUPS) == {
        item["id"] for item in result["workflow_snapshot"]["dimensionGroups"]
    }
    assert "研判流程" in result["messages"][-1].content
    for legacy_field in (
        "layer_plan",
        "layer_mode",
        "fusion_verdict",
        "writer_output",
        "baseline_bundle",
        "mainline_emit_payload",
    ):
        assert legacy_field not in result
        assert not _contains_key(result["workflow_snapshot"], legacy_field)


def test_active_reset_graph_uses_executor_node() -> None:
    assert "execute_fixed_dag" in graph_module.builder.nodes
    for inactive_stage_node in (
        "run_l2_conclusions",
        "run_dimension_composites",
        "decision_synthesizer",
        "report_generator",
    ):
        assert inactive_stage_node not in graph_module.builder.nodes
