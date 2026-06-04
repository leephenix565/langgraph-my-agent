import react_agent.graph as graph_module


def test_fixed_dag_graph_does_not_register_dynamic_agent_nodes() -> None:
    assert not hasattr(graph_module, "_build_agent_node")
    assert not any(name.startswith("agent_") for name in graph_module.builder.nodes)


def test_agent_tool_registry_is_retained_for_later_wrapper_phases() -> None:
    assert graph_module.AGENT_TOOLS
    assert len(graph_module.AGENT_IDS_FOR_NODES) == 25
