#!/usr/bin/env python
"""Merge real and synth question pools into a stable questions_pool JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _validate_date(date_str: str) -> str:
    s = date_str.strip()
    if not re.fullmatch(r"\d{8}", s):
        raise ValueError(f"Invalid --date '{date_str}' expected YYYYMMDD.")
    try:
        datetime.strptime(s, "%Y%m%d")
    except ValueError:
        raise ValueError(f"Invalid --date '{date_str}' expected YYYYMMDD.")
    return s


def _load_catalog_id(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    latest_path = Path("data/catalogs/LATEST")
    if not latest_path.exists():
        raise ValueError("Missing data/catalogs/LATEST; pass --catalog-id explicitly")
    text = latest_path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("data/catalogs/LATEST is empty; pass --catalog-id explicitly")
    return text


def _catalog_hash(catalog_id: str) -> Optional[str]:
    if not isinstance(catalog_id, str):
        return None
    raw = catalog_id.strip()
    if "_" not in raw:
        return None
    suffix = raw.rsplit("_", 1)[-1]
    if re.fullmatch(r"[0-9a-fA-F]{12}", suffix):
        return suffix.lower()
    return None


def _normalize_question(text: str) -> str:
    text = text.strip()
    return re.sub(r"\s+", " ", text)


def _question_id(text: str) -> str:
    norm = _normalize_question(text).lower()
    return f"sha256:{hashlib.sha256(norm.encode('utf-8')).hexdigest()}"


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                yield {"__invalid_json__": True}
                continue
            if isinstance(obj, dict):
                yield obj
            else:
                yield {"__invalid_json__": True}


def _apply_catalog_id(
    raw: Any,
    catalog_id: str,
    allow_mismatch: bool,
    strict_catalog_id: bool,
    stats: Dict[str, int],
) -> Tuple[Optional[str], bool]:
    if raw is None:
        return catalog_id, False
    if not isinstance(raw, str):
        stats["catalog_mismatch_strict"] += 1
        stats["catalog_mismatch"] += 1
        if strict_catalog_id:
            return None, False
        if allow_mismatch:
            return catalog_id, True
        return None, False
    raw_clean = raw.strip()
    if raw_clean == catalog_id:
        return catalog_id, False
    if strict_catalog_id:
        stats["catalog_mismatch_strict"] += 1
        stats["catalog_mismatch"] += 1
        return None, False
    raw_hash = _catalog_hash(raw_clean)
    current_hash = _catalog_hash(catalog_id)
    if raw_hash and current_hash and raw_hash == current_hash:
        stats["catalog_rewritten_hash_match"] += 1
        return catalog_id, True
    stats["catalog_mismatch_strict"] += 1
    stats["catalog_mismatch"] += 1
    if allow_mismatch:
        return catalog_id, True
    return None, False


def _ingest_records(
    records: Iterable[Dict[str, Any]],
    source: str,
    catalog_id: str,
    allow_mismatch: bool,
    strict_catalog_id: bool,
    existing_ids: set[str],
    target: Dict[str, Dict[str, Any]],
    stats: Dict[str, int],
) -> None:
    for record in records:
        if record.get("__invalid_json__"):
            stats["invalid_json"] += 1
            continue
        question = record.get("question")
        if not isinstance(question, str) or not question.strip():
            stats["invalid_rows"] += 1
            continue
        raw_catalog = record.get("catalog_id")
        resolved_catalog, rewritten = _apply_catalog_id(
            raw_catalog, catalog_id, allow_mismatch, strict_catalog_id, stats
        )
        if not resolved_catalog:
            continue
        qid = _question_id(question)
        if qid in existing_ids:
            stats["duplicates_dropped"] += 1
            continue
        lang = record.get("lang")
        if not isinstance(lang, str) or not lang.strip():
            lang = "zh"
        out: Dict[str, Any] = {
            "catalog_id": resolved_catalog,
            "question_id": qid,
            "question": question.strip(),
            "lang": lang,
            "source": source,
        }
        if rewritten:
            existing_source_catalog = record.get("source_catalog_id")
            if existing_source_catalog is not None:
                out["source_catalog_id"] = existing_source_catalog
            elif raw_catalog is not None:
                out["source_catalog_id"] = raw_catalog
        if source == "teacher":
            bucket = record.get("bucket")
            if not isinstance(bucket, str) or not bucket.strip():
                bucket = "unknown"
            else:
                bucket = bucket.strip()
            out["bucket"] = bucket
        else:
            out["bucket"] = "unknown"
            meta: Dict[str, Any] = {}
            for key in ("run_id", "ts", "source_file"):
                value = record.get(key)
                if value is not None:
                    meta[key] = value
            out["meta"] = meta
        if not isinstance(out.get("question"), str) or not out["question"].strip():
            raise ValueError("questions_pool contract violation: question is required")
        if not isinstance(out.get("question_id"), str) or not out["question_id"].startswith("sha256:"):
            raise ValueError("questions_pool contract violation: question_id is required")
        if not isinstance(out.get("source"), str) or not out["source"].strip():
            raise ValueError("questions_pool contract violation: source is required")
        if not isinstance(out.get("bucket"), str) or not out["bucket"].strip():
            raise ValueError("questions_pool contract violation: bucket must be non-empty string")
        target[qid] = out
        existing_ids.add(qid)


def _select_records(
    real_records: Dict[str, Dict[str, Any]],
    synth_records: Dict[str, Dict[str, Any]],
    target_total: int,
    max_real: Optional[int],
    max_synth: Optional[int],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    real_sorted = [real_records[k] for k in sorted(real_records)]
    synth_sorted = [synth_records[k] for k in sorted(synth_records)]
    if max_real is not None:
        real_sorted = real_sorted[: max_real]
    if max_synth is not None:
        synth_sorted = synth_sorted[: max_synth]
    if target_total <= 0:
        return [], []
    if len(real_sorted) >= target_total:
        return real_sorted[:target_total], []
    remaining = target_total - len(real_sorted)
    return real_sorted, synth_sorted[:remaining]


def _write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _self_check() -> int:
    catalog_id = "self_check"
    real_records = [
        {
            "question": "测试问题 A",
            "run_id": "r1",
            "ts": "t1",
            "source_file": "f1.jsonl",
        },
        {
            "question": "测试问题 B",
            "run_id": "r2",
            "ts": "t2",
            "source_file": "f2.jsonl",
        },
    ]
    synth_records = [
        {"question": "测试问题 A", "bucket": "b1"},
        {"question": "测试问题 C", "bucket": "b2"},
    ]
    stats = {
        "invalid_json": 0,
        "invalid_rows": 0,
        "catalog_mismatch": 0,
        "catalog_rewritten_hash_match": 0,
        "catalog_mismatch_strict": 0,
        "duplicates_dropped": 0,
    }
    existing: set[str] = set()
    real_out: Dict[str, Dict[str, Any]] = {}
    synth_out: Dict[str, Dict[str, Any]] = {}
    _ingest_records(real_records, "real", catalog_id, False, False, existing, real_out, stats)
    _ingest_records(synth_records, "teacher", catalog_id, False, False, existing, synth_out, stats)
    hash_match_raw = {"catalog_id": "20260106_b434e7a9a883", "question": "哈希重写测试"}
    hash_match_stats = {
        "invalid_json": 0,
        "invalid_rows": 0,
        "catalog_mismatch": 0,
        "catalog_rewritten_hash_match": 0,
        "catalog_mismatch_strict": 0,
        "duplicates_dropped": 0,
    }
    existing2: set[str] = set()
    real_out2: Dict[str, Dict[str, Any]] = {}
    _ingest_records([hash_match_raw], "real", "20260108_b434e7a9a883", False, False, existing2, real_out2, hash_match_stats)
    if hash_match_stats["catalog_rewritten_hash_match"] != 1:
        raise RuntimeError("Self-check failed: hash match rewrite not counted")
    strict_stats = {
        "invalid_json": 0,
        "invalid_rows": 0,
        "catalog_mismatch": 0,
        "catalog_rewritten_hash_match": 0,
        "catalog_mismatch_strict": 0,
        "duplicates_dropped": 0,
    }
    strict_out: Dict[str, Dict[str, Any]] = {}
    _ingest_records([hash_match_raw], "real", "20260108_b434e7a9a883", False, True, set(), strict_out, strict_stats)
    if strict_stats["catalog_mismatch_strict"] != 1:
        raise RuntimeError("Self-check failed: strict mode mismatch not counted")
    allow_stats = {
        "invalid_json": 0,
        "invalid_rows": 0,
        "catalog_mismatch": 0,
        "catalog_rewritten_hash_match": 0,
        "catalog_mismatch_strict": 0,
        "duplicates_dropped": 0,
    }
    allow_out: Dict[str, Dict[str, Any]] = {}
    _ingest_records(
        [{"catalog_id": "20260106_deadbeefcafe", "question": "强制接纳测试"}],
        "real",
        "20260108_b434e7a9a883",
        True,
        False,
        set(),
        allow_out,
        allow_stats,
    )
    if allow_stats["catalog_mismatch_strict"] != 1 or not allow_out:
        raise RuntimeError("Self-check failed: allow mismatch did not accept")
    real_sel, synth_sel = _select_records(real_out, synth_out, 3, None, None)
    final_records = real_sel + synth_sel
    out_path = Path("data/questions") / "questions_pool_self_check.jsonl"
    _write_jsonl(out_path, final_records)
    if len(final_records) != 3:
        raise RuntimeError("Self-check failed: unexpected output size")
    if stats["duplicates_dropped"] != 1:
        raise RuntimeError("Self-check failed: duplicate handling")
    print("self_check: ok")
    print(f"self_check_out: {out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge real and synth questions into pool.")
    parser.add_argument("--real", required=False)
    parser.add_argument("--synth", required=False)
    parser.add_argument("--out", required=False)
    parser.add_argument("--date", default=None, help="YYYYMMDD")
    parser.add_argument("--catalog-id", default=None)
    parser.add_argument("--target-total", type=int, default=750)
    parser.add_argument("--max-real", type=int, default=None)
    parser.add_argument("--max-synth", type=int, default=None)
    parser.add_argument("--allow-catalog-mismatch", action="store_true")
    parser.add_argument("--allow-mismatch", action="store_true")
    parser.add_argument("--strict-catalog-id", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--summary-out", default=None)
    args = parser.parse_args()

    if args.self_check:
        return _self_check()

    if not args.real or not args.synth or not args.out:
        raise ValueError("--real, --synth, and --out are required unless --self-check is used")

    date_str = _validate_date(args.date or datetime.now().strftime("%Y%m%d"))
    catalog_id = _load_catalog_id(args.catalog_id)

    real_path = Path(args.real)
    synth_path = Path(args.synth)
    out_path = Path(args.out)

    allow_mismatch = args.allow_catalog_mismatch or args.allow_mismatch
    stats = {
        "invalid_json": 0,
        "invalid_rows": 0,
        "catalog_mismatch": 0,
        "catalog_rewritten_hash_match": 0,
        "catalog_mismatch_strict": 0,
        "duplicates_dropped": 0,
    }
    existing_ids: set[str] = set()
    real_records: Dict[str, Dict[str, Any]] = {}
    synth_records: Dict[str, Dict[str, Any]] = {}

    _ingest_records(
        _iter_jsonl(real_path),
        "real",
        catalog_id,
        allow_mismatch,
        args.strict_catalog_id,
        existing_ids,
        real_records,
        stats,
    )
    _ingest_records(
        _iter_jsonl(synth_path),
        "teacher",
        catalog_id,
        allow_mismatch,
        args.strict_catalog_id,
        existing_ids,
        synth_records,
        stats,
    )

    real_selected, synth_selected = _select_records(
        real_records,
        synth_records,
        args.target_total,
        args.max_real,
        args.max_synth,
    )
    final_records = real_selected + synth_selected
    _write_jsonl(out_path, final_records)

    counts_by_bucket: Dict[str, int] = {}
    for rec in synth_selected:
        bucket = rec.get("bucket")
        if isinstance(bucket, str):
            counts_by_bucket[bucket] = counts_by_bucket.get(bucket, 0) + 1

    summary = {
        "catalog_id": catalog_id,
        "date": date_str,
        "total_written": len(final_records),
        "real_written": len(real_selected),
        "synth_written": len(synth_selected),
        "duplicates_dropped": stats["duplicates_dropped"],
        "invalid_json": stats["invalid_json"],
        "invalid_rows": stats["invalid_rows"],
        "catalog_mismatch": stats["catalog_mismatch"],
        "catalog_rewritten_hash_match": stats["catalog_rewritten_hash_match"],
        "catalog_mismatch_strict": stats["catalog_mismatch_strict"],
        "counts_by_bucket": counts_by_bucket,
    }

    if args.summary_out:
        summary_path = Path(args.summary_out)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"catalog_id: {catalog_id}")
    print(f"out: {out_path}")
    print(
        "summary: total_written={total} real_written={real} synth_written={synth} "
        "duplicates_dropped={dup} invalid_json={inv} violations={bad} catalog_mismatch={mis} "
        "catalog_rewritten_hash_match={rew} catalog_mismatch_strict={strict}".format(
            total=summary["total_written"],
            real=summary["real_written"],
            synth=summary["synth_written"],
            dup=summary["duplicates_dropped"],
            inv=summary["invalid_json"],
            bad=summary["invalid_rows"],
            mis=summary["catalog_mismatch"],
            rew=summary["catalog_rewritten_hash_match"],
            strict=summary["catalog_mismatch_strict"],
        )
    )
    print("counts_by_bucket:")
    for key in sorted(counts_by_bucket):
        print(f"  - {key}: {counts_by_bucket[key]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
