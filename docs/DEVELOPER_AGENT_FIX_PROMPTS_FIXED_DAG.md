# Fixed DAG Developer Agent Fix Prompt Catalog

This production-first catalog persists the developer prompts for Phase R8-8P:
Production Endpoint Readiness Rebaseline.

Every prompt distinguishes dev historical evidence from production evidence.
Dev pass is useful for debugging and backfill, but it is not production pass.
Production remediation must be redeployed to the production service and followed
by production `/health` + `/v1/agent/compute` resmoke before any invoke audit.

These prompts do not authorize `/v1/agent/invoke`, runtime binding enablement,
`live_verified=true`, or `invoke_enabled_by_default=true`.

## Prompt Index

| Prompt id | Applies to |
| --- | --- |
| `PROMPT-PROD-HEALTH-FIX` | Production `/health` missing, non-JSON, unsafe, or wrong identity |
| `PROMPT-PROD-COMPUTE-WRAPPER` | Production `/compute` missing, raw payload, wrong envelope, missing `tool_result` |
| `PROMPT-PROD-IDENTITY-FIX` | Production `agent_id` / `external_agent_id` mismatch |
| `PROMPT-PROD-ADAPTER-MAPPING-FIX` | Supported v2.3.1 payload family needs provider-free main-system mapping |
| `PROMPT-PROD-BACKFILL-DEV-PATCH` | Service passed in dev because of non-git patch; production must be backfilled and redeployed |
| `PROMPT-PROD-IPO-WRAPPER` | `market_ipo_investor_behavior` production wrapper |
| `PROMPT-PROD-COMMODITY-RUNBOOK` | `macro_commodity_pricing` production compute/runbook |
| `PROMPT-PROD-MACRO-INDEX-OWNER` | `macro_index_valuation` semantic decision |
| `PROMPT-PROD-MACRO-L3-DEFER` | `macro_sentiment`, `macro_industry_hotspot` L2-vs-L3 classification |
| `PROMPT-PROD-FUND-SERVICE-DISCOVERY` | `market_fund_manager_behavior` production ownership/id discovery |
| `PROMPT-PROD-L3-ADAPTER-DESIGN` | `value_composite`, `market_composite`, `risk_composite`, `macro_composite` |
| `PROMPT-PROD-L4-ADAPTER-DESIGN` | `decision_synthesizer`, `report_generator` |
| `PROMPT-PROD-INVOKE-AUDIT-PREP` | Only agents with production health + compute + adapter mapping pass |

## PROMPT-PROD-HEALTH-FIX

```text
你是 production /health 合约修复助手。

目标：
修复生产服务 /health，使它返回安全、结构化、可审计的 JSON。该修复只解决 health gate，不代表 compute 或 invoke pass。

上下文：
R8-8P 对 production endpoint 重新基线。dev-only evidence 只能作为历史参考，不能当作 production readiness。

适用 agent_id：
任何 production /health missing、non-JSON、unsafe、wrong identity 的 fixed DAG agent。当前重点：financial_data_service。

production endpoint：
使用 R8-8P matrix 中该 agent 的 production endpoint。禁止使用 dev 800x/810x/830x endpoint 替代。

fixed DAG id rules：
health 可以报告 service identity，但必须包含或可追踪 fixed DAG agent_id，不得把 legacy aNN id 作为 primary fixed DAG id。

external_agent_id rules：
external_agent_id 必须是服务自有 id；legacy_agent_id 只能作为 migration note。

禁止项：
- 不调用 /v1/agent/invoke。
- 不改 runtime_bindings。
- 不设置 live_verified=true。
- 不设置 invoke_enabled_by_default=true。
- 不改业务模型、算法、特征工程、数据源。
- 不输出 secret、traceback、chain-of-thought、raw provider response。

允许改动范围：
- 生产服务 /health response builder。
- health schema/protocol。
- health contract tests。
- 不改 compute_core。

需要审计的文件：
- service.py / app.py / main.py
- schemas.py / protocol.py
- health endpoint implementation
- README / runbook
- tests

需要修复的字段：
- schema_version=external_agent_health_v0
- agent_id 或 fixed_dag_agent_id
- external_agent_id
- status
- version/build/runtime metadata
- no unsafe fields

需要运行的本地测试：
- python -m py_compile changed files
- 服务本地 health contract tests
- 禁止 provider/prod invoke tests

需要重新部署到 prod 的说明：
修复必须进入服务 owner 的源码仓库，部署到 production endpoint，再由主系统执行 R8-8P-style production resmoke。

production re-smoke 命令边界：
只允许 GET /health 和 POST /v1/agent/compute。禁止 /v1/agent/invoke。

最终回传格式：
- changed files
- production endpoint
- fixed health fields
- local tests
- deploy version
- confirmation: no runtime binding change, no live flag change, no /invoke call
```

