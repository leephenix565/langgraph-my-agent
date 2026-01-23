#!/usr/bin/env python
"""Prepare Router-SFT data with parse-based labeling and optional filtering."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from react_agent import router_parse


def _extract_first_json(text: str) -> str | None:
    start = None
    depth = 0
    in_str = False
    escape = False
    for i, ch in enumerate(text):
        if start is None:
            if ch == "{":
                start = i
                depth = 1
            continue
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "\"":
                in_str = False
            continue
        if ch == "\"":
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except Exception:
                    return None
    return None


def _canonicalize_response(text: str) -> tuple[str, bool]:
    candidate = _extract_first_json(text)
    if not candidate:
        return text, False
    try:
        obj = json.loads(candidate)
    except Exception:
        return text, False
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")), True


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


def _append_assistant(messages: List[Dict[str, Any]], response: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, dict):
            out.append({"role": msg.get("role"), "content": msg.get("content")})
    out.append({"role": "assistant", "content": response})
    return out


def _strip_assistant(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role == "assistant":
            continue
        out.append({"role": role, "content": content})
    return out


def _label_record(
    record: Dict[str, Any],
    agent_catalog: Dict[str, List[str]],
) -> Tuple[Dict[str, Any], bool]:
    messages = record.get("messages")
    response = record.get("response")
    if not isinstance(messages, list) or not messages:
        raise ValueError("Record missing messages list")
    response_text = response if isinstance(response, str) else ""
    canonical_text, canon_ok = _canonicalize_response(response_text)
    plan, modes, stats = router_parse.parse_router_layers_with_stats(response_text, agent_catalog)
    parse_ok = bool(stats.get("parse_ok"))
    used_default = bool(stats.get("used_default_plan"))
    parse_error = None if parse_ok else ("used_default_plan" if used_default else "parse_failed")

    meta = dict(record.get("meta") or {})
    meta.update(
        {
            "parse_ok": parse_ok,
            "parse_error": parse_error,
            "used_default_plan": used_default,
            "l2_truncated": int(stats.get("l2_truncated", 0)),
            "filtered_agents": int(stats.get("filtered_agents", 0)),
            "canon_success": canon_ok,
        }
    )

    out = dict(record)
    out["messages"] = _append_assistant(messages, canonical_text)
    out["response"] = canonical_text
    out["meta"] = meta
    return out, (parse_ok and not used_default)


def _process_file(
    in_path: Path,
    out_path: Path,
    agent_catalog: Dict[str, List[str]],
    filter_mode: str,
    max_items: int | None,
    val_messages_out: Path | None,
) -> Tuple[int, int, int]:
    total = 0
    parse_ok = 0
    used_default = 0
    kept = 0
    canon_ok = 0
    records_out: List[Dict[str, Any]] = []
    val_msgs_out: List[Dict[str, Any]] = []
    for record in _read_jsonl(in_path):
        if max_items is not None and total >= max_items:
            break
        total += 1
        labeled, strict_ok = _label_record(record, agent_catalog)
        meta = labeled.get("meta") or {}
        if meta.get("parse_ok"):
            parse_ok += 1
        if meta.get("used_default_plan"):
            used_default += 1
        if meta.get("canon_success"):
            canon_ok += 1
        if filter_mode == "strict" and not strict_ok:
            continue
        records_out.append(labeled)
        if val_messages_out is not None and strict_ok:
            base_msgs = record.get("messages") or []
            val_msgs_out.append({"id": record.get("id"), "messages": _strip_assistant(base_msgs)})
        kept += 1
    _write_jsonl(out_path, records_out)
    if val_messages_out is not None:
        _write_jsonl(val_messages_out, val_msgs_out)
    print(
        f"  {in_path.name}: total={total} parse_ok={parse_ok} "
        f"used_default_plan={used_default} strict_kept={kept} canon_success={canon_ok}"
    )
    return total, parse_ok, kept


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare Router-SFT data with parse labeling.")
    ap.add_argument("--in-train", required=True, help="Input train JSONL")
    ap.add_argument("--in-val", required=True, help="Input val JSONL")
    ap.add_argument("--out-dir", required=True, help="Output directory")
    ap.add_argument("--filter-mode", choices=["strict", "all"], default="strict")
    ap.add_argument("--catalog-id", default=None)
    ap.add_argument("--catalog-prompt", default=None)
    ap.add_argument("--max-items", type=int, default=None, help="Optional cap for smoke tests")
    ap.add_argument("--emit-val-messages-strict", action="store_true")
    args = ap.parse_args()

    catalog_id = _load_catalog_id(args.catalog_id)
    catalog_prompt = (
        Path(args.catalog_prompt)
        if args.catalog_prompt
        else Path("data/catalogs") / f"catalog_{catalog_id}_prompt.json"
    )
    agent_catalog = _load_catalog_prompt(catalog_prompt)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_train = out_dir / "prepared_train.jsonl"
    out_val = out_dir / "prepared_val.jsonl"
    val_msgs_strict = out_dir / "val_messages_strict.jsonl" if args.emit_val_messages_strict else None

    t_total, t_ok, t_kept = _process_file(
        Path(args.in_train),
        out_train,
        agent_catalog,
        args.filter_mode,
        args.max_items,
        None,
    )
    v_total, v_ok, v_kept = _process_file(
        Path(args.in_val),
        out_val,
        agent_catalog,
        args.filter_mode,
        args.max_items,
        val_msgs_strict,
    )

    print("prepare_summary:")
    print(f"  filter_mode: {args.filter_mode}")
    print(f"  train_total: {t_total} parse_ok: {t_ok} kept: {t_kept} -> {out_train}")
    print(f"  val_total: {v_total} parse_ok: {v_ok} kept: {v_kept} -> {out_val}")
    if val_msgs_strict is not None:
        print(f"  val_messages_strict: {val_msgs_strict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
