"""Runtime invocation helpers for the public API."""

from __future__ import annotations

import os
import sys
import traceback
from dataclasses import dataclass
from importlib import import_module
from typing import Any, AsyncIterator, Dict, Sequence

from react_agent.context import Context
from react_agent.graph_entry import maybe_make_checkpointer
from react_agent.public_contracts import (
    CheckpointerStatus,
    ContinuityMode,
    OverallStatus,
    PublicTurn,
    ReadinessSurface,
    RunStartedEvent,
    RunStartedEventData,
    WorkflowSnapshotEvent,
    WorkflowSnapshotEventData,
    WorkflowStageEvent,
    WorkflowStageEventData,
    WorkflowStageKey,
    WorkflowStageProgressModel,
    WorkflowStageStatus,
)
from react_agent.public_mapping import build_assistant_turn, build_workflow_snapshot, replay_messages

_PROVIDER_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ROUTER_OPENAI_API_KEY",
    "BASELINE_OPENAI_API_KEY",
    "GOOGLE_API_KEY",
)
_DISABLED_CHECKPOINTER_MODES = {"", "none", "off", "0"}


class PublicRuntimeError(RuntimeError):
    """Raised when the public adapter cannot invoke the LangGraph runtime."""

    def __init__(self, message: str, *, code: str, category: str) -> None:
        super().__init__(message)
        self.code = code
        self.category = category
        self.message = message


class PublicRuntimeUnavailable(PublicRuntimeError):
    """Raised when the underlying runtime is unavailable or misconfigured."""


@dataclass
class RuntimeReadinessProbe:
    continuity_mode: ContinuityMode
    runtime: ReadinessSurface
    provider_env: ReadinessSurface
    search_env: ReadinessSurface
    checkpointer: CheckpointerStatus
    overall_status: OverallStatus
    graph_module: Any | None = None


@dataclass
class PreparedPublicTurnInvoke:
    continuity_mode: ContinuityMode
    graph_app: Any
    invoke_input: Dict[str, Any]
    invoke_kwargs: Dict[str, Any]


@dataclass
class StreamPublicTurnCompleted:
    assistant_turn: PublicTurn
    continuity_mode: ContinuityMode


_WORKFLOW_STAGE_TITLES: Dict[WorkflowStageKey, str] = {
    "routing": "路由规划",
    "analysis": "多角度分析",
    "risk": "风险校验",
    "summary": "汇总结论",
    "fusion": "融合判断",
}
_WORKFLOW_STAGE_ORDER: tuple[WorkflowStageKey, ...] = ("routing", "analysis", "risk", "summary", "fusion")


def _is_env_present(name: str) -> bool:
    return bool(str(os.environ.get(name, "") or "").strip())


def _truncate_debug_text(text: str | None, limit: int = 200) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: max(limit - 3, 0)] + "..."


def _debug_runtime_exception(
    stage: str,
    exc: BaseException,
    *,
    thread_id: str | None = None,
    continuity_mode: ContinuityMode | None = None,
    user_text: str | None = None,
) -> None:
    context = {
        "stage": stage,
        "thread_id": thread_id,
        "continuity_mode": continuity_mode,
        "user_text_preview": _truncate_debug_text(user_text),
        "MODEL": os.environ.get("MODEL", ""),
        "ROUTER_MODEL": os.environ.get("ROUTER_MODEL", ""),
        "BASELINE_MODEL": os.environ.get("BASELINE_MODEL", ""),
        "has_OPENAI_API_KEY": _is_env_present("OPENAI_API_KEY"),
        "has_CEREBRAS_API_KEY": _is_env_present("CEREBRAS_API_KEY"),
        "has_GOOGLE_API_KEY": _is_env_present("GOOGLE_API_KEY"),
        "has_TAVILY_API_KEY": _is_env_present("TAVILY_API_KEY"),
        "exception_type": type(exc).__name__,
        "exception_repr": repr(exc),
    }
    print("[public_runtime][exception]", context, file=sys.stderr, flush=True)
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    sys.stderr.flush()


def _provider_env_surface() -> ReadinessSurface:
    if any(_is_env_present(key) for key in _PROVIDER_ENV_KEYS):
        return ReadinessSurface(status="configured", code="provider_env_configured")
    return ReadinessSurface(
        status="missing",
        code="provider_env_missing",
        hint="Set OPENAI_API_KEY, ROUTER_OPENAI_API_KEY, BASELINE_OPENAI_API_KEY, or GOOGLE_API_KEY.",
    )


