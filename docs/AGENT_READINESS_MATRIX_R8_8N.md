# Agent Readiness Matrix R8-8N

This document is the developer handoff for Phase R8-8N: Agent Readiness Matrix
And Developer Fix Prompts Audit.

It consolidates the fixed DAG roster, controlled readiness evidence, current
service inventory, unresolved gaps, and copy-ready developer prompts for follow
up work.

## Scope

Audit date: 2026-06-10

Repository head at audit time:

```text
fbf2223 docs(readiness): record remaining l2 compute coverage
```

Repository branch:

```text
reset/fixed-dag-v1
```

This audit was read-only. It did not call any endpoint and did not modify
runtime state.

## Non-Claims

- Controlled `/health` plus `/v1/agent/compute` evidence is not production
  readiness.
- No `/v1/agent/invoke` evidence exists for these services.
- No runtime binding was enabled.
- No `live_verified=true` flag was set.
- No `invoke_enabled_by_default=true` flag was set for external candidates.
- No prod port was tested by this audit.
- No public transcript content was updated.
- `sentiment_company_radar` remains market-only and must not be routed into
  `risk_composite`.
- L3 and L4 remain deterministic seams until a separate adapter/runtime design
  phase owns them.

## Evidence Sources

Primary fixed DAG truth:

- `config/fixed_dag/agent_catalog.json`
- `config/fixed_dag/runtime_bindings.json`
- `src/react_agent/fixed_dag_catalog.py`
- `docs/ARCHITECTURE_FIXED_DAG.md`
- `docs/CONTRACTS.md`

Readiness evidence:

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

The `/tmp` artifacts are operational evidence, not repository source of truth.
They are referenced here so developers know what to backfill into service-owned
repositories.

## Coverage Summary

| Metric | Count | Notes |
| --- | ---: | --- |
| Total fixed DAG agents | 27 | Roster count from fixed DAG catalog |
| External-service candidates | 20 | L1 evidence services plus L2 analysis services |
| Controlled compute pass | 14 | Health pass, compute pass, adapter mapping pass |
| Controlled compute failed/problem | 1 | `market_ipo_investor_behavior` has unsupported compute shape |
| Deferred/problem agents | 11 | Includes L3/L4 deferred items |
| L3/L4 deferred | 6 | 4 composites plus decision/report |
| Invoke audit candidates | 14 | Compute-pass services only |
| Service patches outside git | 13 | Must be backfilled by service owners |
| Agents needing developer backfill | 13 | Most service remediations were done outside git |

Layer coverage:

| Layer/group | Coverage |
| --- | --- |
| L1 | 2/2 external evidence services pass; `route_planner` is internal deterministic |
| L2 value | 4/4 pass |
| L2 market | 3/5 pass; IPO wrapper and fund-manager discovery remain |
| L2 risk | 4/4 pass |
| L2 macro | 1/5 pass; four macro candidates remain deferred/problem |
| L3 | 0/4 external readiness; deterministic internal seams only |
| L4 | 0/2 external readiness; deterministic internal seams only |

## Full 27-Agent Matrix

Status values use the R8-8N audit vocabulary:
`controlled_compute_pass`, `service_patch_needed`, `dev_port_missing`,
`service_source_unknown`, `owner_confirmation_needed`, `l3_l4_deferred`,
`not_external_runtime_target`.

