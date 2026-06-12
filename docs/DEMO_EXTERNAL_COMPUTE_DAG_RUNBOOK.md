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

R8-12C adds a report evidence bundle on top of the same demo boundary. The
final report consumes bounded L2 agent summaries and L3 composite summaries,
and the Web workflow detail panel can show those summaries per step. The demo
still does not expose raw external responses, endpoint URLs, secrets, error
stacks, or internal reasoning drafts.

R8-12D optionally adds natural-language LLM report synthesis. Set
`ENABLE_LLM_REPORT_SYNTHESIS=1` only when you intentionally want the main system
model to read `report_input_bundle_v1` and write the final report. The model
does not receive raw external responses or endpoint URLs, and failure falls
back to the template report.

## Required Flags

Both the boolean flag and the allowlist must be set. With only the boolean flag
enabled and an empty allowlist, no HTTP call is made.

```bash
ENABLE_EXTERNAL_COMPUTE_DEMO=1
EXTERNAL_COMPUTE_DEMO_ALLOWLIST=value_traditional_valuation,value_ml_valuation,value_meta_valuation,value_research_synthesis,market_stock_technical,market_capital_flow_chip,sentiment_company_radar,risk_identification,risk_compliance_review,risk_financial_fraud,risk_crash,macro_analysis,value_composite,market_composite,risk_composite,macro_composite
EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS=20
# Optional: use the main-system model to synthesize the final natural report.
ENABLE_LLM_REPORT_SYNTHESIS=1
# Optional: override only the report synthesis model.
# LLM_REPORT_SYNTHESIS_MODEL=deepseek/deepseek-chat
```

Optional selected routing can be enabled separately:

```bash
ENABLE_SELECTED_ROUTING=1
```

For the broad demo, keep selected routing off so the full fixed DAG can display
value, market, risk, and macro paths.

## R8-13H Sandbox A-Class Extension

R8-13H ports the sandbox-validated default-off bridge path for the A-class
L1/L2 remediation candidates into the main development branch:

- `financial_data_service` as L1 `data_bundle_v1`;
- `entity_relation_extractor` as L1 `entity_relation_bundle_v1`;
- `macro_commodity_pricing` as macro L2 `agent_conclusion_v1`;
- `macro_index_valuation` as macro L2 `agent_conclusion_v1`.

This changes the demo data flow only when the explicit external compute demo
flag and allowlist are set. The important ordering change is that the L1
compute bridge runs before L2 `agent_task_v1` construction, so L2 tasks can
receive mapped financial data and entity-relation evidence instead of only the
local placeholder bundles.

Example experimental sandbox allowlist:

```bash
EXTERNAL_COMPUTE_DEMO_ALLOWLIST=financial_data_service,entity_relation_extractor,macro_commodity_pricing,macro_index_valuation,value_traditional_valuation,value_ml_valuation,value_meta_valuation,value_research_synthesis,market_stock_technical,market_capital_flow_chip,sentiment_company_radar,risk_identification,risk_compliance_review,risk_financial_fraud,risk_crash,macro_analysis,value_composite,market_composite,risk_composite,macro_composite
```

Do not treat that allowlist as production readiness. In the latest audit,
`macro_commodity_pricing` and `macro_index_valuation` have service-local
contract tests that pass, `financial_data_service` has a production wrapper
that can be mapped by the adapter, and `entity_relation_extractor` still needs
a confirmed production endpoint before it can count as production evidence.
If testing entity relation from its dev process, set a local loopback override
such as `EXTERNAL_COMPUTE_DEMO_URL_ENTITY_RELATION_EXTRACTOR=http://127.0.0.1:8101`
and label the run as dev-only.

## Local API And Web

Start the local API from the repo root:

```bash
ENABLE_EXTERNAL_COMPUTE_DEMO=1 \
EXTERNAL_COMPUTE_DEMO_ALLOWLIST=value_traditional_valuation,value_ml_valuation,value_meta_valuation,value_research_synthesis,market_stock_technical,market_capital_flow_chip,sentiment_company_radar,risk_identification,risk_compliance_review,risk_financial_fraud,risk_crash,macro_analysis,value_composite,market_composite,risk_composite,macro_composite \
EXTERNAL_COMPUTE_DEMO_TIMEOUT_SECONDS=20 \
ENABLE_LLM_REPORT_SYNTHESIS=1 \
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

If the main system is running on a developer laptop and the external agents
remain on the server, start the SSH same-port tunnel first. See
`docs/LOCAL_REMOTE_AGENT_DEMO_RUNBOOK.md`. The tunnel preserves the bridge's
loopback-only boundary by forwarding local `127.0.0.1:100xx` ports to remote
server `127.0.0.1:100xx` ports.

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

- `market_fund_manager_behavior`
- `macro_sentiment`
- `macro_industry_hotspot`
- L4 agents

R8-13H moves `financial_data_service`, `entity_relation_extractor`,
`macro_commodity_pricing`, and `macro_index_valuation` into experimental
default-off allowlist support. They still require separate controlled
production re-smoke before docs may describe them as production pass.

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
