# ruff: noqa: D101, D102, D103
"""Bounded process launcher contracts for sync-ops supervised services."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from react_agent.ops.sync_contracts import canonical_sha256, stable_id, write_json


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _realpath_text(path: str | Path) -> str:
    return str(Path(path).resolve())


def _start_ticks(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()[21]
    except OSError:
        return ""


def _proc_link(pid: int, name: str) -> str:
    try:
        return os.readlink(f"/proc/{pid}/{name}")
    except OSError:
        return ""


def _path_under(path: Path, roots: Sequence[str]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in roots:
        try:
            resolved.relative_to(Path(root).resolve())
            return True
        except ValueError:
            continue
    return False


def _port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _wait_for_port_release(port: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _port_listening(port):
            return True
        time.sleep(0.05)
    return not _port_listening(port)


def build_supervised_launcher_authority(
    *,
    service_unit_id: str,
    executable: str,
    argv: Sequence[str],
    cwd: str,
    log_dir: str,
    state_dir: str,
    allowed_port_overrides: Sequence[int],
    environment_reference_path: str = "",
    allowed_environment_override_names: Sequence[str] = ("APP_HOST", "APP_PORT"),
    allowed_executable_roots: Sequence[str] = ("/usr/bin", "/usr/local/bin", "/sdb/dlut"),
    allowed_cwd_roots: Sequence[str] = ("/sdb/dlut/prod", "/tmp"),
) -> dict[str, Any]:
    authority_id = stable_id(
        "launch_authority",
        service_unit_id,
        executable,
        "|".join(argv),
        cwd,
        ",".join(str(port) for port in allowed_port_overrides),
    )
    authority: dict[str, Any] = {
        "schema_version": "agent_sync_launch_authority_v1",
        "authority_id": authority_id,
        "authority_kind": "sync_ops_supervised_launcher",
        "service_unit_id": service_unit_id,
        "executable": executable,
        "argv": list(argv),
        "cwd": cwd,
        "environment_source": {
            "classification": "approved_secure_launcher_env_reference" if environment_reference_path else "defaults_sufficient_for_contract_canary",
            "reference_path": environment_reference_path,
            "values_read": False,
            "proc_environ_read": False,
            "allowed_override_names": list(allowed_environment_override_names),
        },
        "allowed_port_overrides": list(allowed_port_overrides),
        "process_owner": {"uid": os.geteuid(), "gid": os.getegid()},
        "allowed_executable_roots": list(allowed_executable_roots),
        "allowed_cwd_roots": list(allowed_cwd_roots),
        "start_contract": {
            "shell": False,
            "start_new_session": True,
            "stdin": "/dev/null",
            "umask": "0077",
            "startup_timeout_seconds": 45,
            "bounded_environment_overrides_only": True,
        },
        "stop_contract": {
            "signal": "SIGTERM",
            "sigkill_allowed": False,
            "graceful_timeout_seconds": 15,
            "listener_release_timeout_seconds": 15,
            "pid_reuse_protection": True,
        },
        "status_contract": {
            "verify_pid": True,
            "verify_start_ticks": True,
            "verify_cwd": True,
            "verify_exe": True,
        },
        "log_contract": {
            "log_dir": log_dir,
            "stdout_mode": "0600",
            "stderr_mode": "0600",
            "portable_artifact_includes_log_bytes": False,
            "max_log_bytes": 1048576,
        },
        "state_contract": {
            "state_dir": state_dir,
            "state_mode": "0600",
            "record_pid": True,
            "record_start_ticks": True,
            "record_cwd": True,
            "record_exe": True,
        },
        "recovery_contract": {
            "bounded_retry": True,
            "manual_intervention_on_sigterm_timeout": True,
            "no_arbitrary_command": True,
            "no_shell": True,
        },
        "canonical_sha256": "",
    }
    authority["canonical_sha256"] = canonical_sha256(authority)
    return authority


def validate_launch_authority(authority: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    kind = str(authority.get("authority_kind") or "")
    executable = str(authority.get("executable") or "")
    argv = [str(item) for item in authority.get("argv") or []]
    cwd = str(authority.get("cwd") or "")
    if kind == "manual_exact_argv":
        blockers.append("manual_exact_argv_is_not_launch_authority")
    if kind != "sync_ops_supervised_launcher":
        blockers.append("unsupported_launch_authority_kind")
    if not executable or not Path(executable).is_absolute():
        blockers.append("executable_must_be_absolute")
    if not argv or argv[0] != executable:
        blockers.append("argv_must_start_with_exact_executable")
    if any(item in {";", "&&", "|", "`"} for item in argv):
        blockers.append("shell_token_in_argv")
    if not cwd or not Path(cwd).is_absolute():
        blockers.append("cwd_must_be_absolute")
    if not _path_under(Path(executable), [str(item) for item in authority.get("allowed_executable_roots") or []]):
        blockers.append("executable_outside_allowed_roots")
    if not _path_under(Path(cwd), [str(item) for item in authority.get("allowed_cwd_roots") or []]):
        blockers.append("cwd_outside_allowed_roots")
    start = _as_mapping(authority.get("start_contract"))
    stop = _as_mapping(authority.get("stop_contract"))
    env = _as_mapping(authority.get("environment_source"))
    if start.get("shell") is not False:
        blockers.append("shell_must_be_false")
    if not start.get("start_new_session"):
        blockers.append("start_new_session_required")
    if stop.get("sigkill_allowed") is not False:
        blockers.append("sigkill_must_not_be_allowed")
    if env.get("values_read") or env.get("proc_environ_read"):
        blockers.append("environment_values_must_not_be_read")
    for nested in ("log_contract", "state_contract"):
        for value in _as_mapping(authority.get(nested)).values():
            if isinstance(value, str) and ("<" in value or ">" in value):
                blockers.append(f"{nested}_contains_placeholder")
    if str(authority.get("canonical_sha256") or "") != canonical_sha256(authority):
        blockers.append("canonical_hash_mismatch")
    return {
        "schema_version": "agent_sync_launch_authority_v1_validation",
        "authority_id": authority.get("authority_id", ""),
        "authority_sha256": authority.get("canonical_sha256", ""),
        "authority_kind": kind,
        "valid": not blockers,
        "blockers": blockers,
    }


def preflight_launch_authority(authority: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_launch_authority(authority)
    blockers = list(validation["blockers"])
    executable = Path(str(authority.get("executable") or ""))
    cwd = Path(str(authority.get("cwd") or ""))
    if not executable.exists():
        blockers.append("executable_missing")
    if not cwd.exists() or not cwd.is_dir():
        blockers.append("cwd_missing")
    env = _as_mapping(authority.get("environment_source"))
    reference = str(env.get("reference_path") or "")
    reference_metadata: dict[str, Any] = {"exists": False, "type": "", "mode": "", "realpath": ""}
    if reference:
        ref = Path(reference)
        reference_metadata = {
            "exists": ref.exists(),
            "type": "regular_file" if ref.is_file() and not ref.is_symlink() else "other",
            "mode": oct(ref.stat().st_mode & 0o777) if ref.exists() else "",
            "realpath": _realpath_text(ref) if ref.exists() else "",
        }
        if not ref.exists() or not ref.is_file() or ref.is_symlink():
            blockers.append("environment_reference_invalid")
    return {
        "schema_version": "agent_sync_launch_authority_preflight_v1",
        "authority_id": authority.get("authority_id", ""),
        "valid": not blockers,
        "blockers": blockers,
        "environment_reference_metadata": reference_metadata,
        "env_values_read": False,
        "proc_environ_read": False,
    }


def _state_record_path(authority: Mapping[str, Any], state_path: Path | None) -> Path:
    if state_path is not None:
        return state_path
    state_dir = Path(str(_as_mapping(authority.get("state_contract")).get("state_dir") or ""))
    return state_dir / f"{authority.get('authority_id')}.state.json"


def start_supervised_process(
    authority: Mapping[str, Any],
    *,
    state_path: Path | None = None,
    environment_overrides: Mapping[str, str] | None = None,
    execute: bool = False,
) -> dict[str, Any]:
    if not execute:
        return {"schema_version": "agent_sync_process_start_result_v1", "started": False, "reason": "execute_required"}
    preflight = preflight_launch_authority(authority)
    if not preflight["valid"]:
        return {"schema_version": "agent_sync_process_start_result_v1", "started": False, "blockers": preflight["blockers"]}
    allowed_names = set(str(item) for item in _as_mapping(authority.get("environment_source")).get("allowed_override_names") or [])
    overrides = dict(environment_overrides or {})
    if set(overrides) - allowed_names:
        return {
            "schema_version": "agent_sync_process_start_result_v1",
            "started": False,
            "blockers": ["unapproved_environment_override"],
        }
    allowed_ports = {int(port) for port in authority.get("allowed_port_overrides") or []}
    if "APP_PORT" in overrides:
        try:
            requested_port = int(overrides["APP_PORT"])
        except ValueError:
            return {
                "schema_version": "agent_sync_process_start_result_v1",
                "started": False,
                "blockers": ["invalid_port_override"],
            }
        if requested_port not in allowed_ports:
            return {
                "schema_version": "agent_sync_process_start_result_v1",
                "started": False,
                "blockers": ["unapproved_port_override"],
            }
    log_dir = Path(str(_as_mapping(authority.get("log_contract")).get("log_dir") or ""))
    log_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(log_dir, 0o700)
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    stdout_fd = os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    stderr_fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    old_umask = os.umask(0o077)
    try:
        with os.fdopen(stdout_fd, "ab", closefd=True) as stdout_handle, os.fdopen(stderr_fd, "ab", closefd=True) as stderr_handle:
            process = subprocess.Popen(
                [str(item) for item in authority.get("argv") or []],
                cwd=str(authority.get("cwd") or ""),
                env={**overrides},
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                start_new_session=True,
                shell=False,
            )
    finally:
        os.umask(old_umask)
    time.sleep(0.05)
    state = {
        "schema_version": "agent_sync_process_state_v1",
        "authority_id": authority.get("authority_id"),
        "authority_sha256": authority.get("canonical_sha256"),
        "pid": process.pid,
        "start_ticks": _start_ticks(process.pid),
        "cwd": _proc_link(process.pid, "cwd"),
        "exe": _proc_link(process.pid, "exe"),
        "argv": [str(item) for item in authority.get("argv") or []],
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "env_values_persisted": False,
    }
    output = _state_record_path(authority, state_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, state)
    output.chmod(0o600)
    return {
        "schema_version": "agent_sync_process_start_result_v1",
        "started": process.poll() is None,
        "pid": process.pid,
        "state_path": str(output),
        "start_ticks": state["start_ticks"],
        "stdout_log_mode": "0600",
        "stderr_log_mode": "0600",
    }


def read_process_state(path: Path) -> dict[str, Any]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return dict(payload)


def status_supervised_process(authority: Mapping[str, Any], *, state_path: Path) -> dict[str, Any]:
    state = read_process_state(state_path)
    validation = validate_launch_authority(authority)
    pid = int(state.get("pid") or 0)
    running = Path(f"/proc/{pid}").exists()
    identity_match = (
        running
        and _start_ticks(pid) == str(state.get("start_ticks") or "")
        and _proc_link(pid, "cwd") == str(state.get("cwd") or "")
        and _proc_link(pid, "exe") == str(state.get("exe") or "")
    )
    try:
        state_cwd = _realpath_text(str(state.get("cwd") or ""))
        authority_cwd = _realpath_text(str(authority.get("cwd") or ""))
    except OSError:
        state_cwd = str(state.get("cwd") or "")
        authority_cwd = str(authority.get("cwd") or "")
    try:
        state_exe = _realpath_text(str(state.get("exe") or ""))
        authority_exe = _realpath_text(str(authority.get("executable") or ""))
    except OSError:
        state_exe = str(state.get("exe") or "")
        authority_exe = str(authority.get("executable") or "")
    authority_binding_match = (
        validation["valid"]
        and state.get("authority_id") == authority.get("authority_id")
        and state.get("authority_sha256") == authority.get("canonical_sha256")
        and [str(item) for item in state.get("argv") or []] == [str(item) for item in authority.get("argv") or []]
        and state_cwd == authority_cwd
        and state_exe == authority_exe
    )
    return {
        "schema_version": "agent_sync_process_status_result_v1",
        "authority_id": authority.get("authority_id", ""),
        "pid": pid,
        "running": running,
        "identity_match": identity_match,
        "authority_binding_match": authority_binding_match,
        "pid_reuse_detected": running and not identity_match,
        "blockers": [] if authority_binding_match else ["authority_state_binding_mismatch"],
    }


def stop_supervised_process(
    authority: Mapping[str, Any],
    *,
    state_path: Path,
    execute: bool = False,
    port: int | None = None,
) -> dict[str, Any]:
    if not execute:
        return {"schema_version": "agent_sync_process_stop_result_v1", "stopped": False, "reason": "execute_required"}
    status = status_supervised_process(authority, state_path=state_path)
    if not status["identity_match"] or not status.get("authority_binding_match"):
        return {
            "schema_version": "agent_sync_process_stop_result_v1",
            "stopped": False,
            "manual_intervention_required": True,
            "reason": "process_identity_or_authority_binding_mismatch",
            "status": status,
        }
    pid = int(status["pid"])
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + float(_as_mapping(authority.get("stop_contract")).get("graceful_timeout_seconds") or 15)
    while time.monotonic() < deadline:
        try:
            waited_pid, _status = os.waitpid(pid, os.WNOHANG)
            if waited_pid == pid:
                release_timeout = float(_as_mapping(authority.get("stop_contract")).get("listener_release_timeout_seconds") or 15)
                port_released = True if port is None else _wait_for_port_release(port, release_timeout)
                return {
                    "schema_version": "agent_sync_process_stop_result_v1",
                    "stopped": port_released,
                    "sigkill_used": False,
                    "pid": pid,
                    "port": port,
                    "port_released": port_released,
                    "manual_intervention_required": not port_released,
                    "reason": "" if port_released else "listener_release_timeout",
                }
        except ChildProcessError:
            pass
        if not Path(f"/proc/{pid}").exists():
            release_timeout = float(_as_mapping(authority.get("stop_contract")).get("listener_release_timeout_seconds") or 15)
            port_released = True if port is None else _wait_for_port_release(port, release_timeout)
            return {
                "schema_version": "agent_sync_process_stop_result_v1",
                "stopped": port_released,
                "sigkill_used": False,
                "pid": pid,
                "port": port,
                "port_released": port_released,
                "manual_intervention_required": not port_released,
                "reason": "" if port_released else "listener_release_timeout",
            }
        time.sleep(0.05)
    return {
        "schema_version": "agent_sync_process_stop_result_v1",
        "stopped": False,
        "sigkill_used": False,
        "manual_intervention_required": True,
        "reason": "sigterm_timeout",
        "pid": pid,
    }
