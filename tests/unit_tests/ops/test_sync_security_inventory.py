"""Tests for sync planner filesystem safety and inventory."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from react_agent.ops.sync_contracts import SyncPlannerError
from react_agent.ops.sync_inventory import inventory_root, inventory_source_roots
from react_agent.ops.sync_security import (
    detect_unicode_collision,
    normalize_safe_relative_path,
    should_include_source_file,
)


def test_normalize_safe_relative_path_rejects_unsafe_paths() -> None:
    assert normalize_safe_relative_path("a\\b.py") == "a/b.py"
    for value in ("../x.py", "/tmp/x.py", "a/\x00.py"):
        with pytest.raises(SyncPlannerError):
            normalize_safe_relative_path(value)


def test_file_policy_blocks_env_secret_large_and_special(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TOKEN=hidden\n", encoding="utf-8")
    assert should_include_source_file(tmp_path, env_file)["classification"] == "blocked_sensitive_source"

    secret = tmp_path / "config.py"
    secret.write_text("api_key = 'abcdefghi12345'\n", encoding="utf-8")
    assert should_include_source_file(tmp_path, secret)["classification"] == "blocked_sensitive_source"

    large = tmp_path / "model.bin"
    large.write_bytes(b"x" * 128)
    assert should_include_source_file(tmp_path, large)["classification"] == "large_asset_reference"


def test_inventory_digest_ignores_mtime_but_tracks_executable(tmp_path: Path) -> None:
    file_path = tmp_path / "agent.py"
    file_path.write_text("print('ok')\n", encoding="utf-8")
    first = inventory_root("agent", tmp_path, root_role="test")
    os.utime(file_path, (1, 1))
    second = inventory_root("agent", tmp_path, root_role="test")
    assert first["tree_digest"] == second["tree_digest"]
    file_path.chmod(file_path.stat().st_mode | stat.S_IXUSR)
    third = inventory_root("agent", tmp_path, root_role="test")
    assert third["tree_digest"] != second["tree_digest"]


def test_inventory_excludes_runtime_noise_and_detects_unicode_collision(tmp_path: Path) -> None:
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"bad")
    (tmp_path / "agent.py").write_text("x=1\n", encoding="utf-8")
    inventory = inventory_root("agent", tmp_path, root_role="test")
    paths = [record["relative_path"] for record in inventory["files"]]
    assert "agent.py" in paths
    assert "__pycache__/x.pyc" not in paths
    assert detect_unicode_collision(["e\u0301.py", "é.py"]) == ["é.py"]


def test_inventory_recurses_nested_packages_and_prunes_excluded_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "pkg" / "subpkg"
    nested.mkdir(parents=True)
    (nested / "agent.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "hidden.py").write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "tests.bak_v22_20260607_082218").mkdir()
    (tmp_path / "tests.bak_v22_20260607_082218" / "old.py").write_text("x = 3\n", encoding="utf-8")
    inventory = inventory_root("agent", tmp_path, root_role="test")
    paths = {record["relative_path"] for record in inventory["files"]}
    assert "pkg/subpkg/agent.py" in paths
    assert "logs/hidden.py" not in paths
    assert "tests.bak_v22_20260607_082218/old.py" not in paths


def test_inventory_source_subroot_preserves_logical_root_prefix(tmp_path: Path) -> None:
    logical = tmp_path / "service"
    subroot = logical / "backend"
    subroot.mkdir(parents=True)
    (subroot / "app.py").write_text("x = 1\n", encoding="utf-8")
    inventory = inventory_source_roots("agent", logical, [subroot], root_role="prod")
    paths = {record["relative_path"] for record in inventory["files"]}
    assert paths == {"backend/app.py"}
    assert inventory["included_count"] == 1


def test_backup_filename_policy_excludes_runtime_artifacts(tmp_path: Path) -> None:
    for relative in (
        "service.backup.py",
        "service.orig.py",
        "backup/service.py",
        "backups/service.py",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n", encoding="utf-8")
        assert should_include_source_file(tmp_path, path)["include"] is False
