# Docs Index

## Current Documentation Roles

Agent Catalog v2 introduces two current authority documents:

- `docs/AGENT_CATALOG_V2_SHEET2_MAPPING.md`: Sheet2-to-runtime-id mapping, layer counts, external valuation id mapping, and catalog/runtime boundaries.
- `docs/AGENT_CATALOG_V2_RUNBOOK.md`: validation commands, external valuation endpoint configuration, mock-vs-live E2E boundary, and rollback notes.

External-agent docs now use one self-contained developer package under
`examples/external_agent_scaffold/`:

- `examples/external_agent_scaffold/README.md`: package landing page and local scaffold commands.
- `examples/external_agent_scaffold/EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md`: canonical external developer and maintainer handoff guide.
- `examples/external_agent_scaffold/EXTERNAL_AGENT_INTEGRATION_STANDARD.md`: canonical protocol reference.
- `examples/external_agent_scaffold/AI_CODING_HANDOFF.md`: Codex/Claude Code handoff prompts and validation checklist.
- `docs/AGENT_REPLACEMENT_GUIDE.md`: maintainer/internal replacement guide, not the third-party external-agent standard.
- `docs/EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md` and `docs/EXTERNAL_AGENT_INTEGRATION_STANDARD.md`: redirect stubs kept only for old links.

This page defines document roles, authority boundaries, and the recommended entrypoints for the current repo snapshot.

## Authority Levels

- `docs/SYSTEM_MAP.md`: S0. Operational source for environment baseline, quality entrypoints, regression artifacts, and CI-facing command guidance.
- `docs/RUNBOOK_ROUTER_SFT.md`: S0 archived/offline. Router-SFT reproduction and command-oriented training/eval runbook; not current Agent Catalog v2 acceptance evidence.
- `docs/CHANGELOG.md`: S0. Change history and phase records.
- `docs/A01_CONTRACT_SCHEMA_V0.md`: S0. a01 contract schema and runtime-consumption boundary.
- `docs/AGENT_CATALOG_V2_SHEET2_MAPPING.md`: S0. Current Agent Catalog v2 mapping authority for Sheet2 names, repo runtime ids, layer counts, external valuation id mapping, and catalog/runtime boundaries.
- `docs/AGENT_CATALOG_V2_RUNBOOK.md`: S0. Operational runbook for validating Agent Catalog v2 and external valuation wrapper behavior.
- `data/a01_sft/DATA_MANIFEST.md`: S0 archived/offline. Final a01-SFT data evidence chain and archive boundary; not current mainline acceptance evidence.
- `docs/PROJECT_OVERVIEW.md`: S1. Narrative entry and current engineering snapshot.
- `docs/MAINLINE_RUNTIME_AUDIT.md`: S1. Evidence-backed mainline runtime understanding audit for topology, state semantics, public-adapter boundaries, and default-vs-optional behavior.
- `docs/ROUTE_PRIOR_RARP_DESIGN.md`: S1 design/archive reference for the historical RARP/RP-2/RP-3 route-prior reliability layer, promotion criteria, and non-goal boundaries. It is not current Agent Catalog v2 acceptance evidence; AC-1B-2A removed the old runtime seam from `react_agent.graph`.
- `docs/FRONTEND_ARCHITECTURE.md`: S1. Frontend/product boundary, public transcript rules, and workflow-inspector rationale.
- `examples/external_agent_scaffold/README.md`: S1. External-agent developer package landing page.
- `examples/external_agent_scaffold/EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md`: S1. Canonical external developer entrypoint for building independent HTTP agents and handing them off for repo-side `AGENT_TOOLS` wrapper integration.
- `examples/external_agent_scaffold/EXTERNAL_AGENT_INTEGRATION_STANDARD.md`: S1. Canonical protocol reference for `external_agent_health_v0`, `external_agent_request_v0`, `external_agent_response_v0`, typed errors, data sources, and current wrapper compatibility boundaries.
- `examples/external_agent_scaffold/AI_CODING_HANDOFF.md`: S1. AI coding assistant handoff for implementing external agent services from the scaffold package.
- `docs/EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md`: S1 redirect only. The canonical guide lives under `examples/external_agent_scaffold/`.
- `docs/EXTERNAL_AGENT_INTEGRATION_STANDARD.md`: S1 redirect only. The canonical protocol reference lives under `examples/external_agent_scaffold/`.
- `docs/AGENT_REPLACEMENT_GUIDE.md`: S1. Maintainer/internal guide for replacing an existing repo functional agent while preserving current graph semantics. It is not the third-party external-agent standard entrypoint.
- `docs/archive/`: S2. Historical handoff notes and archived snapshots.

## Conflict Rules

- Runtime topology, state semantics, protocol behavior, and feature boundaries: prefer `src/react_agent/*` plus focused tests.
- Commands, paths, CI-facing validation steps, and environment baseline: prefer `docs/SYSTEM_MAP.md` and the quality scripts under `scripts/quality/`.
- a01 contract wording: prefer `docs/A01_CONTRACT_SCHEMA_V0.md` plus runtime validation in `src/react_agent/contract_utils.py`.
- Narrative repo description: start from `docs/PROJECT_OVERVIEW.md`, but if it conflicts with runtime code or S0 operation docs, runtime code and S0 docs win.

