# Controlled Readiness Smoke Log

This log records sanitized controlled readiness evidence for fixed-DAG external
service candidates. It is not public transcript content and must not include raw
service responses, credentials, traceback text, provider raw responses, or
chain-of-thought.

R8-8G through R8-8M entries below are dev-only historical evidence unless a
section explicitly says production. Dev evidence is useful for debugging and
service backfill, but it is not production readiness.

## 2026-06-22 - BF-COMPLETE-X sandbox-to-prod backfill completion wave

| Field | Value |
| --- | --- |
| Phase | BF-COMPLETE-X |
| Artifact root | `/tmp/lma-full-backfill-completion-20260622T135236Z` |
| Endpoint calls | controlled production `/health` and `/v1/agent/compute` only |
| External agent invoke called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Provider called | no |
| Production service code changed | yes, scoped `entity_relation_extractor` and `sentiment_company_radar` wrapper files |

Backfill ledger:

- Initial full-audit baseline: `29/31` in-scope change units complete.
- BF-COMPLETE-X closes `entity_relation_extractor__entity_relation_bundle_v1`
  and `sentiment_company_radar__market_only_wrapper`.
- Final ledger: `31/31` in-scope sandbox-to-prod backfill units complete.

Controlled service evidence:

- `entity_relation_extractor` on production port `10017` returned
  `external_agent_health_v0`, mapped compute to `entity_relation_bundle_v1`,
  and propagated the external entity bundle into the controlled graph trace.
- `sentiment_company_radar` on production port `10020` returned
  `external_agent_health_v0`, mapped compute to market
  `conclusion_object_v1`, preserved `external_agent_id=company_radar_agent`,
  and routed only to `market_composite`.

Integrated trace:

- Fixed-DAG `as_of`: `2024-12-31`.
- Demo compute called `21` allowlisted agents, mapped `20`, and failed
  `value_traditional_valuation` because that endpoint timed out.
- L1 external mapped count: `2`.
- L4 compute-default mapped both `decision_synthesizer` and
  `report_generator`.
- PublicTurn validation passed and the original public object passed unsafe
  scan before artifact scrub.

Non-claims:

- This is not external invoke evidence.
- This does not enable non-L4 runtime bindings.
- This does not set live flags.
- This does not call a provider.
- This does not change business models, scoring, training, data sources, or
  fusion algorithms.

## 2026-06-22 - CS1-C3R remaining evidence and durability recovery

| Field | Value |
| --- | --- |
| Phase | CS1-C3R |
| Artifact root | `/tmp/lma-cs1c3r-evidence-durability-20260622T121352Z` |
| Endpoint calls | controlled production `/health` and `/v1/agent/compute` only |
| External agent invoke called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Provider called | no |
| Production service code changed | yes, `market_composite` wrapper/test files only |

Controlled service result:

- `market_composite` returned health ok, compute ok, and adapter partial after
  a scoped restart of port `10023`.
- Pending `sentiment_company_radar` and `market_fund_manager_behavior` slots
  are retained as formal market coverage slots with `weight=0`, no
  `contributing_agents` entry, and no `evidence_refs`.

Integrated trace:

- Fixed-DAG `as_of`: `2024-12-31`.
- Default-off demo compute called and mapped `19` allowlisted agents.
- L4 compute-default called and mapped both `decision_synthesizer` and
  `report_generator`.
- L3 member summaries are nonempty: value `4`, market `5`, risk `4`, macro `5`.
- Temporal rejected agents: none.
- PublicTurn validation passed and the original public object passed unsafe
  scan before artifact scrub.

Non-claims:

- This is not external invoke evidence.
- This does not enable non-L4 runtime bindings.
- This does not set live flags.
- This does not prove provider-backed report synthesis.
- This does not change business models, scoring, training, data sources, or
  fusion algorithms.

## 2026-06-22 - CS1-C3X source durability and macro contract closure

| Field | Value |
| --- | --- |
| Phase | CS1-C3X |
| Artifact root | `/tmp/lma-cs1c3x-source-durability-20260622T103501Z` |
| Endpoint calls | controlled production `/health` and `/v1/agent/compute` only |
| External agent invoke called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Provider called | no |
| Production service code changed | yes, scoped wrapper/test files only |

Controlled service result:

- `macro_composite` returned health ok, compute ok, and adapter partial with
  canonical macro members only:
  `macro_analysis`, `macro_commodity_pricing`, `macro_index_valuation`,
  `macro_sentiment`, and `macro_industry_hotspot`.
- `market_capital_flow_chip` local contract drift tests were repaired and
  focused tests passed; no restart was needed for that test/schema-only
  contract closure.

Integrated trace:

- Fixed-DAG `as_of`: `2024-12-31`.
- Default-off demo compute called and mapped `19` allowlisted agents.
- Temporal rejected agents: none.
- L4 compute-default called and mapped both `decision_synthesizer` and
  `report_generator`.
- `macro_composite` emitted five formal macro slots; the two missing macro L2
  services remained pending/partial with zero weight and were not counted as
  real L2 evidence.
