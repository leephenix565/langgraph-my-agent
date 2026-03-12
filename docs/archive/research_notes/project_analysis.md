# 项目分析（对齐当前仓库）

更新时间：2026-01-09

## 1. 项目整体说明（目的、架构、运行入口）
本仓库是一个基于 LangGraph 的四层多智能体模板与数据合成工具链，核心目的是：
- 在运行态以 Router → Manager → Agents → Summary 的 4 层结构生成最终答复。
- 在离线侧生成 Router SFT 数据（questions → router_plan），并输出可训练的 SFT 数据集。
- 以 config/agents 作为核心元数据来源（agent 列表、层级、默认启用状态、描述等），并由脚本与图运行逻辑共同消费。

运行/训练/评测的可执行命令以 `docs/SYSTEM_MAP.md` 为唯一权威来源。

运行入口与载入方式：
- LangGraph Studio/CLI：读取 `langgraph.json` 中的 `graphs.agent`，指向 `src/react_agent/graph.py:graph`。
- Python 入口：`src/react_agent/__init__.py` 导出 `graph_app`；可直接 `from react_agent import graph_app` 调用。
- 手工示例：`demo_layered_run.py` 展示 `graph_app.ainvoke` 的最小调用方式。

整体运行语义（源码依据 `src/react_agent/graph.py`）：
- Router：`router_node()` 以 `prompts.ROUTER_SYSTEM_PROMPT` 产出 4 层 JSON 计划（L1-L4）并记录日志事件。
- Manager 派发：`manager_broadcast()` 根据 mode（Chain/Star/Debate/Tree）派发给各 agent；Debate/Tree 在派发上视为 Star。
- Agent：`_build_agent_node()` 统一封装 AgentInput（包含 question/subtask/router_plan_summary/tools_config 等）。
- Summary：`manager_summary()` 聚合各层输出，最终以 `Context.system_prompt` 生成用户回答。
- 路由：`route_from_manager_summary()` 依据 pending/当前层/是否最终层决定下一跳（manager_broadcast/noop/__end__）。

模型与工具：
- 默认模型在 `Context.model`（`src/react_agent/context.py`）中定义为 `deepseek/deepseek-chat`，可用 `MODEL` 环境变量覆盖。
- 工具为 `tavily_search`（`src/react_agent/tools.py`），由 `TAVILY_API_KEY` 供给；常量默认 `max_results=5`，运行时在 allow_search=true 时按 `Context.max_search_results` 构造。

日志与追踪：
- `src/react_agent/run_logger.py` 使用 `LOCAL_TRACE=1` 时写入 `log/<YYYYMMDD>/<run_id>.jsonl`。
- 日志 JSONL 会进行字段脱敏（token/secret/password 等）并截断长字符串。

数据合成链路（SFT 数据集）：
- `export_agent_catalog.py` → `data/catalogs/catalog_*.json` + `_prompt.json` + `LATEST`。
- `extract_real_questions.py` / `synthesize_questions.py` 产出 `data/questions` 的真实/合成问题。
- `merge_questions_pool.py` 合并为 `questions_pool_*.jsonl`。
- `generate_router_plans.py` 产出 `data/router_sft/router_sft_*.jsonl`（ok/fail）。
- `export_router_sft_dataset.py` 转成训练用 messages/prompt-completion 格式。
- `tools/generate_router_preds.py` / `tools/generate_router_preds_hf.py` 从 val messages 生成 preds.jsonl。
- `tools/eval_router_outputs.py` 生成 metrics.json 与分布摘要。
（具体命令见 `docs/SYSTEM_MAP.md`）

编码与文本注意：
- `prompts.py`、`demo_layered_run.py` 等文件内包含中文字符串，当前文件中部分中文呈现为乱码（历史编码问题）。

## 2. 目录总览（按当前仓库实际存在）

