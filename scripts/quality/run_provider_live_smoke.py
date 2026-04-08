#!/usr/bin/env python
"""Optional provider/live smoke for the public adapter."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


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
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _artifact_base() -> Dict[str, Any]:
    return {
        "status": "skipped",
        "timestamp": _timestamp(),
        "mode": "optional-non-blocking",
        "health": None,
        "prerequisites": None,
        "thread_id": None,
        "send_message_status": "not-run",
        "continuity_mode": None,
        "error_code": None,
        "error_category": None,
        "residual_condition": None,
        "next_trigger_condition": None,
    }


def _collect_residual_state(health: Dict[str, Any], *, provider_ready: bool, search_ready: bool, checkpointer_ready: bool, runtime_ready: bool) -> Dict[str, str | None]:
    residuals: list[str] = []
    next_steps: list[str] = []
    error_code: str | None = None
    error_category: str | None = None

    def register(code: str | None, category: str, residual: str, next_step: str) -> None:
        nonlocal error_code, error_category
        residuals.append(residual)
        next_steps.append(next_step)
        if error_code is None and code:
            error_code = code
            error_category = category

    if not provider_ready:
        register(
            health.get("providerEnv", {}).get("code"),
            "provider_env",
            "Provider credentials are missing (OPENAI_API_KEY, ROUTER_OPENAI_API_KEY, BASELINE_OPENAI_API_KEY, or GOOGLE_API_KEY).",
            "Configure one supported provider credential.",
        )
    if not search_ready:
        register(
            health.get("searchEnv", {}).get("code"),
            "provider_env",
            "Search credentials are missing (TAVILY_API_KEY).",
            "Configure TAVILY_API_KEY.",
        )
    if not checkpointer_ready:
        register(
            health.get("checkpointer", {}).get("code"),
            "runtime",
            "Checkpointer is not enabled.",
            "Use REACT_AGENT_CHECKPOINTER=memory or another supported checkpointer mode.",
        )
    if not runtime_ready:
        register(
            health.get("runtime", {}).get("code"),
            "runtime",
            "Runtime import/readiness is unavailable in the current environment.",
            "Resolve the runtime import/readiness failure after provider and search prerequisites are configured.",
        )

    next_trigger_condition = None
    if next_steps:
        deduped_steps = list(dict.fromkeys(next_steps))
        next_trigger_condition = " ".join(deduped_steps) + " Rerun the optional smoke afterward."

    return {
        "error_code": error_code,
        "error_category": error_category,
        "residual_condition": " ".join(residuals) if residuals else None,
        "next_trigger_condition": next_trigger_condition,
    }


def _write_artifact(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the optional provider/live smoke."""
    parser = argparse.ArgumentParser(description="Run optional provider/live smoke for the public adapter.")
    parser.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / "ops" / "regression" / "provider" / "out"),
        help="Artifact output directory.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the optional provider-backed public seam smoke and write an artifact."""
    args = parse_args()
    out_dir = Path(args.out_dir)
    artifact_path = out_dir / "provider_live_smoke.json"
    artifact = _artifact_base()

    os.environ.setdefault("REACT_AGENT_CHECKPOINTER", "memory")
    os.environ["REACT_AGENT_PUBLIC_STORE"] = str(out_dir / "provider_live_smoke_threads.json")

    from fastapi.testclient import TestClient

    from react_agent import public_api

    client = TestClient(public_api.app)
    health_response = client.get("/api/health")
    health = health_response.json()
    artifact["health"] = health
    artifact["continuity_mode"] = health.get("continuityDefault")

    provider_ready = health.get("providerEnv", {}).get("status") == "configured"
    search_ready = health.get("searchEnv", {}).get("status") == "configured"
    checkpointer_ready = health.get("checkpointer", {}).get("status") == "enabled"
    runtime_ready = health.get("runtime", {}).get("status") == "ready"
    artifact["prerequisites"] = {
        "provider_env_ready": provider_ready,
        "search_env_ready": search_ready,
        "checkpointer_ready": checkpointer_ready,
        "runtime_ready": runtime_ready,
    }

    if not (provider_ready and search_ready and checkpointer_ready):
        residual_state = _collect_residual_state(
            health,
            provider_ready=provider_ready,
            search_ready=search_ready,
            checkpointer_ready=checkpointer_ready,
            runtime_ready=runtime_ready,
        )
        artifact["status"] = "skipped"
        artifact.update(residual_state)
        _write_artifact(artifact_path, artifact)
        print(f"provider/live smoke skipped: {artifact['error_code']}")
        print(f"artifact: {artifact_path}")
        return 0

    if not runtime_ready:
        artifact["status"] = "failed"
        artifact["error_code"] = health.get("runtime", {}).get("code")
        artifact["error_category"] = "runtime"
        artifact["residual_condition"] = "Runtime import failed even though prerequisites were configured."
        artifact["next_trigger_condition"] = "Fix the runtime import/readiness failure and rerun the optional smoke."
        _write_artifact(artifact_path, artifact)
        print(f"provider/live smoke failed: {artifact['error_code']}")
        print(f"artifact: {artifact_path}")
        return 1

    try:
        create_response = client.post("/api/threads", json={})
        create_response.raise_for_status()
        thread_id = create_response.json()["thread"]["id"]
        artifact["thread_id"] = thread_id

        send_response = client.post(
            f"/api/threads/{thread_id}/messages",
            json={"text": "Please return a one-sentence live provider smoke acknowledgment."},
        )
        artifact["send_message_status"] = str(send_response.status_code)
        if send_response.status_code >= 400:
            detail = send_response.json().get("detail", {})
            artifact["status"] = "failed"
            artifact["error_code"] = detail.get("code")
            artifact["error_category"] = detail.get("category")
            _write_artifact(artifact_path, artifact)
            print(f"provider/live smoke failed: {artifact['error_code']}")
            print(f"artifact: {artifact_path}")
            return 1

        payload = send_response.json()
        artifact["status"] = "passed"
        artifact["continuity_mode"] = payload.get("assistantTurn", {}).get("continuityMode") or artifact["continuity_mode"]
        artifact["residual_condition"] = None
        artifact["next_trigger_condition"] = None
        _write_artifact(artifact_path, artifact)
        print(f"provider/live smoke passed: {thread_id}")
        print(f"artifact: {artifact_path}")
        return 0
    except Exception as exc:
        artifact["status"] = "failed"
        artifact["error_code"] = "provider_live_smoke_failed"
        artifact["error_category"] = "runtime"
        artifact["send_message_status"] = "exception"
        artifact["exception"] = type(exc).__name__
        artifact["residual_condition"] = "The live public seam raised an exception during the optional smoke."
        artifact["next_trigger_condition"] = "Inspect the provider smoke artifact, fix the runtime failure, and rerun the optional smoke."
        _write_artifact(artifact_path, artifact)
        print(f"provider/live smoke failed: {type(exc).__name__}")
        print(f"artifact: {artifact_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
