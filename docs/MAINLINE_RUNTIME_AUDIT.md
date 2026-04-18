# 主线项目理解审计报告

本报告基于当前仓库代码、集成测试、前端 smoke 和主文档交叉核对整理。若文档与代码冲突，以 `src/react_agent/*` 和聚焦测试为准。本轮审计的核心结论是：主线代码事实整体稳定，主要偏差集中在权威文档口径和文档提交状态，而不是 runtime / public 协议行为本身。

## 1. 项目本质

- 一句话本质: 这是一个 "LangGraph 分层多 agent 运行时 + Python public adapter + 单助手聊天前端" 的系统。
- 对外产品模型: public transcript 只暴露 `user/assistant`，多 agent 协作只作为 workflow inspector 展示，不暴露内部 agent 发言或原始 graph 状态。
- 证据:
  - `langgraph.json`: graph 入口指向 `src/react_agent/graph.py:graph`
  - `src/react_agent/public_contracts.py`: public turn role 和 stream event surface
  - `apps/web/src/components/chat/AssistantAnswerCard.tsx`: 单 assistant answer card
  - `apps/web/src/components/workflow/WorkflowPanel.tsx`: workflow inspector

## 2. 主线运行时拓扑

- 运行时入口分两层:
  - Studio/CLI: `langgraph.json -> src/react_agent/graph.py:graph`
  - 产品入口: `apps/web -> /api/* -> src/react_agent/public_api.py -> src/react_agent/public_runtime.py -> src/react_agent/graph.py:get_graph_for_invoke(...)`
- 当前 graph 主链:
  - `__start__ -> router`
  - `router -> manager_broadcast`
  - `router -> baseline_sidecar`
  - `agent nodes -> manager_summary`
  - `manager_summary/finalize_summary -> fusion_gate -> fusion_judge_shadow -> fusion_writer_shadow -> final_emit -> (memory_update | __end__)`
  - `mainline_emit` 仍存在，但在当前图里只是兼容包装，不是主路由落点
- 各关键节点职责:
  - `router_node`: 生成 `layer_plan/layer_mode`，设置 `current_layer`，重置本轮结果池和 fusion sidecar 状态，不直接产出最终回答
  - `manager_broadcast`: 按层和 mode 派工；优先消费经校验的 a01 contract，否则回退到 `a01/a25` 特殊 assignment 或普通 user assignment
  - `_build_agent_node`: 从 `AGENT_TOOLS[agent_id]` 取真实执行实现，组装 agent input 后执行 `tool.ainvoke(...)`，并把结果写回结果池
  - `manager_summary`: 等待 pending、推进到下一层，或在最终层生成/暂存 mainline bundle
  - `finalize_summary`: `FINAL_LAYER` 的强制收口后备
  - `final_emit`: 消费 `final_emit_payload` 或 `mainline_emit_payload`，统一落盘最终公开答案
- 证据:
  - `src/react_agent/graph.py`: `router_node`, `manager_broadcast`, `_build_agent_node`, `manager_summary`, `finalize_summary`, `final_emit`
  - `src/react_agent/graph.py`: `route_from_manager_summary`, `route_after_finalize`, `route_after_fusion_gate`, `route_after_fusion_judge`, `route_after_fusion_writer`, `route_after_final_emit`
  - `src/react_agent/graph.py`: builder edge/conditional edge 注册区

## 3. 状态面与关键 state 字段解释

- `messages`:
  - 是 runtime 混合总线，不是 public transcript
  - 里面会混有 router 原始输出、manager assignment、agent JSON 和最终答案
- 编排主状态:
  - `layer_plan`
  - `layer_mode`
  - `current_layer`
  - `plan`
  - `layer_done`
  - `fanout_targets`
  - `chain_cursor`
  - `current_question`
  - `run_id`
- 结果池:
  - 默认主线消费 `analyst_results`
  - 若 `REACT_AGENT_RESULTS_POOLS=1`，当前轮真实消费 `ephemeral_results`，`analyst_results` 仅保留兼容镜像
- 主线收口状态:
  - `multi_agent_bundle`
  - `mainline_status`
  - `mainline_emit_payload`
  - `final_answer_source`
  - `emitted_bundle`
- fusion sidecar 状态:
  - `baseline_status`
  - `baseline_bundle`
  - `judge_status`
  - `fusion_verdict`
  - `writer_status`
  - `writer_output`
  - `final_emit_payload`
- 连续性增强状态:
  - `thread_summary`
  - `stable_findings`
  - 这两项都只是 supporting context，不是新的 transcript 真源
- 证据:
  - `src/react_agent/state.py`: `State`, `InputState`
  - `src/react_agent/graph_runtime_features.py`: `_results_pools_enabled`, `_thread_summary_enabled`, `_stable_consume_enabled`
  - `src/react_agent/graph.py`: router/update、agent result merge、emit/fusion payload 构建逻辑
  - `docs/FRONTEND_ARCHITECTURE.md`: why `state["messages"]` cannot be rendered directly

