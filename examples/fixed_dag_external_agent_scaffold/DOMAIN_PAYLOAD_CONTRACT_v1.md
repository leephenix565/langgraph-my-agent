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

| External status | Fixed DAG status |
| --- | --- |
| `ok` | `complete` |
| `partial` | `partial` |
| `needs_clarification` | `partial` or adapter error |
| `error` | `error` |

External services must not use `pending_implementation` as a success state.

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
