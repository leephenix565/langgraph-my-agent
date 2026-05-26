# External Agent Developer Guide / 外部独立智能体开发与接入指南

本文是外部独立智能体开发者的主入口，也给 `langgraph-my-agent` 主系统维护者提供接入 checklist。协议字段细节见 [EXTERNAL_AGENT_INTEGRATION_STANDARD.md](EXTERNAL_AGENT_INTEGRATION_STANDARD.md)；替换已有仓库功能 agent 的内部工程指南见 [../../docs/AGENT_REPLACEMENT_GUIDE.md](../../docs/AGENT_REPLACEMENT_GUIDE.md)。

## 1. 一句话目标

开发一个独立 HTTP agent 服务，并由主系统维护者通过 repo-side wrapper 注册到 `AGENT_TOOLS[main_agent_id]`，让它成为当前多智能体 graph 可调用、manager 可汇总、public adapter 可安全投影的功能型 agent。

本文不是 runtime 改造方案，不要求修改 Router prompt、`router_parse.py`、State schema、public API schema 或 frontend；外部 agent 也不会成为 public transcript 里的独立聊天 speaker。

## 2. 接入链路

当前推荐链路是：

```text
external FastAPI service
-> GET /health
-> POST /v1/agent/invoke
-> repo-side httpx wrapper
-> AGENT_TOOLS[main_agent_id]
-> graph agent node
-> AgentOutput
-> manager_summary / final_emit
-> public-safe assistant answer
```

关键判断标准：

- `AGENT_TOOLS[main_agent_id]` 是 graph runtime 的执行真源。
- `config/agents` metadata 只描述 agent，不等于已经接入真实外部服务。
- 外部服务只通过 repo-side wrapper 进入 graph，不直接进入 Router、State、frontend 或 public transcript。
- `turn.text` / public-safe assistant answer 才是最终面向用户的文字事实；外部 agent 原始 JSON 不直接展示给用户。

## 3. 角色分工

外部 agent 开发者负责：

- 提供独立可运行的 HTTP/FastAPI 服务。
- 实现 `GET /health`。
- 实现 `POST /v1/agent/invoke`。
- 返回结构化 `external_agent_response_v0`。
- 提供 typed errors、数据来源、工具结果、边界说明和自测证据。
- 不返回 raw traceback、secret、provider raw response 或 chain-of-thought。
- 不要求主系统传入 raw LangGraph `State`、raw `state["messages"]`、raw router output、manager assignment 或 raw graph event。

主系统维护者负责：

- 选择或确认主系统 `main_agent_id`。
- 确认外部服务自己的 `external_agent_id`。
- 编写 repo-side wrapper，将 `AgentInput` 压缩为外部 HTTP request。
- 将外部 response 映射为内部 `AgentOutput`。
- 在 bootstrap 阶段把 wrapper 注册到 `AGENT_TOOLS[main_agent_id]`。
- 确保 external wrapper 注册早于默认 `_build_agent_tool` / generic stub backfill。
- 编写 wrapper mock tests、fail-soft tests、registry/bootstrap tests 和必要的 smoke 记录。

frontend / public adapter 不负责：

- 不直接调用外部服务。
- 不把外部 agent 当成多 speaker 聊天对象。
- 不暴露 raw graph messages、raw router output、raw agent JSON、raw fusion payload 或 chain-of-thought。
- 不把 workflow inspector 当作 raw debug console。

## 4. ID 命名空间

当前系统使用双命名空间：

| 概念 | 示例 | 归属 | 用途 |
|---|---|---|---|
| `main_agent_id` | `a16_ml_valuation` | `langgraph-my-agent` | `AGENT_TOOLS` key、catalog/runtime id |
| `external_agent_id` | `valuation_ml` | 外部服务 | `/health` 和 `/v1/agent/invoke` response 中的服务 id |

三估值 agent 的当前映射：

| main agent id | external agent id | 默认 endpoint |
|---|---|---|
| `a16_ml_valuation` | `valuation_ml` | `http://127.0.0.1:8102/v1/agent/invoke` |
| `a17_traditional_valuation` | `valuation_traditional` | `http://127.0.0.1:8101/v1/agent/invoke` |
| `a18_meta_valuation` | `valuation_meta` | `http://127.0.0.1:8103/v1/agent/invoke` |

`/health` 和 response 中的 `agent_id` 应表示外部服务 id，例如 `valuation_ml`。主系统 wrapper 负责把它映射到 `AGENT_TOOLS[a16_ml_valuation]`。当前 wrapper 对 returned `agent_id` mismatch 追加 warning/evidence，不把它当 hard fail。

## 5. HTTP endpoint

