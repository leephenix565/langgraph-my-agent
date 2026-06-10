# Fixed DAG Agent Readiness Matrix

This document persists the Phase R8-8N read-only audit result for the fixed DAG
agent roster. It records the current readiness state of all 27 fixed DAG agents,
the controlled compute evidence that exists, the deferred/problem agents, and
the next developer actions.

This document is a developer handoff. It does not enable runtime bindings,
change active graph behavior, call external services, or mark any external
agent production-ready.

## Purpose / Scope

R8-8N audited the fixed DAG readiness state after the R8-8B through R8-8M
controlled smoke phases. The audit used repository files, readiness docs,
sanitized `/tmp/lma-r8-*` summaries, and service patch manifests as evidence.

The audit did not call:

- `/health`
- `/v1/agent/compute`
- `/v1/agent/invoke`
- provider APIs
- prod ports

The matrix below covers the full 27-agent fixed DAG roster.

## Non-Claims

- No `/v1/agent/invoke` evidence exists.
- No runtime binding was enabled.
- No `live_verified=true` flag was set.
- No `invoke_enabled_by_default=true` flag was set for external candidates.
- No active graph runtime integration was changed.
- No production readiness is claimed.
- Controlled compute evidence is not production readiness.
- `sentiment_company_radar` remains market-only and must not be routed into
  `risk_composite`.
- L3 and L4 remain deterministic seams until a separate adapter/runtime design
  phase owns them.

## Evidence Sources

Primary fixed DAG roster and runtime metadata:

- `config/fixed_dag/agent_catalog.json`
- `config/fixed_dag/runtime_bindings.json`
- `src/react_agent/fixed_dag_catalog.py`
- `src/react_agent/fixed_dag_runtime_registry.py`
- `docs/ARCHITECTURE_FIXED_DAG.md`
- `docs/CONTRACTS.md`

Controlled readiness evidence:

- `docs/CONTROLLED_READINESS_SMOKE_LOG.md`
- `docs/EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md`
- `docs/CHANGELOG.md`
- `docs/DECISIONS.md`
- `/tmp/lma-r8-8d-id-value-ml-resmoke/*/summary.json`
- `/tmp/lma-r8-8g-candidate-smoke/*/*/summary.json`
- `/tmp/lma-r8-8h-candidate-smoke/*/*/summary.json`
- `/tmp/lma-r8-8i-candidate-smoke/*/*/summary.json`
- `/tmp/lma-r8-8j-candidate-smoke/*/*/summary.json`
- `/tmp/lma-r8-8k-candidate-smoke/*/*/summary.json`
- `/tmp/lma-r8-8l-candidate-smoke/*/*/summary.json`
- `/tmp/lma-r8-8m-candidate-smoke/*/*/summary.json`
- `/tmp/lma-r8-8*-service-backup/*/service_patch_manifest.json`

The `/tmp` paths are operational evidence and backfill references. They are not
repository source of truth.

## Coverage Summary

| Metric | Count | Notes |
| --- | ---: | --- |
| Total fixed DAG agents | 27 | Catalog roster count |
| External-service candidates | 20 | L1 evidence services and L2 analysis services |
| Controlled compute pass | 14 | Health pass, compute pass, adapter mapping pass |
| Controlled compute failed | 1 | `market_ipo_investor_behavior` has unsupported compute shape |
| Deferred count | 11 | 5 external-service deferred/problem plus 6 L3/L4 deferred |
| Not attempted count | 2 | `macro_commodity_pricing`, `market_fund_manager_behavior` |
| L3/L4 deferred | 6 | 4 composites plus decision/report |
| Invoke audit candidates | 14 | Compute-pass services only |
| Service patches outside git | 13 | Must be backfilled by service owners |
| Agents needing developer backfill | 13 | Non-git service protocol patches |

Layer coverage:

| Layer/group | Coverage |
| --- | --- |
| L1 | 2/2 external evidence services pass; `route_planner` is deterministic internal |
| L2 value | 4/4 pass |
| L2 market | 3/5 pass |
| L2 risk | 4/4 pass |
| L2 macro | 1/5 pass; 4 deferred/problem |
| L3 | 0/4 external controlled compute; deterministic internal seams only |
| L4 | 0/2 external controlled compute; deterministic internal seams only |

## Passed Agents Summary

L1:

- `financial_data_service`
- `entity_relation_extractor`

L2 value:

- `value_ml_valuation`
- `value_traditional_valuation`
- `value_meta_valuation`
- `value_research_synthesis`

L2 market:

- `market_stock_technical`
- `sentiment_company_radar`
- `market_capital_flow_chip`

L2 risk:

- `risk_identification`
- `risk_compliance_review`
- `risk_financial_fraud`
- `risk_crash`

L2 macro:

- `macro_analysis`

These services are candidates for a later controlled invoke audit. They are not
live verified and must remain disabled in runtime bindings until a later phase
explicitly owns invoke and binding decisions.

## Problem / Deferred Agents Summary

| Agent | Current issue | Required next work |
| --- | --- | --- |
| `market_ipo_investor_behavior` | Protocol drift; compute shape unsupported | Add `external_agent_compute_v0.tool_result.agent_conclusion_v1` wrapper |
| `macro_commodity_pricing` | Dev port 8004 was not listening | Provide dev runbook plus structured health and compute wrapper |
| `macro_index_valuation` | Semantic owner decision needed | Do not force index/value valuation into macro |
| `macro_sentiment` | Likely L3/regulator or `macro_conclusion_v1` semantics | Classify before any L2 wrapper |
| `macro_industry_hotspot` | Same as `macro_sentiment` | Classify before any L2 wrapper |
| `market_fund_manager_behavior` | Service root, dev port, and external id unknown | Discover non-stub service metadata |
| L3 composites | External L3 adapter not designed | Keep deterministic seams until explicit L3 adapter/runtime phase |
| L4 decision/report | External L4 adapter not designed | Keep deterministic seams until explicit L4 adapter/runtime phase |

## Full 27-Agent Matrix

