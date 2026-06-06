# Performance And Backtest Compliance

This scaffold keeps the historical performance and backtest ideas, but aligns
them to fixed DAG external-agent handoff.

## One Core, Two Shells

`compute_core` is the shared business core.

- `/v1/agent/compute` calls `compute_core` and returns structured output.
- `/v1/agent/invoke` calls the same `compute_core` and adds answer/key points.

The sample `compute_core` is deterministic local Python. It does not call LLMs,
providers, external HTTP services, or `.env` secrets.

## Point-In-Time Rule

All services must support a requested `as_of` and report `data_as_of`.

Required invariant:

```text
data_as_of <= as_of
```

This protects backtests from future-data leakage.

## Cache Key Rule

If a service caches results, the cache key must include:

- `agent_id`
- `external_agent_id`
- target/entity
- `as_of`
- calculation-relevant options

Do not let different `as_of` dates share a result.

## Idempotency

If `/health.capabilities` includes deterministic behavior, repeated calls with
the same structured input should return the same structured result. Do not
compare naturally variable metadata such as elapsed time.

## Confidence

`confidence` must be numeric in `[0, 1]`. It should reflect uncertainty and
must not be treated as an old fixed `0.75` authority sample.

The sample lowers confidence when `options.missing_fields` simulates partial
data.

## Graceful Degradation

Partial data should return:

- `status=partial`
- warnings naming missing inputs
- reduced confidence
- available evidence

Avoid unnecessary total failure when a bounded partial result is possible.

## Response Time Targets

- `/v1/agent/compute`: <= 5 seconds
- `/v1/agent/invoke`: <= 30 seconds

These are readiness targets for local and controlled validation. They are not
production deployment claims.

## Readiness Evidence Boundary

Package-level performance and backtest checks are readiness evidence only. They
are not graph invocation, adapter acceptance, live verification, or production
readiness. Adapter work, controlled live tests, `live_verified=true`, and
`invoke_enabled_by_default=true` remain separate R8/R9 gates owned by
main-system maintainers. Those flags must remain false for this scaffold until
a later approved readiness phase changes them.

## Non-Claims

Passing this package's local tests does not prove:

- main-system live readiness
- external candidate enablement
- provider readiness
- production deployment readiness
- business correctness
