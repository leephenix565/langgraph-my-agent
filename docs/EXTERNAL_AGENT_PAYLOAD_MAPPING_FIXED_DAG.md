# Fixed DAG External Payload Mapping

This document defines how v2.3.1 external-agent payloads should be mapped into
the current fixed DAG contract family.

External services do not write directly into graph state. They return an
external response. A main-system adapter maps and validates that response before
the fixed DAG executor or later readiness workflow may consume it.

## Mapping Authority

Current fixed DAG authority:

- Catalog: `config/fixed_dag/agent_catalog.json`
- Runtime bindings: `config/fixed_dag/runtime_bindings.json`
- Contracts: `src/react_agent/fixed_dag_contracts.py`
- Executor: `src/react_agent/fixed_dag_executor.py`
- Quality gate: `scripts/quality/run_quality.py`

Legacy `AGENT_TOOLS`, `config/agents/*.json`, and aNN ids may appear as
migration references only. They are not current fixed DAG integration truth.

The R7-G scaffold source package at `E:\muti-agent\external_agent_scaffold` and
its tracked repo mirror under `examples/fixed_dag_external_agent_scaffold/`
contain local example mapping code, v2.3.1 payload samples, semantic validators,
and tests. They are adapter-side samples, not graph state and not runtime
registration truth.

## Identity Mapping

| External or legacy concept | Fixed DAG target | Rule |
| --- | --- | --- |
| old `main_agent_id` or aNN id | `agent_id` | Replace with the fixed DAG `snake_case` id from `config/fixed_dag/agent_catalog.json`. |
| `external_agent_id` | `runtime_bindings.external_agent_id` | Keep as the external service id. It is not the fixed DAG primary id. |
| `legacy_agent_id` | `runtime_bindings.legacy_agent_id` | Keep only as a migration note. |
| endpoint URL | runtime binding metadata or deployment config | Do not expose endpoint URLs in public transcript. |

## Status Mapping

Status has three separate layers:

- external service status: `ok`, `partial`, `needs_clarification`, or `error`
- adapter decision: accept, downgrade, reject, or record a failure result
- fixed DAG conclusion-family status vocabulary: `pending_implementation`,
  `partial`, `complete`, or `error`

| External status | Adapter decision | Fixed DAG conclusion status |
| --- | --- | --- |
| `ok` | accept if required fields validate | `complete` |
| `partial` | accept with warnings and reduced confidence | `partial` |
| `needs_clarification` | map to a bounded partial result with warning unless required fields are missing | `partial` |
| `error` | reject as adapter failure or record a validator-legal failed conclusion when an explicit failure record is needed | `error` |

`pending_implementation` remains a fixed DAG reset skeleton status. External
services should not claim it as their own success state.

## Domain Mapping

| External payload | Fixed DAG contract | Mapping notes |
| --- | --- | --- |
| `external_agent_response_v0` | adapter input | The external response envelope is not graph state. |
| `agent_conclusion_v1` | `conclusion_object_v1` | Map direction outputs with `stance`; map `gate_member` risk outputs as adapter-side risk member evidence. `raw_output` and `quality` are audit metadata, not graph state. |
| `dimension_conclusion_v1` | `dimension_composite_result_v1` | Use for value/market composites. Map `DimensionMember[]` to contributing agents, weights, member confidence, and evidence refs. |
| `risk_conclusion_v1` | `dimension_composite_result_v1` risk fields | Map `gate`, including `manual_review`, `penalty`, `risk_score`, triggered flags, and red lines. Risk must not consume `sentiment_company_radar`. |
| `macro_conclusion_v1` | `dimension_composite_result_v1` macro fields | Map `regime`, directional `dimension_weights` for `value`/`market`, `risk_sensitivity`, and style bias. |
| `decision_conclusion_v1` | `decision_result_v1` | Map decision, score, target price range, dimension views, reasoning trace, calculation trace, confidence, status, and `as_of`; the adapter must preserve the score tolerance evidence. |
| `eval_record_v1` | evaluation/replay evidence | Use for routing F1, reasoning F1, backtest, and replay metrics. It is not graph state. |
| `fixed_dag_plan_v1` | route/plan payload | Map task, targets, selected dimensions, selected agents, route prior, fallback, and `as_of`. |
| `data_bundle_v1` | `data_bundle_v1` | Map target, timestamps, `publish_time`, `snapshot_id`, sources, features, missing fields, and status. |

