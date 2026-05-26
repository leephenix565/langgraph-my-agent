from ops.train_eval.a01.generate_a01_teacher_contracts import compute_quality_metrics


def test_compute_quality_metrics_basic() -> None:
    contract = {
        "schema_version": "a01_contract_v0",
        "objective": "x",
        "constraints": ["c1"],
        "selected_agents": ["a01_cio_orchestrator", "a03_macro_industry_research"],
        "tasks": [
            {
                "agent_id": "a01_cio_orchestrator",
                "task_id": "L1-a01-001",
                "objective": "o1",
                "steps": ["输出", "评估"],
                "agent_can_extend_steps": True,
                "extension_policy": "ok",
            },
            {
                "agent_id": "a03_macro_industry_research",
                "task_id": "L2-a03-001",
                "objective": "o2",
                "steps": ["输出", "收集数据", "输出行业报告"],
                "agent_can_extend_steps": True,
                "extension_policy": "ok",
            },
        ],
        "aggregation": {"strategy": "x", "handoff_notes": "x"},
        "budget": {"time_budget": "x", "cost_budget": "x", "token_budget": "x"},
        "output_spec": {"required_sections": ["x"], "final_answer_format": "x"},
    }

    metrics = compute_quality_metrics(contract)

    assert metrics["steps_total"] == 5
    assert metrics["tasks_count"] == 2
    # generic: 输出(2), 评估(1), 收集(1), 输出行业报告(1) -> 5/5
    assert metrics["generic_ratio"] == 1.0
    # very_generic: 输出(2), 评估(1) -> 3/5
    assert metrics["very_generic_ratio"] == 0.6
    assert metrics["has_duplicate_steps"] is True
    assert metrics["steps_len_stats_per_record"]["count"] == 2
    assert metrics["steps_len_stats_per_record"]["min"] == 2
    assert metrics["steps_len_stats_per_record"]["max"] == 3
