# Fixed DAG Developer Agent Fix Prompt Catalog

这是一份 production-first 的开发者修复提示词目录，用于 R8-8P-DOCS-QA
之后的生产问题处置。每段 prompt 都可以直接复制给 Codex / Claude Code
或服务 owner 使用。

R8-10B 增加了 L3 provider-free adapter pure mapping：
`dimension_conclusion_v1`、`risk_conclusion_v1`、`macro_conclusion_v1` 可以
本地映射为 `dimension_composite_result_v1`。这只是主系统 adapter 能力，不是
L3 production readiness，不启用 runtime bindings，也不允许直接调用 `/invoke`。

R8-10D 已在当前机器的四个 L3 服务目录中做了 bounded protocol wrapper
backfill，并写入 repo-external manifest：
`/tmp/lma-r8-10d-l3-service-backup/20260610T142216Z/service_patch_manifest.json`。
这些补丁只说明服务端协议层已有本地回填草案：没有调用 endpoint、没有重启服务、
没有 production smoke，也没有启用 runtime bindings。下面的 L3 prompt 仍应作为
服务 owner 将补丁回填到各自源码仓库、部署、再申请 R8-10E controlled smoke 的
执行手册。

R8-10D-SNAPSHOT 额外建立了临时交接仓库：
`/sdb/dlut/service-shadow-repos/l3-composite-services`。该仓库只保存四个
L3 服务的说明文件、R8-10D manifest 和 zero-context patch，不复制完整生产目录，
也不是长期源码真源。正式源码仓库可用后，owner 应把 shadow repo 中的 patch
回填到正式仓库并按生产流程部署。

R8-8P 已经证明：dev evidence 只能作为历史参考和 backfill 线索，不能当作
production pass。所有修复必须进入服务 owner 的源码仓库，重新部署到
production endpoint，并经过 production `/health` + `/v1/agent/compute` +
main-system adapter mapping 复测，才可以改变 production matrix 状态。

R8-8Q 已经在当前 production 目录中完成部分 bounded protocol remediation
并通过 production re-smoke：四个 value L2、`market_stock_technical`、
`market_capital_flow_chip`、`sentiment_company_radar`、以及
`market_ipo_investor_behavior` 已有 production compute evidence。下面保留
这些服务的修复 prompt，主要用于服务 owner 将 R8-8Q 生产目录补丁回填到正式
源码仓库、部署、并在后续 resmoke 中防止回归。

R8-11B 已完成首批 tiny allowlist controlled production `/v1/agent/invoke`
smoke：`risk_identification`、`risk_compliance_review`、`risk_crash`、
`risk_financial_fraud`、`value_research_synthesis`。这些结果只是受控
invoke evidence，不是 runtime binding enablement、live_verified 或默认图执行。
后续 prompt 仍应区分：已通过首批 invoke 的 agent 可以进入 runtime-binding
prepare review；其余 compute-pass agent 仍需要只读 invoke audit 或 wrapper backfill。

CS1-C3X 生成了新的 owner handoff patch root：
`/sdb/dlut/prod/backups/cs1c3x_20260622T103501Z/owner_handoffs`。这些 patch
是 review handoff，不是 owner-dev 已接受的源码变更。服务 owner 应先阅读每个
`manifest.json`、`apply_check.txt`、`test_plan.txt` 和 `rollback.txt`，再决定是否
在自己的 dev repo 中应用。`market_stock_technical` 的 patch dry-run 当前失败，
必须由 owner 手工处理上下文/行尾 drift。

CS1-C3R copies those handoff artifacts into a portable output bundle:
`/tmp/lma-cs1c3r-evidence-durability-20260622T121352Z/portable_owner_patches`.
Nine patches are `owner_patch_ready`; `market_stock_technical` remains
`owner_patch_conflict` because current owner files have both line-ending and
context drift. Eleven authority-unresolved services intentionally have no
patch and require owner/source decisions first.

默认边界：

