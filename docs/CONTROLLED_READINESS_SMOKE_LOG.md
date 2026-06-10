# Controlled Readiness Smoke Log

This log records sanitized controlled readiness evidence for fixed-DAG external
service candidates. It is not public transcript content and must not include raw
service responses, credentials, traceback text, provider raw responses, or
chain-of-thought.

## 2026-06-10 - R8-8D-ID value_ml_valuation

| Field | Value |
| --- | --- |
| Phase | R8-8D-ID |
| Run UTC | 2026-06-10T03:06:55Z |
| Artifact directory | `/tmp/lma-r8-8d-id-value-ml-resmoke/20260610T030655Z` |
| Fixed DAG agent id | `value_ml_valuation` |
| External service id | `valuation_ml` |
| Payload family | `external_agent_compute_v0` with `agent_conclusion_v1` tool result |
| Health status | pass |
| Compute status | pass |
| Adapter mapping status | pass |
| Adapter output family | `conclusion_object_v1` |

Service patch summary:

- Dev service source root:
  `/sdb/dlut/dev/机器学习企业估值智能体`.
- Service project was not a usable git repository during remediation; original
  files were backed up outside the repo under
  `/tmp/lma-r8-8d-id-backup/20260610T030433Z`.
- Response identity was remediated only for the dev service compute response:
  top-level and nested tool-result fixed-DAG id are `value_ml_valuation`, and
  external service id is `valuation_ml`.
- The main-system adapter identity gate was not relaxed.
- Dev service tests passed before re-smoke:
  `python3 -m py_compile service.py tests/test_v21_compliance.py`,
  `python3 -m pytest tests/test_v21_compliance.py -q`, and
  `python3 -m pytest tests/test_service_contract.py -q`.
- The dev 8001 process was restarted with the original uvicorn command because
  it was not running in reload mode.

Non-claims:

- This is not `live_verified=true`.
- This does not enable runtime bindings.
- This does not set `invoke_enabled_by_default=true`.
- This does not call `/v1/agent/invoke`.
- This does not update public transcript content.
- This does not prove production readiness.
- This does not authorize default runtime invocation.
- This does not cover prod service ports.

Next gate recommendation:

- Keep `value_ml_valuation` disabled in runtime bindings until a later explicit
  invoke-readiness and runtime-binding phase.
- Continue next controlled smoke work on dev ports only, using `/health` and
  `/v1/agent/compute` before any `/v1/agent/invoke` approval.
