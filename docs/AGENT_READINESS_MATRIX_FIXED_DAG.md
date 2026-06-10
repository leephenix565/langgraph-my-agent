# Fixed DAG Agent Readiness Matrix

This document is the production-first readiness matrix for the fixed DAG agent
roster after Phase R8-8P: Production Endpoint Readiness Rebaseline.

R8-8P rebaselines readiness against confirmed production endpoints. Earlier
R8-8G/H/I/J/K/L/M controlled smoke results used dev endpoints and are now
historical evidence only. Dev evidence remains useful for debugging, service
owner backfill, and wrapper design, but it must not be counted as production
readiness.

## Scope

R8-8P tested only confirmed production endpoints on `127.0.0.1` production
ports or marked production services as missing/deferred. The phase called:

- `GET /health`
- `POST /v1/agent/compute`

The phase did not call `/v1/agent/invoke`.

Production smoke artifact root:

```text
/tmp/lma-r8-8p-prod-readiness/20260610T104456Z
```

## Non-Claims

- No `/v1/agent/invoke` was called.
- No runtime binding was enabled.
- No `live_verified=true` flag was set.
- No `invoke_enabled_by_default=true` flag was set.
- No production endpoint compute pass implies production default invocation.
- No public transcript was updated with raw external output.
- No production service code was modified.
- No production service was started, stopped, or restarted.
- Dev-only evidence is historical and cannot be promoted to production
  evidence.
- `sentiment_company_radar` remains market-only and must not be routed into
  `risk_composite`.
- L3 and L4 remain deterministic seams until a separate adapter/runtime design
  phase owns them.

## Production Coverage Summary

| Metric | Count | Notes |
| --- | ---: | --- |
| Total fixed DAG agents | 27 | Full catalog roster |
| External-service candidates | 20 | L1 evidence services and L2 analysis services |
| Production endpoint known | 18 | Confirmed production listener or production port/cwd |
| Production health pass | 14 | `/health` returned structured JSON and no unsafe content |
| Production compute pass | 13 | `/v1/agent/compute` returned HTTP 2xx structured JSON |
| Production adapter mapping pass | 5 | Mapped through main-system provider-free adapter |
| Production failed/deferred | 13 | Failed health/compute/identity/semantic gates |
| Production endpoint missing | 2 | No confirmed production endpoint |
| Production semantic deferred | 3 | Not safe to force into L2 production mapping |
| Production identity mismatch | 8 | Compute returned service/unknown primary id instead of fixed DAG id |
| Internal deterministic | 1 | `route_planner` |
| L3/L4 deferred | 6 | 4 composites plus decision/report |
| Invoke audit candidates | 5 | Based only on production health + compute + adapter mapping pass |

Layer coverage:

| Layer/group | Production coverage |
| --- | --- |
| L1 | 0/2 production adapter pass; one health failure and one endpoint missing |
| L2 value | 0/4 production adapter pass; all four are identity mismatches |
| L2 market | 0/5 production adapter pass; three identity/missing issues, one semantic/missing, no pass |
| L2 risk | 4/4 production adapter pass |
| L2 macro | 1/5 production adapter pass; remaining macro candidates failed or were deferred |
| L3 | 0/4 external production readiness; deterministic internal seams only |
| L4 | 0/2 external production readiness; deterministic internal seams only |

## Production Pass Agents

These agents have production `/health` pass, production `/v1/agent/compute`
pass, and provider-free adapter mapping pass:

- `risk_identification`
- `risk_compliance_review`
- `risk_financial_fraud`
- `risk_crash`
- `macro_analysis`

These five are candidates for a later production invoke audit planning phase.
They are not live verified and must not be enabled by default.

## Production Failed / Deferred Agents