## 4. agent 注册与执行真源

- 注册链:
  - `src/react_agent/graph.py` import 时执行 `bootstrap_agent_runtime()`
  - `src/react_agent/graph_bootstrap.py` 先决定是否启用 builtins，再从 `config/agents/` 载入 metadata，然后为缺失 tool 的 metadata 自动补 tool
  - `build_node_registry(...)` 最终按 `default_enabled` 过滤进入 node registry
- 执行真源:
  - config JSON 不是执行真源，只是 metadata 种子
  - `AgentMetadata` 也不是执行真源，它决定 catalog 和默认启用状态
  - 真正执行时只看 `AGENT_TOOLS[agent_id]`
- 默认 builtins:
  - `ENABLE_BUILTIN_AGENTS=0`
  - 默认主线依赖 `config/agents/*`，不用旧 built-in catalog
- 证据:
  - `src/react_agent/graph_bootstrap.py`: `bootstrap_agent_runtime`, `build_node_registry`
  - `src/react_agent/agents.py`: `AGENT_METADATA`, `AGENT_TOOLS`, `register_agent`
  - `src/react_agent/graph.py`: `_build_agent_node`
  - `tests/integration_tests/test_graph.py`: 默认 runtime 不含旧 `news` built-in

## 5. a01 contract 的真实消费方式

- a01 contract 不是 runtime 的强真源字段。
- 当前真实链路是:
  - `a01_cio_orchestrator` 先在 `AgentOutput.contract` 里生成 contract
  - manager 从结果池抽取 contract
  - `contract_utils.validate_contract(...)` 严格校验
  - 只有校验通过，`manager_broadcast(...)` 才按 contract 派工
- 校验是强约束:
  - 检查 `schema_version`
  - 检查顶层 keys
  - 检查 `selected_agents`
  - 检查每个 task 的步骤、覆盖和唯一性
- 消费是条件性的:
  - `contract_ok and agent_id in contract_tasks` 才走 `MANAGER_ASSIGNMENT_CONTRACT`
  - 否则仍回退到专用 assignment 或 `MANAGER_ASSIGNMENT_USER`
- 证据:
  - `src/react_agent/prompts.py`: `ORCHESTRATOR_SYSTEM_PROMPT`, `MANAGER_ASSIGNMENT_CONTRACT`
  - `src/react_agent/contract_utils.py`: `extract_contract`, `validate_contract`
  - `src/react_agent/graph.py`: `manager_broadcast`

## 6. Fair Fusion 当前真实落地状态

- 当前不止 baseline:
  - baseline sidecar 已落地
  - judge shadow 已落地
  - writer shadow 已落地
  - source-neutral `final_emit` 已落地
- `fusion_gate` 本身只是 branch-safe fan-in seam，真正分流在 `route_after_fusion_gate(...)`
- 默认不会接管最终答案:
  - `Context.enable_fair_fusion=False`
  - `Context.enable_fair_fusion_source_switch=False`
  - 因此默认可见答案仍来自 mainline
- 不开 `enable_fair_fusion`:
  - baseline 直接进入 `disabled`
  - 主线通过 `manager_summary/finalize_summary -> _run_final_summary -> _emit_final_answer`
- 开 `enable_fair_fusion` 但不开 source switch:
  - baseline/judge/writer 会跑 shadow
  - 最终可见答案仍由 staged mainline bundle 经 `final_emit` 写出
- 证据:
  - `src/react_agent/context.py`: `enable_fair_fusion`, `enable_fair_fusion_source_switch`
  - `src/react_agent/baseline_sidecar.py`: baseline disabled/ready/error 路径
  - `src/react_agent/graph.py`: `fusion_gate`, `fusion_judge_shadow`, `fusion_writer_shadow`, `final_emit`, `_build_final_emit_payload`
  - `src/react_agent/public_contracts.py`: `FusionStepStatus`, `WorkflowFusionStep`
  - `src/react_agent/public_mapping.py`: fusion workflow projection

## 7. public adapter 与前端边界

- 四层配合:
  - `public_contracts`: 定义 public-safe schema 和 stream event 闭包
  - `public_mapping`: 把 `structuredInput` 编译回 canonical `text`，把 runtime state 投影成 public workflow/turn
  - `public_runtime`: 负责 readiness、continuity 和 safe invoke/streaming
  - `public_api`: 负责 HTTP、store、preflight 校验和 `answer.final` 包装
- canonical public truth:
  - 仍然是 `turn.text`
  - `structuredInput/materials/urlReferences` 只能做 additive mirror
  - replay 仍只从 `turn.text` 重建
- 前端不能直接渲染 `state["messages"]`:
  - 因为它不是 transcript，而是内部总线
- 当前前端产品模型:
  - 单一助手人格
  - workflow inspector
  - 不是多 speaker transcript
