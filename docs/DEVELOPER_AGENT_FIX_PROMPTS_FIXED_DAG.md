# Fixed DAG Developer Agent Fix Prompt Catalog

这是一份 production-first 的开发者修复提示词目录，用于 R8-8P-DOCS-QA
之后的生产问题处置。每段 prompt 都可以直接复制给 Codex / Claude Code
或服务 owner 使用。

R8-8P 已经证明：dev evidence 只能作为历史参考和 backfill 线索，不能当作
production pass。所有修复必须进入服务 owner 的源码仓库，重新部署到
production endpoint，并经过 production `/health` + `/v1/agent/compute` +
main-system adapter mapping 复测，才可以改变 production matrix 状态。

默认边界：

- 不调用 `/v1/agent/invoke`，除非未来单独批准 invoke smoke；本目录里的
  invoke prompt 也只允许审计准备，不允许直接调用。
- 不改 `runtime_bindings.json`。
- 不设置 `live_verified=true`。
- 不设置 `invoke_enabled_by_default=true`。
- 不改 fixed DAG graph/executor/public API/frontend。
- 不改业务模型、特征工程、算法、数据源。
- 不输出 secret、traceback、chain-of-thought、raw provider response、raw
  production response。
- dev pass 不等于 production pass。

## Prompt Index

| Prompt id | Applies to |
| --- | --- |
| `PROMPT-PROD-HEALTH-FIX-DATA-SERVICE` | `financial_data_service` production health invalid JSON |
| `PROMPT-PROD-ENDPOINT-MISSING-ENTITY` | `entity_relation_extractor` production endpoint missing |
| `PROMPT-PROD-SENTIMENT-MARKET-ONLY` | `sentiment_company_radar` production endpoint missing; market-only |
| `PROMPT-PROD-IDENTITY-FIX-VALUE-TRADITIONAL` | `value_traditional_valuation` production identity mismatch |
| `PROMPT-PROD-IDENTITY-FIX-VALUE-ML` | `value_ml_valuation` production identity mismatch |
| `PROMPT-PROD-IDENTITY-FIX-VALUE-META` | `value_meta_valuation` production identity mismatch |
| `PROMPT-PROD-IDENTITY-FIX-RESEARCH` | `value_research_synthesis` production identity mismatch |
| `PROMPT-PROD-IDENTITY-FIX-STOCK-TECHNICAL` | `market_stock_technical` production identity mismatch |
| `PROMPT-PROD-IDENTITY-FIX-CAPITAL-FLOW` | `market_capital_flow_chip` production identity mismatch |
| `PROMPT-PROD-FUND-SERVICE-DISCOVERY` | `market_fund_manager_behavior` service metadata + identity |
| `PROMPT-PROD-IPO-WRAPPER` | `market_ipo_investor_behavior` production wrapper |
| `PROMPT-PROD-COMMODITY-COMPUTE-FIX` | `macro_commodity_pricing` production compute failure |
| `PROMPT-PROD-MACRO-INDEX-OWNER` | `macro_index_valuation` semantic decision |
| `PROMPT-PROD-MACRO-SENTIMENT-L2-OR-L3` | `macro_sentiment` L2/L3 classification |
| `PROMPT-PROD-MACRO-HOTSPOT-L2-OR-L3` | `macro_industry_hotspot` L2/L3 classification |
| `PROMPT-PROD-L3-ADAPTER-DESIGN` | value/market/risk/macro composites |
| `PROMPT-PROD-L4-ADAPTER-DESIGN` | `decision_synthesizer`, `report_generator` |
| `PROMPT-PROD-INVOKE-AUDIT-PREP` | only five production health+compute+adapter pass candidates |

## PROMPT-PROD-HEALTH-FIX-DATA-SERVICE

