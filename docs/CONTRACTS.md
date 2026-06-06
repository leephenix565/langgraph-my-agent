# Contracts

This document names the Phase R3 Fixed DAG contracts implemented by
`src/react_agent/fixed_dag_contracts.py` and
`src/react_agent/fixed_dag_executor.py`.

Phase R4-A adds the fixed DAG agent catalog contract implemented by
`src/react_agent/fixed_dag_catalog.py` and sourced from
`config/fixed_dag/agent_catalog.json`.

Phase R4-B adds the fixed DAG runtime binding registry implemented by
`src/react_agent/fixed_dag_runtime_registry.py` and sourced from
`config/fixed_dag/runtime_bindings.json`.

Phase R4-C isolates the legacy aNN registry/bootstrap into explicit
compatibility modules and keeps active graph imports on fixed-DAG contract,
executor, state, catalog, and binding seams.

Phase R7-C upgrades the original repo-external scaffold source package and
syncs a tracked repo mirror. These docs and examples explain how a future
adapter should translate external service envelopes into the fixed DAG
contracts below. They do not change runtime behavior, register scaffold code
into the graph, modify runtime bindings, or enable live invocation.

## Contract Boundary

Contracts separate internal DAG execution from the public transcript. Internal
payloads can be inspected by workflow tooling, but only mapped public fields may
reach the public adapter.

R3 hardens these contracts with deterministic constructors, normalizers,
validators, and topological executor seams. These seams do not implement real
business algorithms and do not call providers or external services.

R4-A makes the fixed DAG catalog the active backend `/api/agents` projection
source. The old `config/agents/*.json` aNN catalog is retained as legacy
migration input, not active reset public catalog truth.

R4-B adds runtime binding metadata for executor step results. The registry is
offline metadata only: it records deterministic seams, disabled external HTTP
candidates, and pending placeholders without invoking providers or external
`/v1/agent/invoke` endpoints.

R4-C keeps `legacy_agent_id` as migration metadata in binding/step-result
contracts but does not use `config/agents/*.json`, `AGENT_METADATA`, or
`AGENT_TOOLS` as active graph registration sources.

R7-C external handoff docs and scaffold package are contract-facing guidance:

- `docs/EXTERNAL_AGENT_HANDOFF_FIXED_DAG.md`
- `docs/EXTERNAL_AGENT_PAYLOAD_MAPPING_FIXED_DAG.md`
- `docs/EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md`
- `docs/EXTERNAL_AGENT_SAMPLE_PAYLOADS_FIXED_DAG.md`
- `examples/fixed_dag_external_agent_scaffold/`
- `E:\muti-agent\external_agent_scaffold`

They may reference historical external envelope names such as
`external_agent_health_v0`, `external_agent_request_v0`, and
`external_agent_response_v0` as adapter-side examples. The active fixed DAG
contract truth remains this document plus `fixed_dag_contracts.py`,
`fixed_dag_catalog.py`, `fixed_dag_runtime_registry.py`, and the JSON files
under `config/fixed_dag/`.

The sample scaffold's `map_response_to_conclusion_object` helper is local
example code. It is not a runtime adapter and does not write graph state.

R7-D clarifies that external service status, adapter decision, and fixed DAG
internal status are separate. External envelopes use `ok`, `partial`,
`needs_clarification`, and `error`; adapter policy maps them into
validator-legal conclusion statuses. Fixed DAG conclusion-family validators
use the intended vocabulary `pending_implementation`, `partial`, `complete`,
and `error`, while step execution status uses a separate enum.
`conclusion_object_v1` enforces the conclusion status enum directly; other
conclusion-family validators currently rely more on builders/typed contracts
than direct status rejection.

## fixed_dag_agent_catalog_v1

Purpose: define the active reset backend catalog of 27 formal `snake_case`
agents.

Catalog fields:

- `schema_version`
- `source`
- `total_count`
- `layer_counts`
- `dimension_counts`
- `agents`

Each agent includes:

- `id`
- `display_name`
- `layer`
- `dimension`
- `role_type`
- `stage`
- `default_enabled`
- `implementation_status`
- `description`
- `input_contract`
- `output_contract`
- `upstream`
- `downstream`

Validation rejects duplicate ids, legacy `aNN` primary ids,
`value_financial_analysis`, bad layer/dimension counts, sentiment-to-risk
routing, and `risk_composite` reading `sentiment_company_radar`.

Seams: `load_fixed_dag_catalog`, `validate_fixed_dag_catalog`,
`fixed_dag_agents`, `fixed_dag_agent_ids`, `fixed_dag_agents_by_layer`,
`fixed_dag_agents_by_dimension`, and `fixed_dag_public_agent_catalog`.

## fixed_dag_runtime_bindings_v1

Purpose: define backend runtime binding metadata for the same 27 formal
`snake_case` agents in `fixed_dag_agent_catalog_v1`.

Registry fields:

- `schema_version`
- `catalog_schema_version`
- `catalog_source`
- `total_count`
- `default_external_invoke_enabled`
- `bindings`

Each binding includes:

