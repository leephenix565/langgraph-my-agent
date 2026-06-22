# CS1-C1X Accelerated Bulk Remediation

Date: 2026-06-22

This phase remediated a narrow readiness slice after CS1-B2X. It changed the
main-system health/temporal boundary, applied file-level production wrapper
patches for four gated services, recovered the two L4 compute-only listeners,
and ran a sanitized full-logical-DAG compute trace.

## Scope

Implemented:

- Main-system health identity validation policy in
  `src/react_agent/fixed_dag_external_health.py`.
- Main-system request `as_of` anti-lookahead guard in
  `src/react_agent/fixed_dag_external_compute_bridge.py`.
- Production wrapper patches for:
  - `market_stock_technical`
  - `macro_analysis`
  - `market_ipo_investor_behavior`
  - `value_composite`
- Controlled restarts for those four services.
- Controlled startup for L4 compute-only services:
  - `decision_synthesizer`
  - `report_generator`
- A sanitized full-logical-DAG trace artifact under:
  `/tmp/lma-cs1c1x-bulk-remediation-20260622T081402Z`.

Not implemented:

- No `/v1/agent/invoke` call.
- No `runtime_bindings.json` change.
- No `live_verified` or `invoke_enabled_by_default` flag change.
- No model, scoring, threshold, feature, training, data-source, or fusion
  algorithm change.
- No provider call.
- No `.env` value inspected or changed.
- No raw service response retained in repository artifacts.

## Health Identity Policy

The new health-only validator accepts three explicit profiles:

- `canonical`: `agent_id` is the formal fixed-DAG id. If
  `fixed_dag_agent_id` is present, it must match the formal id.
- `explicit_bridge_compatibility`: `fixed_dag_agent_id` is the formal id, and
  service-local `agent_id` or `external_agent_id` matches the source-controlled
  alias registry.
- `registered_legacy_compatibility`: no formal id field is present, but the
  observed `agent_id` matches a unique source-controlled health alias, and the
  caller has already verified expected port and source directory.

Compatibility pass is migration debt. It is not a canonical service contract,
not compute evidence, not adapter evidence, not invoke evidence, and not
runtime enablement. The compute adapter identity gate remains strict and was
not relaxed.

Rejected cases include formal-id mismatch, unregistered service-local ids,
ambiguous aliases, source mismatch, legacy `aNN` ids used as primary formal ids,
and any attempt to classify `sentiment_company_radar` as a risk agent.

## Request-As-Of Temporal Boundary

The bridge now fail-closes mapped external compute results when a date-bearing
response is after the requested fixed-DAG `as_of`.

Checked fields:

- `mapped.as_of <= requested_as_of`
- `mapped.data_as_of <= requested_as_of`

The guard runs after adapter mapping and before mapped objects enter executor
state or report bundles. It also rejects raw response dates before mapping when
safe date fields are visible in the external envelope.

Bounded failure reasons:

- `response_as_of_after_requested_as_of`
- `response_data_as_of_after_requested_as_of`
- `response_as_of_invalid_for_requested_as_of`

If `requested_as_of` is unavailable, existing compatibility behavior is kept.
No dates are fabricated for contracts that do not carry date fields.

## Main-System Files

Changed source/test files:

- `src/react_agent/fixed_dag_external_health.py`
- `src/react_agent/fixed_dag_external_compute_bridge.py`
- `tests/unit_tests/test_fixed_dag_external_health.py`
- `tests/unit_tests/test_fixed_dag_external_compute_bridge.py`

Focused validation:

```text
166 passed in 8.23s
```

The focused test set covered health identity profiles, external adapter
contracts, compute bridge temporal guards, executor, contracts, runtime
registry, public mapping, and fixed-DAG docs reset tests.

Full reset mainline validation passed with the repository virtual environment:
static checks, unit tests, public API integration tests, graph smoke tests, and
frontend typecheck/smoke/repo-external build.

## Production Service Patches

Backup root:

```text
/sdb/dlut/prod/backups/cs1c1x_20260622T081402Z
```

Changed production service files and current hashes:

| agent_id | file | after sha256 |
| --- | --- | --- |
| `market_stock_technical` | `service.py` | `a58686701588c8536c94e2a659b129a497684f4de89c9348429bdf75bc144311` |
| `market_stock_technical` | `schemas.py` | `f2a19c8d8882df89daf837e23eb5e07471587bd88ecfeaabbaf2159c64f18df5` |
| `market_stock_technical` | `tests/test_compute_endpoint.py` | `dc6c1042df66333fca675b88d28582de5baf5a6abbc6c9bed379c931506f8ac3` |
| `macro_analysis` | `service.py` | `ccad32a30e851d2a8c0ae3fc586704563ef1a80f1baaa92ef3dde1287743d50f` |
| `macro_analysis` | `tests/test_compute_endpoint.py` | `9bb6a8443869261a189fb620fcf37fe00a4ccaf5b55d1d2bd1fae155c2977cfc` |
| `market_ipo_investor_behavior` | `service.py` | `12914963349646c855b5330e6621826d6200acb49afb7b2958c77473f4588f8a` |
| `market_ipo_investor_behavior` | `schemas.py` | `df9180568488f66c4cd96108fbf71d98ad13252b1d42400e24502584b379f4ba` |
| `market_ipo_investor_behavior` | `tests/test_health_identity.py` | `b78f9744025afef7cbcb2aa9661fd38aa5e191528c4314e240cfcabc07354239` |
| `value_composite` | `service.py` | `729015e4f1570cfe75f55a988032a408f09a4224572edd42f5ee289dc2dbcb5f` |

Patch meanings:

