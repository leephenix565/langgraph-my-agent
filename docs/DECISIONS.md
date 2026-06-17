# Decisions

This document records reset branch decisions. It is intentionally short; deeper
historical context is preserved by the pre-reset tag.

## ADR-062: R8-13J Adds A Next Phase Roadmap Without Runtime Change

Status: accepted.

Decision: the main-system docs now include
`docs/NEXT_PHASE_ROADMAP_FIXED_DAG.md` as the current roadmap entry point. The
roadmap consolidates current fixed DAG progress, A/B/C agent work classes,
near-term demo trace and A-class remediation priorities, medium/long-term
runtime preparation, and documentation cleanup guidance.

Reason: the project accumulated accurate but distributed status across the
readiness matrix, smoke log, demo runbooks, changelog, ADRs, and phase handoff
docs. A new Codex session can understand the repository, but only after reading
many files. The roadmap gives future sessions one planning-oriented entry point
without deleting the audit trail.

Consequence: future planning should start with the roadmap, then drill into the
readiness matrix and smoke log for evidence. The roadmap is not runtime
authority, does not modify `runtime_bindings.json`, does not set live flags,
does not call endpoints, and does not promote demo evidence into production
readiness.

## ADR-056: R8-13I Defines Dev Sandbox Prod Roles And Documentation Authority

Status: accepted.

Decision: the main-system repository now documents a three-directory operating
model on this server. `/sdb/dlut/dev/langgraph-my-agent` is the source-controlled
development authority, `/sdb/dlut/sandbox/langgraph-my-agent-r8-a-class` is an
experiment area, and `/sdb/dlut/prod/langgraph-my-agent` is a runtime/deployment
copy. The docs index points to `docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md` as the
current guide for directory roles, sync policy, and documentation authority.

Reason: recent R8-12/R8-13 work used all three directories. Without an explicit
operating model, it is easy to mistake sandbox experiments or prod runtime
copies for the long-term source of truth. The project also accumulated many
phase-specific documents; deleting them would lose audit and rollback context,
but leaving them unclassified makes the current authority hard to find.

Consequence: future main-system work should be committed and pushed from dev,
sandbox work should be backfilled into dev before it becomes authoritative, and
prod should be updated from stable pushed commits. Phase documents remain
historical records until a dedicated docs-compaction phase merges them into
current authority documents.

## ADR-055: R8-13H Tests A-Class L1/L2 Bridge In Sandbox Before Prod Backfill

Status: accepted for sandbox validation.

Decision: R8-13H ports sandbox-validated default-off external compute bridge
support for A-class remediation candidates into the main development branch.
L1 `financial_data_service` and
`entity_relation_extractor` may be mapped into the executor before L2
`agent_task_v1` construction, and macro L2 `macro_commodity_pricing` /
`macro_index_valuation` may be allowlisted as `agent_conclusion_v1` compute
candidates.

Reason: L2 agents need structured data and entity evidence in their task
payloads. Calling L2 compute while L1 remains placeholder makes the demo look
connected while still starving downstream agents of the evidence they are
supposed to read.

Consequence: the sandbox can validate the data-flow shape without touching
production services, runtime bindings, live flags, or `/v1/agent/invoke`. This
does not create production readiness evidence. Production re-smoke and service
owner backfill remain separate phases.

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

## ADR-022: R7-E Expands Developer-Side AI Coding Handoff

Status: accepted for external scaffold developer workflow.

Decision: R7-E expands `AI_CODING_HANDOFF.md` in the fixed DAG external
scaffold package into a full Codex / Claude Code operating manual. The manual
targets developer-side adaptation work: audit an existing agent project,
preserve its business core, add a minimal fixed DAG external service wrapper,
implement `/health`, `/v1/agent/compute`, and `/v1/agent/invoke`, add local
contract tests, run local validation, and return a maintainer handoff bundle.

Reason: external developers may hand this scaffold zip and their own agent
project to coding tools. The tool needs enough instructions to adapt the
developer project without drifting into main-system runtime edits,
`AGENT_TOOLS`, `config/agents`, runtime binding enablement, provider calls, or
live external invocation.

Consequence: the scaffold package and repo mirror now contain a copy-paste
prompt, adaptation patterns, implementation-mode-neutral guidance, test
requirements, validation commands, and final response format for coding agents.

Non-consequence: R7-E does not change service runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, frontend
product UI, provider readiness, external `/v1/agent/invoke` readiness, or
production deployment. It does not enable wrappers, set `live_verified=true`,
set `invoke_enabled_by_default=true`, restore `value_financial_analysis`,
restore a 28-agent roster, or route `sentiment_company_radar` into risk.

## ADR-023: R7-F Restores v2.3 Domain Payload Superset

Status: accepted for external scaffold contract coverage.

Decision: R7-F upgrades the external scaffold package to
`external-agent-scaffold-v2.3-fixed-dag`. It restores the v2.3 domain payload
family (`agent_conclusion_v1`, `dimension_conclusion_v1`,
`risk_conclusion_v1`, `macro_conclusion_v1`, `decision_conclusion_v1`,
`eval_record_v1`, `fixed_dag_plan_v1`, and `data_bundle_v1`) and adds
scaffold-local semantic validators while preserving fixed DAG three-id rules,
canonical dimensions, readiness boundaries, and Non-Claims.

Reason: the R7-C/R7-D/R7-E scaffold had the correct fixed DAG handoff shape but
was too thin for L3 composites, L4 decision synthesis, evaluation/replay,
planning, and L1 data bundle handoff. External developers need role-specific
payload contracts before R8 adapter work can safely bridge real services.

Consequence: the repo-external package, repo mirror, package docs, sample
payloads, tests, README, index, payload mapping, readiness ladder, contracts,
system map, quality docs, ADRs, and changelog now describe the same v2.3
compatibility superset.

Non-consequence: R7-F does not change active runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, frontend
product UI, provider readiness, external `/v1/agent/invoke` readiness, or
production deployment. It does not enable wrappers, set `live_verified=true`,
set `invoke_enabled_by_default=true`, restore `value_financial_analysis`,
restore a 28-agent roster, or route `sentiment_company_radar` into risk.

## ADR-024: R7-G Patches v2.3.1 External Scaffold Contracts

Status: accepted for external scaffold contract patch.

Decision: R7-G upgrades the external scaffold package to
`external-agent-scaffold-v2.3.1-fixed-dag`. It patches the R7-F v2.3 payload
family by adding L2 `gate_member` semantics, safe L2 `raw_output` and
`quality` dictionaries, `manual_review` risk gates, canonical
`DimensionMember[]` composites, normalized point-in-time date comparison,
macro `dimension_weights` restricted to `value` and `market`, L4 score
tolerance `0.01`, and distinct reasoning-stage validation.

Reason: R7-F restored the right payload family, but review showed that several
contracts were too thin for risk-member L2 agents, risk fusion, value/market
composite recomputation, mixed date formats, and L4 score/trace review.

Consequence: the repo-external package, tracked repo mirror, package docs,
sample payloads, tests, README, index, payload mapping, readiness ladder,
sample docs, contracts, system map, quality docs, ADRs, and changelog now
describe the v2.3.1 contract patch.

Non-consequence: R7-G does not change active runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, frontend
product UI, provider readiness, external `/v1/agent/invoke` readiness, or
production deployment. It does not enable wrappers, set `live_verified=true`,
set `invoke_enabled_by_default=true`, restore `value_financial_analysis`,
restore a 28-agent roster, or route `sentiment_company_radar` into risk.