def _search_env_surface() -> ReadinessSurface:
    if _is_env_present("TAVILY_API_KEY"):
        return ReadinessSurface(status="configured", code="search_env_configured")
    return ReadinessSurface(
        status="missing",
        code="search_env_missing",
        hint="Set TAVILY_API_KEY before importing react_agent.graph.",
    )


def _checkpointer_surface() -> CheckpointerStatus:
    raw_mode = (os.environ.get("REACT_AGENT_CHECKPOINTER", "none") or "none").strip().lower()
    mode = raw_mode or "none"
    if mode in _DISABLED_CHECKPOINTER_MODES:
        return CheckpointerStatus(
            enabled=False,
            mode=mode,
            status="disabled",
            code="checkpointer_disabled",
            hint="Set REACT_AGENT_CHECKPOINTER=memory or sqlite for persistent continuity.",
        )

    saver = maybe_make_checkpointer()
    if saver is None:
        return CheckpointerStatus(
            enabled=False,
            mode=mode,
            status="unavailable",
            code="checkpointer_unavailable",
            hint="The requested checkpointer could not be initialized in this environment.",
        )

    return CheckpointerStatus(
        enabled=True,
        mode=mode,
        status="enabled",
        code="checkpointer_enabled",
    )


def probe_public_runtime() -> RuntimeReadinessProbe:
    """Probe adapter-visible runtime readiness without exposing raw internals."""
    provider_env = _provider_env_surface()
    search_env = _search_env_surface()
    checkpointer = _checkpointer_surface()

    runtime = ReadinessSurface(status="ready", code="runtime_ready")
    continuity_mode: ContinuityMode = "replay"
    graph_module: Any | None = None

    try:
        graph_module = import_module("react_agent.graph")
    except Exception as exc:
        _debug_runtime_exception("probe_public_runtime.import_graph", exc)
        runtime = ReadinessSurface(
            status="import_unavailable",
            code="runtime_import_unavailable",
            hint="LangGraph runtime could not be imported. Check runtime dependencies and required environment variables.",
        )
    else:
        if getattr(graph_module, "graph_persistent", None) is not None:
            continuity_mode = "persistent"

    overall_status: OverallStatus = "ready"
    if (
        runtime.status != "ready"
        or provider_env.status != "configured"
        or search_env.status != "configured"
        or checkpointer.status != "enabled"
    ):
        overall_status = "degraded"

    return RuntimeReadinessProbe(
        continuity_mode=continuity_mode,
        runtime=runtime,
        provider_env=provider_env,
        search_env=search_env,
        checkpointer=checkpointer,
        overall_status=overall_status,
        graph_module=graph_module,
    )


def prepare_public_turn_invoke(
    *,
    thread_id: str,
    history_turns: Sequence[PublicTurn],
    user_text: str,
) -> PreparedPublicTurnInvoke:
    """Prepare a public-safe invoke session shared by sync and stream entrypoints."""
    probe = probe_public_runtime()

    if probe.provider_env.status != "configured":
        raise PublicRuntimeUnavailable(
            "Provider credentials are not configured for public runtime invocation.",
            code=probe.provider_env.code,
            category="provider_env",
        )
    if probe.search_env.status != "configured":
        raise PublicRuntimeUnavailable(
            "Search dependency is not configured for public runtime invocation.",
            code=probe.search_env.code,
            category="provider_env",
        )
    if probe.runtime.status != "ready" or probe.graph_module is None:
        raise PublicRuntimeUnavailable(
            "LangGraph runtime is unavailable for public invocation.",
            code=probe.runtime.code,
            category="runtime",
        )

    graph_app = probe.graph_module.get_graph_for_invoke(
        thread_id if probe.continuity_mode == "persistent" else None
    )
    invoke_kwargs: Dict[str, Any] = {"context": Context()}
    if probe.continuity_mode == "persistent":
        invoke_input = {"messages": [("user", user_text)]}
        invoke_kwargs["config"] = {"configurable": {"thread_id": thread_id}}
    else:
        invoke_input = {"messages": replay_messages(history_turns, user_text)}

    return PreparedPublicTurnInvoke(
        continuity_mode=probe.continuity_mode,
        graph_app=graph_app,
        invoke_input=invoke_input,
        invoke_kwargs=invoke_kwargs,
    )


def get_checkpointer_status() -> tuple[bool, str]:
    """Return whether the configured checkpointer is available."""
    probe = probe_public_runtime()
    return probe.checkpointer.enabled, probe.checkpointer.mode