- 不调用 `/v1/agent/invoke`，除非单独批准 invoke smoke；R8-11B 只批准并执行了
  5 个 production allowlist 服务，其余 invoke prompt 仍只允许审计准备。
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
| `PROMPT-PROD-SENTIMENT-MARKET-ONLY` | `sentiment_company_radar` R8-8Q backfill prompt; keep market-only |
| `PROMPT-PROD-IDENTITY-FIX-VALUE-TRADITIONAL` | `value_traditional_valuation` R8-8Q backfill prompt |
| `PROMPT-PROD-IDENTITY-FIX-VALUE-ML` | `value_ml_valuation` R8-8Q backfill prompt |
| `PROMPT-PROD-IDENTITY-FIX-VALUE-META` | `value_meta_valuation` R8-8Q backfill prompt |
| `PROMPT-PROD-IDENTITY-FIX-RESEARCH` | `value_research_synthesis` R8-8Q backfill prompt |
| `PROMPT-PROD-IDENTITY-FIX-STOCK-TECHNICAL` | `market_stock_technical` R8-8Q backfill prompt |
| `PROMPT-PROD-IDENTITY-FIX-CAPITAL-FLOW` | `market_capital_flow_chip` R8-8Q backfill prompt |
| `PROMPT-PROD-FUND-SERVICE-DISCOVERY` | `market_fund_manager_behavior` service metadata + identity |
| `PROMPT-PROD-IPO-WRAPPER` | `market_ipo_investor_behavior` R8-8Q backfill prompt |
| `PROMPT-PROD-COMMODITY-COMPUTE-FIX` | `macro_commodity_pricing` production compute failure |
| `PROMPT-PROD-MACRO-INDEX-OWNER` | `macro_index_valuation` semantic decision |
| `PROMPT-PROD-MACRO-SENTIMENT-L2-OR-L3` | `macro_sentiment` L2/L3 classification |
| `PROMPT-PROD-MACRO-HOTSPOT-L2-OR-L3` | `macro_industry_hotspot` L2/L3 classification |
| `PROMPT-L3-VALUE-COMPOSITE-BACKFILL` | `value_composite` service protocol backfill |
| `PROMPT-L3-MARKET-COMPOSITE-BACKFILL` | `market_composite` service protocol backfill |
| `PROMPT-L3-RISK-COMPOSITE-BACKFILL` | `risk_composite` service protocol backfill |
| `PROMPT-L3-MACRO-COMPOSITE-BACKFILL` | `macro_composite` service protocol backfill |
| `PROMPT-L3-DIMENSION-CONCLUSION-WRAPPER` | `value_composite`, `market_composite` L3 payload wrapper |
| `PROMPT-L3-RISK-CONCLUSION-WRAPPER` | `risk_composite` L3 risk gate wrapper |
| `PROMPT-L3-MACRO-CONCLUSION-WRAPPER` | `macro_composite` L3 macro regulator wrapper |
| `PROMPT-L3-ADAPTER-MAPPING` | main-system L3 adapter maintainer |
| `PROMPT-PROD-L3-ADAPTER-DESIGN` | value/market/risk/macro composites |
| `PROMPT-PROD-L4-ADAPTER-DESIGN` | `decision_synthesizer`, `report_generator` |
| `PROMPT-PROD-INVOKE-AUDIT-PREP` | production health+compute+adapter pass candidates not yet covered by controlled invoke smoke |

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
R8-8P 中 production /health 和 /compute 可达，但主系统 adapter 以 unknown_agent_id 拒绝。说明 production 没有回填 dev 阶段的 fixed DAG identity wrapper。R8-13G 后还要确认正式源码包含顶层 `stance` / `confidence` 投影：生产 wrapper 不能只返回 `normalized.stance`，否则端到端报告会再次出现 `direction_stance_missing`。

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
external_agent_compute_v0.agent_id；external_agent_compute_v0.external_agent_id；tool_result.agent_id；tool_result.external_agent_id；tool_result.schema_version=agent_conclusion_v1；dimension=value；role=direction；top-level stance；top-level confidence；as_of/data_as_of。

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
dev 阶段已经修过 identity 并通过 controlled smoke，但 R8-8P production 仍因 unknown_agent_id 被 adapter 拒绝。R8-13G 后还要确认正式源码包含顶层 `stance` / `confidence` 投影：生产 wrapper 不能只返回 `normalized.stance`，否则主系统 adapter 会 fail closed。

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
external_agent_compute_v0.agent_id/external_agent_id；tool_result.agent_id/external_agent_id；tool_result.schema_version=agent_conclusion_v1；dimension=value；role=direction；top-level stance；top-level confidence；evidence/as_of/data_as_of。

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
R8-8P production compute 可达，但 adapter 以 unknown_agent_id 拒绝；这通常表示 dev wrapper 没有回填到 production。R8-13G 后还要确认正式源码包含顶层 `stance` / `confidence` 投影：生产 wrapper 不能只返回 `normalized.stance`，否则端到端报告会再次把该 agent 当成 adapter-error evidence。

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
agent_id=value_meta_valuation；external_agent_id=valuation_meta；tool_result.schema_version=agent_conclusion_v1；dimension=value；role=direction；top-level stance；top-level confidence；as_of/data_as_of；safe evidence。

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

## PROMPT-L3-VALUE-COMPOSITE-BACKFILL

