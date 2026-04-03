#!/usr/bin/env python
"""Gate deterministic FF-5B fusion regression metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


REQUIRED_SCENARIO_IDS = {
    "flag_off_mainline_lock",
    "source_switch_baseline",
    "source_switch_fused",
    "baseline_error_fallback",
    "baseline_disabled_fallback",
    "invalid_selected_source_fallback",
    "results_pool_isolation",
    "stable_findings_alignment",
    "thread_summary_alignment",
}


THRESHOLDS: Dict[str, Any] = {
    "case_count_min": 9,
    "business_failure_rate_max": 0.0,
    "results_pool_pollution_count_max": 0,
    "flag_off_mainline_lock_rate_min": 1.0,
    "source_selection_alignment_rate_min": 1.0,
    "emitted_bundle_alignment_rate_min": 1.0,
    "stable_findings_alignment_rate_min": 1.0,
    "thread_summary_alignment_rate_min": 1.0,
    "degraded_fallback_to_mainline_rate_min": 1.0,
    "baseline_search_executed_rate_min": 1.0,
}


def evaluate_gate(metrics: Mapping[str, Any]) -> Dict[str, Any]:
    failing_checks: List[Dict[str, Any]] = []
    warning_checks: List[Dict[str, Any]] = []

    scenario_ids = set(metrics.get("scenario_ids", [])) if isinstance(metrics.get("scenario_ids", []), list) else set()
    missing_ids = sorted(REQUIRED_SCENARIO_IDS - scenario_ids)
    if len(scenario_ids) < THRESHOLDS["case_count_min"]:
        failing_checks.append(
            {
                "name": "case_count",
                "expected": f">={THRESHOLDS['case_count_min']}",
                "actual": metrics.get("case_count", 0),
            }
        )
    if missing_ids:
        failing_checks.append(
            {
                "name": "required_scenario_ids",
                "expected": sorted(REQUIRED_SCENARIO_IDS),
                "actual": sorted(scenario_ids),
                "missing": missing_ids,
            }
        )

    def _require_max(name: str, metric_key: str) -> None:
        actual = metrics.get(metric_key, 0)
        expected = THRESHOLDS[f"{metric_key}_max"]
        if actual > expected:
            failing_checks.append({"name": name, "expected": f"<={expected}", "actual": actual})

    def _require_min(name: str, metric_key: str, *, relevant_key: str | None = None) -> None:
        if relevant_key is not None and int(metrics.get(relevant_key, 0) or 0) == 0:
            warning_checks.append({"name": name, "warning": f"not evaluated; {relevant_key}=0"})
            return
        actual = float(metrics.get(metric_key, 0.0) or 0.0)
        expected = float(THRESHOLDS[f"{metric_key}_min"])
        if actual < expected:
            failing_checks.append({"name": name, "expected": f">={expected}", "actual": actual})

    _require_max("business_failure_rate", "business_failure_rate")
    _require_max("results_pool_pollution_count", "results_pool_pollution_count")
    _require_min("flag_off_mainline_lock_rate", "flag_off_mainline_lock_rate")
    _require_min("source_selection_alignment_rate", "source_selection_alignment_rate")
    _require_min("emitted_bundle_alignment_rate", "emitted_bundle_alignment_rate")
    _require_min("stable_findings_alignment_rate", "stable_findings_alignment_rate")
    _require_min(
        "thread_summary_alignment_rate",
        "thread_summary_alignment_rate",
        relevant_key="thread_summary_relevant_cases",
    )
    _require_min(
        "degraded_fallback_to_mainline_rate",
        "degraded_fallback_to_mainline_rate",
        relevant_key="degraded_relevant_cases",
    )
    _require_min(
        "baseline_search_executed_rate",
        "baseline_search_executed_rate",
        relevant_key="baseline_search_relevant_cases",
    )

    trace_noise_count = int(metrics.get("trace_noise_count", 0) or 0)
    if trace_noise_count > 0:
        warning_checks.append(
            {
                "name": "trace_noise_present",
                "warning": "Trace noise is recorded separately and does not count as a business failure.",
                "actual": trace_noise_count,
            }
        )

    return {
        "gate_pass": not failing_checks,
        "failing_checks": failing_checks,
        "warning_checks": warning_checks,
        "thresholds": THRESHOLDS,
        "metrics_snapshot": dict(metrics),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gate deterministic FF-5B fusion regression metrics.")
    parser.add_argument(
        "--in",
        dest="in_path",
        default=str(REPO_ROOT / "ops" / "regression" / "fusion" / "out" / "fusion_metrics.json"),
        help="Path to fusion_metrics.json.",
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "ops" / "regression" / "fusion" / "out" / "fusion_gate.json"),
        help="Output gate JSON path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    in_path = Path(args.in_path)
    out_path = Path(args.out)
    metrics = json.loads(in_path.read_text(encoding="utf-8"))
    gate = evaluate_gate(metrics)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"gate_pass: {gate['gate_pass']}")
    print(f"failing_checks: {len(gate['failing_checks'])}")
    print(f"warning_checks: {len(gate['warning_checks'])}")
    print(f"out: {out_path}")
    return 0 if gate["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
