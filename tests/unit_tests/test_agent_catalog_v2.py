import json
from pathlib import Path

from react_agent.agents import AGENT_METADATA, AgentMetadata, load_metadata_from_dir


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config" / "agents"

TARGET_IDS_BY_LAYER = {
    "L1": ["a01_cio_orchestrator", "a22_financial_data_service"],
    "L2": [
        "a17_traditional_valuation",
        "a16_ml_valuation",
        "a18_meta_valuation",
        "a11_index_technical_analysis",
        "a04_commodity_hedging",
        "a06_financial_statement_analysis",
        "a12_research_synthesis",
        "a13_fund_manager_behavior",
        "a14_ipo_investor_behavior",
        "a10_stock_technical_analysis",
        "a19_risk_identification",
        "a20_compliance_review",
        "a23_crash_risk",
        "a24_financial_fraud_risk",
        "a15_entity_relation_extraction",
        "a07_macro_sentiment",
        "a08_industry_hotspot",
        "a09_company_sentiment_radar",
        "a03_macro_industry_research",
    ],
    "L3": ["a26_composite_valuation", "a27_risk_constraint", "a28_composite_sentiment"],
    "L4": ["a25_report_center"],
}

EXPECTED_FORMAL_BUSINESS_ORDER = [
    (1, "a01_cio_orchestrator", "L1", "解析层", "问题解析", "问题解析与协同编排智能体"),
    (2, "a22_financial_data_service", "L1", "解析层", "数据支撑", "金融数据服务智能体"),
    (3, "a17_traditional_valuation", "L2", "分析层", "价值分析", "传统企业估值智能体"),
    (4, "a16_ml_valuation", "L2", "分析层", "价值分析", "机器学习企业估值智能体"),
    (5, "a18_meta_valuation", "L2", "分析层", "价值分析", "元学习企业估值智能体"),
    (6, "a11_index_technical_analysis", "L2", "分析层", "价值分析", "股票指数估值智能体"),
    (7, "a04_commodity_hedging", "L2", "分析层", "价值分析", "商品定价分析智能体"),
    (8, "a06_financial_statement_analysis", "L2", "分析层", "价值分析", "企业财务分析智能体"),
    (9, "a12_research_synthesis", "L2", "分析层", "行为分析", "分析师研报与观点集成智能体"),
    (10, "a13_fund_manager_behavior", "L2", "分析层", "行为分析", "基金经理投资行为分析智能体"),
    (11, "a14_ipo_investor_behavior", "L2", "分析层", "行为分析", "IPO投资者构成与行为分析智能体"),
    (12, "a10_stock_technical_analysis", "L2", "分析层", "行为分析", "个股技术分析智能体"),
    (13, "a19_risk_identification", "L2", "分析层", "风险分析", "风险识别智能体"),
    (14, "a20_compliance_review", "L2", "分析层", "风险分析", "公告合规审查智能体"),
    (15, "a23_crash_risk", "L2", "分析层", "风险分析", "股价崩盘风险智能体"),
    (16, "a24_financial_fraud_risk", "L2", "分析层", "风险分析", "财务欺诈（造假）风险智能体"),
    (17, "a15_entity_relation_extraction", "L2", "分析层", "舆情分析", "实体关系抽取智能体"),
    (18, "a07_macro_sentiment", "L2", "分析层", "舆情分析", "宏观情绪感知智能体"),
    (19, "a08_industry_hotspot", "L2", "分析层", "舆情分析", "行业热点洞悉智能体"),
    (20, "a09_company_sentiment_radar", "L2", "分析层", "舆情分析", "企业舆情雷达智能体"),
    (21, "a26_composite_valuation", "L3", "应用层", "估值研判", "综合估值智能体"),
    (22, "a27_risk_constraint", "L3", "应用层", "风险控制", "风险约束智能体"),
    (23, "a28_composite_sentiment", "L3", "应用层", "舆情判断", "综合舆情智能体"),
    (24, "a25_report_center", "L4", "报告层", "报告生成", "报告生成智能体"),
]

DISABLED_NON_EXCEL_FUNCTIONAL_IDS = {
    "a05_annual_report_analysis",
    "a21_portfolio_manager",
}

