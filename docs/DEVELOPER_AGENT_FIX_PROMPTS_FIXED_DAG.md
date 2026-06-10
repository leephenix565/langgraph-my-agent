# Fixed DAG Developer Agent Fix Prompt Catalog

This catalog persists the developer-facing prompts from the R8-8N readiness
audit. Each prompt is written in Chinese so it can be copied directly into
Codex or Claude Code by the owner of the corresponding service.

These prompts do not authorize production invocation. They do not change runtime
bindings, live flags, fixed DAG roster, graph execution, or public transcript
behavior.

## Prompt Index

| Prompt id | Applies to |
| --- | --- |
| `PROMPT-INVOKE-BACKFILL` | `financial_data_service`, `entity_relation_extractor`, `value_traditional_valuation`, `value_ml_valuation`, `value_meta_valuation`, `value_research_synthesis`, `market_stock_technical`, `market_capital_flow_chip` |
| `PROMPT-INVOKE-AUDIT` | `macro_analysis` |
| `PROMPT-SENTIMENT-MARKET-INVOKE` | `sentiment_company_radar` |
| `PROMPT-RISK-INVOKE-BACKFILL` | `risk_identification`, `risk_compliance_review`, `risk_financial_fraud`, `risk_crash` |
| `PROMPT-IPO-WRAPPER` | `market_ipo_investor_behavior` |
| `PROMPT-COMMODITY-RUNBOOK` | `macro_commodity_pricing` |
| `PROMPT-MACRO-INDEX-OWNER` | `macro_index_valuation` |
| `PROMPT-MACRO-L3-DEFER` | `macro_sentiment`, `macro_industry_hotspot` |
| `PROMPT-FUND-SERVICE-DISCOVERY` | `market_fund_manager_behavior` |
| `PROMPT-L3-ADAPTER-DESIGN` | `value_composite`, `market_composite`, `risk_composite`, `macro_composite` |
| `PROMPT-L4-ADAPTER-DESIGN` | `decision_synthesizer`, `report_generator` |

## PROMPT-INVOKE-BACKFILL

适用于：

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

## PROMPT-INVOKE-AUDIT

适用于：

- `macro_analysis`

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

legacy_agent_id：
a03_macro_industry_research 仅迁移备注。

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

需要修复的字段：
本阶段不修复字段，只确认 invoke 是否会返回安全、结构化、可映射的 fixed DAG payload。

需要运行的测试：
本阶段不调用 endpoint。可以运行本地静态或单元测试，但禁止 live invoke。

最终回传格式：
- invoke endpoint file/function
- compute reuse yes/no
- expected response schema
- risks
- next step recommendation
```

## PROMPT-SENTIMENT-MARKET-INVOKE

适用于：

- `sentiment_company_radar`

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

## PROMPT-RISK-INVOKE-BACKFILL

适用于：

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

## PROMPT-IPO-WRAPPER

适用于：

- `market_ipo_investor_behavior`

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

## PROMPT-COMMODITY-RUNBOOK

适用于：

- `macro_commodity_pricing`

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

## PROMPT-MACRO-INDEX-OWNER

适用于：

- `macro_index_valuation`

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

需要修复的字段：
本阶段不修复字段。只有 owner 确认后，才设计 agent_conclusion_v1 wrapper。

需要运行的测试：
本阶段只读，不跑 live tests。

最终回传格式：
- owner decision: macro L2 yes/no/unknown
- evidence from docs/source
- go/no-go for controlled compute resmoke
```

## PROMPT-MACRO-L3-DEFER

适用于：

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

需要修复的字段：
本阶段不修复字段；只做分类。

需要运行的测试：
本阶段不调用 endpoint。后续 wrapper phase 再跑 contract tests。

最终回传格式：
- classification=L2|L3|unknown
- evidence
- needed adapter/wrapper
- resmoke recommendation
```

## PROMPT-FUND-SERVICE-DISCOVERY

适用于：

- `market_fund_manager_behavior`

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

需要修复的字段：
本阶段不修复字段；先确认真实服务边界。

需要运行的测试：
本阶段无 live test；只回传可安全启动的 dev runbook。

最终回传格式：
- service_root
- dev_port
- external_agent_id
- is_stub
- safe dev runbook if available
- next wrapper work
```

## PROMPT-L3-ADAPTER-DESIGN

适用于：

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

需要修复的字段：
- dimension_composite_result_v1
- contributing_agents
- evidence_refs
- manual_review
- provenance

需要运行的测试：
仅 unit tests，no HTTP/provider。

最终回传格式：
- adapter design
- test plan
- non-claims
- runtime enablement blocked items
```

## PROMPT-L4-ADAPTER-DESIGN

适用于：

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

需要修复的字段：
- decision_result_v1
- report_result_v1
- safe public transcript fields
- provenance

需要运行的测试：
unit/static only，no provider/live。

最终回传格式：
- L4 adapter scope
- schema mapping
- public safety boundary
- next phase DoD
```
