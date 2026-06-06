# Fixed DAG Adapter-Oriented Payload Contract v1

This document defines the payload inside `external_agent_response_v0.tool_result`
and how it maps to fixed DAG contracts.

The external response envelope is not graph state. A main-system adapter must
map and validate it before any fixed DAG runtime can consume it.

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

## Status Mapping

Status has three separate layers:

- external service status: the status returned by this scaffold envelope
- adapter decision: whether the main-system adapter can map the payload
- fixed DAG internal status: the validator-facing status after mapping

The current fixed DAG conclusion-family contract status vocabulary is
`pending_implementation`, `partial`, `complete`, and `error`.
`conclusion_object_v1` enforces that enum directly. Other conclusion-family
contracts use the same intended vocabulary in builders and typed contracts, but
their validators may not enforce status with the same strictness yet. Step
execution status is a different internal enum and is not emitted by external
services.

| External status | Adapter decision | Fixed DAG conclusion status |
| --- | --- | --- |
| `ok` | accept if required fields validate | `complete` |
| `partial` | accept with warnings and reduced confidence | `partial` |
| `needs_clarification` | map to a bounded partial result with warning unless required fields are missing | `partial` |
| `error` | reject as adapter failure or map to a validator-legal failed conclusion when the adapter needs an explicit failure record | `error` |

External services must not use `pending_implementation` as a success state.
`pending_implementation` is reserved for the fixed DAG reset skeleton and
runtime placeholders.

## Dimension Mapping

| External dimension | Fixed DAG dimension |
| --- | --- |
| `value` | `value` |
| `market` | `market` |
| `risk` | `risk` |
| `macro` | `macro` |

Do not create a fifth sentiment composite. Company sentiment is a market signal
in the current fixed DAG roster.

## Evidence

Each evidence item should include:

- `fact`
- `source`
- `as_of`
- `data_as_of`
- optional `value`
- optional `unit`

Evidence should be short, bounded, source-backed, and safe for adapter review.
Do not include raw provider responses, secrets, private user data, raw
traceback, or chain-of-thought.

## Event Flags

`event_flags` describe events or signals. They must not carry hidden routing
instructions.

Example fields:

- `type`
- `severity`
- `direction`
- `as_of`

## Point-In-Time Rule

Every mapped payload must satisfy:

```text
data_as_of <= as_of
```

If the service cannot satisfy this rule, return `partial` or `error` with a
typed warning/error. Do not fabricate timestamps.

## Fixed DAG Validation Targets

The main-system adapter should validate mapped payloads against:

- `conclusion_object_v1`
- `dimension_composite_result_v1`
- `decision_result_v1`
- `report_result_v1`
- `data_bundle_v1`
- `entity_relation_bundle_v1`

This package only demonstrates the L2 `agent_conclusion_v1 ->
conclusion_object_v1` mapping.
