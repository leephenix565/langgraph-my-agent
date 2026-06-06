# Fixed DAG External Agent Scaffold

This directory is a sample-only external agent scaffold for the fixed DAG reset
branch. It is runnable for local contract tests, but it is not registered into
the active graph and it does not change `config/fixed_dag/runtime_bindings.json`.

The scaffold demonstrates the boundary other developers should implement when
they want a business service to be reviewed for later fixed DAG integration.
It standardizes protocol shape, ids, evidence, confidence, status, and
readiness evidence. It does not force every agent to use an LLM with function
calling.

## Scope

This sample provides:

- `GET /health`
- `POST /v1/agent/compute`
- `POST /v1/agent/invoke`
- `external_agent_health_v0`
- `external_agent_request_v0`
- `external_agent_response_v0`
- typed errors
- one deterministic `compute_core` shared by `/compute` and `/invoke`
- `as_of` and `data_as_of` point-in-time fields
- evidence, `event_flags`, confidence, warnings, and fail-soft behavior
- local tests that do not call providers or external services

This sample does not provide:

- active fixed DAG runtime registration
- live service readiness
- provider calls
- external `/v1/agent/invoke` calls
- production deployment hardening
- investment advice

## ID Boundary

Use three separate ids:

| Field | Meaning | Example |
| --- | --- | --- |
| `agent_id` | Current fixed DAG `snake_case` id. | `value_ml_valuation` |
| `external_agent_id` | External service-owned id. | `valuation_ml` |
| `legacy_agent_id` | Optional migration note only. | `a16_ml_valuation` |

Do not use an old `aNN` id as the primary `agent_id`. This scaffold rejects
requests such as `agent_id="a16_ml_valuation"` to make the boundary explicit.
If a legacy id is useful for migration notes, document it outside the request
primary id.

## Implementation Modes

Developers may implement the internals as:

- `model_compute_agent`
- `llm_structured_agent`
- `data_service_agent`
- `composite_or_decision_agent`
- a rule or statistics service
- a hybrid service

The optional `implementation_notes` object is documentation metadata. It is not
a current hard validator and it does not require an LLM:

```json
{
  "implementation_type": "model_compute_agent",
  "uses_llm": false,
  "llm_role": "",
  "compute_core": "deterministic_sample_v1",
  "explanation_layer": "deterministic_template"
}
```

## Endpoint Semantics

`/health` returns safe readiness metadata. It must not expose secrets,
credentials, raw provider responses, private config, or raw traceback.

`/v1/agent/compute` runs deterministic structured computation. In this sample it
calls only local Python code. It is intended for local contract, point-in-time,
idempotency, and backtest-style checks.

`/v1/agent/invoke` is an explanation shell over the same `compute_core`. In this
sample it remains deterministic and does not call an LLM. A real service may use
an LLM explanation layer later, but the structured `tool_result` should remain
compatible with the fixed DAG mapping.

## Fixed DAG Mapping

The sample `tool_result` uses `agent_conclusion_v1`. A future repo-side adapter
can map it to `conclusion_object_v1`:

| External field | Fixed DAG field |
| --- | --- |
| `tool_result.agent_id` | `agent_id` |
| `tool_result.dimension` | `dimension` |
| `tool_result.stance` | `stance` |
| `tool_result.confidence` | `confidence` |
| `tool_result.evidence` | `evidence` |
| `tool_result.event_flags` | `event_flags` |
| `tool_result.as_of` | `as_of` |
| `tool_result.data_as_of` | `data_as_of` |

Status mapping:

| External status | Fixed DAG status |
| --- | --- |
| `ok` | `complete` |
| `partial` | `partial` |
| `needs_clarification` | `partial` with warning |
| `error` | `error` or adapter-level skip/fail |

Dimension enum values remain English in the contract:

| Enum | Chinese display label |
| --- | --- |
| `value` | 价值维 |
| `market` | 市场面维 |
| `risk` | 风险维 |
| `macro` | 宏观维 |

`sentiment_company_radar` belongs to `market` and must not route directly into
`risk_composite`.

## Local Validation

From the repo root:

```powershell
conda run --no-capture-output -n cline_env python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q
conda run --no-capture-output -n cline_env python -m ruff check examples/fixed_dag_external_agent_scaffold
```

These commands are local-only. They do not call providers, do not call any
external service, and do not enable the sample in the active fixed DAG runtime.
