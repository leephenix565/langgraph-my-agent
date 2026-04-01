# Docs Index

This page defines document roles, authority boundaries, and the recommended entrypoints for the current repo snapshot. It is a navigation and governance page, not a command runbook.

## Authority Levels

- `docs/SYSTEM_MAP.md`: S0. Operational source for runtime, benchmark, train, and eval commands, plus environment-baseline notes.
- `docs/RUNBOOK_ROUTER_SFT.md`: S0. Router-SFT reproduction and command-oriented runbook.
- `docs/CHANGELOG.md`: S0. Change history, scope boundaries, and snapshot records.
- `docs/A01_CONTRACT_SCHEMA_V0.md`: S0. a01 contract schema and runtime-consumption boundary.
- `data/a01_sft/DATA_MANIFEST.md`: S0. FINAL a01-SFT data evidence chain and archive boundary.
- `docs/PROJECT_OVERVIEW.md`: S1. Narrative entry and current engineering snapshot. It explains what the repo currently is, but it is not the command source of truth.
- `docs/archive/`: S2. Historical handoff notes, archived benchmark writeups, and non-mainline research snapshots.

## Conflict Rules

- Runtime topology, state semantics, protocol behavior, and feature boundaries: prefer `src/react_agent/*` plus focused tests.
- Commands, paths, and operational steps: prefer `docs/SYSTEM_MAP.md` and `docs/RUNBOOK_ROUTER_SFT.md`.
- a01 contract schema wording: prefer `docs/A01_CONTRACT_SCHEMA_V0.md` plus runtime validation in `src/react_agent/contract_utils.py`.
- FINAL a01-SFT data paths and archive semantics: prefer `data/a01_sft/DATA_MANIFEST.md`.
- Narrative and high-level project explanation: start from `docs/PROJECT_OVERVIEW.md`, but if it conflicts with runtime code or S0 operation docs, runtime code and S0 docs win.

## Recommended Reading Order

1. `README.md`: quick repo entry and high-level summary.
2. `docs/PROJECT_OVERVIEW.md`: current engineering snapshot and short reusable project description.
3. `docs/SYSTEM_MAP.md`: runtime entrypoints, benchmark commands, environment baseline, and ops-facing notes.
4. `docs/A01_CONTRACT_SCHEMA_V0.md`: a01 contract protocol details.
5. `docs/CHANGELOG.md`: snapshot history and scope boundaries.

## Navigation

- [README](../README.md)
- [PROJECT_OVERVIEW](PROJECT_OVERVIEW.md)
- [SYSTEM_MAP](SYSTEM_MAP.md)
- [RUNBOOK_ROUTER_SFT](RUNBOOK_ROUTER_SFT.md)
- [A01_CONTRACT_SCHEMA_V0](A01_CONTRACT_SCHEMA_V0.md)
- [CHANGELOG](CHANGELOG.md)
- [DATA_MANIFEST](../data/a01_sft/DATA_MANIFEST.md)

## Current Snapshot Notes

- Current milestone positioning remains `structure-stable`, not `quality-stable`.
- `docs/PROJECT_OVERVIEW.md` is the preferred narrative summary for the current repo snapshot.
- `docs/SYSTEM_MAP.md` remains the preferred ops-facing map for commands and environment usage.
- If a narrative sentence and a runtime behavior differ, do not treat the narrative sentence as runtime truth; check the code and focused tests first.
- Local/Codex environment baseline and Windows pytest fallback remain documented in [SYSTEM_MAP](SYSTEM_MAP.md#environment-baseline-localcodex).
