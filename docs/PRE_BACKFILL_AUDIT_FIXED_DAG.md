# Pre-Backfill Audit For Fixed DAG

日期：2026-06-19

本文是进入下一轮 service-owner backfill 之前的主系统审计总账。目的不是继续改代码，
而是把过去几天发生的事情、当前哪些内容已经成为主系统事实、哪些仍只是 sandbox
实验、哪些已经进 prod 运行目录、以及 backfill 时必须遵守的边界讲清楚。

## 这次审计做了什么

- 只读核对 dev 主系统状态：`/sdb/dlut/dev/langgraph-my-agent` 在
  `reset/fixed-dag-v1`，审计基线提交为
  `2854766 feat(l4): enable compute-default runtime`。
- 只读核对 prod 主系统运行副本状态：
  `/sdb/dlut/prod/langgraph-my-agent` 仍在旧提交 `b475383`，并有早前 L4 helper
  backfill 的本地未提交文件。不要把 prod 主系统运行副本当作源码权威。
- 只读核对 L4 两个服务目录：sandbox、dev、prod 三份代码一致；差异只来自 prod/sandbox
  运行日志和 pycache。
- 没有修改外部 agent 服务代码。
- 没有调用 `/health`、`/v1/agent/compute`、`/v1/agent/invoke`。
- 没有修改 `.env`。

## 当前权威目录

| 目录 | 当前意义 | Backfill 前怎么用 |
| --- | --- | --- |
| `/sdb/dlut/dev/langgraph-my-agent` | 主系统正式开发权威。本次审计以 `2854766` 之后的文档整理为起点。 | 所有主系统代码、测试、文档以这里为准。 |
| `/sdb/dlut/sandbox/r8-13a/services/prod/*` | 用户实验过的 agent 服务副本，包含大量 report material wrapper 实验。 | 只能作为候选 patch 来源，不能整目录覆盖 prod 或其他开发者 dev 仓库。 |
| `/sdb/dlut/prod/*` agent 服务目录 | 当前运行副本，可能混合用户 sandbox 同步和其他开发者同步结果。 | backfill 前必须先比较、备份、确认 owner，不能盲目覆盖。 |
| `/sdb/dlut/dev/*` 其他 agent 仓库 | 其他开发者维护的正式 agent 源码。 | 主系统维护者不能默认改写；需要 owner 接收 patch 或自己同步。 |
| `/sdb/dlut/prod/langgraph-my-agent` | 主系统运行副本。 | 应从 dev/remote 稳定提交更新；不要反向作为主系统源码来源。 |

## 已经发生的主系统变化

### 1. 报告输入变厚

主系统已经把外部 agent 输出中 public-safe 的研究材料投影进最终报告输入包。
关键流向是：

```text
AgentConclusion.raw_output / quality / evidence
  -> fixed_dag_external_adapter
  -> provenance.domain_metrics / drivers / data_quality / research_points
  -> report_input_bundle_v1.agent_evidence_bundle
  -> report_generator / fallback report / LLM report synthesis
```

这解决的是“报告只能看到 summary/stance/confidence，最终像模板”的问题。它不是重写
agent 模型，也不是给薄 agent 编造材料。

### 2. `agent_task_v1` 和 `agent_evidence_bundle_v1` 已恢复

主系统现在能记录每个 DAG agent 收到的中文任务、上游输入摘要、输出摘要、证据质量和
失败原因。R8-13F 的端到端 trace 证明了：

- L2 输出可以进入 L3 上游输入。
- L3 composite 可以消费本轮当前 L2 evidence。
- 最终报告能读取 bounded evidence bundle。

这仍不等于所有 agent 都生产可用业务结论。placeholder、partial、error 仍必须在报告中
显式暴露。

### 3. L3 主系统解释材料已增强

主系统 deterministic L3 builder 已能输出成员覆盖、权重、冲突、风险门、宏观调节和
数据质量边界。另有一个默认关闭的 L3 LLM 解释层：

- 开关：`ENABLE_LLM_L3_EXPLANATION=1`
- 只允许补 public-safe `research_points`
- 不允许改 `stance`、`confidence`、`gate`、`risk_score`、member weights、
  `dimension_weights` 等融合字段

因此，L3 的数学融合仍是 deterministic 或外部 composite service 负责，LLM 只做语言解释。

### 4. L4 已从 seam 推进到 compute-default agent

R8-13Q 已完成 L4 默认运行时变更：

| L4 agent | 当前 runtime | 默认端口 | 输出 |
| --- | --- | ---: | --- |
| `decision_synthesizer` | `external_compute_default` | `10025` | `decision_result_v1` |
| `report_generator` | `external_compute_default` | `10026` | `report_result_v1` |

