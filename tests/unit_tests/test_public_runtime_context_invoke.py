import pytest

from react_agent.context import Context
from react_agent.public_contracts import (
    CheckpointerStatus,
    PublicTurn,
    ReadinessSurface,
)
from react_agent.public_runtime import RuntimeReadinessProbe, invoke_public_turn

pytestmark = pytest.mark.anyio


def _probe(fake_module, *, continuity_mode: str = "replay") -> RuntimeReadinessProbe:
    return RuntimeReadinessProbe(
        continuity_mode=continuity_mode,  # type: ignore[arg-type]
        runtime=ReadinessSurface(status="ready", code="runtime_ready"),
        provider_env=ReadinessSurface(status="configured", code="provider_env_configured"),
        search_env=ReadinessSurface(status="configured", code="search_env_configured"),
        checkpointer=CheckpointerStatus(
            enabled=continuity_mode == "persistent",
            mode="memory" if continuity_mode == "persistent" else "none",
            status="enabled" if continuity_mode == "persistent" else "disabled",
            code="checkpointer_enabled" if continuity_mode == "persistent" else "checkpointer_disabled",
            hint=None,
        ),
        overall_status="ready",
        graph_module=fake_module,
    )


async def test_invoke_public_turn_passes_context(monkeypatch) -> None:
    captured: dict = {}

    class FakeGraphApp:
        async def ainvoke(self, invoke_input, **invoke_kwargs):
            captured["invoke_input"] = invoke_input
            captured["invoke_kwargs"] = invoke_kwargs
            return {"ok": True}

    class FakeGraphModule:
        @staticmethod
        def get_graph_for_invoke(_thread_id):
            return FakeGraphApp()

    monkeypatch.setattr(
        "react_agent.public_runtime.probe_public_runtime",
        lambda: _probe(FakeGraphModule(), continuity_mode="replay"),
    )
    monkeypatch.setattr(
        "react_agent.public_runtime.build_assistant_turn",
        lambda state, continuity_mode: PublicTurn(
            id="assistant-test",
            role="assistant",
            text="ok",
            createdAt="2026-04-05 12:00",
            continuityMode=continuity_mode,  # type: ignore[arg-type]
        ),
    )

    turn, continuity_mode = await invoke_public_turn(
        thread_id="thread-test",
        history_turns=[],
        user_text="hello world",
    )

    assert turn.text == "ok"
    assert continuity_mode == "replay"
    assert captured["invoke_input"] == {"messages": [("user", "hello world")]}
    assert "context" in captured["invoke_kwargs"]
    assert isinstance(captured["invoke_kwargs"]["context"], Context)


async def test_invoke_public_turn_passes_context_with_persistent_config(monkeypatch) -> None:
    captured: dict = {}

    class FakeGraphApp:
        async def ainvoke(self, invoke_input, **invoke_kwargs):
            captured["invoke_input"] = invoke_input
            captured["invoke_kwargs"] = invoke_kwargs
            return {"ok": True}

    class FakeGraphModule:
        @staticmethod
        def get_graph_for_invoke(thread_id):
            assert thread_id == "thread-persistent"
            return FakeGraphApp()

    monkeypatch.setattr(
        "react_agent.public_runtime.probe_public_runtime",
        lambda: _probe(FakeGraphModule(), continuity_mode="persistent"),
    )
    monkeypatch.setattr(
        "react_agent.public_runtime.build_assistant_turn",
        lambda state, continuity_mode: PublicTurn(
            id="assistant-test",
            role="assistant",
            text="ok",
            createdAt="2026-04-05 12:00",
            continuityMode=continuity_mode,  # type: ignore[arg-type]
        ),
    )

    turn, continuity_mode = await invoke_public_turn(
        thread_id="thread-persistent",
        history_turns=[],
        user_text="hello persistent",
    )

    assert turn.text == "ok"
    assert continuity_mode == "persistent"
    assert captured["invoke_input"] == {"messages": [("user", "hello persistent")]}
    assert captured["invoke_kwargs"]["config"] == {"configurable": {"thread_id": "thread-persistent"}}
    assert isinstance(captured["invoke_kwargs"]["context"], Context)
