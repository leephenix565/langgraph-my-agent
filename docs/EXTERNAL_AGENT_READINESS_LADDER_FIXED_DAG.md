# Fixed DAG External Agent Readiness Ladder

This document defines how an external service moves from developer handoff to
default invocation eligibility in the fixed DAG reset system.

Readiness is deliberately staged. Documentation, samples, and local tests do
not imply live service readiness. `live_verified=true` does not imply
`invoke_enabled=true`.

`deployed_but_deferred` is an inventory status, not a readiness level. It means a
server directory, implementation, or listening process has been observed, but the
service has not completed this ladder and is not invoked by the fixed DAG reset
runtime.

R8-7B adds provider-free pure adapter mapping tests for already-available
payload dictionaries. Passing those tests can support L1 adapter mapping review,
but it does not call or verify `/health`, `/v1/agent/compute`,
`/v1/agent/invoke`, any provider, or any deployed service.

## Level Summary

| Level | Name | DoD | Result |
| --- | --- | --- | --- |
| L0 | Docs and samples exist | Handoff bundle includes target fixed DAG id, external service id, chosen v2.3.1 payload schema, health sample, invoke sample, optional compute sample, domain payload sample, limits, and implementation notes. | Ready for protocol review. |
| L1 | Local mock contract passes | Mocked request/response tests or sample-only scaffold tests prove envelope shape, status handling, semantic payload validation, no secrets, no traceback, and bounded payloads. | Ready for adapter mapping review. |
| L2 | Health passes | `GET /health` returns safe structured readiness metadata for the external service. | Service self-report is inspectable. |
| L3 | Compute passes | `/v1/agent/compute` passes anti-lookahead, idempotency, performance, confidence, and graceful-degradation checks where applicable. | Ready for controlled non-LLM/backtest validation. |
| L4 | Invoke controlled live passes | `/v1/agent/invoke` passes a controlled live test with safe response mapping and fail-soft behavior. | Candidate may be marked live verified after review. |
| L5 | Runtime binding prepared | `runtime_bindings.json` maps the fixed DAG id to the external service id while keeping `invoke_enabled_by_default=false`. | Mapping is prepared but still disabled. |
| L6 | Live verified | Maintainer records `live_verified=true` only after manual/live evidence is reviewed. | Live readiness is recorded. |
| L7 | Invoke enabled | Maintainer sets `invoke_enabled_by_default=true` only after explicit approval and rollback plan. | Default invocation may begin. |

## L0: Docs And Samples Exist

Required:

- fixed DAG `agent_id`
- `external_agent_id`
- health sample response
- invoke sample request and response
- optional compute sample request and response
- chosen v2.3.1 payload schema and domain payload sample
- output mapping notes
- evidence policy
- `as_of` and `data_as_of` policy
- known limitations
- optional `implementation_notes`

Internal implementation mode is not a gate. The service may be ML, rules, data
service, LLM, LLM with tools, or hybrid.

## L1: Local Mock Contract Passes

Required:

- Mocked success path.
- Mocked partial path.
- Mocked error path.
- Typed errors are safe.
- No secrets, raw traceback, raw provider response, or chain-of-thought.
- Adapter mapping can convert the external response to the expected fixed DAG
  contract family.
- For R8-7B, the implemented mapping surface is limited to
  `agent_conclusion_v1 -> conclusion_object_v1` and
  `data_bundle_v1 -> data_bundle_v1`.
- If using the R7-G scaffold package, both the repo-external
  `E:\muti-agent\external_agent_scaffold\tests` suite and the tracked repo
  mirror `examples/fixed_dag_external_agent_scaffold/tests` suite pass.

Mock tests do not prove live service readiness.

The R7-G sample scaffold can satisfy L1 for its own deterministic example
service and v2.3.1 payload samples only. It does not advance any real external
candidate to live readiness.