```text
.
├─ .github/
│  └─ workflows/
│     ├─ integration-tests.yml
│     └─ unit-tests.yml
├─ .langgraph_api/
│  ├─ .langgraph_checkpoint.1.pckl
│  ├─ .langgraph_checkpoint.2.pckl
│  ├─ .langgraph_checkpoint.3.pckl
│  ├─ .langgraph_ops.pckl
│  ├─ .langgraph_retry_counter.pckl
│  ├─ store.pckl
│  └─ store.vectors.pckl
├─ config/
│  └─ agents/
│     ├─ agent_001.json
│     ├─ ...
│     └─ agent_027.json
├─ data/
│  ├─ catalogs/
│  ├─ questions/
│  ├─ router_sft/
│  └─ sft/
├─ docs/
├─ log/
│  └─ <YYYYMMDD>/<run_id>.jsonl
├─ src/
│  └─ react_agent/
├─ static/
│  └─ studio_ui.png
├─ tests/
│  ├─ integration_tests/
│  ├─ unit_tests/
│  └─ cassettes/
├─ tools/
├─ .env
├─ .env.example
├─ .gitignore
├─ .codespellignore
├─ agent_full.md
├─ agent_profile.md
├─ demo_layered_run.py
├─ export_agent_catalog.py
├─ export_router_sft_dataset.py
├─ extract_real_questions.py
├─ generate_router_plans.py
├─ merge_questions_pool.py
├─ synthesize_questions.py
├─ langgraph.json
├─ pyproject.toml
├─ Makefile
├─ README.md
├─ project_analysis.md
├─ react_agent/
├─ sitecustomize.py
├─ LICENSE
├─ langchain_community-0.2.14-py3-none-any.whl
├─ 智能体分配.xlsx
└─ et --hard 6f47f8398c24603bfcdd7eb15742c208e8408c83^
```

## 3. 源码核心目录详解（src/react_agent）

`src/react_agent/` 是运行态图与 Agent 的核心实现。

- `src/react_agent/__init__.py`
  - 导出 `graph` 和 `graph_app`，供外部脚本/应用调用。
- `src/react_agent/graph.py`
  - 构建四层 LangGraph，定义 Router/Manager/Agent/Summary 节点与边。
  - 注册 agent、加载 config/agents 元数据、构建 `AGENT_IDS_FOR_NODES` 与节点名。
  - 关键函数：`router_node()`、`manager_broadcast()`、`_build_agent_node()`、`manager_summary()`、`route_from_manager_summary()`、`noop()`。
- `src/react_agent/state.py`
  - 定义图状态结构 `State`、输入结构 `InputState`。
  - 定义 `merge_analyst_results()`（支持 `__reset__` 清空历史）。
- `src/react_agent/context.py`
  - 定义可注入上下文 `Context`（model/system_prompt/analyst_profiles/run_id/max_search_results）。
  - 支持环境变量覆写：字符串字段默认可覆写（如 MODEL/SYSTEM_PROMPT/RUN_ID）；`max_search_results` 需显式解析（MAX_SEARCH_RESULTS）。
- `src/react_agent/agents.py`
  - 定义 `AgentMetadata`、`AgentInput/Output` 协议、`AGENT_METADATA`/`AGENT_TOOLS` 注册表。
  - `load_metadata_from_dir()` 读取 `config/agents/agent_*.json`。
- `src/react_agent/default_agents.py`
  - 内置四类 Analyst（news/filing/data/ecc）的工具与注册逻辑。
  - `_build_agent_tool()` 构建 tool-calling 代理并实现一次 JSON 解析重试。
- `src/react_agent/generic_agent.py`
  - 当描述为空时生成 stub 工具，确保每个 agent 都可运行。
- `src/react_agent/prompts.py`
  - Router/Manager/Analyst/Orchestrator/Report Center 的 system prompts 与 assignment 模板。
  - 注意：文件内部分中文显示为乱码（编码问题）。
- `src/react_agent/tools.py`
  - 暴露 `tavily_search` 工具，默认 `max_results=5`、`search_depth=basic`。
- `src/react_agent/utils.py`
  - `load_chat_model()` 统一加载 provider/model；`get_message_text()` 统一提取文本。
- `src/react_agent/run_logger.py`
  - LOCAL_TRACE 本地 JSONL logger；支持脱敏与截断。

## 4. Agent 配置（config/agents/agent_*.json）

