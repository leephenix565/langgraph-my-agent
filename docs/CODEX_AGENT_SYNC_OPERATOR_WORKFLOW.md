# Codex Agent Sync Operator Workflow

Use this short prompt for future server Codex sessions:

```text
Read AGENTS.md and docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md.
For the named experiment manifest, audit the current repo and durable artifact
store, generate a cycle plan, validate it, and stop for exact machine approval.
If validation reports missing source-bearing baseline mappings, stop and emit a
repair request instead of producing a non-zero approval request.
If risk_financial_fraud is missing current prod source, use the R1X
source-recovery path; do not approve or execute the superseded 67-action
baseline-only repair.
If the process is still running from an empty source root, treat it as R2X
source-loss. Stop at launch-authority blockers; do not invent a restart
launcher, read env values, or call an empty-tree restore rollback.
Do not approve by chat text. Do not write prod, active sandbox, owner-dev,
processes, or endpoints.

If the user later provides an exact approval bundle for the same cycle hash,
run:

python scripts/ops/agent_syncctl.py cycle publish-and-rebase \
  --cycle-plan <cycle-plan.json> \
  --approval-bundle <approval-bundle.json> \
  --execute

Report the durable run id, prod/sandbox/pointer before-after digests, process
and endpoint counts, recovery status, topic status, and non-claims.
```

Codex must not bypass the CLI, mutate files directly, create replacement
approvals, perform semantic merges, invoke endpoints, operate processes, or
reuse a no-op approval for a non-zero cycle.
