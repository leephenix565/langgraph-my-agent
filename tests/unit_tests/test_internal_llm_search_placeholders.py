import types

import anyio
from langchain_core.messages import AIMessage

import react_agent.default_agents as default_agents
import react_agent.graph as graph_module


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
        tool = graph_module.AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert not getattr(tool, "is_external_http_wrapper", False)
        assert not getattr(tool, "is_external_valuation_wrapper", False)
        assert not getattr(tool, "is_stub", False)
        assert getattr(tool, "is_llm_search_placeholder", False)
        assert getattr(tool, "runtime_path", "") == "INTERNAL_LLM_SEARCH_PLACEHOLDER"


def test_special_agents_are_not_llm_search_placeholders() -> None:
    for agent_id in ["a01_cio_orchestrator", "a25_report_center"]:
        tool = graph_module.AGENT_TOOLS.get(agent_id)
        assert tool is not None
        assert not getattr(tool, "is_external_http_wrapper", False)
        assert not getattr(tool, "is_llm_search_placeholder", False)


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
        lambda: graph_module.AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
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
    monkeypatch.setenv("DISABLE_SEARCH", "1")
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
        lambda: graph_module.AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
            _agent_input(allow_search=True)
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
        lambda: graph_module.AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
            _agent_input(allow_search=True)
        )
    )

    assert result["parse_ok"] is False
    evidence = "\n".join(result.get("evidence") or [])
    assert "source_type=llm_search_placeholder" in evidence
    assert "search_status=failed" in evidence
    assert "error_type=RuntimeError" in evidence


def test_placeholder_direct_invoke_with_provider_failure_fails_soft(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SEARCH", "1")

    class RaisingModel:
        def bind_tools(self, tool_list):
            return self

        async def ainvoke(self, msgs, config=None):  # type: ignore[override]
            raise RuntimeError("provider boom")

    monkeypatch.setattr(default_agents, "load_chat_model", lambda _name: RaisingModel())

    result = anyio.run(
        lambda: graph_module.AGENT_TOOLS["a09_company_sentiment_radar"].ainvoke(
            _agent_input(allow_search=True)
        )
    )

    assert result["parse_ok"] is False
    assert result["runtime_path"] == "INTERNAL_LLM_SEARCH_PLACEHOLDER"
    evidence = "\n".join(result.get("evidence") or [])
    assert "source_type=llm_search_placeholder" in evidence
    assert "error_type=RuntimeError" in evidence
