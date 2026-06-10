# Fixed DAG Agent Readiness Matrix

This document is the production-first readiness matrix and remediation
playbook for the fixed DAG agent roster after Phase R8-8P-DOCS-QA.

R8-8P rebaselined readiness against confirmed production endpoints. Earlier
R8-8G/H/I/J/K/L/M controlled smoke results used dev endpoints and are now
historical evidence only. Dev evidence is useful for debugging and service
backfill, but it must never be counted as production evidence.

Production smoke artifact root:

```text
/tmp/lma-r8-8p-prod-readiness/20260610T104456Z
```

## Current Conclusion

R8-8P moved the readiness baseline from dev endpoints to production endpoints.
Only five external candidates currently reached production `/health` pass,
production `/v1/agent/compute` pass, and provider-free adapter mapping pass:
`risk_identification`, `risk_compliance_review`, `risk_financial_fraud`,
`risk_crash`, and `macro_analysis`.

The remaining production gaps are operational rather than graph-runtime
changes. Most failures are caused by production services not backfilling dev
wrapper patches, identity mismatches between service ids and fixed DAG ids,
missing or invalid production health/compute wrappers, missing production
endpoints, or unresolved semantic ownership for macro services.

This document converts those gaps into a production problem playbook. Service
owners should use the matching prompt id in
`docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md`, fix the production service or
ownership decision, redeploy, and request a production `/health` + `/compute`
resmoke. No failed item should be treated as production-ready because it passed
in dev.

## Non-Claims

- No `/v1/agent/invoke` was called.
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

## Production Coverage Summary

| Metric | Count | Notes |
| --- | ---: | --- |
| Total fixed DAG agents | 27 | Full catalog roster |
| External-service candidates | 20 | L1 evidence services and L2 analysis services |
| Production endpoint known | 18 | Confirmed production listener or production port/cwd |
| Production health pass | 14 | `/health` returned structured JSON and no unsafe content |
| Production compute pass | 13 | `/v1/agent/compute` returned HTTP 2xx structured JSON |
| Production adapter mapping pass | 5 | Mapped through main-system provider-free adapter |
| Production failed bucket | 13 | R8-8P artifact failure bucket; endpoint-missing and semantic-deferred counts are also shown separately |
| Production endpoint missing | 2 | No confirmed production endpoint |
| Production semantic deferred | 3 | Not safe to force into L2 production mapping |
| Production identity mismatch | 8 | Compute returned service/unknown primary id instead of fixed DAG id |
| Internal deterministic | 1 | `route_planner` |
| L3/L4 deferred | 6 | 4 composites plus decision/report |
| Production invoke audit candidates | 5 | Based only on production health + compute + adapter mapping pass |

Layer coverage:

| Layer/group | Production coverage |
| --- | --- |
| L1 | 0/2 production adapter pass; one health failure and one endpoint missing |
| L2 value | 0/4 production adapter pass; all four are identity mismatches |
| L2 market | 0/5 production adapter pass; identity mismatches plus one endpoint missing |
| L2 risk | 4/4 production adapter pass |
| L2 macro | 1/5 production adapter pass; remaining macro candidates failed or were deferred |
| L3 | 0/4 external production readiness; deterministic internal seams only |
| L4 | 0/2 external production readiness; deterministic internal seams only |

## Production Health+Compute+Adapter Pass Candidates

These agents have production `/health` pass, production `/v1/agent/compute`
pass, and provider-free adapter mapping pass. This is L3-style production
endpoint evidence only; it is not invoke readiness, live verification, default
invocation, or production business correctness.

