"""v2.3.1 domain payload family and semantic validator tests."""

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


def test_all_v231_domain_payload_samples_validate() -> None:
    """Every v2.3.1 domain response sample passes validate_tool_result."""
    for name in (
        "agent_conclusion.response.json",
        "agent_conclusion.risk_member.response.json",
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


def test_agent_conclusion_direction_requires_stance() -> None:
    """Directional L2 members must provide stance."""
    payload = _sample("agent_conclusion.response.json")
    payload.pop("stance")

    valid, reason = validate_tool_result(payload)

    assert not valid
    assert reason == "direction_stance_missing"


def test_agent_conclusion_gate_member_requires_risk_score() -> None:
    """Risk L2 gate members use risk_score instead of required stance."""
    payload = _sample("agent_conclusion.risk_member.response.json")
    payload.pop("risk_score")

    valid, reason = validate_tool_result(payload)

    assert not valid
    assert reason == "gate_member_risk_score_missing"


def test_agent_conclusion_rejects_direction_with_risk_score() -> None:
    """Directional L2 members do not mix in risk_score."""
    payload = _sample("agent_conclusion.response.json")
    payload["risk_score"] = 0.4

    valid, reason = validate_tool_result(payload)

    assert not valid
    assert reason == "direction_must_not_have_risk_score"


def test_agent_conclusion_preserves_raw_output_and_quality() -> None:
    """raw_output and quality are safe dict payloads, not graph-state fields."""
    payload = _sample("agent_conclusion.risk_member.response.json")
    assert isinstance(payload["raw_output"], dict)
    assert isinstance(payload["quality"], dict)

    valid, reason = validate_tool_result(payload)
    assert valid, reason

    payload["raw_output"] = ["not", "a", "dict"]
    valid, reason = validate_tool_result(payload)
    assert not valid
    assert reason == "validation_error:ValidationError"


def test_risk_gate_accepts_manual_review() -> None:
    """manual_review is a risk gate value, not an envelope status."""
    payload = _sample("risk_conclusion.response.json")
    assert payload["gate"] == "manual_review"

    valid, reason = validate_tool_result(payload)

    assert valid, reason


def test_temporal_validator_normalizes_dates_before_comparison() -> None:
    """Mixed date formats are normalized before anti-lookahead comparison."""
    payload = _sample("agent_conclusion.risk_member.response.json")
    assert payload["as_of"] == "2026-06-06"
    assert payload["data_as_of"] == "20260605"

    valid, reason = validate_tool_result(payload)

    assert valid, reason


def test_temporal_validator_rejects_future_date_with_mixed_formats() -> None:
    """Mixed formats must not bypass future-data checks."""
    payload = _sample("agent_conclusion.risk_member.response.json")
    payload["as_of"] = "20260606"
    payload["data_as_of"] = "2026-06-07"

    valid, reason = validate_tool_result(payload)

    assert not valid
    assert reason == "data_as_of_after_as_of"


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


def test_dimension_members_are_objects() -> None:
    """Dimension members are canonical object entries in v2.3.1."""
    dimension = _sample("dimension_conclusion.response.json")
    members = dimension["members"]
    assert isinstance(members, list)
    assert all(isinstance(member, dict) for member in members)

    dimension["members"] = ["legacy_string_member"]
    valid, reason = validate_tool_result(dimension)
    assert not valid
    assert reason == "validation_error:ValidationError"


def test_dimension_weighted_stance_must_match_member_weights() -> None:
    """Composite stance must match the weighted member stance within tolerance."""
    dimension = _sample("dimension_conclusion.response.json")
    members = dimension["members"]
    assert isinstance(members, list)
    first_member = members[0]
    assert isinstance(first_member, dict)
    first_member["stance"] = -0.9

    valid, reason = validate_tool_result(dimension)

    assert not valid
    assert reason == "weighted_stance_mismatch"


def test_macro_dimension_weights_only_value_market() -> None:
    """Macro dimension weights are directional only; risk is a separate gate."""
    macro = _sample("macro_conclusion.response.json")
    dimension_weights = macro["dimension_weights"]
    assert isinstance(dimension_weights, dict)
    assert set(dimension_weights) == {"value", "market"}

    dimension_weights["risk"] = 0.1
    valid, reason = validate_tool_result(macro)
    assert not valid
    assert reason == "dimension_weights_invalid_keys"


def test_decision_score_accepts_within_001_tolerance() -> None:
    """Displayed score may be rounded from calculation_trace.final_score."""
    decision = _sample("decision_conclusion.response.json")
    calculation_trace = decision["calculation_trace"]
    assert isinstance(calculation_trace, dict)
    assert decision["score"] == 0.31
    assert calculation_trace["final_score"] == 0.314

    valid, reason = validate_tool_result(decision)

    assert valid, reason


def test_decision_score_rejects_outside_001_tolerance() -> None:
    """Score drift beyond 0.01 is rejected."""
    decision = _sample("decision_conclusion.response.json")
    calculation_trace = decision["calculation_trace"]
    assert isinstance(calculation_trace, dict)
    calculation_trace["final_score"] = 0.33

    valid, reason = validate_tool_result(decision)

    assert not valid
    assert reason == "score_mismatch"


def test_decision_reasoning_trace_requires_distinct_stages() -> None:
    """L4 trace depth is counted by distinct stage values."""
    decision = _sample("decision_conclusion.response.json")
    reasoning_trace = decision["reasoning_trace"]
    assert isinstance(reasoning_trace, list)
    for step in reasoning_trace:
        assert isinstance(step, dict)
        step["stage"] = 1

    valid, reason = validate_tool_result(decision)

    assert not valid
    assert reason == "reasoning_trace_stage_depth_too_shallow"


def test_sample_family_confidence_values_are_not_constant() -> None:
    """Samples show confidence as a signal, not a fixed authoritative constant."""
    confidence_values = {
        _sample("agent_conclusion.response.json")["confidence"],
        _sample("agent_conclusion.risk_member.response.json")["confidence"],
        _sample("dimension_conclusion.response.json")["confidence"],
        _sample("decision_conclusion.response.json")["confidence"],
    }

    assert len(confidence_values) >= 3


def test_single_payload_validator_does_not_enforce_global_confidence_variation() -> None:
    """Single-payload validation checks bounds only, not cross-call constancy."""
    payload = _sample("agent_conclusion.response.json")
    payload["confidence"] = 0.42

    valid, reason = validate_tool_result(payload)

    assert valid, reason
