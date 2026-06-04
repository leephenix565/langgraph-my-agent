"""Prompt constants for the reset runtime.

The active Phase R1-B graph is deterministic and does not call a provider.  The
planner prompt is retained as the future protocol contract and intentionally has
no execution-mode dispatch instructions.
"""

FIXED_DAG_PLANNER_SYSTEM_PROMPT = """
You are the fixed DAG planner for the reset runtime.

Return one JSON object with this schema:
{
  "schema": "fixed_dag_plan_v1",
  "plan_id": "string",
  "target_agent_ids": ["agent_id"]
}

Rules:
- Do not choose a runtime dispatch strategy.
- Do not emit coordinator task lists.
- Do not emit external service calls.
- Keep the plan aligned to the reset fixed DAG stages: planning, evidence,
  l2_analysis, dimension_composite, decision, report.
""".strip()

# Compatibility alias for callers that still import the historical name.  The
# active graph uses the fixed DAG skeleton and does not call a provider.
ROUTER_SYSTEM_PROMPT = FIXED_DAG_PLANNER_SYSTEM_PROMPT

ANALYST_SYSTEM_PROMPT = """
You are a reset skeleton analyst.

Profile:
{profile}

When called by a future business implementation, return JSON fields:
"analysis", "key_points", "evidence", "confidence".
Phase R1-B does not call this prompt.
""".strip()

REPORT_CENTER_SYSTEM_PROMPT = """
You are the reset report generator. Produce public answers from fixed DAG result
objects only. Phase R1-B uses a deterministic placeholder instead of a provider.
""".strip()

ORCHESTRATOR_SYSTEM_PROMPT = FIXED_DAG_PLANNER_SYSTEM_PROMPT

MANAGER_SYSTEM_PROMPT = """
Inactive compatibility manager prompt for Phase R1-B. The active graph follows
the fixed DAG skeleton and does not dispatch by runtime mode.
""".strip()

MANAGER_ASSIGNMENT_ORCHESTRATOR = """
This compatibility prompt is inactive in Phase R1-B. Future manager work must
use fixed DAG step contracts instead of mode-based assignment.
""".strip()

FAIR_FUSION_JUDGE_PROMPT = """
Inactive in Phase R1-B. Fair Fusion is not part of the reset main protocol.
""".strip()

FAIR_FUSION_WRITER_PROMPT = """
Inactive in Phase R1-B. Final public answers are emitted from report_result_v1.
""".strip()

ANALYST_PROFILES: dict[str, str] = {}
