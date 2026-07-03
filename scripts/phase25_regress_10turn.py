"""Phase 2.5 regression runner: same-thread multi-turn invoke with consume switch.

This script is tooling-only. It does not modify core runtime logic.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_QUESTIONS: List[str] = [
    "Summarize 3 key 3-6 month gold drivers. Answer <=120 Chinese chars, bullet style.",
    "Expand driver #1 into a causal chain. Answer <=120 Chinese chars, bullet style.",
    "Add a counterfactual: stronger USD. How does it change the view? <=120 chars.",
    "Give bullish/neutral/bearish scenarios, one point each. <=120 chars.",
    "Add one risk from geopolitical easing. <=120 chars.",
    "Compress current view into <=80 Chinese chars.",
    "If real rates rise, which link gets hit first? <=120 chars.",
    "List the top 2 uncertainties. <=80 chars.",
    "If inflation cools faster, update the scenario. <=120 chars.",
    "Final: list 3 executable watch metrics. <=120 chars.",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 2.5 ten-turn regression on same thread_id with consume switch."
    )
    parser.add_argument("--thread_id", type=str, default="phase25-regress-10turn")
    parser.add_argument("--log_dir", type=str, required=True)
    parser.add_argument("--turns", type=int, default=10)
    parser.add_argument("--consume_switch_turn", type=int, default=4)
    parser.add_argument("--window_size", type=int, default=20)
    parser.add_argument(
        "--use_real_model",
        type=str,
        choices=("auto", "always", "never"),
        default="auto",
        help="auto=try real first and fallback to dummy on first failure.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("MODEL", "deepseek/deepseek-v4-flash"),
        help="Context.model passed to graph invocations.",
    )
    parser.add_argument(
        "--question_file",
        type=str,
        default="",
        help="Optional plain-text file (one question per line) to override defaults.",
    )
    parser.add_argument(
        "--summary_out",
        type=str,
        default="",
        help="Optional output JSON path. Default: <log_dir>/per_turn_summary.json",
    )
    return parser.parse_args()


def _load_questions(args: argparse.Namespace) -> List[str]:
    if args.question_file:
        path = Path(args.question_file)
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
        out = [line for line in lines if line]
    else:
        out = list(DEFAULT_QUESTIONS)
    if args.turns <= 0:
        raise ValueError("--turns must be > 0")
    if not out:
        raise ValueError("No questions available.")
    if len(out) >= args.turns:
        return out[: args.turns]
    padded = list(out)
    while len(padded) < args.turns:
        padded.append(out[-1])
    return padded


def _configure_env(log_dir: Path, window_size: int) -> None:
    os.environ["REACT_AGENT_CHECKPOINTER"] = "memory"
    os.environ["REACT_AGENT_RESULTS_POOLS"] = "1"
    os.environ["REACT_AGENT_THREAD_SUMMARY"] = "1"
    os.environ["REACT_AGENT_MESSAGES_WINDOW"] = "1"
    os.environ["REACT_AGENT_MESSAGES_WINDOW_SIZE"] = str(max(1, int(window_size)))
    os.environ["LOCAL_TRACE"] = "1"
    os.environ["DISABLE_SEARCH"] = "1"
    os.environ.setdefault("TAVILY_API_KEY", "dummy-key")
    os.environ["LOG_DIR"] = str(log_dir)


def _clear_log_dir(log_dir: Path) -> None:
    if not log_dir.exists():
        return
    for path in log_dir.glob("*.jsonl"):
        try:
            path.unlink()
        except OSError:
            pass


def _install_dependency_shims() -> None:
    """Best-effort import shims so runner can execute in minimal local envs."""
    try:
        import langchain_community.tools.tavily_search  # type: ignore  # noqa: F401
    except Exception:
        import types

        lc_pkg = sys.modules.get("langchain_community")
        if lc_pkg is None:
            lc_pkg = types.ModuleType("langchain_community")
            sys.modules["langchain_community"] = lc_pkg
        tools_pkg = sys.modules.get("langchain_community.tools")
        if tools_pkg is None:
            tools_pkg = types.ModuleType("langchain_community.tools")
            sys.modules["langchain_community.tools"] = tools_pkg
        tavily_mod = types.ModuleType("langchain_community.tools.tavily_search")

        class _DummyTavilySearchResults:
            def __init__(self, max_results: int = 5, search_depth: str = "basic", **_kwargs: Any) -> None:
                self.max_results = max_results
                self.search_depth = search_depth
                self.name = "tavily_search"

            async def ainvoke(self, *_args: Any, **_kwargs: Any) -> List[Any]:
                return []

            def invoke(self, *_args: Any, **_kwargs: Any) -> List[Any]:
                return []

        tavily_mod.TavilySearchResults = _DummyTavilySearchResults
        sys.modules["langchain_community.tools.tavily_search"] = tavily_mod


def _patch_dummy_models(graph_module: Any, default_agents_module: Any) -> None:
    from langchain_core.messages import AIMessage

    def _dummy_loader(_fully_specified_name: str):
        class _DummyModel:
            async def ainvoke(self, _messages: Any, config: Dict[str, Any] | None = None) -> AIMessage:
                metadata = (config or {}).get("metadata", {})
                node_name = metadata.get("node_name", "")
                if node_name == "router":
                    plan = {
                        "L1": {"mode": "Star", "selected": []},
                        "L2": {"mode": "Star", "selected": []},
                        "L3": {"mode": "Star", "selected": []},
                        "L4": {"mode": "Star", "selected": []},
                    }
                    return AIMessage(content=json.dumps(plan, ensure_ascii=False))
                return AIMessage(content="Dummy final summary.")

        return _DummyModel()

    graph_module.load_chat_model = _dummy_loader
    default_agents_module.load_chat_model = _dummy_loader


def _safe_list_len(val: Any) -> int:
    return len(val) if isinstance(val, list) else 0


def _state_row(turn: int, consume_enabled: int, state: Dict[str, Any], graph_module: Any) -> Dict[str, Any]:
    route_value = ""
    try:
        route_value = str(graph_module.route_from_manager_summary(state))
    except Exception:
        route_value = "unavailable"
    return {
        "turn": turn,
        "consume_enabled": consume_enabled,
        "is_last_step": bool(state.get("is_last_step")),
        "stable_len": _safe_list_len(state.get("stable_findings")),
        "thread_summary_len": len(str(state.get("thread_summary") or "")),
        "messages_len": _safe_list_len(state.get("messages")),
        "route_from_manager_summary_return": route_value,
    }


async def _run_turns(
    *,
    graph_module: Any,
    context_obj: Any,
    questions: List[str],
    thread_id: str,
    consume_switch_turn: int,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows: List[Dict[str, Any]] = []
    failures: List[str] = []
    graph_app = graph_module.get_graph_for_invoke(thread_id)
    for idx, question in enumerate(questions, start=1):
        consume_enabled = 1 if idx >= consume_switch_turn else 0
        os.environ["REACT_AGENT_STABLE_CONSUME"] = str(consume_enabled)
        state = await graph_app.ainvoke(
            {"messages": [("user", question)]},
            context=context_obj,
            config={"configurable": {"thread_id": thread_id}},
        )
        row = _state_row(idx, consume_enabled, state, graph_module)
        rows.append(row)
        if not row["is_last_step"]:
            failures.append(f"turn={idx}: is_last_step=False")
        if idx >= 2 and row["stable_len"] <= 0:
            failures.append(f"turn={idx}: stable_len<=0 under results pools")
        print(
            f"turn={idx:02d} consume={consume_enabled} "
            f"is_last_step={int(row['is_last_step'])} stable_len={row['stable_len']} "
            f"thread_summary_len={row['thread_summary_len']} messages_len={row['messages_len']} "
            f"route={row['route_from_manager_summary_return']}"
        )
    return rows, failures


async def _main_async(args: argparse.Namespace) -> Dict[str, Any]:
    log_dir = Path(args.log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    _clear_log_dir(log_dir)
    _configure_env(log_dir=log_dir, window_size=args.window_size)
    questions = _load_questions(args)
    _install_dependency_shims()

    import react_agent.default_agents as default_agents_module
    import react_agent.graph as graph_module
    from react_agent.context import Context

    strategy = args.use_real_model
    if strategy == "never":
        _patch_dummy_models(graph_module, default_agents_module)
        strategy = "dummy"

    context_obj = Context(model=args.model)
    failures: List[str] = []
    rows: List[Dict[str, Any]] = []
    actual_thread_id = args.thread_id

    try:
        rows, failures = await _run_turns(
            graph_module=graph_module,
            context_obj=context_obj,
            questions=questions,
            thread_id=actual_thread_id,
            consume_switch_turn=args.consume_switch_turn,
        )
        if args.use_real_model == "auto":
            strategy = "real"
    except Exception as exc:
        if args.use_real_model != "auto":
            raise
        print(f"[warn] real-model run failed in auto mode, fallback to dummy: {type(exc).__name__}: {exc}")
        _patch_dummy_models(graph_module, default_agents_module)
        _clear_log_dir(log_dir)
        actual_thread_id = f"{args.thread_id}-dummy"
        rows, failures = await _run_turns(
            graph_module=graph_module,
            context_obj=context_obj,
            questions=questions,
            thread_id=actual_thread_id,
            consume_switch_turn=args.consume_switch_turn,
        )
        strategy = "dummy"

    summary = {
        "thread_id": args.thread_id,
        "actual_thread_id": actual_thread_id,
        "strategy": strategy,
        "model": args.model,
        "turns": args.turns,
        "consume_switch_turn": args.consume_switch_turn,
        "window_size": args.window_size,
        "log_dir": str(log_dir),
        "rows": rows,
        "failures": failures,
    }
    out_path = Path(args.summary_out).resolve() if args.summary_out else log_dir / "per_turn_summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] summary_json={out_path}")
    print(json.dumps(summary, ensure_ascii=False))
    return summary


def main() -> None:
    args = _parse_args()
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
