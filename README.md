# langgraph-my-agent

This branch is the Fixed DAG reset branch. It replaces the old route-mode,
Router-SFT, route-prior, A01 contract dispatch, and Fair Fusion mainline with a
smaller deterministic fixed-DAG runtime skeleton.

Phase R3 upgrades the reset skeleton to plan-driven fixed-DAG execution. Phase
R4-A adds the fixed DAG catalog source and switches the backend public
`/api/agents` projection to the 27 `snake_case` reset agents. Phase R4-B adds
the fixed DAG runtime binding registry for deterministic, external-candidate,
and pending-placeholder runtime metadata. Phase R4-C isolates the legacy aNN
registry/bootstrap from the active fixed-DAG graph import path. Phase R5-B1
migrates the existing web frontend contract to `workflow_snapshot_v2`. Phase
R5-B2 rewrites the existing web workflow inspector around that fixed DAG
snapshot so stages, batches, dimensions, step result metadata, final source,
and provenance render as inspector data rather than public transcript content.
The runtime validates
`dag_steps[].depends_on`, computes deterministic `execution_batches`, emits
per-step `step_results`, and remains a provider-free placeholder skeleton. It
is not a completed business analysis engine.

## Current Branch Scope

- Branch: `reset/fixed-dag-v1`.
- Reset base: `pre-fixed-dag-reset-20260604-1457`.
- Current phase: R5-B2 workflow DAG inspector UI rewrite.
- Current runtime milestone: R3 plan-driven fixed DAG execution orchestration.
- Runtime entry: `langgraph.json -> src/react_agent/graph.py:graph`.
- Public Python workflow contract: `workflow_snapshot_v2`.
- Public agent catalog: fixed DAG 27-agent `snake_case` projection from
  `config/fixed_dag/agent_catalog.json`.
- Public web shell: migrated in place to consume the fixed DAG public contract;
  the current WorkflowPanel renders the R5-B2 fixed DAG inspector from
  `workflow_snapshot_v2`.
- Production status: not a production deployment claim.

Historical material removed on this branch remains recoverable from the
pre-reset tag. Do not use old Agent Catalog v2 docs, route mode docs,
route-prior/RARP material, Router-SFT material, A01 SFT material, or Fair Fusion
docs as current reset authority.

## Active Runtime Skeleton

The active graph is now deterministic and provider-free:

```text
user input
  -> route_planner
  -> prepare_l1_context
  -> execute_fixed_dag
  -> final_emit
  -> memory_update
```

`execute_fixed_dag` walks the 27-agent `fixed_dag_plan_v1` by validated
dependencies, produces topological batches, records per-step execution results,
and fills the L2/L3/L4 placeholder result contracts.

The reset target has 27 formal agent ids:

- L1 planning/evidence seams: 3 target ids.
- L2 conclusion placeholders: 18 target ids.
- L3 dimension composites: 4 target ids.
- L4 decision/report: 2 target ids.

The v4 feedback-aligned roster removes the enterprise financial analysis target.
`sentiment_company_radar` belongs to the market dimension and routes only to
`market_composite`; it is not a direct risk-composite input in this reset
runtime.

See `docs/ARCHITECTURE_FIXED_DAG.md` for the current skeleton map.

## Active Agent Catalog

R4-A makes the fixed DAG catalog the active backend catalog source:

- `config/fixed_dag/agent_catalog.json`
- `src/react_agent/fixed_dag_catalog.py`

The catalog is aligned to the v4 feedback workbook:

- `新架构_固定DAG_最终分层级智能体表_v4_反馈修正版.xlsx`

The public `/api/agents` endpoint now projects 27 enabled `snake_case` reset
agents with layer counts L1=3, L2=18, L3=4, L4=2. Its public shape remains
compatible with the existing `AgentCatalogResponse`, but in R4-A
`configCount`, `runtimeCount`, and `disabledIds` describe the fixed DAG reset
catalog, not the old aNN config catalog.

## Active Runtime Bindings

R4-B adds a backend-only runtime binding source:

- `config/fixed_dag/runtime_bindings.json`
- `src/react_agent/fixed_dag_runtime_registry.py`

The binding registry covers the same 27 fixed DAG ids as the active catalog and
records how each id currently maps to one of these runtime categories:

- deterministic skeleton seams
- external HTTP candidates
- pending placeholders

External HTTP candidates are disabled by default and are not live verified.
Legacy aNN ids may appear only as `legacy_agent_id` migration notes, never as
primary reset ids. Endpoint URLs and env var names are registry metadata for
later adapter work; R4-B does not call them.

The executor annotates `fixed_dag_step_result_v1` records with binding metadata
such as `runtime_kind`, `implementation_status`, `binding_source`,
`legacy_agent_id`, `external_agent_id`, `invoke_enabled`, and `live_verified`.
It does not include endpoint URLs or env var values in step results.