REMOVED_OLD_IDS = {
    "a02_task_router",
    "a03_macro_policy",
    "a04_industry_layout",
    "a05_product_pricing",
    "a06_financial_reports",
    "a07_financial_modeling",
    "a08_tech_due_diligence",
    "a09_macro_sentiment",
    "a10_industry_sentiment",
    "a11_equity_sentiment",
    "a12_ipo_investor_behavior",
    "a13_index_technical_analysis",
    "a14_single_stock_tech",
    "a15_research_synthesis",
    "a16_fund_manager_behavior",
    "a17_client_profile",
    "a18_primary_secondary_valuation",
    "a19_market_risk",
    "a20_fundamental_risk",
    "a21_reg_compliance",
    "a22_suitability_review",
    "a23_portfolio_opt",
    "a26_sci_tech_valuation",
    "a27_portfolio_backtest",
}

EXPECTED_BUSINESS_TAXONOMY = {
    agent_id: (name, business_layer, business_category)
    for _order, agent_id, _layer, business_layer, business_category, name
    in EXPECTED_FORMAL_BUSINESS_ORDER
}


def _load_config_metadata() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CONFIG_DIR.glob("agent_*.json"))
    ]


def _catalog_sort_key(item: dict) -> tuple[int, int, str]:
    order = item.get("business_order")
    if order is not None:
        return (0, int(order), item["id"])
    if item.get("business_status") == "legacy_retained":
        return (1, 0, item["id"])
    if not item.get("default_enabled", True) or item.get("business_status") == "disabled_historical":
        return (2, 0, item["id"])
    return (1, 1, item["id"])


def test_agent_catalog_v2_config_shape() -> None:
    metadata = _load_config_metadata()
    ids = [item["id"] for item in metadata]
    enabled = [item for item in metadata if item["default_enabled"] is True]
    disabled = [item for item in metadata if item["default_enabled"] is False]
    assert len(metadata) == 27
    assert len(enabled) == 25
    assert {item["id"] for item in disabled} == DISABLED_NON_EXCEL_FUNCTIONAL_IDS
    assert all(item["version"] == "catalog_v2_sheet2" for item in metadata)
    assert not (set(ids) & REMOVED_OLD_IDS)

    for layer, expected_ids in TARGET_IDS_BY_LAYER.items():
        actual_ids = [
            item["id"]
            for item in sorted(metadata, key=_catalog_sort_key)
            if item["layer"] == layer and item["default_enabled"]
        ]
        assert actual_ids == expected_ids


def test_excel_functional_catalog_excludes_special_runtime_roles() -> None:
    metadata = _load_config_metadata()
    enabled_ids = {item["id"] for item in metadata if item["default_enabled"]}
    special_ids = {"a01_cio_orchestrator", "a25_report_center"}
    assert special_ids <= enabled_ids
    assert "a02_task_router" not in enabled_ids
    assert len(enabled_ids - special_ids) == 23


def test_agent_catalog_v2_required_metadata_fields() -> None:
    required = {
        "id",
        "name",
        "description",
        "capabilities",
        "input_type",
        "latency_level",
        "cost_level",
        "version",
        "layer",
        "team",
        "role_type",
        "business_order",
        "business_role",
        "business_status",
        "business_layer",
        "business_category",
        "business_subcategory",
        "default_enabled",
    }
    for item in _load_config_metadata():
        assert set(item) == required
        assert item["name"]
        assert item["description"].startswith("功能：")
        assert "输入：" in item["description"]
        assert "输出：" in item["description"]
        assert item["capabilities"]
        assert item["business_layer"]
        assert item["business_category"]
        assert item["business_role"]
        assert item["business_status"] in {"formal", "legacy_retained", "disabled_historical"}


def test_agent_catalog_latest_business_taxonomy_fields() -> None:
    metadata = {item["id"]: item for item in _load_config_metadata()}
    for agent_id, (name, business_layer, business_category) in EXPECTED_BUSINESS_TAXONOMY.items():
        item = metadata[agent_id]
        assert item["name"] == name
        assert item["business_layer"] == business_layer
        assert item["business_category"] == business_category
        assert item["business_role"] == name
        assert item["business_status"] == "formal"

    assert metadata["a03_macro_industry_research"]["name"] == "宏观分析智能体"
    assert metadata["a03_macro_industry_research"]["business_layer"] == "保留层（旧CSV）"
    assert metadata["a03_macro_industry_research"]["business_order"] is None
    assert metadata["a03_macro_industry_research"]["business_status"] == "legacy_retained"
    assert "未列入 agent_layer_latest.xlsx" in metadata["a03_macro_industry_research"][
        "business_subcategory"
    ]

    for disabled_id in DISABLED_NON_EXCEL_FUNCTIONAL_IDS:
        assert metadata[disabled_id]["business_layer"] == "历史保留（disabled）"
        assert metadata[disabled_id]["business_order"] is None
        assert metadata[disabled_id]["business_status"] == "disabled_historical"


