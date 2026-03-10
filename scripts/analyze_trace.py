"""Aggregate LOCAL_TRACE jsonl files into a stable JSON summary."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            return None
        try:
            return int(float(txt))
        except Exception:
            return None
    return None


def _numeric_stats(values: List[int]) -> Dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "median": None, "max": None}
    xs = sorted(values)
    return {"count": len(xs), "min": xs[0], "median": median(xs), "max": xs[-1]}


def load_trace_records(log_dir: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for path in sorted(log_dir.glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                obj["_source_file"] = path.name
                records.append(obj)
    return records


def _ctx_event_summary(records: List[Dict[str, Any]], event_name: str, window_size: int) -> Dict[str, Any]:
    matched = [r for r in records if r.get("event") == event_name]
    ctx_vals: List[int] = []
    full_vals: List[int] = []
    violations = 0
    for rec in matched:
        ctx = _to_int(rec.get("ctx_messages_len"))
        full = _to_int(rec.get("full_messages_len"))
        if ctx is not None:
            ctx_vals.append(ctx)
        if full is not None:
            full_vals.append(full)
        if ctx is not None and full is not None and full > window_size and ctx > window_size:
            violations += 1
    return {
        "count": len(matched),
        "ctx_messages_len": _numeric_stats(ctx_vals),
        "full_messages_len": _numeric_stats(full_vals),
        "window_size": window_size,
        "window_violations": violations,
    }


def _stable_consume_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = [r for r in records if r.get("event") == "stable_consume"]
    by_node: Dict[str, List[int]] = defaultdict(list)
    for rec in matched:
        node = str(rec.get("node") or "unknown")
        summary_len = _to_int(rec.get("stable_summary_len"))
        if summary_len is not None:
            by_node[node].append(summary_len)

    node_stats: Dict[str, Dict[str, Any]] = {}
    for node, vals in sorted(by_node.items()):
        node_stats[node] = _numeric_stats(vals)

    samples: List[Dict[str, Any]] = []
    if matched:
        head = matched[:2]
        tail = matched[-1:]
        for rec in head + tail:
            samples.append(
                {
                    "ts": rec.get("ts"),
                    "node": rec.get("node"),
                    "enabled": rec.get("enabled"),
                    "stable_len": rec.get("stable_len"),
                    "stable_summary_len": rec.get("stable_summary_len"),
                    "run_id": rec.get("run_id"),
                }
            )
    return {"count": len(matched), "by_node": node_stats, "samples": samples}


def summarize_log_dir(log_dir: Path, window_size: int = 20) -> Dict[str, Any]:
    records = load_trace_records(log_dir)
    event_counts = Counter(str(rec.get("event")) for rec in records if rec.get("event"))
    summary: Dict[str, Any] = {
        "log_dir": str(log_dir.resolve()),
        "log_files": sorted(path.name for path in log_dir.glob("*.jsonl")),
        "total_records": len(records),
        "event_counts": dict(sorted(event_counts.items())),
        "ctx_stats": {
            "router_ctx": _ctx_event_summary(records, "router_ctx", window_size),
            "manager_ctx": _ctx_event_summary(records, "manager_ctx", window_size),
        },
        "stable_consume": _stable_consume_summary(records),
    }
    per_turn_path = log_dir / "per_turn_summary.json"
    if per_turn_path.exists():
        try:
            per_turn = json.loads(per_turn_path.read_text(encoding="utf-8"))
        except Exception:
            per_turn = None
        summary["per_turn"] = per_turn
    return summary


def _print_table(summary: Dict[str, Any]) -> None:
    print(f"log_dir: {summary.get('log_dir')}")
    print(f"log_files: {len(summary.get('log_files', []))} | total_records: {summary.get('total_records', 0)}")
    print("event_counts:")
    for k, v in summary.get("event_counts", {}).items():
        print(f"  - {k}: {v}")
    print("ctx_stats:")
    for name in ("router_ctx", "manager_ctx"):
        block = (summary.get("ctx_stats") or {}).get(name, {})
        ctx = block.get("ctx_messages_len", {})
        full = block.get("full_messages_len", {})
        print(
            f"  - {name}: count={block.get('count', 0)} "
            f"ctx[min/med/max]={ctx.get('min')}/{ctx.get('median')}/{ctx.get('max')} "
            f"full[min/med/max]={full.get('min')}/{full.get('median')}/{full.get('max')} "
            f"violations={block.get('window_violations', 0)}"
        )
    stable = summary.get("stable_consume", {})
    print(f"stable_consume: count={stable.get('count', 0)}")
    for node, stats in (stable.get("by_node") or {}).items():
        print(f"  - {node}: min/med/max={stats.get('min')}/{stats.get('median')}/{stats.get('max')}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze LOCAL_TRACE jsonl files under LOG_DIR.")
    parser.add_argument("--log_dir", type=str, required=True)
    parser.add_argument("--window_size", type=int, default=20)
    parser.add_argument("--out_json", type=str, default="")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    log_dir = Path(args.log_dir)
    summary = summarize_log_dir(log_dir=log_dir, window_size=max(1, args.window_size))
    if not args.quiet:
        _print_table(summary)
    if args.out_json:
        out_path = Path(args.out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[done] wrote {out_path}")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
