# Controlled Readiness Smoke Log

This log records sanitized controlled readiness evidence for fixed-DAG external
service candidates. It is not public transcript content and must not include raw
service responses, credentials, traceback text, provider raw responses, or
chain-of-thought.

R8-8G through R8-8M entries below are dev-only historical evidence unless a
section explicitly says production. Dev evidence is useful for debugging and
service backfill, but it is not production readiness.

## 2026-06-11 - R8-8Q production remediation and re-smoke

| Field | Value |
| --- | --- |
| Phase | R8-8Q / R8-11A |
| Artifact directory | `/tmp/lma-r8-8q-prod-resmoke/20260611T020302Z` |
| Service patch manifest | `/tmp/lma-r8-8q-prod-service-backup/20260611T015600Z/service_patch_manifest.json` |
| Environment | production L1/L2 candidate endpoints only |
| Endpoint calls | `GET /health`, `POST /v1/agent/compute` |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |

R8-8Q remediated bounded production protocol wrapper issues and re-smoked the
remaining L1/L2 candidates that were safe to test. The smoke payload set
`allow_llm=false`; no provider call or `/v1/agent/invoke` call was made.

| agent_id | endpoint | health | compute | adapter mapping | status |
| --- | --- | --- | --- | --- | --- |
| `financial_data_service` | `127.0.0.1:11000` | fail: `invalid_json` | skipped | skipped | remediation needed |
| `value_traditional_valuation` | `127.0.0.1:10000` | pass | pass: `agent_conclusion_v1` | pass | production compute evidence |
| `value_ml_valuation` | `127.0.0.1:10001` | pass | pass: `agent_conclusion_v1` | pass | production compute evidence |
| `value_meta_valuation` | `127.0.0.1:10002` | pass | pass: `agent_conclusion_v1` | pass | production compute evidence |
| `value_research_synthesis` | `127.0.0.1:10006` | pass | pass: `agent_conclusion_v1` | pass | production compute evidence |
| `market_stock_technical` | `127.0.0.1:10009` | pass | pass: `agent_conclusion_v1` | pass | production compute evidence |
| `market_capital_flow_chip` | `127.0.0.1:10022` | pass | pass: `agent_conclusion_v1` | pass | production compute evidence |
| `sentiment_company_radar` | `127.0.0.1:10020` | pass | pass: `agent_conclusion_v1` | pass | production compute evidence, market-only |
| `market_ipo_investor_behavior` | `127.0.0.1:10008` | pass | pass: `agent_conclusion_v1` | pass | production compute evidence |
| `macro_commodity_pricing` | `127.0.0.1:10004` | fail: `health_identity_mismatch` | skipped | skipped | remediation needed |

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not prove production default invocation readiness.
- This does not update public transcript content.

## 2026-06-11 - R8-10F value composite production remediation

| Field | Value |
| --- | --- |
| Phase | R8-10F |
| Artifact directory | `/tmp/lma-r8-10f-value-composite-prod-smoke/20260611T014340Z` |
| Environment | production `value_composite` endpoint only |
| Endpoint calls | `GET /health`, `POST /v1/agent/compute` |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |

R8-10F remediated the `value_composite` production health identity mismatch on
`127.0.0.1:10015` and re-smoked only that production endpoint.

| agent_id | endpoint | health | compute | adapter mapping | status |
| --- | --- | --- | --- | --- | --- |
| `value_composite` | `127.0.0.1:10015` | pass | pass: `dimension_conclusion_v1` | pass | production compute evidence |

Sanitized result summary:

- Health identity: `agent_id=value_composite`, `external_agent_id=composite_valuation`,
  `fixed_dag_agent_id=value_composite`.
- Compute envelope: `external_agent_compute_v0` with
  `tool_result.schema_version=dimension_conclusion_v1`.
