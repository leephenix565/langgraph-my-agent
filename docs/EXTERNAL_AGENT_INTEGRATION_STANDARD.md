# 外部 Agent 接入标准说明

本文档定义第三方、同学、其他团队开发的外部 agent，如何按统一协议接入 `langgraph-my-agent` 多智能体系统。

目标不是要求所有 agent 都按同一种业务逻辑开发，而是要求它们暴露一致、可验证、可编排、可降级的服务接口，使主系统 Router 可以选择调用它们，主系统汇总/融合 agent 可以消费它们的结果，同时不破坏当前 `langgraph-my-agent` 的 Router、graph、State、public API、frontend transcript 和单 assistant persona 边界。

## 1. 适用范围

本标准适用于普通功能型外部 agent，例如：

- 宏观分析 agent
- 行业分析 agent
- 个股情绪 agent
- 估值 agent
- 风险管理 agent
- 合规审查 agent
- 组合优化 agent
- 研报综合 agent
- 数据检索 / 文档解析 / 专业计算 agent
- 其他一问一答式或任务执行式分析 agent

本标准不适用于直接替换当前主系统的特殊 runtime 角色：

- `a01_cio_orchestrator`
- `a02_task_router`
- `a25_report_center`

这些角色在当前主系统中承载特殊编排、路由或最终报告语义，不应被普通外部 HTTP agent 直接替换。

## 2. 总体接入原则

外部 agent 必须遵守以下原则：

1. 外部 agent 可以独立实现、独立部署、独立维护。
2. 外部 agent 不需要理解 LangGraph 内部 `State`。
3. 外部 agent 不直接写入主系统 public transcript。
4. 外部 agent 不直接暴露给前端用户作为独立聊天 speaker。
5. 主系统 public transcript 仍保持单一 assistant persona。
6. 主系统 Router 决定是否调用某个 agent。
7. 主系统 manager / fusion / report agent 决定最终如何采纳 agent 结果。
8. 外部 agent 必须返回结构化结果，不能只返回一段自由文本。
9. 外部 agent 必须返回 typed errors，不能把裸 traceback 返回给主系统或用户。
10. 外部 agent 必须显式说明数据来源、工具来源、模型来源、关键假设和限制。
11. 如果 agent 内部使用 LLM，LLM 只能负责理解、编排、解释；专业数字、结论证据和工具结果必须来自确定性工具或明确数据源。
12. 外部 agent 默认应该是 fail-soft：自身失败时返回 typed error，而不是让主系统 graph 崩溃。

推荐接入方式：

```text
外部 agent 独立 FastAPI / HTTP 服务
-> langgraph-my-agent 中实现一个 httpx wrapper tool
-> wrapper 注册到 AGENT_TOOLS[agent_id]
-> graph 仍通过原有 agent node 调用 tool.ainvoke(...)
-> wrapper 把外部响应映射为当前 AgentOutput
```

## 3. 当前主系统真实调用边界

当前 `langgraph-my-agent` 对普通功能 agent 的主线调用形态可以理解为：

```text
Router
-> manager_broadcast
-> _build_agent_node(agent_id)
-> AGENT_TOOLS[agent_id]
-> await tool.ainvoke(agent_input)
-> AgentOutput
-> manager_summary / downstream synthesis
```

因此，外部 agent 真正接入成功的判断标准不是“前端 `/agents` 页面能看到 metadata”，而是：

```text
AGENT_TOOLS[agent_id] 已指向外部 agent wrapper
graph 调用该 agent 时实际命中了外部 HTTP 服务
外部 HTTP 响应可稳定映射为当前 AgentOutput
主系统下游 summary/fusion 能消费该 AgentOutput
```

外部 agent 不应该依赖这些内部对象：

- `state["messages"]`
- raw router output
- raw manager assignment
- raw graph event
- raw chain-of-thought
- public adapter 内部结构
- frontend workflow snapshot 内部字段

外部 agent 只能依赖标准 HTTP request 中明确传入的字段。

## 4. 两层协议

外部 agent 接入分为两层：

1. 外部服务协议：第三方 agent 必须暴露什么 HTTP endpoint、接收什么 request、返回什么 response。
2. 主系统 wrapper 协议：`langgraph-my-agent` 如何把外部 HTTP 服务包装成 `AGENT_TOOLS[agent_id]` 可调用工具。

