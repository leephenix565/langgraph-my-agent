# 功能性智能体替换接入指南

> Scope note: if you are developing a new external HTTP agent from scratch,
> read `examples/external_agent_scaffold/EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md` first. This guide is
> for replacing an existing repo functional agent while preserving current graph
> semantics and runtime ids.

> External-agent boundary: this file is a maintainer/internal replacement guide,
> not the third-party external-agent protocol entrypoint. For independent
> external agents, use `GET /health`, `POST /v1/agent/invoke`,
> `external_agent_response_v0`, and a repo-side wrapper as described in
> `examples/external_agent_scaffold/EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md` and
> `examples/external_agent_scaffold/EXTERNAL_AGENT_INTEGRATION_STANDARD.md`. Any `/invoke`, `/healthz`, or
> direct `AgentOutput` examples below are private/simple replacement patterns
> for maintainers and are not the public external-agent standard.

## Phase AC-1A Catalog v2 Note

Agent Catalog v2 changes the ordinary agent id set. Replacement work after AC-1A must start from `docs/AGENT_CATALOG_V2_SHEET2_MAPPING.md`, not from the old 26-config catalog. The runtime id is still the registration key in `AGENT_TOOLS`; for the three valuation agents, replacement means maintaining the HTTP wrapper contract rather than allowing default LLM valuation output. `a01_cio_orchestrator` and `a25_report_center` remain special runtime roles.

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

## 3. 接入形态选择：先决定“同仓包装”还是“外部协议”

在这个仓库里，“替换功能性智能体”不是只有一种接法。更准确地说，当前有三种接入形态：

### 3.1 同仓 Python 包装

适用情况：

- 同学愿意把实现作为 Python 模块直接被当前仓库 import
- 依赖简单，没有单独部署诉求
- 你希望接入链最短、排查成本最低

推荐级别：

- **默认首选**

原因：

- 最少网络面
- 最少部署面
- 最贴近当前 `tool.ainvoke(...)` 的执行形态

### 3.2 FastAPI/HTTP 私有接口 + 本地 tool 适配

适用情况：

- 同学的 agent 独立维护
- 同学的实现需要单独部署
- 同学的实现不适合同仓直接 import
- 同学的实现甚至不是 Python 写的，但可以通过 HTTP 服务暴露

推荐级别：

- **外部接入首选**

原因：

- 当前仓库已经依赖 `fastapi`
- 当前仓库已经依赖 `httpx`
- 当前 `graph.py` 对普通 agent 的调用就是一次 `await tool.ainvoke(...)` 的请求-响应模型
- 所以外部协议里，HTTP 最接近当前系统的自然边界

### 3.3 其他协议

例如：

- gRPC
- WebSocket
- 消息队列
- 其他 RPC 框架

推荐级别：

- **不作为本文默认方案**

原因：

- 当前 repo 没有现成的 gRPC 基建
- WebSocket / SSE 不适合单 agent 一次性返回 `AgentOutput`
- 消息队列不符合当前 graph turn 内“同步等待 agent 返回结果”的执行模型

本文的明确结论是：

> 如果同学的功能 agent 需要通过外部协议接入，在当前项目现状下，默认优先写成 FastAPI/HTTP 私有接口，而不是泛泛地说“任意 RPC 都可以”。

## 4. 本文适用范围

本文讨论的“功能性智能体”，主要指普通分析/研究/风控/组合/估值/合规类 agent，例如：

- `a03_macro_industry_research`
- `a20_compliance_review`
- `a21_portfolio_manager`

这类 agent 在当前系统里都走同一类普通执行路径：

- metadata 来自 `config/agents/agent_*.json`
- runtime registry 来自 `src/react_agent/agents.py`
- bootstrap 装配来自 `src/react_agent/graph_bootstrap.py`
- graph 执行来自 `src/react_agent/graph.py` 中的 `_build_agent_node(...)`
- 最终真正调用的是 `tool.ainvoke(...)`

## 5. 不适用对象：不要按本文方式替换的特殊角色

下面这些角色**不要**按“普通功能 agent 替换”来理解：

- `a01_cio_orchestrator`
- `a25_report_center`
- `a02_task_router` metadata (removed in AC-1A; real router is `router_node`)

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