- PublicTurn validation passed and the original public object passed unsafe
  scan before artifact scrub.

Non-claims:

- This is not external invoke evidence.
- This does not enable non-L4 runtime bindings.
- This does not set live flags.
- This does not prove provider-backed report synthesis.
- This does not change business models, scoring, training, data sources, or
  fusion algorithms.

## 2026-06-22 - CS1-C2X temporal market public closure

| Field | Value |
| --- | --- |
| Phase | CS1-C2X |
| Artifact root | `/tmp/lma-cs1c2x-temporal-market-public-20260622T092218Z` |
| Endpoint calls | controlled production `/health` and `/v1/agent/compute` only |
| External agent invoke called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Provider called | no |
| Production service code changed | yes, scoped wrapper/protocol files only |

Controlled service results:

- `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, `risk_crash`, `market_ipo_investor_behavior`, and
  `market_capital_flow_chip` all returned health ok, compute ok, and adapter
  complete for `as_of=2024-12-31`.
- `market_composite` returned health ok, compute partial, and adapter partial;
  this is expected while `market_fund_manager_behavior` and
  `sentiment_company_radar` remain absent.

Integrated trace:

- Fixed-DAG `as_of`: `2024-12-31`.
- Default-off demo compute called and mapped `19` allowlisted agents.
- Temporal rejected agents: none.
- L4 compute-default called and mapped both `decision_synthesizer` and
  `report_generator`.
- PublicTurn validation passed.
- Public object unsafe scan passed before artifact scrub.

Non-claims:

- This is not external invoke evidence.
- This does not enable non-L4 runtime bindings.
- This does not set live flags.
- This does not prove provider-backed report synthesis.
- This does not change business models, scoring, training, data sources, or
  fusion algorithms.

## 2026-06-22 - CS1-C1X accelerated bulk readiness convergence

| Field | Value |
| --- | --- |
| Phase | CS1-C1X |
| Artifact root | `/tmp/lma-cs1c1x-bulk-remediation-20260622T081402Z` |
| Endpoint calls | controlled production `/health` and `/v1/agent/compute` only |
| External agent invoke called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Provider called | no |
| Production service code changed | yes, scoped wrapper files only |
| L4 runtime-default path | recovered listeners and mapped both compute-default services |

Health re-audit:

- Canonical health pass:
  `market_ipo_investor_behavior`, `value_composite`,
  `market_stock_technical`, `macro_analysis`, `decision_synthesizer`,
  `report_generator`.
- Compatibility health pass:
  `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, `risk_crash`, `risk_financial_fraud`,
  `risk_identification`, `risk_compliance_review`,
  `macro_commodity_pricing`, `risk_composite`, `macro_composite`.
- Compatibility health pass remains migration debt and is not compute,
  adapter, invoke, or runtime evidence.

Integrated trace:

- Fixed-DAG `as_of`: `2024-12-31`.
- Default-off demo compute called `17` allowlisted L1/L2/L3 agents, mapped
  `12`, and failed closed `5`.
- Mapped demo agents:
  `financial_data_service`, `value_research_synthesis`,
  `market_stock_technical`, `risk_financial_fraud`, `risk_identification`,
  `risk_compliance_review`, `macro_analysis`, `macro_commodity_pricing`,
  `macro_index_valuation`, `value_composite`, `risk_composite`,
  `macro_composite`.
