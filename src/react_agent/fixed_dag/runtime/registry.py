# ruff: noqa: D101, D103
"""Fixed DAG runtime binding registry compatibility facade.

The registry remains metadata-only.  The implementation is split under
``react_agent.fixed_dag.runtime`` while this module preserves the existing
import path for executor, tests, and external callers.
(Originally at ``fixed_dag_runtime_registry.py``, moved here during Phase 1
consolidation.)
"""

from __future__ import annotations

from react_agent.fixed_dag.runtime.annotation import annotate_step_result_with_binding
from react_agent.fixed_dag.runtime.bindings import (
    binding_by_agent_id,
    external_candidate_bindings,
    external_compute_default_agent_ids,
    external_compute_default_bindings,
    fixed_dag_runtime_binding_ids,
    fixed_dag_runtime_bindings,
    load_fixed_dag_runtime_bindings,
    runtime_binding_summary,
)
from react_agent.fixed_dag.runtime.constants import (
    DETERMINISTIC_STATUS,
    EXTERNAL_CANDIDATE_STATUS,
    EXTERNAL_COMPUTE_DEFAULT_STATUS,
    FIXED_DAG_RUNTIME_BINDINGS_PATH,
    FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION,
    FIXED_DAG_RUNTIME_BINDINGS_SOURCE,
    L4_REVIEW_EVIDENCE_SAFE_FIELDS,
    L4_RUNTIME_BINDING_DRY_RUN_SCHEMA_VERSION,
    L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION,
    L4_RUNTIME_REVIEW_AGENT_IDS,
    L4_RUNTIME_REVIEW_COMPUTE_TARGETS,
    L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION,
    L4_RUNTIME_REVIEW_REQUIREMENTS,
    PENDING_PLACEHOLDER_STATUS,
    REQUIRED_BINDING_FIELDS,
    VALID_IMPLEMENTATION_STATUSES,
    VALID_RUNTIME_KINDS,
)
from react_agent.fixed_dag.runtime.l4_review import (
    L4_RUNTIME_REVIEW_CANDIDATE_EVIDENCE,
    build_l4_runtime_binding_dry_run,
    build_l4_runtime_binding_phase_plan,
    build_l4_runtime_review_candidate_package,
    build_l4_runtime_review_evidence_package,
)
from react_agent.fixed_dag.runtime.types import (
    FixedDagRuntimeBinding,
    FixedDagRuntimeBindings,
)
from react_agent.fixed_dag.runtime.validation import (
    validate_fixed_dag_runtime_bindings,
)

__all__ = [
    "DETERMINISTIC_STATUS",
    "EXTERNAL_CANDIDATE_STATUS",
    "EXTERNAL_COMPUTE_DEFAULT_STATUS",
    "FIXED_DAG_RUNTIME_BINDINGS_PATH",
    "FIXED_DAG_RUNTIME_BINDINGS_SCHEMA_VERSION",
    "FIXED_DAG_RUNTIME_BINDINGS_SOURCE",
    "FixedDagRuntimeBinding",
    "FixedDagRuntimeBindings",
    "L4_REVIEW_EVIDENCE_SAFE_FIELDS",
    "L4_RUNTIME_BINDING_DRY_RUN_SCHEMA_VERSION",
    "L4_RUNTIME_BINDING_PHASE_PLAN_SCHEMA_VERSION",
    "L4_RUNTIME_REVIEW_AGENT_IDS",
    "L4_RUNTIME_REVIEW_CANDIDATE_EVIDENCE",
    "L4_RUNTIME_REVIEW_COMPUTE_TARGETS",
    "L4_RUNTIME_REVIEW_EVIDENCE_PACKAGE_SCHEMA_VERSION",
    "L4_RUNTIME_REVIEW_REQUIREMENTS",
    "PENDING_PLACEHOLDER_STATUS",
    "REQUIRED_BINDING_FIELDS",
    "VALID_IMPLEMENTATION_STATUSES",
    "VALID_RUNTIME_KINDS",
    "annotate_step_result_with_binding",
    "binding_by_agent_id",
    "build_l4_runtime_binding_dry_run",
    "build_l4_runtime_binding_phase_plan",
    "build_l4_runtime_review_candidate_package",
    "build_l4_runtime_review_evidence_package",
    "external_candidate_bindings",
    "external_compute_default_agent_ids",
    "external_compute_default_bindings",
    "fixed_dag_runtime_binding_ids",
    "fixed_dag_runtime_bindings",
    "load_fixed_dag_runtime_bindings",
    "runtime_binding_summary",
    "validate_fixed_dag_runtime_bindings",
]
