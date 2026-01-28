# a01 Contract Schema v0 (a01_contract_v0)

> 权威级别：S0（协议级）。本文件定义 a01 输出的强结构合同 JSON，以及运行态消费规则。

## 1) 目的与作用
- a01 负责将 Router 选中的 agents 编译为“任务合同”，供 Manager 按 agent_id 精准派发 subtask。
- 合同是强结构（schema v0）；当合同可用且校验通过时，`manager_broadcast` 优先以合同驱动派发；失败则回退模板广播。

## 2) 顶层 Contract 结构（additionalProperties=false）
必须包含且仅包含以下字段：
- `schema_version` (string): 固定为 `a01_contract_v0`
- `objective` (string): 总目标 / 任务拆解意图
- `constraints` (list[string]): 全局约束
- `selected_agents` (list[string]): 必须与 Router 选中集合完全一致（不增删）
- `tasks` (list[task]): 每个 agent 的任务单，必须覆盖所有 selected_agents
- `aggregation` (object): 汇总策略与交付对齐
- `budget` (object): 预算/成本/时延提示（hints）
- `output_spec` (object): 最终汇总输出规范

## 3) Task 结构（强约束）
每个 `task` 必须包含：
- `agent_id` (string)
- `task_id` (string)
- `objective` (string)
- `steps` (list[string], non-empty)
- `agent_can_extend_steps` (bool, must be true)
- `extension_policy` (string)

## 4) 运行态消费规则（代码证据）
- a01 输出落入 `analyst_results["a01_cio_orchestrator"]["contract"]`。
- `manager_broadcast` 在派发每个 agent 时优先读取并校验合同：
  - 校验通过：按 `tasks[agent_id]` 的 `steps` 构建 subtask。
  - 校验失败：回退到既有模板广播（不破坏现状）。
- contract 不得新增/删除 agent；若 `selected_agents` 与 Router 计划不一致，合同无效。

代码位置：
- `src/react_agent/prompts.py`：a01 输出 schema 说明（ORCHESTRATOR_SYSTEM_PROMPT）
- `src/react_agent/default_agents.py`：解析并保留 contract 字段
- `src/react_agent/graph.py`：合同校验与派发逻辑（manager_broadcast）

## 5) 日志与可回流数据
`run_logger` 记录派发摘要：
- `used_contract` (true/false)
- `contract_hash`
- `task_id`
- `step_count`

## 6) 示例（JSON）
```json
{
  "schema_version": "a01_contract_v0",
  "objective": "拆解多层任务并对齐验收标准",
  "constraints": ["不得新增/删除 agent", "必须按 router_plan_summary 对齐"],
  "selected_agents": ["a01_cio_orchestrator", "a03_macro_policy", "a04_risk_control"],
  "tasks": [
    {
      "agent_id": "a03_macro_policy",
      "task_id": "L2-a03-001",
      "objective": "宏观环境分析",
      "steps": ["界定研究范围", "列出关键假设", "给出结论与不确定性"],
      "agent_can_extend_steps": true,
      "extension_policy": "允许补充验证步骤，但不得偏离目标"
    }
  ],
  "aggregation": {"strategy": "layered_merge", "handoff_notes": "L4 汇总需引用证据卡"},
  "budget": {"time_budget": "fast", "cost_budget": "medium", "token_budget": "controlled"},
  "output_spec": {"required_sections": ["结论", "风险"], "final_answer_format": "bullets"}
}
```
