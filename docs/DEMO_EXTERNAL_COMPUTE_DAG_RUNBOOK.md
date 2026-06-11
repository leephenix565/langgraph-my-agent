# Default-Off External Compute Demo Runbook

This runbook covers the R8-12 demo mode for the fixed DAG system.

## Scope

R8-12 adds a default-off bridge from the fixed DAG executor to selected
production `/v1/agent/compute` endpoints. The bridge is for demo and validation
only. It is not runtime binding enablement, live verification, or default graph
execution.

The bridge never calls `/v1/agent/invoke`. It maps compute responses through
`fixed_dag_external_adapter.py` before results can enter the fixed DAG report
or workflow snapshot.

## Required Flags

Both the boolean flag and the allowlist must be set. With only the boolean flag
enabled and an empty allowlist, no HTTP call is made.

```bash
ENABLE_EXTERNAL_COMPUTE_DEMO=1
EXTERNAL_COMPUTE_DEMO_ALLOWLIST=value_traditional_valuation,value_ml_valuation,value_meta_valuation,value_research_synthesis,market_stock_technical,market_capital_flow_chip,sentiment_company_radar,risk_identification,risk_compliance_review,risk_financial_fraud,risk_crash,macro_analysis,value_composite,market_composite,risk_composite,macro_composite
EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS=20
```

Optional selected routing can be enabled separately:

```bash
ENABLE_SELECTED_ROUTING=1
```

For the broad demo, keep selected routing off so the full fixed DAG can display
value, market, risk, and macro paths.

## Local API And Web

Start the local API from the repo root:

```bash
ENABLE_EXTERNAL_COMPUTE_DEMO=1 \
EXTERNAL_COMPUTE_DEMO_ALLOWLIST=value_traditional_valuation,value_ml_valuation,value_meta_valuation,value_research_synthesis,market_stock_technical,market_capital_flow_chip,sentiment_company_radar,risk_identification,risk_compliance_review,risk_financial_fraud,risk_crash,macro_analysis,value_composite,market_composite,risk_composite,macro_composite \
EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS=20 \
.venv/bin/python -m uvicorn react_agent.public_api:app --host 127.0.0.1 --port 8200
```

Start the web UI in a separate shell:

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8200 \
npm --prefix apps/web run dev -- --host 127.0.0.1 --port 8201
```

Then open:

```text
http://127.0.0.1:8201
```

Suggested demo question:

```text
请从估值、市场、风险和宏观角度分析贵州茅台 600519.SH 当前是否值得关注。
```

## Demo Allowlist Boundary

The R8-12 registry contains only loopback production ports with prior
production compute evidence. Runtime bindings remain unchanged and continue to
be the authority for default runtime behavior.

Do not add these services to the demo allowlist until separate production
compute evidence exists:

- `financial_data_service`
- `entity_relation_extractor`
- `market_fund_manager_behavior`
- `macro_commodity_pricing`
- `macro_index_valuation`
- `macro_sentiment`
- `macro_industry_hotspot`
- L4 agents

`sentiment_company_radar` is market-only and must not be routed into risk.

## Expected UI Result

The answer should be Chinese and should include:

- fixed DAG flow wording;
- value signals;
- market signals;
- risk gate summary;
- macro regulator summary;
- cautious final conclusion;
- a clear statement that this is demo-only structured integration.

The answer must not expose raw JSON, endpoint URLs, secrets, tracebacks,
chain-of-thought, or provider raw output.

## Non-Claims

- R8-12 does not call `/v1/agent/invoke`.
- R8-12 does not modify `runtime_bindings.json`.
- R8-12 does not set live flags.
- R8-12 does not enable default production external invocation.
- R8-12 does not prove business correctness or production readiness.
