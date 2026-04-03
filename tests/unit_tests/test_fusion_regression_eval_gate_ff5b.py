import asyncio
import json

from ops.regression.fusion.eval_fusion_outputs import compute_metrics, read_jsonl
from ops.regression.fusion.gate_fusion_outputs import evaluate_gate
from ops.regression.fusion.run_fusion_regression import run_all_scenarios, write_jsonl
from ops.regression.fusion.scenario_catalog import SCENARIOS


def test_ff5b_run_eval_gate_round_trip(tmp_path) -> None:
    out_dir = tmp_path / "fusion"
    runs_path = out_dir / "fusion_runs.jsonl"
    metrics_path = out_dir / "fusion_metrics.json"
    gate_path = out_dir / "fusion_gate.json"

    records = asyncio.run(run_all_scenarios(SCENARIOS))
    write_jsonl(records, runs_path)

    assert runs_path.exists()
    parsed_records = read_jsonl(runs_path)
    assert len(parsed_records) == len(SCENARIOS)
    assert {record["case_id"] for record in parsed_records} == {scenario.case_id for scenario in SCENARIOS}
    assert all(record["business_status"] == "pass" for record in parsed_records)

    metrics = compute_metrics(parsed_records)
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    assert metrics["case_count"] == len(SCENARIOS)
    assert metrics["business_failure_rate"] == 0.0
    assert metrics["trace_noise_count"] == 0
    assert metrics["final_source_dist"]["mainline"] >= 1
    assert metrics["final_source_dist"]["baseline"] >= 1
    assert metrics["final_source_dist"]["fused"] >= 1

    gate = evaluate_gate(metrics)
    gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    assert gate["gate_pass"] is True
    assert gate["failing_checks"] == []


def test_ff5b_gate_treats_trace_noise_as_warning_only() -> None:
    metrics = {
        "case_count": len(SCENARIOS),
        "scenario_ids": [scenario.case_id for scenario in SCENARIOS],
        "final_source_dist": {"mainline": 3, "baseline": 3, "fused": 3},
        "flag_off_mainline_lock_rate": 1.0,
        "source_selection_alignment_rate": 1.0,
        "emitted_bundle_alignment_rate": 1.0,
        "stable_findings_alignment_rate": 1.0,
        "thread_summary_alignment_rate": 1.0,
        "thread_summary_relevant_cases": 1,
        "baseline_ready_rate": 0.7,
        "baseline_search_executed_rate": 1.0,
        "baseline_search_relevant_cases": 3,
        "judge_ready_rate": 1.0,
        "writer_ready_rate": 1.0,
        "degraded_fallback_to_mainline_rate": 1.0,
        "degraded_relevant_cases": 3,
        "results_pool_pollution_count": 0,
        "business_failure_rate": 0.0,
        "trace_noise_count": 2,
    }

    gate = evaluate_gate(metrics)

    assert gate["gate_pass"] is True
    assert gate["failing_checks"] == []
    assert any(check["name"] == "trace_noise_present" for check in gate["warning_checks"])
