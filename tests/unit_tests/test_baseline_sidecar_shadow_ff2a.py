import react_agent.graph as graph_module


def test_baseline_sidecar_is_not_registered_in_active_reset_graph() -> None:
    assert "baseline_sidecar" not in graph_module.builder.nodes
    assert "fusion_gate" not in graph_module.builder.nodes
    assert "fusion_judge_shadow" not in graph_module.builder.nodes
    assert "fusion_writer_shadow" not in graph_module.builder.nodes


def test_reset_graph_keeps_single_public_emit_node() -> None:
    assert "final_emit" in graph_module.builder.nodes
    assert hasattr(graph_module, "final_emit_node")
