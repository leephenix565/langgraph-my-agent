#!/usr/bin/env python
"""Generate router raw outputs (preds.jsonl) using a local HF model."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _require_hf():
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed as hf_set_seed
    except Exception as exc:
        raise RuntimeError(
            "Missing dependencies: install torch and transformers to run this script."
        ) from exc
    return torch, AutoModelForCausalLM, AutoTokenizer, hf_set_seed


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


def _seed_everything(seed: int, torch, hf_set_seed) -> None:
    random.seed(seed)
    try:
        import numpy as np
    except Exception:
        np = None
    if np is not None:
        np.random.seed(seed)
    if hasattr(torch, "manual_seed"):
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    if hf_set_seed is not None:
        hf_set_seed(seed)


def _messages_to_prompt(messages: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    if not parts:
        raise ValueError("Record messages empty after normalization")
    return "\n\n".join(parts)


def _decode_new_text(tokenizer, output_ids, prompt_len: int) -> str:
    new_ids = output_ids[prompt_len:]
    text = tokenizer.decode(new_ids, skip_special_tokens=True)
    if text and text.strip():
        return text.strip()
    # Fallback: decode full output if new text is empty.
    full = tokenizer.decode(output_ids, skip_special_tokens=True).strip()
    if full:
        return full
    return "<empty>"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate router raw outputs with local HF model.")
    ap.add_argument("--in", dest="in_path", required=True, help="Input val messages JSONL")
    ap.add_argument("--out", required=True, help="Output preds.jsonl")
    ap.add_argument("--model-path", required=True, help="Local HF model path or name")
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--max-new-tokens", type=int, default=512)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch, AutoModelForCausalLM, AutoTokenizer, hf_set_seed = _require_hf()

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available.")

    tokenizer = AutoTokenizer.from_pretrained(args.model_path, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(args.model_path)
    model.to(args.device)
    model.eval()

    in_path = Path(args.in_path)
    out_path = Path(args.out)

    records_out: List[Dict[str, Any]] = []
    processed = 0
    do_sample = args.temperature > 0.0
    run_ts = dt.datetime.utcnow().isoformat()
    source_val_path = str(in_path)
    source_val_sha256 = _sha256_file(in_path)
    _seed_everything(args.seed, torch, hf_set_seed)

    for record in _read_jsonl(in_path):
        if args.max_items is not None and processed >= args.max_items:
            break
        rec_id = record.get("id") or record.get("question_id")
        if not isinstance(rec_id, str) or not rec_id.strip():
            raise ValueError("Record missing id/question_id")
        messages = record.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("Record missing messages list")
        prompt = _messages_to_prompt(messages)
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(args.device)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(args.device)

        with torch.no_grad():
            output_ids = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=args.max_new_tokens,
                do_sample=do_sample,
                temperature=args.temperature if do_sample else None,
            )[0]

        raw_text = _decode_new_text(tokenizer, output_ids, input_ids.shape[-1])
        records_out.append(
            {
                "id": rec_id,
                "raw_text": raw_text,
                "meta": {
                    "hf_model_id": args.model_path,
                    "prompt_format": "flattened_text",
                    "source_val_path": source_val_path,
                    "source_val_sha256": source_val_sha256,
                    "run_ts": run_ts,
                    "seed": args.seed,
                    "do_sample": do_sample,
                    "temperature": args.temperature,
                    "max_new_tokens": args.max_new_tokens,
                    "device": args.device,
                },
            }
        )
        processed += 1
        if processed % 50 == 0:
            print(f"progress: {processed}")

    written = _write_jsonl(out_path, records_out)
    print(f"model_path: {args.model_path}")
    print(f"device: {args.device}")
    print(f"in: {in_path}")
    print(f"out: {out_path}")
    print(f"written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
