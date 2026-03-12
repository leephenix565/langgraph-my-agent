from ops.train_eval.a01.generate_a01_teacher_contracts import compute_quality_distribution_stats


def test_quality_distribution_stats_basic() -> None:
    generic_ratio_list = [0.1, 0.2, 0.3, 0.4, 0.5]
    very_generic_ratio_list = [0.05, 0.1, 0.15, 0.2, 0.25]
    steps_per_task_list = [2.0, 2.5, 3.0, 3.5, 4.0]

    stats = compute_quality_distribution_stats(
        generic_ratio_list,
        very_generic_ratio_list,
        steps_per_task_list,
        duplicate_steps_contract_count=2,
        contract_ok=5,
    )

    assert stats["generic_ratio_p50"] == 0.3
    assert stats["generic_ratio_p90"] == 0.5
    assert stats["generic_ratio_p95"] == 0.5
    assert stats["very_generic_ratio_p50"] == 0.15
    assert stats["very_generic_ratio_p90"] == 0.25
    assert stats["very_generic_ratio_p95"] == 0.25
    assert stats["steps_per_task_p50"] == 3.0
    assert stats["steps_per_task_p90"] == 4.0
    assert stats["steps_per_task_p95"] == 4.0
    assert stats["duplicate_steps_contract_rate"] == 0.4
