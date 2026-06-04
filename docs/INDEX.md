# Reset Documentation Index

This index is the reset branch documentation map. Historical docs removed in
R1-A remain available through tag `pre-fixed-dag-reset-20260604-1457`.

## Current Authority

| Path | Purpose |
| --- | --- |
| `README.md` | Reset branch overview, active R3 plan-driven execution, R4-A fixed DAG catalog projection, R4-B runtime binding registry, and non-claims. |
| `AGENTS.md` | Codex and Vibe Coding workflow rules. |
| `docs/SYSTEM_MAP.md` | Active runtime topology, fixed DAG public catalog source, runtime binding source, retained legacy inputs, quality entrypoints. |
| `docs/ARCHITECTURE_FIXED_DAG.md` | Active fixed DAG executor, catalog source, runtime binding source, batches, step results, and 27 formal agent ids. |
| `docs/CONTRACTS.md` | Runtime contract/executor/catalog/binding seams, execution results, and public/runtime boundary. |
| `docs/FRONTEND_V2.md` | Frontend and workflow inspector boundary. |
| `docs/QUALITY.md` | Safe validation commands for reset phases. |
| `docs/DECISIONS.md` | Reset architecture decisions. |
| `docs/CHANGELOG.md` | Reset branch changelog. |

## Removed Lineage

R1-A removed old Agent Catalog v2 docs, route-prior/RARP docs, Router-SFT docs,
A01 SFT docs/data, archive docs/tests, old route-prior helper source, old
regression/training ops, and the external-agent scaffold package.

These removed files are not current reset authority. Use the pre-reset tag only
when historical recovery is required.

## Current Caveat

R3 proves deterministic plan-driven execution topology, dependency validation,
execution batch/result projection, v4 roster alignment, and backend
contract/executor seam alignment.
R3.6 adds the v4 Excel workbook as an R4 catalog/runtime registry input and
cleans only high-confidence dead files.
R4-A adds `config/fixed_dag/agent_catalog.json` as the active backend catalog
source and switches `/api/agents` to the 27-agent `snake_case` reset projection.
R4-B adds `config/fixed_dag/runtime_bindings.json` and
`src/react_agent/fixed_dag_runtime_registry.py` as the backend runtime binding
registry and annotates executor step results with binding metadata.
It does not prove business-agent correctness, frontend v2 completion, provider
readiness, external service readiness, mainline/fusion-gate rebuilt gates, or
production deployment readiness.
Mainline and fusion-gate reset quality gates remain R6 work.
