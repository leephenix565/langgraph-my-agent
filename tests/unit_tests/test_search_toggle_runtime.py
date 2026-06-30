import react_agent.graph as graph_module
from react_agent.context import Context


def test_disable_search_env_does_not_block_reset_skeleton(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SEARCH", "1")
    result = graph_module.graph.invoke(
        {"messages": [("user", "q")]},
        context=Context(
            disable_external_compute_default=True,
            disable_non_l4_external_compute_default=True,
        ),
    )
    assert result["data_bundle"]["status"] == "pending_implementation"
    assert result["emitted_bundle"]["external_invoked"] is False
