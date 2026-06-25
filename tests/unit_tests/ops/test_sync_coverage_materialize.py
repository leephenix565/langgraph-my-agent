"""Tests for SYNC-OPS-1R2 coverage and temp stage reconstruction."""

from __future__ import annotations

from pathlib import Path

import pytest

from react_agent.ops.sync_contracts import SyncPlannerError, file_sha256
from react_agent.ops.sync_coverage import (
    build_baseline_parity_ledger,
    build_current_prod_coverage_ledger,
)
from react_agent.ops.sync_materialize import (
    compile_stage_with_profile,
    reconstruct_temp_stage,
)
from react_agent.ops.sync_plan import stage_projection_digest_for_actions


def _record(agent_id: str, root: Path, rel: str, *, include: bool = True) -> dict[str, object]:
    path = root / rel
    return {
        "agent_id": agent_id,
        "relative_path": rel,
        "raw_path": str(path),
        "file_type": "regular",
        "mode": "0o644",
        "executable": False,
        "sha256": file_sha256(path) if include else "",
        "sensitive_classification": "not_sensitive",
        "large_asset_classification": "not_large_asset",
        "source_category": "source_code",
        "source_category_reason": "hermetic_fixture",
        "include": include,
        "include_decision": "included_source" if include else "excluded_directory",
    }


def _copy_action(
    *,
    action_id: str,
    agent_id: str,
    rel: str,
    source: Path,
    stage_rel: str | None = None,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "operation": "copy_from_prod",
        "agent_id": agent_id,
        "affected_agent_ids": [agent_id],
        "transaction_root": str(source.parent),
        "source_path": rel,
        "source_sha256": file_sha256(source),
        "source_mode": "0o644",
        "source_file_type": "regular",
        "source_absolute_path": str(source),
        "source_executable": False,
        "source_symlink_target": "",
        "destination_relative_path": rel,
        "stage_relative_path": stage_rel or f"{agent_id}/{rel}",
        "sensitive_classification": "not_sensitive",
        "large_asset_classification": "not_large_asset",
        "source_category": "source_code",
        "source_category_reason": "hermetic_fixture",
    }


def _fixture_plan(tmp_path: Path) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]]]:
    prod = tmp_path / "prod"
    active = tmp_path / "active"
    baseline = tmp_path / "baseline"
    for root in (prod, active, baseline):
        (root / "agent_alpha").mkdir(parents=True)
    (prod / "agent_alpha" / "service.py").write_text("VALUE = 'prod'\n", encoding="utf-8")
    (active / "agent_alpha" / "redacted.py").write_text("SAFE = 'redacted'\n", encoding="utf-8")
    (active / "agent_alpha" / "SANDBOX_SECRET_REQUIREMENTS.md").write_text("No raw secrets.\n", encoding="utf-8")
    shared_source = prod / "agent_alpha" / "shared.py"
    shared_source.write_text("SHARED = True\n", encoding="utf-8")

    service_action = _copy_action(
        action_id="mat_service",
        agent_id="agent_alpha",
        rel="service.py",
        source=prod / "agent_alpha" / "service.py",
    )
    redacted_action = {
        "action_id": "mat_redacted",
        "operation": "preserve_sanitized_derivative",
        "agent_id": "agent_alpha",
        "affected_agent_ids": ["agent_alpha"],
        "baseline_derivative_path": "redacted.py",
        "destination_relative_path": "redacted.py",
        "stage_relative_path": "agent_alpha/redacted.py",
        "source_absolute_path": str(active / "agent_alpha" / "redacted.py"),
        "derivative_sha256": file_sha256(active / "agent_alpha" / "redacted.py"),
        "derivative_manifest_reference": "hermetic_fixture",
    }
    metadata_action = {
        "action_id": "mat_metadata",
        "operation": "preserve_sandbox_metadata",
        "agent_id": "agent_alpha",
        "affected_agent_ids": ["agent_alpha"],
        "baseline_metadata_path": "SANDBOX_SECRET_REQUIREMENTS.md",
        "destination_relative_path": "SANDBOX_SECRET_REQUIREMENTS.md",
        "stage_relative_path": "agent_alpha/SANDBOX_SECRET_REQUIREMENTS.md",
        "source_absolute_path": str(active / "agent_alpha" / "SANDBOX_SECRET_REQUIREMENTS.md"),
        "metadata_sha256": file_sha256(active / "agent_alpha" / "SANDBOX_SECRET_REQUIREMENTS.md"),
    }
    shared_action = _copy_action(
        action_id="mat_shared",
        agent_id="market_composite",
        rel="shared.py",
        source=shared_source,
        stage_rel="market_composite/subagents/fund_manager_behavior/shared.py",
    )
    noop_action = {
        "action_id": "mat_noop",
        "operation": "noop_shared_transaction_member",
        "agent_id": "market_fund_manager_behavior",
        "affected_agent_ids": ["market_fund_manager_behavior"],
        "destination_relative_path": "",
        "stage_relative_path": "",
    }
    actions = [service_action, redacted_action, metadata_action, shared_action, noop_action]
    plan: dict[str, object] = {
        "schema_version": "agent_sync_plan_v1",
        "plan_id": "hermetic_p2s_projection",
        "canonical_sha256": "fixture",
        "agents": [
            {"agent_id": "agent_alpha", "actions": [service_action, redacted_action, metadata_action]},
            {"agent_id": "market_composite", "actions": [shared_action]},
            {"agent_id": "market_fund_manager_behavior", "actions": [noop_action]},
        ],
        "stage_materialization": {
            "expected_stage_projection_digest": stage_projection_digest_for_actions(actions),
        },
    }
    inventory = {
        "agents": [
            {
                "agent_id": "agent_alpha",
                "roots": {
                    "prod": {"files": [_record("agent_alpha", prod / "agent_alpha", "service.py")]},
                    "active_sandbox": {
                        "files": [
                            _record("agent_alpha", active / "agent_alpha", "redacted.py"),
                            _record("agent_alpha", active / "agent_alpha", "SANDBOX_SECRET_REQUIREMENTS.md"),
                        ]
                    },
                    "baseline": {"files": []},
                },
            },
            {
                "agent_id": "market_fund_manager_behavior",
                "roots": {
                    "prod": {"files": [_record("market_fund_manager_behavior", prod / "agent_alpha", "shared.py")]},
                    "active_sandbox": {"files": []},
                    "baseline": {"files": []},
                },
            },
        ],
    }
    previous_manifest = [
        {"agent_id": "agent_alpha", "relative_path": "service.py", "prod_sha256": file_sha256(prod / "agent_alpha" / "service.py")},
        {"agent_id": "agent_alpha", "relative_path": "redacted.py", "staged_sha256": file_sha256(active / "agent_alpha" / "redacted.py")},
        {"agent_id": "market_fund_manager_behavior", "relative_path": "shared.py", "prod_sha256": file_sha256(shared_source)},
    ]
    return plan, inventory, previous_manifest


