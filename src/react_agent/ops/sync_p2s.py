# ruff: noqa: D101, D103
"""P2S writer transaction engine for approved sync plans."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from react_agent.ops.sync_approval import load_approval, validate_approval
from react_agent.ops.sync_artifacts import ArtifactRunStore
from react_agent.ops.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    read_json,
    stable_id,
    write_json,
)
from react_agent.ops.sync_environment import build_environment_snapshot
from react_agent.ops.sync_lock import SyncLockManager
from react_agent.ops.sync_materialize import (
    compile_stage_with_profile,
    compute_stage_digest,
    materialize_stage,
    secret_scan_stage,
)
from react_agent.ops.sync_plan import load_plan, validate_plan


def _all_actions(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        action
        for agent in plan.get("agents") or []
        if isinstance(agent, Mapping)
        for action in agent.get("actions") or []
        if isinstance(action, Mapping)
    ]


def _transaction_ids(plan: Mapping[str, Any]) -> list[str]:
    return [str(agent.get("transaction_id") or "") for agent in plan.get("agents") or [] if isinstance(agent, Mapping)]


def _agent_ids(plan: Mapping[str, Any]) -> list[str]:
    return [str(agent.get("agent_id") or "") for agent in plan.get("agents") or [] if isinstance(agent, Mapping)]


def _target_roots(plan: Mapping[str, Any]) -> list[str]:
    return [str(agent.get("target_root") or "") for agent in plan.get("agents") or [] if isinstance(agent, Mapping)]


def _plan_validation_or_raise(plan: Mapping[str, Any], *, allow_existing_stage: bool = False) -> None:
    validation = validate_plan(plan, check_target_freshness=False, allow_existing_stage=allow_existing_stage)
    if not validation["valid"]:
        raise SyncPlannerError("plan_validation_failed", exit_code=int(validation["exit_code"]), details={"blockers": validation["blockers"]})


def _load_plan_approval(plan_path: Path, approval_path: Path, *, allow_existing_stage: bool = False) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    plan = load_plan(plan_path)
    _plan_validation_or_raise(plan, allow_existing_stage=allow_existing_stage)
    approval = load_approval(approval_path)
    environment = build_environment_snapshot(plan)
    return plan, approval, environment


def _validate_approval_or_raise(
    approval: Mapping[str, Any],
    plan: Mapping[str, Any],
    environment: Mapping[str, Any],
    *,
    require_stage: bool = False,
    require_activate: bool = False,
    require_rollback: bool = False,
) -> dict[str, Any]:
    result = validate_approval(
        approval,
        plan,
        environment_snapshot=environment,
        require_stage=require_stage,
        require_activate=require_activate,
        require_rollback=require_rollback,
    )
    if not result["valid"]:
        raise SyncPlannerError("approval_invalid", exit_code=int(result["exit_code"]), details={"blockers": result["blockers"]})
    return result


def _run_id(plan: Mapping[str, Any], suffix: str = "") -> str:
    base = stable_id("run", str(plan.get("plan_id") or ""), str(plan.get("canonical_sha256") or ""))
    return f"{base}{suffix}"


def _stage_root(plan: Mapping[str, Any]) -> Path:
    return Path(str((plan.get("stage_materialization") or {}).get("stage_root") or ""))


def _candidate_path(plan: Mapping[str, Any]) -> Path:
    activation = plan.get("activation") or {}
    active = Path(str((activation.get("pointer_candidate") or {}).get("active_path") or ""))
    baseline_id = str((plan.get("stage_materialization") or {}).get("baseline_id") or "candidate")
    return active.parent / f".prod-candidate-{baseline_id}"


def _archive_path(plan: Mapping[str, Any]) -> Path:
    return Path(str((plan.get("activation") or {}).get("old_active_sandbox_archive_path") or ""))


def _active_path(plan: Mapping[str, Any]) -> Path:
    activation = plan.get("activation") or {}
    return Path(str((activation.get("pointer_candidate") or {}).get("active_path") or ""))


def _pointer_path(plan: Mapping[str, Any]) -> Path:
    activation = plan.get("activation") or {}
    return Path(str((activation.get("pointer_candidate") or {}).get("path") or ""))


def _validation_profile(plan: Mapping[str, Any]) -> dict[str, str]:
    profile = plan.get("validation_profile") or {}
    if isinstance(profile, Mapping):
        return {str(key): str(value) for key, value in profile.items()}
    return {}


def _hardlink_count(left: Path, right: Path) -> int:
    count = 0
    left_files = [path for path in left.rglob("*") if path.is_file()]
    for source in left_files:
        rel = source.relative_to(left)
        target = right / rel
        if not target.exists() or not target.is_file():
            continue
        try:
            if source.stat().st_ino == target.stat().st_ino and source.stat().st_dev == target.stat().st_dev:
                count += 1
        except OSError:
            continue
    return count


def _copy_tree_no_hardlinks(source: Path, destination: Path) -> dict[str, Any]:
    if destination.exists():
        raise SyncPlannerError("activation_candidate_exists", exit_code=5)
    shutil.copytree(source, destination, symlinks=True, copy_function=shutil.copy2)
    hardlinks = _hardlink_count(source, destination)
    return {"candidate_path": str(destination), "hardlink_count": hardlinks, "copy_strategy": "copy2_no_hardlink"}


def _write_pointer(plan: Mapping[str, Any], path: Path) -> None:
    candidate = (plan.get("activation") or {}).get("pointer_candidate") or {}
    payload = {
        "schema": "fixed_dag_prod_sandbox_baseline_pointer_v1",
        "active_baseline_id": str(candidate.get("active_baseline_id") or ""),
        "active_path": str(candidate.get("active_path") or ""),
        "versioned_baseline_path": str(candidate.get("versioned_baseline_path") or ""),
        "manifest_hashes": {
            "plan_sha256": str(plan.get("canonical_sha256") or ""),
            "stage_projection_digest": str((plan.get("stage_materialization") or {}).get("expected_stage_projection_digest") or ""),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    write_json(tmp, payload)
    os.replace(tmp, path)


def _stage_digest(plan: Mapping[str, Any], root: Path) -> str:
    return compute_stage_digest(root, _all_actions(plan))


def p2s_stage(plan_path: Path, approval_path: Path, artifact_root: Path, *, execute: bool) -> dict[str, Any]:
    if not execute:
        raise SyncPlannerError("execute_required", exit_code=2)
    plan, approval, environment = _load_plan_approval(plan_path, approval_path)
    _validate_approval_or_raise(approval, plan, environment, require_stage=True)
    run_id = _run_id(plan)
    store = ArtifactRunStore(artifact_root, run_id)
    store.initialize()
    locks = SyncLockManager(artifact_root)
    acquired: list[str] = []
    try:
        locks.acquire(
            "global-cycle",
            run_id=run_id,
            plan_id=str(plan["plan_id"]),
            plan_sha256=str(plan["canonical_sha256"]),
            direction="p2s",
            agent_scopes=_agent_ids(plan),
            target_roots=_target_roots(plan),
        )
        acquired.append("global-cycle")
        for txn_id in _transaction_ids(plan):
            locks.acquire(
                f"txn-{txn_id}",
                run_id=run_id,
                plan_id=str(plan["plan_id"]),
                plan_sha256=str(plan["canonical_sha256"]),
                direction="p2s",
                agent_scopes=_agent_ids(plan),
                target_roots=_target_roots(plan),
            )
            acquired.append(f"txn-{txn_id}")
        store.append_event("locks_acquired", {"count": len(acquired)})
        store.write_json("input/plan.json", plan)
        store.write_json("approval/approval.json", approval)
        store.write_json("environment/environment_snapshot.json", environment)
        store.append_event("stage_started", {"stage_root": str(_stage_root(plan))})
        result = materialize_stage(plan, _stage_root(plan), validation_profile=_validation_profile(plan))
        if not result["structural_pass"] or not result["py_compile"]["pass"]:
            store.write_json("validation/stage_result.json", result)
            raise SyncPlannerError("stage_validation_failed", exit_code=7, details={"stage_result": result})
        store.append_event("stage_validated", {"stage_root": str(_stage_root(plan)), "digest": result["actual_stage_digest"]})
        store.write_json("validation/stage_result.json", result)
        store.finalize()
        return {"run_id": run_id, "stage": result, "environment_snapshot_sha256": environment["environment_snapshot_sha256"], "status": "staged"}
    finally:
        for lock_id in reversed(acquired):
            try:
                locks.release(lock_id, run_id=run_id)
            except SyncPlannerError:
                pass


def p2s_verify(plan_path: Path, approval_path: Path, artifact_root: Path, *, execute: bool) -> dict[str, Any]:
    if not execute:
        raise SyncPlannerError("execute_required", exit_code=2)
    plan, approval, environment = _load_plan_approval(plan_path, approval_path, allow_existing_stage=True)
    _validate_approval_or_raise(approval, plan, environment, require_stage=True)
    stage_root = _stage_root(plan)
    if not stage_root.exists():
        raise SyncPlannerError("stage_root_missing", exit_code=7)
    actual = _stage_digest(plan, stage_root)
    expected = str((plan.get("stage_materialization") or {}).get("expected_stage_projection_digest") or "")
    secret = secret_scan_stage(stage_root)
    compiled = compile_stage_with_profile(stage_root, _validation_profile(plan))
    valid = actual == expected and bool(secret["pass"]) and bool(compiled["pass"])
    result = {
        "run_id": _run_id(plan),
        "stage_root": str(stage_root),
        "expected_stage_digest": expected,
        "actual_stage_digest": actual,
        "digest_match": actual == expected,
        "secret_scan": secret,
        "py_compile": compiled,
        "activation_eligible": valid,
        "valid": valid,
    }
    store = ArtifactRunStore(artifact_root, _run_id(plan))
    store.initialize()
    store.write_json("validation/verify_result.json", result)
    store.finalize()
    return result


def p2s_activate(plan_path: Path, approval_path: Path, artifact_root: Path, *, execute: bool) -> dict[str, Any]:
    if not execute:
        raise SyncPlannerError("execute_required", exit_code=2)
    plan, approval, environment = _load_plan_approval(plan_path, approval_path, allow_existing_stage=True)
    _validate_approval_or_raise(approval, plan, environment, require_activate=True)
    stage_root = _stage_root(plan)
    active = _active_path(plan)
    archive = _archive_path(plan)
    candidate = _candidate_path(plan)
    pointer = _pointer_path(plan)
    if not stage_root.exists():
        raise SyncPlannerError("stage_root_missing", exit_code=7)
    if not active.exists():
        raise SyncPlannerError("active_sandbox_missing", exit_code=7)
    store = ArtifactRunStore(artifact_root, _run_id(plan))
    store.initialize()
    copy_result = _copy_tree_no_hardlinks(stage_root, candidate)
    if copy_result["hardlink_count"] != 0:
        raise SyncPlannerError("activation_candidate_has_hardlinks", exit_code=7)
    store.append_event("candidate_built", copy_result)
    candidate_digest = _stage_digest(plan, candidate)
    expected = str((plan.get("stage_materialization") or {}).get("expected_stage_projection_digest") or "")
    if candidate_digest != expected:
        raise SyncPlannerError("candidate_digest_mismatch", exit_code=7)
    os.replace(active, archive)
    store.append_event("active_archived", {"archive": str(archive)})
    os.replace(candidate, active)
    store.append_event("candidate_activated", {"active": str(active)})
    _write_pointer(plan, pointer)
    store.append_event("pointer_updated", {"pointer": str(pointer)})
    post_digest = _stage_digest(plan, active)
    result = {
        "run_id": _run_id(plan),
        "active_path": str(active),
        "archive_path": str(archive),
        "candidate_path": str(candidate),
        "versioned_stage_preserved": stage_root.exists(),
        "hardlink_count": copy_result["hardlink_count"],
        "post_switch_digest": post_digest,
        "post_switch_validated": post_digest == expected,
        "status": "activated",
    }
    store.write_json("activation/activation_result.json", result)
    store.finalize()
    return result


def p2s_rollback(plan_path: Path, approval_path: Path, artifact_root: Path, *, execute: bool) -> dict[str, Any]:
    if not execute:
        raise SyncPlannerError("execute_required", exit_code=2)
    plan, approval, environment = _load_plan_approval(plan_path, approval_path, allow_existing_stage=True)
    _validate_approval_or_raise(approval, plan, environment, require_rollback=True)
    active = _active_path(plan)
    archive = _archive_path(plan)
    failed = active.parent / f"{active.name}-failed-{str(plan.get('plan_id') or 'p2s')}"
    pointer = _pointer_path(plan)
    if not archive.exists():
        raise SyncPlannerError("rollback_archive_missing", exit_code=10)
    if active.exists() and not failed.exists():
        os.replace(active, failed)
    if not active.exists():
        os.replace(archive, active)
    _write_pointer(plan, pointer)
    result = {
        "run_id": _run_id(plan),
        "active_path": str(active),
        "archive_restored": active.exists(),
        "failed_baseline_retained": failed.exists(),
        "pointer_restored": pointer.exists(),
        "status": "rolled_back",
    }
    store = ArtifactRunStore(artifact_root, _run_id(plan))
    store.initialize()
    store.append_event("rollback_finished", result)
    store.write_json("rollback/rollback_result.json", result)
    store.finalize()
    return result


def p2s_recover(artifact_root: Path, run_id: str) -> dict[str, Any]:
    store = ArtifactRunStore(artifact_root, run_id)
    events = store.read_events()
    names = [str(event.get("event_type") or "") for event in events]
    if "pointer_updated" in names:
        status = "resume_safe"
    elif "active_archived" in names or "candidate_activated" in names:
        status = "rollback_required"
    elif "stage_validated" in names or "stage_started" in names:
        status = "resume_safe"
    else:
        status = "manual_intervention_required" if events else "resume_safe"
    return {"schema_version": "agent_sync_recovery_v1", "run_id": run_id, "event_count": len(events), "recommended_action": status, "events": names}


def load_environment_snapshot(path: Path) -> dict[str, Any]:
    snapshot = read_json(path)
    if not isinstance(snapshot, dict):
        raise SyncPlannerError("environment_snapshot_not_object", exit_code=2)
    return dict(snapshot)


def plan_with_validation_profile(plan: Mapping[str, Any], profile: Mapping[str, str]) -> dict[str, Any]:
    decoded = json.loads(json.dumps(plan, ensure_ascii=False, allow_nan=False))
    if not isinstance(decoded, dict):
        raise SyncPlannerError("plan_not_object", exit_code=2)
    updated: dict[str, Any] = dict(decoded)
    updated["validation_profile"] = dict(profile)
    updated["canonical_sha256"] = canonical_sha256(updated)
    return updated
