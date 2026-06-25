#!/usr/bin/env python
"""Thin wrapper for the read-only agent sync planner CLI."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from react_agent.ops.agent_syncctl import main

if __name__ == "__main__":
    raise SystemExit(main())
