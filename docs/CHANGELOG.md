# Changelog

Historical changelog entries before this reset branch are preserved by tag
`pre-fixed-dag-reset-20260604-1457`.

## 2026-06-04 - Phase R5-B1 frontend DAG contract migration

### Changed

- Changed frontend workflow/chat types to consume `workflow_snapshot_v2` with
  `finalSource=reset_skeleton`.
- Changed the streaming placeholder and `workflow.stage` merge path to use
  fixed DAG stages: planning, evidence, L2 analysis, dimension composite,
  decision, and report.
- Changed the existing WorkflowPanel subviews to render a minimal DAG summary
  from `stages`, `dagSteps`, `dimensionGroups`, `executionBatches`,
  `completedSteps`, and public provenance.
- Changed frontend mocks to use the 27 enabled `snake_case` fixed DAG catalog
  and v2 workflow snapshot fixtures.
- Changed frontend smoke tests to assert the fixed DAG contract and transcript
  boundary instead of the old layer/fusion/source model.

### Validated

- `npm --prefix apps/web run test`
- `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`

### Not Done

- No complete R5-B2 WorkflowPanel UI rewrite.
- No Python backend contract, executor, catalog, or runtime binding change.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No external HTTP candidate was enabled or live verified.
- No `/api/agents` runtime binding field exposure.
- No production auth, rate-limit, HTTPS, deployment, persistence, or
  observability claim.
- No push.

## 2026-06-04 - Phase R4-C legacy registry boundary cleanup

### Added

- Added `src/react_agent/agent_types.py` as the no-legacy-import home for shared
  `AgentInput` and `AgentOutput` typing.
- Added `src/react_agent/legacy_agent_registry.py` as the explicit compatibility
  home for historical `AGENT_METADATA`, `AGENT_TOOLS`, metadata loading,
  sorting, and registration helpers.
- Added `src/react_agent/external_http_config.py` as configuration-only retained
  external candidate metadata for fixed-DAG binding validation.
- Added import-boundary coverage proving `react_agent.graph` does not load
  legacy registry/bootstrap/default/generic/external-wrapper implementation
  modules.

### Changed

- Changed `src/react_agent/graph.py` to avoid legacy bootstrap and old registry
  globals on the active fixed-DAG graph import path.
- Changed `src/react_agent/agents.py` into a shared typing facade with lazy
  compatibility exports for legacy registry names.
- Changed legacy catalog, disabled-agent, placeholder, and compatibility tests
  to target `legacy_agent_registry.py` and `graph_bootstrap.py` explicitly.
- Changed public workflow title mapping to use the fixed DAG catalog rather
  than old `config/agents/*.json` metadata.
- Changed fixed DAG runtime binding validation to read external candidate
  metadata from the config-only module instead of the HTTP wrapper module.

### Removed

- Removed `src/react_agent/external_valuation_agents.py` after valuation tests
  migrated to the retained generic `external_http_agents.py` wrapper.
- Removed unreferenced `src/react_agent/json_utils.py`.

### Not Done

- No real business-agent algorithm implementation.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No external HTTP candidate was enabled or live verified.
- No deletion of `config/agents/*.json`.
- No R5 frontend workflow UI rewrite.
- No R6 mainline/fusion/provider readiness rebuild.
- No push.

## 2026-06-04 - Phase R4-B fixed DAG runtime binding registry

### Added

- Added `config/fixed_dag/runtime_bindings.json` as the backend runtime binding
  source for the same 27 fixed DAG `snake_case` agents.
- Added `src/react_agent/fixed_dag_runtime_registry.py` with runtime binding
  loading, validation, grouping, summary, external-candidate lookup, and step
  result annotation helpers.
- Added tests covering runtime binding schema/count/id alignment, forbidden
  primary ids, disabled external candidates, legacy wrapper mapping alignment,
  sentiment market-only routing, and executor annotation.

### Changed

- Changed `fixed_dag_step_result_v1` construction to annotate each executed
  step with runtime binding metadata: `runtime_kind`,
  `implementation_status`, `binding_source`, `legacy_agent_id`,
  `external_agent_id`, `invoke_enabled`, and `live_verified`.
