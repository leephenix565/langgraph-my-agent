from pathlib import Path

import pytest

from scripts.quality import run_quality


def _patch_codespell_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    is_windows: bool,
    python_executable: Path,
    scripts_path: Path,
) -> None:
    monkeypatch.setattr(run_quality, "_is_windows", lambda: is_windows)
    monkeypatch.setattr(run_quality.sys, "executable", str(python_executable))
    monkeypatch.setattr(
        run_quality.sysconfig,
        "get_path",
        lambda name: str(scripts_path) if name == "scripts" else None,
    )


def test_codespell_executable_prefers_windows_env_local_scripts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_root = tmp_path / "env"
    scripts_dir = env_root / "Scripts"
    scripts_dir.mkdir(parents=True)
    codespell = scripts_dir / "codespell.exe"
    codespell.write_text("", encoding="utf-8")
    _patch_codespell_env(
        monkeypatch,
        is_windows=True,
        python_executable=env_root / "python.exe",
        scripts_path=scripts_dir,
    )
    monkeypatch.setattr(run_quality.shutil, "which", lambda name: None)

    assert run_quality._codespell_executable() == str(codespell)


def test_codespell_executable_prefers_posix_env_local_bin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_root = tmp_path / "env"
    bin_dir = env_root / "bin"
    bin_dir.mkdir(parents=True)
    codespell = bin_dir / "codespell"
    codespell.write_text("", encoding="utf-8")
    _patch_codespell_env(
        monkeypatch,
        is_windows=False,
        python_executable=bin_dir / "python",
        scripts_path=bin_dir,
    )
    monkeypatch.setattr(run_quality.shutil, "which", lambda name: None)

    assert run_quality._codespell_executable() == str(codespell)


def test_codespell_executable_falls_back_to_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_root = tmp_path / "env"
    bin_dir = env_root / "bin"
    bin_dir.mkdir(parents=True)
    path_codespell = tmp_path / "path-bin" / "codespell"
    path_codespell.parent.mkdir()
    path_codespell.write_text("", encoding="utf-8")
    _patch_codespell_env(
        monkeypatch,
        is_windows=False,
        python_executable=bin_dir / "python",
        scripts_path=bin_dir,
    )
    monkeypatch.setattr(
        run_quality.shutil,
        "which",
        lambda name: str(path_codespell) if name == "codespell" else None,
    )

    assert run_quality._codespell_executable() == str(path_codespell)


def test_codespell_executable_missing_has_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_root = tmp_path / "env"
    scripts_dir = env_root / "Scripts"
    scripts_dir.mkdir(parents=True)
    python_executable = env_root / "python.exe"
    _patch_codespell_env(
        monkeypatch,
        is_windows=True,
        python_executable=python_executable,
        scripts_path=scripts_dir,
    )
    monkeypatch.setattr(run_quality.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError) as exc_info:
        run_quality._codespell_executable()

    message = str(exc_info.value)
    assert str(python_executable) in message
    assert str(scripts_dir / "codespell.exe") in message
    assert "PATH lookup attempted: codespell.exe, codespell" in message