## ADR-025: R7-H Repairs Reset Consistency Drift Without Runtime Change

Status: accepted for minimal consistency repair.

Decision: R7-H aligns frontend workflow fixtures and smoke assertions with the
backend runtime binding `runtime_kind` literals, restores the local
repo-external scaffold distribution working copy from the tracked mirror when
it is missing, and updates current documentation wording around R7-C/R7-D/R7-G
phase boundaries.

Reason: Phase 1 audit found small drift between frontend mock metadata and
backend binding truth, plus documentation that treated
`E:\muti-agent\external_agent_scaffold` as an always-present source package
even when the current filesystem only had the tracked mirror.

Consequence: the frontend fixture now uses backend runtime metadata literals,
the tracked mirror remains the audit truth for scaffold content, and the local
repo-external path is documented as a restored distribution working copy.

Non-consequence: R7-H does not change active runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, provider
readiness, external `/v1/agent/invoke` readiness, or production deployment. It
does not enable wrappers, set `live_verified=true`, set
`invoke_enabled_by_default=true`, or register the scaffold into the graph.

## ADR-026: R8-1 Adds Selected Plan Contracts Without Changing Active Runtime

Status: accepted for selected routing contract foundation.

Decision: R8-1 adds `route_intent_v1` and `selected_fixed_dag_plan_v1` to
`src/react_agent/fixed_dag_contracts.py` as additive contracts and validators.
The default graph still uses `build_default_fixed_dag_plan`,
`validate_fixed_dag_plan`, and the full 27-agent `fixed_dag_plan_v1` path.

Reason: controlled dynamic routing needs a safe boundary before any LLM or
semantic planner is connected. The planner should produce intent, not raw DAG
dependencies or runtime binding changes. A later deterministic compiler can
translate that intent into a validator-legal selected plan while preserving
full-DAG fallback.

Consequence: `route_intent_v1` records task type, targets, selected dimensions,
selected agents, per-agent briefs, confidence, clarification/fallback metadata,
and provenance. `selected_fixed_dag_plan_v1` records selected dimensions,
selected agents, omitted dimensions, omitted agents, selected stages/steps/DAG
steps, route intent, and fallback metadata. Validators allow explicit dimension
and agent omission, require `report_generator` for selected plans, require risk
and `decision_synthesizer` for investment-judgment task types, keep
`sentiment_company_radar` market-only, reject `value_financial_analysis`, reject
legacy aNN ids and Star/Chain/Debate/Tree dispatch, and reject provider,
external, runtime binding, and unsafe fallback claims.

Non-consequence: R8-1 does not change active runtime behavior, `graph.py`, the
executor default path, fixed DAG topology, the 27-agent roster, catalog,
runtime bindings, runtime registry, public workflow contracts, frontend UI,
provider/search readiness, external `/v1/agent/invoke` readiness, or production
deployment. It does not add an LLM planner, selected DAG compiler, selected
execution, RouteEval suite, or external adapter.

## ADR-027: R8-2 Compiles Route Intent Into Selected DAG Without Enabling Active Runtime

Status: accepted for deterministic selected compiler foundation.

Decision: R8-2 adds `compile_selected_fixed_dag_plan` to compile valid
`route_intent_v1` objects into dependency-closed `selected_fixed_dag_plan_v1`
plans. It also adds selected executor validation helpers:
`validate_selected_dag_steps` and `topological_batches_for_selected_plan`.

Reason: R8-1 established selected contracts, but selected route intent was not
yet an executable selected DAG shape. The next safe step is deterministic
compilation under system-owned rules: the compiler, not an LLM, adds fixed
L1/evidence seams, selected L2 steps, selected composites, policy-gated
decision synthesis, report output, dependencies, and omission metadata.

Consequence: selected plans can now be compiled and validated as complete
selected sub-DAGs without requiring the full 27-agent DAG. The full
`fixed_dag_plan_v1` validator and active graph default remain the regression
baseline. `route_intent_v1` remains planner intent, and
`selected_fixed_dag_plan_v1` is the compiler output target.

Non-consequence: R8-2 does not change active runtime behavior, `graph.py`,
route planner default behavior, fixed DAG topology, the 27-agent roster,
catalog, runtime bindings, runtime registry, public workflow contracts,
frontend UI, provider/search readiness, external `/v1/agent/invoke` readiness,
or production deployment. It does not add an LLM planner, RouteEval suite,
external adapter, or live selected execution path.

## ADR-028: R8-3 Adds Route Intent Planner Seam Behind Default-Off Boundary

Status: accepted for provider-free planner seam preparation.

Decision: R8-3 adds a route-intent planner seam without changing the active
runtime default. `build_default_route_intent` provides deterministic/mock
`route_intent_v1` output for tests and future feature-flag experiments.
`FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT` and `build_route_intent_prompt` define
the future LLM or semantic planner contract. `parse_route_intent_json` and
`normalize_route_intent` normalize raw planner JSON into `route_intent_v1` or a
safe clarification/fallback intent.

Reason: R8-1 and R8-2 created selected routing contracts and deterministic
selected DAG compilation, but route planning still needed a safe seam before
any provider-backed planner could be introduced. The planner must output intent
only; the deterministic compiler remains responsible for executable selected
DAG structure, dependencies, L4 inclusion, omission metadata, and validation.

Consequence: the route-intent prompt and parser reject or fail-soft executable
DAG fields, dependency fields, runtime binding changes, removed ids, legacy
numbered ids, selected sentiment-to-risk misuse, investment intents without
risk, and live invocation claims. Unknown agents can be filtered only when
valid selected agents remain. The full `fixed_dag_plan_v1` default graph path
and full DAG fallback remain the regression baseline.

Non-consequence: R8-3 does not change active runtime behavior, `graph.py`,
route planner default behavior, fixed DAG topology, the 27-agent roster,
catalog, runtime bindings, runtime registry, public workflow contracts,
frontend UI, provider/search readiness, external `/v1/agent/invoke` readiness,
or production deployment. It does not add an active LLM planner, RouteEval
suite, external adapter, live selected execution path, or selected public
workflow projection.

## ADR-029: R8-4 Evaluates Route Intent Selections Before Enabling Active Routing

Status: accepted for provider-free route evaluation baseline.

Decision: R8-4 adds RouteEval as an offline deterministic evaluation seam for
`route_intent_v1`. The evaluator scores task type, targets, selected
dimensions, selected agents, clarification behavior, fallback behavior,
over-selection, and under-selection against a small repo fixture. It does not
evaluate legacy Star/Chain/Debate/Tree modes and does not call providers,
search, external services, or the active graph.

Reason: R8-1 through R8-3 created selected-routing contracts, deterministic
selected compilation, and planner/parser seams, but controlled dynamic routing
still needs a repeatable quality loop before any active selected-routing switch
or provider-backed planner is enabled. Evaluating intent selections first keeps
LLM output away from executable DAG dependencies and preserves the deterministic
compiler boundary.

Consequence: `src/react_agent/route_eval.py` can load JSONL gold cases and
evaluate deterministic/mock planner output or parser-normalizer output with
stable provider-free metrics. The first fixture is intentionally small and is a
baseline only; later RouteEval work should expand the gold set before using
Route F1 as an acceptance threshold.

