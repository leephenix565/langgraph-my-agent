# AI Coding Handoff / 给 Codex 与 Claude Code 的外部智能体开发说明

> 放置位置建议：`examples/external_agent_scaffold/AI_CODING_HANDOFF.md`  
> 读者：外部独立智能体开发者、Codex、Claude Code、主系统维护者  
> 目标：让开发者或编程助手读完本目录后，能基于 scaffold 开发出一个可被 `langgraph-my-agent` repo-side wrapper 接入的外部 HTTP agent 服务。

---

## 0. 先读哪些文件

请按下面顺序阅读本目录：

1. `README.md`  
   了解 scaffold 目录、启动方式、测试方式、sample request/response。

2. `EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md`  
   主入口。理解外部 agent 要实现什么、哪些边界不能碰、如何交付。

3. `EXTERNAL_AGENT_INTEGRATION_STANDARD.md`  
   协议参考。查 health/request/response/typed error/data source 字段。

4. `AI_CODING_HANDOFF.md`  
   当前文件。给 Codex / Claude Code 使用的执行说明、提示词和验收清单。

如果你是主系统维护者，还需要额外阅读仓库根目录下的：

- `docs/AGENT_REPLACEMENT_GUIDE.md`
- `docs/AGENT_CATALOG_V2_RUNBOOK.md`
- `docs/INDEX.md`
- `docs/CHANGELOG.md`

`AGENT_REPLACEMENT_GUIDE.md` 不是第三方外部 agent 标准入口，它只用于主系统内部替换已有功能型 agent。

---

## 1. 一句话目标

你要开发的是一个独立 HTTP/FastAPI agent 服务。它至少实现：

```text
GET  /health
POST /v1/agent/invoke
```

它返回 `external_agent_health_v0`、`external_agent_request_v0`、`external_agent_response_v0` 和 typed errors。主系统维护者会再写 repo-side wrapper，把你的服务注册到：

```text
AGENT_TOOLS[main_agent_id]
```

外部 agent 不直接成为前端聊天 speaker，也不直接写 public transcript。最终用户仍只看到 `user` / `assistant` 两种角色。

---

## 2. 当前接入链路

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

关键边界：

- `AGENT_TOOLS[main_agent_id]` 是执行真源。
- `config/agents` metadata 不是执行真源。
- 外部服务不能要求 raw LangGraph State、raw router output、raw graph messages 或 chain-of-thought。
- 外部服务不能返回 secrets、raw traceback、provider raw response 或 reasoning_content。
- 领域 endpoint，例如 `/v1/valuation/invoke`，只能作为自测或内部复用入口，不能替代 `/v1/agent/invoke`。

---

## 3. 开发者需要改哪些文件

通常从本 scaffold 复制一份目录，然后修改这些文件：

```text
service.py
schemas.py
errors.py
.env.example
sample_requests/health.expected.json
sample_requests/invoke.request.json
sample_requests/invoke.response.json
tests/test_service_contract.py
README.md
```

建议不要一开始改协议字段。优先保持 `schemas.py` 中的协议模型稳定，只把业务逻辑、agent id、agent name、capabilities、tool_result 和 data_sources 换成你的领域实现。

---

## 4. 外部服务最低实现要求

### 4.1 `GET /health`

必须返回可公开、安全、无 secret 的健康信息。最低应包含：

