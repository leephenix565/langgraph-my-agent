
import anyio
from langchain_core.messages import AIMessage

import react_agent.default_agents as default_agents
from react_agent.graph_bootstrap import bootstrap_legacy_agent_runtime
from react_agent.legacy_agent_registry import AGENT_METADATA, AGENT_TOOLS

INTERNAL_PLACEHOLDER_IDS = {
    "a07_macro_sentiment",
    "a08_industry_hotspot",
    "a09_company_sentiment_radar",
    "a13_fund_manager_behavior",
    "a15_entity_relation_extraction",
    "a19_risk_identification",
    "a20_compliance_review",
    "a24_financial_fraud_risk",
    "a27_risk_constraint",
    "a28_composite_sentiment",
}


def setup_module() -> None:
    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()
    bootstrap_legacy_agent_runtime()


def teardown_module() -> None:
    AGENT_METADATA.clear()
    AGENT_TOOLS.clear()


def _agent_input(*, allow_search: bool = True) -> dict:
    return {
        "question": "请简要分析公司舆情风险。",
        "subtask": "生成安全摘要。",
        "shared_context": {},
        "history": [],
        "tools_config": {"allow_search": allow_search},
    }


def test_internal_placeholder_agents_are_registered_as_llm_search_tools() -> None:
    for agent_id in INTERNAL_PLACEHOLDER_IDS:
        tool = AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert not getattr(tool, "is_external_http_wrapper", False)
        assert not getattr(tool, "is_external_valuation_wrapper", False)
        assert not getattr(tool, "is_stub", False)
        assert getattr(tool, "is_llm_search_placeholder", False)
        assert getattr(tool, "runtime_path", "") == "INTERNAL_LLM_SEARCH_PLACEHOLDER"


def test_special_agents_are_not_llm_search_placeholders() -> None:
    for agent_id in ["a01_cio_orchestrator", "a25_report_center"]:
        tool = AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert not getattr(tool, "is_external_http_wrapper", False)
        assert not getattr(tool, "is_llm_search_placeholder", False)


def test_special_agent_direct_invoke_provider_import_failure_is_fail_soft(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SEARCH", "1")

    def raise_import_error(_name):
        raise ImportError("missing provider package")

    monkeypatch.setattr(default_agents, "load_chat_model", raise_import_error)

    for agent_id in ["a01_cio_orchestrator", "a25_report_center"]:
        result = anyio.run(
            lambda aid=agent_id: AGENT_TOOLS[aid].ainvoke(
                _agent_input(allow_search=False)
            )
        )

        assert result["parse_ok"] is False
        evidence = "\n".join(result.get("evidence") or [])
        assert "source_type=internal_runtime_agent" in evidence
        assert "provider_dependency_missing" in evidence
        assert "ImportError" not in evidence


def test_placeholder_direct_invoke_provider_import_failure_is_fail_soft(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SEARCH", "1")

    def raise_import_error(_name):
        raise ImportError("missing provider package")

    monkeypatch.setattr(default_agents, "load_chat_model", raise_import_error)

    result = anyio.run(
        lambda: AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
            _agent_input(allow_search=True)
        )
    )

    assert result["parse_ok"] is False
    assert result["runtime_path"] == "INTERNAL_LLM_SEARCH_PLACEHOLDER"
    evidence = "\n".join(result.get("evidence") or [])
    assert "source_type=llm_search_placeholder" in evidence
    assert "provider_dependency_missing" in evidence
    assert "ImportError" not in evidence


def test_placeholder_direct_invoke_with_mock_search_success(monkeypatch) -> None:
    monkeypatch.delenv("DISABLE_SEARCH", raising=False)

    class DummySearchTool:
        name = "tavily_search"

        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, args, config=None):  # type: ignore[override]
            self.calls += 1
            return f"source=mock; query={args.get('query', '')}"

    class FakeModel:
        def __init__(self) -> None:
            self.turn = 0

        def bind_tools(self, tool_list):
            self.tool_list = tool_list
            return self

        async def ainvoke(self, msgs, config=None):  # type: ignore[override]
            self.turn += 1
            if self.turn == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "tavily_search",
                            "args": {"query": "company sentiment risk"},
                            "id": "tc1",
                            "type": "tool_call",
                        }
                    ],
                )
            return AIMessage(
                content='{"analysis":"ok","key_points":["k"],"evidence":["searched"],"confidence":0.6}',
                tool_calls=[],
            )

    dummy_search = DummySearchTool()
    monkeypatch.setattr(default_agents, "tavily_search", dummy_search)
    monkeypatch.setattr(default_agents, "load_chat_model", lambda _name: FakeModel())

    result = anyio.run(
        lambda: AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
            _agent_input(allow_search=True)
        )
    )

    assert dummy_search.calls == 1
    assert result["parse_ok"] is True
    assert result["runtime_path"] == "INTERNAL_LLM_SEARCH_PLACEHOLDER"
    evidence = "\n".join(result.get("evidence") or [])
    assert "searched" in evidence
    assert "source_type=llm_search_placeholder" in evidence


