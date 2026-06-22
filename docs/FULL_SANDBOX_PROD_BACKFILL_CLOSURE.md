# Full Sandbox-To-Prod Backfill Closure

Date: 2026-06-22

BF-COMPLETE-X uses the change-unit definition of sandbox-to-prod backfill:
current-relevant integration fixes that were formed and validated in sandbox
service work must exist in production as exact, semantically equivalent, or
stricter verified behavior. The denominator is not the 27-agent roster, not a
health-pass count, and not owner-dev durability.

## Baseline

The full audit baseline was:

- in-scope change units: 31
- completed units: 29
- incomplete units: 2
- ratio: 29/31, 93.55%

The two incomplete units were:

- `entity_relation_extractor__entity_relation_bundle_v1`
- `sentiment_company_radar__market_only_wrapper`

## Implemented

`entity_relation_extractor` now has a production runtime package under
`/sdb/dlut/prod/实体关系抽取智能体/entity_relation_agent` with a fixed-DAG
health identity and `entity_relation_bundle_v1` compute wrapper. The deployment
uses port `10017`, the main-system demo registry external id
`entity_relation_agent`, and a provider-free deterministic/degraded path. The
production wrapper does not actively load `.env` files in this phase.

`sentiment_company_radar` now has an import-closed production wrapper under
`/sdb/dlut/prod/企业舆情雷达智能体/company_radar_agent`. The service-local
external id is `company_radar_agent`, matching the R8-8I controlled evidence
and service-local tests. The main-system demo bridge was corrected from
`company_sentiment_radar` to `company_radar_agent`; `runtime_bindings.json` was
not changed. The wrapper remains market-only and rejects fixed-DAG risk
subtasks.

## BF-COMPLETE-X Validation

Local py-compile passed for changed service wrapper files. Controlled live
health and compute checks were run once per service, with a second sentiment
compute attempt after a targeted wrapper degradation fix. Raw bodies were not
retained; artifacts keep only bounded fields and body hashes.

The final controlled trace called 21 demo compute agents and mapped 20. It
failed to map `value_traditional_valuation` because that existing production
service timed out during the trace. Both L4 compute-default agents mapped, the
report input/result validators passed, PublicTurn validation passed, and the
pre-scrub unsafe scan was empty.

## BF-CLOSE-R1 Revalidation

BF-CLOSE-R1 separates backfill scope from post-backfill runtime validation.
The `value_traditional_valuation` timeout was rechecked without modifying
service code or global timeouts:

- `GET /health`: pass.
- `POST /v1/agent/compute` with the current bridge-built request and a
  20-second budget: pass within budget.
- 60-second diagnostic request: not needed.
- Final 21-agent trace: called 21, mapped 21, failed 0.
- L1 external mapped count: 2.
- L4 compute-default mapped both decision/report agents.
- PublicTurn validation passed and the pre-scrub unsafe scan was empty.

## Final Ledger Status

The final change-unit ledger marks all 31 in-scope backfill units as completed
by exact, equivalent, or superseding production behavior.

Backfill scope status: `complete`.

Integrated trace status after BF-CLOSE-R1: `pass`.

Acceptance: `backfill_complete`.

## Non-Claims

- No `/v1/agent/invoke` endpoint was called.
- No provider was called.
- `runtime_bindings.json` was not changed.
- No live flag or invoke-default flag was changed.
- No model, scoring, feature, training, data-source, or fusion algorithm was
  changed.
- No owner-dev repository was modified.
- No `.env` value was inspected or changed.
- No raw endpoint response was retained.
