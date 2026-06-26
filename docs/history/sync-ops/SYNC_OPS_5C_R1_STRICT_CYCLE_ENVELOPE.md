# SYNC-OPS-5C-R1 Strict Cycle Envelope

SYNC-OPS-5C-R1 repairs the final first non-zero cycle packet without executing
the cycle. Source-loss recovery and the full P2S rebase are already complete.

## Root Cause

The final packet contained `agent_sync_first_nonzero_cycle_plan_v1`. That
object is a bounded summary of the selected experiment, change unit, S2P child
plan, projected prod-after descriptor, and first-cycle P2S child plan. It is
not the formal executable publish-and-rebase cycle contract.

The formal CLI validates cycle plans through `validate_cycle_plan()` in
`src/react_agent/ops/sync_cycle.py`. It requires
`schema_version=agent_sync_publish_and_rebase_cycle_v1`,
`mode=strict_all_or_nothing`, `projected_prod_after_state`, a precomputed
`p2s_plan`, and the standard failure/recovery policy fields. The summary object
lacked those fields, so the CLI correctly rejected it with `not_cycle_plan` and
strict-field blockers.

## Repair

The repair adds a deterministic strict-envelope builder. It accepts only the
already frozen children:

- experiment `first_nonzero_risk_fraud_report_contract_3e3a071`
- change unit `cu_792c2d1b0262`
- S2P child `s2p_first_0abdfb4f91a4`
- S2P action `s2p_e1d56522098d`
- projected prod-after descriptor `f6ed15e1...`
- P2S child `p2s_first_52d75b56543f`
- P2S action `p2s_5d09bb73bb47`

The builder does not recompute the business diff, change action ids, or expand
scope. It wraps the frozen children in the formal
`agent_sync_publish_and_rebase_cycle_v1` envelope and creates an
`agent_sync_cycle_approval_request_v1` request that remains
`awaiting_machine_approval`.

## CLI Boundary

`agent-sync cycle validate` validates the strict plan. `agent-sync cycle
publish-and-rebase` without `--execute` performs a dry-run validation of the
strict plan plus approval request and returns `ready_for_machine_approval`.

This phase does not create a machine approval, write production, write the
sandbox, update the pointer, call endpoints, operate processes, or modify
owner-dev repositories.

## Next Step

The next operator action is a final exact machine approval for the strict cycle
plan hash and the two requested actions. Execution still requires `--execute`
and an approved bundle.
