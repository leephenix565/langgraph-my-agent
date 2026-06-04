import react_agent.graph as graph_module


def test_router_plan_summary_is_not_sent_to_a01_in_reset_graph() -> None:
    assert not hasattr(graph_module, "_summarize_router_plan")
    assert not hasattr(graph_module, "_build_agent_node")
    assert "route_planner" in graph_module.builder.nodes