### 4.3 `a02_task_router` metadata (removed in AC-1A; real router is `router_node`)

它更接近路由/任务拆解角色，不适合按“同学做了一个普通功能 agent，就直接平替”的思路处理。

如果你要替换的是这三类角色，属于更高风险的 runtime 角色改造，不是本文范围。

## 6. 在本项目里，“功能性智能体”真实由什么组成

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

## 7. 只改 JSON 为什么不等于“替换成同学的智能体”

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

## 8. 哪些 agent 适合按“功能替换”思路处理

默认建议优先替换这类普通 domain/function agents：

- L2 普通研究/分析 agent
- L3 普通风险/合规/组合/估值 agent
- 不承载 orchestrator / router / final report 特殊职责的 agent

例如下面几类都属于相对标准的功能 agent：

- `a03_macro_industry_research`
- `a20_compliance_review`
- `a21_portfolio_manager`

它们在 graph 中都按普通路径运行：

- `manager_broadcast(...)` 派工
- `_build_agent_node(...)` 组装 `agent_input`
- `tool.ainvoke(...)` 真正执行

这类 agent 最适合“保留原 id，只换实现”。

## 9. 为什么 FastAPI/HTTP 在当前项目里是合适边界

如果你想把同学开发的功能 agent 以“独立服务”的方式接进来，FastAPI/HTTP 是当前项目里最自然的边界。

原因要从当前 graph 的真实调用形态说起。

`src/react_agent/graph.py` 的 `_build_agent_node(...)` 当前做的事情，本质上只有三步：

1. 组装一个 `agent_input`
2. 从 `AGENT_TOOLS[agent_id]` 取出当前 agent 的 tool
3. 执行 `await tool.ainvoke(agent_input, config=...)`

这说明 graph 对普通功能 agent 的期待，不是：

- 长连接会话
- token streaming
- 多轮 agent 内部状态同步

而是：

- 一次异步请求
- 一次标准结果返回

这和 HTTP 的请求-响应模型天然一致。

同时，当前仓库依赖里已经有：

- `fastapi`
- `httpx`

所以最自然的外部接法是：

1. 同学实现单独暴露一个 FastAPI 私有服务
2. 本仓库在 `src/react_agent/external_agents.py` 里用 `httpx.AsyncClient` 包一层 tool
3. 再通过 `register_agent(...)` 覆盖原 `agent_id`

这里必须强调一句：

- **graph 并不会直接“调用一个协议”来替换 agent**
- **真正的替换点仍然是 `AGENT_TOOLS[agent_id]`**

FastAPI/HTTP 只是“同学实现”的承载协议，而不是 graph 的直接替换对象。

同样也不建议：

- 把同学 agent 直接暴露成 public chat API
- 复用 `src/react_agent/public_api.py` 这条面向 Web 前端的 public adapter 作为内部 agent 替换协议

因为 `public_api.py` 是产品 public surface，不是内部普通功能 agent 的执行协议。

## 10. 推荐接入方案：保留原 `agent_id`，只替换执行实现

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

## 11. 替换接入的完整步骤

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

#### 3.1.1 如果走 FastAPI，应使用什么接口形状

如果你选择把同学的实现做成一个独立服务，建议它提供一个极简私有接口。

注意：本节的 `/invoke` / `/healthz` 是内部私有替换模式，只适用于“保留同一个 repo `agent_id`、由维护者写本地 adapter”的简单场景。第三方独立 external-agent 标准入口不是这里的 `/invoke`，而是 `GET /health` + `POST /v1/agent/invoke` + `external_agent_response_v0` + repo-side wrapper。

内部私有替换模式的推荐接口：

- `POST /invoke`
- 可选 `GET /healthz`

在这个内部私有模式中，`POST /invoke` 请求体建议固定为：

- `question`
- `subtask`
- `shared_context`
- `history`
- `tools_config`
- `router_plan_summary`

可附加但不强依赖：

- `agent_id`
- `run_id`

在这个内部私有模式中，`POST /invoke` 返回体可以直接返回兼容 `AgentOutput` 的 JSON：

- `analysis`
- `key_points`
- `evidence`
- `confidence`
- 可选 `parse_ok`

