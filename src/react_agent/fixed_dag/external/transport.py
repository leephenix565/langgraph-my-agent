"""Loopback transport for fixed-DAG external compute."""

from __future__ import annotations

import http.client
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from react_agent.fixed_dag.external.constants import MAX_RESPONSE_BYTES
from react_agent.fixed_dag.external.safety import validate_demo_entry
from react_agent.fixed_dag.external.types import ExternalComputeDemoEntry


def _post_json_loopback(
    entry: ExternalComputeDemoEntry,
    payload: Mapping[str, Any],
    timeout_seconds: float,
) -> Mapping[str, Any]:
    valid, reason = validate_demo_entry(entry)
    if not valid:
        raise ValueError(reason)
    parsed = urlsplit(entry.base_url)
    assert parsed.hostname == "127.0.0.1"
    assert parsed.port is not None
    body = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
    connection = http.client.HTTPConnection(
        parsed.hostname,
        parsed.port,
        timeout=timeout_seconds,
    )
    try:
        connection.request(
            "POST",
            entry.compute_path,
            body=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"http_status_{response.status}")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RuntimeError("response_too_large")
    finally:
        connection.close()
    try:
        parsed_body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_json") from exc
    if not isinstance(parsed_body, Mapping):
        raise ValueError("json_not_object")
    return parsed_body


__all__ = []
