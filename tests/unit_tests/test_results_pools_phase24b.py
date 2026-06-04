from react_agent.fixed_dag_contracts import build_deterministic_fixed_dag_plan
from react_agent.graph import final_emit_node, run_l2_conclusions_node


def test_l2_conclusions_replace_legacy_results_pools() -> None:
    plan = build_deterministic_fixed_dag_plan("q")
    update = run_l2_conclusions_node({"fixed_dag_plan": plan})
    assert "l2_conclusions" in update
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