协议边界要明确：

- 不传 raw `state["messages"]`
- 不传 raw router output
- 不传 raw manager assignment 之外的内部 state 噪声
- 不要求同学服务理解 LangGraph

它只需要：

- 吃下当前功能 agent 的任务输入
- 返回标准 `AgentOutput`

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

## 12. 协议选择建议

为了避免实现时“什么都能做、反而不知道该怎么做”，这里给一个固定决策表。

### 12.1 什么时候选同仓 Python 包装

适用：

- 同学实现就在 Python 仓库里
- 依赖简单
- 不想引入额外部署面

建议：

- 选 **同仓 Python 包装**

### 12.2 什么时候选 FastAPI/HTTP

适用：

- 同学实现独立维护
- 同学实现独立部署
- 同学实现不是 Python
- 你希望接入边界清楚、协议足够简单

建议：

- 选 **FastAPI/HTTP**

### 12.3 什么时候才考虑 gRPC

适用：

- 你明确需要更高吞吐
- 需要强类型 IDL
- 已经有现成服务治理和基础设施

建议：

- 可以考虑 gRPC
- 但这已经超出了当前仓库的默认接入复杂度

### 12.4 为什么不推荐 WebSocket / SSE

不推荐作为功能 agent 替换默认协议。

原因：

- 当前普通 agent 路径消费的是一次性的 `AgentOutput`
- 不是 token 流
- 不是长连接协作协议

### 12.5 为什么不推荐消息队列

不推荐作为默认替换路径。

原因：

- 当前 `manager_broadcast(...) -> _build_agent_node(...)` 是 turn 内等待结果的同步控制流
- 消息队列更适合异步任务，不适合这里的最小替换方案

## 13. 最小 metadata 示例

如果你替换的是现有功能 agent，通常原文件可以继续用；下面给一个“保留原 `agent_id`”的示意写法。

```json
{
  "id": "a21_portfolio_manager",
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

## 14. 最小 Python 适配器示例

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
    base_meta = AGENT_METADATA.get("a21_portfolio_manager")
    meta = base_meta or AgentMetadata(
        id="a21_portfolio_manager",
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

    @tool("agent_a21_portfolio_manager")
    async def external_a21_portfolio_manager(
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

    register_agent(meta, external_a21_portfolio_manager)
```

这个示例的关键点是：

- **同一个 `agent_id`**
- **同一个功能位**
- **新的 tool 实现**

而不是另起一个“长得差不多的新 agent”。

## 15. FastAPI/HTTP 方案的最小双端示例

如果同学的功能 agent 是独立服务，下面示例展示一种内部私有替换形状。它不是第三方 external-agent 标准；对外部独立 agent，应优先使用 `/v1/agent/invoke` 标准协议。

### 15.1 同学侧 FastAPI 服务最小接口示例

```py
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel


class InvokeRequest(BaseModel):
    question: str
    subtask: str
    shared_context: dict = {}
    history: list = []
    tools_config: dict = {}
    router_plan_summary: str | None = None
    agent_id: str | None = None
    run_id: str | None = None


class InvokeResponse(BaseModel):
    analysis: str
    key_points: list[str]
    evidence: list[str]
    confidence: float
    parse_ok: bool = True


app = FastAPI()


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(payload: InvokeRequest) -> InvokeResponse:
    # 这里替换成同学自己的真实逻辑
    return InvokeResponse(
        analysis=f"已完成子任务：{payload.subtask}",
        key_points=["示例要点 1", "示例要点 2"],
        evidence=["source=internal-demo"],
        confidence=0.72,
        parse_ok=True,
    )
```

这个服务不需要理解 LangGraph，也不需要暴露内部 graph 事件。

它只需要：

- 接受当前功能 agent 的任务输入
- 返回标准 `AgentOutput`

### 15.2 本仓库侧 HTTP tool 适配器示例

