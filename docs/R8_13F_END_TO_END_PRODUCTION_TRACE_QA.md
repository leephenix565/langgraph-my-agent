# R8-13F End-to-End Production Trace QA

This document records the R8-13F end-to-end fixed DAG trace QA after the
production L3 composite wrapper backfill.

## Scope

R8-13F closes the main-system gap left after R8-13E: the four production L3
services can now read `context.upstream_outputs`, so the default-off compute
bridge must send bounded current-run L2 outputs to allowlisted L3 compute
calls. R8-13F also restores the sandbox-proven `agent_task_v1` and
`agent_evidence_bundle_v1` trace shape in the main repository so the final
report generator can receive auditable agent inputs and outputs.

This remains demo and QA work. It does not enable production runtime bindings.

## Code Changes

Main-system files changed:

- `src/react_agent/fixed_dag_contracts.py`
- `src/react_agent/fixed_dag_executor.py`
- `src/react_agent/fixed_dag_external_compute_bridge.py`
- `src/react_agent/fixed_dag_llm_placeholders.py`
- `scripts/dev/run_r8_13a_e2e_smoke.py`
- `tests/unit_tests/test_fixed_dag_contracts.py`
- `tests/unit_tests/test_fixed_dag_executor.py`
- `tests/unit_tests/test_fixed_dag_external_compute_bridge.py`
- `tests/unit_tests/test_fixed_dag_llm_placeholders.py`

The change adds or restores:

- `agent_task_v1` instructions for fixed DAG agents.
- `agent_evidence_bundle_v1` inside `report_input_bundle_v1`.
- Bounded `context.upstream_outputs` for allowlisted L3 compute calls.
- L3 request propagation tests for upstream L2 evidence.
- A runnable E2E trace runner under `scripts/dev/run_r8_13a_e2e_smoke.py`.

## E2E Smoke Artifacts

Real production compute with fake report model:

```text
/tmp/lma-r8-13f-prod-e2e/20260612T030650Z
```

Real production compute with configured LLM report synthesis:

```text
/tmp/lma-r8-13f-prod-e2e-llm-report/20260612T030735Z
```

The LLM report run used:

- real default-off external compute bridge
- allowlisted production `/v1/agent/compute` endpoints only
- configured report model loaded from environment
- fake placeholder model for unconnected L2 slots
- no `/v1/agent/invoke`

## E2E Result

Question:

```text
请从估值、市场、风险和宏观角度分析贵州茅台 600519.SH 当前是否值得关注。
```

Mapped production compute agents: 17.

Mapped L2 production compute agents:

- `value_traditional_valuation`
- `value_ml_valuation`
- `value_meta_valuation`
- `value_research_synthesis`
- `market_stock_technical`
- `market_ipo_investor_behavior`
- `market_capital_flow_chip`
- `sentiment_company_radar`
- `risk_crash`
- `risk_financial_fraud`
- `risk_identification`
- `risk_compliance_review`
- `macro_analysis`

Mapped L3 production compute agents:

- `value_composite`
- `market_composite`
- `risk_composite`
- `macro_composite`

Internal placeholder L2 slots: 5.

- `market_fund_manager_behavior`
- `macro_commodity_pricing`
- `macro_index_valuation`
- `macro_sentiment`
- `macro_industry_hotspot`

Failed external compute mappings: 0.

## Evidence Quality Summary

The E2E trace is functionally complete, but the business evidence is mixed:

- L2 total: 18
- L2 complete: 7
- L2 error: 3
- L2 partial: 8
- L2 without readable evidence: 3
- L3 total: 4
- L3 complete: 0

Important quality findings:

- `value_traditional_valuation`, `value_ml_valuation`, and
  `value_meta_valuation` returned service output that still mapped to error
  conclusions because the adapter observed `direction_stance_missing`.
- `value_research_synthesis` produced the only complete value-side L2
  conclusion in this run.
- `market_stock_technical` was complete and strongly negative.
- `market_capital_flow_chip` was complete but low confidence.
- `market_ipo_investor_behavior` and `sentiment_company_radar` returned
  deterministic fallback style outputs.
- All four risk L2 members were available, but `risk_financial_fraud` remained
  partial.
- Only `macro_analysis` was a real macro L2 output; the other macro L2 slots
  were placeholders.
- The four L3 composites successfully consumed the current run's upstream
  outputs, but remained `partial` because upstream L2 evidence was partial,
  placeholder, or error.

## Final Report Behavior

The configured report model produced a natural Chinese final report from the
structured `report_input_bundle_v1`. The report correctly identified that:

- valuation evidence is weak because three value model agents failed mapping;
- market evidence is negative due to technical and sentiment signals;
- risk gate passed with no veto;
- macro is neutral and partly placeholder-driven;
- the system should not claim a strong "worth attention" conclusion from the
  current evidence.

This is the intended behavior: the report generator reads the full structured
bundle and reports both signals and evidence limitations.

## Remaining Remediation

Priority service or protocol fixes:

1. Fix the three value L2 services or adapter shape that causes
   `direction_stance_missing`.
2. Improve `sentiment_company_radar` and `market_ipo_investor_behavior` so they
   stop returning deterministic fallback summaries when LLM output is expected.
3. Connect or remediate the missing macro L2 services:
   `macro_commodity_pricing`, `macro_index_valuation`, `macro_sentiment`, and
   `macro_industry_hotspot`.
4. Connect `market_fund_manager_behavior` or keep it explicitly marked as a
   placeholder.
5. Continue moving the report path toward the formal external
   `report_generator` agent contract after the demo path remains stable.

## Non-Claims

- R8-13F does not call `/v1/agent/invoke`.
- R8-13F does not modify `runtime_bindings.json`.
- R8-13F does not set `live_verified=true`.
- R8-13F does not set `invoke_enabled_by_default=true`.
- R8-13F does not enable default graph calls to production services.
- R8-13F does not store raw external responses, endpoint URLs, credentials, or
  provider raw output in the repository.
- R8-13F does not prove business correctness for every external service.