| Agent | Failure code/status | Reason | Owner/developer action | Prompt |
| --- | --- | --- | --- | --- |
| `financial_data_service` | `production_health_failed` / `health_invalid_json` | Production `/health` did not return safe structured JSON | Fix production health contract, then production resmoke | `PROMPT-PROD-HEALTH-FIX` |
| `entity_relation_extractor` | `production_endpoint_missing` | No confirmed production endpoint | Deploy/register production endpoint | `PROMPT-PROD-BACKFILL-DEV-PATCH` |
| `value_traditional_valuation` | `production_identity_mismatch` / `unknown_agent_id` | Production compute did not emit fixed DAG primary id | Backfill dev identity patch and redeploy | `PROMPT-PROD-IDENTITY-FIX` |
| `value_ml_valuation` | `production_identity_mismatch` / `unknown_agent_id` | Production compute did not emit fixed DAG primary id | Backfill dev identity patch and redeploy | `PROMPT-PROD-IDENTITY-FIX` |
| `value_meta_valuation` | `production_identity_mismatch` / `unknown_agent_id` | Production compute did not emit fixed DAG primary id | Backfill dev identity patch and redeploy | `PROMPT-PROD-IDENTITY-FIX` |
| `value_research_synthesis` | `production_identity_mismatch` / `unknown_agent_id` | Production compute did not emit fixed DAG primary id | Backfill dev identity patch and redeploy | `PROMPT-PROD-IDENTITY-FIX` |
| `market_stock_technical` | `production_identity_mismatch` / `unknown_agent_id` | Production compute did not emit fixed DAG primary id | Backfill dev identity patch and redeploy | `PROMPT-PROD-IDENTITY-FIX` |
| `market_fund_manager_behavior` | `production_identity_mismatch` / `unknown_agent_id` | Production subservice exists, but output identity is not fixed DAG compatible | Confirm service ownership/id and fix wrapper | `PROMPT-PROD-FUND-SERVICE-DISCOVERY` |
| `market_ipo_investor_behavior` | `production_identity_mismatch` / `unknown_agent_id` | Production compute remains incompatible with fixed DAG primary id | Add production compute wrapper | `PROMPT-PROD-IPO-WRAPPER` |
| `market_capital_flow_chip` | `production_identity_mismatch` / `unknown_agent_id` | Production compute did not emit fixed DAG primary id | Backfill dev patch and redeploy | `PROMPT-PROD-IDENTITY-FIX` |
| `sentiment_company_radar` | `production_endpoint_missing` | No confirmed production endpoint | Deploy/register market-only production endpoint | `PROMPT-PROD-BACKFILL-DEV-PATCH` |
| `macro_commodity_pricing` | `production_health_pass_compute_failed` / `compute_http_error` | Production health passed but compute failed | Fix production compute wrapper/runbook | `PROMPT-PROD-COMMODITY-RUNBOOK` |
| `macro_index_valuation` | `production_semantic_deferred` | Macro L2 semantics still need owner confirmation | Do not force index/value valuation into macro | `PROMPT-PROD-MACRO-INDEX-OWNER` |
| `macro_sentiment` | `production_semantic_deferred` | Production listener is placeholder/L3-regulator-like, not safe L2 | Classify L2 vs macro L3 payload | `PROMPT-PROD-MACRO-L3-DEFER` |
| `macro_industry_hotspot` | `production_semantic_deferred` | Production listener is placeholder/L3-regulator-like, not safe L2 | Classify L2 vs macro L3 payload | `PROMPT-PROD-MACRO-L3-DEFER` |

## Full 27-Agent Production Matrix

