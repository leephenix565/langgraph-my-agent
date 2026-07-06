# ruff: noqa: D101, D102, D103, D107
"""File lock contracts for sync writer phases."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from react_agent.ops_sync.sync_contracts import SyncPlannerError, write_json


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    if not value.endswith("Z"):
        raise SyncPlannerError("invalid_lock_timestamp", exit_code=2)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _fsync_parent(path: Path) -> None:
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class SyncLockManager:
    """Manage global and per-transaction locks under an artifact root."""

    def __init__(self, artifact_root: Path):
        self.artifact_root = artifact_root
        self.lock_root = artifact_root / "locks"

    def _lock_path(self, lock_id: str) -> Path:
        if "/" in lock_id or "\\" in lock_id or lock_id in {"", ".", ".."}:
            raise SyncPlannerError("invalid_lock_id", exit_code=2)
        return self.lock_root / f"{lock_id}.json"

    def acquire(
        self,
        lock_id: str,
        *,
        run_id: str,
        plan_id: str,
        plan_sha256: str,
        direction: str,
        agent_scopes: list[str],
        target_roots: list[str],
        ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        self.lock_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        path = self._lock_path(lock_id)
        acquired_at = _now()
        expires_at = (
            datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        payload = {
            "schema_version": "agent_sync_lock_v1",
            "lock_id": lock_id,
            "run_id": run_id,
            "plan_id": plan_id,
            "plan_sha256": plan_sha256,
            "direction": direction,
            "hostname": os.uname().nodename,
            "process_id": os.getpid(),
            "acquired_at": acquired_at,
            "expires_at": expires_at,
            "heartbeat_at": acquired_at,
            "agent_scopes": agent_scopes,
            "target_roots": target_roots,
            "state": "held",
        }
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise SyncPlannerError("lock_conflict", exit_code=6, details={"lock_id": lock_id}) from exc
        try:
            data = (
                __import__("json").dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
            ).encode("utf-8")
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_parent(path)
        return payload

    def read(self, lock_id: str) -> dict[str, Any]:
        import json

        path = self._lock_path(lock_id)
        if not path.exists():
            raise SyncPlannerError("lock_not_found", exit_code=2, details={"lock_id": lock_id})
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SyncPlannerError("lock_not_object", exit_code=2)
        return data

    def heartbeat(self, lock_id: str, *, run_id: str) -> dict[str, Any]:
        lock = self.read(lock_id)
        if lock.get("run_id") != run_id:
            raise SyncPlannerError("lock_owner_mismatch", exit_code=6)
        lock["heartbeat_at"] = _now()
        write_json(self._lock_path(lock_id), lock)
        _fsync_parent(self._lock_path(lock_id))
        return lock

    def release(self, lock_id: str, *, run_id: str) -> dict[str, Any]:
        lock = self.read(lock_id)
        if lock.get("run_id") != run_id:
            raise SyncPlannerError("lock_owner_mismatch", exit_code=6)
        path = self._lock_path(lock_id)
        lock["state"] = "released"
        lock["released_at"] = _now()
        write_json(path.with_suffix(".released.json"), lock)
        path.unlink()
        _fsync_parent(path)
        return lock

    def inspect(self) -> dict[str, Any]:
        locks: list[dict[str, Any]] = []
        if self.lock_root.exists():
            for path in sorted(self.lock_root.glob("*.json")):
                if path.name.endswith(".released.json"):
                    continue
                try:
                    lock = self.read(path.stem)
                except SyncPlannerError:
                    continue
                lock["stale"] = self.is_stale(lock)
                locks.append(lock)
        return {"schema_version": "agent_sync_lock_inspection_v1", "lock_count": len(locks), "locks": locks}

    def is_stale(self, lock: dict[str, Any]) -> bool:
        try:
            return _parse(str(lock.get("expires_at") or "")) <= datetime.now(UTC)
        except SyncPlannerError:
            return True
