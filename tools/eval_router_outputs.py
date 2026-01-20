#!/usr/bin/env python
"""Offline evaluator for router raw outputs.

Input JSONL format (per line):
  {"id": "...", "raw_text": "..."}

Accepted raw field names: raw_text | raw | text | output

Sample input:
  tools/sample_router_preds.jsonl

How to generate preds:
  Run any model on your validation prompts and save the raw assistant output
  into JSONL lines with fields {id, raw_text}.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from react_agent import router_parse


def _load_catalog_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    latest_path = Path("data/catalogs/LATEST")
    if not latest_path.exists():
        raise ValueError("Missing data/catalogs/LATEST; pass --catalog-id explicitly")
    text = latest_path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("data/catalogs/LATEST is empty; pass --catalog-id explicitly")
    return text


def _load_catalog_prompt(path: Path) -> Dict[str, List[str]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    layers = payload.get("layers")
    if not isinstance(layers, dict):
        raise ValueError("Catalog prompt missing layers")
    catalog: Dict[str, List[str]] = {}
    for layer in router_parse.LAYER_ORDER:
        entries = layers.get(layer)
        if not isinstance(entries, list):
            raise ValueError(f"Catalog prompt missing layer: {layer}")
        ids: List[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"Catalog entry not an object in {layer}")
            aid = entry.get("id")
            if not isinstance(aid, str) or not aid:
                raise ValueError(f"Catalog entry missing id in {layer}")
            ids.append(aid)
        catalog[layer] = ids
    return catalog


def _read_jsonl(path: Path) -> Tuple[List[Dict[str, Any]], int]:
    records: List[Dict[str, Any]] = []
    invalid_lines = 0
    with path.open("r", encoding="utf-8-sig") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            if isinstance(obj, dict):
                records.append(obj)
            else:
                invalid_lines += 1
    return records, invalid_lines


def _sha256_file(path: Path) -> str:
    if not path or not path.exists():
        return "unknown"
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.STDOUT)
            .decode("utf-8", errors="replace")
            .strip()
        )
    except Exception:
        return "unknown"


def _extract_raw_text(record: Dict[str, Any]) -> str:
    for key in ("raw_text", "raw", "text", "output"):
        value = record.get(key)
        if isinstance(value, str):
            return value
    return ""


def compute_metrics(records: Iterable[Dict[str, Any]], agent_catalog: Dict[str, List[str]]) -> Dict[str, Any]:
    total = 0
    valid_json = 0
    used_default = 0
    l2_trunc = 0
    filtered_total = 0

    mode_dist: Dict[str, Dict[str, int]] = {layer: {} for layer in router_parse.LAYER_ORDER}
    l2_len_dist = Counter()
    l3_len_dist = Counter()

    for record in records:
        raw_text = _extract_raw_text(record)
        plan, modes, stats = router_parse.parse_router_layers_with_stats(raw_text, agent_catalog)
        total += 1
        if stats.get("parse_ok"):
            valid_json += 1
        if stats.get("used_default_plan"):
            used_default += 1
        if stats.get("l2_truncated"):
            l2_trunc += 1
        filtered_total += int(stats.get("filtered_agents", 0))

        for layer in router_parse.LAYER_ORDER:
            mode = modes.get(layer, "Star")
            mode_dist[layer][mode] = mode_dist[layer].get(mode, 0) + 1

        l2_len_dist[str(len(plan.get("L2", [])))] += 1
        l3_len_dist[str(len(plan.get("L3", [])))] += 1

    valid_rate = valid_json / total if total else 0.0
    used_default_rate = used_default / total if total else 0.0
    l2_trunc_rate = l2_trunc / total if total else 0.0
    avg_filtered = filtered_total / total if total else 0.0

    return {
        "total": total,
        "valid_json_rate": valid_rate,
        "used_default_plan_rate": used_default_rate,
        "l2_trunc_rate": l2_trunc_rate,
        "avg_filtered_agents": avg_filtered,
        "mode_dist": mode_dist,
        "l2_len_dist": dict(l2_len_dist),
        "l3_len_dist": dict(l3_len_dist),
    }


def _print_summary(metrics: Dict[str, Any], invalid_lines: int) -> None:
    print(f"total: {metrics.get('total', 0)}")
    print(f"invalid_lines: {invalid_lines}")
    print(f"valid_json_rate: {metrics.get('valid_json_rate', 0.0):.4f}")
    print(f"used_default_plan_rate: {metrics.get('used_default_plan_rate', 0.0):.4f}")
    print(f"l2_trunc_rate: {metrics.get('l2_trunc_rate', 0.0):.4f}")
    print(f"avg_filtered_agents: {metrics.get('avg_filtered_agents', 0.0):.4f}")
    print("mode_dist:")
    mode_dist = metrics.get("mode_dist", {})
    for layer in router_parse.LAYER_ORDER:
        items = mode_dist.get(layer, {})
        if not items:
            print(f"  - {layer}: (none)")
            continue
        parts = ", ".join(f"{k}={v}" for k, v in sorted(items.items()))
        print(f"  - {layer}: {parts}")
    print("l2_len_dist:", metrics.get("l2_len_dist", {}))
    print("l3_len_dist:", metrics.get("l3_len_dist", {}))


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate router raw outputs with runtime parser.")
    ap.add_argument("--in", dest="in_path", required=True, help="Input JSONL with id + raw_text")
    ap.add_argument("--out", required=True, help="Output metrics.json path")
    ap.add_argument("--catalog-id", default=None)
    ap.add_argument("--catalog-prompt", default=None)
    ap.add_argument("--val-messages", default=None, help="Optional val messages JSONL for metadata")
    args = ap.parse_args()

    catalog_id = _load_catalog_id(args.catalog_id)
    catalog_prompt = (
        Path(args.catalog_prompt)
        if args.catalog_prompt
        else Path("data/catalogs") / f"catalog_{catalog_id}_prompt.json"
    )
    agent_catalog = _load_catalog_prompt(catalog_prompt)

    in_path = Path(args.in_path)
    records, invalid_lines = _read_jsonl(in_path)

    metrics = compute_metrics(records, agent_catalog)
    catalog_latest_path = Path("data/catalogs/LATEST")
    catalog_latest_sha256 = _sha256_file(catalog_latest_path) if catalog_latest_path.exists() else "unknown"
    catalog_resolved_path = catalog_prompt if catalog_prompt.exists() else None
    catalog_sha256 = _sha256_file(catalog_resolved_path) if catalog_resolved_path else "unknown"
    val_messages_path = Path(args.val_messages) if args.val_messages else None
    val_messages_sha256 = _sha256_file(val_messages_path) if val_messages_path else "unknown"
    if val_messages_path is None:
        for record in records:
            meta = record.get("meta")
            if not isinstance(meta, dict):
                continue
            raw_path = meta.get("source_val_path")
            raw_sha = meta.get("source_val_sha256")
            if isinstance(raw_path, str) and raw_path.strip():
                val_messages_path = Path(raw_path)
                val_messages_sha256 = (
                    raw_sha if isinstance(raw_sha, str) and raw_sha else _sha256_file(val_messages_path)
                )
                break
    metrics["meta"] = {
        "git_commit": _git_commit(),
        "preds_path": str(in_path),
        "preds_sha256": _sha256_file(in_path),
        "catalog_latest_path": str(catalog_latest_path),
        "catalog_latest_sha256": catalog_latest_sha256,
        "catalog_resolved_path": str(catalog_resolved_path) if catalog_resolved_path else "unknown",
        "catalog_sha256": catalog_sha256,
        "val_messages_path": str(val_messages_path) if val_messages_path else "unknown",
        "val_messages_sha256": val_messages_sha256,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_summary(metrics, invalid_lines)
    print(f"out: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