## Current Runtime Boundary

R3/R4-C keeps the graph deterministic and routes graph/public fallback
construction through contract, executor, and public mapping seams:

- `src/react_agent/fixed_dag_contracts.py`
- `src/react_agent/fixed_dag_executor.py`
- `src/react_agent/fixed_dag_runtime_registry.py`
- `src/react_agent/graph.py`
- `src/react_agent/prompts.py`
- `src/react_agent/router_parse.py`
- `src/react_agent/state.py`
- `src/react_agent/agent_types.py`
- `src/react_agent/public_contracts.py`
- `src/react_agent/public_mapping.py`
- `src/react_agent/public_runtime.py`
- `src/react_agent/public_api.py`

The graph state now carries `dag_execution`, `dag_step_results`, and
`execution_batches` in addition to the reset result contracts. R4-B step
results include runtime binding metadata for workflow inspection, but this does
not mean any external service was invoked.

R4-C adds an explicit legacy boundary:

- `src/react_agent/legacy_agent_registry.py` owns historical `AGENT_METADATA`
  and `AGENT_TOOLS`.
- `src/react_agent/graph_bootstrap.py` is legacy-only compatibility bootstrap.
- `src/react_agent/agents.py` keeps shared typing and lazy compatibility
  exports, but active fixed-DAG state imports types from `agent_types.py`.
- `config/agents/*.json` remains as migration/readiness input only.
- `src/react_agent/external_http_config.py` keeps offline external candidate
  metadata; `src/react_agent/external_http_agents.py` remains retained wrapper
  infrastructure, not live-verified runtime.

Importing `react_agent.graph` must not import or execute legacy bootstrap,
`AGENT_TOOLS`, default LLM/search placeholder registration, generic agent
registration, or HTTP wrapper implementation modules. `config/agents/*.json` is
still retained, but it is no longer the active reset public catalog or runtime
registration truth.

## Previous R3.6 Cleanup Boundary

R3.6 removed high-confidence dead local artifacts and legacy test fixtures that
were not active entry points, and added the v4 feedback workbook to the repo:

- `新架构_固定DAG_最终分层级智能体表_v4_反馈修正版.xlsx`

That workbook is the R4 baseline input for the `snake_case` catalog/runtime
registry. R4-A adds the backend catalog source and public projection. R3.6 did
not delete the old aNN catalog/config files, the existing web workflow
implementation, external wrapper production code, baseline/fusion regression
inputs, or tracked historical benchmark/trace artifacts that still need an
archive policy.

## Public Transcript Boundary

The product keeps a single assistant transcript. Internal graph steps, raw graph
messages, manager assignments, agent JSON, and provider raw responses must not
be treated as public transcript content.

The workflow inspector is a diagnostic panel. The Python public adapter projects
DAG stages, steps, dimensions, provenance, and final source as
`workflow_snapshot_v2` through reset contract seams. R3 also exposes
`executionBatches` and `stepResults` for the inspector. R4-B adds binding
metadata to `stepResults`. R5-B1 updates the frontend workflow/chat types,
streaming placeholder, mocks, and smoke fixtures to consume this public shape.
R5-B2 renders stage timeline, execution batches, dimension groups, selected
step result metadata, final source, and provenance in the inspector while
preserving the single user/assistant transcript boundary.

## Documentation Index

- `docs/INDEX.md` - reset documentation map.
- `docs/SYSTEM_MAP.md` - active runtime topology and phase map.
- `docs/ARCHITECTURE_FIXED_DAG.md` - fixed DAG skeleton and target ids.
- `docs/CONTRACTS.md` - runtime/public contract payload boundaries.
- `docs/FRONTEND_V2.md` - frontend/public transcript boundary.
- `docs/QUALITY.md` - safe quality commands for the reset branch.
- `docs/DECISIONS.md` - reset architecture decisions.
- `docs/CHANGELOG.md` - reset branch changelog.

## Safe Local Validation

Use the project conda environment when available:

```powershell
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent tests scripts/quality
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_public_api.py
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_graph.py
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
npm --prefix apps/web run test
npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json
```

Do not use successful tests as production readiness evidence.

## Explicit Non-Claims

- No provider or live external service was verified by
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2.
- No `external /v1/agent/invoke` call is part of
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2 validation.
- No demo stack startup is part of R3/R4-A/R4-B/R4-C/R5-B1/R5-B2 validation.
- No real business algorithms for individual agents are implemented in
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2.
- R5-B2 completes the frontend inspector UI rewrite only; it does not change
  backend executor semantics, provider readiness, external readiness, or
  business-agent correctness.
- No mainline or fusion-gate reset quality gate is rebuilt in
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2.
- R4-C isolates legacy registry/bootstrap but does not delete
  `config/agents/*.json` or live-verify external candidates.
- No production auth, rate limit, HTTPS, deployment, or observability claim is made here.
