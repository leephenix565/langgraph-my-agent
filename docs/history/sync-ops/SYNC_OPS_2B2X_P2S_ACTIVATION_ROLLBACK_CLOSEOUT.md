# SYNC-OPS-2B2X P2S Activation, Rollback, Reactivation Closeout

Date: 2026-06-24

## Scope

SYNC-OPS-2B2X closes the production-to-sandbox automation topic with one
machine-approved activation cycle:

- activate the verified immutable stage from SYNC-OPS-2B1;
- verify the new active sandbox baseline;
- perform one controlled rollback and prove exact old active and old pointer
  restoration;
- create a separate post-rollback reactivation request and machine approval;
- reactivate the same immutable stage as the final active sandbox baseline;
- preserve the immutable versioned stage, old active archive, rollback proof,
  and durable artifact-store evidence.

## Frozen Evidence

- Plan id: `p2s_cb655480f481`
- Plan SHA: `12a5c34e6d8e899735449f173891cec1b3642130484aa23b190c75d1198616dd`
- Stage run: `run_fbb3e73cd466`
- Stage root:
  `/sdb/dlut/sandbox/prod-baselines/20260624T060045Z/fixed-dag-services`
- Stage digest:
  `ca24a6ce521006131eca7d87aa2725783df2331d78f49859add6542f5afd8d8d`
- Old active digest:
  `2bc4f825faef39d2ce7d949e656f9d018b4438b25d421f998701e03590f82b36`
- Old pointer SHA:
  `4f4b3f97e2720a1c6013cacb203199027cb93f1dc8052ac9a30cea2ef43dbd23`

The activation cycle run is
`/sdb/dlut/ops-artifacts/agent-sync/runs/run_2b2x_3a3e19c9aff4`.

## Results

The first activation created a candidate from the immutable stage, verified the
candidate digest, archived the old active sandbox, moved the candidate into the
active path, and wrote the frozen pointer candidate. The first active tree
matched the stage digest.

The controlled rollback then moved the new active baseline to the failed-new
baseline proof path, restored the old archive to the active path, and restored
the original pointer bytes. The restored active digest and pointer SHA matched
the frozen old values exactly.

After rollback proof passed, a second approval was created for final
post-rollback reactivation. The final activation rebuilt a fresh candidate from
the immutable stage, archived the restored old active sandbox, moved the
candidate into active, and wrote the same frozen pointer candidate bytes.

Final state:

- active sandbox tree equals the stage digest;
- pointer SHA equals the frozen pointer candidate SHA;
- old active archive exists and equals the old active digest;
- immutable versioned stage remains unchanged;
- failed-new rollback proof remains retained;
- hardlink count is zero;
- secret findings are zero;
- locks were released.

## Non-Claims

This phase did not modify production sources, owner-dev repositories, or main
system production runtime. It did not call endpoints, operate processes, read
environment values, run S2P, delete baselines, publish-and-rebase, or perform
live validation.

## Topic Closure

The `prod_to_sandbox_automation` topic is complete. The next topic is
`sync_ops_3x_sandbox_to_prod_automation`.

SYNC-OPS-3X implements sandbox-to-prod automation as a separate control-plane
capability with experiment manifests, B/S/P/D comparison, per-service backup
and rollback, fake process/live gates, historical replay, and a real no-op
rehearsal. The first non-zero publish remains blocked until a later
machine-approved SYNC-OPS-4X experiment.