```text
你是 financial_data_service 的 Codex / Claude Code production health 合同修复助手。

目标：
只修 production /health 合同，使金融数据服务返回安全、结构化的 external_agent_health_v0 JSON。不要改业务数据逻辑。

背景：
R8-8P production rebaseline 中，financial_data_service 的 production endpoint http://127.0.0.1:11000 /health 返回 HTTP 200，但被判定为 health_invalid_json，/compute 被跳过。dev 修复记录只能作为历史参考，不能算 production pass。

适用 agent_id：
financial_data_service

production endpoint：
http://127.0.0.1:11000

fixed DAG id 规则：
fixed DAG primary id 必须是 financial_data_service。health 可以同时报告 service identity，但必须能明确关联 fixed_dag_agent_id=financial_data_service。

external_agent_id 规则：
external_agent_id=financial_data_service。legacy_agent_id 如存在只能作为迁移备注。

禁止项：
不调用 /v1/agent/invoke；不改 runtime_bindings.json；不设置 live_verified 或 invoke_enabled_by_default；不访问 dev 8100 作为 production evidence；不输出 secret、traceback、raw provider response；不改业务数据获取逻辑。

允许改动范围：
production 服务 /health response builder、health schema/protocol、health contract tests、README/runbook 中的 health 合同说明。

需要审计的文件：
production 服务中的 service.py / app.py / main.py、schema/protocol 文件、health endpoint、tests、部署 runbook；参考 dev backfill 线索 /tmp/lma-r8-8j-service-backup/20260610T053111Z/service_patch_manifest.json。

需要修复的字段：
schema_version=external_agent_health_v0；agent_id 或 fixed_dag_agent_id=financial_data_service；external_agent_id=financial_data_service；status；service/version/build/runtime metadata；不得包含 traceback、secret、raw_response。

需要运行的本地测试：
python -m py_compile changed_python_files；health contract unit test；JSON schema test；unsafe-field test。不要把 production /health 或 /compute smoke 写在本地测试里。

重新部署要求：
修复必须合入服务 owner 的源码仓库并部署到 production endpoint 11000。只修 dev 不会改变 R8-8P production 状态。

production re-smoke 边界：
部署后由维护者只调用 GET /health；health pass 后再调用 POST /v1/agent/compute，并用主系统 adapter 映射 data_bundle_v1。禁止 /v1/agent/invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-ENDPOINT-MISSING-ENTITY

```text
你是 entity_relation_extractor 的 Codex / Claude Code production endpoint 补齐助手。

目标：
为 entity_relation_extractor 提供明确的 production endpoint，并输出 fixed DAG 支持的 entity_relation_bundle_v1 compute payload。

背景：
R8-8P 没有找到 entity_relation_extractor 的 confirmed production endpoint。dev 8101 和 dev evidence 只能作为历史参考，不能作为 production pass。

适用 agent_id：
entity_relation_extractor

production endpoint：
当前缺失。服务 owner 必须提供 production root、host、port、启动/部署 runbook；不要使用 dev 8101 代替。

fixed DAG id 规则：
envelope.agent_id 和 tool_result.agent_id 必须是 entity_relation_extractor。

external_agent_id 规则：
建议 external_agent_id=entity_relation_agent，除非 owner 用 production health/schema 明确给出其他服务 id。legacy_agent_id=a15_entity_relation_extraction 只能作为迁移备注。

禁止项：
不调用 /v1/agent/invoke；不把 dev endpoint 当 production endpoint；不改 runtime_bindings.json；不设置 live flags；不输出 raw business JSON 到 graph state；不改实体关系抽取业务算法。

允许改动范围：
production 服务部署/runbook、/health wrapper、/v1/agent/compute wrapper、entity_relation_bundle_v1 schema/protocol、contract tests。

需要审计的文件：
service.py / app.py / main.py、schema/protocol、compute response builder、README/runbook、deployment scripts、tests；参考 dev backfill 线索 /tmp/lma-r8-8k-service-backup/20260610T060226Z/service_patch_manifest.json。

需要修复的字段：
external_agent_health_v0；external_agent_compute_v0；tool_result.schema_version=entity_relation_bundle_v1；agent_id=entity_relation_extractor；external_agent_id；as_of；data_as_of；entities/relations/evidence/provenance；data_as_of <= as_of。

需要运行的本地测试：
py_compile；health JSON contract test；compute success/partial/error mock tests；entity_relation_bundle_v1 schema test；unsafe-field test。

重新部署要求：
部署到 production endpoint 后，提供生产端口、cwd/root、cmdline/runbook 和部署版本。

production re-smoke 边界：
只允许 GET /health 和 POST /v1/agent/compute，再用主系统 adapter 映射 entity_relation_bundle_v1。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-SENTIMENT-MARKET-ONLY