- Changed graph and public workflow tests to prove binding annotation remains
  metadata-only and does not call providers or external HTTP.
- Strengthened `/api/agents` tests to confirm the public catalog schema remains
  unchanged and does not expose runtime binding internals.
- Updated reset docs to record R4-B runtime binding ownership and later R4-C/R5/R6
  boundaries.

### Not Done

- No real business-agent algorithm implementation.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No external HTTP candidate was enabled or live verified.
- No R4-C legacy aNN config cleanup.
- No R5 frontend workflow UI rewrite.
- No R6 mainline/fusion/provider readiness rebuild.
- No push.

## 2026-06-04 - Phase R4-A fixed DAG catalog source and public projection

### Added

- Added `config/fixed_dag/agent_catalog.json` as the active reset backend
  catalog source for the 27 formal `snake_case` fixed DAG agents.
- Added `src/react_agent/fixed_dag_catalog.py` with stdlib-only catalog loading,
  validation, grouping helpers, and public catalog projection.
- Added catalog tests covering schema, counts, duplicate ids, legacy aNN id
  rejection, sentiment market-only routing, risk-composite exclusion of
  sentiment, and public projection counts.

### Changed

- Changed fixed DAG roster constants to derive from the fixed DAG catalog.
- Changed public `/api/agents` to project the fixed DAG 27-agent catalog through
  the existing `AgentCatalogResponse` shape.
- Changed public API catalog tests from old `27/25/aNN` config semantics to
  reset `27/27/snake_case` semantics.
- Updated reset docs to mark old `config/agents/*.json` as legacy migration
  input, not active reset public catalog truth.

### Not Done

- No real business-agent algorithm implementation.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No external endpoint mapping adapter.
- No R4-C legacy aNN config cleanup.
- No R5 frontend workflow UI rewrite.
- No R6 mainline/fusion/provider readiness rebuild.
- No push.

## 2026-06-04 - Phase R3.6 safe dead-file cleanup and R4 Excel baseline

### Added

- Added `新架构_固定DAG_最终分层级智能体表_v4_反馈修正版.xlsx` as the R4
  `snake_case` catalog/runtime registry input workbook.

### Removed

- Removed high-confidence dead local artifacts and legacy fixtures that were not
  active quality or runtime entry points.

### Changed

- Updated reset docs to record the R3.6 cleanup boundary and non-claims.

### Not Done

- No R4 catalog/runtime registry migration.
- No R5 frontend DAG workflow UI rewrite.
- No R6 mainline/fusion/provider readiness rebuild.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No deletion of `config/agents`, external wrappers, baseline/fusion regression
  inputs, `assets/reference`, or historical `log/tmp/outputs` artifacts.
- No push.

## 2026-06-04 - Phase R3 plan-driven fixed DAG execution

### Added

- Added `src/react_agent/fixed_dag_executor.py` with deterministic DAG
  validation, topological batching, step result construction, plan execution,
  and execution result validation.
- Added `fixed_dag_execution_v1` and `fixed_dag_step_result_v1` runtime
  contracts.
- Added workflow projection for `executionBatches` and `stepResults`.
- Added unit and integration coverage for dependency validation, invalid-plan
  fallback, executor output, graph integration, and public workflow mapping.

### Changed

- Changed the active graph edge path to
  `route_planner -> prepare_l1_context -> execute_fixed_dag -> final_emit ->
  memory_update`.
- Changed public workflow contracts and mapping to include executor trace fields
  while keeping the transcript as a single assistant answer.
- Changed the final reset bundle to include `dag_execution`, `dag_step_results`,
  and `execution_batches`.
- Updated reset docs for R3 execution orchestration and later R4/R5/R6
  ownership.

### Not Done

- No business-agent algorithm implementation.
- No provider, search, or external live verification.
- No frontend workflow UI rewrite.
- No snake_case catalog/runtime registry migration.
- No mainline or fusion-gate artifact-writing validation.
- No push.

## 2026-06-04 - Phase R2 contract and function seam hardening

### Added

- Added deterministic constructors, normalizers, and validators for fixed DAG
  plan, L1 bundles, L2 conclusions, L3 composites, L4 decision/report, workflow
  snapshot, and final emit bundles.
