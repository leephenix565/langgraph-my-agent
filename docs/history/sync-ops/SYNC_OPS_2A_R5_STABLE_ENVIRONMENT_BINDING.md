# SYNC-OPS-2A-R5 Stable Environment Binding

SYNC-OPS-2A-R5 repairs the artifact-store bootstrap authorization model after
SYNC-OPS-2B0 correctly blocked a stale bootstrap. The 2B0 stop was safe, but
it showed that the old environment SHA included volatile observations such as
exact free bytes and unrelated supplementary groups.

## Contract

Bootstrap environments now use `agent_sync_execution_environment_v2`:

- `approval_binding`: stable security facts bound by machine approval.
- `execution_constraints`: predicates rechecked at execution time.
- `observations`: diagnostic facts that do not by themselves invalidate an
  approval.

The approval binding includes the operation type, exact plan id/hash, root and
parent paths, nearest existing ancestor realpath/device/inode/uid/mode,
operator effective uid, access basis, exact action paths, expected path states,
planned modes, no-symlink expectations, and metadata action identity.

Free space is no longer hashed as an exact authorization fact. Plans carry
`minimum_free_bytes`; execution succeeds only when current free space remains
above that threshold. Falling below the threshold is a constraint failure, not
an environment binding mismatch.

## Permission Proof

The bootstrap planner records `access_basis`:

- `owner`: bind ancestor uid and mode; supplementary groups and ancestor gid
  are diagnostic only.
- `group`: bind the relevant ancestor gid and membership in that group.
- `other`: bind mode and `access_basis=other`; groups are diagnostic.
- `acl`: blocked as `unmodeled_posix_acl` until a canonical ACL digest exists.

This keeps owner-based access stable when unrelated supplementary groups vary,
while retaining fail-closed behavior for uid, mode, device, inode, path-state,
symlink, and access-basis drift.

## Drift Classes

- `authorization_binding_drift`: binding hash mismatch, approval invalid.
- `constraint_failure`: enough stable facts match, but execution predicates
  fail, such as insufficient free space.
- `diagnostic_observation_change`: observations changed but binding and
  constraints remain valid.

## Current Phase Result

The previous R4 bootstrap plan and the 2B0 drift-generated plan are superseded.
R5 generates a new bootstrap plan and an approval request that binds
`environment_binding_sha256`; it does not create a machine approval and does
not execute bootstrap.

## Follow-Up

SYNC-OPS-2B0-R1 later used that exact stable-binding request to bootstrap the
durable artifact store. The next approval boundary is P2S stage/verify only,
not another artifact-store bootstrap.

## Non-Claims

R5 does not create `/sdb/dlut/ops-artifacts`, does not write prod, sandbox,
owner-dev, or artifact-store state, does not create a real approval or lock,
does not run P2S stage or activation, does not call endpoints, and does not
operate processes.
