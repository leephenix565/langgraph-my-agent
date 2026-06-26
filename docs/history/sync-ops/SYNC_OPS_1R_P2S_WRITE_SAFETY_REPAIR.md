# SYNC-OPS-1R P2S Write-Safety Repair

SYNC-OPS-1R hardens the read-only sync planner before any future P2S write
automation exists. It remains a planning and validation phase only.

## Scope

The phase repairs P2S plan semantics discovered by the first real current
P2S plan rehearsal:

- backup/runtime-noise files must not become source-bearing actions;
- ordinary materialization actions must carry non-empty source hashes;
- sanitized sandbox derivatives must not be modeled as raw production replace
  actions;
- sandbox-local derivative metadata must not be treated as production source;
- each Agent must carry an explicit disposition;
- P2S file materialization must target a new versioned stage, never the active
  sandbox path;
- activation is a future pointer switch with target-drift preconditions, not a
  file action list.

## P2S Plan Shape

P2S plans now separate three concepts:

1. `observed_diff`: explanatory current prod versus active/versioned sandbox
   baseline observations.
2. `stage_materialization`: future creation of a new versioned baseline using
   `copy_from_prod`, `preserve_sanitized_derivative`,
   `preserve_sandbox_metadata`, `snapshot_semantic_placeholder`, or explicit
   blocked/manual actions.
3. `activation`: future atomic switch preconditions, pointer candidate,
   post-switch verification, and rollback skeleton.

The active sandbox remains immutable input. It is not a file-action target.

## Sanitized Derivatives

Sensitive production source is never copied as an ordinary P2S source action.
For sandbox-only derivatives, the planner records a redacted structural
fingerprint of the production source and preserves the existing derivative only
when the baseline derivative file is present. The fingerprint stores algorithm,
safe line ranges, finding count, and redacted source hash only; it does not
store raw literals, raw snippets, secret hashes, or environment values.

`SANDBOX_SECRET_REQUIREMENTS.md` is baseline-local metadata. It is preserved as
metadata, not copied from production.

## Validation

The P2S validator now rejects:

- missing `stage_materialization` or `activation`;
- stage roots equal to active sandbox or current versioned baseline;
- empty active pointer or active baseline tree digests;
- empty per-Agent target-before digests;
- direct active-sandbox targets;
- legacy `add`/`replace` P2S actions;
- `copy_from_prod` without source hash, mode, or file type;
- backup/runtime-noise copy actions;
- sensitive source copy actions;
- sanitized derivative actions carrying raw source hashes;
- missing dispositions and duplicate stage destinations.

The legacy SYNC-OPS-1 current P2S plan is therefore intentionally invalid under
SYNC-OPS-1R.

SYNC-OPS-1R2 supersedes the SYNC-OPS-1R current approval request because the
1R plan still under-covered nested source packages and support roots. Any
future approval request must be generated from a plan with recursive coverage,
baseline parity, current prod coverage, and temp reconstruction validation.

## Approval Request

The planner may emit a `p2s_approval_request.json` that names a plan hash and
requested future permissions. It is not a machine approval record. Future write
commands must still require a separate approval artifact bound to the exact
plan SHA256.

SYNC-OPS-2A later implements that approval loader and temp-root writer
contract. Any SYNC-OPS-1R approval request remains superseded because it
predates both recursive coverage and environment snapshot binding.

## Non-Claims

SYNC-OPS-1R does not stage, activate, rollback, back up, lock, approve, copy,
replace, delete, smoke, call endpoints, operate processes, or write production,
sandbox, owner-dev, or artifact-store paths.
