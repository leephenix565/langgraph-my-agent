# Project Overview: Current Engineering Snapshot

> Scope note: this document is the narrative and current-snapshot entry for the repo. It does not define command truth. For operational commands, prefer [SYSTEM_MAP.md](/E:/langgraph-my-agent/docs/SYSTEM_MAP.md), [run_quality.py](/E:/langgraph-my-agent/scripts/quality/run_quality.py), and the quality workflows.

## 1. What This Project Is

This repository is a layered multi-agent orchestration system built on LangGraph `StateGraph`. The mainline runtime centers on `src/react_agent/`, `config/agents/`, `langgraph.json`, and the surrounding regression, training, and observability tooling. The current public product shell is a chat-first web app in `apps/web/` backed by a Python public adapter.

## 2. Current Snapshot

- Runtime skeleton: `langgraph.json -> src/react_agent/graph.py:graph`
- Main runtime topology: `__start__ -> router`, then `router -> manager_broadcast` and `router -> baseline_sidecar`; agent nodes return to `manager_summary`; final closeout flows through `manager_summary/finalize_summary -> fusion_gate -> fusion_judge_shadow -> fusion_writer_shadow -> final_emit -> (memory_update | __end__)`
- Default answer path: Fair Fusion baseline/judge/writer sidecars exist in runtime, but defaults keep the visible answer on the mainline path unless fusion and source switching are explicitly enabled
- Baseline sidecar default config: `.env.example` now uses DeepSeek V4 Pro through the OpenAI-compatible baseline override (`BASELINE_MODEL=openai/deepseek-v4-pro`, `BASELINE_OPENAI_BASE_URL=https://api.deepseek.com`); the existing Gemini grounding path is still code-backed when `baseline_model` is explicitly set to `google_genai/...`
- Public product surfaces:
  - Chat: live
  - Settings: live read-only
  - Agents: live read-only
- Public transcript boundary:
  - one visible assistant persona only
  - workflow is an inspector, not a second transcript
  - `text` remains the canonical transcript / store / replay truth
- Assistant answer rendering:
  - the frontend now renders `answerCard.answer` as safe Markdown for headings, lists, tables, quotes, and code
  - the chat view also keeps assistant answers inside a bounded reading width so long Markdown paragraphs and wide blocks do not run into the viewport edge
  - this remains a presentation-layer change only and does not alter the public adapter payload shape
- Typed input boundary:
  - `structuredInput` is additive only
  - pasted `materials` and additive `urlReferences` must still compile into canonical transcript text
- RP-1A / RP-2C runtime seams:
  - the repo now also carries an embedding-first route-prior shadow seam inside `router_node`
  - phase 1 remains shadow-only: no formal Router ownership change, no committed-state expansion, no public-surface expansion
  - missing embedding config or backend failures disable the seam privately and fail open to the existing mainline
  - RP-2C adds optional `ROUTE_PRIOR_RELIABILITY_ENABLED` trace-only reliability shadow and post-router comparison, still default-off and with no Router prompt/parser, State, public API/workflow/health, advisory, or repair change
- RP-3A offline advisory experiments:
  - RP-3A-1 adds a network-free Router advisory A/B dry-run harness for parser-stability and selected-agent-delta evidence only
  - RP-3A-3 adds an optional prediction artifact generator; RP-3A-5 adds `provided_artifact` / `rarp_shadow` advisory-source experiments from RP-2 route-prior/reliability artifacts
  - RP-3A-5F records the latest real RARP provided-artifact smoke evidence: 20/20 Qwen-backed route-prior enabled cases, 20/20 non-empty reliability-card cases, three DeepSeek live reruns, 0/60 parse/default regressions, and 1/60 critical miss on `rp3-manual-gold-0017`
  - these remain offline/ops experiment artifacts; they do not implement runtime Router advisory, `ROUTE_PRIOR_ADVISORY_MODE`, Router prompt mutation, parser changes, or public-surface expansion
- Current phase position:
  - frontend/runtime integration: `Phase F3`
  - repo-level closure: `Phase QS-2`
  - `Phase WS-1` workflow-first streaming is landed surface area, not the current repo phase label

## 3. What Is Already Closed

The repo is already strong on product-baseline closure:

- graph topology and entry wiring
- public adapter truthfulness
- replay honesty
- focused unit coverage
- public adapter integration coverage
- live web shell with a single assistant persona
- typed input / notes / URL references kept honest through canonical transcript text

That means the repo is no longer blocked on product-baseline closure. The current work is F3 hardening plus QS-2 residual closure on top of the already-landed workflow-first streaming seam.

## 4. Landed Seam vs Current Phase

The workflow-first NDJSON seam landed during WS-1 and remains part of the product surface:

- additive workflow-first streaming for the chat surface
- real-time safe workflow/progress updates without exposing raw graph internals or chain-of-thought

The current repo position is different. F3 and QS-2 focus on hardening the public-adapter/web mainline, continuity/readiness surfaces, and authority docs without changing LangGraph runtime business semantics, transcript truth, or the single-assistant product model.

