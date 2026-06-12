# R8-13G Value L2 Stance Remediation

This document records the R8-13G production protocol remediation for the three
value L2 valuation services that exposed `direction_stance_missing` during
R8-13F end-to-end trace QA.

## Scope

R8-13G fixes only the service-side fixed DAG wrapper shape for:

- `value_traditional_valuation` / 传统企业估值智能体
- `value_ml_valuation` / 机器学习企业估值智能体
- `value_meta_valuation` / 元学习企业估值智能体

The production issue was not a valuation-model failure. Each service already
computed a directional valuation signal under `normalized.stance`. The main
system adapter consumes L2 `agent_conclusion_v1` direction signals from the
top-level `stance` field, so the payload was valid for the older local domain
sample but incomplete for fixed DAG adapter mapping.

## Root Cause

The three services returned `external_agent_compute_v0.tool_result` payloads
with:

- `schema_version=agent_conclusion_v1`
- fixed DAG `agent_id`
- `external_agent_id`
- `dimension=value`
- `role=direction`
- `normalized.stance`

They did not expose top-level `stance`, so the main adapter failed closed with
`direction_stance_missing`. The R8-13F final report correctly reflected those
three value L2 outputs as unusable evidence.

## Service Changes

Backup root:

```text
/tmp/lma-r8-13g-value-l2-stance-backfill/20260612T033501Z
```

Changed service files:

| Service | Files | Change |
| --- | --- | --- |
| 传统企业估值智能体 | `/sdb/dlut/prod/传统企业估值智能体/service.py`, `tests/test_domain_contract_v1.py`, `说明.md` | Project `normalized.stance` and `normalized.confidence` to top-level `stance` / `confidence` in the fixed DAG tool result. |
| 机器学习企业估值智能体 | `/sdb/dlut/prod/机器学习企业估值智能体/service.py`, `tests/test_domain_contract_v1.py`, `README.md` | Same top-level fixed DAG direction projection for the ML valuation wrapper. |
| 元学习企业估值智能体 | `/sdb/dlut/prod/元学习企业估值智能体/service.py`, `tests/test_domain_contract_v1.py`, `说明.md` | Same top-level fixed DAG direction projection for the meta valuation wrapper. |

These are protocol-wrapper changes only. The valuation models, feature
engineering, scoring algorithms, data files, data readers, and deployment
configuration were not changed.

## Service Validation

Focused service checks passed:

| Service | Validation |
| --- | --- |
| 传统企业估值智能体 | `python3 -m py_compile service.py tests/test_domain_contract_v1.py`; `python3 -m pytest tests/test_domain_contract_v1.py tests/test_v21_compliance.py -q` |
| 机器学习企业估值智能体 | `python3 -m py_compile service.py tests/test_domain_contract_v1.py`; `python3 -m pytest tests/test_domain_contract_v1.py tests/test_v21_compliance.py tests/test_service_contract.py -q` |
| 元学习企业估值智能体 | `python3 -m py_compile service.py tests/test_domain_contract_v1.py`; `python3 -m pytest tests/test_domain_contract_v1.py tests/test_v21_compliance.py -q` |

## Controlled Restart

Restart log root:

```text
/tmp/lma-r8-13g-value-l2-restart/20260612T033801Z
```

Restarted production services only:

| Agent | Port | Old PID | New PID |
| --- | ---: | ---: | ---: |
| `value_traditional_valuation` | 10000 | 4112136 | 3155393 |
| `value_ml_valuation` | 10001 | 4111981 | 3155489 |
| `value_meta_valuation` | 10002 | 4111666 | 3155705 |

No dev ports were used as production evidence.

## Production Re-smoke

Artifact root:

```text
/tmp/lma-r8-13g-value-l2-resmoke/20260612T033846Z
```

| Agent | Health | Compute | Adapter mapping | Tool stance | Mapped stance |
| --- | --- | --- | --- | ---: | --- |
| `value_traditional_valuation` | pass | pass | pass | 0.0397 | `0.0397` |
| `value_ml_valuation` | pass | pass | pass | -0.000399 | `-0.000399` |
| `value_meta_valuation` | pass | pass | pass | -0.2852 | `-0.2852` |

All three services now map to `conclusion_object_v1` through the main-system
adapter.

## End-to-End Trace

Configured-report E2E artifact:

```text
/tmp/lma-r8-13g-prod-e2e-llm-report/20260612T033912Z
```

The run used:

- default-off external compute demo bridge
- allowlisted production `POST /v1/agent/compute`
- configured report model for final synthesis
- fake placeholder model only for still-unconnected L2 slots
- no `/v1/agent/invoke`

Result:

- Mapped production compute agents: 17.
- Internal LLM placeholder conclusions: 5.
- `value_traditional_valuation`, `value_ml_valuation`, and
  `value_meta_valuation` appeared in the final report as real value-side
  evidence instead of adapter-error conclusions.
- The final report described the value dimension as mixed but usable evidence:
  traditional and meta valuation were slightly positive while ML valuation was
  near neutral/slightly negative.

## Non-Claims

- R8-13G does not call `/v1/agent/invoke`.
- R8-13G does not modify `runtime_bindings.json`.
- R8-13G does not set `live_verified=true`.
- R8-13G does not set `invoke_enabled_by_default=true`.
- R8-13G does not enable default graph calls to production services.
- R8-13G does not prove production business correctness for the valuation
  models.
- R8-13G does not store raw external responses, endpoint URLs, credentials, or
  provider raw output in the repository.

## Remaining Issues

The full demo trace still contains intentional placeholders or low-quality
service outputs for agents that are not yet production-ready:

- `market_fund_manager_behavior`
- `macro_commodity_pricing`
- `macro_index_valuation`
- `macro_sentiment`
- `macro_industry_hotspot`

Those should be remediated in later service-owner phases. R8-13G only closes
the three value L2 `direction_stance_missing` protocol gaps.
