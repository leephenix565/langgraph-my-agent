# LangGraph Layered Multi-Agent System

[![CI](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml)
[![Open in - LangGraph Studio](https://img.shields.io/badge/Open_in-LangGraph_Studio-00324d.svg?logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4NS4zMzMiIGhlaWdodD0iODUuMzMzIiB2ZXJzaW9uPSIxLjAiIHZpZXdCb3g9IjAgMCA2NCA2NCI+PHBhdGggZD0iTTEzIDcuOGMtNi4zIDMuMS03LjEgNi4zLTYuOCAyNS43LjQgMjQuNi4zIDI0LjUgMjUuOSAyNC41QzU3LjUgNTggNTggNTcuNSA1OCAzMi4zIDU4IDcuMyA1Ni43IDYgMzIgNmMtMTIuOCAwLTE2LjEuMy0xOSAxLjhtMzcuNiAxNi42YzIuOCAyLjggMy40IDQuMiAzLjQgNy42cy0uNiA0LjgtMy40IDcuNkw0Ny4yIDQzSDE2LjhsLTMuNC0zLjRjLTQuOC00LjgtNC44LTEwLjQgMC0xNS4ybDMuNC0zLjRoMzAuNHoiLz48cGF0aCBkPSJNMTguOSAyNS42Yy0xLjEgMS4zLTEgMS43LjQgMi41LjkuNiAxLjcgMS44IDEuNyAyLjcgMCAxIC43IDIuOCAxLjYgNC4xIDEuNCAxLjkgMS40IDIuNS4zIDMuMi0xIC42LS42LjkgMS40LjkgMS41IDAgMi43LS41IDIuNy0xIDAtLjYgMS4xLS44IDIuNi0uNGwyLjYuNy0xLjgtMi45Yy01LjktOS4zLTkuNC0xMi4zLTExLjUtOS44TTM5IDI2YzAgMS4xLS45IDIuNS0yIDMuMi0yLjQgMS41LTIuNiAzLjQtLjUgNC4yLjguMyAyIDEuNyAyLjUgMy4xLjYgMS41IDEuNCAyLjMgMiAyIDEuNS0uOSAxLjItMy41LS40LTMuNS0yLjEgMC0yLjgtMi44LS44LTMuMyAxLjYtLjQgMS42LS41IDAtLjYtMS4xLS4xLTEuNS0uNi0xLjItMS42LjctMS43IDMuMy0yLjEgMy41LS41LjEuNS4yIDEuNi4zIDIuMiAwIC43LjkgMS40IDEuOSAxLjYgMi4xLjQgMi4zLTIuMy4yLTMuMi0uOC0uMy0yLTEuNy0yLjUtMy4xLTEuMS0zLTMtMy4zLTMtLjUiLz48L3N2Zz4=)](https://langgraph-studio.vercel.app/templates/open?githubUrl=https://github.com/langchain-ai/react-agent)

This repository is a layered multi-agent orchestration system built on [LangGraph](https://github.com/langchain-ai/langgraph) `StateGraph`. The current runtime entrypoint is `langgraph.json -> src/react_agent/graph.py:graph`, and the mainline repo scope centers on `src/react_agent/`, `config/agents/`, and the supporting regression / training / observability tooling.

![Graph view in LangGraph studio UI](./static/studio_ui.png)

## Current Engineering Snapshot

- Runtime entry: `langgraph.json -> src/react_agent/graph.py:graph`
- Main runtime chain: `router_node -> manager_broadcast -> agent nodes -> manager_summary -> (_run_final_summary / finalize_summary) -> optional memory_update -> __end__`
- a01 contract role: `a01_cio_orchestrator` can emit a contract, but Manager only consumes it after runtime validation; otherwise dispatch falls back to normal assignment templates.
- Optional capabilities boundary: `thread_summary`, `messages window`, `results pools`, `stable consume`, and `checkpointer` are env-gated features, not default-always-on behavior.
- Studio schema compatibility: `AgentOutput` now uses a schema-generatable dict-shaped type surface so `/assistants/{assistant_id}/schemas` can render without changing runtime result handling.
- FF-1 mainline bundle seam: final summary now records a separate `multi_agent_bundle` sidecar in graph state so later baseline/judge/fusion work has an insertion seam without changing current user-visible output.
- FF-2A baseline sidecar scaffold: an isolated `baseline_sidecar` shadow branch can write `baseline_status` and `baseline_bundle`, but it is not part of L1-L4, does not enter a01 contract dispatch, and does not change the current final answer source.
- FF-2B Gemini baseline hardening: when the baseline provider is `google_genai/...`, the baseline sidecar now uses the Gemini Developer API Google Search grounding path and records grounding/search receipts in `baseline_bundle.search_meta`. Generic providers remain scaffold-only baselines.
- FF-2B.1 Gemini grounding JSON compatibility: Gemini grounding/search tool use cannot be combined with `response_mime_type="application/json"`, so the Gemini baseline path now relies on prompt-constrained JSON plus local parsing of `response.text`.
- FF-3A Judge-ready fan-in seam: mainline readiness is now decoupled from final emit via `mainline_status` and `mainline_emit_payload`, and the baseline shadow branch now reaches a branch-safe `fusion_gate` before the existing mainline answer is emitted.
- FF-3B Fusion Judge shadow mode: `fusion_gate` now routes through a shadow-only `fusion_judge_shadow` that writes `judge_status` and `fusion_verdict`, while the final visible answer still stays on the mainline path.
- FF-4A Fusion Writer shadow + source-neutral emit seam: `fusion_verdict` is now writer-ready, `fusion_writer_shadow` writes `writer_status` / `writer_output` / `final_emit_payload`, and the closeout path now runs through a source-neutral `final_emit` seam while the emitted answer still stays on the mainline path.
- FF-4B final source switch: `final_emit` now supports `"mainline" | "baseline" | "fused"` as real emit sources behind `enable_fair_fusion_source_switch`, records the actual `emitted_bundle`, and still defaults to the current mainline-visible behavior when the switch flag is off.
- FF-5B fusion regression / eval / gate: deterministic, network-free fusion harnessing now lives under `ops/regression/fusion/`, emits `fusion_runs.jsonl` / `fusion_metrics.json` / `fusion_gate.json`, and keeps tracing noise classification separate from business failures.
- Current stage: the repo is closer to `structure-stable` than `quality-stable`; runtime structure and protocol closure are stronger than environment, training, and documentation closure.

## Quickstart (30s)

1) Create env file:
   - Bash: `cp .env.example .env`
   - PowerShell: `Copy-Item .env.example .env`
2) Fill required keys in `.env`:
   - `TAVILY_API_KEY` is required before importing `react_agent.graph` / `graph_app`.
   - Keep LangSmith tracing commented out for the default local dev baseline unless you explicitly want remote tracing.
   - For a Gemini-grounded baseline sidecar, set `GOOGLE_API_KEY`, keep `GOOGLE_GENAI_USE_VERTEXAI=false`, and set `BASELINE_MODEL=google_genai/gemini-3-pro-preview` (or another `google_genai/<gemini-model>` value).
3) Run minimal demo: `conda run -n cline_env python demo_layered_run.py`
4) (Optional, Windows recommended) Run unit tests: `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/`

