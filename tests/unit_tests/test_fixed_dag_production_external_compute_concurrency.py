from react_agent.fixed_dag.external import prod_compute


def test_stage_concurrency_honors_source_controlled_policy_values() -> None:
    policy = {"max_concurrency_by_stage": {"l2": 20, "l3": 2}}

    assert prod_compute._stage_concurrency(policy, "l2_analysis") == 20
    assert prod_compute._stage_concurrency(policy, "dimension_composite") == 2


def test_stage_concurrency_keeps_safe_fallback_for_missing_invalid_or_low_values() -> None:
    assert prod_compute._stage_concurrency({}, "l2_analysis") == 1
    assert (
        prod_compute._stage_concurrency(
            {"max_concurrency_by_stage": {"l2": "invalid"}},
            "l2_analysis",
        )
        == 1
    )
    assert (
        prod_compute._stage_concurrency(
            {"max_concurrency_by_stage": {"l2": 0}},
            "l2_analysis",
        )
        == 1
    )


def test_run_stage_caps_workers_by_selected_rows(monkeypatch) -> None:
    captured_workers: list[int] = []

    class ImmediateFuture:
        def __init__(self, result: dict[str, object]) -> None:
            self._result = result

        def result(self, timeout: float | None = None) -> dict[str, object]:
            return self._result

        def cancel(self) -> bool:
            return False

    class RecordingExecutor:
        def __init__(self, max_workers: int) -> None:
            captured_workers.append(max_workers)

        def __enter__(self) -> "RecordingExecutor":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def submit(self, fn, **kwargs):  # noqa: ANN001, ANN202
            return ImmediateFuture(fn(**kwargs))

    def fake_invoke_one(*, row, **_kwargs):  # noqa: ANN001, ANN202
        return {
            "agent_id": row["agent_id"],
            "required_or_optional": row["required_or_optional"],
            "failure_policy": row["failure_policy"],
            "mapped_result": {"status": "failed", "failure_code": "unit"},
            "latency_ms": 0,
        }

    monkeypatch.setattr(prod_compute, "ThreadPoolExecutor", RecordingExecutor)
    monkeypatch.setattr(prod_compute, "_invoke_one", fake_invoke_one)

    rows = [
        (
            f"step-{idx}",
            {"id": f"step-{idx}", "stage": "l2_analysis", "agent_id": f"agent_{idx}"},
            {
                "agent_id": f"agent_{idx}",
                "required_or_optional": "required",
                "failure_policy": "fail_soft_to_pending_l2",
                "timeout_seconds": 30,
            },
        )
        for idx in range(3)
    ]

    outcomes = prod_compute._run_stage(
        stage="l2_analysis",
        rows=rows,
        question="q",
        as_of="2026-07-06",
        agent_tasks={},
        upstream_outputs=None,
        entry_registry={},
        policy={"max_concurrency_by_stage": {"l2": 20, "l3": 2}},
        transport=None,
    )

    assert captured_workers == [3]
    assert [item["agent_id"] for item in outcomes] == ["agent_0", "agent_1", "agent_2"]


def test_run_stage_uses_l2_policy_value_when_rows_exceed_policy(monkeypatch) -> None:
    captured_workers: list[int] = []

    class ImmediateFuture:
        def __init__(self, result: dict[str, object]) -> None:
            self._result = result

        def result(self, timeout: float | None = None) -> dict[str, object]:
            return self._result

        def cancel(self) -> bool:
            return False

    class RecordingExecutor:
        def __init__(self, max_workers: int) -> None:
            captured_workers.append(max_workers)

        def __enter__(self) -> "RecordingExecutor":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def submit(self, fn, **kwargs):  # noqa: ANN001, ANN202
            return ImmediateFuture(fn(**kwargs))

    def fake_invoke_one(*, row, **_kwargs):  # noqa: ANN001, ANN202
        return {
            "agent_id": row["agent_id"],
            "required_or_optional": row["required_or_optional"],
            "failure_policy": row["failure_policy"],
            "mapped_result": {"status": "failed", "failure_code": "unit"},
            "latency_ms": 0,
        }

    monkeypatch.setattr(prod_compute, "ThreadPoolExecutor", RecordingExecutor)
    monkeypatch.setattr(prod_compute, "_invoke_one", fake_invoke_one)

    rows = [
        (
            f"step-{idx}",
            {"id": f"step-{idx}", "stage": "l2_analysis", "agent_id": f"agent_{idx}"},
            {
                "agent_id": f"agent_{idx}",
                "required_or_optional": "required",
                "failure_policy": "fail_soft_to_pending_l2",
                "timeout_seconds": 30,
            },
        )
        for idx in range(25)
    ]

    outcomes = prod_compute._run_stage(
        stage="l2_analysis",
        rows=rows,
        question="q",
        as_of="2026-07-06",
        agent_tasks={},
        upstream_outputs=None,
        entry_registry={},
        policy={"max_concurrency_by_stage": {"l2": 20, "l3": 2}},
        transport=None,
    )

    assert captured_workers == [20]
    assert len(outcomes) == 25
