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

R8-12 adds a default-off external compute demo bridge. The bridge can read
production `/v1/agent/compute` only when both the explicit demo flag and an
allowlist are set. It maps responses through the provider-free adapter before
they can appear in the fixed DAG workflow/report. This does not update
readiness status by itself, does not call `/v1/agent/invoke`, does not change
runtime bindings, and does not set live flags.

R8-12C adds the report-generator evidence bundle that consumes those mapped
results. It lets the final report and Web workflow details show bounded L2
single-agent summaries and L3 composite summaries, but it does not add new
endpoint evidence, does not change readiness counts, and does not deploy the
main system to production.

R8-12D adds a default-off LLM report synthesizer over the same bundle. It can
turn active L2/L3 evidence into a natural Chinese final report when explicitly
enabled, but it does not change which agents have production compute/invoke
evidence and does not enable default runtime bindings.

CS1-C1X adds the current health identity migration policy and request-as-of
temporal guard. It also records scoped production wrapper fixes for
`market_stock_technical`, `macro_analysis`, `market_ipo_investor_behavior`,
and `value_composite`, plus controlled listener recovery for the two L4
compute-default services. The CS1-C1X accelerated trace mapped `12` default-off
demo compute agents and both L4 compute-default agents for a 2024-12-31
question. Four services failed closed on future-dated outputs and must not be
counted as 2024 evidence until their service-side date semantics are fixed:
`value_traditional_valuation`, `value_ml_valuation`,
`value_meta_valuation`, and `risk_crash`. `market_ipo_investor_behavior` now
has canonical health identity, but its current production compute route remains
blocked in the integrated trace.

CS1-C2X closes those immediate C1X blockers. The four temporal-rejected
services now pass controlled production compute and adapter mapping for
`as_of=2024-12-31`, and `market_ipo_investor_behavior` now has a production
compute route that maps to `conclusion_object_v1`. `market_capital_flow_chip`
was restored on port `10022`; `market_composite` was restored on port `10023`
and maps as partial while fund-manager and sentiment members remain absent.
The C2X full logical trace called and mapped `19` demo compute agents plus both
L4 compute-default agents, with no temporal rejects. This remains compute-only
evidence and does not change runtime bindings, live flags, or invoke readiness.

CS1-C3X closes a follow-up macro composite contract issue. `macro_composite`
now emits a five-slot canonical macro member packet only:
`macro_analysis`, `macro_commodity_pricing`, `macro_index_valuation`,
`macro_sentiment`, and `macro_industry_hotspot`. The adapter rejects duplicate
or noncanonical macro members, and local stand-ins are not counted as formal
L2 evidence. The C3X trace again called/mapped `19` demo compute agents plus
both L4 compute-default agents. This does not change invoke readiness,
runtime-binding counts, or live flags. Source durability remains separate:
owner-dev handoff patches were generated for prod-only wrapper/test drift under
`/sdb/dlut/prod/backups/cs1c3x_20260622T103501Z/owner_handoffs`.

CS1-C3R adds a correction on top of C3X. The C3X checksum manifest is known to
be inconsistent for `cs1c3x_validation.txt`; the old artifact is not modified,
and C3R adds a reusable artifact-integrity helper for future phases. C3R also
hardens real-contributor semantics across L3 paths: pending/error/no-evidence
members can remain formal coverage slots, but they must have zero weight and
must not be counted as contributors or evidence refs. `market_composite` was
patched and re-smoked so absent `sentiment_company_radar` and
`market_fund_manager_behavior` are zero-weight market slots. The C3R trace
called/mapped `19` demo compute agents plus both L4 compute-default agents.
`entity_relation_extractor`, `sentiment_company_radar`, and
`market_fund_manager_behavior` remain source/owner blockers, not failed
production endpoint evidence from this phase.

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

