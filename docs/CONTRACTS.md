# Target Contracts

This document names the target Fixed DAG contracts. R1-A does not implement these contracts in runtime code.

## Contract Boundary

Contracts separate internal DAG execution from the public transcript. Internal payloads can be inspected by workflow tooling, but only mapped public fields may reach the public adapter.

## fixed_dag_plan_v1

Purpose: describe the topological execution plan for a user request.

Expected fields:

- `schema_version`
- `request_id`
- `user_text`
- `stages`
- `required_inputs`
- `missing_input_policy`

## data_bundle_v1

Purpose: carry normalized market, financial, and source data into analysis agents.

Expected fields:

- `schema_version`
- `entities`
- `market_data`
- `financial_data`
- `source_coverage`
- `data_quality_flags`

## entity_relation_bundle_v1

Purpose: describe entities, tickers, industries, relationships, and ambiguous references.

Expected fields:

- `schema_version`
- `entities`
- `relations`
- `ambiguities`
- `resolution_notes`

## conclusion_object_v1

Purpose: carry an agent-level finding with evidence and uncertainty.

Expected fields:

- `schema_version`
- `agent_id`
- `dimension`
- `summary`
- `evidence`
- `confidence`
- `limits`

## dimension_composite_result_v1

Purpose: combine L2 findings into one dimension-level result.

Expected fields:

- `schema_version`
- `dimension`
- `inputs`
- `composite_summary`
- `score`
- `target_range`
- `reasoning_trace`
- `risk_flags`

## decision_result_v1

Purpose: combine dimension composites into an investment or research decision object.

Expected fields:

- `schema_version`
- `decision`
- `confidence`
- `dimension_weights`
- `supporting_points`
- `opposing_points`
- `uncertainties`

## report_result_v1

Purpose: render the final assistant-facing report.

Expected fields:

- `schema_version`
- `title`
- `answer`
- `sections`
- `evidence_notes`
- `limitations`

## workflow_snapshot_v2

Purpose: expose safe workflow inspector state without leaking raw graph messages or provider responses.

Expected fields:

- `schema_version`
- `run_id`
- `stage`
- `steps`
- `dimension_status`
- `final_status`
- `public_turn_id`

## Public Exclusions

Do not expose the following as transcript content:

- raw graph messages
- provider raw responses
- manager assignments
- agent JSON payloads
- internal traces
- secrets or environment values