Docs:
- [Project Overview](docs/PROJECT_OVERVIEW.md): current engineering snapshot and reusable short project description
- [SYSTEM_MAP](docs/SYSTEM_MAP.md): runtime / benchmark / training / eval command source
- [Docs Index](docs/INDEX.md): document authority map and reading order

If narrative wording conflicts with runtime behavior, prefer `src/react_agent/*`, focused tests, and the S0 docs referenced from `docs/INDEX.md`.

## Environment Baseline (Local/Codex)

- Python requirement: `>=3.11,<4.0` (from `pyproject.toml`).
- Official local environment: conda env `cline_env`.
- Do not use bare `python` as a validation entrypoint. On this machine it can fall back to system Python 3.7 and cause false failures.
- `TAVILY_API_KEY` is an import-time prerequisite because `src/react_agent/tools.py` instantiates the Tavily tool at module import.
- Local trace defaults to `LOCAL_TRACE=0`; when enabled, [run_logger.py](./src/react_agent/run_logger.py) writes JSONL under `log/<YYYYMMDD>/`.
- Remote LangSmith tracing is not part of the default local dev baseline. Treat `LANGSMITH_TRACING=true` as explicit opt-in.
- `LOCAL_TRACE` and LangSmith tracing are separate systems: `LOCAL_TRACE` writes local JSONL only, while LangSmith tracing uploads run metadata remotely.
- `multi_agent_bundle` is a final-summary sidecar only. It does not participate in `analyst_results`, `ephemeral_results`, a01 contract dispatch, or agent `shared_context`.
- `baseline_bundle` is an isolated shadow sidecar only. It does not participate in `layer_plan`, `analyst_results`, `ephemeral_results`, a01 contract dispatch, or the current final `messages` emit path.
- `enable_fair_fusion` defaults to `False`; FF-2A is scaffold-only and does not yet enable judge/writer behavior or final answer switching.
- FF-3A keeps the final visible answer on the mainline path:
  - `mainline_status="ready"` means the mainline bundle and emit payload have been staged, not that the turn has completed.
  - `is_last_step=True` is still reserved for the actual emitted final answer and downstream `memory_update`.
  - `final_answer_source` is no longer a pure FF-3A-only field; later FF-4B switching can emit `mainline`, `baseline`, or `fused`, but FF-3A itself only introduced the seam and readiness split.
