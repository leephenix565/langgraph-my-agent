from react_agent.graph import final_emit_node


def test_reset_final_emit_builds_single_bundle() -> None:
    update = final_emit_node({"report_result": {"answer": "answer"}})
    assert update["multi_agent_bundle"]["schema"] == "fixed_dag_reset_bundle_v1"
    assert update["emitted_bundle"]["answer"] == "answer"
