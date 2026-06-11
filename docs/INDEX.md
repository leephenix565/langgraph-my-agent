# Reset Documentation Index

This index is the reset branch documentation map. Historical docs removed in
R1-A remain available through tag `pre-fixed-dag-reset-20260604-1457`.

## Current Authority

| Path | Purpose |
| --- | --- |
| `README.md` | Reset branch overview, active R3 plan-driven execution, R4-A fixed DAG catalog projection, R4-B runtime binding registry, R4-C legacy boundary cleanup, R5-B1 frontend contract migration, R5-B2 workflow DAG inspector UI rewrite, R5-B2.6 Chinese localization/copy polish, R5-C user-facing simplification, R5-C1 business-copy professionalization, R6-B reset quality mainline rebuild, R7-G v2.3.1 external scaffold contract patch, R7-H consistency repair, R7-I report-first thought-chain presentation mode, and non-claims. |
| `AGENTS.md` | Codex and Vibe Coding workflow rules. |
| `docs/SYSTEM_MAP.md` | Active runtime topology, fixed DAG public catalog source, runtime binding source, retained legacy inputs, quality entrypoints. |
| `docs/ARCHITECTURE_FIXED_DAG.md` | Active fixed DAG executor, catalog source, runtime binding source, batches, step results, and 27 formal agent ids. |
| `docs/CONTRACTS.md` | Runtime contract/executor/catalog/binding seams, execution results, and public/runtime boundary. |
| `docs/FRONTEND_V2.md` | Frontend and workflow inspector boundary. |
| `docs/QUALITY.md` | R6-B reset mainline, frontend repo-external build gate, and manual/live/archived quality boundaries. |
| `docs/DECISIONS.md` | Reset architecture decisions. |
| `docs/CHANGELOG.md` | Reset branch changelog. |
| `docs/EXTERNAL_AGENT_HANDOFF_FIXED_DAG.md` | R7-G fixed DAG external developer handoff entry point, v2.3.1 source package boundary, payload family, wrapper compatibility note, and submission checklist. |
| `docs/EXTERNAL_AGENT_PAYLOAD_MAPPING_FIXED_DAG.md` | R7-G mapping rules from v2.3.1 external response payloads to fixed DAG contracts. |
| `docs/EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md` | R7-C readiness ladder from docs-only review to explicit live invocation approval. |
| `docs/EXTERNAL_AGENT_SAMPLE_PAYLOADS_FIXED_DAG.md` | R7-G documentation-only endpoint and v2.3.1 domain payload samples. |
| `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` | R8-8P-DOCS-QA production readiness problem playbook: 27-agent production matrix, per-agent failure causes, remediation actions, resmoke boundaries, and next phases. |
| `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` | R8-8P-DOCS-QA production remediation prompt catalog with copy-ready Chinese Codex / Claude Code prompts for service owners and maintainers. |
| `docs/DEMO_EXTERNAL_COMPUTE_DAG_RUNBOOK.md` | R8-12 default-off external compute demo runbook: flags, allowlist, API/Web launch commands, and non-claims. |
| `examples/fixed_dag_external_agent_scaffold/` | R7-G tracked repo mirror and R7-H restore source for the local `E:\muti-agent\external_agent_scaffold` distribution working copy, including schemas, samples, tests, and AI coding handoff. |

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
R6-B rebuilds the default reset mainline quality gate so it runs static, unit,
public-api, graph-smoke, and frontend while keeping fusion-gate archived/manual
and provider/live/external/demo/SFT/RARP paths outside default acceptance.
R7-C rewrites the original repo-external scaffold source package into the
fixed DAG handoff package and syncs the tracked mirror under
`examples/fixed_dag_external_agent_scaffold/`.
R7-D tightens status mapping, wrapper compatibility, distribution, and handoff
checklist wording. It does not change runtime topology, enable wrappers,
register the scaffold into the graph, modify runtime bindings, or prove live
readiness.
R7-E expands the scaffold AI coding handoff so developer-side coding agents can
audit an existing agent project, preserve its business core, wrap it as a fixed
DAG external service, add local contract tests, and return a maintainer handoff
bundle. It remains documentation only and does not change active runtime or
readiness state.
R7-F upgrades the scaffold to `external-agent-scaffold-v2.3-fixed-dag`,
restores the domain payload family, adds semantic validators, and updates the
repo mirror/docs/CHANGELOG. It remains sample-only and does not enable runtime
bindings or prove live readiness.
R7-G upgrades the scaffold to `external-agent-scaffold-v2.3.1-fixed-dag`,
patches risk-member L2 outputs, manual-review risk gates, structured dimension
members, normalized date comparison, macro directional weights, L4 score
tolerance, and distinct reasoning stages. It remains sample-only and does not
enable runtime bindings or prove live readiness.
R7-H repairs small consistency drift by aligning frontend workflow fixture
runtime metadata with backend runtime binding literals, restoring the missing
local repo-external scaffold working copy from the tracked mirror, and keeping
current docs aligned with the R7-C/R7-D/R7-G phase boundaries.
R7-I adds an `apps/web` report-first "研判思维链" disclosure derived from the
existing `workflow_snapshot_v2` payload while retaining the main assistant
report body and the technical WorkflowPanel.
R8-8N-DOCS persists the 27-agent readiness matrix and developer prompt catalog
for service owners. It is a documentation-only handoff and does not call
endpoints, enable runtime bindings, set live flags, or prove production
readiness.
R8-8P rewrites those handoff docs around production endpoint evidence. Earlier
dev-only controlled compute evidence remains historical and cannot be promoted
to production readiness.
R8-8P-DOCS-QA turns the production rebaseline into the current problem
playbook and prompt catalog for remediation/backfill work. It remains
documentation-only and does not call endpoints, change runtime bindings, set
live flags, or prove default production invocation readiness.
R8-12 adds a default-off external compute demo bridge. It only calls production
`/v1/agent/compute` when both the explicit demo flag and an allowlist are set,
does not call `/v1/agent/invoke`, does not change runtime bindings, and does
not set live flags.
It does not prove business-agent correctness, provider readiness, external
service readiness, restored fusion acceptance, or production deployment
readiness.
