# Fixed DAG Agent Readiness Matrix

This document is the production-first readiness matrix and remediation
playbook for the fixed DAG agent roster after Phase R8-8P-DOCS-QA.
R8-10B adds local provider-free L3 adapter mapping, but it does not make L3
services live. R8-10E/R8-10F add L3 production compute evidence. R8-8Q adds
production re-smoke evidence for remediated L1/L2 services. R8-11B adds the
first tiny allowlist controlled production invoke evidence.

R8-8P rebaselined readiness against confirmed production endpoints. Earlier
R8-8G/H/I/J/K/L/M controlled smoke results used dev endpoints and are now
historical evidence only. Dev evidence is useful for debugging and service
backfill, but it must never be counted as production evidence.

Production smoke artifact root:

```text
/tmp/lma-r8-8p-prod-readiness/20260610T104456Z
```

Latest L1/L2 production re-smoke artifact root:

```text
/tmp/lma-r8-8q-prod-resmoke/20260611T020302Z
```

Latest controlled production invoke smoke artifact root:

```text
/tmp/lma-r8-11b-prod-invoke-smoke/20260611T022513Z
```

## Current Conclusion

R8-8P moved the readiness baseline from dev endpoints to production endpoints.
R8-8Q then remediated and re-smoked selected production L1/L2 services. The
current production compute evidence set now includes thirteen L1/L2 external
candidates and all four L3 composite candidates. R8-11B then ran a tiny
controlled production `/v1/agent/invoke` smoke for five low-risk candidates:
`risk_identification`, `risk_compliance_review`, `risk_crash`,
`risk_financial_fraud`, and `value_research_synthesis`. This invoke evidence is
still not runtime binding enablement, live verification, public transcript
integration, or default production invocation.

The remaining production gaps are operational rather than graph-runtime
changes. `financial_data_service` still fails production health with invalid
JSON, `entity_relation_extractor` still lacks confirmed production compute
evidence in this matrix, `market_fund_manager_behavior` remains a
service-discovery/identity item, `macro_commodity_pricing` still fails the
fixed-DAG health/compute gate, and three macro candidates remain semantic
deferred.

This document converts those gaps into a production problem playbook. Service
owners should use the matching prompt id in
`docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md`, fix the production service or
ownership decision, redeploy, and request a production `/health` + `/compute`
resmoke. No failed item should be treated as production-ready because it passed
in dev.

## Non-Claims

- R8-11B called `/v1/agent/invoke` only for the five-service controlled
  production allowlist listed in this document.
- No `live_verified=true` flag was set.
- No `invoke_enabled_by_default=true` flag was set.
- No `runtime_bindings.json` entry was changed.
- No active graph path was changed to call production external services by
  default.
- No production compute pass equals production-ready default invocation.
- No dev pass equals production pass.
- No public transcript was updated with raw external output.
- No production service code was modified by R8-8P or R8-8P-DOCS-QA.
- `sentiment_company_radar` remains market-only and must not be routed into
  `risk_composite`.
- L3 and L4 remain deterministic seams until a separate adapter/runtime design
  phase owns them.
- R8-10B L3 adapter tests are not live readiness and do not enable external L3
  runtime execution.

## Production Coverage Summary

| Metric | Count | Notes |
| --- | ---: | --- |
| Total fixed DAG agents | 27 | Full catalog roster |
| External-service candidates | 20 | L1 evidence services and L2 analysis services |
| Production endpoint known | 19 | Confirmed production listener or production port/cwd |
| Production health pass | 18 | Latest matrix count across production candidates with structured health, including L3 evidence |
| Production compute pass | 18 | Production `/v1/agent/compute` HTTP 2xx structured JSON across current evidence set |
| Production adapter mapping pass | 17 | 13 L1/L2 candidates plus 4 L3 composites mapped through provider-free adapter |
| Controlled production invoke pass | 5 | R8-11B tiny allowlist with `allow_llm=false` and adapter mapping pass |
| Production failed bucket | 7 | Remaining failed/deferred production items in the current matrix, excluding internal deterministic/L4 |
| Production endpoint missing | 1 | `entity_relation_extractor` remains without confirmed production compute evidence in this matrix |
| Production semantic deferred | 3 | Not safe to force into L2 production mapping |
| Production identity mismatch | 1 | `market_fund_manager_behavior` remains unresolved |
| Internal deterministic | 1 | `route_planner` |
| L3/L4 deferred | 6 | 4 composites plus decision/report |
| Production invoke audit candidates | 17 | Based only on production health + compute + adapter mapping pass |

Layer coverage:

| Layer/group | Production coverage |
| --- | --- |
| L1 | 0/2 production adapter pass; one health failure and one endpoint missing |
| L2 value | 4/4 production adapter pass |
| L2 market | 4/5 production adapter pass; fund-manager behavior remains unresolved |
| L2 risk | 4/4 production adapter pass |
| L2 macro | 1/5 production adapter pass; commodity failed and three macro candidates remain deferred |
| L3 | 4/4 production adapter pass; compute evidence only, no active runtime enablement |
| L4 | 0/2 external production readiness; deterministic internal seams only |

## Production Health+Compute+Adapter Pass Candidates

These agents have production `/health` pass, production `/v1/agent/compute`
pass, and provider-free adapter mapping pass. A five-service subset also has
R8-11B controlled production `/v1/agent/invoke` evidence. Neither compute nor
invoke smoke is live verification, default invocation, or production business
correctness.

