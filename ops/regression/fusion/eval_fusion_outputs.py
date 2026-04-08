#!/usr/bin/env python
"""Aggregate deterministic FF-5B fusion regression outputs into metrics."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
    return records


def _rate(values: Iterable[bool]) -> float:
    xs = list(values)
    if not xs:
        return 1.0
    return sum(1 for item in xs if item) / len(xs)


def compute_metrics(records: List[Mapping[str, Any]]) -> Dict[str, Any]:
    case_count = len(records)
    final_sources = Counter(str(record.get("final_answer_source", "") or "") for record in records)
    source_alignment_values: List[bool] = []
    emitted_alignment_values: List[bool] = []
    stable_alignment_values: List[bool] = []
    thread_alignment_values: List[bool] = []
    flag_off_values: List[bool] = []
    degraded_values: List[bool] = []
    results_pool_pollution_count = 0
    trace_noise_count = 0
    business_failures = 0
    baseline_ready = 0
    baseline_search_relevant_values: List[bool] = []
    judge_ready = 0
    writer_ready = 0
    thread_summary_relevant = 0
    degraded_relevant = 0

    for record in records:
        invariants = record.get("invariant_results", {})
        invariants = invariants if isinstance(invariants, dict) else {}
        expected_invariants = record.get("expected_invariants", {})
        expected_invariants = expected_invariants if isinstance(expected_invariants, dict) else {}

        source_alignment_values.append(bool(invariants.get("source_selection_alignment", False)))
        emitted_alignment_values.append(bool(invariants.get("emitted_bundle_alignment", False)))
        stable_alignment_values.append(bool(invariants.get("stable_findings_alignment", False)))

        if "thread_summary_alignment" in expected_invariants:
            thread_summary_relevant += 1
            thread_alignment_values.append(bool(invariants.get("thread_summary_alignment", False)))
        if "flag_off_mainline_lock" in expected_invariants:
            flag_off_values.append(bool(invariants.get("flag_off_mainline_lock", False)))
        if "degraded_fallback_to_mainline" in expected_invariants:
            degraded_relevant += 1
            degraded_values.append(bool(invariants.get("degraded_fallback_to_mainline", False)))

        if bool(record.get("results_pool_pollution", False)):
            results_pool_pollution_count += 1
        trace_noise = record.get("trace_noise", [])
        if isinstance(trace_noise, list):
            trace_noise_count += len(trace_noise)
        if str(record.get("business_status", "") or "") != "pass":
            business_failures += 1

        if str(record.get("baseline_status", "") or "") == "ready":
            baseline_ready += 1
            baseline_search_relevant_values.append(bool(record.get("baseline_search_executed", False)))
        if str(record.get("judge_status", "") or "") == "ready":
            judge_ready += 1
        if str(record.get("writer_status", "") or "") == "ready":
            writer_ready += 1

    metrics = {
        "case_count": case_count,
        "scenario_ids": [str(record.get("case_id", "") or "") for record in records],
        "final_source_dist": dict(sorted(final_sources.items())),
        "flag_off_mainline_lock_rate": _rate(flag_off_values),
        "source_selection_alignment_rate": _rate(source_alignment_values),
        "emitted_bundle_alignment_rate": _rate(emitted_alignment_values),
        "stable_findings_alignment_rate": _rate(stable_alignment_values),
        "thread_summary_alignment_rate": _rate(thread_alignment_values),
        "thread_summary_relevant_cases": thread_summary_relevant,
        "baseline_ready_rate": (baseline_ready / case_count) if case_count else 0.0,
        "baseline_search_executed_rate": _rate(baseline_search_relevant_values),
        "baseline_search_relevant_cases": len(baseline_search_relevant_values),
        "judge_ready_rate": (judge_ready / case_count) if case_count else 0.0,
        "writer_ready_rate": (writer_ready / case_count) if case_count else 0.0,
        "degraded_fallback_to_mainline_rate": _rate(degraded_values),
        "degraded_relevant_cases": degraded_relevant,
        "results_pool_pollution_count": results_pool_pollution_count,
        "business_failure_rate": (business_failures / case_count) if case_count else 0.0,
        "trace_noise_count": trace_noise_count,
    }
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate deterministic FF-5B fusion regression outputs.")
    parser.add_argument(
        "--in",
        dest="in_path",
        default=str(REPO_ROOT / "ops" / "regression" / "fusion" / "out" / "fusion_runs.jsonl"),
        help="Path to fusion_runs.jsonl.",
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "ops" / "regression" / "fusion" / "out" / "fusion_metrics.json"),
        help="Output metrics JSON path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    in_path = Path(args.in_path)
    out_path = Path(args.out)
    records = read_jsonl(in_path)
    metrics = compute_metrics(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"case_count: {metrics['case_count']}")
    print(f"business_failure_rate: {metrics['business_failure_rate']:.4f}")
    print(f"trace_noise_count: {metrics['trace_noise_count']}")
    print(f"out: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

