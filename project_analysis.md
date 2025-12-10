# LangGraph ReAct Agent 项目说明（当前版本）

更新时间：2025-12-10 16:53:25 +08:00

## 1. 项目概览
- 目标：提供一个基于 LangGraph 的 4 层（L1/L2/L4/L5）多代理 Router → Manager → Agents → Summary 模板，默认使用 ReAct 风格迭代。
- 核心文件：`src/react_agent/graph.py` 定义有向图；`config/agents` 维护 25 个系统级 Agent 元数据；若启用环境变量 `ENABLE_BUILTIN_AGENTS=1`，额外注册 4 个内置分析 Agent。
- 默认模型与工具：模型 `deepseek/deepseek-chat`（可通过 Context/环境变量覆盖），唯一公共工具 `tavily_search`（basic 模式，max_results=5）。
- 运行入口：`demo_layered_run.py` 演示端到端调用；`langgraph.json` 将图导出为 `agent`。

## 2. 端到端流程
1) **输入**：外部仅传入 `messages`（`State/InputState`），通常最后一条 HumanMessage 视为当前问题。  
2) **Router**：使用 `ROUTER_SYSTEM_PROMPT` 要求输出纯 JSON：每层包含 `layer/mode/selected`。兼容旧格式 `{"selected":[...]}`（填充 L2/Star）。若解析失败，回退默认计划：  
   - 模式默认：L1 Chain、L2 Star、L4 Star、L5 Chain。  
   - 选人默认：L1 取 1、L2 取前 5、L4 取前 3、L5 取 1（按元数据顺序且 `default_enabled=True`）。  
   - 初始化 `current_layer="L1"`, `chain_cursor=0`, 并写入 `analyst_results={"__reset__": True}` 清空旧结果。  
3) **Manager 派发**（`manager_broadcast`）：  
   - Chain：顺序单发下一个 agent（使用 `Send` 分支），完成后再派下一位。  
   - Star/Debate/Tree：并行派发未完成 agent（Debate/Tree 仅作为标签，分发等同 Star）。  
   - 空层直接跳到 summary。  
   - 派工提示基于 `MANAGER_ASSIGNMENT_USER`，附带计划/已完成/当前 mode。  
4) **Agent 执行**（动态节点 `_build_agent_node`）：  
   - 构造 `AgentInput`（question/subtask/shared_context/history/tools_config），调用 `AGENT_TOOLS[agent_id]`。  
   - 若是内置 Analyst（news/filing/data/ecc，需开启 `ENABLE_BUILTIN_AGENTS`），则模型+工具循环，允许 `tavily_search`。  
   - 对于 `config/agents` 定义的 25 个系统级角色，默认绑定 stub 工具 `build_generic_agent_tool`，返回可预测的 `AgentOutput`。  
   - 结果写入 `analyst_results[agent_id]`，并追加 JSON AIMessage。  
5) **Manager 汇总**（`manager_summary`）：  
   - 若当前层仍有 pending 且 mode=Chain，仅更新 `chain_cursor` 等待。  
   - 否则标记 `layer_done` 并推进 `current_layer`。  
   - L5 完成后，用 `Context.system_prompt`（默认 `MANAGER_SYSTEM_PROMPT`）+ `MANAGER_SUMMARY_USER` 生成用户可读回答；失败时回退为结构化 JSON（包含 question/layer_plan/layer_mode/analyst_results）。  
6) **路由条件**：`route_from_manager_summary` 判断是否结束、等待（noop）或继续派发。  
7) **图结构**：`__start__` → router → manager_broadcast → agent_* → manager_summary，条件边回到 manager_broadcast / noop 或结束。

## 3. 状态与上下文
- **State**（`src/react_agent/state.py`）：`messages`（add_messages merge）；`plan`；`analyst_results`（支持 `{"__reset__": True}` 清空）；`current_question`；`fanout_targets`；`layer_plan`；`layer_mode`；`current_layer`；`layer_done`；`chain_cursor`；`is_last_step`。  
- **Context**（`src/react_agent/context.py`）：`model`、`system_prompt`、`analyst_profiles`、`max_search_results`，支持环境变量覆盖（字段名大写）。默认 system_prompt 为 Manager 提示。

## 4. Agent 资产
- **配置目录**：`config/agents/agent_*.json` 共 25 个，按层分布：L1×2（a01/a02）、L2×15（a03~a17）、L4×7（a18~a24）、L5×1（a25）。全部默认启用并绑定 stub 工具。  
- **内置 Analyst**（可选）：news/filing/data/ecc，层 L2，依赖 `ENABLE_BUILTIN_AGENTS=1` 或缺少 config 目录时自动注册。内置工具支持搜索。  
- **注册逻辑**：启动时加载内置（可选）→ 加载 `config/agents` 元数据 → 对缺少工具的元数据生成 stub 工具并注册。

## 5. Prompt / 工具 / 测试
- Prompt：见 `src/react_agent/prompts.py`。Router 要求纯 JSON；Manager 负责派工和最终总结；Analyst 提示要求中文 JSON 输出（analysis/key_points/evidence/confidence）。部分提示存在原始编码残缺，但不影响含义。  
- 工具：`tavily_search` 唯一公共工具（`tools.py`），在 Analyst 工具调用时按 `tools_config.allow_search` 控制。  
- 测试：`tests/unit_tests` 覆盖模式归一化、Router 解析兼容、Context 环境变量；`tests/integration_tests/test_graph.py` 校验图的基本输出与默认 agent 集合。  
- 示例：`python demo_layered_run.py`（需配置 LLM/Tavily Key），可看到 layer_plan/layer_mode/analyst_results/final message。

## 6. 已知注意事项
- Debate/Tree 仅作为标签，分发仍按 Star 处理；最终摘要仍由 L5 单链路生成。  
- Router 如果返回无法解析的文本，会自动回退到默认 4 层计划；旧格式 `{"selected":[...]}` 仅作用于 L2/Star 兼容。  
- `analyst_results` 合并时若遇到 `{"__reset__": True}` 会清空旧结果，保证新一轮提问不带入历史。  
- 当前 25 个系统级 Agent 全部是 stub 工具（无外部调用），最终输出主要依赖 L5 汇总时的模型调用。 