Route-prior work still fits inside that same hardening posture. RP-1A is an internal embedding-first runtime shadow seam, not a product-surface expansion and not a new top-level repo phase label. RP-1B adds optional offline shadow validation and replay/eval evidence for that seam. RP-2A extends the offline eval tooling with the versioned `route_eval_label_v0` schema and expanded metrics. RP-2B adds offline-first profile-card loading plus deterministic reliability scoring helpers. RP-2C adds an env-gated runtime reliability shadow trace and post-router comparison scaffold. RP-3A-1 adds a network-free offline Router advisory A/B dry-run harness for parser-stability and selected-agent-delta evidence. RP-3A-3 adds optional prediction artifact generation, RP-3A-5 adds real RARP `provided_artifact` / `rarp_shadow` experiments, and RP-3A-5F records three full `manual_gold_20` DeepSeek live provided-artifact reruns using Qwen-backed RARP reliability cards.

RP-3 runtime Router advisory is not implemented. RP-2C remains default-off, trace-only, and fail-open; RP-3A remains offline/ops experimentation. The latest RP-3A-5F smoke shows real RARP cards and parse/default stability, but it still has one stochastic critical miss across 60 live replays and is not production promotion evidence. None of this changes the Router prompt, parser, committed `layer_plan / layer_mode`, State schema, manager dispatch, public API, public workflow, `/api/health`, frontend behavior, or agent execution.

## 5. Runtime and Public Boundary

Important boundaries remain unchanged on the current mainline:

- do not treat `state["messages"]` as the public transcript
- do not turn internal agents into separate public chat speakers
- keep workflow as a summarized inspector layer
- keep `text` as the canonical persisted truth
- keep replay continuity explicitly weaker than persistent graph continuity
- keep `structuredInput`, `materials`, and `urlReferences` as additive mirrors only
- keep workflow/progress stream events client-visible but non-persisted
- keep the existing sync send-message seam available alongside the new stream seam
- keep Fair Fusion represented as baseline/judge/writer sidecars rather than ordinary L1-L4 agents
- keep the default visible answer on the mainline path unless source switching is explicitly enabled

## 6. Quality Entry and CI Position

The repo keeps one repo-level quality entry:

- [run_quality.py](/E:/langgraph-my-agent/scripts/quality/run_quality.py)

That entry now orchestrates:

- `ruff`
- `mypy`
- `codespell`
- Python unit tests
- public adapter integration tests
- runtime graph smoke
- frontend build/test
- deterministic fusion gate

The blocking static step is intentionally scoped to the maintained quality-closure surface rather than the entire historical repo. That keeps the default gate honest without forcing a full cleanup of older bench/tooling areas that are outside the current product-quality closure scope.

The mainline GitHub workflow now centers its blocking jobs on that entry rather than carrying a second logic path for the blocking checks.

Provider/live smoke remains scripted separately and still remains optional and non-blocking for the default gate.

## 7. Active Test Surface

The active default gate surface is now explicit:

- Python unit tests under `tests/unit_tests/`
- public adapter integration under `tests/integration_tests/test_public_api.py`
- runtime graph smoke under `tests/integration_tests/test_graph.py`
- frontend gate entry under `apps/web/src/test/smoke.tsx`

Older frontend test fixtures remain in the repo only as legacy references with a `.legacy.tsx` suffix. They are not part of the default gate.

## 8. Optional Provider / Live Smoke

Provider/live smoke now has:

- a dedicated script: [run_provider_live_smoke.py](/E:/langgraph-my-agent/scripts/quality/run_provider_live_smoke.py)
- a dedicated artifact path: `ops/regression/provider/out/provider_live_smoke.json`
- a dedicated optional workflow: `Optional Provider Live Smoke (Non-Blocking)`

If provider/search/checkpointer prerequisites are absent, the smoke writes a `skipped` artifact and exits `0`. That keeps the evidence path scripted without turning missing credentials into a mainline gate failure.

Current local evidence still shows a `skipped` artifact rather than a passed provider-backed artifact because the environment is missing:

- provider credentials (`OPENAI_API_KEY`, `ROUTER_OPENAI_API_KEY`, `BASELINE_OPENAI_API_KEY`, or `GOOGLE_API_KEY`)
- `TAVILY_API_KEY`
- runtime import/readiness in a fully configured provider-backed state

## 9. Current Product Scope

Current product scope on the mainline now includes:

- the existing sync seam `POST /api/threads/{thread_id}/messages`
- an additive NDJSON stream seam `POST /api/threads/{thread_id}/messages/stream`
- safe public stream events only:
  - `run.started`
  - `workflow.stage`
  - `workflow.snapshot`
  - `answer.final`
  - `error`
- assistant answer Markdown rendering on the client
- a single assistant persona plus workflow inspector product model
- Fair Fusion surfaced as workflow sidecars (`baseline`, `judge`, `writer`, `final source`) rather than ordinary agents

The current mainline still does not add:

- SSE
- token streaming
- raw graph-event streaming
- raw chain-of-thought exposure
- file upload
- URL fetch / HTML parsing / snapshot persistence
- LangGraph runtime business-semantic changes

## 10. Short External Description

> This project is a layered multi-agent orchestration system built on LangGraph `StateGraph`. Its runtime entrypoint is `langgraph.json -> src/react_agent/graph.py:graph`, and its public product shell is a live chat-first web app backed by a Python public adapter. The repo now exposes a single-assistant transcript, a workflow inspector, additive typed input mirrors for structured input, pasted materials, and URL references, plus a workflow-first NDJSON stream seam that preserves transcript text as the only canonical public truth. The current engineering position is `Phase F3 + QS-2`, with the WS-1 streaming seam already landed.
