from copy import deepcopy
from pathlib import Path

from react_agent.external_http_config import EXTERNAL_HTTP_AGENT_CONFIG
from react_agent.fixed_dag_catalog import fixed_dag_agent_by_id, fixed_dag_agent_ids
from react_agent.fixed_dag_runtime_registry import (
    FIXED_DAG_RUNTIME_BINDINGS_PATH,
    FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION,
    L4_RUNTIME_BINDING_DRY_RUN_SCHEMA_VERSION,
    L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION,
    L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION,
    annotate_step_result_with_binding,
    binding_by_agent_id,
    build_l4_runtime_binding_dry_run,
    build_l4_runtime_binding_phase_plan,
    build_l4_runtime_review_candidate_package,
    build_l4_runtime_review_evidence_package,
    external_candidate_bindings,
    external_compute_default_agent_ids,
    fixed_dag_runtime_binding_ids,
    load_fixed_dag_runtime_bindings,
    runtime_binding_summary,
    validate_fixed_dag_runtime_bindings,
)


def test_runtime_registry_facade_preserves_new_module_symbols() -> None:
    import react_agent.fixed_dag_runtime_registry as registry
    from react_agent.fixed_dag.runtime import (
        annotation,
        bindings,
        constants,
        l4_review,
        types,
        validation,
    )

    assert (
        registry.FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION
        == constants.FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION
    )
    assert registry.FixedDagRuntimeBinding is types.FixedDagRuntimeBinding
    assert registry.load_fixed_dag_runtime_bindings is bindings.load_fixed_dag_runtime_bindings
    assert registry.binding_by_agent_id is bindings.binding_by_agent_id
    assert registry.validate_fixed_dag_runtime_bindings is validation.validate_fixed_dag_runtime_bindings
    assert registry.annotate_step_result_with_binding is annotation.annotate_step_result_with_binding
    assert registry.build_l4_runtime_binding_dry_run is l4_review.build_l4_runtime_binding_dry_run


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
        "external_compute_default": 2,
    }
    assert summary["implementation_status_counts"] == {
        "deterministic_skeleton": 5,
        "external_compute_default_enabled": 2,
        "external_candidate_disabled": 11,
        "pending_implementation": 9,
    }
    assert summary["external_candidate_count"] == 11
    assert summary["external_compute_default_count"] == 2
    assert summary["live_verified_count"] == 7
    assert summary["invoke_enabled_count"] == 4


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


def test_l4_bindings_are_external_compute_default_after_runtime_phase() -> None:
    decision = binding_by_agent_id("decision_synthesizer")
    report = binding_by_agent_id("report_generator")

    assert decision["runtime_kind"] == "external_compute_default"
    assert report["runtime_kind"] == "external_compute_default"
    assert decision["implementation_status"] == "external_compute_default_enabled"
    assert report["implementation_status"] == "external_compute_default_enabled"
    assert decision["invoke_enabled_by_default"] is False
    assert report["invoke_enabled_by_default"] is False
    assert decision["live_verified"] is True
    assert report["live_verified"] is True
    assert decision["external_agent_id"] == "l4_decision_synthesizer"
    assert report["external_agent_id"] == "l4_report_generator"
    assert decision["default_url"].endswith(":10025/v1/agent/compute")
    assert report["default_url"].endswith(":10026/v1/agent/compute")
    assert external_compute_default_agent_ids() == (
        "decision_synthesizer",
        "report_generator",
    )


