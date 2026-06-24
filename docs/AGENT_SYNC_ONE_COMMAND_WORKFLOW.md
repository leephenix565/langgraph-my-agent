# Agent Sync One-Command Workflow

This runbook is the normal operator path for future sandbox-to-prod publishes.
It assumes the durable artifact store at
`/sdb/dlut/ops-artifacts/agent-sync` is available and that the current active
baseline pointer is valid.

## Daily Flow

1. Fork an experiment from a registered immutable baseline.

```bash
python scripts/ops/agent_syncctl.py experiment fork \
  --baseline-id 20260624T060045Z \
  --workspace-root /sdb/dlut/sandbox/experiments/<experiment_id>/fixed-dag-services
```

2. Register explicit change units in the experiment manifest. Every non-noop
   file action must belong to exactly one change unit.

3. Inspect the B/S/P/D diff.

```bash
python scripts/ops/agent_syncctl.py experiment diff --manifest experiment.json
```

4. Create and validate a publish-and-rebase cycle plan.

```bash
python scripts/ops/agent_syncctl.py cycle plan \
  --experiment experiment.json \
  --output cycle-plan.json
python scripts/ops/agent_syncctl.py cycle validate --cycle-plan cycle-plan.json
```

5. Request machine approval. The approval bundle must bind the exact cycle,
   S2P, P2S, experiment, action scopes, and capability flags.

6. Execute only with the approved bundle.

```bash
python scripts/ops/agent_syncctl.py cycle publish-and-rebase \
  --cycle-plan cycle-plan.json \
  --approval-bundle approval-bundle.json \
  --execute
```

7. Use status/recover if the command is interrupted.

```bash
python scripts/ops/agent_syncctl.py cycle status --run-root <run-root>
python scripts/ops/agent_syncctl.py cycle recover --run-root <run-root>
```

## Boundaries

- Never edit the active sandbox directly.
- Never publish a whole sandbox tree.
- Never use a no-op approval bundle for non-zero actions.
- Process, live, delete, owner handoff, and publish-and-rebase are separate
  approval flags.
- Sanitized derivatives are blocked by default unless converted into an
  explicitly reviewed prod-safe refactor.
- Owner-dev repositories are read-only for this workflow.
- `/v1/agent/invoke` is not part of sync validation.

## Blockers

The cycle fails closed on target drift, digest scope mismatch, unregistered
experiment changes, owner authority conflicts, unsupported delete, process
authority gaps, projection mismatch, lock conflict, and rollback failure.
