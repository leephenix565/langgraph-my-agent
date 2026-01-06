"""Generic stub agent tool factory for metadata-only roles."""

from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool

from react_agent.agents import AgentOutput


def build_generic_agent_tool(agent_id: str, description: str) -> Any:
    """Build a lightweight tool that emits deterministic AgentOutput."""

    @tool(f"agent_{agent_id}", description=description or "Auto-generated stub system agent.")
    async def _generic_agent(
        question: str,
        subtask: str,
        shared_context: Dict[str, Any] | None = None,
        history: List[Dict[str, Any]] | None = None,
        tools_config: Dict[str, Any] | None = None,
        router_plan_summary: str | None = None,
    ) -> AgentOutput:
        """Auto-generated stub system agent."""
        shared_context = shared_context or {}
        history = history or []
        tools_config = tools_config or {}
        key_points: List[str] = [
            f"Focus: {description[:80]}",
            f"Question: {question[:80]}",
            f"Subtask: {subtask[:80]}",
        ]
        evidence = [f"context_keys={list(shared_context.keys())[:3]}"]
        if tools_config:
            evidence.append(f"tools_config_keys={list(tools_config.keys())[:3]}")
        analysis = (
            f"[Stub:{agent_id}] {description}. Current question: {question}. "
            f"Subtask: {subtask}. History_len={len(history)}."
        )
        return {
            "analysis": analysis,
            "key_points": key_points,
            "evidence": evidence,
            "confidence": 0.5,
        }

    object.__setattr__(_generic_agent, "is_stub", True)
    return _generic_agent
