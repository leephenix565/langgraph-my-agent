# Changelog

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