```text
你是 sentiment_company_radar 的 Codex / Claude Code production market-only 接入助手。

目标：
提供 sentiment_company_radar 的 production endpoint，并确保它只作为 market L2 signal 输出 agent_conclusion_v1。

背景：
R8-8P 没有找到 confirmed production endpoint。历史 dev evidence 表明该服务可作为 market-only L2，但不能作为 production pass。严禁把 company sentiment 接入 risk。

适用 agent_id：
sentiment_company_radar

production endpoint：
当前缺失。owner 必须提供 production endpoint；不要用 dev 8104 或 stub 8304 代替。

fixed DAG id 规则：
envelope.agent_id 和 tool_result.agent_id 必须是 sentiment_company_radar。

external_agent_id 规则：
建议 external_agent_id=company_radar_agent，除非 production schema 明确给出其他服务 id。legacy_agent_id=a09_company_sentiment_radar 只能作为迁移备注。

禁止项：
不调用 /v1/agent/invoke；不接 risk dimension；不路由到 risk_composite；不改 runtime_bindings；不设置 live flags；不输出 raw sentiment dump。

允许改动范围：
production endpoint/runbook、health wrapper、compute wrapper、agent_conclusion_v1 market-only contract tests。

需要审计的文件：
production service.py / app.py / main.py、health endpoint、compute builder、schema/protocol、README/runbook、tests；参考 dev backfill 线索 /tmp/lma-r8-8i-service-backup/20260610T043253Z/service_patch_manifest.json。

需要修复的字段：
external_agent_health_v0；external_agent_compute_v0；tool_result.schema_version=agent_conclusion_v1；role=direction；dimension=market；stance；confidence；evidence；agent_id=sentiment_company_radar；external_agent_id=company_radar_agent；as_of/data_as_of。

需要运行的本地测试：
health JSON test；market-only dimension test；sentiment-to-risk rejection test；compute success/partial/error mock tests；unsafe-field test；py_compile。

重新部署要求：
production endpoint 部署完成后，owner 回传端口、root、版本和 market-only contract test 结果。

production re-smoke 边界：
只允许 production /health + /compute + adapter mapping。禁止 /invoke，禁止 risk route。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-IDENTITY-FIX-VALUE-TRADITIONAL

```text
你是 value_traditional_valuation 的 Codex / Claude Code production identity 修复助手。

目标：
修复 production 10000 compute 输出中的 identity，使固定 DAG primary id 和服务 id 分离正确。

背景：
R8-8P 中 production /health 和 /compute 可达，但主系统 adapter 以 unknown_agent_id 拒绝。说明 production 没有回填 dev 阶段的 fixed DAG identity wrapper。

适用 agent_id：
value_traditional_valuation

production endpoint：
http://127.0.0.1:10000

fixed DAG id 规则：
envelope.agent_id=value_traditional_valuation；tool_result.agent_id=value_traditional_valuation。

external_agent_id 规则：
envelope.external_agent_id=valuation_traditional；tool_result.external_agent_id=valuation_traditional；legacy_agent_id=a17_traditional_valuation 只作为迁移备注。

禁止项：
不放宽主系统 adapter identity gate；不把 valuation_traditional 当 primary agent_id；不调用 /invoke；不改 runtime_bindings；不改估值业务算法/模型/数据。

允许改动范围：
production response builder、schema/protocol、identity contract tests、deployment packaging。

需要审计的文件：
service.py / app.py / main.py、compute response builder、schemas/protocol、tests、README/runbook；参考 dev patch /tmp/lma-r8-8g-service-backup/20260610T034105Z/value_traditional_valuation。

需要修复的字段：
external_agent_compute_v0.agent_id；external_agent_compute_v0.external_agent_id；tool_result.agent_id；tool_result.external_agent_id；tool_result.schema_version=agent_conclusion_v1；dimension=value；role=direction；as_of/data_as_of。

需要运行的本地测试：
identity contract test；agent_conclusion_v1 schema test；data_as_of <= as_of test；success/partial/error mock tests；unsafe-field test；py_compile。

重新部署要求：
把 wrapper 修复合入服务源码仓库并部署到 production 10000。

production re-smoke 边界：
GET /health，POST /v1/agent/compute，adapter mapping to conclusion_object_v1。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-IDENTITY-FIX-VALUE-ML

```text
你是 value_ml_valuation 的 Codex / Claude Code production identity 修复助手。

目标：
把 production 10001 的 compute envelope 和 tool_result primary id 修正为 fixed DAG id。

背景：
dev 阶段已经修过 identity 并通过 controlled smoke，但 R8-8P production 仍因 unknown_agent_id 被 adapter 拒绝。

适用 agent_id：
value_ml_valuation

production endpoint：
http://127.0.0.1:10001

fixed DAG id 规则：
envelope.agent_id=value_ml_valuation；tool_result.agent_id=value_ml_valuation。

external_agent_id 规则：
envelope.external_agent_id=valuation_ml；tool_result.external_agent_id=valuation_ml；legacy_agent_id=a16_ml_valuation 只作为迁移备注。

禁止项：
不让 adapter 接受 valuation_ml 作为 primary id；不调用 /invoke；不改 runtime_bindings；不改 ML 估值模型/特征/数据。

允许改动范围：
production response wrapper、identity/schema tests、deployment package。

需要审计的文件：
service.py / app.py / main.py、compute builder、schema/protocol、tests、deployment scripts；参考 /tmp/lma-r8-8d-id-backup/20260610T030433Z。

需要修复的字段：
external_agent_compute_v0.agent_id/external_agent_id；tool_result.agent_id/external_agent_id；tool_result.schema_version=agent_conclusion_v1；dimension=value；role=direction；confidence/evidence/as_of/data_as_of。

需要运行的本地测试：
identity fixture test；adapter-shaped fixture test if available；anti-lookahead test；unsafe-field test；py_compile。

重新部署要求：
部署到 production 10001 后再申请 production resmoke；dev pass 不改变 production matrix。

production re-smoke 边界：
只允许 /health + /compute + adapter mapping。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-IDENTITY-FIX-VALUE-META

```text
你是 value_meta_valuation 的 Codex / Claude Code production identity 修复助手。