| agent_id | layer | dimension | expected contract | runtime binding | current status | health | compute | adapter | service root / port | issue summary | next action | prompt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `route_planner` | L1 | l1 | `fixed_dag_plan_v1` | `deterministic_system` | `not_external_runtime_target` | n/a | n/a | n/a | n/a | Internal deterministic planner | Keep deterministic | `PROMPT-NONE-INTERNAL` |
| `financial_data_service` | L1 | l1 | `data_bundle_v1` | `external_http_candidate`, disabled | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/金融数据服务智能体/pg-ops-agent-v1.2/backend`, 8100 | Patch outside git; binding still disabled | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `entity_relation_extractor` | L1 | l1 | `entity_relation_bundle_v1` | `pending_placeholder` | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/实体关系抽取智能体/entity_relation_agent`, 8101 | Patch outside git; binding still placeholder | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `value_traditional_valuation` | L2 | value | `conclusion_object_v1` | `external_http_candidate`, disabled | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/传统企业估值智能体`, 8000 | Patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `value_ml_valuation` | L2 | value | `conclusion_object_v1` | `external_http_candidate`, disabled | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/机器学习企业估值智能体`, 8001 | Identity patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `value_meta_valuation` | L2 | value | `conclusion_object_v1` | `external_http_candidate`, disabled | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/元学习企业估值智能体`, 8002 | Patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `value_research_synthesis` | L2 | value | `conclusion_object_v1` | `external_http_candidate`, disabled | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/分析师研报与观点集成智能体`, 8006 | Patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `market_stock_technical` | L2 | market | `conclusion_object_v1` | `external_http_candidate`, disabled | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/个股技术分析智能体`, 8009 | Patch outside git | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `market_fund_manager_behavior` | L2 | market | `conclusion_object_v1` | `pending_placeholder` | `service_source_unknown` | skipped | skipped | skipped | unknown | No non-stub root, dev port, or external id found | Discovery/runbook | `PROMPT-FUND-SERVICE-DISCOVERY` |
| `market_ipo_investor_behavior` | L2 | market | `conclusion_object_v1` | `external_http_candidate`, disabled | `service_patch_needed` | skipped | skipped | skipped | `/sdb/dlut/dev/IPO投资者行为智能体/external_agent_scaffold`, 8008 | Unsupported scaffold/raw business compute shape | Compute wrapper fix, resmoke | `PROMPT-IPO-WRAPPER` |
| `market_capital_flow_chip` | L2 | market | `conclusion_object_v1` | `pending_placeholder` | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/资金流智能体`, 8022 | Patch outside git; binding still placeholder | Backfill patch, then invoke audit | `PROMPT-INVOKE-BACKFILL` |
| `sentiment_company_radar` | L2 | market | `conclusion_object_v1` | `pending_placeholder` | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/企业舆情雷达智能体`, 8104 | Market-only; must not enter risk | Backfill patch, then market-only invoke audit | `PROMPT-SENTIMENT-MARKET-INVOKE` |
| `risk_crash` | L2 | risk | `conclusion_object_v1` | `external_http_candidate`, disabled | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/股价崩盘风险智能体`, 8012 | Patch outside git; L2 gate-member only | Backfill patch, then invoke audit | `PROMPT-RISK-INVOKE-BACKFILL` |
| `risk_financial_fraud` | L2 | risk | `conclusion_object_v1` | `pending_placeholder` | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/财务造假风险智能体`, 8013 | Patch outside git; L2 gate-member only | Backfill patch, then invoke audit | `PROMPT-RISK-INVOKE-BACKFILL` |
| `risk_identification` | L2 | risk | `conclusion_object_v1` | `pending_placeholder` | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/上市公司财务与市场风险规则推理智能体`, 8010 | Patch outside git; L2 gate-member only | Backfill patch, then invoke audit | `PROMPT-RISK-INVOKE-BACKFILL` |
| `risk_compliance_review` | L2 | risk | `conclusion_object_v1` | `pending_placeholder` | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/公告合规审查智能体`, 8011 | Patch outside git; L2 gate-member only | Backfill patch, then invoke audit | `PROMPT-RISK-INVOKE-BACKFILL` |
| `macro_analysis` | L2 | macro | `conclusion_object_v1` | `external_http_candidate`, disabled | `controlled_compute_pass` | pass | pass | pass | `/sdb/dlut/dev/宏观分析智能体`, 8014 | No patch recorded | Invoke audit prep | `PROMPT-INVOKE-AUDIT` |
| `macro_commodity_pricing` | L2 | macro | `conclusion_object_v1` | `external_http_candidate`, disabled | `dev_port_missing` | skipped | skipped | skipped | unknown, expected 8004 | Dev listener missing; do not touch prod 10004 | Runbook and wrapper | `PROMPT-COMMODITY-RUNBOOK` |
| `macro_index_valuation` | L2 | macro | `conclusion_object_v1` | `external_http_candidate`, disabled | `owner_confirmation_needed` | skipped | skipped | skipped | `/sdb/dlut/dev/股票指数估值智能体`, 8003 | Semantics look like index/value valuation | Owner semantic decision | `PROMPT-MACRO-INDEX-OWNER` |
| `macro_sentiment` | L2 | macro | `conclusion_object_v1` | `pending_placeholder` | `l3_l4_deferred` | skipped | skipped | skipped | `/sdb/dlut/dev/宏观情绪感知智能体/macro_sentiment_agent`, 8102 | Likely macro regulator/L3-style payload | L3/macro payload classification | `PROMPT-MACRO-L3-DEFER` |
| `macro_industry_hotspot` | L2 | macro | `conclusion_object_v1` | `pending_placeholder` | `l3_l4_deferred` | skipped | skipped | skipped | `/sdb/dlut/dev/行业热点洞悉智能体/industry_insight_agent`, 8103 | Likely macro regulator/L3-style payload | L3/macro payload classification | `PROMPT-MACRO-L3-DEFER` |
| `value_composite` | L3 | composite | `dimension_composite_result_v1` | `deterministic_composite` | `l3_l4_deferred` | n/a | n/a | n/a | n/a | External L3 adapter not designed | L3 adapter design | `PROMPT-L3-ADAPTER-DESIGN` |
| `market_composite` | L3 | composite | `dimension_composite_result_v1` | `deterministic_composite` | `l3_l4_deferred` | n/a | n/a | n/a | n/a | External L3 adapter not designed | L3 adapter design | `PROMPT-L3-ADAPTER-DESIGN` |
| `risk_composite` | L3 | composite | `dimension_composite_result_v1` | `deterministic_composite` | `l3_l4_deferred` | n/a | n/a | n/a | n/a | External L3 adapter not designed; no sentiment risk input | L3 adapter design | `PROMPT-L3-ADAPTER-DESIGN` |
| `macro_composite` | L3 | composite | `dimension_composite_result_v1` | `deterministic_composite` | `l3_l4_deferred` | n/a | n/a | n/a | n/a | External L3 adapter not designed | L3 adapter design | `PROMPT-L3-ADAPTER-DESIGN` |
| `decision_synthesizer` | L4 | l4 | `decision_result_v1` | `deterministic_decision` | `l3_l4_deferred` | n/a | n/a | n/a | n/a | External L4 decision adapter not designed | L4 adapter design | `PROMPT-L4-ADAPTER-DESIGN` |
| `report_generator` | L4 | l4 | `report_result_v1` | `deterministic_report` | `l3_l4_deferred` | n/a | n/a | n/a | n/a | External L4 report adapter not designed | L4 adapter design | `PROMPT-L4-ADAPTER-DESIGN` |

## Passed Agents

These agents have controlled dev `/health` + `/v1/agent/compute` + provider-free
adapter mapping evidence:

- `financial_data_service`
- `entity_relation_extractor`
- `value_ml_valuation`
- `value_traditional_valuation`
- `value_meta_valuation`
- `value_research_synthesis`
- `market_stock_technical`
- `sentiment_company_radar`
- `market_capital_flow_chip`
- `macro_analysis`
- `risk_identification`
- `risk_compliance_review`
- `risk_financial_fraud`
- `risk_crash`

They are good candidates for a future controlled invoke audit. They are not
live verified and must remain disabled in runtime bindings until a later phase
explicitly owns that change.

## Deferred Or Problem Agents

| agent_id | status | reason | required owner/developer work |
| --- | --- | --- | --- |
| `market_ipo_investor_behavior` | `service_patch_needed` | Service output is scaffold/raw business payload and does not map as L2 `agent_conclusion_v1` | Add service-side compute wrapper and resmoke |
| `macro_commodity_pricing` | `dev_port_missing` | Dev port 8004 was not listening; do not touch prod 10004 | Provide dev runbook, structured health, L2 compute wrapper |
| `macro_index_valuation` | `owner_confirmation_needed` | Service appears index/value oriented; macro L2 semantics unclear | Owner confirms whether this is a macro signal |
| `macro_sentiment` | `l3_l4_deferred` | Likely macro regulator or `macro_conclusion_v1` style payload | Classify L2 vs L3 before wrapper |
| `macro_industry_hotspot` | `l3_l4_deferred` | Likely macro regulator or `macro_conclusion_v1` style payload | Classify L2 vs L3 before wrapper |
| `market_fund_manager_behavior` | `service_source_unknown` | No real non-stub service root/dev port/external id found | Service discovery and runbook |
| L3 composites | `l3_l4_deferred` | Active runtime remains deterministic | Future L3 adapter design |
| L4 decision/report | `l3_l4_deferred` | Active runtime remains deterministic | Future L4 adapter design |

## Service Patches Outside Git

The following dev service changes were applied outside a usable service git
repository during earlier controlled smoke phases. Service owners should
backfill them into their own source-controlled repositories before invoke audit
or runtime binding work.

| agent_id | patch evidence |
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

## Developer Prompt Catalog

Use the prompt id from the matrix and copy the matching prompt below.

### PROMPT-INVOKE-BACKFILL

Use for:

- `financial_data_service`
- `entity_relation_extractor`
- `value_traditional_valuation`
- `value_ml_valuation`
- `value_meta_valuation`
- `value_research_synthesis`
- `market_stock_technical`
- `market_capital_flow_chip`

```text
你是该服务的 Codex / Claude Code 修复助手。

