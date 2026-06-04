from copy import deepcopy
from pathlib import Path

from react_agent.external_http_agents import EXTERNAL_HTTP_AGENT_CONFIG
from react_agent.fixed_dag_catalog import fixed_dag_agent_by_id, fixed_dag_agent_ids
from react_agent.fixed_dag_runtime_registry import (
    FIXED_DAG_RUNTIME_BINDINGS_PATH,
    FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION,
    annotate_step_result_with_binding,
    binding_by_agent_id,
    external_candidate_bindings,
    fixed_dag_runtime_binding_ids,
    load_fixed_dag_runtime_bindings,
    runtime_binding_summary,
    validate_fixed_dag_runtime_bindings,
)


def test_runtime_binding_file_exists_and_matches_catalog() -> None:
    assert FIXED_DAG_RUNTIME_BINDINGS_PATH == Path(__file__).resolve().parents[2] / "config" / "fixed_dag" / "runtime_bindings.json"
    assert FIXED_DAG_RUNTIME_BINDINGS_PATH.exists()

    bindings = load_fixed_dag_runtime_bindings()
    valid, reason = validate_fixed_dag_runtime_bindings(bindings)
    ids = fixed_dag_runtime_binding_ids(bindings)

    assert valid, reason
    assert bindings["schema_version"] == FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION
    assert bindings["total_count"] == 27
    assert ids == fixed_dag_agent_ids()
    assert "value_financial_analysis" not in ids
    assert all(not agent_id.startswith("a") or not agent_id[1:3].isdigit() for agent_id in ids)


def test_runtime_binding_summary_splits_runtime_kinds_and_statuses() -> None:
    summary = runtime_binding_summary()

    assert summary["total_count"] == 27
    assert summary["runtime_kind_counts"] == {
        "deterministic_system": 1,
        "external_http_candidate": 11,
        "pending_placeholder": 9,
        "deterministic_composite": 4,
        "deterministic_decision": 1,
        "deterministic_report": 1,
    }
    assert summary["implementation_status_counts"] == {
        "deterministic_skeleton": 7,
        "external_candidate_disabled": 11,
        "pending_implementation": 9,
    }
    assert summary["external_candidate_count"] == 11
    assert summary["live_verified_count"] == 7
    assert summary["invoke_enabled_count"] == 6


def test_external_candidates_are_disabled_and_match_legacy_wrapper_config() -> None:
    for binding in external_candidate_bindings():
        legacy_agent_id = binding["legacy_agent_id"]
        assert legacy_agent_id in EXTERNAL_HTTP_AGENT_CONFIG
        config = EXTERNAL_HTTP_AGENT_CONFIG[legacy_agent_id]
        assert binding["implementation_status"] == "external_candidate_disabled"
        assert binding["invoke_enabled_by_default"] is False
        assert binding["live_verified"] is False
        assert binding["external_agent_id"] == config.external_agent_id
        assert binding["env_var"] == config.env_var
        assert binding["default_url"] == config.default_url

    value_composite = binding_by_agent_id("value_composite")
    assert value_composite["runtime_kind"] == "deterministic_composite"
    assert value_composite["legacy_agent_id"] == "a26_composite_valuation"
    assert value_composite["external_agent_id"] == "composite_valuation"
    assert value_composite["invoke_enabled_by_default"] is False
    assert "value_composite" not in {item["agent_id"] for item in external_candidate_bindings()}


def test_pending_placeholders_do_not_require_endpoints() -> None:
    pending = [
        binding
        for binding in load_fixed_dag_runtime_bindings()["bindings"]
        if binding["runtime_kind"] == "pending_placeholder"
    ]

    assert len(pending) == 9
    for binding in pending:
        assert binding["implementation_status"] == "pending_implementation"
        assert binding["invoke_enabled_by_default"] is False
        assert binding["live_verified"] is False
        assert binding["external_agent_id"] == ""
        assert binding["env_var"] == ""
        assert binding["default_url"] == ""


