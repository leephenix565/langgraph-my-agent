from pathlib import Path

import pytest

from scripts.quality import run_quality


def test_mainline_dispatch_includes_reset_modes_and_excludes_fusion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(run_quality, "run_static", lambda: calls.append("static"))
    monkeypatch.setattr(run_quality, "run_unit", lambda: calls.append("unit"))
    monkeypatch.setattr(run_quality, "run_public_api", lambda: calls.append("public-api"))
    monkeypatch.setattr(run_quality, "run_graph_smoke", lambda: calls.append("graph-smoke"))
    monkeypatch.setattr(run_quality, "run_frontend", lambda: calls.append("frontend"))
    monkeypatch.setattr(
        run_quality,
        "run_fusion_gate",
        lambda: (_ for _ in ()).throw(AssertionError("fusion-gate is archived/manual only")),
    )

    run_quality.run_mainline()

    assert calls == ["static", "unit", "public-api", "graph-smoke", "frontend"]


def test_frontend_gate_typecheck_smoke_and_repo_external_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    monkeypatch.setattr(run_quality, "_npm_executable", lambda: "npm")
    monkeypatch.setattr(
        run_quality,
        "_run",
        lambda command, **_: commands.append(tuple(command)),
    )

    run_quality.run_frontend()

    assert commands[0] == (
        "npm",
        "--prefix",
        "apps/web",
        "exec",
        "--",
        "tsc",
        "--noEmit",
        "--project",
        "apps/web/tsconfig.json",
    )
    assert commands[1] == ("npm", "--prefix", "apps/web", "run", "test")

    build_command = commands[2]
    assert build_command[:7] == (
        "npm",
        "--prefix",
        "apps/web",
        "run",
        "build",
        "--",
        "--outDir",
    )
    build_out_dir = Path(build_command[7])
    assert build_out_dir.name != "dist"
    assert build_out_dir != run_quality.REPO_ROOT / "apps" / "web" / "dist"
    assert not run_quality._is_relative_to(build_out_dir, run_quality.REPO_ROOT)


def test_frontend_build_out_dir_rejects_repo_internal_path() -> None:
    with pytest.raises(RuntimeError, match="outside the repo"):
        run_quality._assert_repo_external_build_dir(
            run_quality.REPO_ROOT / "apps" / "web" / "dist"
        )
