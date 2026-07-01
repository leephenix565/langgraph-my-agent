import pytest

from react_agent import public_api
from react_agent.context import Context
from react_agent.public_contracts import (
    CheckpointerStatus,
    PublicRoutingRequest,
    PublicTurn,
    ReadinessSurface,
)
from react_agent.public_runtime import (
    RuntimeReadinessProbe,
    invoke_public_turn,
    prepare_public_turn_invoke,
)

pytestmark = pytest.mark.anyio


def test_public_routing_selected_builds_selected_context_only(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_LLM_DIMENSION_ROUTER", raising=False)
    monkeypatch.delenv("ENABLE_EXTERNAL_COMPUTE_DEMO", raising=False)

    context = public_api._context_for_public_routing(PublicRoutingRequest(mode="selected"))

    assert isinstance(context, Context)
    assert context.enable_selected_routing is True
    assert context.enable_llm_dimension_router is False
    assert context.enable_external_compute_demo is False


def test_public_routing_none_keeps_default_runtime_context() -> None:
    assert public_api._context_for_public_routing(None) is None


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
    assert captured["invoke_kwargs"]["context"].enable_selected_routing is False


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


async def test_invoke_public_turn_preserves_explicit_context_override(monkeypatch) -> None:
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

    explicit_context = Context(
        enable_selected_routing=True,
        disable_external_compute_default=True,
        disable_non_l4_external_compute_default=True,
    )
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
        thread_id="thread-selected",
        history_turns=[],
        user_text="hello selected",
        context=explicit_context,
    )

    assert turn.text == "ok"
    assert continuity_mode == "replay"
    assert captured["invoke_kwargs"]["context"] is explicit_context
    assert captured["invoke_kwargs"]["context"].enable_selected_routing is True
    assert captured["invoke_kwargs"]["context"].disable_external_compute_default is True
    assert captured["invoke_kwargs"]["context"].disable_non_l4_external_compute_default is True


async def test_invoke_public_turn_prefers_sync_graph_invoke(monkeypatch) -> None:
    captured: dict = {}

    class FakeGraphApp:
        def invoke(self, invoke_input, **invoke_kwargs):
            captured["invoke_input"] = invoke_input
            captured["invoke_kwargs"] = invoke_kwargs
            return {"ok": True}

        async def ainvoke(self, *_args, **_kwargs):
            raise AssertionError("sync invoke should be preferred for public runtime")

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
        thread_id="thread-sync",
        history_turns=[],
        user_text="hello sync",
    )

    assert turn.text == "ok"
    assert continuity_mode == "replay"
    assert captured["invoke_input"] == {"messages": [("user", "hello sync")]}
    assert isinstance(captured["invoke_kwargs"]["context"], Context)


def test_prepare_public_turn_invoke_preserves_explicit_context_override(monkeypatch) -> None:
    class FakeGraphApp:
        pass

    class FakeGraphModule:
        @staticmethod
        def get_graph_for_invoke(_thread_id):
            return FakeGraphApp()

    explicit_context = Context(
        enable_selected_routing=True,
        disable_external_compute_default=True,
        disable_non_l4_external_compute_default=True,
    )
    monkeypatch.setattr(
        "react_agent.public_runtime.probe_public_runtime",
        lambda: _probe(FakeGraphModule(), continuity_mode="replay"),
    )

    prepared = prepare_public_turn_invoke(
        thread_id="thread-selected",
        history_turns=[],
        user_text="hello selected",
        context=explicit_context,
    )

    assert prepared.invoke_kwargs["context"] is explicit_context
