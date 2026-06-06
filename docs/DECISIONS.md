# Decisions

This document records reset branch decisions. It is intentionally short; deeper
historical context is preserved by the pre-reset tag.

## ADR-001: Fixed DAG Replaces Route Mode Routing

Status: accepted for reset runtime.

Decision: the main architecture is a fixed topological DAG with explicit stages
and dimension composites.

Reason: the reset needs deterministic structure, clearer public workflow
projection, and fewer historical branches.

Consequence: old mode prompt/parser/state/public workflow code is not active
runtime authority in R3.

## ADR-002: snake_case Runtime IDs Replace aNN IDs

Status: accepted for reset target; active for backend catalog projection in
R4-A, runtime binding metadata in R4-B, and legacy boundary isolation in R4-C.

Decision: target formal agents use descriptive `snake_case` ids.

Reason: ids should carry stable role meaning and avoid coupling new architecture
to old catalog numbering.

Consequence: the fixed DAG catalog uses `snake_case` ids as active reset public
catalog truth. Legacy aNN config files remain as explicit migration/readiness
input but are not active reset graph registration truth.

## ADR-003: Sentiment Radar Belongs To Market L2

Status: accepted for reset runtime.

Decision: the company sentiment radar belongs in the market dimension as an L2
signal, not as a cross-cutting risk input and not as a fifth dimension composite.

Reason: v4 feedback aligned the radar to market sentiment, heat, and attention.
Risk handling remains owned by explicit risk L2 agents and the risk composite.

Consequence: L3 has four composites: value, market, risk, and macro.
`sentiment_company_radar` routes to `market_composite` only.

## ADR-004: Pre-Reset Tag Preserves Old History

Status: accepted.

Decision: old docs, data, archive tests, and training lineage removed in R1-A
are recovered through `pre-fixed-dag-reset-20260604-1457`.

Reason: the active reset branch should stay small and unambiguous.

Consequence: current docs should not link old lineage as active authority.

## ADR-005: Frontend Shell Is Retained For Later In-Place Rewrite

Status: accepted for reset.

Decision: R1-B keeps `apps/web` while replacing the Python public workflow
contract.

Reason: the frontend workflow inspector rewrite is separate from the runtime
protocol skeleton.

Consequence: frontend v2 is deferred to R5.

## ADR-006: R1-B Uses Deterministic Provider-Free Skeleton

Status: accepted.

Decision: R1-B active runtime does not call providers, search, external agents,
A01 contract dispatch, mode-based manager assignment, baseline sidecar, or Fair
Fusion. It emits deterministic placeholder objects with reset schemas.

Reason: this phase validates protocol topology before business implementations
or live service readiness.

Consequence: tests can claim skeleton import/invoke/public projection only; they
cannot claim live analysis, provider readiness, external readiness, or production
readiness.

## ADR-007: V4 Feedback Sets The 27-Agent Formal Roster

Status: accepted for reset runtime.

Decision: the active reset roster has 27 formal agent ids: L1=3, L2=18, L3=4,
L4=2. The enterprise financial analysis target is removed.

Reason: the v4 feedback table is the reset roster authority for R1-B-Delta.

Consequence: tests and docs must not describe pre-delta target counts as current
runtime facts.

## ADR-008: R2 Uses Contract And Function Seams

Status: accepted for reset runtime.

Decision: fixed DAG payloads are generated through deterministic constructors,
normalizers, and validators in `fixed_dag_contracts.py`.

Reason: graph nodes and public workflow fallbacks need stable protocol objects
before business algorithms, registry migration, or frontend workflow UI work.

Consequence: R2 hardens the skeleton contracts but does not implement real
business agents, provider readiness, external service readiness, frontend v2, or
mainline/fusion-gate reset quality gates. These seams are the prerequisite for
R3 executor orchestration.

## ADR-009: R3 Uses Plan-Driven Fixed DAG Executor

Status: accepted for reset runtime.

