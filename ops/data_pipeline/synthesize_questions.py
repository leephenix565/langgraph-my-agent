#!/usr/bin/env python
"""Synthesize questions via OpenAI-compatible Chat Completions API."""

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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse


DEEPSEEK_API_KEY = "sk-35355823d3d544e58e7ebb29c6170094"  # Optional: fill in your key here if env vars are not set.

BUCKETS: List[Dict[str, str]] = [
    {
        "name": "利率/通胀/就业（宏观冲击）",
        "desc": "聚焦利率、通胀、就业等宏观冲击对资产价格与配置的影响。",
    },
    {
        "name": "缩表/QT/流动性（信用与资金面）",
        "desc": "关注缩表/QT、流动性与信用环境变化对市场的传导。",
    },
    {
        "name": "汇率/美元/海外风险（跨市场传导）",
        "desc": "强调汇率、美元强弱与海外风险对本地资产的影响。",
    },
    {
        "name": "行业景气/产业链传导（中观）",
        "desc": "围绕行业景气与产业链上下游传导效应的分析问题。",
    },
    {
        "name": "主题轮动/政策催化（主题与风格）",
        "desc": "聚焦主题轮动、政策催化与风格切换的驱动因素。",
    },
    {
        "name": "个股事件（并购/诉讼/产品/事故）",
        "desc": "强调个股重大事件对走势与估值的影响。",
    },
    {
        "name": "财报/指引/预告（基本面）",
        "desc": "关注财报披露、业绩指引与预告对基本面的影响。",
    },
    {
        "name": "资金流/持仓变化（机构行为）",
        "desc": "聚焦资金流向、持仓变化与机构行为信号。",
    },
    {
        "name": "技术面（趋势/形态/量价）",
        "desc": "围绕趋势、形态、量价结构的技术面问题。",
    },
    {
        "name": "舆情/新闻情绪/研报分歧",
        "desc": "关注新闻情绪、舆情与研报分歧对决策的影响。",
    },
    {
        "name": "估值（通用估值）",
        "desc": "侧重通用估值方法与估值区间判断。",
    },
    {
        "name": "科创估值（更重无形资产/政策敏感）",
        "desc": "面向科创企业估值，强调无形资产与政策敏感性。",
    },
    {
        "name": "风险（回撤/波动/极端情景）",
        "desc": "聚焦回撤、波动与极端情景下的风险评估。",
    },
    {
        "name": "合规与投资者保护（规则审查）",
        "desc": "围绕合规规则审查与投资者保护要求的判断问题。",
    },
    {
        "name": "适当性+组合（画像匹配/组合优化/回测）",
        "desc": "强调适当性匹配、组合优化与历史回测的结合。",
    },
]

SYSTEM_PROMPT = (
    "你是金融研究问题生成器。你的任务：只生成“用户问题”，不要生成任何分析过程、"
    "不要生成路由计划、不要提及 agent 或 Router。\n\n"
    "必须严格输出 JSONL：每行一个 JSON 对象，字段只能是：\n"
    '{ "bucket": "...", "lang": "zh", "question": "..." }\n\n'
    "除 JSONL 外，不要输出任何其他文字、标题、解释或代码块。"
)

TIME_PATTERN = re.compile(r"(最近|近\\d+|本周|本月|202\\d年|季度)")
OBJECT_PATTERN = re.compile(r"(ETF|指数|板块|行业|国债|收益率|汇率|美元|黄金|原油|股票|债券|商品|[A-Z]{2,5})", re.I)

DIMENSION_PATTERNS: Dict[str, re.Pattern[str]] = {
    "macro": re.compile(r"宏观|政策|利率|通胀|就业|央行|加息|降息|缩表|QT|流动性|信用"),
    "industry": re.compile(r"行业|产业链|景气|板块|主题|政策催化"),
    "company": re.compile(r"财报|业绩|指引|预告|并购|诉讼|产品|事故|盈利"),
    "flow": re.compile(r"资金流|持仓|北向|南向|机构|资金|换手"),
    "technical": re.compile(r"技术面|均线|趋势|形态|量价|MACD|K线"),
    "sentiment": re.compile(r"舆情|新闻|情绪|研报|分歧|舆论"),
    "valuation": re.compile(r"估值|PE|PB|EV/EBITDA|DCF"),
    "risk": re.compile(r"风险|回撤|波动|极端|压力测试"),
    "compliance": re.compile(r"合规|监管|规则|投资者保护"),
    "suitability": re.compile(r"适当性|画像|风险偏好"),
    "portfolio": re.compile(r"组合|回测|仓位|配置|再平衡"),
}