- Added authoritative roster partition constants for L1, L2, L3, L4, and
  value/market/risk/macro dimensions.
- Added unit coverage for R2 contract invariants, sentiment market-only routing,
  risk-composite exclusion of sentiment, public workflow fallback, and graph
  final bundle shape.

### Changed

- Changed graph nodes to consume contract/function seams instead of scattering
  payload fields in node bodies.
- Changed public workflow fallback mapping to reuse `build_workflow_snapshot_v2`
  so dimension groups remain stable.
- Updated reset docs to describe R2 seam hardening and later R4/R5/R6 ownership.

### Not Done

- No provider, search, or external live verification.
- No frontend workflow UI rewrite.
- No snake_case catalog/runtime registry migration.
- No real business agent algorithm implementation.
- No mainline or fusion-gate artifact-writing validation.
- No push.

## 2026-06-04 - Phase R1-B-Delta fixed DAG roster alignment

### Changed

- Aligned the active reset roster with the v4 feedback table: 27 formal agent
  ids with L1=3, L2=18, L3=4, and L4=2.
- Removed the enterprise financial analysis target from the fixed-DAG runtime
  skeleton.
- Moved `sentiment_company_radar` to the market dimension and limited its output
  route to `market_composite`.
- Renamed the L3 value dimension composite from the earlier fundamental wording
  to `value_composite`.
- Updated reset docs and tests to reject the stale pre-delta target-count,
  L2-count, and sentiment-to-risk wording.

### Not Done

- No real business agent implementation.
- No provider, search, or external live verification.
- No frontend v2 workflow rewrite.
- No production deployment hardening.

## 2026-06-04 - Phase R1-B fixed DAG runtime protocol skeleton

### Added

- Added `src/react_agent/fixed_dag_contracts.py` with deterministic reset
  contracts and `workflow_snapshot_v2` builder.
- Added fixed-DAG parser tests, contract tests, graph skeleton tests, and public
  workflow v2 tests.

### Changed

- Replaced active `src/react_agent/graph.py` routing with the deterministic
  skeleton:
  `route_planner -> prepare_l1_context -> run_l2_conclusions ->
  run_dimension_composites -> decision_synthesizer -> report_generator ->
  final_emit -> memory_update`.
- Changed router prompt/parser surfaces from old route-mode planning to
  `fixed_dag_plan_v1`.
- Changed Python public workflow contracts from layer/mode/fusion fields to DAG
  stages, steps, dimension groups, provenance, and `reset_skeleton` final source.
- Updated reset docs to describe R1-B runtime scope and non-claims.

### Not Done

- No real business agent implementation.
- No provider, search, or external live verification.
- No frontend v2 workflow rewrite.
- No production deployment hardening.
- No mainline or fusion-gate artifact-writing validation.

## 2026-06-04 - Phase R1-A hard slimming reset baseline

### Removed

- Removed old Agent Catalog v2 documentation and replacement runbooks.
- Removed old mainline audit, A01 contract/SFT, route-prior/RARP, Router-SFT,
  external integration, archive, and handoff docs.
- Removed archive tests for route-prior, router eval, and A01 SFT.
- Removed route-prior helper source and its offline regression bundle.
- Removed Router-SFT data, A01 SFT data, Router-SFT tools, old router regression
  scripts, and SFT train/eval requirements.
- Removed old external-agent scaffold package and generated zip.

### Added

- Added reset documentation set:
  - `docs/ARCHITECTURE_FIXED_DAG.md`
  - `docs/CONTRACTS.md`
  - `docs/FRONTEND_V2.md`
  - `docs/QUALITY.md`
  - `docs/DECISIONS.md`
- Added reset-focused docs test coverage.

### Changed

- Rewrote `README.md`, `AGENTS.md`, `docs/INDEX.md`, and `docs/SYSTEM_MAP.md`
  for the reset branch.
- Updated static quality documentation targets so they no longer reference
  deleted docs.

### Not Done

- No runtime graph rewrite in R1-A.
- No prompt/parser/state/public workflow deletion in R1-A.
- No Fair Fusion or baseline sidecar deletion in R1-A.
- No frontend v2 rewrite.
- No provider or external live verification.
- No push.
