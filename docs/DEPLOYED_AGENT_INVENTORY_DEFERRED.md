# Deployed Agent Inventory Deferred

This document records server-deployed-but-deferred evidence for Phase R8-6B.
It is documentation evidence, not runtime authority.

## Boundary

- Directory presence does not mean health verified.
- A listening process does not mean health verified.
- Health verified does not mean compute/invoke verified.
- Compute/invoke verified does not mean `live_verified=true`.
- `live_verified=true` does not mean `invoke_enabled_by_default=true`.
- R8-6B does not call external `/v1/agent/invoke`.
- R8-6B does not change `config/fixed_dag/runtime_bindings.json`.
- R8-6B does not set `live_verified=true` or `invoke_enabled_by_default=true`.
- R8-6B uses default-off internal LLM placeholders for L2 conclusion slots only.

## Inventory

| fixed DAG id | server-deployed evidence | R8-6B status | runtime action |
| --- | --- | --- | --- |
| `sentiment_company_radar` | 企业舆情雷达智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `macro_commodity_pricing` | 商品定价分析智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `macro_sentiment` | 宏观情绪感知智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `macro_industry_hotspot` | 行业热点洞悉智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `financial_data_service` | 金融数据服务智能体 | `deployed_but_deferred` | deterministic L1 bundle remains active |
| `value_research_synthesis` | 测试之分析师智能体 / 分析师研报与观点集成智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `risk_crash` | 股价崩盘风险代码 / 股价崩盘风险智能体 | `deployed_but_deferred` | internal LLM placeholder only; owner/source needs de-duplication |
| `value_meta_valuation` | 元学习企业估值智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `macro_index_valuation` | 股票指数估值智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `risk_financial_fraud` | 财务造假风险智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `entity_relation_extractor` | 实体关系抽取智能体 | `deployed_but_deferred` | deterministic L1 placeholder remains active |
| `value_traditional_valuation` | 传统企业估值智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `value_ml_valuation` | 机器学习企业估值智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `market_stock_technical` | 个股技术分析智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `risk_compliance_review` | 公告合规审查智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `macro_analysis` | 宏观分析智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `market_ipo_investor_behavior` | IPO投资者行为智能体 | `deployed_but_deferred` | internal LLM placeholder only |
| `market_capital_flow_chip` | 资金流智能体 | `deployed_but_deferred` | internal LLM placeholder only |

## Non-Claims

This inventory does not claim provider readiness, search readiness, external
adapter readiness, production deployment readiness, business correctness, market
data correctness, or public transcript readiness. It is a handoff list for later
external adapter readiness, live verification, and runtime binding enablement.
