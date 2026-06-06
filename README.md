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
Phase R5-B2.6 localizes and polishes visible Chinese copy for the existing
fixed DAG inspector, Agents page, Settings page, public-safe skeleton answer,
and supporting frontend fixtures without changing the `workflow_snapshot_v2`
contract. Phase R5-C further simplifies the normal user-facing web surface:
engineering/backlog/readiness details move into workflow technical details,
Settings advanced diagnostics, docs, and tests instead of the default chat,
Agents, and Settings views.
Phase R5-C1 professionalizes the remaining business-facing Chinese copy so
dimension summaries, step descriptions, and answer-card evidence read as
product language rather than implementation notes.
Phase R6-B rebuilds the default reset quality mainline so it covers scoped
static checks, unit tests, public API tests, graph smoke tests, and frontend
typecheck/smoke/repo-external build validation without running archived
fusion-gate or live provider/external gates.
Phase R7-C upgrades the original repo-external scaffold source package at
`E:\muti-agent\external_agent_scaffold` into the fixed DAG handoff package and
syncs the tracked mirror under `examples/fixed_dag_external_agent_scaffold/`.
It remains sample-only contract material: it does not register the scaffold,
enable wrappers, modify runtime bindings, or live-verify external candidates.
Phase R7-D tightens external handoff documentation consistency around status
mapping, wrapper compatibility, package/mirror/zip distribution roles, and
developer handoff evidence without changing runtime behavior.
Phase R7-E expands the scaffold `AI_CODING_HANDOFF.md` into a developer-side
Codex / Claude Code operating manual for adapting an existing agent project
into a fixed DAG external service wrapper.
Phase R7-F upgrades that package to `external-agent-scaffold-v2.3-fixed-dag`,
restoring the broader domain payload family and semantic validators while
keeping fixed DAG ids, readiness boundaries, and Non-Claims.
The runtime validates
`dag_steps[].depends_on`, computes deterministic `execution_batches`, emits
per-step `step_results`, and remains a provider-free placeholder skeleton. It
is not a completed business analysis engine.

## Current Branch Scope

- Branch: `reset/fixed-dag-v1`.
- Reset base: `pre-fixed-dag-reset-20260604-1457`.
- Current phase: R7-F v2.3 external scaffold payload superset over
  the existing fixed DAG web shell and backend skeleton.
- Current runtime milestone: R3 plan-driven fixed DAG execution orchestration.
- Runtime entry: `langgraph.json -> src/react_agent/graph.py:graph`.
- Public Python workflow contract: `workflow_snapshot_v2`.
- Public agent catalog: fixed DAG 27-agent `snake_case` projection from
  `config/fixed_dag/agent_catalog.json`.
- Public web shell: migrated in place to consume the fixed DAG public contract;
  the current WorkflowPanel renders the R5-B2 fixed DAG inspector from
  `workflow_snapshot_v2`, with R5-B2.6 Chinese localization, R5-C
  user-facing simplification, and R5-C1 business-copy professionalization on
  the same payload.
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
R5-B2.6 keeps that boundary and localizes the visible web copy, inspector
labels, status labels, mock/screenshot fixture copy, and deterministic
public-safe reset skeleton answer. It keeps technical ids, schema names, and
runtime enum values available where needed for debugging.
R5-C keeps the same public contracts but reduces engineering/status noise in
normal UI. Chat empty state, answer cards, workflow collapsed summaries, Agents
overview, and Settings default view are product-facing. Provider/search/live
readiness, raw runtime enums, and execution provenance remain available in
technical details, advanced diagnostics, docs, and tests.
R5-C1 keeps the same public contracts and further professionalizes business
copy in the default user surface: dimension summaries avoid route-wiring
explanations, step summaries avoid fixture/roster/transcript language, and
answer cards use "研判依据", "分析框架", "用户问题", and "流程记录" labels.

## Documentation Index

- `docs/INDEX.md` - reset documentation map.
- `docs/SYSTEM_MAP.md` - active runtime topology and phase map.
- `docs/ARCHITECTURE_FIXED_DAG.md` - fixed DAG skeleton and target ids.
- `docs/CONTRACTS.md` - runtime/public contract payload boundaries.
- `docs/FRONTEND_V2.md` - frontend/public transcript boundary.
- `docs/QUALITY.md` - safe quality commands for the reset branch.
- `docs/DECISIONS.md` - reset architecture decisions.
- `docs/CHANGELOG.md` - reset branch changelog.
- `docs/EXTERNAL_AGENT_HANDOFF_FIXED_DAG.md` - fixed DAG external developer
  handoff entry point.
