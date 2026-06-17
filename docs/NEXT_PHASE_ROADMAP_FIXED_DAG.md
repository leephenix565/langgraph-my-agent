# Fixed DAG Next Phase Roadmap

本文是 fixed DAG 主系统的后续推进路线图。它不是新的运行时合同，也不是
production readiness 证明；它只把当前进度、目录使用方式、下一步优先级和
禁止越界项集中在一个入口，方便新开的 Codex 对话快速理解项目。

## Scope

本文覆盖主系统仓库：

```text
/sdb/dlut/dev/langgraph-my-agent
/sdb/dlut/prod/langgraph-my-agent
/sdb/dlut/sandbox/langgraph-my-agent-r8-a-class
```

本文不覆盖外部生产智能体服务源码的归属。外部智能体服务仍由各服务 owner
维护；主系统只记录协议、adapter、demo bridge、trace、readiness evidence
和开发者修复提示词。

## Current Snapshot

截至 R8-13I：

- 主系统已经是固定 DAG 架构，27 个 formal agent id 由
  `config/fixed_dag/agent_catalog.json` 定义。
- default-off external compute demo bridge 已存在。只有显式 flag 和 allowlist
  同时开启时，主系统才会调用 production `/v1/agent/compute`。
- L3 adapter pure mapping 已支持 `dimension_conclusion_v1`,
  `risk_conclusion_v1`, `macro_conclusion_v1`。
- 四个 L3 综合智能体已有 production compute evidence。
- 已有一批 L1/L2/L3 production `/health` + `/compute` + adapter mapping
  evidence。
- 已有第一批极小 allowlist 的 controlled production `/v1/agent/invoke`
  evidence，但这不等于默认运行时启用。
- R8-12C/R8-12D 让最终报告可以读取 public-safe evidence bundle，并在显式
  demo flag 下用 LLM 重新整理 agent 输出，失败时回退到模板报告。
- R8-13F/R8-13G 已恢复端到端 agent_task/evidence trace，并修复三个价值估值
  agent 的 top-level direction stance。

重要边界：

- `runtime_bindings.json` 没有启用外部 production agent。
- 没有设置 `live_verified=true`。
- 没有设置 `invoke_enabled_by_default=true`。
- production compute pass 不等于 production default invocation。
- demo bridge 不是生产运行时默认路径。

## Directory Operating Model

后续工作默认按这个顺序推进：

```text
sandbox 先试大改
  -> dev 整理成正式代码、测试、文档、commit、push
  -> prod 从稳定提交更新部署
```

三个目录的职责：

| Directory | Role | Use |
| --- | --- | --- |
| `/sdb/dlut/dev/langgraph-my-agent` | 正式开发权威仓库 | 修改主系统长期代码、文档、测试、commit、push。 |
| `/sdb/dlut/sandbox/langgraph-my-agent-r8-a-class` | 大改试验场 | 先验证 agent task、trace、report synthesis、A/B 类接入修复。 |
| `/sdb/dlut/prod/langgraph-my-agent` | 主系统运行副本 | 从稳定 commit 更新，用于部署和运行验证，不作为开发源头。 |

更详细说明见 `docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md`。

## Agent Status By Work Type

这个分类用于安排后续工作，不替代
`docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` 的逐 agent 证据矩阵。

### A Class: Mostly Built, Needs Access Or Protocol Completion

这些 agent 已经有较明确的服务、协议或生产 evidence，下一步主要是接入、
resmoke、allowlist、协议细节或把现有补丁回填到正式服务仓库。