- FF-3B shadow-judge note:
  - `judge_status` and `fusion_verdict` are shadow-compare sidecars only; they do not change the emitted answer path.
  - `fusion_judge_shadow` compares `multi_agent_bundle` against `baseline_bundle` and stores a JSON verdict before the writer/final-emit seam.
- FF-4A shadow-writer note:
  - `writer_status`, `writer_output`, and `final_emit_payload` are shadow-sidecar state only; the writer does not write `messages` or change `final_answer_source`.
  - `final_emit` is now the source-neutral closeout seam, but FF-4A still maps it to the staged mainline answer and keeps `final_answer_source="mainline"`.
  - FF-4B later enabled guarded source switching on top of this seam; FF-4A itself is still the writer-shadow-only stage.
- FF-4B final-source-switch note:
  - `enable_fair_fusion_source_switch` defaults to `False`; with the default off, the final visible answer still emits from mainline and `final_answer_source` still ends as `"mainline"`.
  - When enabled, `final_emit` can emit from `mainline`, `baseline`, or `fused` based on the staged `final_emit_payload`.
  - `emitted_bundle` records the actual final emitted bundle, while `multi_agent_bundle` remains the canonical A-line mainline bundle.
- FF-5B deterministic regression / eval / gate note:
  - `ops/regression/fusion/run_fusion_regression.py` runs a deterministic scenario catalog and writes `ops/regression/fusion/out/fusion_runs.jsonl`.
  - `ops/regression/fusion/eval_fusion_outputs.py` aggregates `fusion_runs.jsonl` into `fusion_metrics.json`.
  - `ops/regression/fusion/gate_fusion_outputs.py` converts `fusion_metrics.json` into `fusion_gate.json`.
  - The default gate is network-free and does not depend on live provider calls.
  - LangSmith 403 and local trace issues are classified as `trace_noise`; they are not counted as business failures in the default FF-5B gate.
