#!/usr/bin/env python
"""Generate Router SFT data from questions and catalog prompts."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import random
import re
import socket
import ssl
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

DEEPSEEK_API_KEY = "sk-35355823d3d544e58e7ebb29c6170094"  # Optional: fill in your key here if env vars are not set.

LAYER_ORDER = ["L1", "L2", "L3", "L4"]
ALLOWED_MODES = {"Star", "Chain", "Debate", "Tree"}
DEFAULT_MODES = {"L1": "Chain", "L2": "Star", "L3": "Star", "L4": "Chain"}

MODE_DISTRIBUTION = [
    ("Star", 0.80),
    ("Chain", 0.90),
    ("Debate", 0.95),
    ("Tree", 1.00),
]

ROUTER_SYSTEM_PROMPT = """You are the Router Agent. Output MUST be pure JSON for 4 layers (L1,L2,L3,L4). Each mode MUST be a single value, exactly one of: "Star", "Chain", "Debate", "Tree". Do NOT output lists of modes, explanations, or markdown.
Schema:
{
  "layers": [
    {"layer": "L1", "mode": "Chain", "selected": ["..."]},
    {"layer": "L2", "mode": "Star", "selected": ["..."]},
    {"layer": "L3", "mode": "Star", "selected": ["..."]},
    {"layer": "L4", "mode": "Chain", "selected": ["..."]}
  ],
  "reason": "why you chose the subset per layer and mode"
}
Available agents by layer (id/name/desc_1l):
{agent_catalog}
Rules:
- Allowed layers only: L1,L2,L3,L4; order fixed as above; each layer may be empty but keep the order.
- Modes allowed: Star/Chain/Debate/Tree.
- L2 selected count: default 4, allowed 3-5. Order by importance (most relevant first).
- L3 selected count: default 3, allowed 2-5. Order by importance (most relevant first).
- If you have more than 5 candidates, remove extras before output.
- Do NOT include tools or external roles; only use the listed agent ids.
- Output JSON only, no markdown or extra text.
Current time: {system_time}
"""

USER_PROMPT_TEMPLATE = """Question:
{question}

Mode hint (must follow exactly):
L1={mode_L1}
L2={mode_L2}
L3={mode_L3}
L4={mode_L4}

