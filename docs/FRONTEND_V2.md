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

## Current R7-I Report-First Thought Chain Boundary

R7-I adds a report-first presentation surface for user A style demos. The
assistant answer still renders the natural-language report in the main answer
body, and the new "研判思维链" disclosure sits below that answer as a
public-safe process summary.

R7-I.4 aligns that surface with the reference HTML dynamic stage model: while
the workflow is still progressing and the assistant answer is still the
streaming placeholder, the main answer body shows a public-safe pending answer
state. Once the final answer exists, the primary Markdown body shows the final
natural-language report and the thought chain remains only for traceability.

- The disclosure is derived only from the existing `workflow_snapshot_v2`
  payload: `stages`, `currentStage`, `completedSteps`, `dagSteps`,
  `dimensionGroups`, `stepResults`, `provenance`, and `finalSource`.
- The six public stages are product labels over existing fixed DAG stages:
  "问题理解", "证据接入", "并行分析", "维度综合", "决策生成", and
  "文字报告输出".
- The report output remains in the assistant answer body. The thought-chain
  disclosure explains the process and does not add a side report card,
  document export action, or extra public agent lane.
- The expanded thought chain is a stage-driven answer-formation display:
  progress band, stage rail, current-stage detail, evidence strip, and
  "四维流程信号" row are derived from the current workflow stage and snapshot
  content.
- The four-dimension row is a workflow-stage-derived process/presentation
  signal. It is not a value/market/risk/macro business-agent conclusion, live
  market data, investment advice, real confidence score, or external service
  result.
- In a report-complete snapshot, earlier stages are shown as included/complete
  by stage order; placeholder implementation state remains confined to the
  technical WorkflowPanel rather than the default user-facing thought chain.
- The expanded thought-chain state includes a derived stage progress band and
  a larger report-first process panel; it does not introduce new backend fields
  or claim token/provider/external-service progress.
- R7-I.7 makes the thought chain the default workflow surface for normal users.
  The existing WorkflowPanel remains available behind a secondary "技术流程详情"
  disclosure for raw ids, runtime enum values, execution batches, selected step
  metadata, and provenance details.
- The disclosure must not expose hidden chain-of-thought, provider raw
  responses, external raw responses, raw graph messages, manager assignment
  JSON, endpoint URLs, env var values, secrets, traceback, or raw agent JSON.

R7-I does not change `workflow_snapshot_v2`, backend topology, fixed DAG roster,
runtime bindings, provider/search readiness, external service readiness,
external invocation, demo stack acceptance, or business-agent correctness.

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

## R7-I Done

- Assistant answer cards now keep the report text as the primary answer and add
  a collapsed "研判思维链" disclosure below it.
- The disclosure maps the existing workflow snapshot to six public-safe stages,
  current-stage detail, four dimension summaries, and provenance copy.
- Report-complete UX now points users back to the main assistant answer for the
  report body and avoids waiting-state labels on intermediate stages.
- Expanded thought-chain UX now uses a larger process panel with a derived
  stage progress band and full-width dimension summary area.
- R7-I.4 aligns the panel with the demo's dynamic answer-formation model:
  streaming placeholders render as "正在组织研判答案", current stages drive the
  process detail/evidence strip, early stages keep dimension signals in a
  waiting state, and final answers stay in the main assistant Markdown body.
- The existing WorkflowPanel remains available as the technical fixed DAG
  inspector.
- Frontend smoke covers the report-first answer, collapsed/expanded thought
  chain, six stage labels, and default-surface leakage guards.

## Deferred Work

- visual dependency graph beyond ordered execution batches
- evidence-specific drilldown once backend public evidence cards are formalized
- production auth and rate limits
- persistent run history
- deployment hardening
