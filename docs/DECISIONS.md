# Decisions

This document records reset branch decisions. It is intentionally short; deeper historical context is preserved by the pre-reset tag.

## ADR-001: Fixed DAG Replaces Route Mode Routing

Status: accepted for reset target.

Decision: the new main architecture is a fixed topological DAG with explicit stages and dimension composites.

Reason: the reset needs deterministic structure, clearer public workflow projection, and fewer historical branches.

Consequence: old mode prompt/parser/state/public workflow code remains only until later phases remove or replace it.

## ADR-002: snake_case Runtime IDs Replace aNN IDs

Status: accepted for reset target.

Decision: target formal agents use descriptive `snake_case` ids.

Reason: ids should carry stable role meaning and avoid coupling new architecture to old catalog numbering.

Consequence: legacy config files remain until the catalog/runtime registry phase replaces them.

## ADR-003: Sentiment Radar Is Cross-Cutting L2

Status: accepted for reset target.

Decision: the company sentiment radar belongs in L2 as a cross-cutting signal, not as a fifth dimension composite.

Reason: it feeds market, risk, value, and macro interpretation without creating a separate L3 composite.

Consequence: L3 has four composites: value, market, risk, and macro.

## ADR-004: Pre-Reset Tag Preserves Old History

Status: accepted.

Decision: old docs, data, archive tests, and training lineage removed in R1-A are recovered through `pre-fixed-dag-reset-20260604-1457`.

Reason: the active reset branch should stay small and unambiguous.

Consequence: current docs should not link old lineage as active authority.

## ADR-005: Frontend Shell Is Retained For Later In-Place Rewrite

Status: accepted for R1-A.

Decision: R1-A keeps `apps/web` and the current public adapter while documenting the target frontend boundary.

Reason: deleting frontend workflow components before public contract replacement would break current tests and product shell.

Consequence: frontend v2 is deferred to a later phase.