Decision: after L1 preparation, the active graph delegates deterministic
orchestration to `execute_fixed_dag`.

Reason: execution order should be derived from validated
`dag_steps[].depends_on`, not from hand-maintained graph fanout nodes.

Consequence: runtime emits `fixed_dag_execution_v1`, `execution_batches`, and
`fixed_dag_step_result_v1`; public workflow snapshots include
`executionBatches` and `stepResults`. The executor remains deterministic and
provider-free.

Non-consequence: R3 does not implement real business agents, provider readiness,
external readiness, R5 frontend rewrite, R6 quality gates, or production
deployment.

## ADR-010: R3.6 Keeps Cleanup Narrow

Status: accepted for reset hygiene.

Decision: R3.6 may remove only high-confidence dead files, ignored/generated
local artifacts, and explicitly unreferenced legacy fixtures. It also commits
the v4 feedback workbook as an R4 input.

Reason: R3.5 inventory identified separate ownership for R4 catalog migration,
R5 frontend workflow rewrite, R6 quality/mainline/fusion rebuild, external
readiness, and historical artifact archive policy.

Consequence: R3.6 does not delete `config/agents`, external wrappers,
`apps/web`, baseline/fusion regression inputs, `assets/reference`, or historical
`log/tmp/outputs` artifacts.

Non-consequence: adding the workbook does not complete the R4 registry
migration, and cleanup does not prove provider, external, frontend v2,
mainline/fusion-gate, or production readiness.

## ADR-011: R4-A Uses Fixed DAG Catalog For Public Agent Projection

Status: accepted for backend catalog projection.

Decision: `config/fixed_dag/agent_catalog.json` is the active reset backend
catalog source, and `/api/agents` projects its 27 `snake_case` agents through
the existing public `AgentCatalogResponse` shape.

Reason: public workflow steps already use fixed DAG ids. Keeping `/api/agents`
on old aNN config metadata makes the public catalog disagree with runtime DAG
steps and hides the R4 target roster.

Consequence: in R4-A, `/api/agents` reports `configCount=27`,
`runtimeCount=27`, `disabledIds=[]`, and layer counts L1=3, L2=18, L3=4, L4=2.
Old `config/agents/*.json` remains in the repo as legacy migration input for
external wrapper and cleanup phases, but it is no longer the active reset public
catalog truth.

Non-consequence: R4-A does not implement real business agents, provider/live
readiness, external endpoint mapping, frontend workflow UI rewrite,
mainline/fusion-gate rebuild, or production deployment.

## ADR-012: R4-B Uses Runtime Bindings As Metadata, Not Live Invocation

Status: accepted for backend runtime binding registry.

Decision: `config/fixed_dag/runtime_bindings.json` is the active backend
runtime binding metadata source, and
`src/react_agent/fixed_dag_runtime_registry.py` validates it against the fixed
DAG catalog. Executor step results are annotated with binding metadata such as
runtime kind, implementation status, legacy migration id, external agent id,
invoke-enabled flag, and live-verified flag.

Reason: R4 needs an explicit bridge from fixed DAG `snake_case` ids to
deterministic seams, pending placeholders, and legacy external HTTP candidate
metadata before any later adapter or readiness work can be safely attempted.

Consequence: runtime binding ids must exactly match the 27 fixed DAG catalog
ids. External HTTP candidates are disabled by default and not live verified.
Legacy aNN ids are migration notes only and never primary reset ids.

Non-consequence: R4-B does not change active DAG topology, does not invoke
providers or external `/v1/agent/invoke` endpoints, does not expose binding
fields through `/api/agents`, does not complete frontend v2, does not rebuild
mainline/fusion gates, and does not prove production readiness.

## ADR-013: R4-C Isolates Legacy Registry From Active Fixed DAG Runtime

Status: accepted for reset runtime.