目标：
把已有 controlled /health + /v1/agent/compute + adapter mapping pass 的服务端协议补丁回填到服务项目，并准备后续只读 /v1/agent/invoke 审计。

上下文：
fixed DAG 主系统已有 controlled compute evidence，但 runtime_bindings 仍 disabled，live_verified=false，invoke_enabled_by_default=false。

固定 DAG agent_id：
使用本服务在 R8-8N matrix 中列出的 agent_id。

external_agent_id：
使用服务现有 external id。不得把 legacy aNN id 作为 primary agent_id。

legacy_agent_id：
只能放在 provenance 或 migration note。

禁止项：
- 不改主系统 runtime_bindings。
- 不设置 live_verified=true。
- 不设置 invoke_enabled_by_default=true。
- 不调用 /v1/agent/invoke。
- 不改业务模型、算法、特征工程、数据源。
- 不输出 raw response、secret、traceback、chain-of-thought。

允许改动范围：
- 服务端协议层。
- /health response builder。
- /v1/agent/compute response builder。
- schema / contract tests。
- 不改 compute_core。

需要审计的文件：
- service.py / app.py / main.py
- schemas.py / protocol.py
- README / contract docs
- tests

需要修复的字段：
- envelope.agent_id
- envelope.external_agent_id
- tool_result.agent_id
- tool_result.external_agent_id
- schema_version
- as_of
- data_as_of
- dimension
- status
- provenance