CS1-C1X supersedes parts of that older gap statement for the current server
state: `financial_data_service`, `macro_commodity_pricing`, and
`macro_index_valuation` mapped in the accelerated trace, while
`market_stock_technical`, `macro_analysis`, `value_composite`,
`decision_synthesizer`, and `report_generator` were revalidated after scoped
wrapper or listener work. The matrix rows below retain older phase context and
should be read together with the CS1-C1X note above until a later docs
compaction updates row-by-row status text.

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
- L3 and L4 remain disabled by default. Dev main-system now has default-off
  compute handoff support for L4 `decision_result_v1` / `report_result_v1`,
  but this is not production external readiness and does not change runtime
  bindings or live flags.
- R8-10B L3 adapter tests are not live readiness and do not enable external L3
  runtime execution.
- R8-12 demo mode is default-off. It does not make any external service a
  default runtime dependency and does not promote demo output into production
  readiness.
- R8-13G closes the value L2 adapter gap found by R8-13F: the three valuation
  services now expose top-level `agent_conclusion_v1.stance` in addition to
  `normalized.stance`, so their production compute outputs map as usable value
  evidence instead of `direction_stance_missing` adapter errors.
- R8-13H adds controlled L4 candidate-port evidence for sandbox-sourced
  `decision_synthesizer` and `report_generator` services on production
  candidate ports `10025`/`10026` and dev candidate ports `8025`/`8026`.
  This is `/health` + `/v1/agent/compute` evidence only, uses deterministic
  fallback because provider credentials were unavailable, and does not promote
  either L4 service to production readiness.
- R8-13I formalizes production service roots for L4 decision/report under
  `/sdb/dlut/prod`, restarts production ports `10025`/`10026` from those roots,
  and verifies production-source `/health` + `/v1/agent/compute` + adapter
  mapping. Provider credentials were still unavailable, so LLM-backed L4
  behavior remains deferred and runtime bindings remain unchanged.
- R8-13J restarts production L4 services with provider credentials loaded into
  the process environment, verifies `llm_preflight_status=ok`, and validates
  provider-backed L4 `/v1/agent/compute` for decision and report. Runtime
  bindings and live flags remain unchanged, and `/v1/agent/invoke` is still out
  of scope.
- R8-13K completes the L4 runtime/public-transcript audit without calling
  endpoints. It adds regression coverage that provider-backed L4 outputs
  containing raw provider artifacts, secrets, endpoints, tracebacks, raw
  external JSON, or chain-of-thought markers are rejected by the adapter before
  public transcript emission.
- R8-13L adds the L4 runtime binding review checklist and a runtime-registry
  regression proving that `decision_synthesizer` and `report_generator` remain
  deterministic L4 seams in `runtime_bindings.json`, with no external agent id,
  env var, or default URL.
- R8-13M adds a metadata-only L4 runtime binding dry run for
  `decision_synthesizer` and `report_generator`. It can report proposed
  production compute URLs, missing runtime-review prerequisites, and next
  action, but it never edits `runtime_bindings.json` or enables external L4 by
  default.
- R8-13N adds a safe local L4 runtime review evidence package. It requires
  provider-compute evidence, transcript-safety evidence, rollback-plan evidence,
  and operator approval before recommending that a separate runtime-binding
  phase be opened.
- R8-13O records the current L4 runtime-review candidate package. Provider
  compute, transcript safety, and rollback plan evidence pass; operator
  approval remains pending, so runtime binding stays deferred.
- R8-13P preflights the actual runtime binding phase and finds that a direct
  JSON edit is not valid yet: the runtime schema/executor must first support an
  external L4 compute-default path.
- R8-13Q completes that approved L4 runtime phase for the two L4 services only:
  `decision_synthesizer` and `report_generator` now use
  `external_compute_default` runtime bindings pointed at production-source
  `/v1/agent/compute` ports `10025`/`10026`. The executor calls those compute
  endpoints without enabling the demo bridge, still never calls
  `/v1/agent/invoke`, and keeps non-L4 runtime bindings unchanged.

