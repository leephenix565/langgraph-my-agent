"""Benchmark Doubao Seed 2.0 (Ark OpenAI-compatible) raw vs LangGraph E2E speed.

Outputs:
- CSV summary table
- Markdown summary table

Design goals:
- No API keys in code/logs (read from env only)
- Raw benchmark uses OpenAI-compatible /chat/completions with stream + include_usage
- E2E benchmark runs the existing LangGraph graph end-to-end (router->manager->agents->summary)
- thinking is explicitly disabled in raw payload and in LangChain(OpenAI) calls used by E2E
- Search is disabled for E2E via DISABLE_SEARCH=1 to reduce noise
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import http.client
import importlib.util
import json
import os
import socket
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.parse import urlparse


DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_QUESTION = "请用不超过5条要点分析当前美国科技股板块的主要驱动因素与风险。"
DEFAULT_RAW_PROMPT = "请用一句话解释为什么低时延推理对多智能体编排系统很重要。"


def _pctl(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        return xs[0]
    q = min(max(float(q), 0.0), 1.0)
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def _fmt_num(val: Optional[float], digits: int = 2) -> str:
    if val is None:
        return ""
    return f"{val:.{digits}f}"


def _resolve_models(models_arg: str) -> List[Tuple[str, str]]:
    """Return [(alias, actual_model_id), ...]."""
    if models_arg.strip():
        items: List[Tuple[str, str]] = []
        for chunk in models_arg.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "=" in chunk:
                alias, model = chunk.split("=", 1)
                alias = alias.strip()
                model = model.strip()
            else:
                alias = chunk.strip()
                model = chunk.strip()
            if alias and model:
                items.append((alias, model))
        if items:
            return items

    env_map = {
        "pro": os.environ.get("DOUBAO_SEED2_PRO_MODEL", "").strip(),
        "lite": os.environ.get("DOUBAO_SEED2_LITE_MODEL", "").strip(),
        "mini": os.environ.get("DOUBAO_SEED2_MINI_MODEL", "").strip(),
    }
    out = [(alias, model) for alias, model in env_map.items() if model]
    if out:
        return out
    raise SystemExit(
        "Missing Doubao model ids. Set DOUBAO_SEED2_{PRO,LITE,MINI}_MODEL env vars "
        "or pass --models 'pro=<id>,lite=<id>,mini=<id>'."
    )


def _resolve_api_key() -> str:
    for key_name in ("ARK_API_KEY", "OPENAI_API_KEY", "ARK_OPENAI_API_KEY"):
        val = os.environ.get(key_name, "").strip()
        if val:
            return val
    raise SystemExit("Missing API key: set ARK_API_KEY or OPENAI_API_KEY (env only).")


def _resolve_base_url(cli_base_url: str) -> str:
    if cli_base_url.strip():
        return cli_base_url.strip()
    for key_name in ("ARK_OPENAI_BASE_URL", "OPENAI_BASE_URL"):
        val = os.environ.get(key_name, "").strip()
        if val:
            return val
    return DEFAULT_ARK_BASE_URL


def _resolve_endpoint(base_url: str) -> Tuple[str, str, str]:
    raw = (base_url or "").strip()
    if not raw:
        raw = DEFAULT_ARK_BASE_URL
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    scheme = parsed.scheme or "https"
    host = parsed.netloc or parsed.path
    path = parsed.path if parsed.netloc else ""
    if not host:
        raise ValueError(f"Invalid base_url: {base_url!r}")
    path = (path or "").rstrip("/")
    if path.endswith("/chat/completions"):
        endpoint = path
    else:
        endpoint = f"{path}/chat/completions" if path else "/chat/completions"
    return host, endpoint, scheme


def _build_raw_payload(
    *,
    model: str,
    user_prompt: str,
    temperature: float,
    max_completion_tokens: Optional[int],
    thinking_type: str,
    stream: bool,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": temperature,
        "stream": bool(stream),
        "thinking": {"type": thinking_type},
    }
    if max_completion_tokens is not None and max_completion_tokens > 0:
        payload["max_completion_tokens"] = int(max_completion_tokens)
    if stream:
        payload["stream_options"] = {"include_usage": True}
    return payload


def _post_stream_chat_completion(
    *,
    host: str,
    path: str,
    scheme: str,
    api_key: str,
    payload: Mapping[str, Any],
    timeout_secs: int,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Connection": "close",
    }
    conn_cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(host, timeout=timeout_secs)
    try:
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        status = int(resp.status)
        if status >= 400:
            err_body = resp.read(2048)
            raise RuntimeError(f"HTTP {status}: {err_body.decode('utf-8', errors='replace')}")

        chunks: List[str] = []
        usage: Optional[Dict[str, Any]] = None
        while True:
            line_b = resp.readline()
            if not line_b:
                break
            line = line_b.decode("utf-8", errors="replace").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except Exception:
                continue
            if isinstance(obj, dict):
                usage_obj = obj.get("usage")
                if isinstance(usage_obj, dict):
                    usage = usage_obj
                choices = obj.get("choices")
                if isinstance(choices, list) and choices:
                    delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
                    if isinstance(delta, dict):
                        content = delta.get("content")
                        if isinstance(content, str):
                            chunks.append(content)
                        elif isinstance(content, list):
                            for part in content:
                                if isinstance(part, str):
                                    chunks.append(part)
                                elif isinstance(part, dict) and isinstance(part.get("text"), str):
                                    chunks.append(part["text"])
        return "".join(chunks), usage
    except (socket.timeout, TimeoutError) as exc:
        raise RuntimeError(f"timeout: {exc}") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _completion_tokens_from_usage(usage: Optional[Dict[str, Any]]) -> Optional[int]:
    if not isinstance(usage, dict):
        return None
    for key in ("completion_tokens", "output_tokens"):
        val = usage.get(key)
        if isinstance(val, int):
            return val
    total_tokens = usage.get("total_tokens")
    prompt_tokens = usage.get("prompt_tokens")
    if isinstance(total_tokens, int) and isinstance(prompt_tokens, int):
        return max(total_tokens - prompt_tokens, 0)
    return None


@dataclass
class RawRunResult:
    elapsed_ms: float
    completion_tokens: Optional[int]
    tokens_per_sec: Optional[float]
    usage: Optional[Dict[str, Any]]
    text_chars: int


def _run_raw_once(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    temperature: float,
    max_completion_tokens: Optional[int],
    thinking_type: str,
    timeout_secs: int,
    payload_probe_out: Optional[List[Dict[str, Any]]] = None,
) -> RawRunResult:
    host, path, scheme = _resolve_endpoint(base_url)
    payload = _build_raw_payload(
        model=model,
        user_prompt=prompt,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        thinking_type=thinking_type,
        stream=True,
    )
    if payload_probe_out is not None:
        payload_probe_out.append(payload)
    t0 = time.perf_counter()
    text, usage = _post_stream_chat_completion(
        host=host,
        path=path,
        scheme=scheme,
        api_key=api_key,
        payload=payload,
        timeout_secs=timeout_secs,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    completion_tokens = _completion_tokens_from_usage(usage)
    tps = None
    if completion_tokens is not None and elapsed_ms > 0:
        tps = float(completion_tokens) / (elapsed_ms / 1000.0)
    return RawRunResult(
        elapsed_ms=elapsed_ms,
        completion_tokens=completion_tokens,
        tokens_per_sec=tps,
        usage=usage,
        text_chars=len(text),
    )


@dataclass
class E2ERunResult:
    elapsed_ms: float
    search_tool_calls: int
    final_message_chars: int
    thinking_probe: Dict[str, Any]
    run_id: str
    trace_log_file: str


class _DummySearchTool:
    def __init__(self, counter: Dict[str, int]) -> None:
        self._counter = counter
        self.name = "tavily_search"
        self.max_results = 0

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - runtime guard
        self._counter["search_tool_calls"] = self._counter.get("search_tool_calls", 0) + 1
        raise RuntimeError("Search tool invocation blocked in benchmark (DISABLE_SEARCH expected).")


async def _run_e2e_once(
    *,
    base_url: str,
    api_key: str,
    model_id: str,
    question: str,
    temperature: float,
    thinking_type: str,
    disable_search: bool,
    run_id: str,
    enable_profiling: bool,
    profile_log_dir: Optional[Path],
) -> E2ERunResult:
    # Env is process-global; set before importing graph so graph-level env flags are captured.
    os.environ["OPENAI_BASE_URL"] = base_url
    os.environ["OPENAI_API_KEY"] = api_key
    if disable_search:
        os.environ["DISABLE_SEARCH"] = "1"
        os.environ.setdefault("TAVILY_API_KEY", "disabled-for-benchmark")
    if enable_profiling:
        os.environ["LOCAL_TRACE"] = "1"
        if profile_log_dir is not None:
            os.environ["LOG_DIR"] = str(profile_log_dir)

    try:
        from langchain.chat_models import init_chat_model
        import react_agent.default_agents as default_agents
        import react_agent.graph as graph_module
        from react_agent.context import Context
    except Exception as exc:
        raise RuntimeError(f"E2E benchmark import failed: {exc}") from exc

    # Monkeypatch only inside benchmark process to inject extra_body(thinking=disabled)
    # without changing general runtime defaults.
    search_counter: Dict[str, int] = {"search_tool_calls": 0}
    thinking_probe: Dict[str, Any] = {}
    original_graph_loader = graph_module.load_chat_model
    original_agent_loader = default_agents.load_chat_model
    original_build_tavily_search = default_agents.build_tavily_search
    original_tavily_search = default_agents.tavily_search
    dummy_tool = _DummySearchTool(search_counter)

    def _bench_load_chat_model(fully_specified_name: str):
        if "/" not in fully_specified_name:
            raise ValueError(f"Invalid model spec: {fully_specified_name}")
        provider, model = fully_specified_name.split("/", 1)
        kwargs: Dict[str, Any] = {}
        if provider == "openai":
            kwargs["extra_body"] = {"thinking": {"type": thinking_type}}
            # Preserve explicit non-streaming behavior unless caller requests otherwise.
            kwargs["stream_usage"] = False
            if not thinking_probe:
                thinking_probe.update(
                    {
                        "provider": provider,
                        "model": model,
                        "extra_body": kwargs["extra_body"],
                    }
                )
        return init_chat_model(model, model_provider=provider, **kwargs)

    def _blocked_build_tavily_search(max_results: int):
        search_counter["search_tool_calls"] = search_counter.get("search_tool_calls", 0) + 1
        return dummy_tool

    try:
        graph_module.load_chat_model = _bench_load_chat_model
        default_agents.load_chat_model = _bench_load_chat_model
        if disable_search:
            default_agents.build_tavily_search = _blocked_build_tavily_search
            default_agents.tavily_search = dummy_tool

        t0 = time.perf_counter()
        res = await graph_module.graph.ainvoke(
            {"messages": [("user", question)]},  # type: ignore[arg-type]
            context=Context(model=f"openai/{model_id}", run_id=run_id),
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
    finally:
        graph_module.load_chat_model = original_graph_loader
        default_agents.load_chat_model = original_agent_loader
        default_agents.build_tavily_search = original_build_tavily_search
        default_agents.tavily_search = original_tavily_search

    final_chars = 0
    try:
        msgs = res.get("messages") or []
        if msgs:
            content = getattr(msgs[-1], "content", "")
            final_chars = len(content) if isinstance(content, str) else len(str(content))
    except Exception:
        final_chars = 0
    return E2ERunResult(
        elapsed_ms=elapsed_ms,
        search_tool_calls=search_counter.get("search_tool_calls", 0),
        final_message_chars=final_chars,
        thinking_probe=thinking_probe,
        run_id=run_id,
        trace_log_file=str((profile_log_dir / f"{run_id}.jsonl").resolve()) if enable_profiling and profile_log_dir else "",
    )


def _aggregate_metrics(values: List[float], prefix: str) -> Dict[str, Optional[float]]:
    return {
        f"{prefix}_p50": _pctl(values, 0.50),
        f"{prefix}_p90": _pctl(values, 0.90),
        f"{prefix}_p95": _pctl(values, 0.95),
    }


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError("No benchmark rows to write.")
    fieldnames: List[str] = []
    seen = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError("No benchmark rows to write.")
    display_cols = [
        "model_id",
        "provider_model",
        "raw_tokens_per_sec",
        "raw_latency_ms_p50",
        "raw_latency_ms_p90",
        "raw_latency_ms_p95",
        "e2e_latency_ms_p50",
        "e2e_latency_ms_p90",
        "e2e_latency_ms_p95",
        "temperature",
        "max_completion_tokens",
        "stream",
        "thinking_type",
        "disable_search",
        "runs",
    ]
    cols = [c for c in display_cols if any(c in row for row in rows)]
    lines = [
        "# Doubao Seed2 Speed Benchmark",
        "",
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for row in rows:
        vals = []
        for c in cols:
            v = row.get(c, "")
            if isinstance(v, float):
                vals.append(_fmt_num(v, 2))
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _row_from_runs(
    *,
    alias: str,
    provider_model: str,
    runs: int,
    raw_runs: List[RawRunResult],
    e2e_runs: List[E2ERunResult],
    temperature: float,
    max_completion_tokens: Optional[int],
    thinking_type: str,
    disable_search: bool,
) -> Dict[str, Any]:
    raw_latency = [r.elapsed_ms for r in raw_runs]
    raw_tps = [r.tokens_per_sec for r in raw_runs if r.tokens_per_sec is not None]
    e2e_latency = [r.elapsed_ms for r in e2e_runs]
    search_calls_total = sum(r.search_tool_calls for r in e2e_runs)

    row: Dict[str, Any] = {
        "model_id": alias,
        "provider_model": provider_model,
        "runs": runs,
        "raw_success_runs": len(raw_runs),
        "e2e_success_runs": len(e2e_runs),
        "raw_tokens_per_sec": _pctl([float(x) for x in raw_tps], 0.50),
        "raw_tokens_per_sec_p90": _pctl([float(x) for x in raw_tps], 0.90),
        "raw_tokens_per_sec_p95": _pctl([float(x) for x in raw_tps], 0.95),
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens or "",
        "stream": True,
        "thinking_type": thinking_type,
        "disable_search": int(bool(disable_search)),
        "e2e_search_tool_calls_total": search_calls_total,
    }
    row.update(_aggregate_metrics([float(x) for x in raw_latency], "raw_latency_ms"))
    row.update(_aggregate_metrics([float(x) for x in e2e_latency], "e2e_latency_ms"))
    return row


def _print_payload_probe(base_url: str, payload_probe: Mapping[str, Any]) -> None:
    host, path, scheme = _resolve_endpoint(base_url)
    probe = {
        "scheme": scheme,
        "host": host,
        "path": path,
        "payload": {
            "model": payload_probe.get("model"),
            "stream": payload_probe.get("stream"),
            "stream_options": payload_probe.get("stream_options"),
            "thinking": payload_probe.get("thinking"),
            "temperature": payload_probe.get("temperature"),
            "max_completion_tokens": payload_probe.get("max_completion_tokens"),
        },
    }
    print("[raw_payload_probe]", json.dumps(probe, ensure_ascii=False))


def _print_thinking_probe(thinking_probe: Mapping[str, Any]) -> None:
    if not thinking_probe:
        print("[e2e_thinking_probe] unavailable")
        return
    print("[e2e_thinking_probe]", json.dumps(thinking_probe, ensure_ascii=False))


def _clear_trace_jsonl(log_dir: Path) -> None:
    if not log_dir.exists():
        return
    for path in log_dir.glob("*.jsonl"):
        try:
            path.unlink()
        except OSError:
            continue


def _load_trace_analyzer() -> Any:
    script_path = Path(__file__).resolve().parents[1] / "ops" / "regression" / "analyze_trace.py"
    spec = importlib.util.spec_from_file_location("bench_trace_analyzer", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load trace analyzer from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Benchmark Doubao Seed2.0 raw + LangGraph E2E speed.")
    ap.add_argument(
        "--models",
        type=str,
        default="",
        help="Comma-separated alias=model pairs, e.g. 'pro=<id>,lite=<id>,mini=<id>'. "
        "If empty, reads DOUBAO_SEED2_{PRO,LITE,MINI}_MODEL env vars.",
    )
    ap.add_argument("--runs", type=int, default=3, help="Runs per model for raw and E2E benchmarks.")
    ap.add_argument("--question", type=str, default=DEFAULT_QUESTION, help="Unified E2E question input.")
    ap.add_argument("--raw-prompt", type=str, default=DEFAULT_RAW_PROMPT, help="Prompt used for raw chat benchmark.")
    ap.add_argument("--base-url", type=str, default="", help="Ark/OpenAI-compatible base_url (env fallback supported).")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-completion-tokens", type=int, default=512)
    ap.add_argument("--thinking-type", type=str, default="disabled", help="thinking.type sent to Ark/OpenAI-compatible APIs.")
    ap.add_argument("--raw-timeout", type=int, default=120, help="Raw benchmark HTTP timeout (seconds).")
    ap.add_argument("--e2e-timeout", type=int, default=300, help="E2E graph timeout per run (seconds).")
    ap.add_argument(
        "--disable-search",
        action="store_true",
        default=True,
        help="Force DISABLE_SEARCH=1 during E2E benchmark (default on).",
    )
    ap.add_argument(
        "--allow-search",
        dest="disable_search",
        action="store_false",
        help="Do not force DISABLE_SEARCH=1 (not recommended for speed benchmarking).",
    )
    ap.add_argument(
        "--out-csv",
        type=str,
        default="outputs/benchmarks/doubao_seed2_speed.csv",
        help="CSV summary output path.",
    )
    ap.add_argument(
        "--out-md",
        type=str,
        default="outputs/benchmarks/doubao_seed2_speed.md",
        help="Markdown summary output path.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved config + payload probes without sending requests or running graph.",
    )
    ap.add_argument(
        "--enable-profiling",
        action="store_true",
        help="Enable LOCAL_TRACE profiling and emit node-latency sidecar output.",
    )
    ap.add_argument(
        "--profile-log-dir",
        type=str,
        default="",
        help="Trace log directory used when --enable-profiling is set. "
        "Default: <out-csv-dir>/<out-csv-stem>_trace",
    )
    ap.add_argument(
        "--profile-sidecar",
        type=str,
        default="",
        help="Node-latency profile sidecar JSON path. "
        "Default: <out-csv-dir>/<out-csv-stem>_profile.json",
    )
    ap.add_argument(
        "--profile-window-size",
        type=int,
        default=20,
        help="Window size passed to trace analyzer when building sidecar summary.",
    )
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    models = _resolve_models(args.models)
    api_key = _resolve_api_key()
    base_url = _resolve_base_url(args.base_url)
    out_csv = Path(args.out_csv)
    out_md = Path(args.out_md)
    profile_log_dir: Optional[Path] = None
    profile_sidecar: Optional[Path] = None
    if args.enable_profiling:
        profile_log_dir = (
            Path(args.profile_log_dir)
            if args.profile_log_dir.strip()
            else out_csv.parent / f"{out_csv.stem}_trace"
        )
        profile_sidecar = (
            Path(args.profile_sidecar)
            if args.profile_sidecar.strip()
            else out_csv.parent / f"{out_csv.stem}_profile.json"
        )

    print(f"[config] models={','.join(a for a, _ in models)} runs={args.runs} disable_search={int(args.disable_search)}")
    print(f"[config] base_url={base_url}")
    print(f"[config] api_key_present=1 api_key_len={len(api_key)}")
    print(f"[config] enable_profiling={int(args.enable_profiling)}")
    if args.enable_profiling and profile_log_dir and profile_sidecar:
        print(f"[config] profile_log_dir={profile_log_dir}")
        print(f"[config] profile_sidecar={profile_sidecar}")

    probe_payload = _build_raw_payload(
        model=models[0][1],
        user_prompt=args.raw_prompt,
        temperature=args.temperature,
        max_completion_tokens=args.max_completion_tokens,
        thinking_type=args.thinking_type,
        stream=True,
    )
    _print_payload_probe(base_url, probe_payload)
    if args.dry_run:
        return

    if args.enable_profiling and profile_log_dir:
        profile_log_dir.mkdir(parents=True, exist_ok=True)
        _clear_trace_jsonl(profile_log_dir)

    rows: List[Dict[str, Any]] = []
    profile_runs: List[Dict[str, Any]] = []
    for alias, model_id in models:
        print(f"\n[model] {alias} -> {model_id}")
        raw_runs: List[RawRunResult] = []
        e2e_runs: List[E2ERunResult] = []
        payload_probes: List[Dict[str, Any]] = []

        for i in range(args.runs):
            rr = _run_raw_once(
                base_url=base_url,
                api_key=api_key,
                model=model_id,
                prompt=args.raw_prompt,
                temperature=args.temperature,
                max_completion_tokens=args.max_completion_tokens,
                thinking_type=args.thinking_type,
                timeout_secs=args.raw_timeout,
                payload_probe_out=payload_probes if i == 0 else None,
            )
            raw_runs.append(rr)
            print(
                f"  [raw {i+1}/{args.runs}] elapsed_ms={rr.elapsed_ms:.1f} "
                f"completion_tokens={rr.completion_tokens} tps={_fmt_num(rr.tokens_per_sec)}"
            )

        first_thinking_probe: Dict[str, Any] = {}
        for i in range(args.runs):
            run_id = f"bench_{alias}_{i+1:02d}_{uuid.uuid4().hex[:8]}"
            coro = _run_e2e_once(
                base_url=base_url,
                api_key=api_key,
                model_id=model_id,
                question=args.question,
                temperature=args.temperature,
                thinking_type=args.thinking_type,
                disable_search=args.disable_search,
                run_id=run_id,
                enable_profiling=args.enable_profiling,
                profile_log_dir=profile_log_dir,
            )
            er = asyncio.run(asyncio.wait_for(coro, timeout=args.e2e_timeout))
            e2e_runs.append(er)
            if args.enable_profiling:
                profile_runs.append(
                    {
                        "model_alias": alias,
                        "provider_model": model_id,
                        "run_index": i + 1,
                        "run_id": er.run_id,
                        "trace_log_file": er.trace_log_file,
                    }
                )
            if not first_thinking_probe and er.thinking_probe:
                first_thinking_probe = er.thinking_probe
            print(
                f"  [e2e {i+1}/{args.runs}] elapsed_ms={er.elapsed_ms:.1f} "
                f"search_tool_calls={er.search_tool_calls} final_chars={er.final_message_chars}"
            )

        if payload_probes:
            _print_payload_probe(base_url, payload_probes[0])
        _print_thinking_probe(first_thinking_probe)
        total_search_calls = sum(r.search_tool_calls for r in e2e_runs)
        print(f"[evidence] DISABLE_SEARCH={int(args.disable_search)} e2e_search_tool_calls_total={total_search_calls}")

        rows.append(
            _row_from_runs(
                alias=alias,
                provider_model=model_id,
                runs=args.runs,
                raw_runs=raw_runs,
                e2e_runs=e2e_runs,
                temperature=args.temperature,
                max_completion_tokens=args.max_completion_tokens,
                thinking_type=args.thinking_type,
                disable_search=args.disable_search,
            )
        )

    _write_csv(out_csv, rows)
    _write_markdown(out_md, rows)
    print(f"\n[done] csv={out_csv} md={out_md}")

    if args.enable_profiling and profile_log_dir and profile_sidecar:
        analyzer = _load_trace_analyzer()
        trace_summary = analyzer.summarize_log_dir(
            log_dir=profile_log_dir,
            window_size=max(1, int(args.profile_window_size)),
        )
        sidecar = {
            "profiling_enabled": True,
            "profile_log_dir": str(profile_log_dir.resolve()),
            "profile_window_size": int(args.profile_window_size),
            "runs_per_model": int(args.runs),
            "disable_search": int(bool(args.disable_search)),
            "models": [
                {"model_id": row.get("model_id"), "provider_model": row.get("provider_model")}
                for row in rows
            ],
            "trace_runs": profile_runs,
            "latency_profile": trace_summary.get("latency_profile", {}),
            "trace_summary": trace_summary,
        }
        profile_sidecar.parent.mkdir(parents=True, exist_ok=True)
        profile_sidecar.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[done] profile_sidecar={profile_sidecar}")

    # Console preview (first few columns) for quick copy-paste.
    for row in rows:
        print(
            "[row]",
            json.dumps(
                {
                    "model_id": row["model_id"],
                    "provider_model": row["provider_model"],
                    "raw_tokens_per_sec": row["raw_tokens_per_sec"],
                    "raw_latency_ms_p50": row["raw_latency_ms_p50"],
                    "raw_latency_ms_p90": row["raw_latency_ms_p90"],
                    "e2e_latency_ms_p50": row["e2e_latency_ms_p50"],
                    "e2e_latency_ms_p90": row["e2e_latency_ms_p90"],
                    "disable_search": row["disable_search"],
                    "thinking_type": row["thinking_type"],
                    "e2e_search_tool_calls_total": row["e2e_search_tool_calls_total"],
                },
                ensure_ascii=False,
            ),
        )


if __name__ == "__main__":
    main()
