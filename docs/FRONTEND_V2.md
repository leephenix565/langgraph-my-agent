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

## Current R5-C Product Polish Boundary

R5-B2.6 localized visible Chinese copy across the existing `apps/web` shell and
deterministic fixed DAG skeleton output. R5-C is the next presentation-layer
follow-up: it keeps the same public contracts and reduces engineering/status
noise in normal user-facing views.

- `workflow_snapshot_v2` remains the frontend workflow payload.
- The public transcript remains a single user/assistant transcript.
- Technical ids, schema names, and runtime enum values remain raw where needed
  for debugging, for example `route_planner`, `financial_data_service`,
  `workflow_snapshot_v2`, `external_http_candidate`, and
  `external_candidate_disabled`.
- The UI adds Chinese primary labels around those technical values and keeps
  raw protocol values in small technical labels inside expanded details.
- Chat, answer cards, workflow collapsed summaries, Agents overview, and
  Settings default view should not prominently display backlog/readiness wording
  such as pending implementation, provider missing, external not ready, or live
  verification status.
- Workflow technical details, Settings advanced diagnostics, docs, and tests
  retain the true provider/external/readiness boundary.

This is not a full runtime locale switch and does not change backend topology,
agent roster, provider/search readiness, external service readiness, or
business-agent correctness.

## Current R5-C1 Business Copy Boundary

R5-C1 keeps the R5-C disclosure model but professionalizes the remaining
default user-facing copy that still read like implementation notes.

- Dimension group summaries should describe value, market, risk, and macro
  analysis in business language, not DAG wiring or which agent feeds which
  composite.
- Step summaries should describe what the step helps the user understand, not
  screenshot fixtures, rosters, paths, metadata, or transcript boundaries.
- Assistant answer-card evidence is labeled as "研判依据" with business items
  such as "分析框架", "用户问题", and "流程记录".
- Raw enum values and protocol ids may remain in expanded technical details,
  but they should not be the primary explanation in the default chat surface.

R5-C1 does not change `workflow_snapshot_v2`, fixed DAG topology, the 27-agent
roster, runtime bindings, provider/search readiness, external service
readiness, or business-agent correctness.

## Current R6-B Frontend Quality Boundary

R6-B does not redesign the frontend UI. It changes the default reset quality
gate so frontend validation runs through `scripts/quality/run_quality.py
--mode frontend`:

- TypeScript no-emit check:
  `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`
- Frontend smoke test: `npm --prefix apps/web run test`
- Vite build with a temporary repo-external `--outDir`

The default reset mainline must not write `apps/web/dist`, must not run browser
screenshot capture, and must not imply provider/live/external/demo readiness.

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

## R5-B2.6 Done

- visible sidebar, thread, assistant, composer, workflow, Agents, and Settings
  copy localized to Chinese
- WorkflowPanel labels, status labels, empty states, result metadata labels,
  and provenance copy polished over the same `workflow_snapshot_v2` payload
- fixed DAG deterministic public answer and workflow summaries localized over
  the then-current validation boundary
- frontend smoke expectations, mocks, and screenshot fixture copy aligned to
  the localized public UI
- raw technical ids and enum values kept visible in inspector/debug contexts

## R5-C Done

- Chat empty state now reads as a Chinese capital-market research entry point
  and offers example questions.
- The degraded/local-mode notice is softened and no longer lists provider/search
  diagnostics in the main chat surface.
- Assistant answers and workflow collapsed summaries use product-facing fixed
  DAG研判流程 copy.
- Workflow raw enum values remain available only after expanding details and are
  rendered as small technical labels.
- Agents page defaults to layer and dimension capability summaries, with the
  detailed agent list behind a disclosure.
- Settings defaults to runtime, continuity, and storage status; provider/search
  and checkpointer details live under advanced diagnostics.

## R5-C1 Done

- Dimension group copy now uses business descriptions for value, market, risk,
  and macro dimensions.
- Step summaries in frontend mocks, screenshot fixtures, and public workflow
  output no longer use fixture, roster, path-wiring, metadata, or transcript
  explanations as user-facing copy.
- Assistant answer cards now show "研判依据" with "分析框架", "用户问题", and
  "流程记录" evidence items.
- Frontend smoke assertions guard against those engineering terms reappearing
  in default user-visible surfaces.

## R6-B Done

- The default reset quality mainline now includes the frontend gate after
  static, unit, public API, and graph smoke checks.
- The frontend gate runs TypeScript no-emit, smoke tests, and a repo-external
  temporary build output directory.
- `fusion-gate`, provider live smoke, external invoke checks, demo stack, and
  screenshot capture remain manual/live/archived paths outside the default
  frontend quality gate.

## Deferred Work

- visual dependency graph beyond ordered execution batches
- evidence-specific drilldown once backend public evidence cards are formalized
- production auth and rate limits
- persistent run history
- deployment hardening
