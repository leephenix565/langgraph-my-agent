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
syncs a tracked repo mirror. Phase R7-F restores the domain payload family.
Phase R7-G upgrades that package to
`external-agent-scaffold-v2.3.1-fixed-dag`, patching contract semantics for
L2 risk members, manual review gates, structured dimension members, normalized
date comparison, macro directional weights, L4 score tolerance, and distinct
reasoning stages. These docs and examples explain how a future adapter should
translate external service envelopes into the fixed DAG contracts below. They
do not change runtime behavior, register scaffold code into the graph, modify
runtime bindings, or enable live invocation.

Phase R8-6B adds default-off internal LLM placeholders for fixed-DAG L2
conclusions in `src/react_agent/fixed_dag_llm_placeholders.py`. This is not an
external adapter contract and does not change runtime bindings.

Phase R8-7B adds provider-free pure external payload adapter mapping in
`src/react_agent/fixed_dag_external_adapter.py`. The first implementation slice
maps already-available `agent_conclusion_v1` payloads into
`conclusion_object_v1` and `data_bundle_v1` payloads into the current narrow
internal `data_bundle_v1`. It does not call HTTP, providers, `/health`,
`/v1/agent/compute`, `/v1/agent/invoke`, or deployed server agents; it does not
change the active graph, executor, runtime bindings, live flags, or fixed DAG
roster.

R8-8J extends the same provider-free adapter boundary so
`external_agent_compute_v0` envelopes with concrete `data_bundle_v1` tool
results can map to the internal `data_bundle_v1` contract. This is adapter input
only. It does not make compute envelopes graph state, does not call services,
and does not wire L1 data services into active graph execution.

R8-8K extends the same provider-free adapter boundary so
`external_agent_compute_v0` envelopes with concrete `entity_relation_bundle_v1`
tool results can map to the internal `entity_relation_bundle_v1` contract. This
is adapter input only. It does not make compute envelopes graph state, does not
call services, and does not wire L1 entity-relation services into active graph
execution.

CS1-C2X preserves the CS1-C1X temporal guard and adds an outbound request
compatibility rule: the bridge projects the same requested fixed-DAG date into
top-level `as_of`, top-level `as_of_date`, `context.as_of`,
`context.as_of_date`, `options.as_of`, and `options.as_of_date`. Services may
consume any of these aliases, but mapped date-bearing results must still pass
the request-as-of guard before entering DAG state.

CS1-C2X also clarifies public trace acceptance: the real PublicTurn and
Workflow objects must pass unsafe scanning before artifact scrub. Scrubbed
artifacts are not a substitute for a safe public contract.

CS1-C3X adds a formal L3 member identity invariant for external composites.
Macro composite payloads that include `members` must use unique formal macro L2
ids only:
`macro_analysis`, `macro_commodity_pricing`, `macro_index_valuation`,
`macro_sentiment`, and `macro_industry_hotspot`. Service-local aliases,
Chinese names, and diagnostic stand-ins can remain service-private diagnostics,
but they cannot be emitted as formal members or counted as real L2 evidence.
Pending or partial formal macro members must not contribute positive weight.

CS1-C3R generalizes the L3 contributor invariant across dimensions. A formal
member slot is not necessarily a real contributor. Pending, error,
zero-confidence, no-evidence, deterministic placeholder, and external-failure
fallback slots must carry zero weight, must not enter `contributing_agents`,
must not emit `evidence_refs`, and must not be described as a main contributor
in public report text. Partial members with real bounded business material may
contribute positive weight and must remain labeled partial/degraded.

BF-COMPLETE-X records the final sandbox-to-prod backfill contract closure for
the remaining L1/L2 sandbox units. `entity_relation_extractor` production
compute returns `external_agent_compute_v0` with
`tool_result.schema_version=entity_relation_bundle_v1`,
`tool_result.agent_id=entity_relation_extractor`, bounded entities/relations,
and request-bounded `as_of` / `data_as_of`. `sentiment_company_radar` keeps
formal fixed-DAG id `sentiment_company_radar`, uses service-local
`external_agent_id=company_radar_agent`, emits `agent_conclusion_v1` with
`dimension=market`, `role=direction`, and `output_routes=["market_composite"]`,
and remains invalid for risk routing. These service closures do not relax
compute adapter identity rules, do not change runtime bindings, and do not
enable external invoke.

POST-BF-B1X adds readiness metadata as optional health fields for services that
need to distinguish liveness from production-default readiness:
`service_alive`, `contract_available`, `compute_available`,
`data_dependency_ready`, `ready_for_default_runtime`, `readiness_status`, and
`degraded_reason`. These fields are additive to `external_agent_health_v0` and
do not change compute adapter identity rules. A service can be alive and
compute-capable while still not ready for default runtime because data
dependencies are unavailable. The sentiment wrapper also preserves the
fixed-DAG contract name `stock_sentiment` while internally dispatching to the
existing core `sentiments` implementation.

POST-BF-B2X adds `fixed_dag_non_l4_external_compute_policy_v1` as the
production non-L4 compute policy contract. It is source-controlled in
`config/fixed_dag/non_l4_external_compute_policy.json`, validates the exact
B1X required activation set, optional macro-only degraded candidate, loopback
`/v1/agent/compute` path, per-agent timeout/failure policy, and excluded-agent
boundary. The executor records actual non-L4 compute activity in private
`production_external_compute_*` provenance while preserving the existing public
`externalInvoked=false` no-`/invoke` claim.

