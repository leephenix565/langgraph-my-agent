# Fixed DAG External Agent Integration Standard

This document defines the fixed DAG external-agent service protocol. It is an
adapter-side delivery standard, not active graph registration.

## Endpoints

```text
GET  /health
POST /v1/agent/compute
POST /v1/agent/invoke
```

All endpoints must be safe to call in local contract tests. Live readiness is a
separate later gate.

## Request Envelope

Use `external_agent_request_v0`:

```json
{
  "schema_version": "external_agent_request_v0",
  "request_id": "stable-or-uuid",
  "agent_id": "value_ml_valuation",
  "external_agent_id": "valuation_ml",
  "legacy_agent_id": "a16_ml_valuation",
  "target": "600519.SH",
  "question": "Assess the target.",
  "as_of": "2026-06-05",
  "language": "zh-CN",
  "context": {
    "dimension": "value",
    "task": "valuation"
  },
  "options": {
    "timeout_seconds": 30
  }
}
```

`agent_id` is the fixed DAG primary id. `external_agent_id` is the service id.
`legacy_agent_id` is a migration note only.

## Response Envelope

Use `external_agent_response_v0`:

- `request_id`
- `agent_id`
- `external_agent_id`
- `legacy_agent_id`
- `status`
- `answer`
- `key_points`
- `tool_result`
- `confidence`
- `warnings`
- `errors`

Allowed external statuses:

- `ok`
- `partial`
- `needs_clarification`
- `error`

Mapping to fixed DAG:

| External status | Fixed DAG status |
| --- | --- |
| `ok` | `complete` |
| `partial` | `partial` |
| `needs_clarification` | `partial` or adapter error |
| `error` | `error` |

## Tool Result

For L2 agents, the sample uses `agent_conclusion_v1`. It maps to fixed DAG
`conclusion_object_v1`.

Required fields:

- `schema_version`
- `agent_id`
- `external_agent_id`
- `dimension`
- `target`
- `stance`
- `confidence`
- `label`
- `evidence`
- `event_flags`
- `as_of`
- `data_as_of`
- `status`

## Dimension Values

Contract enums stay English:

| Enum | Chinese display |
| --- | --- |
| `value` | 价值维 |
| `market` | 市场面维 |
| `risk` | 风险维 |
| `macro` | 宏观维 |

`sentiment_company_radar` is a market signal only. It must not route directly
to `risk_composite`.

## Error Standard

Use typed errors:

- `error_code`
- `error_message`
- `stage`
- `recoverable`
- `retryable`
- `user_action_required`
- `suggested_user_action`

Typed errors must not include secrets, raw traceback, provider raw responses,
or chain-of-thought.

## Performance Targets

- `/v1/agent/compute`: target <= 5 seconds
- `/v1/agent/invoke`: target <= 30 seconds

These are readiness targets, not production service-level guarantees.

## Non-Claims

Wrapper registration is not live verification. Sample tests are not live
service readiness. Runtime bindings remain disabled until a later approved
readiness phase.