```text
你是综合估值智能体 value_composite 的 Codex / Claude Code 服务端协议回填助手。本轮只做 L3 compute wrapper 和 schema/test 回填，不改估值业务逻辑。

目标：
把综合估值服务补成 fixed DAG L3 value_composite 协议输出。/v1/agent/compute 必须返回 external_agent_compute_v0，并在 tool_result 中返回 dimension_conclusion_v1，使主系统 R8-10B adapter 可以纯映射为 dimension_composite_result_v1。

背景：
R8-10C 只读审计发现，当前服务进程可在 production 10015 和 dev 8015 被进程表观察到，但没有调用任何 endpoint。源码里有 dimension_conclusion_v1 helper，但常量仍偏向 composite_valuation / value_ml_valuation 兼容层，/health 也更像 sample/L2 兼容信息。当前形态不能直接作为 value_composite L3 production evidence。

适用 agent_id：
value_composite。

生产/开发 endpoint 区分：
production 端口按当前登记为 10015；dev 端口按当前登记为 8015。修复时可以在服务仓库内跑本地单元测试，但不要把 dev 结果写成 production pass。production 只有重新部署并完成后续受控 /health + /compute smoke 后才算证据。

fixed DAG id 规则：
envelope.agent_id 和 tool_result.agent_id 必须是 value_composite。不能使用 composite_valuation、value_ml_valuation、valuation_ml、中文名或 aNN legacy id 作为 primary agent_id。

external_agent_id 规则：
external_agent_id 是服务自有 id，建议继续使用 composite_valuation 或 owner 确认的新 service id。external_agent_id 只能作为服务身份/provenance，不能覆盖 fixed DAG primary id。

输入 L2 contracts：
members[] 只能来自 value L2 roster：value_traditional_valuation、value_ml_valuation、value_meta_valuation、value_research_synthesis。不能把 market/risk/macro agent 放入 value members。

输出 payload schema：
external_agent_compute_v0.tool_result.dimension_conclusion_v1。tool_result 必须包含 schema_version、agent_id=value_composite、external_agent_id、dimension=value、role=direction、target、stance、confidence、members[]、evidence、as_of、data_as_of、status。members[] 中每项至少包含 agent_id、stance、confidence、weight、status，weight 总和约等于 1.0。

禁止项：
不得调用 /v1/agent/invoke；不得改 runtime_bindings；不得设置 live_verified=true 或 invoke_enabled_by_default=true；不得修改估值模型、特征、数据源、聚合算法；不得保存 raw provider response、secret、traceback、chain-of-thought；不得把 L2 agent_conclusion_v1 当成 L3 输出。

允许改动范围：
只允许改综合估值服务项目中的 /health、/v1/agent/compute response wrapper、schema/model、sample、服务本地 tests 或 README/runbook。不要改主系统 graph/executor/public API/frontend。

需要审计的文件：
service.py、schemas.py、compute_core 或 aggregation 调用点、response builder、tests、README/start/runbook。

需要实现的字段：
external_agent_compute_v0 envelope；tool_result.schema_version=dimension_conclusion_v1；tool_result.agent_id=value_composite；tool_result.external_agent_id；dimension=value；role=direction；members[] fixed DAG ids；stance；confidence；evidence；as_of；data_as_of；warnings/errors。

本地测试要求：
至少运行 python3 -m py_compile <changed_python_files>。如果项目有 pytest，新增或更新测试验证 health JSON、compute envelope、dimension_conclusion_v1、members 权重和、identity、data_as_of <= as_of。禁止运行 provider/live/invoke tests。

production re-smoke 边界：
修复部署后只申请后续受控 GET /health 和 POST /v1/agent/compute；仍禁止 /v1/agent/invoke；不改主系统 runtime bindings。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段示例
D) 本地测试结果
E) production 部署/重启方式
F) production /health + /compute re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-L3-MARKET-COMPOSITE-BACKFILL

```text
你是市场面综合智能体 market_composite 的 Codex / Claude Code 服务端协议回填助手。本轮只补齐 L3 member identity 和 wrapper 合同，不改市场融合业务逻辑。

目标：
确认并修正 market_composite 的 production /v1/agent/compute 输出，使它稳定返回 external_agent_compute_v0.tool_result.dimension_conclusion_v1，并能被主系统 R8-10B adapter 纯映射。

背景：
R8-10C 只读审计发现，production 10023 和 dev 8023 有进程证据，但未调用 endpoint。源码已经接近目标形态：compute envelope 和 dimension_conclusion_v1 存在，agent_id 也接近 market_composite。主要风险是 adapter-facing dimension 仍可能使用中文“市场面”，且 members[] 使用 service-local id，如 technical_stock、money_flow、market_sentiment，而主系统 adapter 需要英文 dimension=market 和 fixed DAG market L2 roster。

适用 agent_id：
market_composite。

生产/开发 endpoint 区分：
production 端口按当前登记为 10023；dev 端口按当前登记为 8023。8051/8052/8503 等是市场服务下游或子服务，不是 market_composite 的生产证据。

fixed DAG id 规则：
envelope.agent_id 和 tool_result.agent_id 必须是 market_composite。dimension 必须是英文 market。中文“市场面”可以作为 label 或 display 字段，但不要作为 adapter-facing dimension 主字段。

external_agent_id 规则：
external_agent_id 是服务自有 id；可使用 market_composite 或 owner 确认的 service id，但不能覆盖 fixed DAG id。

输入 L2 contracts：
members[] 只能来自 market L2 roster：market_stock_technical、market_fund_manager_behavior、market_ipo_investor_behavior、market_capital_flow_chip、sentiment_company_radar。sentiment_company_radar 只允许出现在 market，严禁进入 risk。

输出 payload schema：
external_agent_compute_v0.tool_result.dimension_conclusion_v1。字段包括 schema_version、agent_id=market_composite、external_agent_id、dimension=market、role=direction、target、stance、confidence、members[]、evidence、as_of、data_as_of、status。members[] 权重总和约等于 1.0。

禁止项：
不得调用 /v1/agent/invoke；不得改 runtime_bindings；不得设置 live flags；不得把 sentiment_company_radar 迁移到 risk；不得改市场融合模型、期限折算、权重算法或下游数据源；不得保存 raw provider response、secret、traceback、chain-of-thought。

允许改动范围：
只允许改市场面综合服务项目的 response wrapper、schema/test/sample、member id normalization、README/runbook。不要改主系统 graph/executor/runtime。

需要审计的文件：
config.py、composite.py、service.py、schemas.py、members/client.py、tests/test_external_contract.py 或相关 tests、README/runbook。