| Layer | Dimension | Agent | Current Focus |
| --- | --- | --- | --- |
| L1 | evidence | 金融数据服务智能体 `financial_data_service` | production health/data bundle 修复后，把 L1 数据包真正送入 L2 `agent_task_v1`。 |
| L1 | evidence | 实体关系抽取智能体 `entity_relation_extractor` | production endpoint / `entity_relation_bundle_v1` 部署确认；再接入 L2 task。 |
| L2 | value | 传统企业估值智能体 `value_traditional_valuation` | 已修复 direction stance；后续做正式服务仓库回填和 invoke audit。 |
| L2 | value | 机器学习企业估值智能体 `value_ml_valuation` | 已修复 direction stance；后续做正式服务仓库回填和 invoke audit。 |
| L2 | value | 元学习企业估值智能体 `value_meta_valuation` | 已修复 direction stance；后续做正式服务仓库回填和 invoke audit。 |
| L2 | value | 分析师研报与观点集成智能体 `value_research_synthesis` | 协议可用；继续提高样本覆盖和 invoke/runtime 评估。 |
| L2 | market | 个股技术分析智能体 `market_stock_technical` | production compute 可用；继续 invoke audit。 |
| L2 | market | 资金流/筹码分析智能体 `market_capital_flow_chip` | production compute 可用；业务信号偏弱时需要服务 owner 增强解释字段。 |
| L2 | risk | 股价崩盘风险智能体 `risk_crash` | production compute/invoke controlled evidence 可用；后续 runtime prepare 仍需单独审批。 |
| L2 | risk | 财务欺诈风险智能体 `risk_financial_fraud` | 协议可用；当前 partial 更多来自数据/证据不足。 |
| L2 | risk | 风险识别智能体 `risk_identification` | production compute/invoke controlled evidence 可用。 |
| L2 | risk | 公告合规审查智能体 `risk_compliance_review` | production compute/invoke controlled evidence 可用。 |
| L2 | macro | 宏观分析智能体 `macro_analysis` | production compute 可用；上下文不足时偏中性基线。 |
| L2 | macro | 商品定价分析智能体 `macro_commodity_pricing` | 需要修复 production health/compute 后 resmoke，再加入端到端 allowlist。 |
| L2 | macro | 股票指数估值智能体 `macro_index_valuation` | 语义已倾向宏观 L2；需要确认 target/natural-language normalization 和 production resmoke。 |
| L3 | composite | 价值综合智能体 `value_composite` | production compute 可用；需持续确保成员来自当前 L2 evidence。 |
| L3 | composite | 市场面综合智能体 `market_composite` | production compute 可用；质量受上游市场 L2 placeholder/fallback 影响。 |
| L3 | composite | 风险综合智能体 `risk_composite` | production compute 可用；需增强 summary/evidence_refs 的业务可读性。 |
| L3 | composite | 宏观综合智能体 `macro_composite` | production compute 可用；上游宏观 L2 完整度仍是主要限制。 |

### B Class: Service Is Placeholder Or Business Capability Is Incomplete

这些 agent 不能只靠主系统修复。它们需要服务 owner 完成真实业务能力、数据输入、
模型/LLM 可用性或语义归属。

| Layer | Dimension | Agent | Current Issue |
| --- | --- | --- | --- |
| L2 | market | 基金经理投资行为分析智能体 `market_fund_manager_behavior` | 当前更像替身或元数据不完整服务；需要真实业务服务和 fixed DAG wrapper。 |
| L2 | market | IPO 投资者构成与行为分析智能体 `market_ipo_investor_behavior` | 可接 compute，但业务上更像替身/规则或 LLM 兜底，对成熟股场景适用性有限。 |
| L2 | market | 企业舆情雷达智能体 `sentiment_company_radar` | market-only；当前存在 LLM 不可用时 deterministic fallback 的业务质量问题。 |
| L2 | macro | 宏观情绪感知智能体 `macro_sentiment` | 当前偏 placeholder 或 regulator-style 语义；需要明确是否输出 L2 `agent_conclusion_v1`。 |
| L2 | macro | 行业热点洞悉智能体 `macro_industry_hotspot` | 当前偏 placeholder，且历史上存在 id/dimension 漂移；需要 owner 明确 L2 宏观信号输出。 |

### C Class: Framework/Internal Or Future L4 Work

这些不是普通 L2/L3 服务修补项，而是主系统编排、L4 决策/报告或 runtime
enablement 问题。