| agent_id | What passed | What has not passed | Next action |
| --- | --- | --- | --- |
| `risk_identification` | Production health + compute + adapter mapping; R8-11B controlled invoke | runtime binding enablement, live flags, default invocation | runtime binding prepare review |
| `risk_compliance_review` | Production health + compute + adapter mapping; R8-11B controlled invoke | runtime binding enablement, live flags, default invocation | runtime binding prepare review |
| `risk_financial_fraud` | Production health + compute + adapter mapping; R8-11B controlled invoke | runtime binding enablement, live flags, default invocation | runtime binding prepare review |
| `risk_crash` | Production health + compute + adapter mapping; R8-11B controlled invoke | runtime binding enablement, live flags, default invocation | runtime binding prepare review |
| `macro_analysis` | Production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_traditional_valuation` | R8-8Q production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_ml_valuation` | R8-8Q production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_meta_valuation` | R8-8Q production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_research_synthesis` | R8-8Q production health + compute + adapter mapping; R8-11B controlled invoke | runtime binding enablement, live flags, default invocation | runtime binding prepare review |
| `market_stock_technical` | R8-8Q production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `market_capital_flow_chip` | R8-8Q production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `sentiment_company_radar` | R8-8Q production health + compute + adapter mapping as market-only L2 | `/v1/agent/invoke`, runtime binding enablement, live flags, risk routing | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `market_ipo_investor_behavior` | R8-8Q production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_composite` | R8-10F production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `market_composite` | R8-10E production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_composite` | R8-10E production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `macro_composite` | R8-10E production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |

## R8-10C L3 Service Protocol Backfill Audit

R8-10C is a no-endpoint, docs-only protocol backfill audit for the four L3
composite services. It did not call `/health`, `/v1/agent/compute`, or
`/v1/agent/invoke`. It did not modify service code, did not update runtime
bindings, and did not create L3 production readiness evidence.

R8-10B already gives the main system provider-free adapter mappings for
`dimension_conclusion_v1`, `risk_conclusion_v1`, and
`macro_conclusion_v1`. R8-10C found that the services must still backfill or
confirm service-side protocol shape before a later controlled L3 smoke can be
meaningful.

| agent_id | candidate service | current endpoint evidence | current payload shape | problem | required payload | next action | developer_prompt_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `value_composite` | 综合估值智能体 | Prod listener `10015`; dev listener `8015`; both process cwd point to `/sdb/dlut/prod/综合估值智能体`. No endpoint was called. | Source contains a `dimension_conclusion_v1` helper, but normal compute still appears to return `decision_conclusion_v1` from `AGENT_ID=composite_valuation`; the fixed-DAG compatibility branch returns L2 sample `agent_conclusion_v1` for `value_ml_valuation`. | Current service is not yet a true L3 `value_composite` endpoint. | `external_agent_compute_v0.tool_result.dimension_conclusion_v1` with `agent_id=value_composite`, `dimension=value`, and members from value L2 roster. | Service owner confirms ownership and backfills an actual L3 identity/wrapper, then requests controlled L3 smoke. | `PROMPT-L3-VALUE-COMPOSITE-BACKFILL` |
| `market_composite` | 市场面综合智能体 | Prod listener `10023`; dev listener `8023`; subservice listeners exist under market root. No endpoint was called. | Source already builds `external_agent_compute_v0.tool_result.dimension_conclusion_v1` with `agent_id=market_composite`; current payload still exposes Chinese `dimension=市场面` and service-local member ids such as `technical_stock`, `money_flow`, and `market_sentiment`. | Payload is close, but canonical dimension and member ids need fixed DAG alignment before adapter smoke can be authoritative. | `dimension_conclusion_v1` with `agent_id=market_composite`, `dimension=market`, fixed DAG market members, and weights summing to one. | Service owner backfills canonical dimension/member id mapping and confirms market-only sentiment handling, then requests controlled L3 smoke. | `PROMPT-L3-MARKET-COMPOSITE-BACKFILL` |
| `risk_composite` | 综合风险智能体 | Prod listener `10016`; dev listener `8016`; distinct prod/dev service roots. No endpoint was called. | Source emits `risk_conclusion_v1`, but primary id is `risk_synthesis`, tool_result lacks the required `agent_id=risk_composite` shape, dimension is Chinese `风险`, and `gate` is a nested object rather than the R8-10B adapter-facing `pass|penalty|veto|manual_review` field. | Risk L3 protocol mismatch. | `external_agent_compute_v0.tool_result.risk_conclusion_v1` with `agent_id=risk_composite`, `dimension=risk`, `role=gate`, flat gate action, top-level `risk_score`, `penalty`, and risk-only contributing agents. | Service owner adds R8-10B-compatible wrapper without changing D-S risk business logic, then requests controlled L3 smoke. | `PROMPT-L3-RISK-COMPOSITE-BACKFILL` |
| `macro_composite` | 宏观综合智能体 | Prod listener `10024`; no dev `8024` listener observed. No endpoint was called. | Source emits `macro_conclusion_v1` and already uses value/market-only `dimension_weights`, but primary id is `macro_synthesis` and compute returns an `external_agent_response_v0` style envelope. | Macro payload is close, but fixed DAG id and endpoint/runbook backfill are still needed. | `external_agent_compute_v0` or `external_agent_response_v0` tool_result with `schema_version=macro_conclusion_v1`, `agent_id=macro_composite`, `dimension=macro`, `role=regulator`, and value/market-only `dimension_weights`. | Service owner backfills fixed DAG id, confirms prod/dev runbook, and requests controlled L3 smoke. | `PROMPT-L3-MACRO-COMPOSITE-BACKFILL` |