- Adapter target: `dimension_composite_result_v1`.
- Members: `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not prove production default invocation readiness.
- This does not update public transcript content.

## 2026-06-10 - R8-10E L3 production controlled compute smoke

| Field | Value |
| --- | --- |
| Phase | R8-10E |
| Artifact directory | `/tmp/lma-r8-10e-l3-prod-smoke/20260610T150158Z` |
| Environment | production L3 endpoints only |
| Authorized restart | yes, `ALLOW_R8_10E_L3_PROD_RESTART=1` |
| Endpoint calls | `GET /health`, `POST /v1/agent/compute` |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |

Production L3 smoke summary:

| agent_id | endpoint | health | compute | adapter mapping | status |
| --- | --- | --- | --- | --- | --- |
| `value_composite` | `127.0.0.1:10015` | fail: `health_identity_mismatch` | skipped | skipped | remediation needed |
| `market_composite` | `127.0.0.1:10023` | pass | pass: `dimension_conclusion_v1` | pass | production compute evidence |
| `risk_composite` | `127.0.0.1:10016` | pass | pass: `risk_conclusion_v1` | pass | production compute evidence |
| `macro_composite` | `127.0.0.1:10024` | pass | pass: `macro_conclusion_v1` | pass | production compute evidence |

Notes:

- `risk_composite` health returned service-owned `agent_id=risk_synthesis`;
  this matched the expected external service id and was accepted as structured
  service health identity for this compute-only gate.
- `value_composite` health returned value-ML service identity, not
  `value_composite` / `composite_valuation`, so compute was skipped fail-closed.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not prove production default invocation readiness.
- This does not update public transcript content.

## 2026-06-10 - R8-8P production endpoint rebaseline

| Field | Value |
| --- | --- |
| Phase | R8-8P |
| Run UTC | 2026-06-10T10:44:56Z |
| Artifact directory | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z` |
| Environment | production endpoints only |
| Endpoint calls | `GET /health`, `POST /v1/agent/compute` |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |

Production coverage summary:

| Metric | Count |
| --- | ---: |
| Total fixed DAG agents | 27 |
| External-service candidates | 20 |
| Production endpoint known | 18 |
| Production health pass | 14 |
| Production compute pass | 13 |
| Production adapter mapping pass | 5 |
| Production failed bucket | 13 |
| Production endpoint missing | 2 |
| Production semantic deferred | 3 |
| Production identity mismatch | 8 |
| Internal deterministic | 1 |
| L3/L4 deferred | 6 |
| Invoke audit candidates | 5 |

Production health+compute+adapter pass candidates:

- `risk_identification`
- `risk_compliance_review`
- `risk_financial_fraud`
- `risk_crash`
- `macro_analysis`

Production failed/deferred highlights:

- `financial_data_service`: production `/health` failed with invalid JSON.
- `entity_relation_extractor`: no confirmed production endpoint.
- `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, `value_research_synthesis`,
  `market_stock_technical`, `market_fund_manager_behavior`,
  `market_ipo_investor_behavior`, and `market_capital_flow_chip`: production
  compute was reachable, but adapter mapping failed on identity mismatch.
- `sentiment_company_radar`: no confirmed production endpoint.
- `macro_commodity_pricing`: production health passed but compute failed.
- `macro_index_valuation`, `macro_sentiment`, and
  `macro_industry_hotspot`: production semantic deferred.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not prove production default invocation readiness.
- This does not update public transcript content.

## 2026-06-10 - R8-8P-DOCS-QA production remediation playbook

| Field | Value |
| --- | --- |
| Phase | R8-8P-DOCS-QA |
| Source artifact directory | `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z` |
| Endpoint calls | none |
| Runtime bindings changed | no |
| Live flags changed | no |
| Production service code changed | no |

R8-8P-DOCS-QA does not create new health, compute, or adapter evidence. It
turns the R8-8P production results into a problem playbook and copy-ready
developer prompt catalog:

- `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` now records each failed/deferred
  agent's current status, production test result, problem type, failure cause,
  impact, service-owner action, maintainer action, resmoke method, and prompt
  id.
- `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` now provides agent-specific
  Chinese prompts for production health fixes, endpoint deployment, identity
  backfill, compute wrapper fixes, semantic classification, L3/L4 design, and
  invoke-audit preparation.

Problem summary:

- `financial_data_service`: production health contract failure.
- `entity_relation_extractor`: production endpoint missing.
- `sentiment_company_radar`: production endpoint missing; market-only.
- Value and selected market services: production identity mismatch.
- `market_fund_manager_behavior`: service discovery plus identity mismatch.
- `market_ipo_investor_behavior`: production compute wrapper and identity
  contract failure.
- `macro_commodity_pricing`: production compute failure after health pass.
- `macro_index_valuation`, `macro_sentiment`, `macro_industry_hotspot`:
  semantic deferred until owner classification.
- L3/L4: deterministic seams until explicit adapter/runtime design.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not call `/health` or `/v1/agent/compute`.
- This does not prove production default invocation readiness.

## 2026-06-10 - R8-8D-ID value_ml_valuation

| Field | Value |
| --- | --- |
| Phase | R8-8D-ID |
| Run UTC | 2026-06-10T03:06:55Z |
| Artifact directory | `/tmp/lma-r8-8d-id-value-ml-resmoke/20260610T030655Z` |
| Fixed DAG agent id | `value_ml_valuation` |
| External service id | `valuation_ml` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/机器学习企业估值智能体`.
- Service project was not a usable git repository during remediation; original
  files were backed up outside the repo under
  `/tmp/lma-r8-8d-id-backup/20260610T030433Z`.
