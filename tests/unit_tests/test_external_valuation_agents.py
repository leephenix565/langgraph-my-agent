import anyio
import httpx

from react_agent.external_http_agents import (
    EXTERNAL_HTTP_AGENT_CONFIG,
    build_external_http_agent_request,
    build_external_http_tool,
    map_external_http_response_to_agent_output,
)

VALUATION_EXTERNAL_HTTP_CONFIG = {
    "a16_ml_valuation": (
        "valuation_ml",
        "VALUATION_ML_AGENT_URL",
        "http://222.73.85.26:10001/v1/agent/invoke",
    ),
    "a17_traditional_valuation": (
        "valuation_traditional",
        "VALUATION_TRADITIONAL_AGENT_URL",
        "http://222.73.85.26:10000/v1/agent/invoke",
    ),
    "a18_meta_valuation": (
        "valuation_meta",
        "VALUATION_META_AGENT_URL",
        "http://222.73.85.26:10002/v1/agent/invoke",
    ),
}


def test_build_external_http_request_uses_valuation_mapping(monkeypatch) -> None:
    monkeypatch.setenv("EXTERNAL_AGENT_TIMEOUT_SECONDS", "12")
    request = build_external_http_agent_request(
        agent_id="a16_ml_valuation",
        question="value the company",
        subtask="valuation analysis",
        shared_context={
            "messages": ["raw should not leak"],
            "layer_plan": {"L3": ["a16_ml_valuation"]},
        },
        router_plan_summary="L3: a16_ml_valuation",
    )
    assert request["schema_version"] == "external_agent_request_v0"
    assert request["language"] == "en"
    assert request["options"]["external_agent_id"] == "valuation_ml"
    assert request["options"]["timeout_seconds"] == 12.0
    assert request["context"]["main_agent_id"] == "a16_ml_valuation"
    assert request["context"]["external_agent_id"] == "valuation_ml"
    assert "messages" not in request["context"]["shared_context_summary"]


def test_valuation_external_http_config_uses_csv_prod_defaults() -> None:
    for agent_id, (external_agent_id, env_var, default_url) in (
        VALUATION_EXTERNAL_HTTP_CONFIG.items()
    ):
        config = EXTERNAL_HTTP_AGENT_CONFIG[agent_id]
        assert config.external_agent_id == external_agent_id
        assert config.env_var == env_var
        assert config.default_url == default_url


def test_map_valuation_success_response_to_agent_output() -> None:
    output = map_external_http_response_to_agent_output(
        {
            "schema_version": "external_agent_response_v0",
            "agent_id": "valuation_traditional",
            "status": "ok",
            "answer": "DCF target range is 10-12.",
            "native_answer": "native",
            "tool_result": {
                "valuation_result": {"target_price": 11.0, "confidence": 0.73},
                "data_sources": ["mock financials"],
            },
            "warnings": [],
            "errors": [],
        }
    )
    assert output["parse_ok"] is True
    assert output["analysis"] == "DCF target range is 10-12."
    assert output["confidence"] == 0.73
    assert output["key_points"]
    assert "mock financials" in output["evidence"]


def test_valuation_external_http_tool_success(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "schema_version": "external_agent_response_v0",
                "agent_id": "valuation_ml",
                "status": "ok",
                "answer": "machine valuation result",
                "tool_result": {"valuation_result": {"confidence": 0.66}},
                "warnings": [],
                "errors": [],
            }

    class FakeClient:
        def __init__(self, timeout, trust_env=False):
            captured["timeout"] = timeout
            captured["trust_env"] = trust_env

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", FakeClient)
    monkeypatch.setenv("VALUATION_ML_AGENT_URL", "http://test.local/v1/agent/invoke")

    tool = build_external_http_tool("a16_ml_valuation")
    output = anyio.run(
        tool.ainvoke,
        {"question": "valuation question", "subtask": "call external service"},
    )

    assert output["parse_ok"] is True
    assert output["analysis"] == "machine valuation result"
    assert captured["url"] == "http://test.local/v1/agent/invoke"
    assert captured["trust_env"] is False
    assert captured["json"]["options"]["external_agent_id"] == "valuation_ml"
    assert getattr(tool, "is_external_http_wrapper", False)
    assert getattr(tool, "is_external_valuation_wrapper", False)
    assert getattr(tool, "external_agent_id", "") == "valuation_ml"


def test_valuation_external_http_tool_fail_soft_http(monkeypatch) -> None:
    class FakeResponse:
        status_code = 503

        def json(self):
            return {}

    class FakeClient:
        def __init__(self, timeout, trust_env=False):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            return FakeResponse()

    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", FakeClient)
    tool = build_external_http_tool("a17_traditional_valuation")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})
    assert output["parse_ok"] is False
    assert output["confidence"] == 0.0
    assert "http_status_503" in output["evidence"][0]


def test_valuation_external_http_tool_timeout_fail_soft(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, timeout, trust_env=False):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            raise httpx.TimeoutException("too slow")

    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", FakeClient)
    tool = build_external_http_tool("a18_meta_valuation")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})
    assert output["parse_ok"] is False
    assert output["confidence"] == 0.0
    assert "timeout" in output["evidence"][0]
