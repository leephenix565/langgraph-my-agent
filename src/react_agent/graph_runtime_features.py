"""Runtime feature helpers shared by the layered graph runtime."""

from __future__ import annotations

import os
import warnings
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from react_agent.agent_types import AgentOutput
from react_agent.graph_observability import _truncate
from react_agent.state import State
from react_agent.utils import get_message_text

_TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}


def _is_search_disabled_globally() -> bool:
    """Read DISABLE_SEARCH at call time so long-lived processes can reflect env updates."""
    return str(os.environ.get("DISABLE_SEARCH", "") or "").strip().lower() in _TRUTHY_ENV_VALUES


def _thread_summary_enabled() -> bool:
    """Read thread summary toggle at call time to support long-lived processes."""
    raw = (os.environ.get("REACT_AGENT_THREAD_SUMMARY", "0") or "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def _thread_summary_max_chars() -> int:
    raw = (os.environ.get("REACT_AGENT_THREAD_SUMMARY_MAX_CHARS", "2000") or "2000").strip()
    try:
        val = int(raw)
    except Exception:
        warnings.warn(
            f"Invalid REACT_AGENT_THREAD_SUMMARY_MAX_CHARS='{raw}', using default 2000.",
            RuntimeWarning,
        )
        return 2000
    if val <= 0:
        warnings.warn(
            f"Invalid REACT_AGENT_THREAD_SUMMARY_MAX_CHARS='{raw}', using default 2000.",
            RuntimeWarning,
        )
        return 2000
    return val


def _get_latest_user_question(messages: List[AnyMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return get_message_text(msg)
    return get_message_text(messages[-1]) if messages else ""


def _latest_ai_message_text(messages: List[AnyMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return get_message_text(msg)
    return ""


def _build_thread_summary(state: State) -> str:
    """Build an extractive per-thread summary from explicit text only (no extra LLM call)."""
    msgs = list(state.get("messages", []))
    latest_question = state.get("current_question") or _get_latest_user_question(msgs)
    latest_final_answer = _latest_ai_message_text(msgs)
    if not latest_question and not latest_final_answer:
        return ""

    max_chars = _thread_summary_max_chars()
    q_cap = max(120, min(600, max_chars // 3))
    a_cap = max(240, max_chars - q_cap - 80)
    parts: List[str] = []
    if latest_question:
        parts.append(f"Recent user question:\n{_truncate(latest_question, q_cap)}")
    if latest_final_answer:
        parts.append(f"Recent final answer:\n{_truncate(latest_final_answer, a_cap)}")
    summary = _truncate("\n\n".join(parts), max_chars)
    return summary[:max_chars]


def _thread_summary_system_msg(thread_summary: str) -> Dict[str, str]:
    return {
        "role": "system",
        "content": (
            "THREAD SUMMARY (extractive, prior-turn context; use only as supporting context):\n"
            f"{thread_summary}"
        ),
    }


def _stable_consume_enabled() -> bool:
    """Read stable-findings consume toggle at call time; default disabled."""
    raw = (os.environ.get("REACT_AGENT_STABLE_CONSUME", "0") or "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def _read_positive_int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = (os.environ.get(name, str(default)) or str(default)).strip()
    try:
        value = int(raw)
    except Exception:
        warnings.warn(
            f"Invalid {name}='{raw}', using default {default}.",
            RuntimeWarning,
        )
        return default
    if value < minimum:
        warnings.warn(
            f"Invalid {name}='{raw}', clamping to {minimum}.",
            RuntimeWarning,
        )
        return minimum
    return value


def _stable_summary_max_chars() -> int:
    return _read_positive_int_env("REACT_AGENT_STABLE_SUMMARY_MAX_CHARS", 1200)


def _stable_summary_max_items() -> int:
    return _read_positive_int_env("REACT_AGENT_STABLE_SUMMARY_MAX_ITEMS", 5)


def _stable_summary_system_msg(stable_summary: str) -> Dict[str, str]:
    return {
        "role": "system",
        "content": (
            "STABLE FINDINGS (extractive index; prior finalized turns, supporting context only):\n"
            f"{stable_summary}"
        ),
    }


def _build_stable_summary(state: State) -> str:
    """Build a deterministic extractive stable summary from stable_findings."""
    raw = state.get("stable_findings", [])
    if not isinstance(raw, list) or not raw:
        return ""

    max_items = _stable_summary_max_items()
    max_chars = _stable_summary_max_chars()
    question_cap = max(80, min(260, max_chars // 6))
    answer_cap = max(120, min(360, max_chars // 4))
    evidence_cap = max(80, min(200, max_chars // 8))

    entries = raw[-max_items:]
    lines: List[str] = ["STABLE FINDINGS (extractive index):"]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        question = _truncate(str(entry.get("question", "")).strip(), question_cap)
        final_answer = _truncate(str(entry.get("final_answer", "")).strip(), answer_cap)
        if not question and not final_answer:
            continue
        lines.append(f"- Q: {question or '(none)'}")
        lines.append(f"  A: {final_answer or '(none)'}")

        evidence_items: List[str] = []
        evidence = entry.get("evidence", [])
        if isinstance(evidence, list):
            for item in evidence:
                if len(evidence_items) >= 2:
                    break
                if isinstance(item, dict):
                    text = str(item.get("text", "")).strip()
                    agent_id = str(item.get("agent_id", "")).strip()
                    if not text:
                        continue
                    truncated = _truncate(text, evidence_cap)
                    evidence_items.append(f"[{agent_id}] {truncated}" if agent_id else truncated)
                elif isinstance(item, str):
                    text = item.strip()
                    if text:
                        evidence_items.append(_truncate(text, evidence_cap))
        if evidence_items:
            lines.append(f"  Evidence: {'; '.join(evidence_items)}")

    summary = "\n".join(lines)
    return _truncate(summary, max_chars)[:max_chars]


def _messages_window_enabled() -> bool:
    """Read messages-window toggle at call time to support long-lived processes."""
    raw = (os.environ.get("REACT_AGENT_MESSAGES_WINDOW", "0") or "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def _messages_window_size() -> int:
    raw = (os.environ.get("REACT_AGENT_MESSAGES_WINDOW_SIZE", "20") or "20").strip()
    try:
        val = int(raw)
    except Exception:
        warnings.warn(
            f"Invalid REACT_AGENT_MESSAGES_WINDOW_SIZE='{raw}', using default 20.",
            RuntimeWarning,
        )
        return 20
    if val <= 0:
        warnings.warn(
            f"Invalid REACT_AGENT_MESSAGES_WINDOW_SIZE='{raw}', clamping to 1.",
            RuntimeWarning,
        )
        return 1
    return val


def _window_messages(full_messages: List[AnyMessage]) -> List[AnyMessage]:
    """Return a tail window of messages when enabled; otherwise return full messages."""
    if not _messages_window_enabled():
        return full_messages
    size = _messages_window_size()
    if len(full_messages) <= size:
        return full_messages
    return full_messages[-size:]


def _results_pools_enabled() -> bool:
    """Enable ephemeral/stable result pools via env; default off for backward compatibility."""
    raw = (os.environ.get("REACT_AGENT_RESULTS_POOLS", "0") or "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def _stable_findings_max_items() -> int:
    return _read_positive_int_env("REACT_AGENT_STABLE_FINDINGS_MAX_ITEMS", 50)


def _evidence_max_items() -> int:
    return _read_positive_int_env("REACT_AGENT_EVIDENCE_MAX_ITEMS", 20)


def _evidence_max_chars() -> int:
    return _read_positive_int_env("REACT_AGENT_EVIDENCE_MAX_CHARS", 500)


def _stable_text_max_chars() -> int:
    return _read_positive_int_env("REACT_AGENT_STABLE_TEXT_MAX_CHARS", 2000)


def _get_runtime_results_pool(state: State) -> Dict[str, AgentOutput]:
    """Return current-turn result pool; phase-guarded to keep default behavior unchanged."""
    if _results_pools_enabled():
        ep = state.get("ephemeral_results")
        if isinstance(ep, dict):
            return ep
    legacy = state.get("analyst_results", {})
    return legacy if isinstance(legacy, dict) else {}


def _build_stable_evidence_index(filtered_results: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract bounded evidence/index cards from filtered agent outputs."""
    max_items = _evidence_max_items()
    max_chars = _evidence_max_chars()
    cards: List[Dict[str, str]] = []
    for agent_id, result in filtered_results.items():
        if not isinstance(result, dict):
            continue
        evidence = result.get("evidence")
        if isinstance(evidence, list):
            for item in evidence:
                if not isinstance(item, str):
                    continue
                text = _truncate(item, max_chars).strip()
                if not text:
                    continue
                cards.append({"agent_id": str(agent_id), "kind": "evidence", "text": text})
                if len(cards) >= max_items:
                    return cards
        key_points = result.get("key_points")
        if isinstance(key_points, list):
            for item in key_points:
                if not isinstance(item, str):
                    continue
                text = _truncate(item, max_chars).strip()
                if not text:
                    continue
                cards.append({"agent_id": str(agent_id), "kind": "key_point", "text": text})
                if len(cards) >= max_items:
                    return cards
    return cards


def _build_stable_finding_entry(
    question: str,
    final_answer_text: str,
    filtered_results: Dict[str, Any],
    state: State,
) -> Dict[str, Any]:
    """Build a bounded stable finding entry from explicit final-turn artifacts."""
    text_cap = _stable_text_max_chars()
    return {
        "kind": "final_answer",
        "question": _truncate(question, text_cap),
        "final_answer": _truncate(final_answer_text, text_cap),
        "evidence": _build_stable_evidence_index(filtered_results),
        "run_id": str(state.get("run_id") or ""),
    }
