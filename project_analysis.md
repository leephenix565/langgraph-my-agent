# LangGraph ReAct Agent 项目说明（当前版本）

更新时间：2025-12-11 14:52:58 +08:00

## 1. 项目概览
- 目标：提供 4 层（L1/L2/L4/L5）多代理 Router→Manager→Agents→Summary 的 LangGraph 模板，默认 ReAct 流程，可在 LangGraph Studio 直接运行/扩展。
- 核心：`src/react_agent/graph.py` 编排；`config/agents` 管理 25 个系统级角色；可选内置 4 个分析 Agent（需 `ENABLE_BUILTIN_AGENTS=1`）。
- 默认：模型 `deepseek/deepseek-chat`；公共工具 `tavily_search`（basic, max_results=5）；config 角色默认绑定 LLM 工具并启用搜索，描述缺失时才回退 stub。

## 2. 端到端流程
1) **输入**：仅需 `messages`（最后一条 Human 视为当前问题）。  
2) **Router**：`ROUTER_SYSTEM_PROMPT` 强制输出纯 JSON `layers:[{layer,mode,selected}]`，兼容旧格式 `{"selected":[...]}`；解析失败回退默认计划（L1/L5=Chain，L2/L4=Star；默认选人 L1:1, L2:5, L4:3, L5:1）。初始化 `current_layer="L1"`、`chain_cursor=0`、`analyst_results={"__reset__": True}`。  
3) **Manager 派发**：  
   - Chain：顺序单发；完成一位再派下一位。  
   - Star/Debate/Tree：并行派发未完成的 agent（Debate/Tree 与 Star 同等处理）。  
   - 空层跳过到 summary；派工提示来自 `MANAGER_ASSIGNMENT_USER`。  
4) **Agent 执行**：`_build_agent_node` 组装 `AgentInput` 调用 `AGENT_TOOLS[agent_id]`。  
   - config 25 角色：默认 LLM 工具 `_build_agent_tool(desc, default_allow_search=True)`；描述为空回退 stub（带 `is_stub=True` 标记）。  
   - 内置 Analyst（可选）：news/filing/data/ecc，需开关；模型+工具循环，支持 tavily_search。  
   - 结果写入 `analyst_results[agent_id]`，含 `parse_ok` 标志；生成 JSON AIMessage 追加到消息流。  
5) **Manager 汇总**：  
   - 若 pending 且 mode=Chain，仅更新 `chain_cursor` 等待。  
   - 否则标记 `layer_done`，推进下一层并重置 `fanout_targets`。  
   - L5 完成：用 `Context.system_prompt` + `MANAGER_SUMMARY_USER` 生成最终回答；仅使用 `parse_ok=True` 的结果，过滤数量通过 meta 提示 `[meta] 本轮有 N 条输出因解析失败未参与汇总。`  
6) **条件路由**：`route_from_manager_summary`：pending+Chain→manager_broadcast；pending+Star/Debate/Tree 首次→manager_broadcast，已广播→noop；无 pending 且非 L5→manager_broadcast；L5→__end__。  
7) **图结构**：`__start__`→router→manager_broadcast→agent_*→manager_summary→条件边（manager_broadcast/noop/__end__）。

## 3. 状态与上下文
- State（`src/react_agent/state.py`）：`messages`（add_messages merge）、`plan`、`analyst_results`（支持 `{"__reset__": True}`）、`current_question`、`fanout_targets`、`layer_plan`、`layer_mode`、`current_layer`、`layer_done`、`chain_cursor`、`is_last_step`。  
- Context（`src/react_agent/context.py`）：`model`、`system_prompt`、`analyst_profiles`、`max_search_results`，支持环境变量覆盖（字段名大写）。默认 `system_prompt` 为 Manager 提示。

## 4. Agent 资产与注册
- config/agents：25 个系统级角色，默认启用并绑定 LLM 工具（启用搜索）；描述缺失时回退 stub。层分布：L1×2，L2×15，L4×7，L5×1。  
- 内置 4 Analyst（可选）：news/filing/data/ecc（L2），需 `ENABLE_BUILTIN_AGENTS=1` 或缺少 config 目录时自动注册。  
- 注册顺序：先内置（按需）→ 加载 config 元数据 → 对未绑定工具的角色：有描述用 `_build_agent_tool`，无描述用 `build_generic_agent_tool`（stub）。

## 5. Prompt / 工具 / 解析重试
- Prompt（`src/react_agent/prompts.py`）：Router/Manager/Analyst；Analyst 已转义花括号，严格要求 JSON 输出（analysis/key_points/evidence/confidence）。  
- 工具：`tavily_search`（tools.py），config LLM agent 默认允许，tools_config 可覆盖。  
- 解析与重试（`default_agents.py`）：  
  - `_parse_agent_output`：失败时加 `[PARSE_FALLBACK]`，`parse_ok=False`；成功 `parse_ok=True`。  
  - `_build_agent_tool`：若首次解析失败，自动用“只返回合法 JSON 对象”的系统提示重试一次；重试后仍失败才落入 fallback。

## 6. 测试与示例
- Demo：`python demo_layered_run.py`（需配置 LLM/Tavily Key）可查看 layer_plan/layer_mode/analyst_results/最终消息。  
- 单元测试：模式规范、Router 解析兼容、Context 环境变量、prompt 格式安全、解析 fallback/重试、summary 过滤 parse_fail、config agents 工具类型等。  
- 集成测试：`tests/integration_tests/test_graph.py` 验证图基础输出与默认 agent 集合。  
- Makefile：`make test`，`make integration_tests`。

## 7. 行为与注意事项
- Debate/Tree 仅作并行标签，调度等同 Star；最终输出仅在 L5 生成。  
- Router 解析失败或输出非 JSON 自动回退默认计划；旧格式 `{"selected":[...]}` 兼容 L2/Star。  
- `analyst_results` 合并遇 `{"__reset__": True}` 会清空历史，防止回合污染。  
- 汇总阶段过滤 `parse_ok=False` 的结果，并提示过滤数量。  
- stub 仅在描述缺失时使用；其余 config 角色均走 LLM 工具，输出不再是固定模板。  
- 搜索默认开启（config LLM 角色），但需正确配置 tavily/或在测试中 mock 工具调用。 
