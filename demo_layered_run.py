"""Minimal demo to run the 4-layer pipeline and optional thread persistence.

Usage:
    # set your API key envs first, e.g. OPENAI_API_KEY / TAVILY_API_KEY
    # optional: enable in-process thread persistence for Python calls
    #   PowerShell: $env:REACT_AGENT_CHECKPOINTER = "memory"
    #   Bash: export REACT_AGENT_CHECKPOINTER=memory
    python demo_layered_run.py
"""

import asyncio
import os
from typing import Any, Dict, Optional

import react_agent.graph as graph_module
from react_agent.context import Context


def _msg_len(state: Dict[str, Any]) -> int:
    msgs = state.get("messages") or []
    return len(msgs)


def _snippet(state: Dict[str, Any], n: int = 160) -> str:
    msgs = state.get("messages") or []
    if not msgs:
        return ""
    content = getattr(msgs[-1], "content", "")
    text = content if isinstance(content, str) else str(content)
    return text[:n]


def _thread_summary_len(state: Dict[str, Any]) -> int:
    return len((state.get("thread_summary") or ""))


def _thread_summary_snippet(state: Dict[str, Any], n: int = 120) -> str:
    text = str(state.get("thread_summary") or "")
    return text[:n]


async def _run_once(question: str, *, context: Context, thread_id: Optional[str] = None) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"context": context}
    graph_app = graph_module.get_graph_for_invoke(thread_id)
    if thread_id:
        kwargs["config"] = {"configurable": {"thread_id": thread_id}}
    return await graph_app.ainvoke({"messages": [("user", question)]}, **kwargs)


async def main() -> None:
    print("REACT_AGENT_CHECKPOINTER =", os.environ.get("REACT_AGENT_CHECKPOINTER", "(unset)"))
    print("DISABLE_SEARCH =", os.environ.get("DISABLE_SEARCH", "(unset)"))
    print("MODEL =", os.environ.get("MODEL", "deepseek/deepseek-chat"))
    print("Persistent graph available =", bool(getattr(graph_module, "graph_persistent", None)))
    print("REACT_AGENT_THREAD_SUMMARY =", os.environ.get("REACT_AGENT_THREAD_SUMMARY", "(unset)"))
    print("REACT_AGENT_MESSAGES_WINDOW =", os.environ.get("REACT_AGENT_MESSAGES_WINDOW", "(unset)"))
    print("REACT_AGENT_MESSAGES_WINDOW_SIZE =", os.environ.get("REACT_AGENT_MESSAGES_WINDOW_SIZE", "(unset)"))
    print("LOCAL_TRACE =", os.environ.get("LOCAL_TRACE", "(unset)"))
    print(
        "Tip: set REACT_AGENT_CHECKPOINTER=memory before starting this script to enable same-thread "
        "state reuse in Python/demo invocations."
    )
    print(
        "Tip: set REACT_AGENT_THREAD_SUMMARY=1 to enable extractive thread_summary updates/injection "
        "(Router + Manager Summary only)."
    )
    print(
        "Tip: set REACT_AGENT_MESSAGES_WINDOW=1 (and optional REACT_AGENT_MESSAGES_WINDOW_SIZE=20) "
        "to trim only Router/Manager Summary LLM inputs; set LOCAL_TRACE=1 to inspect router_ctx/manager_ctx events."
    )

    context = Context(model=os.environ.get("MODEL", "deepseek/deepseek-chat"))

    print("\n=== Run A (same thread_id) ===")
    thread_id = "demo-thread-1"
    a1 = await _run_once("我叫小明。请记住这个名字。", context=context, thread_id=thread_id)
    print("A1 messages_len:", _msg_len(a1))
    print("A1 thread_summary_len:", _thread_summary_len(a1))
    print("A1 thread_summary:", _thread_summary_snippet(a1))
    print("A1 final snippet:", _snippet(a1))

    a2 = await _run_once("我刚才叫什么？只回答名字。", context=context, thread_id=thread_id)
    print("A2 messages_len:", _msg_len(a2))
    print("A2 thread_summary_len:", _thread_summary_len(a2))
    print("A2 thread_summary:", _thread_summary_snippet(a2))
    print("A2 final snippet:", _snippet(a2))

    print("\n=== Run B (no thread_id, control) ===")
    b1 = await _run_once("我叫小明。请记住这个名字。", context=context)
    print("B1 messages_len:", _msg_len(b1))
    print("B1 thread_summary_len:", _thread_summary_len(b1))
    print("B1 thread_summary:", _thread_summary_snippet(b1))
    print("B1 final snippet:", _snippet(b1))

    b2 = await _run_once("我刚才叫什么？只回答名字。", context=context)
    print("B2 messages_len:", _msg_len(b2))
    print("B2 thread_summary_len:", _thread_summary_len(b2))
    print("B2 thread_summary:", _thread_summary_snippet(b2))
    print("B2 final snippet:", _snippet(b2))


if __name__ == "__main__":
    asyncio.run(main())