边界必须说清楚：

- 只启用 L4 两个 agent 的 `/v1/agent/compute` 默认路径。
- 没有启用 `/v1/agent/invoke`。
- `invoke_enabled_by_default=false`。
- `live_verified=true` 只表示这两个 L4 `/compute` 默认路径通过 R8-13Q controlled
  runtime smoke。
- L1/L2/L3 外部服务仍没有因此变成默认 runtime。
- 可用 `DISABLE_EXTERNAL_COMPUTE_DEFAULT=1` 回滚到 deterministic L4。

最新 controlled runtime smoke 结果：

- `external_compute_demo_enabled=false`
- `external_compute_default_enabled=true`
- 默认 called/mapped：`decision_synthesizer`、`report_generator`
- failed L4 agents：0
- final report：`贵州茅台(600519.SH) 固定流程投资研判报告`

## 已经发生的服务侧变化

这些变化分三类，backfill 时不能混在一起。

### A. 已进入 prod 运行目录并有 production compute evidence

| 范围 | Agent | 已做内容 | 仍不是 |
| --- | --- | --- | --- |
| L3 composite | `value_composite`、`market_composite`、`risk_composite`、`macro_composite` | R8-13E 已把 L3 wrapper backfill 到 prod 运行目录，支持读取 `context.upstream_outputs`，并通过 `/health` + `/compute` smoke。 | 不是 `/invoke` evidence，也不是默认 runtime enablement。 |
| L2 value stance | `value_traditional_valuation`、`value_ml_valuation`、`value_meta_valuation` | R8-13G 已在 prod 运行目录修复 top-level `stance` / `confidence`，解决 `direction_stance_missing`。 | 不是估值模型重写，不是 runtime binding enablement。 |
| L4 services | `decision_synthesizer`、`report_generator` | 服务目录已同步到 `/sdb/dlut/dev` 和 `/sdb/dlut/prod`，并作为 L4 compute-default runtime 使用。 | 不是 `/invoke` 服务默认启用，也不代表上游 evidence 已经完整。 |

### B. 主要还在 sandbox 的 report-material wrapper 实验

这些是下一轮 service-owner backfill 的主要对象。共同特点是：大多不改模型/算法，只把
agent 已有计算结果整理成 public-safe `domain_metrics`、`drivers`、`data_quality`、
`research_points` 和 evidence。

| 优先级 | Agent | Sandbox 中已验证的增强 | Backfill 风险 |
| --- | --- | --- | --- |
| P0 | `value_traditional_valuation` | 估值桥、方法假设、置信度因素、行情/财报时点、更多 evidence。 | prod 已有 stance 和方法字段，必须合并保留，不能用旧 sandbox 文件覆盖。 |
| P0 | `market_stock_technical` | 模型投票、校准概率、top features、数据完整度、短周期边界。 | 只能包装已有模型结果，不应重训或改交易信号。 |
| P0 | `risk_compliance_review` | 十维 rubric、最低维度、发现摘要、关键词、合成语料声明。 | 必须保留“本地演示/合成语料，不是真实交易所公告源”的边界。 |
| P0 | `value_research_synthesis` | 分析师共识桥、预测输入、覆盖摘要、自然语言研究判断。 | `/compute` 不应调用 LLM；LLM 只属于 `/invoke` 解释层。 |
| P0 | `risk_crash` | risk_score bridge、特征驱动、历史窗口、模型验证、model-vintage caveat。 | 不能把模型版本 caveat 写成特征数据前视，也不能消除真实 caveat。 |
| P0 | `macro_index_valuation` | 宏观方向桥、分位数上下文、forward return context、数据窗口。 | 当前是 macro L2 direction，不是 L3 regulator；target normalization 仍要 owner 确认。 |
| P1 | `value_ml_valuation` | ML 估值桥、蒙特卡洛假设、特征快照、本地财务 cache fallback。 | 服务自有 cache 或正式 L1 数据路径必须由 owner 落地；不能依赖临时 dev cache。 |
| P1 | `value_meta_valuation` | 同业支持集、方法假设、置信度边界、top-level stance。 | 不能只同步字段而丢掉原同业/元学习逻辑。 |
| P1 | `risk_identification` | rule-margin、MD&A hits、三维风险概率、2024Q3 600519 快照。 | 当前 600519 快照是 sandbox demo 补强，生产需要全量 period 更新管线。 |
| P1 | `risk_financial_fraud` | HyFormer 概率、规则降级、年度特征可得日、风险门和证据线索。 | `/compute` 不调用 provider；新闻文本 LLM 路径属于 `/invoke`，不能混为 compute 证据。 |
| P1 | `macro_analysis` | 宏观 regime、信号表、资产配置视图、行业轮动、观点交叉验证。 | 不改 nowcast 规则和阈值；LLM 仅属于 `/invoke` 解析/润色。 |

