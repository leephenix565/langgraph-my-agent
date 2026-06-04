from react_agent.graph import route_planner_node


def test_route_planner_resets_stable_findings_for_skeleton_turn() -> None:
    update = route_planner_node({"messages": [("user", "q")], "stable_findings": [{"old": True}]})
    assert update["stable_findings"] == []
    assert update["fixed_dag_plan"]["schema"] == "fixed_dag_plan_v1"