| agent_id | What passed | What has not passed | Next action |
| --- | --- | --- | --- |
| `risk_identification` | Production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_compliance_review` | Production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_financial_fraud` | Production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_crash` | Production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `macro_analysis` | Production health + compute + adapter mapping | `/v1/agent/invoke`, runtime binding enablement, live flags | `PROMPT-PROD-INVOKE-AUDIT-PREP` |

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

- Current status: `production_endpoint_missing`.
- Production test result: no confirmed company-radar production endpoint was
  found.
- Problem type: production deployment / endpoint missing.
- Failure reason: no production service was mapped to fixed DAG
  `sentiment_company_radar` with market-only L2 output.
- Impact: market sentiment radar has no production evidence and must not be
  routed to risk.
- Solution: owner must provide a production endpoint that emits
  `agent_conclusion_v1` with `dimension=market`; it must not emit risk
  dimension or feed `risk_composite`.
- Service owner action: deploy/register production endpoint, document
  `external_agent_id`, add health and compute contract tests, and preserve
  market-only semantics.
- Main-system maintainer action: reject any sentiment-to-risk payload or
  runtime routing proposal.
- Retest method: production `/health` + `/compute` + adapter mapping to
  `conclusion_object_v1` with market dimension only.
- Prompt: `PROMPT-PROD-SENTIMENT-MARKET-ONLY`.

### value_traditional_valuation

- Current status: `production_identity_mismatch`.
- Production test result: production `10000` health and compute were reachable,
  but adapter rejected compute with `unknown_agent_id`.
- Problem type: production service did not backfill fixed DAG identity patch.
- Failure reason: production envelope/tool_result uses a service or legacy id
  as primary `agent_id` instead of `value_traditional_valuation`.
- Impact: value L2 production compute cannot enter the fixed DAG contract.
- Solution: production envelope and nested `tool_result` must use
  `agent_id=value_traditional_valuation`; service id stays in
  `external_agent_id`; legacy id stays only as migration metadata.
- Service owner action: backfill the dev identity wrapper into the service repo,
  redeploy production, and provide before/after identity fields.
- Main-system maintainer action: keep adapter identity gate strict.
- Retest method: production health + compute + adapter mapping to
  `conclusion_object_v1`.
- Prompt: `PROMPT-PROD-IDENTITY-FIX-VALUE-TRADITIONAL`.

### value_ml_valuation

- Current status: `production_identity_mismatch`.
- Production test result: production `10001` health and compute were reachable,
  but adapter rejected compute with `unknown_agent_id`.
- Problem type: production service did not backfill fixed DAG identity patch.
- Failure reason: production primary id remained the service id instead of
  `value_ml_valuation`.
- Impact: the dev identity remediation has not been promoted to production.
- Solution: set envelope/tool_result `agent_id=value_ml_valuation` and
  `external_agent_id=valuation_ml`; preserve `legacy_agent_id` only as
  provenance.
- Service owner action: backfill and redeploy the identity wrapper used in dev.
- Main-system maintainer action: do not relax adapter to accept `valuation_ml`
  as a primary fixed DAG id.
- Retest method: production health + compute + adapter mapping to
  `conclusion_object_v1`.
- Prompt: `PROMPT-PROD-IDENTITY-FIX-VALUE-ML`.

### value_meta_valuation

- Current status: `production_identity_mismatch`.
- Production test result: production `10002` health and compute were reachable,
  but adapter rejected compute with `unknown_agent_id`.
- Problem type: production service did not backfill fixed DAG identity patch.
- Failure reason: production payload does not use
  `value_meta_valuation` as primary fixed DAG id.
- Impact: production meta-valuation cannot contribute to value L2 evidence.
- Solution: set envelope/tool_result `agent_id=value_meta_valuation`,
  `external_agent_id=valuation_meta`, and keep legacy ids in provenance only.
- Service owner action: backfill identity wrapper, tests, and production
  deployment.
- Main-system maintainer action: keep runtime binding disabled until production
  resmoke passes.
- Retest method: production health + compute + adapter mapping to
  `conclusion_object_v1`.
- Prompt: `PROMPT-PROD-IDENTITY-FIX-VALUE-META`.

### value_research_synthesis

- Current status: `production_identity_mismatch`.
- Production test result: production `10006` health and compute were reachable,
  but adapter rejected compute with `unknown_agent_id`.
- Problem type: production service did not backfill fixed DAG identity patch.
- Failure reason: production payload does not use
  `value_research_synthesis` as primary fixed DAG id.
- Impact: analyst/research synthesis has no production adapter evidence.
- Solution: set envelope/tool_result `agent_id=value_research_synthesis`, keep
  the service-owned id in `external_agent_id`, and emit `agent_conclusion_v1`
  for value dimension.
- Service owner action: backfill wrapper and contract tests to production.
- Main-system maintainer action: keep adapter identity gate strict.
- Retest method: production health + compute + adapter mapping.
- Prompt: `PROMPT-PROD-IDENTITY-FIX-RESEARCH`.

### market_stock_technical

- Current status: `production_identity_mismatch`.
- Production test result: production `10009` health and compute were reachable,
  but adapter rejected compute with `unknown_agent_id`.
- Problem type: production service did not backfill market L2 identity wrapper.
- Failure reason: production payload primary id is not
  `market_stock_technical`.
- Impact: technical market signal has no production adapter evidence.
- Solution: set envelope/tool_result `agent_id=market_stock_technical`,
  `dimension=market`, and keep service id in `external_agent_id`.
- Service owner action: backfill identity/dimension wrapper and redeploy.
- Main-system maintainer action: reject non-market or unknown-id payloads.
- Retest method: production health + compute + adapter mapping to
  `conclusion_object_v1`.
- Prompt: `PROMPT-PROD-IDENTITY-FIX-STOCK-TECHNICAL`.

### market_capital_flow_chip

- Current status: `production_identity_mismatch`.
- Production test result: production `10022` health and compute were reachable,
  but adapter rejected compute with `unknown_agent_id`.
- Problem type: production service did not backfill market L2 identity wrapper.
- Failure reason: production payload primary id is not
  `market_capital_flow_chip`.
- Impact: capital-flow/chip signal has no production adapter evidence despite
  dev remediation.
- Solution: set envelope/tool_result `agent_id=market_capital_flow_chip`,
  `external_agent_id=money_flow` or owner-confirmed service id, and
  `dimension=market`.
- Service owner action: backfill dev patch to production; confirm production is
  not a temporary dev 8022 process.
- Main-system maintainer action: keep production endpoint classification tied
  to prod root/port, not dev starts.
- Retest method: production health + compute + adapter mapping.
- Prompt: `PROMPT-PROD-IDENTITY-FIX-CAPITAL-FLOW`.

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

- Current status: `production_identity_mismatch` and compute wrapper problem.
- Production test result: production `10008` health and compute were reachable,
  but adapter rejected payload identity/shape.
- Problem type: compute wrapper contract failure.
- Failure reason: production output is still scaffold/raw-business shaped or
  uses the wrong primary id; it is not the fixed DAG L2 market contract.
- Impact: IPO behavior cannot be used as production market L2 evidence.
- Solution: wrap production compute as
  `external_agent_compute_v0.tool_result.agent_conclusion_v1`, with
  `agent_id=market_ipo_investor_behavior` and `dimension=market`.
- Service owner action: add wrapper tests and redeploy production service.
- Main-system maintainer action: do not map raw/scaffold payloads into graph
  state.
- Retest method: production health + compute + adapter mapping.
- Prompt: `PROMPT-PROD-IPO-WRAPPER`.

### macro_commodity_pricing

- Current status: `production_health_pass_compute_failed`.
- Production test result: production `10004` `/health` passed, but
  `/v1/agent/compute` failed with `compute_http_error`.
- Problem type: production compute endpoint failure.
- Failure reason: production compute route or wrapper does not reliably return
  `external_agent_compute_v0.tool_result.agent_conclusion_v1`.
- Impact: commodity pricing has no macro L2 production adapter evidence.
- Solution: keep structured health; fix production compute wrapper/fail-soft
  path so it emits `agent_conclusion_v1` with `agent_id=macro_commodity_pricing`,
  `dimension=macro`, and target examples such as `CU`.
- Service owner action: debug compute route, add wrapper contract tests, deploy
  production fix.
- Main-system maintainer action: do not treat health pass as compute pass.
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

- Current status: `production_l3_l4_deferred`.
- Production test result: not tested as external L2; deterministic internal seam
  remains.
- Problem type: L3 adapter/runtime design not started.
- Failure reason: L3 composites need `dimension_composite_result_v1`, not L2
  `agent_conclusion_v1`.
- Impact: no external production L3 evidence.
- Solution: design an explicit L3 adapter/runtime phase.
- Service owner action: none until L3 scope is approved.
- Main-system maintainer action: keep deterministic seam.
- Retest method: future L3 phase only.
- Prompt: `PROMPT-PROD-L3-ADAPTER-DESIGN`.

### market_composite

- Current status: `production_l3_l4_deferred`.
- Production test result: not tested as external L2; deterministic internal seam
  remains.
- Problem type: L3 adapter/runtime design not started.
- Failure reason: market composite is an aggregate contract, not an L2 external
  service target.
- Impact: no external production L3 evidence.
- Solution: future L3 adapter design with explicit evidence/provenance rules.
- Service owner action: none until L3 scope is approved.
- Main-system maintainer action: keep deterministic seam.
- Retest method: future L3 phase only.
- Prompt: `PROMPT-PROD-L3-ADAPTER-DESIGN`.

### risk_composite

- Current status: `production_l3_l4_deferred`.
- Production test result: not tested as external L2; deterministic internal seam
  remains.
- Problem type: L3 adapter/runtime design not started.
- Failure reason: risk composite consumes risk member evidence; it must not
  receive sentiment-to-risk or raw risk service payloads directly.
- Impact: no external production L3 risk evidence.
- Solution: future L3 adapter design for `dimension_composite_result_v1` or
  explicit risk composite contract.
- Service owner action: none until L3 scope is approved.
- Main-system maintainer action: preserve no sentiment-to-risk rule.
- Retest method: future L3 phase only.
- Prompt: `PROMPT-PROD-L3-ADAPTER-DESIGN`.

### macro_composite

- Current status: `production_l3_l4_deferred`.
- Production test result: not tested as external L2; deterministic internal seam
  remains.
- Problem type: L3 adapter/runtime design not started.
- Failure reason: macro composite is an aggregate, not a direct L2 external
  agent.
- Impact: no external production L3 evidence.
- Solution: future L3 adapter design after macro L2 semantic issues are settled.
- Service owner action: none until L3 scope is approved.
- Main-system maintainer action: keep deterministic seam.
- Retest method: future L3 phase only.
- Prompt: `PROMPT-PROD-L3-ADAPTER-DESIGN`.

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
| `value_traditional_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10000` | pass | pass | fail | `production_identity_mismatch` | Wrong primary id | Backfill fixed DAG identity wrapper | Identity fix + resmoke | `PROMPT-PROD-IDENTITY-FIX-VALUE-TRADITIONAL` |
| `value_ml_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10001` | pass | pass | fail | `production_identity_mismatch` | Wrong primary id | Backfill `value_ml_valuation` identity wrapper | Identity fix + resmoke | `PROMPT-PROD-IDENTITY-FIX-VALUE-ML` |
| `value_meta_valuation` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10002` | pass | pass | fail | `production_identity_mismatch` | Wrong primary id | Backfill `value_meta_valuation` identity wrapper | Identity fix + resmoke | `PROMPT-PROD-IDENTITY-FIX-VALUE-META` |
| `value_research_synthesis` | L2 | value | `conclusion_object_v1` | `127.0.0.1:10006` | pass | pass | fail | `production_identity_mismatch` | Wrong primary id | Backfill research synthesis wrapper | Identity fix + resmoke | `PROMPT-PROD-IDENTITY-FIX-RESEARCH` |
| `market_stock_technical` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10009` | pass | pass | fail | `production_identity_mismatch` | Wrong primary id | Backfill market identity wrapper | Identity fix + resmoke | `PROMPT-PROD-IDENTITY-FIX-STOCK-TECHNICAL` |
| `market_fund_manager_behavior` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10007` | pass | pass | fail | `production_identity_mismatch` | Service metadata incomplete | Confirm owner/id and wrapper | Discovery + identity fix | `PROMPT-PROD-FUND-SERVICE-DISCOVERY` |
| `market_ipo_investor_behavior` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10008` | pass | pass | fail | `production_identity_mismatch` | Wrapper shape/identity problem | Emit market `agent_conclusion_v1` wrapper | IPO wrapper fix | `PROMPT-PROD-IPO-WRAPPER` |
| `market_capital_flow_chip` | L2 | market | `conclusion_object_v1` | `127.0.0.1:10022` | pass | pass | fail | `production_identity_mismatch` | Wrong primary id | Backfill capital-flow market wrapper | Identity fix + resmoke | `PROMPT-PROD-IDENTITY-FIX-CAPITAL-FLOW` |
| `sentiment_company_radar` | L2 | market | `conclusion_object_v1` | missing | skipped | skipped | skipped | `production_endpoint_missing` | No market-only prod endpoint | Deploy market-only sentiment endpoint | Endpoint + market-only wrapper | `PROMPT-PROD-SENTIMENT-MARKET-ONLY` |
| `risk_crash` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10012` | pass | pass | pass | `production_compute_pass` | Compute evidence only, no invoke | Prepare read-only invoke audit | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_financial_fraud` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10013` | pass | pass | pass | `production_compute_pass` | Compute evidence only, no invoke | Prepare read-only invoke audit | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_identification` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10010` | pass | pass | pass | `production_compute_pass` | Compute evidence only, no invoke | Prepare read-only invoke audit | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `risk_compliance_review` | L2 | risk | `conclusion_object_v1` | `127.0.0.1:10011` | pass | pass | pass | `production_compute_pass` | Compute evidence only, no invoke | Prepare read-only invoke audit | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `macro_analysis` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10014` | pass | pass | pass | `production_compute_pass` | Compute evidence only, no invoke | Prepare read-only invoke audit | Invoke audit prep only | `PROMPT-PROD-INVOKE-AUDIT-PREP` |
| `macro_commodity_pricing` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10004` | pass | fail | skipped | `production_health_pass_compute_failed` | Compute HTTP error | Fix production compute wrapper/runbook | Compute fix + resmoke | `PROMPT-PROD-COMMODITY-COMPUTE-FIX` |
| `macro_index_valuation` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10003` | skipped | skipped | skipped | `production_semantic_deferred` | Macro signal not owner-confirmed | Owner semantic decision | Owner decision then wrapper | `PROMPT-PROD-MACRO-INDEX-OWNER` |
| `macro_sentiment` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10018` | skipped | skipped | skipped | `production_semantic_deferred` | Likely L3/regulator semantics | Classify L2 vs L3 | Classification before smoke | `PROMPT-PROD-MACRO-SENTIMENT-L2-OR-L3` |
| `macro_industry_hotspot` | L2 | macro | `conclusion_object_v1` | `127.0.0.1:10019` | skipped | skipped | skipped | `production_semantic_deferred` | Likely L3/regulator semantics | Classify L2 vs L3 | Classification before smoke | `PROMPT-PROD-MACRO-HOTSPOT-L2-OR-L3` |
| `value_composite` | L3 | composite | `dimension_composite_result_v1` | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | L3 adapter not designed | Future L3 adapter/runtime design | Keep deterministic | `PROMPT-PROD-L3-ADAPTER-DESIGN` |
| `market_composite` | L3 | composite | `dimension_composite_result_v1` | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | L3 adapter not designed | Future L3 adapter/runtime design | Keep deterministic | `PROMPT-PROD-L3-ADAPTER-DESIGN` |
| `risk_composite` | L3 | composite | `dimension_composite_result_v1` | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | L3 adapter not designed | Future L3 adapter/runtime design | Keep deterministic | `PROMPT-PROD-L3-ADAPTER-DESIGN` |
| `macro_composite` | L3 | composite | `dimension_composite_result_v1` | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | L3 adapter not designed | Future L3 adapter/runtime design | Keep deterministic | `PROMPT-PROD-L3-ADAPTER-DESIGN` |
| `decision_synthesizer` | L4 | l4 | `decision_result_v1` | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | L4 adapter not designed | Future L4 adapter/runtime design | Keep deterministic | `PROMPT-PROD-L4-ADAPTER-DESIGN` |
| `report_generator` | L4 | l4 | `report_result_v1` | n/a | n/a | n/a | n/a | `production_l3_l4_deferred` | L4 adapter not designed | Future L4 adapter/runtime design | Keep deterministic | `PROMPT-PROD-L4-ADAPTER-DESIGN` |

