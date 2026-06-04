from copy import deepcopy
from pathlib import Path

from react_agent.fixed_dag_catalog import (
    EXPECTED_DIMENSION_COUNTS,
    EXPECTED_LAYER_COUNTS,
    EXPECTED_TOTAL_COUNT,
    FIXED_DAG_AGENT_CATALOG_SCHEMA_VERSION,
    FIXED_DAG_CATALOG_PATH,
    fixed_dag_agent_ids,
    fixed_dag_agents_by_dimension,
    fixed_dag_agents_by_layer,
    fixed_dag_public_agent_catalog,
    load_fixed_dag_catalog,
    validate_fixed_dag_catalog,
)
from react_agent.fixed_dag_contracts import (
    DIMENSION_GROUPS,
    L1_AGENT_IDS,
    L2_CONCLUSION_AGENT_IDS,
    L3_COMPOSITE_AGENT_IDS,
    L4_AGENT_IDS,
    RESET_RUNTIME_AGENT_IDS,
    build_default_fixed_dag_plan,
    validate_fixed_dag_plan,
)

EXPECTED_RESET_RUNTIME_AGENT_IDS = (
    "route_planner",
    "financial_data_service",
    "entity_relation_extractor",
    "value_traditional_valuation",
    "value_ml_valuation",
    "value_meta_valuation",
    "value_research_synthesis",
    "market_stock_technical",
    "market_fund_manager_behavior",
    "market_ipo_investor_behavior",
    "market_capital_flow_chip",
    "sentiment_company_radar",
    "risk_crash",
    "risk_financial_fraud",
    "risk_identification",
    "risk_compliance_review",
    "macro_analysis",
    "macro_commodity_pricing",
    "macro_index_valuation",
    "macro_sentiment",
    "macro_industry_hotspot",
    "value_composite",
    "market_composite",
    "risk_composite",
    "macro_composite",
    "decision_synthesizer",
    "report_generator",
)


def test_fixed_dag_catalog_file_exists_and_validates() -> None:
    assert FIXED_DAG_CATALOG_PATH == Path(__file__).resolve().parents[2] / "config" / "fixed_dag" / "agent_catalog.json"
    assert FIXED_DAG_CATALOG_PATH.exists()

    catalog = load_fixed_dag_catalog()
    valid, reason = validate_fixed_dag_catalog(catalog)

    assert valid, reason
    assert catalog["schema_version"] == FIXED_DAG_AGENT_CATALOG_SCHEMA_VERSION
    assert catalog["total_count"] == EXPECTED_TOTAL_COUNT
    assert catalog["layer_counts"] == EXPECTED_LAYER_COUNTS
    assert catalog["dimension_counts"] == EXPECTED_DIMENSION_COUNTS
    assert len(catalog["agents"]) == 27
    ids = [agent["id"] for agent in catalog["agents"]]
    assert "value_financial_analysis" not in ids
    assert all(not agent_id.startswith("a") or not agent_id[1:3].isdigit() for agent_id in ids)


def test_fixed_dag_catalog_preserves_sentiment_market_only_boundary() -> None:
    catalog = load_fixed_dag_catalog()
    by_id = {agent["id"]: agent for agent in catalog["agents"]}

    sentiment = by_id["sentiment_company_radar"]
    assert sentiment["layer"] == "L2"
    assert sentiment["dimension"] == "market"
    assert sentiment["downstream"] == ["market_composite"]
    assert "sentiment_company_radar" in by_id["market_composite"]["upstream"]
    assert "sentiment_company_radar" not in by_id["risk_composite"]["upstream"]


def test_fixed_dag_catalog_projection_counts_enabled_agents() -> None:
    payload = fixed_dag_public_agent_catalog()

    assert payload["totals"] == {
        "configCount": 27,
        "runtimeCount": 27,
        "disabledIds": [],
    }
    assert [layer["layer"] for layer in payload["layers"]] == ["L1", "L2", "L3", "L4"]
    assert [len(layer["agents"]) for layer in payload["layers"]] == [3, 18, 4, 2]
    assert payload["disabledAgents"] == []


def test_fixed_dag_catalog_helpers_match_contract_constants() -> None:
    assert fixed_dag_agent_ids() == EXPECTED_RESET_RUNTIME_AGENT_IDS
    assert fixed_dag_agent_ids() == RESET_RUNTIME_AGENT_IDS
    by_layer = fixed_dag_agents_by_layer()
    by_dimension = fixed_dag_agents_by_dimension()

    assert by_layer["L1"] == L1_AGENT_IDS
    assert by_layer["L2"] == L2_CONCLUSION_AGENT_IDS
    assert by_layer["L3"] == L3_COMPOSITE_AGENT_IDS
    assert by_layer["L4"] == L4_AGENT_IDS
    assert by_dimension["value"] == DIMENSION_GROUPS["value"]
    assert by_dimension["market"] == DIMENSION_GROUPS["market"]
    assert by_dimension["risk"] == DIMENSION_GROUPS["risk"]
    assert by_dimension["macro"] == DIMENSION_GROUPS["macro"]

    plan = build_default_fixed_dag_plan("q", as_of="2026-06-04")
    valid, reason = validate_fixed_dag_plan(plan)
    assert valid, reason


def test_fixed_dag_catalog_validator_rejects_duplicate_id() -> None:
    catalog = deepcopy(load_fixed_dag_catalog())
    catalog["agents"][1]["id"] = catalog["agents"][0]["id"]

    valid, reason = validate_fixed_dag_catalog(catalog)

    assert not valid
    assert reason == "duplicate_agent_id"


def test_fixed_dag_catalog_validator_rejects_bad_count() -> None:
    catalog = deepcopy(load_fixed_dag_catalog())
    catalog["total_count"] = 28

    valid, reason = validate_fixed_dag_catalog(catalog)

    assert not valid
    assert reason == "total_count_mismatch"


def test_fixed_dag_catalog_validator_rejects_ann_id() -> None:
    catalog = deepcopy(load_fixed_dag_catalog())
    catalog["agents"][0]["id"] = "a01_cio_orchestrator"

    valid, reason = validate_fixed_dag_catalog(catalog)

    assert not valid
    assert reason == "legacy_ann_id:a01_cio_orchestrator"


def test_fixed_dag_catalog_validator_rejects_sentiment_to_risk_edge() -> None:
    catalog = deepcopy(load_fixed_dag_catalog())
    by_id = {agent["id"]: agent for agent in catalog["agents"]}
    by_id["sentiment_company_radar"]["downstream"] = ["risk_composite"]

    valid, reason = validate_fixed_dag_catalog(catalog)

    assert not valid
    assert reason == "sentiment_downstream_mismatch"


def test_fixed_dag_catalog_validator_rejects_risk_composite_sentiment_input() -> None:
    catalog = deepcopy(load_fixed_dag_catalog())
    by_id = {agent["id"]: agent for agent in catalog["agents"]}
    by_id["risk_composite"]["upstream"].append("sentiment_company_radar")

    valid, reason = validate_fixed_dag_catalog(catalog)

    assert not valid
    assert reason == "risk_composite_reads_sentiment"