需要运行的测试：
- 服务本地最小 contract tests。
- python -m py_compile changed_files。
- 禁止 provider/prod/invoke tests。

最终回传格式：
- changed files
- fixed fields
- test commands/results
- whether restart is required
- confirmation: no runtime binding change, no live flag change, no /invoke call
```

### PROMPT-INVOKE-AUDIT

Use for `macro_analysis`.

```text
你是 macro_analysis 的 controlled invoke audit 准备助手。

目标：
只读审计 /v1/agent/invoke 是否复用已经通过 controlled compute 的安全协议边界。不要直接调用 /invoke。

上下文：
macro_analysis 已通过 controlled /health + /v1/agent/compute + adapter mapping。该证据不是 live readiness。

固定 DAG agent_id：
macro_analysis

external_agent_id：
macro_analysis

禁止项：
- 不调用 /v1/agent/invoke。
- 不改 runtime_bindings。
- 不设置 live flags。
- 不改业务模型或数据源。
- 不输出 raw response、secret、traceback、chain-of-thought。

允许改动范围：
本 prompt 阶段只读。若发现 invoke 协议差异，另开服务端修复阶段。

需要审计的文件：
- service.py
- schemas.py / protocol.py
- invoke endpoint implementation
- compute endpoint implementation
- tests

需要确认：
- invoke 是否复用 compute_core。
- invoke 是否返回与 compute 相同的 tool_result family。
- invoke 是否保持 fixed DAG agent_id。
- invoke 是否有安全过滤和 fail-closed 行为。

最终回传格式：
- invoke endpoint file/function
- compute reuse yes/no
- expected response schema
- risks
- next step recommendation
```

### PROMPT-SENTIMENT-MARKET-INVOKE

Use for `sentiment_company_radar`.

```text
你是 sentiment_company_radar 的服务端协议回填与 controlled invoke audit 准备助手。

目标：
准备后续 controlled invoke audit，但必须保持 market-only。

上下文：
R8-8I 已有 controlled compute pass。主系统明确禁止 sentiment_company_radar 进入 risk。

固定 DAG agent_id：
sentiment_company_radar

external_agent_id：
从服务 health/schema/docs 中确认并保持服务 id。

legacy_agent_id：
a09_company_sentiment_radar 仅作迁移备注。