## R8-12 Demo Bridge Allowlist Boundary

The demo registry includes only loopback production compute endpoints that have
prior production compute evidence. Runtime bindings remain the only authority
for default graph behavior and are unchanged.

Recommended full-DAG demo allowlist:

- `value_traditional_valuation`
- `value_ml_valuation`
- `value_meta_valuation`
- `value_research_synthesis`
- `market_stock_technical`
- `market_capital_flow_chip`
- `sentiment_company_radar` (market-only)
- `risk_identification`
- `risk_compliance_review`
- `risk_financial_fraud`
- `risk_crash`
- `macro_analysis`
- `macro_index_valuation`
- `value_composite`
- `market_composite`
- `risk_composite`
- `macro_composite`

Excluded from the demo allowlist until a later remediation or design phase:

- `financial_data_service`
- `entity_relation_extractor`
- `market_fund_manager_behavior`
- `macro_commodity_pricing`
- `macro_sentiment`
- `macro_industry_hotspot`

`macro_index_valuation` was excluded in earlier ledgers pending owner
semantic confirmation. BG2/BG3 recorded the owner-approved macro L2 role and
production compute evidence, and BG4 included it in a default-off full-DAG QA
allowlist. This does not make it a default runtime binding.

Optional controlled L4 allowlist after R8-13J:

- `decision_synthesizer`
- `report_generator`

These L4 services must be run in explicit `decision` / `report` bridge stages.
After R8-13Q they are also the only approved `external_compute_default` runtime
bindings. This default path is still compute-only and does not imply
`/v1/agent/invoke` enablement for L4 or any lower-layer service.

## Production Coverage Summary

| Metric | Count | Notes |
| --- | ---: | --- |
| Total fixed DAG agents | 27 | Full catalog roster |
| External-service candidates | 20 | L1 evidence services and L2 analysis services |
| Production endpoint known | 19 | Confirmed production listener or production port/cwd |
| Production health pass | 20 | Latest matrix count across production candidates with structured health, including L3 and L4 production-source evidence |
| Production compute pass | 20 | Production `/v1/agent/compute` HTTP 2xx structured JSON across current evidence set, including L4 provider-backed compute |
| Production adapter mapping pass | 19 | 13 L1/L2 candidates, 4 L3 composites, and 2 L4 production-source provider-backed results mapped through the adapter |
| Controlled production invoke pass | 5 | R8-11B tiny allowlist with `allow_llm=false` and adapter mapping pass |
| Production failed bucket | 7 | Remaining failed/deferred production items in the current matrix, excluding internal deterministic/L4 |
| Production endpoint missing | 1 | `entity_relation_extractor` remains without confirmed production compute evidence in this matrix |
| Production semantic deferred | 3 | Not safe to force into L2 production mapping |
| Production identity mismatch | 1 | `market_fund_manager_behavior` remains unresolved |
| Internal deterministic | 1 | `route_planner` |
| L4 compute-default runtime enabled | 2 | Decision/report are the only `external_compute_default` bindings; both use production-source `/v1/agent/compute`, not `/v1/agent/invoke` |
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
| L4 | 2/2 production-source provider-backed compute/adapter pass; R8-13Q enables compute-default runtime for L4 only, with `/v1/agent/invoke` still disabled |

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

- Current status: `production_compute_pass` after R8-13G re-smoke.
- Production test result: production `10000` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved fixed DAG identity, value-dimension wrapper, and
  top-level direction stance gaps.
- Solution applied: production envelope and nested `tool_result` use
  `agent_id=value_traditional_valuation`, service id
  `external_agent_id=valuation_traditional`, legacy id
  `a17_traditional_valuation`, adapter-facing `dimension=value`, and top-level
  `stance` projected from `normalized.stance`.
- Remaining action: service owner backfills this production patch into the
  formal service source repository; maintainer keeps runtime disabled until
  invoke audit.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### value_ml_valuation

