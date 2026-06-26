# SYNC-OPS-5A-R3X Approved Launch Authority

SYNC-OPS-5A-R3X closes the final pre-execution gap before the first compound
source-loss recovery, P2S rebase, and non-zero publish cycle.

The R2X recovery and P2S plans are superseded because the launch authority was
not yet productized. R3X keeps the irreversible source-loss model, but adds a
formal `agent_sync_launch_authority_v1` contract and a bounded sync-ops
supervised launcher.

## Source Provenance

The `risk_financial_fraud` recovery package contains 67 source files. Each file
is matched to the June 23, 2026 prod-to-sandbox file manifests where
`prod_sha256 == staged_sha256`; the three accepted BG lineage hashes remain a
strong overlapping subset. Historical baseline evidence is recorded as
snapshot provenance, not current prod authority.

## Launch Authority

`manual_exact_argv` is audit evidence only. It is not a valid launch authority.
When no stable systemd or supervisor unit exists, the approved path is a
sync-ops supervised launcher with exact executable, argv, cwd, owner
preconditions, bounded environment overrides, no shell, 0600 logs, PID/start
time/cwd/exe state, PID reuse protection, graceful SIGTERM only, and manual
intervention on timeout.

The launch contract freezes `/usr/bin/python3.14 -u -m app.main` from the
recovered canonical service root. Canary uses loopback `APP_HOST=127.0.0.1`
and `APP_PORT=11013`; production restart uses bounded non-secret overrides
`APP_HOST=0.0.0.0` and `APP_PORT=10013`. The control plane does not read
`.env` values or `/proc/*/environ`.

## Recovery And Rebase

Recovery V3 materializes a sibling candidate, validates a shadow canary,
captures incumbent contract behavior, stops the incumbent only after canary
success, atomically swaps the recovered source root, and rolls forward to the
verified source if post-stop recovery is needed. Restoring the empty source
tree is never rollback.

The full P2S rebase V3 remains a complete 26-Agent baseline materialization
with concrete stage, activation candidate, archive paths, a full physical
manifest, and separate stage and activation approval boundaries.

## First Change Unit

The selected first non-zero change remains
`candidate_market_capital_flow_chip_contract_test`: the single tests-only file
`tests/test_domain_contract_v1.py`, risk class `A_docs_tests_material`,
process=false, live=false, delete=false.

## Non-Claims

R3X does not modify prod, active sandbox, the baseline pointer, owner-dev, or
the live service process. It does not call `/health`, `/compute`, or `/invoke`.
It creates no machine approval and executes no recovery, P2S, or publish cycle.

## R4X Supersession

R4X supersedes the R3X broad compound request. Launch authority remains valid
evidence, but cutover approval now requires a real pre-cutover canary closeout
and a staged approval chain.
