#!/usr/bin/env python
"""Gate a01 SFT run based on eval metrics and run_manifest evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate a01 SFT eval results.")
    ap.add_argument("--eval-report", required=True, help="Path to eval_report.json")
    ap.add_argument("--run-manifest", default="", help="Path to run_manifest.json")
    ap.add_argument("--min-valid-json-rate", type=float, default=0.9)
    ap.add_argument("--min-contract-ok-rate", type=float, default=0.9)
    ap.add_argument("--min-schema-keys-match-rate", type=float, default=0.9)
    args = ap.parse_args()

    report_path = Path(args.eval_report)
    if not report_path.exists():
        print("gate_fail: missing eval_report:", report_path)
        return 2
    report = _load_json(report_path)
    metrics = report.get("metrics") or {}

    manifest_path = Path(args.run_manifest) if args.run_manifest else report_path.parent / "run_manifest.json"
    if not manifest_path.exists():
        print("gate_fail: missing run_manifest:", manifest_path)
        return 2
    manifest = _load_json(manifest_path)
    if manifest.get("train_status") != "completed":
        print("gate_fail: train_status not completed")
        return 2

    vjr = float(metrics.get("valid_json_rate", 0.0))
    cor = float(metrics.get("contract_ok_rate", 0.0))
    skr = float(metrics.get("schema_keys_match_rate", 0.0))

    failures = []
    if vjr < args.min_valid_json_rate:
        failures.append(f"valid_json_rate {vjr:.4f} < {args.min_valid_json_rate}")
    if cor < args.min_contract_ok_rate:
        failures.append(f"contract_ok_rate {cor:.4f} < {args.min_contract_ok_rate}")
    if skr < args.min_schema_keys_match_rate:
        failures.append(f"schema_keys_match_rate {skr:.4f} < {args.min_schema_keys_match_rate}")

    if failures:
        print("gate_fail:")
        for item in failures:
            print(" -", item)
        return 1

    print("gate_ok")
    print("  eval_report:", report_path)
    print("  run_manifest:", manifest_path)
    print("  metrics:", metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
