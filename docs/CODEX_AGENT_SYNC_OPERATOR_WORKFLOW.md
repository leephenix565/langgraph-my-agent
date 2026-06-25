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
For R7X and later, reject V6 plans unless the projection and materialization
physical tree digests match under one entry contract. Require explicit
directory mode actions and a temp rehearsal bound to the final plan by action
semantics.
After a 5B source-loss cutover and full P2S rebase have real closeouts, do not
let a stale first-cycle change unit block or roll back those upstream results.
Mark only the stale experiment/cycle packet superseded and generate a new exact
non-zero tests/docs packet from the active baseline.
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
For first non-zero packets generated after 5B, confirm that the plan passed to
the CLI has `schema_version=agent_sync_publish_and_rebase_cycle_v1`. If the
packet only has `agent_sync_first_nonzero_cycle_plan_v1`, generate the strict
envelope and approval request without changing the child S2P/P2S plans or
action ids, then stop for exact machine approval.
After SYNC-OPS-5C-FINAL, an approved strict non-zero cycle may be executed
through the same CLI. The approval bundle must be exact for the strict cycle
hash and S2P/P2S action ids, and process/live/delete/invoke/provider/owner-dev
permissions must remain false.