SYNC-OPS-1 adds the read-only external Agent sync planning contract family. The
source-controlled registry and policy live in `config/ops/`, schemas live in
`config/ops/schemas/`, examples live in `config/ops/examples/`, and the planner
logic lives under `src/react_agent/ops/`. These contracts are separate from
fixed-DAG runtime plans and never enter LangGraph `State`.

The planner validates artifacts with real JSON Schema Draft 2020-12 through
`jsonschema.Draft202012Validator`, then applies repo semantic validators for
catalog equality, route boundaries, canonical plan hashes, target freshness,
sanitized-derivative blockers, active-baseline guards, and approval scope.
Planner commands may emit inventory, B/S/P/D diff, P2S plan, S2P plan, and
cycle plan JSON, but SYNC-OPS-1 has no stage/apply/smoke/rollback/lock command.

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

R8-6B keeps the default L2 conclusion path deterministic. When
`Context.enable_internal_llm_placeholders` /
`ENABLE_INTERNAL_LLM_PLACEHOLDERS=1` is explicitly enabled, L2 conclusions may
be generated by the main-system internal LLM placeholder seam. The output remains
`conclusion_object_v1`, confidence is capped at `0.4`, status is `partial` on
successful placeholder generation, and provider or parse failure falls back to
the deterministic `pending_implementation` conclusion.

R8-7B keeps active runtime behavior unchanged. The external adapter is a pure
mapping layer that accepts dictionaries already available to tests or future
wrappers and returns validator-legal internal objects or controlled adapter
failure records. `external_invoked=false` in mapper output means the mapper
itself made no live call; future live bridges must record invocation facts in a
separate readiness/runtime layer.

R8-12 adds such a bridge only for demo use. The bridge lives in
`fixed_dag_external_compute_bridge.py`, is default-off, and is loaded by
`execute_fixed_dag_plan` only when `enable_external_compute_demo` is true and
`external_compute_demo_allowlist` contains registered fixed DAG ids. It sends
`external_agent_request_v0` requests only to loopback production
`/v1/agent/compute`, maps responses through the pure adapter, and stores only
validator-legal internal contracts plus bounded public-safe summaries. It does
not call `/v1/agent/invoke`, does not change runtime bindings, and does not
make compute evidence default graph execution.

R8-12C adds `report_input_bundle_v1` as the report-generator consumption
contract. The executor builds it after L2/L3 mapping and before report
generation. It contains only bounded public-safe summaries: L2 agent signals,
L3 composite summaries, risk gate summary, macro regulator summary, and
decision context. The same bounded summaries may be projected into
`workflow_snapshot_v2.stepResults` as `agent_evidence` and
`composite_evidence` for Web drilldown. The bundle must not contain raw
external responses, endpoint URLs, secrets, error stacks, or internal reasoning
drafts.

R8-12D adds `fixed_dag_report_synthesizer.py` as a default-off LLM report
synthesis seam. When `enable_llm_report_synthesis` is true, the synthesizer
passes only `report_input_bundle_v1` to the configured chat model and expects a
bounded `report_result_v1` JSON response. Invalid, unsafe, or unavailable model
output fails closed back to the template report from R8-12C. This is a
main-system model call, not an external agent `/v1/agent/invoke` call, and it
does not change runtime bindings or live flags.

R8-13N adds `fixed_dag_l3_explanation_synthesizer.py` as a default-off L3
language explanation seam. When `enable_llm_l3_explanation` is true, it reads
only public-safe L2 conclusions and deterministic L3 composite results, then
may prepend bounded L3 `research_points` and add `provenance.llm_explanation`.
It must not override deterministic fusion fields such as `stance`, `gate`,
`risk_score`, `dimension_weights`, member weights, confidence, status, or
contributing agents. Invalid, unsafe, or unavailable model output fails closed
to the original deterministic L3 results.

R8-13Q adds the approved L4 compute-default runtime boundary. Only
`decision_synthesizer` and `report_generator` may use
`runtime_kind=external_compute_default`, and only with loopback
`/v1/agent/compute` URLs. The executor reads those bindings after the
deterministic L4 fallback payloads are built, calls the L4 compute service, maps
the result through the same public-safe adapter, and records bounded
`external_compute_default_*` provenance. This path is not the R8-12 demo bridge,
does not call `/v1/agent/invoke`, and does not enable any L1/L2/L3 external
service by default. `Context.disable_external_compute_default` or
`DISABLE_EXTERNAL_COMPUTE_DEFAULT=1` restores deterministic L4 behavior for
rollback and offline tests.

CS1-C1X adds a health-only identity validator in
`fixed_dag_external_health.py`. Health validation accepts canonical formal ids,
explicit bridge compatibility, or registered legacy compatibility when the
alias is source-controlled and the caller has verified the expected port and
source. Compatibility health pass is migration debt: it is not a canonical
service contract, compute pass, adapter pass, invoke pass, runtime enablement,
or live flag. The compute adapter identity rule remains strict.

CS1-C1X also adds request-as-of temporal integrity to
`fixed_dag_external_compute_bridge.py`. For date-bearing external compute
results, mapped `as_of` and `data_as_of` must not be after the requested fixed
DAG `as_of`. Failures use bounded reasons such as
`response_as_of_after_requested_as_of` and remain fail-closed before results
enter executor state or report bundles.

R7-G external handoff docs and scaffold package are contract-facing guidance:

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

R7-G maintains scaffold-local v2.3.1 payload schemas and `validate_tool_result` for
`agent_conclusion_v1`, `dimension_conclusion_v1`, `risk_conclusion_v1`,
`macro_conclusion_v1`, `decision_conclusion_v1`, `eval_record_v1`,
`fixed_dag_plan_v1`, and `data_bundle_v1`. These are adapter-side handoff
schemas, not active graph state schemas.

