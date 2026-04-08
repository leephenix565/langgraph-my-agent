# Docs Index

This page defines document roles, authority boundaries, and the recommended entrypoints for the current repo snapshot.

## Authority Levels

- `docs/SYSTEM_MAP.md`: S0. Operational source for environment baseline, quality entrypoints, regression artifacts, and CI-facing command guidance.
- `docs/RUNBOOK_ROUTER_SFT.md`: S0. Router-SFT reproduction and command-oriented training/eval runbook.
- `docs/CHANGELOG.md`: S0. Change history and phase records.
- `docs/A01_CONTRACT_SCHEMA_V0.md`: S0. a01 contract schema and runtime-consumption boundary.
- `data/a01_sft/DATA_MANIFEST.md`: S0. Final a01-SFT data evidence chain and archive boundary.
- `docs/PROJECT_OVERVIEW.md`: S1. Narrative entry and current engineering snapshot.
- `docs/FRONTEND_ARCHITECTURE.md`: S1. Frontend/product boundary, public transcript rules, and workflow-inspector rationale.
- `docs/AGENT_REPLACEMENT_GUIDE.md`: S1. Engineering guide for replacing an existing functional agent with a classmate-developed implementation while keeping current graph semantics.
- `docs/archive/`: S2. Historical handoff notes and archived snapshots.

## Conflict Rules

- Runtime topology, state semantics, protocol behavior, and feature boundaries: prefer `src/react_agent/*` plus focused tests.
- Commands, paths, CI-facing validation steps, and environment baseline: prefer `docs/SYSTEM_MAP.md` and the quality scripts under `scripts/quality/`.
- a01 contract wording: prefer `docs/A01_CONTRACT_SCHEMA_V0.md` plus runtime validation in `src/react_agent/contract_utils.py`.
- Narrative repo description: start from `docs/PROJECT_OVERVIEW.md`, but if it conflicts with runtime code or S0 operation docs, runtime code and S0 docs win.

## Recommended Reading Order

1. `README.md`
2. `docs/PROJECT_OVERVIEW.md`
3. `docs/FRONTEND_ARCHITECTURE.md`
4. `docs/SYSTEM_MAP.md`
5. `docs/AGENT_REPLACEMENT_GUIDE.md`
6. `docs/RUNBOOK_ROUTER_SFT.md`
7. `docs/CHANGELOG.md`

## Current Snapshot Notes

- Current phase: `Phase QS-3：final residual polish`
- The repo is in quality closure, not in a new feature-expansion phase.
- `scripts/quality/run_quality.py` is the repo-level quality command source of truth.
- `scripts/quality/run_provider_live_smoke.py` is an optional provider/live smoke entry and is not part of the default blocking gate.
- The current provider smoke evidence in this local environment is still `skipped` because provider/search/runtime prerequisites are not fully satisfied.
- The active frontend gate entry is `apps/web/src/test/smoke.tsx`.
- Legacy frontend fixtures use a `.legacy.tsx` suffix and are not part of the default gate.

## Navigation

- [README](/E:/langgraph-my-agent/README.md)
- [PROJECT_OVERVIEW](/E:/langgraph-my-agent/docs/PROJECT_OVERVIEW.md)
- [FRONTEND_ARCHITECTURE](/E:/langgraph-my-agent/docs/FRONTEND_ARCHITECTURE.md)
- [AGENT_REPLACEMENT_GUIDE](/E:/langgraph-my-agent/docs/AGENT_REPLACEMENT_GUIDE.md)
- [SYSTEM_MAP](/E:/langgraph-my-agent/docs/SYSTEM_MAP.md)
- [RUNBOOK_ROUTER_SFT](/E:/langgraph-my-agent/docs/RUNBOOK_ROUTER_SFT.md)
- [A01_CONTRACT_SCHEMA_V0](/E:/langgraph-my-agent/docs/A01_CONTRACT_SCHEMA_V0.md)
- [CHANGELOG](/E:/langgraph-my-agent/docs/CHANGELOG.md)
- [DATA_MANIFEST](/E:/langgraph-my-agent/data/a01_sft/DATA_MANIFEST.md)
