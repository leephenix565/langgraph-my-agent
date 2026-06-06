# AI Coding Handoff For Fixed DAG External Agent Adaptation

Package version: `external-agent-scaffold-v2.3-fixed-dag`.

## 1. Purpose

This document is for Codex, Claude Code, or another coding agent that receives
this scaffold package together with a developer's existing agent project.

The coding agent's task is to adapt that developer project into a fixed DAG
external service that can later be reviewed by the main-system maintainers. The
goal is to preserve the developer's business capability while wrapping it with
the fixed DAG external service protocol.

This document is not permission to modify the `langgraph-my-agent` active
runtime. It is not runtime binding approval. It is not live readiness evidence.
It is a sample/local contract handoff package.

v2.3 restores the broader domain payload family from the historical scaffold
lineage while keeping the fixed DAG id model, readiness boundaries, and
Non-Claims. Do not assume every external service is an L2
`agent_conclusion_v1` agent.

## 2. Inputs You May Receive

You may receive:

- `SCAFFOLD_ROOT`: this scaffold package root.
- `AGENT_PROJECT_ROOT`: the developer's existing agent project root.
- `TARGET_AGENT_ID`: the fixed DAG `snake_case` agent id.
- `EXTERNAL_AGENT_ID`: the external service id.
- `LEGACY_AGENT_ID`: optional old aNN migration id.
- `DIMENSION`: one of `value`, `market`, `risk`, or `macro`.
- target payload family, if already known.
- sample input/output from the developer.
- model files, data files, prompts, rules, or notebooks.
- owner notes describing intended behavior and limitations.

If `TARGET_AGENT_ID` is missing, stop and ask the developer to choose a fixed
DAG `snake_case` id from the main-system catalog. Do not invent an agent id.
Do not use an old aNN id as the primary `agent_id`.

## 3. What You Must Not Do

Do not:

- register anything into `AGENT_TOOLS`
- edit `config/agents`
- edit `config/fixed_dag/runtime_bindings.json`
- set `live_verified=true`
- set `invoke_enabled_by_default=true`
- modify the main-system graph
- call providers
- call external live `/v1/agent/invoke`
- start a demo stack
- restore `value_financial_analysis`
- restore a 28-agent roster
- route `sentiment_company_radar` directly into `risk_composite` or the risk dimension
- use an old aNN id as the primary `agent_id`
- use `main_agent_id` as the new request primary field
- output secrets, raw traceback, raw provider responses, or chain-of-thought
- silently pin incompatible dependencies
- delete or rewrite the developer's business core unless explicitly asked

## 4. Fixed DAG ID Rules

Use three ids:

```json
{
  "agent_id": "value_ml_valuation",
  "external_agent_id": "valuation_ml",
  "legacy_agent_id": "a16_ml_valuation"
}
```

Rules:

- `agent_id` is the main-system fixed DAG primary id.
- `external_agent_id` is the service-owned id.
- `legacy_agent_id` is an optional migration note only.
- old aNN ids must not be primary `agent_id` values.
- `main_agent_id` is not part of the new request schema.

## 5. Implementation Mode Neutrality

Do not force every agent to be `LLM + function call`.

Preserve the developer's existing business capability. The fixed DAG handoff
standardizes protocol, contract shape, evidence, timestamp, confidence,
readiness evidence, and safety. It does not standardize the internal technical
route.

Acceptable implementation modes include:

- `model_compute_agent`
- `llm_structured_agent`
- `data_service_agent`
- `deterministic_rule_agent`
- `hybrid_agent`
- `llm_function_call_agent`

An ML model can be the `compute_core`. An LLM can be only an explanation layer.
An LLM must not rewrite the numerical or structured conclusions produced by the
business core, including `stance`, `confidence`, `target`, `evidence`, and
`data_as_of`. All modes must output a mappable `tool_result`.

## 6. Audit First Procedure

Do this before modifying files:

1. Inspect `SCAFFOLD_ROOT`.
2. Read this file, `README.md`, `EXTERNAL_AGENT_INTEGRATION_STANDARD.md`, and
   `DOMAIN_PAYLOAD_CONTRACT_v1.md`.
3. Inspect `AGENT_PROJECT_ROOT`.
4. Identify current entry points.
5. Identify model, data, prompt, config, and dependency requirements.
6. Identify whether the existing project already has an API server.
7. Identify the current output shape and error behavior.
8. Identify where to wrap or call the existing business function as
   `compute_core`.
9. Identify existing tests and fixtures.
10. Produce an adaptation plan before modifying files.

The first audit pass should not edit files. If the developer project structure
is unclear, stop and report questions and recommended next steps. Do not guess
the architecture and blindly rewrite the project.

## 7. Adaptation Patterns

### Pattern A: Existing Python Model Or Library Project

Use this when the developer project exposes Python functions, classes, model
objects, notebooks converted to modules, or local data processing code.

Strategy:

- Keep the business model code in place.
- Add a FastAPI service wrapper.
- Implement `compute_core` by calling the existing model/library function.
- Make `/v1/agent/compute` return structured `external_agent_response_v0`.
- Make `/v1/agent/invoke` call the same `compute_core` and add only
  `answer`, `key_points`, and optional explanation.