## Dimension Mapping

| External label or alias | Fixed DAG dimension id |
| --- | --- |
| `value`, `价值` | `value` |
| `market`, `市场面` | `market` |
| `risk`, `风险` | `risk` |
| `macro`, `宏观` | `macro` |

English values are canonical. Chinese aliases are migration compatibility
inputs accepted before validation; sample outputs should use English. Do not
create a fifth composite dimension for sentiment. Company sentiment is a market
signal in the current roster.

## Evidence Mapping

External evidence should be short, source-backed, and timestamped. Recommended
external fields:

- `fact`
- `source`
- `as_of`
- `data_as_of`
- optional `publish_time`
- optional `value`
- optional `unit`

Adapter output may place evidence into:

- `conclusion_object_v1.evidence`
- `dimension_composite_result_v1.evidence_refs`
- `decision_result_v1.dimension_views`
- `report_result_v1.evidence_cards`
- workflow inspector summaries

Evidence must not contain raw provider responses, secrets, private user data,
chain-of-thought, or raw traceback.

## Event Flag Mapping

`event_flags` are allowed as generic event indicators. They should describe
facts or event signals, not hidden routing instructions.

Rules:

- Use event flags for events such as investigations, penalties, abnormal
  trading, or other detected signals.
- Do not put event facts into stance fields.
- Do not let `sentiment_company_radar` enter `risk_composite`.
- Let the main-system adapter decide how event flags affect fixed DAG
  contracts.

## Point-In-Time Mapping

External services should report:

- `as_of`: the analysis time requested by the caller
- `data_as_of`: the newest data time actually used
- `publish_time`: the publication time of data or evidence, when available

The adapter must reject or downgrade payloads where `data_as_of > as_of` or
`publish_time > as_of`.

For `/v1/agent/compute`, the historical scaffold lineage passed point-in-time
input as `as_of_date`. The fixed DAG scaffold uses `as_of` directly. Future
adapters may support legacy `as_of_date` as a compatibility input, but new
fixed DAG samples should prefer `as_of`.

## Semantic Validator Checklist

The scaffold-level `validate_tool_result` checks target handoff payloads before
R8 adapter work:

- old aNN ids are rejected as primary `agent_id`
- `data_as_of <= as_of` after supported date normalization
- `publish_time <= as_of` after supported date normalization
- success payloads with evidence-bearing schemas include evidence
- confidence values are in `[0, 1]`
- `agent_conclusion_v1` separates direction and `gate_member` role semantics
- `dimension_conclusion_v1` has `DimensionMember[]`, member weights sum to one,
  and weighted stance matches top-level stance
- `risk_conclusion_v1` has `role=gate`, supports `manual_review`, and has no
  `stance`
- `macro_conclusion_v1` has `role=regulator`, `dimension_weights` containing
  only `value` and `market`, and no `stance`
- `decision_conclusion_v1` has at least three distinct reasoning stages and a
  displayed score within `0.01` of `calculation_trace.final_score`
- `data_bundle_v1` includes a replayable `snapshot_id`

## Provenance Mapping

Fixed DAG provenance should distinguish service facts from runtime claims:

- `external_agent_id`: the external service id
- `agent_id`: the fixed DAG target id
- `legacy_agent_id`: optional migration note
- `provider_invoked`: whether the service invoked a provider, if known
- `external_invoked`: true only in a live integration context, never in docs-only
  examples
- `live_verified`: read from the readiness record or runtime binding, not from
  a sample payload alone

Do not let the external service self-declare cross-dimension routes or public
workflow authority.

## Adapter Validation Checklist

Before a mapped object is accepted:

- Target `agent_id` exists in the 27-agent catalog.
- The id is not a legacy aNN primary id.
- The id is not `value_financial_analysis`.
- The output contract matches the selected target agent.
- Status is mapped to a legal fixed DAG status.
- `confidence` is numeric and 0..1.
- `data_as_of <= as_of`.
- `publish_time <= as_of` where present.
- Evidence is safe and bounded.
- `sentiment_company_radar` routes only to `market_composite`.
- No endpoint URL, env var value, secret, raw external JSON, raw graph message,
  raw provider response, or chain-of-thought enters the public transcript.