def test_placeholder_direct_invoke_with_disabled_search_marks_limitation(monkeypatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("DISABLE_SEARCH", "yes")
    captured = {}

    class FakeModel:
        def bind_tools(self, tool_list):
            captured["tool_count"] = len(tool_list)
            return self

        async def ainvoke(self, msgs, config=None):  # type: ignore[override]
            return AIMessage(
                content='{"analysis":"ok","key_points":[],"evidence":[],"confidence":0.5}',
                tool_calls=[],
            )

    monkeypatch.setattr(default_agents, "load_chat_model", lambda _name: FakeModel())

    result = anyio.run(
        lambda: AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
            {
                **_agent_input(allow_search=True),
                "tools_config": {"allow_search": True, "max_search_results": 3},
            }
        )
    )

    assert captured["tool_count"] == 0
    assert result["parse_ok"] is True
    evidence = "\n".join(result.get("evidence") or [])
    assert "source_type=llm_search_placeholder" in evidence
    assert "search_status=disabled" in evidence


def test_placeholder_direct_invoke_with_search_failure_fails_soft(monkeypatch) -> None:
    monkeypatch.delenv("DISABLE_SEARCH", raising=False)

    class RaisingSearchTool:
        name = "tavily_search"

        async def ainvoke(self, args, config=None):  # type: ignore[override]
            raise RuntimeError("search boom")

    class FakeModel:
        def bind_tools(self, tool_list):
            return self

        async def ainvoke(self, msgs, config=None):  # type: ignore[override]
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "tavily_search",
                        "args": {"query": "risk"},
                        "id": "tc1",
                        "type": "tool_call",
                    }
                ],
            )

    monkeypatch.setattr(default_agents, "tavily_search", RaisingSearchTool())
    monkeypatch.setattr(default_agents, "load_chat_model", lambda _name: FakeModel())

    result = anyio.run(
        lambda: AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
            _agent_input(allow_search=True)
        )
    )

    assert result["parse_ok"] is False
    evidence = "\n".join(result.get("evidence") or [])
    assert "source_type=llm_search_placeholder" in evidence
    assert "search_status=failed" in evidence
    assert "error_type=RuntimeError" in evidence


def test_placeholder_search_tool_unavailable_does_not_surface_import_error(monkeypatch) -> None:
    monkeypatch.delenv("DISABLE_SEARCH", raising=False)
    captured = {}

    class FakeModel:
        def bind_tools(self, tool_list):
            captured["tool_count"] = len(tool_list)
            return self

        async def ainvoke(self, msgs, config=None):  # type: ignore[override]
            return AIMessage(
                content='{"analysis":"ok","key_points":[],"evidence":[],"confidence":0.5}',
                tool_calls=[],
            )

    def unavailable_search(_max_results):
        raise ImportError("missing search package")

    monkeypatch.setattr(default_agents, "build_tavily_search", unavailable_search)
    monkeypatch.setattr(default_agents, "load_chat_model", lambda _name: FakeModel())

    result = anyio.run(
        lambda: AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
            {
                **_agent_input(allow_search=True),
                "tools_config": {"allow_search": True, "max_search_results": 3},
            }
        )
    )

    assert captured["tool_count"] == 0
    assert result["parse_ok"] is True
    evidence = "\n".join(result.get("evidence") or [])
    assert "source_type=llm_search_placeholder" in evidence
    assert "search_status=unavailable" in evidence
    assert "ImportError" not in evidence


def test_placeholder_direct_invoke_with_provider_failure_fails_soft(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SEARCH", "1")

    class RaisingModel:
        def bind_tools(self, tool_list):
            return self

        async def ainvoke(self, msgs, config=None):  # type: ignore[override]
            raise RuntimeError("provider boom")

    monkeypatch.setattr(default_agents, "load_chat_model", lambda _name: RaisingModel())

    result = anyio.run(
        lambda: AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
            _agent_input(allow_search=True)
        )
    )

    assert result["parse_ok"] is False
    assert result["runtime_path"] == "INTERNAL_LLM_SEARCH_PLACEHOLDER"
    evidence = "\n".join(result.get("evidence") or [])
    assert "source_type=llm_search_placeholder" in evidence
    assert "error_type=RuntimeError" in evidence
    assert "ImportError" not in evidence


def test_runtime_registration_invariants_remain_after_placeholder_hardening() -> None:
    external_wrappers = [
        tool
        for tool in AGENT_TOOLS.values()
        if getattr(tool, "is_external_http_wrapper", False)
    ]
    assert len(external_wrappers) == 13
    assert "a05_annual_report_analysis" not in AGENT_TOOLS
    assert "a21_portfolio_manager" not in AGENT_TOOLS
    assert "a02_task_router" not in AGENT_TOOLS
