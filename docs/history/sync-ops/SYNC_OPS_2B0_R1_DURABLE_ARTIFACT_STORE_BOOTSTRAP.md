# SYNC-OPS-2B0-R1 Durable Artifact Store Bootstrap

SYNC-OPS-2B0-R1 executed the first real durable artifact-store bootstrap for
`/sdb/dlut/ops-artifacts/agent-sync` under the stable-binding contract from
SYNC-OPS-2A-R5.

## Authorization

The user authorized only the exact bootstrap plan:

- plan id: `bootstrap_2d2981b9ea49`
- plan SHA:
  `ef5d6defdb4e930a270fe3220e9f12b646c04fda9312b7b480f68014d47e9d24`
- environment binding SHA:
  `89520c589f4d6d958ddcb9209bfa8d400e4aad24da416cff235ab030fa5f5929`

The machine approval was created under `/tmp` only. It approved the ten exact
`mkdir_exact` actions and one `STORE_METADATA.json` write. It did not approve
P2S stage, activation, sandbox rollback, delete, chown/chgrp, setuid/setgid,
endpoint calls, process actions, or live validation.

## Hash Contract

The bootstrap plan uses a detached two-hash contract:

- plan SHA excludes only `canonical_sha256`,
  `environment_snapshot_sha256`, `environment_binding_sha256`, and
  `environment_observation_reference`;
- environment approval binding includes the same plan SHA;
- machine approval binds both the plan SHA and the stable environment binding
  SHA;
- action mutations change the plan SHA;
- critical environment mutations change the binding SHA;
- diagnostic observation changes do not change the binding SHA.

## Created Paths

The run created exactly these persistent paths:

- `/sdb/dlut/ops-artifacts` mode `0750`
- `/sdb/dlut/ops-artifacts/agent-sync` mode `0700`
- `/sdb/dlut/ops-artifacts/agent-sync/plans` mode `0700`
- `/sdb/dlut/ops-artifacts/agent-sync/approvals` mode `0700`
- `/sdb/dlut/ops-artifacts/agent-sync/runs` mode `0700`
- `/sdb/dlut/ops-artifacts/agent-sync/locks` mode `0700`
- `/sdb/dlut/ops-artifacts/agent-sync/baselines` mode `0700`
- `/sdb/dlut/ops-artifacts/agent-sync/experiments` mode `0700`
- `/sdb/dlut/ops-artifacts/agent-sync/backups` mode `0700`
- `/sdb/dlut/ops-artifacts/agent-sync/indexes` mode `0700`
- `/sdb/dlut/ops-artifacts/agent-sync/STORE_METADATA.json` mode `0600`

No chown, chgrp, setuid, or setgid action was performed.

## Metadata And Verify

`STORE_METADATA.json` records the bootstrap plan id/hash, environment binding
SHA, approval id, run id, directory layout version, and ownership ledger.
Verification passed with:

- directory actions: `10/10`
- unexpected paths: `0`
- secret findings: `0`
- ownership ledger entries: `11`

Rollback was not attempted because bootstrap verified successfully.

## P2S Replan

After metadata verification, a new P2S plan was generated read-only. The plan
is stage-ready and no longer requests artifact-store initialization. The new
stage approval request remains `awaiting_machine_approval` and requests only
stage and verify; activation and rollback remain false.

SYNC-OPS-2B1 consumed that stage-only boundary. It created and verified the
versioned stage
`/sdb/dlut/sandbox/prod-baselines/20260624T060045Z/fixed-dag-services` under
durable run `run_fbb3e73cd466`. The active sandbox and baseline pointer
remained unchanged, and activation still requires a separate machine approval.

## Non-Claims

This phase did not modify prod, sandbox, owner-dev, the baseline pointer, or
any external service process. It did not execute P2S stage, activation,
sandbox rollback, endpoint smoke, provider/database calls, live validation, or
environment-value reads.