需要实现的字段：
canonical dimension=market；members[].agent_id 从 service-local id 映射到 fixed DAG ids；external_agent_compute_v0 envelope；tool_result.schema_version=dimension_conclusion_v1；bounded evidence；as_of/data_as_of。

本地测试要求：
至少运行 python3 -m py_compile <changed_python_files>。如果项目有 pytest，新增或更新测试验证 dimension=market、member ids 属于 fixed DAG market roster、权重和、sentiment market-only、anti-lookahead。

production re-smoke 边界：
部署后只申请受控 GET /health 和 POST /v1/agent/compute；不调用 /invoke；不修改 runtime bindings。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段示例
D) 本地测试结果
E) production 部署/重启方式
F) production /health + /compute re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-L3-RISK-COMPOSITE-BACKFILL

```text
你是综合风险智能体 risk_composite 的 Codex / Claude Code 服务端协议回填助手。本轮只补齐 adapter-facing risk_conclusion_v1 wrapper，不改 D-S 风险融合算法。

目标：
让 production /v1/agent/compute 返回 external_agent_compute_v0.tool_result.risk_conclusion_v1，并满足主系统 R8-10B adapter 对 risk_composite 的字段要求。

背景：
R8-10C 只读审计发现，production 10016 和 dev 8016 有进程证据，但未调用 endpoint。源码已有 risk_conclusion_v1 语义，但当前 primary id 是 risk_synthesis，dimension 使用中文“风险”，gate 是嵌套对象，且缺少 adapter-facing top-level contributing_agents。主系统 adapter 需要 agent_id=risk_composite、dimension=risk、role=gate 和 flat gate 字段。

适用 agent_id：
risk_composite。

生产/开发 endpoint 区分：
production 端口按当前登记为 10016；dev 端口按当前登记为 8016。任何 dev 测试只能作为修复验证，不能当 production pass。

fixed DAG id 规则：
envelope.agent_id 和 tool_result.agent_id 必须是 risk_composite。不要使用 risk_synthesis、risk_fusion_agent、中文名或 legacy id 作为 primary agent_id。

external_agent_id 规则：
external_agent_id 是服务自有 id，可以由 owner 确认为 risk_synthesis 或 risk_synthesis_service。它只能作为服务身份，不得覆盖 risk_composite。

输入 L2 contracts：
contributing_agents 只能来自 risk L2 roster：risk_crash、risk_financial_fraud、risk_identification、risk_compliance_review。不得包含 sentiment_company_radar。

输出 payload schema：
external_agent_compute_v0.tool_result.risk_conclusion_v1。tool_result 必须包含 schema_version、agent_id=risk_composite、external_agent_id、dimension=risk、role=gate、gate=pass|penalty|veto|manual_review、risk_score、penalty、confidence、triggered_flags、red_lines、contributing_agents、evidence、as_of、data_as_of、status。可以保留原 D-S 富字段作为 bounded detail，但不要让它替代 adapter-facing flat 字段。

禁止项：
不得调用 /v1/agent/invoke；不得改 runtime_bindings；不得设置 live flags；不得输出 direction stance；不得把 risk_conclusion_v1 强塞成 L2 agent_conclusion_v1；不得改风险模型阈值、D-S 算法、成员服务 URL 或数据源；不得保存 secret、traceback、chain-of-thought、raw provider response。

允许改动范围：
只允许改综合风险服务项目的 /health、/v1/agent/compute response wrapper、schema/test/sample、README/runbook。不要改主系统 graph/executor/runtime。

需要审计的文件：
risk_constraint_agent_app.py、schemas.py、compute_core/fusion builder、response builder、tests/test_risk_domain_contract.py、tests/test_service_contract.py、README/runbook。

需要实现的字段：
fixed DAG identity；canonical dimension=risk；flat gate string；top-level penalty；risk_score in 0..1；contributing_agents risk-only；bounded triggered_flags/red_lines；external_agent_compute_v0 envelope。

本地测试要求：
至少运行 python3 -m py_compile <changed_python_files>。如果项目有 pytest，新增或更新测试覆盖 pass、penalty、veto、manual_review，验证 no sentiment_company_radar，验证 data_as_of <= as_of。

production re-smoke 边界：
部署后只申请受控 GET /health 和 POST /v1/agent/compute；不调用 /invoke；不修改 runtime bindings。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段示例
D) 本地测试结果
E) production 部署/重启方式
F) production /health + /compute re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-L3-MACRO-COMPOSITE-BACKFILL

```text
你是宏观综合智能体 macro_composite 的 Codex / Claude Code 服务端协议回填助手。本轮只补齐 fixed DAG identity、compute envelope/runbook 和 macro_conclusion_v1 wrapper，不改宏观 regime 算法。

目标：
让 macro_composite 的 production /v1/agent/compute 明确返回可被主系统 R8-10B adapter 纯映射的 L3 macro payload。允许使用 external_agent_compute_v0.tool_result.macro_conclusion_v1；如果服务因历史原因返回 external_agent_response_v0，也必须明确记录并保持 tool_result 合规。

背景：
R8-10C 只读审计发现，production 10024 有进程证据，当前未看到 dev 8024 listener，也未调用 endpoint。源码已经有 macro_conclusion_v1、dimension=macro、role=regulator、value/market-only dimension_weights 和 risk_sensitivity，但 primary id 是 macro_synthesis，不是 fixed DAG id macro_composite。

