from copy import deepcopy
from pathlib import Path

from react_agent.fixed_dag_non_l4_runtime_registry import (
    NON_L4_ACTIVATION_SOURCE_SHA256,
    NON_L4_EXTERNAL_COMPUTE_DISABLE_ENV_VAR,
    NON_L4_EXTERNAL_COMPUTE_POLICY_PATH,
    NON_L4_EXTERNAL_COMPUTE_POLICY_SCHEMA_VERSION,
    NON_L4_OPTIONAL_AGENT_IDS,
    NON_L4_REQUIRED_AGENT_IDS,
    load_non_l4_external_compute_policy,
    non_l4_external_compute_entries,
    non_l4_policy_enabled_agent_ids,
    non_l4_policy_summary,
    validate_non_l4_external_compute_policy,
)


def _policy():
    return deepcopy(load_non_l4_external_compute_policy())


def test_non_l4_policy_file_validates_and_matches_activation_set() -> None:
    policy = load_non_l4_external_compute_policy()
    valid, reason = validate_non_l4_external_compute_policy(policy)

    assert valid, reason
    assert NON_L4_EXTERNAL_COMPUTE_POLICY_PATH == (
        Path(__file__).resolve().parents[2]
        / "config"
        / "fixed_dag"
        / "non_l4_external_compute_policy.json"
    )
    assert policy["schema_version"] == NON_L4_EXTERNAL_COMPUTE_POLICY_SCHEMA_VERSION
    assert policy["disable_env_var"] == NON_L4_EXTERNAL_COMPUTE_DISABLE_ENV_VAR
    assert policy["activation_source"]["sha256"] == NON_L4_ACTIVATION_SOURCE_SHA256
    summary = non_l4_policy_summary(policy)
    assert tuple(summary["required_agent_ids"]) == NON_L4_REQUIRED_AGENT_IDS
    assert tuple(summary["optional_agent_ids"]) == NON_L4_OPTIONAL_AGENT_IDS
    enabled_ids = non_l4_policy_enabled_agent_ids(policy)
    assert set(enabled_ids) == set(NON_L4_REQUIRED_AGENT_IDS + NON_L4_OPTIONAL_AGENT_IDS)
    assert len(enabled_ids) == len(NON_L4_REQUIRED_AGENT_IDS + NON_L4_OPTIONAL_AGENT_IDS)


def test_non_l4_policy_entries_are_loopback_compute_only() -> None:
    entries = non_l4_external_compute_entries()
    all_entries = non_l4_external_compute_entries(include_disabled=True)

    assert entries["value_traditional_valuation"].base_url == "http://127.0.0.1:10000"
    assert entries["value_composite"].compute_path == "/v1/agent/compute"
    assert all_entries["macro_composite"].agent_id in non_l4_policy_enabled_agent_ids()


def test_non_l4_policy_rejects_duplicate_unknown_and_l4_agents() -> None:
    duplicate = _policy()
    duplicate["agents"].append(deepcopy(duplicate["agents"][0]))
    valid, reason = validate_non_l4_external_compute_policy(duplicate)
    assert not valid
    assert reason == "duplicate_agent_id"

    unknown = _policy()
    unknown["agents"][0]["agent_id"] = "unknown_agent"
    valid, reason = validate_non_l4_external_compute_policy(unknown)
    assert not valid
    assert reason == "unknown_agent:unknown_agent"

    l4 = _policy()
    l4["agents"][0]["agent_id"] = "decision_synthesizer"
    valid, reason = validate_non_l4_external_compute_policy(l4)
    assert not valid
    assert reason == "excluded_agent_present:decision_synthesizer"


def test_non_l4_policy_rejects_excluded_or_mismatched_agents() -> None:
    excluded = _policy()
    excluded["agents"][0]["agent_id"] = "market_fund_manager_behavior"
    valid, reason = validate_non_l4_external_compute_policy(excluded)
    assert not valid
    assert reason == "excluded_agent_present:market_fund_manager_behavior"

    layer = _policy()
    layer["agents"][0]["layer"] = "L3"
    valid, reason = validate_non_l4_external_compute_policy(layer)
    assert not valid
    assert reason == "layer_mismatch:value_traditional_valuation"

    dimension = _policy()
    dimension["agents"][0]["dimension"] = "market"
    valid, reason = validate_non_l4_external_compute_policy(dimension)
    assert not valid
    assert reason == "dimension_mismatch:value_traditional_valuation"


def test_non_l4_policy_rejects_bad_path_timeout_and_artifact_hash() -> None:
    path = _policy()
    path["agents"][0]["compute_path"] = "/v1/agent/invoke"
    valid, reason = validate_non_l4_external_compute_policy(path)
    assert not valid
    assert reason == "compute_path_invalid:value_traditional_valuation"

    timeout = _policy()
    timeout["agents"][0]["timeout_seconds"] = 120
    valid, reason = validate_non_l4_external_compute_policy(timeout)
    assert not valid
    assert reason == "timeout_out_of_bounds:value_traditional_valuation"

    artifact = _policy()
    artifact["activation_source"]["sha256"] = "bad"
    valid, reason = validate_non_l4_external_compute_policy(artifact)
    assert not valid
    assert reason == "activation_source_sha256_mismatch"


def test_non_l4_policy_requires_exact_required_and_optional_sets() -> None:
    missing_required = _policy()
    missing_required["agents"] = missing_required["agents"][1:]
    valid, reason = validate_non_l4_external_compute_policy(missing_required)
    assert not valid
    assert reason == "required_agent_set_mismatch"

    extra_optional = _policy()
    extra_optional["agents"][-1]["agent_id"] = "value_composite"
    valid, reason = validate_non_l4_external_compute_policy(extra_optional)
    assert not valid
    assert reason in {
        "duplicate_agent_id",
        "optional_agent_set_mismatch",
        "service_registry_ref_mismatch:value_composite",
    }
