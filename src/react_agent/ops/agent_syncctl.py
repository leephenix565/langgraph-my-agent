# ruff: noqa: D103
"""Read-only CLI for bidirectional external-agent sync planning."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

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
from react_agent.ops.sync_diff import diff_inventory
from react_agent.ops.sync_inventory import build_runtime_inventory
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
    payload["summary_title"] = "agent-sync inventory"
    payload["exit_code"] = 0
    rows = [
        f"agents={payload['agent_count']}",
        f"fatal_conflicts={payload['fatal_conflict_count']}",
        f"review_warnings={payload['review_warning_count']}",
    ]
    return print_or_json(args, payload, rows)


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
    return print_or_json(args, payload, [f"plan_id={plan['plan_id']}", f"actions={action_count}", f"blocked={blocked_count}"])


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
    return print_or_json(args, payload, [f"plan_id={plan.get('plan_id')}", f"direction={plan.get('direction')}"])


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


def cmd_unsupported(group: str, command: str) -> int:
    payload = {
        "schema_version": "agent_sync_cli_error_v1",
        "reason": "command_not_available_in_sync_ops_1",
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
    for unsupported in ("stage", "activate", "rollback"):
        parser_unsupported = p2s_sub.add_parser(unsupported)
        parser_unsupported.set_defaults(func=lambda _args, cmd=unsupported: cmd_unsupported("p2s", cmd))

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
    plan_validate = plan_sub.add_parser("validate")
    plan_validate.add_argument("--plan", required=True)
    plan_validate.add_argument("--skip-target-freshness", action="store_true")
    _add_output_args(plan_validate)
    plan_validate.set_defaults(func=cmd_plan_validate)
    plan_diff = plan_sub.add_parser("diff")
    _add_output_args(plan_diff)
    plan_diff.set_defaults(func=cmd_plan_diff)

    lock = subparsers.add_parser("lock")
    lock_sub = lock.add_subparsers(dest="command", required=True)
    lock_show = lock_sub.add_parser("show")
    _add_output_args(lock_show)
    lock_show.set_defaults(
        func=lambda args: print_or_json(
            args,
            {
                "summary_title": "agent-sync lock show",
                "locks": [],
                "note": "SYNC-OPS-1 does not acquire or persist locks",
                "exit_code": 0,
            },
            ["locks=0", "read_only=true"],
        )
    )
    force = lock_sub.add_parser("force-release")
    force.set_defaults(func=lambda _args: cmd_unsupported("lock", "force-release"))

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
