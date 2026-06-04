import react_agent.graph as graph_module


def test_legacy_final_layer_finalize_is_not_active_reset_path() -> None:
    assert not hasattr(graph_module, "finalize_summary")
    assert "execute_fixed_dag" in graph_module.builder.nodes
    assert "report_generator" not in graph_module.builder.nodes
    assert hasattr(graph_module, "report_generator_node")
    assert "final_emit" in graph_module.builder.nodes