Non-consequence: R8-4 does not change active runtime behavior, `graph.py`,
route planner default behavior, fixed DAG topology, the 27-agent roster,
catalog, runtime bindings, runtime registry, public workflow contracts,
frontend UI, provider/search readiness, external `/v1/agent/invoke` readiness,
or production deployment. It does not add active selected routing, a live LLM
planner, external adapter readiness, live selected execution, or a final >=80%
Route F1 gate.

## ADR-030: R8-5 Wires Selected Routing Behind A Default-Off Graph Boundary

Status: accepted for default-off graph integration.

Decision: R8-5 wires provider-free selected routing into `route_planner_node`
behind `Context.enable_selected_routing` / `ENABLE_SELECTED_ROUTING=1`. The
default graph path remains the full `fixed_dag_plan_v1`. When explicitly
enabled, the graph builds `route_intent_v1` through the deterministic/mock
planner seam, compiles it into `selected_fixed_dag_plan_v1`, executes it through
selected executor validation, and falls back to the full DAG on compile or
selected validation failure.

Reason: R8-1 through R8-4 established contracts, deterministic compilation,
planner/parser seams, and offline RouteEval. The next safe step is to connect
the selected pipeline under an explicit runtime boundary while keeping the
full DAG default as the regression baseline.

Consequence: selected routing can now be exercised in graph smoke tests without
provider, search, external invocation, runtime binding changes, frontend
changes, or direct LLM-generated DAG dependencies. Selected executions produce
selected step results and selected-subset workflow snapshots. Fallbacks record
public-safe provenance with `selected_routing_requested`,
`selected_routing_fallback`, provider/external false flags, and safe fallback
codes.

Non-consequence: R8-5 does not change default active behavior, fixed DAG
topology, the 27-agent roster, catalog, runtime bindings, runtime registry,
frontend UI, provider/search readiness, external `/v1/agent/invoke` readiness,
or production deployment. It does not add a provider-backed LLM planner,
external adapter readiness, final Route F1 acceptance threshold, or real
business-agent implementation.

## ADR-031: R8-6B Uses Default-Off Internal LLM Placeholders Before External Integration

Status: accepted for default-off L2 placeholder implementation.

Decision: R8-6B adds internal LLM placeholders for fixed-DAG L2 conclusions
behind `Context.enable_internal_llm_placeholders` /
`ENABLE_INTERNAL_LLM_PLACEHOLDERS=1`. The default path remains deterministic.
When explicitly enabled, the executor may call the main-system model to produce
bounded JSON placeholder observations for selected or full L2 slots. Provider
missing, provider configuration errors, parse failures, or unsafe content fall
back to the deterministic pending conclusion.

Reason: server-side business agent directories and processes exist, but they
have not completed fixed-DAG external adapter readiness, live verification, or
runtime binding enablement. The reset runtime needs a bounded way to carry L2
functional slots without claiming those external services are active. Keeping the
placeholder internal, default-off, and L2-only preserves the runtime boundary
while preparing later adapter work.

Consequence: `src/react_agent/fixed_dag_llm_placeholders.py` becomes the active
internal placeholder seam for R8-6B. Successful placeholder conclusions are
`conclusion_object_v1` with `status=partial`, confidence capped at `0.4`, and
`provenance.runtime_path=internal_llm_placeholder`. L3 composites, L4 decision
synthesis, and report generation remain deterministic summaries.

Non-consequence: R8-6B does not enable external `/v1/agent/invoke`, search,
runtime binding changes, `live_verified=true`, `invoke_enabled_by_default=true`,
fixed DAG roster changes, `value_financial_analysis`, sentiment-to-risk routing,
legacy `AGENT_TOOLS`/`config/agents`/aNN authority, frontend rewrite, or
production deployment. Deployed-but-deferred inventory remains documentation
evidence, not runtime authority.

## ADR-032: R8-7B Adds Provider-Free External Payload Adapter Mapping

Status: accepted for pure adapter mapping first slice.

Decision: R8-7B adds `src/react_agent/fixed_dag_external_adapter.py` as a
provider-free, HTTP-free mapping layer from already-available external fixed-DAG
payload dictionaries into current internal contracts. The first supported
families are `agent_conclusion_v1 -> conclusion_object_v1` and
`data_bundle_v1 -> data_bundle_v1`. Unsupported payload families return
controlled adapter failure records or remain future work.

Reason: R8-7A found that the v2.3.1 scaffold payload family is available and
well-tested, but the active main system had no fixed-DAG contract adapter. The
next safe step is pure mapping and safety validation before any health, compute,
invoke, wrapper bridge, executor integration, or runtime binding enablement
work.

Consequence: external L2 direction payloads can be normalized into
validator-legal `conclusion_object_v1`; risk `gate_member` payloads can map only
when the primary id is a current fixed-DAG risk L2 id, with `risk_score`
preserved in provenance; external data bundles can be compressed into the
current narrow internal `DataBundle` shape. Adapter output sets
`provider_invoked=false` and `external_invoked=false` because the mapper itself
performs no live call.

Non-consequence: R8-7B does not call HTTP, providers, `/health`,
`/v1/agent/compute`, `/v1/agent/invoke`, or deployed server agents. It does not
change `graph.py`, `fixed_dag_executor.py`, public API/runtime/mapping modules,
runtime bindings, live flags, the fixed DAG roster, frontend code, L3/L4 active
mapping, external readiness levels, or production deployment. Passing adapter
tests does not imply `live_verified=true` or `invoke_enabled_by_default=true`.

## ADR-033: R8-8C Accepts external_agent_compute_v0 As Adapter Input Only

Status: accepted for compute-envelope adapter compatibility.

Decision: R8-8C treats `external_agent_compute_v0` as a provider-free adapter
input envelope only. When a compute envelope contains a concrete supported L2
`agent_conclusion_v1` `tool_result`, the adapter reuses the existing conclusion
mapper and records the input envelope schema in provenance.

Reason: R8-8B controlled smoke showed `value_ml_valuation` health passing and
`/v1/agent/compute` returning HTTP 200 with an `external_agent_compute_v0`
envelope whose tool result family was `agent_conclusion_v1`. The R8-7B adapter
rejected that outer envelope as unsupported even though the nested payload
family is already in scope.

Consequence: `src/react_agent/fixed_dag_external_adapter.py` can map supported
compute-envelope L2 conclusions without adding HTTP calls, provider calls,
graph/executor integration, runtime binding changes, or live flags. A compute
envelope that declares a tool result schema but lacks a concrete `tool_result`
returns the controlled failure `compute_tool_result_missing`.

Non-consequence: R8-8C does not make `external_agent_compute_v0` graph state,
live readiness evidence, or runtime-binding authority. It does not repair
`financial_data_service`; that service remains blocked on structured JSON
`/health`. `value_ml_valuation` remains deferred until an R8-8D controlled
re-smoke validates the patched adapter boundary. Passing adapter tests does not
imply `live_verified=true` or `invoke_enabled_by_default=true`.

## ADR-034: R8-8E Records Value ML Controlled Compute Evidence Without Runtime Binding Enablement

Status: accepted for controlled readiness evidence logging.

Decision: R8-8E records sanitized controlled health, compute, and adapter
mapping evidence for `value_ml_valuation` after service-side identity
remediation and R8-8D-ID re-smoke. The evidence lives in documentation only and
references repo-external sanitized artifacts.