| agent_id | layer | dimension | expected_payload_or_contract | production_endpoint | production_service_root | production_health_status | production_compute_status | production_adapter_mapping_status | production_status | dev_historical_status | known_issues | next_action | developer_prompt_id | artifact_path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `route_planner` | L1 | l1 | `fixed_dag_plan_v1` | n/a | n/a | n/a | n/a | n/a | `production_internal_deterministic` | deterministic internal | Internal planner, not external service | Keep deterministic | n/a | n/a |
| `financial_data_service` | L1 | l1 | `data_bundle_v1` | `127.0.0.1:11000` | `/sdb/dlut/prod/金融数据服务智能体/pg-ops-agent/backend` | fail | skipped | skipped | `production_health_failed` | dev pass after remediation | Production `/health` invalid JSON | Production health fix and resmoke | `PROMPT-PROD-HEALTH-FIX` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/financial_data_service` |
| `entity_relation_extractor` | L1 | l1 | `entity_relation_bundle_v1` | missing | unknown | skipped | skipped | skipped | `production_endpoint_missing` | dev pass after remediation | No confirmed production endpoint | Production deploy/register then resmoke | `PROMPT-PROD-BACKFILL-DEV-PATCH` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/entity_relation_extractor` |
| `value_traditional_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10000` | `/sdb/dlut/prod/传统企业估值智能体` | pass | pass | fail | `production_identity_mismatch` | dev pass after remediation | `unknown_agent_id`; production patch not backfilled | Backfill identity wrapper and redeploy | `PROMPT-PROD-IDENTITY-FIX` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/value_traditional_valuation` |
| `value_ml_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10001` | `/sdb/dlut/prod/机器学习企业估值智能体` | pass | pass | fail | `production_identity_mismatch` | dev pass after identity remediation | `unknown_agent_id`; production patch not backfilled | Backfill identity wrapper and redeploy | `PROMPT-PROD-IDENTITY-FIX` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/value_ml_valuation` |
| `value_meta_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10002` | `/sdb/dlut/prod/元学习企业估值智能体` | pass | pass | fail | `production_identity_mismatch` | dev pass after remediation | `unknown_agent_id`; production patch not backfilled | Backfill identity wrapper and redeploy | `PROMPT-PROD-IDENTITY-FIX` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/value_meta_valuation` |
| `value_research_synthesis` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10006` | `/sdb/dlut/prod/分析师研报与观点集成智能体` | pass | pass | fail | `production_identity_mismatch` | dev pass after remediation | `unknown_agent_id`; production patch not backfilled | Backfill identity wrapper and redeploy | `PROMPT-PROD-IDENTITY-FIX` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/value_research_synthesis` |
| `market_stock_technical` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10009` | `/sdb/dlut/prod/个股技术分析智能体` | pass | pass | fail | `production_identity_mismatch` | dev pass after remediation | `unknown_agent_id`; production patch not backfilled | Backfill identity wrapper and redeploy | `PROMPT-PROD-IDENTITY-FIX` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/market_stock_technical` |
| `market_fund_manager_behavior` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10007` | `/sdb/dlut/prod/市场面综合智能体/subagents/fund_manager_behavior` | pass | pass | fail | `production_identity_mismatch` | no dev pass | Production subservice exists but id/wrapper not fixed DAG compatible | Confirm service ownership and wrapper | `PROMPT-PROD-FUND-SERVICE-DISCOVERY` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/market_fund_manager_behavior` |
| `market_ipo_investor_behavior` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10008` | `/sdb/dlut/prod/市场面综合智能体` | pass | pass | fail | `production_identity_mismatch` | dev failed/skipped | Production output still not fixed DAG compatible | Add production wrapper | `PROMPT-PROD-IPO-WRAPPER` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/market_ipo_investor_behavior` |
| `market_capital_flow_chip` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10022` | `/sdb/dlut/prod/资金流智能体` | pass | pass | fail | `production_identity_mismatch` | dev pass after remediation | `unknown_agent_id`; production patch not backfilled | Backfill identity wrapper and redeploy | `PROMPT-PROD-IDENTITY-FIX` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/market_capital_flow_chip` |
| `sentiment_company_radar` | L2 | market | `conclusion_object_v1` | missing | unknown | skipped | skipped | skipped | `production_endpoint_missing` | dev pass market-only | No confirmed production endpoint; must remain market-only | Production deploy/register and market-only resmoke | `PROMPT-PROD-BACKFILL-DEV-PATCH` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/sentiment_company_radar` |
| `risk_crash` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10012` | `/sdb/dlut/prod/股价崩盘风险智能体` | pass | pass | pass | `production_compute_pass` | dev pass after remediation | L2 risk gate-member only; not L3 risk evidence | Production invoke audit prep | `PROMPT-PROD-INVOKE-AUDIT-PREP` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/risk_crash` |
| `risk_financial_fraud` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10013` | `/sdb/dlut/prod/财务造假风险智能体` | pass | pass | pass | `production_compute_pass` | dev pass after remediation | L2 risk gate-member only; not L3 risk evidence | Production invoke audit prep | `PROMPT-PROD-INVOKE-AUDIT-PREP` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/risk_financial_fraud` |
| `risk_identification` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10010` | `/sdb/dlut/prod/上市公司财务与市场风险规则推理智能体` | pass | pass | pass | `production_compute_pass` | dev pass after remediation | L2 risk gate-member only; not L3 risk evidence | Production invoke audit prep | `PROMPT-PROD-INVOKE-AUDIT-PREP` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/risk_identification` |
| `risk_compliance_review` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10011` | `/sdb/dlut/prod/公告合规审查智能体` | pass | pass | pass | `production_compute_pass` | dev pass after remediation | L2 risk gate-member only; not L3 risk evidence | Production invoke audit prep | `PROMPT-PROD-INVOKE-AUDIT-PREP` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/risk_compliance_review` |
| `macro_analysis` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10014` | `/sdb/dlut/prod/宏观分析智能体` | pass | pass | pass | `production_compute_pass` | dev pass | Production L2 macro pass | Production invoke audit prep | `PROMPT-PROD-INVOKE-AUDIT-PREP` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/macro_analysis` |
| `macro_commodity_pricing` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10004` | `/sdb/dlut/prod/商品定价分析智能体/agent协议` | pass | fail | skipped | `production_health_pass_compute_failed` | dev endpoint missing | Production compute HTTP error | Fix production compute wrapper/runbook | `PROMPT-PROD-COMMODITY-RUNBOOK` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/macro_commodity_pricing` |
| `macro_index_valuation` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10003` | `/sdb/dlut/prod/股票指数估值智能体` | skipped | skipped | skipped | `production_semantic_deferred` | semantic deferred | Owner has not approved macro L2 semantics | Owner semantic decision | `PROMPT-PROD-MACRO-INDEX-OWNER` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/macro_index_valuation` |
| `macro_sentiment` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10018` | `/sdb/dlut/prod/宏观综合智能体/placeholders.macro_sentiment` | skipped | skipped | skipped | `production_semantic_deferred` | L3-style deferred | Placeholder or macro_conclusion semantics, not L2 | L2/L3 classification | `PROMPT-PROD-MACRO-L3-DEFER` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/macro_sentiment` |
| `macro_industry_hotspot` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10019` | `/sdb/dlut/prod/宏观综合智能体/placeholders.industry_hotspot` | skipped | skipped | skipped | `production_semantic_deferred` | L3-style deferred | Placeholder or macro_conclusion semantics, not L2 | L2/L3 classification | `PROMPT-PROD-MACRO-L3-DEFER` | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z/macro_industry_hotspot` |
| `value_composite` | L3 | composite | `dimension_composite_result_v1` | n/a | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | deterministic internal | L3 adapter not designed | L3 adapter design | `PROMPT-PROD-L3-ADAPTER-DESIGN` | n/a |
| `market_composite` | L3 | composite | `dimension_composite_result_v1` | n/a | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | deterministic internal | L3 adapter not designed | L3 adapter design | `PROMPT-PROD-L3-ADAPTER-DESIGN` | n/a |
| `risk_composite` | L3 | composite | `dimension_composite_result_v1` | n/a | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | deterministic internal | L3 adapter not designed; no sentiment risk input | L3 adapter design | `PROMPT-PROD-L3-ADAPTER-DESIGN` | n/a |
| `macro_composite` | L3 | composite | `dimension_composite_result_v1` | n/a | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | deterministic internal | L3 adapter not designed | L3 adapter design | `PROMPT-PROD-L3-ADAPTER-DESIGN` | n/a |
| `decision_synthesizer` | L4 | l4 | `decision_result_v1` | n/a | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | deterministic internal | L4 adapter not designed | L4 adapter design | `PROMPT-PROD-L4-ADAPTER-DESIGN` | n/a |
| `report_generator` | L4 | l4 | `report_result_v1` | n/a | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | deterministic internal | L4 adapter not designed | L4 adapter design | `PROMPT-PROD-L4-ADAPTER-DESIGN` | n/a |

