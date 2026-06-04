from react_agent.graph import memory_update_node


def test_memory_update_node_is_noop_in_reset_skeleton() -> None:
    assert memory_update_node({"is_last_step": True}) == {}