外部开发者主要负责第一层。

`langgraph-my-agent` 维护者负责第二层。

## 5. 外部服务必须提供的 endpoint

每个外部 agent 服务至少提供：

```text
GET  /health
POST /v1/agent/invoke
```

如果是领域专用 agent，可以额外提供领域 endpoint，例如估值类：

```text
POST /v1/valuation/invoke
```

但所有 agent 都必须支持通用 endpoint：

```text
POST /v1/agent/invoke
```

原因是主系统集成不能为每个业务领域维护完全不同的调用协议。领域 endpoint 可以方便人工调试和领域系统复用，但主系统默认优先对接通用 endpoint。

## 6. Health 协议

`GET /health` 用于主系统或人工检查该外部 agent 是否可用。

标准响应：

```json
{
  "schema_version": "external_agent_health_v0",
  "status": "ok",
  "agent_id": "valuation_traditional",
  "agent_name": "传统估值智能体",
  "version": "0.1.0",
  "capabilities": [
    "natural_language_parse",
    "security_resolve",
    "traditional_valuation"
  ],
  "input_modes": ["natural_language", "structured_json"],
  "output_modes": ["structured_json", "natural_language_answer"],
  "llm_configured": true,
  "tools_configured": true,
  "data_ready": true,
  "max_concurrency": 1,
  "timeout_seconds": 60,
  "warnings": []
}
```

字段要求：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `schema_version` | 是 | 固定为 `external_agent_health_v0` |
| `status` | 是 | `ok`、`degraded`、`error` |
| `agent_id` | 是 | 全局稳定 id，必须和主系统注册 id 一致 |
| `agent_name` | 是 | 人类可读名称 |
| `version` | 是 | 外部 agent 服务版本 |
| `capabilities` | 是 | 能力标签，供 Router/catalog 参考 |
| `input_modes` | 建议 | 支持的输入模式 |
| `output_modes` | 建议 | 支持的输出模式 |
| `llm_configured` | 建议 | 是否配置了 LLM |
| `tools_configured` | 建议 | 核心业务工具是否配置 |
| `data_ready` | 建议 | 本地数据、模型、cache 是否可用 |
| `max_concurrency` | 建议 | 建议并发上限 |
| `timeout_seconds` | 建议 | 建议调用超时 |
| `warnings` | 建议 | 非阻断风险 |

Health 禁止返回：

- API key
- token
- 数据库密码
- raw traceback
- 用户隐私数据
- embedding 向量或大段私有缓存内容

## 7. 通用调用请求协议

主系统调用外部 agent 时使用：

```text
POST /v1/agent/invoke
```

标准 request：

