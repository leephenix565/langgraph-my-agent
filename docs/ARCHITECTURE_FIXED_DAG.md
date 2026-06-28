# Fixed DAG Architecture

This document describes the active reset skeleton, the Phase R4-A fixed DAG
catalog source, the Phase R4-B runtime binding registry, the Phase R4-C legacy
registry boundary cleanup, the Phase R5-B1 frontend contract migration, and the
Phase R5-B2 workflow DAG inspector UI rewrite, the Phase R8-1 selected routing
contract foundation, the Phase R8-2 deterministic selected DAG compiler, and
the Phase R8-3 route-intent planner seam, and the Phase R8-4 RouteEval
baseline, and the Phase R8-5 default-off selected routing graph integration.
The skeleton is deterministic, provider-free, plan-driven, and backed by
explicit catalog, binding, contract, executor, and function seams. It is not a
completed business analysis engine.

M2B starts the active-core source split without changing runtime behavior:
foundational contract constants, types, labels, and public-safety helpers live
under `src/react_agent/fixed_dag/`, while
`src/react_agent/fixed_dag_contracts.py` remains the compatibility facade and
current import authority for existing callers.

M2C continues that split for executor foundations only: execution constants,
topology helpers, validation helpers, and step-result helpers live under
`src/react_agent/fixed_dag/execution/`, while
`src/react_agent/fixed_dag_executor.py` remains the compatibility facade and
current executor import authority. The runner, external compute bridge, runtime
registry, adapter, graph, and public API semantics are unchanged.

M2D splits external compute and runtime binding internals without changing
their contracts: `src/react_agent/fixed_dag/external/` owns bridge constants,
entry types, request builders, loopback transport, and payload safety helpers,
and `src/react_agent/fixed_dag/runtime/` owns runtime binding metadata,
validation, lookup, annotation, and L4 review helpers. The old
`react_agent.fixed_dag_external_compute_bridge` and
`react_agent.fixed_dag_runtime_registry` import paths remain compatibility
facades. Demo/default runtime behavior, `/v1/agent/compute` only enforcement,
runtime binding JSON, graph topology, and public API semantics are unchanged.

M2E completes the executor runner boundary: `execute_fixed_dag_plan` and its
runner-local orchestration helpers live in
`src/react_agent/fixed_dag/execution/runner.py`, while
`src/react_agent/fixed_dag_executor.py` remains the compatibility facade and
current executor import authority. Execution order, report precedence,
external compute demo/default semantics, graph topology, and public API
semantics are unchanged.

M3B adds `src/react_agent/compat/context_state.py` as metadata-only support for
the retained Context/State compatibility boundary. The active graph still reads
and writes the same State fields, compatibility pools remain available, and no
Context dataclass field, State TypedDict field, reducer, runtime shape, graph
topology, or public API contract changes.

REPO-CONSOLIDATION-FINAL records this package organization as complete for the
theme. The old fixed-DAG facades remain supported import surfaces, M4A found no
P4 deletion candidates, and no runtime/config/schema behavior changes are part
of the closeout.

## Active Skeleton Flow

```mermaid
flowchart TD
    A["user input"] --> B["route_planner"]
    B --> C["prepare_l1_context"]
    C --> D["execute_fixed_dag"]
    D --> E["topological execution batches"]
    E --> F["fixed_dag_step_result_v1 per step"]
    F --> G["L2 conclusions, L3 composites, L4 decision/report"]
    G --> H["single assistant transcript"]
```

The formal reset roster has 27 agent ids. The DAG executor itself is
infrastructure and is not counted as an agent id.

The active catalog source is `config/fixed_dag/agent_catalog.json`, loaded and
validated by `src/react_agent/fixed_dag_catalog.py`. The source workbook
`新架构_固定DAG_最终分层级智能体表_v4_反馈修正版.xlsx` is retained as the
R4 baseline input.