Decision: legacy aNN `AGENT_METADATA`, `AGENT_TOOLS`, metadata loading, and
bootstrap behavior live behind explicit compatibility modules. Active
`react_agent.graph` imports fixed-DAG contracts, executor, state, graph entry,
catalog, and binding seams only; it must not import or execute
`legacy_agent_registry`, `graph_bootstrap`, default LLM/search placeholder
registration, generic agent registration, or external HTTP wrapper
implementation modules.

Reason: the reset branch needs a clean runtime authority before frontend DAG UI,
external handoff docs, and later quality gate rebuilds. Keeping old registry
globals on the graph import path made legacy config appear to be active runtime
truth.

Consequence: `config/agents/*.json` is retained as migration/readiness input,
`legacy_agent_id` remains metadata in runtime bindings and step results, and
external HTTP wrapper infrastructure remains available but not live verified or
invoked by the fixed-DAG graph. The old valuation-only facade and unreferenced
JSON helper were removed after references were migrated or absent.

Non-consequence: R4-C does not implement business agent algorithms, does not
enable external candidates, does not call providers or external
`/v1/agent/invoke`, does not rewrite frontend v2, and does not rebuild
mainline/fusion gates.

## ADR-014: R5-B1 Migrates The Web Contract Before The Full Inspector Rewrite

Status: accepted for frontend contract migration.

Decision: R5-B1 updates the existing `apps/web` shell in place so frontend
workflow/chat types, streaming placeholder state, fixed DAG mocks, and smoke
fixtures consume `workflow_snapshot_v2` with `finalSource=reset_skeleton`.
The current WorkflowPanel is only minimally adapted to render DAG stages,
steps, dimension groups, execution batches, completed steps, and public
provenance.

Reason: the public adapter already emits the fixed DAG payload. Keeping the web
app on `layerPlan`, `layerMode`, `agentSteps`, `fusionSteps`, and
`mainline/baseline/fused` would make frontend tests and demos validate the old
contract instead of the active reset contract.

Consequence: frontend mocks now use the 27 enabled `snake_case` fixed DAG
catalog and v2 workflow snapshots. Public transcript remains user/assistant
text only; workflow, step results, execution batches, and runtime binding
metadata remain inspector/debug data, not transcript turns.

Non-consequence: R5-B1 does not change Python backend contracts, executor
topology, runtime bindings, `/api/agents` schema, provider readiness, external
candidate invocation, production deployment, or later quality gates. It also
does not complete the richer R5-B2 DAG timeline, dependency graph,
per-step drilldown, or evidence view.

## ADR-015: R5-B2 Rewrites The Workflow DAG Inspector UI

Status: accepted for frontend inspector UI rewrite.

Decision: R5-B2 keeps the single public user/assistant transcript and rewrites
the existing `apps/web` WorkflowPanel around `workflow_snapshot_v2`. The
inspector renders fixed DAG stage timeline, execution batches, dimension
groups, selectable DAG steps, public-safe step result metadata, final source,
and provenance. Step result metadata may show runtime kind, implementation
status, invoke-enabled status, live-verified status, and warnings.

Reason: R5-B1 aligned the frontend contract with the public fixed DAG payload.
R5-B2 makes that payload inspectable without creating separate public agent chat
lanes and without changing backend runtime authority.

Consequence: frontend mocks, smoke tests, and screenshot fixtures now validate
the inspector against `workflow_snapshot_v2` while preserving transcript safety.
`stepResults`, `executionBatches`, and runtime binding metadata remain
inspector/debug data, not transcript turns.

Non-consequence: R5-B2 does not change Python backend contracts, executor
topology, catalog source, runtime bindings, `/api/agents` schema, provider
readiness, external candidate invocation, production deployment, or later
quality gates. It does not prove business-agent correctness or live service
readiness.

## ADR-016: R5-C Keeps Normal UI Product-Facing And Moves Diagnostics Behind Disclosure

Status: accepted for frontend product polish.

