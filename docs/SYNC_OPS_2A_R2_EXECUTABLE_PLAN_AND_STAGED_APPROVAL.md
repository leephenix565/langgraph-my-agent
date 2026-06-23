# SYNC-OPS-2A-R2 Executable P2S Plan And Staged Approval

SYNC-OPS-2A-R2 freezes the executable P2S plan contract before any real
sandbox write. It supersedes the SYNC-OPS-2A-R1 plan because that plan still
carried read-only planner markers and rollback skeleton metadata even though
the temp writer could stage, verify, activate, and roll back.

## Contract

P2S plans now include `execution_contract` with a writer contract version,
artifact-store preflight, lock requirements, stage, verify, activation,
rollback, and crash-recovery contracts. Executable P2S plans may not contain
`read_only_plan_only`, `plan_only`, `future_write_only`,
`writer_not_available`, `skeleton_only`, or rollback future-phase placeholders.

Stage materialization remains separate from activation. Stage writes only a new
versioned baseline path. Activation is a later transition that can archive the
active sandbox and update the pointer only after a real stage closeout exists.

## Approval Split

The first real execution uses a stage-only approval request:

- artifact-store initialization, if needed
- stage
- verify

It does not authorize activation, rollback, pointer update, active sandbox
archive, deletion, process actions, or live validation. Activation approval is
represented only as a blocked template until a real stage run id, artifact
index hash, stage digest, validation hash, and current active pointer/tree are
available.

## Artifact Store

The configured artifact root is `/sdb/dlut/ops-artifacts/agent-sync`.
R2 performs only read-only preflight. If the root is missing, the plan records
an explicit initialization action that requires machine approval. The phase does
not create the root.

## Rollback

Rollback is modeled as an executable contract with stage-failure,
activation-before-archive, activation-after-archive,
activation-after-candidate, and wrong-run fail-closed cases. Agent rows now
reference transaction rollback ids instead of embedding skeleton rollback
objects.

## Summary Source

Plan, closeout, and terminal metrics use the same structured summary:
recursive inventory total, safe source total, materialization total, physical
write total, shared noop total, derivative, metadata, placeholder, excluded,
runtime asset, unresolved, and coverage ratio.

## Non-Claims

R2 does not create a real approval, lock, backup, stage, artifact-store run, or
activation. It does not modify prod, sandbox, owner-dev, the baseline pointer,
or any process state. It does not call endpoints or inspect env values.