禁止项：
- 不得把 sentiment_company_radar 输出映射到 risk。
- 不得改 risk_composite。
- 不得调用 /v1/agent/invoke，除非后续进入单独 invoke smoke 阶段。
- 不改 runtime_bindings。
- 不改业务模型、数据源或权限逻辑。

允许改动范围：
- 服务协议层。
- /health JSON。
- /v1/agent/compute wrapper。
- contract tests。

需要审计的文件：
- company_radar_agent/service.py
- company_radar_agent/schemas.py
- tests
- README / protocol docs

需要修复的字段：
- agent_id=sentiment_company_radar
- external_agent_id=服务 id
- dimension=market
- tool_result.schema_version=agent_conclusion_v1
- role=direction

需要运行的测试：
- 服务本地 contract tests。
- py_compile changed files。
- 禁止 provider/live/prod/invoke tests。

最终回传格式：
- changed files
- confirmed market-only
- no risk routing
- test results
- readiness for controlled invoke audit
```

### PROMPT-RISK-INVOKE-BACKFILL

Use for:

- `risk_identification`
- `risk_compliance_review`
- `risk_financial_fraud`
- `risk_crash`

```text
你是风险 L2 服务的协议回填与 controlled invoke audit 准备助手。

目标：
回填风险 L2 gate_member compute wrapper 补丁，并准备后续 controlled invoke audit。

上下文：
该服务已有 controlled compute pass，但只是 L2 risk gate_member evidence，不是 L3 risk_conclusion，也不是 production readiness。

固定 DAG agent_id：
使用本服务在 R8-8N matrix 中列出的 risk agent_id。

external_agent_id：
从服务 schema/health/docs 中确认。

legacy_agent_id：
仅作迁移备注。

禁止项：
- 不得把 risk_conclusion_v1 强塞成 L2。
- 不改风险业务模型、打分算法、特征工程、数据源。
- 不调用 /v1/agent/invoke。
- 不设置 live flags。
- 不改 runtime_bindings。

允许改动范围：
- 服务协议边界。
- schema / protocol。
- response builder。
- contract tests。

需要审计的文件：
- app.py / service.py / main.py
- protocol.py / schemas.py
- risk compute wrapper
- tests

需要修复的字段：
- tool_result.schema_version=agent_conclusion_v1
- role=gate_member
- dimension=risk
- risk_score
- bounded confidence
- event_flags
- provenance

需要运行的测试：
- contract tests 或 py_compile。
- 禁止 provider/prod/invoke tests。

最终回传格式：
- risk_score 来源说明
- changed files
- schema fields
- test results
- no runtime binding change
```

### PROMPT-IPO-WRAPPER

Use for `market_ipo_investor_behavior`.

```text
你是 market_ipo_investor_behavior 的服务端 compute wrapper 修复助手。

目标：
把 IPO 投资者行为服务的 /v1/agent/compute 输出包装成 fixed DAG L2 agent_conclusion_v1。

上下文：
R8-8M 记录 compute_unsupported_schema，当前不能算 controlled compute pass。

固定 DAG agent_id：
market_ipo_investor_behavior

external_agent_id：
优先从 /health schema、服务常量或协议文档确认。不要猜。

legacy_agent_id：
a14_ipo_investor_behavior 仅迁移备注。

禁止项：
- 不改业务模型、特征工程、算法、数据源。
- 不调用 /v1/agent/invoke。
- 不访问 prod。
- 不改主系统 runtime_bindings。
- 不设置 live flags。

允许改动范围：
- 服务 response builder。
- schema / protocol。
- contract tests。
- 不改 compute_core。

需要审计的文件：
- /sdb/dlut/dev/IPO投资者行为智能体/external_agent_scaffold/service.py
- schemas.py / protocol.py
- README / contract docs
- tests

需要修复的字段：
- external_agent_compute_v0 envelope
- tool_result.schema_version=agent_conclusion_v1
- agent_id=market_ipo_investor_behavior
- external_agent_id=已确认服务 id
- dimension=market
- stance
- confidence
- evidence
- as_of / data_as_of

需要运行的测试：
- 服务本地最小 contract tests 或 py_compile。
- 禁止 provider/prod/invoke tests。

最终回传格式：
- resolved external_agent_id
- changed files
- test results
- whether ready for controlled compute resmoke
```

### PROMPT-COMMODITY-RUNBOOK

Use for `macro_commodity_pricing`.

```text
你是 macro_commodity_pricing 的 dev runbook 与 fixed DAG wrapper 修复助手。

