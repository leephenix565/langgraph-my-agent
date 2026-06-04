import react_agent.graph as graph_module


def test_report_center_assignment_is_replaced_by_report_generator_node() -> None:
    assert not hasattr(graph_module, "manager_broadcast")
    assert "report_generator" in graph_module.builder.nodes
