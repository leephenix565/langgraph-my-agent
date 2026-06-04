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

## Safety Boundary

Never output secrets, provider raw responses, raw graph messages, manager assignment internals, or agent JSON as a public transcript.
