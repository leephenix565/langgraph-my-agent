# LangGraph ReAct Agent 说明（对齐现状）

更新日期：2026-01-06

## 1. 项目概览
- 目标：提供 4 层（L1/L2/L3/L4）的 Router → Manager → Agents → Summary 模板。
- 入口：`src/react_agent/graph.py:graph`；`langgraph.json` 指向该 graph；`react_agent.graph_app` 导出已编译图；`demo_layered_run.py` 为最小示例。
- Agent 配置：`config/agents` 共 26 个系统角色，分布 L1×2（a02 默认关闭以避免双路由）、L2×15、L3×8、L4×1。`ENABLE_BUILTIN_AGENTS=1` 或缺失 config 时可注册内置 analyst（news/filing/data/ecc，L2）。
- 节点构建：默认仅包含 `default_enabled=true` 的 agent；`INCLUDE_DISABLED_AGENTS=1` 可包含禁用节点。
- 模型：`Context.model` 默认 `deepseek/deepseek-chat`，可用 `MODEL` env 覆盖。
- 搜索工具：`tavily_search`（`max_results=5`、`search_depth="basic"`），需要 `TAVILY_API_KEY`。

## 2. 执行流程
1) 输入：`messages`（最后一条 Human 视为当前问题）。
2) Router（`router_node`）：调用 `ROUTER_SYSTEM_PROMPT` 输出 JSON，解析失败时回退 `_default_layer_plan`（L1:1、L2≤5、L3≤3、L4:1；模式 L1/L4=Chain，L2/L3=Star），并初始化 `current_layer="L1"`、`chain_cursor=0`、`analyst_results={"__reset__": True}`。
3) Manager 派工（`manager_broadcast`）：Chain 顺序单发；Star/Debate/Tree 并发（Debate/Tree 视作 Star 进行派发）；空层直接跳过。
4) Agent 执行（`_build_agent_node`）：构造 `agent_input` 并调用 `AGENT_TOOLS[agent_id]`；`tools_config.allow_search` 对 a01/a25 强制 false。
5) 汇总/推进（`manager_summary`）：Chain 若仍有 pending 则返回 `chain_cursor`；否则标记层完成并推进下一层。最终层使用 `Context.system_prompt` + `MANAGER_SUMMARY_USER` 生成用户答复，`parse_ok=false` 的结果会被过滤并添加 meta note。
6) 条件路由（`route_from_manager_summary`）：pending+Chain→派工；pending+Star/Debate/Tree→先派工再 noop；完成 L4 → `__end__`。

## 3. 状态与上下文
- State（`src/react_agent/state.py`）：`messages`、`plan`、`analyst_results`、`run_id`、`current_question`、`fanout_targets`、`layer_plan`、`layer_mode`、`current_layer`、`layer_done`、`chain_cursor`、`is_last_step`。
- Context（`src/react_agent/context.py`）：`model`/`system_prompt`/`run_id` 支持同名大写 env 覆盖；`analyst_profiles`、`max_search_results`（默认 10，未接入 `tavily_search`）。

## 4. Agent 注册与工具
- 注册顺序：可选内置 → 加载 `config/agents` → 为未注册工具的 agent 构建 LLM tool（有 description 用 `_build_agent_tool`，否则 stub）。
- `AGENT_IDS_FOR_NODES` 由 `default_enabled` 与 `INCLUDE_DISABLED_AGENTS` 决定；节点名为 `agent_{id}_node`。
- `_build_agent_tool` 失败时会 JSON 容错解析；若失败会 `parse_ok=false` 并触发一次重试。

## 5. 日志 / 测试 / 入口
- 本地追踪：`LOCAL_TRACE=1` 写 `log/<YYYYMMDD>/<run_id>.jsonl`；支持 `TRACE_MAX_CHARS` 与 `LOG_DIR`。
- 测试：`tests/unit_tests` + `tests/integration_tests/test_graph.py`。

## 6. 文件分布
- 配置：`.env`、`.env.example`、`langgraph.json`。
- Agents：`config/agents/agent_001.json` … `agent_023.json`、`agent_025.json`、`agent_026.json`、`agent_027.json`（无 `agent_024.json`）。
- 代码：`src/react_agent/`（graph.py, agents.py, context.py, default_agents.py, generic_agent.py, prompts.py, state.py, tools.py, utils.py, run_logger.py, __init__.py）。
- 其他：`log/<YYYYMMDD>/<run_id>.jsonl`（LOCAL_TRACE）、`tests/`、`demo_layered_run.py`。
