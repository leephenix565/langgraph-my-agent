# External Agent Scaffold v2.3.1 Fixed DAG

Package version: `external-agent-scaffold-v2.3.1-fixed-dag`.

This package inherits the historical external-agent scaffold v2.1-v2.2.1
lineage, restores the broader v2.3 domain payload family, and applies the
v2.3.1 contract patch for risk members, manual review gates, structured
dimension members, normalized dates, macro directional weights, and L4 trace
semantics.

It is still a sample-only delivery scaffold. It is not registered into the
`langgraph-my-agent` active graph, does not modify
`config/fixed_dag/runtime_bindings.json`, and does not prove live readiness.

## Source And Distribution Relationship

There are three package locations in the current workflow:

| Location | Role |
| --- | --- |
| `examples/fixed_dag_external_agent_scaffold/` | Canonical tracked repo mirror and audit baseline. Review diffs here. |
| `E:\muti-agent\external_agent_scaffold` | Local distribution working copy edited before zip output. |
| `E:\muti-agent\external_agent_scaffold_v2.3.1_fixed_dag_<timestamp>.zip` | Distribution artifact generated from the local working copy. |

Future scaffold changes should update the tracked repo mirror and the local
distribution working copy together, then regenerate the zip. None of these
locations is active runtime registration or live-readiness evidence.

## Fixed DAG Truth

Current integration authority lives in the main repo:

- `config/fixed_dag/agent_catalog.json`
- `config/fixed_dag/runtime_bindings.json`
- `src/react_agent/fixed_dag_catalog.py`
- `src/react_agent/fixed_dag_runtime_registry.py`
- `src/react_agent/fixed_dag_contracts.py`
- `src/react_agent/fixed_dag_executor.py`
- `scripts/quality/run_quality.py`

Do not treat `AGENT_TOOLS`, `config/agents`, old Agent Catalog v2, old
router/manager graph paths, old aNN ids, or `main_agent_id` as current fixed
DAG handoff truth.

## ID Model

Use three ids:

| Field | Meaning | Example |
| --- | --- | --- |
| `agent_id` | Current fixed DAG `snake_case` primary id. | `value_ml_valuation` |
| `external_agent_id` | External service-owned id. | `valuation_ml` |
| `legacy_agent_id` | Optional migration note only. | `a16_ml_valuation` |

Old aNN ids are rejected as primary `agent_id` values. `main_agent_id` is not a
new request-schema field.

## Payload Family

v2.3.1 uses the v2.3 payload family with patched semantics:

| Schema | Intended role |
| --- | --- |
| `agent_conclusion_v1` | L2 analysis agent conclusion. `direction` members use `stance`; `gate_member` risk members use `risk_score`. |
| `dimension_conclusion_v1` | L3 value or market composite with `DimensionMember[]`. |
| `risk_conclusion_v1` | L3 risk gate, including `manual_review`. |
| `macro_conclusion_v1` | L3 macro regulator. `dimension_weights` only contains `value` and `market`. |
| `decision_conclusion_v1` | L4 decision synthesis with distinct reasoning stages and score tolerance. |
| `eval_record_v1` | Routing, reasoning, backtest, or replay evaluation record. |
| `fixed_dag_plan_v1` | Route or plan payload. |
| `data_bundle_v1` | L1 point-in-time data bundle. |

The default `service.py` still returns a deterministic L2
`agent_conclusion_v1` sample from `/compute` and `/invoke`. The wider payload
family is covered by `schemas.py`, `validate_tool_result`, tests, and
`sample_requests/*.response.json`.

## Dimension Rules

Canonical dimensions are English:

```text
value
market
risk
macro
```

During the migration window, `validate_tool_result` accepts Chinese aliases
such as `价值`, `市场面`, `风险`, and `宏观`, then normalizes them to English.
Samples use English canonical values. A later phase may deprecate Chinese
aliases after adapter compatibility is stable.

`sentiment_company_radar` is a market signal only. It must not route directly
to `risk_composite`.

## Semantic Validators

