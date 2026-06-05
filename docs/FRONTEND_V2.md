# Frontend V2 Boundary

This document describes the frontend boundary for the Fixed DAG reset.

## Product Boundary

The public chat remains a single user and assistant transcript. Internal DAG
execution belongs in a workflow inspector, not in separate public agent chat
lanes.

## Current R5-B2 Workflow Inspector Boundary

The Python public adapter emits `workflow_snapshot_v2` with:

- `stages`
- `dagSteps`
- `dimensionGroups`
- `currentStage`
- `completedSteps`
- `executionBatches`
- `stepResults`
- `provenance`
- `finalSource`

The existing `apps/web` shell is retained and migrated in place. R5-B1 moved
the frontend workflow/chat types, streaming placeholder workflow, fixed DAG
mocks, and smoke fixtures to `workflow_snapshot_v2` instead of the old
`layerPlan`, `layerMode`, `agentSteps`, `fusionSteps`, or
`mainline/baseline/fused` source model.

R5-B2 rewrites the WorkflowPanel around the same public snapshot. The inspector
now renders:

- stage timeline from `stages`, `currentStage`, and live `workflow.stage`
  progress
- execution batches from `executionBatches`
- selectable DAG step cards from `dagSteps`
- dimension group panels from `dimensionGroups`
- public-safe selected step result metadata from `stepResults`
- final source and provenance from `finalSource` and `provenance`

The inspector may show safe structured summaries and runtime binding metadata
such as runtime kind, implementation status, invoke-enabled status,
live-verified status, and warnings. It must not show provider raw responses,
external raw responses, raw graph messages, manager assignment JSON, endpoint
URLs, env var values, or secret-bearing metadata.

R4-A changes the backend `/api/agents` projection to the fixed DAG catalog: 27
enabled `snake_case` agents with L1=3, L2=18, L3=4, and L4=2. Frontend code that
still carries old aNN mock labels is legacy migration input, not active backend
truth.

R4-B adds backend runtime binding metadata to workflow `stepResults`, including
runtime kind, implementation status, binding source, legacy migration id,
external agent id, invoke-enabled flag, and live-verified flag. It does not add
runtime binding fields to `/api/agents`, and it does not expose endpoint URLs,
env var values, provider raw responses, or external raw responses.

The workflow inspector treats the reset roster as 27 formal agents. The
`sentiment_company_radar` step belongs to the market dimension and should not
be shown as a direct risk-composite input.

## Target Composer Flow

```text
composer text
  -> public API request
  -> Fixed DAG runtime skeleton
  -> execute_fixed_dag
  -> workflow_snapshot_v2
  -> final assistant answer
```

## R5-B1 Done

- frontend workflow/chat type update to `workflow_snapshot_v2`
- streaming placeholder and `workflow.stage` merge aligned to fixed DAG stages
- mock workflow snapshot with `dagSteps`, `dimensionGroups`,
  `executionBatches`, `stepResults`, and `finalSource=reset_skeleton`
- mock `/api/agents` catalog aligned to 27 enabled `snake_case` ids
- frontend smoke fixture and assertions updated for the fixed DAG contract

## R5-B2 Done

- WorkflowPanel rewritten as a fixed DAG inspector instead of a minimal summary
- stage timeline rendering
- execution batch rendering
- dimension group rendering
- selectable DAG step list
- selected step result metadata panel
- final source and provenance panel
- screenshot fixture script updated to use `workflow_snapshot_v2`
- frontend smoke assertions expanded for inspector rendering, step metadata,
  transcript boundary, and public-safe negative checks

## Deferred Work

- visual dependency graph beyond ordered execution batches
- evidence-specific drilldown once backend public evidence cards are formalized
- production auth and rate limits
- persistent run history
- deployment hardening