目标：
修复 production 10002 输出 identity，使 meta valuation 进入 fixed DAG value L2 contract。

背景：
R8-8P production compute 可达，但 adapter 以 unknown_agent_id 拒绝；这通常表示 dev wrapper 没有回填到 production。

适用 agent_id：
value_meta_valuation

production endpoint：
http://127.0.0.1:10002

fixed DAG id 规则：
envelope.agent_id=value_meta_valuation；tool_result.agent_id=value_meta_valuation。

external_agent_id 规则：
external_agent_id=valuation_meta；legacy_agent_id=a18_meta_valuation 只作为迁移备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不把 valuation_meta 当 primary id；不改元学习估值业务逻辑。

允许改动范围：
production wrapper、schema/protocol、identity tests、deployment package。

需要审计的文件：
service.py / app.py / main.py、compute response builder、schemas/protocol、tests、runbook；参考 /tmp/lma-r8-8h-service-backup/20260610T035804Z/value_meta_valuation。

需要修复的字段：
agent_id=value_meta_valuation；external_agent_id=valuation_meta；tool_result.schema_version=agent_conclusion_v1；dimension=value；role=direction；as_of/data_as_of；safe evidence。

需要运行的本地测试：
identity contract test；agent_conclusion_v1 schema test；success/partial/error mock tests；unsafe-field test；py_compile。

重新部署要求：
production 10002 必须加载新 wrapper 后才能重测。

production re-smoke 边界：
GET /health，POST /compute，adapter mapping。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-IDENTITY-FIX-RESEARCH

```text
你是 value_research_synthesis 的 Codex / Claude Code production identity 修复助手。

目标：
修复 production 10006 的 analyst research synthesis 输出 identity 和 value L2 wrapper。

背景：
R8-8P production health/compute 可达，但 adapter 以 unknown_agent_id 拒绝。dev smoke log 记录 external service id 为 analyst_research。

适用 agent_id：
value_research_synthesis

production endpoint：
http://127.0.0.1:10006

fixed DAG id 规则：
envelope.agent_id=value_research_synthesis；tool_result.agent_id=value_research_synthesis。

external_agent_id 规则：
external_agent_id=analyst_research；legacy_agent_id=a12_research_synthesis 只作为迁移备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不输出 raw report/provider response；不改研报整合业务逻辑。

允许改动范围：
production wrapper、schema/protocol、identity/value-dimension tests。

需要审计的文件：
service.py / app.py / main.py、compute builder、schemas/protocol、tests、README/runbook；参考 /tmp/lma-r8-8h-service-backup/20260610T040157Z/value_research_synthesis。

需要修复的字段：
external_agent_compute_v0 identity；tool_result identity；tool_result.schema_version=agent_conclusion_v1；dimension=value；role=direction；stance/confidence/evidence；as_of/data_as_of。

需要运行的本地测试：
identity contract test；report raw-output redaction test；schema test；anti-lookahead test；py_compile。

重新部署要求：
部署到 production 10006 并记录版本。

production re-smoke 边界：
只允许 /health + /compute + adapter mapping。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-IDENTITY-FIX-STOCK-TECHNICAL

```text
你是 market_stock_technical 的 Codex / Claude Code production identity 修复助手。

目标：
修复 production 10009 的 technical-stock output identity，并确保它保持 market L2 direction。

背景：
R8-8P production health/compute 可达，但 adapter 以 unknown_agent_id 拒绝。dev evidence 不能替代 production pass。

适用 agent_id：
market_stock_technical

production endpoint：
http://127.0.0.1:10009

fixed DAG id 规则：
envelope.agent_id=market_stock_technical；tool_result.agent_id=market_stock_technical。

external_agent_id 规则：
external_agent_id=technical_stock；legacy_agent_id=a10_stock_technical_analysis 只作为迁移备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不改技术分析算法/数据；不输出 raw indicator dump。

允许改动范围：
production response wrapper、identity/dimension tests、schema/protocol。

