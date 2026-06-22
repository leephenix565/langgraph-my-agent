from __future__ import annotations

from pathlib import Path

import pytest

from scripts.quality.phase_artifact_integrity import (
    verify_sha256_manifest,
    write_sha256_manifest,
)


def test_sha_manifest_uses_relative_paths_and_nested_files(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "artifact.json").write_text('{"ok": true}\n', encoding="utf-8")
    (tmp_path / "nested" / "result.txt").write_text("done\n", encoding="utf-8")

    manifest = write_sha256_manifest(
        tmp_path,
        ["artifact.json", "nested/result.txt"],
    )
    result = verify_sha256_manifest(tmp_path)

    text = manifest.read_text(encoding="utf-8")
    assert "artifact.json" in text
    assert "nested/result.txt" in text
    assert str(tmp_path) not in text
    assert result.returncode == 0
    assert "OK" in (tmp_path / "integrity_verification.txt").read_text(encoding="utf-8")


def test_sha_manifest_detects_post_hash_mutation(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"before": true}\n', encoding="utf-8")
    write_sha256_manifest(tmp_path, [artifact])
    artifact.write_text('{"after": true}\n', encoding="utf-8")

    result = verify_sha256_manifest(tmp_path, verification_output_name=None)

    assert result.returncode != 0
    assert "FAILED" in result.stdout


def test_sha_manifest_rejects_missing_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        write_sha256_manifest(tmp_path, ["missing.json"])


def test_sha_manifest_rejects_self_reference(tmp_path: Path) -> None:
    (tmp_path / "sha256sums.txt").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="must not include itself"):
        write_sha256_manifest(tmp_path, ["sha256sums.txt"])
