# SYNC-OPS-5A-R1X Source Authority And Final Freeze

SYNC-OPS-5A-R1X closes the source-authority gap left after 5A. It does not
write prod, active sandbox, baseline pointers, owner-dev repositories, endpoints,
or processes.

## Old Repair Supersession

The 5A repair plan
`p2s_repair_risk_financial_fraud_20260624T151015Z` is superseded with reason
`superseded_due_source_authority_and_full_baseline_contract_gap`.

It is rejected because it treated a historical baseline as current production
authority, could not make current prod non-empty, used a partial 67-file stage,
contained an unresolved stage placeholder, bundled stage and activation
permissions, lacked executable validation, and had no candidate/archive/pointer,
process recovery, or current-prod-after-state contract.

## Source Authority

`risk_financial_fraud` is classified as
`source_deleted_or_lost_but_service_should_exist`.

The current registered prod root exists but is empty. The current active and
versioned baseline roots are absent. Port `10013` still has a Python process
running from the empty prod root with bounded command shape `python3 -u -m
app.main`, but `/proc` no longer exposes source file mappings or source file
descriptors. Runtime memory is therefore not sufficient authority.

The only complete source authority is the 20260623 historical baseline, which
contains the known BG3 hashes for `app/agent/core.py` and
`tests/test_report_material.py`. Historical baselines are evidence, not direct
current-prod authority, so the next executable step is a prod source recovery
plan with backup, offline tests, process reload approval, live validation
approval, rollback, and crash recovery.

## P2S Rebase

A P2S repair must materialize a complete new baseline:

```text
current active baseline safe files
+ settled recovered risk_financial_fraud source tree
= full versioned stage
```

It may not create a one-Agent partial stage and activate it. Stage/verify and
activation/rollback approval remain split.

## Candidate Requalification

The previous `financial_data_service` candidate is not docs/test material. It
modifies `pg-ops-agent/backend/app/main.py`, including the compute wrapper and
static docs mount. It is at least `B_protocol_wrapper`, requires process reload
and live gate approval, and is superseded by the current main-system adapter and
non-L4 production policy. It is not selected as the final first-cycle candidate
in R1X.

## Next Approval

R1X freezes a recovery-first plan/request. The next phase is a machine approval
for risk-fraud prod source recovery. Only after recovery settles and P2S rebase
is verified should the first real user change cycle be regenerated on the final
state.
