# Repo Collaboration Guide

## Phase Position

- Current frontend/runtime integration work is `Phase F3`: health hardening + continuity/debug polish on top of the public adapter.
- Current repo-level closure work is `Phase QS-2：residual quality closure`.
- `apps/web` now reads live chat-thread data from the Python public adapter.
- `/agents` is now a live read-only catalog surface in this phase.
- `apps/web` now also supports a typed structured input seam for chat, but the compiled transcript text remains the canonical persisted truth and replay source.
- `apps/web` now also supports pasted materials / notes cards through that same typed seam, and those notes must still be compiled into canonical transcript text.
- `apps/web` now also supports additive URL references through that same typed seam, and those references must still be compiled into canonical transcript text.
- Repo-level quality closure now uses `scripts/quality/run_quality.py` as the main validation entrypoint, while provider/live smoke remains optional and non-blocking.
- Do not quietly add SSE, token streaming, or raw graph-event streaming in F3.

## Frontend Public Surface

- Keep a single assistant persona in the public transcript.
- Keep structured input honest: richer chat input may compile into transcript text and may be mirrored into an additive `structuredInput` field, but it must not replace transcript text or become a hidden second persistence layer that replay cannot restore.
- Keep pasted materials honest: `materials` or notes cards may be mirrored into the additive `structuredInput` field, but replay continuity must still be restorable from `turn.text` alone.
- Keep URL references honest: `urlReferences` may be mirrored into the additive `structuredInput` field, but they are references only, not fetched snapshots, and replay continuity must still be restorable from `turn.text` alone.
- Do not turn internal agents into separate chat speakers.
- Do not render raw graph internals such as `state["messages"]`, raw router output, raw manager assignments, raw agent JSON, or raw chain-of-thought.
- Show multi-agent activity only as a summarized workflow layer.
- Keep Fair Fusion semantics as sidecars (`baseline`, `judge`, `writer`, `final source`), not as ordinary L1-L4 agents.

## Continuity Rules

- Preferred continuity is checkpointer-backed persistent graph invocation.
- Transcript replay is an allowed fallback only when persistent graph continuity is unavailable.
- Replay continuity must be labeled explicitly as weaker than persistent graph continuity.
- Do not present replay continuity as equivalent to graph-backed thread persistence.
- Health/readiness surfaces must use structured public-safe status and must not leak raw exception dumps.

## Change Boundaries

- Do not change LangGraph runtime business semantics unless the task explicitly targets runtime behavior.
- If a task touches frontend shell, public adapter, or workflow presentation, preserve the separation between public transcript and internal orchestration state.
- If a task touches docs, update the matching authority docs in the same change.

## Required Doc Sync

When Phase F3 frontend or public-adapter files change, sync at least:

- `README.md`
- `docs/PROJECT_OVERVIEW.md`
- `docs/SYSTEM_MAP.md`
- `docs/CHANGELOG.md`
- `docs/FRONTEND_ARCHITECTURE.md`
- `docs/PROJECT_OVERVIEW.md`

## Verification Baseline

- Repo-level quality closure should prefer `python scripts/quality/run_quality.py --mode mainline`.
- Blocking static checks should prefer `python scripts/quality/run_quality.py --mode static`.
- Frontend changes should pass `npm --prefix apps/web run build` and `npm --prefix apps/web run test`.
- Public adapter changes should pass `pytest tests/integration_tests/test_public_api.py`.
- Runtime graph smoke should pass `pytest tests/integration_tests/test_graph.py`.
- Backend or runtime changes should continue to use the repo's Python validation flow separately from the frontend shell.