需要审计的文件：
service.py / app.py / main.py、compute builder、schema/protocol、tests、runbook；参考 /tmp/lma-r8-8h-service-backup/20260610T040408Z/market_stock_technical。

需要修复的字段：
agent_id=market_stock_technical；external_agent_id=technical_stock；tool_result.schema_version=agent_conclusion_v1；dimension=market；role=direction；stance/confidence/evidence；as_of/data_as_of。

需要运行的本地测试：
identity contract test；dimension=market test；schema test；unsafe-field test；py_compile。

重新部署要求：
production 10009 部署新 wrapper 后申请 resmoke。

production re-smoke 边界：
GET /health，POST /compute，adapter mapping。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-IDENTITY-FIX-CAPITAL-FLOW

```text
你是 market_capital_flow_chip 的 Codex / Claude Code production identity 修复助手。

目标：
把 production 10022 的资金流/筹码服务输出修成 fixed DAG market L2 contract。

背景：
R8-8P production health/compute 可达，但 adapter 因 identity mismatch 拒绝。dev 阶段的 money_flow wrapper 需要回填到 production。

适用 agent_id：
market_capital_flow_chip

production endpoint：
http://127.0.0.1:10022

fixed DAG id 规则：
envelope.agent_id=market_capital_flow_chip；tool_result.agent_id=market_capital_flow_chip。

external_agent_id 规则：
external_agent_id=money_flow，除非 production owner 明确变更；legacy_agent_id 当前无固定值，只能作为备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不把 dev 8022 临时服务当 production；不改资金流业务算法。

允许改动范围：
production wrapper、identity/dimension tests、deployment runbook。

需要审计的文件：
service.py、compute_core.py、schema/protocol、tests、runbook；参考 /tmp/lma-r8-8m-service-backup/20260610T072025Z/service_patch_manifest.json。

需要修复的字段：
agent_id=market_capital_flow_chip；external_agent_id=money_flow；tool_result.schema_version=agent_conclusion_v1；dimension=market；role=direction；as_of/data_as_of；safe evidence.

需要运行的本地测试：
identity contract test；market dimension test；schema test；success/partial/error mock tests；py_compile。

重新部署要求：
部署到 production 10022；回传 production cwd/root 和版本，证明不是 dev process。

production re-smoke 边界：
只允许 /health + /compute + adapter mapping。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-FUND-SERVICE-DISCOVERY

```text
你是 market_fund_manager_behavior 的 Codex / Claude Code production service discovery 与 identity 修复助手。

目标：
确认 fund-manager behavior 的 production service ownership、root、port、external_agent_id，并修复为 fixed DAG market L2 wrapper。

背景：
R8-8P 发现 production subservice http://127.0.0.1:10007 可达，但 output identity 不兼容 fixed DAG。主仓库 runtime_bindings 仍没有明确 endpoint metadata。

适用 agent_id：
market_fund_manager_behavior

production endpoint：
候选为 http://127.0.0.1:10007，但必须由 owner 确认 service root、cmdline、deploy runbook 和 fixed DAG mapping。

fixed DAG id 规则：
envelope.agent_id=market_fund_manager_behavior；tool_result.agent_id=market_fund_manager_behavior。

external_agent_id 规则：
external_agent_id 必须由 production health/schema/docs 确认，不能猜。legacy_agent_id=a13_fund_manager_behavior 只能作为迁移备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不把未知 subservice 强行接入；不改基金经理行为业务算法。

允许改动范围：
service discovery docs、production wrapper、health/compute schema、contract tests、runbook。

需要审计的文件：
production service root、cmdline/runbook、health endpoint、compute builder、schema/protocol、tests、deployment manifest。

需要修复的字段：
external_agent_health_v0 identity；external_agent_compute_v0 identity；tool_result.schema_version=agent_conclusion_v1；dimension=market；role=direction；agent_id/external_agent_id；as_of/data_as_of。

需要运行的本地测试：
service discovery doc check；identity contract test；market dimension test；schema test；unsafe-field test；py_compile。

重新部署要求：
production owner 确认并部署 wrapper 后，回传 endpoint、root、version。

production re-smoke 边界：
只允许 /health + /compute + adapter mapping；禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-IPO-WRAPPER