External v2.3.1 fields such as `DimensionMember[]`, `raw_output`, `quality`,
`calculation_trace`, and risk `manual_review` are adapter inputs. Future R8
adapter code must explicitly decide how to map or discard them; they do not
automatically become fixed DAG runtime state.

R8-7B made that decision for the first supported families, and R8-10B extends
the same provider-free adapter boundary to L3 composite payloads:

- `agent_conclusion_v1` direction outputs map to `conclusion_object_v1`.
- `agent_conclusion_v1` risk `gate_member` outputs may map only when the primary
  `agent_id` is a current fixed-DAG risk L2 id; `risk_score` is preserved in
  provenance because `conclusion_object_v1` has no top-level `risk_score` slot.
- `data_bundle_v1` maps into the current narrow `DataBundle` shape by preserving
  status, timestamps, source names, and bounded notes for snapshot/features.
- `external_agent_compute_v0.tool_result.data_bundle_v1` maps through the same
  `data_bundle_v1` adapter path as R8-8J L1 data-service evidence only.
- `entity_relation_bundle_v1` maps into the current `EntityRelationBundle`
  shape by preserving status, timestamps, bounded entities, bounded relations,
  source names, and safe notes.
- `external_agent_compute_v0.tool_result.entity_relation_bundle_v1` maps
  through the same `entity_relation_bundle_v1` adapter path as R8-8K L1
  entity-relation evidence only.
- `dimension_conclusion_v1` maps into `dimension_composite_result_v1` for
  `value_composite` and `market_composite`. The adapter requires member ids to
  come from the matching L2 roster, requires member weights to sum to roughly
  one, and keeps only bounded member/evidence summaries in provenance.
- `risk_conclusion_v1` maps into `dimension_composite_result_v1` for
  `risk_composite`. It preserves `gate`, `manual_review`, `veto`, `penalty`,
  `risk_score`, triggered flags, and red lines without producing a direction
  `stance`; `sentiment_company_radar` remains forbidden as a risk contributor.
- `macro_conclusion_v1` maps into `dimension_composite_result_v1` for
  `macro_composite`. `dimension_weights` are restricted to `value` and
  `market`; `risk` remains the independent gate and `macro` remains the
  regulator.
- `raw_output` and `quality` do not enter graph state verbatim; bounded
  public-safe report material may appear in provenance/report bundles after
  adapter validation.
- `decision_result_v1` and `report_result_v1` map through the L4 adapter path
  for the R8-13Q compute-default runtime. `decision_conclusion_v1`,
  `eval_record_v1`, `fixed_dag_plan_v1`, and non-L4 active external runtime
  execution remain later work.

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
seams, disabled external HTTP candidates, external compute defaults, and
pending placeholders. External HTTP candidates must have
`invoke_enabled_by_default=false` and `live_verified=false`. External compute
defaults are currently limited to the two L4 ids and must use
`/v1/agent/compute`, not `/v1/agent/invoke`. For those two approved L4 rows,
`live_verified=true` means the compute-default runtime path passed the R8-13Q
controlled smoke; `invoke_enabled_by_default` must still remain false. Legacy
aNN ids may appear only in `legacy_agent_id`; primary `agent_id` values must be
fixed DAG `snake_case` ids.

Validation rejects duplicate ids, ids that do not exactly match the fixed DAG
catalog, legacy aNN primary ids, `value_financial_analysis`, enabled external
candidates, live-verified external candidates, mismatched legacy wrapper
metadata, sentiment-to-risk routing, non-L4 external compute defaults, compute
defaults with invoke URLs, and contract/route drift from the catalog.
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

## route_intent_v1

Purpose: record controlled-routing planner intent without making it an
executable DAG.

R8-1 adds this contract as an additive seam. R8-2 compiles valid route intent
deterministically into `selected_fixed_dag_plan_v1`. R8-3 adds provider-free
planner seam helpers and a future prompt/parser boundary for generating and
normalizing route intent. R8-4 adds provider-free RouteEval over this contract.
R8-5 wires the provider-free planner seam into the graph behind
`Context.enable_selected_routing` / `ENABLE_SELECTED_ROUTING=1`. The active
graph still does not call an LLM planner and selected routing remains
default-off.

Fields:

- `schema`
- `schema_version`
- `task_type`
- `targets`
- `selected_dimensions`
- `selected_agents`
- `task_brief_by_agent`
- `route_confidence`
- `needs_clarification`
- `clarification_question`
- `fallback_reason`
- `provenance`

Allowed `task_type` values are `single`, `compare`, `screen`, `macro`,
`sentiment`, `industry`, `event`, and `general`. Allowed dimensions are
`value`, `market`, `risk`, and `macro`.

Validation requires confidence in `[0, 1]`, selected agents from the fixed DAG
27-agent roster, no legacy aNN ids, no `value_financial_analysis`, no legacy
Star/Chain/Debate/Tree dispatch fields or values, and no provider/external
invocation claim. L2 agents must match their selected dimension; in particular
`sentiment_company_radar` remains market-only. `task_brief_by_agent` keys must
be a subset of `selected_agents`. Clarification requests require a non-empty
question. Empty selected-agent intents require a fallback reason unless they
need clarification.

Policy gates:

- `route_intent_v1` records requested dimensions and business agents. Fixed
  system dependencies, composites, `decision_synthesizer`, and
  `report_generator` are compiler responsibilities.
- Investment-judgment task types (`single`, `compare`, `screen`, `industry`,
  `event`) require the risk dimension and at least one selected risk L2 agent.
