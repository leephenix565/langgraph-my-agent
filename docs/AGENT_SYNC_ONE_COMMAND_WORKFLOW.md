# Agent Sync One-Command Workflow

Current status for the completed first strict non-zero cycle lives in
`docs/CURRENT_STATUS.md`. Historical SYNC-OPS phase records live under
`docs/history/sync-ops/` and are indexed by `docs/history/MANIFEST.json`.

This runbook is the normal operator path for future sandbox-to-prod publishes.
It assumes the durable artifact store at
`/sdb/dlut/ops-artifacts/agent-sync` is available and that the current active
baseline pointer is valid.

## Daily Flow

1. Fork an experiment from a registered immutable baseline.

```bash
python scripts/ops/agent_syncctl.py experiment fork \
  --baseline-id 20260624T060045Z \
  --workspace-root /sdb/dlut/sandbox/experiments/<experiment_id>/fixed-dag-services
```

2. Register explicit change units in the experiment manifest. Every non-noop
   file action must belong to exactly one change unit.

3. Inspect the B/S/P/D diff.

```bash
python scripts/ops/agent_syncctl.py experiment diff --manifest experiment.json
```

4. Create and validate a publish-and-rebase cycle plan.

```bash
python scripts/ops/agent_syncctl.py cycle plan \
  --experiment experiment.json \
  --output cycle-plan.json
python scripts/ops/agent_syncctl.py cycle validate --cycle-plan cycle-plan.json
```

5. Request machine approval. The approval bundle must bind the exact cycle,
   S2P, P2S, experiment, action scopes, and capability flags.

   Do not request approval if any normal Agent has an empty baseline,
   experiment, or prod descriptor without an explicit registered-empty
   disposition. If the current prod source tree is missing, freeze prod source
   recovery first; do not execute an old baseline-only repair plan.

6. Execute only with the approved bundle.

```bash
python scripts/ops/agent_syncctl.py cycle publish-and-rebase \
  --cycle-plan cycle-plan.json \
  --approval-bundle approval-bundle.json \
  --execute
```

7. Use status/recover if the command is interrupted.

```bash
python scripts/ops/agent_syncctl.py cycle status --run-root <run-root>
python scripts/ops/agent_syncctl.py cycle recover --run-root <run-root>
```

## Boundaries

- Never edit the active sandbox directly.
- Never publish a whole sandbox tree.
- Never use a no-op approval bundle for non-zero actions.
- Process, live, delete, owner handoff, and publish-and-rebase are separate
  approval flags.
- Sanitized derivatives are blocked by default unless converted into an
  explicitly reviewed prod-safe refactor.
- Owner-dev repositories are read-only for this workflow.
- `/v1/agent/invoke` is not part of sync validation.

## Blockers

The cycle fails closed on target drift, digest scope mismatch, unregistered
experiment changes, owner authority conflicts, unsupported delete, process
authority gaps, projection mismatch, lock conflict, rollback failure, and
missing source-bearing baseline mappings.

`risk_financial_fraud` has an additional recovery-first guard from
SYNC-OPS-5A-R1X: the superseded 67-action repair plan must not be approved or
executed. Historical baseline bytes can seed a recovery plan only after a source
authority decision, and P2S rebase must materialize a full 26-Agent baseline.
SYNC-OPS-5A-R2X adds that if the service is still running from a deleted source
tree, execution is blocked until launch authority is explicit. Recovery must
materialize a sibling candidate, pass a shadow canary, and roll forward; an
empty-tree restore is not rollback.
SYNC-OPS-5A-R3X adds that launch authority must be a process manager or the
approved sync-ops supervised launcher. Do not treat copied argv text as
executable authority.
SYNC-OPS-5A-R4X adds that source-loss cutover approval requires a real
pre-cutover shadow canary closeout. Do not request P2S stage, P2S activation,
experiment materialization, or first-cycle approval until the preceding node in
the conditional approval chain has a real closeout SHA.
SYNC-OPS-5A-R5X adds that the cutover approval itself must bind a fresh
candidate, canonical archive, complete tree descriptors, production launch
authority, exact action ids, and roll-forward failure states. The R4X canary
directory is evidence only and must not be renamed into production.
SYNC-OPS-5A-R6X adds that the 5B cutover candidate must be a clean pre-start
projection from exact file actions. Reject V5 requests and any plan whose fresh
candidate descriptor contains pycache, runtime files, unknown entries, or file
actions without type/mode/executable metadata.
SYNC-OPS-5A-R7X adds that projection and materialization must share a physical
tree digest contract. Reject V6 requests when the clean projected digest and
the exact 67-file rehearsal digest differ, directory modes are not explicit, or
the rehearsal is not bound to final action semantics.

SYNC-OPS-5B-X adds that completed source-loss and P2S closeouts are not
invalidated by a stale downstream change unit. If the selected experiment patch
is already present in prod and the active baseline, supersede that
experiment/cycle packet and generate a new exact non-zero packet from the
current active baseline.
SYNC-OPS-5C-R1 adds that a first non-zero summary packet is not the executable
cycle contract. Before approval or execution, wrap the frozen experiment,
change unit, S2P child, projected prod-after descriptor, and P2S child in the
formal `agent_sync_publish_and_rebase_cycle_v1` strict envelope. Use
`agent-sync cycle validate` and publish-and-rebase dry-run to confirm
`ready_for_machine_approval`.
SYNC-OPS-5C-FINAL adds that strict non-zero execution is allowed only with an
exact `agent_sync_cycle_approval_bundle_v1`. The approved bundle must match
the strict cycle hash and the two requested S2P/P2S action ids. Execution
records a single-file backup, focused offline test, prod-after descriptor
proof, P2S stage/activation proof, final parity, owner handoff, and zero
process/live/delete/provider/owner-dev actions.

## Codex Operator Prompt

This prompt was formerly its own document (`CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md`, merged here during doc cleanup). Use it for future server Codex sessions:

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
sibling candidate has passed the real shadow-canary closeout.
For R5X and later, require V5 plan to bind canonical target, archive path,
fresh candidate path, production launch authority, complete tree descriptors,
exact action ids, SIGTERM/no-SIGKILL policy, and roll-forward-only failure states.
For R6X and later, require V6 clean candidate projection: complete file
type/mode/executable metadata and non-mutating offline validation proof.
For R7X and later, reject V6 plans unless projection and materialization
physical tree digests match under one entry contract.
After a 5B source-loss cutover and full P2S rebase have real closeouts, do not
let a stale first-cycle change unit block or roll back those upstream results.
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
Codex must not bypass the CLI, mutate files directly, create replacement
approvals, perform semantic merges, invoke endpoints, operate processes, or
reuse a no-op approval for a non-zero cycle.
For first non-zero packets generated after 5B, confirm the packet passed to the
CLI has `schema_version=agent_sync_publish_and_rebase_cycle_v1`. If the packet
only has `agent_sync_first_nonzero_cycle_plan_v1`, generate the strict envelope
and approval request without changing child S2P/P2S action ids, then stop for
exact machine approval.
After SYNC-OPS-5C-FINAL, an approved strict non-zero cycle may be executed
through the same CLI. The approval bundle must be exact for the strict cycle
hash and S2P/P2S action ids, and process/live/delete/invoke/provider/owner-dev
permissions must remain false.
```
