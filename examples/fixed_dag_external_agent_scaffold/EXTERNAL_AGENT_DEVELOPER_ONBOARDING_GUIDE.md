# Fixed DAG External Agent Developer Onboarding Guide

This guide is for developers building an external business agent that may later
be reviewed for fixed DAG integration.

The current package is sample-only. Passing these local tests means the service
boundary is coherent. It does not mean the service is registered, live verified,
or enabled by default.

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

## 2. Implement The Required Endpoints

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

## 3. Do Not Force One Implementation Mode

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

## 4. Output A Mappable Tool Result

For L2 analysis agents, return `tool_result.schema_version =
"agent_conclusion_v1"` with:

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
- optional `implementation_notes`

A future main-system adapter maps this to `conclusion_object_v1`.

## 5. Point-In-Time Rule

Every response must keep:

```text
data_as_of <= as_of
```

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

- health sample response
- compute sample request and response
- invoke sample request and response
- error sample response
- local test commands and results
- implementation notes
- timestamp policy
- evidence policy
- known limitations

## 8. Main-System Maintainer Responsibilities

Maintainers, not external developers, own:

- selecting or approving the fixed DAG target id
- writing adapter code
- reviewing readiness evidence
- updating runtime binding metadata in a later phase
- keeping `invoke_enabled_by_default=false` until explicit approval
- keeping `live_verified=false` until controlled live evidence is accepted

Do not ask developers to edit `AGENT_TOOLS`, `config/agents`, active graph
nodes, or `runtime_bindings` as part of this scaffold package.