- Current status: `production_compute_pass` after R8-13G re-smoke.
- Production test result: production `10001` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved fixed DAG identity, value-dimension wrapper, and
  top-level direction stance gaps.
- Solution applied: production health and compute now advertise
  `agent_id=value_ml_valuation`, `external_agent_id=valuation_ml`,
  `legacy_agent_id=a16_ml_valuation`, adapter-facing `dimension=value`, and
  top-level `stance` projected from `normalized.stance`.
- Remaining action: service owner backfills the wrapper patch into formal
  source control; maintainer keeps the adapter identity gate strict.
- Prompt: `PROMPT-PROD-INVOKE-AUDIT-PREP`.

### value_meta_valuation

- Current status: `production_compute_pass` after R8-13G re-smoke.
- Production test result: production `10002` passed `/health`, passed
  `/v1/agent/compute`, and mapped to `conclusion_object_v1`.
- Problem type: resolved fixed DAG identity, value-dimension wrapper, and
  top-level direction stance gaps.
- Solution applied: production compute now emits
  `agent_id=value_meta_valuation`, `external_agent_id=valuation_meta`,
  `legacy_agent_id=a18_meta_valuation`, `dimension=value`, and top-level
  `stance` projected from `normalized.stance`.
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

- Current status: `production_l4_external_compute_default_enabled`.
- Production test result: R8-13J controlled production-source smoke passed for
  `/health` and provider-backed `/v1/agent/compute` on production port `10025`.
  R8-13Q then validated the default runtime path through the
  `external_compute_default` binding on production port `10025`.
- Problem type: L4 compute-default runtime is enabled; `/v1/agent/invoke`
  remains disabled and lower-layer runtime bindings remain out of scope.
- Failure reason: none for the L4 compute-default smoke; the current smoke
  produced a conservative `research_hold` decision because upstream evidence is
  still incomplete.
- Impact: the default fixed-DAG run now obtains `decision_result_v1` from the
  production-source L4 compute service when external compute default is not
  disabled by context/env rollback.
- Solution: keep the compute-only runtime boundary and continue improving
  upstream L1/L2/L3 evidence before interpreting L4 decisions as final
  production investment judgments.
- Service owner action: maintain production-owned L4 service source/runbook and
  provider configuration hygiene.
- Main-system maintainer action: keep `external_compute_default` limited to L4
  and preserve deterministic rollback via `disable_external_compute_default`.
- Retest method: controlled L4 runtime-default `/v1/agent/compute` smoke; no
  `/v1/agent/invoke`.
- Prompt: `PROMPT-PROD-L4-ADAPTER-DESIGN`.

### report_generator

- Current status: `production_l4_external_compute_default_enabled`.
- Production test result: R8-13J controlled production-source smoke passed for
  `/health` and provider-backed `/v1/agent/compute` on production port `10026`.
  R8-13Q then validated the default runtime path through the
  `external_compute_default` binding on production port `10026`.
- Problem type: L4 compute-default runtime is enabled; `/v1/agent/invoke`
  remains disabled and public transcript safety still depends on adapter
  validation.
- Failure reason: none for the L4 compute-default smoke; the current report
  explicitly says evidence is insufficient where upstream bundles are thin.
- Impact: the default fixed-DAG run now obtains `report_result_v1` from the
  production-source L4 compute service when external compute default is not
  disabled by context/env rollback.
- Solution: keep the compute-only runtime boundary, preserve public-safe
  transcript validation, and improve upstream evidence thickness before
  judging report quality.
- Service owner action: maintain production-owned `report_result_v1` service
  source/runbook and provider configuration hygiene.
- Main-system maintainer action: keep `external_compute_default` limited to L4,
  preserve deterministic rollback, and keep unsafe provider artifacts out of
  public workflow/report payloads.
- Retest method: controlled L4 runtime-default `/v1/agent/compute` smoke; no
  `/v1/agent/invoke`.
