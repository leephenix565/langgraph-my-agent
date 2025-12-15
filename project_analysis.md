# LangGraph ReAct Agent 项目说明（更新版）

更新时间：2025-12-14

## 1. 项目概览
- 目标：提供 4 层（L1/L2/L4/L5）多代理 Router→Manager→Agents→Summary 的 LangGraph 模板，可在 LangGraph Studio 直接运行/扩展。
- 核心：`src/react_agent/graph.py` 编排；`config/agents` 管理 25 个系统级角色；可选内置 4 个分析 Agent（需 `ENABLE_BUILTIN_AGENTS=1`）。
- 模型：`Context.model` 为唯一配置入口，默认 `deepseek/deepseek-chat`，可通过环境变量 `MODEL` 改为 xAI Grok（需安装 `langchain-xai` 且设置 `XAI_API_KEY`）。`load_chat_model` 使用 `provider/model` 解析并调用 `init_chat_model`。
- 工具：默认分析员工具绑定 `tavily_search`（需 `TAVILY_API_KEY`）；未接入 xAI 原生 server-side tools。
- 追踪：可选本地 JSONL（`LOCAL_TRACE=1` → `log/<YYYYMMDD>/<run_id>.jsonl`），LangSmith tracing 可通过 env 开启。

## 2. 端到端流程
1) 输入：`messages`（最后一条 Human 视为当前问题）。
2) Router：用 `ROUTER_SYSTEM_PROMPT` 生成 `layer_plan/layer_mode`（JSON），解析失败回退默认计划（L1/L5=Chain，L2/L4=Star；默认选人 L1:1, L2:5, L4:3, L5:1），初始化 `current_layer="L1"`、`analyst_results={"__reset__": True}`。
3) Manager 派发：Chain 顺序单发；Star/Debate/Tree 并行派发未完成 agent（Debate/Tree 等同 Star）。空层跳过；派工模板 `MANAGER_ASSIGNMENT_USER`。
4) Agent 执行：`_build_agent_node` 取最新消息为 subtask，调用 `AGENT_TOOLS[agent_id]`。config 角色默认 LLM 工具（允许搜索）；描述缺失才回退 stub。内置 Analyst 可选（news/filing/data/ecc）。
5) Manager 汇总：若 pending 且 Chain，返回 chain_cursor 等待；否则推进层级并清 fanout_targets。L5 用 `Context.system_prompt` + `MANAGER_SUMMARY_USER` 汇总，仅保留 `parse_ok=True` 结果，过滤数量用 meta 提示。
6) 条件路由：`route_from_manager_summary` 根据 pending/fanout_targets/层级决定 manager_broadcast/noop/__end__。
7) 图结构：`__start__`→router→manager_broadcast→agent_*→manager_summary→条件边（manager_broadcast/noop/__end__）。

## 3. 状态与上下文
- State（`src/react_agent/state.py`）：`messages`（add_messages）、`plan`、`analyst_results`（支持 `{"__reset__": True}`）、`current_question`、`fanout_targets`、`layer_plan`、`layer_mode`、`current_layer`、`layer_done`、`chain_cursor`、`is_last_step`、`run_id`。
- Context（`src/react_agent/context.py`）：`model`、`system_prompt`、`analyst_profiles`、`max_search_results`、`run_id`，支持环境变量覆盖（字段名大写）。

## 4. Agent 资产与注册
- config/agents：25 个系统级角色，默认启用并绑定 LLM 工具（启用搜索）；描述缺失回退 stub。层分布：L1×2，L2×15，L4×7，L5×1。
- 内置 4 Analyst（可选）：news/filing/data/ecc（L2），需开关；缺少 config 目录时自动注册。
- 注册顺序：先内置（按需）→ 加载 config 元数据 → 未绑定工具的角色：有描述用 `_build_agent_tool`，无描述用 `build_generic_agent_tool`。

## 5. Prompt / 工具 / 解析重试
- Prompt（`src/react_agent/prompts.py`）：Router/Manager/Analyst；Analyst 严格要求 JSON（analysis/key_points/evidence/confidence）。
- 工具：`tavily_search`（tools.py），默认 allow_search=True；未接入 xAI 原生工具。
- 解析与重试（`default_agents.py`）：`_parse_agent_output` 失败加 `[PARSE_FALLBACK]`，`parse_ok=False`；_build_agent_tool 首次失败会用“只返回合法 JSON”提示重试一次。

## 6. 测试与示例
- Demo：`python demo_layered_run.py`（需配置 LLM/Tavily Key）查看 layer_plan/layer_mode/analyst_results/最终消息。
- 单元测试：模式规范、Router 解析兼容、Context 环境变量、prompt 格式安全、解析 fallback/重试、summary 过滤 parse_fail、config agents 工具类型等。
- 集成测试：`tests/integration_tests/test_graph.py` 验证图基础输出与默认 agent 集合。
- Makefile：`make test`，`make integration_tests`。

## 7. 行为与注意事项
- Debate/Tree 标签仅用于并行，调度等同 Star；最终输出仅在 L5 生成。
- Router 解析失败或非 JSON 自动回退默认计划；兼容旧格式 `{"selected":[...]}`。
- `analyst_results` 合并遇 `{"__reset__": True}` 会清空历史，防止回合污染。
- 汇总阶段过滤 `parse_ok=False` 的结果，并提示过滤数量。
- 搜索默认开启（config LLM 角色），需 tavily key 或在测试中 mock。
- 本地日志：`LOCAL_TRACE=1` 时写入 `log/<YYYYMMDD>/<run_id>.jsonl`，异步线程写，避免 ASGI 阻塞；日志包含 run_start/agent_* 等事件。
- LangSmith：设置 LANGSMITH_TRACING/LANGSMITH_API_KEY 等可开启，metadata/tags 携 run_id、layer 等。

## 8. 文件分布
- 根：`.env`、`.env.example`、`langgraph.json`（指向 `src/react_agent/graph.py:graph`）、`pyproject.toml`、`README.md`、`project_analysis.md`、`demo_layered_run.py`。
- 配置：`config/agents/agent_001.json` … `agent_025.json`。
- 源码：`src/react_agent/`（graph.py, agents.py, context.py, default_agents.py, generic_agent.py, prompts.py, state.py, tools.py, utils.py, run_logger.py, __init__.py）。
- 静态：`static/studio_ui.png`。
- 日志（可选）：`log/<YYYYMMDD>/<run_id>.jsonl`（LOCAL_TRACE=1 时生成）。
- 生成物：`react_agent.egg-info/`。
- 测试：`tests/`（unit_tests, integration_tests, cassettes, conftest.py）。