## R8-10D L3 Service Wrapper Backfill

R8-10D applied bounded protocol-wrapper patches to the four L3 service
directories. This phase did not call `/health`, `/v1/agent/compute`, or
`/v1/agent/invoke`; it did not restart services; it did not change main-system
`src/`, `config/`, runtime bindings, live flags, graph, executor, public API,
or frontend behavior. The result is service-side protocol backfill only, not
production readiness evidence. Controlled L3 smoke remains a future R8-10E
phase.

Repo-external backup and manifest:
`/tmp/lma-r8-10d-l3-service-backup/20260610T142216Z/service_patch_manifest.json`.

R8-10D-SNAPSHOT records a temporary handoff repository for the four service
patches because the formal service source repositories are not available in
this environment:

- Shadow repo: `/sdb/dlut/service-shadow-repos/l3-composite-services`
- Shadow repo commit: `7a3c517 chore(snapshot): capture l3 protocol backfill handoff`
- Contents: service-local backfill notes, the R8-10D manifest, and zero-context
  patch files for the protocol wrapper changes.
- Non-claim: this shadow repo is not the long-term source of truth, does not
  prove production readiness, and does not mean the currently running services
  have loaded the patched files.

Each production service directory also now contains
`FIXED_DAG_PROTOCOL_BACKFILL.md` so service owners can see the fixed DAG id,
expected payload, changed files, backup manifest, and R8-10E restart/smoke
boundary beside the deployed files.

| agent_id | service root | wrapper backfilled | validation performed | current status | next action |
| --- | --- | --- | --- | --- | --- |
| `value_composite` | `/sdb/dlut/prod/综合估值智能体` | Fixed DAG request path now returns `external_agent_compute_v0.tool_result.dimension_conclusion_v1` with `agent_id=value_composite`, `dimension=value`, and fixed DAG value member ids for the three computed valuation members. | `py_compile`; focused pytest `tests/test_fixed_dag_l3_wrapper.py`. | `service_wrapper_backfilled_not_smoked` | R8-10E controlled `/health` + `/v1/agent/compute` smoke; do not call `/invoke`. |
| `market_composite` | `/sdb/dlut/prod/市场面综合智能体` | Adapter-facing `dimension=market`; `members[].agent_id` maps service-local market members to fixed DAG market L2 ids while preserving local ids in `external_agent_id`. | `py_compile`; focused pytest for external contract handoff, health, and compute degradation. | `service_wrapper_backfilled_not_smoked` | R8-10E controlled `/health` + `/v1/agent/compute` smoke; keep sentiment market-only. |
| `risk_composite` | `/sdb/dlut/prod/综合风险智能体` | Fixed DAG request path now returns `risk_conclusion_v1` with `agent_id=risk_composite`, `dimension=risk`, `role=gate`, flat `gate`, `risk_score`, `penalty`, and risk-only contributing agents. | `py_compile`; focused pytest `test_fixed_dag_risk_compute_wrapper` plus health schema. | `service_wrapper_backfilled_not_smoked` | R8-10E controlled `/health` + `/v1/agent/compute` smoke; do not route sentiment into risk. |
| `macro_composite` | `/sdb/dlut/prod/宏观综合智能体` | Fixed DAG request path now returns `external_agent_compute_v0.tool_result.macro_conclusion_v1` with `agent_id=macro_composite`, value/market-only `dimension_weights`, `risk_sensitivity`, and macro L2 contributing agents. | `py_compile`; focused pytest for fixed DAG and legacy compute envelopes. | `service_wrapper_backfilled_not_smoked` | R8-10E controlled `/health` + `/v1/agent/compute` smoke; no runtime enablement. |

## Production Problem Playbook

Each item below states the production problem, likely cause, remediation path,
and resmoke boundary. The service owner owns production service fixes and
redeploys. The main-system maintainer owns adapter/runtime decisions and must
not relax identity, dimension, or semantic gates to make a bad production
payload pass.

### financial_data_service

- Current status: `production_health_failed`.
- Production test result: production `GET /health` on `127.0.0.1:11000`
  returned HTTP 200 but failed `health_invalid_json`; compute was skipped.
- Problem type: production health contract failure.
- Failure reason: production health did not return safe
  `external_agent_health_v0` JSON, so the production service cannot enter
  compute smoke.
- Impact: L1 `data_bundle_v1` production evidence is blocked. Dev evidence is
  historical only and cannot substitute for production health.
- Solution: production `/health` must return structured
  `external_agent_health_v0` JSON; plain text/html must remain fail-closed.
  After health passes, `/v1/agent/compute` should return
  `external_agent_compute_v0.tool_result.data_bundle_v1`.
- Service owner action: patch the production health response builder, add a
  health contract test, deploy the production service, and request production
  resmoke.
- Main-system maintainer action: keep runtime bindings disabled and do not
  treat plain text health as pass.
- Retest method: production `GET /health`, then production
  `POST /v1/agent/compute`, then adapter mapping to `data_bundle_v1`; no
  `/v1/agent/invoke`.
- Prompt: `PROMPT-PROD-HEALTH-FIX-DATA-SERVICE`.

