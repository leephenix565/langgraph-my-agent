# Changelog

Historical changelog entries before this reset branch are preserved by tag
`pre-fixed-dag-reset-20260604-1457`.

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
