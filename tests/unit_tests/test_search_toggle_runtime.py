import asyncio

import react_agent.graph as graph_module
from react_agent.context import Context


def test_disable_search_env_does_not_block_reset_skeleton(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SEARCH", "1")
    result = asyncio.run(
        graph_module.graph.ainvoke(
            {"messages": [("user", "q")]},
            context=Context(),
        )
    )
    assert result["data_bundle"]["status"] == "pending_implementation"
    assert result["emitted_bundle"]["external_invoked"] is False
