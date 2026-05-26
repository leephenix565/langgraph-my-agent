# External Agent Integration Protocol Reference

外部开发者第一次接入时，请先读 [EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md](EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md)。本文只保留协议参考、schema 约定、wrapper acceptance checklist 和当前 wrapper compatibility boundary，不再重复 step-by-step 教程。

## 1. Scope

本标准适用于普通功能型外部 HTTP agent，例如估值、风控、行业分析、检索、文档解析、合规、组合优化等任务执行式 agent。

本标准不适用于普通外部 HTTP 替换的特殊 runtime 角色：

- `a01_cio_orchestrator`
- `a25_report_center`
- Router / task-router 类角色

外部 agent 不依赖 LangGraph raw `State`、raw `state["messages"]`、raw router output、raw manager assignment、raw graph event 或 chain-of-thought。

## 2. Runtime Integration Boundary

当前主系统真实链路：

```text
Router
-> manager_broadcast
-> _build_agent_node(main_agent_id)
-> AGENT_TOOLS[main_agent_id]
-> await tool.ainvoke(agent_input)
-> repo-side HTTP wrapper
-> POST /v1/agent/invoke
-> external_agent_response_v0
-> AgentOutput
-> manager_summary / final_emit
-> public-safe assistant answer
```

`AGENT_TOOLS[main_agent_id]` 是执行真源。metadata-only 不构成 runtime 接入成功。

## 3. ID Namespace

| Field | Example | Owner | Meaning |
|---|---|---|---|
| `main_agent_id` | `a16_ml_valuation` | `langgraph-my-agent` | `AGENT_TOOLS` key and catalog/runtime id |
| `external_agent_id` / response `agent_id` | `valuation_ml` | external service | service id returned by `/health` and `/v1/agent/invoke` |

Current valuation mappings:

```text
a16_ml_valuation          -> valuation_ml
a17_traditional_valuation -> valuation_traditional
a18_meta_valuation        -> valuation_meta
```

`health.agent_id` and response `agent_id` are the external service id, not the main-system `AGENT_TOOLS` key. The repo-side wrapper owns the mapping.

## 4. Standard Endpoints

Required:

```text
GET  /health
POST /v1/agent/invoke
```

Allowed domain-specific endpoint:

```text
POST /v1/valuation/invoke
```

Domain endpoints are optional self-test or internal reuse surfaces. They do not replace `POST /v1/agent/invoke`.

`POST /invoke` and `GET /healthz` are not part of this standard. If they appear in [../../docs/AGENT_REPLACEMENT_GUIDE.md](../../docs/AGENT_REPLACEMENT_GUIDE.md), they refer to a private/simple replacement pattern for maintainers, not to third-party external-agent integration.

## 5. `external_agent_health_v0`

Purpose: service readiness and operator/self-test evidence. Current valuation wrappers do not parse `/health` at invoke time; health is not part of the current live wrapper parser boundary.

Recommended schema:

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

Field requirements:

| Field | Required | Notes |
|---|---|---|
| `schema_version` | recommended | `external_agent_health_v0` |
| `status` | yes | `ok`, `degraded`, or `error` |
| `agent_id` | yes | external service id, for example `valuation_ml` |
| `agent_name` | recommended | human-readable name |
| `version` | recommended | service version |
| `capabilities` | recommended | stable capability tags |
| `input_modes` | recommended | supported input modes |
| `output_modes` | recommended | supported response protocols |
| `llm_configured` | recommended | whether LLM dependency is configured |
| `tools_configured` | recommended | whether tools/models/databases are configured |
| `data_ready` | recommended | whether local data/cache/model artifacts are ready |
| `max_concurrency` | optional | recommended concurrency limit |
| `timeout_seconds` | optional | recommended caller timeout |
| `warnings` | optional | non-blocking readiness warnings |

Health responses must not contain API keys, tokens, database passwords, raw traceback, private user data, embedding vectors, provider raw responses, or chain-of-thought.

## 6. `external_agent_request_v0`

Target request shape:

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

Field requirements:

| Field | Required | Notes |
|---|---|---|
| `schema_version` | yes | `external_agent_request_v0` |
| `request_id` | yes | caller trace id |
| `agent_id` | recommended | external service id |
| `question` | yes | user question or compiled subtask question |
| `language` | recommended | for example `zh-CN`, `zh`, `en-US`, `en` |
| `subtask` | optional | assigned subtask |
| `shared_context` | optional | public-safe shared context |
| `history` | optional | short public-safe history; not raw LangGraph state |
| `router_plan_summary` | optional | safe summary object or string |
| `options` | optional | timeout, answer mode, maximum items, domain flags |

Current wrapper compatibility boundary:

Current three-valuation wrappers send compact payloads with `schema_version`, `request_id`, `question`, `language`, nested `context`, and `options`. The nested `context` carries `main_agent_id`, `external_agent_id`, `subtask`, `shared_context_summary`, and `router_plan_summary`. External services intended for the current runtime should accept both target top-level fields and compact `context/options` payloads.