- `general`, `macro`, and `sentiment` intents may omit risk and decision.
- Fallback text must stay public-safe; it must not expose provider, endpoint,
  env var, secret, traceback, runtime binding, placeholder, or similar raw
  implementation language.

Seams:

- `build_route_intent`
- `build_default_route_intent`
- `validate_route_intent`
- `FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT`
- `build_route_intent_prompt`
- `parse_route_intent_json`
- `normalize_route_intent`
- `compile_selected_fixed_dag_plan`
- `load_route_eval_cases`
- `evaluate_route_intents`
- `route_eval_report_to_dict`

R8-3 prompt/parser boundary:

- the planner target is `route_intent_v1` only;
- planner output must not contain executable DAG fields, dependency fields, or
  runtime binding changes;
- parser normalization may filter unknown agents only when valid selected
  agents remain;
- invalid shapes fail soft to a clarification/fallback route intent instead of
  becoming executable plans;
- removed ids, legacy numbered ids, selected sentiment-to-risk misuse,
  investment intents without risk, and provider/external invocation claims are
  rejected or normalized to fallback.

## RouteEval baseline

Purpose: evaluate `route_intent_v1` selection quality before selected routing
is enabled in the active graph.

R8-4 adds `src/react_agent/route_eval.py` and
`tests/fixtures/route_eval_gold.jsonl`. The evaluator is provider-free and
deterministic. It accepts a planner function that returns a route-intent-shaped
mapping, so it can score `build_default_route_intent`, parser-normalizer
fixtures, or later provider-free planner stubs without executing a DAG.

Metrics:

- `task_type_accuracy`
- `target_exact_or_partial_match`
- `dimension_precision`
- `dimension_recall`
- `dimension_f1`
- `agent_precision`
- `agent_recall`
- `agent_f1`
- `over_selection_count`
- `under_selection_count`
- `clarification_accuracy`
- `fallback_rate`

Gold case fields include `id`, `query`, `gold_task_type`, `gold_targets`,
`gold_dimensions`, `gold_agents`, `gold_needs_clarification`,
`acceptable_extra_agents`, `must_not_agents`, and `notes`.
`acceptable_extra_agents` are not counted as false positives.
`must_not_agents` are counted as false positives when predicted.

Non-claims:

- RouteEval does not evaluate Star/Chain/Debate/Tree mode accuracy.
- RouteEval does not produce executable DAGs.
- RouteEval does not call an LLM, provider, search backend, or external
  `/v1/agent/invoke`.
- The first gold set is a small baseline, not the future >=80% Route F1 gate.
- R8-4 does not enable selected routing in `src/react_agent/graph.py`.

## selected routing graph flag

Purpose: connect the selected-routing pipeline to the graph only behind an
explicit default-off boundary.

R8-5 adds `Context.enable_selected_routing` with env support through
`ENABLE_SELECTED_ROUTING=1`. When the flag is false, `route_planner_node` still
returns the full `fixed_dag_plan_v1` baseline. When the flag is true, the graph
uses `build_default_route_intent`, compiles the intent with
`compile_selected_fixed_dag_plan`, and passes the resulting
`selected_fixed_dag_plan_v1` to the existing execution path.

Failure policy:

- invalid route intent, compiler failure, or selected validation failure falls
  back to the full DAG;
- fallback provenance records `selected_routing_requested=true`,
  `selected_routing_fallback=true`, and a public-safe fallback code;
- fallback provenance keeps `provider_invoked=false` and
  `external_invoked=false`;
- the LLM/provider must never generate executable `depends_on` or `dag_steps`.

Non-claims:

- the selected flag does not enable provider, search, or external invocation;
- the selected flag does not modify runtime bindings or external readiness;
- the selected flag does not make RouteEval a formal >=80% acceptance gate;
- the selected flag does not implement real business-agent logic.

## selected_fixed_dag_plan_v1

Purpose: define the deterministic compiler/validator target for a selected
sub-DAG while keeping `fixed_dag_plan_v1` as the full default regression
baseline.

R8-1 adds validation. R8-2 adds deterministic compilation and selected executor
validation helpers. The active graph still does not execute selected plans by
default and the selected validator does not call `validate_fixed_dag_plan`.

Fields include the base plan fields plus:

- `selected_dimensions`
- `selected_agents`
- `omitted_dimensions`
- `omitted_agents`
- `route_intent`
- `fallback_to`
- `fallback_reason`

Selected plans may contain fewer than 27 steps, and `dimension_groups` may be a
selected subset. Validation still requires all selected steps, DAG steps, stage
step ids, targets, selected agents, selected dimensions, omitted agents, and
omitted dimensions to reconcile. Step agent ids must be fixed DAG roster ids
and must match the selected target set. Step dimensions must match the catalog
dimension for the selected agent.

R8-2 `compile_selected_fixed_dag_plan` builds dependency closure
deterministically:

- adds `route_planner`, `financial_data_service`, and
  `entity_relation_extractor`;
- keeps selected L2 business agents only;
- adds selected dimension composites and points each composite at selected
  same-dimension L2 agents;
- adds `decision_synthesizer` for investment-judgment task types;
- always adds `report_generator`;
- makes report depend on decision when present, otherwise on selected dimension
  composites;
- records omitted dimensions and omitted agents.

Validation rejects runtime binding fields, external/provider/raw response
fields, legacy dispatch keys, legacy dispatch values, sentiment-to-risk
dependencies, enabled external invocation claims, unsafe fallback text, bad
fallback targets, and missing full-DAG fallback reason.

Seams:

- `build_selected_fixed_dag_plan`
- `validate_selected_fixed_dag_plan`
- `compile_selected_fixed_dag_plan`
- `validate_selected_dag_steps`
- `topological_batches_for_selected_plan`

