# ruff: noqa: D103
"""Read-only CLI for bidirectional external-agent sync planning."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from react_agent.ops.sync_5a_r1x import (
    build_final_compound_execution_approval_request,
    build_final_compound_execution_plan,
    build_first_cycle_projection,
    build_projected_experiment_contract,
    build_risk_fraud_authority_decision,
    build_risk_fraud_p2s_rebase_plan,
    build_risk_fraud_prod_recovery_plan,
    build_risk_fraud_source_authority_matrix,
    requalify_financial_data_service_candidate,
    validate_final_compound_execution_plan,
    validate_old_risk_fraud_repair_plan,
    validate_risk_fraud_p2s_rebase_plan,
    validate_risk_fraud_prod_recovery_plan,
)
from react_agent.ops.sync_5a_r2x import (
    build_final_compound_execution_approval_request_v2,
    build_final_compound_execution_plan_v2,
    build_first_real_cycle_plan_v2,
    build_full_p2s_rebase_plan_v2,
    build_projected_experiment_manifest_v2,
    build_source_loss_recovery_plan_v2,
    build_source_package_integrity,
    reselect_first_candidate,
    validate_final_compound_execution_plan_v2,
    validate_first_real_cycle_plan_v2,
    validate_full_p2s_rebase_plan_v2,
    validate_source_loss_recovery_plan_v2,
    validate_superseded_r1x_p2s_projection,
    validate_superseded_r1x_recovery_plan,
)
from react_agent.ops.sync_5a_r3x import (
    build_environment_reference_metadata,
    build_final_compound_execution_approval_request_v3,
    build_final_compound_execution_plan_v3,
    build_first_real_cycle_plan_v3,
    build_full_p2s_rebase_plan_v3,
    build_projected_experiment_manifest_v3,
    build_risk_fraud_launch_authority,
    build_source_loss_recovery_plan_v3,
    build_source_package_provenance,
    validate_final_compound_execution_plan_v3,
    validate_first_real_cycle_plan_v3,
    validate_full_p2s_rebase_plan_v3,
    validate_source_loss_recovery_plan_v3,
    validate_source_package_provenance,
)
from react_agent.ops.sync_5a_r4x import (
    build_conditional_approval_chain_v1,
    build_environment_profile_v1,
    build_equivalence_contract_v1,
    build_first_real_cycle_plan_v4,
    build_full_p2s_rebase_plan_v4,
    build_machine_precutover_canary_approval,
    build_precutover_canary_plan_v1,
    build_projected_experiment_v4,
    build_runtime_variable_matrix,
    build_source_loss_recovery_plan_v4,
    validate_conditional_approval_chain_v1,
    validate_environment_profile_v1,
    validate_equivalence_contract_v1,
    validate_full_p2s_rebase_plan_v4,
    validate_machine_precutover_canary_approval,
    validate_precutover_canary_plan_v1,
    validate_runtime_variable_matrix,
    validate_source_loss_recovery_plan_v4,
)
from react_agent.ops.sync_approval import load_approval, validate_approval
from react_agent.ops.sync_artifacts import artifact_store_preflight
from react_agent.ops.sync_bootstrap import (
    bootstrap_artifact_store,
    build_bootstrap_approval_request,
    build_bootstrap_environment_snapshot,
    build_bootstrap_plan,
    recover_bootstrap,
    rollback_bootstrap,
    validate_bootstrap_environment_contract,
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
from react_agent.ops.sync_cycle import (
    build_cycle_plan_from_experiment,
    build_cycle_plan_from_s2p,
    recover_cycle,
    run_cycle_noop,
    run_temp_cycle_compensation,
    run_temp_multi_transaction_cycle,
    run_temp_nonzero_cycle,
    validate_cycle_plan,
)
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
    build_experiment_template,
    build_p2s_plan,
    build_s2p_plan,
    load_baseline_pointer,
    load_plan,
    validate_experiment_manifest,
    validate_plan,
)
from react_agent.ops.sync_process_launcher import (
    preflight_launch_authority,
    start_supervised_process,
    status_supervised_process,
    stop_supervised_process,
    validate_launch_authority,
)
from react_agent.ops.sync_registry import load_sync_policy, validate_static_registry
from react_agent.ops.sync_s2p import (
    build_experiment_fork,
    fake_live_gate,
    prod_digest_summary,
    recover_s2p_journal,
    run_s2p_noop,
    run_temp_historical_replay,
    sandbox_pointer_summary,
    validate_experiment_contract,
    validate_s2p_plan_contract,
)
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


def cmd_experiment_fork(args: argparse.Namespace) -> int:
    manifest = build_experiment_fork(workspace_root=Path(args.workspace_root), experiment_id=args.experiment_id)
    output = ensure_output_path(args.output)
    maybe_write_json(output, manifest)
    payload = {"summary_title": "agent-sync experiment fork", "manifest": manifest, "output": str(output or ""), "exit_code": 0}
    return print_or_json(
        args,
        payload,
        [
            f"experiment_id={manifest['experiment_id']}",
            f"workspace_root={manifest['workspace_root']}",
            f"copied_files={manifest.get('fork_result', {}).get('copied_file_count')}",
        ],
    )


def cmd_experiment_show(args: argparse.Namespace) -> int:
    manifest = read_json(Path(args.manifest))
    validation = validate_experiment_contract(manifest)
    payload = {"summary_title": "agent-sync experiment show", "manifest": manifest, "validation": validation, "exit_code": validation["exit_code"]}
    return print_or_json(args, payload, [f"experiment_id={manifest.get('experiment_id')}", f"status={manifest.get('status')}", f"valid={validation['valid']}"])


def cmd_experiment_diff(args: argparse.Namespace) -> int:
    manifest = read_json(Path(args.manifest))
    plan = build_s2p_plan(manifest)
    summary = plan.get("s2p_summary") or {}
    payload = {"summary_title": "agent-sync experiment diff", "plan_id": plan["plan_id"], "summary": summary, "blockers": plan.get("global_blockers", []), "exit_code": 0}
    return print_or_json(args, payload, [f"actions={summary.get('actionable_file_action_count')}", f"blocked={summary.get('blocked_action_count')}"])


def cmd_experiment_close(args: argparse.Namespace) -> int:
    if not args.reason:
        raise SyncPlannerError("experiment_close_reason_required", exit_code=2)
    manifest_path = Path(args.manifest)
    manifest = read_json(manifest_path)
    manifest["status"] = "closed"
    manifest["closed_at"] = __import__("datetime").datetime.now(__import__("datetime").UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest["close_reason"] = args.reason
    write_json(manifest_path, manifest)
    payload = {"summary_title": "agent-sync experiment close", "experiment_id": manifest.get("experiment_id"), "status": "closed", "exit_code": 0}
    return print_or_json(args, payload, [f"experiment_id={manifest.get('experiment_id')}", "status=closed"])


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


def cmd_s2p_validate(args: argparse.Namespace) -> int:
    plan = load_plan(Path(args.plan))
    result = validate_s2p_plan_contract(plan, check_target_freshness=not args.skip_target_freshness)
    payload = {"summary_title": "agent-sync s2p validate", **result, "exit_code": result["exit_code"]}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"blockers={len(result['blockers'])}"])


def cmd_s2p_explain(args: argparse.Namespace) -> int:
    plan = load_plan(Path(args.plan))
    summary = plan.get("s2p_summary") or {}
    payload = {
        "summary_title": "agent-sync s2p explain",
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("canonical_sha256"),
        "contract": plan.get("execution_contract", {}),
        "summary": summary,
        "approval_requirements": plan.get("approval_requirements", {}),
        "exit_code": 0,
    }
    return print_or_json(
        args,
        payload,
        [
            f"plan_id={payload['plan_id']}",
            f"actions={summary.get('actionable_file_action_count')}",
            f"process={summary.get('process_action_count')}",
            f"live={summary.get('live_gate_count')}",
        ],
    )


def cmd_s2p_rehearse(args: argparse.Namespace) -> int:
    result = run_temp_historical_replay(Path(args.temp_root))
    payload = {"summary_title": "agent-sync s2p rehearse", **result, "exit_code": 0 if result["valid"] else 7}
    return print_or_json(
        args,
        payload,
        [
            f"imported_change_units={result['imported_change_unit_count']}",
            f"exact={result['exact_byte_replay_count']}",
            f"patch={result['patch_replay_count']}",
            f"valid={result['valid']}",
        ],
    )


def cmd_s2p_apply(args: argparse.Namespace) -> int:
    _require_execute(args)
    plan = load_plan(Path(args.plan))
    approval = read_json(Path(args.approval))
    summary = plan.get("s2p_summary") or {}
    if int(summary.get("actionable_file_action_count") or 0) != 0:
        raise SyncPlannerError("nonzero_s2p_apply_requires_sync_ops_4x_machine_approval", exit_code=4)
    result = run_s2p_noop(plan, approval, Path(args.artifact_root))
    payload = {"summary_title": "agent-sync s2p apply", **result, "exit_code": 0 if result["valid"] else 7}
    return print_or_json(args, payload, [f"run_id={result['run_id']}", f"status={result['status']}", f"prod_unchanged={result['prod_unchanged']}"])


def cmd_s2p_verify(args: argparse.Namespace) -> int:
    plan = load_plan(Path(args.plan))
    result = validate_s2p_plan_contract(plan, check_target_freshness=not args.skip_target_freshness)
    prod = prod_digest_summary(plan)
    sandbox = sandbox_pointer_summary()
    payload = {"summary_title": "agent-sync s2p verify", "plan_validation": result, "prod": prod, "sandbox": sandbox, "exit_code": result["exit_code"]}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"prod_digest={prod['combined_digest']}"])


def cmd_s2p_smoke(args: argparse.Namespace) -> int:
    _require_execute(args)
    if not getattr(args, "allow_live", False):
        raise SyncPlannerError("allow_live_required_for_s2p_smoke", exit_code=2)
    result = fake_live_gate("cli_smoke", approved=False)
    payload = {"summary_title": "agent-sync s2p smoke", **result, "exit_code": 4}
    return print_or_json(args, payload, ["executed=false", "reason=live_validation_not_approved"])


def cmd_s2p_rollback(args: argparse.Namespace) -> int:
    _require_execute(args)
    recovery = recover_s2p_journal([])
    payload = {"summary_title": "agent-sync s2p rollback", "rollback_attempted": False, "recovery": recovery, "exit_code": 10}
    return print_or_json(args, payload, ["rollback_attempted=false", f"recommended_action={recovery['recommended_action']}"])


def cmd_cycle_plan(args: argparse.Namespace) -> int:
    if getattr(args, "experiment", None):
        plan = build_cycle_plan_from_experiment(read_json(Path(args.experiment)))
    else:
        if not getattr(args, "s2p_plan", None):
            raise SyncPlannerError("cycle_plan_requires_experiment_or_s2p_plan", exit_code=2)
        s2p = load_plan(Path(args.s2p_plan))
        plan = build_cycle_plan_from_s2p(s2p)
    output = ensure_output_path(args.output)
    maybe_write_json(output, plan)
    payload = {"summary_title": "agent-sync cycle plan", "plan": plan, "validation": validate_cycle_plan(plan), "exit_code": 0}
    return print_or_json(args, payload, [f"cycle_id={plan['cycle_id']}", f"s2p={plan['s2p_plan']['plan_id']}", f"p2s={plan['p2s_plan']['plan_id']}"])


def cmd_cycle_prepare(args: argparse.Namespace) -> int:
    plan = build_cycle_plan_from_experiment(read_json(Path(args.experiment)))
    approval_request = {
        "schema_version": "agent_sync_cycle_approval_request_v1",
        "status": "awaiting_machine_approval",
        "cycle_id": plan["cycle_id"],
        "cycle_plan_sha256": plan["canonical_sha256"],
        "s2p_plan_id": plan["s2p_plan"]["plan_id"],
        "s2p_plan_sha256": plan["s2p_plan"]["plan_sha256"],
        "p2s_plan_id": plan["p2s_plan"]["plan_id"],
        "p2s_plan_sha256": plan["p2s_plan"]["canonical_sha256"],
        "approval_requirements": plan["approval_requirements"],
    }
    output = ensure_output_path(args.output)
    maybe_write_json(output, {"cycle_plan": plan, "approval_request": approval_request})
    payload = {"summary_title": "agent-sync cycle prepare", "cycle_plan": plan, "approval_request": approval_request, "exit_code": 0}
    return print_or_json(args, payload, [f"cycle_id={plan['cycle_id']}", f"status={approval_request['status']}"])


def cmd_cycle_validate(args: argparse.Namespace) -> int:
    plan = read_json(Path(args.cycle_plan))
    result = validate_cycle_plan(plan)
    payload = {"summary_title": "agent-sync cycle validate", **result, "exit_code": result["exit_code"]}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"blockers={len(result['blockers'])}"])


def cmd_cycle_explain(args: argparse.Namespace) -> int:
    plan = read_json(Path(args.cycle_plan))
    payload = {
        "summary_title": "agent-sync cycle explain",
        "cycle_id": plan.get("cycle_id"),
        "cycle_sha256": plan.get("canonical_sha256"),
        "s2p_plan": plan.get("s2p_plan", {}),
        "p2s_plan": plan.get("p2s_plan", {}),
        "approval_requirements": plan.get("approval_requirements", {}),
        "state_machine": plan.get("state_machine", []),
        "exit_code": 0,
    }
    return print_or_json(args, payload, [f"cycle_id={plan.get('cycle_id')}", f"mode={plan.get('mode')}"])


def cmd_cycle_rehearse(args: argparse.Namespace) -> int:
    root = Path(args.temp_root)
    legacy = run_temp_nonzero_cycle(root / "single_transaction")
    multi = run_temp_multi_transaction_cycle(root / "multi_transaction")
    compensation = run_temp_cycle_compensation(root / "compensation")
    valid = bool(legacy["valid"] and multi["valid"] and compensation["valid"])
    payload = {
        "summary_title": "agent-sync cycle rehearse",
        "single_transaction": legacy,
        "multi_transaction": multi,
        "compensation": compensation,
        "valid": valid,
        "exit_code": 0 if valid else 7,
    }
    return print_or_json(
        args,
        payload,
        [
            f"single_s2p_actions={legacy['s2p_action_count']}",
            f"independent_transactions={multi['independent_transaction_count']}",
            f"compensation_valid={compensation['valid']}",
        ],
    )


def cmd_cycle_publish_and_rebase(args: argparse.Namespace) -> int:
    if not args.execute:
        raise SyncPlannerError("execute_required", exit_code=2)
    plan = read_json(Path(args.cycle_plan))
    approval = read_json(Path(args.approval_bundle))
    s2p_actions = int(((plan.get("s2p_plan") or {}).get("summary") or {}).get("actionable_file_action_count") or 0)
    p2s_actions = int((plan.get("p2s_plan") or {}).get("p2s_action_count") or 0)
    if s2p_actions or p2s_actions:
        raise SyncPlannerError("nonzero_cycle_execution_requires_sync_ops_5b_machine_approval", exit_code=4)
    result = run_cycle_noop(plan, approval, Path(args.artifact_root))
    payload = {"summary_title": "agent-sync cycle publish-and-rebase", **result, "exit_code": 0 if result["valid"] else 7}
    return print_or_json(args, payload, [f"cycle_run_id={result['cycle_run_id']}", f"status={result['status']}"])


def cmd_cycle_status(args: argparse.Namespace) -> int:
    run_root = Path(args.run_root)
    events_path = run_root / "journal" / "events.jsonl"
    events: list[dict[str, Any]] = []
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    recovery = recover_cycle(events)
    payload = {"summary_title": "agent-sync cycle status", "run_root": str(run_root), "event_count": len(events), "recovery": recovery, "exit_code": 0}
    return print_or_json(args, payload, [f"event_count={len(events)}", f"recommended_action={recovery['recommended_action']}"])


def cmd_cycle_recover(args: argparse.Namespace) -> int:
    run_root = Path(args.run_root)
    events_path = run_root / "journal" / "events.jsonl"
    events: list[dict[str, Any]] = []
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    recovery = recover_cycle(events)
    payload = {"summary_title": "agent-sync cycle recover", "run_root": str(run_root), "recovery": recovery, "exit_code": 0}
    return print_or_json(args, payload, [f"status={recovery['status']}", f"recommended_action={recovery['recommended_action']}"])


def cmd_cycle_close(args: argparse.Namespace) -> int:
    payload = {"summary_title": "agent-sync cycle close", "status": "closeout_idempotent", "run_root": args.run_root, "exit_code": 0}
    return print_or_json(args, payload, ["status=closeout_idempotent"])


def cmd_risk_fraud_validate_old_repair(args: argparse.Namespace) -> int:
    plan = read_json(Path(args.plan))
    result = validate_old_risk_fraud_repair_plan(plan)
    payload = {"summary_title": "agent-sync risk-fraud validate-old-repair", **result, "exit_code": 7}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"reasons={len(result['rejection_reasons'])}"])


def cmd_risk_fraud_freeze(args: argparse.Namespace) -> int:
    matrix = build_risk_fraud_source_authority_matrix()
    runtime = {
        "listener_exists": bool(args.listener_exists),
        "pid": str(args.pid or ""),
        "cwd": str(args.cwd or ""),
        "runtime_authority_unresolved": bool(args.runtime_authority_unresolved),
        "source_deleted_process_still_alive": bool(args.listener_exists),
    }
    authority = build_risk_fraud_authority_decision(matrix, runtime)
    recovery = build_risk_fraud_prod_recovery_plan(runtime_audit=runtime)
    recovery_validation = validate_risk_fraud_prod_recovery_plan(recovery)
    p2s = build_risk_fraud_p2s_rebase_plan(recovery)
    p2s_validation = validate_risk_fraud_p2s_rebase_plan(p2s)
    candidate = requalify_financial_data_service_candidate(
        patch_path=Path(args.patch),
        rollback_patch_path=Path(args.rollback_patch),
        sandbox_test_path=Path(args.sandbox_test),
    )
    projected_experiment = build_projected_experiment_contract(candidate, p2s)
    first_cycle = build_first_cycle_projection(candidate, projected_experiment)
    compound = build_final_compound_execution_plan(recovery, p2s, projected_experiment, first_cycle)
    compound_validation = validate_final_compound_execution_plan(compound)
    approval_request = build_final_compound_execution_approval_request(compound)
    payload = {
        "summary_title": "agent-sync risk-fraud freeze",
        "source_authority": authority,
        "recovery_plan": recovery,
        "recovery_validation": recovery_validation,
        "p2s_rebase_plan": p2s,
        "p2s_rebase_validation": p2s_validation,
        "candidate": candidate,
        "projected_experiment": projected_experiment,
        "first_cycle": first_cycle,
        "compound_plan": compound,
        "compound_validation": compound_validation,
        "approval_request": approval_request,
        "exit_code": 0 if recovery_validation["valid"] and p2s_validation["valid"] and compound_validation["valid"] else 7,
    }
    return print_or_json(
        args,
        payload,
        [
            f"classification={authority['classification']}",
            f"recovery_actions={recovery_validation['action_count']}",
            f"candidate_risk={candidate['risk_class']}",
            f"request_status={approval_request['status']}",
        ],
    )


def cmd_risk_fraud_freeze_source_loss(args: argparse.Namespace) -> int:
    old_recovery = read_json(Path(args.old_recovery_plan))
    old_p2s = read_json(Path(args.old_p2s_plan))
    runtime = {
        "pid": str(args.pid or ""),
        "cwd": str(args.cwd or ""),
        "exe": str(args.exe or ""),
        "argv": ["python3", "-u", "-m", "app.main"],
        "launch_authority_classification": str(args.launch_authority_classification or ""),
    }
    superseded_recovery = validate_superseded_r1x_recovery_plan(old_recovery)
    superseded_p2s = validate_superseded_r1x_p2s_projection(old_p2s)
    package = build_source_package_integrity()
    recovery = build_source_loss_recovery_plan_v2(runtime_audit=runtime, canary_port=int(args.canary_port))
    recovery_validation = validate_source_loss_recovery_plan_v2(recovery)
    p2s = build_full_p2s_rebase_plan_v2(recovery)
    p2s_validation = validate_full_p2s_rebase_plan_v2(p2s)
    candidates = reselect_first_candidate()
    selected = candidates["selected_candidate"]
    experiment = build_projected_experiment_manifest_v2(selected, p2s)
    first_cycle = build_first_real_cycle_plan_v2(selected, experiment, p2s)
    first_cycle_validation = validate_first_real_cycle_plan_v2(first_cycle)
    compound = build_final_compound_execution_plan_v2(recovery, p2s, experiment, first_cycle)
    compound_validation = validate_final_compound_execution_plan_v2(compound)
    request = build_final_compound_execution_approval_request_v2(compound, selected, first_cycle)
    payload = {
        "summary_title": "agent-sync risk-fraud freeze-source-loss",
        "superseded_recovery_plan": superseded_recovery,
        "superseded_p2s_projection_plan": superseded_p2s,
        "source_package_integrity": package,
        "source_loss_recovery_plan": recovery,
        "source_loss_recovery_validation": recovery_validation,
        "full_p2s_rebase_plan": p2s,
        "full_p2s_rebase_validation": p2s_validation,
        "candidate_reselection": candidates,
        "projected_experiment": experiment,
        "first_cycle_plan": first_cycle,
        "first_cycle_validation": first_cycle_validation,
        "compound_plan": compound,
        "compound_validation": compound_validation,
        "approval_request": request,
        "exit_code": 0
        if recovery_validation["valid"] and p2s_validation["valid"] and first_cycle_validation["valid"] and compound_validation["valid"]
        else 7,
    }
    return print_or_json(
        args,
        payload,
        [
            f"recovery_valid={recovery_validation['valid']}",
            f"launch={recovery['launch_authority']['classification']}",
            f"p2s_actions={p2s_validation['physical_action_count']}",
            f"candidate={selected['candidate_id']}",
        ],
    )


def cmd_risk_fraud_freeze_source_loss_v3(args: argparse.Namespace) -> int:
    argv = json.loads(args.argv_json) if getattr(args, "argv_json", "") else ["python3", "-u", "-m", "app.main"]
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        raise SyncPlannerError("argv_json_must_be_string_array", exit_code=2)
    provenance = build_source_package_provenance()
    provenance_validation = validate_source_package_provenance(provenance)
    launch = build_risk_fraud_launch_authority(canary_port=int(args.canary_port))
    launch_validation = validate_launch_authority(launch)
    environment = build_environment_reference_metadata()
    recovery = build_source_loss_recovery_plan_v3(
        pid=str(args.pid or ""),
        start_ticks=str(args.start_ticks or ""),
        cwd=str(args.cwd or ""),
        exe=str(args.exe or "/usr/bin/python3.14"),
        argv=argv,
        canary_port=int(args.canary_port),
    )
    recovery_validation = validate_source_loss_recovery_plan_v3(recovery)
    p2s = build_full_p2s_rebase_plan_v3(recovery)
    p2s_validation = validate_full_p2s_rebase_plan_v3(p2s)
    candidates = reselect_first_candidate()
    selected = candidates["selected_candidate"]
    experiment = build_projected_experiment_manifest_v3(selected, p2s)
    first_cycle = build_first_real_cycle_plan_v3(selected, experiment, p2s)
    first_cycle_validation = validate_first_real_cycle_plan_v3(first_cycle)
    compound = build_final_compound_execution_plan_v3(recovery, p2s, experiment, first_cycle)
    compound_validation = validate_final_compound_execution_plan_v3(compound)
    request = build_final_compound_execution_approval_request_v3(
        compound=compound,
        recovery=recovery,
        p2s=p2s,
        experiment=experiment,
        cycle=first_cycle,
        provenance=provenance,
    )
    valid = (
        provenance_validation["valid"]
        and launch_validation["valid"]
        and recovery_validation["valid"]
        and p2s_validation["valid"]
        and first_cycle_validation["valid"]
        and compound_validation["valid"]
    )
    payload = {
        "summary_title": "agent-sync risk-fraud freeze-source-loss-v3",
        "source_package_provenance": provenance,
        "source_package_provenance_validation": provenance_validation,
        "environment_reference_metadata": environment,
        "launch_authority": launch,
        "launch_authority_validation": launch_validation,
        "source_loss_recovery_plan_v3": recovery,
        "source_loss_recovery_plan_v3_validation": recovery_validation,
        "full_p2s_rebase_plan_v3": p2s,
        "full_p2s_rebase_plan_v3_validation": p2s_validation,
        "candidate_reselection": candidates,
        "projected_experiment_manifest_v3": experiment,
        "first_real_cycle_plan_v3": first_cycle,
        "first_real_cycle_plan_v3_validation": first_cycle_validation,
        "final_compound_execution_plan_v3": compound,
        "final_compound_execution_plan_v3_validation": compound_validation,
        "final_compound_execution_approval_request_v3": request,
        "exit_code": 0 if valid else 7,
    }
    return print_or_json(
        args,
        payload,
        [
            f"provenance_resolved={provenance_validation['resolved_count']}",
            f"launch_valid={launch_validation['valid']}",
            f"recovery_valid={recovery_validation['valid']}",
            f"request_status={request['status']}",
        ],
    )


def cmd_risk_fraud_freeze_source_loss_v4(args: argparse.Namespace) -> int:
    runtime_identity = {
        "pid": str(args.pid or ""),
        "start_ticks": str(args.start_ticks or ""),
        "cwd": str(args.cwd or ""),
        "exe": str(args.exe or "/usr/bin/python3.14"),
        "argv": json.loads(args.argv_json) if getattr(args, "argv_json", "") else ["python3", "-u", "-m", "app.main"],
    }
    if not isinstance(runtime_identity["argv"], list) or not all(isinstance(item, str) for item in runtime_identity["argv"]):
        raise SyncPlannerError("argv_json_must_be_string_array", exit_code=2)
    matrix = build_runtime_variable_matrix()
    matrix_validation = validate_runtime_variable_matrix(matrix)
    profile = build_environment_profile_v1(variable_matrix=matrix, canary_port=int(args.canary_port))
    profile_validation = validate_environment_profile_v1(profile)
    equivalence = build_equivalence_contract_v1()
    equivalence_validation = validate_equivalence_contract_v1(equivalence)
    plan = build_precutover_canary_plan_v1(
        final_head=str(args.final_head or ""),
        runtime_identity=runtime_identity,
        canary_port=int(args.canary_port),
    )
    plan_validation = validate_precutover_canary_plan_v1(plan)
    approval = build_machine_precutover_canary_approval(plan)
    approval_validation = validate_machine_precutover_canary_approval(approval, plan)
    fake_closeout = {
        "canonical_sha256": canonical_sha256({"plan": plan["canonical_sha256"], "status": "cli_projection_only"}),
        "candidate_path": plan["candidate_path"],
        "candidate_descriptor": plan["candidate_descriptor"],
        "source_provenance_sha256": plan["source_provenance_sha256"],
        "environment_profile_sha256": plan["environment_profile_sha256"],
        "equivalence_result_sha256": equivalence["canonical_sha256"],
        "incumbent_capture_sha256": equivalence["fixture_sha256"],
        "port_release_proof": {"port": int(args.canary_port), "released": True},
        "runtime_artifact_policy": plan["runtime_artifact_policy"],
    }
    recovery = build_source_loss_recovery_plan_v4(precutover_closeout=fake_closeout, runtime_identity=runtime_identity)
    recovery_validation = validate_source_loss_recovery_plan_v4(recovery)
    p2s = build_full_p2s_rebase_plan_v4(recovery)
    p2s_validation = validate_full_p2s_rebase_plan_v4(p2s)
    selected = reselect_first_candidate()["selected_candidate"]
    experiment = build_projected_experiment_v4(selected, p2s)
    cycle = build_first_real_cycle_plan_v4(selected, experiment, p2s)
    chain = build_conditional_approval_chain_v1(
        canary_closeout=fake_closeout,
        recovery_v4=recovery,
        p2s_v4=p2s,
        experiment_v4=experiment,
        cycle_v4=cycle,
    )
    chain_validation = validate_conditional_approval_chain_v1(chain)
    valid = all(
        item["valid"]
        for item in (
            matrix_validation,
            profile_validation,
            equivalence_validation,
            plan_validation,
            approval_validation,
            recovery_validation,
            p2s_validation,
            chain_validation,
        )
    )
    payload = {
        "summary_title": "agent-sync risk-fraud freeze-source-loss-v4",
        "runtime_variable_matrix": matrix,
        "runtime_variable_matrix_validation": matrix_validation,
        "environment_profile_v1": profile,
        "environment_profile_validation": profile_validation,
        "equivalence_contract": equivalence,
        "equivalence_contract_validation": equivalence_validation,
        "precutover_canary_plan": plan,
        "precutover_canary_plan_validation": plan_validation,
        "machine_precutover_canary_approval": approval,
        "precutover_canary_approval_validation": approval_validation,
        "source_loss_recovery_plan_v4": recovery,
        "source_loss_recovery_plan_v4_validation": recovery_validation,
        "full_p2s_rebase_plan_v4": p2s,
        "full_p2s_rebase_plan_v4_validation": p2s_validation,
        "projected_experiment_v4": experiment,
        "first_real_cycle_plan_v4": cycle,
        "conditional_approval_chain_v1": chain,
        "conditional_approval_chain_validation": chain_validation,
        "exit_code": 0 if valid else 7,
    }
    return print_or_json(
        args,
        payload,
        [
            f"plan_id={plan['plan_id']}",
            f"plan_valid={plan_validation['valid']}",
            f"approval_valid={approval_validation['valid']}",
            f"chain_valid={chain_validation['valid']}",
        ],
    )
def _load_launch_authority_from_plan(plan_path: str) -> dict[str, Any]:
    payload = read_json(Path(plan_path))
    if "launch_authority" in payload and isinstance(payload["launch_authority"], dict):
        return dict(payload["launch_authority"])
    if payload.get("schema_version") == "agent_sync_launch_authority_v1":
        return dict(payload)
    raise SyncPlannerError("launch_authority_not_found_in_plan", exit_code=7)


def _validate_process_approval(path_text: str) -> dict[str, Any]:
    approval = read_json(Path(path_text))
    if approval.get("status") != "approved":
        raise SyncPlannerError("process_machine_approval_required", exit_code=4)
    return dict(approval)


def cmd_process_preflight(args: argparse.Namespace) -> int:
    authority = _load_launch_authority_from_plan(args.plan)
    result = preflight_launch_authority(authority)
    payload = {"summary_title": "agent-sync process preflight", **result, "exit_code": 0 if result["valid"] else 7}
    return print_or_json(args, payload, [f"valid={result['valid']}", f"blockers={len(result['blockers'])}"])


def cmd_process_start(args: argparse.Namespace) -> int:
    authority = _load_launch_authority_from_plan(args.plan)
    _validate_process_approval(args.approval)
    overrides: dict[str, str] = {}
    if args.host:
        overrides["APP_HOST"] = str(args.host)
    if args.port:
        overrides["APP_PORT"] = str(args.port)
    if args.python_unbuffered:
        overrides["PYTHONUNBUFFERED"] = "1"
    if args.python_dont_write_bytecode:
        overrides["PYTHONDONTWRITEBYTECODE"] = "1"
    result = start_supervised_process(
        authority,
        state_path=Path(args.state) if args.state else None,
        environment_overrides=overrides or None,
        execute=bool(args.execute),
    )
    payload = {"summary_title": "agent-sync process start", **result, "exit_code": 0 if result.get("started") else 7}
    return print_or_json(args, payload, [f"started={result.get('started')}", f"pid={result.get('pid', '')}"])


def cmd_process_status(args: argparse.Namespace) -> int:
    authority = _load_launch_authority_from_plan(args.plan)
    result = status_supervised_process(authority, state_path=Path(args.state))
    valid = bool(result["identity_match"] and result.get("authority_binding_match"))
    payload = {"summary_title": "agent-sync process status", **result, "exit_code": 0 if valid else 7}
    return print_or_json(
        args,
        payload,
        [
            f"running={result['running']}",
            f"identity_match={result['identity_match']}",
            f"authority_binding_match={result.get('authority_binding_match')}",
        ],
    )


def cmd_process_stop(args: argparse.Namespace) -> int:
    authority = _load_launch_authority_from_plan(args.plan)
    _validate_process_approval(args.approval)
    result = stop_supervised_process(
        authority,
        state_path=Path(args.state),
        execute=bool(args.execute),
        port=int(args.port) if args.port else None,
    )
    payload = {"summary_title": "agent-sync process stop", **result, "exit_code": 0 if result.get("stopped") else 7}
    return print_or_json(args, payload, [f"stopped={result.get('stopped')}", f"reason={result.get('reason', '')}"])


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


def _environment_binding_payload(plan: dict[str, Any]) -> dict[str, Any]:
    environment = build_bootstrap_environment_snapshot(plan)
    contract = validate_bootstrap_environment_contract(plan, environment)
    binding = environment.get("approval_binding") or {}
    constraints = environment.get("execution_constraints") or {}
    observations = environment.get("observations") or {}
    return {
        "summary_title": "agent-sync environment binding",
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("canonical_sha256"),
        "environment_contract_version": environment.get("schema_version"),
        "environment_binding_sha256": environment.get("environment_binding_sha256"),
        "access_basis": binding.get("access_basis"),
        "exact_bound_fields": sorted(binding.keys()) if isinstance(binding, dict) else [],
        "constraint_fields": sorted(constraints.keys()) if isinstance(constraints, dict) else [],
        "diagnostic_only_fields": sorted(observations.keys()) if isinstance(observations, dict) else [],
        "minimum_free_bytes": constraints.get("minimum_free_bytes") if isinstance(constraints, dict) else None,
        "current_free_bytes": observations.get("current_free_bytes") if isinstance(observations, dict) else None,
        "environment": environment,
        "validation": contract,
        "exit_code": contract["exit_code"],
    }


def cmd_environment_explain_binding(args: argparse.Namespace) -> int:
    plan = read_json(Path(args.plan))
    if not isinstance(plan, dict):
        raise SyncPlannerError("bootstrap_plan_not_object", exit_code=2)
    payload = _environment_binding_payload(plan)
    rows = [
        f"contract={payload['environment_contract_version']}",
        f"binding_sha={payload['environment_binding_sha256']}",
        f"access_basis={payload['access_basis']}",
        f"minimum_free_bytes={payload['minimum_free_bytes']}",
        f"current_free_bytes={payload['current_free_bytes']}",
    ]
    return print_or_json(args, payload, rows)


def cmd_environment_validate(args: argparse.Namespace) -> int:
    plan = read_json(Path(args.plan))
    if not isinstance(plan, dict):
        raise SyncPlannerError("bootstrap_plan_not_object", exit_code=2)
    payload = _environment_binding_payload(plan)
    rows = [
        f"valid={payload['validation']['valid']}",
        f"blockers={len(payload['validation']['blockers'])}",
        f"diagnostics={len(payload['validation']['diagnostics'])}",
    ]
    return print_or_json(args, payload, rows)


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
    experiment_fork = experiment_sub.add_parser("fork")
    experiment_fork.add_argument("--workspace-root", required=True)
    experiment_fork.add_argument("--experiment-id")
    experiment_fork.add_argument("--output")
    _add_output_args(experiment_fork)
    experiment_fork.set_defaults(func=cmd_experiment_fork)
    experiment_show = experiment_sub.add_parser("show")
    experiment_show.add_argument("--manifest", required=True)
    _add_output_args(experiment_show)
    experiment_show.set_defaults(func=cmd_experiment_show)
    experiment_diff = experiment_sub.add_parser("diff")
    experiment_diff.add_argument("--manifest", required=True)
    _add_output_args(experiment_diff)
    experiment_diff.set_defaults(func=cmd_experiment_diff)
    experiment_close = experiment_sub.add_parser("close")
    experiment_close.add_argument("--manifest", required=True)
    experiment_close.add_argument("--reason", required=True)
    _add_output_args(experiment_close)
    experiment_close.set_defaults(func=cmd_experiment_close)

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
    s2p_validate = s2p_sub.add_parser("validate")
    s2p_validate.add_argument("--plan", required=True)
    s2p_validate.add_argument("--skip-target-freshness", action="store_true")
    _add_output_args(s2p_validate)
    s2p_validate.set_defaults(func=cmd_s2p_validate)
    s2p_explain = s2p_sub.add_parser("explain")
    s2p_explain.add_argument("--plan", required=True)
    _add_output_args(s2p_explain)
    s2p_explain.set_defaults(func=cmd_s2p_explain)
    s2p_rehearse = s2p_sub.add_parser("rehearse")
    s2p_rehearse.add_argument("--plan")
    s2p_rehearse.add_argument("--temp-root", required=True)
    _add_output_args(s2p_rehearse)
    s2p_rehearse.set_defaults(func=cmd_s2p_rehearse)
    s2p_apply = s2p_sub.add_parser("apply")
    s2p_apply.add_argument("--plan", required=True)
    s2p_apply.add_argument("--approval", required=True)
    s2p_apply.add_argument("--artifact-root", required=True)
    s2p_apply.add_argument("--execute", action="store_true")
    s2p_apply.add_argument("--allow-process-action", action="store_true")
    s2p_apply.add_argument("--allow-live", action="store_true")
    s2p_apply.add_argument("--allow-delete", action="store_true")
    _add_output_args(s2p_apply)
    s2p_apply.set_defaults(func=cmd_s2p_apply)
    s2p_verify = s2p_sub.add_parser("verify")
    s2p_verify.add_argument("--plan", required=True)
    s2p_verify.add_argument("--skip-target-freshness", action="store_true")
    _add_output_args(s2p_verify)
    s2p_verify.set_defaults(func=cmd_s2p_verify)
    s2p_smoke = s2p_sub.add_parser("smoke")
    s2p_smoke.add_argument("--plan", required=True)
    s2p_smoke.add_argument("--approval", required=True)
    s2p_smoke.add_argument("--execute", action="store_true")
    s2p_smoke.add_argument("--allow-live", action="store_true")
    _add_output_args(s2p_smoke)
    s2p_smoke.set_defaults(func=cmd_s2p_smoke)
    s2p_rollback = s2p_sub.add_parser("rollback")
    s2p_rollback.add_argument("--plan", required=True)
    s2p_rollback.add_argument("--approval", required=True)
    s2p_rollback.add_argument("--execute", action="store_true")
    _add_output_args(s2p_rollback)
    s2p_rollback.set_defaults(func=cmd_s2p_rollback)

    cycle = subparsers.add_parser("cycle")
    cycle_sub = cycle.add_subparsers(dest="command", required=True)
    cycle_prepare = cycle_sub.add_parser("prepare")
    cycle_prepare.add_argument("--experiment", required=True)
    cycle_prepare.add_argument("--output")
    _add_output_args(cycle_prepare)
    cycle_prepare.set_defaults(func=cmd_cycle_prepare)
    cycle_plan = cycle_sub.add_parser("plan")
    cycle_plan.add_argument("--s2p-plan")
    cycle_plan.add_argument("--experiment")
    cycle_plan.add_argument("--output")
    _add_output_args(cycle_plan)
    cycle_plan.set_defaults(func=cmd_cycle_plan)
    cycle_validate = cycle_sub.add_parser("validate")
    cycle_validate.add_argument("--cycle-plan", required=True)
    _add_output_args(cycle_validate)
    cycle_validate.set_defaults(func=cmd_cycle_validate)
    cycle_explain = cycle_sub.add_parser("explain")
    cycle_explain.add_argument("--cycle-plan", required=True)
    _add_output_args(cycle_explain)
    cycle_explain.set_defaults(func=cmd_cycle_explain)
    cycle_rehearse = cycle_sub.add_parser("rehearse")
    cycle_rehearse.add_argument("--temp-root", required=True)
    _add_output_args(cycle_rehearse)
    cycle_rehearse.set_defaults(func=cmd_cycle_rehearse)
    publish = cycle_sub.add_parser("publish-and-rebase")
    publish.add_argument("--cycle-plan", required=True)
    publish.add_argument("--approval-bundle", required=True)
    publish.add_argument("--artifact-root", default="/sdb/dlut/ops-artifacts/agent-sync")
    publish.add_argument("--execute", action="store_true")
    _add_output_args(publish)
    publish.set_defaults(func=cmd_cycle_publish_and_rebase)
    cycle_status = cycle_sub.add_parser("status")
    cycle_status.add_argument("--run-root", required=True)
    _add_output_args(cycle_status)
    cycle_status.set_defaults(func=cmd_cycle_status)
    cycle_recover = cycle_sub.add_parser("recover")
    cycle_recover.add_argument("--run-root", required=True)
    _add_output_args(cycle_recover)
    cycle_recover.set_defaults(func=cmd_cycle_recover)
    cycle_close = cycle_sub.add_parser("close")
    cycle_close.add_argument("--run-root", required=True)
    _add_output_args(cycle_close)
    cycle_close.set_defaults(func=cmd_cycle_close)

    risk_fraud = subparsers.add_parser("risk-fraud")
    risk_fraud_sub = risk_fraud.add_subparsers(dest="command", required=True)
    risk_old = risk_fraud_sub.add_parser("validate-old-repair")
    risk_old.add_argument("--plan", required=True)
    _add_output_args(risk_old)
    risk_old.set_defaults(func=cmd_risk_fraud_validate_old_repair)
    risk_freeze = risk_fraud_sub.add_parser("freeze")
    risk_freeze.add_argument("--patch", required=True)
    risk_freeze.add_argument("--rollback-patch", required=True)
    risk_freeze.add_argument("--sandbox-test", required=True)
    risk_freeze.add_argument("--listener-exists", action="store_true")
    risk_freeze.add_argument("--runtime-authority-unresolved", action="store_true")
    risk_freeze.add_argument("--pid", default="")
    risk_freeze.add_argument("--cwd", default="")
    _add_output_args(risk_freeze)
    risk_freeze.set_defaults(func=cmd_risk_fraud_freeze)
    risk_source_loss = risk_fraud_sub.add_parser("freeze-source-loss")
    risk_source_loss.add_argument("--old-recovery-plan", required=True)
    risk_source_loss.add_argument("--old-p2s-plan", required=True)
    risk_source_loss.add_argument("--pid", default="")
    risk_source_loss.add_argument("--cwd", default="")
    risk_source_loss.add_argument("--exe", default="/usr/bin/python3.14")
    risk_source_loss.add_argument("--canary-port", default="11013")
    risk_source_loss.add_argument("--launch-authority-classification", default="")
    _add_output_args(risk_source_loss)
    risk_source_loss.set_defaults(func=cmd_risk_fraud_freeze_source_loss)
    risk_source_loss_v3 = risk_fraud_sub.add_parser("freeze-source-loss-v3")
    risk_source_loss_v3.add_argument("--pid", default="")
    risk_source_loss_v3.add_argument("--start-ticks", default="")
    risk_source_loss_v3.add_argument("--cwd", default="")
    risk_source_loss_v3.add_argument("--exe", default="/usr/bin/python3.14")
    risk_source_loss_v3.add_argument("--argv-json", default="")
    risk_source_loss_v3.add_argument("--canary-port", default="11013")
    _add_output_args(risk_source_loss_v3)
    risk_source_loss_v3.set_defaults(func=cmd_risk_fraud_freeze_source_loss_v3)
    risk_source_loss_v4 = risk_fraud_sub.add_parser("freeze-source-loss-v4")
    risk_source_loss_v4.add_argument("--final-head", required=True)
    risk_source_loss_v4.add_argument("--pid", default="")
    risk_source_loss_v4.add_argument("--start-ticks", default="")
    risk_source_loss_v4.add_argument("--cwd", default="")
    risk_source_loss_v4.add_argument("--exe", default="/usr/bin/python3.14")
    risk_source_loss_v4.add_argument("--argv-json", default="")
    risk_source_loss_v4.add_argument("--canary-port", default="11013")
    _add_output_args(risk_source_loss_v4)
    risk_source_loss_v4.set_defaults(func=cmd_risk_fraud_freeze_source_loss_v4)

    process = subparsers.add_parser("process")
    process_sub = process.add_subparsers(dest="command", required=True)
    process_preflight = process_sub.add_parser("preflight")
    process_preflight.add_argument("--plan", required=True)
    _add_output_args(process_preflight)
    process_preflight.set_defaults(func=cmd_process_preflight)
    process_start = process_sub.add_parser("start")
    process_start.add_argument("--plan", required=True)
    process_start.add_argument("--approval", required=True)
    process_start.add_argument("--state", default="")
    process_start.add_argument("--host", default="")
    process_start.add_argument("--port", default="")
    process_start.add_argument("--python-unbuffered", action="store_true")
    process_start.add_argument("--python-dont-write-bytecode", action="store_true")
    process_start.add_argument("--execute", action="store_true")
    _add_output_args(process_start)
    process_start.set_defaults(func=cmd_process_start)
    process_status = process_sub.add_parser("status")
    process_status.add_argument("--plan", required=True)
    process_status.add_argument("--state", required=True)
    _add_output_args(process_status)
    process_status.set_defaults(func=cmd_process_status)
    process_stop = process_sub.add_parser("stop")
    process_stop.add_argument("--plan", required=True)
    process_stop.add_argument("--approval", required=True)
    process_stop.add_argument("--state", required=True)
    process_stop.add_argument("--port", default="")
    process_stop.add_argument("--execute", action="store_true")
    _add_output_args(process_stop)
    process_stop.set_defaults(func=cmd_process_stop)

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

    environment = subparsers.add_parser("environment")
    environment_sub = environment.add_subparsers(dest="command", required=True)
    environment_explain = environment_sub.add_parser("explain-binding")
    environment_explain.add_argument("--plan", required=True)
    _add_output_args(environment_explain)
    environment_explain.set_defaults(func=cmd_environment_explain_binding)
    environment_validate = environment_sub.add_parser("validate")
    environment_validate.add_argument("--plan", required=True)
    _add_output_args(environment_validate)
    environment_validate.set_defaults(func=cmd_environment_validate)

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
