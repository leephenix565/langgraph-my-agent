# Frontend V2 Boundary

This document describes the frontend boundary for the Fixed DAG reset.

## Product Boundary

The public chat remains a single user and assistant transcript. Internal DAG
execution belongs in a workflow inspector, not in separate public agent chat
lanes.

The assistant answer card may include structured `sections`, `evidenceCards`,
and `limitations` copied from `report_result_v1`. These fields are public-safe
report rendering material. They must not expose raw graph messages, raw agent
JSON, endpoint URLs, provider raw responses, or secrets, and they do not create
separate public agent chat lanes.

For selected-routing turns, answer-card sections are route-aware. Dimensions
outside the selected scope may be intentionally absent from active sections and
shown only as uncovered scope or limitations.

## Current Router M2 Public Selected-Routing Request Boundary

The public HTTP/Web surface exposes selected routing as a per-message,
default-off composer option. The visible control is labeled "选择路由（默认关闭）".

When the control is off, the frontend omits the request `routing` field. If a
client sends `routing: null`, the backend treats it the same way. Both cases
preserve the current server default.

When the control is on, the frontend sends the only supported public routing
request shape:

```json
{
  "text": "...",
  "structuredInput": {},
  "routing": {
    "mode": "selected"
  }
}
```

The sync and streaming message routes use the same request contract. The
backend maps `routing: {"mode": "selected"}` to
`Context(enable_selected_routing=True)` for that request. If the server runs
with `PUBLIC_SELECTED_ROUTING_DEFAULT=1`, omitted/null `routing` also follows
the selected-routing server default; otherwise omitted/null `routing` keeps the
full-DAG default. It does not expose an explicit public `full_dag` force-off
mode, provider-router controls, `/v1/agent/invoke` controls,
`/v1/agent/compute` controls, model/base URL/API key controls, env controls,
runtime binding changes, catalog changes, or non-L4 policy changes.

The rendered answer card must not imply full four-dimension coverage for a
selected request. Unselected dimensions are represented as not covered in this
turn and require a full-DAG request or another selected request to analyze.

Selected-routing observability remains response-side provenance. The frontend
may display the public-safe `workflow_snapshot_v2.provenance` fields such as
`selectedRoutingRequested`, `selectedRoutingFallback`, `selectedDimensions`,
and provider-router status flags, but it must not display raw route intent,
raw selected plans, raw provider responses, raw graph messages, endpoint URLs,
env values, secrets, tracebacks, or chain-of-thought.

## Topic2 Midterm RC1 Profile Display Boundary

`MIDTERM_SUBSET_PROFILE` is server-side only for RC1. The public request shape
does not gain a `profile`, `selectedAgents`, or arbitrary agent-id field, and
the frontend does not need to change its send-message contract to enable the
profile.

When the backend runs with
`FIXED_DAG_DEPLOYMENT_PROFILE=midterm_subset`, normal public sends can return a
selected workflow whose provenance has `selectedRoutingRequested=true`,
`selectedRoutingFallback=false`, `routeGranularity="agent_profile"`, and
`selectedDimensions=["value","market","risk","macro"]`. Existing routing badges
and workflow panels may display that as selected/profile-scoped analysis, but
they must not show deferred agents as active analysis steps if those agents are
not present in `dagSteps`.

The profile is a deployment/runtime selection boundary. It does not expose
compute endpoints, invoke controls, provider settings, env values, raw route
plans, raw graph state, or internal agent JSON to the browser.

## Current Loading UX and Routing Badge Display (2026-07-03)

### Loading Progress

While the graph executes (30-85s typical), the answer card shows:

- An **animated pulse indicator** (three dots with staggered fade animation)
- The **current workflow stage name** and description (规划、证据接入、并行分析等)
- A **step progress counter** (e.g. "12/27 个步骤已完成") when `dagSteps` are available
- These are visible in the default collapsed view; the thought chain progress
  bar remains available on expansion.

The answer text is "正在协作…" as a streaming placeholder until the final
report is ready. The loading view does not show an estimated time remaining.

### Routing Badge

The answer card header (above the report body) displays a **routing badge**:

- Default full DAG: `"全量分析"` in a neutral chip
- Explicit selected routing: `"选择路由：value、risk"` with dimension-specific
  colored chips (`value` blue, `market` amber, `risk` red, `macro` green)
- Selected routing with fallback: `"⚠ 选择路由未稳定完成，已回退到全量分析"`
  in an amber warning chip

The badge reads from `workflow_snapshot_v2.provenance`:
`selectedRoutingRequested`, `selectedRoutingFallback`, `selectedDimensions`.

### Uncovered Dimensions

When selected routing covers fewer than four dimensions, an "未覆盖维度" chip
appears below the routing badge listing the excluded dimensions
(e.g. "未覆盖维度：market、macro"). This is derived client-side from
`selectedDimensions` and the static four-dimension set. The chip includes a
note "基于分析范围推断。"

### History Session Badge

Routing mode is not displayed in the sidebar session list. The
`ChatSessionSummary` model does not carry `provenance`. Routing mode is only
visible on message cards within a session.

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
  -> optional routing: {"mode": "selected"} when the composer toggle is on
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

## Router M2 Public Selected-Routing API Done

- Composer adds a per-message explicit selected-routing toggle.
- The frontend omits `routing` while the toggle is off and sends
  `routing: {"mode": "selected"}` while it is on. When omitted, backend
  behavior follows the server default advertised by `/api/health`.