```json
{
  "schema_version": "external_agent_health_v0",
  "status": "ok",
  "agent_id": "your_external_agent_id",
  "agent_name": "Your External Agent",
  "version": "0.1.0",
  "capabilities": ["your_capability"],
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

`agent_id` 是外部服务自己的 id，例如 `valuation_ml`，不是主系统 id，例如 `a16_ml_valuation`。

### 4.2 `POST /v1/agent/invoke`

必须接受完整 request，也要兼容当前主系统 wrapper 的 compact request：

```json
{
  "schema_version": "external_agent_request_v0",
  "request_id": "req_001",
  "question": "用户问题",
  "language": "zh-CN",
  "context": {
    "main_agent_id": "a16_ml_valuation",
    "external_agent_id": "valuation_ml",
    "subtask": "子任务",
    "shared_context_summary": {},
    "router_plan_summary": "Router plan summary"
  },
  "options": {
    "timeout_seconds": 30,
    "external_agent_id": "valuation_ml"
  }
}
```

最低要求：即使只有 `question`，也能返回结构化 `ok`、`needs_clarification` 或 `error`。

### 4.3 Response

最低可运行 response：

```json
{
  "schema_version": "external_agent_response_v0",
  "request_id": "req_001",
  "agent_id": "your_external_agent_id",
  "status": "ok",
  "question": "用户问题",
  "tool_result": {},
  "native_answer": "工具原生答案",
  "answer": "用户可读答案",
  "warnings": [],
  "errors": []
}
```

推荐同时返回：

```json
{
  "confidence": 0.75,
  "key_points": ["核心结论"],
  "evidence": [{"source": "tool", "summary": "证据摘要"}],
  "data_sources": [{"name": "dataset", "version": "2026-05-21"}]
}
```

当前主系统 wrapper 对 `tool_result`、`answer/native_answer`、`warnings/errors` 兼容性最强。关键业务数字和证据不要只放在顶层 rich fields，也要进入 `tool_result` 或 `answer`。

---

## 5. 业务逻辑实现规则

如果你的 agent 使用 LLM：

- LLM 可以理解问题、抽取字段、解释工具结果。
- 专业数字、估值区间、风险分数、合规结论、检索命中必须来自工具、模型、数据库或明确数据源。
- 不要让 LLM 编造证券代码、估值数值、置信区间、数据来源。
- 不返回 chain-of-thought，只返回结论、证据、工具结果和边界说明。

如果业务实体有歧义，例如公司名、股票代码、文档 id、规则编号，请返回：

```text
status = needs_clarification
```

并在 `errors` 或 `answer` 中给出用户需要补充的信息。

---

## 6. 编程助手执行流程

Codex / Claude Code 应按这个顺序工作：

1. 审计当前 scaffold 文件，不要先改。
2. 明确外部 agent 的领域、`external_agent_id`、服务名、能力标签、依赖项。
3. 修改 service/schema/sample/tests。
4. 保持 endpoint 为 `GET /health` 和 `POST /v1/agent/invoke`。
5. 跑 scaffold contract tests。
6. 启动服务并用 sample request 做本地 smoke。
7. 输出变更摘要、测试结果、已知限制和交付清单。

禁止编程助手：

- 修改主系统 `src/react_agent/*`，除非这是主系统维护者的 wrapper 接入任务。
- 把 `/invoke` 当成第三方标准入口。
- 把 `/healthz` 当成第三方标准入口。
- 返回 raw traceback、secret、provider raw response 或 chain-of-thought。
- 把 scaffold 存在误称为已经注册进 `AGENT_TOOLS`。
- 把 mock test 说成 live graph/Web E2E。

---

## 7. 给 Codex / Claude Code 的开发提示词

把下面提示词发给编程助手，用来把 scaffold 改成你的业务 agent。

```text
你是我的外部智能体服务开发助手。请先审计当前目录，再按最小改动实现。

目标：基于 examples/external_agent_scaffold 开发一个独立 FastAPI external agent 服务。

必须先阅读：
- README.md
- EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md
- EXTERNAL_AGENT_INTEGRATION_STANDARD.md
- AI_CODING_HANDOFF.md
- service.py
- schemas.py
- errors.py
- tests/test_service_contract.py
- sample_requests/*.json

非协商约束：
- 只开发外部服务，不修改主系统 runtime。
- 保留标准 endpoint：GET /health，POST /v1/agent/invoke。
- 不使用 /invoke 或 /healthz 作为第三方标准入口。
- 不要求 raw LangGraph State、raw router output、raw graph messages 或 chain-of-thought。
- 不返回 secrets、raw traceback、provider raw response 或 reasoning_content。
- 业务数字必须来自工具、数据库、模型、检索结果或明确数据源，不能由 LLM 编造。
- response 必须是 external_agent_response_v0，不是主系统 AgentOutput。AgentOutput 映射由 repo-side wrapper 负责。

请先输出审计摘要：
A) 当前 scaffold 文件清单
B) 当前协议模型
C) 需要替换的 agent_id、agent_name、capabilities、业务逻辑点
D) 最小改动计划

然后实现：
1. 更新 health 信息。
2. 更新 invoke 业务逻辑。
3. 更新 sample request/response。
4. 更新 README 的启动、自测、交付说明。
5. 更新或补充 tests，覆盖 ok、needs_clarification、error、no secret/no traceback。

验证命令：
- python -m pytest tests -q -p no:cacheprovider
- python -m uvicorn service:app --host 127.0.0.1 --port 8100
- curl 或 PowerShell 调用 GET /health 和 POST /v1/agent/invoke

最终输出：
A) 修改文件
B) 每个文件改了什么
C) 测试命令与结果
D) sample health 输出
E) sample invoke 输出
F) 已知限制
G) 外部开发者交付 checklist

不要输出 chain-of-thought。不要输出真实 secret。
```

---

## 8. 主系统维护者接入提示词

当外部服务已经开发完成后，主系统维护者可用下面提示词让 Codex 写 repo-side wrapper。

```text
你是 langgraph-my-agent 主系统接入助手。请先审计，再实现最小 wrapper 接入。

目标：把一个已经完成的外部 HTTP agent 服务接入主系统 AGENT_TOOLS[main_agent_id]。

已知外部服务信息：
- main_agent_id: <例如 a16_ml_valuation 或新功能型 agent id>
- external_agent_id: <例如 valuation_ml>
- endpoint: <例如 http://127.0.0.1:8102/v1/agent/invoke>
- health endpoint: <例如 http://127.0.0.1:8102/health>
- timeout_seconds: <例如 30 或 90>

非协商约束：
- 不修改 Router prompt、router_parse.py、State schema、public API schema、frontend。
- 不把外部 agent 变成 public transcript speaker。
- 不绕过 AGENT_TOOLS。
- wrapper 注册必须早于默认 _build_agent_tool / generic stub backfill。
- wrapper 必须 fail-soft，覆盖 timeout、connect error、non-2xx、invalid JSON、missing status、agent_id mismatch。
- wrapper 调用 /v1/agent/invoke，不调用领域 endpoint 作为标准入口。

请先审计：
A) 现有 bootstrap 注册链
B) AGENT_TOOLS 执行真源
C) 类似 wrapper 参考实现
D) 需要新增/修改的 tests 和 docs/changelog

实现最小改动：
1. 新增或更新 wrapper module。
2. 在 bootstrap 阶段注册到 AGENT_TOOLS[main_agent_id]。
3. 添加 wrapper mock success test。
4. 添加 fail-soft tests。
5. 添加 registry/bootstrap test，证明不是 default LLM tool 或 generic stub。
6. 更新 docs/runbook/changelog，记录 endpoint、id 映射、mock/live 边界。

最终输出：
A) 审计证据
B) 修改文件
C) 验证命令与结果
D) wrapper request/response 映射摘要
E) mock/live/graph/public/Web 证据边界
F) changelog entry
```

---

## 9. 自测命令

在 scaffold 目录内：

```bash
python -m pytest tests -q -p no:cacheprovider
python -m uvicorn service:app --host 127.0.0.1 --port 8100
```

另开终端：

```bash
curl http://127.0.0.1:8100/health
curl -X POST http://127.0.0.1:8100/v1/agent/invoke \
  -H "Content-Type: application/json" \
  -d @sample_requests/invoke.request.json
```

如果使用 PowerShell：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8100/health"

$body = Get-Content .\sample_requests\invoke.request.json -Raw
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8100/v1/agent/invoke" `
  -ContentType "application/json" `
  -Body $body
```

---

## 10. 最终交付 checklist

外部开发者交付：

```text
[ ] 服务源码
[ ] README.md
[ ] .env.example，不含真实 key/token/password
[ ] GET /health 示例响应
[ ] POST /v1/agent/invoke sample request
[ ] POST /v1/agent/invoke sample response
[ ] ok 路径测试
[ ] needs_clarification 路径测试
[ ] error 路径测试
[ ] typed error 示例
[ ] tool_result 字段说明
[ ] data_sources / evidence / warnings 字段说明
[ ] LLM 与工具/数据库/模型边界说明
[ ] 自测命令和结果
[ ] external_agent_id
[ ] 本地 endpoint 或部署 endpoint
[ ] timeout_seconds
[ ] 依赖项和启动命令
```

主系统维护者交付：

```text
[ ] main_agent_id
[ ] external_agent_id
[ ] repo-side wrapper
[ ] AGENT_TOOLS[main_agent_id] 注册
[ ] wrapper mock success test
[ ] wrapper fail-soft test
[ ] registry/bootstrap test
[ ] live wrapper smoke，如具备服务环境
[ ] graph-level smoke，如具备 provider/search credentials
[ ] public API / Web smoke，如需要
[ ] docs / runbook / changelog 更新
```

---

## 11. 判断是否完成

满足以下条件，可以认为外部 agent 服务开发完成：

- `GET /health` 返回安全、结构化、无 secret 的 health。
- `POST /v1/agent/invoke` 能返回 `ok`、`needs_clarification`、`error` 中至少三类可测试路径。
- response 是 `external_agent_response_v0`。
- 业务核心结果进入 `tool_result`。
- 用户可读解释进入 `answer` 或 `native_answer`。
- typed errors 不泄露 traceback。
- tests 通过。
- sample request/response 与实际服务一致。
- README 说明启动、测试、依赖、限制和交付物。

满足以下条件，才能认为已经接入主系统：

- 主系统 wrapper 已注册到 `AGENT_TOOLS[main_agent_id]`。
- wrapper 不是 default LLM tool，也不是 generic stub。
- wrapper mock success/fail-soft tests 通过。
- live wrapper smoke 或明确记录未跑 live 的原因。
- graph/public/Web 证据按环境分层记录，不能把 mock test 夸大成 live E2E。
