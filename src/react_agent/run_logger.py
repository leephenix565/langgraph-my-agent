"""Lightweight JSONL run logger for optional local tracing."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _should_enable() -> bool:
    return os.environ.get("LOCAL_TRACE", "0") == "1"


def _max_chars() -> int:
    try:
        return int(os.environ.get("TRACE_MAX_CHARS", "4000"))
    except Exception:
        return 4000


def _log_dir() -> Path:
    raw = os.environ.get("LOG_DIR")
    if raw:
        return Path(raw)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Path("log") / date_str


def _truncate(val: str, limit: int) -> str:
    if len(val) <= limit:
        return val
    return val[: limit - 8] + "...[trunc]"


def _sanitize(obj: Any, limit: int) -> Any:
    """Drop sensitive keys and truncate long strings recursively."""
    sensitive_keys = {"api_key", "token", "secret", "password"}
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(sk in lk for sk in sensitive_keys):
                continue
            out[k] = _sanitize(v, limit)
        return out
    if isinstance(obj, list):
        return [_sanitize(v, limit) for v in obj]
    if isinstance(obj, str):
        return _truncate(obj, limit)
    return obj


class RunLogger:
    """JSONL logger scoped to a single run."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.enabled = _should_enable()
        self.max_chars = _max_chars()
        self.log_path: Optional[Path] = None
        self.log_dir: Optional[Path] = None
        if self.enabled:
            self.log_dir = _log_dir()
            self.log_path = self.log_dir / f"{self.run_id}.jsonl"

    def log_event(self, event: str, **fields: Any) -> None:
        if not self.enabled or not self.log_path:
            return
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "event": event,
        }
        record.update(_sanitize(fields, self.max_chars))
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self._log_async(record))
                return
        except RuntimeError:
            # No running loop; fall back to blocking path.
            pass
        self._log_blocking(record)

    def _log_blocking(self, record: Dict[str, Any]) -> None:
        """Blocking path (used only when no event loop is running)."""
        try:
            if self.log_dir:
                self.log_dir.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:  # type: ignore[arg-type]
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            return

    async def _log_async(self, record: Dict[str, Any]) -> None:
        """Async-safe logging using thread offload for I/O."""
        if not self.log_dir or not self.log_path:
            return
        try:
            await asyncio.to_thread(self.log_dir.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(self._write_record, record)
        except Exception:
            return

    def _write_record(self, record: Dict[str, Any]) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:  # type: ignore[arg-type]
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_run_logger(run_id: str | None) -> RunLogger:
    rid = run_id or uuid.uuid4().hex[:8]
    return RunLogger(rid)