```text
你是 market_ipo_investor_behavior 的 Codex / Claude Code production compute wrapper 修复助手。

目标：
让 production 10008 输出 fixed DAG market L2 agent_conclusion_v1，而不是 raw/scaffold/business payload 或错误 identity。

背景：
R8-8P production health/compute 可达，但 adapter 因 identity/shape 不兼容拒绝。这个服务的 protocol drift 比普通 identity fix 更大。

适用 agent_id：
market_ipo_investor_behavior

production endpoint：
http://127.0.0.1:10008

fixed DAG id 规则：
envelope.agent_id=market_ipo_investor_behavior；tool_result.agent_id=market_ipo_investor_behavior。

external_agent_id 规则：
external_agent_id=ipo_investor_behavior，除非 production owner 明确变更。legacy_agent_id=a14_ipo_investor_behavior 只能作为迁移备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不返回 raw CRJ/scaffold/business payload；不改 IPO 行为模型/数据源。

允许改动范围：
production response wrapper、schema/protocol、wrapper tests、runbook。

需要审计的文件：
production service.py / app.py / main.py、compute_core、response builder、schema/protocol、tests、README/runbook。

需要修复的字段：
schema_version=external_agent_compute_v0；agent_id=market_ipo_investor_behavior；external_agent_id=ipo_investor_behavior；tool_result.schema_version=agent_conclusion_v1；dimension=market；role=direction；stance/confidence/evidence；as_of/data_as_of。

需要运行的本地测试：
wrapper contract test；raw payload does-not-leak test；market dimension test；schema success/partial/error tests；py_compile。

重新部署要求：
部署 production 10008 wrapper 后申请 production resmoke。

production re-smoke 边界：
GET /health，POST /compute，adapter mapping。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-COMMODITY-COMPUTE-FIX

```text
你是 macro_commodity_pricing 的 Codex / Claude Code production compute 修复助手。

目标：
修复 production 10004 的 /v1/agent/compute，使其返回 fixed DAG L2 macro agent_conclusion_v1。

背景：
R8-8P production /health passed，但 /compute 返回 compute_http_error。dev 8004 未监听或不稳定，不能作为 production evidence。

适用 agent_id：
macro_commodity_pricing

production endpoint：
http://127.0.0.1:10004

fixed DAG id 规则：
envelope.agent_id=macro_commodity_pricing；tool_result.agent_id=macro_commodity_pricing。

external_agent_id 规则：
external_agent_id=price_influence_agent；legacy_agent_id=a04_commodity_hedging 只能作为迁移备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不把 health pass 写成 compute pass；不改商品定价业务模型/数据源/算法。

允许改动范围：
production compute route/wrapper、fail-soft envelope、schema/protocol、contract tests、runbook。

需要审计的文件：
/sdb/dlut/prod/商品定价分析智能体/agent协议/service.py、compute pipeline、schema/protocol、tests、README/runbook、deployment scripts。

需要修复的字段：
external_agent_compute_v0；status；agent_id=macro_commodity_pricing；external_agent_id=price_influence_agent；tool_result.schema_version=agent_conclusion_v1；dimension=macro；role=direction；target examples such as CU；as_of/data_as_of。

需要运行的本地测试：
compute route contract test；error-path typed envelope test；macro dimension test；schema success/partial/error tests；unsafe-field test；py_compile。

重新部署要求：
production 10004 必须部署修复后的 compute wrapper。

production re-smoke 边界：
只允许 /health + /compute + adapter mapping。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-MACRO-INDEX-OWNER

```text
你是 macro_index_valuation 的 Codex / Claude Code production semantic owner 确认助手。

目标：
确认股票指数估值服务是否应作为 fixed DAG macro L2 signal；如果不能确认，保持 deferred。

背景：
R8-8P 发现 production 10003 endpoint，但没有强行 smoke 为 macro，因为服务语义更像 index/value valuation。

适用 agent_id：
macro_index_valuation

production endpoint：
http://127.0.0.1:10003

fixed DAG id 规则：
只有 owner 明确批准 macro L2 后，agent_id 才能是 macro_index_valuation。

external_agent_id 规则：
external_agent_id=valuation_index；legacy_agent_id=a11_index_technical_analysis 只作为迁移备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不强行把 index/value valuation 归一为 macro；不先写 wrapper 再补语义解释。

允许改动范围：
语义审计、owner decision 记录、future wrapper scope 文档。若 owner 批准，再另开 production wrapper 修复。

需要审计的文件：
README、service.py、schema/protocol、sample output、domain docs、owner/runbook 文档。

需要修复的字段：
本 prompt 不直接修字段。若 owner 批准，下一步 wrapper 必须输出 agent_conclusion_v1、dimension=macro、agent_id=macro_index_valuation。

需要运行的本地测试：
只读语义审计不跑 live endpoint。可以跑文档/schema unit checks。

重新部署要求：
只有实现 wrapper 后才需要 production deployment。

production re-smoke 边界：
owner 确认 + wrapper 部署后，才允许 /health + /compute + adapter mapping。禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-MACRO-SENTIMENT-L2-OR-L3

```text
你是 macro_sentiment 的 Codex / Claude Code production payload 分类助手。