- Gemini grounding baseline note:
  - `BASELINE_MODEL=google_genai/<gemini-model>` switches the baseline sidecar onto the Gemini Developer API path.
  - `GOOGLE_API_KEY` is the credential used for that path; keep `GOOGLE_GENAI_USE_VERTEXAI=false` for Developer API usage.
  - On the Gemini path, the sidecar bypasses `baseline_openai_base_url` / `baseline_openai_api_key` and uses the direct Gemini SDK client.
  - Gemini grounding/search tool use cannot be combined with `response_mime_type="application/json"`.
  - The current FF-2B.1 compatibility fix keeps JSON constrained by prompt and parses `response.text` locally instead of using provider-side structured JSON mode.
  - When the baseline provider is not `google_genai`, the sidecar remains a generic provider scaffold and `search_meta` only records request intent rather than a provider-native search receipt.

Interpreter self-check:
- `conda run -n cline_env python --version`
- `conda run -n cline_env python -c "import sys; print(sys.executable)"`

Minimal import smoke (placeholder key only, do not commit real keys):
- PowerShell: `$env:TAVILY_API_KEY="test-key"; conda run -n cline_env python -c "from react_agent import graph_app; print(graph_app is not None)"`

Local LangSmith note:
- If your existing untracked `.env` still contains `LANGSMITH_TRACING=true`, local `langgraph dev` may continue to emit remote ingest warnings until that local file is aligned with the opt-in baseline above.

## Fusion Regression / Eval / Gate

Deterministic FF-5B regression lives under `ops/regression/fusion/`. The default harness is network-free, does not call live providers, and treats tracing noise separately from business failures.

Minimal run sequence:

```bash
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.run_fusion_regression
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.eval_fusion_outputs
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.gate_fusion_outputs
```

Artifacts:
- `ops/regression/fusion/out/fusion_runs.jsonl`
- `ops/regression/fusion/out/fusion_metrics.json`
- `ops/regression/fusion/out/fusion_gate.json`

Optional live/provider smoke can still be run manually, but it is intentionally outside the default FF-5B gate.

Windows pytest execution note:
- Recommended command uses `--no-capture-output` to avoid conda output re-encoding (`UnicodeEncodeError(gbk)` in `conda run` capture path).
- This is an execution-layer workaround, not a project logic fix.
- Verification-only fallback (do not treat as new baseline): `D:\AnacondaEnvs\cline_env\python.exe -m pytest tests/unit_tests/`

## Repository Focus (Mainline Snapshot)

- Mainline runtime scope: `src/react_agent/`, `config/agents/`, `langgraph.json`, `pyproject.toml`, `react_agent/`, `sitecustomize.py`.
- Offline data-pipeline scripts are grouped under `ops/data_pipeline/`.
- Archived non-mainline docs/materials are grouped under `docs/archive/` and `assets/reference/`.
- When collaborating on runtime changes, prioritize the mainline scope + S0 docs from `docs/INDEX.md`.

## How to customize

1. **Add new tools**: Extend the agent's capabilities by adding new tools in [tools.py](./src/react_agent/tools.py). These can be any Python functions that perform specific tasks.
2. **Select a different model**: We default to `deepseek/deepseek-chat`. You can select a compatible chat model using `provider/model-name` via runtime context. Example: `openai/gpt-4-turbo-preview`.
3. **Customize the prompt**: We provide a default system prompt in [prompts.py](./src/react_agent/prompts.py). You can easily update this via context in the studio.

You can also extend the current runtime by:

- Modifying the agent's reasoning process in [graph.py](./src/react_agent/graph.py).
- Adjusting the ReAct loop or adding additional steps to the agent's decision-making process.

## Development

While iterating on your graph, you can edit past state and rerun your app from past states to debug specific nodes. Local changes will be automatically applied via hot reload. Try adding an interrupt before the agent calls tools, updating the default system message in `src/react_agent/context.py` to take on a persona, or adding additional nodes and edges!

Follow up requests will be appended to the same thread. You can create an entirely new thread, clearing previous history, using the `+` button in the top right.

You can find the latest (under construction) docs on [LangGraph](https://github.com/langchain-ai/langgraph) here, including examples and other references. Using those guides can help you pick the right patterns to adapt here for your use case.

[^1]: https://python.langchain.com/docs/concepts/#tools
