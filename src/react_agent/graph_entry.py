"""Entry helpers for compiled graph variants."""

from __future__ import annotations

import os
import warnings
from typing import Any, Tuple


def maybe_make_checkpointer():
    """Optionally create a checkpointer from env without changing default behavior."""
    mode = (os.environ.get("REACT_AGENT_CHECKPOINTER", "none") or "none").strip().lower()
    if mode in {"", "none", "off", "0"}:
        return None

    if mode == "memory":
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except Exception as exc:
            warnings.warn(
                f"REACT_AGENT_CHECKPOINTER=memory requested but MemorySaver is unavailable: {exc}",
                RuntimeWarning,
            )
            return None
        return MemorySaver()

    if mode == "sqlite":
        db_path = (os.environ.get("REACT_AGENT_CHECKPOINT_DB", "checkpoints.db") or "checkpoints.db").strip()
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except Exception as exc:
            warnings.warn(
                "REACT_AGENT_CHECKPOINTER=sqlite requested but sqlite saver dependency is unavailable "
                f"(REACT_AGENT_CHECKPOINT_DB={db_path}): {exc}",
                RuntimeWarning,
            )
            return None
        try:
            if hasattr(SqliteSaver, "from_conn_string"):
                return SqliteSaver.from_conn_string(db_path)
            return SqliteSaver(db_path)  # type: ignore[call-arg]
        except Exception as exc:
            warnings.warn(
                f"Failed to initialize sqlite checkpointer (REACT_AGENT_CHECKPOINT_DB={db_path}): {exc}",
                RuntimeWarning,
            )
            return None

    warnings.warn(
        f"Unknown REACT_AGENT_CHECKPOINTER='{mode}', expected one of: none, memory, sqlite. "
        "Falling back to no checkpointer.",
        RuntimeWarning,
    )
    return None


def compile_graph_variants(builder: Any, graph_name: str) -> Tuple[Any, Any]:
    """Compile replay and optional persistent graph variants."""
    graph = builder.compile(name=graph_name)
    checkpointer = maybe_make_checkpointer()
    graph_persistent = (
        builder.compile(name=graph_name, checkpointer=checkpointer)
        if checkpointer is not None
        else None
    )
    return graph, graph_persistent


def select_graph_for_invoke(thread_id: str | None, graph: Any, graph_persistent: Any) -> Any:
    """Select the persistent graph only when continuity has a thread id."""
    if thread_id and graph_persistent is not None:
        return graph_persistent
    return graph
