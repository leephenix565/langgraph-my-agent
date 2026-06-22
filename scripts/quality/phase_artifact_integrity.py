"""Helpers for phase artifact SHA256 manifests.

The phase closeout convention is:
1. finalize every primary artifact;
2. finalize validation output;
3. write a relative-path sha256 manifest that does not include itself;
4. run verification and store the verification transcript separately.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Iterable
from pathlib import Path


def _relative_artifact_path(root: Path, path: Path, *, manifest_path: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"artifact outside root: {path}") from exc
    if resolved_path == manifest_path.resolve():
        raise ValueError("sha256sums.txt must not include itself")
    return relative


def sha256_file(path: Path) -> str:
    """Return the hex SHA256 digest for a finalized artifact file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256_manifest(
    root: str | Path,
    artifact_paths: Iterable[str | Path],
    *,
    manifest_name: str = "sha256sums.txt",
) -> Path:
    """Write a relative-path SHA256 manifest for finalized artifacts."""
    root_path = Path(root)
    manifest_path = root_path / manifest_name
    rows: list[tuple[Path, str]] = []
    for raw_path in artifact_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = root_path / path
        relative = _relative_artifact_path(root_path, path, manifest_path=manifest_path)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        rows.append((relative, sha256_file(path)))
    lines = [
        f"{digest}  {relative.as_posix()}"
        for relative, digest in sorted(rows, key=lambda item: item[0].as_posix())
    ]
    manifest_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return manifest_path


def verify_sha256_manifest(
    root: str | Path,
    *,
    manifest_name: str = "sha256sums.txt",
    verification_output_name: str | None = "integrity_verification.txt",
) -> subprocess.CompletedProcess[str]:
    """Run `sha256sum -c` and optionally persist its detached transcript."""
    root_path = Path(root)
    manifest_path = root_path / manifest_name
    if not manifest_path.is_file():
        raise FileNotFoundError(str(manifest_path))
    result = subprocess.run(
        ["sha256sum", "-c", manifest_name],
        cwd=root_path,
        check=False,
        capture_output=True,
        text=True,
    )
    if verification_output_name:
        output_path = root_path / verification_output_name
        transcript = result.stdout
        if result.stderr:
            transcript += result.stderr
        output_path.write_text(transcript, encoding="utf-8")
    return result


__all__ = [
    "sha256_file",
    "verify_sha256_manifest",
    "write_sha256_manifest",
]
