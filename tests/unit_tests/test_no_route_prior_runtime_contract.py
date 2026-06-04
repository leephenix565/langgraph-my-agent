import asyncio

import react_agent.graph as graph_module
from react_agent.context import Context


def test_graph_import_and_run_without_route_prior_runtime_seam() -> None:
    result = asyncio.run(
        graph_module.graph.ainvoke(
            {"messages": [("user", "q")]},
            context=Context(),
        )
    )
    assert result["fixed_dag_plan"]["schema"] == "fixed_dag_plan_v1"
    assert "route_prior" not in result
    assert "layer_plan" not in result


def test_provider_failure_path_is_not_part_of_route_planner(monkeypatch) -> None:
    monkeypatch.setattr(
        "react_agent.default_agents.load_chat_model",
        lambda _name: (_ for _ in ()).throw(AssertionError("provider called")),
    )
    update = graph_module.route_planner_node({"messages": [("user", "q")]})
    assert update["fixed_dag_plan"]["schema"] == "fixed_dag_plan_v1"
    assert update["workflow_snapshot"]["schema"] == "workflow_snapshot_v2"
