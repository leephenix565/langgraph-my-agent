# SYNC-OPS-2B1 Real P2S Stage Verify

SYNC-OPS-2B1 executed the first real P2S stage/verify transaction through the
agent-sync control plane. It created a new immutable versioned sandbox baseline
stage and verified it, but it did not activate that baseline.

## Authorization

The user authorized only the exact stage-only P2S plan:

- plan id: `p2s_cb655480f481`
- plan SHA:
  `12a5c34e6d8e899735449f173891cec1b3642130484aa23b190c75d1198616dd`
- frozen environment snapshot SHA:
  `2de0b925689ddb361d49d8a40431fb784e88adc0a1e84163ea71bf8f1a9ee1ad`
- stage root:
  `/sdb/dlut/sandbox/prod-baselines/20260624T060045Z/fixed-dag-services`

The machine approval was stage-only. It approved 26 Agent scopes, 26
transaction scopes, and 1582 action scopes. It set stage and verify to true,
and artifact-store initialization, activation, rollback, delete, process
action, live validation, and publish-and-rebase to false.

## Stage Result

The durable run id is `run_fbb3e73cd466` under
`/sdb/dlut/ops-artifacts/agent-sync/runs/run_fbb3e73cd466`.

The stage materialization summary:

- materialization actions: `1582`
- physical writes: `1581`
- shared noop: `1`
- expected projection digest:
  `ca24a6ce521006131eca7d87aa2725783df2331d78f49859add6542f5afd8d8d`
- actual projection digest:
  `ca24a6ce521006131eca7d87aa2725783df2331d78f49859add6542f5afd8d8d`
- duplicate destinations: `0`
- unexpected files: `0`
- source-stage hardlinks: `0`

During the first validation pass, Python compile validation exposed that
`py_compile` had written `__pycache__` files inside the new stage. The writer
helper now directs compile byproducts to a `/tmp` cache, and the validation
byproducts from this run were removed from the new versioned stage. No planned
source file was removed, and the final verify digest still matches the plan.

## Verify Result

Verify passed with:

- secret findings: `0`
- hard compile failures: `0`
- diagnostic compile findings: `1`

The single diagnostic is the previously classified legacy reference:
`risk_crash/part3_panelExp/core/base_funces/skmodels.py`. It remains
diagnostic-only and is not a runtime/startup/test hard gate.

## Active Sandbox Boundary

The active sandbox remained unchanged:

- active path:
  `/sdb/dlut/sandbox/r8-13a/services/prod`
- active tree before:
  `2bc4f825faef39d2ce7d949e656f9d018b4438b25d421f998701e03590f82b36`
- active tree after:
  `2bc4f825faef39d2ce7d949e656f9d018b4438b25d421f998701e03590f82b36`
- pointer SHA before:
  `4f4b3f97e2720a1c6013cacb203199027cb93f1dc8052ac9a30cea2ef43dbd23`
- pointer SHA after:
  `4f4b3f97e2720a1c6013cacb203199027cb93f1dc8052ac9a30cea2ef43dbd23`

No archive path or active candidate path was created.

## Activation Request

After verify, a new activation approval request was generated with status
`awaiting_machine_approval`. It binds the real stage run id, artifact index
SHA, stage digest, stage validation SHA, current active pointer SHA, current
active tree SHA, candidate path, and archive path.

The request is not a machine approval. It does not contain `approval_id` or
`approved_at`, and it was not executed.

## Non-Claims

This phase did not modify prod, active sandbox, owner-dev, or the baseline
pointer. It did not activate, roll back active sandbox state, call endpoints,
operate processes, read environment values, or output secrets.

## Follow-Up Closure

SYNC-OPS-2B2X consumed this stage evidence in the final P2S activation cycle.
The same immutable stage was activated, rolled back to prove exact old
active/pointer restoration, and reactivated through a second independent
machine approval. The final active sandbox baseline is `20260624T060045Z`.
