# ruff: noqa: D103
"""Read-only CLI for bidirectional external-agent sync planning."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from react_agent.ops.sync_approval import load_approval, validate_approval
from react_agent.ops.sync_artifacts import artifact_store_preflight
from react_agent.ops.sync_bootstrap import (
    bootstrap_artifact_store,
    build_bootstrap_approval_request,
    build_bootstrap_environment_snapshot,
    build_bootstrap_plan,
    recover_bootstrap,
    rollback_bootstrap,
    validate_bootstrap_plan,
    verify_artifact_store,
)
from react_agent.ops.sync_contracts import (
    EXAMPLES_DIR,
    READ_ONLY_UNSUPPORTED_COMMANDS,
    SCHEMA_FILES,
    SCHEMAS_DIR,
    SYNC_POLICY_PATH,
    SyncPlannerError,
    canonical_sha256,
    ensure_output_path,
    maybe_write_json,
    print_or_json,
    read_json,
    validate_by_schema_version,
    validate_schema_meta,
    write_json,
)
from react_agent.ops.sync_coverage import load_plan_and_build_ledgers
from react_agent.ops.sync_diff import diff_inventory
from react_agent.ops.sync_environment import build_environment_snapshot
from react_agent.ops.sync_inventory import build_runtime_inventory
from react_agent.ops.sync_lock import SyncLockManager
from react_agent.ops.sync_p2s import (
    p2s_activate,
    p2s_recover,
    p2s_rollback,
    p2s_stage,
    p2s_verify,
    run_full_scale_p2s_rehearsal,
)
from react_agent.ops.sync_plan import (
    build_cycle_plan,
    build_experiment_template,
    build_p2s_plan,
    build_s2p_plan,
    load_baseline_pointer,
    load_plan,
    validate_experiment_manifest,
    validate_plan,
)
from react_agent.ops.sync_registry import load_sync_policy, validate_static_registry
from react_agent.ops.sync_summary import p2s_summary_from_plan


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json-output", help="Write JSON output to an explicit file path.")
    parser.add_argument("--stdout-json", action="store_true", help="Write JSON output to stdout.")


def _schema_validation_payload() -> dict[str, Any]:
    schema_results: list[dict[str, Any]] = []
    example_results: list[dict[str, Any]] = []
    for filename in sorted(SCHEMA_FILES.values()):
        path = SCHEMAS_DIR / filename
        schema = read_json(path)
        validate_schema_meta(schema)
        schema_results.append({"schema": filename, "meta_valid": True})
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        instance = read_json(path)
        if isinstance(instance, dict) and "schema_version" in instance:
            validate_by_schema_version(instance)
            example_results.append({"example": path.name, "valid": True, "schema_version": instance["schema_version"]})
        elif path.name == "canonical_hash_test_vectors.json":
            for vector in instance:
                expected = vector["canonical_sha256"]
                actual = canonical_sha256(vector["input"])
                if actual != expected:
                    raise SyncPlannerError("canonical_hash_vector_failed", exit_code=7, details={"vector_id": vector["vector_id"]})
            example_results.append({"example": path.name, "valid": True, "schema_version": "canonical_hash_vectors"})
    return {
        "summary_title": "schema validation",
        "schema_count": len(schema_results),
        "example_count": len(example_results),
        "schemas": schema_results,
        "examples": example_results,
        "exit_code": 0,
    }


def cmd_inventory(args: argparse.Namespace) -> int:
    payload = build_runtime_inventory(include_files=not args.no_files)
    if getattr(args, "source_policy_summary", False):
        counts: dict[str, int] = {}
        for agent in payload.get("agents") or []:
            if not isinstance(agent, dict):
                continue
            for record in (agent.get("roots") or {}).get("prod", {}).get("files") or []:
                if isinstance(record, dict):
                    category = str(record.get("source_category") or "unknown")
                    counts[category] = counts.get(category, 0) + 1
        payload["source_policy_summary"] = {"source_category_counts": dict(sorted(counts.items()))}
    payload["summary_title"] = "agent-sync inventory"
    payload["exit_code"] = 0
    rows = [
        f"agents={payload['agent_count']}",
        f"fatal_conflicts={payload['fatal_conflict_count']}",
        f"review_warnings={payload['review_warning_count']}",
    ]
    return print_or_json(args, payload, rows)


def _plan_source_audit(plan: dict[str, Any]) -> dict[str, Any]:
    actions = [
        action
        for agent in plan.get("agents", [])
        if isinstance(agent, dict)
        for action in agent.get("actions", [])
        if isinstance(action, dict)
    ]
    generated_or_local = [
        action
        for action in actions
        if action.get("operation") in {"copy_from_prod", "snapshot_semantic_placeholder"}
        and action.get("source_category")
        in {
            "generated_artifact",
            "experiment_result",
            "data_asset",
            "model_asset",
            "backup_artifact",
            "editor_local_metadata",
            "runtime_noise",
            "sensitive_blocked",
            "unknown_blocked",
        }
    ]
    not_scanned = [
        action
        for action in actions
        if action.get("operation") in {"copy_from_prod", "snapshot_semantic_placeholder"}
        and action.get("sensitive_classification") == "not_scanned"
    ]
    return {
        "schema_version": "agent_sync_p2s_source_audit_v1",
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("canonical_sha256"),
        "source_selection": plan.get("source_selection", {}),
        "copy_action_count": sum(1 for action in actions if action.get("operation") == "copy_from_prod"),
        "not_scanned_copy_count": len(not_scanned),
        "non_materializable_copy_count": len(generated_or_local),
        "valid": not not_scanned and not generated_or_local,
        "exit_code": 0 if not not_scanned and not generated_or_local else 7,
    }


def cmd_status(args: argparse.Namespace) -> int:
    registry_validation = validate_static_registry()
    pointer = load_baseline_pointer()
    payload = {
        "summary_title": "agent-sync status",
        "registry": registry_validation,
        "baseline_pointer": pointer,
        "policy": {"path": str(SYNC_POLICY_PATH), "schema_version": load_sync_policy()["schema_version"]},
        "exit_code": 0 if registry_validation["valid"] else 3,
    }
    rows = [
        f"registry_valid={registry_validation['valid']}",
        f"formal_external_agents={registry_validation['formal_external_agent_count']}",
        f"baseline_id={pointer['active_baseline_id']}",
    ]
    return print_or_json(args, payload, rows)


def cmd_baseline_show(args: argparse.Namespace) -> int:
    payload = load_baseline_pointer(Path(args.pointer)) if args.pointer else load_baseline_pointer()
    payload["summary_title"] = "agent-sync baseline"
    payload["exit_code"] = 0
    rows = [
        f"baseline_id={payload['active_baseline_id']}",
        f"active_exists={payload['active_exists']}",
        f"versioned_baseline_exists={payload['versioned_baseline_exists']}",
    ]
    return print_or_json(args, payload, rows)


def cmd_experiment_init(args: argparse.Namespace) -> int:
    output = ensure_output_path(args.output)
    if output is None:
        raise SyncPlannerError("experiment_init_requires_output", exit_code=2)
    template = build_experiment_template(output_root=args.workspace_root)
    write_json(output, template)
    payload = {
        "summary_title": "agent-sync experiment init",
        "output": str(output),
        "experiment_id": template["experiment_id"],
        "exit_code": 0,
    }
    return print_or_json(args, payload, [f"created={output}", f"experiment_id={template['experiment_id']}"])


def cmd_experiment_validate(args: argparse.Namespace) -> int:
    manifest = read_json(Path(args.manifest))
    result = validate_experiment_manifest(manifest)
    payload = {"summary_title": "agent-sync experiment validate", **result, "exit_code": 0 if result["valid"] else 7}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"blockers={len(result['blockers'])}"])


def cmd_p2s_plan(args: argparse.Namespace) -> int:
    plan = build_p2s_plan()
    output = ensure_output_path(args.output)
    maybe_write_json(output, plan)
    validation = validate_plan(plan, check_target_freshness=False)
    payload = {"summary_title": "agent-sync p2s plan", "plan": plan, "validation": validation, "exit_code": validation["exit_code"]}
    action_count = sum(len(agent["actions"]) for agent in plan["agents"])
    blocked_count = sum(len(agent["blocked_actions"]) for agent in plan["agents"])
    summary = plan.get("summary") or p2s_summary_from_plan(plan)
    return print_or_json(
        args,
        payload,
        [
            f"plan_id={plan['plan_id']}",
            f"actions={action_count}",
            f"blocked={blocked_count}",
            f"physical_writes={summary['physical_write_total']}",
        ],
    )


def cmd_p2s_coverage(args: argparse.Namespace) -> int:
    ledgers = load_plan_and_build_ledgers(Path(args.plan))
    historical = ledgers["historical_parity"]
    current = ledgers["current_prod_coverage"]
    valid = historical["unresolved_count"] == 0 and current["unresolved_count"] == 0
    payload = {
        "summary_title": "agent-sync p2s coverage",
        "historical_parity": historical,
        "current_prod_coverage": current,
        "valid": valid,
        "exit_code": 0 if valid else 7,
    }
    rows = [
        f"historical_rows={historical['row_count']}",
        f"historical_unresolved={historical['unresolved_count']}",
        f"current_rows={current['row_count']}",
        f"current_unresolved={current['unresolved_count']}",
        f"safe_source_coverage_ratio={current['safe_source_coverage_ratio']:.6f}",
    ]
    return print_or_json(args, payload, rows)


def cmd_p2s_source_audit(args: argparse.Namespace) -> int:
    plan = load_plan(Path(args.plan))
    payload = {"summary_title": "agent-sync p2s source audit", **_plan_source_audit(plan)}
    rows = [
        f"plan_id={payload['plan_id']}",
        f"not_scanned_copy_count={payload['not_scanned_copy_count']}",
        f"non_materializable_copy_count={payload['non_materializable_copy_count']}",
    ]
    return print_or_json(args, payload, rows)


def cmd_p2s_rehearse(args: argparse.Namespace) -> int:
    plan = load_plan(Path(args.plan))
    result = run_full_scale_p2s_rehearsal(plan, Path(args.temp_root))
    payload = {"summary_title": "agent-sync p2s rehearse", **result, "exit_code": 0}
    rows = [
        f"plan_id={result['plan_id']}",
        f"planned_actions={result['planned_action_count']}",
        f"written_actions={result['written_action_count']}",
        f"physical_writes={result.get('execution_summary', {}).get('physical_write_total')}",
        f"stage_only_activate_rejected={result.get('stage_only_activate_rejection', {}).get('rejected')}",
        f"hardlink_count={result['hardlink_count']}",
    ]
    return print_or_json(args, payload, rows)


def cmd_s2p_plan(args: argparse.Namespace) -> int:
    manifest = read_json(Path(args.experiment))
    plan = build_s2p_plan(manifest)
    output = ensure_output_path(args.output)
    maybe_write_json(output, plan)
    validation = validate_plan(plan, check_target_freshness=False)
    exit_code = 11 if plan["global_blockers"] else validation["exit_code"]
    payload = {"summary_title": "agent-sync s2p plan", "plan": plan, "validation": validation, "exit_code": exit_code}
    action_count = sum(len(agent["actions"]) for agent in plan["agents"])
    blocked_count = sum(len(agent["blocked_actions"]) for agent in plan["agents"]) + len(plan["global_blockers"])
    return print_or_json(args, payload, [f"plan_id={plan['plan_id']}", f"actions={action_count}", f"blocked={blocked_count}"])


def cmd_cycle_plan(args: argparse.Namespace) -> int:
    s2p = load_plan(Path(args.s2p_plan))
    plan = build_cycle_plan(s2p)
    output = ensure_output_path(args.output)
    maybe_write_json(output, plan)
    payload = {"summary_title": "agent-sync cycle plan", "plan": plan, "exit_code": 0}
    return print_or_json(args, payload, [f"plan_id={plan['plan_id']}", "p2s_rebase=deferred"])


def cmd_plan_show(args: argparse.Namespace) -> int:
    plan = load_plan(Path(args.plan))
    payload = {"summary_title": "agent-sync plan show", "plan": plan, "exit_code": 0}
    rows = [f"plan_id={plan.get('plan_id')}", f"direction={plan.get('direction')}"]
    if plan.get("direction") == "p2s":
        rows.extend(
            [
                f"observed_diff={'present' if plan.get('observed_diff') else 'missing'}",
                f"stage_materialization={'present' if plan.get('stage_materialization') else 'missing'}",
                f"activation={'present' if plan.get('activation') else 'missing'}",
                f"rollback={'present' if plan.get('activation', {}).get('rollback') else 'missing'}",
            ]
        )
    return print_or_json(args, payload, rows)


def cmd_plan_explain_execution(args: argparse.Namespace) -> int:
    plan = load_plan(Path(args.plan))
    contract = plan.get("execution_contract") or {}
    store = (contract.get("artifact_store") or {}) if isinstance(contract, dict) else {}
    summary = plan.get("summary") or (p2s_summary_from_plan(plan) if plan.get("direction") == "p2s" else {})
    payload = {
        "summary_title": "agent-sync plan execution",
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("canonical_sha256"),
        "writer_contract_version": contract.get("writer_contract_version") if isinstance(contract, dict) else "",
        "artifact_store_initialization": plan.get("artifact_store_initialization", {}),
        "required_permissions": plan.get("approval_requirements", {}),
        "environment_binding": {
            "environment_snapshot_required": bool((plan.get("approval_requirements") or {}).get("environment_snapshot_required")),
            "stage_only_approval_cannot_activate": bool((plan.get("activation_approval_boundary") or {}).get("stage_only_approval_cannot_activate")),
        },
        "artifact_store_root": store.get("root") if isinstance(store, dict) else "",
        "summary": summary,
        "exit_code": 0,
    }
    rows = [
        f"plan_id={payload['plan_id']}",
        f"writer_contract_version={payload['writer_contract_version']}",
        f"artifact_store_initialization_required={payload['artifact_store_initialization'].get('required')}",
        f"stage_permission={payload['required_permissions'].get('stage_approved')}",
        f"activate_permission={payload['required_permissions'].get('activate_approved')}",
    ]
    return print_or_json(args, payload, rows)


def cmd_plan_validate(args: argparse.Namespace) -> int:
    plan = load_plan(Path(args.plan))
    result = validate_plan(plan, check_target_freshness=not args.skip_target_freshness)
    payload = {"summary_title": "agent-sync plan validate", **result, "exit_code": result["exit_code"]}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"blockers={len(result['blockers'])}"])


def cmd_plan_diff(args: argparse.Namespace) -> int:
    inventory = build_runtime_inventory(include_files=True)
    diff = diff_inventory(inventory)
    payload = {"summary_title": "agent-sync plan diff", "diff": diff, "exit_code": 0}
    return print_or_json(args, payload, [f"agents={diff['agent_count']}", f"classifications={len(diff['totals'])}"])


def cmd_schema_validate(args: argparse.Namespace) -> int:
    payload = _schema_validation_payload()
    return print_or_json(args, payload, [f"schemas={payload['schema_count']}", f"examples={payload['example_count']}"])


def _require_execute(args: argparse.Namespace) -> None:
    if not getattr(args, "execute", False):
        raise SyncPlannerError("execute_required", exit_code=2)


def cmd_approval_validate(args: argparse.Namespace) -> int:
    plan = load_plan(Path(args.plan))
    approval = load_approval(Path(args.approval))
    environment = build_environment_snapshot(plan)
    result = validate_approval(
        approval,
        plan,
        environment_snapshot=environment,
        require_stage=args.require_stage,
        require_verify=args.require_verify,
        require_artifact_store_initialize=args.require_artifact_store_initialize,
        require_activate=args.require_activate,
        require_rollback=args.require_rollback,
    )
    payload = {"summary_title": "agent-sync approval validate", **result, "exit_code": result["exit_code"]}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"blockers={len(result['blockers'])}"])


def cmd_artifact_store_preflight(args: argparse.Namespace) -> int:
    payload = {
        "summary_title": "agent-sync artifact-store preflight",
        **artifact_store_preflight(Path(args.root)),
    }
    payload["exit_code"] = 0 if payload.get("ready") else 3
    return print_or_json(
        args,
        payload,
        [
            f"root_exists={payload['root_exists']}",
            f"parent_exists={payload['parent_exists']}",
            f"creation_required={payload['creation_required']}",
            f"blockers={len(payload['blockers'])}",
        ],
    )


def cmd_artifact_store_bootstrap_plan(args: argparse.Namespace) -> int:
    plan = build_bootstrap_plan(Path(args.root))
    environment = build_bootstrap_environment_snapshot(plan)
    request = build_bootstrap_approval_request(plan, environment)
    output = ensure_output_path(args.output)
    maybe_write_json(output, plan)
    payload = {
        "summary_title": "agent-sync artifact-store bootstrap plan",
        "plan": plan,
        "environment": environment,
        "approval_request": request,
        "validation": validate_bootstrap_plan(plan),
        "exit_code": 0,
    }
    return print_or_json(
        args,
        payload,
        [
            f"plan_id={plan['plan_id']}",
            f"root={plan['root']}",
            f"directory_actions={len(plan['directory_actions'])}",
            f"status={request['status']}",
        ],
    )


def cmd_artifact_store_bootstrap_validate(args: argparse.Namespace) -> int:
    plan = read_json(Path(args.plan))
    if not isinstance(plan, dict):
        raise SyncPlannerError("bootstrap_plan_not_object", exit_code=2)
    result = validate_bootstrap_plan(plan)
    payload = {"summary_title": "agent-sync artifact-store bootstrap validate", **result, "exit_code": result["exit_code"]}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"blockers={len(result['blockers'])}"])


def cmd_artifact_store_bootstrap(args: argparse.Namespace) -> int:
    _require_execute(args)
    plan = read_json(Path(args.plan))
    approval = read_json(Path(args.approval))
    if not isinstance(plan, dict) or not isinstance(approval, dict):
        raise SyncPlannerError("bootstrap_input_not_object", exit_code=2)
    result = bootstrap_artifact_store(plan, approval, execute=True)
    payload = {"summary_title": "agent-sync artifact-store bootstrap", **result, "exit_code": 0}
    return print_or_json(args, payload, [f"status={result['status']}", f"root={result['root']}"])


def cmd_artifact_store_verify(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.plan:
        plan = read_json(Path(args.plan))
        if isinstance(plan, dict):
            root = Path(str(plan.get("root") or root))
    result = verify_artifact_store(root)
    payload = {"summary_title": "agent-sync artifact-store verify", **result, "exit_code": result["exit_code"]}
    return print_or_json(args, payload, [f"bootstrapped={result['bootstrapped']}", f"blockers={len(result['blockers'])}"])


def cmd_artifact_store_recover(args: argparse.Namespace) -> int:
    plan = read_json(Path(args.plan))
    if not isinstance(plan, dict):
        raise SyncPlannerError("bootstrap_plan_not_object", exit_code=2)
    result = recover_bootstrap(plan)
    payload = {"summary_title": "agent-sync artifact-store recover", **result, "exit_code": result["exit_code"]}
    return print_or_json(args, payload, [f"recommended_action={result['recommended_action']}"])


def cmd_artifact_store_bootstrap_rollback(args: argparse.Namespace) -> int:
    _require_execute(args)
    plan = read_json(Path(args.plan))
    approval = read_json(Path(args.approval))
    if not isinstance(plan, dict) or not isinstance(approval, dict):
        raise SyncPlannerError("bootstrap_input_not_object", exit_code=2)
    result = rollback_bootstrap(plan, approval, execute=True)
    payload = {"summary_title": "agent-sync artifact-store bootstrap rollback", **result, "exit_code": result["exit_code"]}
    return print_or_json(args, payload, [f"status={result['status']}", f"removed={len(result['removed_directories'])}"])


def cmd_p2s_stage(args: argparse.Namespace) -> int:
    _require_execute(args)
    result = p2s_stage(Path(args.plan), Path(args.approval), Path(args.artifact_root), execute=True)
    payload = {"summary_title": "agent-sync p2s stage", **result, "exit_code": 0}
    return print_or_json(args, payload, [f"run_id={result['run_id']}", f"status={result['status']}"])


def cmd_p2s_verify(args: argparse.Namespace) -> int:
    _require_execute(args)
    result = p2s_verify(Path(args.plan), Path(args.approval), Path(args.artifact_root), execute=True)
    payload = {"summary_title": "agent-sync p2s verify", **result, "exit_code": 0 if result["valid"] else 7}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"digest_match={result['digest_match']}"])


def cmd_p2s_activate(args: argparse.Namespace) -> int:
    _require_execute(args)
    result = p2s_activate(Path(args.plan), Path(args.approval), Path(args.artifact_root), execute=True)
    payload = {"summary_title": "agent-sync p2s activate", **result, "exit_code": 0}
    return print_or_json(args, payload, [f"status={result['status']}", f"hardlink_count={result['hardlink_count']}"])


def cmd_p2s_rollback(args: argparse.Namespace) -> int:
    _require_execute(args)
    result = p2s_rollback(Path(args.plan), Path(args.approval), Path(args.artifact_root), execute=True)
    payload = {"summary_title": "agent-sync p2s rollback", **result, "exit_code": 0}
    return print_or_json(args, payload, [f"status={result['status']}", f"archive_restored={result['archive_restored']}"])


def cmd_run_status(args: argparse.Namespace) -> int:
    artifact_root = Path(args.artifact_root)
    run_root = artifact_root / "runs" / args.run_id
    payload = {
        "summary_title": "agent-sync run status",
        "run_id": args.run_id,
        "run_root": str(run_root),
        "exists": run_root.exists(),
        "events": p2s_recover(artifact_root, args.run_id),
        "exit_code": 0,
    }
    return print_or_json(args, payload, [f"run_id={args.run_id}", f"exists={run_root.exists()}"])


def cmd_run_recover(args: argparse.Namespace) -> int:
    result = p2s_recover(Path(args.artifact_root), args.run_id)
    payload = {"summary_title": "agent-sync run recover", **result, "exit_code": 0}
    return print_or_json(args, payload, [f"run_id={args.run_id}", f"recommended_action={result['recommended_action']}"])


def cmd_unsupported(group: str, command: str) -> int:
    payload = {
        "schema_version": "agent_sync_cli_error_v1",
        "reason": "command_not_available_before_sync_ops_2",
        "command": f"{group} {command}",
        "exit_code": 2,
    }
    sys.stderr.write(json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-sync", description="Read-only external Agent sync planner.")
    subparsers = parser.add_subparsers(dest="group", required=True)

    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--no-files", action="store_true")
    inventory.add_argument("--source-policy-summary", action="store_true")
    _add_output_args(inventory)
    inventory.set_defaults(func=cmd_inventory)

    status = subparsers.add_parser("status")
    _add_output_args(status)
    status.set_defaults(func=cmd_status)

    schema = subparsers.add_parser("schema")
    schema_sub = schema.add_subparsers(dest="command", required=True)
    schema_validate = schema_sub.add_parser("validate")
    _add_output_args(schema_validate)
    schema_validate.set_defaults(func=cmd_schema_validate)

    baseline = subparsers.add_parser("baseline")
    baseline_sub = baseline.add_subparsers(dest="command", required=True)
    baseline_show = baseline_sub.add_parser("show")
    baseline_show.add_argument("--pointer")
    _add_output_args(baseline_show)
    baseline_show.set_defaults(func=cmd_baseline_show)

    experiment = subparsers.add_parser("experiment")
    experiment_sub = experiment.add_subparsers(dest="command", required=True)
    experiment_init = experiment_sub.add_parser("init")
    experiment_init.add_argument("--output", required=True)
    experiment_init.add_argument("--workspace-root", default="/tmp/agent-sync-experiment")
    _add_output_args(experiment_init)
    experiment_init.set_defaults(func=cmd_experiment_init)
    experiment_validate = experiment_sub.add_parser("validate")
    experiment_validate.add_argument("--manifest", required=True)
    _add_output_args(experiment_validate)
    experiment_validate.set_defaults(func=cmd_experiment_validate)

    p2s = subparsers.add_parser("p2s")
    p2s_sub = p2s.add_subparsers(dest="command", required=True)
    p2s_plan = p2s_sub.add_parser("plan")
    p2s_plan.add_argument("--output")
    _add_output_args(p2s_plan)
    p2s_plan.set_defaults(func=cmd_p2s_plan)
    p2s_coverage = p2s_sub.add_parser("coverage")
    p2s_coverage.add_argument("--plan", required=True)
    _add_output_args(p2s_coverage)
    p2s_coverage.set_defaults(func=cmd_p2s_coverage)
    p2s_source_audit = p2s_sub.add_parser("source-audit")
    p2s_source_audit.add_argument("--plan", required=True)
    _add_output_args(p2s_source_audit)
    p2s_source_audit.set_defaults(func=cmd_p2s_source_audit)
    p2s_rehearse = p2s_sub.add_parser("rehearse")
    p2s_rehearse.add_argument("--plan", required=True)
    p2s_rehearse.add_argument("--temp-root", required=True)
    _add_output_args(p2s_rehearse)
    p2s_rehearse.set_defaults(func=cmd_p2s_rehearse)
    for command_name, command_func in (
        ("stage", cmd_p2s_stage),
        ("verify", cmd_p2s_verify),
        ("activate", cmd_p2s_activate),
        ("rollback", cmd_p2s_rollback),
    ):
        p2s_command = p2s_sub.add_parser(command_name)
        p2s_command.add_argument("--plan", required=True)
        p2s_command.add_argument("--approval", required=True)
        p2s_command.add_argument("--artifact-root", required=True)
        p2s_command.add_argument("--execute", action="store_true")
        _add_output_args(p2s_command)
        p2s_command.set_defaults(func=command_func)

    approval = subparsers.add_parser("approval")
    approval_sub = approval.add_subparsers(dest="command", required=True)
    approval_validate = approval_sub.add_parser("validate")
    approval_validate.add_argument("--plan", required=True)
    approval_validate.add_argument("--approval", required=True)
    approval_validate.add_argument("--require-stage", action="store_true")
    approval_validate.add_argument("--require-verify", action="store_true")
    approval_validate.add_argument("--require-artifact-store-initialize", action="store_true")
    approval_validate.add_argument("--require-activate", action="store_true")
    approval_validate.add_argument("--require-rollback", action="store_true")
    _add_output_args(approval_validate)
    approval_validate.set_defaults(func=cmd_approval_validate)

    s2p = subparsers.add_parser("s2p")
    s2p_sub = s2p.add_subparsers(dest="command", required=True)
    s2p_plan = s2p_sub.add_parser("plan")
    s2p_plan.add_argument("--experiment", required=True)
    s2p_plan.add_argument("--output")
    _add_output_args(s2p_plan)
    s2p_plan.set_defaults(func=cmd_s2p_plan)
    for unsupported in ("apply", "smoke", "rollback"):
        parser_unsupported = s2p_sub.add_parser(unsupported)
        parser_unsupported.set_defaults(func=lambda _args, cmd=unsupported: cmd_unsupported("s2p", cmd))

    cycle = subparsers.add_parser("cycle")
    cycle_sub = cycle.add_subparsers(dest="command", required=True)
    cycle_plan = cycle_sub.add_parser("plan")
    cycle_plan.add_argument("--s2p-plan", required=True)
    cycle_plan.add_argument("--output")
    _add_output_args(cycle_plan)
    cycle_plan.set_defaults(func=cmd_cycle_plan)
    publish = cycle_sub.add_parser("publish-and-rebase")
    publish.set_defaults(func=lambda _args: cmd_unsupported("cycle", "publish-and-rebase"))

    plan = subparsers.add_parser("plan")
    plan_sub = plan.add_subparsers(dest="command", required=True)
    plan_show = plan_sub.add_parser("show")
    plan_show.add_argument("--plan", required=True)
    _add_output_args(plan_show)
    plan_show.set_defaults(func=cmd_plan_show)
    plan_explain = plan_sub.add_parser("explain-execution")
    plan_explain.add_argument("--plan", required=True)
    _add_output_args(plan_explain)
    plan_explain.set_defaults(func=cmd_plan_explain_execution)
    plan_validate = plan_sub.add_parser("validate")
    plan_validate.add_argument("--plan", required=True)
    plan_validate.add_argument("--skip-target-freshness", action="store_true")
    _add_output_args(plan_validate)
    plan_validate.set_defaults(func=cmd_plan_validate)
    plan_diff = plan_sub.add_parser("diff")
    _add_output_args(plan_diff)
    plan_diff.set_defaults(func=cmd_plan_diff)

    artifact_store = subparsers.add_parser("artifact-store")
    artifact_store_sub = artifact_store.add_subparsers(dest="command", required=True)
    artifact_preflight = artifact_store_sub.add_parser("preflight")
    artifact_preflight.add_argument("--root", default="/sdb/dlut/ops-artifacts/agent-sync")
    _add_output_args(artifact_preflight)
    artifact_preflight.set_defaults(func=cmd_artifact_store_preflight)
    artifact_bootstrap_plan = artifact_store_sub.add_parser("bootstrap-plan")
    artifact_bootstrap_plan.add_argument("--root", default="/sdb/dlut/ops-artifacts/agent-sync")
    artifact_bootstrap_plan.add_argument("--output")
    _add_output_args(artifact_bootstrap_plan)
    artifact_bootstrap_plan.set_defaults(func=cmd_artifact_store_bootstrap_plan)
    artifact_bootstrap_validate = artifact_store_sub.add_parser("bootstrap-validate")
    artifact_bootstrap_validate.add_argument("--plan", required=True)
    _add_output_args(artifact_bootstrap_validate)
    artifact_bootstrap_validate.set_defaults(func=cmd_artifact_store_bootstrap_validate)
    artifact_bootstrap = artifact_store_sub.add_parser("bootstrap")
    artifact_bootstrap.add_argument("--plan", required=True)
    artifact_bootstrap.add_argument("--approval", required=True)
    artifact_bootstrap.add_argument("--execute", action="store_true")
    _add_output_args(artifact_bootstrap)
    artifact_bootstrap.set_defaults(func=cmd_artifact_store_bootstrap)
    artifact_verify = artifact_store_sub.add_parser("verify")
    artifact_verify.add_argument("--root", default="/sdb/dlut/ops-artifacts/agent-sync")
    artifact_verify.add_argument("--plan")
    _add_output_args(artifact_verify)
    artifact_verify.set_defaults(func=cmd_artifact_store_verify)
    artifact_recover = artifact_store_sub.add_parser("recover")
    artifact_recover.add_argument("--plan", required=True)
    _add_output_args(artifact_recover)
    artifact_recover.set_defaults(func=cmd_artifact_store_recover)
    artifact_rollback = artifact_store_sub.add_parser("bootstrap-rollback")
    artifact_rollback.add_argument("--plan", required=True)
    artifact_rollback.add_argument("--approval", required=True)
    artifact_rollback.add_argument("--execute", action="store_true")
    _add_output_args(artifact_rollback)
    artifact_rollback.set_defaults(func=cmd_artifact_store_bootstrap_rollback)

    lock = subparsers.add_parser("lock")
    lock_sub = lock.add_subparsers(dest="command", required=True)
    lock_show = lock_sub.add_parser("show")
    lock_show.add_argument("--artifact-root", default="/sdb/dlut/ops-artifacts/agent-sync")
    _add_output_args(lock_show)
    lock_show.set_defaults(
        func=lambda args: print_or_json(args, {"summary_title": "agent-sync lock show", **SyncLockManager(Path(args.artifact_root)).inspect(), "exit_code": 0}, ["lock_inspection=true"])
    )
    force = lock_sub.add_parser("force-release")
    force.set_defaults(func=lambda _args: cmd_unsupported("lock", "force-release"))

    run = subparsers.add_parser("run")
    run_sub = run.add_subparsers(dest="command", required=True)
    run_status = run_sub.add_parser("status")
    run_status.add_argument("--artifact-root", required=True)
    run_status.add_argument("--run-id", required=True)
    _add_output_args(run_status)
    run_status.set_defaults(func=cmd_run_status)
    run_recover = run_sub.add_parser("recover")
    run_recover.add_argument("--artifact-root", required=True)
    run_recover.add_argument("--run-id", required=True)
    _add_output_args(run_recover)
    run_recover.set_defaults(func=cmd_run_recover)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    group = getattr(args, "group", "")
    command = getattr(args, "command", "")
    if (group, command) in READ_ONLY_UNSUPPORTED_COMMANDS:
        return cmd_unsupported(group, command)
    try:
        return int(args.func(args))
    except SyncPlannerError as exc:
        payload = {"schema_version": "agent_sync_cli_error_v1", "reason": exc.reason, "details": exc.details, "exit_code": exc.exit_code}
        sys.stderr.write(json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n")
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
