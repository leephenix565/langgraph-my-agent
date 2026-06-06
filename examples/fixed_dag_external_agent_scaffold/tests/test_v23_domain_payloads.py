"""v2.3 domain payload family and semantic validator tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCAFFOLD_DIR = Path(__file__).resolve().parents[1]
if str(SCAFFOLD_DIR) not in sys.path:
    sys.path.insert(0, str(SCAFFOLD_DIR))

from schemas import normalize_dimension, validate_tool_result  # noqa: E402


def _sample(name: str) -> dict[str, object]:
    return json.loads(
        (SCAFFOLD_DIR / "sample_requests" / name).read_text(encoding="utf-8")
    )


def test_all_v23_domain_payload_samples_validate() -> None:
    """Every v2.3 domain response sample passes validate_tool_result."""
    for name in (
        "agent_conclusion.response.json",
        "dimension_conclusion.response.json",
        "risk_conclusion.response.json",
        "macro_conclusion.response.json",
        "decision_conclusion.response.json",
        "eval_record.response.json",
        "data_bundle.response.json",
        "fixed_dag_plan.response.json",
        "compute.response.json",
        "invoke.response.json",
        "error.response.json",
    ):
        valid, reason = validate_tool_result(_sample(name))
        assert valid, f"{name}: {reason}"


def test_dimension_aliases_normalize_before_validation() -> None:
    """Chinese aliases are accepted only as migration input and normalize to English."""
    assert normalize_dimension("风险") == "risk"
    assert normalize_dimension("市场面") == "market"

    payload = _sample("risk_conclusion.response.json")
    payload["dimension"] = "风险"
    valid, reason = validate_tool_result(payload)
    assert valid, reason


def test_implementation_notes_are_optional() -> None:
    """Existing agents do not fail if implementation_notes are absent."""
    payload = _sample("agent_conclusion.response.json")
    payload.pop("implementation_notes", None)
    valid, reason = validate_tool_result(payload)
    assert valid, reason


def test_ann_primary_agent_id_is_rejected_by_domain_validator() -> None:
    """Old aNN ids remain migration notes, not primary agent ids."""
    payload = _sample("agent_conclusion.response.json")
    payload["agent_id"] = "a16_ml_valuation"

    valid, reason = validate_tool_result(payload)

    assert not valid
    assert reason == "legacy_agent_id_as_primary"


def test_anti_lookahead_checks_data_bundle_and_evidence_publish_times() -> None:
    """data_as_of, publish_time, and evidence timestamps cannot exceed as_of."""
    data_bundle = _sample("data_bundle.response.json")
    data_bundle["publish_time"] = "2026-06-06"
    valid, reason = validate_tool_result(data_bundle)
    assert not valid
    assert reason == "publish_time_after_as_of"

    conclusion = _sample("agent_conclusion.response.json")
    evidence = conclusion["evidence"]
    assert isinstance(evidence, list)
    evidence[0]["publish_time"] = "2026-06-06"
    valid, reason = validate_tool_result(conclusion)
    assert not valid
    assert reason == "evidence_publish_time_after_as_of"


def test_l3_gate_and_regulator_payloads_reject_direction_stance() -> None:
    """Risk and macro are not directional stance payloads."""
    risk = _sample("risk_conclusion.response.json")
    risk["stance"] = 0.2
    valid, reason = validate_tool_result(risk)
    assert not valid
    assert reason == "risk_must_not_have_stance"

    macro = _sample("macro_conclusion.response.json")
    macro["stance"] = 0.2
    valid, reason = validate_tool_result(macro)
    assert not valid
    assert reason == "macro_must_not_have_stance"


def test_weights_and_dimension_weight_semantics_are_checked() -> None:
    """Composite and macro weights must be explainable and normalized."""
    dimension = _sample("dimension_conclusion.response.json")
    weights = dimension["weights"]
    assert isinstance(weights, dict)
    weights["value_ml_valuation"] = 0.4
    valid, reason = validate_tool_result(dimension)
    assert not valid
    assert reason == "weights_sum_not_one"

    macro = _sample("macro_conclusion.response.json")
    dimension_weights = macro["dimension_weights"]
    assert isinstance(dimension_weights, dict)
    dimension_weights["unknown"] = 0.1
    valid, reason = validate_tool_result(macro)
    assert not valid
    assert reason == "validation_error:ValueError"


def test_decision_trace_requires_depth_and_recomputable_score() -> None:
    """L4 decision payloads require at least 3 reasoning stages and score trace."""
    short_trace = _sample("decision_conclusion.response.json")
    reasoning_trace = short_trace["reasoning_trace"]
    assert isinstance(reasoning_trace, list)
    short_trace["reasoning_trace"] = reasoning_trace[:2]
    valid, reason = validate_tool_result(short_trace)
    assert not valid
    assert reason == "reasoning_trace_too_short"

    mismatch = _sample("decision_conclusion.response.json")
    calculation_trace = mismatch["calculation_trace"]
    assert isinstance(calculation_trace, dict)
    calculation_trace["final_score"] = 0.99
    valid, reason = validate_tool_result(mismatch)
    assert not valid
    assert reason == "score_mismatch"


def test_sample_confidence_values_are_not_constant() -> None:
    """Samples show confidence as a signal, not a fixed authoritative constant."""
    confidence_values = {
        _sample("agent_conclusion.response.json")["confidence"],
        _sample("dimension_conclusion.response.json")["confidence"],
        _sample("decision_conclusion.response.json")["confidence"],
    }

    assert len(confidence_values) >= 3
