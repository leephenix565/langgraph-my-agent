# SYNC-OPS-5A-R7X Cutover Tree Digest Parity

SYNC-OPS-5A-R7X supersedes Source-Loss Recovery V6 because the clean
projection digest did not match the physical tree produced by the exact
67-file materialization rehearsal.

R6X correctly removed pycache and runtime noise from the pre-start candidate
projection, but it still used a synthetic projection digest contract that did
not match the inventory contract used after materialization. The source-bearing
descriptor was stable, but the complete physical tree descriptor was not:

- projected clean digest: `04e9da04599ad91422df55c7fc321f012567fd0ec392caeeb62b0c588f2e5e00`;
- actual materialized digest: `f87e62ec18b6e2dbfc304dda47c14608fd1e7eda54d728ca5b70571f8785e203`;
- source-bearing descriptor: `e6f4d26e29074a59245ed809aadea1ebdf74bff5d1c2cea16b45a7a4e647b6e5`.

## Physical Tree Contract

R7X introduces `agent_sync_cutover_physical_tree_descriptor_v2`. The physical
digest covers only normalized POSIX relative path, entry type, regular-file
content SHA, directory/file mode, executable bit, and safe symlink target. It
does not include absolute root, root role, timestamps, uid/gid, generated time,
or policy classification labels.

Policy classification is bound separately by
`classification_manifest_sha256`. A classification-only change is not a
physical tree change, and a physical mode/content change cannot be hidden as a
policy-only update.

## Directory Modes

Directory creation is now explicit machine-approved action scope. The
directory ledger contains the root entry plus the 10 parent directories implied
by the 67 source files. Each directory action binds:

- relative path;
- expected missing state before candidate materialization;
- pre-cutover candidate mode;
- canonical post-cutover mode;
- symlink and hardlink rejection;
- whether an explicit mode transition is required.

The fresh candidate root uses the current canonical root mode. Parent
directories preserve the frozen source package directory modes. If a future
root or parent mode transition is required, it must be a separate requested
action.

## Unified Materializer

Projection, temp rehearsal, and the future 5B writer use one materializer
contract: `source_loss_candidate_materializer_v2`. The same path validator,
directory action executor, file action executor, chmod policy, fsync boundary,
and physical descriptor builder qualify the temp rehearsal and the final
machine approval request.

Temp rehearsal actions are allowed to bind to a repo-external root, but only
through `agent_sync_action_semantics_binding_v1`. The semantics hash excludes
the absolute root and binds operation, content hash, type, mode, executable
bit, relative path, classification policy, and symlink/hardlink policy.

## V7 Gate

Source-Loss Recovery V7 is valid only when:

- the V6 plan is rejected under the R7 validator;
- 11 directory actions and 67 file actions are complete;
- expected physical digest equals actual materialized digest;
- post-offline-validation digest still equals the expected digest;
- action semantics match one-to-one between temp rehearsal and final plan;
- frozen source provenance remains stable;
- no incumbent stop, endpoint call, canonical write, real fresh candidate
  materialization, P2S, pointer write, owner-dev write, env-value access, or
  machine approval occurred.

The next executable step remains a 5B machine approval for the exact V7 cutover
request. P2S stage, activation, experiment materialization, and the first
non-zero cycle remain blocked behind real upstream closeouts.