目标：
补齐 dev service runbook、structured health、和 fixed DAG L2 compute wrapper。

上下文：
R8-8M 记录 dev 8004 port_not_listening。不要触碰 prod 10004。

固定 DAG agent_id：
macro_commodity_pricing

external_agent_id：
runtime binding 当前候选为 price_influence_agent；仍需从服务文档/health/schema 确认。

legacy_agent_id：
a04_commodity_hedging 仅迁移备注。

禁止项：
- 不访问 prod 10004。
- 不调用 /v1/agent/invoke。
- 不需要 secret 的启动。
- 不改模型、算法、特征工程、数据源。
- 不改主系统 runtime_bindings。

允许改动范围：
- dev 启动文档。
- /health JSON。
- /v1/agent/compute wrapper。
- schema / tests。

需要审计的文件：
- README
- start scripts
- service.py / app.py
- schema / protocol
- contract docs

需要修复的字段：
- external_agent_health_v0
- external_agent_compute_v0
- tool_result.agent_conclusion_v1
- dimension=macro
- target
- as_of / data_as_of

需要运行的测试：
- py_compile 或服务本地 contract tests。
- 不跑 provider/prod/invoke tests。

最终回传格式：
- service root
- safe dev command
- external_agent_id
- changed files
- test results
- controlled compute resmoke readiness
```

### PROMPT-MACRO-INDEX-OWNER

Use for `macro_index_valuation`.

```text
你是 macro_index_valuation 的语义 owner 确认助手。

目标：
确认 macro_index_valuation 是否应作为 fixed DAG macro L2 signal，还是应保持 deferred。

上下文：
服务监听 8003，但 R8-8M 因 semantic_dimension_unclear defer。不要强行把 index/value valuation 归一为 macro。

固定 DAG agent_id：
macro_index_valuation

external_agent_id：
runtime binding 候选为 valuation_index；仍需服务 owner 确认。

legacy_agent_id：
a11_index_technical_analysis 仅迁移备注。

禁止项：
- 不改主系统 adapter gate。
- 不强行 dimension=macro。
- 不调用 /v1/agent/invoke。
- 不写 runtime_bindings。
- 不设置 live flags。

允许改动范围：
本阶段只做语义审计或服务文档澄清；若 owner 确认，再另开 compute wrapper phase。

需要审计的文件：
- README
- service.py
- schema
- domain docs
- sample outputs

需要确认：
- 服务输出是否是 macro signal。
- 是否只适用于 index/value valuation。
- 是否能合法输出 L2 agent_conclusion_v1 dimension=macro。

最终回传格式：
- owner decision: macro L2 yes/no/unknown
- evidence from docs/source
- go/no-go for controlled compute resmoke
```

### PROMPT-MACRO-L3-DEFER

Use for:

- `macro_sentiment`
- `macro_industry_hotspot`

```text
你是宏观类服务 payload 分类助手。

目标：
判断该服务是 L2 agent_conclusion_v1 方向 agent，还是未来 L3/macro_conclusion_v1/regulator payload。

上下文：
R8-8M 已因 l3_payload_deferred 跳过。不得强行塞入 L2 conclusion_object。

固定 DAG agent_id：
macro_sentiment 或 macro_industry_hotspot。

external_agent_id：
从服务 health/schema/docs 中确认。

legacy_agent_id：
macro_sentiment=a07_macro_sentiment。
macro_industry_hotspot=a08_industry_hotspot。
仅迁移备注。

禁止项：
- 不改 L3/L4 active runtime。
- 不调用 /v1/agent/invoke。
- 不强行 agent_conclusion_v1。
- 不改 runtime_bindings。
- 不设置 live flags。

允许改动范围：
只读协议/语义审计；如确认 L2，再另开 wrapper phase。

需要审计的文件：
- service.py
- schemas.py
- README
- agent protocol docs
- sample outputs

需要判断：
- 如果是 L2：是否可以输出 tool_result.agent_conclusion_v1、dimension=macro、role=direction。
- 如果是 L3：记录 macro_conclusion_v1 / dimension_composite adapter needs。

最终回传格式：
- classification=L2|L3|unknown
- evidence
- needed adapter/wrapper
- resmoke recommendation
```

### PROMPT-FUND-SERVICE-DISCOVERY

Use for `market_fund_manager_behavior`.

```text
你是 market_fund_manager_behavior 服务发现与 runbook 审计助手。