## PROMPT-PROD-COMPUTE-WRAPPER

```text
你是 production /v1/agent/compute wrapper 修复助手。

目标：
让 production /v1/agent/compute 输出 fixed DAG 支持的 envelope 和 tool_result。

上下文：
R8-8P production smoke 只接受 production endpoint 的结构化 compute 结果。dev pass 不能替代 production pass。

适用 agent_id：
production compute missing、HTTP error、raw business payload、wrong envelope、missing tool_result、unsupported schema 的服务。

production endpoint：
使用 matrix 中的 production endpoint。不要使用 dev endpoint。

fixed DAG id rules：
tool_result.agent_id 必须是 fixed DAG snake_case id。

external_agent_id rules：
external_agent_id 保留服务自有 id；legacy aNN id 只能作为 legacy_agent_id/provenance。

禁止项：
- 不调用 /v1/agent/invoke。
- 不改 runtime_bindings。
- 不设置 live flags。
- 不改业务 compute_core、模型、数据源。

允许改动范围：
- production response wrapper。
- schema/protocol。
- contract tests。
- 不改业务核心算法。

需要审计的文件：
- compute endpoint implementation
- response builder
- schemas.py / protocol.py
- tests
- runbook/deploy scripts

需要修复的字段：
- schema_version=external_agent_compute_v0
- status=ok|partial|needs_clarification|error
- agent_id
- external_agent_id
- as_of
- data_as_of
- tool_result
- warnings/errors

需要运行的本地测试：
- wrapper contract tests
- anti-lookahead test: data_as_of <= as_of
- py_compile changed files
- 禁止 provider/prod invoke tests

需要重新部署到 prod 的说明：
部署 production wrapper 后重新执行 production /health + /compute + adapter mapping。

production re-smoke 命令边界：
只允许 GET /health 和 POST /v1/agent/compute。

最终回传格式：
- changed files
- production endpoint
- tool_result schema
- local tests
- deployment notes
- resmoke readiness
```

## PROMPT-PROD-IDENTITY-FIX

