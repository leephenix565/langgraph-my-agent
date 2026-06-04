import pytest

import react_agent.graph as graph_module
from react_agent.context import Context

pytestmark = pytest.mark.anyio


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
