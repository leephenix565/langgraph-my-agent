# POST-BF-B2X Non-L4 Runtime Activation And Release

POST-BF-B2X closes the agent integration and productionization topic by adding
a production non-L4 `/v1/agent/compute` orchestration path for the normal
fixed-DAG Web/API runtime.

## Frozen Backfill Status

Sandbox-to-prod backfill remains closed:

- total change units: `31`
- completed change units: `31`
- incomplete change units: `0`
- completion ratio: `1.0`

This phase does not reopen backfill and does not change owner-dev durability
status.

## Runtime Decision

The phase implements a dedicated production non-L4 orchestration path:

- policy source: `config/fixed_dag/non_l4_external_compute_policy.json`
- loader/validator: `src/react_agent/fixed_dag_non_l4_runtime_registry.py`
- executor orchestration: `src/react_agent/fixed_dag_production_external_compute.py`

It is not the demo bridge and is not the L4 `external_compute_default` runtime
binding path. `config/fixed_dag/runtime_bindings.json` remains unchanged and
still contains only the two L4 compute-default rows.

Demo mode and production non-L4 mode are mutually exclusive. When
`enable_external_compute_demo=True`, production non-L4 orchestration is
suppressed for that run.

Rollback is independent from L4:

```text
DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT=1
```

closes only the non-L4 production orchestration. It does not disable
`decision_synthesizer` or `report_generator`.

## Activated Agents

Required production non-L4 agents:

- `value_traditional_valuation`
- `value_ml_valuation`
- `value_meta_valuation`
- `market_ipo_investor_behavior`
- `market_capital_flow_chip`
- `risk_crash`
- `macro_analysis`
- `macro_index_valuation`
- `value_composite`

Optional degraded canary passed and is enabled:

- `macro_composite`

Normal product default external counts after this phase:

- L1 external default: `0`
- L2 external default: `8`
- L3 external default: `2`
- L4 external default: `2`
- total external default: `12`

L1 still uses local deterministic fallback for `financial_data_service` and
`entity_relation_extractor`.

## Excluded Agents

Excluded from this activation set:

- data dependency: `entity_relation_extractor`, `sentiment_company_radar`
- pending semantics: `market_fund_manager_behavior`, `macro_sentiment`,
  `macro_industry_hotspot`
- source/activation not approved in B1X: `financial_data_service`,
  `value_research_synthesis`, `market_stock_technical`,
  `risk_financial_fraud`, `risk_identification`, `risk_compliance_review`,
  `macro_commodity_pricing`, `market_composite`, `risk_composite`

Exclusion here means "not production-default activated in this wave"; it does
not mean the service is removed or backfill-incomplete.

## Execution Semantics

The executor keeps the current fixed-DAG ordering:

1. build and validate the fixed DAG plan;
2. build local deterministic L1 bundles;
3. run production non-L4 L2 overlay when demo is off and rollback is off;
4. rebuild deterministic L3 from final L2 outputs;
5. run production non-L4 L3 overlay for enabled composites;
6. run existing L4 external compute default;
7. build report and public output.

L2 uses stage-bounded concurrency, with default max concurrency `4`. L3 uses
default max concurrency `2`. Results are merged in catalog/DAG order, not
completion order, and each agent is called at most once per run.

Required failures fail soft to current deterministic/pending contracts. Optional
failures fail soft to deterministic L3 fallback. Final answer emission must not
depend on every external service succeeding.

## Public Boundary

`externalInvoked` remains the existing public no-`/invoke` claim. External
`/compute` activity is recorded in private provenance fields such as:

- `production_external_compute_called_agents`
- `production_external_compute_mapped_agents`
- `production_external_compute_failed_agents`
- `production_external_compute_latency_ms_by_agent`
- `external_compute_default_called_agents`

Public workflow objects must not include endpoint URLs, ports, PID/cwd,
headers, raw responses, credentials, traceback, or internal reasoning.

## Validation Summary

Development canary used production policy with demo disabled and provider
disabled. The final policy maps:

- non-L4 called/mapped: `10/10`
- L4 called/mapped: `2/2`
- demo called: `0`
- provider calls: `0`
- invoke calls: `0`

Optional `macro_composite` canary passed twice as a partial macro result with
five canonical formal member slots. Pending macro members keep zero-weight
coverage and are not counted as complete evidence.

## Non-Claims

This phase does not:

- call `/v1/agent/invoke`;
- call providers;
- modify `runtime_bindings.json`;
- set `live_verified=true`;
- set `invoke_enabled_by_default=true`;
- enable demo bridge as a production implementation;
- modify database schema or data;
- change model, scoring, feature, training, or fusion algorithms;
- modify owner-dev repositories;
- inspect or change `.env` values.

## Topic Closure

If the release closeout artifacts record successful prod normal-path canary and
rollback validation, the `agent_integration_and_productionization` topic is
closed. Remaining work becomes separate backlog:

- excluded-source owner closure;
- entity/sentiment data readiness;
- fund-manager semantics;
- macro sentiment/hotspot implementation;
- owner durability.