- Add tests and sample requests around the wrapper, not around hidden live
  services.

### Pattern B: Existing API Service

Use this when the developer project already has an HTTP API or service process.

Strategy:

- Do not rewrite the business service.
- Add a compatibility adapter layer.
- Keep existing internal endpoints if needed.
- Add fixed DAG endpoints: `/health`, `/v1/agent/compute`, and
  `/v1/agent/invoke`.
- Map the old response into this scaffold schema.
- Keep live calls out of local tests by mocking or using deterministic fixtures.

### Pattern C: New Service From Scaffold

Use this when the developer project has no service wrapper yet.

Strategy:

- Copy the scaffold shape into the developer project.
- Replace the sample deterministic `compute_core`.
- Update ids, dimension, sample requests, sample responses, and tests.
- Keep the hard rules.
- Do not register the service in the main system.

### Pattern D: ML Plus Optional LLM Explainer

Use this when the business answer comes from an ML/statistical model and the
developer wants natural-language explanation.

Strategy:

- Treat ML output as the core result.
- Let `/v1/agent/compute` run without LLM credentials.
- Let `/v1/agent/invoke` optionally call an explanation layer.
- Do not let the LLM change `stance`, `confidence`, `target`, `evidence`,
  `event_flags`, `as_of`, or `data_as_of`.
- Keep local tests no-provider by default.

## 8. Required Service Contract

Expose:

```text
GET  /health
POST /v1/agent/compute
POST /v1/agent/invoke
```

Contract intent:

- `/health` returns safe service metadata.
- `/v1/agent/compute` is structured, fast, point-in-time, and does not require
  an LLM.
- `/v1/agent/invoke` is an explanation shell over the same `compute_core`.
- `/compute` and `/invoke` must share `compute_core`.
- both endpoints must be safe under local tests.

The sample service returns `agent_conclusion_v1` by default. A real adapted
project may emit another v2.3 payload if its fixed DAG role requires it.

## 9. Required Payload Rules

Requests and responses should handle:

- `schema_version`
- `request_id`
- `agent_id`
- `external_agent_id`
- optional `legacy_agent_id`
- `target`
- `question` for `/invoke`
- `as_of`
- `context`
- `options`
- `tool_result`
- `evidence`
- `event_flags`
- `confidence`
- `warnings`
- `errors`

Rules:

- `data_as_of <= as_of`
- `publish_time <= as_of` when present
- `confidence` must be in `[0, 1]`
- successful results need evidence
- `event_flags` must not encode hidden routing instructions
- typed errors must not leak secrets, raw traceback, provider raw response, or
  chain-of-thought
- old aNN primary ids must be rejected

Choose the payload family that matches the role:

- L2 analysis: `agent_conclusion_v1`
- L3 value or market composite: `dimension_conclusion_v1`
- L3 risk composite: `risk_conclusion_v1`
- L3 macro composite: `macro_conclusion_v1`
- L4 decision synthesis: `decision_conclusion_v1`
- evaluation or replay: `eval_record_v1`
- routing or planning: `fixed_dag_plan_v1`
- L1 data packet: `data_bundle_v1`

Do not force risk or macro payloads into directional `stance` output. Risk uses
`role=gate`; macro uses `role=regulator`.

## 10. Mapping Target

For an L2 external service, return:

```text
tool_result.schema_version = agent_conclusion_v1
```

A future main-system adapter maps `agent_conclusion_v1` to
`conclusion_object_v1`.

For other roles, use:

| External schema | Future mapping target |
| --- | --- |
| `dimension_conclusion_v1` | value/market dimension composite |
| `risk_conclusion_v1` | risk composite gate fields |
| `macro_conclusion_v1` | macro composite regulator fields |
| `decision_conclusion_v1` | decision result |
| `eval_record_v1` | evaluation/replay evidence |
| `fixed_dag_plan_v1` | route/plan payload |
| `data_bundle_v1` | L1 data bundle |

The external envelope is not graph state. Do not write directly into fixed DAG
runtime state. Do not emit step results. Do not mark runtime bindings as live
or enabled.

Read:

- `DOMAIN_PAYLOAD_CONTRACT_v1.md`
- `EXTERNAL_AGENT_INTEGRATION_STANDARD.md`
- `schemas.py` and `validate_tool_result`

## 11. File Modification Strategy In Developer Project

Prefer adding a small adapter package, for example:

```text
fixed_dag_adapter/
  service.py
  schemas.py
  errors.py
  sample_requests/
    health.expected.json
    compute.request.json
    compute.response.json
    invoke.request.json
    invoke.response.json
    error.response.json
  tests/
    test_fixed_dag_contract.py
  .env.example
```

Prefer:

- small wrappers
- explicit mapping functions
- local tests
- clear dependency notes
- preserving existing business modules

Avoid:

- rewriting the model core
- deleting training or model code
- moving large dependency trees
- changing business algorithms without owner approval
- silently pinning incompatible versions

