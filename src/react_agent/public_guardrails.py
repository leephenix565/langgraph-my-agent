"""Small-scope public API guardrails for trial deployments."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any

DEFAULT_RATE_LIMIT_PER_MINUTE = 120
DEFAULT_MAX_MESSAGE_CHARS = 20_000
DEFAULT_MAX_ACTIVE_STREAMS_PER_IP = 3
DEFAULT_REQUEST_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class PublicApiGuardrailConfig:
    rate_limit_per_minute: int
    max_message_chars: int
    max_active_streams_per_ip: int
    request_timeout_seconds: int


class PublicApiGuardrailViolation(RuntimeError):
    """Raised when a request violates public trial guardrails."""

    def __init__(self, *, status_code: int, code: str, message: str, category: str = "request") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.category = category


def _read_int_env(name: str, default: int) -> int:
    raw = str(os.environ.get(name, "") or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_public_api_guardrail_config() -> PublicApiGuardrailConfig:
    """Read guardrail config at request time so tests and processes can update env safely."""
    return PublicApiGuardrailConfig(
        rate_limit_per_minute=_read_int_env("PUBLIC_API_RATE_LIMIT_PER_MINUTE", DEFAULT_RATE_LIMIT_PER_MINUTE),
        max_message_chars=_read_int_env("PUBLIC_API_MAX_MESSAGE_CHARS", DEFAULT_MAX_MESSAGE_CHARS),
        max_active_streams_per_ip=_read_int_env(
            "PUBLIC_API_MAX_ACTIVE_STREAMS_PER_IP",
            DEFAULT_MAX_ACTIVE_STREAMS_PER_IP,
        ),
        request_timeout_seconds=_read_int_env(
            "PUBLIC_API_REQUEST_TIMEOUT_SECONDS",
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
        ),
    )


def client_key_from_request(request: Any) -> str:
    """Return the conservative per-process client key used for trial guardrails."""
    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    value = str(host or "").strip()
    return value or "unknown"


class InMemoryMinuteRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._windows: dict[str, tuple[int, int]] = {}

    def check(self, client_key: str, *, now: float | None = None) -> None:
        limit = get_public_api_guardrail_config().rate_limit_per_minute
        if limit <= 0:
            return

        current_window = int((time.time() if now is None else now) // 60)
        with self._lock:
            stale_keys = [key for key, (window, _) in self._windows.items() if window != current_window]
            for key in stale_keys:
                self._windows.pop(key, None)

            window, count = self._windows.get(client_key, (current_window, 0))
            if window != current_window:
                window, count = current_window, 0
            count += 1
            self._windows[client_key] = (window, count)

            if count > limit:
                raise PublicApiGuardrailViolation(
                    status_code=429,
                    code="public_rate_limit_exceeded",
                    message="Too many public API requests. Please retry later.",
                )

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()


class ActiveStreamLimiter:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counts: dict[str, int] = {}

    def acquire(self, client_key: str) -> None:
        limit = get_public_api_guardrail_config().max_active_streams_per_ip
        if limit <= 0:
            return

        with self._lock:
            count = self._counts.get(client_key, 0)
            if count >= limit:
                raise PublicApiGuardrailViolation(
                    status_code=429,
                    code="public_stream_limit_exceeded",
                    message="Too many active streaming requests. Please wait for one to finish.",
                )
            self._counts[client_key] = count + 1

    def release(self, client_key: str) -> None:
        with self._lock:
            count = self._counts.get(client_key, 0)
            if count <= 1:
                self._counts.pop(client_key, None)
                return
            self._counts[client_key] = count - 1

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


rate_limiter = InMemoryMinuteRateLimiter()
active_stream_limiter = ActiveStreamLimiter()


def check_rate_limit(client_key: str) -> None:
    rate_limiter.check(client_key)


def validate_message_length(text: str) -> None:
    max_chars = get_public_api_guardrail_config().max_message_chars
    if max_chars <= 0:
        return
    if len(text) > max_chars:
        raise PublicApiGuardrailViolation(
            status_code=413,
            code="message_too_long",
            message="Input is too long. Please shorten it and retry.",
        )


def acquire_stream_slot(client_key: str) -> None:
    active_stream_limiter.acquire(client_key)


def release_stream_slot(client_key: str) -> None:
    active_stream_limiter.release(client_key)


def reset_public_guardrail_state() -> None:
    rate_limiter.reset()
    active_stream_limiter.reset()