### C. 暂不 backfill 或必须等 owner 的项

| Agent | 原因 |
| --- | --- |
| `financial_data_service` | 真实 L1 数据路径当前不在本轮主系统可修范围内；需要 owner 修 production health/data bundle。 |
| `entity_relation_extractor` | production endpoint / wrapper 仍未确认；用户已明确该项暂不处理。 |
| `macro_commodity_pricing` | production health/compute 仍需 owner 修复后 resmoke。 |
| `market_fund_manager_behavior` | 当前服务身份/真实业务能力未明确；不要纳入真实 evidence。 |
| `market_ipo_investor_behavior` | 用户已明确 placeholder/未成熟项先不处理；成熟股场景业务适配性也需 owner 说明。 |
| `macro_sentiment` | 语义更像 placeholder/regulator-style，需先定 L2 vs L3。 |
| `macro_industry_hotspot` | placeholder/语义未定，不能包装成真实宏观 L2。 |

## 为什么不能直接 rsync sandbox 到 prod

1. prod 可能已经包含其他开发者从各自 dev agent 仓库同步过来的改动。
2. 有些 prod 运行目录已有关键修复，例如三个 value L2 的 top-level stance。
3. sandbox 中的实验有些只针对 600519.SH 或本地 fixture，不是全量生产数据能力。
4. 有些 wrapper 增强只适合 `/compute`，不能自动推广到 `/invoke`。
5. L4 已经是主系统 compute-default runtime，但这不改变 L1/L2/L3 的 runtime 边界。

正确做法是按 agent 生成最小 patch，逐个 owner 审查、逐个测试、逐个 smoke。

## 下一轮 backfill 的推荐顺序

### 第一批：低风险、收益高

1. `value_traditional_valuation`
2. `market_stock_technical`
3. `risk_compliance_review`

理由：三者已在最早的 sandbox demo 中验证过进入报告包，业务算法不需要大改，主要是
report material wrapper 和证据边界。

### 第二批：当前报告质量提升明显

4. `value_research_synthesis`
5. `risk_crash`
6. `macro_index_valuation`

理由：这三者对 value/risk/macro 三个维度的材料厚度影响很大，但需要更小心区分
模型版本、宏观语义和 target normalization。

### 第三批：数据路径或 owner 责任更重

7. `value_ml_valuation`
8. `value_meta_valuation`
9. `risk_identification`
10. `risk_financial_fraud`
11. `macro_analysis`

理由：这些 agent 的 wrapper 增强已有验证，但部分依赖服务自有数据、period 快照、
HyFormer/nowcast 边界或 owner 数据管线。

## 每个 agent backfill 前必须做的审计

对每个目标 agent，先做下面的只读审计：

1. 确认 owner 和正式 dev agent 仓库位置。
2. 比较 owner dev、sandbox、prod 三份文件，不只比较文件名，要看业务逻辑差异。
3. 记录 prod 当前 PID、cwd、cmdline、端口和启动方式。
4. 检查 prod 运行目录是否是 git 仓库，以及是否有未提交改动。
5. 找出本次只需要回填的最小 wrapper/report-material diff。
6. 明确哪些字段只是报告材料，哪些字段会影响模型分数、risk gate、stance 或权重。
7. 明确是否需要数据文件或 cache；需要时必须由 owner 接收，不能暗用临时 dev cache。
8. 明确验证方式：py_compile、focused unit tests、direct handler、controlled
   `/health` + `/compute` smoke。`/invoke` 必须另开审计。

## Backfill 执行边界

- 不调用 `/v1/agent/invoke`，除非另开 invoke audit 并得到明确批准。
- 不把 `/v1/agent/compute` evidence 写成 `/invoke` evidence。
- 不修改 `.env`。
- 不把 placeholder agent 说成真实完成。
- 不用 sandbox 整目录覆盖 prod。
- 不覆盖其他开发者在 dev agent 仓库或 prod 运行目录中的工作。
- 不把 L4 `external_compute_default` 推广到 L1/L2/L3。
- 不把 L4 `live_verified=true` 解读成所有 agent live verified。
- 每个 backfill 都要更新相关说明文档和 `docs/CHANGELOG.md`。

## 当前下一步

在真正改外部 agent 之前，先按本文选择第一批 agent，逐个做三方 diff：

```text
owner dev agent repo
  vs sandbox/r8-13a/services/prod/<agent>
  vs prod/<agent>
```

只有 diff 和验证计划清楚后，才进入实际 backfill。第一批建议从
`value_traditional_valuation`、`market_stock_technical`、`risk_compliance_review`
开始。
