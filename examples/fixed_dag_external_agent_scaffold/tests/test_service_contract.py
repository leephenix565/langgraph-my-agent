"""Local tests for the sample fixed DAG external-agent service."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

SCAFFOLD_DIR = Path(__file__).resolve().parents[1]
if str(SCAFFOLD_DIR) not in sys.path:
    sys.path.insert(0, str(SCAFFOLD_DIR))

import service  # noqa: E402

client = TestClient(service.app)


def _compute_payload(**overrides: object) -> dict[str, object]:
    """Build a valid compute payload with optional overrides."""
    payload: dict[str, object] = {
        "schema_version": "external_agent_request_v0",
        "request_id": "test-compute-001",
        "agent_id": service.FIXED_DAG_AGENT_ID,
        "external_agent_id": service.EXTERNAL_AGENT_ID,
        "legacy_agent_id": service.LEGACY_AGENT_ID,
        "target": "600519.SH",
        "as_of": "2026-06-05",
        "language": "zh-CN",
        "context": {"dimension": "value", "task": "valuation"},
        "options": {},
    }
    payload.update(overrides)
    return payload


def _invoke_payload(**overrides: object) -> dict[str, object]:
    """Build a valid invoke payload with optional overrides."""
    payload = _compute_payload(request_id="test-invoke-001")
    payload["question"] = "Evaluate 600519.SH with the sample valuation agent."
    payload.update(overrides)
    return payload


def test_health_schema_is_safe_and_sample_only() -> None:
    """Health exposes safe metadata and no active runtime claim."""
    response = client.get("/health")
    body = response.json()

    assert response.status_code == 200
    assert body["schema_version"] == "external_agent_health_v0"
    assert body["status"] == "ok"
    assert body["agent_id"] == "value_ml_valuation"
    assert body["external_agent_id"] == "valuation_ml"
    assert body["legacy_agent_id"] == "a16_ml_valuation"
    assert body["llm_configured"] is False
    assert body["tools_configured"] is False
    assert "sample-only" in " ".join(body["warnings"])
    assert "fixed_dag_external_scaffold" in body["capabilities"]


def test_compute_success_returns_mappable_conclusion() -> None:
    """Compute returns an agent_conclusion_v1 tool_result."""
    response = client.post("/v1/agent/compute", json=_compute_payload())
    body = response.json()
    tool_result = body["tool_result"]

    assert response.status_code == 200
    assert body["schema_version"] == "external_agent_response_v0"
    assert body["request_id"] == "test-compute-001"
    assert body["legacy_agent_id"] == "a16_ml_valuation"
    assert body["status"] == "ok"
    assert body["confidence"] == tool_result["confidence"]
    assert 0.0 <= body["confidence"] <= 1.0
    assert tool_result["schema_version"] == "agent_conclusion_v1"
    assert tool_result["agent_id"] == "value_ml_valuation"
    assert tool_result["dimension"] == "value"
    assert tool_result["data_as_of"] <= tool_result["as_of"]
    assert tool_result["evidence"]
    assert isinstance(tool_result["event_flags"], list)


def test_invoke_success_uses_same_core_result() -> None:
    """Invoke is only an explanation shell over compute_core."""
    compute_body = client.post("/v1/agent/compute", json=_compute_payload()).json()
    invoke_body = client.post("/v1/agent/invoke", json=_invoke_payload()).json()

    assert invoke_body["status"] == "ok"
    assert invoke_body["answer"]
    assert invoke_body["tool_result"] == compute_body["tool_result"]
    assert "provider" in " ".join(invoke_body["key_points"])


def test_request_id_roundtrip() -> None:
    """Both endpoints preserve request_id."""
    compute_body = client.post(
        "/v1/agent/compute",
        json=_compute_payload(request_id="roundtrip-compute"),
    ).json()
    invoke_body = client.post(
        "/v1/agent/invoke",
        json=_invoke_payload(request_id="roundtrip-invoke"),
    ).json()

    assert compute_body["request_id"] == "roundtrip-compute"
    assert invoke_body["request_id"] == "roundtrip-invoke"


def test_as_of_changes_data_window_and_keeps_anti_lookahead() -> None:
    """Different as_of values produce matching data_as_of values."""
    early = client.post(
        "/v1/agent/compute",
        json=_compute_payload(request_id="early", as_of="2026-01-31"),
    ).json()
    late = client.post(
        "/v1/agent/compute",
        json=_compute_payload(request_id="late", as_of="2026-06-05"),
    ).json()

    assert early["tool_result"]["data_as_of"] == "2026-01-31"
    assert late["tool_result"]["data_as_of"] == "2026-06-05"
    assert early["tool_result"]["data_as_of"] <= early["tool_result"]["as_of"]
    assert late["tool_result"]["data_as_of"] <= late["tool_result"]["as_of"]


def test_partial_degradation_lowers_confidence_and_warns() -> None:
    """Missing fields return partial status with lower confidence."""
    full = client.post("/v1/agent/compute", json=_compute_payload()).json()
    degraded = client.post(
        "/v1/agent/compute",
        json=_compute_payload(
            request_id="degraded",
            options={"missing_fields": ["pe_ratio", "cash_flow"]},
        ),
    ).json()

    assert degraded["status"] == "partial"
    assert degraded["confidence"] < full["confidence"]
    assert degraded["warnings"]
    assert degraded["tool_result"]["warnings"]


def test_idempotent_for_same_structured_input() -> None:
    """Same structured input returns the same structured result."""
    payload = _compute_payload(request_id="idempotent")
    first = client.post("/v1/agent/compute", json=payload).json()
    second = client.post("/v1/agent/compute", json=payload).json()

    assert first["tool_result"] == second["tool_result"]
    assert first["confidence"] == second["confidence"]


def test_ann_primary_id_is_rejected_without_sensitive_leakage() -> None:
    """Old aNN ids cannot be used as primary fixed DAG agent ids."""
    response = client.post(
        "/v1/agent/compute",
        json=_compute_payload(agent_id="a16_ml_valuation"),
    )
    body = response.json()
    rendered = json.dumps(body, ensure_ascii=False).lower()

    assert response.status_code == 200
    assert body["status"] == "error"
    assert body["errors"][0]["error_code"] == "LEGACY_AGENT_ID_AS_PRIMARY"
    assert "traceback" not in rendered
    assert "secret" not in rendered
    assert "provider raw" not in rendered


def test_empty_question_error_is_typed_and_safe() -> None:
    """Invoke returns a typed error for empty questions."""
    body = client.post(
        "/v1/agent/invoke",
        json=_invoke_payload(question=""),
    ).json()
    rendered = json.dumps(body, ensure_ascii=False).lower()

    assert body["status"] == "error"
    assert body["errors"][0]["error_code"] == "EMPTY_QUESTION"
    assert "traceback" not in rendered
    assert "secret" not in rendered


def test_sample_never_calls_provider_or_external_service() -> None:
    """The sample service is local-only."""
    client.post("/v1/agent/compute", json=_compute_payload())
    client.post("/v1/agent/invoke", json=_invoke_payload())

    assert service.PROVIDER_CALL_COUNT == 0
    assert service.EXTERNAL_CALL_COUNT == 0
