# CS1-C3X Source Durability And Remaining Evidence

Run UTC: 2026-06-22T10:35:01Z

Artifact root:
`/tmp/lma-cs1c3x-source-durability-20260622T103501Z`

Backup root:
`/sdb/dlut/prod/backups/cs1c3x_20260622T103501Z`

## Objective

CS1-C3X closes the macro L3 member-contract issue found after CS1-C2X,
records source durability for production wrapper changes, and captures the
remaining L1/market evidence blockers without broadening runtime scope.

## Macro Follow-Up Finding

CS1-C2X mapped `macro_composite`, but the production wrapper allowed
service-local macro business-core members to leak into fixed-DAG public
material:

- formal members:
  `macro_analysis`, `macro_commodity_pricing`, `macro_index_valuation`,
  `macro_sentiment`, `macro_industry_hotspot`
- non-canonical local stand-ins:
  `valuation_index`, `industry_hotspot`

The root cause was two-sided:

- the service wrapper merged local business-core members and evidence refs with
  fixed-DAG upstream outputs;
- the main-system adapter validated macro `contributing_agents`, but did not
  fail closed on `members`.

## Contract Closure

C3X adds fail-closed macro member validation in
`src/react_agent/fixed_dag_external_adapter.py`:

- member ids must be unique;
- member ids must be formal macro L2 ids;
- pending, partial, error, and not-available formal members must have zero
  weight if weight is present;
- Chinese names, legacy ids, and service-local aliases are rejected.

The production `macro_composite` wrapper now projects exactly five formal macro
slots. Local stand-ins may remain inside the business core as internal
diagnostics, but they are not emitted as formal members or public evidence.

The macro business fields remain unchanged: regime, dimension weights, risk
sensitivity, style bias, and industry adjustment logic were not modified.

## Production Service Changes

Changed production runtime files:

- `/sdb/dlut/prod/宏观综合智能体/service.py`
- `/sdb/dlut/prod/宏观综合智能体/tests/test_synthesis.py`
- `/sdb/dlut/prod/资金流智能体/schemas.py`
- `/sdb/dlut/prod/资金流智能体/tests/test_domain_contract_v1.py`

`market_capital_flow_chip` was a service-local contract drift closure only:
production behavior already emitted canonical `market`; local tests/schema were
updated so Chinese `市场面` remains compatibility input and is not the canonical
contract.

## Controlled Evidence

Macro live smoke:

- `GET /health`: pass, `external_agent_health_v0`
- `POST /v1/agent/compute`: pass, `external_agent_compute_v0`
- adapter: pass, `dimension_composite_result_v1`
- members:
  `macro_analysis`, `macro_commodity_pricing`, `macro_index_valuation`,
  `macro_sentiment`, `macro_industry_hotspot`

Final trace:

- default-off demo compute called/mapped: `19` / `19`
- failed agents: none
- temporal rejected agents: none
- L4 compute-default called/mapped: `2` / `2`
- report input bundle: valid
- report source: `external_compute_default_l4_report`
- PublicTurn validation: pass
- public unsafe scan before scrub: pass

The final trace does not include production `entity_relation_extractor`,
`sentiment_company_radar`, or `market_fund_manager_behavior`; those remain
blocked by source/listener/owner evidence gates.

## Source Durability

C3X generated owner review handoff patches under:

`/sdb/dlut/prod/backups/cs1c3x_20260622T103501Z/owner_handoffs`

The handoff set covers production wrapper/test drift for:

- `value_traditional_valuation`
- `value_ml_valuation`
- `value_meta_valuation`
- `risk_crash`
- `market_stock_technical`
- `macro_analysis`
- `value_composite`
- `market_ipo_investor_behavior`
- `macro_composite`
- `market_capital_flow_chip`

`market_stock_technical` has a review patch but its dry-run apply check failed
because the owner-dev file has line-ending/context drift. It must be handled by
the owner; C3X did not modify owner-dev repositories.

Durability matrix:

`/tmp/lma-cs1c3x-source-durability-20260622T103501Z/source_durability_matrix.json`

## Remaining Blockers

- `entity_relation_extractor`: production port/root evidence is not closed; dev
  8101 evidence is not production evidence.
- `sentiment_company_radar`: expected production market-only listener remains
  absent; dev listener is not production evidence.
- `market_fund_manager_behavior`: formal source/owner/endpoint identity remains
  unresolved.
- `macro_sentiment` and `macro_industry_hotspot`: remain semantic-deferred
  formal macro slots and must not be counted as real L2 evidence.

## Prod Main Stash

The C2X prod-main stash
`cs1c2x-prod-main-dirty-20260622T093703Z` was exported to the C3X artifact root
and dropped only after its helper file was verified as absorbed by current
`HEAD`. No `git reset` or `git clean` was used.

## Validation

Focused validation included:

- main adapter tests: `44 passed`
- macro service tests: `21 passed`
- capital-flow focused tests: `29 passed`
- market-composite focused tests: `23 passed`
- final controlled trace: `19` mapped demo agents, `2` mapped L4 default agents

## Non-Claims

- No `/v1/agent/invoke` call.
- No provider call.
- No `runtime_bindings.json` change.
- No live flag or invoke-default flag change.
- No model, scoring, feature, training, data-source, or fusion algorithm change.
- No owner-dev repository modification.
- No `.env` value inspected or changed.
- No raw endpoint response retained.
