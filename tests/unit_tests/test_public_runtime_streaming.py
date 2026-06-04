from react_agent.fixed_dag_contracts import (
    build_deterministic_fixed_dag_plan,
    build_workflow_snapshot_v2,
)
from react_agent.fixed_dag_executor import execute_fixed_dag_plan
from react_agent.public_runtime import _build_stage_progress_data


def _statuses(data):
    return {stage.key: stage.status for stage in data.stages}


def test_stage_progress_starts_with_planning_running():
    data = _build_stage_progress_data({})
    assert data.currentStage == "planning"
    assert _statuses(data) == {
        "planning": "running",
        "evidence": "waiting",
        "l2_analysis": "waiting",
        "dimension_composite": "waiting",
        "decision": "waiting",
        "report": "waiting",
    }


def test_stage_progress_marks_report_complete_when_all_steps_done():
    plan = build_deterministic_fixed_dag_plan("q")
    snapshot = build_workflow_snapshot_v2(
        plan=plan,
        current_stage="report",
        completed_steps=[step["id"] for step in plan["steps"]],
    )
    data = _build_stage_progress_data({"workflow_snapshot": snapshot})
    assert data.currentStage == "report"
    assert set(_statuses(data).values()) == {"completed"}


def test_stage_progress_accepts_executor_snapshot_completion():
    plan = build_deterministic_fixed_dag_plan("q")
    execution = execute_fixed_dag_plan(plan, question="q", as_of="2026-06-04")
    data = _build_stage_progress_data({"workflow_snapshot": execution["workflow_snapshot"]})

    assert data.currentStage == "report"
    assert set(_statuses(data).values()) == {"completed"}


def test_stage_progress_marks_current_stage_failed_when_stream_errors():
    plan = build_deterministic_fixed_dag_plan("q")
    snapshot = build_workflow_snapshot_v2(
        plan=plan,
        current_stage="decision",
        completed_steps=["route_planner"],
    )
    data = _build_stage_progress_data({"workflow_snapshot": snapshot}, failed=True)
    assert data.currentStage == "decision"
    assert _statuses(data)["decision"] == "failed"
