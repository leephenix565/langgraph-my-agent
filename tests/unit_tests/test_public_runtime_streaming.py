from react_agent.public_runtime import _build_stage_progress_data


def _statuses(data):
    return {stage.key: stage.status for stage in data.stages}


def test_stage_progress_starts_with_routing_running():
    data = _build_stage_progress_data({})
    assert data.currentStage == "routing"
    assert _statuses(data) == {
        "routing": "running",
        "analysis": "waiting",
        "risk": "waiting",
        "summary": "waiting",
        "fusion": "waiting",
    }


def test_stage_progress_marks_fusion_complete_when_answer_is_emitted():
    data = _build_stage_progress_data(
        {
            "layer_plan": {"L1": ["a01_cio_orchestrator"]},
            "current_layer": "L4",
            "layer_done": {"L1": True, "L2": True, "L3": True},
            "mainline_status": "ready",
            "emitted_bundle": {"answer": "Final answer"},
            "final_answer_source": "fused",
            "baseline_status": "ready",
            "judge_status": "ready",
            "writer_status": "ready",
        }
    )
    assert data.currentStage == "fusion"
    assert _statuses(data) == {
        "routing": "completed",
        "analysis": "completed",
        "risk": "completed",
        "summary": "completed",
        "fusion": "completed",
    }


def test_stage_progress_marks_failed_fusion_when_stream_errors_after_start():
    data = _build_stage_progress_data(
        {
            "layer_plan": {"L1": ["a01_cio_orchestrator"]},
            "current_layer": "L4",
            "layer_done": {"L1": True, "L2": True, "L3": True},
            "baseline_status": "ready",
        },
        failed=True,
    )
    assert data.currentStage == "fusion"
    assert _statuses(data)["fusion"] == "failed"
