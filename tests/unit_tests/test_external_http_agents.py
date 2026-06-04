import anyio
import httpx
import pytest

from react_agent.external_http_agents import (
    EXTERNAL_HTTP_AGENT_CONFIG,
    build_external_http_agent_request,
    build_external_http_tool,
    map_external_http_response_to_agent_output,
    register_external_http_agents,
)
from react_agent.legacy_agent_registry import AgentMetadata

P0_EXTERNAL_HTTP_CONFIG = {
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

P1A_EXTERNAL_HTTP_CONFIG = {
    "a22_financial_data_service": (
        "financial_data_service",
        "FINANCIAL_DATA_AGENT_URL",
        "http://222.73.85.26:11000/v1/agent/invoke",
    ),
    "a03_macro_industry_research": (
        "macro_analysis",
        "MACRO_ANALYSIS_AGENT_URL",
        "http://222.73.85.26:10014/v1/agent/invoke",
    ),
    "a04_commodity_hedging": (
        "price_influence_agent",
        "COMMODITY_PRICING_AGENT_URL",
        "http://222.73.85.26:10004/v1/agent/invoke",
    ),
    "a06_financial_statement_analysis": (
        "financial_report_agent",
        "ENTERPRISE_FINANCIAL_ANALYSIS_AGENT_URL",
        "http://222.73.85.26:10005/v1/agent/invoke",
    ),
    "a10_stock_technical_analysis": (
        "technical_stock",
        "STOCK_TECHNICAL_ANALYSIS_AGENT_URL",
        "http://222.73.85.26:10009/v1/agent/invoke",
    ),
    "a11_index_technical_analysis": (
        "valuation_index",
        "INDEX_VALUATION_AGENT_URL",
        "http://222.73.85.26:10003/v1/agent/invoke",
    ),
    "a12_research_synthesis": (
        "analyst_research",
        "RESEARCH_SYNTHESIS_AGENT_URL",
        "http://222.73.85.26:10006/v1/agent/invoke",
    ),
    "a14_ipo_investor_behavior": (
        "ipo_investor_behavior",
        "IPO_INVESTOR_BEHAVIOR_AGENT_URL",
        "http://222.73.85.26:10008/v1/agent/invoke",
    ),
    "a23_crash_risk": (
        "crash_risk",
        "CRASH_RISK_AGENT_URL",
        "http://222.73.85.26:10012/v1/agent/invoke",
    ),
    "a26_composite_valuation": (
        "composite_valuation",
        "COMPOSITE_VALUATION_AGENT_URL",
        "http://222.73.85.26:10015/v1/agent/invoke",
    ),
}

EXPECTED_EXTERNAL_HTTP_CONFIG = {
    **P0_EXTERNAL_HTTP_CONFIG,
    **P1A_EXTERNAL_HTTP_CONFIG,
}

HELD_OR_FUTURE_AGENT_IDS = {
    "a27_risk_constraint",
    "a13_fund_manager_behavior",
    "a19_risk_identification",
    "a20_compliance_review",
    "a24_financial_fraud_risk",
    "a15_entity_relation_extraction",
    "a07_macro_sentiment",
    "a08_industry_hotspot",
    "a09_company_sentiment_radar",
    "a28_composite_sentiment",
}


def _metadata(agent_id: str, *, enabled: bool = True) -> AgentMetadata:
    return AgentMetadata(
        id=agent_id,
        name=agent_id,
        description="external",
        capabilities=[],
        input_type="",
        latency_level="",
        cost_level="",
        version="",
        layer="L3",
        default_enabled=enabled,
    )


def test_build_external_http_agent_request_uses_compact_context(monkeypatch) -> None:
    monkeypatch.setenv("EXTERNAL_AGENT_TIMEOUT_SECONDS", "12")
    request = build_external_http_agent_request(
        agent_id="a16_ml_valuation",
        question="帮我用机器学习估值看看中国能建",
        subtask="估值分析",
        shared_context={
            "messages": ["raw should not leak"],
            "layer_plan": {"L3": ["a16_ml_valuation"]},
        },
        router_plan_summary="L3: a16_ml_valuation",
    )
    assert request["schema_version"] == "external_agent_request_v0"
    assert request["language"] == "zh"
    assert request["options"]["external_agent_id"] == "valuation_ml"
    assert request["options"]["timeout_seconds"] == 12.0
    assert request["context"]["main_agent_id"] == "a16_ml_valuation"
    assert request["context"]["external_agent_id"] == "valuation_ml"
    assert "messages" not in request["context"]["shared_context_summary"]


def test_map_external_http_success_response_to_agent_output() -> None:
    output = map_external_http_response_to_agent_output(
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


def test_maps_top_level_key_points() -> None:
    output = map_external_http_response_to_agent_output(
        {
            "schema_version": "external_agent_response_v0",
            "agent_id": "valuation_ml",
            "status": "ok",
            "answer": "结论文本",
            "key_points": ["要点1", "要点2"],
            "tool_result": {},
        }
    )
    assert output["parse_ok"] is True
    assert output["key_points"][:2] == ["要点1", "要点2"]


def test_maps_top_level_evidence() -> None:
    output = map_external_http_response_to_agent_output(
        {
            "schema_version": "external_agent_response_v0",
            "agent_id": "valuation_ml",
            "status": "ok",
            "answer": "结论文本",
            "evidence": [
                {"source": "model", "detail": "x"},
                {"source": "data", "detail": "y"},
            ],
            "tool_result": {},
        }
    )
    assert output["parse_ok"] is True
    assert any("model: x" in item for item in output["evidence"])
    assert any("data: y" in item for item in output["evidence"])


def test_merges_top_level_and_tool_result_key_points_without_dropping_existing_data() -> None:
    output = map_external_http_response_to_agent_output(
        {
            "schema_version": "external_agent_response_v0",
            "agent_id": "valuation_ml",
            "status": "ok",
            "answer": "结论文本",
            "key_points": ["top point"],
            "tool_result": {
                "key_points": ["tool point"],
                "summary": "tool summary",
            },
        }
    )
    # Stable priority is top-level key_points, then tool_result key_points,
    # then compact tool_result summaries.
    assert output["key_points"][:3] == [
        "top point",
        "tool point",
        "summary: tool summary",
    ]


def test_preserves_tool_result_when_top_level_evidence_exists() -> None:
    output = map_external_http_response_to_agent_output(
        {
            "schema_version": "external_agent_response_v0",
            "agent_id": "valuation_ml",
            "status": "ok",
            "answer": "结论文本",
            "evidence": ["top evidence"],
            "tool_result": {
                "evidence": ["tool evidence"],
                "data_sources": ["tool data source"],
            },
        }
    )
    assert output["evidence"][:3] == [
        "top evidence",
        "tool evidence",
        "tool data source",
    ]


def test_top_level_evidence_bad_shape_does_not_crash_and_preserves_safely() -> None:
    output = map_external_http_response_to_agent_output(
        {
            "schema_version": "external_agent_response_v0",
            "agent_id": "valuation_ml",
            "status": "ok",
            "answer": "结论文本",
            "evidence": {"unexpected": {"nested": "value"}},
            "tool_result": {},
        }
    )
    assert output["parse_ok"] is True
    assert output["evidence"]
    assert "unexpected" in output["evidence"][0]


@pytest.mark.parametrize("status,confidence", [("partial", 0.4), ("needs_clarification", 0.4)])
def test_map_external_http_partial_statuses_remain_parse_ok(status, confidence) -> None:
    output = map_external_http_response_to_agent_output(
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


def test_map_external_http_error_status_fail_soft() -> None:
    output = map_external_http_response_to_agent_output(
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


def test_external_http_tool_success_and_env_override(monkeypatch) -> None:
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
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:8080")
    monkeypatch.delenv("EXTERNAL_AGENT_TRUST_ENV", raising=False)
    monkeypatch.setenv("VALUATION_ML_AGENT_URL", "http://test.local/v1/agent/invoke")

    tool = build_external_http_tool("a16_ml_valuation")
    output = anyio.run(tool.ainvoke, {"question": "估值问题", "subtask": "调用外部服务"})

    assert output["parse_ok"] is True
    assert output["analysis"] == "机器学习估值结果。"
    assert captured["trust_env"] is False
    assert captured["url"] == "http://test.local/v1/agent/invoke"
    assert captured["json"]["options"]["external_agent_id"] == "valuation_ml"
    assert getattr(tool, "is_external_http_wrapper", False)
    assert getattr(tool, "is_external_valuation_wrapper", False)
    assert getattr(tool, "external_agent_id", "") == "valuation_ml"


def test_external_http_tool_can_explicitly_trust_env_when_enabled(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "agent_id": "valuation_ml",
                "status": "ok",
                "answer": "ok",
                "tool_result": {},
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
            return FakeResponse()

    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", FakeClient)
    monkeypatch.setenv("EXTERNAL_AGENT_TRUST_ENV", "true")

    tool = build_external_http_tool("a16_ml_valuation")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})

    assert output["parse_ok"] is True
    assert captured["trust_env"] is True


def test_p1a_external_http_tool_success_and_request_mapping(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "schema_version": "external_agent_response_v0",
                "agent_id": "financial_data_service",
                "status": "ok",
                "answer": "金融数据服务返回了行情与财务摘要。",
                "key_points": ["行情数据已归一化"],
                "evidence": [{"source": "market_data", "detail": "mock quote"}],
                "tool_result": {
                    "key_points": ["财务数据已归一化"],
                    "data_sources": ["mock fundamentals"],
                    "summary": "data package ready",
                    "confidence": 0.72,
                },
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
    monkeypatch.setenv("FINANCIAL_DATA_AGENT_URL", "http://test.local/financial-data")

    tool = build_external_http_tool("a22_financial_data_service")
    output = anyio.run(tool.ainvoke, {"question": "取中国能建数据", "subtask": "数据准备"})

    assert output["parse_ok"] is True
    assert output["analysis"] == "金融数据服务返回了行情与财务摘要。"
    assert output["confidence"] == 0.72
    assert captured["trust_env"] is False
    assert output["key_points"][:3] == [
        "行情数据已归一化",
        "财务数据已归一化",
        "summary: data package ready",
    ]
    assert any("market_data: mock quote" in item for item in output["evidence"])
    assert "mock fundamentals" in output["evidence"]
    assert captured["url"] == "http://test.local/financial-data"
    assert captured["json"]["context"]["main_agent_id"] == "a22_financial_data_service"
    assert captured["json"]["context"]["external_agent_id"] == "financial_data_service"
    assert captured["json"]["options"]["external_agent_id"] == "financial_data_service"
    assert getattr(tool, "is_external_http_wrapper", False)
    assert not getattr(tool, "is_external_valuation_wrapper", False)
    assert getattr(tool, "external_agent_id", "") == "financial_data_service"


@pytest.mark.parametrize(
    "agent_id,expected_external_agent_id,expected_env_var,expected_url",
    [
        (agent_id, external_agent_id, env_var, url)
        for agent_id, (external_agent_id, env_var, url) in EXPECTED_EXTERNAL_HTTP_CONFIG.items()
    ],
)
def test_external_http_default_endpoints_and_env_vars_are_csv_prod(
    agent_id, expected_external_agent_id, expected_env_var, expected_url
) -> None:
    config = EXTERNAL_HTTP_AGENT_CONFIG[agent_id]
    assert config.external_agent_id == expected_external_agent_id
    assert config.env_var == expected_env_var
    assert config.default_url == expected_url


def test_external_http_config_contains_only_p0_and_p1a_agents() -> None:
    assert len(EXTERNAL_HTTP_AGENT_CONFIG) == 13
    assert set(EXTERNAL_HTTP_AGENT_CONFIG) == set(EXPECTED_EXTERNAL_HTTP_CONFIG)
    assert not (set(EXTERNAL_HTTP_AGENT_CONFIG) & HELD_OR_FUTURE_AGENT_IDS)


def test_p1a_env_override_takes_precedence(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "agent_id": "macro_analysis",
                "status": "ok",
                "answer": "宏观分析结果。",
                "tool_result": {},
            }

    class FakeClient:
        def __init__(self, timeout, trust_env=False):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            captured["url"] = url
            return FakeResponse()

    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", FakeClient)
    monkeypatch.setenv("MACRO_ANALYSIS_AGENT_URL", "http://test.local/macro")

    tool = build_external_http_tool("a03_macro_industry_research")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})

    assert output["parse_ok"] is True
    assert captured["url"] == "http://test.local/macro"


def test_service_reported_external_agent_id_does_not_warn(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "agent_id": "price_influence_agent",
                "status": "ok",
                "answer": "商品定价影响分析完成。",
                "tool_result": {},
            }

    class FakeClient:
        def __init__(self, timeout, trust_env=False):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            assert json["context"]["main_agent_id"] == "a04_commodity_hedging"
            assert json["context"]["external_agent_id"] == "price_influence_agent"
            assert json["options"]["external_agent_id"] == "price_influence_agent"
            return FakeResponse()

    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", FakeClient)
    tool = build_external_http_tool("a04_commodity_hedging")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})

    assert output["parse_ok"] is True
    assert not any("returned_agent_id=" in item for item in output.get("evidence", []))