### entity_relation_extractor

- Current status: `production_endpoint_missing`.
- Production test result: no confirmed production endpoint was found; dev
  `8101` is not production evidence.
- Problem type: production deployment / endpoint missing.
- Failure reason: production service root, port, and externally reachable local
  production endpoint are not confirmed for the fixed DAG id.
- Impact: L1 `entity_relation_bundle_v1` production evidence is absent.
- Solution: service owner must provide and deploy a production endpoint with
  `/health` and `/v1/agent/compute`; compute should return
  `external_agent_compute_v0.tool_result.entity_relation_bundle_v1`.
- Service owner action: publish production service root, port,
  `external_agent_id`, health schema, compute wrapper, tests, and deployment
  runbook.
- Main-system maintainer action: keep endpoint status missing until production
  endpoint discovery and production resmoke pass.
- Retest method: production endpoint discovery, production health, production
  compute, adapter mapping to `entity_relation_bundle_v1`; no dev endpoint
  substitution.
- Prompt: `PROMPT-PROD-ENDPOINT-MISSING-ENTITY`.

### sentiment_company_radar

- Current status: `production_compute_pass` after R8-8Q.
- Production test result: production `10020` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved production endpoint and market-dimension wrapper gap.
- Failure reason before R8-8Q: production evidence was missing and the market
  subagent wrapper emitted a Chinese dimension value that the main-system
  adapter intentionally rejected.
- Impact: this service can now enter `/invoke` audit planning as market-only
  evidence, but it is still not live/default runtime.
- Solution applied: the shared market subagent protocol wrapper now emits
  adapter-facing `dimension=market` while preserving
  `external_agent_id=company_sentiment_radar`.
- Service owner action: backfill the wrapper patch into the formal service
  source repository and preserve market-only routing.
- Main-system maintainer action: keep the sentiment-to-risk guard and do not
  relax runtime bindings.
- Retest method: production `/health` + `/compute` + adapter mapping only; no
  `/v1/agent/invoke` until a later audit phase.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### value_traditional_valuation

- Current status: `production_compute_pass` after R8-8Q.
- Production test result: production `10000` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved fixed DAG identity and value-dimension wrapper gap.
- Solution applied: production envelope and nested `tool_result` now use
  `agent_id=value_traditional_valuation`, service id
  `external_agent_id=valuation_traditional`, legacy id
  `a17_traditional_valuation`, and adapter-facing `dimension=value`.
- Remaining action: service owner backfills this production patch into the
  formal service source repository; maintainer keeps runtime disabled until
  invoke audit.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### value_ml_valuation

- Current status: `production_compute_pass` after R8-8Q.
- Production test result: production `10001` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved fixed DAG identity and value-dimension wrapper gap.
- Solution applied: production health and compute now advertise
  `agent_id=value_ml_valuation`, `external_agent_id=valuation_ml`,
  `legacy_agent_id=a16_ml_valuation`, and adapter-facing `dimension=value`.
- Remaining action: service owner backfills the wrapper patch into formal
  source control; maintainer keeps the adapter identity gate strict.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### value_meta_valuation

- Current status: `production_compute_pass` after R8-8Q.
- Production test result: production `10002` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved fixed DAG identity and value-dimension wrapper gap.
- Solution applied: production compute now emits
  `agent_id=value_meta_valuation`, `external_agent_id=valuation_meta`,
  `legacy_agent_id=a18_meta_valuation`, and `dimension=value`.
- Remaining action: service owner backfills the production protocol patch into
  formal source control.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### value_research_synthesis

- Current status: `production_compute_pass` after R8-8Q.
- Production test result: production `10006` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved fixed DAG primary id default.
- Solution applied: production default primary id is now
  `value_research_synthesis`, while service-owned
  `external_agent_id=analyst_research` and legacy id
  `a12_research_synthesis` remain metadata.
- Remaining action: service owner backfills the default identity patch into the
  formal service source repository.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### market_stock_technical

- Current status: `production_compute_pass` after R8-8Q.
- Production test result: production `10009` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved production envelope identity and market-dimension
  wrapper gap.
- Solution applied: compute envelope includes `external_agent_id=technical_stock`
  and tool result emits adapter-facing `dimension=market`.
- Remaining action: service owner backfills the wrapper patch into the formal
  service source repository.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### market_capital_flow_chip

- Current status: `production_compute_pass` after R8-8Q.
- Production test result: production `10022` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved production envelope identity and market-dimension
  wrapper gap.
- Solution applied: compute envelope now includes `external_agent_id=money_flow`
  and tool result emits adapter-facing `dimension=market`.
- Remaining action: service owner backfills the wrapper patch into formal
  source control. The R8-8Q process restart used the production root and
  production port only.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### market_fund_manager_behavior

- Current status: `production_identity_mismatch` and service metadata
  incomplete.
- Production test result: production subservice on `10007` was reachable, but
  output identity was not fixed DAG compatible.
- Problem type: service discovery plus identity mismatch.
- Failure reason: ownership, service root, fixed DAG mapping, and
  `external_agent_id` are not clearly documented enough to accept production
  evidence.
- Impact: fund-manager behavior cannot be counted as market L2 production
  evidence.
- Solution: owner must confirm service root, production port, service id,
  `external_agent_id`, and `agent_conclusion_v1` wrapper with
  `dimension=market`.
- Service owner action: document the service, fix identity/wrapper, and add
  contract tests.