def _coerce_optional_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _layer_done_set(state: Dict[str, Any]) -> set[str]:
    raw = state.get("layer_done", {})
    if not isinstance(raw, dict):
        return set()
    return {str(layer).strip().upper() for layer, done in raw.items() if done}


def _build_stage_progress_data(
    state: Dict[str, Any],
    *,
    failed: bool = False,
) -> WorkflowStageEventData:
    layer_plan = state.get("layer_plan", {})
    current_layer = str(state.get("current_layer", "") or "").strip().upper()
    layer_done = _layer_done_set(state)
    mainline_ready = str(state.get("mainline_status", "") or "").strip().lower() == "ready"
    emitted_bundle = state.get("emitted_bundle", {})
    emitted_answer = bool(
        isinstance(emitted_bundle, dict) and str(emitted_bundle.get("answer", "") or "").strip()
    )
    final_answer_source = _coerce_optional_str(state.get("final_answer_source"))
    fusion_running = any(
        _coerce_optional_str(state.get(key))
        for key in ("baseline_status", "judge_status", "writer_status")
    )

    routing_completed = bool(layer_plan) or bool(current_layer)
    analysis_completed = "L2" in layer_done or current_layer in {"L3", "L4"} or mainline_ready
    risk_completed = "L3" in layer_done or current_layer == "L4" or mainline_ready
    summary_completed = mainline_ready or emitted_answer
    fusion_completed = bool(final_answer_source) or emitted_answer

    statuses: Dict[WorkflowStageKey, WorkflowStageStatus] = {
        "routing": "completed" if routing_completed else "running",
        "analysis": "completed" if analysis_completed else "running" if routing_completed else "waiting",
        "risk": (
            "completed"
            if risk_completed
            else "running"
            if current_layer == "L3" or ("L2" in layer_done and not mainline_ready)
            else "waiting"
        ),
        "summary": (
            "completed"
            if summary_completed
            else "running"
            if current_layer == "L4" or "L3" in layer_done
            else "waiting"
        ),
        "fusion": "completed" if fusion_completed else "running" if fusion_running else "waiting",
    }

    if failed and not fusion_completed:
        statuses["fusion"] = "failed"

    stages = [
        WorkflowStageProgressModel(key=key, title=_WORKFLOW_STAGE_TITLES[key], status=statuses[key])
        for key in _WORKFLOW_STAGE_ORDER
    ]

    current_stage: WorkflowStageKey | None = None
    for stage in stages:
        if stage.status == "failed":
            current_stage = stage.key
            break
    if current_stage is None:
        for stage in stages:
            if stage.status == "running":
                current_stage = stage.key
                break
    if current_stage is None and all(stage.status == "completed" for stage in stages):
        current_stage = "fusion"

    return WorkflowStageEventData(stages=stages, currentStage=current_stage)


def _has_workflow_snapshot_signal(state: Dict[str, Any]) -> bool:
    relevant_keys = (
        "run_id",
        "layer_plan",
        "layer_mode",
        "current_layer",
        "layer_done",
        "fanout_targets",
        "mainline_status",
        "baseline_status",
        "judge_status",
        "writer_status",
        "final_answer_source",
        "emitted_bundle",
    )
    for key in relevant_keys:
        value = state.get(key)
        if value in (None, "", {}, [], ()):
            continue
        return True
    return False


def _build_workflow_snapshot_event(
    state: Dict[str, Any],
    continuity_mode: ContinuityMode,
) -> WorkflowSnapshotEvent:
    return WorkflowSnapshotEvent(
        type="workflow.snapshot",
        data=WorkflowSnapshotEventData(
            workflow=build_workflow_snapshot(state, continuity_mode),
            runId=_coerce_optional_str(state.get("run_id")),
            continuityMode=continuity_mode,
        ),
    )