def test_formal_business_order_matches_authoritative_table() -> None:
    metadata = {item["id"]: item for item in _load_config_metadata()}
    ordered_ids = [
        item["id"]
        for item in sorted(metadata.values(), key=_catalog_sort_key)
        if item.get("business_status") == "formal"
    ]
    assert ordered_ids == [agent_id for _order, agent_id, *_rest in EXPECTED_FORMAL_BUSINESS_ORDER]

    orders = [
        item["business_order"]
        for item in metadata.values()
        if item.get("business_status") == "formal"
    ]
    assert sorted(orders) == list(range(1, 25))

    for order, agent_id, layer, business_layer, business_category, name in EXPECTED_FORMAL_BUSINESS_ORDER:
        item = metadata[agent_id]
        assert item["business_order"] == order
        assert item["layer"] == layer
        assert item["business_layer"] == business_layer
        assert item["business_category"] == business_category
        assert item["name"] == name
        assert item["business_role"] == name

    assert [metadata[agent_id]["layer"] for _order, agent_id, *_ in EXPECTED_FORMAL_BUSINESS_ORDER[:2]] == ["L1", "L1"]
    assert {metadata[agent_id]["layer"] for _order, agent_id, *_ in EXPECTED_FORMAL_BUSINESS_ORDER[2:20]} == {"L2"}
    assert {metadata[agent_id]["layer"] for _order, agent_id, *_ in EXPECTED_FORMAL_BUSINESS_ORDER[20:23]} == {"L3"}
    assert metadata["a25_report_center"]["layer"] == "L4"


def test_a22_profile_is_limited_to_explicit_data_service_requests() -> None:
    metadata = {item["id"]: item for item in _load_config_metadata()}
    description = metadata["a22_financial_data_service"]["description"]
    assert "明确要求原始数据获取" in description
    assert "数据库/API 查询" in description
    assert "不应自动把本智能体作为通用支撑" in description


def test_route_sensitive_profiles_are_specific() -> None:
    metadata = {item["id"]: item for item in _load_config_metadata()}

    a04_description = metadata["a04_commodity_hedging"]["description"]
    old_display_name = "大宗商品价格分析" + "与套期保值智能体"
    assert metadata["a04_commodity_hedging"]["name"] == "商品定价分析智能体"
    assert old_display_name not in a04_description
    assert "commodity pricing" in a04_description
    assert "price influence" in a04_description
    assert "商品定价" in a04_description
    assert "铜" in a04_description
    assert "股价崩盘风险" in a04_description

    a06_description = metadata["a06_financial_statement_analysis"]["description"]
    assert "财务报表" in a06_description
    assert "企业财务健康" in a06_description
    assert "不要因为用户提出普通“风险”" in a06_description
    assert "应优先选择 a23_crash_risk" in a06_description

    a23_description = metadata["a23_crash_risk"]["description"]
    assert "crash risk" in a23_description
    assert "NCSKEW" in a23_description
    assert "DUVOL" in a23_description
    assert "不代表排除本智能体" in a23_description
    assert "不要自动加派 a06_financial_statement_analysis" in a23_description


def test_load_metadata_from_dir_uses_filename_order(tmp_path) -> None:
    first = {
        "id": "ordered_first",
        "name": "first",
        "description": "first",
        "capabilities": [],
        "input_type": "",
        "latency_level": "",
        "cost_level": "",
        "version": "",
        "layer": "L2",
    }
    second = dict(first, id="ordered_second", name="second")
    (tmp_path / "agent_010.json").write_text(json.dumps(second), encoding="utf-8")
    (tmp_path / "agent_001.json").write_text(json.dumps(first), encoding="utf-8")

    previous = dict(AGENT_METADATA)
    try:
        AGENT_METADATA.clear()
        load_metadata_from_dir(tmp_path)
        assert list(AGENT_METADATA) == ["ordered_first", "ordered_second"]
        assert all(isinstance(meta, AgentMetadata) for meta in AGENT_METADATA.values())
    finally:
        AGENT_METADATA.clear()
        AGENT_METADATA.update(previous)
