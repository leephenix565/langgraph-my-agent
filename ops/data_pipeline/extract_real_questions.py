#!/usr/bin/env python
"""Extract real questions from log JSONL files."""

from __future__ import annotations

import argparse
import glob
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


TARGET_EVENTS: Tuple[str, ...] = ("run_start", "router_decision")
MAX_BUFFER_BYTES = 200 * 1024
MAX_BUFFER_LINES = 50


class Stats:
    def __init__(self) -> None:
        self.files_scanned = 0
        self.records_parsed_ok = 0
        self.records_recovered_ok = 0
        self.records_dropped = 0
        self.questions_raw = 0


def _validate_date(date_str: str) -> None:
    if not re.fullmatch(r"\d{8}", date_str):
        raise ValueError(f"Invalid --date '{date_str}', expected YYYYMMDD")


def _load_catalog_id(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    latest_path = Path("data/catalogs/LATEST")
    if not latest_path.exists():
        raise ValueError("Missing data/catalogs/LATEST; pass --catalog-id explicitly")
    text = latest_path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("data/catalogs/LATEST is empty; pass --catalog-id explicitly")
    if text.startswith("{"):
        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and isinstance(payload.get("catalog_id"), str):
                return payload["catalog_id"].strip()
        except Exception:
            pass
    return text


def _iter_log_files(pattern: str) -> List[Path]:
    files = [Path(p) for p in glob.glob(pattern, recursive=True)]
    files = [p for p in files if p.is_file()]
    return sorted(files, key=lambda p: str(p))


def _parse_lines(
    lines: Iterable[str],
    source_file: Path,
    stats: Stats,
    candidates: Dict[str, Dict[str, Dict[str, Any]]],
) -> None:
    buffer = ""
    buffer_lines = 0
    buffer_bytes = 0

    def handle_record(obj: Any) -> None:
        if not isinstance(obj, dict):
            return
        event = obj.get("event")
        if event not in TARGET_EVENTS:
            return
        question = obj.get("question")
        if not isinstance(question, str) or not question.strip():
            return
        run_id = obj.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            return
        ts_val = obj.get("ts")
        ts = ts_val if isinstance(ts_val, str) else ("" if ts_val is None else str(ts_val))
        record = {
            "question": question,
            "run_id": run_id,
            "ts": ts,
            "source_event": event,
            "source_file": str(source_file),
        }
        stats.questions_raw += 1
        entry = candidates.setdefault(run_id, {"run_start": None, "router_decision": None})
        if event == "run_start":
            entry["run_start"] = record
        elif entry.get("router_decision") is None:
            entry["router_decision"] = record

    for line in lines:
        if not line.strip():
            continue
        if not buffer:
            try:
                obj = json.loads(line)
            except Exception:
                buffer = line
                buffer_lines = 1
                buffer_bytes = len(line.encode("utf-8"))
                continue
            stats.records_parsed_ok += 1
            handle_record(obj)
            continue

        buffer += "\n" + line
        buffer_lines += 1
        buffer_bytes += len(line.encode("utf-8")) + 1
        try:
            obj = json.loads(buffer)
        except Exception:
            if buffer_bytes > MAX_BUFFER_BYTES or buffer_lines > MAX_BUFFER_LINES:
                stats.records_dropped += 1
                buffer = ""
                buffer_lines = 0
                buffer_bytes = 0
            continue
        stats.records_recovered_ok += 1
        handle_record(obj)
        buffer = ""
        buffer_lines = 0
        buffer_bytes = 0

    if buffer.strip():
        stats.records_dropped += 1


def _dedup_candidates(
    candidates: Dict[str, Dict[str, Dict[str, Any]]], catalog_id: str
) -> List[Dict[str, Any]]:
    results = []
    for run_id, entry in candidates.items():
        record = entry.get("run_start") or entry.get("router_decision")
        if not record:
            continue
        results.append(
            {
                "catalog_id": catalog_id,
                "question": record["question"],
                "run_id": record["run_id"],
                "ts": record["ts"],
                "source_event": record["source_event"],
                "source_file": record["source_file"],
            }
        )
    results.sort(key=lambda r: (r.get("ts", ""), r.get("run_id", "")))
    return results


def _write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _summarize(records: List[Dict[str, Any]], stats: Stats) -> None:
    by_source_event = Counter(r["source_event"] for r in records)
    question_counts = Counter(r["question"] for r in records)
    duplicates = [(q, c) for q, c in question_counts.items() if c > 1]
    duplicates.sort(key=lambda item: (-item[1], item[0]))

    print(f"files_scanned: {stats.files_scanned}")
    print(f"records_parsed_ok: {stats.records_parsed_ok}")
    print(f"records_recovered_ok: {stats.records_recovered_ok}")
    print(f"records_dropped: {stats.records_dropped}")
    print(f"questions_raw: {stats.questions_raw}")
    print(f"questions_dedup: {len(records)}")
    print(
        "by_source_event: "
        f"run_start={by_source_event.get('run_start', 0)}, "
        f"router_decision={by_source_event.get('router_decision', 0)}"
    )
    print("top_duplicate_questions:")
    if duplicates:
        for question, count in duplicates[:5]:
            preview = re.sub(r"\s+", " ", question).strip()
            if len(preview) > 160:
                preview = preview[:157] + "..."
            print(f"  - ({count}) {preview}")
    else:
        print("  - (none)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract real questions from log JSONL files.")
    parser.add_argument("--log-glob", default="log/**/*.jsonl", help="Glob for log JSONL files")
    parser.add_argument("--out", default=None, help="Output JSONL path")
    parser.add_argument("--date", default=None, help="Date override (YYYYMMDD)")
    parser.add_argument("--catalog-id", default=None, help="Catalog id override")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y%m%d")
    _validate_date(date_str)

    out_path = Path(args.out) if args.out else Path("data/questions") / f"real_questions_{date_str}.jsonl"
    catalog_id = _load_catalog_id(args.catalog_id)

    files = _iter_log_files(args.log_glob)
    stats = Stats()
    candidates: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for path in files:
        stats.files_scanned += 1
        text = path.read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        _parse_lines(lines, path, stats, candidates)

    records = _dedup_candidates(candidates, catalog_id)
    _write_jsonl(out_path, records)

    _summarize(records, stats)
    print(f"output_path: {out_path} (abs: {out_path.resolve()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