The active runtime binding source is `config/fixed_dag/runtime_bindings.json`,
loaded and validated by `src/react_agent/fixed_dag_runtime_registry.py`. It maps
the same 27 target ids to deterministic seams, disabled external HTTP
candidates, or pending placeholders. The binding registry does not change the
DAG topology and does not enable external invocation.

POST-BF-B2X adds a production non-L4 external compute policy that is separate
from runtime bindings:
`config/fixed_dag/non_l4_external_compute_policy.json`. The policy is loaded
and validated by `src/react_agent/fixed_dag_non_l4_runtime_registry.py`, and
the executor uses `src/react_agent/fixed_dag_production_external_compute.py` to
overlay the approved non-L4 `/v1/agent/compute` results. This path does not
modify `runtime_bindings.json`, does not use demo URL overrides, and does not
call `/v1/agent/invoke`. The current policy is `enabled_by_default=true` for
the required ids `value_traditional_valuation`, `value_ml_valuation`,
`value_meta_valuation`, `market_ipo_investor_behavior`,
`market_capital_flow_chip`, `risk_crash`, `macro_analysis`,
`macro_index_valuation`, and `value_composite`. RQ3A adds optional enabled
coverage rows for `value_research_synthesis`, `market_stock_technical`,
`sentiment_company_radar`, `risk_financial_fraud`, `risk_identification`,
`risk_compliance_review`, `macro_commodity_pricing`, `market_composite`,
`risk_composite`, and `macro_composite`. Rollback uses
`DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT` without changing runtime bindings.
RQ3B does not change that policy; it only lets the adapter accept a partial
`risk_composite` when a non-contributing risk member is excluded from weighted
evidence and preserved as a coverage limitation. RQ3C keeps the same adapter
boundary and filters `risk_composite` evidence references that still point at
non-contributing members before final L3 validation; the filtered references
are preserved only as coverage-limit metadata.

## Target IDs

| target_id | runtime layer | dimension | role |
| --- | --- | --- | --- |
| route_planner | L1 | planning | fixed DAG plan seam |
| financial_data_service | L1 | evidence | financial data bundle seam |
| entity_relation_extractor | L1 | evidence | entity and relation extraction seam |
| value_traditional_valuation | L2 | value | traditional valuation conclusion |
| value_ml_valuation | L2 | value | ML valuation conclusion |
| value_meta_valuation | L2 | value | meta valuation conclusion |
| value_research_synthesis | L2 | value | analyst research synthesis conclusion |
| market_stock_technical | L2 | market | stock technical conclusion |
| market_fund_manager_behavior | L2 | market | fund manager behavior conclusion |
| market_ipo_investor_behavior | L2 | market | IPO investor behavior conclusion |
| market_capital_flow_chip | L2 | market | capital flow and chip conclusion |
| sentiment_company_radar | L2 | market | company sentiment conclusion |
| risk_crash | L2 | risk | crash risk conclusion |
| risk_financial_fraud | L2 | risk | financial fraud risk conclusion |
| risk_identification | L2 | risk | risk identification conclusion |
| risk_compliance_review | L2 | risk | compliance review conclusion |
| macro_analysis | L2 | macro | macro analysis conclusion |
| macro_commodity_pricing | L2 | macro | commodity pricing conclusion |
| macro_index_valuation | L2 | macro | index valuation conclusion |
| macro_sentiment | L2 | macro | macro sentiment conclusion |
| macro_industry_hotspot | L2 | macro | industry hotspot conclusion |
| value_composite | L3 | value | value dimension composite |
| market_composite | L3 | market | market dimension composite |
| risk_composite | L3 | risk | risk dimension composite |
| macro_composite | L3 | macro | macro dimension composite |
| decision_synthesizer | L4 | decision | deterministic fallback plus active compute-only `external_compute_default` binding |
| report_generator | L4 | report | deterministic fallback plus active compute-only `external_compute_default` binding |

