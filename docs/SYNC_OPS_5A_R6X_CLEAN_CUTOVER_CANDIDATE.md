# SYNC-OPS-5A-R6X Clean Cutover Candidate

SYNC-OPS-5A-R6X closes the final source-loss cutover planning defect before
requesting machine approval for 5B.

R5X correctly required a fresh sibling candidate and a complete cutover state
machine, but its expected fresh-candidate descriptor was built by scanning the
historical source root. That root contained post-test Python bytecode, so the
V5 plan combined 67 file actions with a 124-entry expected tree that included
runtime and unknown entries. R6X supersedes that V5 plan and request.

## Clean Projection

The pre-start cutover candidate is projected only from the approved 67 file
actions and the directories implied by their relative paths:

- 67 regular source files;
- 10 parent directories;
- 1 root entry;
- 78 total projected entries;
- no symlinks, special files, runtime artifacts, unknown entries, sensitive
  entries, or unexpected entries.

Each file action binds content, type, mode, executable bit, destination path,
root containment, no-follow-symlink, and no-hardlink rules. A plan missing this
metadata fails closed with `file_action_metadata_incomplete`.

## Offline Validation

Offline validation must be tree-non-mutating. Python bytecode, pytest cache,
temporary files, logs, sockets, pid files, and runtime databases must not be
created under the candidate tree. Validation uses repo-external cache and temp
paths and proves the candidate full-entry digest before validation equals the
digest after validation.

## Runtime Artifacts

Post-start runtime artifacts are governed by a separate policy. They may be
recorded after a recovered process starts, but they never enter the clean
pre-start candidate descriptor. Unknown post-start artifacts remain blocked
unless a later approval adds explicit authority.

## Archive Portability

R6X portable evidence contains JSON contracts, summaries, hashes, and bounded
manifests only. It does not package raw temp fixtures, source trees, candidate
bytes, canary bytes, backup bytes, pycache, or runtime files. Archive entry
names must be POSIX paths with no backslashes, absolute paths, traversal,
normalized duplicates, symlinks, or raw fixture entries.

## Non-Claims

R6X does not stop the incumbent, create a real fresh candidate, modify the
canonical target, start recovered production, stage or activate P2S, change the
active sandbox, update the pointer, modify owner-dev, call endpoints, read
environment values, or approve execution.
