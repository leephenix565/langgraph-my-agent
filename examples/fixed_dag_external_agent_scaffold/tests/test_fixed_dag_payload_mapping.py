"""Mapping tests from external sample payloads to fixed DAG contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from react_agent.fixed_dag_contracts import validate_conclusion_object

SCAFFOLD_DIR = Path(__file__).resolve().parents[1]
if str(SCAFFOLD_DIR) not in sys.path:
    sys.path.insert(0, str(SCAFFOLD_DIR))

import service  # noqa: E402

client = TestClient(service.app)


def _compute_payload(**overrides: object) -> dict[str, object]:
    """Build a valid compute payload with optional overrides."""
    payload: dict[str, object] = {
        "schema_version": "external_agent_request_v0",
        "request_id": "mapping-compute-001",
        "agent_id": service.FIXED_DAG_AGENT_ID,
        "external_agent_id": service.EXTERNAL_AGENT_ID,
        "target": "600519.SH",
        "as_of": "2026-06-05",
        "language": "zh-CN",
        "context": {"dimension": "value", "task": "valuation"},
        "options": {},
    }
    payload.update(overrides)
    return payload


def test_status_mapping_to_fixed_dag_status() -> None:
    """External statuses map to fixed DAG statuses."""
    assert service.external_status_to_fixed_dag_status("ok") == "complete"
    assert service.external_status_to_fixed_dag_status("partial") == "partial"
    assert service.external_status_to_fixed_dag_status("needs_clarification") == "partial"
    assert service.external_status_to_fixed_dag_status("error") == "error"


def test_dimension_mapping_uses_english_contract_enums() -> None:
    """Contract dimensions remain English while labels may be Chinese."""
    assert service.DIMENSION_LABELS == {
        "value": "价值维",
        "market": "市场面维",
        "risk": "风险维",
        "macro": "宏观维",
    }


def test_compute_response_maps_to_valid_conclusion_object() -> None:
    """Sample compute output maps to a valid conclusion_object_v1."""
    response = client.post("/v1/agent/compute", json=_compute_payload()).json()
    mapped = service.map_response_to_conclusion_object(response)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["schema"] == "conclusion_object_v1"
    assert mapped["agent_id"] == "value_ml_valuation"
    assert mapped["dimension"] == "value"
    assert mapped["status"] == "complete"
    assert mapped["evidence"]
    assert mapped["event_flags"]
    assert mapped["provenance"]["provider_invoked"] is False
    assert mapped["provenance"]["external_invoked"] is False


def test_partial_response_maps_to_partial_conclusion_object() -> None:
    """Partial external output remains partial after mapping."""
    response = client.post(
        "/v1/agent/compute",
        json=_compute_payload(
            options={"missing_fields": ["latest_features"]},
        ),
    ).json()
    mapped = service.map_response_to_conclusion_object(response)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["status"] == "partial"
    assert mapped["confidence"] < 0.72


def test_sentiment_company_radar_maps_only_to_market_route() -> None:
    """Sentiment radar receives only market_composite output route."""
    response = client.post(
        "/v1/agent/compute",
        json=_compute_payload(
            agent_id="sentiment_company_radar",
            external_agent_id="sentiment_company_radar_service",
            context={"dimension": "market", "task": "sentiment"},
        ),
    ).json()
    mapped = service.map_response_to_conclusion_object(response)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["dimension"] == "market"
    assert mapped["output_routes"] == ["market_composite"]


def test_sample_requests_do_not_use_main_agent_id() -> None:
    """Sample request files avoid the old main_agent_id field."""
    for path in (SCAFFOLD_DIR / "sample_requests").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rendered = json.dumps(payload, ensure_ascii=False)
        assert "main_agent_id" not in rendered


def test_sample_response_files_match_service_output() -> None:
    """Checked-in sample responses match the deterministic sample service."""
    sample_dir = SCAFFOLD_DIR / "sample_requests"
    compute_request = json.loads(
        (sample_dir / "compute.request.json").read_text(encoding="utf-8")
    )
    invoke_request = json.loads(
        (sample_dir / "invoke.request.json").read_text(encoding="utf-8")
    )
    expected_compute = json.loads(
        (sample_dir / "compute.response.json").read_text(encoding="utf-8")
    )
    expected_invoke = json.loads(
        (sample_dir / "invoke.response.json").read_text(encoding="utf-8")
    )

    assert client.post("/v1/agent/compute", json=compute_request).json() == expected_compute
    assert client.post("/v1/agent/invoke", json=invoke_request).json() == expected_invoke


def test_cache_key_includes_as_of() -> None:
    """Point-in-time date is part of the deterministic cache key."""
    common = {
        "agent_id": service.FIXED_DAG_AGENT_ID,
        "external_agent_id": service.EXTERNAL_AGENT_ID,
        "target": "600519.SH",
        "options": {},
    }
    early = service.make_cache_key(as_of="2026-01-31", **common)
    late = service.make_cache_key(as_of="2026-06-05", **common)

    assert early != late