def test_l4_runtime_binding_dry_run_blocks_without_required_evidence() -> None:
    dry_run = build_l4_runtime_binding_dry_run()

    assert dry_run["schema_version"] == L4_RUNTIME_BINDING_DRY_RUN_SCHEMA_VERSION
    assert dry_run["status"] == "blocked_pending_requirements"
    assert dry_run["runtime_bindings_changed"] is False
    assert dry_run["default_runtime_enabled"] is True
    assert dry_run["invoke_endpoint_required"] is False
    assert dry_run["recommended_next_action"] == "do_not_edit_runtime_bindings"
    assert dry_run["blocking_reasons"] == [
        "provider_compute_pass_missing",
        "transcript_safety_pass_missing",
        "rollback_plan_ready_missing",
        "operator_approval_missing",
    ]
    by_agent = {item["agent_id"]: item for item in dry_run["agents"]}
    assert (
        by_agent["decision_synthesizer"]["current_binding_scope"]
        == "external_l4_compute_default"
    )
    assert by_agent["decision_synthesizer"]["current_runtime_kind"] == "external_compute_default"
    assert by_agent["report_generator"]["current_runtime_kind"] == "external_compute_default"
    assert by_agent["decision_synthesizer"]["current_external_agent_id"] == "l4_decision_synthesizer"
    assert by_agent["report_generator"]["current_external_agent_id"] == "l4_report_generator"
    assert by_agent["decision_synthesizer"]["default_binding_currently_external"] is True
    assert by_agent["decision_synthesizer"]["binding_edit_required"] is False
    assert by_agent["decision_synthesizer"]["proposed_external_live_verified"] is False
    assert (
        by_agent["decision_synthesizer"][
            "proposed_external_invoke_enabled_by_default"
        ]
        is False
    )
    assert by_agent["decision_synthesizer"]["proposed_compute_url"].endswith(
        ":10025/v1/agent/compute"
    )
    assert by_agent["report_generator"]["proposed_compute_url"].endswith(
        ":10026/v1/agent/compute"
    )


def test_l4_runtime_binding_dry_run_ready_state_is_still_metadata_only() -> None:
    dry_run = build_l4_runtime_binding_dry_run(
        provider_compute_pass=True,
        transcript_safety_pass=True,
        rollback_plan_ready=True,
        operator_approval=True,
    )

    assert dry_run["status"] == "ready_for_runtime_binding_review"
    assert dry_run["runtime_bindings_changed"] is False
    assert dry_run["default_runtime_enabled"] is True
    assert dry_run["invoke_endpoint_required"] is False
    assert dry_run["blocking_reasons"] == []
    assert dry_run["recommended_next_action"] == "open_explicit_runtime_binding_phase"
    assert all(not item["binding_edit_required"] for item in dry_run["agents"])
    assert all(
        item["proposed_external_live_verified"] is False
        for item in dry_run["agents"]
    )
    assert all(
        item["proposed_external_invoke_enabled_by_default"] is False
        for item in dry_run["agents"]
    )


def test_l4_runtime_review_evidence_package_blocks_without_evidence() -> None:
    package = build_l4_runtime_review_evidence_package()

    assert package["schema_version"] == L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION
    assert package["status"] == "blocked_pending_evidence"
    assert package["runtime_bindings_changed"] is False
    assert package["default_runtime_enabled"] is True
    assert package["invoke_endpoint_required"] is False
    assert package["recommended_next_action"] == "collect_missing_l4_runtime_review_evidence"
    assert package["missing_evidence"] == [
        {
            "requirement": "provider_compute_pass",
            "status": "missing",
            "reason": "missing_evidence_record",
        },
        {
            "requirement": "transcript_safety_pass",
            "status": "missing",
            "reason": "missing_evidence_record",
        },
        {
            "requirement": "rollback_plan_ready",
            "status": "missing",
            "reason": "missing_evidence_record",
        },
        {
            "requirement": "operator_approval",
            "status": "missing",
            "reason": "missing_evidence_record",
        },
    ]
    assert package["dry_run"]["status"] == "blocked_pending_requirements"
    assert "no_runtime_bindings_edit" in package["non_actions"]


def test_l4_runtime_review_evidence_package_rejects_unsafe_or_weak_records() -> None:
    package = build_l4_runtime_review_evidence_package(
        evidence={
            "provider_compute_pass": {
                "passed": True,
                "reference": "docs/CONTROLLED_READINESS_SMOKE_LOG.md#r8-13j",
                "summary": "provider compute smoke passed",
            },
            "transcript_safety_pass": {
                "passed": True,
                "reference": "http://127.0.0.1:10026/v1/agent/compute",
                "summary": "raw_response traceback secret",
            },
            "rollback_plan_ready": {
                "passed": True,
                "summary": "rollback is described but no artifact reference",
            },
            "operator_approval": {
                "passed": False,
                "reference": "operator approval is still pending",
            },
        }
    )

    assert package["status"] == "blocked_pending_evidence"
    missing_by_requirement = {
        item["requirement"]: item
        for item in package["missing_evidence"]
    }
    assert missing_by_requirement["transcript_safety_pass"]["reason"] == "missing_or_unsafe_reference"
    assert missing_by_requirement["rollback_plan_ready"]["reason"] == "missing_or_unsafe_reference"
    assert missing_by_requirement["operator_approval"]["reason"] == "evidence_not_passed"
    rendered = repr(package["required_evidence"])
    assert "raw_response" not in rendered
    assert "secret" not in rendered
    assert "http://127.0.0.1" not in rendered
    assert package["dry_run"]["blocking_reasons"] == [
        "transcript_safety_pass_missing",
        "rollback_plan_ready_missing",
        "operator_approval_missing",
    ]


