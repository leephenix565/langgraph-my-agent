import httpx
import pytest
import anyio

from react_agent.external_valuation_agents import (
    EXTERNAL_VALUATION_AGENT_CONFIG,
    build_external_agent_request,
    build_external_valuation_tool,
    map_external_response_to_agent_output,
)


def test_build_external_agent_request_uses_external_mapping(monkeypatch) -> None:
    monkeypatch.setenv("EXTERNAL_AGENT_TIMEOUT_SECONDS", "12")
    request = build_external_agent_request(
        agent_id="a16_ml_valuation",
        question="帮我用机器学习估值看看中国能建",
        subtask="估值分析",
        shared_context={"messages": ["raw should not leak"], "layer_plan": {"L3": ["a16_ml_valuation"]}},
        router_plan_summary="L3: a16_ml_valuation",
    )
    assert request["schema_version"] == "external_agent_request_v0"
    assert request["language"] == "zh"
    assert request["options"]["external_agent_id"] == "valuation_ml"
    assert request["options"]["timeout_seconds"] == 12.0
    assert request["context"]["main_agent_id"] == "a16_ml_valuation"
    assert request["context"]["external_agent_id"] == "valuation_ml"
    assert "messages" not in request["context"]["shared_context_summary"]


def test_external_valuation_config_uses_csv_prod_defaults() -> None:
    assert (
        EXTERNAL_VALUATION_AGENT_CONFIG["a16_ml_valuation"]["default_url"]
        == "http://222.73.85.26:10001/v1/agent/invoke"
    )
    assert (
        EXTERNAL_VALUATION_AGENT_CONFIG["a17_traditional_valuation"]["default_url"]
        == "http://222.73.85.26:10000/v1/agent/invoke"
    )
    assert (
        EXTERNAL_VALUATION_AGENT_CONFIG["a18_meta_valuation"]["default_url"]
        == "http://222.73.85.26:10002/v1/agent/invoke"
    )


def test_map_external_success_response_to_agent_output() -> None:
    output = map_external_response_to_agent_output(
        {
            "schema_version": "external_agent_response_v0",
            "agent_id": "valuation_traditional",
            "status": "ok",
            "answer": "DCF 目标价区间为 10-12 元。",
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
    assert output["analysis"] == "DCF 目标价区间为 10-12 元。"
    assert output["confidence"] == 0.73
    assert output["key_points"]
    assert "mock financials" in output["evidence"]


@pytest.mark.parametrize("status,confidence", [("partial", 0.4), ("needs_clarification", 0.4)])
def test_map_external_partial_statuses_remain_parse_ok(status, confidence) -> None:
    output = map_external_response_to_agent_output(
        {
            "schema_version": "external_agent_response_v0",
            "agent_id": "valuation_meta",
            "status": status,
            "answer": "需要补充目标日期。",
            "tool_result": {},
            "warnings": ["missing target_date"],
            "errors": [],
        }
    )
    assert output["parse_ok"] is True
    assert output["confidence"] == confidence
    assert any("missing target_date" in item for item in output["evidence"])


def test_map_external_error_status_fail_soft() -> None:
    output = map_external_response_to_agent_output(
        {
            "schema_version": "external_agent_response_v0",
            "agent_id": "valuation_ml",
            "status": "error",
            "answer": "",
            "tool_result": {},
            "warnings": [],
            "errors": ["provider unavailable"],
        }
    )
    assert output["parse_ok"] is False
    assert output["confidence"] == 0.0
    assert "外部智能体服务不可用" in output["analysis"]
    assert any("provider unavailable" in item for item in output["evidence"])


def test_external_valuation_tool_success(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "schema_version": "external_agent_response_v0",
                "agent_id": "valuation_ml",
                "status": "ok",
                "answer": "机器学习估值结果。",
                "tool_result": {"valuation_result": {"confidence": 0.66}},
                "warnings": [],
                "errors": [],
            }

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

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

    tool = build_external_valuation_tool("a16_ml_valuation")
    output = anyio.run(
        tool.ainvoke,
        {"question": "估值问题", "subtask": "调用外部服务"},
    )

    assert output["parse_ok"] is True
    assert output["analysis"] == "机器学习估值结果。"
    assert captured["url"] == "http://test.local/v1/agent/invoke"
    assert captured["json"]["options"]["external_agent_id"] == "valuation_ml"
    assert getattr(tool, "is_external_valuation_wrapper", False)
    assert getattr(tool, "external_agent_id", "") == "valuation_ml"


@pytest.mark.parametrize(
    "response,expected_reason",
    [
        ({"status_code": 503, "json": lambda: {}}, "http_status_503"),
        ({"status_code": 200, "json": lambda: (_ for _ in ()).throw(ValueError("bad"))}, "invalid_json"),
    ],
)
def test_external_valuation_tool_fail_soft_http_and_json(monkeypatch, response, expected_reason) -> None:
    class FakeResponse:
        status_code = response["status_code"]

        def json(self):
            return response["json"]()

    class FakeClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            return FakeResponse()

    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", FakeClient)
    tool = build_external_valuation_tool("a17_traditional_valuation")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})
    assert output["parse_ok"] is False
    assert output["confidence"] == 0.0
    assert expected_reason in output["evidence"][0]


def test_external_valuation_tool_timeout_fail_soft(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            raise httpx.TimeoutException("too slow")

    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", FakeClient)
    tool = build_external_valuation_tool("a18_meta_valuation")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})
    assert output["parse_ok"] is False
    assert output["confidence"] == 0.0
    assert "timeout" in output["evidence"][0]