| Layer | Agent | Current Issue |
| --- | --- | --- |
| L1 | 任务路由规划智能体 `route_planner` | 主系统内部 planner 可用；外部 route service 不是当前默认路径。 |
| L4 | 综合研判智能体 `decision_synthesizer` | 真实冲突消解、风险门、宏观调权决策仍未作为独立外部服务完成。 |
| L4 | 报告生成智能体 `report_generator` | 当前报告由主系统 evidence bundle + optional LLM synthesizer 生成，不是独立生产报告智能体服务。 |

## Near-Term Roadmap

### P0: Stabilize The End-To-End Demo Trace

目标：让 demo 真实展示“用户问题 -> router/task -> L1/L2/L3 evidence ->
LLM synthesis report -> workflow trace”。

DoD:

- 端到端 trace 能展示每个 active agent 收到的中文 `agent_task_v1`。
- trace 能展示每个 active agent 的 bounded 输出摘要、状态、confidence、stance
  或 gate/regulator 字段。
- 最终报告读取 evidence bundle，而不是只读模板字段。
- 无法接入的 agent 明确显示为 placeholder/未启用/未成熟，不伪装成真实结论。
- 仍然 default-off，不改 runtime bindings，不设置 live flags。

建议目录：

- 先在 sandbox 验证 trace 和报告质量。
- 成熟后回填 dev，commit/push。
- prod 只更新稳定提交并单独部署。

### P1: Finish A-Class Production Compute Coverage

目标：把“已经基本做了但没稳定进入端到端”的 agent 补齐。

优先顺序：

1. `financial_data_service`: 修 production health JSON 和 `data_bundle_v1`
   compute，之后让 L1 data bundle 进入 L2 task。
2. `entity_relation_extractor`: 确认 production endpoint 和
   `entity_relation_bundle_v1`，之后让实体关系进入 L2 task。
3. `macro_commodity_pricing`: 修 production health/compute，加入宏观 L2
   allowlist。
4. `macro_index_valuation`: 固化自然语言 target normalization，例如把
   “沪深300/上证指数/大盘估值”转成服务可接受的 target，再 resmoke。
5. `market_fund_manager_behavior`: 如果服务 owner 已提供真实实现，补协议、
   allowlist 和 resmoke；如果仍是 placeholder，不进入真实 evidence。

### P2: Improve Business Quality Of Connected Agents

目标：减少“协议通了但业务输出薄”的问题。

重点：

- `value_composite`: summary 不能只像文件名或工程痕迹，应解释成员贡献、
  权重、冲突和最终价值维 stance。
- `risk_composite`: summary 应解释 gate、risk_score、主要触发项和未触发项。
- `macro_composite`: summary 应解释 regime、value/market weights、
  risk_sensitivity 和上游宏观信号。
- `sentiment_company_radar` / `market_ipo_investor_behavior`: 明确 LLM 失败时的
  deterministic fallback 质量边界。
- `risk_financial_fraud`: partial 状态要说明缺哪些数据，不要只输出空泛结论。

### P3: Move From Demo Bridge To Controlled Invoke Readiness

目标：继续扩展 `/v1/agent/invoke` 的只读审计和小白名单 smoke。

步骤：

1. 只读审计 invoke 路径是否复用 compute/core wrapper。
2. 确认 `allow_llm=false` 是否真的避免 provider 调用。
3. 只对结构化 `tool_result` 返回路径做 tiny allowlist invoke smoke。
4. 记录 sanitized evidence。
5. 仍不改 runtime bindings，不设置 live flags。

### P4: Design Real L4 Decision And Report Agents

目标：把当前主系统内部 L4 seam 升级成明确的 L4 决策和报告合同。

需要先定义：

- `decision_synthesizer` 如何处理 value/market/risk/macro 冲突。
- risk gate 的 `manual_review`、`veto`、`penalty` 如何影响最终结论。
- macro regulator 的 `dimension_weights` 如何影响 value/market 权重。
- `report_generator` 接收什么 bounded evidence bundle。
- 哪些内容允许进入 public transcript，哪些必须只在 private trace。

