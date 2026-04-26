# System Map

This document is the S0 operational source for the current repo snapshot.

## 1. Current Phase

- Frontend/runtime integration: `Phase F3`
- Repo-level closure: `Phase QS-2`
- Landed seam still in scope: `Phase WS-1` workflow-first streaming
- Scope: hardening the public-adapter/web mainline, continuity/readiness surfaces, and authority-doc truth without changing LangGraph runtime business semantics
- Non-goals:
  - no new product features
  - no file upload
  - no URL fetch / HTML parsing / snapshot persistence
  - no SSE
  - no token streaming
  - no raw graph-event or chain-of-thought streaming
  - no LangGraph runtime business-semantic changes

## 2. Environment Baseline

- Python requirement: `>=3.11,<4.0`
- Local baseline env: `cline_env`
- Clean Windows/Codex validation example: `D:\AnacondaEnvs\langgraph_agent_py311`
- Frontend baseline: `node` + `npm` under `apps/web/`
- Do not treat `pnpm` or `yarn` as the documented frontend baseline.
- Mainline Python dependency truth: `pyproject.toml`
- Local development/static install path: `python -m pip install -e ".[dev]"`, then `python -m pip install pytest`
- `.[dev]` supplies static tooling for `scripts/quality/run_quality.py --mode static`: `ruff`, `mypy`, and `codespell`.
- `pytest` is installed separately in local and CI test gates unless dependency-group tooling is used explicitly.
- `requirements-hf.txt` and `requirements-train.txt` are optional non-mainline dependency sets for HF/model-side and training/fine-tuning workflows. They are not default mainline quality inputs.
- `TAVILY_API_KEY` remains an import-time prerequisite for `react_agent.graph`.
- RP-1A private embedding envs:
  - `ROUTE_PRIOR_EMBEDDINGS_ENABLED`
  - `ROUTE_PRIOR_EMBEDDINGS_MODEL`
  - `ROUTE_PRIOR_OPENAI_BASE_URL` with fallback to `OPENAI_BASE_URL`
  - `ROUTE_PRIOR_OPENAI_API_KEY` with fallback to `OPENAI_API_KEY`
- These RP-1A envs are internal runtime config only. They do not extend `/api/health` readiness or any public-safe contract.
- Static gate tooling lives in the repo's dev dependency surface and is required for `scripts/quality/run_quality.py --mode static`.

Recommended environment self-check:

```powershell
conda run --no-capture-output -n cline_env python --version
conda run --no-capture-output -n cline_env python -c "import sys; print(sys.executable)"
npm --version
```

Windows pytest note:

- Prefer `conda run --no-capture-output -n cline_env python ...`
- If `cline_env` is polluted or `conda run` is unavailable, prefer a clean Python 3.11 env for Windows/Codex validation.
- Use `PYTHONNOUSERSITE=1` so user-site packages do not contaminate validation.
- Use env-local `TEMP`, `TMP`, and `MYPY_CACHE_DIR` when C-drive temp space or repo-local cache permissions are unreliable.
- This is an execution-layer workaround for Windows terminal output issues, not a logic change

## 3. Repo-Level Quality Entry

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

`mainline` currently runs:

1. `ruff`
2. `mypy`
3. `codespell`
4. `pytest tests/unit_tests`
5. `pytest tests/integration_tests/test_public_api.py`
6. `pytest tests/integration_tests/test_graph.py`
7. `npm --prefix apps/web run build`
8. `npm --prefix apps/web run test`
9. deterministic fusion regression / eval / gate

Current blocking static scope is intentionally narrower than the full repo:

- `scripts/quality/`
- active Python integration tests
- current authority docs / README / `AGENTS.md`

This keeps the default quality gate anchored to the maintained quality-closure surface instead of dragging historical bench/tooling debt into the blocking path.

Underlying convenience wrappers in `Makefile`:

- `make quality`
- `make quality_static`
- `make quality_unit`
- `make quality_public_api`
- `make quality_graph_smoke`
- `make quality_frontend`
- `make quality_fusion_gate`
- `make quality_provider_smoke`

The script path above is the command truth. `Makefile` is only a wrapper.

## 4. Mainline CI

Mainline blocking workflow:

- file: `.github/workflows/unit-tests.yml`
- workflow name: `Quality Gate`

Current blocking job split:

