# Frontend V2 Target

This document describes the frontend boundary for the Fixed DAG reset.

## Product Boundary

The public chat remains a single user and assistant transcript. Internal DAG
execution belongs in a workflow inspector, not in separate public agent chat
lanes.

## Current R2 Boundary

The Python public adapter emits `workflow_snapshot_v2` with:

- `stages`
- `dagSteps`
- `dimensionGroups`
- `currentStage`
- `completedSteps`
- `provenance`
- `finalSource`

The existing `apps/web` shell is retained. Its full workflow inspector rewrite
is deferred to R5, so frontend code may still contain old mock/UI labels until
that phase.

R2 hardens the backend workflow payload construction through
`fixed_dag_contracts.py`. It does not rewrite the frontend workflow UI or types.

The workflow inspector target should treat the reset roster as 27 formal agents
(L1=3, L2=18, L3=4, L4=2). `sentiment_company_radar` is a market-dimension L2
step and should not be shown as a direct risk-composite input.

## Target Composer Flow

```text
composer text
  -> public API request
  -> Fixed DAG runtime skeleton
  -> workflow_snapshot_v2
  -> final assistant answer
```

## Workflow Inspector Target

The inspector should show:

- DAG stage
- dimension
- step
- status
- evidence coverage
- final report readiness

The inspector may show safe structured summaries. It must not show provider raw
responses, raw graph messages, manager assignment JSON, or secret-bearing
metadata.

## Implementation Preference

Rewrite the existing `apps/web` shell in place unless a later phase explicitly
approves a separate app. Do not create a second public transcript model.

## Deferred Work

- frontend workflow type update
- DAG progress timeline
- dimension-level status panels
- report evidence view
- alignment of frontend mocks with the full 27-agent DAG snapshot
- production auth and rate limits
- persistent run history
- deployment hardening