## Dev Historical Evidence Appendix

Earlier R8-8G/H/I/J/K/L/M evidence is retained only as dev historical evidence.
It helped identify wrappers and service patches, but it does not drive the
production status above.

Dev historical controlled compute pass agents:

- `financial_data_service`
- `entity_relation_extractor`
- `value_ml_valuation`
- `value_traditional_valuation`
- `value_meta_valuation`
- `value_research_synthesis`
- `market_stock_technical`
- `sentiment_company_radar`
- `market_capital_flow_chip`
- `risk_identification`
- `risk_compliance_review`
- `risk_financial_fraud`
- `risk_crash`
- `macro_analysis`

Important production rebaseline result: only five of these currently pass
production adapter mapping. Several dev fixes were not backfilled to production.

## Service Patch Backfill Inventory

These patches made dev services pass. They must be backfilled into
service-owned source-controlled repositories and redeployed to production before
production evidence can pass.

| agent_id | dev patch evidence |
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

Because only five production candidates passed adapter mapping, the next phase
should be R8-8Q production remediation/backfill, not broad runtime binding
enablement.

Recommended sequence:

1. R8-8Q: backfill dev service protocol fixes into production services and
   redeploy.
2. R8-8R: production `/health` + `/v1/agent/compute` resmoke for failed agents.
3. R8-9A: production `/v1/agent/invoke` audit planning only for the five current
   production pass agents and any later production-pass resmoke agents.
4. R8-9B: first controlled production invoke smoke for a tiny allowlist, still
   without runtime binding enablement.
