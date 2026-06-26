"""Display labels used by fixed-DAG contract projections."""

from __future__ import annotations

STAGE_TITLE_LABELS: dict[str, str] = {
    "planning": "规划",
    "evidence": "证据接入",
    "l2_analysis": "L2 分析",
    "dimension_composite": "维度综合",
    "decision": "决策",
    "report": "报告",
}

AGENT_TITLE_LABELS: dict[str, str] = {
    "route_planner": "路径规划器",
    "financial_data_service": "金融数据服务",
    "entity_relation_extractor": "实体关系抽取器",
    "value_traditional_valuation": "传统企业估值",
    "value_ml_valuation": "机器学习企业估值",
    "value_meta_valuation": "元学习企业估值",
    "value_research_synthesis": "研报观点综合",
    "market_stock_technical": "个股技术分析",
    "market_fund_manager_behavior": "基金经理行为分析",
    "market_ipo_investor_behavior": "IPO 投资者行为分析",
    "market_capital_flow_chip": "资金流与筹码分析",
    "sentiment_company_radar": "企业舆情雷达",
    "risk_crash": "股价崩盘风险",
    "risk_financial_fraud": "财务欺诈风险",
    "risk_identification": "风险识别",
    "risk_compliance_review": "公告合规审查",
    "macro_analysis": "宏观分析",
    "macro_commodity_pricing": "商品定价分析",
    "macro_index_valuation": "股票指数估值",
    "macro_sentiment": "宏观情绪感知",
    "macro_industry_hotspot": "行业热点洞察",
    "value_composite": "价值综合",
    "market_composite": "市场综合",
    "risk_composite": "风险综合",
    "macro_composite": "宏观综合",
    "decision_synthesizer": "决策综合器",
    "report_generator": "报告生成器",
}

DIMENSION_TITLE_LABELS: dict[str, str] = {
    "value": "价值综合",
    "market": "市场综合",
    "risk": "风险综合",
    "macro": "宏观综合",
}


__all__ = [
    "AGENT_TITLE_LABELS",
    "DIMENSION_TITLE_LABELS",
    "STAGE_TITLE_LABELS",
]
