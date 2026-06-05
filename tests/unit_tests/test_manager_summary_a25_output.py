from react_agent.fixed_dag_contracts import (
    build_decision_result,
    build_deterministic_fixed_dag_plan,
)
from react_agent.graph import final_emit_node, report_generator_node


def test_report_generator_placeholder_is_public_safe() -> None:
    plan = build_deterministic_fixed_dag_plan("market view")
    report = report_generator_node(
        {
            "current_question": "market view",
            "fixed_dag_plan": plan,
            "decision_result": build_decision_result(),
            "dimension_results": {},
        }
    )
    assert report["report_result"]["schema"] == "report_result_v1"
    assert report["report_result"]["status"] == "pending_implementation"
    assert "研判流程" in report["report_result"]["answer"]


def test_final_emit_uses_report_result_not_a25_manager_output() -> None:
    final = final_emit_node(
        {
            "fixed_dag_plan": build_deterministic_fixed_dag_plan("q"),
            "report_result": {"answer": "reset answer"},
        }
    )
    assert final["messages"][0].content == "reset answer"
    assert final["final_emit_payload"]["source"] == "reset_skeleton"
    assert final["emitted_bundle"]["summary_source"] == "reset_skeleton"