## 7. `external_agent_response_v0`

Target response shape:

```json
{
  "schema_version": "external_agent_response_v0",
  "request_id": "req_001",
  "agent_id": "valuation_ml",
  "status": "ok",
  "question": "请评估这家公司是否低估。",
  "parsed_request": {},
  "tool_result": {},
  "native_answer": "工具原生答案",
  "answer": "用户可读答案",
  "answer_mode": "structured",
  "confidence": 0.75,
  "key_points": ["核心结论"],
  "evidence": [{"source": "model", "summary": "证据摘要"}],
  "data_sources": [{"name": "valuation_db", "version": "2026-05-21"}],
  "warnings": [],
  "errors": []
}
```

Field requirements:

| Field | Required | Notes |
|---|---|---|
| `schema_version` | yes | `external_agent_response_v0` |
| `request_id` | yes | echo request id |
| `agent_id` | yes | external service id |
| `status` | yes | `ok`, `partial`, `needs_clarification`, `error` |
| `question` | recommended | original or compiled question |
| `parsed_request` | optional | parser output |
| `tool_result` | yes | structured business result |
| `native_answer` | optional | native template/tool answer |
| `answer` | yes | user-readable answer |
| `answer_mode` | recommended | `structured`, `template_only`, `llm_enhanced`, etc. |
| `confidence` | recommended | numeric 0..1 when available |
| `key_points` | recommended | rich target field |
| `evidence` | recommended | rich target field |
| `data_sources` | recommended | rich target field |
| `warnings` | yes | non-blocking warnings |
| `errors` | yes | typed errors |

Current wrapper compatibility boundary:

- Current wrappers primarily read `status`, `answer` / `native_answer`, `tool_result`, `warnings`, `errors`, and confidence fallback sources.
- Current wrappers summarize selected `tool_result` fields into `AgentOutput.key_points` and `AgentOutput.evidence`.
- Current wrappers do not strictly validate full `schema_version`, `request_id`, typed error object schema, or full `tool_result` schema.
- Current wrappers do not fully consume top-level `key_points`, `evidence`, or `data_sources`. Treat those as recommended rich fields and also place important evidence in `tool_result` or answer text until wrapper behavior is upgraded.

## 8. Typed Error Schema

Recommended typed error object:

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

Typed errors should be safe to log and summarize. Do not include raw traceback, raw provider response, secret values, user-private data, or chain-of-thought.

## 9. Data Source Schema

Recommended data source object:

```json
{
  "name": "valuation_snapshot",
  "version": "2026-05-21",
  "snapshot_date": "2026-05-21",
  "description": "Local valuation feature snapshot",
  "url": null
}
```

For current wrapper compatibility, key data-source facts should also appear in `tool_result` or answer/evidence text, not only in top-level `data_sources`.

## 10. Wrapper Acceptance Checklist

The repo-side wrapper should:

- Map `main_agent_id` to `external_agent_id`.
- Read endpoint config or use a documented default.
- Send `POST /v1/agent/invoke`.
- Build `external_agent_request_v0`.
- Use public-safe compact context, not raw LangGraph state.
- Set timeout.
- Fail soft on timeout, `httpx.HTTPError`, non-2xx, invalid JSON, response root not object, missing status, and unexpected exception.
- Map response to `AgentOutput`.
- Add warning/evidence on returned `agent_id` mismatch.
- Register into `AGENT_TOOLS[main_agent_id]` before default `_build_agent_tool` / generic stub backfill.
- Avoid exposing raw external response to public transcript.

Do not document current wrapper behavior as stricter than it is: current wrappers are compatibility wrappers, not full `external_agent_response_v0` validators.

## 11. Current Reference Implementations

The three valuation agents are the current reference runtime-connected examples:

```text
a16_ml_valuation          -> valuation_ml          -> http://127.0.0.1:8102/v1/agent/invoke
a17_traditional_valuation -> valuation_traditional -> http://127.0.0.1:8101/v1/agent/invoke
a18_meta_valuation        -> valuation_meta        -> http://127.0.0.1:8103/v1/agent/invoke
```

Their service responses may be narrower than the richer target schema. The repo-side wrappers keep current runtime compatibility by extracting from `tool_result`, answer fields, warnings, errors, and confidence fallbacks.

## 12. Acceptance Evidence Levels

- Scaffold tests prove the example service contract only.
- Wrapper mock tests prove wrapper request/mapping/fail-soft behavior with mocked HTTP.
- Registry/bootstrap tests prove `AGENT_TOOLS[main_agent_id]` is occupied by wrapper code.
- Wrapper live smoke proves HTTP connectivity to a running service.
- Graph smoke proves graph agent node consumes wrapper output.
- Public API/Web smoke proves public-safe projection and no raw internal leakage.

Do not call a mock wrapper test or scaffold self-test a live graph/Web E2E pass.