Reason: R8-8D showed that the service compute response used the external service
id as the primary `agent_id`, which the main-system adapter correctly rejected.
The right remediation is to fix the dev service response identity to emit fixed
DAG `agent_id=value_ml_valuation` and `external_agent_id=valuation_ml`, then
record the controlled smoke evidence without relaxing main-system identity
validation.

Consequence: `value_ml_valuation` now has documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
`conclusion_object_v1`. The evidence can inform later invoke-readiness and
runtime-binding review.

Non-consequence: R8-8E does not change main-system adapter gates, graph,
executor, public API, public runtime, public mapping, frontend, fixed DAG
roster, or runtime bindings. It does not call `/v1/agent/invoke`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
claim prod readiness, and does not update public transcript content.

## ADR-035: R8-8G Records Additional Controlled Compute Evidence Without Runtime Enablement

Status: accepted for accelerated controlled readiness evidence logging.

Decision: R8-8G records sanitized controlled health, compute, and adapter
mapping evidence for additional dev services that pass the bounded smoke gate.
In this phase, `macro_analysis` passed without service patching, and
`value_traditional_valuation` passed after bounded dev service identity
remediation.

Reason: R8-8D-ID proved the remediation pattern for services that still emit an
external service id as primary `agent_id`. R8-8G applies that pattern only where
needed and keeps the main-system adapter strict: the fixed DAG id remains the
primary `agent_id`, and the external service id remains `external_agent_id`.

Consequence: `macro_analysis` and `value_traditional_valuation` now have
documented dev-only evidence for structured health, `/v1/agent/compute`, and
provider-free adapter mapping into `conclusion_object_v1`. The evidence can
inform later invoke-readiness and runtime-binding review.

Non-consequence: R8-8G does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, or fixed DAG roster. It does not call `/v1/agent/invoke`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
claim prod readiness, and does not update public transcript content.

## ADR-036: R8-8H Expands Controlled Compute Evidence Without Runtime Enablement

Status: accepted for expanded controlled readiness evidence logging.

Decision: R8-8H records sanitized controlled health, compute, and adapter
mapping evidence for an expanded L2 dev-service batch. In this phase,
`value_meta_valuation`, `value_research_synthesis`, and
`market_stock_technical` passed after bounded service-side protocol remediation
where needed.

Reason: R8-8G established a safe service-side remediation pattern for deployed
dev services that were already close to the fixed DAG external payload family
but still emitted service-owned ids or non-canonical dimensions at the adapter
boundary. R8-8H applies that pattern to additional L2 candidates while keeping
the main-system adapter strict: fixed DAG ids remain primary `agent_id`, service
ids remain `external_agent_id`, and adapter-facing dimensions use canonical
English fixed DAG values.

Consequence: the three R8-8H services now have documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
`conclusion_object_v1`. The evidence can inform later invoke-readiness and
runtime-binding review, but remains documentation-only.

Non-consequence: R8-8H does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, and does not
update public transcript content.

## ADR-037: R8-8I Broadens Controlled Compute Evidence Without Runtime Enablement

Status: accepted for broadened controlled readiness evidence logging.

Decision: R8-8I records sanitized controlled health, compute, and adapter
mapping evidence for `sentiment_company_radar` after bounded service-side
protocol remediation. The evidence is market-only L2 evidence and is recorded
in documentation only.

Reason: the dev `company_radar_agent` service was already close to the fixed DAG
external compute-envelope family but still emitted service-owned identity and
Chinese-domain dimension fields at the adapter boundary. The correct remediation
is service-side: the fixed DAG id becomes primary `agent_id`, the service-owned
id remains `external_agent_id`, and the adapter-facing dimension is canonical
`market`. The main-system adapter identity gate remains strict.

Consequence: `sentiment_company_radar` now has documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
`conclusion_object_v1` with `market_composite` output routing. The evidence can
inform later invoke-readiness and runtime-binding review.

Non-consequence: R8-8I does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, does not update
public transcript content, and does not create or imply any
`sentiment_company_radar` risk route.

## ADR-038: R8-8I-QA Completes Sentiment Radar Evidence Logging Without Runtime Enablement

Status: accepted for documentation QA completion.

Decision: R8-8I-QA records that the `sentiment_company_radar` controlled
readiness evidence is fully represented in the reset documentation set:
controlled smoke log, readiness ladder, quality boundary, changelog, README, and
decision log. The evidence remains market-only health, compute, and
provider-free adapter mapping evidence.

Reason: R8-8I produced a successful dev-only controlled smoke for
`sentiment_company_radar`, and the follow-up QA pass ensures that the evidence
is not misread as live readiness, runtime binding enablement, risk routing, or
production readiness.

Consequence: downstream R8-8J work can proceed with a clean documentation
baseline for prior market-only evidence. The evidence can inform later
invoke-readiness and runtime-binding review, but it remains documentation-only.

Non-consequence: R8-8I-QA does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, does not update
public transcript content, and does not create or imply any
`sentiment_company_radar` risk route.

## ADR-039: R8-8J Expands Controlled Compute Evidence Without Runtime Enablement

Status: accepted for controlled L1 readiness evidence logging.

Decision: R8-8J records sanitized controlled health, compute, and adapter
mapping evidence for `financial_data_service` after bounded dev service
protocol remediation. The main-system adapter is extended only as a
provider-free pure mapper so `external_agent_compute_v0` envelopes with concrete
`data_bundle_v1` tool results can map to the internal `data_bundle_v1`
contract.

Reason: the earlier R8-8B smoke showed the L1 data service blocked on an
unstructured health boundary. The dev service was close enough for a bounded
service-side wrapper fix: structured health JSON plus a fixed-DAG compute
envelope around data-bundle evidence. The adapter needed a narrow L1
compute-envelope branch, but runtime bindings and active graph behavior remain
separate readiness concerns.

Consequence: `financial_data_service` now has documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
`data_bundle_v1`. The evidence can inform later invoke-readiness and
runtime-binding review, but remains documentation-only.

Non-consequence: R8-8J does not change runtime bindings, graph, executor, public
API, public runtime, public mapping, frontend, L3/L4 active runtime, or fixed
DAG roster. It does not call `/v1/agent/invoke`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
claim prod readiness, does not update public transcript content, and does not
wire L1 data service output into active graph execution.

## ADR-040: R8-8K Extends Controlled Compute Evidence Without Runtime Enablement

Status: accepted for entity-relation and risk controlled readiness evidence
logging.

Decision: R8-8K records sanitized controlled health, compute, and adapter
mapping evidence for `entity_relation_extractor`, `risk_identification`, and
`risk_compliance_review` after bounded dev service protocol remediation. The
main-system adapter is extended only as a provider-free pure mapper so
`external_agent_compute_v0` envelopes with concrete
`entity_relation_bundle_v1` tool results can map to the internal
`entity_relation_bundle_v1` contract.

Reason: entity relation is an L1 fixed-DAG dependency, while the two risk
services are L2 risk gate-member signals. The deployed dev services were close
to the external compute-envelope family but needed service-side identity,
wrapper, and role/dimension normalization. The correct boundary remains strict:
fixed DAG ids are primary `agent_id` values, service-owned ids remain
`external_agent_id`, risk services emit `agent_conclusion_v1 role=gate_member`,
and L3 `risk_conclusion_v1` remains a separate later integration concern.