目标：
判断 macro_sentiment 是 L2 agent_conclusion_v1 direction 服务，还是未来 L3/macro_conclusion_v1/regulator 服务。

背景：
R8-8P 将 production 10018 标为 semantic deferred。它看起来像 placeholder 或 L3/regulator-style 服务，不应强塞 L2。

适用 agent_id：
macro_sentiment

production endpoint：
http://127.0.0.1:10018

fixed DAG id 规则：
如果分类为 L2，agent_id 必须是 macro_sentiment。如果分类为 L3/regulator，不要伪造 L2 fixed DAG id。

external_agent_id 规则：
从 production health/schema/docs 中确认。legacy_agent_id=a07_macro_sentiment 只能作为迁移备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不把 macro_conclusion_v1 或 regulator payload 强塞进 L2；不绕过 owner 语义判断。

允许改动范围：
只读分类、owner decision、future wrapper/L3 design 文档。若确认 L2，再另开 production wrapper phase。

需要审计的文件：
production service.py / app.py、schema/protocol、sample output、README/runbook、domain owner notes。

需要修复的字段：
本 prompt 不直接修字段。若为 L2，后续 wrapper 必须输出 agent_conclusion_v1、dimension=macro、role=direction。

需要运行的本地测试：
只读分类不跑 live endpoint；可跑 schema/document checks。

重新部署要求：
只有实现 L2 wrapper 或 L3 adapter 后才部署。

production re-smoke 边界：
分类后另开 /health + /compute resmoke；禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-MACRO-HOTSPOT-L2-OR-L3

```text
你是 macro_industry_hotspot 的 Codex / Claude Code production payload 分类助手。

目标：
判断行业热点服务是 macro L2 direction signal，还是未来 L3/macro_conclusion/regulator payload。

背景：
R8-8P 将 production 10019 标为 semantic deferred。当前不允许把不清楚的宏观热点聚合强行塞进 L2。

适用 agent_id：
macro_industry_hotspot

production endpoint：
http://127.0.0.1:10019

fixed DAG id 规则：
若 owner 确认为 L2，agent_id=macro_industry_hotspot。若为 L3/regulator，保持 deferred。

external_agent_id 规则：
从 production health/schema/docs 中确认。legacy_agent_id=a08_industry_hotspot 只能作为迁移备注。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不强行 L3 到 L2；不绕开 owner semantic decision。

允许改动范围：
只读分类、owner decision、future wrapper/L3 design 文档。

需要审计的文件：
production service.py / app.py、schema/protocol、sample output、README/runbook、domain owner notes。

需要修复的字段：
本 prompt 不直接修字段。若为 L2，后续 wrapper 输出 agent_conclusion_v1、dimension=macro、role=direction、target examples such as 白酒。

需要运行的本地测试：
只读分类不跑 live endpoint；可跑 schema/document checks。

重新部署要求：
只有实现 L2 wrapper 或 L3 adapter 后才部署。

production re-smoke 边界：
分类后另开 /health + /compute resmoke；禁止 /invoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-L3-ADAPTER-DESIGN

```text
你是 fixed DAG L3 adapter/runtime design 助手。

目标：
为 value_composite、market_composite、risk_composite、macro_composite 设计未来 L3 adapter/runtime，而不是把它们按 L2 production smoke 处理。

背景：
R8-8P/R8-8P-DOCS-QA 保持 L3 deterministic seams。L3 需要 dimension_composite_result_v1 或明确的 composite payload，不是 agent_conclusion_v1。

适用 agent_id：
value_composite, market_composite, risk_composite, macro_composite

production endpoint：
当前不适用。不要访问 production composite endpoints，也不要把旧 10015/10016 等服务直接当 current authority。

fixed DAG id 规则：
各 composite fixed DAG ids 保持 primary ids；不得使用 legacy aNN id 作为 current truth。

external_agent_id 规则：
若未来有 external composite 服务，只能作为 provenance/service id，不得覆盖 fixed DAG id。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不把 L2/risk_conclusion/macro_conclusion/raw payload 强塞 L3；不允许 sentiment_company_radar 进 risk_composite。

允许改动范围：
设计文档、contract proposal、provider-free sample fixtures、unit tests；实现需另开批准 phase。

需要审计的文件：
fixed_dag_contracts.py、fixed_dag_external_adapter.py、docs/CONTRACTS.md、docs/EXTERNAL_AGENT_PAYLOAD_MAPPING_FIXED_DAG.md、sample payloads、current L3 deterministic executor path。