- Main-system maintainer action: keep this as discovery/remediation until owner
  metadata and production resmoke pass.
- Retest method: production endpoint discovery, health, compute, adapter
  mapping.
- Prompt: `PROMPT-PROD-FUND-SERVICE-DISCOVERY`.

### market_ipo_investor_behavior

- Current status: `production_compute_pass` after R8-8Q.
- Production test result: production `10008` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved market subagent dimension wrapper gap.
- Solution applied: the shared market subagent protocol wrapper now emits
  adapter-facing `dimension=market` while preserving
  `external_agent_id=ipo_investor_behavior`.
- Remaining action: service owner backfills the shared wrapper patch into the
  formal service source repository.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### macro_commodity_pricing

- Current status: `production_health_failed`.
- Production test result: R8-8Q production `10004` `/health` returned HTTP 200
  JSON but failed fixed-DAG health identity validation; compute was skipped
  fail-closed.
- Problem type: production compute endpoint failure.
- Failure reason: production health advertises service-owned
  `price_influence_agent` without fixed DAG `macro_commodity_pricing`
  identity, and the service still lacks a verified fixed DAG compute wrapper.
- Impact: commodity pricing has no macro L2 production adapter evidence.
- Solution: fix structured health to include fixed DAG identity, then add or
  repair production `/v1/agent/compute` so it emits
  `external_agent_compute_v0.tool_result.agent_conclusion_v1` with
  `agent_id=macro_commodity_pricing`, `external_agent_id=price_influence_agent`,
  `dimension=macro`, and target examples such as `CU`.
- Service owner action: add health/compute wrapper contract tests and deploy
  the production fix.
- Main-system maintainer action: do not treat service-owned health identity or
  a missing compute wrapper as production pass.
- Retest method: production health + compute + adapter mapping.
- Prompt: `PROMPT-PROD-COMMODITY-COMPUTE-FIX`.

### macro_index_valuation

- Current status: `production_semantic_deferred`.
- Production test result: production endpoint exists, but compute was deferred
  because macro L2 semantics are not owner-confirmed.
- Problem type: owner semantic decision required.
- Failure reason: the service naturally looks like index/value valuation, and
  forcing it into `dimension=macro` without owner approval would create an
  invalid signal.
- Impact: no production macro L2 evidence is recorded for this service.
- Solution: owner must decide whether stock-index valuation is a macro L2
  signal. If yes, implement a production wrapper that emits
  `agent_conclusion_v1` with `dimension=macro`; if no, keep it deferred or
  redesign the roster.
- Service owner action: provide written semantic decision and wrapper scope.
- Main-system maintainer action: do not force-normalize index/value semantics
  into macro.
- Retest method: only after owner confirmation and wrapper deployment,
  production health + compute + adapter mapping.
- Prompt: `PROMPT-PROD-MACRO-INDEX-OWNER`.

### macro_sentiment

- Current status: `production_semantic_deferred`.
- Production test result: production endpoint appeared placeholder or
  L3/regulator-style; L2 compute was not forced.
- Problem type: L2 vs L3 semantic mismatch.
- Failure reason: service semantics may be `macro_conclusion_v1` or regulator
  style rather than L2 `agent_conclusion_v1`.
- Impact: no macro L2 production evidence; forcing it into L2 could corrupt
  macro composite inputs.
- Solution: owner must classify the service. If it is L2, add an
  `agent_conclusion_v1` direction wrapper. If it is L3/regulator, defer to L3
  adapter design.
- Service owner action: classify payload family and provide wrapper or L3 design
  proposal.
- Main-system maintainer action: reject `macro_conclusion_v1` forced into L2.
- Retest method: after classification/wrapper, production health + compute +
  adapter mapping; no `/invoke`.
- Prompt: `PROMPT-PROD-MACRO-SENTIMENT-L2-OR-L3`.

### macro_industry_hotspot

- Current status: `production_semantic_deferred`.
- Production test result: production endpoint appeared placeholder or
  L3/regulator-style; L2 compute was not forced.
- Problem type: L2 vs L3 semantic mismatch.
- Failure reason: industry hotspot may be a macro/regulator aggregate rather
  than an L2 directional agent.
- Impact: no macro L2 production evidence; forcing it into L2 would weaken the
  contract boundary.
- Solution: owner must classify as L2 `agent_conclusion_v1` or future
  L3/macro payload. If L2, production wrapper must emit `dimension=macro`.
- Service owner action: classify payload, add wrapper if L2, or document L3
  deferral.
- Main-system maintainer action: keep semantic deferred until classification.
- Retest method: production health + compute + adapter mapping only after
  classification.
- Prompt: `PROMPT-PROD-MACRO-HOTSPOT-L2-OR-L3`.

### value_composite

- Current status: `service_wrapper_backfilled_not_smoked`.
- Production test result: R8-10C only inspected process state and shallow
  source. Production listener `10015` exists, and dev listener `8015` exists,
  but no endpoint was called.
- Problem type: L3 identity and wrapper mismatch.
- Failure reason: the service source contains a `dimension_conclusion_v1`
  helper, but the normal compute path still appears to emit
  `decision_conclusion_v1` under `AGENT_ID=composite_valuation`; the fixed DAG
  compatibility branch emits L2 sample `agent_conclusion_v1` under
  `value_ml_valuation`. It is not yet a true L3 `value_composite` service path.