当前 `config/agents` 共 26 个 JSON（L1=2，L2=15，L3=8，L4=1；其中 a02 默认 disabled）。

| 文件 | id | layer | default_enabled | name |
|---|---|---|---|---|
| config/agents/agent_001.json | a01_cio_orchestrator | L1 | true | CIO Orchestrator |
| config/agents/agent_002.json | a02_task_router | L1 | false | Task Decomposer |
| config/agents/agent_003.json | a03_macro_policy | L2 | true | 宏观与货币政策研究智能体 |
| config/agents/agent_004.json | a04_industry_layout | L2 | true | 产业链与行业格局研究智能体 |
| config/agents/agent_005.json | a05_product_pricing | L2 | true | 大宗商品价格预测智能体 |
| config/agents/agent_006.json | a06_financial_reports | L2 | true | 公司年报分析智能体4 |
| config/agents/agent_007.json | a07_financial_modeling | L2 | true | 公司财报分析智能体 |
| config/agents/agent_008.json | a08_tech_due_diligence | L2 | true | 上市材料分析智能体 |
| config/agents/agent_009.json | a09_macro_sentiment | L2 | true | 宏观舆情感知智能体6 |
| config/agents/agent_010.json | a10_industry_sentiment | L2 | true | 中观行业舆情感知智能体7 |
| config/agents/agent_011.json | a11_equity_sentiment | L2 | true | 微观个股舆情感知智能体8 |
| config/agents/agent_012.json | a12_ipo_investor_behavior | L2 | true | IPO投资者构成与行为分析智能体 |
| config/agents/agent_013.json | a13_index_technical_analysis | L2 | true | 指数技术分析智能体5 |
| config/agents/agent_014.json | a14_single_stock_tech | L2 | true | 个股技术分析智能体 |
| config/agents/agent_015.json | a15_research_synthesis | L2 | true | 分析师研报与观点集成智能体2 |
| config/agents/agent_016.json | a16_fund_manager_behavior | L2 | true | 基金经理投资行为分析智能体 |
| config/agents/agent_017.json | a17_client_profile | L2 | true | 客户画像（风险偏好）智能体 |
| config/agents/agent_018.json | a18_primary_secondary_valuation | L3 | true | 企业通用估值智能体1 |
| config/agents/agent_019.json | a19_market_risk | L3 | true | 股价相关风险智能体 |
| config/agents/agent_020.json | a20_fundamental_risk | L3 | true | 财务困境风险智能体 |
| config/agents/agent_021.json | a21_reg_compliance | L3 | true | 监管合规与投资者保护规则审查智能体 |
| config/agents/agent_022.json | a22_suitability_review | L3 | true | 投资者适当性与风险承受匹配审查智能体 |
| config/agents/agent_023.json | a23_portfolio_opt | L3 | true | 投资组合优化智能体 |
| config/agents/agent_025.json | a25_report_center | L4 | true | Report & Decision Center |
| config/agents/agent_026.json | a26_sci_tech_valuation | L3 | true | 科创企业估值智能体3 |
| config/agents/agent_027.json | a27_portfolio_backtest | L3 | true | 投资组合历史回测智能体 |

说明：`graph.py` 在启动时从 `config/agents` 加载元数据，并可由 `ENABLE_BUILTIN_AGENTS` 决定是否额外注册内置 analyst（news/filing/data/ecc）。

## 5. 根目录脚本与文档说明

- `.env`
  - 本地环境变量文件（包含 API keys/模型配置等），不应提交真实密钥。
