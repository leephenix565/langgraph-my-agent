# 功能性智能体替换接入指南

## 1. 文档目的

本文只回答一个具体工程问题：

> 如果想把当前系统里的某个“功能性智能体”，替换成同学自己开发的“对应功能智能体”，在这个仓库里应该怎么接入？

这里说的“替换”，不是泛泛地“再加一个 agent”，而是：

- 系统里已经有一个现成的功能 agent
- 你希望它继续承担原来的产品职责和 layer 位置
- 但运行时真正执行它的人，换成同学开发的实现

本文只讨论这种场景，不讨论：

- public transcript / store / replay 语义改造
- 多说话人聊天
- raw graph messages 暴露
- router / orchestrator / report center 这类特殊 runtime 角色改造

## 2. 先给结论：推荐的最小正确替换方式

对于“把现有功能 agent 换成同学开发的对应 agent”这个场景，默认推荐策略是：

1. **保留原有 `agent_id` 不变**
2. **保留原有 layer 定位不变**
3. **必要时保留原 metadata 文件，只替换执行实现**
4. **把同学的实现包装成当前仓库兼容的 tool**
5. **在 bootstrap 阶段把这个 tool 注册进 `AGENT_TOOLS`**

也就是说，最小正确替换不是“改个 JSON”，而是：

`同一个 agent_id` + `新的执行实现`

这样做的好处是：

- router / catalog / layer plan / manager dispatch 不需要跟着改 id
- `graph.py` 里的节点注册和派工链路基本不受影响
- `/agents` 页面、workflow 展示和下游结果消费的认知成本最低
- 更符合“替换同功能 agent”，而不是“新增另一个平行 agent”

## 3. 本文适用范围

本文讨论的“功能性智能体”，主要指普通分析/研究/风控/组合/估值/合规类 agent，例如：

- `a03_macro_policy`
- `a21_reg_compliance`
- `a23_portfolio_opt`

这类 agent 在当前系统里都走同一类普通执行路径：

- metadata 来自 `config/agents/agent_*.json`
- runtime registry 来自 `src/react_agent/agents.py`
- bootstrap 装配来自 `src/react_agent/graph_bootstrap.py`
- graph 执行来自 `src/react_agent/graph.py` 中的 `_build_agent_node(...)`
- 最终真正调用的是 `tool.ainvoke(...)`

## 4. 不适用对象：不要按本文方式替换的特殊角色

下面这些角色**不要**按“普通功能 agent 替换”来理解：

- `a01_cio_orchestrator`
- `a25_report_center`
- `a02_task_router`

原因不是它们“更高级”，而是它们在当前代码里根本不是普通 analyst 路径。

### 4.1 `a01_cio_orchestrator`

它不是普通功能 agent，而是带有专门 runtime 语义的 orchestrator 角色。

相关证据：

- `src/react_agent/graph.py` 的 `manager_broadcast(...)` 对 `a01_cio_orchestrator` 有单独 assignment 分支
- `src/react_agent/default_agents.py` 的 `_build_agent_tool(...)` 对 `a01_cio_orchestrator` 使用 `ORCHESTRATOR_SYSTEM_PROMPT`
- `src/react_agent/prompts.py` 里存在专门的 `ORCHESTRATOR_SYSTEM_PROMPT`

### 4.2 `a25_report_center`

它不是普通功能 agent，而是最终报告骨架与证据约束角色。

相关证据：

- `src/react_agent/graph.py` 的 `manager_broadcast(...)` 对 `a25_report_center` 有单独 assignment 分支
- `src/react_agent/default_agents.py` 的 `_build_agent_tool(...)` 对 `a25_report_center` 使用 `REPORT_CENTER_SYSTEM_PROMPT`
- `src/react_agent/prompts.py` 里存在专门的 `REPORT_CENTER_SYSTEM_PROMPT`
- `src/react_agent/graph.py` 的 summary/build bundle 路径还会单独处理 `a25_report_center` 结果

### 4.3 `a02_task_router`

它更接近路由/任务拆解角色，不适合按“同学做了一个普通功能 agent，就直接平替”的思路处理。

如果你要替换的是这三类角色，属于更高风险的 runtime 角色改造，不是本文范围。

## 5. 在本项目里，“功能性智能体”真实由什么组成

