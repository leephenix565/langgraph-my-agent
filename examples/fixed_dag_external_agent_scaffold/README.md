# Fixed DAG External Agent Scaffold

Package version: `fixed-dag-scaffold-v0.1`.

This package is the fixed DAG version of the historical external-agent scaffold
protocol package / v2.1-v2.2.1 lineage. It keeps the useful transport,
endpoint, safety, timestamp, confidence, evidence, idempotency, and degradation
ideas, but replaces the old `AGENT_TOOLS`, `config/agents`, aNN primary id, and
`main_agent_id` handoff model.

The package is a sample-only delivery scaffold for external developers. It is
not registered into the `langgraph-my-agent` active graph, does not modify
`config/fixed_dag/runtime_bindings.json`, and does not prove live readiness.

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

New samples use all three fields. The old `main_agent_id` field is not a
primary request field in this package.

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

Optional metadata:

```json
{
  "implementation_notes": {
    "implementation_type": "model_compute_agent",
    "uses_llm": false,
    "llm_role": "",
    "compute_core": "sample_deterministic_core",
    "explanation_layer": "optional"
  }
}
```

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

## Sample Files

`sample_requests/` contains:

- `health.expected.json`
- `compute.request.json`
- `compute.response.json`
- `invoke.request.json`
- `invoke.response.json`
- `error.response.json`

The response samples include `as_of`, `data_as_of`, evidence, event flags,
confidence in `[0, 1]`, typed errors where applicable, and no secret or raw
traceback fields.

## Non-Claims

This package does not:

- register an external service into the main graph
- change the 27-agent fixed DAG roster
- restore `value_financial_analysis`
- restore a 28-agent roster
- route `sentiment_company_radar` into `risk_composite`
- modify `runtime_bindings`
- set `live_verified=true`
- set `invoke_enabled_by_default=true`
- prove live service readiness
- prove provider readiness
- provide production auth, rate limits, TLS, observability, or persistence
