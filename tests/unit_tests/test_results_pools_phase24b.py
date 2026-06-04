from react_agent.fixed_dag_contracts import build_deterministic_fixed_dag_plan
from react_agent.graph import execute_fixed_dag_node, final_emit_node


def test_l2_conclusions_replace_legacy_results_pools() -> None:
    plan = build_deterministic_fixed_dag_plan("q")
    update = execute_fixed_dag_node({"fixed_dag_plan": plan, "current_question": "q"})
    assert "l2_conclusions" in update
    assert "dag_step_results" in update
    assert "execution_batches" in update
    assert "analyst_results" not in update
    assert "ephemeral_results" not in update


def test_final_emit_keeps_legacy_results_out_of_public_bundle() -> None:
    update = final_emit_node(
        {
            "analyst_results": {"raw": {"analysis": "hide"}},
            "ephemeral_results": {"raw": {"analysis": "hide"}},
            "report_result": {"answer": "answer"},
        }
    )
    assert "analyst_results" not in update["multi_agent_bundle"]
    assert "ephemeral_results" not in update["multi_agent_bundle"]
