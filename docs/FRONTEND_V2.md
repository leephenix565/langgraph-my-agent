# Frontend V2 Target

This document describes the target frontend boundary for the Fixed DAG reset. R1-A does not implement the frontend rewrite.

## Product Boundary

The public chat remains a single user and assistant transcript. Internal DAG execution belongs in a workflow inspector, not in separate public agent chat lanes.

## Target Composer Flow

```text
composer text
  -> public API request
  -> Fixed DAG runtime
  -> workflow snapshots
  -> final assistant answer
```

## Workflow Inspector Target

The inspector should move from old layer/mode/fusion concepts to:

- DAG stage
- dimension
- step
- status
- evidence coverage
- final report readiness

The inspector may show safe structured summaries. It must not show provider raw responses, raw graph messages, manager assignment JSON, or secret-bearing metadata.

## Implementation Preference

Rewrite the existing `apps/web` shell in place unless a later phase explicitly approves a separate app. Do not create a second public transcript model.

## Deferred Work

- frontend workflow type update
- DAG progress timeline
- dimension-level status panels
- report evidence view
- production auth and rate limits
- persistent run history
- deployment hardening
