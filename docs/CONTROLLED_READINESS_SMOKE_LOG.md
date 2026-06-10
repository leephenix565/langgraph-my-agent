# Controlled Readiness Smoke Log

This log records sanitized controlled readiness evidence for fixed-DAG external
service candidates. It is not public transcript content and must not include raw
service responses, credentials, traceback text, provider raw responses, or
chain-of-thought.

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