The company sentiment radar output route is `market_composite` only. Generic
event flags may still exist in conclusion contracts, but the radar is not a
direct `risk_composite` input in this v4 feedback-aligned roster.

## Execution Principles

- The DAG executor is infrastructure and is not counted as a target id.
- `fixed_dag_agent_catalog_v1` is the active roster/catalog source for reset
  backend projection.
- `fixed_dag_runtime_bindings_v1` is the active backend runtime binding
  metadata source. Catalog ids, runtime binding ids, and executor step agent ids
  must match exactly.
- `fixed_dag_plan_v1.dag_steps[].depends_on` is the executor input.
- `validate_dag_steps` checks unique ids, dependency existence, acyclicity,
  stage/dimension legality, roster membership, and dimension dependency rules.
- `topological_batches` groups ready steps into deterministic
  `execution_batches`.
- Each walked step records a `fixed_dag_step_result_v1` placeholder annotated
  with binding metadata such as runtime kind and implementation status.
- The executor output is `fixed_dag_execution_v1` and feeds
  `workflow_snapshot_v2`.
- L1 prepares the plan, entity/relation bundle, and financial data bundle through
  deterministic constructors and validators.
- L2 produces normalized pending conclusion objects with `as_of`, `data_as_of`,
  optional generic `event_flags`, and no live invocation claims.
- L3 produces deterministic dimension composites from available L2 outputs.
  Value and market use confidence-weighted direction material, risk uses only
  risk-member `risk_score` material, and macro keeps default value/market
  weights unless usable macro members exist. Missing placeholder members remain
  weight `0` and keep the composite `partial` or `pending_implementation`.
- A default-off L3 explanation seam may run after deterministic L3 construction
  and before L4 decision/report generation. It can add public-safe Chinese
  `research_points` and `provenance.llm_explanation` to L3 outputs, but it must
  not change fusion fields such as `stance`, `confidence`, `gate`, `risk_score`,
  `dimension_weights`, member weights, status, or contributing agents.
- L4 builds deterministic decision and report fallback outputs with stable
  fields, then the active R8-13Q runtime may overlay them through the two L4
  `external_compute_default` runtime bindings. Only `decision_synthesizer` and
  `report_generator` use that runtime kind; both target production-source
  `/v1/agent/compute` ports `10025`/`10026`, do not call `/v1/agent/invoke`,
  and can be disabled for rollback/tests through
  `disable_external_compute_default`. The older default-off external compute
  demo bridge remains a separate controlled/demo path and is not
  `runtime_bindings.json` authority.
- Public output remains a single assistant answer.
- R3 placeholders use `status=pending_implementation` until real business
  implementations replace them.
- R4-A owns the fixed DAG catalog source and `/api/agents` public projection.
- R4-B owns the runtime binding registry and offline external endpoint mapping
  metadata.
- R4-C owns active import boundary cleanup: legacy `AGENT_METADATA`,
  `AGENT_TOOLS`, placeholder bootstrap, and `config/agents` metadata are
  explicit compatibility/migration inputs, not active fixed-DAG runtime truth.
- Active `react_agent.graph` imports must not load `legacy_agent_registry`,
  `graph_bootstrap`, default agents, generic agents, or external HTTP wrapper
  implementation modules.
- R5-B1 owns frontend contract alignment with `workflow_snapshot_v2`.
- R5-B2 owns frontend workflow inspector rendering over the same public
  snapshot.
- R6 owns mainline/fusion-gate rebuild.
- R8-1 owns selected routing contracts only: `route_intent_v1` and
  `selected_fixed_dag_plan_v1` are additive validator seams for future
  controlled dynamic routing.
- R8-2 owns deterministic selected DAG compilation and selected executor
  validation helpers without changing the active graph default.
- R8-3 owns provider-free planner seam preparation: deterministic/mock route
  intent construction, a future route-intent prompt contract, and parser
  normalization into `route_intent_v1` without changing the active graph
  default.
