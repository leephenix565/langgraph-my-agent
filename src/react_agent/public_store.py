"""File-backed store for public API thread state."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import List, Optional

from react_agent.public_contracts import PublicThreadDetail, StoreEnvelope

DEFAULT_STORE_PATH = Path("var/public_api/threads.json")


def default_store_path() -> Path:
    return DEFAULT_STORE_PATH


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
            return StoreEnvelope.model_validate(raw)

    def _write_envelope(self, envelope: StoreEnvelope) -> None:
        payload = json.dumps(envelope.model_dump(mode="json"), ensure_ascii=False, indent=2)
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp_path.write_text(payload, encoding="utf-8")
        temp_path.replace(self.path)

    def list_threads(self) -> List[PublicThreadDetail]:
        envelope = self._read_envelope()
        return list(envelope.threads.values())

    def get_thread(self, thread_id: str) -> Optional[PublicThreadDetail]:
        envelope = self._read_envelope()
        return envelope.threads.get(thread_id)

    def upsert_thread(self, detail: PublicThreadDetail) -> PublicThreadDetail:
        with self._lock:
            envelope = self._read_envelope()
            envelope.threads[detail.thread.id] = detail
            self._write_envelope(envelope)
        return detail
