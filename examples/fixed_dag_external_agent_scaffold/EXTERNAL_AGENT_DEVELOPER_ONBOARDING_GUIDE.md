# Fixed DAG External Agent Developer Onboarding Guide

This guide is for developers building an external business agent that may later
be reviewed for fixed DAG integration.

Package version: `external-agent-scaffold-v2.3-fixed-dag`.

Passing local tests means the service boundary is coherent. It does not mean
the service is registered, live verified, enabled by default, or accepted by a
main-system adapter.

## 1. Choose The Fixed DAG Agent

Read the main-system catalog:

```text
config/fixed_dag/agent_catalog.json
```

Pick the `snake_case` `agent_id` whose layer, dimension, input contract, output
contract, upstream, and downstream match your service.

Do not use:

- old aNN ids as primary ids
- `main_agent_id`
- `AGENT_TOOLS`
- `config/agents`
- old Agent Catalog v2 counts
- old 25-agent, 28-agent, or `L2=19` catalog counts
- `value_financial_analysis`

The sample target is:

```json
{
  "agent_id": "value_ml_valuation",
  "external_agent_id": "valuation_ml",
  "legacy_agent_id": "a16_ml_valuation"
}
```

`legacy_agent_id` is only a migration note.

## 2. Select The Payload Shape

Choose the payload matching your role:

- L2 analysis: `agent_conclusion_v1`
- L3 value or market composite: `dimension_conclusion_v1`
- L3 risk composite: `risk_conclusion_v1`
- L3 macro composite: `macro_conclusion_v1`
- L4 decision synthesis: `decision_conclusion_v1`
- evaluation or replay: `eval_record_v1`
- routing or planning: `fixed_dag_plan_v1`
- L1 data packet: `data_bundle_v1`

Do not force a risk gate or macro regulator into a directional stance payload.
Risk uses `role=gate`; macro uses `role=regulator`.

## 3. Implement The Required Endpoints

Required endpoints:

```text
GET  /health
POST /v1/agent/compute
POST /v1/agent/invoke
```

`/health` returns safe service metadata.

`/compute` receives structured inputs, calls deterministic or model compute,
and returns structured output. It should not require LLM credentials.

`/invoke` may parse or explain a natural-language request, but it should call
the same `compute_core` and keep the structured `tool_result` stable.

## 4. Do Not Force One Implementation Mode

You may implement the internals as:

- ML model plus optional LLM explainer
- rules or statistics
- data service
- NLP or LLM structured agent
- deterministic compute
- LLM plus function call
- hybrid

Use optional `implementation_notes` to describe the internals. The fixed DAG
gate standardizes protocol and readiness evidence, not your internal approach.
Missing `implementation_notes` should not fail an otherwise valid payload.

## 5. Point-In-Time And Evidence Rules

Every response must keep:

```text
data_as_of <= as_of
publish_time <= as_of
```

Evidence-bearing successful payloads must include bounded evidence with
`fact`, `source`, and `as_of` or `data_as_of`. Do not fabricate evidence.

If data is missing, return `partial` with warnings and reduced confidence
instead of fabricating a complete result.

## 6. Safety Rule

Do not return:

- real secrets
- raw traceback
- raw provider responses
- raw external JSON that includes private details
- chain-of-thought
- endpoint credentials
- private user data

Use typed errors from `errors.py`.

## 7. Local Handoff Evidence

Before submitting a service, provide:

- selected fixed DAG `agent_id`
- service-owned `external_agent_id`
- optional migration-only `legacy_agent_id`
- chosen payload schema version
- `implementation_notes` if available
- health sample response
- compute sample request and response
- invoke sample request and response
- error sample response
- domain payload sample
- local test command output
- timestamp policy for `as_of`, `data_as_of`, and `publish_time`
- evidence policy and source boundaries
- confidence policy, including when confidence is reduced
- known limitations and degraded/partial behavior
- performance note for `/v1/agent/compute` and `/v1/agent/invoke`
- dependency list, including runtime, model, data, and package dependencies
- explicit no-secrets confirmation

## 8. Main-System Maintainer Responsibilities

Maintainers, not external developers, own:

- selecting or approving the fixed DAG target id
- writing R8 adapter code
- reviewing readiness evidence
- updating runtime binding metadata in a later phase
- keeping `invoke_enabled_by_default=false` until explicit approval
- keeping `live_verified=false` until controlled live evidence is accepted

Do not ask developers to edit `AGENT_TOOLS`, `config/agents`, active graph
nodes, or `runtime_bindings` as part of this scaffold package.