很多人第一次看这个仓库时，会误以为：

- `config/agents/agent_*.json` 就是 agent 本体

这不对。对当前系统来说，一个功能 agent 至少有两部分：

1. **metadata**
2. **可执行 tool**

### 5.1 metadata：告诉系统“它是谁”

metadata 来自：

- `config/agents/agent_*.json`
- `src/react_agent/agents.py` 的 `AgentMetadata`
- runtime registry `AGENT_METADATA`

它负责描述：

- `id`
- `name`
- `description`
- `capabilities`
- `input_type`
- `latency_level`
- `cost_level`
- `version`
- `layer`
- `team`
- `role_type`
- `default_enabled`

### 5.2 tool：告诉系统“怎么真正执行它”

执行能力最终来自：

- `src/react_agent/agents.py` 的 `AGENT_TOOLS`
- `src/react_agent/agents.py` 的 `register_agent(...)`

graph 真正运行时，不是看 JSON 文案，而是看：

- 这个 `agent_id` 有没有 metadata
- 这个 `agent_id` 有没有对应 tool

### 5.3 graph 运行时只认 registry，不认“你心里觉得已经接上了”

真正调用链如下：

1. `src/react_agent/graph.py` import 时执行 `bootstrap_agent_runtime()`
2. `src/react_agent/graph_bootstrap.py` 负责装配 metadata 和 tool
3. `src/react_agent/graph.py` 调用 `build_node_registry(...)`
4. `manager_broadcast(...)` 在某一层选中 agent
5. `_build_agent_node(agent_id)` 从 `AGENT_TOOLS[agent_id]` 取出 tool
6. 执行 `await tool.ainvoke(agent_input, config=...)`

所以，“替换成功”的标准不是：

- `/agents` 页面里看到了它

而是：

- `AGENT_TOOLS` 里这个 id 的实现，已经变成同学那套逻辑

## 6. 只改 JSON 为什么不等于“替换成同学的智能体”

这是最容易踩的坑。

`src/react_agent/graph_bootstrap.py` 的 `bootstrap_agent_runtime()` 逻辑是：

1. 先根据条件注册 built-in
2. 再 `load_metadata_from_dir(CONFIG_AGENT_DIR)`
3. 然后遍历 `AGENT_METADATA`
4. 如果某个 id 还没有 tool，就自动补一个 tool

补 tool 的规则是：

- description 不为空：用 `src/react_agent/default_agents.py` 里的 `_build_agent_tool(...)`
- description 为空：用 `src/react_agent/generic_agent.py` 里的 `build_generic_agent_tool(...)`

这意味着：

- 只改 `config/agents/agent_*.json`
- 或只让 metadata 进入 `AGENT_METADATA`

都**不等于**“runtime 已经在执行同学的实现”。

在这种情况下，系统仍可能跑的是：

- description 驱动的默认 LLM tool
- 或 generic stub tool

而不是你同学真正写的 agent。

## 7. 哪些 agent 适合按“功能替换”思路处理

默认建议优先替换这类普通 domain/function agents：

- L2 普通研究/分析 agent
- L3 普通风险/合规/组合/估值 agent
- 不承载 orchestrator / router / final report 特殊职责的 agent

例如下面几类都属于相对标准的功能 agent：

- `a03_macro_policy`
- `a21_reg_compliance`
- `a23_portfolio_opt`

它们在 graph 中都按普通路径运行：

- `manager_broadcast(...)` 派工
- `_build_agent_node(...)` 组装 `agent_input`
- `tool.ainvoke(...)` 真正执行

这类 agent 最适合“保留原 id，只换实现”。

## 8. 推荐接入方案：保留原 `agent_id`，只替换执行实现

这是本文最推荐的方案。

### 8.1 为什么推荐保留原 `agent_id`

因为当前系统很多地方都围绕现有 id 运作：

- metadata catalog
- layer plan
- manager dispatch
- graph node registry
- analyst result key
- summary / fusion / workflow 观察层

如果你直接新建一个全新 `agent_id`，代价会明显增加：

- router 需要学会选它
- catalog 和现有认知需要同步
- layer plan 可能要改
- graph import 时 node registry 也要确保纳入它
- 旧 id 对应的消费链可能还在

但如果你只是想把“现有某个功能 agent”换成同学写的“对应功能 agent”，通常没有必要承担这部分额外成本。