## Developer Execution Order

P0 remediation should focus on services that block the largest amount of
production L1/L2 coverage:

1. `financial_data_service`: fix production `/health` JSON, then compute
   `data_bundle_v1`.
2. Value family identity mismatches:
   `value_traditional_valuation`, `value_ml_valuation`,
   `value_meta_valuation`, `value_research_synthesis`.
3. Market identity mismatches:
   `market_stock_technical`, `market_capital_flow_chip`.
4. `macro_commodity_pricing`: fix production compute failure.

P1 remediation should establish missing or unclear market/L1 services:

1. `entity_relation_extractor`: production endpoint and
   `entity_relation_bundle_v1` wrapper.
2. `sentiment_company_radar`: market-only production endpoint.
3. `market_ipo_investor_behavior`: production L2 market wrapper.
4. `market_fund_manager_behavior`: service discovery, owner metadata, and
   wrapper identity.

P2 work should not be forced into L2:

1. `macro_index_valuation`: owner decision on macro semantics.
2. `macro_sentiment` and `macro_industry_hotspot`: L2 vs L3 classification.
3. L3/L4 adapter/runtime design for composites, decision, and report.

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

## Next Phase

Recommended sequence:

1. R8-8Q: production remediation/backfill for health, identity, compute wrapper,
   endpoint, and semantic-decision failures.
2. R8-8R: production `/health` + `/v1/agent/compute` resmoke for remediated
   agents.
3. R8-9A: production `/v1/agent/invoke` audit planning only for the five current
   production pass candidates and any later production-pass resmoke agents.
4. R8-9B: first controlled production invoke smoke for a tiny allowlist, still
   without runtime binding enablement.
