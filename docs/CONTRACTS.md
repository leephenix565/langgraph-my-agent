# Contracts

This document names the Phase R2 Fixed DAG contracts implemented by
`src/react_agent/fixed_dag_contracts.py`.

## Contract Boundary

Contracts separate internal DAG execution from the public transcript. Internal
payloads can be inspected by workflow tooling, but only mapped public fields may
reach the public adapter.

R2 hardens these contracts with deterministic constructors, normalizers, and
validators. These seams do not implement real business algorithms and do not
call providers or external services.

## fixed_dag_plan_v1

Purpose: describe the deterministic reset execution plan for a user request.

Runtime fields:

- `schema`
- `schema_version`
- `plan_id`
- `user_text`
- `as_of`
- `stages`
- `steps`
- `dag_steps`
- `target_agent_ids`
- `target`
- `dimension_groups`
- `provenance`

The plan has no dispatch strategy field and no legacy layer-mode selector.
For R1-B-Delta, `target_agent_ids` contains the 27 formal v4 feedback-aligned
agent ids: L1=3, L2=18, L3=4, L4=2.

Seams:

- `build_default_fixed_dag_plan`
- `normalize_fixed_dag_plan`
- `validate_fixed_dag_plan`

## data_bundle_v1

Purpose: carry the financial data service seam into analysis placeholders.

Runtime fields:

- `schema`
- `schema_version`
- `status`
- `as_of`
- `data_as_of`
- `sources`
- `notes`

Seams: `build_data_bundle`, `validate_data_bundle`.

## entity_relation_bundle_v1

Purpose: describe the entity and relation resolution seam.

Runtime fields:

- `schema`
- `schema_version`
- `status`
- `as_of`
- `data_as_of`
- `entities`
- `relations`
- `notes`

Seams: `build_entity_relation_bundle`, `validate_entity_relation_bundle`.

## conclusion_object_v1

Purpose: carry an agent-level finding with evidence and uncertainty.

Runtime fields:

- `schema`
- `schema_version`
- `agent_id`
- `dimension`
- `stance`
- `confidence`
- `status`
- `evidence`
- `as_of`
- `data_as_of`
- optional generic `event_flags`
- optional `output_routes`
- `provenance`

`output_routes` is a generic contract field. In the current roster,
`sentiment_company_radar` sets it to `["market_composite"]`; it does not route
directly to `risk_composite`.

Seams: `build_pending_conclusion`, `build_l2_conclusions`,
`validate_conclusion_object`.

## dimension_composite_result_v1

Purpose: combine L2 findings into one dimension-level result.

Runtime fields:

- `schema`
- `schema_version`
- `agent_id`
- `dimension`
- `stance`
- `confidence`
- `status`
- `contributing_agents`
- `evidence_refs`
- `as_of`
- `data_as_of`
- value/market `vote_type`
- risk-only `gate`, `veto`, `penalty`, `risk_score`
- macro-only `regime`, `dimension_weights`, `risk_sensitivity`

Seams: `build_value_composite`, `build_market_composite`,
`build_risk_composite`, `build_macro_composite`, `build_dimension_results`,
`validate_dimension_composite_result`.

## decision_result_v1

Purpose: combine dimension composites into a decision object.

Runtime fields:

- `schema`
- `schema_version`
- `decision`
- `score`
- `target_price_range`
- `dimension_views`
- `reasoning_trace`
- `confidence`
- `status`
- `as_of`

Seams: `build_decision_result`, `validate_decision_result`.

## report_result_v1

Purpose: render the final assistant-facing report.

Runtime fields:

- `schema`
- `schema_version`
- `title`
- `answer`
- `status`
- `sections`
- `evidence_cards`
- `limitations`

Seams: `build_report_result`, `validate_report_result`.

## workflow_snapshot_v2

Purpose: expose safe workflow inspector state without leaking raw graph messages
or provider responses.

Public fields:

- `schema`
- `schemaVersion`
- `planId`
- `stages`
- `dagSteps`
- `dimensionGroups`
- `currentStage`
- `completedSteps`
- `provenance`
- `finalSource`

`finalSource` is currently `reset_skeleton`.

Seams: `build_workflow_snapshot_v2`, `validate_workflow_snapshot_v2`.
Graph final emission also uses `build_final_emit_payload`,
`build_emitted_bundle`, and `build_reset_multi_agent_bundle`.

## Public Exclusions

Do not expose the following as transcript content:

- raw graph messages
- provider raw responses
- manager assignments
- agent JSON payloads
- internal traces
- secrets or environment values