def test_old_external_agent_id_now_warns_but_does_not_fail(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "agent_id": "commodity_pricing",
                "status": "ok",
                "answer": "旧 external_agent_id 仍返回成功体。",
                "tool_result": {},
            }

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
    tool = build_external_http_tool("a04_commodity_hedging")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})

    assert output["parse_ok"] is True
    assert any(
        "returned_agent_id=commodity_pricing, expected=price_influence_agent" in item
        for item in output["evidence"]
    )


@pytest.mark.parametrize(
    "response,expected_reason",
    [
        ({"status_code": 503, "json": lambda: {}}, "http_status_503"),
        ({"status_code": 200, "json": lambda: (_ for _ in ()).throw(ValueError("bad"))}, "invalid_json"),
        ({"status_code": 200, "json": lambda: ["not", "object"]}, "invalid_schema: response_root_not_object"),
        ({"status_code": 200, "json": lambda: {"answer": "missing status"}}, "missing_status"),
    ],
)
def test_external_http_tool_fail_soft_response_cases(monkeypatch, response, expected_reason) -> None:
    class FakeResponse:
        status_code = response["status_code"]

        def json(self):
            return response["json"]()

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
    assert expected_reason in output["evidence"][0]


@pytest.mark.parametrize(
    "exception,expected_reason",
    [
        (httpx.TimeoutException("too slow"), "timeout"),
        (httpx.ConnectError("network unavailable"), "http_error:ConnectError"),
        (RuntimeError("boom"), "unexpected_error:RuntimeError"),
    ],
)
def test_external_http_tool_fail_soft_exceptions(monkeypatch, exception, expected_reason) -> None:
    class FakeClient:
        def __init__(self, timeout, trust_env=False):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            raise exception

    monkeypatch.setattr("react_agent.external_http_agents.httpx.AsyncClient", FakeClient)
    tool = build_external_http_tool("a18_meta_valuation")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})
    assert output["parse_ok"] is False
    assert output["confidence"] == 0.0
    assert expected_reason in output["evidence"][0]


