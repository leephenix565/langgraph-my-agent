# AI Coding Handoff For Fixed DAG External Scaffold

You are editing the external-agent scaffold source package. Keep the package
aligned to the fixed DAG reset system.

## Hard Rules

Do not:

- register anything into `AGENT_TOOLS`
- edit `config/agents`
- edit `config/fixed_dag/runtime_bindings.json`
- change the fixed DAG 27-agent roster
- restore `value_financial_analysis`
- restore a 28-agent roster
- route `sentiment_company_radar` into risk
- start a demo stack
- call providers
- call external `/v1/agent/invoke`
- set `live_verified=true`
- set `invoke_enabled_by_default=true`
- output secrets, raw traceback, raw provider response, or chain-of-thought

## What To Implement

Implement only the external service package boundary:

- `GET /health`
- `POST /v1/agent/compute`
- `POST /v1/agent/invoke`
- local deterministic `compute_core`
- structured schemas
- typed errors
- sample request/response files
- local tests

## Current ID Model

Use:

```json
{
  "agent_id": "value_ml_valuation",
  "external_agent_id": "valuation_ml",
  "legacy_agent_id": "a16_ml_valuation"
}
```

`agent_id` is the fixed DAG primary id. `legacy_agent_id` is a migration note
only. Do not reintroduce `main_agent_id` as a request field.

## Contract Target

For an L2 service, `tool_result.schema_version` should be
`agent_conclusion_v1`, which a future main-system adapter can map to
`conclusion_object_v1`.

Required safety checks:

- `confidence` in `[0, 1]`
- `data_as_of <= as_of`
- evidence present for successful conclusions
- event flags are arrays
- typed errors are safe
- aNN primary ids are rejected
- no provider/external HTTP calls in local tests

## Validation Commands

From this package directory:

```powershell
conda run --no-capture-output -n cline_env python -m pytest tests -q
conda run --no-capture-output -n cline_env python -m ruff check .
```

From the main repo:

```powershell
conda run --no-capture-output -n cline_env python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
```

Do not run fusion-gate, provider live smoke, demo stack, or live external
invoke in this phase.