- Response identity was remediated only for the dev service compute response:
  top-level and nested tool-result fixed-DAG id are `value_ml_valuation`, and
  external service id is `valuation_ml`.
- The main-system adapter identity gate was not relaxed.
- Dev service tests passed before re-smoke:
  `python3 -m py_compile service.py tests/test_v21_compliance.py`,
  `python3 -m pytest tests/test_v21_compliance.py -q`, and
  `python3 -m pytest tests/test_service_contract.py -q`.
- The dev 8001 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.

Next gate recommendation:

- Keep `value_ml_valuation` disabled in runtime bindings until a later explicit
  invoke-readiness and runtime-binding phase.
- Continue next controlled smoke work on dev ports only, using `/health` and
  `/v1/agent/compute` before any `/v1/agent/invoke` approval.

## 2026-06-10 - R8-8G macro_analysis

| Field | Value |
| --- | --- |
| Phase | R8-8G |
| Run UTC | 2026-06-10T03:40:47Z |
| Artifact directory | `/tmp/lma-r8-8g-candidate-smoke/20260610T033958Z/macro_analysis` |
| Fixed DAG agent id | `macro_analysis` |
| External service id | `macro_analysis` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |

Service patch summary:

- No service patch was required for this controlled smoke.
- The dev service was already listening on port 8014 and emitted a structured
  `external_agent_compute_v0` compute envelope that mapped through the
  provider-free fixed DAG adapter.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.

Next gate recommendation:

- Keep `macro_analysis` disabled in runtime bindings until a later explicit
  invoke-readiness and runtime-binding phase.
- If advanced later, run a separate controlled `/v1/agent/invoke` review before
  any `live_verified` or invoke-enabled change.

## 2026-06-10 - R8-8G value_traditional_valuation

| Field | Value |
| --- | --- |
| Phase | R8-8G |
| Run UTC | 2026-06-10T03:43:32Z |
| Artifact directory | `/tmp/lma-r8-8g-candidate-smoke/20260610T033958Z/value_traditional_valuation` |
| Fixed DAG agent id | `value_traditional_valuation` |
| External service id | `valuation_traditional` |
| Legacy agent id | `a17_traditional_valuation` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/传统企业估值智能体`.
- Service project was not a usable git repository during remediation; original
  files were backed up outside the repo under
  `/tmp/lma-r8-8g-service-backup/20260610T034105Z/value_traditional_valuation`.
- Response identity was remediated only for the dev service compute response:
  top-level and nested tool-result fixed-DAG id are
  `value_traditional_valuation`, and external service id is
  `valuation_traditional`.
- The main-system adapter identity gate was not relaxed.
- Dev service tests passed before re-smoke:
  `python3 -m py_compile service.py tests/test_v21_compliance.py`,
  `python3 -m pytest tests/test_v21_compliance.py -q`, and
  `python3 -m pytest tests/test_domain_contract_v1.py -q`.
- The dev 8000 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.

Next gate recommendation:

- Keep `value_traditional_valuation` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Treat `value_meta_valuation` as the closest next identity-remediation sibling
  if the value-family controlled smoke sequence continues.

## 2026-06-10 - R8-8H value_meta_valuation

| Field | Value |
| --- | --- |
| Phase | R8-8H |
| Run UTC | 2026-06-10T04:00:43Z |
| Artifact directory | `/tmp/lma-r8-8h-candidate-smoke/20260610T040043Z/value_meta_valuation` |
| Fixed DAG agent id | `value_meta_valuation` |
| External service id | `valuation_meta` |
| Legacy agent id | `a18_meta_valuation` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/元学习企业估值智能体`.
- Service project was not a usable git repository during remediation; original
  files were backed up outside the repo under
  `/tmp/lma-r8-8h-service-backup/20260610T035804Z/value_meta_valuation`.