If dependencies conflict, report the conflict and propose a minimal wrapper
strategy. Do not silently mutate the environment.

## 12. Tests To Add In Developer Project

Add tests for:

- health schema
- compute success
- invoke success
- `request_id` roundtrip
- `data_as_of <= as_of`
- `publish_time <= as_of` when present
- confidence bounds
- evidence present for successful output
- `event_flags` shape
- selected v2.3 payload family semantic checks
- typed errors are safe
- old aNN primary `agent_id` rejected
- no secrets or raw traceback
- no provider call in local tests
- no external live call in local tests

Tests may use FastAPI `TestClient`, fixtures, mocks, or deterministic model
inputs. Do not require live provider credentials for local contract tests.

## 13. Validation Commands

From the adapted developer project:

```powershell
python -m pytest tests -q
python -m ruff check .
```

If validating this scaffold package:

```powershell
python -m pytest tests -q
python -m ruff check .
```

Do not run main-system live invoke. Do not run provider smoke. Do not modify
runtime bindings. Do not set live or enabled flags.

## 14. Handoff Bundle To Return To Maintainers

Return:

- service source path
- selected `agent_id`
- `external_agent_id`
- optional `legacy_agent_id`
- selected payload schema version
- `implementation_notes`
- health sample
- compute request/response
- invoke request/response
- error response
- domain payload sample
- local test output
- timestamp policy
- evidence policy
- confidence policy
- known limitations
- dependency list
- no secrets confirmation
- performance note

## 15. Final Response Format For Coding Agent

Use this structure:

```text
A) Audit Summary
B) Adaptation Strategy
C) Files Changed
D) Endpoint Summary
E) Contract Mapping
F) Tests Added
G) Validation Results
H) Remaining Risks
I) Handoff Bundle
J) Final Conclusion
```

Final conclusion must be one of:

```text
ADAPTATION_COMPLETE_READY_FOR_MAINTAINER_REVIEW
ADAPTATION_COMPLETE_WITH_LIMITATIONS
BLOCKED_BY_MISSING_AGENT_ID
BLOCKED_BY_PROJECT_STRUCTURE
BLOCKED_BY_DEPENDENCY_CONFLICT
BLOCKED_BY_TEST_FAILURE
BLOCKED_BY_SCOPE_CONFLICT
```

## 16. Copy-Paste Prompt For Codex / Claude Code

Use this prompt when giving the scaffold and an existing developer project to a
coding agent:

```text
You are my coding agent for adapting an existing agent project into a fixed DAG
external service.

Inputs:
- SCAFFOLD_ROOT=<path to this scaffold>
- AGENT_PROJECT_ROOT=<path to your agent project>
- TARGET_AGENT_ID=<fixed dag snake_case id>
- EXTERNAL_AGENT_ID=<service id>
- LEGACY_AGENT_ID=<optional old id or empty>
- DIMENSION=<value|market|risk|macro>
- PAYLOAD_SCHEMA=<agent_conclusion_v1|dimension_conclusion_v1|risk_conclusion_v1|macro_conclusion_v1|decision_conclusion_v1|eval_record_v1|fixed_dag_plan_v1|data_bundle_v1>

Rules:
- First read SCAFFOLD_ROOT/AI_CODING_HANDOFF.md.
- Also read SCAFFOLD_ROOT/README.md,
  SCAFFOLD_ROOT/EXTERNAL_AGENT_INTEGRATION_STANDARD.md, and
  SCAFFOLD_ROOT/DOMAIN_PAYLOAD_CONTRACT_v1.md.
- Inspect AGENT_PROJECT_ROOT before modifying files.
- Audit first and produce an adaptation plan.
- If TARGET_AGENT_ID is missing, stop and ask me to choose a fixed DAG
  snake_case id from the catalog.
- Preserve the existing business compute core.
- Do not force LLM + function call.
- Choose the v2.3 payload schema that matches the fixed DAG role.
- Implement a minimal wrapper or adapter.
- Expose GET /health, POST /v1/agent/compute, and POST /v1/agent/invoke.
- Make /compute and /invoke share compute_core.
- Add schemas, typed errors, sample_requests, and local contract tests.
- Validate data_as_of <= as_of, publish_time <= as_of when present,
  confidence in [0,1], evidence, event_flags, request_id roundtrip,
  selected v2.3 payload semantics, and safe typed errors.
- Reject old aNN primary agent_id values.
- Do not modify any main-system runtime files.
- Do not edit AGENT_TOOLS, config/agents, or runtime_bindings.
- Do not set live_verified=true or invoke_enabled_by_default=true.
- Do not call providers or external live /v1/agent/invoke in tests.
- Do not start demo stacks.
- Do not output secrets, raw traceback, provider raw responses, or
  chain-of-thought.
- Run local validation commands and report exact results.
- Return a handoff bundle for main-system maintainers.

Final response format:
A) Audit Summary
B) Adaptation Strategy
C) Files Changed
D) Endpoint Summary
E) Contract Mapping
F) Tests Added
G) Validation Results
H) Remaining Risks
I) Handoff Bundle
J) Final Conclusion
```