```py
from __future__ import annotations

from typing import Any, Dict, List

import httpx
from langchain_core.tools import tool

from react_agent.agents import (
    AGENT_METADATA,
    AgentMetadata,
    AgentOutput,
    register_agent,
)

REMOTE_BASE_URL = "http://127.0.0.1:9001"


def register_external_function_agents() -> None:
    base_meta = AGENT_METADATA.get("a20_compliance_review")
    meta = base_meta or AgentMetadata(
        id="a20_compliance_review",
        name="监管合规智能体",
        description="通过外部 FastAPI 服务接入的合规功能位",
        capabilities=["compliance", "regulatory", "policy"],
        input_type="compliance",
        latency_level="medium",
        cost_level="normal",
        version="v0.3-external-http",
        layer="L3",
        team="compliance",
        role_type="system",
        default_enabled=True,
    )

    @tool("agent_a20_compliance_review")
    async def external_a20_compliance_review(
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

        payload = {
            "agent_id": "a20_compliance_review",
            "question": question,
            "subtask": subtask,
            "shared_context": shared_context,
            "history": history,
            "tools_config": tools_config,
            "router_plan_summary": router_plan_summary,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{REMOTE_BASE_URL}/invoke", json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return {
                "analysis": f"a20_compliance_review 外部替换实现暂不可用：{type(exc).__name__}",
                "key_points": [],
                "evidence": ["external replacement wrapper fail-soft"],
                "confidence": 0.0,
                "parse_ok": False,
            }

        return {
            "analysis": str(data.get("analysis", "")).strip(),
            "key_points": [
                str(item).strip()
                for item in data.get("key_points", [])
                if str(item).strip()
            ],
            "evidence": [
                str(item).strip()
                for item in data.get("evidence", [])
                if str(item).strip()
            ],
            "confidence": float(data.get("confidence", 0.5)),
            "parse_ok": bool(data.get("parse_ok", True)),
        }

    register_agent(meta, external_a20_compliance_review)
```

这个例子的关键仍然是：

- **保留原 `agent_id`**
- **只把内部执行改成一次 HTTP 调用**
- **graph / router / public transcript 不跟着变形**

## 16. 在 bootstrap 中如何挂这段注册

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

## 17. 错误处理和验证建议

如果你走 FastAPI/HTTP 方案，建议错误语义保持最简单：

本仓库 wrapper 如果遇到：

- 超时
- 非 2xx
- 无法解析 JSON
- 返回体不符合 `AgentOutput`

推荐做法：

- **在 wrapper 内返回 fail-soft `AgentOutput`**

理由是当前外部 HTTP wrapper 的生产口径应尽量把 transport/schema 失败压缩成可消费的结构化降级结果，避免把一次远端失败扩大成 graph 主链路异常。`src/react_agent/graph.py` 的 `_build_agent_node(...)` 仍有兜底：

- `except Exception`
- fail-soft 结构化兜底输出

但它应作为最后防线，而不是 HTTP adapter 的常规错误处理模板。

同时建议增加一套最小验证 checklist：

1. 外部服务 `GET /healthz` 正常；如果按统一 external-agent 标准接入，则检查 `GET /health`
2. 本仓库 wrapper 实际命中远端 `POST /invoke`；如果按统一 external-agent 标准接入，则应命中 `POST /v1/agent/invoke`
3. `AGENT_TOOLS[agent_id]` 已经被 HTTP wrapper 覆盖
4. graph 调到该 agent 时，日志或 trace 能看到远端调用

## 18. 如何验证“真的替换成功”

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

## 19. 最容易踩的坑

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

## 20. 推荐的最小实施 checklist

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

## 21. 什么时候才应该新建全新 `agent_id`

只有在下面这种情况下，才更适合新建而不是“替换”：

- 你不是要替换现有功能位
- 而是新增一个之前根本不存在的新职责
- 并愿意同步承担 router、catalog、layer plan、node registry、产品认知的整体适配成本

否则，对“功能性智能体换成同学开发的对应智能体”这个需求，默认还是：

**保留原 `agent_id`，只替换执行实现。**

## 22. 最后总结

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

如果同学的实现不适合同仓直接 import，那么在当前项目里最自然的外部协议默认方案就是：

- **FastAPI/HTTP 私有接口**
- **本仓库 `httpx.AsyncClient` wrapper**
- **最终仍注册进 `AGENT_TOOLS[agent_id]`**

也就是说，协议可以换，但 graph 的主业务语义和当前多智能体装配方式不用换。
