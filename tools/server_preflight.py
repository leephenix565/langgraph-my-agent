#!/usr/bin/env python
"""Collect server-side evidence for a01 SFT runs (no training logic)."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple


FINAL_FILES = [
    "data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl",
    "data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl",
    "data/a01_sft/final/a01_sft_teacher_stats_FINAL.json",
]


def _run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        return 0, out.strip()
    except Exception as exc:  # pragma: no cover
        return 1, f"ERR: {exc}"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def _torch_info() -> List[str]:
    try:
        import torch  # type: ignore

        lines = [
            f"torch_version: {getattr(torch, '__version__', 'unknown')}",
            f"cuda_available: {torch.cuda.is_available()}",
            f"torch_cuda_version: {getattr(torch.version, 'cuda', None)}",
        ]
        if torch.cuda.is_available():
            try:
                lines.append(f"cuda_device_0: {torch.cuda.get_device_name(0)}")
            except Exception:
                lines.append("cuda_device_0: unknown")
        return lines
    except Exception:
        return ["torch_version: not_installed", "cuda_available: false", "torch_cuda_version: None"]


def _nvidia_smi() -> List[str]:
    if not shutil.which("nvidia-smi"):
        return ["nvidia_smi: not_found"]
    code, out = _run(["nvidia-smi"])
    if code != 0:
        return [f"nvidia_smi: error ({out})"]
    lines = out.splitlines()
    return ["nvidia_smi:"] + lines[:10]


def _df_summary() -> List[str]:
    if not shutil.which("df"):
        return ["df_h: not_found"]
    code, out = _run(["df", "-h"])
    if code != 0:
        return [f"df_h: error ({out})"]
    lines = out.splitlines()
    return ["df_h:"] + lines[:10]


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect server preflight evidence.")
    ap.add_argument("--out-dir", default="", help="Output dir for preflight.txt")
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else Path("runs/a01_sft") / f"{ts}_preflight"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "preflight.txt"

    lines: List[str] = []
    lines.append(f"timestamp_utc: {datetime.now(timezone.utc).isoformat()}")

    code, commit = _run(["git", "rev-parse", "HEAD"])
    lines.append(f"git_commit: {commit if code == 0 else 'unknown'}")
    _, status = _run(["git", "status", "--porcelain"])
    lines.append("git_status_dirty: yes" if status else "git_status_dirty: no")
    if status:
        lines.append("git_status_porcelain:")
        lines.extend(status.splitlines())

    lines.append("")
    lines.append("final_artifacts:")
    for rel in FINAL_FILES:
        path = Path(rel)
        if not path.exists():
            lines.append(f"- {rel}: missing")
            continue
        lines.append(f"- {rel}")
        lines.append(f"  sha256: {_sha256(path)}")
        lines.append(f"  lines: {_line_count(path)}")

    lines.append("")
    lines.append(f"python_version: {sys.version.replace(chr(10), ' ')}")
    _, pip_ver = _run([sys.executable, "-m", "pip", "--version"])
    lines.append(f"pip_version: {pip_ver}")
    lines.extend(_torch_info())
    lines.extend(_df_summary())
    lines.extend(_nvidia_smi())

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"preflight_written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