适用 agent_id：
macro_composite。

生产/开发 endpoint 区分：
production 端口按当前登记为 10024。dev 8024 当前未从进程表确认，owner 需要补 runbook 或启动说明。dev 结果不能当 production pass。

fixed DAG id 规则：
envelope.agent_id 和 tool_result.agent_id 必须是 macro_composite。不要使用 macro_synthesis 作为 primary fixed DAG id。

external_agent_id 规则：
external_agent_id 是服务自有 id，建议保留 macro_synthesis_service 或 owner 确认的新 service id。external_agent_id 不得覆盖 macro_composite。

输入 L2 contracts：
contributing_agents 应来自 macro L2 roster：macro_analysis、macro_commodity_pricing、macro_index_valuation、macro_sentiment、macro_industry_hotspot。若某成员是占位或不可用，应在 warnings/provenance 中 bounded 说明。

输出 payload schema：
tool_result.schema_version=macro_conclusion_v1；agent_id=macro_composite；external_agent_id；dimension=macro；role=regulator；regime；dimension_weights 只能包含 value 和 market，且数值和约等于 1.0；risk_sensitivity in 0..1；style_bias bounded；contributing_agents；evidence；as_of；data_as_of；status。

禁止项：
不得调用 /v1/agent/invoke；不得改 runtime_bindings；不得设置 live flags；不得输出 direction stance；dimension_weights 不得包含 risk 或 macro；不得把 macro_conclusion_v1 强塞成 L2 agent_conclusion_v1；不得改 regime 模型、特征、权重算法、成员服务 URL 或数据源。

允许改动范围：
只允许改宏观综合服务项目的 /health、/v1/agent/compute response wrapper、schema/test/sample、README/runbook。不要改主系统 graph/executor/runtime。

需要审计的文件：
config.py、service.py、synthesis_core.py、schemas.py、agent_clients.py、tests/test_synthesis.py、tests/test_regime.py、README/runbook。

需要实现的字段：
fixed DAG identity；production/dev runbook；external_agent_compute_v0 or explicitly supported response envelope；tool_result.agent_id=macro_composite；contributing_agents；dimension_weights value/market only；risk_sensitivity；bounded evidence/provenance。

本地测试要求：
至少运行 python3 -m py_compile <changed_python_files>。如果项目有 pytest，新增或更新测试验证 agent_id=macro_composite、dimension_weights 只含 value/market、risk_sensitivity、contributing_agents、data_as_of <= as_of，并增加负例拒绝 risk/macro weights。

production re-smoke 边界：
部署后只申请受控 GET /health 和 POST /v1/agent/compute；不调用 /invoke；不修改 runtime bindings。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段示例
D) 本地测试结果
E) production 部署/重启方式
F) production /health + /compute re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-L3-DIMENSION-CONCLUSION-WRAPPER

```text
你是 fixed DAG L3 value/market composite 服务端协议修复助手。

目标：
为 value_composite 或 market_composite 服务实现 production /v1/agent/compute 的 L3 输出 wrapper，使它返回 external_agent_compute_v0.tool_result.dimension_conclusion_v1，并能被主系统 R8-10B adapter 纯映射为 dimension_composite_result_v1。

上下文：
R8-10B 已经在主系统支持 dimension_conclusion_v1 -> dimension_composite_result_v1 的 provider-free pure mapping。这个能力不等于 live readiness，也不启用 runtime bindings。服务 owner 需要先把 L3 服务输出补齐，再请求后续受控 L3 /health + /compute smoke。

适用 agent_id：
value_composite, market_composite

固定 DAG id 规则：
tool_result.agent_id 必须分别是 value_composite 或 market_composite。不得使用中文名、旧 aNN id、服务内部 id 或 L2 agent id 作为 primary agent_id。

输入 L2 contracts：
value_composite 只能消费 value L2 members：value_traditional_valuation、value_ml_valuation、value_meta_valuation、value_research_synthesis。
market_composite 只能消费 market L2 members：market_stock_technical、market_fund_manager_behavior、market_ipo_investor_behavior、market_capital_flow_chip、sentiment_company_radar。sentiment_company_radar 只能在 market 出现，不能进入 risk。

输出 payload schema：
schema_version=dimension_conclusion_v1；dimension=value 或 market；role=direction；members 为 DimensionMember[]；每个 member 至少包含 agent_id、stance、confidence、weight、status；weight 总和约等于 1.0；confidence 在 0..1；as_of/data_as_of 满足 data_as_of <= as_of；evidence 只放安全摘要。

禁止项：
不得调用 /v1/agent/invoke；不得改 runtime_bindings；不得设置 live_verified 或 invoke_enabled_by_default；不得把 risk 或 macro agent 放进 value/market members；不得把完整 raw_output、provider raw response、traceback、secret、chain-of-thought 写入 payload。

允许改动范围：
只修改当前 L3 服务项目里的 /health、/v1/agent/compute response wrapper、schema/test/sample；不改主系统 graph/executor；不改业务模型、特征工程、算法和数据源。

需要审计的文件：
服务端 app/service/router 文件、compute_core 调用点、response builder、schema/model 文件、本地 tests、README/runbook。

需要实现的字段：
external_agent_compute_v0 envelope；tool_result.schema_version=dimension_conclusion_v1；tool_result.agent_id；tool_result.external_agent_id；dimension；members[]；stance；confidence；evidence；as_of；data_as_of；status；warnings/errors。

需要运行的测试：
python3 -m py_compile <changed_python_files>；如项目有 tests，运行相关 pytest；如项目有 ruff，运行相关 ruff check。禁止运行 provider/live/invoke tests。

不得调用 /invoke：
本 prompt 只允许修 compute wrapper 和本地测试。/invoke 审计必须另开阶段。

不得设置 live flags：
不要修改 runtime bindings，不要设置 live_verified=true 或 invoke_enabled_by_default=true。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段示例
D) 本地测试结果
E) production 部署/重启方式
F) production /health + /compute re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-L3-RISK-CONCLUSION-WRAPPER

```text
你是 fixed DAG L3 risk_composite 服务端协议修复助手。

