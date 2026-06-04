# Contracts

This document names the Phase R1-B Fixed DAG contracts implemented by
`src/react_agent/fixed_dag_contracts.py`.

## Contract Boundary

Contracts separate internal DAG execution from the public transcript. Internal
payloads can be inspected by workflow tooling, but only mapped public fields may
reach the public adapter.

## fixed_dag_plan_v1

Purpose: describe the deterministic reset execution plan for a user request.

Runtime fields:

- `schema`
- `plan_id`
- `user_text`
- `stages`
- `steps`
- `target_agent_ids`
- `dimension_groups`
- `provenance`

The plan has no dispatch strategy field and no legacy layer-mode selector.

## data_bundle_v1

Purpose: carry the financial data service seam into analysis placeholders.

Runtime fields:

- `schema`
- `status`
- `as_of`
- `data_as_of`
- `sources`
- `notes`

## entity_relation_bundle_v1

Purpose: describe the entity and relation resolution seam.

Runtime fields:

- `schema`
- `status`
- `entities`
- `relations`
- `notes`

## conclusion_object_v1

Purpose: carry an agent-level finding with evidence and uncertainty.

Runtime fields:

- `schema`
- `agent_id`
- `stance`
- `confidence`
- `status`
- `evidence`
- `as_of`
- `data_as_of`
- optional `output_routes`

## dimension_composite_result_v1

Purpose: combine L2 findings into one dimension-level result.

Runtime fields:

- `schema`
- `dimension`
- `stance`
- `confidence`
- `status`
- `contributing_agents`
- `evidence_refs`
- risk-only `gate`, `veto`, `penalty`
- macro-only `dimension_weights`, `risk_sensitivity`

## decision_result_v1

Purpose: combine dimension composites into a decision object.

Runtime fields:

- `schema`
- `decision`
- `score`
- `target_price_range`
- `reasoning_trace`
- `status`

## report_result_v1

Purpose: render the final assistant-facing report.

Runtime fields:

- `schema`
- `title`
- `answer`
- `status`
- `sections`
- `limitations`

## workflow_snapshot_v2

Purpose: expose safe workflow inspector state without leaking raw graph messages
or provider responses.

Public fields:

- `schema`
- `planId`
- `stages`
- `dagSteps`
- `dimensionGroups`
- `currentStage`
- `completedSteps`
- `provenance`
- `finalSource`

`finalSource` is currently `reset_skeleton`.

## Public Exclusions

Do not expose the following as transcript content:

- raw graph messages
- provider raw responses
- manager assignments
- agent JSON payloads
- internal traces
- secrets or environment values