外部服务至少提供：

```text
GET  /health
POST /v1/agent/invoke
```

可以额外提供领域 endpoint，例如：

```text
POST /v1/valuation/invoke
```

领域 endpoint 只用于领域自测、内部复用或人工调试，不能替代 `POST /v1/agent/invoke`。主系统 wrapper 的标准调用入口是 `/v1/agent/invoke`。

`POST /invoke` 或 `GET /healthz` 不是第三方 external-agent 标准入口。它们只可能出现在 [../../docs/AGENT_REPLACEMENT_GUIDE.md](../../docs/AGENT_REPLACEMENT_GUIDE.md) 的内部私有替换模式里。

## 6. Health 协议

`GET /health` 用于人工检查、运维检查和交付验收。当前三估值 wrapper runtime 不在每次 invoke 前解析 health schema，因此 health 是 service/self-test contract，不是当前 wrapper 的 live parser boundary。

推荐 response：

```json
{
  "schema_version": "external_agent_health_v0",
  "status": "ok",
  "agent_id": "valuation_ml",
  "agent_name": "Machine Learning Valuation Agent",
  "version": "0.1.0",
  "capabilities": ["valuation", "structured_response"],
  "input_modes": ["question"],
  "output_modes": ["external_agent_response_v0"],
  "llm_configured": true,
  "tools_configured": true,
  "data_ready": true,
  "max_concurrency": 1,
  "timeout_seconds": 30,
  "warnings": []
}
```

如果已有服务暂时只能返回较窄 health payload，至少应包含 `status`、外部 `agent_id`、版本或能力线索，并在 README 中说明缺失字段。新服务建议实现完整字段。

## 7. Request 协议

目标标准 request 可以包含顶层任务字段：

```json
{
  "schema_version": "external_agent_request_v0",
  "request_id": "req_001",
  "agent_id": "valuation_ml",
  "question": "请评估这家公司是否低估。",
  "language": "zh-CN",
  "subtask": "从机器学习估值角度分析估值区间。",
  "shared_context": {},
  "history": [],
  "router_plan_summary": {},
  "options": {
    "answer_mode": "structured",
    "timeout_seconds": 30
  }
}
```

当前三估值 repo-side wrapper 实际发送 compact payload：

```json
{
  "schema_version": "external_agent_request_v0",
  "request_id": "a16_ml_valuation-...",
  "question": "请评估这家公司是否低估。",
  "language": "zh",
  "context": {
    "main_agent_id": "a16_ml_valuation",
    "external_agent_id": "valuation_ml",
    "subtask": "从机器学习估值角度分析估值区间。",
    "shared_context_summary": {},
    "router_plan_summary": "Router plan summary"
  },
  "options": {
    "timeout_seconds": 30,
    "external_agent_id": "valuation_ml"
  }
}
```

因此，面向当前主系统的外部服务应至少支持：

- `schema_version`
- `request_id`
- `question`
- `language`
- `context`
- `options`

推荐做法是同时兼容目标顶层字段和当前 compact `context/options` 字段，忽略未知字段，并在只有 `question` 的情况下也能返回结构化结果或 typed clarification。

## 8. Response 协议

最低可运行 response 字段：

```json
{
  "schema_version": "external_agent_response_v0",
  "request_id": "req_001",
  "agent_id": "valuation_ml",
  "status": "ok",
  "question": "请评估这家公司是否低估。",
  "tool_result": {},
  "native_answer": "工具原生答案",
  "answer": "用户可读答案",
  "warnings": [],
  "errors": []
}
```

推荐 richer target fields：

```json
{
  "answer_mode": "structured",
  "confidence": 0.75,
  "key_points": ["核心结论"],
  "evidence": [{"source": "model", "summary": "证据摘要"}],
  "data_sources": [{"name": "valuation_db", "version": "2026-05-21"}]
}
```

当前 wrapper compatibility boundary：

- 当前 wrapper 主要消费 `status`、`answer` / `native_answer`、`tool_result`、`warnings`、`errors` 和 confidence fallback。
- 当前 wrapper 会从 `tool_result` 中总结部分估值/证据字段。
- 当前 wrapper 不严格校验完整 `external_agent_response_v0`：不会强校验 `schema_version`、`request_id`、typed error object schema 或完整 `tool_result` schema。
- 当前 wrapper 不完整消费顶层 `key_points`、`evidence`、`data_sources`。这些字段仍是推荐 rich fields；为了兼容当前 wrapper，应把关键证据也放入 `tool_result`、`answer`、`native_answer`、`warnings` 或可被安全摘要的结构里。

`status` 建议值：