def test_runtime_bindings_preserve_catalog_routes_and_sentiment_boundary() -> None:
    catalog_by_id = fixed_dag_agent_by_id()
    bindings = {binding["agent_id"]: binding for binding in load_fixed_dag_runtime_bindings()["bindings"]}

    for agent_id, binding in bindings.items():
        assert binding["routes_to"] == catalog_by_id[agent_id]["downstream"]

    assert bindings["sentiment_company_radar"]["routes_to"] == ["market_composite"]
    assert bindings["sentiment_company_radar"]["runtime_kind"] == "pending_placeholder"
    assert "risk_composite" not in bindings["sentiment_company_radar"]["routes_to"]
    assert "sentiment_company_radar" not in catalog_by_id["risk_composite"]["upstream"]


def test_runtime_binding_validator_rejects_duplicate_id() -> None:
    bindings = deepcopy(load_fixed_dag_runtime_bindings())
    bindings["bindings"][1]["agent_id"] = bindings["bindings"][0]["agent_id"]

    valid, reason = validate_fixed_dag_runtime_bindings(bindings)

    assert not valid
    assert reason == "duplicate_agent_id"


def test_runtime_binding_validator_rejects_missing_or_extra_catalog_id() -> None:
    missing = deepcopy(load_fixed_dag_runtime_bindings())
    missing["bindings"] = missing["bindings"][:-1]
    valid, reason = validate_fixed_dag_runtime_bindings(missing)
    assert not valid
    assert reason == "bindings_count_mismatch"

    extra = deepcopy(load_fixed_dag_runtime_bindings())
    extra["bindings"][-1]["agent_id"] = "extra_runtime_agent"
    valid, reason = validate_fixed_dag_runtime_bindings(extra)
    assert not valid
    assert reason == "binding_ids_do_not_match_catalog"


def test_runtime_binding_validator_rejects_forbidden_primary_ids() -> None:
    value_financial = deepcopy(load_fixed_dag_runtime_bindings())
    value_financial["bindings"][0]["agent_id"] = "value_financial_analysis"
    valid, reason = validate_fixed_dag_runtime_bindings(value_financial)
    assert not valid
    assert reason == "forbidden_agent_id:value_financial_analysis"

    legacy_ann = deepcopy(load_fixed_dag_runtime_bindings())
    legacy_ann["bindings"][0]["agent_id"] = "a01_cio_orchestrator"
    valid, reason = validate_fixed_dag_runtime_bindings(legacy_ann)
    assert not valid
    assert reason == "legacy_ann_primary_id:a01_cio_orchestrator"


def test_runtime_binding_validator_rejects_enabled_external_candidate() -> None:
    bindings = deepcopy(load_fixed_dag_runtime_bindings())
    financial = next(item for item in bindings["bindings"] if item["agent_id"] == "financial_data_service")
    financial["invoke_enabled_by_default"] = True

    valid, reason = validate_fixed_dag_runtime_bindings(bindings)

    assert not valid
    assert reason == "external_candidate_invoke_enabled:financial_data_service"


def test_runtime_binding_validator_rejects_sentiment_risk_route() -> None:
    bindings = deepcopy(load_fixed_dag_runtime_bindings())
    sentiment = next(item for item in bindings["bindings"] if item["agent_id"] == "sentiment_company_radar")
    sentiment["routes_to"] = ["risk_composite"]

    valid, reason = validate_fixed_dag_runtime_bindings(bindings)

    assert not valid
    assert reason == "routes_to_mismatch:sentiment_company_radar"


def test_annotate_step_result_adds_binding_metadata_without_live_invocation() -> None:
    base = {
        "schema_version": "fixed_dag_step_result_v1",
        "step_id": "financial_data_service",
        "agent_id": "financial_data_service",
        "stage": "evidence",
        "dimension": "l1",
        "status": "pending_implementation",
        "depends_on": ["route_planner"],
        "output_ref": "data_bundle",
        "summary": "pending",
        "warnings": [],
    }

    result = annotate_step_result_with_binding(base)

    assert result["runtime_kind"] == "external_http_candidate"
    assert result["implementation_status"] == "external_candidate_disabled"
    assert result["binding_source"] == "config/fixed_dag/runtime_bindings.json"
    assert result["legacy_agent_id"] == "a22_financial_data_service"
    assert result["external_agent_id"] == "financial_data_service"
    assert result["invoke_enabled"] is False
    assert result["live_verified"] is False
