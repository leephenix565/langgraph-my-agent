# SYNC-OPS-4X Publish-And-Rebase Cycle

SYNC-OPS-4X closes the bidirectional Agent sync control plane by adding an
approved one-command publish-and-rebase cycle. The cycle combines an executable
S2P plan with a precomputed P2S rebase plan, while keeping planning, machine
approval, file apply, process action, live validation, and rollback as separate
capabilities.

## Integration Repairs

- `risk_financial_fraud` is a registered empty source-bearing tree for the
  current baseline and experiment mapping. It receives non-empty typed B/S
  digest descriptors with file count `0`.
- `market_fund_manager_behavior` is a shared transaction member owned by
  `market_composite`. It is not independently materialized or applied.
- `agent_sync_digest_descriptor_v1` records algorithm, scope, root role,
  include profile, entry contract, relative path basis, digest, and file count.
  Incompatible descriptors fail closed with `digest_scope_mismatch`.

The P2S digest `ca24a6...` is a source-bearing versioned-stage projection. The
S2P diagnostic digest family such as `5bdef3...` describes S2P
workspace/prod-inventory scope. They are not directly comparable without
compatible digest descriptors.

## Cycle Contract

`agent_sync_publish_and_rebase_cycle_v1` binds the experiment reference,
baseline authority, registry/policy/catalog hashes, S2P plan id/hash, projected
prod after-state, precomputed P2S plan, strict failure policy, recovery policy,
and canonical cycle hash.

`agent_sync_cycle_approval_bundle_v1` binds the cycle hash, S2P hash, P2S hash,
experiment hash, action scopes, and capability flags. A no-op bundle has empty
S2P/P2S action scopes and does not approve backup, apply, process, live, delete,
P2S stage, or activation.

## Strict Execution

```bash
python scripts/ops/agent_syncctl.py cycle publish-and-rebase \
  --cycle-plan cycle-plan.json \
  --approval-bundle approval-bundle.json \
  --execute
```

Strict mode does not proceed to P2S after any S2P transaction failure. If S2P
settles successfully, the actual prod after-state must match the approved
projection before the precomputed P2S plan may run. P2S failure leaves prod
settled and reports rebase pending unless the approved cycle contract says
otherwise.

## Artifact Policy

Cycle artifacts store contracts, manifests, hash summaries, bounded patches,
test summaries, and closeout records. They do not store full experiment
workspaces, raw prod/source trees, backup bytes, endpoint raw responses, venvs,
caches, or sensitive source. Archive entries use POSIX relative paths and reject
backslashes, absolute paths, traversal, normalized duplicates, and symlink
entries.

## Closure

SYNC-OPS-4X runs a real current-server no-op cycle only. The first real non-zero
publish still requires a real experiment manifest, explicit change units, a
non-zero cycle plan, and a separate exact machine approval bundle.

SYNC-OPS-5A later found that `risk_financial_fraud` was not a completed mapping
despite the 4X repair marker: the current prod, active baseline, and immutable
baseline all lacked its source-bearing tree. The 4X no-op evidence remains
valid, but first non-zero execution is blocked until the baseline repair
request is approved and completed.