- Response identity and compute tool-result dimension were remediated only for
  the dev service boundary: fixed-DAG id is `value_meta_valuation`, external
  service id is `valuation_meta`, and the emitted adapter-facing dimension is
  `value`.
- The main-system adapter identity gate was not relaxed.
- Dev service tests passed before re-smoke:
  `python3 -m py_compile service.py tests/test_v21_compliance.py` and
  `python3 -m pytest tests/test_v21_compliance.py tests/test_domain_contract_v1.py -q`.
- The dev 8002 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.

Next gate recommendation:

- Keep `value_meta_valuation` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Treat the value-family identity remediation pattern as service-side evidence
  only; do not loosen main-system fixed-DAG identity validation.

## 2026-06-10 - R8-8H value_research_synthesis

| Field | Value |
| --- | --- |
| Phase | R8-8H |
| Run UTC | 2026-06-10T04:00:43Z |
| Artifact directory | `/tmp/lma-r8-8h-candidate-smoke/20260610T040043Z/value_research_synthesis` |
| Fixed DAG agent id | `value_research_synthesis` |
| External service id | `analyst_research` |
| Legacy agent id | `a12_research_synthesis` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/分析师研报与观点集成智能体`.
- Service project was not a usable git repository during remediation; original
  `service.py` was backed up outside the repo under
  `/tmp/lma-r8-8h-service-backup/20260610T040157Z/value_research_synthesis`.
- Response identity was remediated only for the dev service boundary:
  fixed-DAG id is `value_research_synthesis`, external service id is
  `analyst_research`, and the emitted adapter-facing dimension remains `value`.
- The main-system adapter identity gate was not relaxed.
- Dev service tests passed before re-smoke:
  `python3 -m py_compile service.py` and
  `python3 -m pytest tests/test_service_contract.py tests/test_compute_endpoint.py tests/test_domain_payload.py tests/test_local_data_offline.py -q`.
- The dev 8006 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.

Next gate recommendation:

- Keep `value_research_synthesis` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- The next value-family work should be invoke-readiness review, not automatic
  runtime binding enablement.

## 2026-06-10 - R8-8H market_stock_technical

| Field | Value |
| --- | --- |
| Phase | R8-8H |
| Run UTC | 2026-06-10T04:00:43Z |
| Artifact directory | `/tmp/lma-r8-8h-candidate-smoke/20260610T040043Z/market_stock_technical` |
| Fixed DAG agent id | `market_stock_technical` |
| External service id | `technical_stock` |
| Legacy agent id | `a10_stock_technical_analysis` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/个股技术分析智能体`.
- Service project was not a usable git repository during remediation; original
  service and test files were backed up outside the repo under
  `/tmp/lma-r8-8h-service-backup/20260610T040408Z/market_stock_technical`.
- Response identity and compute tool-result dimension were remediated only for
  the dev service boundary: fixed-DAG id is `market_stock_technical`, external
  service id is `technical_stock`, and the emitted adapter-facing dimension is
  `market`.
- The main-system adapter identity gate was not relaxed.
- Dev service tests passed before re-smoke:
  `python3 -m py_compile service.py schemas.py tests/test_compute_endpoint.py tests/test_domain_contract_v1.py tests/test_service_contract.py` and
  `python3 -m pytest tests/test_service_contract.py tests/test_compute_endpoint.py tests/test_domain_contract_v1.py tests/test_local_data_offline.py -q -p no:cacheprovider`.
- The dev 8009 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.

Next gate recommendation:

- Keep `market_stock_technical` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Do not treat `dimension=market` compute mapping as evidence for any L3 market
  composite or L4 decision runtime path.

## 2026-06-10 - R8-8I sentiment_company_radar

