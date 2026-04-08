#!/usr/bin/env python
"""Run deterministic FF-5B fusion regression scenarios."""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

from langchain_core.messages import AIMessage, HumanMessage

from .scenario_catalog import FusionScenario, SCENARIOS


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _load_runtime_modules():
    os.environ.setdefault("TAVILY_API_KEY", "ff5b-dummy-key")
    from react_agent.context import Context
    from react_agent import graph as graph_mod

    return Context, graph_mod


@contextmanager
def _temp_env(overrides: Mapping[str, str]) -> Iterator[None]:
    old_values: Dict[str, Optional[str]] = {}
    for key, value in overrides.items():
        old_values[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, old in old_values.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_runtime_state(seed_state: Mapping[str, Any], *, run_id: str) -> Dict[str, Any]:
    question = str(seed_state.get("current_question", "") or "")
    state = copy.deepcopy(dict(seed_state))
    state.setdefault("messages", [HumanMessage(content=question)])
    state.setdefault("current_question", question)
    state.setdefault("current_layer", "L4")
    state.setdefault("run_id", run_id)
    state.setdefault("is_last_step", False)
    state.setdefault("final_answer_source", "")
    state.setdefault("emitted_bundle", {})
    state.setdefault("final_emit_payload", {})
    state.setdefault("stable_findings", [])
    state.setdefault("thread_summary", "")
    state.setdefault("analyst_results", {})
    state.setdefault("ephemeral_results", {})
    state.setdefault("layer_done", {})
    return state


def _append_messages(existing: Iterable[Any], new_messages: Iterable[Any]) -> List[Any]:
    merged = list(existing)
    merged.extend(list(new_messages))
    return merged


def _materialize_emit_payload(graph_mod, state: Dict[str, Any], context) -> Dict[str, Any]:
    mainline_bundle = state.get("multi_agent_bundle", {})
    writer_output = state.get("writer_output", {})
    fusion_verdict = state.get("fusion_verdict", {})
    payload = graph_mod._build_final_emit_payload(  # type: ignore[attr-defined]
        state=state,
        mainline_bundle=mainline_bundle if isinstance(mainline_bundle, dict) else {},
        selected_source="mainline",
        source_switch_enabled=context.enable_fair_fusion_source_switch,
        writer_output=writer_output if isinstance(writer_output, dict) else {},
        writer_status=str(state.get("writer_status", "") or ""),
        fusion_verdict=fusion_verdict if isinstance(fusion_verdict, dict) else {},
        judge_status=str(state.get("judge_status", "") or ""),
    )
    return payload


def _summarize_bundle(bundle: Mapping[str, Any]) -> Dict[str, Any]:
    evidence = bundle.get("evidence_cards", [])
    accepted_cards = bundle.get("accepted_cards", [])
    return {
        "question": str(bundle.get("question", "") or ""),
        "answer": str(bundle.get("answer", "") or ""),
        "summary_source": str(bundle.get("summary_source", "") or ""),
        "evidence_count": len(evidence) if isinstance(evidence, list) else 0,
        "accepted_cards_count": len(accepted_cards) if isinstance(accepted_cards, list) else 0,
        "confidence": bundle.get("confidence"),
    }


def _summarize_message(message: Any) -> Dict[str, Any]:
    text = ""
    if isinstance(message, AIMessage):
        text = str(message.content or "")
    elif hasattr(message, "content"):
        text = str(getattr(message, "content") or "")
    return {
        "text": text,
        "char_len": len(text),
        "sha256": _sha256_text(text) if text else "",
    }


def _summarize_stable_findings(stable_findings: Any) -> Dict[str, Any]:
    if not isinstance(stable_findings, list) or not stable_findings:
        return {"count": 0, "latest_question": "", "latest_final_answer": "", "latest_evidence_count": 0}
    latest = stable_findings[-1] if isinstance(stable_findings[-1], dict) else {}
    evidence = latest.get("evidence", []) if isinstance(latest, dict) else []
    return {
        "count": len(stable_findings),
        "latest_question": str(latest.get("question", "") or ""),
        "latest_final_answer": str(latest.get("final_answer", "") or ""),
        "latest_evidence_count": len(evidence) if isinstance(evidence, list) else 0,
    }


def _summarize_thread_summary(thread_summary: Any, final_answer_text: str) -> Dict[str, Any]:
    text = str(thread_summary or "")
    return {
        "present": bool(text),
        "char_len": len(text),
        "contains_final_answer": final_answer_text in text if text and final_answer_text else False,
        "preview": text[:160],
    }


def _selected_source_alignment(
    scenario: FusionScenario,
    state: Mapping[str, Any],
    payload: Mapping[str, Any],
    final_state: Mapping[str, Any],
) -> bool:
    expected_source = scenario.expected_source
    final_source = str(final_state.get("final_answer_source", "") or "")
    payload_source = str(payload.get("selected_source", "") or "")
    writer_selected = str((state.get("writer_output") or {}).get("selected_source", "") or "")
    verdict_decision = str((state.get("fusion_verdict") or {}).get("decision", "") or "")
    source_switch_enabled = bool(scenario.flags.get("context", {}).get("enable_fair_fusion_source_switch"))
    if not source_switch_enabled:
        return (
            expected_source == "mainline"
            and payload_source == "mainline"
            and final_source == "mainline"
            and writer_selected in {"mainline", "baseline", "fused", "unknown"}
            and verdict_decision in {"mainline", "baseline", "fused", "unknown"}
        )
    return payload_source == expected_source and final_source == expected_source


def _evaluate_invariants(
    scenario: FusionScenario,
    *,
    pre_emit_state: Mapping[str, Any],
    payload: Mapping[str, Any],
    final_state: Mapping[str, Any],
    route_after_gate: str,
    route_after_judge: str,
    route_after_writer: str,
) -> Dict[str, bool]:
    emitted_bundle = final_state.get("emitted_bundle", {})
    emitted_bundle = emitted_bundle if isinstance(emitted_bundle, dict) else {}
    emitted_answer = str(emitted_bundle.get("answer", "") or "")
    emitted_question = str(emitted_bundle.get("question", "") or "")
    final_messages = list(final_state.get("messages", []))
    final_message = final_messages[-1] if final_messages else None
    final_message_text = _summarize_message(final_message)["text"]
    stable_summary = _summarize_stable_findings(final_state.get("stable_findings", []))
    thread_summary = _summarize_thread_summary(final_state.get("thread_summary", ""), emitted_answer)
    writer_selected = str((pre_emit_state.get("writer_output") or {}).get("selected_source", "") or "")
    results_pool_clean = (
        pre_emit_state.get("analyst_results", {}) == final_state.get("analyst_results", {})
        and pre_emit_state.get("ephemeral_results", {}) == final_state.get("ephemeral_results", {})
    )
    return {
        "route_after_gate_final_emit": route_after_gate == "final_emit",
        "route_after_judge_final_emit": route_after_judge == "final_emit",
        "route_after_writer_final_emit": route_after_writer == "final_emit",
        "source_selection_alignment": _selected_source_alignment(
            scenario,
            state=pre_emit_state,
            payload=payload,
            final_state=final_state,
        ),
        "emitted_bundle_alignment": bool(emitted_answer) and emitted_answer == final_message_text,
        "stable_findings_alignment": (
            stable_summary["count"] > 0
            and stable_summary["latest_final_answer"] == emitted_answer
            and stable_summary["latest_question"] == emitted_question
        ),
        "thread_summary_alignment": (
            not bool(scenario.flags.get("env", {}).get("REACT_AGENT_THREAD_SUMMARY") == "1")
            or thread_summary["contains_final_answer"]
        ),
        "results_pool_isolation": results_pool_clean,
        "flag_off_mainline_lock": (
            not bool(scenario.flags.get("context", {}).get("enable_fair_fusion_source_switch"))
            and str(final_state.get("final_answer_source", "") or "") == "mainline"
        ),
        "degraded_fallback_to_mainline": (
            (
                str(pre_emit_state.get("baseline_status", "") or "") in {"error", "disabled"}
                or writer_selected not in {"mainline", "baseline", "fused"}
            )
            and str(final_state.get("final_answer_source", "") or "") == "mainline"
        ),
    }


async def run_scenario(scenario: FusionScenario) -> Dict[str, Any]:
    Context, graph_mod = _load_runtime_modules()
    context_flags = dict(scenario.flags.get("context", {}))
    env_flags = {str(k): str(v) for k, v in dict(scenario.flags.get("env", {})).items()}
    runtime = types.SimpleNamespace(
        context=Context(
            run_id=f"ff5b-{scenario.case_id}",
            model="deepseek/deepseek-chat",
            **context_flags,
        )
    )
    with _temp_env(env_flags):
        state = _build_runtime_state(scenario.seed_state, run_id=f"ff5b-{scenario.case_id}")
        payload = _materialize_emit_payload(graph_mod, state, runtime.context)
        state["final_emit_payload"] = payload
        route_after_gate = graph_mod.route_after_fusion_gate(state)  # type: ignore[attr-defined]
        route_after_judge = graph_mod.route_after_fusion_judge(state)  # type: ignore[attr-defined]
        route_after_writer = graph_mod.route_after_fusion_writer(state)  # type: ignore[attr-defined]
        emit_out = await graph_mod.final_emit(state, runtime)  # type: ignore[arg-type]

        merged_state = dict(state)
        merged_state.update(emit_out)
        merged_state["messages"] = _append_messages(state.get("messages", []), emit_out.get("messages", []))

        memory_out: Dict[str, Any] = {}
        if env_flags.get("REACT_AGENT_THREAD_SUMMARY") == "1":
            memory_out = await graph_mod.memory_update(merged_state, runtime)  # type: ignore[arg-type]
            merged_state.update(memory_out)

        invariant_results = _evaluate_invariants(
            scenario,
            pre_emit_state=state,
            payload=payload,
            final_state=merged_state,
            route_after_gate=route_after_gate,
            route_after_judge=route_after_judge,
            route_after_writer=route_after_writer,
        )
        expected_statuses = dict(scenario.expected_terminal_statuses)
        failing_notes: List[str] = []
        for status_name, expected_value in expected_statuses.items():
            actual_value = str(merged_state.get(status_name, "") or "")
            if actual_value != expected_value:
                failing_notes.append(
                    f"terminal status mismatch: {status_name} expected={expected_value} actual={actual_value}"
                )
        final_source = str(merged_state.get("final_answer_source", "") or "")
        if final_source != scenario.expected_source:
            failing_notes.append(
                f"final source mismatch: expected={scenario.expected_source} actual={final_source}"
            )
        for invariant_name, expected_value in scenario.expected_invariants.items():
            actual_value = invariant_results.get(invariant_name, False)
            if actual_value != expected_value:
                failing_notes.append(
                    f"invariant mismatch: {invariant_name} expected={expected_value} actual={actual_value}"
                )

        emitted_bundle = merged_state.get("emitted_bundle", {})
        emitted_bundle = emitted_bundle if isinstance(emitted_bundle, dict) else {}
        final_message = merged_state.get("messages", [])[-1] if merged_state.get("messages") else None
        stable_summary = _summarize_stable_findings(merged_state.get("stable_findings", []))
        record = {
            "case_id": scenario.case_id,
            "description": scenario.description,
            "flags": scenario.flags,
            "expected_source": scenario.expected_source,
            "expected_terminal_statuses": scenario.expected_terminal_statuses,
            "expected_invariants": scenario.expected_invariants,
            "route_after_fusion_gate": route_after_gate,
            "route_after_fusion_judge": route_after_judge,
            "route_after_fusion_writer": route_after_writer,
            "baseline_status": str(merged_state.get("baseline_status", "") or ""),
            "judge_status": str(merged_state.get("judge_status", "") or ""),
            "writer_status": str(merged_state.get("writer_status", "") or ""),
            "fusion_verdict_decision": str((merged_state.get("fusion_verdict") or {}).get("decision", "") or ""),
            "writer_selected_source": str((merged_state.get("writer_output") or {}).get("selected_source", "") or ""),
            "final_emit_selected_source": str(payload.get("selected_source", "") or ""),
            "final_answer_source": final_source,
            "emitted_bundle_summary": _summarize_bundle(emitted_bundle),
            "final_message_summary": _summarize_message(final_message),
            "stable_findings_summary": stable_summary,
            "thread_summary_summary": _summarize_thread_summary(
                merged_state.get("thread_summary", ""),
                str(emitted_bundle.get("answer", "") or ""),
            ),
            "baseline_search_executed": bool(
                isinstance(merged_state.get("baseline_bundle"), dict)
                and isinstance((merged_state.get("baseline_bundle") or {}).get("search_meta"), dict)
                and (merged_state.get("baseline_bundle") or {}).get("search_meta", {}).get("search_executed") is True
            ),
            "results_pool_pollution": not invariant_results.get("results_pool_isolation", False),
            "invariant_results": invariant_results,
            "business_status": "fail" if failing_notes else "pass",
            "trace_noise": [],
            "notes": failing_notes,
        }
        return record


async def run_all_scenarios(scenarios: Iterable[FusionScenario]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for scenario in scenarios:
        records.append(await run_scenario(scenario))
    return records


def write_jsonl(records: Iterable[Mapping[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(dict(record), ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic FF-5B fusion regression scenarios.")
    parser.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / "ops" / "regression" / "fusion" / "out"),
        help="Directory for fusion regression artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    records = asyncio.run(run_all_scenarios(SCENARIOS))
    out_path = out_dir / "fusion_runs.jsonl"
    write_jsonl(records, out_path)
    passed = sum(1 for record in records if record.get("business_status") == "pass")
    print(f"cases: {len(records)}")
    print(f"business_pass: {passed}")
    print(f"out: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

