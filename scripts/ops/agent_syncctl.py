#!/usr/bin/env python
"""Thin wrapper for the read-only agent sync planner CLI."""

from __future__ import annotations

from react_agent.ops.agent_syncctl import main

if __name__ == "__main__":
    raise SystemExit(main())