Non-claims:

- `route_intent_v1` is not executable.
- `selected_fixed_dag_plan_v1` is not the active runtime default.
- R8-5 does not add an active LLM planner,
  external adapter, public workflow field, web UI change, provider call, search
  call, external `/v1/agent/invoke` call, or runtime binding change.

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
deterministic default plan and set `fallback_used=true`. R8-5 allows selected
plans to flow through selected executor validation; selected execution emits
step results and workflow snapshot entries for the selected step subset only.

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

R8-6B adds one narrow provenance exception for internal placeholders:
`provider_invoked=true` is allowed only when `provenance.source` and
`provenance.runtime_path` are both `internal_llm_placeholder`, confidence is
`<=0.4`, and `external_invoked=false`. This records an internal model
placeholder path, not an external service or live business-agent result. Raw
model output, endpoints, secrets, tracebacks, and chain-of-thought are not stored
in graph state.

Seams: `build_pending_conclusion`, `build_l2_conclusions`,
`build_l2_conclusions_with_internal_placeholders`,
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
- optional bounded `provenance`

Seams: `build_value_composite`, `build_market_composite`,
`build_risk_composite`, `build_macro_composite`, `build_dimension_results`,
`validate_dimension_composite_result`.

R8-10B notes: the deterministic macro placeholder and the external macro
adapter both use `dimension_weights` keys `value` and `market` only. A risk
decision remains represented by `risk_composite`; macro is a regulator over
directional value/market weights rather than a fourth direction vote.

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

`report_result_v1.sections`, `evidence_cards`, and `limitations` are now
preserved through `build_final_emit_payload`, `build_emitted_bundle`, and the
public assistant answer card. The public transcript still remains a single
assistant answer; these fields are structured report material for UI rendering
and artifacts, not raw graph messages or raw agent JSON.

## report_input_bundle_v1

Purpose: describe the structured L2 and L3 evidence that the report generator
receives, without exposing raw agent JSON or endpoint details.

Runtime fields:

- `schema`
- `schema_version`
- `question`
- `status`
- `agent_task_summaries`
- `agent_evidence_bundle`
- `l2_agent_summaries`
- `l3_composite_summaries`
- `risk_gate`
- `macro_regulator`
- `decision_context`
- `limitations`
- `provenance`

`l2_agent_summaries[]` contains bounded fields such as `agent_id`,
`display_name`, `dimension`, `stance`, `confidence`, `summary`, and source.
`l3_composite_summaries[]` adds bounded composite-specific fields such as
members, risk gate/risk score, macro regime, and value/market macro weights.
`agent_evidence_bundle.l2_agent_outputs[]` and
`agent_evidence_bundle.l3_composite_outputs[]` may include additive
public-safe report material:

- `evidence_items`: bounded fact/source/as-of evidence items.
- `domain_metrics`: allowlisted business metrics from mapped external
  `raw_output`, such as valuation bridges, model vote counts, risk scores,
  regime details, member counts, or fair-value ranges.
- `drivers`: allowlisted named drivers, model features, method assumptions,
  rubric tables, member-weight summaries, warnings, or fusion details.
- `research_points`: bounded deterministic research judgments with
  `claim`, `support`, `interpretation`, `decision_implication`, and `caveat`.
- `data_quality`: bounded coverage, data-source, anti-lookahead, cached,
  missing-component, corpus, or composite-status notes.

The public-safe allowlist can grow for service-owned report material without
creating a new payload family. The June 18 sandbox wrapper pass added projection
support for financial-fraud bridges (`fraud_risk_bridge`, `model_context`,
`feature_diagnostics`, `risk_gate_rule`) and macro-cycle bridges
(`macro_regime_bridge`, `macro_signal_table`, `asset_allocation_view`,
`sector_rotation_summary`, `macro_data_window`, `zeping_crosscheck_context`).
These fields remain bounded report inputs only; they do not make `/compute`
evidence into `/invoke` evidence, enable runtime bindings, or set live flags.

The June 19 L3 material pass extends the same boundary to service-owned
composite research packets. Default-off external L3 compute requests may receive
bounded current-run L2 report material in `context.upstream_outputs` and
`agent_task_v1.upstream_results`, including `domain_metrics`, `drivers`,
`research_points`, `data_quality`, and bounded evidence. The bridge must strip
endpoint URLs, secrets, raw responses, tracebacks, and internal reasoning
drafts before sending this context. External L3 payloads may then expose
report-facing `composite_research_packet`, `composite_quality`,
`conflict_summary`, `dominant_signals`, `missing_or_degraded_members`,
`final_implication`, and `limitations`. These fields explain already-computed
fusion outputs; they must not override stable fields such as `stance`,
`confidence`, `gate`, `risk_score`, `dimension_weights`, member weights,
`status`, or `contributing_agents`.

For deterministic L3 risk composites, member-level warnings and model/data
boundaries may also be summarized as `member_boundary_summary` inside L3
`drivers` and `data_quality`. This is report-facing material only: it does not
change `risk_score`, `gate`, member weights, or L2 source values. Its purpose is
to keep caveats such as model-vintage limits or missing text evidence visible
after L3 compression.

When external L3 services are not overlaid, the main-system deterministic L3
projection may derive bounded composite material from already available L2
outputs. It marks the composite `complete` only when all selected members are
complete, `partial` when at least one selected member is complete/partial, and
`pending_implementation` when no selected member is usable. Member weights are
confidence-normalized among usable members; missing or placeholder members have
weight `0`. Risk composites read only risk-dimension members and must not
consume `sentiment_company_radar`.