- Fail-closed demo agents:
  `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, and `risk_crash` failed the request-as-of temporal
  guard; `market_ipo_investor_behavior` remains a compute-route blocker.
- L4 compute-default called and mapped both `decision_synthesizer` and
  `report_generator`.
- `report_input_bundle_v1` validation passed.

Non-claims:

- This is not external invoke evidence.
- This does not enable non-L4 runtime bindings.
- This does not set live flags.
- This does not prove provider-backed report synthesis.
- This does not count future-dated failed-closed service outputs as real
  2024 evidence.

## 2026-06-21 - Phase BG4 post-backfill full-DAG E2E QA

| Field | Value |
| --- | --- |
| Phase | BG4 |
| Question | `请从估值、市场、风险和宏观角度分析贵州茅台 600519.SH 当前是否值得关注。` |
| Execution path | fixed DAG full graph with default-off external compute demo bridge |
| Endpoint calls | allowlisted production `/v1/agent/compute` only; no `/health` in this phase |
| External agent invoke called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Production service code changed | no |
| L4 runtime-default path | preserved; `decision_synthesizer` and `report_generator` attempted and failed closed |
| Artifact root | `/tmp/lma-bg4-post-backfill-e2e-20260621_151711` |

The BG4 QA run saved sanitized `report_input_bundle_v1`,
`agent_evidence_bundle_v1`, `workflow_snapshot_v2`, `report_result_v1`, and
final report artifacts. It did not write raw service responses to the
repository.

Result summary:

| Item | Result |
| --- | --- |
| Demo compute called | 17 allowlisted L2/L3 agents |
| Demo compute mapped | 13 agents |
| Demo compute failed | `market_capital_flow_chip`, `sentiment_company_radar`, `value_composite`, `market_composite` |
| L4 compute-default mapped | none |
| L4 compute-default failed | `decision_synthesizer`, `report_generator` |
| `report_input_bundle_v1` validation | pass |
| `report_result_v1` validation | pass |
| Artifact unsafe scan | pass |

Enhanced-material summary:

| Agent | Status in bundle | Evidence | Research points | Drivers | Notes |
| --- | --- | --- | --- | --- | --- |
| `risk_crash` | complete | 7 | 5 | 6 | Consumed by `risk_composite`. |
| `risk_compliance_review` | complete | 3 | 3 | 4 | Consumed by `risk_composite`. |
| `risk_financial_fraud` | partial | 4 | 3 | 6 | Consumed by `risk_composite` with low weight because the feature/model path was unavailable for the requested `as_of`. |
| `macro_index_valuation` | complete | 6 | 4 | 7 | Consumed by `macro_composite` as an owner-approved macro L2 direction signal. |

Report quality notes:

- The fallback final report expanded valuation, market, risk, compliance,
  financial-fraud, crash-risk, macro-analysis, and macro-index valuation
  material from `agent_evidence_bundle_v1`.
- The report remained a fallback report, not an external L4 or real-provider
  report: the L4 compute-default services were unavailable and configured LLM
  report synthesis had no credential available in the current process
  environment.
- Market coverage remained partial because market flow, sentiment, and market
  composite endpoints did not map in this run.

Non-claims:

- This is default-off demo QA, not default runtime enablement.
- This is not invoke evidence.
- This did not inspect or change `.env` values.
- This did not modify `config/fixed_dag/runtime_bindings.json`.
- This did not set `live_verified=true` or
  `invoke_enabled_by_default=true`.
- This does not change production readiness counts.
- Raw service responses, credentials, traceback text, provider raw responses,
  and chain-of-thought were not stored in the repository.

## 2026-06-21 - Phase BG3 B2C duo report-material controlled compute smoke

| Field | Value |
| --- | --- |
| Phase | BG3 |
| Production service roots | `/sdb/dlut/prod/财务造假风险智能体`, `/sdb/dlut/prod/股票指数估值智能体` |
| Production ports | `risk_financial_fraud=10013`, `macro_index_valuation=10003` |
| Endpoint calls | controlled production `/health` and `/v1/agent/compute` only |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Backup root | `/sdb/dlut/prod/backups/bg3_20260621_145721` |
| Smoke artifact root | `/tmp/lma-bg3-b2c-duo-20260621_145721` |

Phase BG3 applied only file-level public-safe report-material wrapper changes
for the two target services, restarted only those services, and then exercised
their fixed-DAG `/v1/agent/compute` request shape. The smoke did not write raw
service responses to the repository.

Result summary:

| Agent | Health | Compute | Adapter mapping | Report material |
| --- | --- | --- | --- | --- |
| `risk_financial_fraud` | pass, `external_agent_health_v0`, service id `financial_fraud_agent` | pass, `external_agent_compute_v0`, `agent_conclusion_v1`, `agent_id=risk_financial_fraud`, `role=gate_member`, `status=partial` | pass, `conclusion_object_v1`, `status=partial` | 4 evidence items, 3 research points, 6 adapter drivers |
| `macro_index_valuation` | pass, `external_agent_health_v0`, service id `macro_index_valuation`, external id `valuation_index` | pass, `external_agent_compute_v0`, `agent_conclusion_v1`, `agent_id=macro_index_valuation`, `dimension=macro`, `status=ok` | pass, `conclusion_object_v1`, `status=complete` | 6 evidence items, 4 research points, 7 adapter drivers |

Non-claims:

- This did not call `/v1/agent/invoke`.
- This did not inspect or change `.env` values.
- This did not modify `config/fixed_dag/runtime_bindings.json`.
- This did not set `live_verified=true` or
  `invoke_enabled_by_default=true`.
- This does not make either L2 service a default runtime binding.
- This does not claim model, scoring, feature, training, data, dependency, or
  deployment changes.
- Raw service responses, credentials, traceback text, provider raw responses,
  and chain-of-thought were not stored in the repository.

## 2026-06-21 - Phase BG2 blocker-unlock controlled compute smoke

| Field | Value |
| --- | --- |
| Phase | BG2 |
| Production service roots | `/sdb/dlut/prod/财务造假风险智能体`, `/sdb/dlut/prod/股票指数估值智能体` |
| Production ports | `risk_financial_fraud=10013`, `macro_index_valuation=10003` |
| Endpoint calls | controlled production `/health` and `/v1/agent/compute` only |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Smoke artifact root | `/tmp/lma-bg2-blocker-unlock-20260621_143632` |

Phase BG2 restored the missing `risk_financial_fraud` production process from
its prod service root, then exercised only compute-path readiness for
`risk_financial_fraud` and `macro_index_valuation`. The smoke did not write raw
service responses to the repository.

Result summary:

| Agent | Health | Compute | Adapter mapping | Report material |
| --- | --- | --- | --- | --- |
| `risk_financial_fraud` | pass, `external_agent_health_v0`, service id `financial_fraud_agent` | pass, `external_agent_compute_v0`, `agent_conclusion_v1`, `agent_id=risk_financial_fraud`, `role=gate_member`, `status=partial` | pass, `conclusion_object_v1`, `status=partial` | 1 evidence item, 0 research points, 1 driver |
| `macro_index_valuation` | pass, `external_agent_health_v0`, service id `macro_index_valuation`, external id `valuation_index` | pass, `external_agent_compute_v0`, `agent_conclusion_v1`, `agent_id=macro_index_valuation`, `dimension=macro`, `status=ok` | pass, `conclusion_object_v1`, `status=complete` | 3 evidence items, 0 research points, 0 drivers |

Non-claims:

- This did not call `/v1/agent/invoke`.
- This did not modify `.env`.
- This did not modify `config/fixed_dag/runtime_bindings.json`.
- This did not set `live_verified=true` or
  `invoke_enabled_by_default=true`.
- This does not make either L2 service a default runtime binding.
- This does not claim model, scoring, feature, training, data, dependency, or
  deployment changes.
- Raw service responses, credentials, traceback text, provider raw responses,
  and chain-of-thought were not stored in the repository.

## 2026-06-21 - Phase B3 risk report-material controlled restart + compute smoke

| Field | Value |
| --- | --- |
| Phase | B3 |
| Production service roots | `/sdb/dlut/prod/股价崩盘风险智能体`, `/sdb/dlut/prod/公告合规审查智能体` |
| Production ports | `risk_crash=10012`, `risk_compliance_review=10011` |
| Endpoint calls | controlled production `/health` and `/v1/agent/compute` only |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Restart artifact root | `/tmp/lma-b3-risk-report-material-restart-20260621_132817` |
| Smoke artifact root | `/tmp/lma-b3-risk-report-material-smoke-20260621_133101` |

Phase B3 restarted only the two B2A/B2B backfilled risk L2 services from their
production roots and then exercised their fixed-DAG `/v1/agent/compute` request
shape. The smoke did not write raw service responses to the repository.

Result summary:

| Agent | Health | Compute | Adapter mapping | Report material |
| --- | --- | --- | --- | --- |
| `risk_crash` | pass, `external_agent_health_v0`, service id `crash_risk`, fixed DAG id `risk_crash` | pass, `external_agent_compute_v0`, `agent_conclusion_v1`, `agent_id=risk_crash`, `role=gate_member` | pass, `conclusion_object_v1`, `status=complete` | 7 evidence items, 5 research points, 6 drivers |
| `risk_compliance_review` | pass, `external_agent_health_v0`, service id `announcement_compliance` | pass, `external_agent_compute_v0`, `agent_conclusion_v1`, `agent_id=risk_compliance_review`, `role=gate_member` | pass, `conclusion_object_v1`, `status=complete` | 3 evidence items, 3 research points, 5 drivers |

Non-claims:

- This did not call `/v1/agent/invoke`.
- This did not modify `.env`.
- This did not modify `config/fixed_dag/runtime_bindings.json`.
- This did not set `live_verified=true` or
  `invoke_enabled_by_default=true`.
- This does not make either risk L2 service a default runtime binding.
- This does not claim model, scoring, rubric, feature, data, dependency, or
  deployment changes.
- Raw service responses, credentials, traceback text, provider raw responses,
  and chain-of-thought were not stored in the repository.

## 2026-06-19 - R8-13Q L4 runtime-binding default compute smoke

| Field | Value |
| --- | --- |
| Phase | R8-13Q |
| Runtime path | `runtime_bindings.json` external L4 compute default |
| Demo bridge enabled | no |
| Agents called | `decision_synthesizer`, `report_generator` |
| Endpoint calls | controlled `/v1/agent/compute` for L4 decision/report only |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | yes, L4 rows only |
| L4 live verification flag | yes, L4 compute-default smoke only |
| `.env` changed | no |

Result summary:

| Field | Value |
| --- | --- |
| Execution validation | pass, `validate_dag_execution_result=ok` |
| Default-called agents | `decision_synthesizer`, `report_generator` |
| Default-mapped agents | `decision_synthesizer`, `report_generator` |
| Failed agents | none |
| Decision schema | `decision_result_v1` |
| Decision | `research_hold` |
| Decision status | `pending_implementation` |
| Report schema | `report_result_v1` |
| Report status | `complete` |
| Report title | `贵州茅台(600519.SH) 固定流程投资研判报告` |
| Report sections / evidence cards | 5 / 5 |

Non-claims:

- This did not call `/v1/agent/invoke`.
- This did not modify `.env`.
- The L4 `live_verified=true` fields mean the compute-default runtime smoke
  passed for the two L4 `/v1/agent/compute` bindings only; they are not
  `/invoke` evidence and do not apply to L1/L2/L3 services.
- This did not expose raw provider output, credentials, endpoint URLs, raw graph
  messages, traceback text, or chain-of-thought.
- The public `external_invoked` transcript claim remains false; the runtime
  compute-default evidence is recorded under bounded
  `external_compute_default_*` provenance fields.

## 2026-06-19 - R8-13J L4 provider-backed controlled compute smoke

| Field | Value |
| --- | --- |
| Phase | R8-13J |
| Production service roots | `/sdb/dlut/prod/决策融合智能体`, `/sdb/dlut/prod/报告生成智能体` |
| Production ports | `decision_synthesizer=10025`, `report_generator=10026` |
| Endpoint calls | controlled `/health` and `/v1/agent/compute` for L4 decision/report only |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Provider raw response stored | no |

R8-13J restarts the production L4 service processes with provider credentials
loaded from the existing production main-system `.env` into the process
environment. The `.env` file itself was not modified and no credential values
were printed. The smoke validates the provider-backed L4 compute path through
the default-off main-system bridge and a direct metadata check.

Health result:

| Agent | Port | Source version | Health | Provider preflight |
| --- | ---: | --- | --- | --- |
| `decision_synthesizer` | 10025 | `0.1.0-production-source` | pass | `ok` |
| `report_generator` | 10026 | `0.1.0-production-source` | pass | `ok` |

Default-off bridge compute result:

| Agent | Mapping | Result schema | Result status | Public result |
| --- | --- | --- | --- | --- |
| `decision_synthesizer` | pass | `decision_result_v1` | `partial` | `decision=manual_review`, `reasoning_trace` count 4 |
| `report_generator` | pass | `report_result_v1` | `complete` | 5 sections, 5 evidence cards in the bridge smoke |

Direct service metadata check:

| Agent | Provider invoked | LLM output used | Warnings |
| --- | --- | --- | ---: |
| `decision_synthesizer` | true | true | 0 |
| `report_generator` | true | true | 0 |

Sanitized report result:

- Title: `贵州茅台（600519.SH）综合研判报告（2026-06-19）`.
- Final decision context: `manual_review`.
- The report names the main conflict: positive value signal versus weaker
  market signal, macro valuation pressure, and risk manual-review gate.
- The report keeps limitations visible: no L1 real-time data path, incomplete
  non-value dimensions, risk manual review, and default-off L4 compute boundary.

Non-claims:

- This does not call `/v1/agent/invoke`.
- This does not set `live_verified=true`.
- This does not set `invoke_enabled_by_default=true`.
- This does not modify `config/fixed_dag/runtime_bindings.json`.
- This does not make the default graph path depend on L4 services.
- This does not store raw provider output, credentials, endpoint URLs, or raw
  graph messages in the repository.

## 2026-06-19 - R8-13I L4 production-source controlled smoke

| Field | Value |
| --- | --- |
| Phase | R8-13I |
| Production service roots | `/sdb/dlut/prod/决策融合智能体`, `/sdb/dlut/prod/报告生成智能体` |
| Development candidate roots | `/sdb/dlut/sandbox/r8-13a/services/prod/决策融合智能体`, `/sdb/dlut/sandbox/r8-13a/services/prod/报告生成智能体` |
| Production ports | `decision_synthesizer=10025`, `report_generator=10026` |
| Development ports | `decision_synthesizer=8025`, `report_generator=8026` |
| Endpoint calls | controlled `/health` and `/v1/agent/compute` for L4 decision/report only |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Provider raw response stored | no |

R8-13I formalizes the L4 service source under `/sdb/dlut/prod` and restarts
the production ports from those service roots. The production services import
the production main-system tree, with a minimal L4 helper backfill in
`/sdb/dlut/prod/langgraph-my-agent/src/react_agent/`. Development candidate
ports remain on the sandbox service roots.

Health result:

| Environment | Agent | Port | Source version | Health | Provider preflight |
| --- | --- | ---: | --- | --- | --- |
| production source | `decision_synthesizer` | 10025 | `0.1.0-production-source` | pass | `missing_credential` |
| production source | `report_generator` | 10026 | `0.1.0-production-source` | pass | `missing_credential` |
| development candidate | `decision_synthesizer` | 8025 | `0.1.0-sandbox` | pass | `missing_credential` |
| development candidate | `report_generator` | 8026 | `0.1.0-sandbox` | pass | `missing_credential` |

Compute + adapter mapping result:

| Environment | Decision mapping | Report mapping | Decision status | Report status | Report shape | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| production source ports 10025/10026 | pass | pass | `pending_implementation` | `pending_implementation` | 6 sections, 5 evidence cards | Provider credentials absent, so both services used deterministic fallback. |
| development candidate ports 8025/8026 | pass | pass | `pending_implementation` | `pending_implementation` | 6 sections, 5 evidence cards | Same request path with loopback URL overrides. |

Sanitized details:

- `decision_synthesizer` mapped to `decision_result_v1`.
- `report_generator` mapped to `report_result_v1`.
- `report_input_bundle_v1` validation passed before each report request.
- Production port process cwd now points at `/sdb/dlut/prod/决策融合智能体`
  and `/sdb/dlut/prod/报告生成智能体`.
- Development port process cwd remains under the sandbox service tree.

Non-claims:

- This does not call `/v1/agent/invoke`.
- This does not set `live_verified=true`.
- This does not set `invoke_enabled_by_default=true`.
- This does not modify `config/fixed_dag/runtime_bindings.json`.
- This does not make the default graph path depend on L4 services.
- This does not verify provider-backed LLM decision/report behavior, because
  provider credentials were unavailable.

## 2026-06-19 - R8-13H L4 service controlled smoke

| Field | Value |
| --- | --- |
| Phase | R8-13H |
| Service roots | `/sdb/dlut/sandbox/r8-13a/services/prod/决策融合智能体`, `/sdb/dlut/sandbox/r8-13a/services/prod/报告生成智能体` |
| Production candidate ports | `decision_synthesizer=10025`, `report_generator=10026` |
| Development candidate ports | `decision_synthesizer=8025`, `report_generator=8026` |
| Endpoint calls | controlled `/health` and `/v1/agent/compute` for L4 decision/report only |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Provider raw response stored | no |

R8-13H starts sandbox L4 service wrappers on both production-candidate and
development-candidate loopback ports, then validates the default-off
main-system compute bridge with an explicit L4 allowlist. The services are
still sourced from sandbox directories, so this smoke is candidate-port
evidence and not formal production service-source readiness.

Health result:

| Environment | Agent | Port | Health | Provider preflight |
| --- | --- | ---: | --- | --- |
| production candidate | `decision_synthesizer` | 10025 | pass | `missing_credential` |
| production candidate | `report_generator` | 10026 | pass | `missing_credential` |
| development candidate | `decision_synthesizer` | 8025 | pass | `missing_credential` |
| development candidate | `report_generator` | 8026 | pass | `missing_credential` |

Compute + adapter mapping result:

| Environment | Decision mapping | Report mapping | Decision status | Report status | Notes |
| --- | --- | --- | --- | --- | --- |
| production candidate ports 10025/10026 | pass | pass | `pending_implementation` | `pending_implementation` | Provider credentials absent, so both services used deterministic fallback. |
| development candidate ports 8025/8026 | pass | pass | `pending_implementation` | `pending_implementation` | Same request path with loopback URL overrides. |

Sanitized details:

- `decision_synthesizer` mapped to `decision_result_v1`.
- `report_generator` mapped to `report_result_v1`.
- `report_input_bundle_v1` validation passed before the L4 report request.
- The mapped report contained 6 sections and 5 evidence cards in both runs.
- The L4 report limitation states that the L4 report service is only running
  through the explicit compute allowlist and does not change default runtime
  configuration.

Non-claims:

- This does not call `/v1/agent/invoke`.
- This does not set `live_verified=true`.
- This does not set `invoke_enabled_by_default=true`.
- This does not modify `config/fixed_dag/runtime_bindings.json`.
- This does not make the default graph path depend on L4 services.
- This does not prove formal production service-source readiness, because the
  service roots remain under the sandbox tree.

## 2026-06-18 - R8-13N L3 explanation and report provider validation

| Field | Value |
| --- | --- |
| Phase | R8-13N |
| Artifact directory | `/tmp/lma-r8-13n-l3-real-provider-demo/20260618T061151Z` |
| Main-system mode | default-off L3 explanation synthesis + default-off LLM report synthesis |
| Provider model | `openai/deepseek-v4-flash` |
| Endpoint calls | none |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Raw provider response stored | no |

R8-13N validates the main-system L3 language explanation seam and final LLM
report synthesis seam with the configured provider. The validation uses local
public-safe fixture conclusions for four L2 agents, builds deterministic L3
composites, then lets the L3 explanation layer add bounded `research_points`
before `report_input_bundle_v1` and final report synthesis.

Sanitized QA result:

- L3 explanation attempted: yes.
- L3 provider invoked: yes.
- L3 explanation used: yes.
- Final report synthesis attempted: yes.
- Final report provider invoked: yes.
- Final LLM report used: yes.
- `report_input_bundle_v1` validation: pass.
- `report_result_v1` validation: pass.

Non-claims:

- This is not external agent endpoint readiness.
- This does not call `/health`, `/v1/agent/compute`, or `/v1/agent/invoke`.
- This does not enable runtime bindings or default provider use.
- This does not set `live_verified=true` or
  `invoke_enabled_by_default=true`.
- This does not make placeholder agents real evidence.
- This does not store raw provider output, credentials, endpoint URLs, or raw
  graph messages in the repo.

## 2026-06-12 - R8-13G value L2 stance remediation and re-smoke

| Field | Value |
| --- | --- |
| Phase | R8-13G |
| Backup root | `/tmp/lma-r8-13g-value-l2-stance-backfill/20260612T033501Z` |
| Restart log root | `/tmp/lma-r8-13g-value-l2-restart/20260612T033801Z` |
| Smoke artifact root | `/tmp/lma-r8-13g-value-l2-resmoke/20260612T033846Z` |
| E2E trace artifact | `/tmp/lma-r8-13g-prod-e2e-llm-report/20260612T033912Z` |
| Endpoint calls | production `/health` and `/v1/agent/compute` for three value L2 services; allowlisted production `/v1/agent/compute` for the E2E trace |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |

R8-13G remediates a protocol-wrapper gap in
`value_traditional_valuation`, `value_ml_valuation`, and
`value_meta_valuation`: each service already produced `normalized.stance`, but
the fixed DAG adapter requires top-level `agent_conclusion_v1.stance` for
direction L2 outputs.

Production value L2 result:

| Agent | Health | Compute | Adapter mapping | Mapped stance |
| --- | --- | --- | --- | --- |
| `value_traditional_valuation` | pass | pass | pass | `0.0397` |
| `value_ml_valuation` | pass | pass | pass | `-0.000399` |
| `value_meta_valuation` | pass | pass | pass | `-0.2852` |

The configured-report E2E trace mapped 17 production compute agents and used 5
explicit placeholder L2 slots. The three value valuation services now appear in
the report as usable value-side evidence instead of adapter-error conclusions.

Non-claims:

- This is not `/v1/agent/invoke` readiness.
- This does not enable runtime bindings or default external invocation.
- This does not set `live_verified=true` or
  `invoke_enabled_by_default=true`.
- This does not change valuation models, feature engineering, scoring
  algorithms, data files, or deployment configuration.
- This does not store raw external responses, endpoint URLs, credentials, or
  provider raw output in the repo.

## 2026-06-12 - R8-13F end-to-end production compute trace QA

| Field | Value |
| --- | --- |
| Phase | R8-13F |
| Artifact directory | `/tmp/lma-r8-13f-prod-e2e-llm-report/20260612T030735Z` |
| Main-system mode | default-off external compute demo bridge + LLM report synthesis |
| Endpoint calls | allowlisted production `POST /v1/agent/compute` only |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Production service directories changed | no |

R8-13F validates the end-to-end QA path after production L3 backfill. The main
system generates `agent_task_v1`, maps production L2 compute outputs, passes
bounded `context.upstream_outputs` to allowlisted L3 production compute calls,
builds `agent_evidence_bundle_v1`, and lets the configured report model produce
a final Chinese report from the structured bundle.

Sanitized QA result:

- Mapped production compute agents: 17.
- Failed external compute mappings: 0.
- Internal placeholder L2 conclusions: 5.
- L2 quality summary: 7 complete, 3 error, 8 partial.
- L3 quality summary: 4 partial composites because upstream evidence remained
  partial, placeholder, or error.

Non-claims:

- This is not `/v1/agent/invoke` readiness.
- This does not enable runtime bindings or default external invocation.
- This does not set `live_verified=true` or
  `invoke_enabled_by_default=true`.
- This does not store raw external responses, endpoint URLs, credentials, or
  provider raw output in the repo.

## 2026-06-12 - R8-13E production L3 backfill and smoke

| Field | Value |
| --- | --- |
| Phase | R8-13E |
| Backup root | `/tmp/lma-r8-13e-prod-l3-backfill/20260612T024513Z` |
| Restart log root | `/tmp/lma-r8-13e-prod-l3-restart/20260612T024553Z` |
| Smoke artifact root | `/tmp/lma-r8-13e-prod-l3-smoke/20260612T024649Z` |
| Endpoint calls | production `/health` and `/v1/agent/compute` for four L3 services |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |

Production L3 result:

| Agent | Health | Compute | Adapter mapping |
| --- | --- | --- | --- |
| `value_composite` | pass | pass | pass |
| `market_composite` | pass | pass | pass |
| `risk_composite` | pass | pass | pass |
| `macro_composite` | pass | pass | pass |

Non-claims:

- This does not enable runtime bindings or default external invocation.
- This does not set `live_verified=true` or
  `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not change business models, scoring algorithms, feature
  engineering, model files, data files, or deployment configuration.

