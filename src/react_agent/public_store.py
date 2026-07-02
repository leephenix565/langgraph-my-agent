# ruff: noqa: D102, D103, D107
"""File-backed store for public API thread state."""

from __future__ import annotations

import json
import threading
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, List

from pydantic import ValidationError

from react_agent.public_contracts import PublicThreadDetail, StoreEnvelope

DEFAULT_STORE_PATH = Path("var/public_api/threads.json")


def default_store_path() -> Path:
    return DEFAULT_STORE_PATH


def _now_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class PublicStoreError(RuntimeError):
    """Raised when the public store cannot be read or written safely."""


class PublicThreadStore:
    """Small JSON file store for public thread summaries and turns."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or default_store_path())
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_envelope(StoreEnvelope())

    def _read_envelope(self) -> StoreEnvelope:
        with self._lock:
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                envelope = StoreEnvelope()
                self._write_envelope(envelope)
                return envelope
            except json.JSONDecodeError as exc:
                raise PublicStoreError(f"Invalid public store JSON at {self.path}: {exc}") from exc
            return self._validate_or_repair_envelope(raw)

    def _validate_or_repair_envelope(self, raw: Any) -> StoreEnvelope:
        try:
            return StoreEnvelope.model_validate(raw)
        except ValidationError as exc:
            envelope = self._repair_legacy_envelope(raw)
            if envelope is None:
                raise PublicStoreError(
                    f"Invalid public store envelope at {self.path}: {exc}"
                ) from exc
            self._write_envelope(envelope)
            return envelope

    def _repair_legacy_envelope(self, raw: Any) -> StoreEnvelope | None:
        if not isinstance(raw, Mapping):
            return None
        raw_threads = raw.get("threads", {})
        thread_items: list[tuple[str, Any]]
        if isinstance(raw_threads, Mapping):
            thread_items = [(str(key), value) for key, value in raw_threads.items()]
        elif isinstance(raw_threads, list):
            thread_items = [(str(index), value) for index, value in enumerate(raw_threads)]
        else:
            return None

        repaired: dict[str, PublicThreadDetail] = {}
        for _raw_key, item in thread_items:
            try:
                detail = PublicThreadDetail.model_validate(item)
            except ValidationError:
                continue
            repaired[detail.thread.id] = detail
        return StoreEnvelope(version=1, threads=repaired)

    def _write_envelope(self, envelope: StoreEnvelope) -> None:
        payload = json.dumps(envelope.model_dump(mode="json"), ensure_ascii=False, indent=2)
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp_path.write_text(payload, encoding="utf-8")
        temp_path.replace(self.path)

    def list_threads(self) -> List[PublicThreadDetail]:
        envelope = self._read_envelope()
        return list(envelope.threads.values())

    def get_thread(self, thread_id: str) -> PublicThreadDetail | None:
        envelope = self._read_envelope()
        return envelope.threads.get(thread_id)

    def upsert_thread(self, detail: PublicThreadDetail) -> PublicThreadDetail:
        with self._lock:
            envelope = self._read_envelope()
            envelope.threads[detail.thread.id] = detail
            self._write_envelope(envelope)
        return detail

    def delete_thread(self, thread_id: str) -> bool:
        with self._lock:
            envelope = self._read_envelope()
            if thread_id not in envelope.threads:
                return False
            del envelope.threads[thread_id]
            self._write_envelope(envelope)
        return True

    def clear_thread_messages(self, thread_id: str) -> PublicThreadDetail | None:
        with self._lock:
            envelope = self._read_envelope()
            detail = envelope.threads.get(thread_id)
            if detail is None:
                return None
            cleared_thread = detail.thread.model_copy(
                update={
                    "updatedAt": _now_label(),
                    "preview": "等待第一条消息。",
                    "finalSource": "reset_skeleton",
                }
            )
            cleared_detail = detail.model_copy(update={"thread": cleared_thread, "turns": []})
            envelope.threads[thread_id] = cleared_detail
            self._write_envelope(envelope)
        return cleared_detail
