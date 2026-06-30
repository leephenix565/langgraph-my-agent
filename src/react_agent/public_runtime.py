# ruff: noqa: D101, D103, D107
"""Runtime invocation helpers for the public API."""

from __future__ import annotations

import os
import sys
import traceback
from dataclasses import dataclass
from importlib import import_module
from typing import Any, AsyncIterator, Dict, Sequence

from react_agent.context import Context
from react_agent.fixed_dag_contracts import FIXED_DAG_STAGE_ORDER
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
from react_agent.public_mapping import (
    build_assistant_turn,
    build_workflow_snapshot,
    replay_messages,
)

_PROVIDER_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ROUTER_OPENAI_API_KEY",
    "BASELINE_OPENAI_API_KEY",
    "GOOGLE_API_KEY",
)
_DISABLED_CHECKPOINTER_MODES = {"", "none", "off", "0"}
_TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}


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
    "planning": "规划",
    "evidence": "证据接入",
    "l2_analysis": "L2 结论",
    "dimension_composite": "维度综合",
    "decision": "决策",
    "report": "报告",
}
_WORKFLOW_STAGE_ORDER: tuple[WorkflowStageKey, ...] = FIXED_DAG_STAGE_ORDER


def _is_env_present(name: str) -> bool:
    return bool(str(os.environ.get(name, "") or "").strip())


def _is_truthy_env(name: str) -> bool:
    return str(os.environ.get(name, "") or "").strip().lower() in _TRUTHY_ENV_VALUES


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
    sys.stderr.write(f"[public_runtime][exception] {context}\n")
    sys.stderr.flush()
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    sys.stderr.flush()


def _provider_env_surface() -> ReadinessSurface:
    if any(_is_env_present(key) for key in _PROVIDER_ENV_KEYS):
        return ReadinessSurface(status="configured", code="provider_env_configured")
    return ReadinessSurface(
        status="missing",
        code="provider_env_missing_optional_for_reset",
        hint="R3 重置骨架无需 provider 凭据即可调用。",
    )


def _search_env_surface() -> ReadinessSurface:
    if _is_truthy_env("DISABLE_SEARCH"):
        return ReadinessSurface(
            status="disabled",
            code="search_env_disabled",
            hint="搜索已禁用；R3 重置骨架不需要搜索。",
        )
    if _is_env_present("TAVILY_API_KEY"):
        return ReadinessSurface(status="configured", code="search_env_available")
    return ReadinessSurface(
        status="missing",
        code="search_env_missing_optional_for_reset",
        hint="R3 重置骨架无需 Tavily 搜索即可调用。",
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
            hint="设置 REACT_AGENT_CHECKPOINTER=memory 或 sqlite 可启用持久连续性。",
        )

    saver = maybe_make_checkpointer()
    if saver is None:
        return CheckpointerStatus(
            enabled=False,
            mode=mode,
            status="unavailable",
            code="checkpointer_unavailable",
            hint="当前环境无法初始化请求的 checkpointer。",
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
            hint="无法导入 LangGraph 运行时。",
        )
    else:
        if getattr(graph_module, "graph_persistent", None) is not None:
            continuity_mode = "persistent"

    overall_status: OverallStatus = "ready"
    if runtime.status != "ready" or checkpointer.status != "enabled":
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
    context: Context | None = None,
) -> PreparedPublicTurnInvoke:
    """Prepare a public-safe invoke session shared by sync and stream entrypoints."""
    probe = probe_public_runtime()
    if probe.runtime.status != "ready" or probe.graph_module is None:
        raise PublicRuntimeUnavailable(
            "LangGraph 运行时不可用于公开调用。",
            code=probe.runtime.code,
            category="runtime",
        )

    graph_app = probe.graph_module.get_graph_for_invoke(
        thread_id if probe.continuity_mode == "persistent" else None
    )
    invoke_kwargs: Dict[str, Any] = {"context": context or Context()}
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
    probe = probe_public_runtime()
    return probe.checkpointer.enabled, probe.checkpointer.mode


def _coerce_optional_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _completed_steps(state: Dict[str, Any]) -> set[str]:
    snapshot = state.get("workflow_snapshot", {})
    if not isinstance(snapshot, dict):
        return set()
    raw = snapshot.get("completedSteps", [])
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw if str(item)}