### 8.2 什么叫“只替换执行实现”

就是下面这件事：

- metadata 继续沿用原 `agent_id`
- graph 继续把它当成原来的功能位
- 但 `AGENT_TOOLS[agent_id]` 指向的 tool，不再是默认实现，而是同学实现的包装器

## 9. 替换接入的完整步骤

下面按“替换一个现有功能 agent”为主线说明。

### 第一步：选定要替换的现有 agent

先去看：

- `config/agents/agent_*.json`

确认下面几件事：

1. 它是普通功能 agent，而不是 `a01/a25/a02`
2. 它的 `id`、`layer`、`team`、`capabilities`、`input_type` 是否与你同学的实现语义一致
3. 它在产品和 graph 中承担的职责是否就是你想替换的那个位置

如果只是“能力有点像”，但实际上不是同一个职责位，就不建议硬替。

### 第二步：决定替换策略

默认策略：

- **保留原 `agent_id`**
- **保留原 layer**
- **只替换执行实现**

什么时候可以改 metadata？

- `name`
- `description`
- `version`
- `capabilities`

这些字段如果确实需要反映新实现，可以调整。

但下面这些字段一般不建议轻易改：

- `id`
- `layer`
- `role_type`
- `default_enabled`

尤其是：

- `id` 决定 graph/runtime registry 的定位
- `layer` 影响 router/manager 调度语义

### 第三步：准备同学 agent 的适配层

同学开发的 agent，无论原始形式是什么：

- 自定义 Python 类
- SDK 调用封装
- LangChain / LangGraph 子链
- 另一个服务的 RPC/HTTP 客户端

最终都建议被包装成当前仓库兼容的 tool。

#### 3.1 当前 graph 实际会传入什么

`src/react_agent/graph.py` 的 `_build_agent_node(...)` 当前会传入：

- `question`
- `subtask`
- `shared_context`
- `history`
- `tools_config`
- `router_plan_summary`

注意：

- `router_plan_summary` 虽然没有显式写进 `AgentInput` 轻量类型定义里
- 但 runtime 调用路径当前确实会传这个字段

所以你的包装层最好显式接收它。

#### 3.2 当前 graph 希望拿回什么

当前系统对 `AgentOutput` 的常用消费字段主要是：

- `analysis`
- `key_points`
- `evidence`
- `confidence`
- 可选 `parse_ok`

建议同学实现的最终包装输出至少回到这套字段。

如果你直接返回另一套复杂 JSON，虽然未必立刻报错，但很容易让：

- manager summary
- evidence 汇总
- 下游结果消费

出现质量下降或语义不稳定。

### 第四步：在仓库里注册这个替换实现

推荐做法是新增一个集中适配模块，例如：

- `src/react_agent/external_agents.py`

这个模块只负责两件事：

1. 包装同学 agent
2. 调 `register_agent(...)`

#### 4.1 推荐的注册时机

推荐在 `bootstrap_agent_runtime()` 流程里，**metadata load 完成之后、默认 tool 回填之前**，显式调用外部注册函数。

推荐顺序如下：

1. `load_metadata_from_dir(CONFIG_AGENT_DIR)`
2. `register_external_function_agents()`
3. 默认回填 `_build_agent_tool(...)` / `build_generic_agent_tool(...)`

这样做的原因是：

- metadata 已经从配置文件加载进来了
- 你可以直接复用原 metadata
- 你自己的 tool 会先占住 `AGENT_TOOLS[agent_id]`
- 后续默认回填逻辑看到这个 id 已经有 tool，就不会再覆盖

#### 4.2 为什么不建议只在 graph import 之后“临时覆盖”

如果只是某个别处 import 以后再临时改 registry：

- 调用顺序更不透明
- import-time 行为更难推断
- 后续排查“到底跑的是谁”会更难

对“同学功能 agent 替换”这类长期维护场景，不推荐这种隐式覆盖方式。

## 10. 最小 metadata 示例

如果你替换的是现有功能 agent，通常原文件可以继续用；下面给一个“保留原 `agent_id`”的示意写法。