| status | 语义 |
|---|---|
| `ok` | 完整成功 |
| `partial` | 部分成功，必须带 warning |
| `needs_clarification` | 需要用户补充信息 |
| `error` | 执行失败，不应作为有效分析结论 |

## 9. Typed errors

外部服务失败时不要返回 raw traceback。推荐 typed error：

```json
{
  "error_code": "DATA_NOT_FOUND",
  "error_message": "No matching security was found.",
  "stage": "resolver",
  "recoverable": true,
  "retryable": false,
  "user_action_required": true,
  "suggested_user_action": "Please provide a stock code or exchange."
}
```

当前 wrapper 会把 errors 安全压缩进 `AgentOutput.evidence` 或降级说明中，不会保留完整 typed-error object 作为 public contract。typed errors 仍然是外部服务交付和主系统 wrapper 测试的重要证据。

## 10. Evidence、data sources 与 tool_result

建议区分三层：

- `tool_result`: 机器可读的领域计算、检索或模型输出。
- `evidence`: 支撑结论的短证据摘要，面向 manager/public-safe summary。
- `data_sources`: 数据表、模型版本、检索来源、快照日期等来源信息。

当前 wrapper 对 `tool_result` 的兼容性最强。外部服务不要只把关键事实放在顶层 `data_sources`，也不要只返回自由文本。专业数字、估值区间、风险指标、证券解析结果等应进入 `tool_result`，并在 `answer` 中给出用户可读解释。

## 11. LLM 与工具边界

如果外部 agent 使用 LLM：

- LLM 可以负责意图理解、字段解析、自然语言解释和报告润色。
- 专业数值、检索命中、估值区间、风险分数、合规结论等必须来自工具、模型、数据库或明确数据源。
- 不要让 LLM 编造数据源、证券代码、估值数值或置信区间。
- 不要返回 chain-of-thought；只返回结论、证据、工具结果和边界说明。

## 12. Repo-side wrapper 规则

主系统 wrapper 应做这些事：

1. 读取 endpoint 配置或默认 endpoint。
2. 构造 `external_agent_request_v0`。
3. 使用 `httpx` 调用 `/v1/agent/invoke`。
4. 设置 timeout。
5. 对 timeout、`httpx.HTTPError`、non-2xx、invalid JSON、response root not object、missing status、unexpected exception 做 fail-soft。
6. 将 response 映射为内部 `AgentOutput`。
7. 对 returned `agent_id` mismatch 追加 warning/evidence。
8. 不把 raw traceback、raw provider response 或 raw external JSON 暴露给 public transcript。

当前三估值 wrapper 的默认 endpoint：

```text
a16_ml_valuation          -> valuation_ml          -> http://127.0.0.1:8102/v1/agent/invoke
a17_traditional_valuation -> valuation_traditional -> http://127.0.0.1:8101/v1/agent/invoke
a18_meta_valuation        -> valuation_meta        -> http://127.0.0.1:8103/v1/agent/invoke
```

## 13. AGENT_TOOLS 注册规则

主系统维护者必须保证：

- wrapper 注册到 `AGENT_TOOLS[main_agent_id]`。
- 注册发生在默认 `_build_agent_tool` / generic stub backfill 之前。
- 如果只更新 `config/agents` metadata，但没有 wrapper 占住 `AGENT_TOOLS[main_agent_id]`，就不能声称真实外部服务已经接入。

对于特殊 runtime role，不按普通外部 HTTP agent 替换：

- `a01_cio_orchestrator`
- `a25_report_center`
- Router / task-router 类 runtime 角色

## 14. Public transcript 与 workflow inspector 边界

外部 agent 的活动不改变 public transcript 规则：

- public transcript 只允许 `user` / `assistant`。
- external agent 不成为前端聊天 speaker。
- workflow inspector 只能展示 safe stage/snapshot/progress/evidence summary。
- 不展示 raw graph messages、raw router output、raw agent JSON、raw fusion payload、raw provider response 或 chain-of-thought。

## 15. Validation ladder

不要把不同层级的验收混在一起：

1. External service self-test  
   验证 `/health`、`/v1/agent/invoke`、typed error、无 secret/traceback 泄露。

2. Schema/model tests  
   验证 request/response 模型和 sample JSON。

3. Wrapper mock success  
   mock HTTP response，验证 request shape 和 `AgentOutput` mapping。

4. Wrapper fail-soft  
   覆盖 timeout、connect error、non-2xx、invalid JSON、response root not object、missing status、unexpected exception。

5. Registry/bootstrap  
   验证 `AGENT_TOOLS[main_agent_id]` 是 external wrapper，而不是 default LLM tool 或 generic stub。

