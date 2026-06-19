# L4 Runtime Review Evidence R8-13O

This document is the local evidence package that supported deciding whether a
separate external-L4 runtime binding phase could be opened. R8-13O itself was
not a runtime binding change.

## Post-R8-13Q Status

After explicit operator approval, R8-13Q implemented the separate runtime phase
that this document prepared:

- `decision_synthesizer` now uses `runtime_kind=external_compute_default` and
  production-source `/v1/agent/compute` port `10025`.
- `report_generator` now uses `runtime_kind=external_compute_default` and
  production-source `/v1/agent/compute` port `10026`.
- `invoke_enabled_by_default` remains false for both L4 bindings.
- No `/v1/agent/invoke` path is enabled.
- `disable_external_compute_default` /
  `DISABLE_EXTERNAL_COMPUTE_DEFAULT=1` is the deterministic rollback/test
  control.

The remaining R8-13O sections below are retained as historical gate evidence
for why the R8-13Q runtime phase was allowed to proceed.

## Scope

Target L4 ids:

- `decision_synthesizer`
- `report_generator`

Candidate external services:

- production-source `decision_synthesizer` service on port `10025`
- production-source `report_generator` service on port `10026`

R8-13O graph default at evidence-package time:

- `decision_synthesizer` remains the deterministic internal L4 decision seam.
- `report_generator` remains the deterministic internal L4 report seam.
- `config/fixed_dag/runtime_bindings.json` remains unchanged.

## Evidence Package

The main-system local package builder is:

- `build_l4_runtime_review_candidate_package`

R8-13O candidate status at evidence-package time:

- `provider_compute_pass`: pass
- `transcript_safety_pass`: pass
- `rollback_plan_ready`: pass
- `operator_approval`: pending

At R8-13O time, operator approval was pending, so the candidate package remained
`blocked_pending_evidence` and the embedded dry run kept
`default_runtime_enabled=false`. R8-13Q later recorded operator approval for the
L4 runtime goal and completed the separate runtime binding phase.

## Evidence References

Provider compute pass:

- Reference:
  `docs/CONTROLLED_READINESS_SMOKE_LOG.md#r8-13j-l4-provider-backed-controlled-compute-smoke`
- Meaning: production-source L4 provider-backed controlled compute was recorded
  for both L4 ids, with no `/v1/agent/invoke`, no runtime binding change, no
  live flag change, and no stored provider raw response.

Transcript safety pass:

- Reference:
  `tests/unit_tests/test_fixed_dag_external_adapter.py::l4_provider_backed_safety_regression`
- Meaning: adapter regression tests reject unsafe provider-backed L4 public
  payloads before transcript emission.

Rollback plan ready:

- Reference: this document, `#rollback-plan`
- Meaning: maintainers can revert an external-L4 runtime binding attempt by
  restoring deterministic internal L4 seams and disabling external defaults.

Operator approval at R8-13O time:

- Reference: `pending-user-approval-for-runtime-binding-phase`
- Meaning: no explicit approval has been granted yet to edit
  `config/fixed_dag/runtime_bindings.json`.

## Rollback Plan

If a later approved runtime binding phase edits L4 bindings and must be rolled
back, restore these properties for both L4 ids:

- `decision_synthesizer.runtime_kind=deterministic_decision`
- `report_generator.runtime_kind=deterministic_report`
- `implementation_status=deterministic_skeleton`
- `external_agent_id=""`
- `env_var=""`
- `default_url=""`

External candidate defaults must not remain enabled after rollback:

- no external L4 default URL
- no external L4 env var
- no external L4 live/default flag
- no `/v1/agent/invoke` dependency

Validation after rollback:

- run runtime registry tests
- run L4 adapter transcript safety tests
- verify `config/fixed_dag/runtime_bindings.json` contains no external L4 URL
- verify default graph execution can still produce deterministic L4 decision
  and report outputs

## Non-Claims

R8-13O does not:

- call `/health`
- call `/v1/agent/compute`
- call `/v1/agent/invoke`
- modify `.env`
- edit `config/fixed_dag/runtime_bindings.json`
- set `live_verified=true`
- set `invoke_enabled_by_default=true`
- make external L4 services default graph dependencies

## Next Gate

The next gate is explicit operator approval to open a runtime binding phase.
Even after approval, the runtime binding edit must be implemented in a separate
phase with tests and documentation.

## R8-13P Preflight Note

The current runtime binding schema does not yet support an enabled external L4
`/v1/agent/compute` default path. Existing external HTTP candidates are
disabled by contract, and the deterministic L4 rows do not carry external
compute endpoint fields.

After operator approval, the next implementation phase must add:

- an explicit compute-default runtime kind or equivalent schema field;
- compute endpoint binding fields for L4 services;
- executor support for using external L4 compute as the default path;
- rollback tests proving deterministic L4 can be restored.

R8-13Q has now landed that phase for the two L4 services only. The historical
R8-13P preflight was correct at the time; current runtime bindings now contain
the explicit compute-default kind, endpoint fields, executor support, and
rollback tests described above.