def test_hermetic_parity_and_coverage_are_fully_resolved(tmp_path: Path) -> None:
    plan, inventory, previous_manifest = _fixture_plan(tmp_path)
    historical = build_baseline_parity_ledger(plan=plan, inventory=inventory, previous_manifest=previous_manifest)
    current = build_current_prod_coverage_ledger(plan=plan, inventory=inventory)
    assert historical["row_count"] == 3
    assert historical["unresolved_count"] == 0
    assert current["unresolved_count"] == 0
    assert current["safe_source_unresolved_count"] == 0
    assert current["safe_source_coverage_ratio"] == 1.0
    assert current["coverage_counts"]["shared_transaction_materialized_elsewhere"] == 1
    assert current["coverage_counts"]["materialized_from_current_prod"] == 1


def test_temp_stage_reconstruction_matches_projection_digest(tmp_path: Path) -> None:
    plan, _, _ = _fixture_plan(tmp_path)
    result = reconstruct_temp_stage(plan, tmp_path / "stage")
    assert result["digest_match"] is True
    assert result["structural_pass"] is True
    assert result["duplicate_destination_count"] == 0
    assert result["secret_scan"]["pass"] is True


def test_temp_stage_reconstruction_fails_closed_on_copy_source_drift(tmp_path: Path) -> None:
    plan, _, _ = _fixture_plan(tmp_path)
    source = Path(str(plan["agents"][0]["actions"][0]["source_absolute_path"]))  # type: ignore[index]
    source.write_text("VALUE = 'drifted'\n", encoding="utf-8")

    with pytest.raises(SyncPlannerError) as exc_info:
        reconstruct_temp_stage(plan, tmp_path / "stage")

    assert exc_info.value.reason == "materialization_source_hash_drift"
    assert exc_info.value.details["operation"] == "copy_from_prod"


def test_temp_stage_reconstruction_fails_closed_on_preserved_derivative_drift(tmp_path: Path) -> None:
    plan, _, _ = _fixture_plan(tmp_path)
    derivative_action = plan["agents"][0]["actions"][1]  # type: ignore[index]
    Path(str(derivative_action["source_absolute_path"])).write_text("SAFE = 'drifted'\n", encoding="utf-8")

    with pytest.raises(SyncPlannerError) as exc_info:
        reconstruct_temp_stage(plan, tmp_path / "stage")

    assert exc_info.value.reason == "materialization_source_hash_drift"
    assert exc_info.value.details["operation"] == "preserve_sanitized_derivative"


def test_compile_stage_does_not_write_pycache_inside_stage(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    package = stage / "agent"
    package.mkdir(parents=True)
    (package / "service.py").write_text("VALUE = 1\n", encoding="utf-8")

    result = compile_stage_with_profile(stage)

    assert result["pass"] is True
    assert not list(stage.rglob("__pycache__"))
