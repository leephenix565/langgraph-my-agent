import react_agent.tools as tools
from react_agent.tools import build_tavily_search


def test_build_tavily_search_max_results() -> None:
    tool = build_tavily_search(7)
    assert getattr(tool, "max_results", None) == 7


def test_build_tavily_search_unavailable_preserves_normalized_max_results(monkeypatch) -> None:
    monkeypatch.setattr(tools, "TavilySearch", None)
    monkeypatch.setattr(tools, "_TAVILY_IMPORT_ERROR", "ModuleNotFoundError")

    tool = build_tavily_search(-1)

    assert getattr(tool, "is_search_unavailable", False) is True
    assert getattr(tool, "unavailable_reason", "") == "ModuleNotFoundError"
    assert getattr(tool, "max_results", None) == 5