- R8-4 owns provider-free RouteEval baseline coverage for `route_intent_v1`
  selection quality without changing the active graph default.
- R8-5 owns default-off selected routing graph integration through explicit
  context/env flagging while preserving the full DAG default.
- Router M1A owns default-off internal dimension routing: selected routing can
  use a provider-free dimension-only intent, while the compiler expands
  dimensions into concrete agents deterministically.
- Router M1D owns the fake-provider-only internal LLM dimension-router seam:
  a separate provider-router flag defaults false, is gated behind selected
  routing, parses fake structured output immediately, and keeps real provider
  integration for a later controlled phase.
- Router M1F0 owns the router-only provider preflight factory and artifact
  safety wrapper for a future controlled real-provider dry-run. It is
  fail-closed, creates no model client, reads no env values, and does not enter
  the active graph runtime path.

## R8-1 Selected Routing Contract Boundary

The active graph still uses `build_default_fixed_dag_plan`,
`validate_fixed_dag_plan`, and the full 27-agent `fixed_dag_plan_v1` path. R8-1
does not change `src/react_agent/graph.py`, the executor default behavior, the
fixed DAG catalog, runtime bindings, public workflow mapping, or the web UI.

R8-1 adds two contract-level shapes in `fixed_dag_contracts.py`:

- `route_intent_v1`: a planner intent contract. It records `task_type`,
  `targets`, `selected_dimensions`, `selected_agents`, `task_brief_by_agent`,
  `route_confidence`, clarification/fallback fields, and provenance. It is not
  executable DAG state.
- `selected_fixed_dag_plan_v1`: a future compiler output target. It can contain
  fewer than 27 steps and a subset of dimensions, but selected dimensions,
  selected agents, omitted dimensions, omitted agents, targets, stages, steps,
  and DAG steps must reconcile.

Policy gates are deliberately conservative:

- selected plans may omit dimensions, but omissions must be explicit;
- `report_generator` is always required for selected plans;
- investment-judgment task types require the risk dimension and
  `decision_synthesizer`;
- pure general, macro, or sentiment tasks may omit risk and decision;
- invalid selected contracts fall back to the full DAG path in later compiler
  work;
- the LLM, if added later, must not generate raw dependencies, runtime binding
  changes, external invocation flags, or legacy route-mode dispatch.

## R8-2 Deterministic Selected DAG Compiler

R8-2 implements `compile_selected_fixed_dag_plan` as a deterministic compiler
from `route_intent_v1` to `selected_fixed_dag_plan_v1`. It does not call an LLM,
provider, search backend, or external service.

Compiler behavior:

- validates `route_intent_v1` before compilation;
- treats `route_intent_v1` as planner intent, not executable DAG state;
- starts from selected dimensions and selected business agents;
- adds `route_planner`, `financial_data_service`, and
  `entity_relation_extractor`;
- keeps only selected L2 agents and gives them the fixed evidence dependencies;
- adds a selected dimension composite when that dimension has selected L2
  agents;
- sets composite `target_ids` and dependencies to selected same-dimension L2
  agents only;
- adds `decision_synthesizer` for investment-judgment task types;
- always includes `report_generator`;
- makes `report_generator` depend on `decision_synthesizer` when present, or on
  selected dimension composites otherwise;
- records omitted dimensions and omitted agents explicitly.

Executor-side selected validation is available through
`validate_selected_dag_steps` and `topological_batches_for_selected_plan`. The
selected path validates identity, dependency existence, stage order, acyclicity,
selected dimension composite dependencies, selected decision/report
dependencies, and the sentiment market-only boundary without requiring the full
27-agent DAG.

The active graph still uses the full `fixed_dag_plan_v1` path. R8-2 does not
modify `src/react_agent/graph.py`, public workflow mapping, frontend rendering,
the fixed DAG catalog, runtime bindings, or the runtime registry. R8-4 owns
RouteEval. R8-5 owns the default-off graph boundary for selected routing;
external adapter readiness remains later work.

