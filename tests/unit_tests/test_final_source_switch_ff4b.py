from react_agent.graph import final_emit_node


def test_final_source_switch_is_collapsed_to_reset_skeleton() -> None:
    update = final_emit_node({"report_result": {"answer": "answer"}})
    assert update["final_answer_source"] == "reset_skeleton"
    assert update["final_emit_payload"]["source"] == "reset_skeleton"
    assert update["emitted_bundle"]["summary_source"] == "reset_skeleton"
