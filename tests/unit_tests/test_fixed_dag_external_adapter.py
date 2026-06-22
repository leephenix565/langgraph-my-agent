import json
from copy import deepcopy
from pathlib import Path

from react_agent.fixed_dag_contracts import (
    validate_conclusion_object,
    validate_data_bundle,
    validate_decision_result,
    validate_dimension_composite_result,
    validate_entity_relation_bundle,
    validate_report_result,
)
from react_agent.fixed_dag_external_adapter import (
    ADAPTER_FAILURE_SCHEMA_VERSION,
    EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION,
    EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION,
    EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
    FIXED_DAG_EXTERNAL_ADAPTER_SOURCE,
    map_external_agent_conclusion_to_conclusion_object,
    map_external_compute_envelope_to_fixed_dag_object,
    map_external_data_bundle_to_data_bundle,
    map_external_entity_relation_bundle_to_entity_relation_bundle,
    map_external_response_to_fixed_dag_object,
    validate_external_compute_envelope,
    validate_external_response_envelope,
)

SAMPLE_DIR = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "fixed_dag_external_agent_scaffold"
    / "sample_requests"
)


def _sample(name: str) -> dict[str, object]:
    return json.loads((SAMPLE_DIR / name).read_text(encoding="utf-8"))


def _compute_envelope(tool_result: dict[str, object] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION,
        "agent_id": "valuation_ml",
        "external_agent_id": "valuation_ml",
        "status": "ok",
        "confidence": 0.7071,
        "as_of": "20260605",
        "data_as_of": "20260605",
        "warnings": ["Model output is research-only."],
        "errors": [],
    }
    if tool_result is not None:
        payload["tool_result"] = tool_result
    return payload