```text
你是 production identity 修复助手。

目标：
修复 production compute 输出中的 agent identity，使 fixed DAG primary id 和 service-owned external id 同时正确。

上下文：
R8-8P 中多个 production 服务 health/compute 通过，但 adapter 因 unknown_agent_id 失败。这通常表示 production 没有回填 dev 阶段的 identity wrapper。

适用 agent_id：
value_traditional_valuation、value_ml_valuation、value_meta_valuation、value_research_synthesis、market_stock_technical、market_capital_flow_chip，以及任何 production_identity_mismatch 服务。

production endpoint：
使用 R8-8P matrix 中对应 production endpoint。

fixed DAG id rules：
envelope.agent_id 和 tool_result.agent_id 必须是 fixed DAG id。

external_agent_id rules：
envelope.external_agent_id 和 tool_result.external_agent_id 必须是服务自有 id，例如 valuation_ml、valuation_meta、technical_stock、money_flow 等。

legacy_agent_id if known：
legacy aNN id 只能保留为 legacy_agent_id 或 provenance，不得作为 primary agent_id。

禁止项：
- 不放宽主系统 adapter identity gate。
- 不把 service id 当 fixed DAG primary id。
- 不调用 /v1/agent/invoke。
- 不改 runtime_bindings 或 live flags。
- 不改业务算法/数据源。

允许改动范围：
- production response builder。
- schema/protocol。
- identity contract tests。

需要审计的文件：
- service.py / app.py / main.py
- schemas.py / protocol.py
- compute response builder
- existing dev patch/backfill notes
- tests

需要修复的字段：
- envelope.agent_id
- envelope.external_agent_id
- tool_result.agent_id
- tool_result.external_agent_id
- legacy_agent_id
- provenance

需要运行的本地测试：
- identity contract tests
- adapter fixture test if available
- py_compile changed files

需要重新部署到 prod 的说明：
修复必须进入 production 服务部署；仅修 dev 不会改变 production readiness。

production re-smoke 命令边界：
GET /health, POST /v1/agent/compute, main-system adapter mapping. 禁止 /invoke。

最终回传格式：
- before/after identity fields
- changed files
- tests
- deployment version
- production resmoke result request
```

## PROMPT-PROD-ADAPTER-MAPPING-FIX

```text
你是主系统 provider-free adapter mapping 修复助手。

目标：
仅当 production 服务返回明确的 v2.3.1 payload family，而主系统缺少纯映射时，最小扩展 fixed_dag_external_adapter。

上下文：
R8-8P 不允许通过 adapter 放宽 identity 或语义 gate。adapter fix 只处理已支持/应支持的安全 payload family。

适用 agent_id：
仅适用于 production 返回标准 v2.3.1 payload，但 mapper 明显缺失 pure mapping 的服务。

production endpoint：
不由本 prompt 调用。使用 sanitized production artifact 作为 fixture 来源。

fixed DAG id rules：
不得接受 legacy aNN primary id、unknown id、sentiment-to-risk、L3 payload 强塞 L2。

external_agent_id rules：
external id 只进入 provenance，不作为 fixed DAG primary id。

禁止项：
- 不做 HTTP/provider 调用。
- 不接 executor active runtime。
- 不改 runtime_bindings。
- 不设置 live flags。
- 不修生产服务代码。

允许改动范围：
- src/react_agent/fixed_dag_external_adapter.py
- tests/unit_tests/test_fixed_dag_external_adapter.py
- docs/CONTRACTS.md if contract wording changes

需要审计的文件：
- fixed_dag_external_adapter.py
- fixed_dag_contracts.py
- production sanitized artifacts
- adapter unit tests

需要修复的字段：
只新增 provider-free mapping and validation；不得泄露 raw output。

需要运行的本地测试：
- ruff targeted files
- pytest tests/unit_tests/test_fixed_dag_external_adapter.py -q
- static quality

需要重新部署到 prod 的说明：
主系统 adapter change does not fix service production output. Production service may still need redeploy if identity/payload is wrong.

production re-smoke 命令边界：
After adapter change, rerun production /health + /compute + adapter mapping only. 禁止 /invoke。

最终回传格式：
- mapping added
- test fixture source
- tests
- non-claims
- remaining service-side blockers
```

## PROMPT-PROD-BACKFILL-DEV-PATCH