目标：
找到真实 non-stub 服务根目录、dev port、external_agent_id 和 compute wrapper 状态。

上下文：
当前 fixed DAG 只有 pending_placeholder。R8-8M 记录 service_not_found_or_port_unknown。

固定 DAG agent_id：
market_fund_manager_behavior

external_agent_id：
必须从服务源码、health schema 或文档确认。不要猜。

legacy_agent_id：
a13_fund_manager_behavior 仅迁移备注。

禁止项：
- 不启动不明服务。
- 不碰 prod。
- 不调用 /v1/agent/invoke。
- 不改主系统 runtime_bindings。
- 不设置 live flags。

允许改动范围：
只读 inventory/runbook 审计；若 root/port 明确，另开 service wrapper phase。

需要审计的文件：
- README
- start scripts
- service.py
- schema / contract docs
- tests

最终回传格式：
- service_root
- dev_port
- external_agent_id
- is_stub
- safe dev runbook if available
- next wrapper work
```

### PROMPT-L3-ADAPTER-DESIGN

Use for:

- `value_composite`
- `market_composite`
- `risk_composite`
- `macro_composite`

```text
你是 fixed DAG L3 composite adapter 设计助手。

目标：
设计 future L3 payload adapter，不接 active runtime。

上下文：
当前 L3 是 deterministic_composite seam。不得把 L3 payload 强塞 L2。

固定 DAG agent_id：
value_composite / market_composite / risk_composite / macro_composite。

external_agent_id：
若存在服务候选，先作为 deferred candidate，不启用。

legacy_agent_id：
仅迁移备注。

禁止项：
- 不调用 endpoint。
- 不改 runtime_bindings。
- 不接 graph/executor。
- 不设置 live flags。
- 不把 sentiment_company_radar 接入 risk_composite。

允许改动范围：
- 设计文档。
- provider-free pure adapter tests 的候选方案。

需要审计的文件：
- src/react_agent/fixed_dag_contracts.py
- src/react_agent/fixed_dag_external_adapter.py
- docs/CONTRACTS.md
- docs/EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md

需要设计的字段：
- dimension_composite_result_v1
- contributing_agents
- evidence_refs
- manual_review
- provenance

需要运行的测试：
仅 unit tests，no HTTP/provider.

最终回传格式：
- adapter design
- test plan
- non-claims
- runtime enablement blocked items
```

### PROMPT-L4-ADAPTER-DESIGN

Use for:

- `decision_synthesizer`
- `report_generator`

```text
你是 fixed DAG L4 decision/report adapter 设计助手。

目标：
设计 future L4 decision/report adapter，或确认继续 deterministic seam。

上下文：
当前 L4 是 deterministic_decision/report。没有 external compute/invoke readiness。

固定 DAG agent_id：
decision_synthesizer 或 report_generator。

external_agent_id：
若服务候选存在，先 deferred，不启用。

legacy_agent_id：
report_generator 可保留 a25_report_center 迁移备注。

禁止项：
- 不生成 public transcript raw agent JSON。
- 不调用 endpoint。
- 不改 runtime_bindings。
- 不设置 live flags。
- 不接 active runtime。

允许改动范围：
- 设计文档。
- contract tests。
- adapter pure mapping draft。

需要审计的文件：
- src/react_agent/fixed_dag_contracts.py
- public mapping/transcript docs
- docs/CONTRACTS.md
- docs/QUALITY.md

需要设计的字段：
- decision_result_v1
- report_result_v1
- safe public transcript fields
- provenance

需要运行的测试：
unit/static only，no provider/live.

最终回传格式：
- L4 adapter scope
- schema mapping
- public safety boundary
- next phase DoD
```

## Recommended Next Phases

1. R8-9A: controlled `/v1/agent/invoke` audit plan only. Do not call invoke yet.
2. R8-9B: first controlled invoke smoke for a tiny allowlist, still no runtime
   binding change.
3. Service-owner backfill: move non-git service protocol patches into each
   service-owned repository.
4. Macro cleanup: resolve `macro_index_valuation`, `macro_sentiment`,
   `macro_industry_hotspot`, and `macro_commodity_pricing`.
5. L3/L4 adapter design: define composite, decision, and report adapter
   contracts before any live runtime work.
