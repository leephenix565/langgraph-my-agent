from react_agent.fixed_dag_external_health import validate_external_health_identity


def test_health_identity_accepts_each_overstrict_audit_candidate() -> None:
    candidates = [
        (
            "value_traditional_valuation",
            {"agent_id": "valuation_traditional", "fixed_dag_agent_id": "value_traditional_valuation", "external_agent_id": "valuation_traditional"},
            "explicit_bridge_compatibility",
            10000,
        ),
        (
            "value_ml_valuation",
            {"agent_id": "valuation_ml", "fixed_dag_agent_id": "value_ml_valuation", "external_agent_id": "valuation_ml"},
            "explicit_bridge_compatibility",
            10001,
        ),
        (
            "value_meta_valuation",
            {"agent_id": "valuation_meta", "fixed_dag_agent_id": "value_meta_valuation", "external_agent_id": "valuation_meta"},
            "explicit_bridge_compatibility",
            10002,
        ),
        (
            "risk_crash",
            {"agent_id": "crash_risk", "fixed_dag_agent_id": "risk_crash", "external_agent_id": "crash_risk"},
            "explicit_bridge_compatibility",
            10012,
        ),
        (
            "risk_financial_fraud",
            {"agent_id": "financial_fraud_agent", "fixed_dag_agent_id": "risk_financial_fraud", "external_agent_id": "financial_fraud_agent"},
            "explicit_bridge_compatibility",
            10013,
        ),
        (
            "macro_commodity_pricing",
            {"agent_id": "price_influence_agent", "fixed_dag_agent_id": "macro_commodity_pricing", "external_agent_id": "price_influence_agent"},
            "explicit_bridge_compatibility",
            10004,
        ),
        (
            "risk_identification",
            {"agent_id": "market_risk_reasoning", "external_agent_id": ""},
            "registered_legacy_compatibility",
            10010,
        ),
        (
            "risk_compliance_review",
            {"agent_id": "announcement_compliance", "external_agent_id": ""},
            "registered_legacy_compatibility",
            10011,
        ),
        (
            "risk_composite",
            {"agent_id": "risk_synthesis", "external_agent_id": ""},
            "registered_legacy_compatibility",
            10016,
        ),
        (
            "macro_composite",
            {"agent_id": "macro_synthesis", "external_agent_id": "macro_synthesis_service"},
            "registered_legacy_compatibility",
            10024,
        ),
    ]

    for expected_agent_id, payload, profile, port in candidates:
        result = validate_external_health_identity(
            payload,
            expected_agent_id=expected_agent_id,
            expected_external_agent_id=str(payload.get("external_agent_id") or payload["agent_id"]),
            expected_port=port,
            observed_port=port,
            source_matches=True,
        )

        assert result["health_identity_pass"] is True, expected_agent_id
        assert result["identity_profile"] == profile
        assert result["compatibility_debt"] is True


def test_health_identity_accepts_canonical_formal_agent_id() -> None:
    result = validate_external_health_identity(
        {
            "schema_version": "external_agent_health_v0",
            "agent_id": "financial_data_service",
            "external_agent_id": "financial_data_service",
            "status": "ok",
        },
        expected_agent_id="financial_data_service",
        expected_external_agent_id="financial_data_service",
    )

    assert result["health_identity_pass"] is True
    assert result["identity_profile"] == "canonical"
    assert result["compatibility_debt"] is False


def test_health_identity_accepts_explicit_bridge_compatibility_profile() -> None:
    result = validate_external_health_identity(
        {
            "schema_version": "external_agent_health_v0",
            "agent_id": "valuation_ml",
            "fixed_dag_agent_id": "value_ml_valuation",
            "external_agent_id": "valuation_ml",
            "status": "ok",
        },
        expected_agent_id="value_ml_valuation",
        expected_external_agent_id="valuation_ml",
    )

    assert result["health_identity_pass"] is True
    assert result["identity_profile"] == "explicit_bridge_compatibility"
    assert result["compatibility_debt"] is True


def test_health_identity_accepts_registered_legacy_alias_with_source_and_port() -> None:
    result = validate_external_health_identity(
        {
            "schema_version": "external_agent_health_v0",
            "agent_id": "risk_synthesis",
            "external_agent_id": "",
            "status": "ok",
        },
        expected_agent_id="risk_composite",
        expected_external_agent_id="risk_synthesis",
        expected_port=10016,
        observed_port=10016,
        source_matches=True,
    )

    assert result["health_identity_pass"] is True
    assert result["identity_profile"] == "registered_legacy_compatibility"
    assert result["compatibility_debt"] is True


def test_health_identity_rejects_unregistered_ipo_service_local_primary() -> None:
    result = validate_external_health_identity(
        {
            "schema_version": "external_agent_health_v0",
            "agent_id": "ipo_investor_behavior_comprehensive",
            "external_agent_id": "",
            "status": "ok",
        },
        expected_agent_id="market_ipo_investor_behavior",
        expected_external_agent_id="ipo_investor_behavior",
        expected_port=10008,
        observed_port=10008,
    )

    assert result["health_identity_pass"] is False
    assert result["reason"] == "legacy_alias_not_registered"


def test_health_identity_rejects_formal_field_mismatch() -> None:
    result = validate_external_health_identity(
        {
            "agent_id": "valuation_ml",
            "fixed_dag_agent_id": "value_meta_valuation",
            "external_agent_id": "valuation_ml",
        },
        expected_agent_id="value_ml_valuation",
        expected_external_agent_id="valuation_ml",
    )

    assert result["health_identity_pass"] is False
    assert result["reason"] == "fixed_dag_agent_id_mismatch"


def test_health_identity_rejects_legacy_alias_without_matching_source() -> None:
    result = validate_external_health_identity(
        {"agent_id": "announcement_compliance", "external_agent_id": ""},
        expected_agent_id="risk_compliance_review",
        expected_external_agent_id="announcement_compliance",
        expected_port=10011,
        observed_port=10011,
        source_matches=False,
    )

    assert result["health_identity_pass"] is False
    assert result["reason"] == "source_mismatch"


def test_health_identity_rejects_legacy_ann_primary_id() -> None:
    result = validate_external_health_identity(
        {"agent_id": "a12_risk_compliance_review", "external_agent_id": ""},
        expected_agent_id="risk_compliance_review",
        expected_external_agent_id="announcement_compliance",
        expected_port=10011,
        observed_port=10011,
    )

    assert result["health_identity_pass"] is False
    assert result["reason"] == "legacy_primary_id_not_allowed"


def test_health_identity_rejects_sentiment_as_risk_composite_alias() -> None:
    result = validate_external_health_identity(
        {"agent_id": "company_sentiment_radar", "external_agent_id": ""},
        expected_agent_id="risk_composite",
        expected_external_agent_id="risk_synthesis",
        expected_port=10016,
        observed_port=10016,
    )

    assert result["health_identity_pass"] is False
    assert result["reason"] == "sentiment_company_radar_not_risk"