```text
你是 service owner 的 dev patch backfill 助手。

目标：
把之前让 dev 服务 pass 的非 git 补丁回填到服务源码仓库，部署到 production endpoint，然后重新做 production smoke。

上下文：
R8-8G/H/I/J/K/L/M 的 dev evidence 是 historical only。R8-8P 发现很多 production 服务没有这些补丁。

适用 agent_id：
所有 dev pass 但 production missing/failing 的服务，尤其 entity_relation_extractor、sentiment_company_radar、value/market identity mismatch 服务。

production endpoint：
如果已有 endpoint，使用 matrix 中 endpoint；如果 missing，先部署/注册 production endpoint。

fixed DAG id rules：
fixed DAG snake_case id 是 primary agent_id。

external_agent_id rules：
服务自有 id 放 external_agent_id。

legacy_agent_id if known：
保留 migration note，不作为 primary id。

禁止项：
- 不只修 dev。
- 不调用 /v1/agent/invoke。
- 不改 runtime_bindings。
- 不设置 live flags。
- 不改业务核心。

允许改动范围：
- 服务协议 wrapper。
- health/compute schema。
- tests。
- deployment packaging/runbook。

需要审计的文件：
- `/tmp/lma-r8-8*-service-backup/*`
- service owner repo files
- deployment scripts
- service tests

需要修复的字段：
按对应 dev patch manifest 回填 identity、schema_version、tool_result、dimension、risk_score、data_as_of/as_of。

需要运行的本地测试：
- service contract tests
- py_compile
- deployment smoke on production /health + /compute

需要重新部署到 prod 的说明：
必须部署到 production process; otherwise R8-8P status will not change.

production re-smoke 命令边界：
GET /health, POST /v1/agent/compute, adapter mapping. 禁止 /invoke。

最终回传格式：
- dev patch source
- service repo commit
- prod deployment version
- production endpoint
- production resmoke artifacts
```

## PROMPT-PROD-IPO-WRAPPER

```text
你是 market_ipo_investor_behavior 的 production wrapper 修复助手。

目标：
让 production 10008 输出 fixed DAG L2 market agent_conclusion_v1，而不是 raw/scaffold/business payload 或错误 identity。

上下文：
R8-8P production health/compute 可达，但 adapter 失败。dev evidence 也没有 production pass 效力。

适用 agent_id：
market_ipo_investor_behavior

production endpoint：
http://127.0.0.1:10008

fixed DAG id rules：
agent_id 必须是 market_ipo_investor_behavior。

external_agent_id rules：
external_agent_id 应为 ipo_investor_behavior 或 owner 确认的服务 id。

legacy_agent_id if known：
a14_ipo_investor_behavior 仅迁移备注。

禁止项：
- 不改业务模型/特征/算法/数据源。
- 不调用 /v1/agent/invoke。
- 不改 runtime bindings。
- 不设置 live flags。

允许改动范围：
- production service wrapper。
- schema/protocol。
- contract tests。

需要审计的文件：
- production market subagent service.py
- schemas/protocol
- README/runbook
- tests

需要修复的字段：
- external_agent_compute_v0
- tool_result.schema_version=agent_conclusion_v1
- role=direction
- dimension=market
- stance
- confidence
- evidence
- as_of/data_as_of

需要运行的本地测试：
- production wrapper contract tests
- py_compile changed files

需要重新部署到 prod 的说明：
部署后重新跑 production resmoke；dev-only pass 不接受。

production re-smoke 命令边界：
GET /health, POST /v1/agent/compute, adapter mapping. 禁止 /invoke。

最终回传格式：
- changed files
- external_agent_id
- test results
- production deploy notes
- resmoke result
```

## PROMPT-PROD-COMMODITY-RUNBOOK

```text
你是 macro_commodity_pricing 的 production compute 修复助手。

目标：
修复 production 10004 的 /v1/agent/compute，使其返回 fixed DAG L2 macro agent_conclusion_v1。

上下文：
R8-8P production /health pass，但 /compute HTTP error。之前 dev 8004 未监听，不能作为 production evidence。

适用 agent_id：
macro_commodity_pricing

production endpoint：
http://127.0.0.1:10004

fixed DAG id rules：
tool_result.agent_id=macro_commodity_pricing。

external_agent_id rules：
external_agent_id=price_influence_agent，除非服务 owner 明确更新。

legacy_agent_id if known：
a04_commodity_hedging 仅迁移备注。

禁止项：
- 不访问 dev 8004 作为 production 替代。
- 不调用 /v1/agent/invoke。
- 不改商品定价业务模型、数据源、算法。
- 不改 runtime bindings。

允许改动范围：
- production compute wrapper。
- error handling/fail-soft envelope。
- schema/tests/runbook。

需要审计的文件：
- /sdb/dlut/prod/商品定价分析智能体/agent协议/service.py
- schemas.py / protocol.py
- README/runbook
- tests

需要修复的字段：
- external_agent_compute_v0
- status
- agent_id/external_agent_id
- tool_result.agent_conclusion_v1
- dimension=macro
- target=CU
- as_of/data_as_of

需要运行的本地测试：
- wrapper tests
- py_compile
- production compute dry-run only if explicitly approved by maintainer

需要重新部署到 prod 的说明：
修复后生产进程必须加载新代码，再执行 R8-8P production resmoke。

production re-smoke 命令边界：
GET /health, POST /v1/agent/compute. 禁止 /invoke。

最终回传格式：
- root cause of compute_http_error
- changed files
- tests
- deploy notes
- production resmoke outcome
```

## PROMPT-PROD-MACRO-INDEX-OWNER

```text
你是 macro_index_valuation 的 production semantic owner 确认助手。

目标：
确认生产 10003 是否应作为 fixed DAG macro L2 signal，还是应保持 deferred。

上下文：
R8-8P 未 smoke compute，因为该服务更像 index/value valuation，缺少 owner 对 macro L2 的明确确认。

适用 agent_id：
macro_index_valuation

production endpoint：
http://127.0.0.1:10003

fixed DAG id rules：
若 owner 批准 macro L2，agent_id 必须是 macro_index_valuation。

external_agent_id rules：
runtime 候选为 valuation_index。

legacy_agent_id if known：
a11_index_technical_analysis 仅迁移备注。

禁止项：
- 不强行把 index/value valuation 归一为 macro。
- 不调用 /v1/agent/invoke。
- 不改 runtime bindings。
- 不设置 live flags。

允许改动范围：
本阶段只做语义确认和文档/owner 记录；确认后再另开 wrapper phase。

需要审计的文件：
- README
- service.py
- schema/protocol
- sample output
- owner/domain docs

需要修复的字段：
本阶段不修字段。确认后再定义 dimension=macro 的 agent_conclusion_v1 wrapper。

需要运行的本地测试：
只读阶段不跑 live endpoint。

需要重新部署到 prod 的说明：
若 owner 确认并实现 wrapper，需要生产部署后 resmoke。

production re-smoke 命令边界：
确认和 wrapper 后，只允许 /health + /compute，禁止 /invoke。

最终回传格式：
- owner decision yes/no/unknown
- semantic evidence
- allowed output contract
- next implementation prompt
```

## PROMPT-PROD-MACRO-L3-DEFER

```text
你是 macro_sentiment / macro_industry_hotspot 的 production payload 分类助手。

目标：
判断生产服务是 L2 agent_conclusion_v1，还是未来 L3/macro_conclusion_v1/regulator payload。

上下文：
R8-8P 将 10018/10019 标记为 production_semantic_deferred。它们看起来是 placeholder 或 L3/regulator-like 服务，不应强塞 L2。

适用 agent_id：
macro_sentiment, macro_industry_hotspot

production endpoint：
macro_sentiment: http://127.0.0.1:10018
macro_industry_hotspot: http://127.0.0.1:10019

fixed DAG id rules：
若分类为 L2，fixed DAG id 必须是对应 snake_case id。

external_agent_id rules：
从 production health/schema/docs 中确认。

legacy_agent_id if known：
macro_sentiment=a07_macro_sentiment。
macro_industry_hotspot=a08_industry_hotspot。

禁止项：
- 不把 macro_conclusion_v1 强塞 L2。
- 不调用 /v1/agent/invoke。
- 不改 runtime bindings。
- 不设置 live flags。

允许改动范围：
只读协议/语义分类；若确认为 L2，再另开 production wrapper phase。

需要审计的文件：
- production service.py
- schemas.py / protocol.py
- placeholder implementation
- README/docs

需要修复的字段：
本阶段不修字段，只分类。

需要运行的本地测试：
不跑 live endpoint。

需要重新部署到 prod 的说明：
若分类后需要 wrapper，必须部署到 production 后 resmoke。

production re-smoke 命令边界：
分类后只允许 /health + /compute，禁止 /invoke。

最终回传格式：
- classification=L2|L3|placeholder|unknown
- evidence
- next adapter/wrapper work
- whether production resmoke is allowed
```

## PROMPT-PROD-FUND-SERVICE-DISCOVERY

```text
你是 market_fund_manager_behavior 的 production service ownership 修复助手。

目标：
确认 10007 production subservice 是否应作为 fixed DAG market_fund_manager_behavior，并修复 identity/wrapper。

上下文：
R8-8P 发现 production 10007 存在，但 adapter 因 unknown_agent_id 失败。此前 dev 阶段没有有效 pass。

适用 agent_id：
market_fund_manager_behavior

production endpoint：
http://127.0.0.1:10007

fixed DAG id rules：
如果 owner 确认该服务对应 fixed DAG，tool_result.agent_id 必须是 market_fund_manager_behavior。

external_agent_id rules：
必须从 service constants/health/docs 中确认，不要猜。

legacy_agent_id if known：
a13_fund_manager_behavior 仅迁移备注。

禁止项：
- 不把综合市场服务或 stub 误当成 L2。
- 不调用 /v1/agent/invoke。
- 不改 runtime bindings。
- 不设置 live flags。

允许改动范围：
- service ownership docs。
- production wrapper。
- contract tests。

需要审计的文件：
- /sdb/dlut/prod/市场面综合智能体/subagents/fund_manager_behavior/service.py
- schema/protocol
- README/runbook
- tests

需要修复的字段：
- agent_id=market_fund_manager_behavior
- external_agent_id=confirmed service id
- dimension=market
- role=direction
- tool_result.schema_version=agent_conclusion_v1

需要运行的本地测试：
- wrapper contract tests
- py_compile

需要重新部署到 prod 的说明：
Production wrapper must be deployed before resmoke.

production re-smoke 命令边界：
GET /health, POST /v1/agent/compute, adapter mapping. 禁止 /invoke。

最终回传格式：
- ownership decision
- external_agent_id
- changed files
- tests
- production resmoke readiness
```

## PROMPT-PROD-L3-ADAPTER-DESIGN

```text
你是 fixed DAG L3 production adapter 设计助手。

目标：
设计 future L3 payload adapter，不接 active runtime，不把 L3 payload 强塞 L2。

上下文：
R8-8P 仍将 value_composite、market_composite、risk_composite、macro_composite 标记为 production_l3_l4_deferred。

适用 agent_id：
value_composite, market_composite, risk_composite, macro_composite

production endpoint：
当前无 active external production endpoint 要测试。若存在候选，只做 deferred inventory。

fixed DAG id rules：
L3 composite id 只映射到 dimension_composite_result_v1。

external_agent_id rules：
服务 id 只进入 provenance，不作为 fixed DAG id。

legacy_agent_id if known：
仅迁移备注。

禁止项：
- 不调用 endpoint。
- 不改 runtime bindings。
- 不设置 live flags。
- 不把 sentiment_company_radar 接入 risk_composite。
- 不强塞 L3 到 L2 conclusion_object。

允许改动范围：
- design docs
- provider-free adapter proposal
- unit tests proposal

需要审计的文件：
- fixed_dag_contracts.py
- fixed_dag_external_adapter.py
- docs/CONTRACTS.md
- readiness ladder

需要修复的字段：
- dimension_composite_result_v1
- contributing_agents
- evidence_refs
- manual_review
- provenance

需要运行的本地测试：
设计阶段不跑 live endpoint；后续只跑 unit/static。

需要重新部署到 prod 的说明：
无 production deployment until adapter/runtime phase is approved.

production re-smoke 命令边界：
未来 phase 才定义；当前禁止 /invoke。

最终回传格式：
- schema design
- adapter scope
- tests
- runtime non-claims
```

## PROMPT-PROD-L4-ADAPTER-DESIGN

```text
你是 fixed DAG L4 production adapter 设计助手。

目标：
设计 future L4 decision/report adapter，或确认继续 deterministic seam。

上下文：
R8-8P 没有 L4 production external readiness。decision_synthesizer 和 report_generator 仍是 deterministic seams。

适用 agent_id：
decision_synthesizer, report_generator

production endpoint：
当前不测试 production endpoint。

fixed DAG id rules：
decision_synthesizer -> decision_result_v1。
report_generator -> report_result_v1。

external_agent_id rules：
如未来有服务 id，只进入 provenance。

legacy_agent_id if known：
report_generator 可保留 a25_report_center 迁移备注。

禁止项：
- 不生成 public transcript raw agent JSON。
- 不调用 endpoint。
- 不改 runtime bindings。
- 不设置 live flags。
- 不接 active runtime。

允许改动范围：
- design docs
- contract tests
- adapter pure mapping draft

需要审计的文件：
- fixed_dag_contracts.py
- public transcript/mapping docs
- docs/CONTRACTS.md
- docs/QUALITY.md

需要修复的字段：
- decision_result_v1
- report_result_v1
- safe public transcript projection
- provenance

需要运行的本地测试：
unit/static only; no provider/live.

需要重新部署到 prod 的说明：
无 production deployment until adapter/runtime phase is approved.

production re-smoke 命令边界：
未来 phase 才定义；当前禁止 /invoke。

最终回传格式：
- L4 adapter scope
- schema mapping
- public safety boundary
- next phase DoD
```

## PROMPT-PROD-INVOKE-AUDIT-PREP

```text
你是 production invoke audit 准备助手。

目标：
只读审计已 production health + compute + adapter mapping pass 的服务，判断是否可以进入后续 controlled /v1/agent/invoke smoke。不要直接调用 /invoke。

上下文：
R8-8P 只有 risk_identification、risk_compliance_review、risk_financial_fraud、risk_crash、macro_analysis 通过 production adapter mapping。

适用 agent_id：
仅适用于 production_compute_pass 的 agent。

production endpoint：
使用 R8-8P matrix 中的 production endpoint。

fixed DAG id rules：
invoke 输出必须维持 compute 中已验证的 fixed DAG id。

external_agent_id rules：
external id 只作为服务 id/provenance。

legacy_agent_id if known：
仅迁移备注。

禁止项：
- 本 prompt 不调用 /v1/agent/invoke。
- 不改 runtime bindings。
- 不设置 live_verified=true。
- 不设置 invoke_enabled_by_default=true。
- 不改业务模型/数据源。

允许改动范围：
只读审计 invoke endpoint implementation, tests, schema, failure modes.

需要审计的文件：
- invoke endpoint implementation
- compute endpoint implementation
- schema/protocol
- tests
- runbook

需要修复的字段：
本阶段不修字段；只确认 invoke 是否复用 compute_core 和 safe response mapping。

需要运行的本地测试：
本阶段不跑 live invoke。可以跑 local unit/static only.

需要重新部署到 prod 的说明：
若发现 invoke wrapper gap，另开 production service fix and deploy phase。

production re-smoke 命令边界：
下一阶段才允许 tiny allowlist /invoke smoke；本 prompt 禁止调用。

最终回传格式：
- invoke endpoint file/function
- compute reuse yes/no
- expected response schema
- safety/fail-soft behavior
- whether ready for controlled invoke smoke
```