def test_l4_runtime_review_evidence_package_ready_is_still_metadata_only() -> None:
    package = build_l4_runtime_review_evidence_package(
        evidence={
            "provider_compute_pass": {
                "passed": True,
                "reference": "docs/CONTROLLED_READINESS_SMOKE_LOG.md#r8-13j",
                "summary": "provider-backed compute evidence is recorded",
                "validated_by": "codex",
                "validated_at": "2026-06-19",
            },
            "transcript_safety_pass": {
                "passed": True,
                "reference": "tests/unit_tests/test_fixed_dag_external_adapter.py",
                "summary": "adapter rejects unsafe L4 public payloads",
            },
            "rollback_plan_ready": {
                "passed": True,
                "reference": "docs/CONTRACTS.md#l4-service-handoff",
                "summary": "fallback and rollback boundary is documented",
            },
            "operator_approval": {
                "passed": True,
                "reference": "operator-approval:2026-06-19:l4-runtime-review",
                "summary": "operator approved opening a runtime binding phase",
            },
        }
    )

    assert package["status"] == "ready_for_explicit_runtime_binding_phase"
    assert package["runtime_bindings_changed"] is False
    assert package["default_runtime_enabled"] is True
    assert package["invoke_endpoint_required"] is False
    assert package["missing_evidence"] == []
    assert package["dry_run"]["status"] == "ready_for_runtime_binding_review"
    assert package["dry_run"]["runtime_bindings_changed"] is False
    assert package["dry_run"]["default_runtime_enabled"] is True
    assert all(
        item["proposed_external_live_verified"] is False
        for item in package["dry_run"]["agents"]
    )
    assert all(
        item["proposed_external_invoke_enabled_by_default"] is False
        for item in package["dry_run"]["agents"]
    )
    assert package["recommended_next_action"] == "open_explicit_runtime_binding_phase"


def test_l4_runtime_review_candidate_package_is_ready_after_operator_approval() -> None:
    package = build_l4_runtime_review_candidate_package()

    assert package["schema_version"] == L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION
    assert package["status"] == "ready_for_explicit_runtime_binding_phase"
    assert package["runtime_bindings_changed"] is False
    assert package["default_runtime_enabled"] is True
    assert package["invoke_endpoint_required"] is False
    assert package["missing_evidence"] == []
    passed = {
        item["requirement"]
        for item in package["required_evidence"]
        if item["status"] == "pass"
    }
    assert passed == {
        "provider_compute_pass",
        "transcript_safety_pass",
        "rollback_plan_ready",
        "operator_approval",
    }
    assert package["dry_run"]["blocking_reasons"] == []
    assert package["recommended_next_action"] == "open_explicit_runtime_binding_phase"


def test_l4_runtime_binding_phase_plan_reports_configured_pending_smoke() -> None:
    plan = build_l4_runtime_binding_phase_plan()

    assert plan["schema_version"] == L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION
    assert plan["status"] == "runtime_binding_configured_pending_smoke"
    assert plan["runtime_bindings_changed"] is False
    assert plan["config_edit_allowed"] is False
    assert plan["current_schema_allows_external_l4_default"] is True
    assert plan["missing_evidence"] == []
    assert plan["required_work"] == ["run_default_l4_compute_runtime_smoke"]
    assert {
        item["agent_id"]
        for item in plan["planned_agent_changes"]
    } == {"decision_synthesizer", "report_generator"}
    assert all(
        item["target_endpoint_kind"] == "compute_only"
        for item in plan["planned_agent_changes"]
    )
    assert all(
        item["invoke_endpoint_required"] is False
        for item in plan["planned_agent_changes"]
    )