Consequence: the three R8-8K services now have documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
either `entity_relation_bundle_v1` or `conclusion_object_v1`. The evidence can
inform later invoke-readiness and runtime-binding review, but remains
documentation-only.

Non-consequence: R8-8K does not change runtime bindings, graph, executor,
public API, public runtime, public mapping, frontend, L3/L4 active runtime, or
fixed DAG roster. It does not call `/v1/agent/invoke`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
claim prod readiness, does not update public transcript content, and does not
wire L1 entity-relation or risk L2 outputs into active graph execution.

## ADR-041: R8-8L Records Remaining Risk And Market Controlled Compute Evidence Without Runtime Enablement

Status: accepted for remaining risk controlled readiness evidence logging and
market-candidate deferral.

Decision: R8-8L records sanitized controlled health, compute, and adapter
mapping evidence for `risk_financial_fraud` and `risk_crash` after bounded dev
service protocol remediation. The two services remain L2 risk gate-member
signals represented as `agent_conclusion_v1 role=gate_member`, mapped through
the existing provider-free adapter into `conclusion_object_v1`. The market and
macro candidates that did not meet the bounded-remediation criteria remain
deferred.

Reason: the two risk dev services were deployed and listening but emitted
service-owned identities, Chinese risk dimensions, and `role=gate` values at
the adapter boundary. The correct remediation is service-side wrapper
normalization: fixed DAG ids become primary `agent_id` values, service-owned
ids remain `external_agent_id`, risk dimensions are canonical `risk`, and risk
scores are bounded before adapter mapping. This preserves the main-system
adapter identity gate and avoids forcing L3 `risk_conclusion_v1` or unrelated
market/macro payloads into L2 contracts.

Consequence: `risk_financial_fraud` and `risk_crash` now have documented
dev-only evidence for structured health, `/v1/agent/compute`, and
provider-free adapter mapping into `conclusion_object_v1`. The evidence can
inform later invoke-readiness and runtime-binding review, but remains
documentation-only.

Non-consequence: R8-8L does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, does not update
public transcript content, does not route sentiment to risk, and does not wire
any risk L2 output into L3 `risk_composite` or L4 decision runtime.

## ADR-042: R8-8M Extends Remaining L2 Controlled Compute Evidence Without Runtime Enablement

Status: accepted for remaining L2 controlled readiness evidence logging and
deferred-candidate classification.

Decision: R8-8M records sanitized controlled health, compute, and adapter
mapping evidence for `market_capital_flow_chip` after bounded dev service
protocol remediation. The service remains an L2 market direction signal
represented as `agent_conclusion_v1 role=direction`, mapped through the
existing provider-free adapter into `conclusion_object_v1`. Other R8-8M
candidates remain deferred when they emit L3/regulator semantics, have larger
protocol drift, lack a dev listener or compute endpoint, or lack non-stub
service metadata.

Reason: the money-flow service had clear source, a documented dev port, and a
bounded wrapper path into the existing L2 direction payload family. The correct
remediation is service-side identity and dimension normalization: fixed DAG id
`market_capital_flow_chip` is the primary `agent_id`, service-owned id
`money_flow` remains `external_agent_id`, and the adapter-facing dimension is
canonical `market`. Services with macro regulator payloads or broader scaffold
payload drift should not be forced into L2 direction contracts.

Consequence: `market_capital_flow_chip` now has documented dev-only evidence
for structured health, `/v1/agent/compute`, and provider-free adapter mapping
into `conclusion_object_v1`. The evidence can inform later invoke-readiness and
runtime-binding review, but remains documentation-only.

Non-consequence: R8-8M does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, does not update
public transcript content, and does not wire any market L2 output into L3
`market_composite` or L4 decision runtime.

## ADR-043: R8-8N-DOCS Persists Agent Readiness Matrix Without Runtime Enablement

Status: accepted for readiness documentation persistence.

Decision: R8-8N-DOCS persists the R8-8N read-only audit into
`docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` and
`docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md`. The matrix records the full
27-agent fixed DAG roster, controlled compute evidence, deferred/problem
agents, service patch backfill inventory, and next developer actions. The
prompt catalog gives service owners copy-ready Codex / Claude Code prompts for
service-side backfill, wrapper fixes, semantic deferrals, and future L3/L4
adapter design.

Reason: the R8-8N audit produced operationally useful readiness state, but the
audit phase was intentionally read-only. Persisting the matrix and prompt
catalog in maintained docs gives downstream developers a stable handoff without
changing runtime behavior.

Consequence: developers now have repository-local documentation for which
agents have controlled compute evidence, which remain deferred, and which
service-side protocol patches must be backfilled into service-owned
repositories before invoke audit or runtime binding work.

Non-consequence: R8-8N-DOCS does not call endpoints, does not call providers,
does not call `/v1/agent/invoke`, does not modify runtime bindings, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
change graph, executor, public API, public runtime, public mapping, frontend,
adapter logic, external service code, or fixed DAG roster, and does not prove
production readiness.

## ADR-044: R8-8P Rebaselines Agent Readiness Against Production Endpoints

Status: accepted for production readiness rebaseline.

Decision: R8-8P separates production endpoint evidence from the earlier dev
controlled smoke evidence. The fixed DAG readiness matrix is now production
first: production endpoint discovery, production `/health`, production
`/v1/agent/compute`, and provider-free adapter mapping determine production
endpoint status. Earlier R8-8G/H/I/J/K/L/M dev endpoint evidence is retained only as
historical debugging and backfill input.

Reason: the previous matrix documented useful controlled compute evidence, but
most of that evidence came from dev ports. Production readiness cannot be
inferred from dev endpoints. A production rebaseline is required before any
invoke audit, runtime binding preparation, or live verification review.

Consequence: only services with production health pass, production compute
pass, and production adapter mapping pass can be considered candidates for a
later production invoke audit. Services that passed in dev but fail production
identity, health, compute, or semantic gates must go through production
remediation/backfill and production resmoke.

Non-consequence: R8-8P does not call `/v1/agent/invoke`, does not modify
runtime bindings, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not change graph, executor, public API,
public runtime, public mapping, frontend, fixed DAG roster, adapter logic, or
production service code, and does not enable production default invocation.

## ADR-045: R8-8P-DOCS-QA Turns Production Rebaseline Into Developer Remediation Playbook

Status: accepted for production readiness documentation refinement.

Decision: R8-8P-DOCS-QA deepens
`docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` into a production problem playbook
and rewrites `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` as a copy-ready
Chinese remediation prompt catalog. Each failed/deferred production candidate
now has a specific issue, likely cause, owner action, maintainer action,
resmoke boundary, and prompt id. The prompts distinguish dev historical
evidence, production failure, production remediation, redeployment, and
production resmoke.

Reason: R8-8P established the production endpoint baseline, but service owners
need a concrete handoff that tells them exactly what failed and what to fix.
Generic prompt categories were not enough for production backfill work because
identity pairs, production endpoints, payload families, local tests, and
resmoke boundaries differ by agent.

Consequence: downstream developers can hand a specific prompt to Codex /
Claude Code or a service owner for `financial_data_service`,
`entity_relation_extractor`, `sentiment_company_radar`, value/market identity
fixes, `macro_commodity_pricing`, macro semantic decisions, L3/L4 design, and
future invoke-audit preparation. The current production matrix remains based
only on R8-8P production endpoint evidence.

