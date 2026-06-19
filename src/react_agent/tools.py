"""Search tools exposed to the multi-agent graph."""

from __future__ import annotations

from typing import Any, Callable, List

from langchain_core.tools import BaseTool, tool

try:  # pragma: no cover - import availability is environment-dependent.
    from langchain_tavily import TavilySearch
except Exception as exc:  # pragma: no cover
    TavilySearch = None  # type: ignore[assignment]
    _TAVILY_IMPORT_ERROR = type(exc).__name__
else:
    _TAVILY_IMPORT_ERROR = ""


def _unavailable_search_tool(reason: str, *, max_results: int) -> BaseTool:
    safe_reason = reason or "unavailable"

    @tool("tavily_search")
    async def _search_unavailable(query: str) -> str:
        """Return a safe search-unavailable marker instead of failing import/bootstrap."""
        del query
        return f"search_unavailable:{safe_reason}"

    object.__setattr__(_search_unavailable, "is_search_unavailable", True)
    object.__setattr__(_search_unavailable, "unavailable_reason", safe_reason)
    object.__setattr__(_search_unavailable, "max_results", max_results)
    return _search_unavailable


def build_tavily_search(max_results: int) -> BaseTool:
    """Build Tavily search when configured, otherwise return a fail-soft tool."""
    if not isinstance(max_results, int) or max_results <= 0:
        max_results = 5
    if TavilySearch is None:
        return _unavailable_search_tool(
            _TAVILY_IMPORT_ERROR or "missing_langchain_tavily",
            max_results=max_results,
        )
    try:
        return TavilySearch(
            max_results=max_results,
            search_depth="basic",
            name="tavily_search",
        )
    except Exception as exc:
        return _unavailable_search_tool(type(exc).__name__, max_results=max_results)


tavily_search = build_tavily_search(5)


TOOLS: List[Callable[..., Any]] = [tavily_search]