```json
{
  "id": "a23_portfolio_opt",
  "name": "投资组合优化智能体",
  "description": "由外部实现替换后的组合优化功能位，继续承担 L3 组合配置与优化分析职责。",
  "capabilities": ["allocation", "hedging", "backtest"],
  "input_type": "portfolio",
  "latency_level": "medium",
  "cost_level": "normal",
  "version": "v0.3-external",
  "layer": "L3",
  "team": "portfolio",
  "role_type": "system",
  "default_enabled": true
}
```

哪些字段建议保持不变：

- `id`
- `layer`
- `role_type`
- `default_enabled`

哪些字段可以视情况调整：

- `name`
- `description`
- `version`
- `capabilities`

## 11. 最小 Python 适配器示例

下面的示例只展示“怎么把同学的实现包成当前系统兼容 tool”，不是要求你必须按这个文件名实现。

推荐新增：

- `src/react_agent/external_agents.py`

示例：

```py
from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool

from react_agent.agents import (
    AGENT_METADATA,
    AgentMetadata,
    AgentOutput,
    register_agent,
)


async def invoke_classmate_portfolio_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    # 这里替换成你同学自己的实现：
    # - 直接调用本地 Python 类
    # - 调用内部 SDK
    # - 调用另一个服务
    # 只要最后能拿到结果即可
    raise NotImplementedError


def register_external_function_agents() -> None:
    base_meta = AGENT_METADATA.get("a23_portfolio_opt")
    meta = base_meta or AgentMetadata(
        id="a23_portfolio_opt",
        name="投资组合优化智能体",
        description="外部实现接入的组合优化功能位",
        capabilities=["allocation", "hedging", "backtest"],
        input_type="portfolio",
        latency_level="medium",
        cost_level="normal",
        version="v0.3-external",
        layer="L3",
        team="portfolio",
        role_type="system",
        default_enabled=True,
    )

    @tool("agent_a23_portfolio_opt")
    async def external_a23_portfolio_opt(
        question: str,
        subtask: str,
        shared_context: Dict[str, Any] | None = None,
        history: List[Dict[str, Any]] | None = None,
        tools_config: Dict[str, Any] | None = None,
        router_plan_summary: str | None = None,
    ) -> AgentOutput:
        shared_context = shared_context or {}
        history = history or []
        tools_config = tools_config or {}

        result = await invoke_classmate_portfolio_agent(
            {
                "question": question,
                "subtask": subtask,
                "shared_context": shared_context,
                "history": history,
                "tools_config": tools_config,
                "router_plan_summary": router_plan_summary,
            }
        )

        return {
            "analysis": str(result.get("analysis", "")).strip(),
            "key_points": [
                str(item).strip()
                for item in result.get("key_points", [])
                if str(item).strip()
            ],
            "evidence": [
                str(item).strip()
                for item in result.get("evidence", [])
                if str(item).strip()
            ],
            "confidence": float(result.get("confidence", 0.5)),
            "parse_ok": bool(result.get("parse_ok", True)),
        }

    register_agent(meta, external_a23_portfolio_opt)
```

这个示例的关键点是：

- **同一个 `agent_id`**
- **同一个功能位**
- **新的 tool 实现**

而不是另起一个“长得差不多的新 agent”。

## 12. 在 bootstrap 中如何挂这段注册

推荐把外部注册插到 `src/react_agent/graph_bootstrap.py` 的 bootstrap 流程中。

推荐思路：

```py
from react_agent.external_agents import register_external_function_agents


def bootstrap_agent_runtime() -> None:
    enable_builtin = ...
    config_exists = ...
    if enable_builtin or not config_exists:
        register_builtin_agents()
    if config_exists:
        load_metadata_from_dir(CONFIG_AGENT_DIR)

    register_external_function_agents()

    for aid, meta in list(AGENT_METADATA.items()):
        if aid in AGENT_TOOLS:
            continue
        ...
```

这里的关键不是“必须叫这个函数名”，而是**顺序**：

- 先让 metadata 进来
- 再覆盖/注册你自己的 tool
- 最后才做默认 tool 回填

## 13. 如何验证“真的替换成功”

不要只看一个信号。

### 13.1 静态验证

至少确认下面几点：

1. `AGENT_METADATA` 里有这个 agent
2. `AGENT_TOOLS` 里有这个 agent
3. `AGENT_TOOLS[agent_id]` 不再是你不想要的默认实现

### 13.2 graph 运行时验证

