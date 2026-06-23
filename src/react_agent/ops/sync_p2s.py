# ruff: noqa: D101, D103
"""P2S writer transaction engine for approved sync plans."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from react_agent.ops.sync_approval import load_approval, validate_approval
from react_agent.ops.sync_artifacts import ArtifactRunStore, artifact_store_preflight
from react_agent.ops.sync_bootstrap import (
    bootstrap_artifact_store,
    build_bootstrap_environment_snapshot,
    build_bootstrap_plan,
    build_temp_bootstrap_approval,
    verify_artifact_store,
)
from react_agent.ops.sync_contracts import (
    SyncPlannerError,
    canonical_sha256,
    file_sha256,
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
from react_agent.ops.sync_plan import (
    artifact_store_initialization_contract,
    load_plan,
    validate_plan,
)
from react_agent.ops.sync_summary import p2s_summary_from_plan


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


def _expected_artifact_root(plan: Mapping[str, Any]) -> Path:
    contract = plan.get("execution_contract") or {}
    artifact_store = contract.get("artifact_store") if isinstance(contract, Mapping) else {}
    return Path(str((artifact_store or {}).get("root") or ""))


def _require_bootstrapped_artifact_store(plan: Mapping[str, Any], artifact_root: Path) -> None:
    if str(plan.get("execution_status") or "") == "blocked_artifact_store_not_ready":
        raise SyncPlannerError("artifact_store_not_bootstrapped", exit_code=3)
    expected = _expected_artifact_root(plan)
    if expected and artifact_root.resolve(strict=False) != expected.resolve(strict=False):
        raise SyncPlannerError(
            "artifact_store_root_mismatch",
            exit_code=3,
            details={"expected_root": str(expected), "provided_root": str(artifact_root)},
        )
    verify = verify_artifact_store(artifact_root)
    if not verify["bootstrapped"]:
        raise SyncPlannerError("artifact_store_not_bootstrapped", exit_code=3, details={"blockers": verify["blockers"]})


def _validate_approval_or_raise(
    approval: Mapping[str, Any],
    plan: Mapping[str, Any],
    environment: Mapping[str, Any],
    *,
    require_stage: bool = False,
    require_verify: bool = False,
    require_artifact_store_initialize: bool = False,
    require_activate: bool = False,
    require_rollback: bool = False,
) -> dict[str, Any]:
    result = validate_approval(
        approval,
        plan,
        environment_snapshot=environment,
        require_stage=require_stage,
        require_verify=require_verify,
        require_artifact_store_initialize=require_artifact_store_initialize,
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


def _write_rollback_pointer(plan: Mapping[str, Any], path: Path) -> None:
    baseline = plan.get("baseline") or {}
    activation = plan.get("activation") or {}
    preconditions = activation.get("preconditions") if isinstance(activation, Mapping) else {}
    old_active = str((preconditions or {}).get("old_active_path") or baseline.get("active_path") or "")
    payload = {
        "schema": "fixed_dag_prod_sandbox_baseline_pointer_v1",
        "active_baseline_id": str(baseline.get("active_baseline_id") or ""),
        "active_path": old_active,
        "versioned_baseline_path": str(baseline.get("versioned_baseline_path") or ""),
        "manifest_hashes": baseline.get("manifest_hashes") or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    write_json(tmp, payload)
    os.replace(tmp, path)


def _stage_digest(plan: Mapping[str, Any], root: Path) -> str:
    return compute_stage_digest(root, _all_actions(plan))


def _load_verified_stage_result(store: ArtifactRunStore, plan: Mapping[str, Any]) -> dict[str, Any]:
    verify_path = store.resolve("validation/verify_result.json")
    if not verify_path.exists():
        raise SyncPlannerError("stage_verify_result_missing", exit_code=7)
    result = read_json(verify_path)
    if not isinstance(result, dict) or result.get("valid") is not True:
        raise SyncPlannerError("stage_verify_result_not_valid", exit_code=7)
    expected = str((plan.get("stage_materialization") or {}).get("expected_stage_projection_digest") or "")
    if str(result.get("actual_stage_digest") or "") != expected:
        raise SyncPlannerError("stage_verify_digest_mismatch", exit_code=7)
    return result


def p2s_stage(plan_path: Path, approval_path: Path, artifact_root: Path, *, execute: bool) -> dict[str, Any]:
    if not execute:
        raise SyncPlannerError("execute_required", exit_code=2)
    plan, approval, environment = _load_plan_approval(plan_path, approval_path)
    _require_bootstrapped_artifact_store(plan, artifact_root)
    _validate_approval_or_raise(
        approval,
        plan,
        environment,
        require_stage=True,
        require_artifact_store_initialize=False,
    )
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
    _require_bootstrapped_artifact_store(plan, artifact_root)
    _validate_approval_or_raise(approval, plan, environment, require_verify=True)
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
    _require_bootstrapped_artifact_store(plan, artifact_root)
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
    _load_verified_stage_result(store, plan)
    copy_result = _copy_tree_no_hardlinks(stage_root, candidate)
    if copy_result["hardlink_count"] != 0:
        raise SyncPlannerError("activation_candidate_has_hardlinks", exit_code=7)
    store.append_event("candidate_built", copy_result)
    candidate_digest = _stage_digest(plan, candidate)
    expected = str((plan.get("stage_materialization") or {}).get("expected_stage_projection_digest") or "")
    if candidate_digest != expected:
        raise SyncPlannerError("candidate_digest_mismatch", exit_code=7)
    archive.parent.mkdir(parents=True, exist_ok=True)
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
    _require_bootstrapped_artifact_store(plan, artifact_root)
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
    _write_rollback_pointer(plan, pointer)
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


def _require_temp_rehearsal_root(root: Path) -> None:
    resolved = root.resolve(strict=False)
    tmp = Path("/tmp").resolve(strict=False)
    if tmp not in [resolved, *resolved.parents]:
        raise SyncPlannerError("p2s_rehearsal_temp_root_not_under_tmp", exit_code=2)
    forbidden = [
        Path("/sdb/dlut/prod").resolve(strict=False),
        Path("/sdb/dlut/sandbox").resolve(strict=False),
        Path("/sdb/dlut/ops-artifacts/agent-sync").resolve(strict=False),
    ]
    if any(path in [resolved, *resolved.parents] for path in forbidden):
        raise SyncPlannerError("p2s_rehearsal_temp_root_forbidden", exit_code=2)


def _future(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _all_action_ids(plan: Mapping[str, Any]) -> list[str]:
    return [
        str(action.get("action_id") or "")
        for agent in plan.get("agents") or []
        if isinstance(agent, Mapping)
        for action in agent.get("actions") or []
        if isinstance(action, Mapping)
    ]


def prepare_temp_rehearsal_plan(plan: Mapping[str, Any], temp_root: Path) -> dict[str, Any]:
    _require_temp_rehearsal_root(temp_root)
    decoded = json.loads(json.dumps(plan, ensure_ascii=False, allow_nan=False))
    if not isinstance(decoded, dict):
        raise SyncPlannerError("plan_not_object", exit_code=2)
    active = temp_root / "active"
    pointer = temp_root / "PROD_BASELINE_POINTER.json"
    baseline_id = str((decoded.get("stage_materialization") or {}).get("baseline_id") or "temp-baseline")
    stage_root = temp_root / "versioned" / baseline_id / "fixed-dag-services"
    archive = temp_root / "archives" / f"active-pre-{baseline_id}"
    old_pointer = {
        "schema": "fixed_dag_prod_sandbox_baseline_pointer_v1",
        "active_baseline_id": str((decoded.get("baseline") or {}).get("active_baseline_id") or "temp-old-baseline"),
        "active_path": str(active),
        "versioned_baseline_path": str(temp_root / "old-versioned" / "fixed-dag-services"),
        "manifest_hashes": {},
    }
    active.mkdir(parents=True, exist_ok=True)
    write_json(pointer, old_pointer)
    decoded["test_only_temp_roots"] = True
    decoded["target_snapshot"]["active_sandbox_path"] = str(active)
    decoded["target_snapshot"]["active_sandbox_pointer_sha256"] = file_sha256(pointer)
    decoded["target_snapshot"]["active_baseline_tree_sha256"] = "temp-active-tree"
    decoded["target_snapshot"]["versioned_baseline_tree_sha256"] = "temp-old-versioned-tree"
    decoded["baseline"]["active_path"] = str(active)
    decoded["baseline"]["versioned_baseline_path"] = str(temp_root / "old-versioned" / "fixed-dag-services")
    decoded["baseline"]["pointer_path"] = str(pointer)
    decoded["baseline"]["pointer_sha256"] = file_sha256(pointer)
    decoded["stage_materialization"]["stage_root"] = str(stage_root)
    decoded["stage_materialization"]["expected_stage_root_state"] = "missing"
    store_preflight = artifact_store_preflight(temp_root / "artifact-store")
    decoded["artifact_store_preflight"] = store_preflight
    decoded["execution_status"] = "stage_ready" if store_preflight.get("ready") else "blocked_artifact_store_not_ready"
    if isinstance(decoded.get("artifact_store_initialization"), dict):
        decoded["artifact_store_initialization"] = artifact_store_initialization_contract(store_preflight)
    if isinstance(decoded.get("execution_contract"), dict):
        contract = decoded["execution_contract"]
        if isinstance(contract.get("artifact_store"), dict):
            contract["artifact_store"]["root"] = str(temp_root / "artifact-store")
            contract["artifact_store"]["preflight"] = decoded["artifact_store_preflight"]
            contract["artifact_store"]["bootstrap_required"] = not bool(store_preflight.get("ready"))
            contract["artifact_store"]["ready"] = bool(store_preflight.get("ready"))
            contract["artifact_store"]["metadata_sha256"] = str(store_preflight.get("metadata_sha256") or "")
            contract["artifact_store"]["initialization_requires_approval"] = False
        if isinstance(contract.get("stage"), dict):
            contract["stage"]["stage_root"] = str(stage_root)
        if isinstance(contract.get("activation"), dict):
            contract["activation"]["active_path"] = str(active)
    decoded["activation"]["old_active_sandbox_archive_path"] = str(archive)
    decoded["activation"]["new_versioned_baseline_path"] = str(stage_root)
    decoded["activation"]["pointer_candidate"]["path"] = str(pointer)
    decoded["activation"]["pointer_candidate"]["active_path"] = str(active)
    decoded["activation"]["pointer_candidate"]["versioned_baseline_path"] = str(stage_root)
    decoded["activation"]["preconditions"]["active_pointer_sha256"] = file_sha256(pointer)
    decoded["activation"]["preconditions"]["active_baseline_tree_sha256"] = "temp-active-tree"
    decoded["activation"]["preconditions"]["old_active_path"] = str(active)
    for agent in decoded.get("agents") or []:
        if isinstance(agent, dict):
            agent["target_root"] = str(stage_root / str(agent.get("agent_id") or ""))
            agent["target_before_tree_sha256"] = "temp-active-tree"
            agent["active_tree_sha256"] = "temp-active-tree"
    decoded["canonical_sha256"] = canonical_sha256(decoded)
    return decoded


def build_temp_rehearsal_approval(
    plan: Mapping[str, Any],
    *,
    approval_id: str = "temp-rehearsal-stage-approval",
    stage: bool = True,
    verify: bool = True,
    activate: bool = False,
    rollback: bool = False,
) -> dict[str, Any]:
    environment = build_environment_snapshot(plan)
    return {
        "schema_version": "agent_sync_approval_v1",
        "approval_id": approval_id,
        "status": "approved",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_sha256": str(plan.get("canonical_sha256") or ""),
        "environment_snapshot_sha256": str(environment.get("environment_snapshot_sha256") or ""),
        "approved_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "expires_at": _future(),
        "execution_phase": "SYNC-OPS-2B",
        "approved_agent_ids": _agent_ids(plan),
        "approved_transaction_ids": _transaction_ids(plan),
        "approved_action_ids": _all_action_ids(plan),
        "stage_approved": stage,
        "verify_approved": verify,
        "artifact_store_initialize_approved": stage,
        "activate_approved": activate,
        "rollback_approved": rollback,
        "post_rollback_reactivate_approved": False,
        "delete_approved": False,
        "process_action_approved": False,
        "live_validation_approved": False,
        "partial_success_rebase_approved": False,
        "operator_reference": "sync-ops-2a-r2-temp-rehearsal",
        "notes": "temp-only approval fixture; not valid for real server roots",
    }


def _tree_byte_count(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


def run_full_scale_p2s_rehearsal(plan: Mapping[str, Any], temp_root: Path) -> dict[str, Any]:
    _require_temp_rehearsal_root(temp_root)
    if temp_root.exists() and any(temp_root.iterdir()):
        raise SyncPlannerError("p2s_rehearsal_temp_root_not_empty", exit_code=2)
    temp_root.mkdir(parents=True, exist_ok=True)
    artifact_root = temp_root / "artifact-store"
    bootstrap_plan = build_bootstrap_plan(artifact_root)
    bootstrap_environment = build_bootstrap_environment_snapshot(bootstrap_plan)
    bootstrap_approval = build_temp_bootstrap_approval(bootstrap_plan, bootstrap_environment)
    bootstrap_result = bootstrap_artifact_store(bootstrap_plan, bootstrap_approval, execute=True)
    rehearsal_plan = prepare_temp_rehearsal_plan(plan, temp_root)
    stage_approval = build_temp_rehearsal_approval(rehearsal_plan)
    activation_approval = build_temp_rehearsal_approval(
        rehearsal_plan,
        approval_id="temp-rehearsal-activation-approval",
        stage=False,
        verify=False,
        activate=True,
        rollback=True,
    )
    input_root = temp_root / "input"
    plan_path = input_root / "plan.json"
    stage_approval_path = input_root / "stage_approval.json"
    activation_approval_path = input_root / "activation_approval.json"
    write_json(plan_path, rehearsal_plan)
    write_json(stage_approval_path, stage_approval)
    write_json(activation_approval_path, activation_approval)
    stage = p2s_stage(plan_path, stage_approval_path, artifact_root, execute=True)
    verify = p2s_verify(plan_path, stage_approval_path, artifact_root, execute=True)
    try:
        p2s_activate(plan_path, stage_approval_path, artifact_root, execute=True)
        stage_only_activate_rejection = {"rejected": False, "reason": "", "blockers": []}
    except SyncPlannerError as exc:
        stage_only_activate_rejection = {
            "rejected": True,
            "reason": exc.reason,
            "exit_code": exc.exit_code,
            "blockers": list(exc.details.get("blockers", [])),
        }
    activate = p2s_activate(plan_path, activation_approval_path, artifact_root, execute=True)
    recover = p2s_recover(artifact_root, str(stage["run_id"]))
    rollback = p2s_rollback(plan_path, activation_approval_path, artifact_root, execute=True)
    stage_root = _stage_root(rehearsal_plan)
    plan_summary = p2s_summary_from_plan(rehearsal_plan)
    execution_summary = {
        "planned_action_total": plan_summary["materialization_total"],
        "physical_write_total": plan_summary["physical_write_total"],
        "shared_noop_total": plan_summary["shared_noop_total"],
        "written_file_total": int(stage["stage"].get("written_file_count") or 0),
        "byte_count": _tree_byte_count(stage_root),
        "hardlink_count": int(activate.get("hardlink_count") or 0),
        "stage_only_activate_rejected": bool(stage_only_activate_rejection.get("rejected")),
        "event_count": int(recover.get("event_count") or 0),
    }
    return {
        "schema_version": "agent_sync_p2s_full_scale_temp_rehearsal_v1",
        "temp_root": str(temp_root),
        "plan_id": str(rehearsal_plan.get("plan_id") or ""),
        "plan_sha256": str(rehearsal_plan.get("canonical_sha256") or ""),
        "environment_snapshot_sha256": build_environment_snapshot(rehearsal_plan)["environment_snapshot_sha256"],
        "planned_action_count": len(_all_actions(rehearsal_plan)),
        "written_action_count": int(stage["stage"].get("written_file_count") or 0),
        "byte_count": execution_summary["byte_count"],
        "plan_summary": plan_summary,
        "execution_summary": execution_summary,
        "stage": stage["stage"],
        "bootstrap": bootstrap_result,
        "verify": verify,
        "stage_only_activate_rejection": stage_only_activate_rejection,
        "activate": activate,
        "rollback": rollback,
        "crash_recovery": recover,
        "versioned_stage_preserved": stage_root.exists(),
        "old_active_restored_after_rollback": _active_path(rehearsal_plan).exists(),
        "failed_baseline_retained": bool(rollback.get("failed_baseline_retained")),
        "hardlink_count": int(activate.get("hardlink_count") or 0),
        "real_roots_modified": False,
    }


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