| Field | Value |
| --- | --- |
| Phase | R8-8I |
| Run UTC | 2026-06-10T04:48:54Z |
| Artifact directory | `/tmp/lma-r8-8i-candidate-smoke/20260610T044854Z/sentiment_company_radar` |
| Fixed DAG agent id | `sentiment_company_radar` |
| External service id | `company_radar_agent` |
| Legacy agent id | `a09_company_sentiment_radar` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |
| Adapter output route | `market_composite` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/企业舆情雷达智能体/company_radar_agent`.
- Service project was not a usable git repository during remediation; original
  service, schema, and local test files were backed up outside the repo under
  `/tmp/lma-r8-8i-service-backup/20260610T043253Z/sentiment_company_radar`.
- Response identity, structured health identity, and compute tool-result
  dimension were remediated only for the dev service boundary: fixed-DAG id is
  `sentiment_company_radar`, external service id is `company_radar_agent`, and
  the emitted adapter-facing dimension is `market`.
- The main-system adapter identity gate was not relaxed.
- The service remains market-only. It is not risk evidence and must not be
  routed into risk composites.
- Dev service validation before smoke:
  `python3 -m py_compile company_radar_agent/service.py company_radar_agent/schemas.py company_radar_agent/tests/conftest.py company_radar_agent/tests/test_service_contract.py`.
- The dev 8104 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.
- This does not provide L3 market composite or L4 decision runtime evidence.

Next gate recommendation:

- Keep `sentiment_company_radar` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Treat its controlled compute evidence as L2 market-only evidence. Do not
  restore or infer any sentiment-to-risk path.
- Revisit L1 `financial_data_service` separately; R8-8J records that follow-up
  as a distinct L1 data-bundle evidence item.

## 2026-06-10 - R8-8J financial_data_service

| Field | Value |
| --- | --- |
| Phase | R8-8J |
| Run UTC | 2026-06-10T05:33:59Z |
| Artifact directory | `/tmp/lma-r8-8j-candidate-smoke/20260610T053359Z/financial_data_service` |
| Fixed DAG agent id | `financial_data_service` |
| External service id | `financial_data_service` |
| Payload family | `external_agent_compute_v0` with `data_bundle_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `data_bundle_v1` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/金融数据服务智能体/pg-ops-agent-v1.2/backend`.
- Service project was not a usable git repository during remediation; original
  `app/main.py` was backed up outside the repo under
  `/tmp/lma-r8-8j-service-backup/20260610T053111Z/financial_data_service`.
- Structured health and compute wrappers were remediated only for the dev
  service boundary: fixed-DAG id is `financial_data_service`, external service
  id is `financial_data_service`, health emits `external_agent_health_v0`, and
  compute emits `external_agent_compute_v0` with a concrete `data_bundle_v1`
  tool result.
- The service patch did not change the service business core, database query
  service, model logic, data files, prod config, or main-system runtime
  bindings.
- The main-system adapter gained a provider-free pure mapping branch for
  `external_agent_compute_v0.tool_result.data_bundle_v1`; it is still not an
  HTTP wrapper and is not wired into graph execution.
- Dev service validation before smoke:
  `python3 -m py_compile app/main.py`.
- The dev 8100 process was restarted with `PORT=8100` and the existing
  `run.py` entry because it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.
- This does not wire L1 data service results into active graph execution.

Next gate recommendation:

- Keep `financial_data_service` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Treat this as L1 data-bundle controlled evidence only. A future phase should
  review invoke semantics and active graph binding separately before any
  `live_verified` or invoke-enabled change.

## 2026-06-10 - R8-8K entity_relation_extractor

| Field | Value |
| --- | --- |
| Phase | R8-8K |
| Run UTC | 2026-06-10T06:11:34Z |
| Artifact directory | `/tmp/lma-r8-8k-candidate-smoke/20260610T061134Z/entity_relation_extractor` |
| Fixed DAG agent id | `entity_relation_extractor` |
| External service id | `entity_relation_agent` |
| Legacy agent id | `a15_entity_relation_extraction` |
| Payload family | `external_agent_compute_v0` with `entity_relation_bundle_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `entity_relation_bundle_v1` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/实体关系抽取智能体/entity_relation_agent`.
- Service project was not a usable git repository during remediation; original
  service and schema files were backed up outside the repo under
  `/tmp/lma-r8-8k-service-backup/20260610T060226Z/entity_relation_extractor`.
- The dev service boundary now emits fixed-DAG id
  `entity_relation_extractor`, external service id `entity_relation_agent`, and
  `external_agent_compute_v0` with a concrete `entity_relation_bundle_v1` tool
  result for fixed-DAG compute requests.
- The service patch did not change the relation extraction business core,
  database logic, model logic, data files, prod config, or main-system runtime
  bindings.
- The main-system adapter gained a provider-free pure mapping branch for
  `external_agent_compute_v0.tool_result.entity_relation_bundle_v1`; it is
  still not an HTTP wrapper and is not wired into graph execution.
- Dev service validation before smoke:
  `python3 -m py_compile entity_relation_agent/service.py entity_relation_agent/schemas.py`.
- The dev 8101 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.
- This does not wire L1 entity-relation results into active graph execution.

Next gate recommendation:

- Keep `entity_relation_extractor` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Treat this as L1 entity-relation controlled evidence only. Active graph
  consumption, L2 dependency wiring, and default runtime invocation remain
  separate later gates.

## 2026-06-10 - R8-8K risk_identification

| Field | Value |
| --- | --- |
| Phase | R8-8K |
| Run UTC | 2026-06-10T06:11:34Z |
| Artifact directory | `/tmp/lma-r8-8k-candidate-smoke/20260610T061134Z/risk_identification` |
| Fixed DAG agent id | `risk_identification` |
| External service id | `market_risk_reasoning` |
| Legacy agent id | `a19_risk_identification` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |
| Adapter output stance | `risk_gate_member` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/上市公司财务与市场风险规则推理智能体`.
- Service project was not a usable git repository during remediation; original
  service and protocol files were backed up outside the repo under
  `/tmp/lma-r8-8k-service-backup/20260610T060226Z/risk_identification`.
