# SYNC-OPS-5A-R5X Source-Loss Cutover Contract

SYNC-OPS-5A-R5X freezes the final approval contract for the
`risk_financial_fraud` source-loss cutover. R4X already proved the 67-file
candidate in a real shadow canary, but V4 still was not executable approval
material because it did not bind full target paths, fresh candidate actions,
production launch authority, or roll-forward failure states.

## V4 Supersession

R5X marks Recovery V4, P2S V4, and first-cycle V4 as superseded due to:

- missing `canonical_target_path`, `archive_path`, and
  `fresh_cutover_candidate_path`;
- no exact stop/archive/rename/start/smoke action ids;
- source-only descriptor use where directory rename moves the full tree;
- reuse risk around the already-run canary candidate;
- canary port release proof standing in for production port 10013;
- no explicit roll-forward state for interruption after the incumbent stops;
- no production launch authority hash in the cutover approval request.

## Fresh Candidate

The R4X canary directory is retained as evidence only. It may contain runtime
artifacts produced by py_compile, pytest, service startup, or local storage.
V5 requires a new sibling path:

```text
/sdb/dlut/prod/.agent-sync-risk-fraud-cutover-<v5-plan-id>
```

The fresh candidate is expected to be missing before execution and must be
materialized from the frozen source package provenance. It must not be copied
from the canary directory. The expected source descriptor remains the 67-file
descriptor proved by R4X.

## Full Tree Descriptor

`agent_sync_cutover_tree_descriptor_v1` records the complete directory shape:
relative POSIX path, entry type, mode, executable bit, safe symlink target,
source-bearing digest, and classification counts for source, runtime, data or
model references, unknown entries, and sensitive references. It intentionally
does not include uid/gid, mtimes, secret values, or raw sensitive content.

The canonical archive path is also frozen:

```text
/sdb/dlut/prod/.agent-sync-archive-risk-fraud-<v5-plan-id>
```

The archive preserves the full current canonical directory for evidence and
manual recovery. It is not represented as a restartable old runtime.

## Production Launch Authority

V5 separates production launch authority from the R4X canary launcher.
`agent_sync_production_launch_authority_v1` binds:

- executable `/usr/bin/python3.14`;
- argv `["/usr/bin/python3.14", "-u", "-m", "app.main"]`;
- cwd `/sdb/dlut/prod/财务造假风险智能体`;
- production port `10013`;
- the R4X clean environment profile SHA;
- supervised launcher semantics: no shell, start_new_session, 0077 umask,
  bounded logs/state under the artifact store, PID/start/cwd/exe checks, and
  SIGTERM-only stop.

SIGKILL remains disallowed.

## Roll-Forward State Machine

`agent_sync_source_loss_recovery_plan_v5` binds 67 materialization actions and
22 cutover actions. The ordered cutover scope includes final incumbent health,
compute and adapter capture, SIGTERM, PID stop proof, port-10013 release,
canonical archive rename, fresh candidate rename, recovered production start,
new PID/listener proof, recovered health/compute/adapter, equivalence
comparison, settle closeout, and lock release.

Failure semantics are roll-forward only after the incumbent is stopped. V5 does
not claim that the source-less incumbent can be restarted from an empty tree.
If the recovered process fails after candidate cutover, the plan retries the
same verified recovered source and otherwise requires manual intervention.

## Approval Chain

R5X generates `source_loss_cutover_approval_request_v5` with status
`awaiting_machine_approval`. It binds the V5 plan hash, canary closeout SHA,
source provenance SHA, environment profile SHA, canonical and archive paths,
fresh candidate path, production launch authority SHA, incumbent identity, and
all requested action ids.

Downstream nodes remain blocked:

1. `precutover_canary`: executed and closed in R4X.
2. `source_loss_cutover_v5`: awaiting machine approval.
3. `recovery_settle`: blocked pending real cutover closeout.
4. `p2s_stage_verify_v5`: blocked pending recovery settle.
5. `p2s_activate_rollback_v5`: blocked pending real stage closeout.
6. `experiment_materialization_v5`: blocked pending P2S activation closeout.
7. `first_nonzero_cycle_v5`: blocked pending experiment validation.

## Non-Claims

R5X does not stop the incumbent, signal any process, create the real fresh
candidate, modify the canonical target, start recovered production, call
endpoints, execute P2S, mutate active sandbox, write the pointer, modify
owner-dev, read environment values, create a machine approval, or execute the
first non-zero cycle.
