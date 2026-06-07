# Changelog

## 2026-06-07 - Phase R7-G v2.3.1 scaffold contract patch

### Changed

- Upgraded the package target to
  `external-agent-scaffold-v2.3.1-fixed-dag`.
- Patched `agent_conclusion_v1` so L2 direction members use `stance` and L2
  risk gate members use `risk_score`.
- Added safe dictionary fields for `raw_output` and `quality`; these are
  handoff audit metadata and not graph state.
- Added `manual_review` as a risk gate value.
- Changed `dimension_conclusion_v1.members` to canonical `DimensionMember[]`
  and validate member weight sum plus weighted stance.
- Normalized supported date formats before anti-lookahead comparison.
- Restricted macro `dimension_weights` to directional `value` and `market`.
- Relaxed L4 score/final-score tolerance to `0.01` and validate distinct
  reasoning stages.
- Updated samples, docs, tests, and service metadata for v2.3.1.

### Not Done

- No active graph registration.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No production deployment claim.

## 2026-06-06 - Phase R7-F v2.3 domain payload superset and semantic validators

### Changed

- Upgraded package wording from `fixed-dag-scaffold-v0.1` to
  `external-agent-scaffold-v2.3-fixed-dag`.
- Restored the v2.3 domain payload family while keeping fixed DAG three-id
  rules, canonical English dimensions, readiness boundaries, and Non-Claims.
- Added `validate_tool_result` semantic validation for anti-lookahead,
  publish-time boundaries, evidence shape, confidence bounds, risk gate
  placement, macro regulator placement, value/market weights, decision
  reasoning depth, decision score trace, data bundle replay ids, and aNN
  primary-id rejection.
- Added domain sample payloads for `agent_conclusion_v1`,
  `dimension_conclusion_v1`, `risk_conclusion_v1`, `macro_conclusion_v1`,
  `decision_conclusion_v1`, `eval_record_v1`, `fixed_dag_plan_v1`, and
  `data_bundle_v1`.
- Clarified that the default service remains a deterministic L2 sample, while
  the wider payload family is covered by schemas, samples, and tests.

### Not Done

- No active graph registration.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No production deployment claim.

## 2026-06-06 - AI coding handoff expansion

### Changed

- Expanded `AI_CODING_HANDOFF.md` into a full Codex / Claude Code operating
  manual for adapting a developer-owned agent project into a fixed DAG external
  service.
- Added audit-first procedure, implementation-mode neutrality, adaptation
  patterns, service contract rules, payload rules, mapping target, developer
  project file strategy, tests, validation commands, handoff bundle checklist,
  final response format, and copy-paste prompt template.
- Clarified that coding agents must preserve the developer's business core and
  must not modify main-system runtime, `AGENT_TOOLS`, `config/agents`, or
  runtime binding enablement.

### Not Done

- No service runtime behavior change.
- No schema or sample payload change.
- No active graph registration.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No production deployment claim.

## 2026-06-06 - Documentation consistency pass

### Changed

- Clarified status mapping across external service status, adapter decision,
  and fixed DAG validator status.
- Clarified that legacy repo wrapper compatibility code may still emit compact
  legacy-shaped payloads until R8 adapter work, but new external services
  should implement this fixed DAG scaffold contract.
- Clarified the relationship between the tracked repo mirror, the local
  distribution working copy, and generated zip artifacts.
- Tightened the developer handoff checklist to include ids, samples, test
  output, timestamp/evidence/confidence policies, performance notes,
  dependencies, known limitations, and no-secrets confirmation.

### Not Done

- No active graph registration.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No production deployment claim.

## 2026-06-05 - Fixed DAG scaffold migration

### Changed

- Rewrote the package from the historical scaffold protocol package /
  v2.1-v2.2.1 lineage into `fixed-dag-scaffold-v0.1`.
- Replaced old `main_agent_id`, aNN primary id, `AGENT_TOOLS`, and
  `config/agents` handoff language with fixed DAG `snake_case agent_id`,
  `external_agent_id`, and optional `legacy_agent_id`.
- Rebuilt `schemas.py`, `service.py`, sample requests, and tests around fixed
  DAG external handoff boundaries.
- Updated all package docs for fixed DAG catalog/runtime binding/contract
  authority, readiness ladder, no-live-readiness claims, and implementation
  mode neutrality.

### Added

- `AgentConclusionToolResult`
- `ImplementationNotes`
- `legacy_agent_id` in sample request/response paths
- `sample_requests/error.response.json`
- Local tests for fixed DAG id acceptance, aNN primary id rejection, mapping to
  `conclusion_object_v1`, sample response sync, safety, and no provider or
  external calls.

### Not Done

- No active graph registration.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No production deployment claim.
