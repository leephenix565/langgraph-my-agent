# Current Status

This is the current operational status entry for the Fixed DAG reset branch.
Use it for status and roadmap orientation before reading historical phase
records.

## Source Authority

- Branch: `reset/fixed-dag-v1`.
- Source authority: the current Git HEAD in `/sdb/dlut/dev/langgraph-my-agent`.
- Reset lineage anchor: `pre-fixed-dag-reset-20260604-1457`.
- This document intentionally avoids short-lived process identifiers and raw
  endpoint payloads.

## Runtime And Catalog

- The active graph remains `langgraph.json -> src/react_agent/graph.py:graph`.
- The formal catalog has 27 fixed DAG agent ids from
  `config/fixed_dag/agent_catalog.json`.
- Runtime binding authority remains
  `config/fixed_dag/runtime_bindings.json`.
- L4 `decision_synthesizer` and `report_generator` are the current
  compute-default external bindings. This is a compute path, not an invoke
  path.
- `invoke_enabled_by_default` remains false for the catalog/runtime binding
  boundary.

## Sync Workflow Status

- The bidirectional agent sync validation topic is complete.
- The strict one-command publish-and-rebase workflow is operational.
- Final strict cycle: `cycle_strict_e7bc707d5b8b`.
- Current active external-agent baseline:
  `first-cycle-p2s_52d75b56543f`.
- Durable final cycle run:
  `/sdb/dlut/ops-artifacts/agent-sync/runs/run_cycle_strict_cycle_strict_e7bc707d5b8b_20260625T135349Z`.
- Future non-zero work should use the normal experiment workflow: fork an
  immutable baseline, register exact change units, generate exact S2P/P2S
  children, request machine approval, then execute the approved strict cycle.

## Repository Roles

- `/sdb/dlut/dev/langgraph-my-agent` is the main-system development authority.
- `/sdb/dlut/prod/langgraph-my-agent` is a runtime/deployment copy, not a source
  authority.
- `/sdb/dlut/sandbox/*` holds experiments and immutable baselines. The active
  baseline is not edited in place.
- External owner-dev repositories are read-only to this workflow unless a
  separate owner workflow grants write authority.

## Current Engineering Theme

The active engineering theme is Repository Authority & Active-Core
Consolidation. M3B records the Context/State active-vs-compat boundary in
metadata-only helpers so tests can validate retained compatibility fields
without changing runtime shape. No field deletion, public contract change,
graph topology change, catalog change, or runtime binding change is part of
this step.

## Current Non-Claims

- Passing static or mainline quality is not production readiness by itself.
- Current docs do not add runtime bindings, live flags, process actions, or
  provider calls.
- Default validation and sync quality gates do not call `/v1/agent/invoke`.
- The smoke/evidence ledgers in `docs/history/` are historical evidence, not
  runtime or configuration authority.
- Public transcripts must not expose secrets, raw graph messages, provider raw
  responses, manager assignment internals, or agent JSON.

## Evidence And History

- Start with `docs/INDEX.md` for the current reading order.
- Historical phase ledgers live under `docs/history/` and are indexed by
  `docs/history/MANIFEST.json`.
- Sync operator procedures live in
  `docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md` and
  `docs/CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md`.
