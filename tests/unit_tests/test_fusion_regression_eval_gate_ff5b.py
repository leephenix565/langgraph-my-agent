import react_agent.graph as graph_module


def test_fusion_eval_gate_is_not_reset_acceptance_surface() -> None:
    assert "fusion_gate" not in graph_module.builder.nodes
    assert "final_emit" in graph_module.builder.nodes
