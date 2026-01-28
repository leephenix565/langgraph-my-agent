#!/usr/bin/env python
"""Evaluate a01 SFT model outputs on FINAL val set."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"Missing eval deps. Install requirements-hf.txt. ({exc})")

from react_agent import contract_utils
from react_agent.json_utils import extract_first_json


WEIGHT_CANDIDATES = [
    "model.safetensors",
    "model.safetensors.index.json",
    "pytorch_model.bin",
    "pytorch_model.bin.index.json",
    "adapter_model.safetensors",
    "adapter_model.bin",
]


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def _format_messages(tokenizer, messages: List[Dict[str, Any]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    parts: List[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _dir_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def _format_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.2f}{unit}"
        size /= 1024.0
    return f"{size:.2f}TB"


def _collect_model_hashes(model_path: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    if model_path.is_file():
        hashes[model_path.name] = _sha256(model_path)
        return hashes
    for name in WEIGHT_CANDIDATES:
        candidate = model_path / name
        if candidate.exists():
            hashes[name] = _sha256(candidate)
    return hashes

def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate a01 SFT outputs on val jsonl.")
    ap.add_argument("--model-path", required=True, help="HF model path (adapter or merged)")
    ap.add_argument("--val-jsonl", required=True, help="FINAL val jsonl")
    ap.add_argument("--out-dir", required=True, help="output directory for eval_report.json")
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--max-new-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model_path, use_fast=True, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model_path, trust_remote_code=True)
    model.to(args.device)
    model.eval()

    total = 0
    valid_json = 0
    contract_ok = 0
    schema_keys_match = 0
    required_keys = contract_utils.CONTRACT_REQUIRED_KEYS

    for rec in _read_jsonl(Path(args.val_jsonl)):
        if args.max_items is not None and total >= args.max_items:
            break
        total += 1
        messages = rec.get("messages") or []
        prompt = _format_messages(tokenizer, messages)
        inputs = tokenizer(prompt, return_tensors="pt").to(args.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=args.temperature > 0,
                temperature=max(args.temperature, 0.0),
            )
        generated = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )
        candidate = extract_first_json(generated)
        if not candidate:
            continue
        try:
            obj = json.loads(candidate)
        except Exception:
            continue
        valid_json += 1
        contract = obj.get("contract") if isinstance(obj, dict) else None
        if isinstance(contract, dict):
            if set(contract.keys()) == set(required_keys):
                schema_keys_match += 1
            selected = (rec.get("meta") or {}).get("selected_agents") or []
            if isinstance(selected, list):
                ok, _reason, _tasks = contract_utils.validate_contract(contract, selected)
                if ok:
                    contract_ok += 1

    metrics = {
        "valid_json_rate": (valid_json / total) if total else 0.0,
        "contract_ok_rate": (contract_ok / total) if total else 0.0,
        "schema_keys_match_rate": (schema_keys_match / total) if total else 0.0,
    }
    model_dir_bytes = _dir_size(Path(args.model_path))
    report = {
        "meta": {
            "git_commit": _git_commit(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_path": args.model_path,
            "model_sha256": _collect_model_hashes(Path(args.model_path)),
            "model_dir_bytes": model_dir_bytes,
            "model_dir_human": _format_size(model_dir_bytes),
            "val_jsonl": args.val_jsonl,
            "val_sha256": _sha256(Path(args.val_jsonl)),
            "device": args.device,
            "max_new_tokens": args.max_new_tokens,
            "temperature": args.temperature,
        },
        "counts": {
            "total": total,
            "valid_json": valid_json,
            "contract_ok": contract_ok,
            "schema_keys_match": schema_keys_match,
        },
        "metrics": metrics,
    }
    out_path = out_dir / "eval_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("eval_done:")
    print("  out:", out_path)
    print("  metrics:", metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