Non-consequence: R8-8P-DOCS-QA does not call endpoints, does not call
providers, does not call `/v1/agent/invoke`, does not modify runtime bindings,
does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not change graph, executor, public API,
public runtime, public mapping, frontend, adapter logic, external service code,
or fixed DAG roster, and does not prove production default invocation
readiness. Dev evidence remains historical/backfill input only.

## ADR-046: R8-10B Maps L3 Composite Payloads Without Enabling Runtime

Status: accepted for provider-free adapter compatibility.

Decision: R8-10B adds pure mappings from L3 external payload families into the
existing internal `dimension_composite_result_v1` contract. Value and market
composites use `dimension_conclusion_v1`; risk composite uses
`risk_conclusion_v1`; macro composite uses `macro_conclusion_v1`. The adapter
accepts these payloads directly or inside `external_agent_compute_v0` /
`external_agent_response_v0` envelopes. Macro `dimension_weights` are restricted
to `value` and `market`; risk remains an independent gate and macro remains a
regulator rather than a direction vote.

Reason: L3 composites need member weights, gate semantics, macro regime, and
bounded provenance that L2 `agent_conclusion_v1` cannot represent. Mapping the
explicit L3 payload families lets service owners backfill correct wrappers and
lets the main system validate sanitized payloads without relaxing L2 identity
or dimension gates.

Consequence: `fixed_dag_external_adapter.py` can now map L3 payload dictionaries
into validator-legal `dimension_composite_result_v1` objects, and unit tests
cover direct plus envelope forms. The deterministic macro placeholder uses the
same value/market-only weight key policy.

Non-consequence: R8-10B does not call endpoints, does not call providers, does
not call `/v1/agent/invoke`, does not modify runtime bindings, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
wire active L3 runtime execution, does not change graph/executor/public
API/frontend behavior, does not modify external services, and does not prove
L3 production readiness.

## ADR-047: R8-10C Sends L3 Services To Protocol Backfill Before Smoke

Status: accepted for L3 service readiness documentation.

Decision: R8-10C records that the four L3 services must complete service-owner
protocol backfill before controlled L3 health/compute smoke. The main-system
adapter already supports L3 payload families from R8-10B, but that local mapper
does not make the services ready. `value_composite` needs a true
`agent_id=value_composite` L3 value wrapper; `market_composite` needs fixed DAG
member id normalization; `risk_composite` needs R8-10B-compatible fixed id,
canonical dimension, flat gate, and risk-only contributing agents; and
`macro_composite` needs fixed id/runbook alignment around `macro_conclusion_v1`.

Reason: smoking a service before its identity and payload family are aligned
would either fail predictably or encourage weakening the adapter gates. The
safer path is to give service owners precise backfill prompts, keep runtime
bindings disabled, and only run controlled L3 smoke after the service-side
wrappers are redeployed.

Consequence: `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` now includes an L3
service protocol backfill audit table, and
`docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` now includes four
service-specific L3 backfill prompts.

Non-consequence: R8-10C does not call endpoints, does not call providers, does
not call `/v1/agent/invoke`, does not modify service code, does not modify
runtime bindings, does not set live flags, does not wire active L3 runtime
execution, and does not create L3 production readiness evidence.

## ADR-048: R8-10D Backfills L3 Service Wrappers Before Controlled Smoke

Status: accepted for bounded L3 service protocol implementation.

Decision: R8-10D applies service-side protocol wrapper patches for the four L3
composites before any controlled endpoint smoke. `value_composite` and
`market_composite` use adapter-facing `dimension_conclusion_v1`; `risk_composite`
uses `risk_conclusion_v1` with a flat gate action; and `macro_composite` uses
`macro_conclusion_v1` with value/market-only `dimension_weights`. The changes
are restricted to service wrapper/schema/test layers and main-repo
documentation.

Reason: R8-10B made the main-system adapter capable of pure L3 mapping, and
R8-10C showed that service payload shape was still the gating issue. Backfilling
the wrappers first avoids weakening adapter identity/dimension gates and gives
R8-10E a meaningful controlled smoke target.

Consequence: the local service directories now contain fixed DAG L3 wrapper
paths and focused tests. A repo-external backup and manifest record the
non-git service changes at
`/tmp/lma-r8-10d-l3-service-backup/20260610T142216Z/service_patch_manifest.json`.
Service owners still need to backfill these changes into source-controlled
service repositories where applicable.

Non-consequence: R8-10D does not call `/health`, does not call
`/v1/agent/compute`, does not call `/v1/agent/invoke`, does not call providers,
does not restart services, does not modify runtime bindings, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
change main-system graph/executor/public API/frontend behavior, does not enable
active L3 runtime execution, and does not prove L3 production readiness.

## ADR-049: R8-10D-SNAPSHOT Uses A Shadow Handoff Repo For L3 Service Patches

Status: accepted for temporary service patch handoff.

Decision: because the formal source repositories for the four L3 composite
services are not available in this environment, R8-10D-SNAPSHOT records the
R8-10D service wrapper patches in a local shadow handoff repository at
`/sdb/dlut/service-shadow-repos/l3-composite-services`. The shadow repository
contains service notes, the R8-10D manifest, and zero-context patch files. It
does not mirror whole production directories.

Reason: committing directly inside `/sdb/dlut/prod/...` would treat deployed
production directories as source-of-truth repositories and risks capturing
runtime state, virtual environments, logs, data, models, or secret-bearing
deployment material. A separate shadow repo gives developers a reviewable
handoff artifact while preserving the long-term requirement that service owners
backfill patches into formal source-controlled repositories.

Consequence: service owners can inspect one local repository to understand the
L3 wrapper changes and apply them to their eventual formal service repos. The
four production service directories also include
`FIXED_DAG_PROTOCOL_BACKFILL.md` notes that point to the backup manifest and
shadow repo.

Non-consequence: R8-10D-SNAPSHOT does not call endpoints, does not restart
services, does not modify runtime bindings, does not set live flags, does not
prove that running services loaded the patched files, and does not create L3
production readiness evidence. Controlled endpoint verification remains
R8-10E.

## ADR-050: R8-10E Records L3 Production Compute Evidence Without Runtime Enablement

Status: accepted for L3 production controlled compute evidence.

Decision: R8-10E performs authorized controlled restart and production
`/health` + `/v1/agent/compute` smoke for the four L3 production services.
`market_composite`, `risk_composite`, and `macro_composite` produced production
compute payloads that mapped through the main-system L3 adapter into
`dimension_composite_result_v1`. `value_composite` failed closed at health
identity validation and did not proceed to compute.

Reason: R8-10B added pure L3 adapter mapping and R8-10D backfilled service
wrappers, but neither phase proved that production processes had loaded the
wrappers. R8-10E provides compute-level production evidence while preserving
the runtime boundary.

Consequence: the readiness matrix and controlled smoke log can list the three
passing L3 services as production compute evidence candidates for later invoke
audit planning. `value_composite` remains a service-side remediation item.

Non-consequence: R8-10E does not call `/v1/agent/invoke`, does not modify
runtime bindings, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not update public transcript content,
does not wire active graph/runtime L3 execution, and does not prove production
default invocation readiness.

## ADR-051: R8-10F Remediates Value Composite Health Identity Before Readiness Evidence

Status: accepted for scoped L3 production service remediation.

