#!/usr/bin/env python
"""Generate a01 contract SFT data using a teacher model."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import threading
from urllib.parse import urlsplit
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import http.client
import random as _random
import socket
import ssl

from react_agent import prompts, router_parse
from react_agent.contract_utils import validate_contract
from react_agent.json_utils import canonicalize_response, extract_first_json

LAYER_ORDER = router_parse.LAYER_ORDER
DEFAULT_MODES = router_parse.DEFAULT_MODES
SHORT_PROFILE_FIELDS = ["id", "name", "description", "capabilities", "layer", "role_type"]
DEEPSEEK_API_KEY = "sk-35355823d3d544e58e7ebb29c6170094"
GENERIC_V1 = [
    "收集",
    "汇总",
    "整理",
    "总结",
    "撰写",
    "输出",
    "列出",
    "梳理",
    "评估",
    "监测",
    "分析",
    "生成",
    "提供",
    "提交",
]
VERY_GENERIC_V1 = [
    "确保",
    "符合",
    "提交",
    "对齐",
]
VERY_GENERIC_OUTPUT_OBJECTS = [
    "报告",
    "结果",
    "结论",
    "清单",
    "图表",
    "分析",
    "数据",
    "指标",
    "建议",
    "方案",
    "摘要",
    "纪要",
    "说明",
]
VERY_GENERIC_EVAL_OBJECTS = [
    "风险",
    "影响",
    "幅度",
    "趋势",
    "波动",
    "估值",
    "质量",
    "合规",
    "一致性",
    "可行",
    "收益",
    "成本",
    "效率",
    "稳定",
]


class RetryableError(Exception):
    def __init__(self, message: str, *, is_timeout: bool = False) -> None:
        super().__init__(message)
        self.is_timeout = is_timeout


class FatalAPIError(Exception):
    pass


def _pctl(vals: List[float], p: float) -> float:
    if not vals:
        return 0
    vals = sorted(vals)
    idx = int(round(p * (len(vals) - 1)))
    return vals[idx]


def _is_generic_step(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    return any(k in text for k in GENERIC_V1)


def _is_very_generic_step(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    if any(k in text for k in VERY_GENERIC_V1):
        return True
    if "输出" in text:
        if not any(obj in text for obj in VERY_GENERIC_OUTPUT_OBJECTS):
            return True
    if "评估" in text:
        if not any(obj in text for obj in VERY_GENERIC_EVAL_OBJECTS):
            return True
    return False


def compute_quality_metrics(contract: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(contract, dict):
        return {
            "generic_ratio": 0.0,
            "very_generic_ratio": 0.0,
            "has_duplicate_steps": False,
            "steps_len_stats_per_record": {"count": 0, "min": 0, "p50": 0, "p90": 0, "max": 0},
            "steps_total": 0,
            "tasks_count": 0,
            "generic_steps": 0,
            "very_generic_steps": 0,
        }
    tasks = contract.get("tasks")
    tasks = tasks if isinstance(tasks, list) else []
    steps_len_list: List[int] = []
    steps_total = 0
    generic_steps = 0
    very_generic_steps = 0
    has_duplicate_steps = False
    seen_steps = set()

    for task in tasks:
        if not isinstance(task, dict):
            continue
        steps = task.get("steps")
        if not isinstance(steps, list):
            continue
        steps_len_list.append(len(steps))
        for step in steps:
            if not isinstance(step, str):
                continue
            steps_total += 1
            if _is_generic_step(step):
                generic_steps += 1
            if _is_very_generic_step(step):
                very_generic_steps += 1
            norm = " ".join(step.strip().lower().split())
            if norm in seen_steps:
                has_duplicate_steps = True
            else:
                seen_steps.add(norm)

    steps_len_stats = {
        "count": len(steps_len_list),
        "min": min(steps_len_list) if steps_len_list else 0,
        "p50": _pctl(steps_len_list, 0.5),
        "p90": _pctl(steps_len_list, 0.9),
        "max": max(steps_len_list) if steps_len_list else 0,
    }
    generic_ratio = (generic_steps / steps_total) if steps_total else 0.0
    very_generic_ratio = (very_generic_steps / steps_total) if steps_total else 0.0
    return {
        "generic_ratio": generic_ratio,
        "very_generic_ratio": very_generic_ratio,
        "has_duplicate_steps": has_duplicate_steps,
        "steps_len_stats_per_record": steps_len_stats,
        "steps_total": steps_total,
        "tasks_count": len(tasks),
        "generic_steps": generic_steps,
        "very_generic_steps": very_generic_steps,
    }


def compute_teacher_observability(
    assistant_text: str,
    raw_text: str,
    elapsed_ms: float,
) -> Dict[str, Any]:
    assistant_chars = len(assistant_text) if isinstance(assistant_text, str) else 0
    raw_chars = len(raw_text) if isinstance(raw_text, str) else 0
    usage_total_tokens = None
    if isinstance(raw_text, str) and raw_text.strip():
        try:
            payload = json.loads(raw_text)
        except Exception:
            payload = None
        if isinstance(payload, dict):
            usage = payload.get("usage")
            if isinstance(usage, dict):
                total_tokens = usage.get("total_tokens")
                if isinstance(total_tokens, int):
                    usage_total_tokens = total_tokens
    return {
        "elapsed_ms": elapsed_ms,
        "assistant_chars": assistant_chars,
        "raw_chars": raw_chars,
        "usage_total_tokens": usage_total_tokens,
    }


def compute_quality_distribution_stats(
    generic_ratio_list: List[float],
    very_generic_ratio_list: List[float],
    steps_per_task_list: List[float],
    *,
    duplicate_steps_contract_count: int,
    contract_ok: int,
) -> Dict[str, float]:
    duplicate_rate = (duplicate_steps_contract_count / contract_ok) if contract_ok else 0.0
    return {
        "generic_ratio_p50": _pctl(generic_ratio_list, 0.5),
        "generic_ratio_p90": _pctl(generic_ratio_list, 0.9),
        "generic_ratio_p95": _pctl(generic_ratio_list, 0.95),
        "very_generic_ratio_p50": _pctl(very_generic_ratio_list, 0.5),
        "very_generic_ratio_p90": _pctl(very_generic_ratio_list, 0.9),
        "very_generic_ratio_p95": _pctl(very_generic_ratio_list, 0.95),
        "steps_per_task_p50": _pctl(steps_per_task_list, 0.5),
        "steps_per_task_p90": _pctl(steps_per_task_list, 0.9),
        "steps_per_task_p95": _pctl(steps_per_task_list, 0.95),
        "duplicate_steps_contract_rate": duplicate_rate,
    }


class RateLimiter:
    def __init__(self, min_interval_sec: float) -> None:
        self.min_interval_sec = max(0.0, float(min_interval_sec))
        self._lock = threading.Lock()
        self._last_ts = 0.0

    def wait(self) -> None:
        if self.min_interval_sec <= 0:
            return
        with self._lock:
            now = time.perf_counter()
            elapsed = now - self._last_ts
            wait_for = self.min_interval_sec - elapsed
            if wait_for > 0:
                time.sleep(wait_for)
            self._last_ts = time.perf_counter()


def _resolve_endpoint(base_url: str) -> Tuple[str, str, str]:
    if not base_url:
        raise ValueError("Missing base_url")
    if "://" not in base_url:
        base_url = f"https://{base_url}"
    parts = urlsplit(base_url)
    scheme = parts.scheme or "https"
    host = parts.netloc
    if not host:
        raise ValueError(f"Invalid base_url: {base_url}")
    path = "/chat/completions"
    return host, path, scheme


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
            delay = (retry_backoff ** attempt) + _random.uniform(0, 0.5)
            time.sleep(delay)
        except FatalAPIError as exc:
            raise RuntimeError(str(exc)) from exc
    return "", "", retries, timeouts


@dataclass
class Split:
    train: List[Dict[str, Any]]
    val: List[Dict[str, Any]]


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


def _load_profiles(path: Path) -> Dict[str, Dict[str, Any]]:
    profiles: Dict[str, Dict[str, Any]] = {}
    for file in sorted(path.glob("agent_*.json")):
        try:
            obj = json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = obj.get("id")
        if isinstance(aid, str) and aid:
            profiles[aid] = obj
    return profiles


def _short_profile_pack(agent_ids: List[str], profiles: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    pack: List[Dict[str, Any]] = []
    for aid in agent_ids:
        prof = profiles.get(aid, {})
        entry = {k: prof.get(k, "") for k in SHORT_PROFILE_FIELDS}
        pack.append(entry)
    return pack


def _parse_plan(plan_obj: Dict[str, Any]) -> Tuple[Dict[str, List[str]], Dict[str, str], List[str]]:
    layer_plan: Dict[str, List[str]] = {}
    layer_mode: Dict[str, str] = {}
    layers = plan_obj.get("layers")
    if not isinstance(layers, list):
        raise ValueError("missing_layers")
    for entry in layers:
        if not isinstance(entry, dict):
            continue
        layer = entry.get("layer")
        if not isinstance(layer, str) or layer not in LAYER_ORDER:
            continue
        selected = entry.get("selected") or []
        if isinstance(selected, list):
            layer_plan[layer] = [s for s in selected if isinstance(s, str)]
        else:
            layer_plan[layer] = []
        mode = entry.get("mode")
        layer_mode[layer] = mode if isinstance(mode, str) else DEFAULT_MODES.get(layer, "Star")
    for layer in LAYER_ORDER:
        layer_plan.setdefault(layer, [])
        layer_mode.setdefault(layer, DEFAULT_MODES.get(layer, "Star"))
    selected_all: List[str] = []
    seen = set()
    for layer in LAYER_ORDER:
        for aid in layer_plan.get(layer, []):
            if aid not in seen:
                selected_all.append(aid)
                seen.add(aid)
    return layer_plan, layer_mode, selected_all


def _summarize_router_plan(layer_plan: Dict[str, List[str]], layer_mode: Dict[str, str], limit: int = 800) -> str:
    lines: List[str] = []
    for layer in LAYER_ORDER:
        mode = layer_mode.get(layer, DEFAULT_MODES.get(layer, "Star"))
        agents = layer_plan.get(layer, [])
        agent_str = ", ".join(agents) if agents else "none"
        lines.append(f"{layer}({mode}): {agent_str}")
    text = "\n".join(lines)
    if len(text) <= limit:
        return text
    truncated: List[str] = []
    total = 0
    for line in lines:
        if total + len(line) + 1 > limit:
            break
        truncated.append(line)
        total += len(line) + 1
    return "\n".join(truncated) + "\n...[trunc]"


def _extract_question_from_messages(messages: List[Dict[str, Any]]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                if content.startswith("Question:"):
                    return content.split("Question:", 1)[-1].strip()
                return content.strip()
    return ""


def _load_questions_pool(path: Path) -> Dict[str, Dict[str, Any]]:
    data: Dict[str, Dict[str, Any]] = {}
    for rec in _read_jsonl(path):
        qid = rec.get("question_id")
        if isinstance(qid, str):
            data[qid] = rec
    return data


def _teacher_prompts(
    question: str,
    router_plan_summary: str,
    selected_agents: List[str],
    layer_plan: Dict[str, List[str]],
    layer_mode: Dict[str, str],
    profile_pack: List[Dict[str, Any]],
) -> Tuple[str, str]:
    system_prompt = prompts.ORCHESTRATOR_SYSTEM_PROMPT
    user_prompt = (
        "Question:\n"
        f"{question}\n\n"
        "router_plan_summary:\n"
        f"{router_plan_summary}\n\n"
        "selected_agents:\n"
        f"{json.dumps(selected_agents, ensure_ascii=False)}\n\n"
        "layer_plan:\n"
        f"{json.dumps(layer_plan, ensure_ascii=False)}\n\n"
        "layer_mode:\n"
        f"{json.dumps(layer_mode, ensure_ascii=False)}\n\n"
        "agent_profiles_short:\n"
        f"{json.dumps(profile_pack, ensure_ascii=False)}\n\n"
        "Contract constraints:\n"
        "- Do NOT add/remove agents; tasks must cover selected_agents exactly once.\n"
        "- steps must be a list of strings with length 2-6 per task.\n"
        "- agent_can_extend_steps must be true; extension_policy must be a string.\n"
        "- Output JSON only (no markdown)."
    )
    return system_prompt, user_prompt


def _resolve_teacher(args: argparse.Namespace) -> Tuple[str, str, str, float]:
    api_key = args.api_key
    if not api_key:
        api_key = os.environ.get("DEEPSEEK_API_KEY") or DEEPSEEK_API_KEY.strip()
    if not api_key:
        raise ValueError("Missing API key: set DEEPSEEK_API_KEY or pass --api-key")
    base_url = args.base_url or "https://api.deepseek.com"
    model = args.model or "deepseek-chat"
    temperature = args.temperature
    return base_url, api_key, model, temperature


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a01 contract SFT data (teacher).")
    ap.add_argument("--router-sft", default="", help="router_sft_*.jsonl (with router_plan_parsed)")
    ap.add_argument("--router-messages", default="", help="router_sft_messages_*.jsonl (messages+response)")
    ap.add_argument("--questions", default="", help="questions_pool_*.jsonl for question lookup")
    ap.add_argument("--out-train", required=True, help="output train jsonl")
    ap.add_argument("--out-val", required=True, help="output val jsonl")
    ap.add_argument("--out-stats", default="", help="output stats json")
    ap.add_argument("--val-ratio", type=float, default=0.02)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.0, help="sleep seconds between API calls")
    ap.add_argument("--workers", type=int, default=1, help="number of worker threads")
    ap.add_argument("--min-interval-ms", type=float, default=0.0, help="min interval between teacher calls")
    ap.add_argument("--qps", type=float, default=0.0, help="max queries per second")
    ap.add_argument("--api-key", default="", help="override API key")
    ap.add_argument("--base-url", default="", help="override API base URL")
    ap.add_argument("--model", default="", help="override teacher model")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    if not args.router_sft and not args.router_messages:
        raise ValueError("Must provide --router-sft or --router-messages")

    profiles = _load_profiles(REPO_ROOT / "config" / "agents")
    questions_pool = _load_questions_pool(Path(args.questions)) if args.questions else {}
    base_url, api_key, model, temperature = _resolve_teacher(args)

    records_out: List[Dict[str, Any]] = []
    total = 0
    json_extracted_ok = 0
    contract_ok = 0
    dropped = Counter()
    step_lengths: List[int] = []
    total_steps = 0
    total_tasks = 0
    generic_steps_total = 0
    very_generic_steps_total = 0
    duplicate_steps_contract_count = 0
    generic_ratio_list: List[float] = []
    very_generic_ratio_list: List[float] = []
    steps_per_task_list: List[float] = []
    elapsed_ms_list: List[float] = []
    assistant_chars_list: List[float] = []
    usage_total_tokens_list: List[float] = []

    min_interval_sec = 0.0
    if args.min_interval_ms and args.min_interval_ms > 0:
        min_interval_sec = max(min_interval_sec, args.min_interval_ms / 1000.0)
    if args.qps and args.qps > 0:
        min_interval_sec = max(min_interval_sec, 1.0 / args.qps)
    limiter = RateLimiter(min_interval_sec)

    def _process_item(item: Dict[str, Any]) -> Dict[str, Any]:
        question_id = item["question_id"]
        question = item["question"]
        plan_obj = item["plan_obj"]
        meta = item["meta"]
        try:
            layer_plan, layer_mode, selected_agents = _parse_plan(plan_obj)
        except Exception:
            return {"ok": False, "reason": "invalid_router_plan"}
        if not selected_agents:
            return {"ok": False, "reason": "empty_selected_agents"}
        profile_pack = _short_profile_pack(selected_agents, profiles)
        summary = _summarize_router_plan(layer_plan, layer_mode)
        system_prompt, user_prompt = _teacher_prompts(
            question, summary, selected_agents, layer_plan, layer_mode, profile_pack
        )

        limiter.wait()
        start_ts = time.perf_counter()
        try:
            assistant_text, raw_text, retries, timeouts = _call_teacher(
                base_url=base_url,
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                timeout_secs=args.timeout,
            )
        except Exception:
            return {"ok": False, "reason": "teacher_error"}
        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        teacher_obs = compute_teacher_observability(assistant_text, raw_text, elapsed_ms)

        canonical_text, canon_ok = canonicalize_response(assistant_text)
        if not canon_ok:
            return {"ok": False, "reason": "invalid_json"}
        try:
            output_obj = json.loads(canonical_text)
        except Exception:
            return {"ok": False, "reason": "invalid_json"}
        contract = output_obj.get("contract") if isinstance(output_obj, dict) else None
        ok, reason, tasks_by_agent = validate_contract(contract, selected_agents)
        if not ok:
            return {"ok": False, "reason": reason or "invalid_contract"}

        steps_len_list: List[int] = []
        for task in tasks_by_agent.values():
            steps = task.get("steps") or []
            if isinstance(steps, list):
                steps_len_list.append(len(steps))

        quality = compute_quality_metrics(contract)
        tasks_count = quality.get("tasks_count", 0)
        steps_total = quality.get("steps_total", 0)
        steps_per_task = (steps_total / tasks_count) if tasks_count else 0.0

        rec_meta = {
            "question_id": question_id,
            "catalog_id": meta.get("catalog_id"),
            "source": meta.get("source"),
            "bucket": meta.get("bucket", "unknown"),
            "source_catalog_id": meta.get("source_catalog_id"),
            "router_plan_summary": summary,
            "selected_agents": selected_agents,
            "layer_plan": layer_plan,
            "layer_mode": layer_mode,
            "teacher": {
                "provider": "deepseek",
                "model": model,
                "base_url": base_url,
                "temperature": temperature,
                "retries": retries,
                "timeouts": timeouts,
                "elapsed_ms": teacher_obs["elapsed_ms"],
                "assistant_chars": teacher_obs["assistant_chars"],
                "raw_chars": teacher_obs["raw_chars"],
            },
            "quality": {
                "generic_ratio": quality["generic_ratio"],
                "very_generic_ratio": quality["very_generic_ratio"],
                "has_duplicate_steps": quality["has_duplicate_steps"],
                "steps_len_stats_per_record": quality["steps_len_stats_per_record"],
            },
        }
        if teacher_obs.get("usage_total_tokens") is not None:
            rec_meta["teacher"]["usage_total_tokens"] = teacher_obs["usage_total_tokens"]

        rec = {
            "id": question_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response": canonical_text,
            "meta": rec_meta,
        }
        return {
            "ok": True,
            "rec": rec,
            "quality": quality,
            "steps_len_list": steps_len_list,
            "steps_per_task": steps_per_task,
            "teacher_obs": teacher_obs,
        }

    items: List[Dict[str, Any]] = []
    if args.router_sft:
        for rec in _read_jsonl(Path(args.router_sft)):
            if args.max_items is not None and len(items) >= args.max_items:
                break
            question_id = rec.get("question_id") or rec.get("id")
            if not isinstance(question_id, str):
                dropped["missing_question_id"] += 1
                continue
            question = rec.get("question")
            if not isinstance(question, str) or not question.strip():
                pool = questions_pool.get(question_id, {})
                question = pool.get("question", "")
            if not question:
                dropped["missing_question"] += 1
                continue
            plan_obj = rec.get("router_plan_parsed") or rec.get("router_plan_raw")
            if not isinstance(plan_obj, dict):
                dropped["missing_router_plan"] += 1
                continue
            meta = {
                "catalog_id": rec.get("catalog_id"),
                "source": rec.get("source"),
                "bucket": rec.get("bucket", "unknown"),
                "source_catalog_id": rec.get("source_catalog_id"),
            }
            items.append(
                {
                    "question_id": question_id,
                    "question": question,
                    "plan_obj": plan_obj,
                    "meta": meta,
                }
            )

    if args.router_messages:
        for rec in _read_jsonl(Path(args.router_messages)):
            if args.max_items is not None and len(items) >= args.max_items:
                break
            meta = rec.get("meta")
            meta = meta if isinstance(meta, dict) else {}
            question_id = meta.get("question_id") or rec.get("id")
            if not isinstance(question_id, str):
                dropped["missing_question_id"] += 1
                continue
            question = _extract_question_from_messages(rec.get("messages") or [])
            if not question:
                pool = questions_pool.get(question_id, {})
                question = pool.get("question", "")
            if not question:
                dropped["missing_question"] += 1
                continue
            response = rec.get("response", "")
            if not isinstance(response, str) or not response.strip():
                dropped["missing_router_plan"] += 1
                continue
            candidate = extract_first_json(response)
            if not candidate:
                dropped["missing_router_plan"] += 1
                continue
            try:
                plan_obj = json.loads(candidate)
            except Exception:
                dropped["missing_router_plan"] += 1
                continue
            items.append(
                {
                    "question_id": question_id,
                    "question": question,
                    "plan_obj": plan_obj,
                    "meta": meta,
                }
            )

    def _iter_results():
        if args.workers <= 1:
            for item in items:
                yield _process_item(item)
                if args.sleep:
                    time.sleep(args.sleep)
            return
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for res in ex.map(_process_item, items):
                yield res

    for res in _iter_results():
        total += 1
        if not res.get("ok"):
            dropped[res.get("reason", "unknown_error")] += 1
            continue
        rec = res["rec"]
        quality = res["quality"]
        steps_len_list = res["steps_len_list"]
        steps_per_task = res["steps_per_task"]
        teacher_obs = res["teacher_obs"]

        records_out.append(rec)
        contract_ok += 1
        json_extracted_ok += 1

        for length in steps_len_list:
            step_lengths.append(length)

        total_steps += quality.get("steps_total", 0)
        total_tasks += quality.get("tasks_count", 0)
        generic_steps_total += quality.get("generic_steps", 0)
        very_generic_steps_total += quality.get("very_generic_steps", 0)
        if quality.get("has_duplicate_steps"):
            duplicate_steps_contract_count += 1
        generic_ratio_list.append(quality.get("generic_ratio", 0.0))
        very_generic_ratio_list.append(quality.get("very_generic_ratio", 0.0))
        steps_per_task_list.append(steps_per_task)

        elapsed_ms_list.append(teacher_obs.get("elapsed_ms", 0.0))
        assistant_chars_list.append(teacher_obs.get("assistant_chars", 0.0))
        usage_val = teacher_obs.get("usage_total_tokens")
        if isinstance(usage_val, int):
            usage_total_tokens_list.append(float(usage_val))

    split = _split_records(records_out, args.val_ratio, args.seed)
    train_n = _write_jsonl(Path(args.out_train), split.train)
    val_n = _write_jsonl(Path(args.out_val), split.val)

    steps_stats = {
        "count": len(step_lengths),
        "min": min(step_lengths) if step_lengths else 0,
        "p50": _pctl(step_lengths, 0.5),
        "p90": _pctl(step_lengths, 0.9),
        "max": max(step_lengths) if step_lengths else 0,
    }

    overreach_reasons = {
        "selected_agents_mismatch",
        "task_agent_mismatch",
        "duplicate_task_agent",
        "tasks_cover_mismatch",
        "missing_a01",
    }
    overreach_count = sum(count for reason, count in dropped.items() if reason in overreach_reasons)
    teacher_error = dropped.get("teacher_error", 0)
    coverage_rate = (contract_ok / total) if total else 0.0
    overreach_rate = (overreach_count / total) if total else 0.0

    avg_steps_per_task = (total_steps / total_tasks) if total_tasks else 0.0
    generic_steps_ratio_v1 = (generic_steps_total / total_steps) if total_steps else 0.0
    very_generic_steps_ratio_v1 = (very_generic_steps_total / total_steps) if total_steps else 0.0
    quality_dist = compute_quality_distribution_stats(
        generic_ratio_list,
        very_generic_ratio_list,
        steps_per_task_list,
        duplicate_steps_contract_count=duplicate_steps_contract_count,
        contract_ok=contract_ok,
    )
    elapsed_ms_p50 = _pctl(elapsed_ms_list, 0.5)
    elapsed_ms_p90 = _pctl(elapsed_ms_list, 0.9)
    elapsed_ms_p95 = _pctl(elapsed_ms_list, 0.95)
    assistant_chars_p50 = _pctl(assistant_chars_list, 0.5)
    assistant_chars_p90 = _pctl(assistant_chars_list, 0.9)
    assistant_chars_p95 = _pctl(assistant_chars_list, 0.95)
    usage_total_tokens_p50 = _pctl(usage_total_tokens_list, 0.5)
    usage_total_tokens_p90 = _pctl(usage_total_tokens_list, 0.9)
    usage_total_tokens_p95 = _pctl(usage_total_tokens_list, 0.95)
    stats = {
        "total": total,
        "json_extracted_ok": json_extracted_ok,
        "contract_ok": contract_ok,
        "teacher_error": teacher_error,
        "train_written": train_n,
        "val_written": val_n,
        "coverage_rate": coverage_rate,
        "overreach_rate": overreach_rate,
        "dropped_reason_topk": dropped.most_common(10),
        "steps_len_stats": steps_stats,
        "generic_steps_ratio_v1": generic_steps_ratio_v1,
        "very_generic_steps_ratio_v1": very_generic_steps_ratio_v1,
        "duplicate_steps_contract_count": duplicate_steps_contract_count,
        "avg_steps_per_task": avg_steps_per_task,
        "elapsed_ms_p50": elapsed_ms_p50,
        "elapsed_ms_p90": elapsed_ms_p90,
        "elapsed_ms_p95": elapsed_ms_p95,
        "assistant_chars_p50": assistant_chars_p50,
        "assistant_chars_p90": assistant_chars_p90,
        "assistant_chars_p95": assistant_chars_p95,
        "usage_total_tokens_p50": usage_total_tokens_p50,
        "usage_total_tokens_p90": usage_total_tokens_p90,
        "usage_total_tokens_p95": usage_total_tokens_p95,
        **quality_dist,
    }
    if args.out_stats:
        out_path = Path(args.out_stats)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
