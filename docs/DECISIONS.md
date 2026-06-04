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

Status: accepted for reset target.

Decision: target formal agents use descriptive `snake_case` ids.

Reason: ids should carry stable role meaning and avoid coupling new architecture
to old catalog numbering.

Consequence: legacy config files remain until the catalog/runtime registry phase
replaces them.

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