- `agent_id`
- `runtime_kind`
- `implementation_status`
- `invoke_enabled_by_default`
- `live_verified`
- `legacy_agent_id`
- `external_agent_id`
- `env_var`
- `default_url`
- `input_contract`
- `output_contract`
- `routes_to`
- `notes`

Allowed `runtime_kind` values are deterministic system/composite/decision/report
seams, disabled external HTTP candidates, and pending placeholders. External
HTTP candidates must have `invoke_enabled_by_default=false` and
`live_verified=false` in R4-B. Legacy aNN ids may appear only in
`legacy_agent_id`; primary `agent_id` values must be fixed DAG `snake_case` ids.

Validation rejects duplicate ids, ids that do not exactly match the fixed DAG
catalog, legacy aNN primary ids, `value_financial_analysis`, enabled external
candidates, live-verified external candidates, mismatched legacy wrapper
metadata, sentiment-to-risk routing, and contract/route drift from the catalog.
R4-C validates legacy external mapping through `external_http_config.py`, a
configuration-only module, so fixed-DAG binding checks do not import HTTP
wrapper implementation code.

Seams: `load_fixed_dag_runtime_bindings`,
`validate_fixed_dag_runtime_bindings`, `fixed_dag_runtime_bindings`,
`binding_by_agent_id`, `fixed_dag_runtime_binding_ids`,
`external_candidate_bindings`, `runtime_binding_summary`, and
`annotate_step_result_with_binding`.

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
The current reset roster in `target_agent_ids` contains the 27 formal v4
feedback-aligned agent ids from `fixed_dag_agent_catalog_v1`: L1=3, L2=18,
L3=4, L4=2.

Each step includes `depends_on`. R3 validates step id uniqueness, dependency
existence, acyclicity, legal stage, legal dimension, roster membership, and the
dimension-specific dependency rules before execution.

Seams:

- `build_default_fixed_dag_plan`
- `normalize_fixed_dag_plan`
- `validate_fixed_dag_plan`
- `validate_dag_steps`
- `topological_batches`

## fixed_dag_execution_v1

Purpose: record deterministic execution of a fixed DAG plan.

Runtime fields:

- `schema_version`
- `plan_id`
- `status`
- `fallback_used`
- `fallback_reason`
- `execution_batches`
- `step_results`
- `l2_conclusions`
- `dimension_results`
- `decision_result`
- `report_result`
- `limitations`
- `provenance`

`status` is `complete`, `partial`, or `degraded`. Invalid plans fail soft to the
deterministic default plan and set `fallback_used=true`.

Seams: `execute_fixed_dag_plan`, `validate_dag_execution_result`.

## fixed_dag_step_result_v1

Purpose: record one walked DAG step without exposing raw agent/provider output.

Runtime fields:

- `schema_version`
- `step_id`
- `agent_id`
- `stage`
- `dimension`
- `status`
- `depends_on`
- `output_ref`
- `summary`
- `warnings`
- `runtime_kind`
- `implementation_status`
- `binding_source`
- `legacy_agent_id`
- `external_agent_id`
- `invoke_enabled`
- `live_verified`

Allowed statuses are `complete`, `pending_implementation`, `skipped`, `blocked`,
and `failed`. R3 uses `complete` for planning and `pending_implementation` for
business placeholders. R4-B adds binding metadata to each step result but does
not include endpoint URLs or env var names in step results.

Seams: `build_step_result`, `validate_step_result`,
`build_initial_step_results`.

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
- `planId`
- `stages`
- `dagSteps`
- `dimensionGroups`
- `currentStage`
- `completedSteps`
- `executionBatches`
- `stepResults`
- `provenance`
- `finalSource`

`finalSource` is currently `reset_skeleton`.
`provenance` includes executor-oriented fields such as `executionStatus`,
`fallbackUsed`, and `limitations` while keeping provider and external invocation
flags false.

Seams: `build_workflow_snapshot_v2`, `validate_workflow_snapshot_v2`.
Graph final emission also uses `build_final_emit_payload`,
`build_emitted_bundle`, and `build_reset_multi_agent_bundle`.
`fixed_dag_reset_bundle_v1` includes `dag_execution`, `dag_step_results`, and
`execution_batches`.

## Public Agent Catalog

Purpose: expose the reset agent catalog to the web shell without leaking old
config/profile/tool internals.

Endpoint: `GET /api/agents`

Public response model: `AgentCatalogResponse`.

R4-A/R4-B/R4-C semantics:

- `configCount=27`
- `runtimeCount=27`
- `disabledIds=[]`
- layer rows L1=3, L2=18, L3=4, L4=2
- agent ids are the fixed DAG `snake_case` ids
- descriptions may say `pending_implementation` or `deterministic_skeleton`

The field names remain compatible with the existing public schema. Their R4-A
meaning is reset catalog projection, not old aNN config file enablement.
R4-B/R4-C do not add runtime binding or legacy registry fields to
`/api/agents`.

## Public Exclusions

Do not expose the following as transcript content:

- raw graph messages
- provider raw responses
- manager assignments
- agent JSON payloads
- internal traces
- secrets or environment values
- provider or external raw responses
- endpoint URLs or env var values as transcript content