```json
{
  "schema_version": "external_agent_request_v0",
  "request_id": "uuid",
  "agent_id": "valuation_traditional",
  "question": "帮我看看中国能建现在是不是低估？",
  "language": "zh",
  "subtask": "从传统估值视角判断中国能建是否低估",
  "shared_context": {},
  "history": [],
  "router_plan_summary": "Router 计划摘要",
  "options": {
    "answer_mode": "auto",
    "timeout_seconds": 60,
    "max_items": 3
  }
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `schema_version` | 是 | 固定为 `external_agent_request_v0` |
| `request_id` | 是 | 调用追踪 id |
| `agent_id` | 建议 | 目标 agent id |
| `question` | 是 | 用户原始问题或主系统编译后的任务问题 |
| `language` | 建议 | `zh`、`en`、`auto` |
| `subtask` | 建议 | manager 分配给该 agent 的子任务 |
| `shared_context` | 可选 | 上游可公开共享上下文 |
| `history` | 可选 | 短历史，不是 LangGraph raw state |
| `router_plan_summary` | 可选 | Router 计划摘要 |
| `options` | 可选 | 超时、最大条目数、answer mode 等 |

外部 agent 必须能在只给 `question` 的情况下工作。其他字段是增强信息，不能成为唯一入口。

## 8. 通用调用响应协议

标准 response：

```json
{
  "schema_version": "external_agent_response_v0",
  "request_id": "uuid",
  "agent_id": "valuation_traditional",
  "status": "ok",
  "question": "帮我看看中国能建现在是不是低估？",
  "parsed_request": {},
  "tool_result": {},
  "native_answer": "原工具或模板答案",
  "answer": "给用户看的自然语言解释",
  "answer_mode": "llm_enhanced",
  "confidence": 0.78,
  "key_points": [],
  "evidence": [],
  "data_sources": [],
  "warnings": [],
  "errors": []
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `schema_version` | 是 | 固定为 `external_agent_response_v0` |
| `request_id` | 是 | 必须回传请求 id |
| `agent_id` | 是 | 响应 agent id |
| `status` | 是 | `ok`、`partial`、`needs_clarification`、`error` |
| `question` | 是 | 原问题 |
| `parsed_request` | 建议 | LLM parser 或规则 parser 的结构化结果 |
| `tool_result` | 是 | 业务工具、模型、检索或计算的结构化输出 |
| `native_answer` | 建议 | 原生模板答案或工具自身答案 |
| `answer` | 是 | 用户友好的自然语言回答 |
| `answer_mode` | 是 | `llm_enhanced`、`template_only`、`template_with_note`、`error_explanation` |
| `confidence` | 建议 | 0 到 1 的自评置信度 |
| `key_points` | 建议 | 下游汇总 agent 可消费的要点 |
| `evidence` | 建议 | 支撑证据 |
| `data_sources` | 建议 | 数据来源 |
| `warnings` | 是 | 非阻断风险 |
| `errors` | 是 | typed errors |

### 8.1 `status` 语义

| status | 含义 | 主系统建议 |
| --- | --- | --- |
| `ok` | 完整成功 | 正常用于汇总 |
| `partial` | 部分成功 | 可用于汇总，但必须保留 warning |
| `needs_clarification` | 需要用户补充信息 | 主系统可追问或在最终回答中说明 |
| `error` | 执行失败 | 不应当作有效分析结论 |

### 8.2 `answer_mode` 语义

| answer_mode | 含义 |
| --- | --- |
| `llm_enhanced` | LLM 基于工具结果做了自然语言解释 |
| `template_only` | 没有 LLM 增强，直接返回模板/原生答案 |
| `template_with_note` | 返回模板答案，并附带边界说明 |
| `error_explanation` | 对错误或澄清需求做用户可读解释 |

## 9. Typed Error 协议

禁止把裸 traceback 直接返回给主系统或用户。

标准错误结构：

```json
{
  "error_code": "DATA_NOT_FOUND",
  "error_message": "未能获取该股票的财务数据",
  "stage": "data_loading",
  "recoverable": true,
  "retryable": false,
  "user_action_required": true,
  "suggested_user_action": "请确认股票代码是否正确，或稍后重试。"
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `error_code` | 是 | 稳定错误码 |
| `error_message` | 是 | 可读错误说明 |
| `stage` | 是 | 错误阶段 |
| `recoverable` | 是 | 是否可恢复 |
| `retryable` | 是 | 是否适合自动重试 |
| `user_action_required` | 是 | 是否需要用户补充信息 |
| `suggested_user_action` | 建议 | 下一步建议 |

通用错误码建议：

```text
INVALID_QUESTION
MISSING_REQUIRED_FIELD
MISSING_ENTITY
ENTITY_NOT_FOUND
ENTITY_AMBIGUOUS
TOO_MANY_ITEMS
DATA_NOT_FOUND
DATA_STALE
DATA_SOURCE_UNAVAILABLE
MODEL_NOT_CONFIGURED
MODEL_LOAD_FAILED
MODEL_INFERENCE_FAILED
TOOL_NOT_CONFIGURED
TOOL_EXECUTION_FAILED
LLM_NOT_CONFIGURED
LLM_PARSE_FAILED
LLM_ANSWER_FAILED
TIMEOUT
RATE_LIMITED
UNAUTHORIZED
RESULT_SCHEMA_INVALID
UNSUPPORTED_REQUEST
```

领域 agent 可以增加领域错误码，但必须保持结构不变。

## 10. 数据来源协议

外部 agent 必须显式返回数据来源。建议放在 `data_sources` 或领域 `tool_result.data_source` 中。

通用结构：

```json
{
  "source_type": "api",
  "source_name": "tushare",
  "dataset_name": null,
  "dataset_version": null,
  "as_of": "2026-05-07",
  "cache_hit": true,
  "cache_path": "data/cache/finance_data",
  "freshness": "fresh",
  "warnings": []
}
```

字段建议：

| 字段 | 说明 |
| --- | --- |
| `source_type` | `api`、`cache`、`csv`、`database`、`document`、`model`、`manual` |
| `source_name` | 数据源名称 |
| `dataset_name` | 数据集名称 |
| `dataset_version` | 数据集版本 |
| `as_of` | 数据日期 |
| `cache_hit` | 是否命中缓存 |
| `cache_path` | 本地缓存路径，不能泄露敏感信息 |
| `freshness` | `fresh`、`stale`、`unknown` |
| `warnings` | 数据边界 |

禁止返回：

- API key
- 数据库连接串
- 用户隐私原文
- 大段原始私有文档
- embedding 原始向量

## 11. LLM 与工具边界

如果外部 agent 内部使用 LLM，必须明确边界。

推荐流程：

```text
自然语言输入
-> LLM parser 理解问题
-> resolver / entity parser 解析业务实体
-> request validator 校验
-> deterministic tool / retrieval / model 执行
-> result normalizer 结构化结果
-> native/template answer 生成
-> LLM answerer 解释工具结果
-> response builder 返回结构化 JSON + answer
```

原则：

1. LLM 可以理解用户意图。
2. LLM 可以抽取实体、日期、约束和任务类型。
3. LLM 可以选择或编排工具。
4. LLM 可以解释工具结果。
5. LLM 不应编造专业数字。
6. LLM 不应覆盖 deterministic tool 的核心结论。
7. LLM 不应隐藏工具失败。
8. LLM 不应输出无数据来源的确定性判断。

如果 agent 使用原生 function calling / tools 协议，也必须满足：

```text
LLM 只负责选择工具和填参数
工具返回结果才是事实来源
最终 answer 必须能追溯到 tool_result
```

## 12. Entity Resolver / 业务实体解析要求

凡是涉及业务实体的 agent，都应该有自己的 resolver。

例子：

| Agent 类型 | Resolver 输出 |
| --- | --- |
| 估值 agent | 股票代码、公司名、市场 |
| 合规 agent | 规则编号、业务场景、客户类型 |
| 文档 agent | 文件 id、段落 id、页码 |
| 行业 agent | 行业 taxonomy id、产业链节点 |
| 风险 agent | 资产 id、风险指标、时间窗口 |

Resolver 必须返回：

```json
{
  "status": "resolved",
  "items": [
    {
      "query": "中国能建",
      "status": "resolved",
      "entity_id": "601868.SH",
      "name": "中国能建",
      "confidence": 0.99,
      "match_type": "exact"
    }
  ]
}
```

如果存在歧义：

```json
{
  "status": "needs_clarification",
  "items": [
    {
      "query": "平安",
      "status": "ambiguous",
      "candidates": [
        {"entity_id": "000001.SZ", "name": "平安银行"},
        {"entity_id": "601318.SH", "name": "中国平安"}
      ]
    }
  ],
  "clarification_question": "你说的“平安”是平安银行还是中国平安？"
}
```

如果 resolver 失败，不能继续假装执行专业分析。

## 13. 主系统 AgentOutput 映射

当前主系统普通 agent 常用输出可抽象为：

```json
{
  "analysis": "分析正文",
  "key_points": ["要点1", "要点2"],
  "evidence": ["证据1", "证据2"],
  "confidence": 0.78,
  "parse_ok": true
}
```

外部 agent wrapper 推荐映射：

```text
analysis   <- response.answer 或 response.native_answer
key_points <- response.key_points
evidence   <- response.evidence + response.data_sources 摘要
confidence <- response.confidence
parse_ok   <- response.status in ["ok", "partial", "needs_clarification"] 且 response 可解析
```

如果外部 agent 返回领域 schema，例如估值 response，wrapper 仍应压缩成当前主系统可消费的 `AgentOutput`，同时在 evidence 中保留结构化摘要。

## 14. 主系统 Wrapper 要求

`langgraph-my-agent` 内部接入外部 agent 时，应新增 wrapper，而不是让 graph 直接依赖第三方代码。

Wrapper 职责：

1. 从配置读取外部服务 URL。
2. 构造 `external_agent_request_v0`。
3. 使用 httpx 调用 `/v1/agent/invoke`。
4. 设置 timeout。
5. 处理连接失败、超时、非 2xx、schema invalid。
6. 把外部 response 映射为 `AgentOutput`。
7. 只把摘要和结构化 evidence 传给下游。
8. 不把外部服务 raw traceback 暴露给 public transcript。

Wrapper 伪代码：

```python
async def external_agent_tool(agent_input):
    request = {
        "schema_version": "external_agent_request_v0",
        "request_id": make_request_id(),
        "agent_id": AGENT_ID,
        "question": agent_input.question,
        "subtask": agent_input.subtask,
        "shared_context": public_safe_context(agent_input),
        "options": {"timeout_seconds": 60},
    }

    try:
        response = await httpx_client.post(url, json=request, timeout=60)
        response.raise_for_status()
        body = validate_external_response(response.json())
    except Exception as exc:
        return AgentOutput(
            analysis=f"{AGENT_ID} 调用失败，已跳过该外部结果。",
            key_points=[],
            evidence=[],
            confidence=0.0,
            parse_ok=False,
        )

    return AgentOutput(
        analysis=body["answer"] or body.get("native_answer", ""),
        key_points=body.get("key_points", []),
        evidence=body.get("evidence", []) + summarize_sources(body.get("data_sources", [])),
        confidence=body.get("confidence", 0.5),
        parse_ok=body["status"] in {"ok", "partial", "needs_clarification"},
    )
```

## 15. Agent Catalog 注册要求

外部 agent 想接入主系统，必须提供 catalog metadata。

推荐字段：

```json
{
  "agent_id": "valuation_traditional",
  "layer": "L2",
  "team": "valuation",
  "name": "传统估值智能体",
  "description": "基于 DCF/PE/PS 规则树的传统估值分析 agent。",
  "capabilities": [
    "natural_language_parse",
    "security_resolve",
    "traditional_valuation"
  ],
  "input_type": "natural_language_or_structured_json",
  "output_type": "external_agent_response_v0",
  "cost_level": "normal",
  "latency_level": "medium",
  "endpoint": "http://127.0.0.1:8101/v1/agent/invoke",
  "health_endpoint": "http://127.0.0.1:8101/health",
  "timeout_seconds": 60,
  "owner": "external",
  "status": "experimental"
}
```

注意：

- `agent_id` 必须稳定。
- 不要和当前已有 ordinary agent id 冲突。
- 不要使用 `a01_cio_orchestrator`、`a02_task_router`、`a25_report_center` 这类特殊 runtime id。
- `layer` 必须符合主系统层级设计。
- `capabilities` 必须真实，不要写未实现能力。

## 16. 安全与密钥要求

每个外部 agent 可以有自己的 `.env`。

`.env` 可以用于本地压缩包交付，但如果上传 GitHub 必须删除。

`.env.example` 只能放变量名，不能放真实值：

```env
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
TUSHARE_TOKEN=
```

禁止：

- 在源码中硬编码 API key。
- 在 health 中返回 key。
- 在 response 中返回 key。
- 在日志中打印 key。
- 在错误中打印完整 provider request/response。
- 把 `.env` 提交到公开仓库。

允许：

- 每个外部 agent 自己维护独立 `.env`。
- 本地压缩包交付时附带 `.env`，但必须明确只供本地使用。
- `.env.example` 只作为变量说明。

## 17. Timeout / Retry / 并发要求

外部 agent 应声明自身建议超时：

```json
{
  "timeout_seconds": 60,
  "max_concurrency": 1
}
```

主系统 wrapper 应设置硬超时。推荐：

| 类型 | 推荐超时 |
| --- | --- |
| 轻量 parser / 规则 agent | 15-30 秒 |
| 普通 LLM + 工具 agent | 60 秒 |
| 本地模型 / 大文件处理 agent | 120 秒 |
| 外部数据源较慢 agent | 120 秒，但应返回进度或 partial |

重试建议：

- 网络瞬断可重试 1 次。
- 4xx 不自动重试。
- typed `retryable=false` 不重试。
- provider rate limit 不应无限重试。

## 18. 日志与可观测性

外部 agent 应记录内部日志，但不要把敏感信息写入日志。

建议日志字段：

```json
{
  "request_id": "uuid",
  "agent_id": "valuation_traditional",
  "stage": "tool_execution",
  "status": "ok",
  "latency_ms": 1234,
  "error_code": null
}
```

建议阶段：

```text
request_received
llm_parse
entity_resolve
request_validate
tool_execution
result_normalize
llm_answer
response_build
```

禁止日志：

- API key
- 用户隐私全文，除非业务明确允许
- raw traceback 直接返回给用户
- embedding 原始向量

## 19. 领域 endpoint 规范

领域 endpoint 是可选的，主要用于人工调试、领域系统复用、或保留更强类型的业务 schema。

以估值 agent 为例：

```text
POST /v1/valuation/invoke
```

估值请求：

```json
{
  "schema_version": "valuation_agent_request_v0",
  "request_id": "uuid",
  "question": "帮我比较中国能建和中国建筑谁更低估？",
  "language": "zh",
  "securities": [
    {"query": "中国能建"},
    {"query": "中国建筑"}
  ],
  "target_date": null,
  "options": {
    "max_securities": 3,
    "answer_mode": "auto",
    "allow_remote_resolver_refresh": true
  }
}
```

估值响应：

```json
{
  "schema_version": "valuation_agent_response_v0",
  "request_id": "uuid",
  "agent_id": "valuation_traditional",
  "status": "ok",
  "is_multi_security": true,
  "parsed_request": {},
  "security": {},
  "valuation_results": [],
  "template_answers": [],
  "answer": "...",
  "answer_mode": "llm_enhanced",
  "warnings": [],
  "errors": []
}
```

但主系统默认仍建议通过 `/v1/agent/invoke` 调用，除非 wrapper 明确需要领域 schema。

## 20. 多标 / 多实体要求

如果 agent 支持多个实体，必须有上限。

示例：

```text
MAX_SECURITIES=3
```

多实体规则：

1. 超过上限返回 `TOO_MANY_ITEMS`。
2. 每个实体独立标记成功或失败。
3. 允许 `partial`。
4. partial 时必须说明哪些实体失败。
5. 不允许因为一个实体失败就编造整体结论。

partial response 示例：

```json
{
  "status": "partial",
  "success_count": 1,
  "error_count": 1,
  "tool_result": {
    "items": [
      {"entity_id": "601868.SH", "status": "ok"},
      {"entity_id": "601668.SH", "status": "error", "error_code": "DATA_NOT_FOUND"}
    ]
  },
  "warnings": ["部分标的处理失败，结论不完整。"]
}
```

## 21. 输出质量要求

外部 agent 的 `answer` 应该：

1. 回答用户问题。
2. 明确使用的方法视角。
3. 明确数据边界。
4. 明确不确定性。
5. 不输出无法追溯的数字。
6. 不隐藏失败。
7. 不夸大能力。
8. 不把实验性能力说成生产能力。

不合格回答示例：

```text
这个股票一定会上涨，建议买入。
```

合格回答示例：

```text
从传统估值视角看，该公司当前市值处于工具计算的合理区间内，因此不能仅凭该模型判断为明显低估。该结论基于 Tushare 财务数据和 PE/DCF/PS 规则树，不构成买卖建议。
```

## 22. 外部 agent 自测清单

外部开发者交付前至少完成以下自测。

### 22.1 Health

```text
GET /health
```

必须验证：

- HTTP 200
- `status` 是 `ok` 或 `degraded`
- `agent_id` 正确
- 不泄露 secret
- capabilities 真实

### 22.2 最小调用

```text
POST /v1/agent/invoke
```

必须验证：

- 只给 `question` 可以工作
- 返回 `external_agent_response_v0`
- `status` 合法
- `answer` 非空
- `errors` 是 list
- `warnings` 是 list

### 22.3 错误路径

必须至少验证：

- 缺必要实体
- 实体歧义
- 数据缺失
- LLM 不可用
- 工具失败
- 超过最大实体数

### 22.4 Schema 校验

必须验证：

- response 可 JSON 序列化
- typed error 字段完整
- data source 字段存在
- no raw traceback
- no secret

### 22.5 降级

如果 LLM 不可用：

- 不能崩溃
- 应返回 template/native answer 或 typed error
- `answer_mode` 应标记为 `template_only`、`template_with_note` 或 `error_explanation`

## 23. 主系统接入验收清单

主系统维护者接入某个外部 agent 前，应确认：

1. 外部服务可独立运行。
2. `/health` 通过。
3. `/v1/agent/invoke` 通过。
4. response schema 稳定。
5. typed errors 可解析。
6. wrapper 超时和失败降级可用。
7. wrapper 输出可映射为 `AgentOutput`。
8. `AGENT_TOOLS[agent_id]` 注册正确。
9. Router catalog metadata 与真实能力一致。
10. 不修改 public API 暴露内部字段。
11. 不破坏单 assistant transcript。
12. 不把外部 raw logs 暴露给前端。
13. focused integration smoke 通过。

## 24. 标准开发目录建议

外部 agent 推荐目录：

```text
external-agent/
  service.py
  schemas.py
  errors.py
  resolver.py
  llm_parser.py
  llm_answerer.py
  answer_modes.py
  adapters/
    tool_adapter.py
  data/
    cache/
  outputs/
    logs/
  .env
  .env.example
  README.md
  CHANGELOG.md
```

不是所有 agent 都必须完全一样，但必须提供等价能力。

## 25. 估值智能体参考实现

当前本机已有三个估值 agent 作为参考实现：

```text
E:\muti-agent\传统估值智能体
E:\muti-agent\机器学习估值智能体
E:\muti-agent\元学习估值智能体
```

它们的参考接口：

```text
传统估值: http://127.0.0.1:8101
机器学习: http://127.0.0.1:8102
元学习:   http://127.0.0.1:8103
```

它们共同实现：

```text
GET  /health
POST /v1/agent/invoke
POST /v1/valuation/invoke
```

它们的链路是：

```text
自然语言输入
-> LLM parser
-> resolver
-> 原有确定性估值工具
-> template_answer
-> LLM answerer
-> 结构化 JSON + answer
```

注意：这三个估值服务目前是参考实现和后续可接入对象，不等于已经接入 `langgraph-my-agent` runtime。真正 runtime 接入还需要在主系统中实现 wrapper 并注册到 `AGENT_TOOLS`。

## 26. 禁止事项

外部 agent 接入时禁止：

1. 直接修改主系统 Router prompt 来硬塞外部 agent。
2. 直接修改 Router parser 输出 schema。
3. 扩展主系统 `State` 来塞外部 agent 私有字段，除非任务明确批准。
4. 把外部 agent raw response 直接暴露到 public transcript。
5. 把外部 agent 作为独立前端 speaker。
6. 把 secret 写进 `.env.example` 或公开文档。
7. 把实验 smoke 说成生产上线证据。
8. 用 LLM 编造工具没有返回的专业数字。
9. 出错时返回裸 traceback。
10. 绕过 `AGENT_TOOLS` / wrapper 直接让 graph 依赖第三方项目代码。

## 27. 推荐实施顺序

外部 agent 开发者：

```text
1. 梳理原 agent 能力、输入、输出、数据源
2. 定义 schemas.py / errors.py
3. 实现 resolver 或业务实体解析器
4. 实现 tool adapter，封装原有确定性工具
5. 实现 native/template answer
6. 实现 LLM parser / answerer，可降级
7. 实现 FastAPI service
8. 实现 /health 和 /v1/agent/invoke
9. 补 .env.example、README、CHANGELOG
10. 跑自测清单
```

主系统维护者：

```text
1. 审核外部 agent health 和 invoke schema
2. 编写 httpx wrapper
3. 映射 external response -> AgentOutput
4. 注册 AGENT_TOOLS[agent_id]
5. 更新 catalog metadata
6. 跑 focused integration smoke
7. 更新主系统 docs / changelog
```

## 28. 最小合格标准

一个外部 agent 想接入 `langgraph-my-agent`，最低必须满足：

```text
1. 独立可运行
2. GET /health 可用
3. POST /v1/agent/invoke 可用
4. request/response 是 JSON
5. response 有 schema_version
6. response 有 status
7. response 有 answer
8. response 有 typed errors
9. response 有结构化 tool_result 或等价字段
10. 关键数据来源可追溯
11. 不泄露 secret
12. LLM 不编造工具结果
13. 失败时不让主系统崩溃
```

满足这些之后，才可以进入主系统 wrapper 接入阶段。