这部分不应混在 L2 接入修复里做。

## Medium-Term Roadmap

中期目标是从 demo-ready 走向 runtime-prepare，但仍保持显式审批：

1. 完成 A 类 agent 的 production compute 和 adapter mapping coverage。
2. 完成更多低风险 agent 的 controlled invoke smoke。
3. 把 production 服务端临时补丁回填到各服务正式源码仓库。
4. 固化 `agent_task_v1` 输入合同，让自然语言任务、L1 evidence、上游结果都能
   被 L2/L3/L4 理解。
5. 建立可重复运行的 sanitized trace artifact 格式。
6. 设计 runtime binding prepare checklist，但不自动启用。

## Long-Term Roadmap

长期目标是进入真实多智能体生产工作流：

1. 由 router/orchestrator 生成每个 agent 的中文任务。
2. L1 证据层稳定提供 data/entity bundles。
3. L2 单体 agent 读取自然语言任务和结构化证据，输出结构化观点。
4. L3 综合 agent 读取对应维度 L2 输出，输出综合结论、风险门或宏观调节器。
5. L4 decision synthesizer 做冲突消解、风险门处理、宏观调权和最终判断。
6. L4 report generator 读取完整 bounded evidence bundle 后生成中文研判报告。
7. 经过 invoke audit、runtime binding prepare、审批后，才考虑默认生产启用。

## Documentation Cleanup Plan

不要现在删除阶段文档。建议后续开一个 docs-compaction phase：

1. 保留 `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` 作为逐 agent readiness
   当前权威。
2. 保留 `docs/CONTROLLED_READINESS_SMOKE_LOG.md` 作为 evidence 账本。
3. 保留 `docs/DEMO_EXTERNAL_COMPUTE_DAG_RUNBOOK.md` 作为 demo 运行入口。
4. 把 R8-13D/E/F/G 这类阶段文档的关键结论合并进上面三个当前权威文档。
5. 合并后再把阶段文档降级为 archive 或 historical reference。
6. 不删除仍包含 backup path、artifact path、service patch inventory 的文档。

## Non-Goals

- 不把 dev evidence 升级成 production evidence。
- 不把 compute pass 写成 invoke pass。
- 不把 invoke pass 写成 runtime binding enablement。
- 不自动修改 `runtime_bindings.json`。
- 不设置 `live_verified=true`。
- 不设置 `invoke_enabled_by_default=true`。
- 不把 placeholder agent 伪装成真实生产智能体。
- 不把外部服务源码并入主系统仓库。
- 不在 public transcript 中暴露 raw response、secret、traceback 或 chain-of-thought。

## Suggested Prompt For A New Codex Session

新开对话时可以让 Codex 先读这些入口：

```text
你是我的 Codex fixed DAG 主系统继续推进助手。

当前主仓库：
/sdb/dlut/dev/langgraph-my-agent
branch: reset/fixed-dag-v1

请先只读审计，不要修改文件。按顺序读取：

AGENTS.md
README.md
docs/INDEX.md
docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md
docs/NEXT_PHASE_ROADMAP_FIXED_DAG.md
docs/SYSTEM_MAP.md
docs/ARCHITECTURE_FIXED_DAG.md
docs/CONTRACTS.md
docs/DEMO_EXTERNAL_COMPUTE_DAG_RUNBOOK.md
docs/AGENT_READINESS_MATRIX_FIXED_DAG.md
docs/CONTROLLED_READINESS_SMOKE_LOG.md
docs/DECISIONS.md
docs/CHANGELOG.md

然后总结：
1. dev/prod/sandbox 三个目录分别是什么；
2. fixed DAG 当前主流程是什么；
3. 哪些 agent 已真实接入；
4. 哪些 agent 是占位、未完成或语义 deferred；
5. 当前 demo bridge 和 LLM report synthesis 的边界；
6. 下一步如果要继续推进端到端真实报告，应该先做什么。

在我确认前，不要改代码、不要调用 endpoint、不要 push。
```
