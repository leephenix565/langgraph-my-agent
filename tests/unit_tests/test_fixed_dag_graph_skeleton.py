import pytest

import react_agent.graph as graph_module
from react_agent.context import Context
from react_agent.fixed_dag_contracts import DIMENSION_GROUPS

pytestmark = pytest.mark.anyio


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


async def test_graph_skeleton_invokes_without_provider_or_external(monkeypatch) -> None:
    def fail_load_model(*args, **kwargs):
        raise AssertionError("provider should not be called")

    monkeypatch.setattr("react_agent.default_agents.load_chat_model", fail_load_model)

    result = await graph_module.graph.ainvoke(
        {"messages": [("user", "Demo question")]},
        context=Context(),
    )

    assert result["fixed_dag_plan"]["schema"] == "fixed_dag_plan_v1"
    assert result["workflow_snapshot"]["schema"] == "workflow_snapshot_v2"
    assert result["report_result"]["schema"] == "report_result_v1"
    assert result["final_answer_source"] == "reset_skeleton"
    assert result["is_last_step"] is True
    assert result["final_emit_payload"]["source"] == "reset_skeleton"
    assert result["emitted_bundle"]["provider_invoked"] is False
    assert result["emitted_bundle"]["external_invoked"] is False
    assert result["multi_agent_bundle"]["schema"] == "fixed_dag_reset_bundle_v1"
    assert set(DIMENSION_GROUPS) == {
        item["id"] for item in result["workflow_snapshot"]["dimensionGroups"]
    }
    assert "Fixed DAG reset skeleton is active" in result["messages"][-1].content
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
