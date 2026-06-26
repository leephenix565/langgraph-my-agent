# SYNC-OPS-2B0 Durable Artifact Store Bootstrap

SYNC-OPS-2B0 attempted to execute the first real durable artifact-store
bootstrap for `/sdb/dlut/ops-artifacts/agent-sync` using the exact
R4-approved bootstrap plan:

- plan id: `bootstrap_4af904444541`
- plan SHA:
  `3f5719a673bf324cd2d7b3379e3813dc6b476496e21ca5772c099bb4371b8290`
- environment SHA:
  `760dbc5ea0f1c32501e55f89be829c133d7cfff2ad0ec36fc5805a7a2ec66ee4`

The plan was not executed. Before creating a machine approval, the operator
rebuilt the environment snapshot and found that the current environment SHA no
longer matched the approved SHA. The mismatch invalidated the approval path, so
no machine approval was created and no real artifact-store write occurred.

SYNC-OPS-2A-R5 later classified that mismatch as a contract issue: the old
environment SHA included volatile observations such as exact free bytes and
irrelevant supplementary groups. Future bootstrap approval binds
`environment_binding_sha256`, while free space and unrelated group observations
are execution/diagnostic facts.

## Execution Guard

The bootstrap executor now fails closed if the current approval binding does
not match the plan-bound binding SHA. This duplicates the operator preflight
inside the writer path so an approved bootstrap cannot proceed after ancestor,
device, ownership, operator, access-basis, path-state, or symlink drift.
Free-space shortage is enforced separately as an execution constraint.

`STORE_METADATA.json` is also prepared for a single final atomic replace. The
ownership ledger is built before the final replace using the temp file identity,
so execution does not need a second persistent metadata overwrite.

## Result

- machine approval: not created
- real bootstrap: not executed
- real directories created: `0`
- `STORE_METADATA.json`: not written
- P2S stage: not executed
- P2S activation: not executed
- baseline pointer: unchanged

The next valid step is to use the R5 stable-binding bootstrap plan/request,
then obtain a new machine approval for that exact plan and binding. The R4 plan
and the 2B0 drift-generated plan are superseded.

## Non-Claims

2B0 did not modify prod, sandbox, owner-dev, the real artifact store, baseline
pointer, endpoints, process state, or environment values. It did not perform
P2S stage, activation, sandbox rollback, delete, chown, chgrp, setuid, setgid,
or live validation.