## 2026-06-12 - R8-13D sandbox L3 backfill handoff package

| Field | Value |
| --- | --- |
| Phase | R8-13D |
| Package directory | `/tmp/lma-r8-13d-handoff-package/20260612T023822Z` |
| Source sandbox trace | `/tmp/lma-r8-13c-real-agent-e2e/20260611T122047Z` |
| Endpoint calls during package generation | none |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Production service directories changed | no |

R8-13D packages the R8-13C sandbox trace and candidate L3 service patches for
review. It is not a new live smoke and does not create new production
readiness evidence.

Non-claims:

- This does not modify `/sdb/dlut/prod`.
- This does not call `/health`, `/v1/agent/compute`, or `/v1/agent/invoke`.
- This does not enable runtime bindings or default external invocation.
- This does not set `live_verified=true` or
  `invoke_enabled_by_default=true`.

## 2026-06-11 - R8-12D LLM report synthesizer implementation

| Field | Value |
| --- | --- |
| Phase | R8-12D |
| Endpoint calls | none |
| Real provider calls during validation | none |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |

R8-12D adds a default-off LLM report synthesizer that reads only
`report_input_bundle_v1` and returns a validated `report_result_v1`. Tests use
fake model transports. Live model use requires an explicit
`ENABLE_LLM_REPORT_SYNTHESIS=1` runtime flag and remains separate from runtime
binding enablement.

