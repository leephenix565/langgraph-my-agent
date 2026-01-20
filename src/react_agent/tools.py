"""Search tools exposed to the multi-agent graph."""

from typing import Any, Callable, List

from langchain_community.tools.tavily_search import TavilySearchResults

# TavilySearchResults reads TAVILY_API_KEY from environment.
tavily_search = TavilySearchResults(
    max_results=5,
    search_depth="basic",
)
# 统一名称，便于在 prompts 与代码中引用。
tavily_search.name = "tavily_search"

def build_tavily_search(max_results: int) -> TavilySearchResults:
    if not isinstance(max_results, int) or max_results <= 0:
        max_results = tavily_search.max_results
    tool = TavilySearchResults(
        max_results=max_results,
        search_depth="basic",
    )
    tool.name = "tavily_search"
    return tool


TOOLS: List[Callable[..., Any]] = [tavily_search]