def test_l4_runtime_binding_phase_plan_ready_package_reports_existing_config() -> None:
    package = build_l4_runtime_review_evidence_package(
        evidence={
            "provider_compute_pass": {
                "passed": True,
                "reference": "docs/CONTROLLED_READINESS_SMOKE_LOG.md#r8-13j",
            },
            "transcript_safety_pass": {
                "passed": True,
                "reference": "tests/unit_tests/test_fixed_dag_external_adapter.py",
            },
            "rollback_plan_ready": {
                "passed": True,
                "reference": "docs/L4_RUNTIME_REVIEW_EVIDENCE_R8_13O.md",
            },
            "operator_approval": {
                "passed": True,
                "reference": "operator-approval:2026-06-19:l4-runtime-review",
            },
        }
    )

    plan = build_l4_runtime_binding_phase_plan(evidence_package=package)

    assert plan["status"] == "runtime_binding_configured_pending_smoke"
    assert plan["runtime_bindings_changed"] is False
    assert plan["config_edit_allowed"] is False
    assert plan["current_schema_allows_external_l4_default"] is True
    assert plan["missing_evidence"] == []
    assert plan["required_work"] == ["run_default_l4_compute_runtime_smoke"]
    by_agent = {item["agent_id"]: item for item in plan["planned_agent_changes"]}
    assert by_agent["decision_synthesizer"]["target_runtime_kind"] == "external_compute_default"
    assert by_agent["report_generator"]["target_runtime_kind"] == "external_compute_default"
    assert by_agent["decision_synthesizer"]["already_configured"] is True
    assert by_agent["report_generator"]["already_configured"] is True
    assert by_agent["decision_synthesizer"]["binding_edit_required"] is False
    assert by_agent["report_generator"]["binding_edit_required"] is False
    assert by_agent["decision_synthesizer"]["requires_runtime_schema_extension"] is False
    assert by_agent["report_generator"]["requires_executor_default_path"] is False


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


def test_runtime_binding_validator_rejects_non_l4_external_compute_default() -> None:
    bindings = deepcopy(load_fixed_dag_runtime_bindings())
    financial = next(
        item for item in bindings["bindings"] if item["agent_id"] == "financial_data_service"
    )
    financial.update(
        {
            "runtime_kind": "external_compute_default",
            "implementation_status": "external_compute_default_enabled",
            "live_verified": True,
            "external_agent_id": "financial_data_service",
            "env_var": "FINANCIAL_DATA_SERVICE_COMPUTE_URL",
            "default_url": "http://127.0.0.1:11000/v1/agent/compute",
        }
    )

    valid, reason = validate_fixed_dag_runtime_bindings(bindings)

    assert not valid
    assert reason == "external_compute_default_not_l4:financial_data_service"


def test_runtime_binding_validator_rejects_l4_external_compute_default_invoke_url() -> None:
    bindings = deepcopy(load_fixed_dag_runtime_bindings())
    decision = next(
        item for item in bindings["bindings"] if item["agent_id"] == "decision_synthesizer"
    )
    decision["default_url"] = "http://127.0.0.1:10025/v1/agent/invoke"

    valid, reason = validate_fixed_dag_runtime_bindings(bindings)

    assert not valid
    assert reason == "external_compute_default_url_not_compute:decision_synthesizer"


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


def test_annotate_step_result_adds_l4_default_runtime_metadata() -> None:
    for agent_id, external_agent_id in (
        ("decision_synthesizer", "l4_decision_synthesizer"),
        ("report_generator", "l4_report_generator"),
    ):
        result = annotate_step_result_with_binding(
            {
                "schema_version": "fixed_dag_step_result_v1",
                "step_id": agent_id,
                "agent_id": agent_id,
                "stage": "l4_synthesis",
                "dimension": "l4",
                "status": "complete",
                "depends_on": [],
                "output_ref": agent_id,
                "summary": "complete",
                "warnings": [],
            }
        )

        assert result["runtime_kind"] == "external_compute_default"
        assert result["implementation_status"] == "external_compute_default_enabled"
        assert result["binding_source"] == "config/fixed_dag/runtime_bindings.json"
        assert result["external_agent_id"] == external_agent_id
        assert result["invoke_enabled"] is False
        assert result["live_verified"] is True