{retry_notice}
Constraints reminder:
- L2 must select 3-5 agents (default 4); L3 must select 2-5 agents (default 3).
- selected must be ordered by importance; trim extras to <=5 before output.
Output a single JSON object only. Do not include markdown, code fences, or any extra text.
"""


def _render_router_system_prompt(template: str, system_time: str, agent_catalog: str) -> str:
    rendered = template.replace("{system_time}", system_time).replace("{agent_catalog}", agent_catalog)
    if "{agent_catalog}" in rendered or "{system_time}" in rendered:
        raise ValueError("Router system prompt rendering failed; unresolved placeholders remain.")
    return rendered


def _extract_assistant_content(chat_completion_raw: str) -> str:
    if not isinstance(chat_completion_raw, str) or not chat_completion_raw.strip():
        return ""
    try:
        payload = json.loads(chat_completion_raw)
    except Exception:
        return chat_completion_raw
    if not isinstance(payload, dict):
        return chat_completion_raw
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return chat_completion_raw
    first = choices[0]
    if not isinstance(first, dict):
        return chat_completion_raw
    message = first.get("message")
    if not isinstance(message, dict):
        return chat_completion_raw
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    return chat_completion_raw


def _excerpt(text: str, limit: int = 800) -> str:
    if not isinstance(text, str) or not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 8] + "...[trunc]"


class RetryableError(Exception):
    def __init__(self, message: str, *, is_timeout: bool = False) -> None:
        super().__init__(message)
        self.is_timeout = is_timeout


class FatalAPIError(Exception):
    pass


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


def _normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _question_id(text: str) -> str:
    norm = _normalize_question(text)
    return f"sha256:{hashlib.sha256(norm.encode('utf-8')).hexdigest()}"


def _resolve_questions_path(explicit: Optional[str]) -> Path:
    if explicit:
        if any(ch in explicit for ch in ["*", "?", "["]):
            matches = sorted(Path().glob(explicit))
            if not matches:
                raise ValueError(f"No questions files matched pattern: {explicit}")
            return matches[-1]
        return Path(explicit)
    candidates = sorted(Path("data/questions").glob("questions_pool_*.jsonl"))
    if not candidates:
        raise ValueError("No data/questions/questions_pool_*.jsonl found; pass --questions explicitly")
    return candidates[-1]


def _load_catalog_prompt(
    path: Path,
) -> Tuple[
    str,
    Dict[str, List[Dict[str, str]]],
    Dict[str, set[str]],
    Dict[str, List[str]],
    Dict[str, str],
]:
    if not path.exists():
        raise ValueError(f"Catalog prompt not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    catalog_id = payload.get("catalog_id", "")
    layers = payload.get("layers")
    if not isinstance(layers, dict):
        raise ValueError("Catalog prompt missing layers")
    layer_ids: Dict[str, set[str]] = {}
    layer_ordered_ids: Dict[str, List[str]] = {}
    id_to_layer: Dict[str, str] = {}
    for layer in LAYER_ORDER:
        entries = layers.get(layer)
        if not isinstance(entries, list):
            raise ValueError(f"Catalog prompt missing layer: {layer}")
        ids: set[str] = set()
        ordered: List[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"Catalog entry not an object in {layer}")
            aid = entry.get("id")
            if not isinstance(aid, str) or not aid:
                raise ValueError(f"Catalog entry missing id in {layer}")
            ids.add(aid)
            ordered.append(aid)
            id_to_layer[aid] = layer
        layer_ids[layer] = ids
        layer_ordered_ids[layer] = ordered
    return catalog_id, layers, layer_ids, layer_ordered_ids, id_to_layer


def _normalize_mode(mode: Any) -> Optional[str]:
    if mode is None:
        return None
    raw = str(mode).strip()
    for sep in [",", ";", "|", "/"]:
        if sep in raw:
            raw = raw.split(sep)[0]
            break
    raw = raw.strip().split()[0]
    token = raw.lower()
    if token in {"star", "chain", "debate", "tree"}:
        return token.title()
    return None


def _resolve_endpoint(base_url: str) -> Tuple[str, str, str]:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid base_url: {base_url}")
    scheme = parsed.scheme.lower()
    if scheme not in {"https", "http"}:
        raise ValueError(f"Unsupported scheme for base_url: {base_url}")
    base_path = parsed.path.rstrip("/")
    if base_path.endswith("/chat/completions"):
        path = base_path
    elif base_path:
        path = base_path + "/chat/completions"
    else:
        path = "/chat/completions"
    if not path.startswith("/"):
        path = "/" + path
    return parsed.netloc, path, scheme


def _post_chat_completion(
    host: str,
    path: str,
    scheme: str,
    api_key: str,
    payload: Dict[str, Any],
    timeout_secs: int,
) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Connection": "close",
    }
    body = json.dumps(payload).encode("utf-8")
    conn_cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(host, timeout=timeout_secs)
    try:
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        status = resp.status
        try:
            raw = resp.read()
        except http.client.IncompleteRead as exc:
            raise RetryableError(f"IncompleteRead: {exc}", is_timeout=False) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise RetryableError(f"Timeout: {exc}", is_timeout=True) from exc
    except (OSError, ssl.SSLError) as exc:
        raise RetryableError(f"Transport error: {exc}", is_timeout=False) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    text = raw.decode("utf-8", errors="replace")
    if status >= 400:
        snippet = text[:300]
        if status == 429 or 500 <= status < 600:
            raise RetryableError(f"HTTP {status}: {snippet}", is_timeout=False)
        raise FatalAPIError(f"HTTP {status}: {snippet}")
    return text


def _call_teacher(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    timeout_secs: int,
    max_retries: int = 3,
    retry_backoff: float = 1.5,
) -> Tuple[str, str, int, int]:
    host, path, scheme = _resolve_endpoint(base_url)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    retries = 0
    timeouts = 0
    for attempt in range(max_retries):
        try:
            raw_text = _post_chat_completion(host, path, scheme, api_key, payload, timeout_secs)
            assistant_text = _extract_assistant_content(raw_text)
            return assistant_text, raw_text, retries, timeouts
        except RetryableError as exc:
            if exc.is_timeout:
                timeouts += 1
            if attempt >= max_retries - 1:
                raise RuntimeError(f"API retry limit exceeded: {exc}") from exc
            retries += 1
            delay = (retry_backoff ** attempt) + random.uniform(0, 0.5)
            time.sleep(delay)
        except FatalAPIError as exc:
            raise RuntimeError(str(exc)) from exc
    return "", "", retries, timeouts


def _extract_json_obj(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    text = (raw_text or "").strip()
    if not text:
        return None, "empty_response"
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed, None
        return None, "invalid_json"
    except Exception:
        pass
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None, "invalid_json"
    candidate = text[first : last + 1]
    try:
        parsed = json.loads(candidate)
    except Exception:
        return None, "invalid_json"
    if not isinstance(parsed, dict):
        return None, "invalid_json"
    return parsed, None


def _validate_router_plan(
    plan: Dict[str, Any],
    layer_ids: Dict[str, set[str]],
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    violations: List[str] = []
    layers = plan.get("layers")
    if not isinstance(layers, list):
        return None, ["missing_layers"]
    normalized_layers: List[Dict[str, Any]] = []
    if len(layers) != len(LAYER_ORDER):
        violations.append(f"layer_count:{len(layers)}")
    for idx, layer_name in enumerate(LAYER_ORDER):
        entry = layers[idx] if idx < len(layers) else None
        if not isinstance(entry, dict):
            violations.append(f"layer_entry_not_object:{layer_name}")
            entry = {}
        layer_value = entry.get("layer")
        if layer_value != layer_name:
            violations.append(f"layer_order:{layer_value}")
        mode = _normalize_mode(entry.get("mode"))
        if mode is None or mode not in ALLOWED_MODES:
            violations.append(f"invalid_mode:{layer_name}")
            mode = DEFAULT_MODES[layer_name]
        selected = entry.get("selected")
        selected_list: List[str] = []
        if not isinstance(selected, list):
            violations.append(f"selected_not_list:{layer_name}")
        else:
            seen = set()
            for aid in selected:
                if not isinstance(aid, str):
                    violations.append(f"selected_not_str:{layer_name}")
                    continue
                if aid in seen:
                    violations.append(f"duplicate_selected:{layer_name}:{aid}")
                    continue
                seen.add(aid)
                if aid not in layer_ids.get(layer_name, set()):
                    violations.append(f"unknown_agent_id:{layer_name}:{aid}")
                selected_list.append(aid)
        if layer_name in {"L2", "L3"}:
            if not (1 <= len(selected_list) <= 5):
                violations.append(f"{layer_name}_selected_count:{len(selected_list)}")
        normalized_layers.append(
            {"layer": layer_name, "mode": mode, "selected": selected_list}
        )
    reason = plan.get("reason")
    if not isinstance(reason, str):
        violations.append("missing_reason")
        reason = ""
    normalized = {"layers": normalized_layers, "reason": reason}
    return normalized, violations


def _parse_overselect_violation(violation: str) -> Optional[Tuple[str, int]]:
    for layer in ("L2", "L3"):
        prefix = f"{layer}_selected_count:"
        if violation.startswith(prefix):
            try:
                count = int(violation.split(":", 1)[-1])
            except ValueError:
                return None
            return layer, count
    return None


def _only_overselect_violations(violations: List[str]) -> bool:
    if not violations:
        return False
    for violation in violations:
        parsed = _parse_overselect_violation(violation)
        if not parsed:
            return False
        _, count = parsed
        if count <= 5:
            return False
    return True


def _only_unknown_or_overselect_violations(violations: List[str]) -> bool:
    if not violations:
        return False
    for violation in violations:
        if violation.startswith("unknown_agent_id:"):
            continue
        parsed = _parse_overselect_violation(violation)
        if not parsed:
            return False
        _, count = parsed
        if count <= 5:
            return False
    return True


def _apply_unknown_agent_fix(
    plan: Dict[str, Any],
    layer_ids: Dict[str, set[str]],
    layer_ordered_ids: Dict[str, List[str]],
    id_to_layer: Dict[str, str],
) -> Tuple[Dict[str, Any], List[str]]:
    layers = plan.get("layers")
    if not isinstance(layers, list):
        return plan, []
    notes: List[str] = []
    selected_map: Dict[str, List[str]] = {}
    original_counts: Dict[str, int] = {}
    moves: Dict[str, List[str]] = {"L2": [], "L3": []}

    for entry in layers:
        if not isinstance(entry, dict):
            continue
        layer = entry.get("layer")
        selected = entry.get("selected")
        if layer in {"L2", "L3"} and isinstance(selected, list):
            original_counts[layer] = len(selected)
            kept: List[str] = []
            seen: set[str] = set()
            for aid in selected:
                if not isinstance(aid, str):
                    continue
                if aid in seen:
                    continue
                seen.add(aid)
                actual_layer = id_to_layer.get(aid)
                if actual_layer == layer:
                    kept.append(aid)
                elif actual_layer in {"L2", "L3"}:
                    moves[actual_layer].append(aid)
                    notes.append(f"relocated_{aid}:{layer}->{actual_layer}")
                else:
                    if actual_layer is None:
                        notes.append(f"dropped_unknown:{aid}")
                    else:
                        notes.append(f"dropped_cross_layer:{aid}->{actual_layer}")
            selected_map[layer] = kept

    for layer in ("L2", "L3"):
        selected = selected_map.get(layer, [])
        for aid in moves[layer]:
            if aid in selected:
                continue
            selected.append(aid)
        rank = {aid: idx for idx, aid in enumerate(layer_ordered_ids.get(layer, []))}
        selected.sort(key=lambda aid: rank.get(aid, 10**9))
        if len(selected) > 5:
            notes.append(f"trimmed_{layer}:{len(selected)}->5")
            selected = selected[:5]
        min_required = 3 if layer == "L2" else 2
        original = original_counts.get(layer, len(selected))
        if layer == "L2":
            desired = original if 3 <= original <= 5 else 4
        else:
            desired = original if 2 <= original <= 5 else 3
        desired = min(desired, 5)
        desired = max(desired, min_required)
        notes.append(f"desired_{layer}:{original}->{desired}")
        for aid in layer_ordered_ids.get(layer, []):
            if len(selected) >= desired:
                break
            if aid in selected:
                continue
            selected.append(aid)
            notes.append(f"filled_{layer}:{aid}")
        selected_map[layer] = selected

    fixed_layers: List[Dict[str, Any]] = []
    for entry in layers:
        if not isinstance(entry, dict):
            fixed_layers.append(entry)
            continue
        layer = entry.get("layer")
        if layer in {"L2", "L3"} and layer in selected_map:
            new_entry = dict(entry)
            new_entry["selected"] = selected_map[layer]
            fixed_layers.append(new_entry)
        else:
            fixed_layers.append(entry)

    reason = plan.get("reason")
    if not isinstance(reason, str):
        reason = ""
    return {"layers": fixed_layers, "reason": reason}, notes


def _apply_overselect_fix(plan: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    layers = plan.get("layers")
    if not isinstance(layers, list):
        return plan, []
    fixed_layers: List[Dict[str, Any]] = []
    notes: List[str] = []
    for entry in layers:
        if not isinstance(entry, dict):
            fixed_layers.append(entry)
            continue
        layer = entry.get("layer")
        selected = entry.get("selected")
        if layer in {"L2", "L3"} and isinstance(selected, list) and len(selected) > 5:
            original = len(selected)
            trimmed = selected[:5]
            new_entry = dict(entry)
            new_entry["selected"] = trimmed
            fixed_layers.append(new_entry)
            notes.append(f"trimmed_{layer}:{original}->5")
        else:
            fixed_layers.append(entry)
    reason = plan.get("reason")
    if not isinstance(reason, str):
        reason = ""
    return {"layers": fixed_layers, "reason": reason}, notes


def _format_user_prompt(
    question: str,
    mode_hint: Dict[str, str],
    retry_notice: str,
) -> str:
    return USER_PROMPT_TEMPLATE.format(
        question=question,
        mode_L1=mode_hint.get("L1", DEFAULT_MODES["L1"]),
        mode_L2=mode_hint.get("L2", DEFAULT_MODES["L2"]),
        mode_L3=mode_hint.get("L3", DEFAULT_MODES["L3"]),
        mode_L4=mode_hint.get("L4", DEFAULT_MODES["L4"]),
        retry_notice=retry_notice,
    )


def _mode_hint_for_question(question_id: str) -> Dict[str, str]:
    seed = int(question_id.split(":", 1)[-1][:8], 16)
    rng = random.Random(seed)
    r = rng.random()
    l2_mode = "Star"
    for mode, threshold in MODE_DISTRIBUTION:
        if r <= threshold:
            l2_mode = mode
            break
    return {
        "L1": "Chain",
        "L2": l2_mode,
        "L3": "Star",
        "L4": "Chain",
    }


def _iter_questions(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                yield obj


def _infer_source(record: Dict[str, Any], path: Path) -> str:
    src = record.get("source")
    if src in {"real", "teacher"}:
        return src
    name = path.name.lower()
    if "real_questions" in name:
        return "real"
    if "synth_questions" in name or "teacher" in name:
        return "teacher"
    return "unknown"


def _self_check(args: argparse.Namespace) -> int:
    date_str = _validate_date(args.date or datetime.now().strftime("%Y%m%d"))
    catalog_id = _load_catalog_id(args.catalog_id)
    catalog_prompt_path = (
        Path(args.catalog_prompt)
        if args.catalog_prompt
        else Path("data/catalogs") / f"catalog_{catalog_id}_prompt.json"
    )
    _, layers, layer_ids, layer_ordered_ids, id_to_layer = _load_catalog_prompt(catalog_prompt_path)
    questions_path: Optional[Path] = None
    if args.questions:
        try:
            questions_path = _resolve_questions_path(args.questions)
        except ValueError:
            questions_path = None
    if not questions_path:
        fallback = sorted(Path("data/questions").glob("*.jsonl"))
        questions_path = fallback[-1] if fallback else None
    out_ok = (
        Path(args.out_ok)
        if args.out_ok
        else Path("data/router_sft") / f"router_sft_self_check_{date_str}_{catalog_id}.jsonl"
    )
    out_fail = (
        Path(args.out_fail)
        if args.out_fail
        else Path("data/router_sft") / f"router_sft_fail_self_check_{date_str}_{catalog_id}.jsonl"
    )
    out_ok.parent.mkdir(parents=True, exist_ok=True)
    out_fail.parent.mkdir(parents=True, exist_ok=True)
    question = None
    source = "unknown"
    bucket = "unknown"
    mock_payload = json.dumps(
        {"choices": [{"message": {"content": "{\"layers\":[],\"reason\":\"self-check\"}"}}]}
    )
    extracted = _extract_assistant_content(mock_payload)
    if extracted != "{\"layers\":[],\"reason\":\"self-check\"}":
        raise RuntimeError("Self-check failed: assistant content extraction")
    over_plan = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": [next(iter(layer_ids["L1"]))]},
            {"layer": "L2", "mode": "Star", "selected": list(layer_ids["L2"])[:6]},
            {"layer": "L3", "mode": "Star", "selected": list(layer_ids["L3"])[:6]},
            {"layer": "L4", "mode": "Chain", "selected": [next(iter(layer_ids["L4"]))]},
        ],
        "reason": "self-check overselect",
    }
    normalized, violations = _validate_router_plan(over_plan, layer_ids)
    if not _only_overselect_violations(violations):
        raise RuntimeError("Self-check failed: expected only overselect violations")
    fixed, notes = _apply_overselect_fix(normalized or {})
    fixed_norm, fixed_violations = _validate_router_plan(fixed, layer_ids)
    if fixed_violations:
        raise RuntimeError("Self-check failed: overselect auto-fix did not validate")
    if not notes:
        raise RuntimeError("Self-check failed: overselect auto-fix produced no notes")
    cross_plan = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": [next(iter(layer_ids["L1"]))]},
            {"layer": "L2", "mode": "Star", "selected": ["a03_macro_policy", "a19_market_risk"]},
            {
                "layer": "L3",
                "mode": "Star",
                "selected": [
                    "a18_primary_secondary_valuation",
                    "a20_fundamental_risk",
                    "a21_reg_compliance",
                    "a22_suitability_review",
                    "a23_portfolio_opt",
                    "a14_single_stock_tech",
                ],
            },
            {"layer": "L4", "mode": "Chain", "selected": [next(iter(layer_ids["L4"]))]},
        ],
        "reason": "self-check cross-layer",
    }
    normalized, violations = _validate_router_plan(cross_plan, layer_ids)
    if not _only_unknown_or_overselect_violations(violations):
        raise RuntimeError("Self-check failed: expected unknown_agent_id violations")
    fixed, notes = _apply_unknown_agent_fix(normalized or {}, layer_ids, layer_ordered_ids, id_to_layer)
    fixed_norm, fixed_violations = _validate_router_plan(fixed, layer_ids)
    if fixed_violations:
        raise RuntimeError("Self-check failed: unknown agent auto-fix did not validate")
    l2_ids = []
    l3_ids = []
    for entry in fixed_norm.get("layers", []):
        if entry.get("layer") == "L2":
            l2_ids = entry.get("selected") or []
        if entry.get("layer") == "L3":
            l3_ids = entry.get("selected") or []
    if "a19_market_risk" in l2_ids or "a19_market_risk" not in l3_ids:
        raise RuntimeError("Self-check failed: cross-layer relocation did not occur")
    if "a14_single_stock_tech" not in l2_ids or "a14_single_stock_tech" in l3_ids:
        raise RuntimeError("Self-check failed: reverse cross-layer relocation did not occur")
    rank_l2 = {aid: idx for idx, aid in enumerate(layer_ordered_ids.get("L2", []))}
    rank_l3 = {aid: idx for idx, aid in enumerate(layer_ordered_ids.get("L3", []))}
    if sorted(l2_ids, key=lambda aid: rank_l2.get(aid, 10**9)) != l2_ids:
        raise RuntimeError("Self-check failed: L2 ordering not catalog-stable")
    if sorted(l3_ids, key=lambda aid: rank_l3.get(aid, 10**9)) != l3_ids:
        raise RuntimeError("Self-check failed: L3 ordering not catalog-stable")
    if not notes or not any(n.startswith("desired_") for n in notes) or not any(n.startswith("relocated_") for n in notes):
        raise RuntimeError("Self-check failed: unknown agent auto-fix produced no notes")
    if questions_path:
        for record in _iter_questions(questions_path):
            question = record.get("question")
            source = _infer_source(record, questions_path)
            bucket = record.get("bucket")
            if not isinstance(bucket, str) or not bucket.strip():
                bucket = "unknown"
            else:
                bucket = bucket.strip()
            if isinstance(question, str) and question.strip():
                break
    if not question:
        question = "Dummy question for self-check."
    qid = _question_id(question)
    mode_hint = _mode_hint_for_question(qid)
    plan = {
        "layers": [
            {"layer": "L1", "mode": "Chain", "selected": [next(iter(layer_ids["L1"]))]},
            {"layer": "L2", "mode": "Star", "selected": [next(iter(layer_ids["L2"]))]},
            {"layer": "L3", "mode": "Star", "selected": [next(iter(layer_ids["L3"]))]},
            {"layer": "L4", "mode": "Chain", "selected": [next(iter(layer_ids["L4"]))]},
        ],
        "reason": "self-check",
    }
    normalized, violations = _validate_router_plan(plan, layer_ids)
    if violations or not normalized:
        raise RuntimeError(f"Self-check validation failed: {violations}")
    ok_record = {
        "catalog_id": catalog_id,
        "question_id": qid,
        "source": source,
        "bucket": bucket,
        "question": question,
        "mode_hint": mode_hint,
        "teacher": {"provider": "self_check", "model": "none", "base_url": "none", "temperature": 0.0},
        "router_plan_raw": plan,
        "router_plan_parsed": normalized,
        "parser_ok": True,
        "violations": [],
    }
    with out_ok.open("w", encoding="utf-8") as ok_fh:
        ok_fh.write(json.dumps(ok_record, ensure_ascii=False) + "\n")
    with out_fail.open("w", encoding="utf-8") as fail_fh:
        fail_fh.write("")
    print("self_check: ok")
    print(f"self_check_out_ok: {out_ok}")
    print(f"self_check_out_fail: {out_fail}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Router SFT data.")
    parser.add_argument("--questions", default=None)
    parser.add_argument("--catalog-id", default=None)
    parser.add_argument("--catalog-prompt", default=None)
    parser.add_argument("--out-ok", default=None)
    parser.add_argument("--out-fail", default=None)
    parser.add_argument("--date", default=None, help="YYYYMMDD")
    parser.add_argument("--provider", default="deepseek", choices=["deepseek", "openai"])
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--max-items", type=int, default=750)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return _self_check(args)

    date_str = _validate_date(args.date or datetime.now().strftime("%Y%m%d"))
    catalog_id = _load_catalog_id(args.catalog_id)
    catalog_prompt_path = (
        Path(args.catalog_prompt)
        if args.catalog_prompt
        else Path("data/catalogs") / f"catalog_{catalog_id}_prompt.json"
    )
    catalog_id_in_prompt, layers, layer_ids, layer_ordered_ids, id_to_layer = _load_catalog_prompt(
        catalog_prompt_path
    )
    if catalog_id_in_prompt and catalog_id_in_prompt != catalog_id:
        raise ValueError(
            f"Catalog id mismatch: LATEST={catalog_id} prompt={catalog_id_in_prompt}"
        )

    questions_path = _resolve_questions_path(args.questions)
    out_ok = (
        Path(args.out_ok)
        if args.out_ok
        else Path("data/router_sft") / f"router_sft_{date_str}_{catalog_id}.jsonl"
    )
    out_fail = (
        Path(args.out_fail)
        if args.out_fail
        else Path("data/router_sft") / f"router_sft_fail_{date_str}_{catalog_id}.jsonl"
    )
    out_ok.parent.mkdir(parents=True, exist_ok=True)
    out_fail.parent.mkdir(parents=True, exist_ok=True)

    api_key = args.api_key
    if not api_key:
        if args.provider == "deepseek":
            api_key = os.environ.get("DEEPSEEK_API_KEY") or DEEPSEEK_API_KEY.strip()
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing API key: set DEEPSEEK_API_KEY/OPENAI_API_KEY or pass --api-key")

    if args.base_url:
        base_url = args.base_url
    else:
        base_url = (
            "https://api.deepseek.com/v1" if args.provider == "deepseek" else "https://api.openai.com/v1"
        )
    if args.model:
        model = args.model
    else:
        if args.provider == "deepseek":
            model = "deepseek-chat"
        else:
            model = os.environ.get("TEACHER_MODEL") or os.environ.get("MODEL")
    if not model:
        raise ValueError("Missing model: set TEACHER_MODEL/MODEL or pass --model")

    agent_catalog_str = json.dumps(layers, ensure_ascii=False)
    system_prompt = _render_router_system_prompt(
        ROUTER_SYSTEM_PROMPT,
        system_time=datetime.now(tz=UTC).isoformat(),
        agent_catalog=agent_catalog_str,
    )

    total = 0
    ok = 0
    fail = 0
    invalid_json = 0
    violations_count = 0
    retries = 0
    timeouts = 0
    repair_retries = 0

    counts_by_bucket_ok: Dict[str, int] = {}
    counts_by_bucket_fail: Dict[str, int] = {}
    counts_by_l2_mode: Dict[str, int] = {}

    processed = 0
    with out_ok.open("w", encoding="utf-8") as ok_fh, out_fail.open("w", encoding="utf-8") as fail_fh:
        for record in _iter_questions(questions_path):
            if processed >= args.max_items:
                break
            question = record.get("question")
            if not isinstance(question, str) or not question.strip():
                continue
            source = _infer_source(record, questions_path)
            bucket = record.get("bucket")
            if not isinstance(bucket, str) or not bucket.strip():
                bucket = "unknown"
            else:
                bucket = bucket.strip()
            qid = _question_id(question)
            mode_hint = record.get("mode_hint")
            if not isinstance(mode_hint, dict):
                mode_hint = _mode_hint_for_question(qid)
            else:
                normalized_hint = {
                    "L1": _normalize_mode(mode_hint.get("L1")) or DEFAULT_MODES["L1"],
                    "L2": _normalize_mode(mode_hint.get("L2")) or DEFAULT_MODES["L2"],
                    "L3": _normalize_mode(mode_hint.get("L3")) or DEFAULT_MODES["L3"],
                    "L4": _normalize_mode(mode_hint.get("L4")) or DEFAULT_MODES["L4"],
                }
                mode_hint = normalized_hint

            processed += 1
            total += 1
            attempts = 0
            last_raw_text = ""
            last_parsed: Optional[Dict[str, Any]] = None
            last_normalized: Optional[Dict[str, Any]] = None
            last_violations: List[str] = []
            fail_reason = ""
            auto_fix = False
            fix_notes: List[str] = []
            while attempts <= 2:
                retry_notice = ""
                if attempts > 0:
                    if fail_reason == "schema_violation" and last_violations:
                        violations_text = "; ".join(last_violations)
                        retry_notice = (
                            "Previous output violated schema. Violations:\n"
                            f"{violations_text}\n"
                            "Fix by removing excess selections and ensuring counts are within limits. "
                            "Output only corrected JSON."
                        )
                    else:
                        retry_notice = (
                            "Previous output was invalid. Fix the JSON only and output the corrected JSON now.\n"
                            f"Error: {fail_reason or 'invalid_json'}"
                        )
                user_prompt = _format_user_prompt(question, mode_hint, retry_notice)
                try:
                    assistant_text, raw_text, call_retries, call_timeouts = _call_teacher(
                        base_url=base_url,
                        api_key=api_key,
                        model=model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=args.temperature,
                        timeout_secs=args.timeout,
                    )
                    retries += call_retries
                    timeouts += call_timeouts
                except RuntimeError as exc:
                    fail_reason = "http_error"
                    last_raw_text = str(exc)
                    break
                last_raw_text = assistant_text
                parsed, parse_error = _extract_json_obj(assistant_text)
                if parse_error:
                    fail_reason = "invalid_json"
                    attempts += 1
                    repair_retries += 1
                    continue
                last_parsed = parsed
                normalized, violations = _validate_router_plan(parsed or {}, layer_ids)
                last_normalized = normalized
                last_violations = violations
                if violations:
                    if _only_overselect_violations(violations) and normalized:
                        fixed_plan, notes = _apply_overselect_fix(normalized)
                        fixed_norm, fixed_violations = _validate_router_plan(fixed_plan, layer_ids)
                        if not fixed_violations:
                            last_normalized = fixed_norm
                            auto_fix = True
                            fix_notes = notes
                            fail_reason = ""
                            break
                    if _only_unknown_or_overselect_violations(violations) and normalized:
                        fixed_plan, notes = _apply_unknown_agent_fix(
                            normalized, layer_ids, layer_ordered_ids, id_to_layer
                        )
                        fixed_norm, fixed_violations = _validate_router_plan(fixed_plan, layer_ids)
                        if not fixed_violations:
                            last_normalized = fixed_norm
                            auto_fix = True
                            fix_notes = notes
                            fail_reason = ""
                            break
                    fail_reason = "schema_violation"
                    attempts += 1
                    repair_retries += 1
                    continue
                fail_reason = ""
                break

            if fail_reason:
                fail += 1
                if fail_reason == "invalid_json":
                    invalid_json += 1
                if fail_reason == "schema_violation":
                    violations_count += 1
                counts_by_bucket_fail[bucket] = counts_by_bucket_fail.get(bucket, 0) + 1
                fail_record = {
                    "catalog_id": catalog_id,
                    "question_id": qid,
                    "source": source,
                    "bucket": bucket,
                    "question": question,
                    "mode_hint": mode_hint,
                    "teacher": {
                        "provider": args.provider,
                        "model": model,
                        "base_url": base_url,
                        "temperature": args.temperature,
                    },
                    "router_plan_raw": last_parsed,
                    "router_plan_parsed": last_normalized,
                    "parser_ok": False,
                    "violations": last_violations,
                    "fail_reason": fail_reason,
                    "teacher_text": last_raw_text,
                    "assistant_content_excerpt": _excerpt(last_raw_text),
                }
                fail_fh.write(json.dumps(fail_record, ensure_ascii=False) + "\n")
            else:
                ok += 1
                counts_by_bucket_ok[bucket] = counts_by_bucket_ok.get(bucket, 0) + 1
                l2_mode = "Star"
                if last_normalized:
                    for layer_entry in last_normalized.get("layers", []):
                        if layer_entry.get("layer") == "L2":
                            l2_mode = layer_entry.get("mode", "Star")
                            break
                counts_by_l2_mode[l2_mode] = counts_by_l2_mode.get(l2_mode, 0) + 1
                ok_record = {
                    "catalog_id": catalog_id,
                    "question_id": qid,
                    "source": source,
                    "bucket": bucket,
                    "question": question,
                    "mode_hint": mode_hint,
                    "teacher": {
                        "provider": args.provider,
                        "model": model,
                        "base_url": base_url,
                        "temperature": args.temperature,
                    },
                    "router_plan_raw": last_parsed,
                    "router_plan_parsed": last_normalized,
                    "parser_ok": True,
                    "violations": [],
                    "assistant_content_excerpt": _excerpt(last_raw_text),
                }
                if auto_fix:
                    ok_record["auto_fix"] = True
                    ok_record["fix_notes"] = fix_notes
                ok_fh.write(json.dumps(ok_record, ensure_ascii=False) + "\n")

            if processed % max(1, args.batch_size) == 0:
                print(f"progress: {processed}/{args.max_items} ok={ok} fail={fail}")

    ok_rate = ok / total if total else 0.0
    avg_retries = repair_retries / total if total else 0.0

    print(f"catalog_id: {catalog_id}")
    print(f"questions_file: {questions_path}")
    print(f"out_ok: {out_ok}")
    print(f"out_fail: {out_fail}")
    print(
        "summary: total={total} ok={ok} fail={fail} invalid_json={inv} violations={vio} retries={ret} timeouts={to}".format(
            total=total,
            ok=ok,
            fail=fail,
            inv=invalid_json,
            vio=violations_count,
            ret=retries,
            to=timeouts,
        )
    )
    print(f"ok_rate: {ok_rate:.3f} avg_retries: {avg_retries:.3f}")
    print("counts_by_bucket_ok:")
    for key in sorted(counts_by_bucket_ok, key=lambda k: str(k)):
        print(f"  - {key}: {counts_by_bucket_ok[key]}")
    print("counts_by_bucket_fail:")
    for key in sorted(counts_by_bucket_fail, key=lambda k: str(k)):
        print(f"  - {key}: {counts_by_bucket_fail[key]}")
    print("counts_by_L2_mode:")
    for key in sorted(counts_by_l2_mode):
        print(f"  - {key}: {counts_by_l2_mode[key]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