6. Wrapper live smoke  
   真实启动外部服务，证明 wrapper 能通过 HTTP 命中服务。mock test 不能替代 live smoke。

7. Graph-level smoke  
   证明 graph agent node 能调用 wrapper，并把 `AgentOutput` 放入下游可消费结果。

8. Public API smoke  
   证明 public answer 不泄露内部 raw JSON 或多 speaker。

9. Web smoke  
   证明 transcript 与 workflow inspector 符合 public boundary。Web mock 不能替代真实 graph/live wrapper evidence。

10. Docs/changelog evidence  
   记录 endpoint、ids、测试命令、mock-vs-live 边界和 scope boundary。

## 16. 外部开发者交付 checklist

- 服务源码和 README。
- `.env.example`，不包含真实 secret。
- `GET /health` 输出示例。
- `POST /v1/agent/invoke` sample request/response。
- typed error 示例。
- 数据来源、工具来源、模型版本和限制说明。
- self-test 和 schema test 结果。
- external service id，例如 `valuation_ml`。
- 服务 endpoint，例如 `http://127.0.0.1:8102/v1/agent/invoke`。
- 说明是否需要数据库、本地模型、缓存文件或外部 provider。

## 17. 主系统维护者接入 checklist

- 选择 `main_agent_id`，并确认它不是 a01/a25/Router 等特殊角色。
- 确认 `external_agent_id`。
- 审核 `/health` 和 `/v1/agent/invoke` schema。
- 编写或更新 repo-side wrapper。
- 确认 wrapper 使用 `/v1/agent/invoke`，不是领域 endpoint 或 `/invoke`。
- 注册到 `AGENT_TOOLS[main_agent_id]`，且早于默认回填。
- 添加 wrapper mock success 与 fail-soft tests。
- 添加或更新 registry/bootstrap tests。
- 明确 mock、live smoke、graph smoke、public API smoke、Web smoke 的证据层级。
- 更新 docs 和 changelog。

## 18. Scaffold 使用方式

本目录是最小 FastAPI 服务脚手架。它提供：

- `GET /health`
- `POST /v1/agent/invoke`
- `external_agent_health_v0`
- `external_agent_request_v0`
- `external_agent_response_v0`
- typed errors
- deterministic `ok`、`needs_clarification`、`error` paths

它只是服务端样板：

- 没有注册进 `AGENT_TOOLS`。
- 不修改 `config/agents`。
- 不参与默认 graph runtime。
- 不构成 live graph/Web E2E 证据。

运行命令和 sample JSON 以 scaffold README 为准。

## 19. 三估值 agent 参考案例

当前三估值 agent 是参考实现兼 runtime-connected 外部 wrapper 案例：

- `a16_ml_valuation -> valuation_ml`
- `a17_traditional_valuation -> valuation_traditional`
- `a18_meta_valuation -> valuation_meta`

它们说明了当前主系统的兼容边界：

- 主系统 id 与外部服务 id 分离。
- wrapper 发送 compact request。
- 外部服务可以有 `/v1/valuation/invoke`，但主系统 wrapper 使用 `/v1/agent/invoke`。
- 三估值服务 response 可比 target rich schema 更窄，wrapper 主要通过 `tool_result`、`answer/native_answer`、`warnings/errors` 做映射。

## 20. 常见误区

- 误区：只加 metadata 就算接入。  
  事实：必须注册 repo-side wrapper 到 `AGENT_TOOLS[main_agent_id]`。

- 误区：外部服务直接返回 `AgentOutput` 就是标准。  
  事实：第三方 external-agent 标准是 `external_agent_response_v0`，由 repo-side wrapper 映射为 `AgentOutput`。

- 误区：`/v1/valuation/invoke` 可以替代 `/v1/agent/invoke`。  
  事实：领域 endpoint 只能辅助调试，主系统标准入口是 `/v1/agent/invoke`。

- 误区：`/invoke` 是第三方 external-agent 标准。  
  事实：`/invoke` 只属于内部 private/simple replacement pattern。

- 误区：当前 wrapper 已严格校验完整 response schema。  
  事实：当前 wrapper 是兼容型弱校验，主要校验 HTTP/JSON/root/status 并 fail-soft。

- 误区：顶层 `key_points/evidence/data_sources` 当前会被完整消费。  
  事实：它们是推荐 rich fields；当前三估值 wrapper 主要通过 `tool_result` 和答案字段提取摘要。

- 误区：mock wrapper test 等于 live graph/Web E2E。  
  事实：mock、live wrapper、graph、public API、Web 是不同证据层级。

- 误区：外部 agent 会在聊天里单独发言。  
  事实：public transcript 仍只有 `user` / `assistant`。
