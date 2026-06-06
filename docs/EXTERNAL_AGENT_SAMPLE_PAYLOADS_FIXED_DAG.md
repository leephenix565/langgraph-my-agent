# Fixed DAG External Agent Sample Payloads

These samples are documentation examples only. R7-F keeps runnable sample files
under `examples/fixed_dag_external_agent_scaffold/sample_requests/` for local
scaffold tests. Neither the documentation snippets nor the runnable sample
files are active graph state or live service evidence.

Samples use fixed DAG `snake_case` ids. `legacy_agent_id` appears only as an
optional migration note. No sample includes secrets, real endpoints, env var
values, API keys, `value_financial_analysis`, or sentiment-to-risk routing.

## Runnable Sample File Set

The repo mirror contains endpoint samples:

- `health.expected.json`
- `compute.request.json`
- `compute.response.json`
- `invoke.request.json`
- `invoke.response.json`
- `error.response.json`

It also contains v2.3 domain payload samples:

- `agent_conclusion.response.json`
- `dimension_conclusion.response.json`
- `risk_conclusion.response.json`
- `macro_conclusion.response.json`
- `decision_conclusion.response.json`
- `eval_record.response.json`
- `data_bundle.response.json`
- `fixed_dag_plan.response.json`

All domain payload samples are expected to pass `validate_tool_result`.

## Canonical Request Identity

Use three ids:

```json
{
  "agent_id": "value_ml_valuation",
  "external_agent_id": "valuation_ml",
  "legacy_agent_id": "a16_ml_valuation"
}
```

`agent_id` is the fixed DAG primary id. `external_agent_id` is the service id.
`legacy_agent_id` is only a migration note. Do not use `main_agent_id` or an old
aNN id as the primary path.

## Endpoint Response Example

The default service returns `agent_conclusion_v1` from `/compute` and `/invoke`.
The response envelope shape is:

```json
{
  "schema_version": "external_agent_response_v0",
  "request_id": "sample-compute-001",
  "agent_id": "value_ml_valuation",
  "external_agent_id": "valuation_ml",
  "legacy_agent_id": "a16_ml_valuation",
  "status": "ok",
  "answer": "",
  "key_points": [],
  "tool_result": {
    "schema_version": "agent_conclusion_v1",
    "agent_id": "value_ml_valuation",
    "external_agent_id": "valuation_ml",
    "legacy_agent_id": "a16_ml_valuation",
    "dimension": "value",
    "role": "direction",
    "target": "600519.SH",
    "stance": -0.4,
    "confidence": 0.72,
    "label": "slightly_negative",
    "evidence": [
      {
        "fact": "Deterministic sample feature set is bounded by as_of.",
        "source": "sample_local_snapshot",
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "publish_time": "2026-06-05"
      }
    ],
    "event_flags": [
      {
        "type": "sample_point_in_time_check",
        "severity": 0.1,
        "direction": "neutral",
        "as_of": "2026-06-05"
      }
    ],
    "as_of": "2026-06-05",
    "data_as_of": "2026-06-05",
    "status": "ok"
  },
  "confidence": 0.72,
  "warnings": [],
  "errors": []
}
```

## Payload Family Examples

Use the checked-in JSON files as the complete source for field examples. The
intent is:

| File | Schema | Purpose |
| --- | --- | --- |
| `agent_conclusion.response.json` | `agent_conclusion_v1` | L2 analysis result. |
| `dimension_conclusion.response.json` | `dimension_conclusion_v1` | L3 value/market composite with members and weights. |
| `risk_conclusion.response.json` | `risk_conclusion_v1` | L3 risk gate with no `stance`. |
| `macro_conclusion.response.json` | `macro_conclusion_v1` | L3 macro regulator with `dimension_weights` and no `stance`. |
| `decision_conclusion.response.json` | `decision_conclusion_v1` | L4 decision with reasoning trace and calculation trace. |
| `eval_record.response.json` | `eval_record_v1` | Evaluation or replay metric record. |
| `data_bundle.response.json` | `data_bundle_v1` | L1 point-in-time data bundle with `snapshot_id`. |
| `fixed_dag_plan.response.json` | `fixed_dag_plan_v1` | Route or plan payload. |

## Validator Expectations

Samples should satisfy:

- canonical English dimensions in checked-in outputs
- migration alias normalization for Chinese dimension inputs
- `data_as_of <= as_of`
- `publish_time <= as_of`
- confidence in `[0, 1]`
- evidence present for successful evidence-bearing payloads
- risk uses `role=gate` and has no `stance`
- macro uses `role=regulator` and has no `stance`
- value/market weights sum to one
- decision reasoning trace has at least three stages
- decision `score` matches `calculation_trace.final_score`
- data bundle includes `snapshot_id`

## Failure Response

`error.response.json` demonstrates typed error shape and safe rejection of old
aNN primary ids. It is a negative example and should not be copied into a valid
request.

## Non-Claims

The sample payloads do not prove:

- live external service readiness
- provider readiness
- runtime binding acceptance
- production deployment readiness
- business correctness