Decision: R5-C keeps the single public user/assistant transcript and the
`workflow_snapshot_v2` contract, but changes the normal `apps/web` experience
to product-facing Chinese copy. Chat empty state, assistant answer cards,
workflow collapsed summaries, Agents overview, and Settings default view should
not prominently display backlog/readiness language such as pending
implementation, provider missing, external not ready, or live verification
status. Runtime enum values, provenance, provider/search/readiness flags, and
limitations remain available in expanded workflow technical details, Settings
advanced diagnostics, docs, and tests.

Reason: R5-B2/R5-B2.6 made the fixed DAG payload visible and localized, but the
normal UI still read like an engineering checklist. Product users need a calmer
research surface while reviewers still need exact technical boundaries.

Consequence: frontend mocks, smoke tests, screenshot fixture copy, public-safe
answer copy, and related assertions now validate user-facing simplification and
advanced diagnostic disclosure without changing schema, topology, or runtime
authority.

Non-consequence: R5-C does not change fixed DAG topology, roster, runtime
bindings, `/api/agents` schema, provider readiness, external candidate
invocation, production deployment, or later quality gates. It does not
prove business-agent correctness or live service readiness.

## ADR-017: R5-C1 Business Copy Avoids Implementation Notes In Default UI

Status: accepted for frontend product copy.

Decision: R5-C1 keeps the same public contracts and disclosure model, but
removes remaining implementation-note wording from default user-facing copy.
Dimension summaries should explain value, market, risk, and macro analysis in
business terms. Step summaries should not mention screenshot fixtures, rosters,
path wiring, metadata, or transcript boundaries. Answer cards should present
evidence as "研判依据" with "分析框架", "用户问题", and "流程记录" items.

Reason: R5-C reduced major engineering/status noise, but screenshots showed
remaining copy still explained internal wiring rather than user value. Business
users need professional product language by default, while reviewers can still
inspect raw protocol values in expanded technical details.

Consequence: frontend mocks, screenshot fixtures, smoke tests, public-safe
answer copy, and docs now validate default-surface business copy and guard
against fixture/roster/transcript/path-wiring terms reappearing in ordinary
chat surfaces.

Non-consequence: R5-C1 does not change fixed DAG topology, the 27-agent roster,
runtime bindings, public schemas, provider readiness, external candidate
invocation, production deployment, or later quality gates. It does not
prove business-agent correctness or live service readiness.

## ADR-018: R6-B Rebuilds Reset Mainline And Archives Fusion Gate

Status: accepted for reset quality.

Decision: `scripts/quality/run_quality.py --mode mainline` is the default
fixed-DAG reset quality gate and runs static, unit, public-api, graph-smoke,
and frontend. It does not run `fusion-gate`.

Reason: the reset branch needs a non-provider, non-live, non-artifact default
quality closure that matches the active fixed-DAG runtime and frontend shell.
The old mainline mixed in the historical fusion regression gate, and the old
frontend mode could write `apps/web/dist`.

Consequence: the frontend mode performs TypeScript no-emit, frontend smoke,
and Vite build with a temporary repo-external `--outDir`. PR/push CI no longer
blocks on fusion-gate. `fusion-gate` remains explicit archived/manual lineage.
Provider live smoke remains optional live/manual or scheduled.

Non-consequence: R6-B does not change fixed DAG topology, the 27-agent roster,
runtime bindings, public schemas, frontend product UI, provider readiness,
external `/v1/agent/invoke` readiness, production deployment, Router-SFT, or
RARP/route-prior lineage. Passing reset mainline does not prove live services
or restored fusion acceptance.

## ADR-019: R7-B Standardizes Fixed DAG External Handoff By Contract

Status: accepted for external developer documentation.

Decision: R7-B external developer onboarding is standardized through fixed DAG
ids, runtime binding metadata, contract mapping, sample payloads, a sample-only
local scaffold, and an explicit readiness ladder. The handoff does not require
every external agent to use the same internal implementation mode.

