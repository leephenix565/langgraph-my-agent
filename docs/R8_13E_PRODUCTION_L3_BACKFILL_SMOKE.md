# R8-13E Production L3 Backfill And Smoke

This document records the controlled production backfill for the four L3
composite services. The work applies the R8-13D reviewed service patches to
production service directories, validates the changed files, restarts only the
four target L3 services, and records production `/health` +
`/v1/agent/compute` smoke results.

## Scope

Production services modified:

- `/sdb/dlut/prod/综合估值智能体`
- `/sdb/dlut/prod/市场面综合智能体`
- `/sdb/dlut/prod/综合风险智能体`
- `/sdb/dlut/prod/宏观综合智能体`

Production services not modified:

- L1 services
- L2 services
- L4 services
- main-system runtime binding configuration

No `/v1/agent/invoke` endpoint was called.

## Backup

Backup root:

```text
/tmp/lma-r8-13e-prod-l3-backfill/20260612T024513Z
```

Backup manifest:

```text
/tmp/lma-r8-13e-prod-l3-backfill/20260612T024513Z/metadata/service_patch_manifest.json
```

All production service roots were non-git directories during this phase, so the
rollback source is the `/tmp` backup above.

## Changed Files

### value_composite

Production root:

```text
/sdb/dlut/prod/综合估值智能体
```

Changed files:

- `service.py`
- `tests/test_fixed_dag_l3_wrapper.py`

Behavior added:

- Reads `context.upstream_outputs` for fixed DAG value composite requests.
- Builds `dimension_conclusion_v1` from value L2 members:
  - `value_traditional_valuation`
  - `value_ml_valuation`
  - `value_meta_valuation`
  - `value_research_synthesis`
- Keeps the business compute core unchanged.

### market_composite

Production root:

```text
/sdb/dlut/prod/市场面综合智能体
```

Changed files:

- `composite.py`
- `service.py`
- `tests/test_external_contract.py`

Behavior added:

- Reads `context.upstream_outputs` for fixed DAG market composite requests.
- Builds `dimension_conclusion_v1` from market L2 members:
  - `market_stock_technical`
  - `market_fund_manager_behavior`
  - `market_ipo_investor_behavior`
  - `market_capital_flow_chip`
  - `sentiment_company_radar`
- Downweights partial or placeholder member outputs.
- Keeps `sentiment_company_radar` market-only.
- Keeps the business compute core unchanged.

### risk_composite

Production root:

```text
/sdb/dlut/prod/综合风险智能体
```

Changed files:

- `risk_constraint_agent_app.py`
- `tests/test_fixed_dag_upstream_wrapper.py`

Behavior added:

- Reads `context.upstream_outputs` for fixed DAG risk composite requests.
- Builds `risk_conclusion_v1` from risk L2 members:
  - `risk_crash`
  - `risk_financial_fraud`
  - `risk_identification`
  - `risk_compliance_review`
- Does not consume `sentiment_company_radar`.
- Preserves gate semantics: `pass`, `penalty`, `veto`, and `manual_review`.
- Keeps the business compute core unchanged.

### macro_composite

Production root:

```text
/sdb/dlut/prod/宏观综合智能体
```

Changed files:

- `service.py`
- `tests/test_synthesis.py`

Behavior added:

- Reads `context.upstream_outputs` for fixed DAG macro composite requests.
- Builds `macro_conclusion_v1` from macro L2 members:
  - `macro_analysis`
  - `macro_commodity_pricing`
  - `macro_index_valuation`
  - `macro_sentiment`
  - `macro_industry_hotspot`
- Keeps `dimension_weights` limited to `value` and `market`.
- Keeps `risk_sensitivity` as the risk-control channel.
- Keeps the business compute core unchanged.

## Service Validation

Focused service validation passed:

| Service | Validation |
| --- | --- |
| `value_composite` | `py_compile` passed; `tests/test_fixed_dag_l3_wrapper.py` passed, 5 tests |
| `market_composite` | `py_compile` passed; `tests/test_external_contract.py` passed, 9 tests |
| `risk_composite` | `py_compile` passed; `tests/test_fixed_dag_upstream_wrapper.py` passed, 1 test |
| `macro_composite` | `py_compile` passed; `tests/test_synthesis.py` passed, 20 tests |

## Restart

Restart log root:

```text
/tmp/lma-r8-13e-prod-l3-restart/20260612T024553Z
```

Only these ports were restarted:

| Agent | Port | New PID observed |
| --- | --- | --- |
| `value_composite` | `10015` | `3083138` |
| `market_composite` | `10023` | `3083333` |
| `risk_composite` | `10016` | `3083413` |
| `macro_composite` | `10024` | `3083591` |

No dev ports were restarted.

## Production Smoke

Smoke artifact root:

```text
/tmp/lma-r8-13e-prod-l3-smoke/20260612T024649Z
```

Smoke endpoints:

- `GET /health`
- `POST /v1/agent/compute`

No `/v1/agent/invoke` endpoint was called.

Result:

| Agent | Health | Compute | Adapter mapping | Adapter status |
| --- | --- | --- | --- | --- |
| `value_composite` | pass | pass | pass | `complete` |
| `market_composite` | pass | pass | pass | `partial` |
| `risk_composite` | pass | pass | pass | `partial` |
| `macro_composite` | pass | pass | pass | `partial` |

The `partial` adapter status reflects partial or placeholder upstream L2
signals in the controlled smoke input. It is still a protocol pass for the L3
wrapper and adapter mapping.

## Rollback

If rollback is required, restore the backed up files from:

```text
/tmp/lma-r8-13e-prod-l3-backfill/20260612T024513Z
```

Then restart only the affected service using its original command recorded in
the backup manifest.

## Non-Claims

- R8-13E does not call `/v1/agent/invoke`.
- R8-13E does not modify `runtime_bindings.json`.
- R8-13E does not set `live_verified=true`.
- R8-13E does not set `invoke_enabled_by_default=true`.
- R8-13E does not enable default graph calls to production external services.
- R8-13E does not change business models, feature engineering, scoring
  algorithms, model files, data files, or deployment configuration.
- R8-13E proves only controlled L3 `/health` + `/v1/agent/compute` protocol
  and adapter mapping after backfill.