## Recommended Reading Order

1. `README.md`
2. `docs/PROJECT_OVERVIEW.md`
3. `docs/AGENT_CATALOG_V2_SHEET2_MAPPING.md`
4. `docs/AGENT_CATALOG_V2_RUNBOOK.md`
5. `docs/MAINLINE_RUNTIME_AUDIT.md`
6. `docs/ROUTE_PRIOR_RARP_DESIGN.md` (archive/design reference, non-mainline)
7. `docs/FRONTEND_ARCHITECTURE.md`
8. `docs/SYSTEM_MAP.md`
9. `examples/external_agent_scaffold/README.md` (external-agent developer package)
10. `examples/external_agent_scaffold/EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md` (external HTTP agent developer and maintainer handoff path)
11. `examples/external_agent_scaffold/EXTERNAL_AGENT_INTEGRATION_STANDARD.md` (protocol reference)
12. `examples/external_agent_scaffold/AI_CODING_HANDOFF.md` (Codex/Claude Code handoff)
13. `docs/AGENT_REPLACEMENT_GUIDE.md` (maintainer/internal replacement guide)
14. `docs/RUNBOOK_ROUTER_SFT.md` (archived/offline)
15. `docs/CHANGELOG.md`

## Current Snapshot Notes

- Current repo-wide phase position: `Phase F3 + QS-2`
- Agent Catalog and external-agent docs also carry narrower workstream labels such as `AC-1A`, `AC-1B`, and `EXT-DOC-*`; these are workstream labels, not replacements for the repo-wide phase position.
- The WS-1 workflow-first streaming seam is landed surface area, not the current repo phase label.
- The repo is in hardening and quality closure, not in a new feature-expansion phase.
- `scripts/quality/run_quality.py` is the repo-level quality command source of truth.
- `scripts/quality/run_provider_live_smoke.py` is an optional provider/live smoke entry and is not part of the default blocking gate.
- The current provider smoke evidence in this local environment is still `skipped` because provider/search/runtime prerequisites are not fully satisfied.
- The active frontend gate entry is `apps/web/src/test/smoke.tsx`.
- Legacy frontend fixtures use a `.legacy.tsx` suffix and are not part of the default gate.
- `docs/ROUTE_PRIOR_RARP_DESIGN.md` is a design/archive reference for route-prior reliability work. AC-1B-2A removed the old RP-1A/RP-2C runtime seam from `react_agent.graph`; RP-2A/RP-2B/RP-3A offline tooling and evidence are archived/non-mainline as of AC-1B-1. Future `router_prior_v2` work must be rebuilt from stable Agent Catalog v2 metadata, new profile cards, and new manual labels.

## Navigation

- [README](../README.md)
- [PROJECT_OVERVIEW](PROJECT_OVERVIEW.md)
- [MAINLINE_RUNTIME_AUDIT](MAINLINE_RUNTIME_AUDIT.md)
- [AGENT_CATALOG_V2_SHEET2_MAPPING](AGENT_CATALOG_V2_SHEET2_MAPPING.md)
- [AGENT_CATALOG_V2_RUNBOOK](AGENT_CATALOG_V2_RUNBOOK.md)
- [ROUTE_PRIOR_RARP_DESIGN](ROUTE_PRIOR_RARP_DESIGN.md)
- [FRONTEND_ARCHITECTURE](FRONTEND_ARCHITECTURE.md)
- [EXTERNAL_AGENT_SCAFFOLD_PACKAGE](../examples/external_agent_scaffold/README.md)
- [EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE](../examples/external_agent_scaffold/EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md)
- [EXTERNAL_AGENT_INTEGRATION_STANDARD](../examples/external_agent_scaffold/EXTERNAL_AGENT_INTEGRATION_STANDARD.md)
- [AI_CODING_HANDOFF](../examples/external_agent_scaffold/AI_CODING_HANDOFF.md)
- [AGENT_REPLACEMENT_GUIDE](AGENT_REPLACEMENT_GUIDE.md)
- [SYSTEM_MAP](SYSTEM_MAP.md)
- [RUNBOOK_ROUTER_SFT](RUNBOOK_ROUTER_SFT.md)
- [A01_CONTRACT_SCHEMA_V0](A01_CONTRACT_SCHEMA_V0.md)
- [CHANGELOG](CHANGELOG.md)
- [DATA_MANIFEST](../data/a01_sft/DATA_MANIFEST.md)

## Examples

- `examples/external_agent_scaffold/`: canonical external-agent developer package.
  It contains the scaffold service, protocol docs, AI coding handoff, sample
  requests, and contract tests. It is not registered in `AGENT_TOOLS` and does
  not participate in the default graph runtime.

Navigation note: `ROUTE_PRIOR_RARP_DESIGN`, `RUNBOOK_ROUTER_SFT`, and
`DATA_MANIFEST` are retained as archive/design/offline lineage references. They
are not current Agent Catalog v2 acceptance evidence.
