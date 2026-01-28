from tools.generate_a01_teacher_contracts import (
    compute_quality_distribution_stats,
    compute_teacher_observability,
)


def test_quality_distribution_stats_empty_lists() -> None:
    stats = compute_quality_distribution_stats(
        [],
        [],
        [],
        duplicate_steps_contract_count=0,
        contract_ok=0,
    )
    assert stats["generic_ratio_p50"] == 0
    assert stats["very_generic_ratio_p95"] == 0
    assert stats["steps_per_task_p90"] == 0
    assert stats["duplicate_steps_contract_rate"] == 0.0


def test_compute_teacher_observability_usage() -> None:
    raw = '{"usage":{"total_tokens":123},"choices":[{"message":{"content":"ok"}}]}'
    obs = compute_teacher_observability("assistant", raw, 12.3)
    assert obs["elapsed_ms"] == 12.3
    assert obs["assistant_chars"] == 9
    assert obs["raw_chars"] == len(raw)
    assert obs["usage_total_tokens"] == 123
