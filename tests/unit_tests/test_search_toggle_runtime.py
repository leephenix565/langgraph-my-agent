import asyncio
import importlib

from langchain_core.messages import AIMessage


def _load_env_for_import(monkeypatch) -> None:
    # Avoid import-time Tavily validation failures in test envs without a real key.
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")


def test_disable_search_env_is_read_at_runtime(monkeypatch) -> None:
    _load_env_for_import(monkeypatch)

    import react_agent.graph as graph_module

    graph_module = importlib.reload(graph_module)
    agent_id = next(
        aid for aid in graph_module.AGENT_IDS_FOR_NODES if aid not in {"a01_cio_orchestrator", "a25_report_center"}
    )

    captured = []

    class DummyTool:
        async def ainvoke(self, agent_input, config=None):  # type: ignore[override]
            captured.append(agent_input["tools_config"]["allow_search"])
            return {
                "analysis": "ok",
                "key_points": [],
                "evidence": [],
                "confidence": 0.1,
                "parse_ok": True,
            }

    orig_tool = graph_module.AGENT_TOOLS.get(agent_id)
    graph_module.AGENT_TOOLS[agent_id] = DummyTool()
    node = graph_module._build_agent_node(agent_id)

    class _Ctx:
        run_id = "test"
        model = "openai/test-model"

    class _Runtime:
        context = _Ctx()

    state = {
        "messages": [],
        "current_question": "q",
        "analyst_results": {},
        "layer_plan": {"L2": [agent_id]},
        "layer_mode": {"L2": "Star"},
        "current_layer": "L2",
        "run_id": "test",
    }

    try:
        monkeypatch.delenv("DISABLE_SEARCH", raising=False)
        asyncio.run(node(state, _Runtime()))
        monkeypatch.setenv("DISABLE_SEARCH", "1")
        asyncio.run(node(state, _Runtime()))
    finally:
        if orig_tool is not None:
            graph_module.AGENT_TOOLS[agent_id] = orig_tool

    assert captured == [True, False]


def test_tool_calls_trigger_search_tool_invocation(monkeypatch) -> None:
    _load_env_for_import(monkeypatch)

    import react_agent.default_agents as default_agents

    class DummySearchTool:
        name = "tavily_search"

        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, args, config=None):  # type: ignore[override]
            self.calls += 1
            return f"search_result_for={args.get('query', '')}"

    class FakeBoundModel:
        def __init__(self) -> None:
            self._turn = 0

        async def ainvoke(self, msgs, config=None):  # type: ignore[override]
            self._turn += 1
            if self._turn == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "tavily_search", "args": {"query": "fed rate"}, "id": "tc1", "type": "tool_call"}
                    ],
                )
            return AIMessage(content='{"analysis":"ok","key_points":[],"evidence":[],"confidence":0.7}', tool_calls=[])

    class FakeModelFactory:
        def __init__(self) -> None:
            self.bound = FakeBoundModel()

        def bind_tools(self, tool_list):
            return self.bound

    dummy_tool = DummySearchTool()
    monkeypatch.setattr(default_agents, "load_chat_model", lambda name: FakeModelFactory())
    monkeypatch.setattr(default_agents, "get_runtime", lambda ctx: None)

    result = asyncio.run(
        default_agents._call_with_tools([dummy_tool], [{"role": "user", "content": "search latest fed decision"}])
    )

    assert dummy_tool.calls == 1
    assert isinstance(result, AIMessage)