- `.env.example`
  - 环境变量模板（`MODEL`、`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`TAVILY_API_KEY` 等示例）。
- `.gitignore`
  - Git 忽略规则。
- `.codespellignore`
  - 拼写检查忽略词。
- `README.md`
  - LangGraph ReAct 模板说明文档，包含 Studio 入口与模型配置示例。
- `LICENSE`
  - MIT License。
- `pyproject.toml`
  - Python 项目元数据与依赖声明（langgraph/langchain 系列与 dev 工具）。
- `Makefile`
  - 包含 test/lint 等 targets（命令细节见 `docs/SYSTEM_MAP.md`）。
- `langgraph.json`
  - LangGraph Studio/CLI 的入口描述（graph 指向 `src/react_agent/graph.py:graph`）。
- `demo_layered_run.py`
  - 直接调用 `graph_app.ainvoke` 的最小示例。
- `agent_profile.md` / `agent_full.md`
  - 自定义的 agent 文档与清单说明（需与实际 config/agents 对齐）。
- `project_analysis.md`
  - 当前项目分析与目录说明（本文）。
- `docs/SYSTEM_MAP.md`
  - 单一真源系统地图（运行/训练/评测路径）。
- `智能体分配.xlsx`
  - Agent 名称与描述的外部“单一真源”表格（用于配置对齐）。
- `langchain_community-0.2.14-py3-none-any.whl`
  - 本地 wheel 包，用于离线或固定版本安装。
- `react_agent/`
  - root 级 shim 包，用于 src-layout 导入时保证 `import react_agent` 可用。
- `sitecustomize.py`
  - 本地运行时将 `src/` 注入 sys.path（用于 CLI/pytest）。
- `et --hard 6f47f8398c24603bfcdd7eb15742c208e8408c83^`
  - 看起来是一次命令输出的快照文件（非标准项目文件）。

### 离线/数据工具脚本（根目录）
- `export_agent_catalog.py`
  - 从 `config/agents` 读取并输出 enabled 的 catalog 快照与 prompt 版；生成 `LATEST`。
- `extract_real_questions.py`
  - 从 `log/**/*.jsonl` 抽取真实用户问题（事件类型 run_start/router_decision）。
- `synthesize_questions.py`
  - 基于 OpenAI-compatible API 生成合成问题池（15 buckets × 50）。
  - 脚本内提供 `DEEPSEEK_API_KEY` 本地占位变量（不应写入真实密钥）。
- `merge_questions_pool.py`
  - 合并 real + synth，统一 `questions_pool_*.jsonl`，并支持 catalog hash 重写逻辑。
- `generate_router_plans.py`
  - 使用 teacher 生成 RouterPlan，并做严格解析/校验/修复，输出 ok/fail 两份 JSONL。
  - 包含 overselect 与 cross-layer 的自动修复逻辑。
- `export_router_sft_dataset.py`
  - 将 router_sft ok 数据转换为训练格式（messages 或 prompt/completion）。
- `tools/eval_router_outputs.py`
  - 离线评测：输入 preds.jsonl（id/raw_text），输出 metrics.json 与分布摘要。
- `tools/generate_router_preds.py`
  - provider 模型推理：读取 val messages JSONL，输出 preds.jsonl。
- `tools/generate_router_preds_hf.py`
  - 本地 HF 推理：读取 val messages JSONL，输出 preds.jsonl（不依赖 API key）。
- `tools/sample_router_preds.jsonl`
  - 最小评测样例输入。
- `tools/README.md`
  - tools 目录内使用说明。

## 6. tests 目录说明

- `tests/conftest.py`
  - pytest 全局夹具，设置 `TAVILY_API_KEY`/`OPENAI_API_KEY` 占位与 anyio 后端。

- `tests/unit_tests/test_router_prompt_format.py`
  - 检查 `ROUTER_SYSTEM_PROMPT.format()` 仅需 `system_time`/`agent_catalog`。
- `tests/unit_tests/test_analyst_prompt_format.py`
  - 检查 `ANALYST_SYSTEM_PROMPT` 的 `{profile}` 渲染与 JSON schema 字段。
- `tests/unit_tests/test_orchestrator_prompt.py`
  - 验证 a01 使用 Orchestrator system prompt 与派发模板。
- `tests/unit_tests/test_report_center_assignment.py`
  - 验证 a25 assignment 模板与 `allow_search=false`。
- `tests/unit_tests/test_router_plan_summary_to_a01.py`
  - 验证 `router_plan_summary` 被传给 a01。
- `tests/unit_tests/test_parse_router_layers.py`
  - 覆盖 Router 输出解析、旧格式兼容、空层处理、路由与 fanout 重置。
- `tests/unit_tests/test_mode_normalize.py`
  - 覆盖 mode 归一化逻辑。
- `tests/unit_tests/test_manager_summary_a25_output.py`
  - 验证 L4 总结使用 Manager LLM，a25 输出注入逻辑。
- `tests/unit_tests/test_llm_json_retry_and_summary_filter.py`
  - 验证 Agent JSON 解析重试与 parse_ok 过滤。
- `tests/unit_tests/test_disabled_agents_nodes.py`
  - 验证 disabled agent 默认不建节点，INCLUDE_DISABLED_AGENTS=1 时建节点。
- `tests/unit_tests/test_config_agents_tools.py`
  - 验证 config agents 默认生成 LLM tool，description 为空时使用 stub。
- `tests/unit_tests/test_configuration.py`
  - 验证 Context 环境变量覆写逻辑。
- `tests/unit_tests/test_agent_parse_fallback_flagged.py`
  - 验证 Agent parse fallback 标记 parse_ok=false。
- `tests/unit_tests/test_agent_fail_soft.py`
  - 验证 Agent 异常时 fail-soft 输出结构。
- `tests/unit_tests/test_router_parse_stats.py`
  - 覆盖 router_parse 统计字段（fallback/截断/过滤）。
- `tests/unit_tests/test_eval_router_outputs.py`
  - 覆盖离线评测指标计算（valid_json_rate/长度分布）。

- `tests/integration_tests/test_graph.py`
  - 端到端调用 graph，验证 layer_plan 与 built-in 是否被默认禁用。
（回归命令见 `docs/SYSTEM_MAP.md`）

- `tests/cassettes/103fe67e-a040-4e4e-aadb-b20a7057f904.yaml`
  - 录制的 HTTP 交互 fixture（用于集成测试）。

## 7. data 与 log 目录说明（当前实际文件）

### data/catalogs/
- `data/catalogs/LATEST`
  - 当前最新 catalog_id（文本文件）。
- `data/catalogs/catalog_20260106_b434e7a9a883.json`
  - enabled agent catalog 快照（结构化层级）。
- `data/catalogs/catalog_20260106_b434e7a9a883_prompt.json`
  - prompt 版 catalog（id/name/desc_1l）。
- `data/catalogs/catalog_20260108_b434e7a9a883.json`
  - 后续日期生成的同 hash catalog。
- `data/catalogs/catalog_20260108_b434e7a9a883_prompt.json`
  - prompt 版 catalog。
- `data/catalogs/catalog_20260108_b434e7a9a883_prompt_v1.json`
  - prompt 版 v1（用于 SFT 生成或兼容版本）。

### data/questions/
- `data/questions/real_questions_20260106.jsonl`
  - 从 `log/**/*.jsonl` 抽取的真实问题。
- `data/questions/synth_questions_20260107_20260106_b434e7a9a883.jsonl`
  - 合成问题池（15 buckets × 50）。
- `data/questions/questions_pool_20260107_20260106_b434e7a9a883.jsonl`
- `data/questions/questions_pool_20260108_20260106_b434e7a9a883.jsonl`
- `data/questions/questions_pool_20260108_20260108_b434e7a9a883.jsonl`
- `data/questions/questions_pool_20260108_20260108_b434e7a9a883_v1.jsonl`
  - 合并后的 questions_pool（不同日期/版本）。
- `data/questions/questions_pool_sample200_20260108_20260106_b434e7a9a883.jsonl`
  - 抽样子集（200 条）。
- `data/questions/questions_pool_self_check.jsonl`
  - merge_questions_pool 的自检产物。

### data/router_sft/
- `data/router_sft/router_sft_20260108_20260106_b434e7a9a883.jsonl`
- `data/router_sft/router_sft_20260108_20260108_b434e7a9a883.jsonl`
- `data/router_sft/router_sft_20260108_20260108_b434e7a9a883_v1.jsonl`
  - RouterPlan OK 数据集（不同日期/版本）。
- `data/router_sft/router_sft_fail_20260108_20260106_b434e7a9a883.jsonl`
- `data/router_sft/router_sft_fail_20260108_20260108_b434e7a9a883.jsonl`
- `data/router_sft/router_sft_fail_self_check_20260108_20260108_b434e7a9a883.jsonl`
  - 失败样本与自检失败输出。
- `data/router_sft/router_sft_self_check_20260108_20260108_b434e7a9a883.jsonl`
  - 自检 OK 样本。

### data/sft/
- `data/sft/router_sft_messages_20260108_b434e7a9a883_v1.train.jsonl`
- `data/sft/router_sft_messages_20260108_b434e7a9a883_v1.val.jsonl`
  - 训练/验证集输出（messages 格式）。

### log/
以下为 LOCAL_TRACE 产物，文件名为 run_id（示例）：
- `log/20251214/1a4a7680.jsonl`
- `log/20251214/2163fb20.jsonl`
- `log/20251214/393ac123.jsonl`
- `log/20251214/53ce723a.jsonl`
- `log/20251214/866826e5.jsonl`
- `log/20251214/af903c6b.jsonl`
- `log/20251214/b7100ca6.jsonl`
- `log/20251214/c6655e9a.jsonl`
- `log/20251214/d63773a5.jsonl`
- `log/20251214/e5114c39.jsonl`
- `log/20251214/e9052127.jsonl`
- `log/20251214/eb97fe0e.jsonl`
- `log/20251214/f9c3c56e.jsonl`
- `log/20251215/062db90e.jsonl`
- `log/20251215/0ed92f51.jsonl`
- `log/20251215/1029517b.jsonl`
- `log/20251215/33ffe0cd.jsonl`
- `log/20251215/f2eaf7d2.jsonl`
- `log/20251216/1357921c.jsonl`
- `log/20251216/2420c7b3.jsonl`
- `log/20251216/26a9571f.jsonl`
- `log/20251216/36f8b525.jsonl`
- `log/20251216/6e28291b.jsonl`
- `log/20251216/781a0c88.jsonl`
- `log/20251216/998ecedb.jsonl`
- `log/20251219/ab866079.jsonl`
- `log/20251220/72dfa0e2.jsonl`
- `log/20251220/e875ae7e.jsonl`
- `log/20251221/72dfa0e2.jsonl`
- `log/20251221/dd5fc176.jsonl`
- `log/20251221/ef9a5fa1.jsonl`
- `log/20251222/ec113d54.jsonl`
- `log/20251222/ef9a5fa1.jsonl`
- `log/20251222/f2556d76.jsonl`

## 8. 其他目录与环境产物

- `.github/workflows/`
  - `integration-tests.yml` / `unit-tests.yml`：GitHub Actions CI 配置。
- `.langgraph_api/`
  - LangGraph Studio/CLI 本地运行时持久化文件（checkpoint/ops/store）。
- `.pytest_cache/`
  - pytest 缓存。
- `.venv/`
  - 本地虚拟环境（若存在）。
- `react_agent.egg-info/`
  - setuptools 构建产物（包元数据）。
- `__pycache__/`
  - Python 字节码缓存。
- `tmp_pkgs/`
  - 临时包或本地安装缓存（非核心源码）。

## 9. 项目内关键约定（从代码提取的“事实”）
- Router 输出必须是 4 层 JSON（L1-L4），mode 仅允许 Star/Chain/Debate/Tree（`prompts.py` + `graph.py` + `generate_router_plans.py`）。
- 运行期解析仅对 L2 做 `>5` 截断（计入 `l2_truncated`）；L3 正常解析不截断，但当 Router JSON 不可解析而回退 default_plan 时，L3 会按默认计划取前 3（`default_layer_plan`）。
- a01（Orchestrator）与 a25（Report Center）拥有硬编码的 system prompt 与派发模板；并默认禁止搜索工具。
- `INCLUDE_DISABLED_AGENTS=1` 时会将 `default_enabled=false` 的 agent（如 a02）纳入图节点。
- `ENABLE_BUILTIN_AGENTS=1` 或缺失 config 时，会注册内置 analyst（news/filing/data/ecc）。

以上内容为对当前仓库文件的结构性梳理，便于后续对齐 agent 目录、数据管线与 RouterPlan 生成契约。