- Prompt: `PROMPT-PROD-L4-ADAPTER-DESIGN`.

## 2026-06-21 Phase B3 Risk Report-Material Refresh Note

Phase B3 refreshed production compute and adapter evidence for the two
file-level backfilled risk L2 report-material wrappers:

- `risk_crash`: controlled restart on production port `10012`, production
  `/health` pass, fixed-DAG `/v1/agent/compute` pass, adapter mapping to
  `conclusion_object_v1` pass.
- `risk_compliance_review`: controlled restart on production port `10011`,
  production `/health` pass, fixed-DAG `/v1/agent/compute` pass, adapter
  mapping to `conclusion_object_v1` pass.

This is not `/v1/agent/invoke` evidence, not default runtime enablement, and
does not change `live_verified` or `invoke_enabled_by_default`.

## 2026-06-21 Phase BG1 Backfill Gate Review

Phase BG1 rechecked five next-batch sandbox-to-prod backfill candidates before
any production file write, restart, or endpoint call. No candidate met the full
BG1 implementation gate, so the production readiness counts below do not
change.

| Agent | BG1 gate status | Current boundary |
| --- | --- | --- |
| `risk_financial_fraud` | `blocked_no_prod_process` | Audited prod and sandbox wrapper files already matched for the checked paths, but no production listener/process was present on port `10013`; BG1 did not start a missing service. |
| `market_capital_flow_chip` | `blocked_process_missing_manual_merge` | No production listener/process was present on port `10022`, and sandbox/prod/dev service and schema files have three-way drift that requires owner-aware merge review. |
| `macro_index_valuation` | `blocked_semantic_and_service_drift` | Production process exists on port `10003`, but sandbox/prod/dev `service.py` differ and the macro-index semantic-deferred boundary still needs owner confirmation before wrapper backfill. |
| `value_traditional_valuation` | `blocked_data_path_scope` | Production process exists on port `10000`, but sandbox changes include service wrapper material plus `tools/data_loader.py` local finance-cache/data-path behavior, outside BG1 wrapper-only scope. |
| `value_meta_valuation` | `blocked_prod_only_preserve` | Production process exists on port `10002`, but sandbox/prod/dev drift spans service, SPTS store, valuation adapter, meta agent, historical valuation, and cache/test files; prod-only model-context explanations must be preserved before any merge. |

BG1 did not call `/health`, `/v1/agent/compute`, or `/v1/agent/invoke`; did not
modify runtime bindings or live flags; and did not change model, scoring,
feature, training, data, dependency, or deployment files.

## 2026-06-21 Phase BG2 Blocker-Unlock Review

Phase BG2 resolved only blockers that could be cleared without service code
changes. It did not apply sandbox-to-prod patches.

| Agent | BG2 status | Current boundary |
| --- | --- | --- |
| `risk_financial_fraud` | `started_smoke_passed_ready_for_B2C` | Production process was restored on port `10013`; controlled `/health`, `/v1/agent/compute`, and adapter mapping passed. Current production output remains report-material thin, so B2C should only patch the audited sandbox report-material wrapper. |
| `market_capital_flow_chip` | `blocked_local_contract_failure` | No production listener was present on port `10022`; focused local contract tests still fail on legacy service-local dimension validation while fixed-DAG output uses `market`. |
| `macro_index_valuation` | `owner_semantic_approved_smoke_passed_ready_for_B2C` | Owner service docs approve the macro L2 role; existing production port `10003` passed controlled `/health`, `/v1/agent/compute`, and adapter mapping. B2C should only patch the audited sandbox report-material wrapper. |
| `value_traditional_valuation` | `blocked_model_data_scope` | Sandbox/prod drift includes valuation fusion, adapter assumptions, and data-loader/cache behavior, not only report-material wrapper changes. |
| `value_meta_valuation` | `blocked_output_semantics_scope` | Sandbox/prod drift changes valuation output behavior, including historical valuation safety-floor semantics, not only report-material wrapper changes. |