def test_external_http_agent_id_mismatch_is_warning(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "agent_id": "unexpected_agent",
                "status": "ok",
                "answer": "ok",
                "tool_result": {},
            }

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
    tool = build_external_http_tool("a16_ml_valuation")
    output = anyio.run(tool.ainvoke, {"question": "q", "subtask": "s"})
    assert output["parse_ok"] is True
    assert any("returned_agent_id=unexpected_agent" in item for item in output["evidence"])


def test_register_external_http_agents_all_enabled_p0_and_p1a_ids() -> None:
    metadata = {
        agent_id: _metadata(agent_id)
        for agent_id in EXPECTED_EXTERNAL_HTTP_CONFIG
    }
    wrappers = register_external_http_agents(metadata)
    assert set(wrappers) == set(EXPECTED_EXTERNAL_HTTP_CONFIG)
    for agent_id, tool in wrappers.items():
        assert getattr(tool, "is_external_http_wrapper", False)
        assert getattr(tool, "external_agent_id", "") == EXTERNAL_HTTP_AGENT_CONFIG[agent_id].external_agent_id


def test_register_external_http_agents_skips_special_disabled_and_unconfigured_ids() -> None:
    metadata = {
        "a01_cio_orchestrator": AgentMetadata(
            id="a01_cio_orchestrator",
            name="orchestrator",
            description="special",
            capabilities=[],
            input_type="",
            latency_level="",
            cost_level="",
            version="",
            layer="L1",
            default_enabled=True,
        ),
        "a25_report_center": _metadata("a25_report_center"),
        "a16_ml_valuation": _metadata("a16_ml_valuation"),
        "a17_traditional_valuation": _metadata("a17_traditional_valuation", enabled=False),
        "a22_financial_data_service": _metadata("a22_financial_data_service"),
        "a27_risk_constraint": _metadata("a27_risk_constraint"),
    }
    wrappers = register_external_http_agents(metadata)
    assert set(wrappers) == {"a16_ml_valuation", "a22_financial_data_service"}
    assert getattr(wrappers["a16_ml_valuation"], "is_external_http_wrapper", False)
    assert getattr(wrappers["a22_financial_data_service"], "is_external_http_wrapper", False)