- 证据:
  - `src/react_agent/public_contracts.py`: `PublicTurn`, `StreamEvent`
  - `src/react_agent/public_mapping.py`: `build_user_turn`, `replay_messages`, workflow mapping helpers
  - `src/react_agent/public_runtime.py`: invoke/stream preparation
  - `src/react_agent/public_api.py`: threads/messages/stream handler
  - `apps/web/src/types/chat.ts`: `role: "user" | "assistant"` 和 stream event type
  - `apps/web/src/components/chat/AssistantAnswerCard.tsx`
  - `apps/web/src/components/workflow/WorkflowPanel.tsx`

## 8. 当前默认行为 vs 可选行为

- 默认行为:
  - `enable_fair_fusion=false`
  - `enable_fair_fusion_source_switch=false`
  - `REACT_AGENT_CHECKPOINTER=none`
  - `INCLUDE_DISABLED_AGENTS=0`
  - `ENABLE_BUILTIN_AGENTS=0`
  - 默认 continuity 允许 replay fallback
  - 默认可见答案来自 mainline
- env-gated 可选能力:
  - `thread_summary`
  - `stable_findings`
  - `messages window`
  - `results pools`
  - persistent checkpointer
  - router/baseline provider override
  - global `DISABLE_SEARCH`
  - fusion/source-switch
- public invoke 的硬前提:
  - provider/search readiness 不满足时，public invoke 直接返回 503
  - provider/live smoke 仍是单独的 optional path，不属于默认 mainline gate
- 证据:
  - `src/react_agent/context.py`
  - `src/react_agent/graph_entry.py`
  - `src/react_agent/graph_runtime_features.py`
  - `src/react_agent/public_runtime.py`
  - `scripts/quality/run_quality.py`

## 9. 当前不能破坏的工程边界

- 不能把 `structuredInput/materials/urlReferences` 变成第二持久化真源
- 不能把内部 agents 暴露成多个 public speaker
- 不能让前端直接消费 raw `messages`、raw router output、raw agent JSON、raw fusion payload
- 不能把 baseline/judge/writer 当普通 agent 处理
- 不能把 `a01/a25/a02` 当普通功能 agent 直接平替
- 证据:
  - `src/react_agent/public_mapping.py`
  - `src/react_agent/public_contracts.py`
  - `docs/FRONTEND_ARCHITECTURE.md`
  - `src/react_agent/graph.py`
  - `src/react_agent/baseline_sidecar.py`
  - `src/react_agent/default_agents.py`
  - `config/agents/agent_002.json`

## 10. 已确认事实

- `config/agents/` 当前有 26 个 agent config 文件
- `default_enabled=false` 的默认禁用 agent 是 `a02_task_router`
- 默认 node registry 纳入 25 个 enabled agent；`a02` 只有在 `INCLUDE_DISABLED_AGENTS=1` 时才会进入
- `a01_cio_orchestrator` 和 `a25_report_center` 不是普通功能 agent；二者都有专用 prompt 和专用 assignment/summary 处理
- `a02_task_router` 也不属于当前普通主线，但原因不同: 它是 reserved/deprecated 且默认 disabled
- active frontend smoke entry 仍然是 `apps/web/src/test/smoke.tsx`
- public transcript 的 canonical truth 仍然是 `turn.text`
- 当前 stream seam 仍然只允许:
  - `run.started`
  - `workflow.stage`
  - `workflow.snapshot`
  - `answer.final`
  - `error`
- 证据:
  - `config/agents/`
  - `config/agents/agent_002.json`
  - `src/react_agent/graph_bootstrap.py`
  - `tests/unit_tests/test_disabled_agents_nodes.py`
  - `src/react_agent/default_agents.py`
  - `apps/web/package.json`
  - `apps/web/src/test/smoke.tsx`
  - `src/react_agent/public_mapping.py`
  - `src/react_agent/public_contracts.py`
  - `apps/web/src/types/chat.ts`
  - `tests/integration_tests/test_public_api.py`

## 11. 仍待核实事项

- 真实 deployment 是否打开了这些 env/flag，仓库静态审计无法直接确认:
  - `ENABLE_FAIR_FUSION`
  - `ENABLE_FAIR_FUSION_SOURCE_SWITCH`
  - `REACT_AGENT_CHECKPOINTER`
  - provider/search credential 实况
- 当前结论里的默认值都来自代码默认值，不等于线上真实配置
- 证据:
  - `src/react_agent/context.py`
  - `src/react_agent/graph_entry.py`
  - `src/react_agent/public_runtime.py`

## 12. 后续修改建议

- 如果改 runtime 主线，优先守住三条:
  - `AGENT_TOOLS` 才是执行真源
  - `turn.text` 才是 public/replay 真源
  - `state["messages"]` 绝不能直接变成前端 transcript
- 如果改 a01 contract，必须同步核对:
  - `src/react_agent/prompts.py`
  - `src/react_agent/contract_utils.py`
  - `src/react_agent/graph.py: manager_broadcast`
- 如果改 Fair Fusion，必须先明确是 shadow 还是 source switch，并同步更新 public mapping、集成测试和前端 final-source 展示
