import react_agent.graph as graph_module


def test_fair_fusion_fan_in_seam_removed_from_active_graph() -> None:
    for node in ("manager_summary", "fusion_gate", "fusion_judge_shadow", "fusion_writer_shadow"):
        assert node not in graph_module.builder.nodes
        assert not hasattr(graph_module, node)


def test_fixed_dag_uses_dimension_composite_stage_instead() -> None:
    assert "run_dimension_composites" in graph_module.builder.nodes
