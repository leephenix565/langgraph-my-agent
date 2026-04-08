# Project Overview: Current Engineering Snapshot

> Scope note: this document is the narrative and current-snapshot entry for the repo. It does not define command truth. For operational commands, prefer [SYSTEM_MAP.md](/E:/langgraph-my-agent/docs/SYSTEM_MAP.md), [run_quality.py](/E:/langgraph-my-agent/scripts/quality/run_quality.py), and the quality workflows.

## 1. What This Project Is

This repository is a layered multi-agent orchestration system built on LangGraph `StateGraph`. The mainline runtime centers on `src/react_agent/`, `config/agents/`, `langgraph.json`, and the surrounding regression, training, and observability tooling. The current public product shell is a chat-first web app in `apps/web/` backed by a Python public adapter.

## 2. Current Snapshot

- Runtime skeleton: `langgraph.json -> src/react_agent/graph.py:graph`
- Main runtime chain: `router_node -> manager_broadcast -> agent nodes -> manager_summary -> (_run_final_summary / finalize_summary) -> optional memory_update -> __end__`
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
- Current phase: `Phase WS-1：workflow-first streaming`

## 3. What Is Already Closed

The repo is already strong on product-baseline closure:

- graph topology and entry wiring
- public adapter truthfulness
- replay honesty
- focused unit coverage
- public adapter integration coverage
- live web shell with a single assistant persona
- typed input / notes / URL references kept honest through canonical transcript text

That means the repo is no longer blocked on product-baseline closure or the first quality-stable loop. The current step is an additive workflow-first streaming seam that preserves the same transcript and runtime boundaries.

## 4. Why WS-1 Exists

QS-1B through QS-3 closed the main quality and credibility gaps, which makes it safe to add one narrow new interaction seam:

- additive workflow-first streaming for the chat surface
- real-time safe workflow/progress updates without exposing raw graph internals or chain-of-thought

WS-1 adds that seam without changing the LangGraph runtime business semantics, the public transcript truth rules, or the single-assistant product model.

## 5. Runtime and Public Boundary

Important boundaries remain unchanged in WS-1:

- do not treat `state["messages"]` as the public transcript
- do not turn internal agents into separate public chat speakers
- keep workflow as a summarized inspector layer
- keep `text` as the canonical persisted truth
- keep replay continuity explicitly weaker than persistent graph continuity
- keep `structuredInput`, `materials`, and `urlReferences` as additive mirrors only
- keep workflow/progress stream events client-visible but non-persisted
- keep the existing sync send-message seam available alongside the new stream seam

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

Current product scope in WS-1 now includes:

- the existing sync seam `POST /api/threads/{thread_id}/messages`
- an additive NDJSON stream seam `POST /api/threads/{thread_id}/messages/stream`
- safe public stream events only:
  - `run.started`
  - `workflow.stage`
  - `workflow.snapshot`
  - `answer.final`
  - `error`
- assistant answer Markdown rendering on the client

WS-1 still does not add:

- SSE
- token streaming
- raw graph-event streaming
- raw chain-of-thought exposure
- file upload
- URL fetch / HTML parsing / snapshot persistence
- LangGraph runtime business-semantic changes

## 10. Short External Description

> This project is a layered multi-agent orchestration system built on LangGraph `StateGraph`. Its runtime entrypoint is `langgraph.json -> src/react_agent/graph.py:graph`, and its public product shell is a live chat-first web app backed by a Python public adapter. The repo now has live Chat, Settings, and Agents surfaces, additive typed input mirrors for structured input, pasted materials, and URL references, plus a workflow-first NDJSON stream seam that preserves transcript text as the only canonical public truth. The current engineering phase is `Phase WS-1：workflow-first streaming`.