Reason: later external services may be implemented as deterministic services,
machine-learning services, data services, LLM services, LLM-with-tools services,
or hybrids. The reset architecture needs stable boundary contracts and review
evidence without coupling the platform to one implementation style.

Consequence: new docs and the sample scaffold define how external envelopes
should map to `conclusion_object_v1`, `dimension_composite_result_v1`,
`decision_result_v1`, `report_result_v1`, `data_bundle_v1`, and
`entity_relation_bundle_v1`; how readiness moves from docs-only review to
controlled live verification; and what cannot be treated as runtime truth.

Non-consequence: R7-B does not change fixed DAG topology, the 27-agent roster,
runtime bindings, public schemas, frontend product UI, provider readiness,
external `/v1/agent/invoke` readiness, production deployment, Router-SFT, or
RARP/route-prior lineage. It does not register the sample scaffold into the
graph, enable a wrapper, live-verify an external service, restore old `aNN`
catalog authority, restore `value_financial_analysis`, or route
`sentiment_company_radar` into risk.

## ADR-020: R7-C Keeps External Scaffold Source And Repo Mirror Aligned

Status: accepted for external developer package governance.

Decision: R7-C upgrades the original repo-external scaffold source package at
`E:\muti-agent\external_agent_scaffold` and syncs its contents into the tracked
repo mirror `examples/fixed_dag_external_agent_scaffold/`. The package uses
fixed DAG `agent_id`, `external_agent_id`, and migration-only `legacy_agent_id`
fields; it does not use old `main_agent_id` or aNN primary ids in the current
schema path.

Reason: external developers receive the repo-external package, while reviewers
need a tracked copy for diffs, docs, tests, and changelog history. Maintaining
one package shape in both locations prevents the old v2.1-v2.2.1 scaffold
lineage, `AGENT_TOOLS`, `config/agents`, and aNN id assumptions from drifting
back into handoff instructions.

Consequence: scaffold docs, schemas, service code, samples, and tests must stay
aligned between the external source package and the repo mirror. Local tests
may prove endpoint shape, schema mapping, typed errors, anti-lookahead,
confidence bounds, evidence, event flags, and no-provider/no-external-call
sample behavior.

Non-consequence: R7-C does not change fixed DAG topology, the 27-agent roster,
runtime bindings, public schemas, frontend product UI, provider readiness,
external `/v1/agent/invoke` readiness, production deployment, Router-SFT, or
RARP/route-prior lineage. It does not register the scaffold into the graph,
enable a wrapper, live-verify an external service, restore
`value_financial_analysis`, restore a 28-agent roster, or route
`sentiment_company_radar` into risk.

## ADR-021: R7-D Separates Scaffold Contract From Legacy Wrapper Compatibility

Status: accepted for external handoff documentation consistency.

Decision: R7-D keeps the fixed DAG scaffold contract authoritative for new
external services and documents legacy wrapper compatibility as a maintainer
bridge concern. External developers should implement `agent_id`,
`external_agent_id`, `legacy_agent_id`, `/health`, `/v1/agent/compute`, and
`/v1/agent/invoke` as shown in the scaffold package, not the older
`main_agent_id` wrapper context shape.

Reason: the repo still retains legacy external wrapper compatibility code for
old aNN services, but the fixed DAG reset branch must not let that compatibility
shape become the current handoff contract. R7-D also clarifies status mapping
across external service status, adapter decision, and fixed DAG validator
status.

Consequence: source package docs, repo mirror docs, payload mapping docs,
quality docs, and changelog now describe the same handoff boundary. The sample
mapper reads `legacy_agent_id` from the response being mapped instead of a
global sample constant.

Non-consequence: R7-D does not change active runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, frontend
product UI, provider readiness, external `/v1/agent/invoke` readiness,
production deployment, Router-SFT, or RARP/route-prior lineage. It does not
enable wrappers, set `live_verified=true`, set `invoke_enabled_by_default=true`,
restore `value_financial_analysis`, restore a 28-agent roster, or route
`sentiment_company_radar` into risk.