| agent_id | layer | dimension | expected_payload_or_contract | runtime_binding_kind | implementation_status | current_status | health_status | compute_status | adapter_mapping_status | known_issues | next_action | developer_prompt_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `route_planner` | L1 | l1 | `fixed_dag_plan_v1` | `deterministic_system` | `deterministic_skeleton` | `not_external_runtime_target` | n/a | n/a | n/a | Internal deterministic planner | Keep deterministic | `PROMPT-NONE-INTERNAL` |
| `financial_data_service` | L1 | l1 | `data_bundle_v1` | `external_http_candidate` | `external_candidate_disabled` | `controlled_compute_pass` | pass | pass | pass | Patch outside git; binding disabled | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `entity_relation_extractor` | L1 | l1 | `entity_relation_bundle_v1` | `pending_placeholder` | `pending_implementation` | `controlled_compute_pass` | pass | pass | pass | Patch outside git; binding placeholder | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `value_traditional_valuation` | L2 | value | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `controlled_compute_pass` | pass | pass | pass | Patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `value_ml_valuation` | L2 | value | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `controlled_compute_pass` | pass | pass | pass | Identity patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `value_meta_valuation` | L2 | value | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `controlled_compute_pass` | pass | pass | pass | Patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `value_research_synthesis` | L2 | value | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `controlled_compute_pass` | pass | pass | pass | Patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `market_stock_technical` | L2 | market | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `controlled_compute_pass` | pass | pass | pass | Patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `market_fund_manager_behavior` | L2 | market | `conclusion_object_v1` | `pending_placeholder` | `pending_implementation` | `service_source_unknown` | skipped | skipped | skipped | No non-stub service root, dev port, or external id found | Discover service/runbook | `PROMPT-FUND-SERVICE-DISCOVERY` |
| `market_ipo_investor_behavior` | L2 | market | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `service_patch_needed` | skipped | skipped | skipped | Unsupported scaffold/raw business compute shape | Add compute wrapper, then resmoke | `PROMPT-IPO-WRAPPER` |
| `market_capital_flow_chip` | L2 | market | `conclusion_object_v1` | `pending_placeholder` | `pending_implementation` | `controlled_compute_pass` | pass | pass | pass | Patch outside git; binding placeholder | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `sentiment_company_radar` | L2 | market | `conclusion_object_v1` | `pending_placeholder` | `pending_implementation` | `controlled_compute_pass` | pass | pass | pass | Market-only; must not enter risk | Backfill patch, then market-only invoke audit | `PROMPT-SENTIMENT-MARKET-INVOKE` |
| `risk_crash` | L2 | risk | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `controlled_compute_pass` | pass | pass | pass | Patch outside git; L2 gate-member only | Backfill patch, then invoke audit | `PROMPT-RISK-INVOKE-BACKFILL` |
| `risk_financial_fraud` | L2 | risk | `conclusion_object_v1` | `pending_placeholder` | `pending_implementation` | `controlled_compute_pass` | pass | pass | pass | Patch outside git; L2 gate-member only | Backfill patch, then invoke audit | `PROMPT-RISK-INVOKE-BACKFILL` |
| `risk_identification` | L2 | risk | `conclusion_object_v1` | `pending_placeholder` | `pending_implementation` | `controlled_compute_pass` | pass | pass | pass | Patch outside git; L2 gate-member only | Backfill patch, then invoke audit | `PROMPT-RISK-INVOKE-BACKFILL` |
| `risk_compliance_review` | L2 | risk | `conclusion_object_v1` | `pending_placeholder` | `pending_implementation` | `controlled_compute_pass` | pass | pass | pass | Patch outside git; L2 gate-member only | Backfill patch, then invoke audit | `PROMPT-RISK-INVOKE-BACKFILL` |
| `macro_analysis` | L2 | macro | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `controlled_compute_pass` | pass | pass | pass | No patch recorded | Invoke audit prep | `PROMPT-INVOKE-AUDIT` |
| `macro_commodity_pricing` | L2 | macro | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `dev_port_missing` | skipped | skipped | skipped | Dev listener missing; do not touch prod 10004 | Add dev runbook and wrapper | `PROMPT-COMMODITY-RUNBOOK` |
| `macro_index_valuation` | L2 | macro | `conclusion_object_v1` | `external_http_candidate` | `external_candidate_disabled` | `owner_confirmation_needed` | skipped | skipped | skipped | Looks index/value oriented; macro semantics unclear | Owner semantic decision | `PROMPT-MACRO-INDEX-OWNER` |
| `macro_sentiment` | L2 | macro | `conclusion_object_v1` | `pending_placeholder` | `pending_implementation` | `l3_l4_deferred` | skipped | skipped | skipped | Likely macro regulator/L3-style payload | L2 vs L3 classification | `PROMPT-MACRO-L3-DEFER` |
| `macro_industry_hotspot` | L2 | macro | `conclusion_object_v1` | `pending_placeholder` | `pending_implementation` | `l3_l4_deferred` | skipped | skipped | skipped | Likely macro regulator/L3-style payload | L2 vs L3 classification | `PROMPT-MACRO-L3-DEFER` |
| `value_composite` | L3 | composite | `dimension_composite_result_v1` | `deterministic_composite` | `deterministic_skeleton` | `l3_l4_deferred` | n/a | n/a | n/a | External L3 adapter not designed | L3 adapter design | `PROMPT-L3-ADAPTER-DESIGN` |
| `market_composite` | L3 | composite | `dimension_composite_result_v1` | `deterministic_composite` | `deterministic_skeleton` | `l3_l4_deferred` | n/a | n/a | n/a | External L3 adapter not designed | L3 adapter design | `PROMPT-L3-ADAPTER-DESIGN` |
| `risk_composite` | L3 | composite | `dimension_composite_result_v1` | `deterministic_composite` | `deterministic_skeleton` | `l3_l4_deferred` | n/a | n/a | n/a | External L3 adapter not designed; no sentiment risk input | L3 adapter design | `PROMPT-L3-ADAPTER-DESIGN` |
| `macro_composite` | L3 | composite | `dimension_composite_result_v1` | `deterministic_composite` | `deterministic_skeleton` | `l3_l4_deferred` | n/a | n/a | n/a | External L3 adapter not designed | L3 adapter design | `PROMPT-L3-ADAPTER-DESIGN` |
| `decision_synthesizer` | L4 | l4 | `decision_result_v1` | `deterministic_decision` | `deterministic_skeleton` | `l3_l4_deferred` | n/a | n/a | n/a | External L4 decision adapter not designed | L4 adapter design | `PROMPT-L4-ADAPTER-DESIGN` |
| `report_generator` | L4 | l4 | `report_result_v1` | `deterministic_report` | `deterministic_skeleton` | `l3_l4_deferred` | n/a | n/a | n/a | External L4 report adapter not designed | L4 adapter design | `PROMPT-L4-ADAPTER-DESIGN` |