Decision: R8-10F fixes the `value_composite` production health identity on
`127.0.0.1:10015`, keeping `agent_id=value_composite`,
`external_agent_id=composite_valuation`, and
`fixed_dag_agent_id=value_composite` in structured
`external_agent_health_v0`. It also preserves the existing fixed DAG L3 compute
wrapper and verifies that production compute maps through the main-system
adapter into `dimension_composite_result_v1`.

Reason: R8-10E showed the value composite production service had loaded enough
wrapper code for L3 compute but still advertised the value-ML sample identity
from `/health`, so the readiness smoke correctly skipped compute fail-closed.
Readiness evidence should only advance after the service advertises the correct
production identity and the compute envelope maps through the existing adapter
without relaxing identity gates.

Consequence: `value_composite` joins the L3 production compute evidence set.
The service wrapper now rejects unintended value members at the protocol layer
by only emitting fixed DAG value L2 member ids.

Non-consequence: R8-10F does not call `/v1/agent/invoke`, does not modify
runtime bindings, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not change main-system adapter gates,
does not update public transcript content, and does not prove production
default invocation readiness.

## ADR-052: R8-8Q Remediates Production Compute Endpoints Without Runtime Enablement

Status: accepted for scoped production L1/L2 remediation and compute evidence.

Decision: R8-8Q applies bounded production service protocol-wrapper
remediations for selected L1/L2 candidates and then re-smokes only production
`GET /health` and `POST /v1/agent/compute`. The phase records new production
compute evidence for `value_traditional_valuation`, `value_ml_valuation`,
`value_meta_valuation`, `value_research_synthesis`,
`market_stock_technical`, `market_capital_flow_chip`,
`sentiment_company_radar`, and `market_ipo_investor_behavior`.

Reason: R8-8P showed that several services had dev evidence but production
wrappers still emitted service ids, legacy ids, Chinese dimension labels, or
missing envelope identity fields. The smallest safe remediation is to fix the
production protocol wrapper and re-run controlled compute smoke without
relaxing main-system adapter gates.

Consequence: the readiness matrix and controlled smoke log can list the eight
remediated L1/L2 services as production compute evidence candidates for later
invoke audit planning. `financial_data_service`, `entity_relation_extractor`,
`market_fund_manager_behavior`, `macro_commodity_pricing`, and semantic-deferred
macro services remain outside the pass set.

Non-consequence: R8-8Q does not call `/v1/agent/invoke`, does not modify
runtime bindings, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not update public transcript content,
does not wire active graph/runtime external execution, and does not prove
production default invocation readiness.

## ADR-053: R8-11B Runs First Controlled Production Invoke Smoke Without Runtime Enablement

Status: accepted for a tiny production invoke evidence allowlist.

Decision: R8-11B audits production `/v1/agent/invoke` source paths and then
runs a controlled invoke smoke for five low-risk services only:
`risk_identification`, `risk_compliance_review`, `risk_crash`,
`risk_financial_fraud`, and `value_research_synthesis`. The smoke uses
production endpoints, no-LLM style request options, sanitized artifacts, and
the existing provider-free fixed-DAG adapter to validate the returned
`tool_result`.

Reason: R8-8Q and R8-10E/F created production health + compute + adapter
mapping evidence, but compute evidence is below L4 invoke evidence in the
readiness ladder. A very small allowlist lets the project validate the invoke
transport and tool-result mapping boundary without enabling runtime bindings
or broad production invocation.

Consequence: the readiness matrix and controlled smoke log can mark the five
services as having controlled production invoke evidence. They may proceed to a
runtime-binding preparation review, but the config remains unchanged until a
separate approved phase owns that work.

Non-consequence: R8-11B does not push, does not modify runtime bindings, does
not set `live_verified=true`, does not set `invoke_enabled_by_default=true`,
does not make the fixed DAG graph call production services by default, does not
update public transcript content, does not weaken adapter identity gates, and
does not prove production business correctness.

## ADR-054: R8-12 Uses Default-Off Compute Bridge For Demo Before Runtime Enablement

Status: accepted for demo-only fixed DAG external compute integration.

Decision: R8-12 adds a default-off bridge that can call allowlisted production
`/v1/agent/compute` endpoints from `execute_fixed_dag_plan` only when an
explicit demo flag and allowlist are both set. Responses must map through the
provider-free fixed-DAG adapter before replacing L2/L3 placeholder outputs.

Reason: the project needs a same-day web demo that shows structured external
agent outputs flowing through the fixed DAG workflow, but runtime binding
enablement and broad production invocation are separate readiness phases. The
smallest safe bridge is demo-only, allowlisted, loopback-only, compute-only,
and fail-soft back to deterministic placeholders.

Consequence: the local API/Web demo can display a Chinese fixed-DAG report with
value, market, risk, and macro summaries sourced from mapped production compute
responses. Tests cover default-off behavior, allowlist enforcement, loopback
and `/invoke` rejection, mapping success, fallback, selected routing
coexistence, and public-safe output.

Non-consequence: R8-12 does not call `/v1/agent/invoke` from the bridge, does
not modify `runtime_bindings.json`, does not set `live_verified=true`, does not
set `invoke_enabled_by_default=true`, does not make external services default
graph dependencies, does not update public transcript content with raw external
responses, and does not prove production business correctness.

## ADR-055: R8-12B Uses SSH Tunnels For Local Demo Access To Remote Agents

Status: accepted for local demo/dev tooling.

Decision: R8-12B documents and scripts a same-port SSH tunnel workflow for
developers who run the main fixed-DAG project locally while the external
production agents remain on the server. The helpers forward only the 16 R8-12
demo allowlist ports from local `127.0.0.1` to remote `127.0.0.1`, use
`ExitOnForwardFailure=yes`, and refuse to proceed when a required local port is
already in use.

Reason: the R8-12 bridge intentionally accepts only loopback production
compute endpoints and an explicit allowlist. SSH local forwarding preserves
that loopback-only boundary for a developer laptop without exposing the
production `100xx` service ports to the public network or introducing a new
remote proxy surface.

Consequence: a developer can clone the repo locally, start the tunnel, run the
local API/Web with the R8-12 demo flags, and see the same external-compute
workflow shape against server-hosted agents. The sample allowlist JSON is
handoff documentation only; the current bridge still uses environment flags
and the built-in same-port demo registry.

Non-consequence: R8-12B does not start an SSH tunnel during validation, does
not call `/health`, `/v1/agent/compute`, or `/v1/agent/invoke`, does not store
SSH passwords or write `.env`, does not modify `runtime_bindings.json`, does
not set `live_verified=true`, does not set `invoke_enabled_by_default=true`,
and does not expose production agent ports on `0.0.0.0`.

## ADR-056: R8-12C Feeds Report Generation From Public-Safe Evidence Bundles

Status: accepted for fixed DAG report generation and workflow projection.

Decision: R8-12C introduces `report_input_bundle_v1` as the bounded input
package for the fixed DAG report generator. The executor builds the bundle from
current L2 conclusions, L3 composite results, risk gate, macro regulator, and
decision context, then passes it to `build_report_result`. The same summaries
are projected into `workflow_snapshot_v2.stepResults` as `agent_evidence` and
`composite_evidence` so the Web workflow details can show what each single
agent and composite agent contributed to the final report.

Reason: the R8-12 demo could already call allowlisted production `/compute`
services and map the results into internal contracts, but the final report did
not explicitly consume or expose the detailed L2/L3 input bundle. A bounded
report input contract makes the report generator's inputs auditable without
turning raw external payloads into public transcript content.

