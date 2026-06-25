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
For R3X and later, launch authority must be a process manager or the approved
sync-ops supervised launcher contract. Do not execute ad hoc shell commands or
read environment values.
For R4X and later, a source-loss cutover request is valid only after the exact
sibling candidate has passed the real shadow-canary closeout. Do not collapse
cutover, P2S stage, P2S activation, experiment materialization, and first
publish into one broad approval.
For R5X and later, do not reuse the canary directory as the production cutover
candidate. Require the V5 plan to bind canonical target, archive path, fresh
candidate path, production launch authority, complete tree descriptors, exact
action ids, SIGTERM/no-SIGKILL policy, and roll-forward-only failure states.
For R6X and later, require the V6 clean candidate projection: 67 files, 10
parent directories, one root entry, 78 total entries, no runtime/unknown/
unexpected entries, complete file type/mode/executable metadata, and
non-mutating offline validation proof.
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
