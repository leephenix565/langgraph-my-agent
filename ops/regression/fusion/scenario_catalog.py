"""Deterministic FF-5B fusion regression scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class FusionScenario:
    """A deterministic fusion regression case."""

    case_id: str
    description: str
    flags: Dict[str, Any]
    seed_state: Dict[str, Any]
    expected_source: str
    expected_terminal_statuses: Dict[str, str]
    expected_invariants: Dict[str, bool]


def _filtered_results() -> Dict[str, Any]:
    return {
        "a25_report_center": {
            "analysis": "mainline synthesized analysis",
            "key_points": ["Fact A"],
            "evidence": ["Evidence A"],
            "confidence": 0.91,
            "parse_ok": True,
        }
    }


def _mainline_bundle(question: str) -> Dict[str, Any]:
    return {
        "question": question,
        "answer": "mainline final answer",
        "summary_source": "manager_summary",
        "evidence_cards": [{"title": "m-card", "detail": "mainline evidence"}],
        "filtered_out": 0,
        "process_health": {"result_count": 1, "filtered_out": 0},
    }


def _mainline_emit_payload() -> Dict[str, Any]:
    return {
        "response_text": "mainline final answer",
        "layer_done": {"L1": True, "L2": True, "L3": True, "L4": True},
        "filtered_results": _filtered_results(),
        "summary_source": "manager_summary",
    }


def _baseline_bundle(question: str) -> Dict[str, Any]:
    return {
        "question": question,
        "answer": "baseline sidecar answer",
        "key_points": ["Baseline point"],
        "evidence_cards": [{"title": "b-card", "detail": "baseline evidence"}],
        "search_meta": {
            "provider": "google_genai",
            "search_binding": "gemini_google_search",
            "search_executed": True,
            "grounding_metadata_present": True,
        },
        "confidence": 0.62,
        "summary_source": "baseline_sidecar",
    }


def _fusion_verdict(decision: str) -> Dict[str, Any]:
    return {
        "decision": decision,
        "decision_reason": f"prefer {decision}",
        "winner_by_dimension": {
            "accuracy": "mainline",
            "coverage": "baseline",
        },
        "rewrite_plan": ["Preserve supported facts only."],
        "accepted_cards": [
            {"title": "m-card", "detail": "mainline evidence"},
            {"title": "b-card", "detail": "baseline evidence"},
        ],
        "must_keep_facts": ["Fact A"],
        "must_drop_facts": ["Fact B"],
        "confidence": 0.74,
    }


def _writer_output(selected_source: str) -> Dict[str, Any]:
    return {
        "proposed_answer": "writer proposed fused answer",
        "selected_source": selected_source,
        "accepted_cards": [
            {"title": "m-card", "detail": "mainline evidence"},
            {"title": "b-card", "detail": "baseline evidence"},
        ],
        "dropped_cards": ["drop-card"],
        "note": f"shadow writer selected {selected_source}",
    }


def _seed_state(
    *,
    question: str,
    baseline_status: str,
    baseline_bundle: Dict[str, Any],
    verdict_decision: str,
    writer_selected_source: str,
) -> Dict[str, Any]:
    return {
        "current_question": question,
        "current_layer": "L4",
        "multi_agent_bundle": _mainline_bundle(question),
        "mainline_status": "ready",
        "mainline_emit_payload": _mainline_emit_payload(),
        "baseline_status": baseline_status,
        "baseline_bundle": baseline_bundle,
        "judge_status": "ready",
        "fusion_verdict": _fusion_verdict(verdict_decision),
        "writer_status": "ready",
        "writer_output": _writer_output(writer_selected_source),
        "analyst_results": {},
        "ephemeral_results": {},
        "stable_findings": [],
        "thread_summary": "",
    }


def _flags(*, source_switch: bool, thread_summary: bool = False) -> Dict[str, Any]:
    return {
        "context": {
            "enable_fair_fusion": True,
            "enable_fair_fusion_source_switch": source_switch,
        },
        "env": {
            "REACT_AGENT_RESULTS_POOLS": "1",
            "REACT_AGENT_THREAD_SUMMARY": "1" if thread_summary else "0",
        },
    }


QUESTION = "demo question"


SCENARIOS: List[FusionScenario] = [
    FusionScenario(
        case_id="flag_off_mainline_lock",
        description="Source switch flag off keeps final visible answer on mainline even when shadow writer prefers fused.",
        flags=_flags(source_switch=False),
        seed_state=_seed_state(
            question=QUESTION,
            baseline_status="ready",
            baseline_bundle=_baseline_bundle(QUESTION),
            verdict_decision="fused",
            writer_selected_source="fused",
        ),
        expected_source="mainline",
        expected_terminal_statuses={
            "baseline_status": "ready",
            "judge_status": "ready",
            "writer_status": "ready",
        },
        expected_invariants={
            "route_after_gate_final_emit": True,
            "route_after_judge_final_emit": True,
            "route_after_writer_final_emit": True,
            "source_selection_alignment": True,
            "emitted_bundle_alignment": True,
            "stable_findings_alignment": True,
            "results_pool_isolation": True,
            "flag_off_mainline_lock": True,
        },
    ),
    FusionScenario(
        case_id="source_switch_baseline",
        description="Source switch flag on allows a baseline final emit when baseline is ready and the writer selects baseline.",
        flags=_flags(source_switch=True),
        seed_state=_seed_state(
            question=QUESTION,
            baseline_status="ready",
            baseline_bundle=_baseline_bundle(QUESTION),
            verdict_decision="baseline",
            writer_selected_source="baseline",
        ),
        expected_source="baseline",
        expected_terminal_statuses={
            "baseline_status": "ready",
            "judge_status": "ready",
            "writer_status": "ready",
        },
        expected_invariants={
            "route_after_gate_final_emit": True,
            "source_selection_alignment": True,
            "emitted_bundle_alignment": True,
            "stable_findings_alignment": True,
            "results_pool_isolation": True,
        },
    ),
    FusionScenario(
        case_id="source_switch_fused",
        description="Source switch flag on allows a fused final emit when the writer selects fused.",
        flags=_flags(source_switch=True),
        seed_state=_seed_state(
            question=QUESTION,
            baseline_status="ready",
            baseline_bundle=_baseline_bundle(QUESTION),
            verdict_decision="fused",
            writer_selected_source="fused",
        ),
        expected_source="fused",
        expected_terminal_statuses={
            "baseline_status": "ready",
            "judge_status": "ready",
            "writer_status": "ready",
        },
        expected_invariants={
            "route_after_gate_final_emit": True,
            "source_selection_alignment": True,
            "emitted_bundle_alignment": True,
            "stable_findings_alignment": True,
            "results_pool_isolation": True,
        },
    ),
    FusionScenario(
        case_id="baseline_error_fallback",
        description="A degraded baseline error path still falls back to a mainline final emit without polluting results pools.",
        flags=_flags(source_switch=True),
        seed_state=_seed_state(
            question=QUESTION,
            baseline_status="error",
            baseline_bundle={"error": "baseline boom"},
            verdict_decision="mainline",
            writer_selected_source="mainline",
        ),
        expected_source="mainline",
        expected_terminal_statuses={
            "baseline_status": "error",
            "judge_status": "ready",
            "writer_status": "ready",
        },
        expected_invariants={
            "route_after_gate_final_emit": True,
            "source_selection_alignment": True,
            "emitted_bundle_alignment": True,
            "stable_findings_alignment": True,
            "results_pool_isolation": True,
            "degraded_fallback_to_mainline": True,
        },
    ),
    FusionScenario(
        case_id="baseline_disabled_fallback",
        description="A disabled baseline path still falls back to a mainline final emit without polluting results pools.",
        flags=_flags(source_switch=True),
        seed_state=_seed_state(
            question=QUESTION,
            baseline_status="disabled",
            baseline_bundle={},
            verdict_decision="mainline",
            writer_selected_source="mainline",
        ),
        expected_source="mainline",
        expected_terminal_statuses={
            "baseline_status": "disabled",
            "judge_status": "ready",
            "writer_status": "ready",
        },
        expected_invariants={
            "route_after_gate_final_emit": True,
            "source_selection_alignment": True,
            "emitted_bundle_alignment": True,
            "stable_findings_alignment": True,
            "results_pool_isolation": True,
            "degraded_fallback_to_mainline": True,
        },
    ),
    FusionScenario(
        case_id="invalid_selected_source_fallback",
        description="An invalid selected_source falls back to mainline even when source switching is enabled.",
        flags=_flags(source_switch=True),
        seed_state=_seed_state(
            question=QUESTION,
            baseline_status="ready",
            baseline_bundle=_baseline_bundle(QUESTION),
            verdict_decision="unknown",
            writer_selected_source="unknown",
        ),
        expected_source="mainline",
        expected_terminal_statuses={
            "baseline_status": "ready",
            "judge_status": "ready",
            "writer_status": "ready",
        },
        expected_invariants={
            "route_after_gate_final_emit": True,
            "source_selection_alignment": True,
            "emitted_bundle_alignment": True,
            "stable_findings_alignment": True,
            "results_pool_isolation": True,
            "degraded_fallback_to_mainline": True,
        },
    ),
    FusionScenario(
        case_id="results_pool_isolation",
        description="Final emit and deterministic harness preserve baseline/fusion isolation from analyst and ephemeral result pools.",
        flags=_flags(source_switch=True),
        seed_state=_seed_state(
            question=QUESTION,
            baseline_status="ready",
            baseline_bundle=_baseline_bundle(QUESTION),
            verdict_decision="mainline",
            writer_selected_source="mainline",
        ),
        expected_source="mainline",
        expected_terminal_statuses={
            "baseline_status": "ready",
            "judge_status": "ready",
            "writer_status": "ready",
        },
        expected_invariants={
            "route_after_gate_final_emit": True,
            "source_selection_alignment": True,
            "emitted_bundle_alignment": True,
            "stable_findings_alignment": True,
            "results_pool_isolation": True,
        },
    ),
    FusionScenario(
        case_id="stable_findings_alignment",
        description="Stable findings follow the final emitted baseline answer rather than always the staged mainline answer.",
        flags=_flags(source_switch=True),
        seed_state=_seed_state(
            question=QUESTION,
            baseline_status="ready",
            baseline_bundle=_baseline_bundle(QUESTION),
            verdict_decision="baseline",
            writer_selected_source="baseline",
        ),
        expected_source="baseline",
        expected_terminal_statuses={
            "baseline_status": "ready",
            "judge_status": "ready",
            "writer_status": "ready",
        },
        expected_invariants={
            "route_after_gate_final_emit": True,
            "source_selection_alignment": True,
            "emitted_bundle_alignment": True,
            "stable_findings_alignment": True,
            "results_pool_isolation": True,
        },
    ),
    FusionScenario(
        case_id="thread_summary_alignment",
        description="Optional thread summary follows the final emitted fused answer rather than the staged mainline answer.",
        flags=_flags(source_switch=True, thread_summary=True),
        seed_state=_seed_state(
            question=QUESTION,
            baseline_status="ready",
            baseline_bundle=_baseline_bundle(QUESTION),
            verdict_decision="fused",
            writer_selected_source="fused",
        ),
        expected_source="fused",
        expected_terminal_statuses={
            "baseline_status": "ready",
            "judge_status": "ready",
            "writer_status": "ready",
        },
        expected_invariants={
            "route_after_gate_final_emit": True,
            "source_selection_alignment": True,
            "emitted_bundle_alignment": True,
            "stable_findings_alignment": True,
            "thread_summary_alignment": True,
            "results_pool_isolation": True,
        },
    ),
]