- `python-static`
- `python-unit`
- `public-adapter-integration`
- `graph-smoke`
- `frontend`
- `fusion-gate`

Responsibilities:

- blocking static checks: `ruff`, `mypy`, `codespell`
- Python unit tests
- public adapter integration tests
- runtime graph smoke
- frontend build/test
- deterministic fusion gate

This workflow is the mainline quality gate for `push` to `main`, `pull_request`, and `workflow_dispatch`.

## 5. Active Test Surface

Active default-gate tests:

- `tests/unit_tests/`
- `tests/integration_tests/test_public_api.py`
- `tests/integration_tests/test_graph.py`
- `apps/web/src/test/smoke.tsx`

Legacy frontend fixtures:

- `apps/web/src/test/app.smoke.legacy.tsx`
- `apps/web/src/test/workflow.smoke.legacy.tsx`

They are retained only for reference and are not part of the default frontend gate.

## 6. Optional Provider / Live Smoke

Provider/live smoke is scripted, but it remains optional and non-blocking for the default gate.

Command:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_provider_live_smoke.py --out-dir ops/regression/provider/out
```

Output artifact:

- `ops/regression/provider/out/provider_live_smoke.json`

Artifact fields include:

- `status`
- `timestamp`
- `mode`
- `health`
- `prerequisites`
- `thread_id`
- `send_message_status`
- `continuity_mode`
- `error_code`
- `error_category`
- `residual_condition`
- `next_trigger_condition`

Behavior:

- if provider/search/checkpointer prerequisites are missing, the script writes `status="skipped"` and exits `0`
- if the environment is ready, the script exercises:
  - `GET /api/health`
  - `POST /api/threads`
  - `POST /api/threads/{id}/messages`
- if the live seam fails, the script writes `status="failed"` and exits non-zero

Optional workflow:

- file: `.github/workflows/integration-tests.yml`
- workflow name: `Optional Provider Live Smoke (Non-Blocking)`
- trigger: scheduled or manual only
- not part of the default blocking gate

Residual boundary:

- the current local evidence still remains a scripted `skipped` path rather than a passed provider-backed artifact
- current missing conditions in this environment are:
  - provider credentials (`OPENAI_API_KEY`, `ROUTER_OPENAI_API_KEY`, `BASELINE_OPENAI_API_KEY`, or `GOOGLE_API_KEY`)
  - `TAVILY_API_KEY`
  - runtime import/readiness in a fully configured provider-backed state

## 7. Deterministic Fusion Gate

Deterministic FF-5B regression/eval/gate remains network-free and is part of the mainline quality entry.

Commands:

```powershell
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.run_fusion_regression --out-dir ops/regression/fusion/out
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.eval_fusion_outputs --in ops/regression/fusion/out/fusion_runs.jsonl --out ops/regression/fusion/out/fusion_metrics.json
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.gate_fusion_outputs --in ops/regression/fusion/out/fusion_metrics.json --out ops/regression/fusion/out/fusion_gate.json
```

Artifacts:

- `ops/regression/fusion/out/fusion_runs.jsonl`
- `ops/regression/fusion/out/fusion_metrics.json`
- `ops/regression/fusion/out/fusion_gate.json`

Default gate policy:

- deterministic
- network-free
- trace noise remains warning-only
- provider/live smoke remains outside the default blocking gate

## 8. RP-1B Route-Prior Offline Eval

RP-1B route-prior evaluation is an optional offline regression/eval harness under `ops/regression/route_prior/`. It validates RP-1A shadow outputs against labeled question JSONL by reporting top-k match, shortlist recall, low-confidence fallback rate, formal-Router overlap observation, wildcard retention, and false-negative examples.

Commands:

```powershell
python -m ops.regression.route_prior.run_route_prior_eval --dataset ops/regression/route_prior/fixtures/rp1b_labeling_template.jsonl --out-dir ops/regression/route_prior/out --max-items 10 --prewarm-endpoint
python -m ops.regression.route_prior.eval_route_prior_outputs --runs ops/regression/route_prior/out/route_prior_runs.jsonl --out ops/regression/route_prior/out/route_prior_metrics.json
```

Artifacts:

- `ops/regression/route_prior/out/route_prior_runs.jsonl`
- `ops/regression/route_prior/out/route_prior_run_summary.json`
- `ops/regression/route_prior/out/route_prior_metrics.json`
- `ops/regression/route_prior/out/route_prior_false_negatives.json`

Policy:

- optional and non-blocking unless future work explicitly promotes it into the mainline gate
- default unit coverage stays network-free and does not require a local embeddings endpoint
- live runs require the private RP-1A embedding envs and a local OpenAI-compatible `/v1/embeddings` service
- fixture records marked `draft_for_human_review` are labeling drafts, not final quality evidence
- no runtime graph change, Router prompt/parser change, State schema change, public API change, public workflow change, or `/api/health` expansion

## 9. Runtime and Public Boundary

Runtime entry:

- `langgraph.json -> src/react_agent/graph.py:graph`

Current runtime topology:

- `__start__ -> router`
- `router_node` also runs an internal RP-1A embedding-first semantic-retrieval shadow seam before the formal Router model invoke
- `router -> manager_broadcast` and `router -> baseline_sidecar`
- `agent nodes -> manager_summary`
- `manager_summary/finalize_summary -> fusion_gate -> fusion_judge_shadow -> fusion_writer_shadow -> final_emit -> (memory_update | __end__)`
- `mainline_emit` remains a compatibility wrapper; current graph routing targets `final_emit`

Current public path:

- `apps/web -> /api/* -> react_agent.public_api -> react_agent.public_runtime -> react_agent.graph.get_graph_for_invoke(...)`

Default answer-source behavior:

- Fair Fusion baseline/judge/writer sidecars exist in runtime
- `enable_fair_fusion=false` and `enable_fair_fusion_source_switch=false` by default
- the visible answer therefore stays on the mainline path unless source switching is explicitly enabled

Important boundaries that remain unchanged on the current mainline:

- keep RP-1A shadow-only, fail-open, and trace-only
- do not let RP-1A alter formal Router prompt shape, parse semantics, or committed routing outputs
- do not surface RP-1A embedding config/readiness on `/api/health`
- do not treat `state["messages"]` as the public transcript
- do not turn internal agents into separate public chat speakers
- keep workflow as a summarized inspector
- keep `text` as the canonical transcript / store / replay truth
- keep replay continuity explicitly weaker than persistent graph continuity
- keep `structuredInput`, `materials`, and `urlReferences` additive only
- keep Fair Fusion as baseline/judge/writer sidecars rather than ordinary L1-L4 agents

## 10. Public Adapter Truthfulness

The current public adapter truth surface remains:

- `/api/health`
- `/api/threads`
- `/api/agents`
- `/api/threads/{thread_id}`
- `/api/threads/{thread_id}/messages`
- `/api/threads/{thread_id}/messages/stream`

Stream-event surface:

- transport: `application/x-ndjson`
- safe event types only:
  - `run.started`
  - `workflow.stage`
  - `workflow.snapshot`
  - `answer.final`
  - `error`

Truthfulness rules that still apply:

- `text` remains canonical on send-message ingress and stored user turns
- replay reconstructs continuity from `turn.text` alone
- `structuredInput` is an additive mirror only
- `materials` and `urlReferences` must still compile into canonical transcript text
- workflow stays an inspector, not a raw graph dump
- stream progress events are public-safe projections only and are never persisted as transcript turns
- `answer.final` is the only streaming event that carries the final persisted assistant answer payload

## 11. Frontend Baseline

Frontend commands still live under `apps/web/`:

```powershell
npm --prefix apps/web install
npm --prefix apps/web run build
npm --prefix apps/web run test
npm --prefix apps/web run screenshots
```

Important current test fact:

- the active frontend gate entry is `tsx src/test/smoke.tsx`
- the assistant answer card now renders `answerCard.answer` through a client-side Markdown renderer with GFM table support
- the chat message column now keeps a stable horizontal gutter and constrains assistant Markdown blocks so they wrap or scroll inside the answer card instead of overflowing the viewport
- the chat shell now prefers the additive NDJSON stream seam and falls back to the sync seam when a readable stream is unavailable
- this frontend rendering change does not alter backend contracts, transcript truth, or replay semantics
- legacy fixture files with a `.legacy.tsx` suffix are not part of the default gate

## 12. Router-SFT Runbook Position

Router-SFT training/eval command truth lives in:

- `docs/RUNBOOK_ROUTER_SFT.md`

It is not part of the default mainline quality gate.
