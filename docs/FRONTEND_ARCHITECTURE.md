# FRONTEND_ARCHITECTURE

## 1. Phase Position

This document defines the frontend and public-adapter architecture for the live shell that now sits on top of the Python public adapter.

Current relevant phases:

- `Phase WS-1`: workflow-first NDJSON streaming on top of the live adapter and quality baseline
- `Phase PF-2E-B`: additive typed input seam through structured input, pasted materials, and URL references
- `Phase QS-2：residual quality closure`: quality-entry alignment, active-test-surface cleanup, and authority-doc cleanup

The repo now contains:

- a live chat-first frontend under `apps/web`
- a Python public adapter under `src/react_agent/public_*.py`
- a JSON file-backed public thread store at `var/public_api/threads.json`

## 2. Product Shape

The product remains a chat-first workspace with one visible assistant persona.

- Left rail: conversation list and workspace navigation
- Main thread: public user/assistant transcript only
- Composer: workflow-first NDJSON streaming against the Python public adapter with sync fallback preserved
- Structured input: a collapsed layer inside the composer that compiles richer user input into transcript text and mirrors it into an additive typed field
- Assistant answer card: the visible answer container
- Workflow panel: an inspector that shows live progress during streaming and returns to ordinary answer inspection after completion
- Agents page: a live read-only catalog-style explanation view for the layered runtime topology
- Settings page: a read-only readiness/status view backed by `/api/health`

This shape is deliberate. The UI should feel like one assistant with an inspectable collaboration engine behind it, not a room full of agents talking to the user.

## 3. Structured Input Boundary

The frontend can now collect:

- task / question
- known background / material
- pasted materials / notes cards
- URL references
- constraints
- output preference

Frontend rules:

- the frontend compiles those fields into normalized transcript text before calling `sendMessage(threadId, text, structuredInput?)`
- pasted materials become `materials: string[]` and must still compile into canonical transcript text
- URL references become `urlReferences: string[]` and must still compile into canonical transcript text
- when only `task` is filled, the frontend sends the raw task text and may still mirror `{ task }` into the typed field
- the public transcript, public store, and replay continuity all continue to treat transcript text as the only canonical truth source
- the typed `structuredInput` field is an additive mirror only; it does not participate in runtime invoke or replay reconstruction
- structured user-bubble rendering now prefers `turn.structuredInput` and falls back to parsing `turn.text` when older turns have no typed field

## 4. Public Transcript vs Workflow Layer

The frontend boundary is split into two surfaces.

### Public transcript

- Roles are limited to `user` and `assistant`
- The assistant answer is rendered as one cohesive card
- The assistant answer body is rendered as safe client-side Markdown with GFM support for common answer structures such as tables and fenced code blocks
- The assistant answer card keeps a bounded reading width and contains wide Markdown blocks locally so the chat view does not overflow the viewport
- Final source provenance may be shown as metadata on the answer card

### Workflow layer

- planning: layer plan and mode
- execution: summarized agent steps grouped by layer
- fusion: baseline/judge/writer sidecars
- final source: which answer source was emitted and why
- live progress: client-only stage status during an in-flight stream; never persisted as transcript

The workflow layer exists to explain collaboration safely without exposing raw internals.

WS-1 keeps that promise by streaming only safe product events rather than raw graph messages:

- `run.started`
- `workflow.stage`
- `workflow.snapshot`
- `answer.final`
- `error`

## 5. Why The Frontend Must Not Render `state["messages"]`

`state["messages"]` is not a safe or coherent public transcript. In the current runtime it mixes:

- router raw output
- manager debug messages
- manager assignment messages stored as `HumanMessage`
- agent JSON payloads
- final visible answer

Because of that mixture, rendering `state["messages"]` directly would leak internal orchestration state and break the single-assistant product model.

## 6. Public Adapter Contract

The public adapter maps runtime state into a safe contract instead of exposing raw graph state.

Primary safe seams:

- final answer: `emitted_bundle["answer"]`
- source badge: `final_answer_source`
- additive stream seam: `POST /api/threads/{thread_id}/messages/stream`
- workflow snapshot:
  - `layer_plan`
  - `layer_mode`
  - `current_layer`
  - `layer_done`
  - `fanout_targets`
  - `baseline_status`
  - `judge_status`
  - `writer_status`
- safe provenance/debug fields:
  - `runId`
  - `continuityMode`
  - `evidenceCount`
  - normalized emit-path provenance summary

Internal-only fields remain hidden:

- `messages`
- `analyst_results`
- `ephemeral_results`
- raw fusion / writer payloads
- raw router output
- raw chain-of-thought

## 7. Continuity Modes

The public adapter supports two continuity modes.

### Persistent continuity

- selected only when the canonical `get_graph_for_invoke(thread_id)` path resolves to a checkpointer-backed graph

### Replay continuity

- selected when no checkpointer is available
- the adapter replays stored public transcript turns into `messages`
- this is intentionally weaker than persistent graph state
- the frontend must label it as replay continuity and must not present it as full persistent memory

## 8. Health and Error Surface

The adapter keeps health and error signaling on the existing public surface instead of adding a separate debug API.

- `/api/health` always reports API liveness with `200`
- readiness details are carried as structured public-safe fields:
  - runtime import readiness
  - provider env readiness
  - search env readiness
  - checkpointer status
- transport failures remain distinct from degraded readiness:
  - unavailable: the web shell cannot reach the adapter at all
  - degraded: the adapter is alive, but readiness is below the preferred baseline
  - request error: a specific request failed while the adapter remained reachable

## 9. Active Frontend Test Surface

The active frontend gate entry is:

- `apps/web/src/test/smoke.tsx`

Legacy fixtures are retained only as reference files:

- `apps/web/src/test/app.smoke.legacy.tsx`
- `apps/web/src/test/workflow.smoke.legacy.tsx`

They are not part of the default frontend gate and should not be described as if they were.

## 10. Current Implementation Boundary

The current frontend/public-adapter phase intentionally does all of the following:

- uses a Python HTTP adapter / BFF
- keeps the sync request/response seam available
- adds a workflow-first NDJSON stream seam that projects safe progress events only
- keeps runtime invoke text-only even though the public send-message seam now supports optional `structuredInput`
- keeps transcript text as the canonical persisted truth and replay source while storing `structuredInput` only as an additive mirror
- keeps the transcript to one assistant persona
- renders assistant answer Markdown on the client without changing the backend/public-adapter payload shape
- keeps workflow rendering separate from the transcript
- keeps `/settings` read-only and backed by the existing health contract
- keeps `/agents` on a live read-only catalog surface instead of a runtime control panel
- avoids surfacing raw graph internals or raw agent messages
- does not add SSE or token/step/raw graph streaming
- does not add file upload, URL fetch, HTML parsing, or snapshot persistence
- does not alter runtime business semantics
