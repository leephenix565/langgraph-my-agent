"""Constants for fixed-DAG runtime binding metadata."""

from pathlib import Path

FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION = "fixed_dag_runtime_bindings_v1"
FIXED_DAG_RUNTIME_BINDINGS_SOURCE = "config/fixed_dag/runtime_bindings.json"
L4_RUNTIME_BINDING_DRY_RUN_SCHEMA_VERSION = "fixed_dag_l4_runtime_binding_dry_run_v1"
L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION = (
    "fixed_dag_l4_runtime_review_evidence_package_v1"
)
L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION = (
    "fixed_dag_l4_runtime_binding_phase_plan_v1"
)
FIXED_DAG_RUNTIME_BINDINGS_PATH = (
    Path(__file__).resolve().parents[4]
    / "config"
    / "fixed_dag"
    / "runtime_bindings.json"
)
L4_RUNTIME_REVIEW_AGENT_IDS = ("decision_synthesizer", "report_generator")
L4_RUNTIME_REVIEW_REQUIREMENTS = (
    "provider_compute_pass",
    "transcript_safety_pass",
    "rollback_plan_ready",
    "operator_approval",
)
L4_RUNTIME_REVIEW_COMPUTE_TARGETS = {
    "decision_synthesizer": {
        "external_agent_id": "l4_decision_synthesizer",
        "compute_url": "http://127.0.0.1:10025/v1/agent/compute",
        "output_contract": "decision_result_v1",
    },
    "report_generator": {
        "external_agent_id": "l4_report_generator",
        "compute_url": "http://127.0.0.1:10026/v1/agent/compute",
        "output_contract": "report_result_v1",
    },
}
L4_REVIEW_EVIDENCE_SAFE_FIELDS = (
    "reference",
    "summary",
    "validated_by",
    "validated_at",
)
_L4_REVIEW_UNSAFE_TOKENS = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "env",
    "endpoint",
    "default_url",
    "raw_response",
    "raw_provider_response",
    "raw_external_json",
    "traceback",
    "chain_of_thought",
    "chain-of-thought",
    "cot",
    "/v1/agent/invoke",
)
VALID_RUNTIME_KINDS = {
    "deterministic_system",
    "deterministic_l1_bundle",
    "deterministic_composite",
    "deterministic_decision",
    "deterministic_report",
    "external_compute_default",
    "external_http_candidate",
    "pending_placeholder",
}
VALID_IMPLEMENTATION_STATUSES = {
    "deterministic_skeleton",
    "external_compute_default_enabled",
    "external_candidate_disabled",
    "pending_implementation",
}
REQUIRED_BINDING_FIELDS = {
    "agent_id",
    "runtime_kind",
    "implementation_status",
    "invoke_enabled_by_default",
    "live_verified",
    "legacy_agent_id",
    "external_agent_id",
    "env_var",
    "default_url",
    "input_contract",
    "output_contract",
    "notes",
    "routes_to",
}
EXTERNAL_CANDIDATE_STATUS = "external_candidate_disabled"
EXTERNAL_COMPUTE_DEFAULT_STATUS = "external_compute_default_enabled"
PENDING_PLACEHOLDER_STATUS = "pending_implementation"
DETERMINISTIC_STATUS = "deterministic_skeleton"

__all__ = [
    "DETERMINISTIC_STATUS",
    "EXTERNAL_CANDIDATE_STATUS",
    "EXTERNAL_COMPUTE_DEFAULT_STATUS",
    "FIXED_DAG_RUNTIME_BINDINGS_PATH",
    "FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION",
    "FIXED_DAG_RUNTIME_BINDINGS_SOURCE",
    "L4_REVIEW_EVIDENCE_SAFE_FIELDS",
    "L4_RUNTIME_BINDING_DRY_RUN_SCHEMA_VERSION",
    "L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION",
    "L4_RUNTIME_REVIEW_AGENT_IDS",
    "L4_RUNTIME_REVIEW_COMPUTE_TARGETS",
    "L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION",
    "L4_RUNTIME_REVIEW_REQUIREMENTS",
    "PENDING_PLACEHOLDER_STATUS",
    "REQUIRED_BINDING_FIELDS",
    "VALID_IMPLEMENTATION_STATUSES",
    "VALID_RUNTIME_KINDS",
]