## R8-3 Route Intent Planner Seam

R8-3 adds the planner seam that prepares `route_intent_v1` before deterministic
selected compilation. It does not call an LLM, provider, search backend, or
external service, and it does not make selected routing the active graph
default.

Planner seam behavior:

- `build_default_route_intent` builds a provider-free deterministic/mock route
  intent for tests and future feature-flag experiments;
- `build_default_dimension_route_intent` builds the M1A provider-free
  dimension-only route intent used by the default-off graph seam;
- M1D adds a fake-provider-only graph seam for later LLM routing. It accepts
  only dimension-only `route_intent_v1` JSON from injected fake providers,
  parses it immediately, and discards the raw output before state or workflow
  projection;
- M1F0 adds `src/react_agent/router_provider.py` as the future real-provider
  preflight boundary. It stores only provider policy booleans, env var names,
  bounded call options, factory/preflight results, and sanitized artifact
  metadata. It does not call `load_chat_model`, create a model client, read env
  values, or invoke providers;
- `FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT` defines the future LLM or semantic
  planner contract and targets `route_intent_v1` only; in M1A it asks only for
  `selected_dimensions` and forbids concrete agent ids;
- `build_route_intent_prompt` renders that prompt with a fixed DAG catalog
  summary without invoking any provider;
- `parse_route_intent_json` extracts provider-style JSON, filters unknown
  agents when valid selected agents remain, and fail-softs to a clarification
  intent for invalid or unsafe shapes;
- `normalize_route_intent` converts mapping-like planner output into
  `route_intent_v1` or a public-safe fallback intent;
- parser and validator guards reject executable DAG fields, dependency fields,
  runtime binding fields, removed ids, legacy numbered ids, selected
  sentiment-to-risk misuse, investment intents without risk, and live invocation
  claims.

The selected compiler remains the only path from route intent to selected DAG.
R8-3 does not modify `src/react_agent/graph.py`, public workflow mapping,
frontend rendering, the fixed DAG catalog, runtime bindings, or the runtime
registry. A later phase must explicitly connect and validate active selected
routing before runtime behavior changes.

## R8-4 RouteEval Baseline

R8-4 adds RouteEval as an offline deterministic evaluation seam for
`route_intent_v1`. It evaluates planner/parser output as intent selections,
not as executable DAGs and not as old route-mode dispatch.

RouteEval behavior:

- loads a small JSONL gold set from `tests/fixtures/route_eval_gold.jsonl`;
- evaluates task type, targets, selected dimensions, selected agents,
  clarification, and fallback behavior;
- reports dimension and agent precision, recall, F1, over-selection, and
  under-selection;
- treats `acceptable_extra_agents` as non-penalized extras;
- treats `must_not_agents` as false positives when predicted;
- penalizes sentiment-to-risk mistakes through the market-only gold cases;
- does not evaluate legacy route-mode dispatch accuracy;
- does not call an LLM, provider, search backend, external service, demo stack,
  or fusion-gate.

The first gold set is intentionally small and deterministic. It is not the
future formal Route F1 acceptance suite and does not imply an 80% routing
quality threshold. The active graph still uses the full `fixed_dag_plan_v1`
path until a later phase explicitly connects selected routing behind a
validated runtime boundary.

## R8-5 Default-Off Selected Routing Graph Integration

R8-5 wires the selected route-intent and deterministic compiler pipeline into
`src/react_agent/graph.py` without changing default behavior.

Runtime behavior:

- `Context.enable_selected_routing` defaults to `False`;
- `ENABLE_SELECTED_ROUTING=1` can enable the same flag through the existing
  boolean env parser;
- default graph invocations still build and execute the full
  `fixed_dag_plan_v1`;