Non-claims:

- This does not create new production endpoint evidence.
- This does not call external agent `/v1/agent/invoke`.
- This does not enable runtime bindings.
- This does not set live flags.
- This does not store raw model output or raw external responses.

## 2026-06-11 - R8-12C report generator evidence bundle integration

| Field | Value |
| --- | --- |
| Phase | R8-12C |
| Endpoint calls | none |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Default external invocation enabled | no |

R8-12C is an implementation and documentation phase, not a live readiness
smoke. It wires `report_input_bundle_v1` into report generation so the final
answer can consume bounded L2 agent summaries, L3 composite summaries, risk
gate information, macro regulator information, and decision context. The same
bounded summaries are projected into `workflow_snapshot_v2.stepResults` as
`agent_evidence` and `composite_evidence` for Web workflow drilldown.

Non-claims:

- This does not create new production endpoint evidence.
- This does not call `/v1/agent/invoke`.
- This does not enable runtime bindings.
- This does not set live flags.
- This does not deploy the main system to production.

## 2026-06-11 - R8-12 default-off external compute demo

| Field | Value |
| --- | --- |
| Phase | R8-12 |
| Artifact directory | `/tmp/lma-r8-12-demo/20260611T025315Z` |
| Local API | `http://127.0.0.1:8212` |
| Local Web | `http://127.0.0.1:8213` |
| Bridge endpoint calls | production `POST /v1/agent/compute` for explicit allowlist only |
| `/v1/agent/invoke` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Default external invocation enabled | no |

