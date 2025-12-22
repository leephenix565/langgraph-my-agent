# LangGraph ReAct Agent 说明（更新版）

更新日期：2025-12-14

## 1. 项目概览
- 目标：提供 4 层（L1/L2/L3/L4）的 Router → Manager → Agents → Summary 模板，可在 LangGraph Studio 运行/扩展。
- 入口：`src/react_agent/graph.py:graph`；`langgraph.json` 指向该 graph；`demo_layered_run.py` 为最小示例。
- Agent 配置：`config/agents` 共 25 个系统角色，当前分布 L1×1（a02_task_router 默认关闭以避免双路由，保留实验）、L2×15、L3×7、L4×1。`ENABLE_BUILTIN_AGENTS=1` 时可注册内置 analyst（news/filing/data/ecc，L2）。`INCLUDE_DISABLED_AGENTS=1` 可在图中包含已禁用节点，默认不包含。
- 模型：`Context.model` 默认 `deepseek/deepseek-chat`（可用 `MODEL` env 覆盖，如 xai/grok-*）；`load_chat_model` 解析 `provider/model` → `init_chat_model`。
- 搜索工具：`tavily_search`（`tools.py`），`max_results=5`、`search_depth="basic"`，需要 `TAVILY_API_KEY`，未接入 xAI 工具。
- 日志：`LOCAL_TRACE=1` 时写入 `log/<YYYYMMDD>/<run_id>.jsonl`；LangSmith tracing 通过 `LANGSMITH_TRACING/LANGSMITH_API_KEY`。

## 2. 执行流程
1) 输入：`messages`（最后一条 Human 视为当前问题）。
2) Router（`router_node`）：使用 `ROUTER_SYSTEM_PROMPT` 生成 `layer_plan/layer_mode`（JSON）；解析失败回退默认：L1/L4=Chain，L2/L3=Star，数量 L1:1，L2:≤5，L3:≤3，L4:1；初始化 `current_layer="L1"`，`analyst_results={"__reset__": True}`。
3) Manager 派工（`manager_broadcast`）：Chain 顺序单发，Star/Debate/Tree 并发（Debate/Tree 按 Star 处理）；空层直接跳过。a01/a25 使用专用派工模板，其它用 `MANAGER_ASSIGNMENT_USER`。
4) Agent 执行（`_build_agent_node`）：取最新 subtask，调用 `AGENT_TOOLS[agent_id]`；config agent 默认允许搜索，a01/a25 强制禁止搜索；异常 fail-soft 为 `parse_ok=False` 并记录 `agent_error`。
5) 汇总/推进（`manager_summary`）：若 `pending` 存在（Chain）返回 `chain_cursor` 继续；否则标记层完成推进下一层。L4 终结时始终由 manager_summary LLM 产出最终消息，`analyst_results` 中的 a25 草稿注入 `MANAGER_SUMMARY_USER`（包含 L4 Draft 段落）。`parse_ok=False` 的结果被过滤。
6) 条件路由（`route_from_manager_summary`）：pending+Chain→派工；pending+Star→先派工后 noop；层完则下一层，否则终止。
7) 图边：`__start__→router→manager_broadcast→agent_*→manager_summary→(manager_broadcast|noop|__end__)`。

## 3. 状态与上下文
- State（`src/react_agent/state.py`）：`messages`（add_messages 合并）、`plan`、`analyst_results`（支持 `{"__reset__": True}` 清空）、`current_question`、`fanout_targets`、`layer_plan`、`layer_mode`、`current_layer`、`layer_done`、`chain_cursor`、`is_last_step`、`run_id`。
- Context（`src/react_agent/context.py`）：`model`、`system_prompt`、`analyst_profiles`、`max_search_results`、`run_id`，支持同名大写 env 覆盖。`max_search_results` 当前未在工具中使用。

## 4. Agent 注册与工具
- 注册流程（`graph.py` 顶部）：可选内置→加载 config 元数据→为每个未注册工具的 agent 构建 LLM 工具（有 description 用 `_build_agent_tool`，否则 stub）。
- 节点注册：默认仅 `default_enabled=True` 的 agent 会 add_node；`INCLUDE_DISABLED_AGENTS=1` 可包含禁用节点。
- 工具与搜索：config agents 默认 allow_search=True；内置 analyst 默认 False；特例 a01/a25 在 `agent_input.tools_config` 强制 False；tavily_search 固定 `max_results=5`。

## 5. Prompt / 解析 / 回退
- Prompt（`prompts.py`）：Router、Manager；a01 用 `ORCHESTRATOR_SYSTEM_PROMPT`；a25 用 `REPORT_CENTER_SYSTEM_PROMPT`（骨架+证据卡，缺证据 parse_ok 应为 false）；派工模板：`MANAGER_ASSIGNMENT_USER`、`MANAGER_ASSIGNMENT_ORCHESTRATOR`、`MANAGER_ASSIGNMENT_REPORT_CENTER`。`MANAGER_SUMMARY_USER` 含 L4 Draft (a25_report_center) 段落，要求终稿以 a25 骨架为主线、数字来自 evidence cards。
- 解析与回退：`_parse_agent_output` 容错 JSON；失败标记 `parse_ok=False`，追加 `[PARSE_FALLBACK]`；manager_summary 过滤 `parse_ok=False`；agent 异常 fail-soft 不再终止并发。

## 6. 日志 / 测试 / 入口
- Demo：`python demo_layered_run.py`（需配置模型/Tavily key）。
- 测试：`tests/unit_tests` 覆盖 router 解析、mode 归一、派工/提示格式、fail-soft 等；`tests/integration_tests/test_graph.py` 检查层键与默认 agent 集合。建议命令：`python -m pytest`。
- LangSmith/本地日志：`LOCAL_TRACE=1` 写 JSONL；LangSmith 通过 env 开启。

## 7. 行为与注意事项
- L4 最终答复由 manager_summary 生成；a25 仅提供草稿/证据，未 parse_ok 时标记缺口。
- a01 仅做任务拆解/验收设计，不输出市场结论；a02 默认禁用避免双 router。
- Content Exists Risk/400：捕获为 `agent_error`，fail-soft 写入 `parse_ok=False`，并行不会被取消。
- 搜索上限：`Context.max_search_results` 未接线，Tavily 固定 5。
- 默认模型与 README 描述不一致（代码默认为 deepseek），需按需覆盖 `MODEL`。

## 8. 文件分布
- 配置：`.env`、`.env.example`、`langgraph.json`（指向 `src/react_agent/graph.py:graph`）。
- Agents：`config/agents/agent_001.json` … `agent_025.json`（a02 默认 disabled）。
- 代码：`src/react_agent/`（graph.py, agents.py, context.py, default_agents.py, generic_agent.py, prompts.py, state.py, tools.py, utils.py, run_logger.py, __init__.py）。
- 其他：`static/studio_ui.png`、`log/<YYYYMMDD>/<run_id>.jsonl`（LOCAL_TRACE）、`react_agent.egg-info/`、`tests/`（unit_tests, integration_tests, cassettes, conftest.py）。
