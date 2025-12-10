# 多层 ReAct 路由代理设计说明（当前版本）

更新时间：2025-12-10 16:53:25 +08:00  
适用分支：当前工作区（未做额外改动）

## 1. 设计概览
- 目标：提供一个 4 层（L1/L2/L4/L5）的 Router → Manager → Agents → Summary 图谱，默认 ReAct 迭代，便于在 LangGraph Studio 中快速扩展。
- 核心实现：`src/react_agent/graph.py` 负责图编排；`config/agents` 持久化 25 个系统级角色；可选内置 4 个 Analyst（需 `ENABLE_BUILTIN_AGENTS=1`）。
- 默认配置：模型 `deepseek/deepseek-chat`；唯一公共工具 `tavily_search`（basic，max_results=5）。全部系统级角色为 stub 工具，真实模型调用仅发生在 Router 和 L5 汇总。

## 2. 链路与状态
1) **输入**：仅需 `messages`（最后一条 Human 视为当前问题）。  
2) **Router**（`router_node`）：  
   - Prompt 要求输出纯 JSON：`layers:[{layer,mode,selected}]`，允许模式 Star/Chain/Debate/Tree。  
   - 兼容旧格式 `{"selected":[...]}`（填充 L2/Star）。解析失败回退默认计划：L1/L5=Chain，L2/L4=Star；选人 L1:1, L2:前5, L4:前3, L5:1。  
   - 初始化 `current_layer="L1"`, `chain_cursor=0`, 并写入 `analyst_results={"__reset__": True}` 清空历史。  
3) **Manager 派发**（`manager_broadcast`）：  
   - Chain：顺序单发，完成一位再派下一位（带 `MANAGER_ASSIGNMENT_USER` 提示）。  
   - Star/Debate/Tree：并行派发未完成 agent（Debate/Tree 仅标签，实际与 Star 相同）。  
   - 空层直接跳 summary。  
4) **Agent 节点**（动态 `_build_agent_node`）：  
   - 构造 `AgentInput`（question/subtask/shared_context/history/tools_config），调用 `AGENT_TOOLS[agent_id]`。  
   - `config/agents` 中的 25 个角色使用 stub 工具 `build_generic_agent_tool`，输出确定性的 `AgentOutput`。  
   - 内置 Analyst（news/filing/data/ecc，需启用）走模型+工具循环，允许 `tavily_search`。  
   - 执行结果写入 `analyst_results[agent_id]` 并追加 JSON AIMessage。  
5) **Manager 汇总**（`manager_summary`）：  
   - 若当前层存在 pending 且模式为 Chain，仅更新 `chain_cursor` 等待。  
   - 否则标记 `layer_done` 并推进下一层。  
   - L5 结束后，用 `Context.system_prompt`（默认 `MANAGER_SYSTEM_PROMPT`）+ `MANAGER_SUMMARY_USER` 生成最终回答；失败回退结构化 JSON（包含 question/layer_plan/layer_mode/analyst_results）。  
6) **路由条件**：`route_from_manager_summary` 决定结束/等待（noop）/继续派发。  
7) **图结构**：`__start__` → router → manager_broadcast → agent_* → manager_summary → 条件边（manager_broadcast/noop/__end__）。

### State / Context
- State（`src/react_agent/state.py`）：`messages`（add_messages merge）、`plan`、`analyst_results`（支持 `{"__reset__": True}` 清空）、`current_question`、`fanout_targets`、`layer_plan`、`layer_mode`、`current_layer`、`layer_done`、`chain_cursor`、`is_last_step`。  
- Context（`src/react_agent/context.py`）：`model`、`system_prompt`、`analyst_profiles`、`max_search_results`，默认 Manager prompt，可被环境变量覆盖（字段名大写）。

## 3. Agent 资产
- **配置目录**：`config/agents/agent_*.json` 共 25 个，全部默认启用并绑定 stub：  
  - L1×2：`a01_cio_orchestrator`, `a02_task_router`  
  - L2×15：`a03_macro_policy` ~ `a17_client_profile`  
  - L4×7：`a18_primary_secondary_valuation` ~ `a24_shared_services`  
  - L5×1：`a25_report_center`  
- **内置 Analyst（可选）**：news/filing/data/ecc，层 L2，开启方式 `ENABLE_BUILTIN_AGENTS=1`（或缺少 config 目录时自动注册），具备搜索工具。  
- **注册流程**：优先注册内置（按需）→ 加载 config 元数据 → 对无工具的元数据生成 stub 工具并注册。

## 4. Prompt 与工具
- Prompt：`src/react_agent/prompts.py` 定义 Router、Manager、Analyst 提示。Router 强制纯 JSON；Analyst 提示要求中文 JSON 输出字段（analysis/key_points/evidence/confidence）。部分原始文本存在编码残缺，但语义清晰。  
- 工具：唯一公共工具 `tavily_search`（`tools.py`），在 Analyst 工具循环中按 `tools_config.allow_search` 控制是否启用。

## 5. 运行与测试
- Demo：`python demo_layered_run.py`（需配置 LLM/Tavily Key），会输出 layer_plan/layer_mode/analyst_results/最终消息。  
- 测试：  
  - Unit：模式归一化、Router 解析兼容、Context 环境变量（`tests/unit_tests`）。  
  - Integration：基础图输出与默认 agent 集合检查（`tests/integration_tests/test_graph.py`）。  
- Makefile：`make test` 运行单测；`make integration_tests` 运行集成测试。

## 6. 行为与限制
- Debate/Tree 仅用于标记并行模式，实际分发等同 Star。  
- Router 返回不可解析文本时自动回退默认 4 层计划；旧格式 `{"selected":[...]}` 仅兼容 L2/Star。  
- `analyst_results` 合并遇到 `{"__reset__": True}` 会清空旧结果，确保新问题不带入历史。  
- 25 个系统级角色均为 stub，无外部调用；最终用户可读答案主要依赖 L5 的模型总结。  
- 由于缺省启用 stub，真实多工具能力需为特定 agent 绑定真实工具或启用内置 Analyst。
