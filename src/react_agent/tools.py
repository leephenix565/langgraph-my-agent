"""Search tools exposed to the multi-agent graph."""

from typing import Any, Callable, List

from langchain_tavily import TavilySearch

# TavilySearch reads TAVILY_API_KEY from environment.
tavily_search = TavilySearch(
    max_results=5,
    search_depth="basic",
    name="tavily_search",
)

def build_tavily_search(max_results: int) -> TavilySearch:
    if not isinstance(max_results, int) or max_results <= 0:
        max_results = tavily_search.max_results
    tool = TavilySearch(
        max_results=max_results,
        search_depth="basic",
        name="tavily_search",
    )
    return tool


TOOLS: List[Callable[..., Any]] = [tavily_search]