至少确认下面几点：

1. `src/react_agent/graph.py` import 不报错
2. `build_node_registry(...)` 已为这个 id 生成 node
3. `manager_broadcast(...)` 选到该 agent 时，会走到 `_build_agent_node(...)`
4. `_build_agent_node(...)` 里的 `tool.ainvoke(...)` 实际命中了新包装器

### 13.3 产品面验证

还要确认下面几点没有被你顺手破坏：

1. public transcript 仍然只有一个 assistant persona
2. workflow 仍然只是 inspector / progress layer
3. 不会把内部 agent 变成多个聊天发言人
4. 不暴露 raw graph messages、raw router output、raw agent JSON、raw CoT

### 13.4 “出现在 `/agents` 页面”为什么不够

因为 `/agents` 页面是 metadata catalog，不是 runtime call trace。

它最多只能证明：

- metadata 在

它不能证明：

- graph 调用的是你同学那套实现

## 14. 最容易踩的坑

### 坑 1：只换 JSON，没换执行逻辑

这是最常见的误判。

结果通常是：

- 页面上看起来 agent 信息变了
- 实际 runtime 还在跑默认 `_build_agent_tool(...)`
- 或 generic stub

### 坑 2：为了“干净”新建一个全新 `agent_id`

这样会额外引入：

- router 选择问题
- layer plan 对齐问题
- graph node registry 收口问题
- 旧结果消费链适配成本

如果目标只是“把现有功能位换成同学实现”，通常不值得。

### 坑 3：输出不回到当前 `AgentOutput` 常用字段

当前系统对普通 agent 的稳定消费面主要还是：

- `analysis`
- `key_points`
- `evidence`
- `confidence`
- `parse_ok`

如果你直接返回另一套复杂对象，下游链路虽然未必立即崩，但很容易降质。

### 坑 4：把 `a01/a25/a02` 当成功能 agent 平替

这三类不是普通 analyst 功能位。

它们带有更强的 runtime 角色语义，替换方式不同。

### 坑 5：误以为 public transcript 会出现多个 agent 发言

不会。

当前系统的 public transcript 仍然维持单助手人格。

内部多 agent 协作只允许通过：

- workflow
- summarized progress
- safe workflow snapshot

这种方式被观察，而不是变成多个聊天说话人。

### 坑 6：忽略 `tools_config` / `shared_context` / `router_plan_summary`

同学的 agent 包装器如果完全不理这些输入，通常不会影响“能不能跑”，但会明显影响它在当前多智能体系统里的协作质量。

尤其建议至少正确消费：

- `subtask`
- `shared_context`
- `tools_config`
- `router_plan_summary`

## 15. 推荐的最小实施 checklist

如果你要真正落地替换一个功能 agent，可以按下面顺序执行。

### 15.1 选择对象

- 选一个普通功能 agent
- 确认不是 `a01/a25/a02`

### 15.2 保留定位

- 保留原 `agent_id`
- 保留原 `layer`

### 15.3 准备适配器

- 把同学实现包装成当前 tool 签名
- 输出映射回 `AgentOutput`

### 15.4 接入 bootstrap

- 在 metadata load 之后注册
- 在默认 tool 回填之前覆盖

### 15.5 做双重验证

- catalog 层验证
- graph 真实执行验证

## 16. 什么时候才应该新建全新 `agent_id`

只有在下面这种情况下，才更适合新建而不是“替换”：

- 你不是要替换现有功能位
- 而是新增一个之前根本不存在的新职责
- 并愿意同步承担 router、catalog、layer plan、node registry、产品认知的整体适配成本

否则，对“功能性智能体换成同学开发的对应智能体”这个需求，默认还是：

**保留原 `agent_id`，只替换执行实现。**

## 17. 最后总结

在这个仓库里，替换一个功能性智能体的本质不是：

- 改介绍文案
- 改配置文件名字
- 让 `/agents` 页多一条记录

而是：

1. 找到现有功能位
2. 保留它的 `agent_id` 和 layer 定位
3. 把同学实现包装成当前 runtime 兼容的 tool
4. 在 bootstrap 里注册进 `AGENT_TOOLS`
5. 验证 graph 真正调用到了它

如果你做到的是这五步，才算真正把“系统里的功能性智能体”替换成了“同学开发的对应智能体”。