- The dev service boundary now emits fixed-DAG id `risk_identification`,
  external service id `market_risk_reasoning`, canonical dimension `risk`, and
  `agent_conclusion_v1 role=gate_member` with bounded `risk_score` for
  fixed-DAG compute requests.
- The service patch did not change the risk rules, compute core, model logic,
  data files, prod config, or main-system runtime bindings.
- The main-system adapter identity gate was not relaxed.
- Dev service validation before smoke:
  `python3 -m py_compile market_risk_model/agent/app.py market_risk_model/agent/protocol.py`.
- The dev 8010 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.
- This does not provide L3 `risk_composite` or L4 decision runtime evidence.

Next gate recommendation:

- Keep `risk_identification` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Treat this as L2 risk gate-member controlled evidence only; a later risk
  composite phase must separately review L3 `risk_conclusion_v1`.

## 2026-06-10 - R8-8K risk_compliance_review

| Field | Value |
| --- | --- |
| Phase | R8-8K |
| Run UTC | 2026-06-10T06:11:34Z |
| Artifact directory | `/tmp/lma-r8-8k-candidate-smoke/20260610T061134Z/risk_compliance_review` |
| Fixed DAG agent id | `risk_compliance_review` |
| External service id | `announcement_compliance` |
| Legacy agent id | `a20_compliance_review` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |
| Adapter output stance | `risk_gate_member` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/公告合规审查智能体`.
- Service project was not a usable git repository during remediation; original
  service and protocol files were backed up outside the repo under
  `/tmp/lma-r8-8k-service-backup/20260610T060226Z/risk_compliance_review`.
- The dev service boundary now emits fixed-DAG id `risk_compliance_review`,
  external service id `announcement_compliance`, canonical dimension `risk`,
  and `agent_conclusion_v1 role=gate_member` with bounded `risk_score` for
  fixed-DAG compute requests.
- The service patch did not change the compliance rules, compute core, model
  logic, data files, prod config, or main-system runtime bindings.
- The main-system adapter identity gate was not relaxed.
- Dev service validation before smoke:
  `python3 -m py_compile announcement_compliance/agent/app.py announcement_compliance/agent/protocol.py`.
- The dev 8011 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.
- This does not provide L3 `risk_composite` or L4 decision runtime evidence.

Next gate recommendation:

- Keep `risk_compliance_review` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Treat this as L2 risk gate-member controlled evidence only; L3 risk
  composite integration remains deferred.

## 2026-06-10 - R8-8L risk_financial_fraud

| Field | Value |
| --- | --- |
| Phase | R8-8L |
| Run UTC | 2026-06-10T06:52:14Z |
| Artifact directory | `/tmp/lma-r8-8l-candidate-smoke/20260610T065214Z/risk_financial_fraud` |
| Fixed DAG agent id | `risk_financial_fraud` |
| External service id | `financial_fraud_agent` |
| Legacy agent id | `a24_financial_fraud_risk` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |
| Adapter output stance | `risk_gate_member` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/财务造假风险智能体`.
- Service project was not a usable git repository during remediation; original
  service and schema files were backed up outside the repo under
  `/tmp/lma-r8-8l-service-backup/20260610T064145Z/risk_financial_fraud`.
