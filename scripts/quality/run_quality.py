#!/usr/bin/env python
"""Repo-level quality runner for the fixed-DAG reset branch."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import Iterable, Mapping


def _maybe_reexec_into_conda() -> None:
    if os.environ.get("REACT_AGENT_QUALITY_REEXEC") == "1":
        return
    if sys.version_info >= (3, 11):
        return
    conda = shutil.which("conda")
    if not conda:
        return
    env_name = os.environ.get("REACT_AGENT_CONDA_ENV", "cline_env")
    result = subprocess.run(
        [
            conda,
            "run",
            "--no-capture-output",
            "-n",
            env_name,
            "python",
            __file__,
            *sys.argv[1:],
        ],
        env={**os.environ, "REACT_AGENT_QUALITY_REEXEC": "1"},
        check=False,
    )
    raise SystemExit(result.returncode)


_maybe_reexec_into_conda()


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
FUSION_OUT_DIR = REPO_ROOT / "ops" / "regression" / "fusion" / "out"
STATIC_RUFF_TARGETS = (
    "scripts/quality",
    "src/react_agent/agent_types.py",
    "src/react_agent/context.py",
    "src/react_agent/fixed_dag_catalog.py",
    "src/react_agent/fixed_dag_contracts.py",
    "src/react_agent/fixed_dag_executor.py",
    "src/react_agent/fixed_dag_l3_explanation_synthesizer.py",
    "src/react_agent/fixed_dag_non_l4_runtime_registry.py",
    "src/react_agent/fixed_dag_production_external_compute.py",
    "src/react_agent/fixed_dag_report_synthesizer.py",
    "src/react_agent/fixed_dag_runtime_registry.py",
    "src/react_agent/graph.py",
    "src/react_agent/ops/agent_syncctl.py",
    "src/react_agent/ops/sync_5a_r1x.py",
    "src/react_agent/ops/sync_5a_r2x.py",
    "src/react_agent/ops/sync_5a_r3x.py",
    "src/react_agent/ops/sync_5a_r4x.py",
    "src/react_agent/ops/sync_5a_r5x.py",
    "src/react_agent/ops/sync_5a_r6x.py",
    "src/react_agent/ops/sync_5a_r7x.py",
    "src/react_agent/ops/sync_approval.py",
    "src/react_agent/ops/sync_artifacts.py",
    "src/react_agent/ops/sync_bootstrap.py",
    "src/react_agent/ops/sync_contracts.py",
    "src/react_agent/ops/sync_cycle.py",
    "src/react_agent/ops/sync_diff.py",
    "src/react_agent/ops/sync_environment.py",
    "src/react_agent/ops/sync_inventory.py",
    "src/react_agent/ops/sync_lock.py",
    "src/react_agent/ops/sync_materialize.py",
    "src/react_agent/ops/sync_p2s.py",
    "src/react_agent/ops/sync_plan.py",
    "src/react_agent/ops/sync_process_launcher.py",
    "src/react_agent/ops/sync_registry.py",
    "src/react_agent/ops/sync_runtime_assets.py",
    "src/react_agent/ops/sync_security.py",
    "src/react_agent/public_api.py",
    "src/react_agent/public_contracts.py",
    "src/react_agent/public_mapping.py",
    "src/react_agent/public_runtime.py",
    "src/react_agent/public_store.py",
    "src/react_agent/router_parse.py",
    "src/react_agent/router_provider.py",
    "src/react_agent/state.py",
    "tests/integration_tests/test_public_api.py",
    "tests/integration_tests/test_graph.py",
    "tests/integration_tests/test_sync_ops_planner.py",
    "tests/unit_tests/ops/test_sync_artifact_store_bootstrap.py",
    "tests/unit_tests/ops/test_sync_contracts.py",
    "tests/unit_tests/ops/test_sync_coverage_materialize.py",
    "tests/unit_tests/ops/test_sync_cycle_4x.py",
    "tests/unit_tests/ops/test_sync_5a_r1x.py",
    "tests/unit_tests/ops/test_sync_5a_r2x.py",
    "tests/unit_tests/ops/test_sync_5a_r3x.py",
    "tests/unit_tests/ops/test_sync_5a_r4x.py",
    "tests/unit_tests/ops/test_sync_5a_r5x.py",
    "tests/unit_tests/ops/test_sync_5a_r6x.py",
    "tests/unit_tests/ops/test_sync_5a_r7x.py",
    "tests/unit_tests/ops/test_sync_p2s_safety.py",
    "tests/unit_tests/ops/test_sync_plan_cli.py",
    "tests/unit_tests/ops/test_sync_registry_diff.py",
    "tests/unit_tests/ops/test_sync_security_inventory.py",
    "tests/unit_tests/ops/test_sync_source_policy_r1.py",
    "tests/unit_tests/ops/test_sync_writer_2a.py",
    "tests/unit_tests/test_fixed_dag_catalog.py",
    "tests/unit_tests/test_fixed_dag_contracts.py",
    "tests/unit_tests/test_fixed_dag_executor.py",
    "tests/unit_tests/test_fixed_dag_graph_skeleton.py",
    "tests/unit_tests/test_fixed_dag_l3_explanation_synthesizer.py",
    "tests/unit_tests/test_fixed_dag_non_l4_runtime_registry.py",
    "tests/unit_tests/test_fixed_dag_report_synthesizer.py",
    "tests/unit_tests/test_fixed_dag_runtime_registry.py",
    "tests/unit_tests/test_no_route_prior_runtime_contract.py",
    "tests/unit_tests/test_public_mapping_fixed_dag.py",
    "tests/unit_tests/test_public_runtime_streaming.py",
    "tests/unit_tests/test_parse_router_layers.py",
    "tests/unit_tests/test_router_parse_stats.py",
    "tests/unit_tests/test_router_prompt_format.py",
    "tests/unit_tests/test_router_provider_factory.py",
    "tests/unit_tests/test_quality_runner_codespell.py",
    "tests/unit_tests/test_quality_runner_dispatch.py",
)
STATIC_MYPY_TARGETS = (
    "scripts/quality/run_quality.py",
    "scripts/quality/run_provider_live_smoke.py",
    "scripts/ops/agent_syncctl.py",
    "src/react_agent/ops",
)
STATIC_CODESPELL_TARGETS = (
    "README.md",
    "AGENTS.md",
    "docs/CURRENT_STATUS.md",
    "docs/REPOSITORY_CONSOLIDATION_CLOSEOUT.md",
    "docs/SYSTEM_MAP.md",
    "docs/INDEX.md",
    "docs/ARCHITECTURE_FIXED_DAG.md",
    "docs/CONTRACTS.md",
    "docs/FRONTEND_V2.md",
    "docs/QUALITY.md",
    "docs/DECISIONS.md",
    "docs/CHANGELOG.md",
    "docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md",
    "docs/history/README.md",
    "docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md",
    "docs/CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md",
)


def _run(
    command: Iterable[str],
    *,
    cwd: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    rendered = " ".join(command)
    print(f"[quality] {rendered}", flush=True)
    subprocess.run(
        list(command),
        cwd=str(cwd or REPO_ROOT),
        env=env,
        check=True,
    )


def _npm_executable() -> str:
    if _is_windows():
        return "npm.cmd"
    return "npm"


def _is_windows() -> bool:
    return os.name == "nt"


def _codespell_names() -> tuple[str, ...]:
    if _is_windows():
        return ("codespell.exe", "codespell")
    return ("codespell", "codespell.exe")


def _unique_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).casefold() if _is_windows() else str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return tuple(unique)


def _codespell_env_candidates() -> tuple[Path, ...]:
    scripts_path = sysconfig.get_path("scripts")
    candidate_dirs: list[Path] = []
    if scripts_path:
        candidate_dirs.append(Path(scripts_path))

    python_dir = Path(sys.executable).resolve().parent
    if _is_windows():
        candidate_dirs.append(python_dir / "Scripts")
    candidate_dirs.append(python_dir)

    return _unique_paths(
        directory / name for directory in candidate_dirs for name in _codespell_names()
    )


def _codespell_executable() -> str:
    env_candidates = _codespell_env_candidates()
    for candidate in env_candidates:
        if candidate.is_file():
            return str(candidate)

    path_names = _codespell_names()
    for name in path_names:
        found = shutil.which(name)
        if found:
            return found

    rendered_candidates = "\n".join(f"  - {path}" for path in env_candidates)
    raise RuntimeError(
        "Could not locate the codespell executable for the active Python environment.\n"
        f"Python executable: {sys.executable}\n"
        "Env-local candidate paths:\n"
        f"{rendered_candidates}\n"
        f"PATH lookup attempted: {', '.join(path_names)}"
    )


def _python_module(*args: str, extra_env: Mapping[str, str] | None = None) -> None:
    _run((sys.executable, *args), extra_env=extra_env)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _assert_repo_external_build_dir(path: Path) -> None:
    if _is_relative_to(path, REPO_ROOT):
        raise RuntimeError(f"Frontend build outDir must be outside the repo: {path}")


def run_static() -> None:
    """Run the blocking static checks for the maintained quality surface."""
    _python_module("-m", "ruff", "check", *STATIC_RUFF_TARGETS)
    _python_module("-m", "mypy", "--strict", "--follow-imports=skip", *STATIC_MYPY_TARGETS)
    _run((_codespell_executable(), "-I", ".codespellignore", *STATIC_CODESPELL_TARGETS))


def run_unit() -> None:
    """Run focused Python unit tests."""
    _python_module("-m", "pytest", "tests/unit_tests", "-q")


def run_public_api() -> None:
    """Run the public adapter integration contract tests."""
    _python_module("-m", "pytest", "tests/integration_tests/test_public_api.py", "-q")


def run_graph_smoke() -> None:
    """Run the blocking runtime graph smoke test."""
    _python_module("-m", "pytest", "tests/integration_tests/test_graph.py", "-q")


def run_frontend() -> None:
    """Run the active frontend typecheck, smoke, and repo-external build gate."""
    npm = _npm_executable()
    _run(
        (
            npm,
            "--prefix",
            "apps/web",
            "exec",
            "--",
            "tsc",
            "--noEmit",
            "--project",
            "apps/web/tsconfig.json",
        )
    )
    _run(("node", "--import", "tsx", "src/test/smoke.tsx"), cwd=REPO_ROOT / "apps" / "web")
    with tempfile.TemporaryDirectory(prefix="lma-web-build-") as out_dir_name:
        out_dir = Path(out_dir_name)
        _assert_repo_external_build_dir(out_dir)
        print(f"[quality] frontend build outDir: {out_dir}", flush=True)
        _run(
            (
                npm,
                "--prefix",
                "apps/web",
                "run",
                "build",
                "--",
                "--outDir",
                str(out_dir),
            )
        )


def run_fusion_gate() -> None:
    """Run the archived/manual deterministic fusion regression chain."""
    print("[quality] archived/manual fusion-gate mode; not part of reset mainline", flush=True)
    fusion_env = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "test"),
        "TAVILY_API_KEY": os.environ.get("TAVILY_API_KEY", "ff5b-dummy-key"),
    }
    _python_module(
        "-m",
        "ops.regression.fusion.run_fusion_regression",
        "--out-dir",
        str(FUSION_OUT_DIR),
        extra_env=fusion_env,
    )
    _python_module(
        "-m",
        "ops.regression.fusion.eval_fusion_outputs",
        "--in",
        str(FUSION_OUT_DIR / "fusion_runs.jsonl"),
        "--out",
        str(FUSION_OUT_DIR / "fusion_metrics.json"),
        extra_env=fusion_env,
    )
    _python_module(
        "-m",
        "ops.regression.fusion.gate_fusion_outputs",
        "--in",
        str(FUSION_OUT_DIR / "fusion_metrics.json"),
        "--out",
        str(FUSION_OUT_DIR / "fusion_gate.json"),
        extra_env=fusion_env,
    )


def run_mainline() -> None:
    """Run the default fixed-DAG reset quality gate."""
    run_static()
    run_unit()
    run_public_api()
    run_graph_smoke()
    run_frontend()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the repo-level quality runner."""
    parser = argparse.ArgumentParser(
        description="Run fixed-DAG reset quality checks.",
        epilog=(
            "Reset mainline runs static, unit, public-api, graph-smoke, and "
            "frontend. fusion-gate is archived/manual only; provider/live, "
            "external invoke, demo stack, Router-SFT, and RARP checks are not "
            "default mainline gates."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("static", "unit", "public-api", "graph-smoke", "frontend", "fusion-gate", "mainline"),
        default="mainline",
        help=(
            "Quality mode to execute. mainline is the reset default gate; "
            "fusion-gate is archived/manual only."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Dispatch the selected quality mode."""
    args = parse_args()
    if args.mode == "static":
        run_static()
    elif args.mode == "unit":
        run_unit()
    elif args.mode == "public-api":
        run_public_api()
    elif args.mode == "graph-smoke":
        run_graph_smoke()
    elif args.mode == "frontend":
        run_frontend()
    elif args.mode == "fusion-gate":
        run_fusion_gate()
    else:
        run_mainline()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