- Impact: R8-10B adapter mapping exists, but a later L3 smoke would fail fixed
  DAG identity unless the service owner backfills the wrapper.
- Solution: add or correct a production compute wrapper that emits
  `external_agent_compute_v0.tool_result.dimension_conclusion_v1` with
  `agent_id=value_composite`, `dimension=value`, value L2 members, bounded
  evidence, and `data_as_of <= as_of`.
- Service owner action: backfill the wrapper and tests in the service-owned
  repo; do not change valuation business logic.
- Main-system maintainer action: keep deterministic seam and runtime bindings
  disabled until a later controlled L3 smoke phase.
- Retest method: future controlled L3 `/health` + `/v1/agent/compute` smoke
  only after owner backfill; no `/v1/agent/invoke`.
- Prompt: `PROMPT-L3-VALUE-COMPOSITE-BACKFILL`.

### market_composite

- Current status: `service_wrapper_backfilled_not_smoked`.
- Production test result: R8-10C only inspected process state and shallow
  source. Production listener `10023` and dev listener `8023` exist; subservice
  listeners also exist under the market root. No endpoint was called.
- Problem type: L3 member-id alignment.
- Failure reason: the service source already builds
  `external_agent_compute_v0.tool_result.dimension_conclusion_v1` with
  `agent_id=market_composite`, but the adapter-facing dimension still needs to
  be canonical English `market`, and member ids are service-local names such as
  `technical_stock`, `money_flow`, and `market_sentiment`, not the fixed DAG
  market L2 roster.
- Impact: R8-10B adapter mapping can validate L3 payloads, but service-local
  member ids would block authoritative mapping.
- Solution: backfill fixed DAG member ids:
  `market_stock_technical`, `market_capital_flow_chip`,
  `sentiment_company_radar`, `market_ipo_investor_behavior`, and
  `market_fund_manager_behavior`; keep sentiment market-only.
- Service owner action: add member-id normalization in the service wrapper and
  tests; do not change market fusion business logic.
- Main-system maintainer action: keep deterministic seam and runtime bindings
  disabled until a later controlled L3 smoke phase.
- Retest method: future controlled L3 `/health` + `/v1/agent/compute` smoke
  only after owner backfill; no `/v1/agent/invoke`.
- Prompt: `PROMPT-L3-MARKET-COMPOSITE-BACKFILL`.

### risk_composite

- Current status: `service_wrapper_backfilled_not_smoked`.
- Production test result: R8-10C only inspected process state and shallow
  source. Production listener `10016` and dev listener `8016` exist. No
  endpoint was called.
- Problem type: L3 risk payload shape mismatch.
- Failure reason: the service emits `risk_conclusion_v1`, but primary id is
  `risk_synthesis`; the adapter-facing payload needs `agent_id=risk_composite`,
  `dimension=risk`, `role=gate`, and a flat gate value
  `pass|penalty|veto|manual_review`. Current source uses Chinese dimension
  labels and a nested `gate` object with `action`.
- Impact: the business risk synthesis may be usable, but the protocol is not
  directly ready for R8-10B adapter smoke.
- Solution: add a bounded adapter-facing wrapper that preserves the existing
  D-S risk calculation while emitting R8-10B `risk_conclusion_v1` fields.
- Service owner action: backfill fixed DAG identity, flat gate action, top-level
  `risk_score`, `penalty`, risk-only contributing agents, and tests.
- Main-system maintainer action: keep no-sentiment-to-risk and no-runtime flags
  unchanged.
- Retest method: future controlled L3 `/health` + `/v1/agent/compute` smoke
  only after owner backfill; no `/v1/agent/invoke`.
- Prompt: `PROMPT-L3-RISK-COMPOSITE-BACKFILL`.

### macro_composite

- Current status: `service_wrapper_backfilled_not_smoked`.
- Production test result: R8-10C only inspected process state and shallow
  source. Production listener `10024` exists; no dev `8024` listener was
  observed. No endpoint was called.
- Problem type: L3 macro identity/runbook backfill.
- Failure reason: the service source already emits `macro_conclusion_v1` and
  value/market-only `dimension_weights`, but primary id is `macro_synthesis`,
  not `macro_composite`; compute currently returns an
  `external_agent_response_v0` style envelope rather than a clearly documented
  compute envelope.
- Impact: R8-10B can map macro payloads, but fixed DAG identity and runbook
  alignment must be explicit before controlled L3 smoke.
- Solution: backfill fixed DAG `agent_id=macro_composite`, keep
  `external_agent_id=macro_synthesis_service` or another owner-approved service
  id, and document whether compute returns `external_agent_compute_v0` or
  supported `external_agent_response_v0`.
- Service owner action: add tests proving `dimension_weights` contains only
  `value` and `market`, `risk_sensitivity` is separate, and no direction
  stance is emitted.
- Main-system maintainer action: keep deterministic seam and runtime bindings
  disabled until a later controlled L3 smoke phase.
- Retest method: future controlled L3 `/health` + `/v1/agent/compute` smoke
  only after owner backfill; no `/v1/agent/invoke`.
- Prompt: `PROMPT-L3-MACRO-COMPOSITE-BACKFILL`.

### decision_synthesizer

- Current status: `production_l3_l4_deferred`.
- Production test result: not tested as external service; deterministic internal
  seam remains.
- Problem type: L4 adapter/runtime design not started.
- Failure reason: decision synthesis has separate L4 semantics and public safety
  requirements.