目标：
为 risk_composite 服务实现 production /v1/agent/compute 的 L3 风险闸门 wrapper，使它返回 external_agent_compute_v0.tool_result.risk_conclusion_v1，并能被主系统 R8-10B adapter 纯映射为 dimension_composite_result_v1。

上下文：
R8-10B 已经支持 risk_conclusion_v1 -> dimension_composite_result_v1。risk_composite 是风险 gate，不是方向票。它不会输出普通 stance，也不能消费 sentiment_company_radar。

适用 agent_id：
risk_composite

固定 DAG id 规则：
tool_result.agent_id 必须是 risk_composite；dimension 必须是 risk；role 必须是 gate。external_agent_id 只能保存服务 id，不得覆盖 fixed DAG id。

输入 L2 contracts：
contributing_agents 只能来自 risk L2 roster：risk_crash、risk_financial_fraud、risk_identification、risk_compliance_review。

输出 payload schema：
schema_version=risk_conclusion_v1；agent_id=risk_composite；dimension=risk；role=gate；gate 只能是 pass、penalty、veto、manual_review；risk_score 在 0..1；penalty 在 0..1；confidence 在 0..1；triggered_flags 和 red_lines 是安全 bounded 字符串列表；as_of/data_as_of 满足 data_as_of <= as_of。

禁止项：
不得调用 /v1/agent/invoke；不得改 runtime_bindings；不得设置 live flags；不得输出 direction stance；不得把 sentiment_company_radar 放进 contributing_agents；不得把 risk_conclusion_v1 强塞成 L2 agent_conclusion_v1。

允许改动范围：
只修改 risk_composite 服务项目里的 /health、/v1/agent/compute response wrapper、schema/test/sample；不改主系统 runtime；不改风险模型或阈值算法。

需要审计的文件：
服务端 app/service/router 文件、risk aggregation 或 compute_core 调用点、response builder、schema/model 文件、本地 tests、README/runbook。

需要实现的字段：
external_agent_compute_v0 envelope；tool_result.schema_version=risk_conclusion_v1；tool_result.agent_id=risk_composite；external_agent_id；dimension=risk；role=gate；gate；risk_score；penalty；triggered_flags；red_lines；contributing_agents；evidence；as_of；data_as_of；status。

需要运行的测试：
python3 -m py_compile <changed_python_files>；相关 pytest/ruff 如可用。增加至少一个 manual_review fixture，并确认 veto 时 gate=veto、veto 语义可被 adapter 映射。

不得调用 /invoke：
本 prompt 只允许修 compute wrapper 和本地测试。/invoke 另开阶段。

不得设置 live flags：
不要修改 runtime bindings，不要设置 live_verified=true 或 invoke_enabled_by_default=true。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段示例
D) 本地测试结果
E) production 部署/重启方式
F) production /health + /compute re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-L3-MACRO-CONCLUSION-WRAPPER

```text
你是 fixed DAG L3 macro_composite 服务端协议修复助手。

目标：
为 macro_composite 服务实现 production /v1/agent/compute 的 L3 宏观调节器 wrapper，使它返回 external_agent_compute_v0.tool_result.macro_conclusion_v1，并能被主系统 R8-10B adapter 纯映射为 dimension_composite_result_v1。

上下文：
R8-10B 已经支持 macro_conclusion_v1 -> dimension_composite_result_v1。macro_composite 是 regulator，不是普通方向票。宏观只调节 value/market 方向权重；risk 是独立 gate；macro 本身不是 dimension_weights 的一个 key。

适用 agent_id：
macro_composite

固定 DAG id 规则：
tool_result.agent_id 必须是 macro_composite；dimension 必须是 macro；role 必须是 regulator。external_agent_id 只能保存服务 id。

输入 L2 contracts：
contributing_agents 只能来自 macro L2 roster：macro_analysis、macro_commodity_pricing、macro_index_valuation、macro_sentiment、macro_industry_hotspot。

输出 payload schema：
schema_version=macro_conclusion_v1；agent_id=macro_composite；dimension=macro；role=regulator；regime 必填；dimension_weights 必须且只能包含 value、market；risk_sensitivity 在 0..1；style_bias 如存在只能是 bounded 安全摘要；confidence 在 0..1；as_of/data_as_of 满足 data_as_of <= as_of。

禁止项：
不得调用 /v1/agent/invoke；不得改 runtime_bindings；不得设置 live flags；不得输出 direction stance；dimension_weights 不得包含 risk 或 macro；不得把 macro_conclusion_v1 强塞成 L2 agent_conclusion_v1。

允许改动范围：
只修改 macro_composite 服务项目里的 /health、/v1/agent/compute response wrapper、schema/test/sample；不改主系统 runtime；不改宏观模型或权重算法。

需要审计的文件：
服务端 app/service/router 文件、macro aggregation 或 compute_core 调用点、response builder、schema/model 文件、本地 tests、README/runbook。

需要实现的字段：
external_agent_compute_v0 envelope；tool_result.schema_version=macro_conclusion_v1；tool_result.agent_id=macro_composite；external_agent_id；dimension=macro；role=regulator；regime；dimension_weights={value, market}；risk_sensitivity；style_bias；contributing_agents；evidence；as_of；data_as_of；status。

需要运行的测试：
python3 -m py_compile <changed_python_files>；相关 pytest/ruff 如可用。增加一个 fixture 验证 dimension_weights 只含 value/market，另一个负例验证 risk/macro keys 被拒绝。

不得调用 /invoke：
本 prompt 只允许修 compute wrapper 和本地测试。/invoke 另开阶段。

不得设置 live flags：
不要修改 runtime bindings，不要设置 live_verified=true 或 invoke_enabled_by_default=true。

最终回传格式：
A) 修改范围
B) 修复前问题
C) 修复后字段示例
D) 本地测试结果
E) production 部署/重启方式
F) production /health + /compute re-smoke 结果
G) 非声明：未调用 /invoke、未设置 live flags、未改 runtime bindings
```

