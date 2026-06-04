import react_agent.graph as graph_module


def test_a01_contract_dispatch_is_not_active_reset_protocol() -> None:
    assert not hasattr(graph_module, "manager_broadcast")
    assert "manager_broadcast" not in graph_module.builder.nodes


def test_fixed_dag_plan_is_active_dispatch_protocol() -> None:
    assert "route_planner" in graph_module.builder.nodes
    assert "prepare_l1_context" in graph_module.builder.nodes
    assert "execute_fixed_dag" in graph_module.builder.nodes
    assert "run_l2_conclusions" not in graph_module.builder.nodes
