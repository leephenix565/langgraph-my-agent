# SYNC-OPS-2A-R3 Artifact Store Bootstrap

SYNC-OPS-2A-R3 separates durable artifact-store bootstrap from ordinary P2S
stage execution. Creating `/sdb/dlut/ops-artifacts/agent-sync` is a one-time
infrastructure write, not an implicit side effect of every P2S run.

## Contract

The bootstrap contract uses a dedicated plan and approval:

- `agent_sync_artifact_store_bootstrap_plan_v1`
- `agent_sync_artifact_store_bootstrap_environment_v1`
- `agent_sync_artifact_store_bootstrap_approval_v1`
- `agent_sync_artifact_store_metadata_v1`

The plan lists exact `mkdir_exact` actions only. It does not allow wildcard
parents, broad recursive creation, symlink parents, ownership guessing, chown,
chgrp, setuid, or setgid. The current target root is
`/sdb/dlut/ops-artifacts/agent-sync`; the nearest existing ancestor is
`/sdb/dlut`.

## Bootstrap Sequence

The approved bootstrap executor validates the plan hash, stable environment
binding hash, approval scope, and exact action ids, then creates only the
listed directories. It writes `STORE_METADATA.json` atomically in the store
root with mode `0600` after the directory layout verifies.

SYNC-OPS-2A-R4 tightened this rollback contract. Store metadata now includes a
per-path ownership ledger, and rollback first preflights the entire store. If
the store is non-empty, foreign, missing the ownership ledger, or contains
unknown paths, rollback returns `noop_not_safe_to_remove` with
`mutation_count=0` and does not delete empty sibling directories.

## Filesystem Boundary

Artifact-store writes require same-directory temp files, `fsync`, safe relative
artifact paths, and a bootstrapped metadata marker. They do not require the
artifact store to be on the same filesystem as the sandbox.

Sandbox activation remains separate. Active sandbox, candidate, and archive
paths must still satisfy atomic rename constraints for activation.

## P2S Interaction

When the durable store is missing or lacks metadata, P2S planning may emit a
draft plan, but the plan has
`execution_status=blocked_artifact_store_not_ready`. No executable stage
approval request is emitted. `p2s stage`, `p2s verify`, `p2s activate`, and
`p2s rollback` reject the plan before creating run artifacts.

After a bootstrap run produces valid store metadata, operators must regenerate
the P2S plan and environment binding before requesting stage-only approval.

## CLI

New bootstrap commands:

- `agent-sync artifact-store bootstrap-plan`
- `agent-sync artifact-store bootstrap-validate`
- `agent-sync artifact-store bootstrap`
- `agent-sync artifact-store verify`
- `agent-sync artifact-store recover`
- `agent-sync artifact-store bootstrap-rollback`

Write commands require `--plan`, `--approval`, and `--execute`. This phase
tests those paths only in repo-external temporary directories.

## Non-Claims

R3 does not create the real artifact store, approval, lock, backup, stage, or
activation. It does not modify prod, sandbox, owner-dev, the baseline pointer,
or any process state. It does not call endpoints or inspect env values.
