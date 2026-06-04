import react_agent.graph as graph_module


def test_fusion_judge_shadow_is_not_active_reset_node() -> None:
    assert "fusion_judge_shadow" not in graph_module.builder.nodes
    assert not hasattr(graph_module, "fusion_judge_shadow")


def test_reset_decision_synthesizer_replaces_judge_shadow() -> None:
    assert "execute_fixed_dag" in graph_module.builder.nodes
    assert "decision_synthesizer" not in graph_module.builder.nodes
    assert hasattr(graph_module, "decision_synthesizer_node")