R8-12 added a default-off demo bridge that is activated only by explicit local
flags and an explicit allowlist. The local API smoke submitted one Chinese stock
analysis question through the public API, executed the fixed DAG, read
production `/v1/agent/compute` structured results for allowlisted services, and
mapped those results through the fixed-DAG external adapter before producing the
public answer and workflow snapshot.

Sanitized demo result:

- Public API smoke passed with HTTP 200 for the message request.
- The public answer contained the Chinese external-compute demo summary.
- The workflow snapshot reached `report`.
- Sixteen allowlisted L2/L3 steps were marked complete from mapped external
  compute results.
- The answer artifact did not contain `/v1/agent/invoke`.
- Web server launch succeeded; screenshot capture was not available because the
  host lacks a Chromium/Chrome browser binary for Playwright. The screenshot
  limitation is recorded in
  `/tmp/lma-r8-12-demo/20260611T025315Z/screenshot.failure.json`.

Allowlist used:

- `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, `value_research_synthesis`
- `market_stock_technical`, `market_capital_flow_chip`,
  `sentiment_company_radar`
- `risk_identification`, `risk_compliance_review`,
  `risk_financial_fraud`, `risk_crash`
- `macro_analysis`
- `value_composite`, `market_composite`, `risk_composite`,
  `macro_composite`

Non-claims:

- This is default-off demo evidence only.
- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not make the fixed DAG graph call production external services by
  default.
- This does not prove production business correctness.
- This does not update public transcript content with raw external responses.

## 2026-06-11 - R8-11B first controlled production invoke smoke

| Field | Value |
| --- | --- |
| Phase | R8-11B |
| Artifact directory | `/tmp/lma-r8-11b-prod-invoke-smoke/20260611T022513Z` |
| Environment | production invoke tiny allowlist only |
| Endpoint calls | `POST /v1/agent/invoke` |
| `/health` or `/v1/agent/compute` called | no |
| Runtime bindings changed | no |
| Live flags changed | no |
| Allow-LLM setting | `allow_llm=false`; service-compatible no-LLM options included |

R8-11B audited production invoke paths and then invoked only a five-service
allowlist whose source path could return structured tool results without a
required provider/LLM call. The smoke verified HTTP 200, structured JSON,
fixed-DAG `tool_result` mapping, and no unsafe content in the sanitized
artifact.

| agent_id | endpoint | invoke | adapter mapping | mapping input | status |
| --- | --- | --- | --- | --- | --- |
| `risk_identification` | `127.0.0.1:10010` | pass | pass: `conclusion_object_v1` | `tool_result` | controlled production invoke evidence |
| `risk_compliance_review` | `127.0.0.1:10011` | pass | pass: `conclusion_object_v1` | `tool_result` | controlled production invoke evidence |
| `risk_crash` | `127.0.0.1:10012` | pass | pass: `conclusion_object_v1` | `tool_result` | controlled production invoke evidence |
| `risk_financial_fraud` | `127.0.0.1:10013` | pass | pass: `conclusion_object_v1` | `tool_result` | controlled production invoke evidence |
| `value_research_synthesis` | `127.0.0.1:10006` | pass | pass: `conclusion_object_v1` | envelope | controlled production invoke evidence |

Notes:

- For the four risk services, the current main-system adapter mapping used the
  sanitized `tool_result` because several legacy `external_agent_response_v0`
  envelopes do not expose every envelope identity field that the strict adapter
  response-envelope validator expects.
- This phase did not weaken adapter identity gates and did not change service
  code.

Non-claims:

- This is controlled production invoke evidence only.
- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not make the fixed DAG graph call these services by default.
- This does not update public transcript content.

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