Fallback report rendering prefers the detailed `agent_evidence_bundle` entries
when present. It expands L2 entries only when they have public-safe report
material or error status; no-evidence placeholder/pending L2 entries are kept in
`report_input_bundle_v1` and workflow trace but are summarized as a missing
coverage count instead of being rendered as fake research material. Compact
summaries remain available for UI surfaces that only need a short status
overview.
The bundle is validated before report rendering and before
`validate_dag_execution_result` accepts an execution result.

Seams: `build_report_input_bundle`, `validate_report_input_bundle`,
`build_report_result`.

Non-claims: the bundle does not enable runtime bindings, does not call
`/v1/agent/invoke`, does not set live flags, and does not prove production
business correctness.

## LLM report synthesis seam

Purpose: allow a default-off report generator to read `report_input_bundle_v1`
and produce a natural Chinese `report_result_v1`.

Boundary: this is the R8-12D main-system fallback/demo seam, anchored locally by
tag `r8-12d-llm-report-synthesizer-fallback`. It is not the formal external
`report_generator` agent integration. The future external service should use
the same bounded input/output contract so the main system can swap the primary
path without accepting raw agent output or enabling runtime bindings by default.

Runtime controls:

- `Context.enable_llm_report_synthesis`
- `ENABLE_LLM_REPORT_SYNTHESIS=1`
- optional `Context.llm_report_synthesis_model`
- optional `LLM_REPORT_SYNTHESIS_MODEL`

Failure behavior: invalid report input, provider/model load failure, missing
known-provider credentials, parse failure, invalid schema, or unsafe output
returns the fallback template `report_result_v1`. The fallback must remain
valid and public-safe.

Provider preflight: for known providers such as DeepSeek/OpenAI, the
synthesizer records only secret-free readiness metadata such as `provider`,
`model`, `credential_status`, `base_url_status`, and `preflight_status`. Missing
credentials short-circuit before any provider invocation. Credential names,
credential values, raw provider responses, and endpoint URLs must not enter
graph state or public workflow.

Safety rules:

- The synthesizer receives only `report_input_bundle_v1`.
- It must not receive raw external payloads or endpoint URLs.
- It must not call external agent `/v1/agent/invoke`.
- It must not store raw model output in graph state or public workflow.
- It may set public workflow `providerInvoked=true` when the explicit synthesis
  flag actually invokes the configured model.

## L4 external compute handoff seam

Purpose: allow `decision_synthesizer` and `report_generator` to be tested as
formal L4 agent ids through the same default-off compute-only bridge used by
the rest of the fixed DAG.

Runtime controls:

- `Context.enable_external_compute_demo`
- `ENABLE_EXTERNAL_COMPUTE_DEMO=1`
- explicit `EXTERNAL_COMPUTE_DEMO_ALLOWLIST` entries for
  `decision_synthesizer` and/or `report_generator`

Input:

- `decision_synthesizer` receives bounded current-run `dimension_results`
  under `context.dimension_results`.
- `report_generator` receives bounded current-run `decision_result` and
  `report_input_bundle_v1` under `context`.
- Requests remain `/v1/agent/compute` requests. The bridge never calls external
  `/v1/agent/invoke`.

Output:

- `decision_synthesizer` must return `decision_result_v1`.
- `report_generator` must return `report_result_v1`.
- The main-system adapter validates both payloads and strips unsafe text such
  as secrets, endpoint URLs, raw provider responses, raw external JSON,
  tracebacks, and internal reasoning drafts.
- R8-13K adds a regression requirement for provider-backed L4 output: if a
  `decision_result_v1` or `report_result_v1` contains raw provider artifacts,
  secrets, endpoint URLs, tracebacks, raw external JSON, or chain-of-thought
  markers anywhere in the public-facing payload, the adapter must return an
  adapter failure instead of allowing the payload into the final transcript.

Boundary:

- This seam is default-off and allowlist-only.
- It does not modify runtime bindings, set `live_verified`, or set
  `invoke_enabled_by_default`.
- It does not make sandbox L4 services production-default.
- When an external `report_generator` result is mapped, the internal LLM report
  synthesis seam must not overwrite it in the same execution.
- Provider-backed `/v1/agent/compute` pass was not runtime enablement by
  itself. R8-13Q later completed the separate runtime/public-transcript review
  and config phase for the two L4 ids only.
- Minimum runtime review checklist before any external-L4 default path:
  public answer safety, workflow detail safety, deterministic fallback and
  rollback, explicit operator control for the two L4 ids only, provider
  credential hygiene, and separation of `/compute` evidence from `/invoke`
  evidence.

## fixed_dag_l4_runtime_binding_dry_run_v1

Purpose: simulate whether the two L4 ids could enter a later external default
runtime-binding review without editing `runtime_bindings.json`.

Runtime fields:

- `schema_version`
- `status`
- `runtime_bindings_changed`
- `default_runtime_enabled`
- `invoke_endpoint_required`
- `agents`
- `readiness`
- `blocking_reasons`
- `recommended_next_action`

Seam: `build_l4_runtime_binding_dry_run`.

The dry run is metadata-only. Before R8-13Q it read deterministic L4 bindings,
showed the proposed compute URLs for `decision_synthesizer` and
`report_generator`, and reported missing requirements such as rollback plan or
operator approval. After R8-13Q it detects the current
`external_compute_default` bindings and reports the default path as already
configured. It never calls endpoints and `invoke_endpoint_required` remains
false.

## fixed_dag_l4_runtime_review_evidence_package_v1

Purpose: package the evidence required to decide whether an explicit external
L4 runtime-binding phase may be opened. This is still local metadata and does
not call endpoints or edit configuration.

