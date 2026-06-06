# Fixed DAG External Agent Sample Payloads

These samples are documentation examples only. R7-B also includes runnable
sample files under `examples/fixed_dag_external_agent_scaffold/sample_requests/`
for local scaffold tests. Neither the documentation snippets nor the runnable
sample files are active graph state or live service evidence.

Samples use fixed DAG `snake_case` ids. `legacy_agent_id` appears only as an
optional migration note. No sample includes secrets, real endpoints, env var
values, API keys, `value_financial_analysis`, or sentiment-to-risk routing.

## Health Response

```json
{
  "schema_version": "external_agent_health_v0",
  "status": "ok",
  "agent_id": "valuation_ml_service",
  "agent_name": "ML Valuation Service",
  "version": "2026.06.05",
  "capabilities": ["valuation", "structured_response", "point_in_time"],
  "input_modes": ["question", "structured"],
  "output_modes": ["external_agent_response_v0"],
  "llm_configured": false,
  "tools_configured": true,
  "data_ready": true,
  "max_concurrency": 2,
  "timeout_seconds": 30,
  "warnings": []
}
```

## Invoke Request

```json
{
  "schema_version": "external_agent_request_v0",
  "request_id": "req_demo_value_ml_001",
  "agent_id": "valuation_ml_service",
  "question": "Assess the valuation outlook for 600519.SH as of 2026-05-29.",
  "language": "en-US",
  "subtask": "Produce a machine-readable valuation finding.",
  "shared_context": {
    "fixed_dag_agent_id": "value_ml_valuation",
    "legacy_agent_id": "a16_ml_valuation",
    "as_of": "2026-05-29"
  },
  "history": [],
  "router_plan_summary": {},
  "options": {
    "answer_mode": "structured",
    "as_of_date": "2026-05-29",
    "timeout_seconds": 30
  }
}
```

## Invoke Response

```json
{
  "schema_version": "external_agent_response_v0",
  "request_id": "req_demo_value_ml_001",
  "agent_id": "valuation_ml_service",
  "status": "ok",
  "question": "Assess the valuation outlook for 600519.SH as of 2026-05-29.",
  "tool_result": {
    "schema_version": "agent_conclusion_v1",
    "trace_id": "req_demo_value_ml_001",
    "agent_id": "value_ml_valuation",
    "dimension": "价值",
    "role": "direction",
    "target": "600519.SH",
    "as_of": "2026-05-29",
    "data_as_of": "2026-05-29",
    "normalized": {
      "stance": 0.35,
      "confidence": 0.72,
      "label": "moderately_positive"
    },
    "event_flags": [],
    "evidence": [
      {
        "fact": "Valuation model percentile is above its neutral baseline.",
        "source": "local_model_snapshot",
        "data_as_of": "2026-05-29",
        "value": 0.64,
        "unit": "percentile"
      }
    ],
    "quality": {
      "anti_lookahead_passed": true
    },
    "status": "ok",
    "warnings": []
  },
  "answer": "The service produced a structured valuation finding for adapter mapping.",
  "confidence": 0.72,
  "key_points": ["Structured finding is ready for fixed DAG adapter mapping."],
  "evidence": [
    {
      "source": "local_model_snapshot",
      "summary": "Point-in-time model output dated 2026-05-29."
    }
  ],
  "data_sources": [
    {
      "name": "local_model_snapshot",
      "version": "2026-05-29"
    }
  ],
  "warnings": [],
  "errors": []
}
```

## Compute Request

```json
{
  "target": "600519.SH",
  "as_of_date": "2026-05-29",
  "horizon_days": 120,
  "options": {
    "model_version": "demo_model_2026_05"
  }
}
```

## Compute Response

```json
{
  "schema_version": "external_agent_compute_v0",
  "agent_id": "valuation_ml_service",
  "status": "ok",
  "tool_result": {
    "schema_version": "agent_conclusion_v1",
    "trace_id": "compute_demo_value_ml_001",
    "agent_id": "value_ml_valuation",
    "dimension": "价值",
    "role": "direction",
    "target": "600519.SH",
    "as_of": "2026-05-29",
    "data_as_of": "2026-05-29",
    "normalized": {
      "stance": 0.35,
      "confidence": 0.72,
      "label": "moderately_positive"
    },
    "event_flags": [],
    "evidence": [
      {
        "fact": "Point-in-time features are not newer than as_of.",
        "source": "local_feature_snapshot",
        "data_as_of": "2026-05-29"
      }
    ],
    "quality": {
      "anti_lookahead_passed": true,
      "cached": false
    },
    "status": "ok",
    "warnings": []
  },
  "confidence": 0.72,
  "warnings": [],
  "elapsed_ms": 24.2
}
```

## Mapped `conclusion_object_v1`

The main-system adapter maps the external payload into a fixed DAG object like
this:

```json
{
  "schema": "conclusion_object_v1",
  "schema_version": "conclusion_object_v1",
  "agent_id": "value_ml_valuation",
  "dimension": "value",
  "stance": "moderately_positive",
  "confidence": 0.72,
  "status": "complete",
  "evidence": [
    {
      "fact": "Valuation model percentile is above its neutral baseline.",
      "source": "local_model_snapshot",
      "data_as_of": "2026-05-29",
      "value": 0.64,
      "unit": "percentile"
    }
  ],
  "as_of": "2026-05-29",
  "data_as_of": "2026-05-29",
  "event_flags": [],
  "provenance": {
    "source": "external_agent_adapter",
    "fixed_dag_agent_id": "value_ml_valuation",
    "external_agent_id": "valuation_ml_service",
    "legacy_agent_id": "a16_ml_valuation",
    "provider_invoked": false,
    "external_invoked": true
  }
}
```

In docs-only examples, `external_invoked` is illustrative of a mapped live
adapter result. It is not a claim that the current reset mainline invoked an
external service.

## Partial Response

```json
{
  "schema_version": "external_agent_response_v0",
  "request_id": "req_demo_partial_001",
  "agent_id": "valuation_ml_service",
  "status": "partial",
  "question": "Assess the valuation outlook for 600519.SH.",
  "tool_result": {
    "schema_version": "agent_conclusion_v1",
    "trace_id": "req_demo_partial_001",
    "agent_id": "value_ml_valuation",
    "dimension": "价值",
    "role": "direction",
    "target": "600519.SH",
    "as_of": "2026-05-29",
    "data_as_of": "2026-05-29",
    "normalized": {
      "stance": 0.0,
      "confidence": 0.35,
      "label": "incomplete"
    },
    "event_flags": [],
    "evidence": [],
    "quality": {
      "missing_fields": ["latest_model_features"]
    },
    "status": "partial",
    "warnings": ["latest_model_features unavailable at the requested as_of"]
  },
  "answer": "The service returned a partial result because required features were missing.",
  "confidence": 0.35,
  "warnings": ["latest_model_features unavailable at the requested as_of"],
  "errors": []
}
```

## Failure Response

```json
{
  "schema_version": "external_agent_response_v0",
  "request_id": "req_demo_error_001",
  "agent_id": "valuation_ml_service",
  "status": "error",
  "question": "",
  "tool_result": {},
  "answer": "A non-empty target or question is required.",
  "confidence": 0.0,
  "warnings": [],
  "errors": [
    {
      "error_code": "EMPTY_QUESTION",
      "error_message": "question must not be empty",
      "stage": "request_validation",
      "recoverable": true,
      "retryable": false,
      "user_action_required": true,
      "suggested_user_action": "Provide a non-empty question or structured target."
    }
  ]
}
```
