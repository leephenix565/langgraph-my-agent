# SYNC-OPS-3X Sandbox-to-Prod Automation

Date: 2026-06-24

## Scope

SYNC-OPS-3X implements the sandbox-to-prod control plane after the P2S topic
closed. It adds experiment manifests, B/S/P/D diffing, change-unit gated S2P
plans, machine approval contracts, backed-up file transactions, offline
validation boundaries, process/live gate contracts, rollback and crash
recovery, owner handoff records, historical replay, and a real current-server
zero-action rehearsal.

This phase does not approve or execute a non-zero sandbox-to-prod publish.

## Baseline And Experiments

The active external-agent sandbox baseline remains immutable. Future work forks
an experiment workspace from the registered versioned baseline:

```text
B = immutable baseline
S = experiment workspace
P = current prod
D = owner-dev candidate
```

`agent-sync experiment fork` creates a temp or future registered experiment
workspace from the immutable baseline. It rejects active sandbox, versioned
baseline, and prod roots as mutable experiment destinations. Every non-noop
S2P file action must be covered by exactly one change unit.

## S2P Planning

The S2P plan preserves prod-only changes by default. It can plan only explicit
A/B risk change units automatically. C-class changes become manual-review
plans, while D/S and delete actions fail closed. Sanitized sandbox derivatives
are not publishable unless a later reviewed prod-safe refactor change family
explicitly owns them.

The plan binds registry, policy, catalog, active pointer, artifact-store
metadata, current prod transaction digests, the experiment manifest hash, and
the main-system tool version. Target drift after planning returns
`target_snapshot_stale`.

## Transaction Writer

Each service update is a per-service transaction:

```text
precheck -> backup -> temp replacements -> apply -> verify -> offline tests
-> optional process -> optional live gate -> close
```

Replacement files are prepared in the target filesystem and applied with
`os.replace`. Replace actions require target-before hashes and a backup
manifest. On failure, the journal drives rollback of only the files touched by
that transaction. Hardlinks, symlink targets, whole-tree rsync, and implicit
delete are forbidden.

## Process And Live Gates

File apply, process restart, and live health/compute smoke are independently
approved capabilities. Process actions must use registry service-unit metadata
and cannot execute arbitrary shell commands or recover environment from
`/proc/*/environ`. Live gates are limited to loopback `/health` and
`/v1/agent/compute`; `/v1/agent/invoke` remains forbidden.

SYNC-OPS-3X tests these gates with fake controllers/transports only. The real
current-server rehearsal has `process_action_count=0` and `endpoint_call_count=0`.

## Historical Replay

The historical 31-unit backfill ledger is imported with explicit dispositions:
exact byte replay, patch replay, contract-equivalent fixture, historical
evidence only, or unavailable. Missing historical bytes are not fabricated.
The temp replay covers non-zero backup/apply/offline/fake restart/fake
health-compute-adapter/rollback/recovery behavior under `/tmp`.

## Real No-Op Rehearsal

The current real environment rehearsal forks a `/tmp` experiment from active
baseline bytes, builds an S2P plan, and executes only when the plan has zero
actionable file actions, zero deletes, zero process actions, zero live gates,
and zero unresolved blockers. The durable artifact store records the no-op
plan, no-op approval, locks, journal, run result, and before/after prod,
sandbox, and pointer digests.

No production file is modified during the no-op run.

## SYNC-OPS-4X Entry

SYNC-OPS-4X implements the one-command publish-and-rebase cycle and closes the
integration gap between S2P and P2S. The first real non-zero publish still
requires a fresh experiment, explicit change units, a hash-bound cycle approval
bundle, backup/apply/offline validation approval, and separate process/live
permissions if those gates are needed.

## Non-Claims

SYNC-OPS-3X does not modify prod source files, active sandbox, immutable
baselines, baseline pointer, or owner-dev repositories. It does not call real
endpoints, operate real processes, call `/v1/agent/invoke`, read env values, or
complete a real non-zero publish.
