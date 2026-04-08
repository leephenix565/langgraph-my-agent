# LangGraph Layered Multi-Agent System

[![Quality Gate](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml)

This repository is a layered multi-agent orchestration system built on LangGraph `StateGraph`. The runtime entrypoint is `langgraph.json -> src/react_agent/graph.py:graph`, and the current product shell lives under `apps/web/` on top of a Python public adapter in `src/react_agent/public_*.py`.

## Current Snapshot

- Runtime mainline: `router_node -> manager_broadcast -> agent nodes -> manager_summary -> (_run_final_summary / finalize_summary) -> optional memory_update -> __end__`
- Public product surfaces:
  - Chat: live
  - Settings: live read-only
  - Agents: live read-only
- Public transcript boundary:
  - one visible assistant persona only
  - workflow stays an inspector
  - `text` remains the canonical transcript / store / replay truth
- Assistant answer rendering:
  - `answerCard.answer` is now rendered as safe client-side Markdown in the web shell
  - this is a presentation-layer change only; it does not change the Python public adapter contract or transcript truth
- Typed input boundary:
  - `structuredInput` is additive only
  - pasted `materials` and additive `urlReferences` must still compile into canonical transcript text
- Streaming boundary:
  - sync `POST /api/threads/{thread_id}/messages` remains supported and unchanged
  - additive `POST /api/threads/{thread_id}/messages/stream` now returns safe NDJSON workflow events
  - workflow progress is client-visible but not persisted; only the final assistant turn remains transcript / store / replay truth
- Current phase: `Phase WS-1：workflow-first streaming`
- Current positioning: the repo is adding a safe workflow-first streaming seam on top of the quality-closure baseline without changing transcript truth or runtime business semantics

## Quickstart

1. Copy `.env.example` to `.env`.
2. Fill only the keys you actually need for your local workflow.
3. Use the documented local baseline:
   - Python: conda env `cline_env`
   - Frontend: `node` + `npm` under `apps/web/`
4. Minimal local demo:

```powershell
conda run --no-capture-output -n cline_env python demo_layered_run.py
```

## Unified Quality Entry

The repo keeps one repo-level quality command source of truth:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
```

Available modes:

- `mainline`
- `static`
- `unit`
- `public-api`
- `graph-smoke`
- `frontend`
- `fusion-gate`

`mainline` now runs:

1. `ruff`
2. `mypy`
3. `codespell`
4. `pytest tests/unit_tests`
5. `pytest tests/integration_tests/test_public_api.py`
6. `pytest tests/integration_tests/test_graph.py`
7. `npm --prefix apps/web run build`
8. `npm --prefix apps/web run test`
9. deterministic fusion regression / eval / gate

The blocking static step currently targets the maintained quality-closure surface:

- `scripts/quality/`
- active Python integration tests
- current authority docs / README / `AGENTS.md`

Examples:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode public-api
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode graph-smoke
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode frontend
```

Convenience wrappers remain in `Makefile`, but they are wrappers only:

```powershell
make quality
make quality_static
make quality_unit
make quality_public_api
make quality_graph_smoke
make quality_frontend
make quality_fusion_gate
make quality_provider_smoke
```

## Active Test Surface

The active blocking test surface is now explicit:

- Python unit tests: `tests/unit_tests`
- Public adapter integration: `tests/integration_tests/test_public_api.py`
- Runtime graph smoke: `tests/integration_tests/test_graph.py`
- Frontend active gate entry: `apps/web/src/test/smoke.tsx`

Legacy frontend fixtures are kept for reference only and now use a `.legacy.tsx` suffix:

- `apps/web/src/test/app.smoke.legacy.tsx`
- `apps/web/src/test/workflow.smoke.legacy.tsx`

They are not part of the default frontend gate.

## Optional Provider / Live Smoke

Provider/live smoke is scripted, but it remains optional and non-blocking for the default quality gate.

Command:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_provider_live_smoke.py --out-dir ops/regression/provider/out
```

Artifact:

- `ops/regression/provider/out/provider_live_smoke.json`

Behavior:

- if provider/search/checkpointer prerequisites are not satisfied, the script writes a `skipped` artifact and exits `0`
- if the environment is ready, it runs the live public seam:
  - `GET /api/health`
  - `POST /api/threads`
  - `POST /api/threads/{id}/messages`
- if the real live invocation fails, the script writes a failure artifact and exits non-zero

Important boundary:

- this script is not part of the default blocking gate
- URL references remain references only; the smoke does not fetch URLs, parse HTML, upload files, or change runtime business semantics

Current local evidence snapshot:

- latest artifact status: `skipped`
- current missing prerequisites in this environment:
  - provider credentials (`OPENAI_API_KEY`, `ROUTER_OPENAI_API_KEY`, `BASELINE_OPENAI_API_KEY`, or `GOOGLE_API_KEY`)
  - search credential (`TAVILY_API_KEY`)
  - runtime import/readiness is still unavailable in the current environment
- this remains an acceptable residual because provider/live smoke is scripted evidence, but still optional and non-blocking by design

## CI Workflows

Mainline blocking workflow:

- file: `.github/workflows/unit-tests.yml`
- workflow name: `Quality Gate`
- blocking jobs:
  - `python-static`
  - `python-unit`
  - `public-adapter-integration`
  - `graph-smoke`
  - `frontend`
  - `fusion-gate`

Optional provider/live smoke workflow:

- file: `.github/workflows/integration-tests.yml`
- workflow name: `Optional Provider Live Smoke (Non-Blocking)`
- trigger: scheduled or manual only
- not part of the default blocking gate

## Deterministic Fusion Gate

The deterministic FF-5B fusion regression / eval / gate chain is part of the mainline quality entry.

Underlying commands:

```powershell
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.run_fusion_regression --out-dir ops/regression/fusion/out
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.eval_fusion_outputs --in ops/regression/fusion/out/fusion_runs.jsonl --out ops/regression/fusion/out/fusion_metrics.json
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.gate_fusion_outputs --in ops/regression/fusion/out/fusion_metrics.json --out ops/regression/fusion/out/fusion_gate.json
```

Artifacts:

- `ops/regression/fusion/out/fusion_runs.jsonl`
- `ops/regression/fusion/out/fusion_metrics.json`
- `ops/regression/fusion/out/fusion_gate.json`

## Environment Baseline

- Python requirement: `>=3.11,<4.0`
- Local baseline: conda env `cline_env`
- Frontend baseline: `npm`, not `pnpm` or `yarn`
- Dev quality tools should be installed alongside the project when you intend to run `--mode static`
- `TAVILY_API_KEY` remains an import-time prerequisite for `react_agent.graph`
- replay continuity remains weaker than persistent graph continuity and must stay labeled that way
- `state["messages"]` is not the public transcript

## Product Boundary

What this repo does in the current phase:

- keeps a single assistant persona in the public transcript
- keeps workflow as an answer-level inspector
- renders assistant answer Markdown on the client while keeping the answer payload as plain text from the backend
- keeps the chat view inside a readable width and contains wide Markdown blocks inside the assistant card instead of letting them push the page wider
- adds a workflow-first NDJSON streaming seam that emits only safe public events and keeps the old sync seam available
- keeps `structuredInput` additive and honest
- keeps `materials` and `urlReferences` compiled into canonical transcript text
- keeps `/settings` and `/agents` read-only

What WS-1 still does not do:

- no new product feature expansion
- no runtime business-semantic change
- no file upload
- no URL fetch / HTML parsing / snapshot persistence
- no SSE
- no token streaming
- no raw graph-event or chain-of-thought streaming

## Docs

- [Project Overview](docs/PROJECT_OVERVIEW.md)
- [System Map](docs/SYSTEM_MAP.md)
- [Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md)
- [Docs Index](docs/INDEX.md)
- [Router SFT Runbook](docs/RUNBOOK_ROUTER_SFT.md)
- [Changelog](docs/CHANGELOG.md)

If documentation conflicts with runtime behavior, prefer `src/react_agent/*`, focused tests, and the S0 docs referenced by `docs/INDEX.md`.