- selected graph invocations use provider-free
  `build_default_dimension_route_intent`;
- the route intent is compiled by `compile_selected_fixed_dag_plan`;
- M1A route intent is dimension-only: planner output may select only `value`,
  `market`, `risk`, and `macro`; concrete L2/L3/L4 agents are expanded by the
  deterministic compiler from current catalog/constants;
- selected plans execute through `validate_selected_dag_steps` and
  `topological_batches_for_selected_plan`;
- selected L2 conclusions, dimension composites, step results, and
  `workflow_snapshot_v2` are projected as selected subsets;
- `workflow_snapshot_v2.provenance` may expose selected-routing summary fields
  (`selectedRoutingRequested`, `selectedRoutingFallback`, `fallbackReason`,
  `routeGranularity`, `selectedDimensions`, `expandedAgentCount`) without raw
  provider/LLM output, prompts, endpoints, secrets, or chain-of-thought;
- M1D adds a separate default-false fake provider-router flag
  (`Context.enable_llm_dimension_router` / `ENABLE_LLM_DIMENSION_ROUTER=1`).
  The flag is effective only when selected routing is also enabled. Selected
  routing alone continues to use the provider-free M1A path; the provider flag
  alone keeps the full DAG and records `selected_routing_disabled` without
  invoking the fake seam;
- when both flags are enabled and an injected fake provider returns valid
  dimension-only JSON, the graph parses it through
  `parse_dimension_route_intent_json`, compiles the deterministic selected
  plan, and exposes only bounded public-safe metadata such as provider-router
  enabled/invoked, mode `fake`, parse status, selected dimensions, and fallback
  reason;
- malformed provider text, markdown/code fences, forbidden fields,
  `selected_agents`, unknown dimensions, legacy named route modes,
  low confidence, clarification requests, exceptions, timeouts, or unavailable
  fake providers fall back to the full DAG with safe reason codes;
- M1F0 adds a router-only preflight factory/wrapper for future real-provider
  use. It requires selected routing, the LLM dimension-router flag, explicit
  real-provider authorization, explicit env-value access authorization,
  explicit provider-call authorization, call cap `1`, streaming `false`, retry
  `0`, timeout `<=8s`, max tokens `<=220`, whitelist-enabled artifacts, no raw
  response retention, and no prompt/message retention before it reports a
  future single-call dry-run as ready. Even then, M1F0 returns a deferred
  factory result and does not create a provider client;
- M1F0 artifact safety is allowlist-only and rejects or omits raw responses,
  raw response hashes, prompts, messages, endpoint/base URL material, env
  values, secrets, tracebacks, chain-of-thought, `selected_agents`,
  `runtime_bindings`, `dag_steps`, and `depends_on`;
- M1F3 adds pure compatibility helpers to the same router-only wrapper:
  provider-prefixed router model ids such as `provider/model` can be normalized
  to the provider API model id for OpenAI-compatible HTTP clients, and the
  future real-provider request contract requires JSON object response format
  for dimension-only `route_intent_v1` output. These helpers do not create
  clients, read env values, call providers, store prompts/messages, or retain
  raw responses;
- compile or selected validation failure falls back to the full DAG with
  public-safe fallback provenance.

R8-5/M1A/M1D/M1F0/M1F3 do not call a real LLM/provider, search backend, external
`/v1/agent/invoke`, `/health`, or runtime binding adapter. M1D and M1F0 do not
invoke `load_chat_model`, and M1F3 keeps that boundary. These phases do not
read provider credentials, change the fixed DAG roster, runtime bindings,
RouteEval threshold policy, external adapter readiness, or real business-agent
implementation status. M1A, M1D, M1F0, and M1F3 add only public-safe
selected-routing/provider-router metadata and safety contracts; they do not
create an external router service, assign ports, copy scaffold material, move
`report_generator` from port `10026`, or promote the `10028/8028` planning
reservation to runtime authority.
