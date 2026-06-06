# Fixed DAG External Agent Integration Standard

This document defines the `external-agent-scaffold-v2.3-fixed-dag` service
protocol. It is an adapter-side delivery standard, not active graph
registration.

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

| External status | Adapter decision | Fixed DAG conclusion status |
| --- | --- | --- |
| `ok` | accept if required fields validate | `complete` |
| `partial` | accept with warnings and reduced confidence | `partial` |
| `needs_clarification` | map to partial with warning unless required fields are missing | `partial` |
| `error` | reject or record a validator-legal failure result according to adapter policy | `error` |

Fixed DAG conclusion-family validators allow `pending_implementation`,
`partial`, `complete`, and `error`. External services should never return
`pending_implementation` as their own success status.

## Tool Result Payload Family

`external_agent_response_v0.tool_result` may use one of these v2.3 schemas:

| Schema | Layer / role | Key semantics |
| --- | --- | --- |
| `agent_conclusion_v1` | L2 analysis | `role=direction`, includes `stance`, evidence, event flags. |
| `dimension_conclusion_v1` | L3 value/market composite | `dimension` is `value` or `market`, members and weights sum to one. |
| `risk_conclusion_v1` | L3 risk composite | `role=gate`, includes `gate`, `risk_score`, `penalty`; no `stance`. |
| `macro_conclusion_v1` | L3 macro composite | `role=regulator`, includes `dimension_weights`; no `stance`. |
| `decision_conclusion_v1` | L4 decision synthesis | Requires at least three reasoning stages and recomputable score. |
| `eval_record_v1` | eval/replay | Routing F1, reasoning F1, backtest, replay metrics. |
| `fixed_dag_plan_v1` | route/plan | Task, targets, selected dimensions, selected agents, route prior, fallback. |
| `data_bundle_v1` | L1 data packet | Point-in-time data bundle with `publish_time` and `snapshot_id`. |

The default sample service returns `agent_conclusion_v1`. The wider family is
validated through `schemas.py`, tests, and sample payload files.

## Dimension Values

Contract enums stay English:

| Enum | Meaning |
| --- | --- |
| `value` | value dimension |
| `market` | market dimension |
| `risk` | risk dimension |
| `macro` | macro dimension |

Migration aliases such as `价值`, `市场面`, `风险`, and `宏观` are normalized by
`validate_tool_result`. Samples use English canonical values. A later phase may
remove Chinese alias acceptance.

`sentiment_company_radar` is a market signal only. It must not route directly
to `risk_composite`.

## Semantic Validation

Use `validate_tool_result(payload)` from `schemas.py` for local contract
evidence. It checks:

- `agent_id` is not an old aNN primary id
- `data_as_of <= as_of`
- `publish_time <= as_of`
- evidence timestamps do not exceed the payload `as_of`
- evidence-bearing success payloads include evidence
- confidence is in `[0, 1]`
- `dimension_conclusion_v1` weights are explainable and sum to one
- risk gate placement is correct and has no `stance`
- macro regulator placement is correct and has no `stance`
- macro `dimension_weights` use allowed dimension keys and sum to one
- L4 decision reasoning trace depth is at least three
- L4 `score` matches `calculation_trace.final_score`
- data bundles include replayable `snapshot_id`

## Current Wrapper Compatibility Boundary

This scaffold defines the target fixed DAG handoff contract for new external
services. Existing repo compatibility wrappers may still construct compact
legacy-shaped payloads, including `main_agent_id` in context, until a later R8
adapter implementation replaces or bridges that path.

External developers should implement the fixed DAG scaffold contract shown in
this package. They should not infer the current target handoff contract from
legacy wrapper files and should not add `main_agent_id` to the new request
schema. Main-system maintainers own any adapter bridge between legacy wrapper
compatibility payloads and this fixed DAG scaffold contract.

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
