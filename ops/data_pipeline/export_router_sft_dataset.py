#!/usr/bin/env python
"""Convert router_sft OK jsonl -> SFT dataset jsonl."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


_DEFAULT_SYSTEM_TEMPLATE_FROM = str(Path(__file__).with_name("generate_router_plans.py"))


def _read_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Invalid JSONL at {path}:{line_no}: {e}") from e


def _write_jsonl(path: str, records: Iterable[Dict[str, Any]]) -> int:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def _compact_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _sha256_file(path: str | os.PathLike[str]) -> str:
    p = os.fspath(path)
    if not os.path.exists(p):
        return "unknown"
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_catalog_version(name: str) -> Tuple[Optional[str], Optional[str]]:
    m = re.search(r"router_sft_messages_(\\d{8}_[0-9a-f]{12})_(v\\d+)", name)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"router_sft_\\d{8}_(\\d{8}_[0-9a-f]{12})(?:_(v\\d+))?", name)
    if m:
        return m.group(1), m.group(2)
    return None, None


def _load_catalog_prompt(path: str) -> str:
    """
    Your catalog_*_prompt.json may either:
    - contain a string field like {"prompt": "..."}; OR
    - be a structured JSON describing agents/layers
    We turn it into a prompt string deterministically.
    """
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict) and isinstance(obj.get("prompt"), str) and obj["prompt"].strip():
        return obj["prompt"].strip()
    # fallback: pretty JSON
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _extract_triple_quoted_string(py_text: str, var_name: str) -> Optional[str]:
    """
    Extract: VAR_NAME = '''...''' or VAR_NAME = \"\"\"...\"\"\"
    Non-greedy across lines.
    """
    # Match VAR = """ ... """ or VAR = ''' ... '''
    pat = re.compile(
        rf"{re.escape(var_name)}\s*=\s*(?P<q>'''|\"\"\")(?P<body>.*?)(?P=q)",
        re.DOTALL,
    )
    m = pat.search(py_text)
    if not m:
        return None
    return m.group("body")


def _render_router_system_prompt(template: str, agent_catalog: str, system_time: str) -> str:
    s = template.replace("{agent_catalog}", agent_catalog).replace("{system_time}", system_time)
    # Guard: placeholders must be rendered
    if "{agent_catalog}" in s or "{system_time}" in s:
        raise ValueError("System prompt not rendered: placeholders still present")
    return s


def _default_router_system_prompt(agent_catalog: str, system_time: str) -> str:
    """
    Fallback minimal system prompt if you don't want to extract from the router plan generator script.
    (Recommended: use --system-template-from, default points to sibling generate_router_plans.py)
    """
    return (
        "You are the Router Agent.\n"
        "Output MUST be pure JSON.\n"
        "Allowed layers only: L1,L2,L3,L4 in this fixed order.\n"
        "Modes allowed: Star/Chain/Debate/Tree.\n"
        "L2 selected count: default 4, allowed 3-5.\n"
        "L3 selected count: default 3, allowed 2-5.\n"
        "Do NOT include tools or external roles; only use listed agent ids.\n"
        "Output JSON only, no markdown or extra text.\n"
        f"Current time: {system_time}\n\n"
        "Agent catalog:\n"
        f"{agent_catalog}\n"
    )


@dataclass
class Split:
    train: List[Dict[str, Any]]
    val: List[Dict[str, Any]]


def _split_records(records: List[Dict[str, Any]], val_ratio: float, seed: int) -> Split:
    if val_ratio <= 0:
        return Split(train=records, val=[])
    rnd = random.Random(seed)
    idx = list(range(len(records)))
    rnd.shuffle(idx)
    val_n = int(round(len(records) * val_ratio))
    val_set = set(idx[:val_n])
    train, val = [], []
    for i, r in enumerate(records):
        (val if i in val_set else train).append(r)
    return Split(train=train, val=val)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-ok", required=True, help="router_sft_*.jsonl OK file")
    ap.add_argument("--catalog-prompt", required=True, help="catalog_*_prompt.json (v1 recommended)")
    ap.add_argument("--out-messages", required=True, help="output jsonl in messages+response format")
    ap.add_argument("--out-prompt", default="", help="optional output jsonl in prompt/completion format")
    ap.add_argument(
        "--system-template-from",
        default=_DEFAULT_SYSTEM_TEMPLATE_FROM,
        help="extract ROUTER_SYSTEM_PROMPT from this .py; empty disables extraction",
    )
    ap.add_argument("--system-var", default="ROUTER_SYSTEM_PROMPT", help="variable name to extract from system-template-from")
    ap.add_argument("--system-time", default="2026-01-08", help="rendered system_time string")
    ap.add_argument("--user-prefix", default="Question: ", help="prefix before question in user content")
    ap.add_argument("--include-mode-hint", action="store_true",
                    help="NOT recommended unless runtime router also sees mode_hint (leakage risk)")
    ap.add_argument("--val-ratio", type=float, default=0.02, help="validation split ratio (0 disables)")
    ap.add_argument("--seed", type=int, default=42, help="seed for split shuffle")
    args = ap.parse_args()

    agent_catalog = _load_catalog_prompt(args.catalog_prompt)

    system_prompt: str
    if args.system_template_from:
        with open(args.system_template_from, "r", encoding="utf-8") as f:
            py_text = f.read()
        template = _extract_triple_quoted_string(py_text, args.system_var)
        if template is None:
            # fallback minimal
            system_prompt = _default_router_system_prompt(agent_catalog, args.system_time)
        else:
            system_prompt = _render_router_system_prompt(template, agent_catalog, args.system_time)
    else:
        system_prompt = _default_router_system_prompt(agent_catalog, args.system_time)

    records_out_messages: List[Dict[str, Any]] = []
    records_out_prompt: List[Dict[str, Any]] = []

    for r in _read_jsonl(args.in_ok):
        qid = r.get("question_id") or r.get("id")
        question = r.get("question")
        plan = (r.get("router_plan_parsed") or r.get("router_plan_raw") or {})
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Bad record: missing question (question_id={qid})")
        if not isinstance(plan, dict) or "layers" not in plan:
            raise ValueError(f"Bad record: missing router_plan_parsed.layers (question_id={qid})")

        # assistant JSON (compact)
        assistant_json = _compact_json(plan)

        # user content
        user_content = f"{args.user_prefix}{question.strip()}"
        if args.include_mode_hint and isinstance(r.get("mode_hint"), dict):
            user_content += "\nMode hint: " + json.dumps(r["mode_hint"], ensure_ascii=False)

        meta = {
            "question_id": qid,
            "bucket": r.get("bucket", "unknown"),
            "source": r.get("source", "unknown"),
            "catalog_id": r.get("catalog_id"),
            "source_catalog_id": r.get("source_catalog_id"),
            "auto_fix": bool(r.get("auto_fix", False)),
            "fix_notes": r.get("fix_notes") or [],
        }

        # messages format
        rec_msg = {
            "id": qid,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response": assistant_json,
            "meta": meta,
        }
        records_out_messages.append(rec_msg)

        # prompt/completion format (optional)
        if args.out_prompt:
            # simple concatenation; many trainers accept this
            prompt = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_content}\n\n[ASSISTANT]\n"
            rec_pc = {"id": qid, "prompt": prompt, "completion": assistant_json, "meta": meta}
            records_out_prompt.append(rec_pc)

    # deterministic order: sort by question_id (then split)
    records_out_messages.sort(key=lambda x: str(x.get("id", "")))
    records_out_prompt.sort(key=lambda x: str(x.get("id", "")))

    split_msg = _split_records(records_out_messages, args.val_ratio, args.seed)
    out_train = args.out_messages
    out_val = ""
    if args.val_ratio > 0:
        base, ext = os.path.splitext(args.out_messages)
        out_train = f"{base}.train{ext or '.jsonl'}"
        out_val = f"{base}.val{ext or '.jsonl'}"

    n_train = _write_jsonl(out_train, split_msg.train)
    n_val = _write_jsonl(out_val, split_msg.val) if out_val else 0

    if args.out_prompt:
        split_pc = _split_records(records_out_prompt, args.val_ratio, args.seed)
        base, ext = os.path.splitext(args.out_prompt)
        out_pc_train = args.out_prompt
        out_pc_val = ""
        if args.val_ratio > 0:
            out_pc_train = f"{base}.train{ext or '.jsonl'}"
            out_pc_val = f"{base}.val{ext or '.jsonl'}"
        _write_jsonl(out_pc_train, split_pc.train)
        if out_pc_val:
            _write_jsonl(out_pc_val, split_pc.val)

    catalog_id, version = _parse_catalog_version(os.path.basename(args.out_messages))
    if catalog_id is None:
        catalog_id, version = _parse_catalog_version(os.path.basename(args.in_ok))
    version = version or "v1"
    manifest_dir = os.path.dirname(args.in_ok) or "data/router_sft"
    manifest_path = os.path.join(manifest_dir, f"MANIFEST_{catalog_id or 'unknown'}_{version}.json")
    manifest: Dict[str, Any] = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as fh:
            try:
                manifest = json.load(fh)
            except json.JSONDecodeError:
                manifest = {}
    if not manifest:
        manifest = {
            "created_at": dt.datetime.utcnow().isoformat(),
            "catalog_id": catalog_id or "unknown",
            "files": [],
        }
    manifest["seed"] = args.seed
    manifest["val_ratio"] = args.val_ratio
    manifest["in_ok_sha256"] = _sha256_file(args.in_ok)
    manifest["out_train_sha256"] = _sha256_file(out_train)
    manifest["out_val_sha256"] = _sha256_file(out_val) if out_val else "unknown"
    manifest["updated_at"] = dt.datetime.utcnow().isoformat()
    with open(manifest_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=2))

    print("export_ok:")
    print("  in_ok:", args.in_ok)
    print("  catalog_prompt:", args.catalog_prompt)
    print("  system_template_from:", args.system_template_from or "(fallback minimal)")
    print("  out_messages_train:", out_train, "n=", n_train)
    if out_val:
        print("  out_messages_val:", out_val, "n=", n_val)
    if args.out_prompt:
        print("  out_prompt:* train/val written too")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
