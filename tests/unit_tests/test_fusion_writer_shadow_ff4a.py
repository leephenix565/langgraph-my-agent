import react_agent.graph as graph_module


def test_fusion_writer_shadow_is_not_active_reset_node() -> None:
    assert "fusion_writer_shadow" not in graph_module.builder.nodes
    assert not hasattr(graph_module, "fusion_writer_shadow")


def test_report_generator_replaces_fusion_writer() -> None:
    assert "report_generator" in graph_module.builder.nodes
    assert hasattr(graph_module, "report_generator_node")
