# Fixed DAG Adapter-Oriented Payload Contract v2.3

This document defines the payload inside `external_agent_response_v0.tool_result`
and how it maps to future fixed DAG adapter contracts.

The external response envelope is not graph state. A main-system adapter must
map and validate it before any fixed DAG runtime can consume it.

## Payload Family

| External schema | Intended fixed DAG target |
| --- | --- |
| `agent_conclusion_v1` | `conclusion_object_v1` |
| `dimension_conclusion_v1` | value/market `dimension_composite_result_v1` |
| `risk_conclusion_v1` | risk fields inside `dimension_composite_result_v1` |
| `macro_conclusion_v1` | macro fields inside `dimension_composite_result_v1` |
| `decision_conclusion_v1` | `decision_result_v1` |
| `eval_record_v1` | evaluation/replay evidence, not graph state |
| `fixed_dag_plan_v1` | route/plan payload |
| `data_bundle_v1` | L1 `data_bundle_v1` |

## L2 Agent Conclusion

External `agent_conclusion_v1` maps to fixed DAG `conclusion_object_v1`.

| External field | Fixed DAG field |
| --- | --- |
| `agent_id` | `agent_id` |
| `dimension` | `dimension` |
| `stance` | `stance` |
| `confidence` | `confidence` |
| `status` | mapped `status` |
| `evidence` | `evidence` |
| `event_flags` | `event_flags` |
| `as_of` | `as_of` |
| `data_as_of` | `data_as_of` |
| `external_agent_id` | `provenance.external_agent_id` |
| `legacy_agent_id` | `provenance.legacy_agent_id` |

## L3 Dimension Payloads

`dimension_conclusion_v1` is only for value and market composites. It must
include members, weights, and dispersion. Weights must be explainable by
members and sum to one.

`risk_conclusion_v1` is a gate payload. It must use `role=gate`, include
`gate`, `risk_score`, `penalty`, `triggered_flags`, and `red_lines`, and must
not include `stance`.

`macro_conclusion_v1` is a regulator payload. It must use `role=regulator`,
include `regime`, `dimension_weights`, `risk_sensitivity`, and `style_bias`,
and must not include `stance`.

## L4 Decision Payload

`decision_conclusion_v1` includes `decision`, `score`, `target_price_range`,
`dimension_views`, `calculation_trace`, `reasoning_trace`, `conflicts`,
evidence, `as_of`, `status`, and `confidence`.

`reasoning_trace` must have at least three stages. `score` must match
`calculation_trace.final_score` or the adapter must reject the payload.

## Evaluation, Plan, And Data Payloads

`eval_record_v1` is for metrics such as routing F1, reasoning F1, replay, and
backtest records. It is readiness/evaluation evidence, not graph state.

`fixed_dag_plan_v1` is for route or planning payloads. It should include task,
targets, selected dimensions, selected agents, route prior, fallback, `as_of`,
and status.

`data_bundle_v1` is for L1 data packets. It must include target, `as_of`,
`data_as_of`, `publish_time`, `snapshot_id`, sources, feature bundle, missing
fields, and status. `snapshot_id` enables replay.

## Status Mapping

Status has three separate layers:

- external service status: the status returned by this scaffold envelope
- adapter decision: whether the main-system adapter can map the payload
- fixed DAG internal status: the validator-facing status after mapping

The current fixed DAG conclusion-family contract status vocabulary is
`pending_implementation`, `partial`, `complete`, and `error`.

| External status | Adapter decision | Fixed DAG conclusion status |
| --- | --- | --- |
| `ok` | accept if required fields validate | `complete` |
| `partial` | accept with warnings and reduced confidence | `partial` |
| `needs_clarification` | map to a bounded partial result with warning unless required fields are missing | `partial` |
| `error` | reject as adapter failure or map to a validator-legal failed conclusion when the adapter needs an explicit failure record | `error` |

External services must not use `pending_implementation` as a success state.

## Dimension Mapping

Canonical dimensions are:

```text
value
market
risk
macro
```

Migration aliases `价值`, `市场面`, `风险`, and `宏观` may be accepted by
`validate_tool_result` during phase 0 compatibility. Adapter outputs and sample
payloads should use English canonical dimensions. A later phase may deprecate
Chinese aliases.

Do not create a fifth sentiment composite. Company sentiment is a market signal
in the current fixed DAG roster.

## Evidence And Event Flags

Evidence items should include:

- `fact`
- `source`
- `as_of`
- `data_as_of`
- optional `publish_time`
- optional `value`
- optional `unit`

Evidence should be short, bounded, source-backed, and safe for adapter review.
Do not include raw provider responses, secrets, private user data, raw
traceback, or chain-of-thought.

`event_flags` describe events or signals. They must not carry hidden routing
instructions.

## Point-In-Time Rule

Every mapped payload must satisfy:

```text
data_as_of <= as_of
publish_time <= as_of
```

If evidence or source snapshots contain `publish_time`, that publish time must
also be no later than `as_of`.

## Implementation Notes

`implementation_notes` is optional. If present, it should describe
implementation type, LLM usage, compute core, and explanation layer. If absent,
the payload should still validate when required business fields are valid.

## R8 Boundary

This package defines the target external handoff contract. R8 is the later
main-system adapter phase that will bridge external responses into active fixed
DAG runtime binding. This package alone does not enable or live-verify any
external service.