The R8-7B adapter module also does not advance any real external candidate to
live readiness. It does not change `config/fixed_dag/runtime_bindings.json`, set
`live_verified=true`, set `invoke_enabled_by_default=true`, or enable runtime
invocation.

For v2.3.1 samples, L1 evidence should cover direction versus gate-member L2
roles, `manual_review` risk gates, structured `DimensionMember[]`, normalized
date comparisons, value/market-only macro weights, L4 score tolerance `0.01`,
and distinct reasoning stages.

## L2: Health Passes

Required:

- `GET /health` is reachable in a controlled environment.
- Response includes service id, status, version or capability information, and
  warnings if degraded.
- Response contains no credentials, raw traceback, private data, provider raw
  responses, or chain-of-thought.

Health passing does not imply invoke passing.

## L3: Compute Passes

Required when the service supports point-in-time, backtest, batch, or
latency-sensitive workflows:

- `/v1/agent/compute` does not require LLM credentials.
- `as_of` or `as_of_date` is honored.
- Output timestamps satisfy `data_as_of <= as_of`.
- Repeated deterministic inputs produce stable results if the service claims
  deterministic behavior.
- Confidence is numeric and reflects uncertainty rather than a hard-coded
  constant.
- Partial data returns structured degradation instead of unnecessary total
  failure.
- Performance target is documented.

Compute passing does not imply production invocation should be enabled.

## L4: Invoke Controlled Live Passes

Required:

- `/v1/agent/invoke` is called in a controlled live environment.
- The adapter records request/response mapping evidence.
- Timeout, non-2xx, invalid JSON, missing status, and service mismatch remain
  fail-soft.
- The mapped fixed DAG object validates against the selected contract.
- Public transcript remains user/assistant only.

This level is manual/live readiness work and is not part of default reset
mainline.

## L5: Runtime Binding Prepared

Required:

- `config/fixed_dag/runtime_bindings.json` has the fixed DAG `agent_id`.
- `external_agent_id` is recorded for the selected service.
- `legacy_agent_id` is a migration note only.
- `invoke_enabled_by_default=false`.
- `live_verified=false` unless L4 evidence has already been accepted.

Prepared mapping does not call the service.

## Deployed But Deferred

R8-6B may record `deployed_but_deferred` evidence in documentation when a server
agent directory or process exists but the service is not yet active runtime
authority. This state can exist before or alongside L0-L5 evidence, but it does
not replace any ladder level.

Required wording:

- Directory presence does not mean health verified.
- Listening process presence does not mean health verified.
- Health verified does not mean compute/invoke verified.
- Compute/invoke verified does not mean `live_verified=true`.
- `live_verified=true` does not mean `invoke_enabled_by_default=true`.
- The fixed DAG runtime does not call deployed-but-deferred services by default.
- Internal LLM placeholders are not external adapter readiness or live service
  proof.

## L6: Live Verified

Set `live_verified=true` only after:

- L4 controlled live evidence exists.
- The maintainer reviewed the evidence.
- The service identity matches the binding.
- Known limitations are documented.
- No public transcript leakage is observed.

`live_verified=true` records readiness evidence. It does not enable default
invocation by itself.

## L7: Invoke Enabled

Set `invoke_enabled_by_default=true` only after:

- L6 is complete.
- The user or owner explicitly approves enabling.
- There is a rollback plan.
- The adapter fail-soft tests pass.
- The runtime binding is reviewed.
- The quality boundary is updated if needed.

No external candidate may jump directly from samples to enabled invocation.

## Non-Claims

The readiness ladder does not claim:

- provider readiness
- production deployment readiness
- business correctness for all market conditions
- restored fusion-gate acceptance
- demo stack acceptance
- public Web end-to-end live proof
- deployed-but-deferred inventory implies live verification
- internal LLM placeholder output is a real external business-agent result
- R8-7B adapter mapping tests imply health, compute, invoke, live verification,
  runtime binding enablement, or production deployment

Default reset mainline remains no-provider and no-external-invoke.
