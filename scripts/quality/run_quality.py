#!/usr/bin/env python
"""Repo-level quality runner for QS-2."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
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
    "tests/integration_tests/test_public_api.py",
    "tests/integration_tests/test_graph.py",
)
STATIC_MYPY_TARGETS = (
    "scripts/quality/run_quality.py",
    "scripts/quality/run_provider_live_smoke.py",
)
STATIC_CODESPELL_TARGETS = (
    "README.md",
    "AGENTS.md",
    "docs/PROJECT_OVERVIEW.md",
    "docs/SYSTEM_MAP.md",
    "docs/INDEX.md",
    "docs/RUNBOOK_ROUTER_SFT.md",
    "docs/FRONTEND_ARCHITECTURE.md",
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


def run_static() -> None:
    """Run the blocking static checks for the maintained quality surface."""
    _python_module("-m", "ruff", "check", *STATIC_RUFF_TARGETS)
    _python_module("-m", "mypy", "--strict", "--follow-imports=skip", *STATIC_MYPY_TARGETS)
    _run((_codespell_executable(), "-I", ".codespellignore", *STATIC_CODESPELL_TARGETS))


def run_unit() -> None:
    """Run focused Python unit tests."""
    _python_module("-m", "pytest", "tests/unit_tests")


def run_public_api() -> None:
    """Run the public adapter integration contract tests."""
    _python_module("-m", "pytest", "tests/integration_tests/test_public_api.py")


def run_graph_smoke() -> None:
    """Run the blocking runtime graph smoke test."""
    _python_module("-m", "pytest", "tests/integration_tests/test_graph.py")


def run_frontend() -> None:
    """Run the active frontend build and smoke gate."""
    npm = _npm_executable()
    _run((npm, "--prefix", "apps/web", "run", "build"))
    _run((npm, "--prefix", "apps/web", "run", "test"))


def run_fusion_gate() -> None:
    """Run the deterministic fusion regression, eval, and gate chain."""
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
    """Run the default blocking quality closure entrypoint."""
    run_static()
    run_unit()
    run_public_api()
    run_graph_smoke()
    run_frontend()
    run_fusion_gate()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the repo-level quality runner."""
    parser = argparse.ArgumentParser(description="Run repo-level quality checks.")
    parser.add_argument(
        "--mode",
        choices=("static", "unit", "public-api", "graph-smoke", "frontend", "fusion-gate", "mainline"),
        default="mainline",
        help="Quality mode to execute.",
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