BG2 did not call `/v1/agent/invoke`; did not modify runtime bindings or live
flags; and did not change service code, model, scoring, feature, training,
data, dependency, or deployment files.

## 2026-06-21 Phase BG3 B2C Duo Report-Material Refresh

Phase BG3 file-level backfilled the two BG2-ready report-material wrappers and
then refreshed controlled production compute and adapter evidence:

- `risk_financial_fraud`: production `app/agent/core.py` report-material
  projection plus `tests/test_report_material.py`; controlled compute now
  maps to `conclusion_object_v1` with 4 evidence items, 3 research points, and
  6 adapter drivers.
- `macro_index_valuation`: production `service.py` report-material projection
  plus `tests/test_domain_payload_agent.py`; controlled compute now maps to
  `conclusion_object_v1` with 6 evidence items, 4 research points, and 7
  adapter drivers.

This is not `/v1/agent/invoke` evidence, not default runtime enablement, and
does not change `live_verified` or `invoke_enabled_by_default`.

## 2026-06-21 Phase BG4 Post-Backfill Full-DAG QA Note

Phase BG4 ran one full fixed-DAG QA trace with the default-off external compute
demo bridge and an explicit L2/L3 allowlist. It did not modify production
service code, did not change runtime bindings or live flags, and did not call
external agent invoke.

BG4 result summary:

- Demo compute called 17 allowlisted L2/L3 agents, mapped 13, and failed 4:
  `market_capital_flow_chip`, `sentiment_company_radar`, `value_composite`,
  and `market_composite`.
- L4 `external_compute_default` remained enabled in the graph. The run
  attempted `decision_synthesizer` and `report_generator`; both failed closed
  because the production ports were unavailable, so the executor kept fallback
  decision/report behavior.
- `report_input_bundle_v1`, `agent_evidence_bundle_v1`, `workflow_snapshot_v2`,
  `report_result_v1`, and `final_report.md` were saved as sanitized artifacts
  under `/tmp/lma-bg4-post-backfill-e2e-20260621_151711`.
- The four enhanced agents reached `agent_evidence_bundle_v1`:
  `risk_crash` (`7` evidence, `5` research points, `6` drivers),
  `risk_compliance_review` (`3` evidence, `3` research points, `4` drivers),
  `risk_financial_fraud` (`4` evidence, `3` research points, `6` drivers,
  still partial), and `macro_index_valuation` (`6` evidence, `4` research
  points, `7` drivers).
- `risk_composite` consumed `risk_crash`, `risk_compliance_review`, and
  `risk_financial_fraud`; `macro_composite` consumed `macro_index_valuation`.

This note is QA evidence only. It does not change the matrix production
readiness counts, does not create invoke evidence, and does not promote any
L1/L2/L3 agent into default runtime execution.

## Full 27-Agent Production Matrix

