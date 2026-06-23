# SYNC-OPS-2A-R4 Bootstrap Rollback Atomicity

SYNC-OPS-2A-R4 closes the artifact-store bootstrap rollback and archive
portability gaps found after R3. It does not create the real durable store and
does not execute P2S stage.

## Rollback Atomicity

Bootstrap rollback now runs in two phases:

1. A read-only preflight inspects every candidate rollback path, store metadata,
   ownership ledger entries, standard subdirectories, unknown paths, and
   non-empty run/plan/approval/backup/lock directories.
2. Execution starts only when the whole preflight is safe. It removes the
   current run's metadata and then empty directories in reverse order.

If any path is unsafe, rollback returns `noop_not_safe_to_remove` with
`mutation_count=0`, no removed files, and no removed directories. A non-empty
store is treated as one unit; rollback must not delete empty sibling
directories after discovering later content.

## Ownership Ledger

`STORE_METADATA.json` now records
`agent_sync_artifact_store_bootstrap_ownership_ledger_v1`. The ledger binds the
bootstrap run id, plan id, plan hash, and every path created by that run.
Rollback can remove only ledger paths with `created_by_this_run=true`.

The ledger prevents rollback from deleting:

- preexisting parent directories;
- paths created by another run;
- unknown files or directories;
- stores that already contain run, plan, approval, backup, lock, baseline,
  experiment, or index content.

## Partial Recovery

If bootstrap failed before metadata was written and only exact planned empty
directories exist, recovery may roll back that partial bootstrap. If metadata
belongs to a different run, the ledger is missing, or any unknown content is
present, rollback is a zero-mutation no-op and requires operator review.

## Request And Approval Types

Bootstrap approval requests now use `requested_action_ids`. Machine approvals
continue to use `approved_action_ids` and `status=approved`. An
`awaiting_machine_approval` request is not a machine approval and must be
rejected by the approval validator.

## Archive Portability

Sync archive helpers now create ZIP entries with POSIX `/` names and reject
backslashes, absolute paths, traversal components, normalized duplicates, and
symlink entries. This keeps uploaded artifacts portable across Linux and
Windows archive tooling.

## Non-Claims

R4 does not modify prod, sandbox, owner-dev, the real artifact store, real
approvals, real locks, backups, stages, activation, endpoints, process state,
or environment values. All bootstrap rollback and archive coverage runs in
repo-external temporary directories.

## 2B0 Follow-Up

SYNC-OPS-2B0 did not execute the R4 bootstrap request. The rebuilt environment
snapshot no longer matched the R4 plan-bound environment SHA, so no machine
approval was created and no real artifact-store write occurred. The R4 request
must be treated as stale. SYNC-OPS-2A-R5 supersedes the R4/2B0 environment
snapshot contract with a stable authorization binding plus execution
constraints and diagnostic observations.
