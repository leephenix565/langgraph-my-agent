#!/usr/bin/env python
"""Generate router raw outputs (preds.jsonl) from val messages JSONL."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from react_agent.context import Context  # noqa: E402
from react_agent.utils import get_message_text, load_chat_model  # noqa: E402


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(obj, dict):
                raise RuntimeError(f"Invalid JSONL object at {path}:{line_no}")
            yield obj


def _write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _messages_from_record(record: Dict[str, Any]) -> List[Dict[str, str]]:
    messages = record.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("Record missing messages list")
    out: List[Dict[str, str]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            continue
        out.append({"role": role, "content": content})
    if not out:
        raise ValueError("Record messages empty after normalization")
    return out


def _call_model(model: Any, messages: List[Dict[str, str]]) -> str:
    if hasattr(model, "invoke"):
        resp = model.invoke(messages)
        return get_message_text(resp)
    if hasattr(model, "ainvoke"):
        resp = asyncio.run(model.ainvoke(messages))
        return get_message_text(resp)
    raise ValueError("Model does not support invoke/ainvoke")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate router raw outputs from val messages JSONL.")
    ap.add_argument("--in", dest="in_path", required=True, help="Input val messages JSONL")
    ap.add_argument("--out", required=True, help="Output preds.jsonl")
    ap.add_argument("--model", default=None, help="Override Context.model (provider/model)")
    ap.add_argument("--max-items", type=int, default=None, help="Optional cap on processed items")
    args = ap.parse_args()

    model_name = args.model or Context().model
    model = load_chat_model(model_name)

    in_path = Path(args.in_path)
    out_path = Path(args.out)

    records_out: List[Dict[str, Any]] = []
    processed = 0
    run_ts = dt.datetime.utcnow().isoformat()
    source_val_path = str(in_path)
    source_val_sha256 = _sha256_file(in_path)
    provider = model_name.split("/", 1)[0] if "/" in model_name else "unknown"
    for record in _read_jsonl(in_path):
        if args.max_items is not None and processed >= args.max_items:
            break
        rec_id = record.get("id") or record.get("question_id")
        if not isinstance(rec_id, str) or not rec_id.strip():
            raise ValueError("Record missing id/question_id")
        messages = _messages_from_record(record)
        raw_text = _call_model(model, messages)
        records_out.append(
            {
                "id": rec_id,
                "raw_text": raw_text,
                "meta": {
                    "provider": provider,
                    "model": model_name,
                    "prompt_format": "chat_messages",
                    "source_val_path": source_val_path,
                    "source_val_sha256": source_val_sha256,
                    "run_ts": run_ts,
                },
            }
        )
        processed += 1
        if processed % 50 == 0:
            print(f"progress: {processed}")

    written = _write_jsonl(out_path, records_out)
    print(f"model: {model_name}")
    print(f"in: {in_path}")
    print(f"out: {out_path}")
    print(f"written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
