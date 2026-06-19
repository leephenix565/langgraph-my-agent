from react_agent.graph import final_emit_node


def test_reset_final_emit_builds_single_bundle() -> None:
    update = final_emit_node({"report_result": {"answer": "answer"}})
    assert update["multi_agent_bundle"]["schema"] == "fixed_dag_reset_bundle_v1"
    assert update["emitted_bundle"]["answer"] == "answer"


def test_reset_final_emit_preserves_report_sections_and_limitations() -> None:
    update = final_emit_node(
        {
            "report_result": {
                "answer": "answer",
                "sections": [
                    {
                        "id": "value",
                        "title": "价值分析",
                        "content": "估值细节",
                    }
                ],
                "evidence_cards": [{"title": "估值证据", "note": "PE"}],
                "limitations": ["显式开关路径。"],
            }
        }
    )

    assert update["multi_agent_bundle"]["report_result"]["sections"][0]["title"] == "价值分析"
    assert update["final_emit_payload"]["sections"][0]["title"] == "价值分析"
    assert update["emitted_bundle"]["sections"][0]["content"] == "估值细节"
    assert update["emitted_bundle"]["evidence_cards"][0]["title"] == "估值证据"
    assert update["emitted_bundle"]["limitations"] == ["显式开关路径。"]
