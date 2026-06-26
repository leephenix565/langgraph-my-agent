# Documentation Index

This index is navigation only. Current facts live in the authority documents
below; historical phase records live under `docs/history/` and are indexed by
`docs/history/MANIFEST.json`.

## Start Here

1. [`README.md`](../README.md) - repository overview.
2. [`AGENTS.md`](../AGENTS.md) - operator and Codex workflow policy.
3. [`docs/INDEX.md`](INDEX.md) - this navigation map.
4. [`docs/CURRENT_STATUS.md`](CURRENT_STATUS.md) - current status and next theme.
5. [`docs/ARCHITECTURE_FIXED_DAG.md`](ARCHITECTURE_FIXED_DAG.md) - fixed DAG architecture.
6. [`docs/CONTRACTS.md`](CONTRACTS.md) - runtime and public contracts.
7. [`docs/QUALITY.md`](QUALITY.md) - quality gates and validation boundaries.
8. [`docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md`](AGENT_SYNC_ONE_COMMAND_WORKFLOW.md) - sync operations runbook.

## Current Authority

| Path | Purpose |
| --- | --- |
| [`README.md`](../README.md) | Repository overview and non-claims. |
| [`AGENTS.md`](../AGENTS.md) | Codex workflow, sync approval boundaries, and safety policy. |
| [`docs/CURRENT_STATUS.md`](CURRENT_STATUS.md) | Current operational status, active baseline, and current engineering theme. |
| [`docs/REPOSITORY_CONSOLIDATION_CLOSEOUT.md`](REPOSITORY_CONSOLIDATION_CLOSEOUT.md) | Final closeout for repository authority and active-core consolidation. |
| [`docs/SYSTEM_MAP.md`](SYSTEM_MAP.md) | Current runtime topology and operational map. |
| [`docs/ARCHITECTURE_FIXED_DAG.md`](ARCHITECTURE_FIXED_DAG.md) | Logical 27-agent DAG architecture and catalog semantics. |
| [`docs/CONTRACTS.md`](CONTRACTS.md) | Internal/public contract and schema boundaries. |
| [`docs/QUALITY.md`](QUALITY.md) | Maintained quality gates and live/manual exclusions. |
| [`docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md`](REPO_ENVIRONMENT_AND_DOCS_GUIDE.md) | Dev/prod/sandbox roles, owner boundaries, and docs governance. |

## Current Status

- [`docs/CURRENT_STATUS.md`](CURRENT_STATUS.md) is the single status summary.
- [`docs/REPOSITORY_CONSOLIDATION_CLOSEOUT.md`](REPOSITORY_CONSOLIDATION_CLOSEOUT.md)
  records the completed repository authority and active-core consolidation theme.
- [`docs/CHANGELOG.md`](CHANGELOG.md) records changes over time; it is not the
  current status authority.
- [`docs/history/`](history/README.md) preserves historical evidence and phase
  closeouts.

## Runbooks

| Path | Purpose |
| --- | --- |
| [`docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md`](AGENT_SYNC_ONE_COMMAND_WORKFLOW.md) | Normal strict publish-and-rebase workflow. |
| [`docs/CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md`](CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md) | Short Codex operator prompt wrapper. |
| [`docs/DEMO_EXTERNAL_COMPUTE_DAG_RUNBOOK.md`](DEMO_EXTERNAL_COMPUTE_DAG_RUNBOOK.md) | Default-off external compute demo. |
| [`docs/LOCAL_REMOTE_AGENT_DEMO_RUNBOOK.md`](LOCAL_REMOTE_AGENT_DEMO_RUNBOOK.md) | Local remote-agent demo over SSH tunnel. |

## Reference

| Path | Purpose |
| --- | --- |
| [`docs/FRONTEND_V2.md`](FRONTEND_V2.md) | Frontend/public transcript boundary. |
| [`docs/EXTERNAL_AGENT_PAYLOAD_MAPPING_FIXED_DAG.md`](EXTERNAL_AGENT_PAYLOAD_MAPPING_FIXED_DAG.md) | External payload mapping rules. |
| [`docs/EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md`](EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md) | Readiness ladder and live invocation boundary. |
| [`docs/AGENT_READINESS_MATRIX_FIXED_DAG.md`](AGENT_READINESS_MATRIX_FIXED_DAG.md) | Current production readiness problem playbook. |
| [`docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md`](DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md) | Owner-facing remediation prompt catalog. |
| [`docs/报告完善计划（中文）.md`](报告完善计划（中文）.md) | Report-quality improvement plan. |
| [`examples/fixed_dag_external_agent_scaffold/`](../examples/fixed_dag_external_agent_scaffold/) | Tracked external scaffold mirror. |

## Operations / Sync

- Current runbook: [`docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md`](AGENT_SYNC_ONE_COMMAND_WORKFLOW.md).
- Operator prompt wrapper: [`docs/CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md`](CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md).
- Historical sync closeouts: [`docs/history/sync-ops/`](history/sync-ops/).

## Quality

- Current quality policy: [`docs/QUALITY.md`](QUALITY.md).
- Historical evidence docs are discoverable through manifest/link checks, not
  current authority prose.

## Decisions / Changelog

- [`docs/DECISIONS.md`](DECISIONS.md) records ADRs.
- [`docs/CHANGELOG.md`](CHANGELOG.md) records chronological changes.

## Historical Evidence

Historical records are retained under [`docs/history/`](history/README.md):

- `backfill/` - 3 retained historical records.
- `cs1/` - 4 retained historical records.
- `misc/` - 5 retained historical records.
- `r8/` - 6 retained historical records.
- `releases/` - 1 retained historical records.
- `sync-ops/` - 26 retained historical records.

Use [`docs/history/MANIFEST.json`](history/MANIFEST.json) for original-path mapping, content hashes, and retained reference classes.