## PROMPT-L3-ADAPTER-MAPPING

```text
你是 fixed DAG 主系统 L3 adapter maintainer。

目标：
维护或扩展 main-system provider-free L3 adapter mapping。当前 R8-10B 已支持 dimension_conclusion_v1、risk_conclusion_v1、macro_conclusion_v1 以及 external_agent_compute_v0 / external_agent_response_v0 tool_result envelope。

上下文：
L3 mapping 只处理已经拿到的 payload dict，不做 HTTP/provider 调用，不接 active runtime。任何服务端 smoke、runtime binding、/invoke audit 都必须另开阶段。

适用 agent_id：
value_composite, market_composite, risk_composite, macro_composite。

固定 DAG id 规则：
value/market 使用 dimension_conclusion_v1；risk 使用 risk_conclusion_v1；macro 使用 macro_conclusion_v1。不得让 L3 主要沿用 L2 agent_conclusion_v1。

输入 L2 contracts：
mapping 必须校验 members/contributing_agents 来自对应 L2 roster；market 可含 sentiment_company_radar；risk 不得含 sentiment_company_radar。

输出 payload schema：
统一输出 dimension_composite_result_v1，且只保留 bounded provenance、member summaries、triggered flags、red lines、style bias，不保留完整 raw object。

禁止项：
不调用 /health、/compute、/invoke；不改 runtime_bindings；不设置 live flags；不改 graph/executor/public API/frontend；不把 adapter unit test 当 live readiness。

允许改动范围：
src/react_agent/fixed_dag_external_adapter.py、src/react_agent/fixed_dag_contracts.py、相关 unit tests、contract/docs/changelog/ADR。

需要审计的文件：
fixed_dag_external_adapter.py、fixed_dag_contracts.py、test_fixed_dag_external_adapter.py、test_fixed_dag_contracts.py、docs/CONTRACTS.md、docs/EXTERNAL_AGENT_PAYLOAD_MAPPING_FIXED_DAG.md。

需要实现的字段：
schema_version dispatch；identity/dimension validation；data_as_of <= as_of；member weights；risk gate；macro value/market-only dimension_weights；safe provenance；controlled adapter failure reason。

需要运行的测试：
.venv/bin/python -m ruff check src/react_agent/fixed_dag_external_adapter.py src/react_agent/fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_contracts.py
.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_contracts.py -q
.venv/bin/python scripts/quality/run_quality.py --mode static
git diff --check

不得调用 /invoke：
本 prompt 不允许 live endpoint 调用。

不得设置 live flags：
不要修改 runtime bindings，不要设置 live_verified=true 或 invoke_enabled_by_default=true。

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
你是 fixed DAG L4 decision/report 服务化验证助手。

目标：
把 decision_synthesizer 和 report_generator 按正式 L4 agent 的身份接入 default-off /v1/agent/compute 验证路径。主系统 dev 已有 adapter/bridge/executor handoff；本 prompt 负责服务 owner 或主系统维护者做受控服务 evidence，而不是默认启用 runtime。

背景：
R8-8P 没有把 L4 当 production external L2 service。R8-12D 先提供了主系统内部 default-off LLM report synthesis fallback。R8-13 L4 handoff 后，主系统可以在显式 demo flag + allowlist 下把 decision_synthesizer 映射为 decision_result_v1，把 report_generator 映射为 report_result_v1。L4 仍是 public transcript safety 边界；没有 production /health + /compute evidence 之前，matrix 状态仍是 production_l3_l4_deferred。

适用 agent_id：
decision_synthesizer, report_generator

production endpoint：
候选 loopback 端口为 decision_synthesizer=http://127.0.0.1:10025，report_generator=http://127.0.0.1:10026。只有在用户明确批准 controlled L4 smoke 时才访问；不要把 sandbox loopback 当生产默认 runtime。

fixed DAG id 规则：
decision_synthesizer 和 report_generator 保持 fixed DAG ids。

external_agent_id 规则：
external id 只能作为 provenance，不得覆盖 primary fixed DAG id。

禁止项：
不调用 /invoke；不改 runtime_bindings；不设置 live_verified=true；不设置 invoke_enabled_by_default=true；不把 /compute evidence 当 /invoke evidence；不输出 raw graph messages、raw agent JSON、manager internals、provider raw responses、traceback、endpoint URLs 或 secret；不把 L4 report raw text 直接变成 public transcript。

允许改动范围：
L4 service wrapper、compute-only request/response builder、contract tests、sample fixtures、public-safety policy、main-system adapter/contract tests、docs/changelog/ADR。runtime binding enablement 必须另开批准 phase。

需要审计的文件：
fixed_dag_external_adapter.py、fixed_dag_external_compute_bridge.py、fixed_dag_executor.py、fixed_dag_contracts.py、fixed_dag_report_synthesizer.py、fixed_dag_l4_decision_synthesizer.py、public_mapping.py、public_contracts.py、docs/CONTRACTS.md、docs/FRONTEND_V2.md、current report/decision deterministic seams。

需要修复的字段：
decision_synthesizer 必须返回 decision_result_v1，包含 decision/action、confidence、rationale、dimension impacts、risk guard/override context、status、as_of/data_as_of。report_generator 必须返回 report_result_v1，包含 public-safe title、answer、sections、evidence_cards、limitations、status、as_of/data_as_of。所有字段都必须通过 main-system validator 和 unsafe-text filter。

需要运行的本地测试：
py_compile；adapter mapping tests；bridge allowlist/context tests；executor overlay tests；public mapping tests；report_result/final_emit payload tests；frontend public type/build check if public fields changed。controlled service smoke 只在用户批准后运行 /health + /v1/agent/compute，禁止 /invoke。

重新部署要求：
如果是服务 owner 实现，必须提供服务 root、端口、启动命令、版本、health JSON、compute sample、contract test 结果。主系统 dev handoff 合入不等于 production deployment。

production re-smoke 边界：
只允许 controlled /health + /v1/agent/compute + main-system adapter mapping。必须显式 allowlist decision_synthesizer/report_generator。禁止 /invoke；禁止改 runtime bindings；禁止设置 live flags。通过后仍只说明 L4 compute evidence，不自动进入 runtime enabled。

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
R8-8P 首批只有五个 agent 达到 production health + compute + adapter mapping pass。R8-10E/R8-10F 又补齐四个 L3 composite 的 production compute evidence，R8-8Q 补齐八个 value/market L2 的 production compute evidence。R8-11B 已经对 `risk_identification`、`risk_compliance_review`、`risk_crash`、`risk_financial_fraud`、`value_research_synthesis` 完成 controlled production invoke smoke。只有当前 matrix 中 health + compute + adapter mapping 全部 pass、且尚未通过 controlled invoke 的 agent，才继续用本 prompt 做 invoke audit prep；失败、semantic deferred、endpoint missing 的 agent 不能进入 invoke audit。

适用 agent_id：
risk_identification, risk_compliance_review, risk_financial_fraud, risk_crash, macro_analysis,
value_traditional_valuation, value_ml_valuation, value_meta_valuation, value_research_synthesis,
market_stock_technical, market_capital_flow_chip, sentiment_company_radar, market_ipo_investor_behavior,
value_composite, market_composite, risk_composite, macro_composite

production endpoint：
risk_identification: http://127.0.0.1:10010
risk_compliance_review: http://127.0.0.1:10011
risk_financial_fraud: http://127.0.0.1:10013
risk_crash: http://127.0.0.1:10012
macro_analysis: http://127.0.0.1:10014
value_traditional_valuation: http://127.0.0.1:10000
value_ml_valuation: http://127.0.0.1:10001
value_meta_valuation: http://127.0.0.1:10002
value_research_synthesis: http://127.0.0.1:10006
market_stock_technical: http://127.0.0.1:10009
market_capital_flow_chip: http://127.0.0.1:10022
sentiment_company_radar: http://127.0.0.1:10020
market_ipo_investor_behavior: http://127.0.0.1:10008
value_composite: http://127.0.0.1:10015
market_composite: http://127.0.0.1:10023
risk_composite: http://127.0.0.1:10016
macro_composite: http://127.0.0.1:10024

fixed DAG id 规则：
invoke 若未来被 smoke，输出必须维持 compute 中已验证的 fixed DAG primary id，不得退回 service id 或 legacy id。

external_agent_id 规则：
risk_identification=market_risk_reasoning；risk_compliance_review=announcement_compliance；risk_financial_fraud=financial_fraud_agent；risk_crash=crash_risk；macro_analysis=macro_analysis；value_traditional_valuation=valuation_traditional；value_ml_valuation=valuation_ml；value_meta_valuation=valuation_meta；value_research_synthesis=analyst_research；market_stock_technical=technical_stock；market_capital_flow_chip=money_flow；sentiment_company_radar=company_sentiment_radar；market_ipo_investor_behavior=ipo_investor_behavior；value_composite=composite_valuation；market_composite、risk_composite、macro_composite 使用各自 R8-10E/R8-10F smoke 记录的 production external service id。

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