- The dev service boundary now emits fixed-DAG id `risk_financial_fraud`,
  external service id `financial_fraud_agent`, canonical dimension `risk`,
  and `agent_conclusion_v1 role=gate_member` with bounded `risk_score` for
  fixed-DAG compute requests.
- The service patch did not change the financial-fraud model, feature logic,
  compute core, data files, prod config, or main-system runtime bindings.
- The main-system adapter identity gate was not relaxed.
- Dev service validation before smoke:
  `python3 -m py_compile app/main.py app/schemas.py`.
- The dev 8013 process was restarted with the original command because it was
  not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.
- This does not provide L3 `risk_conclusion_v1`, L3 `risk_composite`, or L4
  decision runtime evidence.

Next gate recommendation:

- Keep `risk_financial_fraud` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Treat this as L2 risk gate-member controlled evidence only; L3 risk
  composite integration remains deferred.

## 2026-06-10 - R8-8L risk_crash

| Field | Value |
| --- | --- |
| Phase | R8-8L |
| Run UTC | 2026-06-10T06:52:14Z |
| Artifact directory | `/tmp/lma-r8-8l-candidate-smoke/20260610T065214Z/risk_crash` |
| Fixed DAG agent id | `risk_crash` |
| External service id | `crash_risk` |
| Legacy agent id | `a23_crash_risk` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |
| Adapter output stance | `risk_gate_member` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/股价崩盘风险智能体`.
- Service project was not a usable git repository during remediation; original
  service and protocol files were backed up outside the repo under
  `/tmp/lma-r8-8l-service-backup/20260610T064145Z/risk_crash`.
- The dev service boundary now emits fixed-DAG id `risk_crash`, external
  service id `crash_risk`, canonical dimension `risk`, and
  `agent_conclusion_v1 role=gate_member` with bounded `risk_score` for
  fixed-DAG compute requests.
- The service patch did not change the crash-risk model, feature logic, compute
  core, data files, prod config, or main-system runtime bindings.
- The main-system adapter identity gate was not relaxed.
- Dev service validation before smoke:
  `python3 -m py_compile crash_risk_model/agent/app.py crash_risk_model/agent/protocol.py`.
- The dev 8012 process was restarted with the original command because it was
  not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.
- This does not provide L3 `risk_conclusion_v1`, L3 `risk_composite`, or L4
  decision runtime evidence.

Next gate recommendation:

- Keep `risk_crash` disabled in runtime bindings until a later explicit
  invoke-readiness and runtime-binding phase.
- Treat this as L2 risk gate-member controlled evidence only; L3 risk
  composite integration remains deferred.

## 2026-06-10 - R8-8M market_capital_flow_chip

| Field | Value |
| --- | --- |
| Phase | R8-8M |
| Run UTC | 2026-06-10T07:22:50Z |
| Artifact directory | `/tmp/lma-r8-8m-candidate-smoke/20260610T072250Z/market_capital_flow_chip` |
| Fixed DAG agent id | `market_capital_flow_chip` |
| External service id | `money_flow` |
| Legacy agent id | `capital_flow_chip_analysis` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |
| Adapter output dimension | `market` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/资金流智能体`.
- Service project was not a usable git repository during remediation; original
  service, schema, compute-core, and registration files were backed up outside
  the repo under
  `/tmp/lma-r8-8m-service-backup/20260610T072025Z/market_capital_flow_chip`.
- The dev service boundary now emits fixed-DAG id `market_capital_flow_chip`,
  external service id `money_flow`, canonical dimension `market`, and
  `agent_conclusion_v1 role=direction` for fixed-DAG compute requests.
- The service patch did not change the money-flow model, feature engineering,
  scoring algorithm, data files, prod config, or main-system runtime bindings.
- The main-system adapter identity gate was not relaxed.
- Dev service validation before smoke:
  `python3 -m py_compile service.py schemas.py compute_core.py agents/money_flow_agent.py`.
- The dev 8022 process was started with the service's documented dev command
  because no dev listener was present before R8-8M.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.
- This does not provide L3 `market_composite` or L4 decision runtime evidence.

Next gate recommendation:

- Keep `market_capital_flow_chip` disabled in runtime bindings until a later
  explicit invoke-readiness and runtime-binding phase.
- Treat this as L2 market direction controlled evidence only; L3 market
  composite integration remains deferred.
