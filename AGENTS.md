# Codex Workflow

This repository follows an audit-first workflow. User goals, constraints, and DoD are the requirement source. Repository facts must come from current files, tests, logs, and diffs.

## Core Rules

- Audit before implementation.
- Do not guess code facts.
- Do not push unless the user explicitly asks.
- Do not modify `.env`.
- Do not call providers or external `/v1/agent/invoke` during audit or reset cleanup phases.
- Do not start or stop demo stacks unless the user explicitly asks.
- Do not rewrite architecture from a dirty tree.
- Every implementation phase must update docs and changelog in the same commit.

## Reset Branch Rules

The `reset/fixed-dag-v1` branch is a phase-based rewrite branch.

- Make large changes in named phase commits.
- Keep each phase scoped to its DoD.
- Preserve current runtime boundaries until the phase explicitly owns them.
- Treat the pre-reset tag as the preserved history source.
- Do not restore old Agent Catalog v2, route mode, route-prior, RARP, Router-SFT, or external scaffold material as current authority.

## Subagent Policy

Use subagents only when work can be split into clear, mostly read-only tasks. Typical read-only roles:

- repo explorer
- protocol auditor
- test impact analyst
- docs impact analyst

The final repository edits must be integrated by a single writer. Do not let multiple writers modify overlapping files in the same phase.

## Documentation Sync

Implementation changes must update the relevant reset docs:

- runtime or graph topology: `docs/SYSTEM_MAP.md`, `docs/ARCHITECTURE_FIXED_DAG.md`, `docs/CHANGELOG.md`
- public API or transcript boundary: `docs/CONTRACTS.md`, `docs/FRONTEND_V2.md`, `docs/CHANGELOG.md`
- quality gates: `docs/QUALITY.md`, `docs/CHANGELOG.md`
- durable architecture decision: `docs/DECISIONS.md`, `docs/CHANGELOG.md`

## Bidirectional Agent Sync Workflow

- The active sandbox baseline is not a mutable experiment. Fork experiments
  from registered immutable baselines with `agent-sync experiment fork`.
- Every non-noop sandbox-to-prod file action must be covered by one explicit
  change unit. Unregistered workspace changes are blockers.
- Plan generation and machine approval are separate. Chat text is not approval.
- One-command publish-and-rebase may run only from an approved cycle plan and
  approval bundle:
  `python scripts/ops/agent_syncctl.py cycle publish-and-rebase --cycle-plan <plan> --approval-bundle <bundle> --execute`.
- Do not publish a whole sandbox tree, use `rsync --delete`, or perform an
  automatic semantic merge.
- Owner-dev repositories are read-only unless a separate owner workflow grants
  write authority.
- Sanitized derivatives are non-publishable by default; convert them into an
  explicitly reviewed prod-safe refactor before planning a publish.
- Historical baselines are source evidence, not current production authority.
  If a registered prod source tree is missing, generate and approve an explicit
  prod source recovery plan before any full-baseline P2S rebase or non-zero
  cycle.
- A running service whose source tree has been deleted is a source-loss
  incident. Do not plan in-place writes into its cwd, and do not call restoring
  an empty tree rollback. Require launch authority, sibling candidate, shadow
  canary, and explicit irreversible roll-forward approval.
- Manual argv evidence is not launch authority. Source-loss execution must use
  a process manager or the approved sync-ops supervised launcher contract with
  exact executable, argv, cwd, PID reuse checks, bounded logs, and no shell.
- Source-loss cutover approval requires a real pre-cutover shadow canary
  closeout for the exact sibling candidate and exact environment profile. Do
  not combine cutover, P2S stage, P2S activation, experiment materialization,
  and first publish into one broad approval.
- A shadow-canary directory that has run a process is evidence, not a clean
  production cutover candidate. Source-loss cutover approval must bind a fresh
  sibling candidate path, canonical archive path, full-tree descriptors,
  production launch authority, exact action ids, SIGTERM/no-SIGKILL policy,
  and roll-forward failure states.
- A pre-start cutover candidate is clean by construction: project it only from
  approved file actions and implied directories. Do not include pycache,
  pytest cache, runtime DBs, logs, sockets, pid files, unknown entries, or
  validation artifacts. Offline validation must prove the candidate tree is
  unchanged before and after checks.
- Process action, live validation, delete, owner handoff, and P2S activation
  remain independent approval capabilities.
- The durable sync artifact store is
  `/sdb/dlut/ops-artifacts/agent-sync`; closeouts should store manifests,
  hashes, bounded patches, and results, not full workspaces or raw source trees.
- Fail closed on target drift, digest-scope mismatch, owner conflicts, lock
  conflicts, and rollback failures. Use `agent-sync cycle status` and
  `agent-sync cycle recover` for interrupted cycle runs.

## Safety Boundary

Never output secrets, provider raw responses, raw graph messages, manager assignment internals, or agent JSON as a public transcript.
