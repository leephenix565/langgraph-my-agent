import json
from copy import deepcopy
from pathlib import Path

from react_agent.fixed_dag_contracts import (
    validate_conclusion_object,
    validate_data_bundle,
)
from react_agent.fixed_dag_external_adapter import (
    ADAPTER_FAILURE_SCHEMA_VERSION,
    EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION,
    EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION,
    FIXED_DAG_EXTERNAL_ADAPTER_SOURCE,
    map_external_agent_conclusion_to_conclusion_object,
    map_external_compute_envelope_to_fixed_dag_object,
    map_external_data_bundle_to_data_bundle,
    map_external_response_to_fixed_dag_object,
    validate_external_compute_envelope,
    validate_external_response_envelope,
)

SAMPLE_DIR = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "fixed_dag_external_agent_scaffold"
    / "sample_requests"
)


def _sample(name: str) -> dict[str, object]:
    return json.loads((SAMPLE_DIR / name).read_text(encoding="utf-8"))


def _compute_envelope(tool_result: dict[str, object] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION,
        "agent_id": "valuation_ml",
        "external_agent_id": "valuation_ml",
        "status": "ok",
        "confidence": 0.7071,
        "as_of": "20260605",
        "data_as_of": "20260605",
        "warnings": ["Model output is research-only."],
        "errors": [],
    }
    if tool_result is not None:
        payload["tool_result"] = tool_result
    return payload