`schemas.py` exposes `validate_tool_result(payload)`. It validates by
`schema_version` and checks:

- aNN ids are rejected as primary `agent_id`
- `data_as_of <= as_of`
- `publish_time <= as_of`
- evidence timestamps do not exceed `as_of`
- success payloads with evidence-bearing schemas include evidence
- confidence is in `[0, 1]`
- `agent_conclusion_v1` supports `direction` and `gate_member`; `raw_output`
  and `quality` must be safe dictionaries
- `dimension_conclusion_v1` uses structured members, checks member weights sum
  to one within `0.01`, and checks weighted stance within `0.02`
- `risk_conclusion_v1` has `role=gate`, supports `manual_review`, and has no
  `stance`
- `macro_conclusion_v1` has `role=regulator`, no `stance`, and normalized
  `dimension_weights` containing only `value` and `market`
- `decision_conclusion_v1` has at least three distinct `reasoning_trace.stage`
  values and a displayed `score` within `0.01` of
  `calculation_trace.final_score`; document `score` as
  `round(final_score, 2)`
- `data_bundle_v1` includes replayable `snapshot_id`

`implementation_notes` remains optional. Existing agents that do not provide
it should still pass if their required contract fields are valid.

## Implementation Modes

The platform does not require every agent to be `LLM + function call`.
Developers may implement:

- machine-learning model plus optional LLM explainer
- rule or statistical model
- data service
- NLP or LLM structured agent
- deterministic `compute_core`
- LLM plus function call
- hybrid systems

The standardized object is the boundary: input protocol, output protocol, ID
mapping, evidence, timestamps, confidence, status, and readiness ladder.

## Endpoints

The sample service exposes:

```text
GET  /health
POST /v1/agent/compute
POST /v1/agent/invoke
```

`/compute` calls deterministic local `compute_core` and returns structured
payloads. `/invoke` calls the same core and only adds answer/key points. The
sample does not call LLMs, providers, external HTTP services, or `.env`
secrets.

## Quick Start

From the package directory:

```powershell
conda run --no-capture-output -n cline_env python -m pytest tests -q
conda run --no-capture-output -n cline_env python -m ruff check .
```

Optional local manual server:

```powershell
conda run --no-capture-output -n cline_env python -m uvicorn service:app --host 127.0.0.1 --port 8100
```

The tests use in-process FastAPI `TestClient`. They do not start a network
service and do not call external `/v1/agent/invoke`.

For Codex, Claude Code, or another coding agent adapting an existing developer
project, start with `AI_CODING_HANDOFF.md`.

## Sample Files

`sample_requests/` contains the endpoint samples plus domain payload samples:

- `health.expected.json`
- `compute.request.json`
- `compute.response.json`
- `invoke.request.json`
- `invoke.response.json`
- `error.response.json`
- `agent_conclusion.response.json`
- `agent_conclusion.risk_member.response.json`
- `dimension_conclusion.response.json`
- `risk_conclusion.response.json`
- `macro_conclusion.response.json`
- `decision_conclusion.response.json`
- `eval_record.response.json`
- `data_bundle.response.json`
- `fixed_dag_plan.response.json`

The samples include `as_of`, `data_as_of`, evidence where applicable, event
flags where applicable, confidence in `[0, 1]`, typed errors where applicable,
and no secret or raw traceback fields.

`error.response.json` is a negative rejection example. Do not copy its legacy
`agent_id` into a valid request.

## Non-Claims

This package does not:

- register an external service into the main graph
- change the 27-agent fixed DAG roster
- rely on old 25-agent, 28-agent, or `L2=19` catalog counts
- restore `value_financial_analysis`
- route `sentiment_company_radar` into `risk_composite`
- modify `runtime_bindings`
- set `live_verified=true`
- set `invoke_enabled_by_default=true`
- prove live service readiness
- prove provider readiness
- provide production auth, rate limits, TLS, observability, or persistence

R8 is the later main-system adapter phase. This package only defines and tests
the external handoff contract.
