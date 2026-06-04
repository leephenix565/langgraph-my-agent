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
runtime authority in R1-B.

## ADR-002: snake_case Runtime IDs Replace aNN IDs

Status: accepted for reset target.

Decision: target formal agents use descriptive `snake_case` ids.

Reason: ids should carry stable role meaning and avoid coupling new architecture
to old catalog numbering.

Consequence: legacy config files remain until the catalog/runtime registry phase
replaces them.

## ADR-003: Sentiment Radar Is Cross-Cutting L2

Status: accepted for reset runtime.

Decision: the company sentiment radar belongs in L2 as a cross-cutting signal,
not as a fifth dimension composite.

Reason: it feeds market and risk interpretation without creating a separate L3
composite.

Consequence: L3 has four composites: market, fundamental, risk, and macro.

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
