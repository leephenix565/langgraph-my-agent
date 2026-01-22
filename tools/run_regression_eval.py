#!/usr/bin/env python
"""Run a two-pass preds->eval regression check and compare metrics meta."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def _run(cmd: List[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _load_meta(path: Path) -> Dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in meta.items():
        if isinstance(v, str):
            out[k] = v
    return out


def _compare_meta(meta1: Dict[str, str], meta2: Dict[str, str], gate_mode: str) -> Dict[str, object]:
    keys = ["git_commit", "preds_content_sha256", "val_messages_sha256", "catalog_sha256"]
    if gate_mode == "condition":
        hard_keys = ["git_commit", "val_messages_sha256", "catalog_sha256"]
    else:
        hard_keys = list(keys)
    soft_keys = [k for k in keys if k not in hard_keys]
    field_matches: Dict[str, bool] = {}
    diff_keys: List[str] = []
    for key in keys:
        v1 = meta1.get(key, "unknown")
        v2 = meta2.get(key, "unknown")
        ok = v1 == v2
        field_matches[key] = ok
        if not ok:
            diff_keys.append(key)
    hard_match = all(field_matches.get(k, False) for k in hard_keys)
    soft_mismatch_keys = [k for k in soft_keys if not field_matches.get(k, False)]
    return {
        "gate_mode": gate_mode,
        "hard_keys": hard_keys,
        "soft_keys": soft_keys,
        "hard_match": hard_match,
        "soft_mismatch_keys": soft_mismatch_keys,
        "meta_match": len(diff_keys) == 0,
        "diff_keys": diff_keys,
        "field_matches": field_matches,
        "run1_meta": {k: meta1.get(k, "unknown") for k in keys},
        "run2_meta": {k: meta2.get(k, "unknown") for k in keys},
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run two preds->eval passes and compare metrics meta for regression gating."
    )
    ap.add_argument("--val-messages", required=True, help="Val messages JSONL path")
    ap.add_argument("--out-dir", default="tmp/regression_eval", help="Output directory")
    ap.add_argument("--mode", choices=["provider", "hf"], default="provider")
    ap.add_argument("--model", default=None, help="Provider model name")
    ap.add_argument("--hf-model-path", default=None, help="HF model path or name")
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--max-new-tokens", type=int, default=512)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--catalog-id", default=None)
    ap.add_argument("--catalog-prompt", default=None)
    ap.add_argument("--gate-mode", choices=["repro", "condition"], default="repro")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    preds1 = out_dir / "preds_run1.jsonl"
    preds2 = out_dir / "preds_run2.jsonl"
    metrics1 = out_dir / "metrics_run1.json"
    metrics2 = out_dir / "metrics_run2.json"
    compare_path = out_dir / "compare.json"

    if args.mode == "provider":
        script = Path("tools/generate_router_preds.py")
        def _preds_cmd(out_path: Path) -> List[str]:
            cmd = [sys.executable, str(script), "--in", args.val_messages, "--out", str(out_path)]
            if args.model:
                cmd += ["--model", args.model]
            if args.max_items is not None:
                cmd += ["--max-items", str(args.max_items)]
            return cmd
    else:
        if not args.hf_model_path:
            raise ValueError("--hf-model-path is required when --mode hf")
        script = Path("tools/generate_router_preds_hf.py")
        def _preds_cmd(out_path: Path) -> List[str]:
            cmd = [
                sys.executable,
                str(script),
                "--in",
                args.val_messages,
                "--out",
                str(out_path),
                "--model-path",
                args.hf_model_path,
                "--device",
                args.device,
                "--max-new-tokens",
                str(args.max_new_tokens),
                "--temperature",
                str(args.temperature),
                "--seed",
                str(args.seed),
            ]
            if args.max_items is not None:
                cmd += ["--max-items", str(args.max_items)]
            return cmd

    def _eval_cmd(preds_path: Path, out_path: Path) -> List[str]:
        cmd = [
            sys.executable,
            "tools/eval_router_outputs.py",
            "--in",
            str(preds_path),
            "--out",
            str(out_path),
            "--val-messages",
            args.val_messages,
        ]
        if args.catalog_id:
            cmd += ["--catalog-id", args.catalog_id]
        if args.catalog_prompt:
            cmd += ["--catalog-prompt", args.catalog_prompt]
        return cmd

    _run(_preds_cmd(preds1))
    _run(_eval_cmd(preds1, metrics1))
    _run(_preds_cmd(preds2))
    _run(_eval_cmd(preds2, metrics2))

    meta1 = _load_meta(metrics1)
    meta2 = _load_meta(metrics2)
    compare = _compare_meta(meta1, meta2, args.gate_mode)
    compare.update(
        {
            "metrics_run1": str(metrics1),
            "metrics_run2": str(metrics2),
        }
    )
    compare_path.write_text(json.dumps(compare, ensure_ascii=False, indent=2), encoding="utf-8")

    print("gate_mode:", compare["gate_mode"])
    print("hard_match:", compare["hard_match"])
    print("meta_match:", compare["meta_match"], "(strict all keys)")
    print("diff_keys:", compare["diff_keys"])
    print("compare:", compare_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