- `market_stock_technical`: accepts top-level fixed-DAG `as_of` and preserves
  anti-lookahead behavior for historical requests.
- `macro_analysis`: accepts top-level/options/context `as_of` and prevents the
  service runtime day from overriding the request boundary.
- `market_ipo_investor_behavior`: fixes `/health` identity to expose formal
  `market_ipo_investor_behavior` while preserving service-local identity as
  external/legacy metadata. It does not change compute behavior.
- `value_composite`: fixes `/health`, canonical value member ids, value
  upstream member projection, compute envelope schema/status, and response
  wrapper defaults. It does not change valuation fusion logic.

Service-local validation:

- `market_stock_technical`: `26 passed`.
- `macro_analysis`: `14 passed`.
- `market_ipo_investor_behavior`: `2 passed`.
- `value_composite`: `5 passed` after the final wrapper patch.

## Restarts

Restart manifest:

```text
/tmp/lma-cs1c1x-bulk-remediation-20260622T081402Z/process_restart_manifest.json
```

Restarted or started ports:

- `10009` `market_stock_technical`
- `10014` `macro_analysis`
- `10008` `market_ipo_investor_behavior`
- `10015` `value_composite`
- `10025` `decision_synthesizer`
- `10026` `report_generator`

`value_composite` required two additional controlled restarts after wrapper
contract fixes uncovered by the integrated trace. The final PID recorded in the
manifest is the active post-fix process.

## Health Evidence

Health artifact:

```text
/tmp/lma-cs1c1x-bulk-remediation-20260622T081402Z/health_results.json
```

Canonical health pass:

- `market_ipo_investor_behavior`
- `value_composite`
- `market_stock_technical`
- `macro_analysis`
- `decision_synthesizer`
- `report_generator`

Compatibility health pass:

- `value_traditional_valuation`
- `value_ml_valuation`
- `value_meta_valuation`
- `risk_crash`
- `risk_financial_fraud`
- `risk_identification`
- `risk_compliance_review`
- `macro_commodity_pricing`
- `risk_composite`
- `macro_composite`

No health target failed in the CS1-C1X re-audit. Compatibility pass agents keep
compatibility debt until their service contracts are made canonical.

## Integrated Trace

Trace artifact:

```text
/tmp/lma-cs1c1x-bulk-remediation-20260622T081402Z/integrated_trace.json
```

Configuration:

- Question: `请基于截至 2024-12-31 的可用信息，分析贵州茅台 600519.SH 的估值、市场、风险和宏观环境，并明确数据与证据边界。`
- Fixed-DAG `as_of`: `2024-12-31`
- `enable_selected_routing=false`
- `enable_internal_llm_placeholders=false`
- `enable_external_compute_demo=true`
- `enable_llm_l3_explanation=false`
- `enable_llm_report_synthesis=false`
- `disable_external_compute_default=false`
- Provider calls: `0`

Demo compute:

- Called `17` allowlisted L1/L2/L3 compute endpoints.
- Mapped `12`.
- Failed closed `5`.

Mapped demo agents:

- `financial_data_service`
- `value_research_synthesis`
- `market_stock_technical`
- `risk_financial_fraud`
- `risk_identification`
- `risk_compliance_review`
- `macro_analysis`
- `macro_commodity_pricing`
- `macro_index_valuation`
- `value_composite`
- `risk_composite`
- `macro_composite`

Fail-closed demo agents:

- `value_traditional_valuation`: `response_as_of_after_requested_as_of`
- `value_ml_valuation`: `response_as_of_after_requested_as_of`
- `value_meta_valuation`: `response_as_of_after_requested_as_of`
- `risk_crash`: `response_as_of_after_requested_as_of`
- `market_ipo_investor_behavior`: compute route/runtime blocker remains

L4 compute-default:

- Called `decision_synthesizer` and `report_generator`.
- Mapped both.
- Failed none.

Report validators:

- `report_input_bundle_v1`: pass.
- `report_result_v1`: produced by the controlled trace and retained as
  sanitized artifact.
- `workflow_snapshot_v2`: produced and retained as sanitized artifact.

## Rollback

Main-system rollback:

- Revert the CS1-C1X main-system commit.
- No runtime binding rollback is required because runtime bindings were not
  changed.

Service rollback:

- Restore the changed service files from
  `/sdb/dlut/prod/backups/cs1c1x_20260622T081402Z/<agent_id>/`.
- Restart only the corresponding service port after restoring files.
- Stop only the CS1-C1X-started L4 PIDs if L4 recovery needs to be undone.

Owner durability:

- Production service patches are not committed into the main-system repo.
- Owner-dev repositories were not modified by this phase.
- Owner handoff material is recorded in the CS1-C1X artifact directory.

## Remaining Blockers

- `market_ipo_investor_behavior` health is canonical, but current production
  compute still fails the integrated trace. This phase did not change its
  business compute path.
- `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, and `risk_crash` fail closed on request-as-of
  temporal integrity for the 2024-12-31 trace. They must not be counted as real
  2024 evidence until service-side date semantics are fixed.
- `entity_relation_extractor`, `market_fund_manager_behavior`,
  `market_capital_flow_chip`, `sentiment_company_radar`, `macro_sentiment`,
  `macro_industry_hotspot`, and `market_composite` were not included in the
  accelerated compute allowlist.

## Non-Claims

- CS1-C1X does not prove `/v1/agent/invoke` readiness.
- CS1-C1X does not enable non-L4 external services by default.
- CS1-C1X does not change the 27-agent roster.
- CS1-C1X does not prove provider-backed report synthesis.
- CS1-C1X does not prove all 27 external services are healthy or compute-ready.
- CS1-C1X does not make compatibility health profiles canonical.