需要修复的字段：
本 prompt 是设计，不直接修字段。设计必须覆盖 status、confidence、members/evidence、provenance、as_of/data_as_of、安全清洗。

需要运行的本地测试：
future phase 应跑 adapter unit tests、contract tests、static quality。当前设计阶段不跑 live endpoints。

重新部署要求：
无 production deployment；这是 main-system design 预备。

production re-smoke 边界：
未来 L3 phase 单独定义；当前禁止 /invoke 和 production composite smoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-L4-ADAPTER-DESIGN

```text
你是 fixed DAG L4 adapter/runtime design 助手。

目标：
为 decision_synthesizer 和 report_generator 设计未来 L4 adapter/runtime 或继续保持 deterministic seam。

背景：
R8-8P 没有把 L4 当 production external L2 service。L4 涉及 decision_result_v1、report_result_v1 和 public transcript safety。

适用 agent_id：
decision_synthesizer, report_generator

production endpoint：
当前不适用；不要访问 production L4 endpoints。

fixed DAG id 规则：
decision_synthesizer 和 report_generator 保持 fixed DAG ids。

external_agent_id 规则：
未来 external id 只能作为 provenance，不得覆盖 primary id。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live flags；不输出 raw graph messages、raw agent JSON、manager internals、provider raw responses；不把 L4 report raw text直接变成 public transcript。

允许改动范围：
设计文档、contract proposal、public-safety policy、sample fixtures、unit tests；实现需另开批准 phase。

需要审计的文件：
fixed_dag_contracts.py、public_mapping.py、public_api.py、docs/CONTRACTS.md、docs/FRONTEND_V2.md、current report/decision deterministic seams。

需要修复的字段：
本 prompt 是设计，不直接修字段。设计必须覆盖 decision/report schema、public-safe summary、provenance、redaction、status/failure behavior。

需要运行的本地测试：
future phase 应跑 public API tests、adapter/contract tests、frontend public-safety tests。当前设计阶段不跑 live endpoints。

重新部署要求：
无 production deployment；这是 main-system design 预备。

production re-smoke 边界：
未来 L4 phase 单独定义；当前禁止 /invoke 和 production L4 smoke。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-PROD-INVOKE-AUDIT-PREP

```text
你是 production /v1/agent/invoke audit 准备助手。注意：本 prompt 只做只读审计准备，不允许调用 /invoke。

目标：
审计已经 production health + compute + adapter mapping pass 的服务，判断它们是否可以进入后续 tiny allowlist controlled /v1/agent/invoke smoke。

背景：
R8-8P 只有五个 agent 达到 production health + compute + adapter mapping pass：risk_identification、risk_compliance_review、risk_financial_fraud、risk_crash、macro_analysis。只有这五个可以用本 prompt 做 invoke audit prep。

适用 agent_id：
risk_identification, risk_compliance_review, risk_financial_fraud, risk_crash, macro_analysis

production endpoint：
risk_identification: http://127.0.0.1:10010
risk_compliance_review: http://127.0.0.1:10011
risk_financial_fraud: http://127.0.0.1:10013
risk_crash: http://127.0.0.1:10012
macro_analysis: http://127.0.0.1:10014

fixed DAG id 规则：
invoke 若未来被 smoke，输出必须维持 compute 中已验证的 fixed DAG primary id，不得退回 service id 或 legacy id。

external_agent_id 规则：
risk_identification=market_risk_reasoning；risk_compliance_review=announcement_compliance；risk_financial_fraud=financial_fraud_agent；risk_crash=crash_risk；macro_analysis=macro_analysis。

禁止项：
本 prompt 不调用 /v1/agent/invoke；不改 runtime_bindings；不设置 live_verified=true；不设置 invoke_enabled_by_default=true；不改业务模型/数据源；不把 compute pass 写成 invoke pass。

允许改动范围：
只读审计 invoke endpoint implementation、schema、tests、failure modes、whether invoke reuses compute_core safely。

需要审计的文件：
invoke endpoint implementation、compute endpoint implementation、schema/protocol、contract tests、runbook、redaction/sanitization logic。

需要修复的字段：
本阶段不修字段；只记录 invoke 是否复用 compute identity、tool_result schema、status mapping、safe failure, and redaction.

需要运行的本地测试：
只允许 local unit/static tests，不跑 live invoke。可以跑 schema unit tests、py_compile、no-secret/traceback fixtures。

重新部署要求：
若发现 invoke wrapper gap，另开 production service fix/deploy phase；本 prompt 不部署。

production re-smoke 边界：
下一阶段才可能允许 tiny allowlist /invoke smoke。本 prompt 只读审计，不调用 endpoint。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段
D) 本地测试结果
E) production 部署/重启方式
F) production re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```