Consequence: report text and workflow details can explain the individual agent
signals, composite members, risk gate, and macro regulator that shaped a fixed
DAG answer. Tests validate default-off behavior, report bundle validation, no
raw leakage, and frontend rendering of the bounded summaries.

Non-consequence: R8-12C does not call production endpoints, does not call
`/v1/agent/invoke`, does not modify `runtime_bindings.json`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
make external services default runtime dependencies, and does not deploy the
main system to `/sdb/dlut/prod/langgraph-my-agent`. Production rollout requires
a separate backup, sync, validation, and restart step for the main-system
service.

## ADR-057: R8-12D Uses Default-Off LLM Synthesis For Final Reports

Status: accepted for explicit demo/runtime flag use.

Decision: R8-12D adds a default-off LLM report synthesis seam. When
`Context.enable_llm_report_synthesis` or `ENABLE_LLM_REPORT_SYNTHESIS=1` is
explicitly set, the main system may load the configured chat model and ask it
to produce a `report_result_v1` from `report_input_bundle_v1`. The synthesizer
does not receive raw external responses or endpoint URLs, and invalid or unsafe
model output fails closed to the template report.

Reason: R8-12C made the report generator's L2/L3 inputs auditable, but the
report remained template-shaped. The target demo and user workflow require the
report generator to understand the single-agent and composite-agent inputs and
write a natural Chinese final report. The safest first step is to give the
model only the bounded public-safe input bundle and keep the feature behind an
explicit flag.

Consequence: an explicit demo can combine the R8-12 external compute bridge
with R8-12D LLM report synthesis so active agent evidence informs the final
natural-language report. Public workflow provenance may show
`providerInvoked=true` when this path actually invokes the configured model.

Version management: the local annotated tag
`r8-12d-llm-report-synthesizer-fallback` anchors the current implementation
state. The tag labels this as a main-system fallback/demo seam before a formal
external `report_generator` service is wired through the fixed DAG
external-agent contract.

Future direction: the formal multi-agent implementation should move primary
report synthesis behind the `report_generator` agent contract:
`report_input_bundle_v1` in, `report_result_v1` out, with controlled compute
evidence before any invoke or runtime-binding phase. The R8-12D synthesizer can
remain as a safe fallback when that external service is unavailable.

Non-consequence: R8-12D does not call external agent `/v1/agent/invoke`, does
not modify `runtime_bindings.json`, does not set `live_verified=true`, does not
set `invoke_enabled_by_default=true`, does not make provider use default, does
not store raw model output, and does not deploy the main system to production.

## ADR-058: R8-13D Packages Sandbox L3 Repairs Before Production Backfill

Status: accepted for R8-13D handoff.

Decision: R8-13D does not directly modify the four production L3 service
directories. Instead, it packages the successful sandbox R8-13C main-system
patch, sanitized E2E trace, and reviewable candidate service patches under
`/tmp/lma-r8-13d-handoff-package/20260612T023822Z`.

Reason: the four L3 composite services need production backfill, but direct
production edits should happen only after a reviewer can inspect the exact
patch, target files, validation plan, and rollback path. A package-first phase
keeps the demonstrated sandbox flow reproducible without turning it into
unreviewed production runtime behavior.

Consequence: service owners and maintainers can review per-service patches for
`value_composite`, `market_composite`, `risk_composite`, and
`macro_composite`. The next phase may apply one patch at a time with
service-local backup, focused validation, controlled restart, and production
`/health` + `/v1/agent/compute` smoke.

Non-consequence: R8-13D does not modify `/sdb/dlut/prod`, does not call
`/v1/agent/invoke`, does not change `runtime_bindings.json`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, and does
not prove production readiness for the L3 services.

## ADR-059: R8-13E Backfills Production L3 Wrappers Without Runtime Enablement

Status: accepted for controlled production L3 protocol backfill.

Decision: R8-13E applies the reviewed R8-13D service wrapper patches to the
four production L3 composite service directories. The patches add support for
bounded `context.upstream_outputs` so `value_composite`, `market_composite`,
`risk_composite`, and `macro_composite` can synthesize their L3 payloads from
the current run's L2 outputs.

Reason: the sandbox R8-13C trace proved the intended orchestration shape, but
the formal production L3 services still needed the same protocol wrapper
behavior before a production controlled smoke could verify it. Applying only
the protocol wrapper layer keeps the business algorithms and deployment
configuration unchanged.

Consequence: the four L3 production services now pass controlled production
`/health` + `/v1/agent/compute` smoke with adapter mapping. The smoke artifact
root is `/tmp/lma-r8-13e-prod-l3-smoke/20260612T024649Z`.

Non-consequence: R8-13E does not call `/v1/agent/invoke`, does not change
`runtime_bindings.json`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, and does not enable default graph calls to
production external services.

## ADR-060: R8-13F Restores End-to-End Agent Task Trace Without Runtime Enablement

Status: accepted for default-off demo QA.

Decision: R8-13F restores the sandbox-proven main-system trace path in the
reset branch. The executor now builds `agent_task_v1` instructions,
`agent_evidence_bundle_v1`, and report input bundles that expose each agent's
bounded task, inputs, output summary, and evidence quality. The default-off
compute bridge may send bounded current-run L2 `context.upstream_outputs` to
allowlisted L3 production compute endpoints.

Reason: after R8-13E, the four production L3 services could accept upstream
outputs, but the active main-system demo bridge still did not send them. That
meant an end-to-end run could pass protocol checks without proving that L3
composites consumed the current run's L2 evidence. R8-13F fixes that main
system gap and makes the trace auditable from user question to final report.

Consequence: the R8-13F QA run
`/tmp/lma-r8-13f-prod-e2e-llm-report/20260612T030735Z` mapped 17 production
compute agents and produced a natural Chinese report from the configured
report model. The trace also exposed service quality problems, including
`direction_stance_missing` in three value L2 services and placeholder macro
slots.

Non-consequence: R8-13F does not call `/v1/agent/invoke`, does not change
`runtime_bindings.json`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not enable default graph calls to
production services, and does not store raw external responses or provider raw
output in the repository.

## ADR-061: R8-13G Backfills Value L2 Direction Stance Without Runtime Enablement

Status: accepted for controlled production service remediation.

Decision: R8-13G fixes the three production value L2 valuation service wrappers
that returned `normalized.stance` but omitted the top-level
`agent_conclusion_v1.stance` field required by the fixed DAG adapter. The
services now project the already-computed direction and confidence to top-level
`stance` / `confidence` while preserving the existing business payload.

Reason: R8-13F proved the end-to-end trace path but exposed
`direction_stance_missing` for `value_traditional_valuation`,
`value_ml_valuation`, and `value_meta_valuation`. This was a protocol shape
gap, not a valuation-model gap. Fixing it service-side keeps the main adapter
strict and avoids relaxing the fixed DAG identity or direction contract.

Consequence: after service-local validation and controlled restart, all three
value L2 services passed production `/health`, production
`/v1/agent/compute`, and main-system adapter mapping. The R8-13G E2E trace
`/tmp/lma-r8-13g-prod-e2e-llm-report/20260612T033912Z` includes those three
services as usable value-side evidence in the final configured-report run.

Non-consequence: R8-13G does not call `/v1/agent/invoke`, does not change
`runtime_bindings.json`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not enable default graph calls to
production services, and does not change valuation models, feature
engineering, scoring algorithms, data files, or deployment configuration.