| agent_id | layer | dimension | expected_payload_or_contract | production_endpoint | production_health_status | production_compute_status | production_adapter_mapping_status | production_status | problem_summary | solution_summary | next_action | developer_prompt_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `route_planner` | L1 | l1 | `fixed_dag_plan_v1` | n/a | n/a | n/a | n/a | `production_internal_deterministic` | Internal deterministic planner | Keep deterministic | No endpoint work | n/a |
| `financial_data_service` | L1 | l1 | `data_bundle_v1` | `127.0.0.1:11000` | fail | skipped | skipped | `production_health_failed` | `/health` invalid JSON | Fix structured production health, then compute wrapper | Production health fix and resmoke | `PROMPT-PROD-HEALTH-FIX-DATA-SERVICE` |
| `entity_relation_extractor` | L1 | l1 | `entity_relation_bundle_v1` | missing | skipped | skipped | skipped | `production_endpoint_missing` | No production endpoint | Deploy/register prod endpoint and entity wrapper | Endpoint + wrapper deployment | `PROMPT-PROD-ENDPOINT-MISSING-ENTITY` |
| `value_traditional_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10000` | pass | pass | pass | `production_compute_pass` | R8-13G remediated top-level direction stance after R8-13F exposed `direction_stance_missing` | Backfill service patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_ml_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10001` | pass | pass | pass | `production_compute_pass` | R8-13G remediated top-level direction stance after R8-13F exposed `direction_stance_missing`; sandbox wrapper carries report material, adapter-verified top-level stance, and a service-owned local financial CSV fallback that uses `ann_date <= as_of` | Backfill service patch and service-owned financial cache/data path to formal repo/prod | Invoke audit prep only after prod owned data path is confirmed | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_meta_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10002` | pass | pass | pass | `production_compute_pass` | R8-13G remediated top-level direction stance after R8-13F exposed `direction_stance_missing`; sandbox wrapper carries report material and adapter-verified top-level stance | Backfill service patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `value_research_synthesis` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10006` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping; sandbox wrapper carries analyst consensus report material | Backfill service patch to formal repo; review runtime binding prepare boundary | Runtime binding prepare review; keep disabled | n/a |
| `market_stock_technical` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10009` | pass | pass | pass | `production_compute_pass` | R8-8Q remediated envelope external id and market dimension | Backfill service patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `market_fund_manager_behavior` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10007` | pass | pass | fail | `production_identity_mismatch` | Service metadata incomplete | Confirm owner/id and wrapper | Discovery + identity fix | `PROMPT-PROD-FUND-SERVICE-DISCOVERY` |
| `market_ipo_investor_behavior` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10008` | pass | pass | pass | `production_compute_pass` | R8-8Q remediated market dimension wrapper | Backfill shared market subagent patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `market_capital_flow_chip` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10022` | pass | pass | pass | `production_compute_pass` | R8-8Q remediated envelope external id and market dimension | Backfill service patch to formal repo | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `sentiment_company_radar` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10020` | pass | pass | pass | `production_compute_pass` | R8-8Q confirmed market-only production endpoint and wrapper | Preserve market-only routing | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_crash` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10012` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping; sandbox wrapper now carries model drivers/research points and a model-vintage caveat that distinguishes feature anti-lookahead from production-model training-window limits; main-system `risk_composite` preserves the caveat as report-facing member boundary material | Review runtime binding prepare boundary; run full endpoint contract after local TestClient compatibility issue is resolved | Runtime binding prepare review; keep disabled | n/a |
| `risk_financial_fraud` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10013` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping; BG2 restored the production process; BG3 backfilled public-safe report material without changing HyFormer scoring, thresholds, feature data, or provider paths | Report-material wrapper backfilled; keep runtime disabled | Runtime binding prepare review; keep disabled | n/a |
| `risk_identification` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10010` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping; sandbox wrapper now carries rule-margin/MD&A-hit risk drivers and research points; sandbox 600519.SH snapshot has 2024Q3 numeric period with explicit MD&A-missing warning | Review runtime binding prepare boundary; service owner must provide full snapshot refresh pipeline before production freshness advancement | Runtime binding prepare review; keep disabled | n/a |
| `risk_compliance_review` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10011` | pass | pass | pass | `controlled_invoke_pass` | R8-11B controlled invoke smoke passed with adapter mapping | Review runtime binding prepare boundary | Runtime binding prepare review; keep disabled | n/a |
| `macro_analysis` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10014` | pass | pass | pass | `production_compute_pass` | Compute evidence only, no invoke; sandbox wrapper now carries macro-regime/signal-table/sector-rotation report material without changing deterministic cycle rules | Prepare read-only invoke audit | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `macro_commodity_pricing` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10004` | fail | skipped | skipped | `production_health_failed` | Fixed DAG health identity missing; compute wrapper not verified | Fix production health identity and compute wrapper | Health/compute fix + resmoke | `PROMPT-PROD-COMMODITY-COMPUTE-FIX` |
| `macro_index_valuation` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10003` | pass | pass | pass | `production_compute_pass` | Owner approval exists in service repo; BG2 refreshed controlled production compute and adapter evidence; BG3 backfilled public-safe macro-index report material without changing percentile/statistical core, target normalization, data, or deploy files | Report-material wrapper backfilled; keep runtime disabled | Invoke audit prep only after owner review; no default runtime enablement | `PROMPT-PROD-MACRO-INDEX-OWNER` |
| `macro_sentiment` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10018` | skipped | skipped | skipped | `production_semantic_deferred` | Likely L3/regulator semantics | Classify L2 vs L3 | Classification before smoke | `PROMPT-PROD-MACRO-SENTIMENT-L2-OR-L3` |
| `macro_industry_hotspot` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10019` | skipped | skipped | skipped | `production_semantic_deferred` | Likely L3/regulator semantics | Classify L2 vs L3 | Classification before smoke | `PROMPT-PROD-MACRO-HOTSPOT-L2-OR-L3` |
| `value_composite` | L3 | composite | `dimension_composite_result_v1` | `127.0.0.1:10015` | pass | pass | pass | `production_compute_pass` | R8-10F remediated production health identity and verified L3 value compute mapping | Prepare L3 invoke audit planning later | Keep runtime disabled until invoke audit | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `market_composite` | L3 | composite | `dimension_composite_result_v1` | `127.0.0.1:10023` | pass | pass | pass | `production_compute_pass` | L3 compute evidence only, no invoke/default runtime | Prepare L3 invoke audit planning later | Keep runtime disabled until invoke audit | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_composite` | L3 | composite | `dimension_composite_result_v1` | `127.0.0.1:10016` | pass | pass | pass | `production_compute_pass` | L3 risk gate compute evidence only, no invoke/default runtime | Prepare L3 invoke audit planning later | Keep runtime disabled until invoke audit | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `macro_composite` | L3 | composite | `dimension_composite_result_v1` | `127.0.0.1:10024` | pass | pass | pass | `production_compute_pass` | L3 macro regulator compute evidence only, no invoke/default runtime | Prepare L3 invoke audit planning later | Keep runtime disabled until invoke audit | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `decision_synthesizer` | L4 | l4 | `decision_result_v1` | `127.0.0.1:10025` | pass | pass | pass | `production_l4_external_compute_default_enabled` | R8-13J production-source provider-backed compute passed; R8-13K/R8-13L/R8-13M/R8-13N/R8-13O/R8-13P completed transcript, evidence, rollback, and schema preflight gates; R8-13Q switches this L4 row to `external_compute_default` and validates controlled default `/v1/agent/compute` execution | Keep compute-only L4 runtime default monitored; improve upstream evidence before relying on decision quality | `/v1/agent/invoke` remains disabled; deterministic rollback available via `disable_external_compute_default` | `PROMPT-PROD-L4-ADAPTER-DESIGN` |
| `report_generator` | L4 | l4 | `report_result_v1` | `127.0.0.1:10026` | pass | pass | pass | `production_l4_external_compute_default_enabled` | R8-13J production-source provider-backed compute passed; R8-13K/R8-13L/R8-13M/R8-13N/R8-13O/R8-13P completed transcript, evidence, rollback, and schema preflight gates; R8-13Q switches this L4 row to `external_compute_default` and validates controlled default `/v1/agent/compute` execution | Keep compute-only L4 runtime default monitored; improve upstream report materials before judging final report richness | `/v1/agent/invoke` remains disabled; deterministic rollback available via `disable_external_compute_default` | `PROMPT-PROD-L4-ADAPTER-DESIGN` |

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
3. L4 runtime-default monitoring after R8-13Q; this is compute-only L4 default
   execution, not `/v1/agent/invoke` enablement.

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
