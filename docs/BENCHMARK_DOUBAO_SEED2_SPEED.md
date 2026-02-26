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