- Impact: no external production L4 evidence.
- Solution: future L4 adapter design for decision payloads.
- Service owner action: none until L4 scope is approved.
- Main-system maintainer action: keep deterministic seam.
- Retest method: future L4 phase only.
- Prompt: `PROMPT-PROD-L4-ADAPTER-DESIGN`.

### report_generator

- Current status: `production_l3_l4_deferred`.
- Production test result: not tested as external service; deterministic internal
  seam remains.
- Problem type: L4 adapter/runtime design not started.
- Failure reason: report output has public transcript constraints and is not an
  L2/L3 compute wrapper.
- Impact: no external production L4 evidence.
- Solution: future L4 adapter design for report payloads and public-safe output.
- Service owner action: none until L4 scope is approved.
- Main-system maintainer action: keep deterministic seam and transcript safety.
- Retest method: future L4 phase only.
- Prompt: `PROMPT-PROD-L4-ADAPTER-DESIGN`.

## Full 27-Agent Production Matrix

| agent_id | layer | dimension | expected_payload_or_contract | production_endpoint | production_health_status | production_compute_status | production_adapter_mapping_status | production_status | problem_summary | solution_summary | next_action | developer_prompt_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `route_planner` | L1 | l1 | `fixed_dag_plan_v1` | n/a | n/a | n/a | n/a | `production_internal_deterministic` | Internal deterministic planner | Keep deterministic | No endpoint work | n/a |
| `financial_data_service` | L1 | l1 | `data_bundle_v1` | `127.0.0.1:11000` | fail | skipped | skipped | `production_health_failed` | `/health` invalid JSON | Fix structured production health, then compute wrapper | Production health fix and resmoke | `PROMPT-PROD-HEALTH-FIX-DATA-SERVICE` |
| `entity_relation_extractor` | L1 | l1 | `entity_relation_bundle_v1` | missing | skipped | skipped | skipped | `production_endpoint_missing` | No production endpoint | Deploy/register prod endpoint and entity wrapper | Endpoint + wrapper deployment | `PROMPT-PROD-ENDPOINT-MISSING-ENTITY` |
| `value_traditional_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10000` | pass | pass | pass | `production_compute_pass` | R8-8Q remediated identity and value dimension | Backfill service patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_ml_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10001` | pass | pass | pass | `production_compute_pass` | R8-8Q remediated identity and value dimension | Backfill service patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_meta_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10002` | pass | pass | pass | `production_compute_pass` | R8-8Q remediated identity and value dimension | Backfill service patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_research_synthesis` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10006` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping | Backfill service patch to formal repo; review runtime binding prepare boundary | Runtime binding prepare review; keep disabled | n/a |
| `market_stock_technical` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10009` | pass | pass | pass | `production_compute_pass` | R8-8Q remediated envelope external id and market dimension | Backfill service patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `market_fund_manager_behavior` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10007` | pass | pass | fail | `production_identity_mismatch` | Service metadata incomplete | Confirm owner/id and wrapper | Discovery + identity fix | `PROMPT-PROD-FUND-SERVICE-DISCOVERY` |
| `market_ipo_investor_behavior` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10008` | pass | pass | pass | `production_compute_pass` | R8-8Q remediated market dimension wrapper | Backfill shared market subagent patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `market_capital_flow_chip` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10022` | pass | pass | pass | `production_compute_pass` | R8-8Q remediated envelope external id and market dimension | Backfill service patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `sentiment_company_radar` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10020` | pass | pass | pass | `production_compute_pass` | R8-8Q confirmed market-only production endpoint and wrapper | Preserve market-only routing | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_crash` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10012` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping | Review runtime binding prepare boundary | Runtime binding prepare review; keep disabled | n/a |
| `risk_financial_fraud` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10013` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping | Review runtime binding prepare boundary | Runtime binding prepare review; keep disabled | n/a |
| `risk_identification` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10010` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping | Review runtime binding prepare boundary | Runtime binding prepare review; keep disabled | n/a |
| `risk_compliance_review` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10011` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping | Review runtime binding prepare boundary | Runtime binding prepare review; keep disabled | n/a |
| `macro_analysis` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10014` | pass | pass | pass | `production_compute_pass` | Compute evidence only, no invoke | Prepare read-only invoke audit | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `macro_commodity_pricing` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10004` | fail | skipped | skipped | `production_health_failed` | Fixed DAG health identity missing; compute wrapper not verified | Fix production health identity and compute wrapper | Health/compute fix + resmoke | `PROMPT-PROD-COMMODITY-COMPUTE-FIX` |
| `macro_index_valuation` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10003` | skipped | skipped | skipped | `production_semantic_deferred` | Macro signal not owner-confirmed | Owner semantic decision | Owner decision then wrapper | `PROMPT-PROD-MACRO-INDEX-OWNER` |
| `macro_sentiment` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10018` | skipped | skipped | skipped | `production_semantic_deferred` | Likely L3/regulator semantics | Classify L2 vs L3 | Classification before smoke | `PROMPT-PROD-MACRO-SENTIMENT-L2-OR-L3` |
| `macro_industry_hotspot` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10019` | skipped | skipped | skipped | `production_semantic_deferred` | Likely L3/regulator semantics | Classify L2 vs L3 | Classification before smoke | `PROMPT-PROD-MACRO-HOTSPOT-L2-OR-L3` |
| `value_composite` | L3 | composite | `dimension_composite_result_v1` | `127.0.0.1:10015` | pass | pass | pass | `production_compute_pass` | R8-10F remediated production health identity and verified L3 value compute mapping | Prepare L3 invoke audit planning later | Keep runtime disabled until invoke audit | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `market_composite` | L3 | composite | `dimension_composite_result_v1` | `127.0.0.1:10023` | pass | pass | pass | `production_compute_pass` | L3 compute evidence only, no invoke/default runtime | Prepare L3 invoke audit planning later | Keep runtime disabled until invoke audit | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_composite` | L3 | composite | `dimension_composite_result_v1` | `127.0.0.1:10016` | pass | pass | pass | `production_compute_pass` | L3 risk gate compute evidence only, no invoke/default runtime | Prepare L3 invoke audit planning later | Keep runtime disabled until invoke audit | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `macro_composite` | L3 | composite | `dimension_composite_result_v1` | `127.0.0.1:10024` | pass | pass | pass | `production_compute_pass` | L3 macro regulator compute evidence only, no invoke/default runtime | Prepare L3 invoke audit planning later | Keep runtime disabled until invoke audit | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `decision_synthesizer` | L4 | l4 | `decision_result_v1` | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | L4 adapter not designed | Future L4 adapter/runtime design | Keep deterministic | `PROMPT-PROD-L4-ADAPTER-DESIGN` |
| `report_generator` | L4 | l4 | `report_result_v1` | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | L4 adapter not designed | Future L4 adapter/runtime design | Keep deterministic | `PROMPT-PROD-L4-ADAPTER-DESIGN` |