Seam: `build_l4_runtime_review_evidence_package`.

Current repo-recorded candidate seam:

- `build_l4_runtime_review_candidate_package`

Required evidence records:

- `provider_compute_pass`
- `transcript_safety_pass`
- `rollback_plan_ready`
- `operator_approval`

Each evidence record must be a mapping with `passed=true` and a safe
`reference`. Optional safe fields are `summary`, `validated_by`, and
`validated_at`. Unknown fields are ignored. Unsafe references or text, including
raw provider artifacts, secrets, endpoint URLs, tracebacks, raw external JSON,
or chain-of-thought markers, are not preserved and cannot satisfy the evidence
requirement.

Output:

- `schema_version`
- `status`
- `runtime_bindings_changed`
- `default_runtime_enabled`
- `invoke_endpoint_required`
- `required_evidence`
- `missing_evidence`
- `dry_run`
- `non_actions`
- `recommended_next_action`

Status values:

- `blocked_pending_evidence`: at least one required record is missing, invalid,
  unsafe, or not passing.
- `ready_for_explicit_runtime_binding_phase`: all four required records are
  passing and safe. This means only that a separate runtime-binding phase may be
  opened; it does not edit runtime bindings.

The package remains metadata-only: it does not call endpoints or edit
configuration. R8-13O recorded a candidate package with provider compute,
transcript safety, and rollback-plan evidence passing while
`operator_approval` was pending. R8-13Q records operator approval for the L4
runtime goal and uses the same evidence gate before the runtime binding phase.
`invoke_endpoint_required` remains false.

## fixed_dag_l4_runtime_binding_phase_plan_v1

Purpose: describe the intended external-L4 runtime binding phase without
editing runtime bindings.

Seam: `build_l4_runtime_binding_phase_plan`.

The preflight consumes an L4 runtime review evidence package and returns:

- `schema_version`
- `status`
- `runtime_bindings_changed`
- `config_edit_allowed`
- `current_schema_allows_external_l4_default`
- `missing_evidence`
- `planned_agent_changes`
- `required_work`
- `recommended_next_action`

Current status:

- R8-13Q configures the two L4 rows as `external_compute_default`.
- The executor calls L4 `/v1/agent/compute` from runtime bindings without
  enabling the default-off demo bridge and without calling `/v1/agent/invoke`.
- `disable_external_compute_default` can be used as a rollback/test control to
  restore deterministic L4 behavior without editing `.env`.

The phase-plan preflight now reports `runtime_binding_configured_pending_smoke`
after the config edit, and the controlled smoke evidence is recorded in
`docs/CONTROLLED_READINESS_SMOKE_LOG.md`.

## L3 LLM explanation seam

Purpose: allow a default-off language layer to explain deterministic L3
composites, member conflicts, missing coverage, and decision implications
without making the LLM responsible for fusion.

Runtime controls:

- `Context.enable_llm_l3_explanation`
- `ENABLE_LLM_L3_EXPLANATION=1`
- optional `Context.llm_l3_explanation_model`
- optional `LLM_L3_EXPLANATION_MODEL`

Input: the seam receives only bounded public-safe snapshots of current-run L2
conclusions and deterministic L3 composite results. Prompt construction strips
raw external JSON, endpoint URLs, secrets, traceback text, raw provider
responses, and internal reasoning drafts.

Output: valid model output may add bounded Chinese `research_points` to L3
`provenance` and attach `provenance.llm_explanation` with
`language_only=true` and `fusion_fields_overridden=false`. These fields flow
into `report_input_bundle_v1.agent_evidence_bundle.l3_composite_outputs[]` and
can be rendered by fallback or LLM report synthesis.

Non-overrides: after applying model output, the executor preserves deterministic
L3 `stance`, `confidence`, `status`, `gate`, `veto`, `penalty`, `risk_score`,
`regime`, `risk_sensitivity`, `dimension_weights`, and contributing agents. A
validator failure discards the explanation and keeps the deterministic result.

Failure behavior: invalid model names, missing known-provider credentials,
model load failure, unsafe output, non-JSON output, schema mismatch, or invalid
post-application L3 result returns the original deterministic L3 results. Known
provider credential checks short-circuit before invocation and record only
secret-free readiness metadata.

Safety rules:

- The seam must not call external agent `/v1/agent/invoke`.
- It must not store raw model output in graph state or public workflow.
- It must not change runtime bindings or live flags.
- It must not turn placeholder or partial members into complete evidence.
- It may set public workflow `providerInvoked=true` when the explicit L3
  explanation flag actually invokes the configured model.

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
R8-12C may include optional `stepResults.agent_evidence` and
`stepResults.composite_evidence` fields. They are public-safe report input
summaries only, not raw external payloads. These evidence objects may include
`domain_metrics`, `drivers`, `research_points`, `data_quality`, bounded
evidence items, and member previews when those fields were already present in
the validated `report_input_bundle_v1`.
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

## Agent Sync P2S Plan Contract

`agent_sync_plan_v1` P2S plans separate review information from future write
steps:

- `observed_diff` is explanatory B/S/P/D state and is not executable.
- `stage_materialization` describes how a future approved phase would build a
  new missing versioned sandbox baseline.
- `activation` describes future pointer-switch preconditions, post-switch
  verification, and rollback skeleton.

P2S file materialization actions must not target the active sandbox path.
Ordinary `copy_from_prod` actions require non-empty source hash, mode, file
type, source-root digest, and safe destination path. Sensitive production
source must use `preserve_sanitized_derivative` with redacted structural
fingerprint metadata or become a manual-review blocker. Baseline-local metadata
uses `preserve_sandbox_metadata`.

