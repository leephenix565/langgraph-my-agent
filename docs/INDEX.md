# Reset Documentation Index

This index is the reset branch documentation map. Historical docs removed in
R1-A remain available through tag `pre-fixed-dag-reset-20260604-1457`.

## Current Authority

| Path | Purpose |
| --- | --- |
| `README.md` | Reset branch overview, active R3 plan-driven execution, R4-A fixed DAG catalog projection, R4-B runtime binding registry, R4-C legacy boundary cleanup, R5-B1 frontend contract migration, R5-B2 workflow DAG inspector UI rewrite, R5-B2.6 Chinese localization/copy polish, R5-C user-facing simplification, R5-C1 business-copy professionalization, and non-claims. |
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
R4-C isolates legacy aNN registry/bootstrap into explicit compatibility modules
and keeps active `react_agent.graph` imports off old `AGENT_TOOLS`,
placeholder bootstrap, generic agent, and external HTTP wrapper implementation
paths.
R5-B1 migrates `apps/web` workflow/chat types, streaming placeholder state,
fixed DAG mocks, and frontend smoke fixtures to `workflow_snapshot_v2` and
`finalSource=reset_skeleton`.
R5-B2 rewrites WorkflowPanel as a fixed DAG inspector that renders stage
timeline, execution batches, dimension groups, selectable step result metadata,
final source, and provenance from `workflow_snapshot_v2`.
R5-B2.6 localizes and polishes visible Chinese copy for the same fixed DAG
inspector, Agents page, Settings page, frontend fixtures, and deterministic
public-safe skeleton answer without changing backend/runtime/public contracts.
R5-C further reduces normal user-facing engineering/status noise by moving
provider/search/readiness and raw enum details into workflow technical details,
Settings advanced diagnostics, docs, and tests while keeping the same public
contracts and fixed DAG topology.
R5-C1 further professionalizes default user-facing copy for dimension summaries,
step descriptions, and answer-card evidence labels without changing public
contracts or fixed DAG topology.
It does not prove business-agent correctness, provider readiness, external
service readiness, mainline/fusion-gate rebuilt gates, or production deployment
readiness.
Mainline and fusion-gate reset quality gates remain R6 work.
