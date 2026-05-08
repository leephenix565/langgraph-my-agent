# LangGraph Layered Multi-Agent System

[![Quality Gate](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml)

This repository is a layered multi-agent orchestration system built on LangGraph `StateGraph`. The runtime entrypoint is `langgraph.json -> src/react_agent/graph.py:graph`, and the current product shell lives under `apps/web/` on top of a Python public adapter in `src/react_agent/public_*.py`.

## Current Snapshot

- Runtime entry: `langgraph.json -> src/react_agent/graph.py:graph`
- Runtime mainline topology: `__start__ -> router`, then `router -> manager_broadcast` and `router -> baseline_sidecar`; agent nodes return to `manager_summary`; final closeout runs through `manager_summary/finalize_summary -> fusion_gate -> fusion_judge_shadow -> fusion_writer_shadow -> final_emit -> (memory_update | __end__)`
- Default answer path: Fair Fusion baseline/judge/writer sidecars exist in the runtime, but `Context.enable_fair_fusion=False` and `Context.enable_fair_fusion_source_switch=False` by default, so the visible answer still comes from the mainline bundle unless those flags are explicitly enabled
- Baseline sidecar default config: `.env.example` now points the isolated Fair Fusion baseline at DeepSeek V4 Pro through the OpenAI-compatible path (`BASELINE_MODEL=openai/deepseek-v4-pro`, `BASELINE_OPENAI_BASE_URL=https://api.deepseek.com`); the existing `google_genai/...` Gemini grounding code path remains available only when explicitly configured
- RP-1A / RP-2C route-prior shadows:
  - `router_node` now also hosts an internal embedding-first semantic-retrieval shadow seam before the formal Router invoke
  - it is shadow-only, fail-open, and does not alter formal Router prompt shape, parse semantics, committed state, or public workflow projection
  - missing or broken embedding config disables the seam privately and does not change `/api/health`
  - RP-2C can add private reliability shadow and post-router comparison trace when `ROUTE_PRIOR_RELIABILITY_ENABLED=1`; default env keeps current Router behavior unchanged
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
- Current phase position:
  - frontend/runtime integration: `Phase F3`
  - repo-level closure: `Phase QS-2`
  - `Phase WS-1` workflow-first streaming is a landed seam, not the current repo phase label
- Current positioning: the repo is hardening the public-adapter/web mainline, continuity/readiness surfaces, and authority-doc truth without changing transcript truth or LangGraph runtime business semantics

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

## Local Clean Python Environment

For stable local and Codex validation on Windows, prefer a clean Python 3.11 environment when the documented `cline_env` is polluted, unavailable through `conda run`, or not active in the current shell. The mainline Python dependency truth is `pyproject.toml`.

Install the mainline runtime and static-tooling surface into the clean environment:

```powershell
python -m pip install -e ".[dev]"
python -m pip install pytest
```

`.[dev]` installs the static quality tools used by `scripts/quality/run_quality.py --mode static`: `ruff`, `mypy`, and `codespell`. Install `pytest` separately for local test gates unless your dependency-group tooling explicitly installs the repo's dev dependency group.

Do not install `requirements-hf.txt` or `requirements-train.txt` into the default mainline environment. They are optional non-mainline dependency sets for HF/model-side and training/fine-tuning workflows.

Windows example path:

```powershell
$env:REACT_AGENT_ENV = "D:\AnacondaEnvs\langgraph_agent_py311"
$env:PYTHONNOUSERSITE = "1"
$env:TEMP = "$env:REACT_AGENT_ENV\pip-tmp"
$env:TMP = "$env:REACT_AGENT_ENV\pip-tmp"
$env:MYPY_CACHE_DIR = "$env:REACT_AGENT_ENV\mypy-cache"
$env:Path = "$env:REACT_AGENT_ENV;$env:REACT_AGENT_ENV\Scripts;$env:REACT_AGENT_ENV\Library\bin;$env:Path"
```

The `PYTHONNOUSERSITE=1` setting prevents user-site packages from contaminating validation. The env-local `TEMP`, `TMP`, and `MYPY_CACHE_DIR` settings avoid unreliable C-drive temp space or repo-local cache permissions on Windows.

Validated local commands:

```powershell
& "$env:REACT_AGENT_ENV\python.exe" scripts\quality\run_quality.py --mode static
& "$env:REACT_AGENT_ENV\python.exe" -m pytest tests\unit_tests\test_route_profile_registry_rp1a.py tests\unit_tests\test_route_prior_embeddings_rp1a.py tests\unit_tests\test_route_prior_rp1a.py -q
& "$env:REACT_AGENT_ENV\python.exe" -m pytest tests\integration_tests\test_graph.py -q
& "$env:REACT_AGENT_ENV\python.exe" -m pytest tests\integration_tests\test_public_api.py -q
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

## RP-1B / RP-2A / RP-2B / RP-2C Route-Prior Work

RP-1B adds an optional offline validation harness for the RP-1A route-prior shadow seam. RP-2A extends the same tooling with `route_eval_label_v0`, legacy `expected_agents` compatibility, must/critical/nice-to-have/negative labels, safe/effective recall, precision/F1/Jaccard, cost, high-confidence wrong, ECE/Brier, and label-source grouped metrics. RP-2B adds optional internal route profile cards plus deterministic reliability scoring helpers. RP-2C optionally wires those helpers into `router_node` as private runtime trace and post-router comparison only.

Minimal live run, requiring a local OpenAI-compatible embeddings endpoint:

```powershell
python -m ops.regression.route_prior.run_route_prior_eval --dataset ops/regression/route_prior/fixtures/rp1b_labeling_template.jsonl --out-dir ops/regression/route_prior/out --max-items 10 --prewarm-endpoint
python -m ops.regression.route_prior.eval_route_prior_outputs --runs ops/regression/route_prior/out/route_prior_runs.jsonl --out ops/regression/route_prior/out/route_prior_metrics.json
```

Local RP-1A embedding experiments can use the project-external Qwen service
documented in `docs/SYSTEM_MAP.md`: `Qwen/Qwen3-Embedding-0.6B` served on
`http://127.0.0.1:8001/v1/embeddings`. It is not repo runtime code; keep the
matching `ROUTE_PRIOR_*` env values local and do not add them to `.env.example`.

Optional RP-2B reliability-card artifact generation:

```powershell
python -m ops.regression.route_prior.run_route_prior_eval --dataset ops/regression/route_prior/fixtures/rp2_labeling_template.jsonl --out-dir ops/regression/route_prior/out --enable-rarp-scoring --profile-cards-dir config/route_profiles --reliability-table ops/regression/route_prior/out/route_reliability_table.json
```

Optional RP-2C runtime trace is private and default-off:

```powershell
$env:ROUTE_PRIOR_RELIABILITY_ENABLED="1"
$env:LOCAL_TRACE="1"
```

Optional RP-3A-1 network-free Router advisory A/B parser dry-run:

```powershell
python -m ops.regression.route_prior.run_router_advisory_ab --dataset ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl --out-dir ops/regression/route_prior/out --max-items 20 --mode network-free
```

This harness does not call an LLM and does not change runtime Router behavior.

Optional RP-3A-3 Router advisory prediction artifact generation:

```powershell
python -m ops.regression.route_prior.generate_router_advisory_predictions --dataset ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl --out ops/regression/route_prior/out/router_advisory_predictions_dry_run.jsonl --summary-out ops/regression/route_prior/out/router_advisory_predictions_dry_run_summary.json --max-items 20 --mode dry-run
```

Default `dry-run` mode is network-free and writes enriched prediction JSONL for the replay harness. Explicit `--mode live` is optional and writes skipped/error summaries when provider prerequisites are missing or fail.

Optional DeepSeek teacher-proxy labeling for offline experiments:

```powershell
python -m ops.regression.route_prior.generate_deepseek_teacher_labels --input ops/regression/route_prior/out/rp1b_manual_draft_20.jsonl --out ops/regression/route_prior/out/rp1b_deepseek_teacher_v1_20.jsonl --max-items 20
```

DeepSeek-generated records use `label_source="deepseek_teacher_v1"`. They are model-generated teacher-proxy labels, not human/manual gold labels, and can only support proxy-quality observations such as Qwen route-prior alignment with that teacher.

Most checked-in fixtures are labeling templates. `draft_for_human_review` labels are not final quality evidence; quality conclusions require human-reviewed `manual` or `manual_gold` labels. RP-3G adds `ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl` as a GPT Pro assisted, project-owner accepted 20-case smoke fixture only; it is not an initial or promotion-quality dataset. Route-prior offline eval is not part of the default blocking gate unless explicitly promoted later. RP-2C is env-gated, trace-only, fail-open, and does not alter Router prompt/parser semantics, committed routing outputs, State schema, public workflow, frontend behavior, `/api/agents`, or `/api/health`. RP-3A-1 adds an offline network-free parser dry-run harness only; RP-3A-2B hardens optional prediction JSONL metadata replay for that harness; RP-3A-3 adds an optional prediction artifact generator with default network-free dry-run and explicit optional live mode; RP-3A-4D hardens the label-stub advisory with per-layer agent groups after a wrong-layer smoke regression; RP-3A-5 adds offline `provided_artifact` / `rarp_shadow` advisory-source experiments for the optional prediction-generator path only; RP-3A-5B makes missing, disabled, low-confidence, or empty-card provided artifacts explicit noop/no-advisory cases; RP-3A-5E hardens wildcard-only provided-artifact rendering; RP-3A-5F records three full `manual_gold_20` DeepSeek live provided-artifact reruns using real Qwen-backed RARP cards. The latest smoke evidence has `enabled_count=20`, `cards_non_empty_count=20`, `parse/default` regressions `0/60`, and `critical_miss_regressions=1/60` on `rp3-manual-gold-0017`; per-case report artifacts live under ignored `ops/regression/route_prior/out/rp3_routing_case_report.md` and `ops/regression/route_prior/out/rp3_routing_case_table.json`. None of these implement runtime advisory or production promotion. RP-3 runtime prompt advisory and `ROUTE_PRIOR_ADVISORY_MODE` remain unimplemented.

## Environment Baseline

- Python requirement: `>=3.11,<4.0`
- Local baseline: conda env `cline_env`
- Clean Windows/Codex validation example: `D:\AnacondaEnvs\langgraph_agent_py311`
- Frontend baseline: `npm`, not `pnpm` or `yarn`
- Dev quality tools should be installed alongside the project when you intend to run `--mode static`
- Mainline Python dependencies come from `pyproject.toml`. Local development/static validation should install `.[dev]` plus `pytest`.
- `requirements-hf.txt` and `requirements-train.txt` are optional non-mainline dependency sets and are not default quality-gate inputs.
- `TAVILY_API_KEY` remains an import-time prerequisite for `react_agent.graph`
- RP-1A private embedding envs:
  - `ROUTE_PRIOR_EMBEDDINGS_ENABLED`
  - `ROUTE_PRIOR_EMBEDDINGS_MODEL`
  - `ROUTE_PRIOR_OPENAI_BASE_URL` falling back to `OPENAI_BASE_URL`
  - `ROUTE_PRIOR_OPENAI_API_KEY` falling back to `OPENAI_API_KEY`
- RP-2C private reliability trace envs:
  - `ROUTE_PRIOR_RELIABILITY_ENABLED`
  - optional `ROUTE_PRIOR_PROFILE_CARDS_DIR`
  - optional `ROUTE_PRIOR_RELIABILITY_TABLE`
  - optional `ROUTE_PRIOR_TRACE_TOP_CARDS`
- These route-prior envs are runtime-internal only. They do not expand public readiness or the public adapter contract.
- replay continuity remains weaker than persistent graph continuity and must stay labeled that way
- `state["messages"]` is not the public transcript

## Product Boundary

What this repo does on the current mainline:

- keeps a single assistant persona in the public transcript
- keeps workflow as an answer-level inspector
- keeps the final visible answer on the mainline path by default; Fair Fusion remains a sidecar/shadow path unless explicitly gated on
- renders assistant answer Markdown on the client while keeping the answer payload as plain text from the backend
- keeps the chat view inside a readable width and contains wide Markdown blocks inside the assistant card instead of letting them push the page wider
- adds a workflow-first NDJSON streaming seam that emits only safe public events and keeps the old sync seam available
- keeps `structuredInput` additive and honest
- keeps `materials` and `urlReferences` compiled into canonical transcript text
- keeps `/settings` and `/agents` read-only

What the current mainline still does not do:

- no new product feature expansion
- no runtime business-semantic change
- no file upload
- no URL fetch / HTML parsing / snapshot persistence
- no SSE
- no token streaming
- no raw graph-event or chain-of-thought streaming

## Docs

- [Project Overview](docs/PROJECT_OVERVIEW.md)
- [Mainline Runtime Audit](docs/MAINLINE_RUNTIME_AUDIT.md)
- [System Map](docs/SYSTEM_MAP.md)
- [Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md)
- [Docs Index](docs/INDEX.md)
- [Router SFT Runbook](docs/RUNBOOK_ROUTER_SFT.md)
- [Changelog](docs/CHANGELOG.md)

If documentation conflicts with runtime behavior, prefer `src/react_agent/*`, focused tests, and the S0 docs referenced by `docs/INDEX.md`.