- `docs/EXTERNAL_AGENT_PAYLOAD_MAPPING_FIXED_DAG.md` - mapping from external
  payload envelopes to fixed DAG contracts.
- `docs/EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md` - readiness ladder from
  docs-only review to explicit live invocation approval.
- `docs/EXTERNAL_AGENT_SAMPLE_PAYLOADS_FIXED_DAG.md` - documentation-only
  endpoint and v2.3 domain payload samples.
- `examples/fixed_dag_external_agent_scaffold/` - tracked repo mirror of the
  upgraded v2.3 fixed DAG external scaffold package and its local tests.

## Safe Local Validation

Use the project conda environment when available. R6-B makes `mainline` the
default reset quality gate:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode unit
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode public-api
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode graph-smoke
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode frontend
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
```

`frontend` uses TypeScript no-emit, the frontend smoke test, and a temporary
repo-external Vite build `--outDir`; it must not write `apps/web/dist`.

Do not use successful tests as production readiness evidence.

R7-F scaffold validation runs the repo-external package tests and ruff for
`E:\muti-agent\external_agent_scaffold`, the tracked repo mirror tests and ruff
for `examples/fixed_dag_external_agent_scaffold/`, then uses the same
non-provider static and mainline commands. These checks do not call providers,
do not call external `/v1/agent/invoke`, and do not prove live external
readiness.

## Explicit Non-Claims

- No provider or live external service was verified by
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1/R6-B/R7-B/R7-C.
- No `external /v1/agent/invoke` call is part of
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1/R6-B/R7-B/R7-C validation.
- No demo stack startup is part of
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1/R6-B/R7-B/R7-C validation.
- No real business algorithms for individual agents are implemented in
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1.
- R5-B2 completes the frontend inspector UI rewrite only; it does not change
  backend executor semantics, provider readiness, external readiness, or
  business-agent correctness.
- R5-B2.6 completes Chinese visible-copy localization and visual copy polish
  only; it does not add a runtime locale switch, change public schemas, or
  change fixed DAG topology, roster, provider readiness, external readiness, or
  business-agent correctness.
- R5-C completes user-facing simplification and diagnostic disclosure cleanup
  only; it does not change public schemas, fixed DAG topology, roster, provider
  readiness, external readiness, or business-agent correctness.
- R5-C1 completes user-facing business copy professionalization only; it does
  not change public schemas, fixed DAG topology, roster, provider readiness,
  external readiness, or business-agent correctness.
- R6-B rebuilds the default reset mainline quality gate only. It does not
  restore fusion acceptance, and `fusion-gate` remains archived/manual.
- R7-B adds external developer handoff docs, payload mapping docs, readiness
  ladder docs, sample payload docs, and a sample-only local scaffold. It does
  not register the scaffold into the graph, modify runtime bindings, enable
  external candidates, live-verify services, or force one internal
  implementation mode for external agents.
- R7-C upgrades the original repo-external scaffold source package and syncs a
  tracked repo mirror. It does not turn the scaffold into active runtime code,
  enable `runtime_bindings`, register wrappers, or prove live service
  readiness.
- R7-D only tightens external handoff wording and consistency. It does not
  change active runtime behavior, enable bindings, bridge legacy wrappers, or
  prove live readiness.
- R7-E only expands developer-side AI coding instructions for adapting
  external agent projects. It does not change service runtime behavior,
  schemas, samples, active runtime, runtime bindings, or live readiness.
- R7-F restores the scaffold v2.3 domain payload family and semantic
  validators. It does not change active runtime behavior, enable bindings,
  bridge legacy wrappers, call providers, call external live invoke, or prove
  live readiness.
- Provider live smoke, external invoke checks, Router-SFT, RARP/route-prior,
  demo stack acceptance, and browser screenshot visual capture remain outside
  the default reset mainline.
- R4-C isolates legacy registry/bootstrap but does not delete
  `config/agents/*.json` or live-verify external candidates.
- No production auth, rate limit, HTTPS, deployment, or observability claim is made here.