async def stream_public_turn(
    *,
    thread_id: str,
    user_text: str,
    prepared: PreparedPublicTurnInvoke,
) -> AsyncIterator[RunStartedEvent | WorkflowStageEvent | WorkflowSnapshotEvent | StreamPublicTurnCompleted]:
    """Stream safe workflow/progress events without exposing raw graph state."""
    continuity_mode = prepared.continuity_mode
    yield RunStartedEvent(
        type="run.started",
        data=RunStartedEventData(threadId=thread_id, continuityMode=continuity_mode),
    )

    last_stage_event = WorkflowStageEvent(
        type="workflow.stage",
        data=_build_stage_progress_data({}),
    )
    last_stage_payload = last_stage_event.model_dump(mode="json")
    last_snapshot_payload: Dict[str, Any] | None = None
    last_state: Dict[str, Any] | None = None
    yield last_stage_event

    try:
        async for state in prepared.graph_app.astream(
            prepared.invoke_input,
            stream_mode="values",
            **prepared.invoke_kwargs,
        ):
            if not isinstance(state, dict):
                continue
            last_state = state

            next_stage_event = WorkflowStageEvent(
                type="workflow.stage",
                data=_build_stage_progress_data(state),
            )
            next_stage_payload = next_stage_event.model_dump(mode="json")
            if next_stage_payload != last_stage_payload:
                last_stage_payload = next_stage_payload
                last_stage_event = next_stage_event
                yield next_stage_event

            if _has_workflow_snapshot_signal(state):
                next_snapshot_event = _build_workflow_snapshot_event(state, continuity_mode)
                next_snapshot_payload = next_snapshot_event.model_dump(mode="json")
                if next_snapshot_payload != last_snapshot_payload:
                    last_snapshot_payload = next_snapshot_payload
                    yield next_snapshot_event
    except Exception as exc:
        _debug_runtime_exception(
            "stream_public_turn.astream",
            exc,
            thread_id=thread_id,
            continuity_mode=continuity_mode,
            user_text=user_text,
        )
        failed_stage_event = WorkflowStageEvent(
            type="workflow.stage",
            data=_build_stage_progress_data(last_state or {}, failed=True),
        )
        failed_stage_payload = failed_stage_event.model_dump(mode="json")
        if failed_stage_payload != last_stage_payload:
            yield failed_stage_event
        raise PublicRuntimeUnavailable(
            "LangGraph runtime invocation failed before a public answer could be produced.",
            code="runtime_invoke_unavailable",
            category="runtime",
        ) from None

    if not isinstance(last_state, dict):
        raise PublicRuntimeError(
            "LangGraph runtime returned an invalid completed state.",
            code="runtime_state_invalid",
            category="contract",
        )

    try:
        assistant_turn = build_assistant_turn(last_state, continuity_mode)
    except Exception as exc:
        _debug_runtime_exception(
            "stream_public_turn.build_assistant_turn",
            exc,
            thread_id=thread_id,
            continuity_mode=continuity_mode,
            user_text=user_text,
        )
        failed_stage_event = WorkflowStageEvent(
            type="workflow.stage",
            data=_build_stage_progress_data(last_state, failed=True),
        )
        failed_stage_payload = failed_stage_event.model_dump(mode="json")
        if failed_stage_payload != last_stage_payload:
            yield failed_stage_event
        raise PublicRuntimeError(
            "Completed state could not be mapped into the public contract.",
            code="public_mapping_failed",
            category="contract",
        ) from None

    yield StreamPublicTurnCompleted(
        assistant_turn=assistant_turn,
        continuity_mode=continuity_mode,
    )


async def invoke_public_turn(
    *,
    thread_id: str,
    history_turns: Sequence[PublicTurn],
    user_text: str,
) -> tuple[PublicTurn, ContinuityMode]:
    """Invoke the runtime and map a completed state to a safe assistant turn."""
    prepared = prepare_public_turn_invoke(
        thread_id=thread_id,
        history_turns=history_turns,
        user_text=user_text,
    )

    try:
        state = await prepared.graph_app.ainvoke(prepared.invoke_input, **prepared.invoke_kwargs)
    except Exception as exc:
        _debug_runtime_exception(
            "invoke_public_turn.ainvoke",
            exc,
            thread_id=thread_id,
            continuity_mode=prepared.continuity_mode,
            user_text=user_text,
        )
        raise PublicRuntimeUnavailable(
            "LangGraph runtime invocation failed before a public answer could be produced.",
            code="runtime_invoke_unavailable",
            category="runtime",
        ) from None

    if not isinstance(state, dict):
        raise PublicRuntimeError(
            "LangGraph runtime returned an invalid completed state.",
            code="runtime_state_invalid",
            category="contract",
        )

    try:
        assistant_turn = build_assistant_turn(state, prepared.continuity_mode)
    except Exception as exc:
        _debug_runtime_exception(
            "invoke_public_turn.build_assistant_turn",
            exc,
            thread_id=thread_id,
            continuity_mode=prepared.continuity_mode,
            user_text=user_text,
        )
        raise PublicRuntimeError(
            "Completed state could not be mapped into the public contract.",
            code="public_mapping_failed",
            category="contract",
        ) from None

    return assistant_turn, prepared.continuity_mode
