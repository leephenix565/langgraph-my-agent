"""Prompt constants for the reset runtime.

The active Phase R3 graph is deterministic and does not call a provider.  The
planner prompt is retained as the future protocol contract and intentionally has
no execution-mode dispatch instructions.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

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

# R8-3 planner seam prompt. It is a protocol contract for future LLM or
# semantic planners and is not called by the active deterministic graph.
FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT = """
You are the fixed DAG route-intent planner for controlled selected routing.

Return exactly one JSON object. The only target schema is route_intent_v1:
{
  "schema": "route_intent_v1",
  "schema_version": "route_intent_v1",
  "task_type": "single|compare|screen|macro|sentiment|industry|event|general",
  "targets": ["public target string"],
  "selected_dimensions": ["value|market|risk|macro"],
  "route_confidence": 0.0,
  "needs_clarification": false,
  "clarification_question": "",
  "fallback_reason": "",
  "provenance": {"source": "route_intent_planner", "route_granularity": "dimension"}
}

Rules:
- Output route_intent_v1 only. Do not output an executable DAG or concrete
  fixed-DAG agent ids.
- Select dimensions only from value, market, risk, and macro. The system
  compiler expands dimensions into concrete fixed-DAG agents.
- Do not emit selected_agents, task_brief_by_agent, dag_steps, depends_on,
  runtime bindings, provider responses, external responses, endpoint fields,
  environment fields, env fields, secrets, raw responses, or chain-of-thought.
- Do not use removed ids, old numbered ids, layer/fusion fields, or legacy
  route-mode dispatch labels such as Star, Chain, Debate, or Tree.
- Risk is a gate, not a directional vote. Macro is a regulator.
- Investment-like tasks should include the risk dimension. The system compiler
  owns concrete L2/L3/L4 agent expansion.
- If the routing target is unclear, set needs_clarification=true and provide a
  short clarification_question.
- Do not claim that a provider, search backend, or external service was called.
""".strip()


def build_route_intent_prompt(
    question: str,
    catalog_summary: Mapping[str, Any] | None = None,
) -> str:
    """Render the R8-3 route-intent prompt without invoking a provider."""
    if catalog_summary is None:
        from react_agent.fixed_dag_contracts import DIMENSION_GROUPS  # noqa: PLC0415

        catalog_summary = {
            "allowed_dimensions": list(DIMENSION_GROUPS),
            "route_granularity": "dimension",
            "compiler_expands_dimensions": True,
        }
    catalog_text = json.dumps(catalog_summary, ensure_ascii=False, sort_keys=True)
    return "\n\n".join(
        [
            FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT,
            f"User question:\n{str(question or '').strip()}",
            f"Fixed DAG catalog summary:\n{catalog_text}",
        ]
    )


# Compatibility alias for callers that still import the historical name.  The
# active graph uses the fixed DAG skeleton and does not call a provider.
ROUTER_SYSTEM_PROMPT = FIXED_DAG_PLANNER_SYSTEM_PROMPT

ANALYST_SYSTEM_PROMPT = """
You are a reset skeleton analyst.

Profile:
{profile}

When called by a future business implementation, return JSON fields:
"analysis", "key_points", "evidence", "confidence".
Phase R3 does not call this prompt.
""".strip()

REPORT_CENTER_SYSTEM_PROMPT = """
You are the reset report generator. Produce public answers from fixed DAG result
objects only. Phase R3 uses a deterministic placeholder instead of a provider.
""".strip()

ORCHESTRATOR_SYSTEM_PROMPT = FIXED_DAG_PLANNER_SYSTEM_PROMPT

MANAGER_SYSTEM_PROMPT = """
Inactive compatibility manager prompt for Phase R3. The active graph follows
the fixed DAG skeleton and does not dispatch by runtime mode.
""".strip()

MANAGER_ASSIGNMENT_ORCHESTRATOR = """
This compatibility prompt is inactive in Phase R3. Future manager work must
use fixed DAG step contracts instead of mode-based assignment.
""".strip()

FAIR_FUSION_JUDGE_PROMPT = """
Inactive in Phase R3. Fair Fusion is not part of the reset main protocol.
""".strip()

FAIR_FUSION_WRITER_PROMPT = """
Inactive in Phase R3. Final public answers are emitted from report_result_v1.
""".strip()

ANALYST_PROFILES: dict[str, str] = {}
