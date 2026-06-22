# CS1-C2X Temporal Market Public Closure

Date: 2026-06-22

Artifact root:

```text
/tmp/lma-cs1c2x-temporal-market-public-20260622T092218Z
```

## Scope

CS1-C2X closes the CS1-C1X public-turn and temporal-readiness gaps, repairs
the next market path slice, and runs a new controlled full logical DAG trace.

In scope:

- main-system request `as_of` projection for external compute requests;
- public workflow provenance wording that must be safe before artifact scrub;
- production wrapper fixes for `value_traditional_valuation`,
  `value_ml_valuation`, `value_meta_valuation`, `risk_crash`, and
  `market_ipo_investor_behavior`;
- controlled listener recovery for `market_capital_flow_chip` and
  `market_composite`;
- sanitized health, compute, adapter, PublicTurn, and integrated trace
  artifacts.

Out of scope:

- external agent invoke calls;
- provider calls;
- runtime binding changes;
- live flag changes;
- model, scoring, threshold, feature, training, data-source, or fusion
  algorithm changes;
- semantic-deferred macro agents;
- owner-dev repository writes.

## Main-System Changes

`fixed_dag_external_compute_bridge.py` now projects the same requested `as_of`
into top-level `as_of`, top-level `as_of_date`, `context.as_of`,
`context.as_of_date`, `options.as_of`, and `options.as_of_date`. This keeps the
request boundary explicit for services that were migrated at different times.

`fixed_dag_executor.py` no longer emits the literal external invoke path in L4
runtime-default workflow limitations. The same non-claim is preserved as
human-readable text without an endpoint string, so PublicTurn/Workflow can pass
unsafe scanning before artifact scrub.

The compute adapter identity gate remains strict. Health compatibility policy
from CS1-C1X was not extended to compute results.

## Service Changes

Changed production wrapper files:

- `/sdb/dlut/prod/传统企业估值智能体/service.py`
- `/sdb/dlut/prod/机器学习企业估值智能体/service.py`
- `/sdb/dlut/prod/元学习企业估值智能体/service.py`
- `/sdb/dlut/prod/股价崩盘风险智能体/crash_risk_model/agent/protocol.py`
- `/sdb/dlut/prod/股价崩盘风险智能体/crash_risk_model/agent/app.py`
- `/sdb/dlut/prod/IPO投资者行为智能体/service.py`

Backups:

```text
/sdb/dlut/prod/backups/cs1c2x_20260622T093703Z
```

Temporal services now consume the requested historical `as_of` through
compatible aliases and no longer mask future `data_as_of` by relabeling the
response `as_of`. If a future-dated output appears, the main-system temporal
guard remains fail-closed.

`market_ipo_investor_behavior` now exposes production
`POST /v1/agent/compute` on the root FastAPI app. The route reuses the
service's current deterministic data/core path and projects a fixed-DAG
`agent_conclusion_v1` with `agent_id=market_ipo_investor_behavior`,
`dimension=market`, and `role=direction`.

`market_capital_flow_chip` was restored on port `10022` without code changes.
The first start inherited `PORT=8022`; the operator stopped that new PID and
restarted the same service with `PORT=10022`.

`market_composite` was restored on port `10023` without code changes. It maps
as a partial L3 result when market members are missing.

## Controlled Evidence

Controlled health and compute were run only for services changed or restored in
this phase. Sanitized results are in:

```text
/tmp/lma-cs1c2x-temporal-market-public-20260622T092218Z/health_compute_results.json
```

Results:

- `value_traditional_valuation`: health ok, compute ok, adapter complete,
  `as_of=2024-12-31`, `data_as_of=2024-12-31`.
- `value_ml_valuation`: health ok, compute ok, adapter complete,
  `as_of=2024-12-31`, `data_as_of=2024-12-31`.
- `value_meta_valuation`: health ok, compute ok, adapter complete,
  `as_of=2024-12-31`, `data_as_of=2024-12-31`.
- `risk_crash`: health ok, compute ok, adapter complete,
  `as_of=2024-12-31`, `data_as_of=2024-12-31`.
- `market_ipo_investor_behavior`: health ok, compute ok, adapter complete,
  `as_of=2024-12-31`, `data_as_of=2024-12-31`.
- `market_capital_flow_chip`: health ok, compute ok, adapter complete,
  `as_of=2024-12-31`, `data_as_of=2024-12-31`.
- `market_composite`: health ok, compute partial, adapter partial,
  `as_of=2024-12-31`, `data_as_of=2024-06-28`.

## Full Logical Trace

The C2X trace used:

- question:
  `请基于截至 2024-12-31 的可用信息，分析贵州茅台 600519.SH 的估值、市场、风险和宏观环境，并明确数据与证据边界。`
- `fixed_dag_as_of=2024-12-31`;
- default-off external compute demo bridge with explicit allowlist;
- L4 compute-default runtime for `decision_synthesizer` and
  `report_generator`;
- no provider calls.

Trace result:

- logical workflow step count: `27`;
- demo compute called: `19`;
- demo compute mapped: `19`;
- demo compute failed: `0`;
- temporal rejected agents: `[]`;
- L4 compute-default called: `decision_synthesizer`, `report_generator`;
- L4 compute-default mapped: `decision_synthesizer`, `report_generator`;
- `report_input_bundle_v1` validation: pass;
- PublicTurn validation: pass;
- public unsafe scan before scrub: pass.

Artifact files:

- `integrated_trace.json`
- `public_turn.json`
- `per_agent_failure_map.json`
- `health_compute_results.json`
- `integrated_trace_artifacts/workflow_trace.json`
- `integrated_trace_artifacts/report_input_bundle.json`
- `integrated_trace_artifacts/report_result.json`
- `final_report.md`

## Blockers

`market_fund_manager_behavior` remains blocked on source/owner discovery. It
was not restored in CS1-C2X.

`sentiment_company_radar` remains blocked because production lacks a complete
market-only service wrapper at the expected port. It must remain market-only
and must not be routed into risk.

`market_composite` therefore remains partial when those members are absent.

## Rollback

Service rollback sources are the file-level backups under:

```text
/sdb/dlut/prod/backups/cs1c2x_20260622T093703Z
```

After restoring a service file, restart only that service's PID/port. Do not
restart unrelated agents or the full stack.

## Non-Claims

- No external agent invoke endpoint was called.
- No provider was called.
- `runtime_bindings.json` was not changed.
- `live_verified` and `invoke_enabled_by_default` were not changed.
- No model, scoring, threshold, feature, training, data-source, or fusion
  algorithm was changed.
- No `.env` value was inspected or changed.
- Raw endpoint responses were not retained in repository artifacts.