def _validate_date(date_str: str) -> str:
    s = date_str.strip()
    if not re.fullmatch(r"\d{8}", s):
        raise ValueError(f"Invalid --date '{date_str}' expected YYYYMMDD.")
    try:
        datetime.strptime(s, "%Y%m%d")
    except ValueError:
        raise ValueError(f"Invalid --date '{date_str}' expected YYYYMMDD.")
    return s


def _self_check_validate_date() -> None:
    valid = ["20260107", "20240229", "20251231"]
    invalid = ["2026-01-07", "20260230", "abcd0101", "2026010"]
    for value in valid:
        if _validate_date(value) != value:
            raise ValueError("Date self-check failed on valid case")
    for value in invalid:
        try:
            _validate_date(value)
        except ValueError:
            continue
        raise ValueError("Date self-check failed on invalid case")


def _load_catalog_id(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    latest_path = Path("data/catalogs/LATEST")
    if not latest_path.exists():
        raise ValueError("Missing data/catalogs/LATEST; pass --catalog-id explicitly")
    text = latest_path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("data/catalogs/LATEST is empty; pass --catalog-id explicitly")
    if text.startswith("{"):
        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and isinstance(payload.get("catalog_id"), str):
                return payload["catalog_id"].strip()
        except Exception:
            pass
    return text


def _normalize_question(text: str) -> str:
    return re.sub(r"\\s+", " ", text).strip().lower()


def _count_dimensions(question: str) -> int:
    count = 0
    for pattern in DIMENSION_PATTERNS.values():
        if pattern.search(question):
            count += 1
    return count


def _passes_quality(question: str) -> bool:
    if not question or not isinstance(question, str):
        return False
    if len(question) < 20 or len(question) > 250:
        return False
    if not TIME_PATTERN.search(question):
        return False
    if not OBJECT_PATTERN.search(question):
        return False
    if _count_dimensions(question) < 2:
        return False
    return True


def _build_avoidlist(
    bucket_questions: List[str],
    all_questions: List[str],
    rng: random.Random,
    max_items: int = 20,
) -> List[str]:
    candidates: List[str] = []
    candidates.extend(bucket_questions[-50:])
    candidates.extend(all_questions[-50:])
    seen = set()
    uniq = []
    for item in reversed(candidates):
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    if not uniq:
        return []
    k = min(max_items, len(uniq))
    if len(uniq) <= k:
        return list(reversed(uniq))
    return rng.sample(list(reversed(uniq)), k)


def _format_user_prompt(bucket: Dict[str, str], n: int, avoidlist: List[str]) -> str:
    avoid_block = "\n".join(avoidlist) if avoidlist else "(none)"
    return (
        f"bucket: {bucket['name']}\n"
        f"bucket_desc: {bucket['desc']}\n\n"
        f"请生成 {n} 条中文金融问题（lang=zh），要求：\n"
        "1) 每条必须包含明确对象 + 明确时间窗口：\n"
        "   - 对象必须属于：股票/ETF/行业主题/商品/债券/汇率（任选其一或多个）\n"
        "   - 时间窗口示例：最近3天/最近1周/最近1个月/2025年12月/2026年1月\n"
        "2) 每条必须是“多信号融合”任务：至少包含以下维度中的 2–3 个：\n"
        "   宏观政策/数据、行业/产业链、公司事件/财报、资金流/持仓、技术面、新闻情绪、估值、风险、合规/适当性、组合构建/回测/仓位时点\n"
        "2.5) 每行问题不超过 80 字；本次输出不超过上述数量的 JSONL 行数。\n"
        "3) 避免重复：不要与下列问题同义改写（不要只换个说法）：\n"
        f"{avoid_block}\n\n"
        "只输出 JSONL。"
    )


class RetryableError(Exception):
    def __init__(self, message: str, *, is_timeout: bool = False) -> None:
        super().__init__(message)
        self.is_timeout = is_timeout


class FatalAPIError(Exception):
    pass


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


def _extract_jsonl_from_content(content: str) -> Tuple[List[Dict[str, Any]], int]:
    items: List[Dict[str, Any]] = []
    invalid = 0
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            invalid += 1
            continue
        if isinstance(obj, dict):
            items.append(obj)
        else:
            invalid += 1
    return items, invalid


def _call_teacher(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_secs: int,
    max_retries: int,
    retry_backoff: float,
) -> Tuple[List[Dict[str, Any]], int, int, int]:
    host, path, scheme = _resolve_endpoint(base_url)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    retries = 0
    timeouts = 0
    for attempt in range(max_retries):
        try:
            raw = _post_chat_completion(host, path, scheme, api_key, payload, timeout_secs)
            break
        except RetryableError as exc:
            if exc.is_timeout:
                timeouts += 1
            if attempt >= max_retries - 1:
                raise RuntimeError(f"API retry limit exceeded: {exc}") from exc
            retries += 1
            delay = (retry_backoff ** attempt) + random.uniform(0, 0.5)
            time.sleep(delay)
            continue
        except FatalAPIError as exc:
            raise RuntimeError(str(exc)) from exc
    try:
        data = json.loads(raw)
    except Exception:
        return [], 1, retries, timeouts
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return [], 1, retries, timeouts
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return [], 1, retries, timeouts
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return [], 1, retries, timeouts
    items, invalid = _extract_jsonl_from_content(content)
    return items, invalid, retries, timeouts


def _load_existing_output(
    out_path: Path,
    bucket_records: Dict[str, List[Dict[str, Any]]],
    bucket_questions: Dict[str, List[str]],
    all_questions: List[str],
    seen_hashes: set[str],
) -> None:
    if not out_path.exists():
        return
    with out_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            bucket = obj.get("bucket")
            question = obj.get("question")
            if bucket not in bucket_records or not isinstance(question, str):
                continue
            norm = _normalize_question(question)
            h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            bucket_records[bucket].append(obj)
            bucket_questions[bucket].append(question.strip())
            all_questions.append(question.strip())


def _append_records(out_path: Path, records: List[Dict[str, Any]]) -> None:
    if not records:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize question pool by buckets.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--date", default=None, help="YYYYMMDD")
    parser.add_argument("--out", default=None, help="Output JSONL path")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-calls", type=int, default=500)
    parser.add_argument("--max-tokens", type=int, default=800)
    parser.add_argument("--timeout-secs", type=int, default=300)
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument("--retry-backoff", type=float, default=1.5)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--catalog-id", default=None)
    parser.add_argument("--sample", type=int, default=0, help="Print N random samples")
    parser.add_argument("--self-check", action="store_true", help="Run date validation self-check and exit")
    args = parser.parse_args()

    if args.self_check:
        _self_check_validate_date()
        print("self_check: ok")
        return 0

    date_str = _validate_date(args.date or datetime.now().strftime("%Y%m%d"))
    catalog_id = _load_catalog_id(args.catalog_id)

    deepseek_env_key = os.environ.get("DEEPSEEK_API_KEY")
    openai_env_key = os.environ.get("OPENAI_API_KEY")
    provider = "openai"
    using_deepseek = False
    local_deepseek_key = DEEPSEEK_API_KEY.strip()
    if args.api_key:
        api_key = args.api_key
    elif deepseek_env_key:
        api_key = deepseek_env_key
        provider = "deepseek"
        using_deepseek = True
    elif local_deepseek_key:
        api_key = local_deepseek_key
        provider = "deepseek"
        using_deepseek = True
    elif openai_env_key:
        api_key = openai_env_key
    else:
        raise ValueError("Missing API key: set DEEPSEEK_API_KEY/OPENAI_API_KEY or pass --api-key")

    if args.base_url:
        base_url = args.base_url
    else:
        base_url = "https://api.deepseek.com/v1" if using_deepseek else "https://api.openai.com/v1"

    if args.model:
        model = args.model
    elif using_deepseek:
        model = "deepseek-chat"
    else:
        model = os.environ.get("TEACHER_MODEL") or os.environ.get("MODEL")
    if not model:
        raise ValueError("Missing model: set TEACHER_MODEL/MODEL or pass --model")

    print(f"provider={provider} base_url={base_url} model={model}")

    out_path = (
        Path(args.out)
        if args.out
        else Path("data/questions") / f"synth_questions_{date_str}_{catalog_id}.jsonl"
    )

    rng = random.Random(args.seed)
    api_calls = 0
    invalid_json = 0
    rejected_by_rules = 0
    duplicates_dropped = 0
    retries = 0
    timeouts = 0

    seen_hashes = set()
    all_questions: List[str] = []
    bucket_records: Dict[str, List[Dict[str, Any]]] = {b["name"]: [] for b in BUCKETS}
    bucket_questions: Dict[str, List[str]] = {b["name"]: [] for b in BUCKETS}

    _load_existing_output(out_path, bucket_records, bucket_questions, all_questions, seen_hashes)
    for bucket in BUCKETS:
        bucket_name = bucket["name"]
        if len(bucket_records[bucket_name]) > 50:
            raise RuntimeError(f"Existing output has >50 entries for bucket: {bucket_name}")

    for bucket in BUCKETS:
        bucket_name = bucket["name"]
        target = 50
        while len(bucket_records[bucket_name]) < target:
            if api_calls >= args.max_calls:
                break
            remaining = target - len(bucket_records[bucket_name])
            batch_size = min(args.batch_size, remaining)
            avoidlist = _build_avoidlist(bucket_questions[bucket_name], all_questions, rng)
            user_prompt = _format_user_prompt(bucket, batch_size, avoidlist)
            items, invalid, call_retries, call_timeouts = _call_teacher(
                base_url,
                api_key,
                model,
                SYSTEM_PROMPT,
                user_prompt,
                temperature=0.7,
                max_tokens=args.max_tokens,
                timeout_secs=args.timeout_secs,
                max_retries=args.max_retries,
                retry_backoff=args.retry_backoff,
            )
            api_calls += 1
            invalid_json += invalid
            retries += call_retries
            timeouts += call_timeouts
            new_records: List[Dict[str, Any]] = []
            for item in items:
                if not isinstance(item, dict):
                    invalid_json += 1
                    continue
                if item.get("bucket") != bucket_name:
                    rejected_by_rules += 1
                    continue
                if item.get("lang") != "zh":
                    rejected_by_rules += 1
                    continue
                question = item.get("question")
                if not isinstance(question, str):
                    rejected_by_rules += 1
                    continue
                if not _passes_quality(question):
                    rejected_by_rules += 1
                    continue
                norm = _normalize_question(question)
                h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
                if h in seen_hashes:
                    duplicates_dropped += 1
                    continue
                seen_hashes.add(h)
                record = {
                    "catalog_id": catalog_id,
                    "source": "teacher",
                    "bucket": bucket_name,
                    "lang": "zh",
                    "question": question.strip(),
                }
                bucket_records[bucket_name].append(record)
                bucket_questions[bucket_name].append(question.strip())
                all_questions.append(question.strip())
                new_records.append(record)
                if len(bucket_records[bucket_name]) >= target:
                    break
            _append_records(out_path, new_records)

    counts_by_bucket = {b["name"]: len(bucket_records[b["name"]]) for b in BUCKETS}
    total_written = sum(counts_by_bucket.values())
    if total_written != 750:
        missing = {k: v for k, v in counts_by_bucket.items() if v < 50}
        raise RuntimeError(
            f"Generation incomplete: total={total_written}, missing={missing}, api_calls={api_calls}"
        )

    print(f"catalog_id: {catalog_id}")
    print(f"out_path: {out_path}")
    print(
        "total_written: {total} | duplicates_dropped: {dup} | rejected_by_rules: {rej} | "
        "invalid_json: {inv} | api_calls: {calls} | retries: {ret} | timeouts: {to}".format(
            total=total_written,
            dup=duplicates_dropped,
            rej=rejected_by_rules,
            inv=invalid_json,
            calls=api_calls,
            ret=retries,
            to=timeouts,
        )
    )
    print("counts_by_bucket:")
    for bucket in BUCKETS:
        name = bucket["name"]
        print(f"  - {name}: {counts_by_bucket[name]}")

    if args.sample > 0:
        samples: List[Dict[str, Any]] = []
        for bucket in BUCKETS:
            samples.extend(bucket_records[bucket["name"]])
        rng.shuffle(samples)
        print("sample_questions:")
        for rec in samples[: args.sample]:
            print(f"  - {rec['bucket']}: {rec['question']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