def _assert_safe_public_payload(payload: dict[str, object]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    for token in (
        "api_key",
        "secret",
        "password",
        "endpoint",
        "default_url",
        "raw_response",
        "raw_provider_response",
        "raw_external_json",
        "traceback",
        "chain-of-thought",
        "chain_of_thought",
    ):
        assert token not in rendered


def test_direction_agent_conclusion_maps_to_valid_conclusion_object() -> None:
    mapped = map_external_agent_conclusion_to_conclusion_object(
        _sample("agent_conclusion.response.json")
    )
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["schema"] == "conclusion_object_v1"
    assert mapped["agent_id"] == "value_ml_valuation"
    assert mapped["dimension"] == "value"
    assert mapped["status"] == "complete"
    assert mapped["stance"] == "0.18"
    assert mapped["evidence"]
    assert mapped["provenance"]["adapter_source"] == FIXED_DAG_EXTERNAL_ADAPTER_SOURCE
    assert mapped["provenance"]["external_agent_id"] == "valuation_ml"
    assert mapped["provenance"]["legacy_agent_id"] == "a16_ml_valuation"
    assert mapped["provenance"]["provider_invoked"] is False
    assert mapped["provenance"]["external_invoked"] is False
    _assert_safe_public_payload(mapped)


def test_external_response_envelope_maps_tool_result() -> None:
    payload = _sample("compute.response.json")
    valid, reason = validate_external_response_envelope(payload)
    mapped = map_external_response_to_fixed_dag_object(payload)
    mapped_valid, mapped_reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert payload["schema_version"] == EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION
    assert mapped_valid, mapped_reason
    assert mapped["agent_id"] == "value_ml_valuation"
    assert mapped["status"] == "complete"
    assert mapped["provenance"]["external_status"] == "ok"


def test_external_compute_envelope_maps_agent_conclusion_tool_result() -> None:
    payload = _compute_envelope(_sample("agent_conclusion.response.json"))
    valid, reason = validate_external_compute_envelope(payload)
    mapped = map_external_response_to_fixed_dag_object(payload)
    mapped_valid, mapped_reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped_valid, mapped_reason
    assert mapped["schema"] == "conclusion_object_v1"
    assert mapped["agent_id"] == "value_ml_valuation"
    assert mapped["status"] == "complete"
    assert mapped["provenance"]["adapter_source"] == FIXED_DAG_EXTERNAL_ADAPTER_SOURCE
    assert mapped["provenance"]["adapter_input_schema"] == EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION
    assert mapped["provenance"]["compute_envelope_status"] == "ok"
    assert mapped["provenance"]["external_agent_id"] == "valuation_ml"
    assert mapped["provenance"]["provider_invoked"] is False
    assert mapped["provenance"]["external_invoked"] is False
    _assert_safe_public_payload(mapped)


def test_external_compute_envelope_without_tool_result_fails_controlled() -> None:
    for tool_result in ("missing", None, {}):
        payload = _compute_envelope()
        payload["tool_result_schema_version"] = "agent_conclusion_v1"
        if tool_result != "missing":
            payload["tool_result"] = tool_result

        valid, reason = validate_external_compute_envelope(payload)
        mapped = map_external_compute_envelope_to_fixed_dag_object(payload)

        assert not valid
        assert reason == "compute_tool_result_missing"
        assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
        assert mapped["reason"] == "compute_tool_result_missing"
        _assert_safe_public_payload(mapped)


def test_external_compute_envelope_anti_lookahead_returns_error_conclusion() -> None:
    tool_result = _sample("agent_conclusion.response.json")
    tool_result["data_as_of"] = "2026-06-06"
    tool_result["as_of"] = "2026-06-05"

    mapped = map_external_response_to_fixed_dag_object(_compute_envelope(tool_result))
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["status"] == "error"
    assert mapped["provenance"]["adapter_failure"] is True
    assert mapped["provenance"]["reason"] == "data_as_of_after_as_of"
    assert mapped["provenance"]["provider_invoked"] is False
    assert mapped["provenance"]["external_invoked"] is False
    _assert_safe_public_payload(mapped)


def test_external_compute_envelope_identity_rejections_return_controlled_failure() -> None:
    legacy = _sample("agent_conclusion.response.json")
    legacy["agent_id"] = "a16_ml_valuation"
    mapped = map_external_response_to_fixed_dag_object(_compute_envelope(legacy))
    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "legacy_agent_id_as_primary"

    unknown = _sample("agent_conclusion.response.json")
    unknown["agent_id"] = "unknown_agent"
    mapped = map_external_response_to_fixed_dag_object(_compute_envelope(unknown))
    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unknown_agent_id"
    _assert_safe_public_payload(mapped)


def test_external_compute_envelope_unsafe_raw_content_does_not_leak() -> None:
    tool_result = _sample("agent_conclusion.response.json")
    tool_result["raw_output"] = {
        "secret": "api_key=abc",
        "safe_metric": 1,
        "endpoint": "http://example.invalid/v1/agent/invoke",
    }
    tool_result["quality"] = {"model_trust": 0.8, "raw_response": "traceback"}
    payload = _compute_envelope(tool_result)
    payload["raw_response"] = "traceback with chain-of-thought"

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["provenance"]["raw_output_keys"] == ["safe_metric"]
    assert mapped["provenance"]["quality_keys"] == ["model_trust"]
    _assert_safe_public_payload(mapped)


def test_health_payload_is_not_treated_as_adapter_success() -> None:
    mapped = map_external_response_to_fixed_dag_object(
        {
            "schema_version": "external_agent_health_v0",
            "agent_id": "financial_data_service",
            "status": "ok",
        }
    )

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unsupported_schema_version"


def test_risk_gate_member_maps_to_validator_legal_conclusion() -> None:
    payload = {
        "schema_version": "agent_conclusion_v1",
        "agent_id": "risk_crash",
        "external_agent_id": "crash_risk",
        "legacy_agent_id": "a23_crash_risk",
        "dimension": "risk",
        "role": "gate_member",
        "risk_score": 0.64,
        "confidence": 0.57,
        "evidence": [
            {
                "fact": "Crash risk signal is elevated before the requested date.",
                "source": "sample_crash_risk_snapshot",
                "as_of": "2026-06-05",
                "data_as_of": "20260605",
                "value": 0.64,
                "unit": "risk_score",
            }
        ],
        "event_flags": [{"type": "risk_manual_review_recommended"}],
        "as_of": "2026-06-06",
        "data_as_of": "20260605",
        "status": "ok",
    }

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["agent_id"] == "risk_crash"
    assert mapped["dimension"] == "risk"
    assert mapped["stance"] == "risk_gate_member"
    assert mapped["status"] == "complete"
    assert mapped["data_as_of"] == "2026-06-05"
    assert mapped["provenance"]["risk_score"] == 0.64
    assert "sentiment_company_radar" not in json.dumps(mapped)


def test_scaffold_unknown_risk_member_returns_controlled_failure() -> None:
    mapped = map_external_agent_conclusion_to_conclusion_object(
        _sample("agent_conclusion.risk_member.response.json")
    )

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unknown_agent_id"
    _assert_safe_public_payload(mapped)


def test_needs_clarification_maps_to_partial() -> None:
    payload = _sample("agent_conclusion.response.json")
    payload["status"] = "needs_clarification"

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["status"] == "partial"
    assert mapped["provenance"]["external_status"] == "needs_clarification"


def test_external_error_maps_to_error_conclusion_for_known_agent() -> None:
    payload = _sample("agent_conclusion.response.json")
    payload["status"] = "error"
    payload["confidence"] = 0.0

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["status"] == "error"
    assert mapped["confidence"] == 0.0


def test_identity_rejections_return_controlled_failure() -> None:
    legacy = _sample("agent_conclusion.response.json")
    legacy["agent_id"] = "a16_ml_valuation"
    assert map_external_agent_conclusion_to_conclusion_object(legacy)["reason"] == (
        "legacy_agent_id_as_primary"
    )

    removed = _sample("agent_conclusion.response.json")
    removed["agent_id"] = "value_financial_analysis"
    assert map_external_agent_conclusion_to_conclusion_object(removed)["reason"] == (
        "forbidden_agent_id"
    )

    unknown = _sample("agent_conclusion.response.json")
    unknown["agent_id"] = "unknown_agent"
    assert map_external_agent_conclusion_to_conclusion_object(unknown)["reason"] == (
        "unknown_agent_id"
    )


def test_sentiment_company_radar_cannot_map_to_risk_dimension() -> None:
    payload = _sample("agent_conclusion.response.json")
    payload["agent_id"] = "sentiment_company_radar"
    payload["external_agent_id"] = "sentiment_company_radar_service"
    payload["dimension"] = "risk"

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "sentiment_company_radar_risk_dimension"


def test_unsafe_raw_output_and_evidence_do_not_leak() -> None:
    payload = _sample("agent_conclusion.response.json")
    payload["raw_output"] = {
        "secret": "api_key=abc",
        "safe_metric": 1,
        "endpoint": "http://example.invalid/v1/agent/invoke",
    }
    payload["quality"] = {
        "model_trust": 0.8,
        "raw_response": "traceback and chain-of-thought",
    }
    payload["evidence"] = [
        {
            "fact": "Safe fact.",
            "source": "safe_source",
            "note": "endpoint=http://example.invalid",
            "as_of": "2026-06-05",
        }
    ]

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["provenance"]["raw_output_keys"] == ["safe_metric"]
    assert mapped["provenance"]["quality_keys"] == ["model_trust"]
    _assert_safe_public_payload(mapped)


def test_data_bundle_maps_to_internal_contract() -> None:
    mapped = map_external_data_bundle_to_data_bundle(_sample("data_bundle.response.json"))
    valid, reason = validate_data_bundle(mapped)

    assert valid, reason
    assert mapped["schema"] == "data_bundle_v1"
    assert mapped["schema_version"] == "data_bundle_v1"
    assert mapped["status"] == "complete"
    assert mapped["as_of"] == "2026-06-05"
    assert mapped["data_as_of"] == "2026-06-05"
    assert mapped["sources"] == ["sample_local_snapshot"]
    assert any("snapshot_id: sample-snapshot-600519-20260605" == note for note in mapped["notes"])
    assert any(note == "feature_key: close" for note in mapped["notes"])
    _assert_safe_public_payload(mapped)


def test_data_bundle_anti_lookahead_returns_controlled_failure() -> None:
    payload = deepcopy(_sample("data_bundle.response.json"))
    payload["data_as_of"] = "2026-06-06"
    payload["as_of"] = "2026-06-05"

    mapped = map_external_data_bundle_to_data_bundle(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "data_as_of_after_as_of"


def test_unsupported_or_bad_envelope_returns_controlled_failure() -> None:
    error_payload = _sample("error.response.json")
    mapped = map_external_response_to_fixed_dag_object(error_payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unsupported_tool_result_schema"

    missing = deepcopy(_sample("compute.response.json"))
    missing.pop("confidence")
    mapped = map_external_response_to_fixed_dag_object(missing)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "missing_confidence"


def test_adapter_module_has_no_http_call_path() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "react_agent"
        / "fixed_dag_external_adapter.py"
    ).read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source
    assert "TestClient" not in source
    assert "external_http_agents" not in source