def _stage_step_ids(state: Dict[str, Any]) -> dict[str, set[str]]:
    snapshot = state.get("workflow_snapshot", {})
    if not isinstance(snapshot, dict):
        return {}
    stages = snapshot.get("stages", [])
    result: dict[str, set[str]] = {}
    if not isinstance(stages, list):
        return result
    for item in stages:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        step_ids = item.get("stepIds", [])
        if key and isinstance(step_ids, list):
            result[key] = {str(step_id) for step_id in step_ids}
    return result


def _build_stage_progress_data(
    state: Dict[str, Any],
    *,
    failed: bool = False,
) -> WorkflowStageEventData:
    snapshot = state.get("workflow_snapshot", {})
    current_stage = None
    if isinstance(snapshot, dict):
        current_stage = snapshot.get("currentStage")
    current_stage = current_stage or "planning"
    completed_steps = _completed_steps(state)
    stage_steps = _stage_step_ids(state)

    statuses: Dict[WorkflowStageKey, WorkflowStageStatus] = {}
    reached_current = False
    for key in _WORKFLOW_STAGE_ORDER:
        step_ids = stage_steps.get(key, set())
        if step_ids and step_ids.issubset(completed_steps):
            statuses[key] = "completed"
            continue
        if key == current_stage:
            statuses[key] = "failed" if failed else "running"
            reached_current = True
            continue
        statuses[key] = "waiting" if reached_current else "completed" if completed_steps else "waiting"

    stages = [
        WorkflowStageProgressModel(key=key, title=_WORKFLOW_STAGE_TITLES[key], status=statuses[key])
        for key in _WORKFLOW_STAGE_ORDER
    ]

    active_stage: WorkflowStageKey | None = None
    for stage in stages:
        if stage.status in {"failed", "running"}:
            active_stage = stage.key
            break
    if active_stage is None and all(stage.status == "completed" for stage in stages):
        active_stage = "report"

    return WorkflowStageEventData(stages=stages, currentStage=active_stage)


def _has_workflow_snapshot_signal(state: Dict[str, Any]) -> bool:
    relevant_keys = (
        "run_id",
        "fixed_dag_plan",
        "data_bundle",
        "entity_relation_bundle",
        "dag_execution",
        "dag_step_results",
        "execution_batches",
        "l2_conclusions",
        "dimension_results",
        "decision_result",
        "report_result",
        "workflow_snapshot",
        "final_emit_payload",
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
        stream = getattr(prepared.graph_app, "stream", None)
        if callable(stream):
            state_iterable = stream(
                prepared.invoke_input,
                stream_mode="values",
                **prepared.invoke_kwargs,
            )
        else:
            state_iterable = prepared.graph_app.astream(
                prepared.invoke_input,
                stream_mode="values",
                **prepared.invoke_kwargs,
            )
        if hasattr(state_iterable, "__aiter__"):
            state_source = state_iterable
        else:
            async def _sync_state_source() -> AsyncIterator[Any]:
                for item in state_iterable:
                    yield item

            state_source = _sync_state_source()

        async for state in state_source:
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
            "stream_public_turn.stream",
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
            "LangGraph 运行时在生成公开回答前调用失败。",
            code="runtime_invoke_unavailable",
            category="runtime",
        ) from None

    if not isinstance(last_state, dict):
        raise PublicRuntimeError(
            "LangGraph 运行时返回了无效的完成状态。",
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
            "完成状态无法映射到 public contract。",
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
    context: Context | None = None,
) -> tuple[PublicTurn, ContinuityMode]:
    """Invoke the runtime and map a completed state to a safe assistant turn."""
    prepared = prepare_public_turn_invoke(
        thread_id=thread_id,
        history_turns=history_turns,
        user_text=user_text,
        context=context,
    )

    try:
        invoke = getattr(prepared.graph_app, "invoke", None)
        if callable(invoke):
            state = invoke(prepared.invoke_input, **prepared.invoke_kwargs)
        else:
            state = await prepared.graph_app.ainvoke(
                prepared.invoke_input,
                **prepared.invoke_kwargs,
            )
    except Exception as exc:
        _debug_runtime_exception(
            "invoke_public_turn.invoke",
            exc,
            thread_id=thread_id,
            continuity_mode=prepared.continuity_mode,
            user_text=user_text,
        )
        raise PublicRuntimeUnavailable(
            "LangGraph 运行时在生成公开回答前调用失败。",
            code="runtime_invoke_unavailable",
            category="runtime",
        ) from None

    if not isinstance(state, dict):
        raise PublicRuntimeError(
            "LangGraph 运行时返回了无效的完成状态。",
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
            "完成状态无法映射到 public contract。",
            code="public_mapping_failed",
            category="contract",
        ) from None

    return assistant_turn, prepared.continuity_mode
