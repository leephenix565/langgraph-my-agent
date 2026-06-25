"""SYNC-OPS-5A-R3X launch-authority and provenance tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from react_agent.ops.sync_5a_r2x import reselect_first_candidate
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
from react_agent.ops.sync_contracts import validate_by_schema_version, write_json
from react_agent.ops.sync_process_launcher import (
    build_supervised_launcher_authority,
    read_process_state,
    start_supervised_process,
    status_supervised_process,
    stop_supervised_process,
    validate_launch_authority,
)


def _runtime() -> dict[str, object]:
    return {
        "pid": "740899",
        "start_ticks": "12455435",
        "cwd": "/sdb/dlut/prod/财务造假风险智能体",
        "exe": "/usr/bin/python3.14",
        "argv": ["python3", "-u", "-m", "app.main"],
    }


def test_source_package_provenance_resolves_all_67_files() -> None:
    provenance = build_source_package_provenance()
    validation = validate_source_package_provenance(provenance)
    assert validation["valid"] is True
    assert validation["resolved_count"] == 67
    assert validation["unresolved_count"] == 0
    assert validation["baseline_manifest_provenance_count"] == 67
    assert validation["accepted_direct_lineage_count"] == 3
    assert provenance["classification_counts"].get("historical_baseline_only", 0) == 0
    validate_by_schema_version(provenance)


def test_manual_exact_argv_is_not_approved_launch_authority() -> None:
    authority = build_risk_fraud_launch_authority()
    assert validate_launch_authority(authority)["valid"] is True
    manual = dict(authority)
    manual["authority_kind"] = "manual_exact_argv"
    manual["canonical_sha256"] = ""
    from react_agent.ops.sync_contracts import canonical_sha256

    manual["canonical_sha256"] = canonical_sha256(manual)
    result = validate_launch_authority(manual)
    assert result["valid"] is False
    assert "manual_exact_argv_is_not_launch_authority" in result["blockers"]
    validate_by_schema_version(authority)


def test_supervised_launcher_temp_start_status_stop(tmp_path: Path) -> None:
    script = tmp_path / "fake_service.py"
    script.write_text(
        "import signal, time\n"
        "running=True\n"
        "def stop(signum, frame):\n"
        "    global running\n"
        "    running=False\n"
        "signal.signal(signal.SIGTERM, stop)\n"
        "while running:\n"
        "    time.sleep(0.05)\n",
        encoding="utf-8",
    )
    authority = build_supervised_launcher_authority(
        service_unit_id="fake",
        executable=sys.executable,
        argv=[sys.executable, str(script)],
        cwd=str(tmp_path),
        log_dir=str(tmp_path / "logs"),
        state_dir=str(tmp_path / "state"),
        allowed_port_overrides=[11013],
        allowed_executable_roots=[str(Path(sys.executable).resolve().parents[1]), "/usr/bin", "/sdb/dlut"],
        allowed_cwd_roots=[str(tmp_path)],
    )
    assert validate_launch_authority(authority)["valid"] is True
    state_path = tmp_path / "state.json"
    start = start_supervised_process(authority, state_path=state_path, execute=True)
    assert start["started"] is True
    assert state_path.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "logs" / "stdout.log").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "logs" / "stderr.log").stat().st_mode & 0o777 == 0o600
    status = status_supervised_process(authority, state_path=state_path)
    assert status["running"] is True
    assert status["identity_match"] is True
    assert status["authority_binding_match"] is True
    stop = stop_supervised_process(authority, state_path=state_path, execute=True)
    assert stop["stopped"] is True
    assert stop["sigkill_used"] is False


def test_supervised_launcher_rejects_unapproved_port_and_swapped_state(tmp_path: Path) -> None:
    script = tmp_path / "fake_service.py"
    script.write_text("import time\nwhile True:\n    time.sleep(0.1)\n", encoding="utf-8")
    authority = build_supervised_launcher_authority(
        service_unit_id="fake",
        executable=sys.executable,
        argv=[sys.executable, str(script)],
        cwd=str(tmp_path),
        log_dir=str(tmp_path / "logs"),
        state_dir=str(tmp_path / "state"),
        allowed_port_overrides=[11013],
        allowed_executable_roots=[str(Path(sys.executable).resolve().parents[1]), "/usr/bin", "/sdb/dlut"],
        allowed_cwd_roots=[str(tmp_path)],
    )
    rejected = start_supervised_process(
        authority,
        state_path=tmp_path / "bad-state.json",
        environment_overrides={"APP_PORT": "11014"},
        execute=True,
    )
    assert rejected["started"] is False
    assert "unapproved_port_override" in rejected["blockers"]

    state_path = tmp_path / "state.json"
    start = start_supervised_process(authority, state_path=state_path, execute=True)
    assert start["started"] is True
    try:
        swapped = read_process_state(state_path)
        swapped["authority_id"] = "launch_authority_swapped"
        swapped["authority_sha256"] = "0" * 64
        write_json(state_path, swapped)
        status = status_supervised_process(authority, state_path=state_path)
        assert status["identity_match"] is True
        assert status["authority_binding_match"] is False
        stopped = stop_supervised_process(authority, state_path=state_path, execute=True)
        assert stopped["stopped"] is False
        assert stopped["manual_intervention_required"] is True
    finally:
        os.kill(int(start["pid"]), 15)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                waited, _status = os.waitpid(int(start["pid"]), os.WNOHANG)
                if waited == int(start["pid"]):
                    break
            except ChildProcessError:
                break
            time.sleep(0.05)


def test_process_cli_temp_start_status_stop(tmp_path: Path) -> None:
    script = tmp_path / "fake_cli_service.py"
    script.write_text(
        "import signal, time\n"
        "running=True\n"
        "def stop(signum, frame):\n"
        "    global running\n"
        "    running=False\n"
        "signal.signal(signal.SIGTERM, stop)\n"
        "while running:\n"
        "    time.sleep(0.05)\n",
        encoding="utf-8",
    )
    authority = build_supervised_launcher_authority(
        service_unit_id="fake_cli",
        executable=sys.executable,
        argv=[sys.executable, str(script)],
        cwd=str(tmp_path),
        log_dir=str(tmp_path / "logs"),
        state_dir=str(tmp_path / "state"),
        allowed_port_overrides=[11013],
        allowed_executable_roots=[str(Path(sys.executable).resolve().parents[1]), "/usr/bin", "/sdb/dlut"],
        allowed_cwd_roots=[str(tmp_path)],
    )
    plan_path = tmp_path / "plan.json"
    approval_path = tmp_path / "approval.json"
    state_path = tmp_path / "state.json"
    write_json(plan_path, authority)
    write_json(approval_path, {"status": "approved"})
    root = Path(__file__).resolve().parents[3]

    preflight = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "process",
            "preflight",
            "--plan",
            str(plan_path),
            "--stdout-json",
        ],
        check=False,
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert preflight.returncode == 0, preflight.stderr
    start = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "process",
            "start",
            "--plan",
            str(plan_path),
            "--approval",
            str(approval_path),
            "--state",
            str(state_path),
            "--port",
            "11013",
            "--execute",
            "--stdout-json",
        ],
        check=False,
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert start.returncode == 0, start.stderr
    try:
        status = subprocess.run(
            [
                sys.executable,
                "scripts/ops/agent_syncctl.py",
                "process",
                "status",
                "--plan",
                str(plan_path),
                "--state",
                str(state_path),
                "--stdout-json",
            ],
            check=False,
            cwd=root,
            capture_output=True,
            text=True,
        )
        assert status.returncode == 0, status.stderr
        payload = json.loads(status.stdout)
        assert payload["identity_match"] is True
        assert payload["authority_binding_match"] is True
    finally:
        stop = subprocess.run(
            [
                sys.executable,
                "scripts/ops/agent_syncctl.py",
                "process",
                "stop",
                "--plan",
                str(plan_path),
                "--approval",
                str(approval_path),
                "--state",
                str(state_path),
                "--execute",
                "--stdout-json",
            ],
            check=False,
            cwd=root,
            capture_output=True,
            text=True,
        )
        assert stop.returncode == 0, stop.stderr


def test_source_loss_recovery_v3_is_valid_and_binds_launcher_and_provenance() -> None:
    runtime = _runtime()
    plan = build_source_loss_recovery_plan_v3(
        pid=str(runtime["pid"]),
        start_ticks=str(runtime["start_ticks"]),
        cwd=str(runtime["cwd"]),
        exe=str(runtime["exe"]),
        argv=["python3", "-u", "-m", "app.main"],
    )
    validation = validate_source_loss_recovery_plan_v3(plan)
    assert validation["valid"] is True
    assert validation["action_count"] == 67
    assert validation["provenance_resolved_count"] == 67
    assert plan["incident"]["previous_runtime_restore_supported"] is False
    assert plan["requested_permissions"]["sigkill"] is False
    assert all("target_path" not in action for action in plan["file_actions"])
    assert "<" not in json.dumps(plan, ensure_ascii=False)
    assert ">" not in json.dumps(plan, ensure_ascii=False)
    validate_by_schema_version(plan)


def test_full_p2s_v3_and_compound_request_are_awaiting_approval() -> None:
    runtime = _runtime()
    recovery = build_source_loss_recovery_plan_v3(
        pid=str(runtime["pid"]),
        start_ticks=str(runtime["start_ticks"]),
        cwd=str(runtime["cwd"]),
        exe=str(runtime["exe"]),
        argv=["python3", "-u", "-m", "app.main"],
    )
    p2s = build_full_p2s_rebase_plan_v3(recovery)
    p2s_validation = validate_full_p2s_rebase_plan_v3(p2s)
    selected = reselect_first_candidate()["selected_candidate"]
    experiment = build_projected_experiment_manifest_v3(selected, p2s)
    cycle = build_first_real_cycle_plan_v3(selected, experiment, p2s)
    compound = build_final_compound_execution_plan_v3(recovery, p2s, experiment, cycle)
    request = build_final_compound_execution_approval_request_v3(
        compound=compound,
        recovery=recovery,
        p2s=p2s,
        experiment=experiment,
        cycle=cycle,
        provenance=build_source_package_provenance(),
    )
    assert p2s_validation["valid"] is True
    assert p2s_validation["physical_action_count"] > 67
    assert p2s["stage_approval_request"]["activate_requested"] is False
    assert validate_first_real_cycle_plan_v3(cycle)["valid"] is True
    assert validate_final_compound_execution_plan_v3(compound)["valid"] is True
    assert request["status"] == "awaiting_machine_approval"
    assert request["approval_id"] == ""
    assert request["approved_at"] == ""
    assert request["requested_permissions"]["irreversible_source_loss_cutover_acknowledged"] is True
    assert request["requested_permissions"]["first_cycle_process"] is False
    assert request["requested_permissions"]["first_cycle_live"] is False
    validate_by_schema_version(build_environment_reference_metadata())
    validate_by_schema_version(p2s)
    validate_by_schema_version(experiment)
    validate_by_schema_version(cycle)
    validate_by_schema_version(compound)
    validate_by_schema_version(request)


def test_risk_fraud_v3_cli_generates_awaiting_request() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ops/agent_syncctl.py",
            "risk-fraud",
            "freeze-source-loss-v3",
            "--pid",
            "740899",
            "--start-ticks",
            "12455435",
            "--cwd",
            "/sdb/dlut/prod/财务造假风险智能体",
            "--exe",
            "/usr/bin/python3.14",
            "--argv-json",
            '["python3", "-u", "-m", "app.main"]',
            "--stdout-json",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["source_package_provenance_validation"]["resolved_count"] == 67
    assert payload["source_loss_recovery_plan_v3_validation"]["valid"] is True
    assert payload["final_compound_execution_approval_request_v3"]["status"] == "awaiting_machine_approval"