def _assert_safe_public_payload(payload: dict[str, object]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    for token in (
        "api_key",
        "secret",
        "password",
        "endpoint",
        "default_url",
        "raw_response",
        "raw_provider_response",
        "raw_external_json",
        "traceback",
        "chain-of-thought",
        "chain_of_thought",
    ):
        assert token not in rendered


def test_direction_agent_conclusion_maps_to_valid_conclusion_object() -> None:
    mapped = map_external_agent_conclusion_to_conclusion_object(
        _sample("agent_conclusion.response.json")
    )
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["schema"] == "conclusion_object_v1"
    assert mapped["agent_id"] == "value_ml_valuation"
    assert mapped["dimension"] == "value"
    assert mapped["status"] == "complete"
    assert mapped["stance"] == "0.18"
    assert mapped["evidence"]
    assert mapped["provenance"]["adapter_source"] == FIXED_DAG_EXTERNAL_ADAPTER_SOURCE
    assert mapped["provenance"]["external_agent_id"] == "valuation_ml"
    assert mapped["provenance"]["legacy_agent_id"] == "a16_ml_valuation"
    assert mapped["provenance"]["provider_invoked"] is False
    assert mapped["provenance"]["external_invoked"] is False
    _assert_safe_public_payload(mapped)


def test_external_response_envelope_maps_tool_result() -> None:
    payload = _sample("compute.response.json")
    valid, reason = validate_external_response_envelope(payload)
    mapped = map_external_response_to_fixed_dag_object(payload)
    mapped_valid, mapped_reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert payload["schema_version"] == EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION
    assert mapped_valid, mapped_reason
    assert mapped["agent_id"] == "value_ml_valuation"
    assert mapped["status"] == "complete"
    assert mapped["provenance"]["external_status"] == "ok"


def test_external_compute_envelope_maps_agent_conclusion_tool_result() -> None:
    payload = _compute_envelope(_sample("agent_conclusion.response.json"))
    valid, reason = validate_external_compute_envelope(payload)
    mapped = map_external_response_to_fixed_dag_object(payload)
    mapped_valid, mapped_reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped_valid, mapped_reason
    assert mapped["schema"] == "conclusion_object_v1"
    assert mapped["agent_id"] == "value_ml_valuation"
    assert mapped["status"] == "complete"
    assert mapped["provenance"]["adapter_source"] == FIXED_DAG_EXTERNAL_ADAPTER_SOURCE
    assert mapped["provenance"]["adapter_input_schema"] == EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION
    assert mapped["provenance"]["compute_envelope_status"] == "ok"
    assert mapped["provenance"]["external_agent_id"] == "valuation_ml"
    assert mapped["provenance"]["provider_invoked"] is False
    assert mapped["provenance"]["external_invoked"] is False
    _assert_safe_public_payload(mapped)


def test_report_material_allowlist_maps_financial_fraud_and_macro_context() -> None:
    fraud_payload = _compute_envelope(
        {
            "schema_version": "agent_conclusion_v1",
            "agent_id": "risk_financial_fraud",
            "external_agent_id": "financial_fraud_agent",
            "dimension": "risk",
            "role": "gate_member",
            "target": "600519.SH",
            "scope": "stock",
            "as_of": "2024-12-31",
            "data_as_of": "2024-12-31",
            "risk_score": 0.25,
            "confidence": 0.73,
            "raw_output": {
                "risk_score": 25,
                "risk_level": "low",
                "fraud_risk_bridge": {"risk_score": 25, "gate_action": "pass"},
                "model_context": {"model_available": True, "threshold": 0.5},
                "feature_diagnostics": {"financial_report_period": "2024", "coverage": 1.0},
                "risk_gate_rule": {"pass": "0-39", "selected_action": "pass"},
                "research_points": [
                    {
                        "claim": "财务造假风险闸门为 pass。",
                        "support": "风险分数 25/100，模型和本地特征均可用。",
                        "interpretation": "作为风险闸门材料，不直接给出买卖结论。",
                    }
                ],
                "drivers": [
                    {"name": "fraud_risk_bridge", "value": {"risk_score": 25}},
                    {"name": "model_context", "value": {"model_available": True}},
                ],
            },
            "quality": {
                "anti_lookahead_passed": True,
                "feature_data_anti_lookahead_passed": True,
                "model_available": True,
                "financial_report_period": "2024",
                "financial_publish_time": "2025-04-30",
                "annual_feature_available_after": "2025-04-30",
            },
            "evidence": [
                {
                    "fact": "财务造假风险分数为 25/100，闸门 action=pass。",
                    "source": "financial_fraud_risk_gate",
                    "as_of": "2024-12-31",
                    "data_as_of": "2024-12-31",
                }
            ],
            "status": "ok",
        }
    )
    fraud_payload["agent_id"] = "risk_financial_fraud"
    fraud_payload["external_agent_id"] = "financial_fraud_agent"

    fraud_mapped = map_external_response_to_fixed_dag_object(fraud_payload)
    valid, reason = validate_conclusion_object(fraud_mapped)
    assert valid, reason
    fraud_provenance = fraud_mapped["provenance"]
    assert fraud_provenance["domain_metrics"]["fraud_risk_bridge"]["gate_action"] == "pass"
    assert fraud_provenance["domain_metrics"]["model_context"]["model_available"] is True
    assert fraud_provenance["domain_metrics"]["feature_diagnostics"]["financial_report_period"] == "2024"
    assert any(item["name"] == "fraud_risk_bridge" for item in fraud_provenance["drivers"])
    assert fraud_provenance["research_points"][0]["claim"] == "财务造假风险闸门为 pass。"
    assert fraud_provenance["data_quality"]["annual_feature_available_after"] == "2025-04-30"
    _assert_safe_public_payload(fraud_mapped)

    macro_payload = _compute_envelope(
        {
            "schema_version": "agent_conclusion_v1",
            "agent_id": "macro_analysis",
            "external_agent_id": "macro_analysis",
            "dimension": "macro",
            "role": "direction",
            "target": "A股权益",
            "scope": "macro",
            "as_of": "2024-12-31",
            "data_as_of": "2024-12-31",
            "stance": 0.6,
            "confidence": 0.8,
            "raw_output": {
                "macro_regime_bridge": {"quadrant_label": "宽货币·宽信用", "stance": 0.6},
                "macro_signal_table": {"growth": {"signal": "up", "pmi": 51.0}},
                "asset_allocation_view": {"best_asset_class": "股票"},
                "sector_rotation_summary": {"available": True, "industry_recommend": ["电子"]},
                "macro_data_window": {"as_of": "20241231", "knowledge_version": "2026-05-27"},
                "zeping_crosscheck_context": {"agree": True, "zeping_phase": "复苏"},
                "research_points": [
                    {
                        "claim": "宏观周期判断为宽货币·宽信用 / 复苏。",
                        "support": "stance=0.6，行业推荐包含电子。",
                    }
                ],
                "drivers": [
                    {"name": "macro_regime_bridge", "value": {"stance": 0.6}},
                    {"name": "macro_signal_table", "value": {"growth": {"signal": "up"}}},
                ],
            },
            "quality": {
                "anti_lookahead_passed": True,
                "macro_data_window": {"as_of": "20241231", "data_as_of": "20241231"},
                "release_dates": {"growth": "2024-12-01"},
                "knowledge_version": "2026-05-27",
                "sector_rotation_available": True,
            },
            "evidence": [
                {
                    "fact": "宏观周期=宽货币·宽信用 / 复苏，stance=0.6。",
                    "source": "macro_regime_bridge",
                    "as_of": "2024-12-31",
                    "data_as_of": "2024-12-31",
                }
            ],
            "status": "ok",
        }
    )
    macro_payload["agent_id"] = "macro_analysis"
    macro_payload["external_agent_id"] = "macro_analysis"

    macro_mapped = map_external_response_to_fixed_dag_object(macro_payload)
    valid, reason = validate_conclusion_object(macro_mapped)
    assert valid, reason
    macro_provenance = macro_mapped["provenance"]
    assert macro_provenance["domain_metrics"]["macro_regime_bridge"]["stance"] == 0.6
    assert macro_provenance["domain_metrics"]["sector_rotation_summary"]["industry_recommend"] == ["电子"]
    assert any(item["name"] == "macro_signal_table" for item in macro_provenance["drivers"])
    assert macro_provenance["research_points"][0]["claim"].startswith("宏观周期判断")
    assert macro_provenance["data_quality"]["knowledge_version"] == "2026-05-27"
    _assert_safe_public_payload(macro_mapped)


def test_external_compute_envelope_maps_data_bundle_tool_result() -> None:
    payload = _compute_envelope(_sample("data_bundle.response.json"))
    payload["agent_id"] = "financial_data_service"
    payload["external_agent_id"] = "financial_data_service"

    valid, reason = validate_external_compute_envelope(payload)
    mapped = map_external_response_to_fixed_dag_object(payload)
    mapped_valid, mapped_reason = validate_data_bundle(mapped)

    assert valid, reason
    assert mapped_valid, mapped_reason
    assert mapped["schema"] == "data_bundle_v1"
    assert mapped["schema_version"] == "data_bundle_v1"
    assert mapped["status"] == "complete"
    assert mapped["sources"] == ["sample_local_snapshot"]
    assert any("feature_key: close" == note for note in mapped["notes"])
    _assert_safe_public_payload(mapped)


def _entity_relation_payload() -> dict[str, object]:
    return {
        "schema_version": EXTERNAL_ENTITY_RELATION_BUNDLE_SCHEMA_VERSION,
        "agent_id": "entity_relation_extractor",
        "external_agent_id": "entity_relation_agent",
        "status": "ok",
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "entities": [
            {"id": "600519.SH", "name": "贵州茅台", "type": "security"},
            {"id": "baijiu", "name": "白酒", "type": "industry"},
        ],
        "relations": [
            {
                "source": "600519.SH",
                "target": "baijiu",
                "type": "belongs_to",
                "weight": 1.0,
            }
        ],
        "sources": ["entity_relation_agent_local_snapshot"],
        "notes": ["bounded test fixture"],
    }


def _dimension_conclusion_payload(
    *,
    agent_id: str = "value_composite",
    dimension: str = "value",
    members: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if members is None:
        members = [
            {
                "agent_id": "value_ml_valuation",
                "stance": 0.2,
                "confidence": 0.72,
                "weight": 0.6,
                "status": "ok",
            },
            {
                "agent_id": "value_research_synthesis",
                "stance": 0.1,
                "confidence": 0.68,
                "weight": 0.4,
                "status": "ok",
            },
        ]
    return {
        "schema_version": "dimension_conclusion_v1",
        "agent_id": agent_id,
        "external_agent_id": f"{agent_id}_service",
        "dimension": dimension,
        "role": "direction",
        "target": "600519.SH",
        "stance": 0.16,
        "confidence": 0.7,
        "members": members,
        "method": "weighted_member_vote",
        "dispersion": 0.12,
        "fair_value_range": {"low": 1500.0, "mid": 1650.0, "high": 1800.0},
        "valuation": {"method": "member_weighted", "fair_value_center": 1650.0},
        "warnings": ["one member was partial"],
        "evidence": [
            {
                "id": "dimension-evidence-1",
                "fact": "Weighted value members are mildly positive.",
                "source": "bounded_l3_fixture",
                "as_of": "2026-06-05",
                "data_as_of": "2026-06-05",
            }
        ],
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "status": "ok",
    }


def _risk_conclusion_payload(*, gate: str = "pass") -> dict[str, object]:
    return {
        "schema_version": "risk_conclusion_v1",
        "agent_id": "risk_composite",
        "external_agent_id": "risk_composite_service",
        "dimension": "risk",
        "role": "gate",
        "target": "600519.SH",
        "gate": gate,
        "risk_score": 0.42,
        "penalty": 0.15,
        "confidence": 0.78,
        "contributing_agents": ["risk_identification", "risk_compliance_review"],
        "members": [
            {
                "agent_id": "risk_identification",
                "risk_score": 0.55,
                "confidence": 0.62,
                "weight": 0.4,
                "status": "partial",
            },
            {
                "agent_id": "risk_compliance_review",
                "risk_score": 0.34,
                "confidence": 0.86,
                "weight": 0.6,
                "status": "ok",
            },
        ],
        "triggered_flags": ["bounded_risk_flag"],
        "red_lines": ["manual review only if disclosure changes"],
        "warnings": ["risk member partial"],
        "evidence": [
            {
                "id": "risk-evidence-1",
                "fact": "Risk gate inputs remain below veto level.",
                "source": "bounded_l3_fixture",
                "as_of": "2026-06-05",
                "data_as_of": "2026-06-05",
            }
        ],
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "status": "ok",
    }


def _macro_conclusion_payload() -> dict[str, object]:
    return {
        "schema_version": "macro_conclusion_v1",
        "agent_id": "macro_composite",
        "external_agent_id": "macro_composite_service",
        "dimension": "macro",
        "role": "regulator",
        "target": "CN_A_SHARE_MACRO",
        "regime": "neutral_liquidity_watch",
        "dimension_weights": {"value": 0.55, "market": 0.45},
        "risk_sensitivity": 0.6,
        "style_bias": {"quality": 0.7, "defensive": 0.3},
        "regime_detail": {"name": "neutral", "confidence": 0.69},
        "members": {
            "macro_analysis": {"confidence": 0.64, "status": "ok", "summary": "growth stable"},
            "macro_commodity_pricing": {"confidence": 0.48, "status": "partial"},
            "macro_industry_hotspot": {
                "name": "macro_industry_hotspot",
                "confidence": 0.0,
                "status": "pending",
                "weight": 0.0,
            },
        },
        "warnings": ["macro commodity member partial"],
        "confidence": 0.69,
        "contributing_agents": ["macro_analysis", "macro_commodity_pricing"],
        "evidence": [
            {
                "id": "macro-evidence-1",
                "fact": "Macro regime supports balanced value and market weights.",
                "source": "bounded_l3_fixture",
                "as_of": "2026-06-05",
                "data_as_of": "2026-06-05",
            }
        ],
        "as_of": "2026-06-05",
        "data_as_of": "2026-06-05",
        "status": "ok",
    }


def _response_envelope(tool_result: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION,
        "agent_id": str(tool_result["agent_id"]),
        "external_agent_id": str(tool_result.get("external_agent_id", "")),
        "status": "ok",
        "confidence": 0.7,
        "warnings": [],
        "errors": [],
        "tool_result": tool_result,
    }


def test_external_compute_envelope_maps_entity_relation_bundle_tool_result() -> None:
    payload = _compute_envelope(_entity_relation_payload())
    payload["agent_id"] = "entity_relation_extractor"
    payload["external_agent_id"] = "entity_relation_agent"

    valid, reason = validate_external_compute_envelope(payload)
    mapped = map_external_response_to_fixed_dag_object(payload)
    mapped_valid, mapped_reason = validate_entity_relation_bundle(mapped)

    assert valid, reason
    assert mapped_valid, mapped_reason
    assert mapped["schema"] == "entity_relation_bundle_v1"
    assert mapped["schema_version"] == "entity_relation_bundle_v1"
    assert mapped["status"] == "complete"
    assert mapped["entities"][0]["id"] == "600519.SH"
    assert mapped["relations"][0]["type"] == "belongs_to"
    assert "source: entity_relation_agent_local_snapshot" in mapped["notes"]
    _assert_safe_public_payload(mapped)


def test_dimension_conclusion_value_maps_to_dimension_composite_result() -> None:
    mapped = map_external_response_to_fixed_dag_object(_dimension_conclusion_payload())
    valid, reason = validate_dimension_composite_result(mapped)

    assert valid, reason
    assert mapped["schema"] == "dimension_composite_result_v1"
    assert mapped["agent_id"] == "value_composite"
    assert mapped["dimension"] == "value"
    assert mapped["status"] == "complete"
    assert mapped["contributing_agents"] == ["value_ml_valuation", "value_research_synthesis"]
    assert mapped["evidence_refs"] == ["dimension-evidence-1"]
    assert mapped["vote_type"] == "weighted_member_vote"
    assert mapped["provenance"]["adapter_input_schema"] == "dimension_conclusion_v1"
    assert mapped["provenance"]["domain_metrics"]["fair_value_range"] == {
        "low": 1500.0,
        "mid": 1650.0,
        "high": 1800.0,
    }
    driver_names = {item["name"] for item in mapped["provenance"]["drivers"]}
    assert {"fair_value_range", "valuation", "member_weight_summary"} <= driver_names
    assert mapped["provenance"]["data_quality"]["composite_status"] == "ok"
    assert mapped["provenance"]["data_quality"]["member_count"] == 2
    assert mapped["provenance"]["provider_invoked"] is False
    assert mapped["provenance"]["external_invoked"] is False
    _assert_safe_public_payload(mapped)


def test_dimension_conclusion_projects_l3_research_packet() -> None:
    payload = _dimension_conclusion_payload()
    payload.update(
        {
            "composite_research_packet": {
                "consensus": "价值成员整体偏正面",
                "dominant_member": "value_meta_valuation",
                "conflict": "ML 估值弱于传统与研报综合",
            },
            "composite_quality": {
                "coverage": 1.0,
                "partial_members": [],
            },
            "conflict_summary": {
                "level": "medium",
                "reason": "ML 与研报方向不同",
            },
            "dominant_signals": [
                "研报综合目标价上修",
                "元学习估值高于当前市值",
            ],
            "missing_or_degraded_members": [],
            "final_implication": "估值维度可以支持关注，但不能覆盖市场维度冲突。",
            "limitations": [
                "估值口径来自成员模型，不是新的外部报价。",
            ],
            "research_points": [
                {
                    "claim": "价值综合不是简单平均，而是由研报与元学习估值主导。",
                    "support": "两个高权重成员给出正向估值线索。",
                    "interpretation": "ML 估值偏弱构成维度内冲突。",
                    "decision_implication": "L4 应保留关注但降低确定性。",
                    "caveat": "不把成员模型分歧包装成一致结论。",
                }
            ],
            "quality": {
                "composite_quality": {"coverage": 1.0},
                "conflict_summary": {"level": "medium"},
                "missing_or_degraded_members": [],
            },
        }
    )

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_dimension_composite_result(mapped)
    provenance = mapped["provenance"]

    assert valid, reason
    assert provenance["domain_metrics"]["composite_research_packet"]["dominant_member"] == "value_meta_valuation"
    assert provenance["domain_metrics"]["conflict_summary"]["level"] == "medium"
    assert any(item["name"] == "composite_research_packet" for item in provenance["drivers"])
    assert provenance["research_points"][0]["claim"].startswith("价值综合不是简单平均")
    assert provenance["data_quality"]["composite_quality"]["coverage"] == 1.0
    assert provenance["data_quality"]["conflict_summary"]["level"] == "medium"
    _assert_safe_public_payload(mapped)


def test_dimension_conclusion_market_maps_and_allows_sentiment_company_radar() -> None:
    payload = _dimension_conclusion_payload(
        agent_id="market_composite",
        dimension="market",
        members=[
            {
                "agent_id": "market_stock_technical",
                "stance": 0.1,
                "confidence": 0.65,
                "weight": 0.5,
                "status": "ok",
            },
            {
                "agent_id": "sentiment_company_radar",
                "stance": -0.05,
                "confidence": 0.61,
                "weight": 0.5,
                "status": "ok",
            },
        ],
    )

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_dimension_composite_result(mapped)

    assert valid, reason
    assert mapped["agent_id"] == "market_composite"
    assert mapped["dimension"] == "market"
    assert "sentiment_company_radar" in mapped["contributing_agents"]
    _assert_safe_public_payload(mapped)


def test_dimension_conclusion_value_rejects_sentiment_or_risk_member() -> None:
    payload = _dimension_conclusion_payload(
        members=[
            {
                "agent_id": "sentiment_company_radar",
                "stance": 0.0,
                "confidence": 0.5,
                "weight": 1.0,
                "status": "ok",
            }
        ],
    )

    mapped = map_external_response_to_fixed_dag_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "dimension_member_agent_mismatch"
    _assert_safe_public_payload(mapped)


def test_dimension_conclusion_rejects_weights_sum_not_approx_one() -> None:
    payload = _dimension_conclusion_payload()
    payload["members"] = [
        {
            "agent_id": "value_ml_valuation",
            "stance": 0.2,
            "confidence": 0.72,
            "weight": 0.6,
            "status": "ok",
        },
        {
            "agent_id": "value_research_synthesis",
            "stance": 0.1,
            "confidence": 0.68,
            "weight": 0.3,
            "status": "ok",
        },
    ]

    mapped = map_external_response_to_fixed_dag_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "dimension_member_weight_sum_mismatch"


def test_risk_conclusion_gate_pass_maps_to_dimension_composite_result() -> None:
    mapped = map_external_response_to_fixed_dag_object(_risk_conclusion_payload())
    valid, reason = validate_dimension_composite_result(mapped)

    assert valid, reason
    assert mapped["schema"] == "dimension_composite_result_v1"
    assert mapped["agent_id"] == "risk_composite"
    assert mapped["dimension"] == "risk"
    assert mapped["stance"] == "risk_gate"
    assert mapped["gate"] == "pass"
    assert mapped["veto"] is False
    assert mapped["risk_score"] == 0.42
    assert mapped["provenance"]["triggered_flags"] == ["bounded_risk_flag"]
    assert mapped["provenance"]["member_weight_summary"][0]["risk_score"] == 0.55
    assert mapped["provenance"]["data_quality"]["member_count"] == 2
    _assert_safe_public_payload(mapped)


def test_risk_conclusion_manual_review_maps_and_preserves_gate() -> None:
    payload = _risk_conclusion_payload(gate="manual_review")
    payload["penalty"] = 0.0

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_dimension_composite_result(mapped)

    assert valid, reason
    assert mapped["gate"] == "manual_review"
    assert mapped["veto"] is False
    assert mapped["penalty"] == 0.0
    _assert_safe_public_payload(mapped)


def test_risk_conclusion_rejects_sentiment_company_radar_contributor() -> None:
    payload = _risk_conclusion_payload()
    payload["contributing_agents"] = ["risk_identification", "sentiment_company_radar"]

    mapped = map_external_response_to_fixed_dag_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "risk_reads_sentiment"
    _assert_safe_public_payload(mapped)


def test_macro_conclusion_maps_with_value_market_dimension_weights_only() -> None:
    mapped = map_external_response_to_fixed_dag_object(_macro_conclusion_payload())
    valid, reason = validate_dimension_composite_result(mapped)

    assert valid, reason
    assert mapped["schema"] == "dimension_composite_result_v1"
    assert mapped["agent_id"] == "macro_composite"
    assert mapped["dimension"] == "macro"
    assert mapped["stance"] == "macro_regulator"
    assert mapped["dimension_weights"] == {"value": 0.55, "market": 0.45}
    assert mapped["risk_sensitivity"] == 0.6
    assert mapped["provenance"]["style_bias"] == {"quality": 0.7, "defensive": 0.3}
    assert mapped["provenance"]["member_weight_summary"][0]["agent_id"] == "macro_analysis"
    assert mapped["provenance"]["member_weight_summary"][2]["status"] == "pending"
    assert mapped["provenance"]["domain_metrics"]["regime_detail"] == {
        "confidence": 0.69,
        "name": "neutral",
    }
    _assert_safe_public_payload(mapped)


def test_macro_conclusion_rejects_dimension_weights_containing_risk_or_macro() -> None:
    payload = _macro_conclusion_payload()
    payload["dimension_weights"] = {
        "value": 0.4,
        "market": 0.4,
        "risk": 0.1,
        "macro": 0.1,
    }

    mapped = map_external_response_to_fixed_dag_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "dimension_weights_invalid_keys"
    _assert_safe_public_payload(mapped)


def test_macro_conclusion_rejects_noncanonical_member_packet() -> None:
    payload = _macro_conclusion_payload()
    payload["members"] = [
        {"agent_id": "macro_analysis", "status": "ok", "confidence": 0.8},
        {"agent_id": "股票指数估值智能体", "status": "error", "confidence": 0.0},
        {"agent_id": "macro_index_valuation", "status": "ok", "confidence": 0.9},
        {
            "agent_id": "行业热点智能体（LLM 占位）",
            "status": "partial",
            "confidence": 0.4,
            "stance": 0.035,
        },
    ]

    mapped = map_external_response_to_fixed_dag_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "macro_member_agent_mismatch"
    _assert_safe_public_payload(mapped)


def test_macro_conclusion_rejects_duplicate_formal_member() -> None:
    payload = _macro_conclusion_payload()
    payload["members"] = [
        {"agent_id": "macro_analysis", "status": "ok", "confidence": 0.8},
        {"agent_id": "macro_index_valuation", "status": "ok", "confidence": 0.9},
        {"agent_id": "macro_index_valuation", "status": "partial", "confidence": 0.0},
    ]

    mapped = map_external_response_to_fixed_dag_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "duplicate_macro_member"
    _assert_safe_public_payload(mapped)


def test_macro_conclusion_rejects_pending_member_with_nonzero_weight() -> None:
    payload = _macro_conclusion_payload()
    payload["members"] = {
        "macro_analysis": {"status": "ok", "confidence": 0.8},
        "macro_industry_hotspot": {
            "status": "pending",
            "confidence": 0.0,
            "weight": 0.2,
        },
    }

    mapped = map_external_response_to_fixed_dag_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "macro_pending_member_weight_nonzero"
    _assert_safe_public_payload(mapped)


def test_external_compute_envelope_maps_l3_tool_result() -> None:
    payload = _compute_envelope(_risk_conclusion_payload())
    payload["agent_id"] = "risk_composite"
    payload["external_agent_id"] = "risk_composite_service"

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_dimension_composite_result(mapped)

    assert valid, reason
    assert mapped["agent_id"] == "risk_composite"
    assert mapped["provenance"]["adapter_input_schema"] == "risk_conclusion_v1"
    assert mapped["provenance"]["envelope_schema"] == EXTERNAL_AGENT_COMPUTE_SCHEMA_VERSION
    assert mapped["provenance"]["compute_envelope_status"] == "ok"
    _assert_safe_public_payload(mapped)


def test_external_response_envelope_maps_l3_tool_result() -> None:
    payload = _response_envelope(_macro_conclusion_payload())

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_dimension_composite_result(mapped)

    assert valid, reason
    assert mapped["agent_id"] == "macro_composite"
    assert mapped["provenance"]["adapter_input_schema"] == "macro_conclusion_v1"
    assert mapped["provenance"]["envelope_schema"] == EXTERNAL_AGENT_RESPONSE_SCHEMA_VERSION
    assert mapped["provenance"]["response_envelope_status"] == "ok"
    _assert_safe_public_payload(mapped)


def test_l3_unsafe_raw_fields_do_not_leak() -> None:
    payload = _dimension_conclusion_payload()
    payload["raw_output"] = {"secret": "api_key=abc", "safe_metric": 1}
    payload["members"] = [
        {
            "agent_id": "value_ml_valuation",
            "stance": 0.2,
            "confidence": 0.72,
            "weight": 1.0,
            "status": "ok",
            "raw_response": "traceback",
        }
    ]
    payload["evidence"] = [
        {
            "id": "safe-evidence",
            "fact": "Safe fact.",
            "source": "bounded_l3_fixture",
            "note": "raw_response hidden",
        }
    ]

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_dimension_composite_result(mapped)

    assert valid, reason
    _assert_safe_public_payload(mapped)
    rendered = json.dumps(mapped, ensure_ascii=False).lower()
    assert "safe-evidence" in rendered
    assert "raw_response" not in rendered


def test_entity_relation_bundle_unsafe_content_does_not_leak() -> None:
    payload = _entity_relation_payload()
    payload["entities"] = [{"id": "safe"}, {"id": "api_key=abc"}]
    payload["relations"] = [{"source": "safe", "target": "secret"}]
    payload["notes"] = ["raw_response should be stripped", "safe note"]

    mapped = map_external_entity_relation_bundle_to_entity_relation_bundle(payload)
    valid, reason = validate_entity_relation_bundle(mapped)

    assert valid, reason
    rendered = json.dumps(mapped, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "secret" not in rendered
    assert "raw_response" not in rendered
    assert "safe note" in rendered


def test_external_compute_envelope_without_tool_result_fails_controlled() -> None:
    for tool_result in ("missing", None, {}):
        payload = _compute_envelope()
        payload["tool_result_schema_version"] = "agent_conclusion_v1"
        if tool_result != "missing":
            payload["tool_result"] = tool_result

        valid, reason = validate_external_compute_envelope(payload)
        mapped = map_external_compute_envelope_to_fixed_dag_object(payload)

        assert not valid
        assert reason == "compute_tool_result_missing"
        assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
        assert mapped["reason"] == "compute_tool_result_missing"
        _assert_safe_public_payload(mapped)


def test_external_compute_envelope_anti_lookahead_returns_error_conclusion() -> None:
    tool_result = _sample("agent_conclusion.response.json")
    tool_result["data_as_of"] = "2026-06-06"
    tool_result["as_of"] = "2026-06-05"

    mapped = map_external_response_to_fixed_dag_object(_compute_envelope(tool_result))
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["status"] == "error"
    assert mapped["provenance"]["adapter_failure"] is True
    assert mapped["provenance"]["reason"] == "data_as_of_after_as_of"
    assert mapped["provenance"]["provider_invoked"] is False
    assert mapped["provenance"]["external_invoked"] is False
    _assert_safe_public_payload(mapped)


def test_external_compute_envelope_identity_rejections_return_controlled_failure() -> None:
    legacy = _sample("agent_conclusion.response.json")
    legacy["agent_id"] = "a16_ml_valuation"
    mapped = map_external_response_to_fixed_dag_object(_compute_envelope(legacy))
    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "legacy_agent_id_as_primary"

    unknown = _sample("agent_conclusion.response.json")
    unknown["agent_id"] = "unknown_agent"
    mapped = map_external_response_to_fixed_dag_object(_compute_envelope(unknown))
    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unknown_agent_id"
    _assert_safe_public_payload(mapped)


def test_external_compute_envelope_unsafe_raw_content_does_not_leak() -> None:
    tool_result = _sample("agent_conclusion.response.json")
    tool_result["raw_output"] = {
        "secret": "api_key=abc",
        "safe_metric": 1,
        "endpoint": "http://example.invalid/v1/agent/invoke",
    }
    tool_result["quality"] = {"model_trust": 0.8, "raw_response": "traceback"}
    payload = _compute_envelope(tool_result)
    payload["raw_response"] = "traceback with chain-of-thought"

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["provenance"]["raw_output_keys"] == ["safe_metric"]
    assert mapped["provenance"]["quality_keys"] == ["model_trust"]
    _assert_safe_public_payload(mapped)


def test_agent_conclusion_extracts_first_batch_report_material() -> None:
    tool_result = _sample("agent_conclusion.response.json")
    valuation_bridge = {
        "current_market_value": 18000.0,
        "fair_value_center_mv": 21000.0,
        "undervalued_ratio": 0.1667,
    }
    model_vote_table = [
        {"model": "xgb", "trend": "涨", "calibrated_probability": 0.62},
        {"model": "catboost", "trend": "跌", "calibrated_probability": 0.47},
    ]
    rubric_score_table = [
        {"name_cn": "风险揭示", "score": 38.0, "weight": 0.12},
    ]
    research_points = [
        {
            "claim": "估值显著低于合理价值中枢。",
            "support": "合理市值中枢 21000 亿元，当前市值 18000 亿元。",
            "interpretation": "折价幅度已经超过轻微偏离区间。",
            "decision_implication": "估值端可作为较重要的正向输入。",
            "caveat": "仍需复核同行估值和盈利敏感性。",
        }
    ]
    tool_result["raw_output"] = {
        "valuation_bridge": valuation_bridge,
        "financial_report_period": "20240930",
        "financial_publish_time": "20241026",
        "model_vote_table": model_vote_table,
        "rubric_score_table": rubric_score_table,
        "research_points": research_points,
        "drivers": [
            {"name": "valuation_bridge", "value": valuation_bridge},
            {"name": "model_vote_table", "value": model_vote_table},
            {"name": "rubric_score_table", "value": rubric_score_table},
        ],
        "endpoint": "http://example.invalid/v1/agent/invoke",
    }
    tool_result["quality"] = {
        "dimension_coverage": 1.0,
        "financial_report_period": "20240930",
        "financial_publish_time": "20241026",
        "missing_components": [],
        "corpus_notice": "本地演示/合成公告语料。",
        "raw_response": "traceback",
    }

    mapped = map_external_response_to_fixed_dag_object(_compute_envelope(tool_result))
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["provenance"]["domain_metrics"]["valuation_bridge"] == valuation_bridge
    assert mapped["provenance"]["domain_metrics"]["financial_report_period"] == "20240930"
    assert mapped["provenance"]["domain_metrics"]["financial_publish_time"] == "20241026"
    assert mapped["provenance"]["drivers"] == [
        {"name": "valuation_bridge", "value": valuation_bridge},
        {"name": "model_vote_table", "value": model_vote_table},
        {"name": "rubric_score_table", "value": rubric_score_table},
    ]
    assert mapped["provenance"]["research_points"] == research_points
    assert mapped["provenance"]["data_quality"]["dimension_coverage"] == 1.0
    assert mapped["provenance"]["data_quality"]["financial_report_period"] == "20240930"
    assert mapped["provenance"]["data_quality"]["financial_publish_time"] == "20241026"
    assert mapped["provenance"]["data_quality"]["corpus_notice"] == "本地演示/合成公告语料。"
    _assert_safe_public_payload(mapped)


def test_health_payload_is_not_treated_as_adapter_success() -> None:
    mapped = map_external_response_to_fixed_dag_object(
        {
            "schema_version": "external_agent_health_v0",
            "agent_id": "financial_data_service",
            "status": "ok",
        }
    )

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unsupported_schema_version"


def test_l4_decision_compute_envelope_maps_to_decision_result() -> None:
    payload = _compute_envelope(
        {
            "schema": "decision_result_v1",
            "schema_version": "decision_result_v1",
            "decision": "defensive_observe",
            "score": -0.31,
            "target_price_range": {"low": None, "mid": None, "high": None},
            "dimension_views": {
                "value": {"stance": "0.12", "confidence": 0.7, "status": "complete"},
                "market": {"stance": "-0.6", "confidence": 0.8, "status": "partial"},
            },
            "reasoning_trace": [
                {"stage": "dimension_induction", "summary": "价值偏正，市场偏负。"},
                {"stage": "macro_risk_adjustment", "summary": "风险闸门通过但维持扣分。"},
                {"stage": "conflict_resolution", "summary": "冲突下选择防御观察。"},
            ],
            "confidence": 0.48,
            "status": "partial",
            "as_of": "2026-06-05",
        }
    )
    payload["agent_id"] = "decision_synthesizer"
    payload["external_agent_id"] = "l4_decision_synthesizer"

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_decision_result(mapped)

    assert valid, reason
    assert mapped["schema"] == "decision_result_v1"
    assert mapped["decision"] == "defensive_observe"
    assert mapped["score"] == -0.31
    _assert_safe_public_payload(mapped)


def test_l4_report_compute_envelope_maps_to_report_result() -> None:
    payload = _compute_envelope(
        {
            "schema": "report_result_v1",
            "schema_version": "report_result_v1",
            "title": "固定 DAG 研判报告",
            "answer": "研判流程报告：价值和市场信号存在冲突，最终维持防御观察。",
            "status": "complete",
            "sections": [
                {
                    "id": "decision",
                    "title": "综合结论",
                    "content": "L4 报告服务读取 decision_result_v1 后生成报告。",
                }
            ],
            "evidence_cards": [
                {"title": "L4 决策", "note": "decision=defensive_observe。"}
            ],
            "limitations": ["显式 compute-only L4 路径。"],
        }
    )
    payload["agent_id"] = "report_generator"
    payload["external_agent_id"] = "l4_report_generator"

    mapped = map_external_response_to_fixed_dag_object(payload)
    valid, reason = validate_report_result(mapped)

    assert valid, reason
    assert mapped["schema"] == "report_result_v1"
    assert mapped["sections"][0]["title"] == "综合结论"
    assert any("显式计算白名单路径" in item for item in mapped["limitations"])
    assert not any("compute-only" in item for item in mapped["limitations"])
    _assert_safe_public_payload(mapped)


def test_l4_provider_backed_report_rejects_raw_provider_artifacts() -> None:
    payload = _compute_envelope(
        {
            "schema": "report_result_v1",
            "schema_version": "report_result_v1",
            "title": "固定 DAG 研判报告",
            "answer": "研判流程报告：raw_provider_response should never reach transcript.",
            "status": "complete",
            "sections": [
                {
                    "id": "decision",
                    "title": "综合结论",
                    "content": "traceback endpoint secret",
                }
            ],
            "evidence_cards": [
                {"title": "L4 决策", "note": "api_key must_not_leak"}
            ],
            "limitations": ["显式计算白名单路径。"],
        }
    )
    payload["agent_id"] = "report_generator"
    payload["external_agent_id"] = "l4_report_generator"
    payload["metadata"] = {
        "provider_invoked": True,
        "used_llm_report": True,
        "raw_provider_response": "secret",
    }

    mapped = map_external_response_to_fixed_dag_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unsafe_report_result"
    _assert_safe_public_payload(mapped)


def test_l4_provider_backed_decision_rejects_raw_provider_artifacts() -> None:
    payload = _compute_envelope(
        {
            "schema": "decision_result_v1",
            "schema_version": "decision_result_v1",
            "decision": "manual_review",
            "score": 0.0,
            "target_price_range": {"low": None, "mid": None, "high": None},
            "dimension_views": {
                "value": {"stance": "0.24", "confidence": 0.78, "status": "complete"}
            },
            "reasoning_trace": [
                {
                    "stage": "dimension_induction",
                    "summary": "chain-of-thought raw_response should fail",
                },
                {"stage": "macro_risk_adjustment", "summary": "宏观压力。"},
                {"stage": "conflict_resolution", "summary": "人工复核。"},
            ],
            "confidence": 0.0,
            "status": "partial",
            "as_of": "2026-06-19",
        }
    )
    payload["agent_id"] = "decision_synthesizer"
    payload["external_agent_id"] = "l4_decision_synthesizer"
    payload["metadata"] = {
        "provider_invoked": True,
        "used_llm_decision": True,
        "provider_endpoint": "https://example.invalid",
    }

    mapped = map_external_response_to_fixed_dag_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unsafe_decision_result"
    _assert_safe_public_payload(mapped)


def test_risk_gate_member_maps_to_validator_legal_conclusion() -> None:
    model_vintage_boundary = {
        "feature_data_anti_lookahead_passed": True,
        "production_model_trained_through_feature_year": 2024,
        "as_of_market_feature_year": 2023,
        "target_feature_year": 2023,
        "model_vintage_caveat": True,
        "boundary_type": "model_vintage",
        "interpretation": "特征按 as_of 截断；这是模型版本 caveat。",
    }
    payload = {
        "schema_version": "agent_conclusion_v1",
        "agent_id": "risk_crash",
        "external_agent_id": "crash_risk",
        "legacy_agent_id": "a23_crash_risk",
        "dimension": "risk",
        "role": "gate_member",
        "risk_score": 0.64,
        "confidence": 0.57,
        "evidence": [
            {
                "fact": "Crash risk signal is elevated before the requested date.",
                "source": "sample_crash_risk_snapshot",
                "as_of": "2026-06-05",
                "data_as_of": "20260605",
                "value": 0.64,
                "unit": "risk_score",
            }
        ],
        "event_flags": [{"type": "risk_manual_review_recommended"}],
        "as_of": "2026-06-06",
        "data_as_of": "20260605",
        "status": "ok",
        "raw_output": {
            "risk_score": 0.64,
            "model_vintage_boundary": model_vintage_boundary,
            "drivers": [
                {"name": "model_vintage_boundary", "value": model_vintage_boundary}
            ],
        },
        "quality": {
            "anti_lookahead_passed": True,
            "feature_data_anti_lookahead_passed": True,
            "model_vintage_caveat": True,
        },
    }

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["agent_id"] == "risk_crash"
    assert mapped["dimension"] == "risk"
    assert mapped["stance"] == "risk_gate_member"
    assert mapped["status"] == "complete"
    assert mapped["data_as_of"] == "2026-06-05"
    assert mapped["provenance"]["risk_score"] == 0.64
    assert mapped["provenance"]["domain_metrics"]["model_vintage_boundary"] == (
        model_vintage_boundary
    )
    assert mapped["provenance"]["drivers"] == [
        {"name": "model_vintage_boundary", "value": model_vintage_boundary}
    ]
    assert mapped["provenance"]["data_quality"]["feature_data_anti_lookahead_passed"] is True
    assert mapped["provenance"]["data_quality"]["model_vintage_caveat"] is True
    assert "sentiment_company_radar" not in json.dumps(mapped)
    _assert_safe_public_payload(mapped)


def test_scaffold_unknown_risk_member_returns_controlled_failure() -> None:
    mapped = map_external_agent_conclusion_to_conclusion_object(
        _sample("agent_conclusion.risk_member.response.json")
    )

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unknown_agent_id"
    _assert_safe_public_payload(mapped)


def test_needs_clarification_maps_to_partial() -> None:
    payload = _sample("agent_conclusion.response.json")
    payload["status"] = "needs_clarification"

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["status"] == "partial"
    assert mapped["provenance"]["external_status"] == "needs_clarification"


def test_external_error_maps_to_error_conclusion_for_known_agent() -> None:
    payload = _sample("agent_conclusion.response.json")
    payload["status"] = "error"
    payload["confidence"] = 0.0

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["status"] == "error"
    assert mapped["confidence"] == 0.0


def test_identity_rejections_return_controlled_failure() -> None:
    legacy = _sample("agent_conclusion.response.json")
    legacy["agent_id"] = "a16_ml_valuation"
    assert map_external_agent_conclusion_to_conclusion_object(legacy)["reason"] == (
        "legacy_agent_id_as_primary"
    )

    removed = _sample("agent_conclusion.response.json")
    removed["agent_id"] = "value_financial_analysis"
    assert map_external_agent_conclusion_to_conclusion_object(removed)["reason"] == (
        "forbidden_agent_id"
    )

    unknown = _sample("agent_conclusion.response.json")
    unknown["agent_id"] = "unknown_agent"
    assert map_external_agent_conclusion_to_conclusion_object(unknown)["reason"] == (
        "unknown_agent_id"
    )


def test_sentiment_company_radar_cannot_map_to_risk_dimension() -> None:
    payload = _sample("agent_conclusion.response.json")
    payload["agent_id"] = "sentiment_company_radar"
    payload["external_agent_id"] = "sentiment_company_radar_service"
    payload["dimension"] = "risk"

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "sentiment_company_radar_risk_dimension"


def test_unsafe_raw_output_and_evidence_do_not_leak() -> None:
    payload = _sample("agent_conclusion.response.json")
    payload["raw_output"] = {
        "secret": "api_key=abc",
        "safe_metric": 1,
        "endpoint": "http://example.invalid/v1/agent/invoke",
    }
    payload["quality"] = {
        "model_trust": 0.8,
        "raw_response": "traceback and chain-of-thought",
    }
    payload["evidence"] = [
        {
            "fact": "Safe fact.",
            "source": "safe_source",
            "note": "endpoint=http://example.invalid",
            "as_of": "2026-06-05",
        }
    ]

    mapped = map_external_agent_conclusion_to_conclusion_object(payload)
    valid, reason = validate_conclusion_object(mapped)

    assert valid, reason
    assert mapped["provenance"]["raw_output_keys"] == ["safe_metric"]
    assert mapped["provenance"]["quality_keys"] == ["model_trust"]
    _assert_safe_public_payload(mapped)


def test_data_bundle_maps_to_internal_contract() -> None:
    mapped = map_external_data_bundle_to_data_bundle(_sample("data_bundle.response.json"))
    valid, reason = validate_data_bundle(mapped)

    assert valid, reason
    assert mapped["schema"] == "data_bundle_v1"
    assert mapped["schema_version"] == "data_bundle_v1"
    assert mapped["status"] == "complete"
    assert mapped["as_of"] == "2026-06-05"
    assert mapped["data_as_of"] == "2026-06-05"
    assert mapped["sources"] == ["sample_local_snapshot"]
    assert any("snapshot_id: sample-snapshot-600519-20260605" == note for note in mapped["notes"])
    assert any(note == "feature_key: close" for note in mapped["notes"])
    _assert_safe_public_payload(mapped)


def test_data_bundle_anti_lookahead_returns_controlled_failure() -> None:
    payload = deepcopy(_sample("data_bundle.response.json"))
    payload["data_as_of"] = "2026-06-06"
    payload["as_of"] = "2026-06-05"

    mapped = map_external_data_bundle_to_data_bundle(payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "data_as_of_after_as_of"


def test_unsupported_or_bad_envelope_returns_controlled_failure() -> None:
    error_payload = _sample("error.response.json")
    mapped = map_external_response_to_fixed_dag_object(error_payload)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "unsupported_tool_result_schema"

    missing = deepcopy(_sample("compute.response.json"))
    missing.pop("confidence")
    mapped = map_external_response_to_fixed_dag_object(missing)

    assert mapped["schema"] == ADAPTER_FAILURE_SCHEMA_VERSION
    assert mapped["reason"] == "missing_confidence"


def test_adapter_module_has_no_http_call_path() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "react_agent"
        / "fixed_dag_external_adapter.py"
    ).read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source
    assert "TestClient" not in source
    assert "external_http_agents" not in source