## Developer Execution Order

P0 remediation should now focus on the remaining production blockers:

1. `financial_data_service`: fix production `/health` JSON, then compute
   `data_bundle_v1`.
2. `macro_commodity_pricing`: fix production fixed-DAG health identity, then
   compute wrapper.
3. `entity_relation_extractor`: confirm production endpoint and
   `entity_relation_bundle_v1` wrapper.
4. `market_fund_manager_behavior`: resolve service discovery, owner metadata,
   and fixed DAG wrapper.

P1 work should backfill the R8-8Q production patches into formal service source
repositories and continue invoke audits beyond the R8-11B tiny allowlist:

1. Value family: `value_traditional_valuation`, `value_ml_valuation`,
   `value_meta_valuation`, `value_research_synthesis`.
2. Market family: `market_stock_technical`, `market_capital_flow_chip`,
   `sentiment_company_radar`, `market_ipo_investor_behavior`.
3. Existing production compute pass set not included in R8-11B: run read-only
   `/invoke` audit planning before any controlled invoke call.

P2 work should not be forced into L2:

1. `macro_index_valuation`: owner decision on macro semantics.
2. `macro_sentiment` and `macro_industry_hotspot`: L2 vs L3 classification.
3. L4 adapter/runtime design for decision and report.

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

Important production rebaseline result: R8-8Q remediated eight L1/L2 production
services that previously failed or lacked confirmed production evidence. Dev
evidence remains historical; production pass status is driven only by
production artifact roots listed in this document.

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

R8-8Q production remediation patch manifest:

```text
/tmp/lma-r8-8q-prod-service-backup/20260611T015600Z/service_patch_manifest.json
```

The R8-8Q production patch manifest covers protocol-only wrapper changes for
`value_traditional_valuation`, `value_ml_valuation`, `value_meta_valuation`,
`value_research_synthesis`, `market_stock_technical`,
`market_capital_flow_chip`, `sentiment_company_radar`, and
`market_ipo_investor_behavior`. Service owners still need to backfill these
changes into their formal source-controlled repositories. The manifest records
`business_core_changed=false`.

## R8-11B Runtime Binding Readiness Recommendation

R8-11B does not edit `runtime_bindings.json`. The following table is a
recommendation only, based on controlled production invoke smoke results.

| agent_id | compute_pass | invoke_pass | remaining risk | ready_for_runtime_binding_prepare? | requires_owner_backfill? |
| --- | --- | --- | --- | --- | --- |
| `risk_identification` | yes | yes | adapter mapped sanitized `tool_result`; strict envelope fields remain a later polish item | yes, review only | no |
| `risk_compliance_review` | yes | yes | adapter mapped sanitized `tool_result`; strict envelope fields remain a later polish item | yes, review only | no |
| `risk_crash` | yes | yes | adapter mapped sanitized `tool_result`; strict envelope fields remain a later polish item | yes, review only | no |
| `risk_financial_fraud` | yes | yes | avoid news-text payloads unless provider behavior is separately audited | yes, review only | no |
| `value_research_synthesis` | yes | yes | invoke stayed in no-LLM/template path for this smoke | yes, review only | yes, R8-8Q patch backfill |

## Next Phase

Recommended sequence:

1. R8-8R: production `/health` + `/v1/agent/compute` resmoke for remaining
   remediated agents: `financial_data_service`, `entity_relation_extractor`,
   `market_fund_manager_behavior`, and `macro_commodity_pricing`.
2. R8-11C: continue production `/v1/agent/invoke` audit planning for remaining
   compute-pass services, especially those with narrative/provider risk.
3. R8-11D: if approved, run a second tiny controlled invoke smoke for services
   whose `allow_llm=false` path is proven safe.
4. Service-owner backfill phase: move service protocol patches into each
   service's source-controlled repo and redeploy.
