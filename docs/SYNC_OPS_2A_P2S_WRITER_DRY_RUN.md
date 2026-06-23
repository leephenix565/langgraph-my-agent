# SYNC-OPS-2A P2S Writer Dry Run

SYNC-OPS-2A implements the P2S writer contracts after the SYNC-OPS-1R2
coverage repair. It does not execute against the real production or sandbox
trees. Real P2S execution still requires a separate SYNC-OPS-2B machine
approval.

## Scope

Implemented:

- machine approval loading and exact plan/hash validation;
- environment snapshot binding for non-sensitive current facts;
- global coordinator lock plus per-transaction locks;
- durable run artifact helper with atomic writes, manifest hashes, and journal
  events;
- P2S stage, verify, activate, rollback, and recovery primitives;
- validation profiles for runtime, startup, test, placeholder, legacy, archived,
  and excluded Python files;
- temp-root end-to-end writer tests for stage, verify, activate, rollback, lock
  conflict, approval denial, artifact integrity, and crash recovery status.

Not implemented or not executed in this phase:

- real `/sdb/dlut/sandbox` stage or activation;
- real `/sdb/dlut/ops-artifacts/agent-sync` run creation;
- real approval record creation;
- real lock acquisition;
- endpoint smoke;
- process restart;
- owner-dev modification;
- prod or sandbox file writes.

## Old Plan Supersession

The SYNC-OPS-1R2 plan `p2s_acb890722181` with SHA
`c020648d5121d3c4fe72f9c9207eaa9b74c81a7a55064991bc5059b9c1bd4db0`
is superseded by the 2A writer contract. The old request remains an approval
request only and is not machine approval.

Reasons:

- approval now binds to an environment snapshot;
- stage, activate, and rollback permissions are separate;
- global and transaction lock contracts are part of execution;
- run artifacts and recovery journal are part of execution evidence;
- validation profiles are now explicit;
- the tool/schema version changes the canonical plan hash.

## Approval And Environment

An approval record is a file-based JSON artifact with `status=approved`, exact
`plan_id`, exact `plan_sha256`, and exact `environment_snapshot_sha256`.
Chat text is not approval. Missing `--plan`, `--approval`, or `--execute`
returns an error before any writer path runs.

The environment snapshot includes registry, policy, catalog, active pointer,
active baseline tree, per-transaction digests, expected stage state, filesystem
device boundary, tool version, and plan hash. It excludes PID, endpoint
responses, command lines, credentials, and environment values.

## P2S Transaction Model

The writer keeps the immutable versioned stage separate from the active sandbox.
Activation builds an independent active candidate from the versioned stage and
forbids hard links. If activation succeeds, the previous active sandbox is
renamed to an archive path and the candidate is renamed into the active path.

Rollback requires separate approval. It restores the archived active sandbox,
preserves the failed active tree, and rewrites the pointer from the plan.

## Validation Profiles

Python files are classified before stage validation:

- runtime/startup/contract/offline/placeholder Python compile failures are hard
  blockers;
- proven unreachable legacy Python is diagnostic only and remains visible in
  limitations;
- archived experiment Python is diagnostic unless policy promotes it;
- excluded Python is not materialized.

The current risk crash file
`risk_crash/part3_panelExp/core/base_funces/skmodels.py` is classified as an
unreachable legacy reference. Its compile error is diagnostic-only and does not
block the current P2S plan.

## SYNC-OPS-2B Entry

SYNC-OPS-2A-R1 supersedes the 2A current plan/request with a stricter source
selection policy and a full-scale temp rehearsal requirement. SYNC-OPS-2B may
begin only with:

- a fresh current P2S plan from the 2A-R1 tool version;
- matching environment snapshot SHA;
- a real machine approval file with stage/activate/rollback scopes explicitly
  set;
- writable approved artifact-store root;
- clean target drift checks;
- no runtime-required compile blockers.
- `not_scanned copy=0`, unknown blocked count `0`, sensitive copy count `0`,
  and full-scale temp stage/verify/activate/rollback pass.

## Non-Claims

SYNC-OPS-2A does not modify real prod, sandbox, owner-dev, or the real artifact
store. It does not create approval, lock, backup, real stage, activation,
endpoint smoke, process action, or provider call evidence.
