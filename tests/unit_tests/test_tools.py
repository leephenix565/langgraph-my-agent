from react_agent.tools import build_tavily_search


def test_build_tavily_search_max_results() -> None:
    tool = build_tavily_search(7)
    assert getattr(tool, "max_results", None) == 7
