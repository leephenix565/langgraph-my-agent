# ruff: noqa: D101, D103
"""Backward-compatibility shim — moved to ``fixed_dag/contracts/``."""

from react_agent.fixed_dag.contracts import *  # noqa: F401, F403
from react_agent.fixed_dag.contracts import __all__  # noqa: F401
from react_agent.fixed_dag.contracts.report import (  # noqa: F401
    _has_report_material,
    _report_bundle_sections,
)
from react_agent.fixed_dag.contracts.workflow import (  # noqa: F401
    _completed_from_payloads,
    _completed_from_step_results,
    _dimension_group_summary,
    _step_status_from_results,
)

# Explicit re-exports of private names (not covered by `import *`)
from react_agent.fixed_dag.safety import (  # noqa: F401
    LEGACY_CONTRACT_KEYS,
    LEGACY_DISPATCH_VALUES,
    SELECTED_PLAN_FORBIDDEN_KEYS,
    SELECTED_PLAN_PUBLIC_UNSAFE_TEXT_TOKENS,
    _contains_legacy_dispatch_value,
    _contains_legacy_key,
    _contains_public_unsafe_text,
    _contains_selected_plan_forbidden_key,
    _contains_unsafe_report_key,
    _looks_like_legacy_agent_id,
    _safe_public_detail_value,
)
