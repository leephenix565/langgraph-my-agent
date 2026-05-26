import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


SCAFFOLD_DIR = Path(__file__).resolve().parents[1]
if str(SCAFFOLD_DIR) not in sys.path:
    sys.path.insert(0, str(SCAFFOLD_DIR))

from service import app  # noqa: E402


client = TestClient(app)


def test_health_schema():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "external_agent_health_v0"
    assert body["status"] == "ok"
    assert body["agent_id"] == "example_external_agent"
    assert body["llm_configured"] is False
    assert body["tools_configured"] is True
    assert body["data_ready"] is True


def test_invoke_ok():
    response = client.post(
        "/v1/agent/invoke",
        json={
            "schema_version": "external_agent_request_v0",
            "request_id": "req_ok",
            "agent_id": "example_external_agent",
            "question": "Return a deterministic scaffold analysis.",
            "language": "en-US",
            "subtask": "Contract test.",
            "options": {"answer_mode": "structured"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "external_agent_response_v0"
    assert body["request_id"] == "req_ok"
    assert body["agent_id"] == "example_external_agent"
    assert body["status"] == "ok"
    assert body["confidence"] == 0.75
    assert body["tool_result"]["example_metric"] == 1.0
    assert body["errors"] == []


def test_needs_clarification():
    response = client.post(
        "/v1/agent/invoke",
        json={
            "schema_version": "external_agent_request_v0",
            "request_id": "req_clarify",
            "question": "This request is ambiguous.",
            "options": {},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert body["confidence"] == 0.2
    assert body["errors"] == []
    assert "specific target" in body["answer"]


def test_typed_error():
    response = client.post(
        "/v1/agent/invoke",
        json={
            "schema_version": "external_agent_request_v0",
            "request_id": "req_error",
            "question": "",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["confidence"] == 0.0
    assert body["errors"][0]["error_code"] == "EMPTY_QUESTION"
    assert body["errors"][0]["stage"] == "request_validation"
    assert body["errors"][0]["recoverable"] is True
    assert body["errors"][0]["retryable"] is False


def test_no_secrets_or_traceback_in_responses():
    responses = [
        client.get("/health").json(),
        client.post(
            "/v1/agent/invoke",
            json={
                "schema_version": "external_agent_request_v0",
                "request_id": "req_ok",
                "question": "Return a deterministic scaffold analysis.",
            },
        ).json(),
        client.post(
            "/v1/agent/invoke",
            json={
                "schema_version": "external_agent_request_v0",
                "request_id": "req_forced",
                "question": "force_error",
            },
        ).json(),
    ]

    text = json.dumps(responses, ensure_ascii=False).lower()
    forbidden = [
        "traceback",
        "api_key",
        "authorization",
        "password",
        "sk-",
        "chain-of-thought",
        "reasoning_content",
    ]
    for token in forbidden:
        assert token not in text