`p2s_approval_request.json` is only a request for future machine approval. It
is not an approval record and cannot authorize stage, activate, backup, lock,
process, endpoint, or rollback actions.

SYNC-OPS-1R2 adds recursive coverage invariants to that contract:

- inventory must recurse through registered source and support subroots while
  preserving logical-root relative paths;
- every historical baseline manifest file must receive a terminal parity
  disposition;
- every current production inventory file must receive a terminal coverage
  disposition;
- current safe source-bearing files must be materialized, preserved,
  explicitly omitted, excluded by policy, or resolved through a shared
  transaction;
- `expected_stage_projection_digest` must match a temp-only reconstruction
  before any future approval request can be used.

SYNC-OPS-2A adds write-run contracts without executing real server writes:

- `agent_sync_approval_v1` must be `status=approved` and bind exact plan SHA
  plus exact `agent_sync_environment_snapshot_v1` SHA.
- Stage, activate, and rollback booleans are independent approval capabilities.
- `agent_sync_environment_snapshot_v1` contains non-sensitive hashes and
  filesystem boundary facts only; it excludes PID, command line, endpoint
  response, credentials, and env values.
- `agent_sync_lock_v1` records global and transaction lock scopes outside the
  target tree. Stale locks are audited, not auto-deleted.
- P2S activation builds an independent candidate and verifies zero hard links
  before switching active sandbox state.
- The recovery journal records stage, candidate, archive, pointer, rollback,
  and closeout events so interrupted runs can classify resume versus rollback.

SYNC-OPS-2A-R1 adds source-selection invariants to P2S plans:

- every inventory file receives a source role before planning;
- `copy_from_prod` and `snapshot_semantic_placeholder` actions must include
  `source_category`, `source_sha256`, completed sensitive classification, file
  mode, and file type;
- `not_scanned`, sensitive, unknown, editor/local metadata, backup artifacts,
  generated artifacts, experiment results, data/model assets, and runtime
  noise cannot be materialized by ordinary copy;
- runtime static assets, test fixtures, and legacy references require explicit
  manifest evidence before materialization;
- full-scale temp rehearsal of the actual plan is required before a real
  approval request can be considered actionable.

SYNC-OPS-2A-R2 freezes the executable P2S write contract:

- P2S plans include `execution_contract` with writer contract version,
  artifact-store preflight, locks, stage, verify, activation, rollback, and
  crash-recovery sections.
- Executable P2S plans must not contain read-only planner markers or rollback
  skeleton fields.
- The first real request is stage-only: artifact-store initialization if
  required, stage, and verify. It does not authorize active sandbox archive,
  pointer update, activation, or rollback.
- Activation approval is only a template until a real stage run id, artifact
  index SHA, stage digest, validation SHA, and latest active pointer/tree are
  available.
- Plan, closeout, CLI, and terminal summaries use the same
  `agent_sync_p2s_summary_v1` object so logical materialization actions and
  physical writes are not conflated.

SYNC-OPS-2A-R3 adds a separate artifact-store bootstrap contract:

- `agent_sync_artifact_store_bootstrap_plan_v1` lists exact directory actions
  and a root metadata write. It cannot authorize wildcard parents, arbitrary
  recursive creation, chown, chgrp, setuid, or setgid.
- `agent_sync_artifact_store_bootstrap_approval_v1` binds exact bootstrap plan
  SHA, stable bootstrap environment binding SHA, and action ids.
- `STORE_METADATA.json` is the durable marker that makes the store usable by
  later P2S runs. It records the bootstrap plan id/hash and stable
  environment binding SHA used by the machine approval.
- `STORE_METADATA.json` also carries a bootstrap ownership ledger. Bootstrap
  rollback may remove only paths that ledger marks as created by the same run.
- Bootstrap rollback is preflighted and all-or-nothing. Unsafe rollback returns
  `noop_not_safe_to_remove` with zero mutations.
- Bootstrap approval requests are distinct from approvals: requests use
  `requested_action_ids`; executable approvals use `approved_action_ids`.
- P2S plans generated while the store is missing or lacks metadata use
  `execution_status=blocked_artifact_store_not_ready`; stage/verify/activate/
  rollback reject before creating run artifacts.
- Artifact-store atomic-write requirements are local to the store directory;
  sandbox activation atomic-rename requirements remain scoped to active,
  candidate, and archive paths.
- Archive artifacts must use POSIX `/` entry names and reject backslashes,
  absolute entries, traversal components, duplicate normalized entries, and
  symlink entries.

SYNC-OPS-2B0 confirms the bootstrap execution boundary:

- a machine approval is created only after the current approved environment
  binding matches the plan-bound binding SHA;
- bootstrap execution repeats that binding comparison before creating any
  directory;
- environment drift blocks execution with no machine approval, no real
  artifact-store write, and no P2S stage;
- a drifted bootstrap requires a new plan, environment binding, request, and
  machine approval.

SYNC-OPS-2A-R5 repairs the bootstrap environment model:

- `agent_sync_execution_environment_v2` separates `approval_binding`,
  `execution_constraints`, and `observations`;
- machine approval binds `environment_binding_sha256`, not exact free-space or
  diagnostic observation samples;
- free space is checked as `current_free_bytes >= minimum_free_bytes` at
  execution time;
- `access_basis=owner` binds ancestor uid/mode and operator euid while
  supplementary groups and ancestor gid remain diagnostic;
- `access_basis=group` binds the relevant gid and membership in that group;
- unmodeled POSIX ACLs block until a canonical ACL digest is added;
- root realpath/device/inode/uid/mode, path-state, symlink, action, access
  basis, and relevant group drift remain fail-closed.

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