- Sync and streaming sends share the same typed request behavior.
- Frontend smoke covers toggle visibility, omitted-routing serialization, and
  selected request serialization.
- The UI does not expose `full_dag`, provider-router, compute, invoke, model,
  base URL, API key, env, runtime-binding, catalog, or non-L4 policy controls.

## R7-I.7 Done — Layer-Based Thought-Chain Progress

- Progress bar switched from 27-step granularity to L1/L2/L3/L4 layer counting.
  Label reads "研判流程 · 3/4 层处理中" instead of "研判流程 · 25/27 个任务处理中".
- Dimension agent members without stance/confidence data are hidden entirely
  instead of showing "待分析" badges.
- Dimension cards grid changed from single-column to responsive auto-fit with
  `minmax(280px, 1fr)`, displaying 4 dimension cards in 2 columns on wider
  screens.
- `dimensionTitle` now correctly uses backend `group.title` when available.
- `detailSummary` deduplicates identical step descriptions before joining.
- Backend `_dimension_group_summary` produces dynamic dimension summaries
  (e.g. "综合positive_watch，基于 3 个成员分析线索。") instead of hardcoded
  "维度综合结果。" or "汇总单一维度的分析结论，形成维度判断。".
- All dimension agents shown (removed `slice(0, 3)` limit on member list).
- No `7-I.7` impacts on backend graph, catalog, runtime bindings, or agent
  services.

### Tests

- Frontend smoke, TypeScript typecheck (`tsc --noEmit`), and full unit test
  suite pass (470 passed, 0 new failures).

## R7-I.8 Done — Report Content Formatting

- Added `_format_report_paragraphs()` in `public_mapping.py` that splits
  agent-generated report text at semantic markers (业务判断, 覆盖限制,
  风险提示, 关键证据, etc.), converting them to `**bold**` Markdown headings
  separated by `\n\n` paragraph breaks. Used for both `answer` and each
  `section.content`.
- Marker patterns auto-derived from `AGENT_TITLE_LABELS` for all 27 agent
  names plus sub-markers (关键证据, 业务指标, 驱动因素, 研究判断引用).
- When no markers are found, sentences are grouped into paragraphs of 3 per
  group as a fallback.
- Text shorter than 30 chars is not processed.
- No frontend changes required — ReactMarkdown renders the added `**bold**`
  and `\n\n` naturally.

### Tests

- `test_public_mapping_fixed_dag.py` 6 passed; `test_fixed_dag_external_adapter.py`
  53 passed; `test_fixed_dag_contracts.py` 46 passed.
- Frontend smoke assertions updated for new paragraph layout.

## R7-I.9 Done — Report Layout and Section Rendering

- Assistant card widened from `42rem` (672px) to `48rem` (768px) for better
  Chinese text line length.
- Body text increased to 15px, line-height 1.9, paragraph gap 12px for dense
  financial report readability.
- `AnswerCardModel.sections` (up to 7 structured sections with titles and
  content) now rendered as distinct bordered cards below the answer body,
  each with a bold title and Markdown-rendered content.
- `AnswerCardModel.evidenceCards` now rendered as blue-tinted card grid below
  citations (previously the data was sent but never rendered).
- Citations redesigned from cramped left-border list to multi-column
  (`auto-fit, minmax(200px,1fr)`), rounded border, card-style display.
- Message list padding increased from 16px to 24px for more breathing room.
- Backend `_convert_bold_headers_to_markdown_headings()` converts
  `**Section Title**: content` pattern at paragraph starts to `## heading`
  plus new paragraph, giving reports proper visual hierarchy via CSS heading
  styles.

## R8-13Q Done — External Adapter Envelope Compatibility

- `validate_external_compute_envelope` now accepts both
  `external_agent_compute_v0` and `external_agent_response_v0` envelope
  schema versions. Previously only `compute_v0` was accepted, causing 3 risk
  agents that return `response_v0` to be rejected at the envelope level.
- Non-L4 production compute policy L2 concurrency raised from 4 to 20,
  allowing all 15 deployed L2 agents to run in parallel without queuing.
  All agent timeouts raised from 20s to 30s for completion headroom.
- Quality summary text revised from "L2 完成 7/18" to "L2 已获取 14/18 个
  agent 数据（9 完全完成 + 5 降级参考）" for more accurate reporting.
- These changes do not modify the public API schema, runtime bindings,
  agent catalog, graph topology, or selected-routing behavior.
- Expected max L2 coverage: 14/18 agents with data (9 complete + 5 partial),
  limited by 3 undeployed agents and 1 with IPO-only data scope.

### Production Agent Service Repairs (outside git)

- `risk_identification` (port 10010): agent_id changed from `risk_rule_reasoning`
  to `risk_identification` to match policy. Restarted.
- `market_ipo_investor_behavior` (port 10008): added `/v1/agent/compute` compute
  endpoint. Agent_id aligned to `market_ipo_investor_behavior`. Restarted.
- `market_capital_flow_chip` (port 10022): service had stopped. Restarted.
- `market_composite` (port 10023): service had stopped. Restarted.

### Not Done

- 3 L2 agents remain undeployed: `market_fund_manager_behavior`,
  `macro_sentiment`, `macro_industry_hotspot`.
- `market_ipo_investor_behavior` can only serve IPO-stage companies, not
  fully traded stocks.
- No API contract version bump, no graph topology change, no catalog change,
  no runtime binding change.

## Deferred Work

- visual dependency graph beyond ordered execution batches
- evidence-specific drilldown once backend public evidence cards are formalized
- production auth and rate limits
- persistent run history
- deployment hardening
