"""Fixed-DAG contracts compatibility package.

Split into sub-modules during Phase 2 consolidation. All names
re-exported for backward compatibility.
"""

from __future__ import annotations

# Re-exported constants and labels from the fixed_dag package
from react_agent.fixed_dag.constants import (  # noqa: F401
    AGENT_DIMENSIONS,
    AGENT_EVIDENCE_BUNDLE_SCHEMA_VERSION,
    AGENT_TASK_SCHEMA_VERSION,
    CONCLUSION_OBJECT_SCHEMA_VERSION,
    DATA_BUNDLE_SCHEMA_VERSION,
    DECISION_RESULT_SCHEMA_VERSION,
    DEFAULT_AS_OF,
    DIMENSION_COMPOSITE_AGENT_IDS,
    DIMENSION_COMPOSITE_SCHEMA_VERSION,
    DIMENSION_GROUPS,
    ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
    EXECUTED_STEP_STATUSES,
    FIXED_DAG_SCHEMA_VERSION,
    FIXED_DAG_STAGE_ORDER,
    INVESTMENT_JUDGMENT_TASK_TYPES,
    L1_AGENT_IDS,
    L2_CONCLUSION_AGENT_IDS,
    L3_COMPOSITE_AGENT_IDS,
    L4_AGENT_IDS,
    MACRO_AGENT_IDS,
    MARKET_AGENT_IDS,
    REPORT_INPUT_BUNDLE_SCHEMA_VERSION,
    REPORT_RESULT_SCHEMA_VERSION,
    RESET_RUNTIME_AGENT_IDS,
    RESET_SOURCE,
    RISK_AGENT_IDS,
    ROUTE_INTENT_SCHEMA_VERSION,
    ROUTE_TASK_TYPES,
    SELECTED_FIXED_DAG_SCHEMA_VERSION,
    SELECTED_PLAN_FALLBACK_TARGETS,
    SENTIMENT_COMPANY_RADAR_OUTPUT_ROUTES,
    VALUE_AGENT_IDS,
    WORKFLOW_SNAPSHOT_SCHEMA_VERSION,
)
from react_agent.fixed_dag.labels import (  # noqa: F401
    AGENT_TITLE_LABELS,
    DIMENSION_TITLE_LABELS,
    STAGE_TITLE_LABELS,
)
from react_agent.fixed_dag.safety import (  # noqa: F401
    LEGACY_CONTRACT_KEYS,
    LEGACY_DISPATCH_VALUES,
    REPORT_BUNDLE_UNSAFE_KEYS,
    SELECTED_PLAN_FORBIDDEN_KEYS,
    SELECTED_PLAN_PUBLIC_UNSAFE_TEXT_TOKENS,
    _safe_public_detail_value,
    _looks_like_legacy_agent_id,
    _contains_legacy_dispatch_value,
    _contains_legacy_key,
    _contains_selected_plan_forbidden_key,
    _contains_unsafe_report_key,
)
from react_agent.fixed_dag.types import (  # noqa: F401
    AgentTask,
    ConclusionObject,
    ConclusionStatus,
    DataBundle,
    DecisionResult,
    DimensionCompositeResult,
    DimensionName,
    EntityRelationBundle,
    FixedDagDimension,
    FixedDagPlan,
    FixedDagStage,
    FixedDagStep,
    FixedDagStepStatus,
    ReportInputBundle,
    ReportResult,
    RouteIntent,
    RouteTaskType,
    SelectedFixedDagPlan,
)

# Re-export everything from sub-modules for backward compat
from react_agent.fixed_dag.contracts.helpers import *  # noqa: F401, F403
from react_agent.fixed_dag.contracts.plan import *  # noqa: F401, F403
from react_agent.fixed_dag.contracts.composite import *  # noqa: F401, F403
from react_agent.fixed_dag.contracts.report import *  # noqa: F401, F403
from react_agent.fixed_dag.contracts.workflow import *  # noqa: F401, F403

# Explicit re-export of private names (not covered by `import *`)
from react_agent.fixed_dag.contracts.report import (  # noqa: F401
    _has_report_material,
    _report_bundle_sections,
)
from react_agent.fixed_dag.contracts.workflow import (  # noqa: F401
    _completed_from_payloads,
    _completed_from_step_results,
    _step_status_from_results,
    _dimension_group_summary,
)

# Dynamic __all__ matching the original fixed_dag_contracts.py pattern
__all__ = sorted(
    name
    for name in globals()
    if not name.startswith("_")
    and name not in {"Any", "Mapping", "cast", "json", "re"}
)
