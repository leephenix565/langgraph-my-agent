# SYNC-OPS-5A-R4X Real Shadow Canary And Approval Chain

SYNC-OPS-5A-R4X is the final qualification step before the irreversible
`risk_financial_fraud` source-loss cutover.

R4X supersedes the R3X Recovery V3, P2S V3, first-cycle V3, and compound V3
plans because they did not bind a real canary result, did not prove
environment parity, and allowed a broad downstream approval shape.

## Environment Profile

R4X introduces `agent_sync_runtime_variable_matrix_v1` and
`agent_sync_service_environment_profile_v1`.

The risk-fraud package parses environment variables at import/startup time.
The control plane classifies startup variables, optional path-backed
variables, default-backed variables, and optional secret-backed variables
without reading `.env` values or `/proc/*/environ`.

The canary and future recovered production launch from the same clean
allowlist profile. The only permitted differences are `APP_HOST` and
`APP_PORT`. Candidate runtime artifacts, such as an initialized SQLite
database, are explicitly excluded from the source descriptor and from future
P2S baseline materialization.

## Real Canary Contract

R4X adds `agent_sync_incumbent_canary_equivalence_v1` and a concrete
`agent_sync_source_loss_precutover_canary_plan_v1`.

The canary plan materializes the exact 67-file recovered source package into a
sibling candidate, runs offline validation, captures the incumbent on port
10013, starts a supervised canary on loopback port 11013, performs bounded
`/health`, `/v1/agent/compute`, and adapter checks, and then stops only the
canary.

Acceptance compares identity, schema, adapter mapping, status severity, and
degradation categories. Raw response body equality is diagnostic only and raw
bodies are not persisted.

## Approval Chain

R4X replaces the broad compound request with
`agent_sync_conditional_approval_chain_v1`.

The chain is:

1. `precutover_canary`: executed and closed in R4X.
2. `source_loss_cutover`: awaiting machine approval.
3. `p2s_stage_verify`: blocked pending recovery settle.
4. `p2s_activate_rollback`: blocked pending real stage closeout.
5. `experiment_materialization`: blocked pending P2S activation closeout.
6. `first_nonzero_publish_and_rebase`: blocked pending experiment validation.

No downstream approval can bind a projected artifact where a real closeout SHA
is required.

## Non-Claims

R4X does not stop the incumbent, rename the canonical source root, start a new
production process, stage or activate P2S, modify the active sandbox, write the
baseline pointer, execute the first non-zero cycle, modify owner-dev, call
`/v1/agent/invoke`, read environment values, or output secrets.
