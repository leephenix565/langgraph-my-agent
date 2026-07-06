# ruff: noqa: D101, D103
"""Shim — moved to react_agent.ops_sync.agent_syncctl."""

from react_agent.ops_sync.agent_syncctl import *  # noqa: F401, F403
from react_agent.ops_sync.agent_syncctl import main as main

__all__ = ["main"]
