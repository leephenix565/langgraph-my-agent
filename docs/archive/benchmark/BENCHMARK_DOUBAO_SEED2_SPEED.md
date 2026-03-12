# Doubao Seed2.0 Speed Benchmark Harness

## Purpose

This document describes the benchmark harness for comparing **Doubao Seed2.0** model variants (e.g. `pro` / `lite` / `mini`) on:

- raw OpenAI-compatible chat latency / throughput
- end-to-end LangGraph multi-agent latency (Router -> Manager -> Agents -> Summary)

The harness is implemented in `tools/bench_doubao_seed2_speed.py`.

## What it measures

For each model variant, the harness runs two measurements:

1. **Raw benchmark** (direct OpenAI-compatible HTTP request)
   - endpoint: `<base_url>/chat/completions`
   - `stream=true`
   - `stream_options.include_usage=true`
   - `thinking={"type":"disabled"}`
   - outputs raw latency percentiles and token throughput (`completion_tokens / wall_time`)

2. **E2E benchmark** (existing graph runtime)
   - runs the current LangGraph flow end-to-end with one fixed question
   - forces `DISABLE_SEARCH=1` during the benchmark process to avoid search noise
   - injects `thinking={"type":"disabled"}` into OpenAI-provider LangChain calls used by Router / Manager / Agents
   - outputs E2E latency percentiles

## Environment variables (no secrets in code)

Required (API key from env only):

- `ARK_API_KEY` **or** `OPENAI_API_KEY`

Model ids (recommended if using default `--models` behavior):

- `DOUBAO_SEED2_PRO_MODEL`
- `DOUBAO_SEED2_LITE_MODEL`
- `DOUBAO_SEED2_MINI_MODEL`

Optional:

- `ARK_OPENAI_BASE_URL` (fallback to `OPENAI_BASE_URL`, then default `https://ark.cn-beijing.volces.com/api/v3`)

## Repro command

```bash
python tools/bench_doubao_seed2_speed.py --runs 3
```

Optional explicit model mapping:

```bash
python tools/bench_doubao_seed2_speed.py \
  --models "pro=<ark_model_id_pro>,lite=<ark_model_id_lite>,mini=<ark_model_id_mini>" \
  --runs 3
```

## 2026-03-11 Qwen server benchmark run (OpenAI-compatible)

Target server model:

- `base_url=http://10.7.46.122:8000/v1`
- `model_id=Qwen3-30B-A3B-Instruct-2507-int8`
- `runs=3`

Routing guard used for this run:

- `ROUTER_MODEL` unset
- `ROUTER_OPENAI_BASE_URL` unset
- `ROUTER_OPENAI_API_KEY` unset
- E2E keeps benchmark default `DISABLE_SEARCH=1`

Dry-run command:

```bash
D:\AnacondaEnvs\cline_env\python.exe tools/bench_doubao_seed2_speed.py --models "qwen=Qwen3-30B-A3B-Instruct-2507-int8" --base-url "http://10.7.46.122:8000/v1" --runs 1 --dry-run
```

Real-run command used to finish 3 E2E runs:

```bash
D:\AnacondaEnvs\cline_env\python.exe tools/bench_doubao_seed2_speed.py --models "qwen=Qwen3-30B-A3B-Instruct-2507-int8" --base-url "http://10.7.46.122:8000/v1" --runs 3 --e2e-timeout 1200 --out-csv outputs/benchmarks/qwen30b_e2e_20260311.csv --out-md outputs/benchmarks/qwen30b_e2e_20260311.md
```

Notes:

- The default `--e2e-timeout 300` timed out on this model/server path; `--e2e-timeout 1200` was used for completion.
- This is execution/benchmark tuning only, not runtime business-logic change.

Outputs:

- `outputs/benchmarks/qwen30b_e2e_20260311.csv`
- `outputs/benchmarks/qwen30b_e2e_20260311.md`

Key result row (`qwen30b_e2e_20260311.csv`):

- `raw_success_runs=3`, `e2e_success_runs=3`
- `raw_tokens_per_sec(p50)=130.48`
- `raw_latency_ms_p50/p90/p95 = 275.91 / 276.73 / 276.83`
- `e2e_latency_ms_p50/p90/p95 = 538749.71 / 553109.67 / 554904.66`
- `e2e_search_tool_calls_total=0`

## Node-level latency profiling (sidecar)

To profile where E2E time is spent by node, enable LOCAL_TRACE profiling in the harness:

```bash
D:\AnacondaEnvs\cline_env\python.exe tools/bench_doubao_seed2_speed.py --models "qwen=Qwen3-30B-A3B-Instruct-2507-int8" --base-url "http://10.7.46.122:8000/v1" --runs 3 --e2e-timeout 1200 --out-csv outputs/benchmarks/qwen30b_e2e_20260311.csv --out-md outputs/benchmarks/qwen30b_e2e_20260311.md --enable-profiling
```

Profiling behavior:

- Keeps benchmark main table unchanged (CSV/MD still store raw+E2E totals).
- Writes trace JSONL under `<out-csv-dir>/<out-csv-stem>_trace/` by default.
- Writes sidecar summary JSON under `<out-csv-dir>/<out-csv-stem>_profile.json` by default.
- Sidecar includes `latency_profile` aggregated from `node_latency` events (`router`, `manager_broadcast`, `agent`, `manager_summary`, `summary`, `finalize_summary`) and per-agent latency stats.
- Sidecar trace summary now also includes:
  - `malformed_jsonl` (bad-line counts/samples for trace integrity checks)
  - `error_summary` (grouped by node/agent/event/status code/error signature for 5xx triage)

Optional explicit paths:

```bash
--profile-log-dir outputs/benchmarks/qwen30b_e2e_20260311_trace
--profile-sidecar outputs/benchmarks/qwen30b_e2e_20260311_profile.json
```

## Outputs

By default the harness writes:

- `outputs/benchmarks/doubao_seed2_speed.csv`
- `outputs/benchmarks/doubao_seed2_speed.md`

Each row records:

- `model_id` (alias: `pro` / `lite` / `mini`)
- `provider_model` (actual Ark model id)
- `raw_tokens_per_sec` (p50)
- `raw_latency_ms_p50/p90/p95`
- `e2e_latency_ms_p50/p90/p95`
- fixed benchmark params (`temperature`, `max_completion_tokens`, `stream`, `thinking_type`, `disable_search`)

## Fixed benchmark controls (default)

- `temperature=0.0`
- `stream=true`
- `thinking_type=disabled`
- `DISABLE_SEARCH=1` (inside benchmark process unless `--allow-search`)

## Evidence / sanity checks

The harness prints:

- `[raw_payload_probe]` with sanitized request payload fields (includes `thinking` and `stream_options`)
- `[e2e_thinking_probe]` showing the LangChain OpenAI `extra_body` override used for E2E
- `[evidence] DISABLE_SEARCH=1 e2e_search_tool_calls_total=...` to confirm search calls stay at zero during E2E runs

No API key values are printed.

## Notes

- The benchmark harness is for comparative speed measurement; it does not change runtime schema or graph topology.
- `DISABLE_SEARCH` is benchmark-oriented and keeps default runtime behavior unchanged when not set.