## Service Patches Outside Git Inventory

These service-side patches were applied in dev service directories that were
not usable service git repositories during the smoke/remediation phases. Service
owners must backfill the same protocol changes into their own source-controlled
repositories before invoke audit or runtime binding work.

| agent_id | patch/backfill evidence |
| --- | --- |
| `value_ml_valuation` | `/tmp/lma-r8-8d-id-backup/20260610T030433Z` |
| `value_traditional_valuation` | `/tmp/lma-r8-8g-service-backup/20260610T034105Z/value_traditional_valuation` |
| `value_meta_valuation` | `/tmp/lma-r8-8h-service-backup/20260610T035804Z/value_meta_valuation` |
| `value_research_synthesis` | `/tmp/lma-r8-8h-service-backup/20260610T040157Z/value_research_synthesis` |
| `market_stock_technical` | `/tmp/lma-r8-8h-service-backup/20260610T040408Z/market_stock_technical` |
| `sentiment_company_radar` | `/tmp/lma-r8-8i-service-backup/20260610T043253Z/service_patch_manifest.json` |
| `financial_data_service` | `/tmp/lma-r8-8j-service-backup/20260610T053111Z/service_patch_manifest.json` |
| `entity_relation_extractor` | `/tmp/lma-r8-8k-service-backup/20260610T060226Z/service_patch_manifest.json` |
| `risk_identification` | `/tmp/lma-r8-8k-service-backup/20260610T060226Z/service_patch_manifest.json` |
| `risk_compliance_review` | `/tmp/lma-r8-8k-service-backup/20260610T060226Z/service_patch_manifest.json` |
| `risk_financial_fraud` | `/tmp/lma-r8-8l-service-backup/20260610T064145Z/service_patch_manifest.json` |
| `risk_crash` | `/tmp/lma-r8-8l-service-backup/20260610T064145Z/service_patch_manifest.json` |
| `market_capital_flow_chip` | `/tmp/lma-r8-8m-service-backup/20260610T072025Z/service_patch_manifest.json` |

## Next Recommended Phases

1. R8-9A: controlled `/v1/agent/invoke` audit plan only, no calls yet.
2. R8-9B: first controlled invoke smoke for a tiny allowlist, still no runtime
   binding change.
3. Service-owner backfill phase: move the 13 non-git service protocol patches
   into each service's source-controlled repository.
4. Macro cleanup phase: resolve `macro_index_valuation`, `macro_sentiment`,
   `macro_industry_hotspot`, and `macro_commodity_pricing`.
5. L3/L4 adapter design phase: define composite, decision, and report adapter
   contracts before any live runtime work.
