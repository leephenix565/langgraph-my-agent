# Agent Catalog v2 Sheet2 Mapping

Phase: `EXCEL-CATALOG-ALIGN-1` + `EXTERNAL-HTTP-P0` + `EXTERNAL-HTTP-P1A` + `LATEST-LAYER-SHEET`
Business taxonomy authority: `/sdb/dlut/agent_layer_latest.xlsx`
Endpoint/profile lineage: `/sdb/dlut/智能体分工及访问接口.csv` plus `/sdb/dlut/智能体的描述.csv`
Repository authority after this alignment: this mapping document plus `config/agents/*.json`

## Current Catalog Facts

- `/sdb/dlut/agent_layer_latest.xlsx` is now the authority for business-layer and business-category metadata on listed agents.
- Runtime `layer` remains the graph dispatch layer (`L1`/`L2`/`L3`/`L4`) and must not be overwritten by business layers such as `解析层` / `分析层` / `应用层` / `报告层`.
- Excel/CSV lineage remains the authority for endpoint defaults and profile intent where the latest layer sheet does not carry service URLs.
- The main-system row `主系统 / 资本市场认知多智能体系统` is excluded from the functional-agent count.
- Router runtime, `a01_cio_orchestrator`, and `a25_report_center` are special system runtime roles. They must not be replaced by external functional profiles.
- `config/agents/*.json` includes `business_layer`, `business_category`, and `business_subcategory` for the latest business taxonomy without changing dispatch semantics.
- `config/agents` now has `configCount=27`, `runtimeCount=25`, and `disabledIds=["a05_annual_report_analysis", "a21_portfolio_manager"]`.
- Enabled runtime roles are L1=1, L2=12, L3=11, L4=1. The 23 enabled functional agents are `runtimeCount - 2 special roles`.
- Layer display in `/api/agents` includes disabled metadata, so public catalog layer rows are L1=1, L2=13, L3=12, L4=1.
- Disabled retained metadata may appear in catalog metadata, but disabled ids are not graph nodes, not `AGENT_TOOLS` tools, and not callable.
- `a02_task_router` metadata remains absent. The real Router runtime remains `router_node` inside `src/react_agent/graph.py`.
- Catalog/profile alignment is separate from runtime wrapper integration and does not bypass `AGENT_TOOLS`.
- Runtime wrapper P0 migrates `a16/a17/a18` onto the generic table-driven external HTTP wrapper using Excel/CSV production invoke endpoints as defaults.
- Runtime wrapper P1-A registers 10 dev-present functional agents on the same generic external HTTP wrapper path. Wrapper registration is mock/unit verified only and is not live service verification.
- `a03_macro_industry_research` remains enabled and callable because its external wrapper is already live-verified, even though `宏观分析智能体` is not listed in `/sdb/dlut/agent_layer_latest.xlsx`; it is tagged as `保留层（旧CSV）/价值分析` pending an explicit taxonomy decision.
- `a27_risk_constraint` remains held because the route standard is unclear. Source-missing agents remain pending delivery or an explicitly approved endpoint-only policy.

## Runtime Chain

```text
config/agents/*.json
-> react_agent.agents.load_metadata_from_dir(...), sorted by filename
-> AGENT_METADATA
-> graph_bootstrap.bootstrap_agent_runtime()
-> generic external HTTP wrapper registration for P0 + P1-A ids
-> default _build_agent_tool(...) fallback for other enabled agents
-> AGENT_TOOLS as the execution truth
-> /api/agents as public metadata projection
```

The 13 P0 + P1-A ids are runtime-wrapped external HTTP agents. Other enabled functional profiles default to LLM tools until a repo-side wrapper is explicitly implemented and registered.

## Enabled Catalog Table

| File | Runtime agent id | Layer | Team | Business layer | Business category | Official name | Execution status |
|---|---|---|---|---|---|---|---|
| `agent_001.json` | `a01_cio_orchestrator` | L1 | management | 解析层（2） | 问题解析 | 问题解析与协同编排智能体 | special runtime role |
| `agent_003.json` | `a03_macro_industry_research` | L2 | fundamental | 保留层（旧CSV） | 价值分析 | 宏观分析智能体 | generic HTTP wrapper -> `macro_analysis`; pending latest-sheet decision |
| `agent_004.json` | `a04_commodity_hedging` | L2 | fundamental | 分析层（17） | 价值分析 | 商品定价分析智能体 | generic HTTP wrapper -> `price_influence_agent` |
| `agent_006.json` | `a06_financial_statement_analysis` | L2 | fundamental | 分析层（17） | 价值分析 | 企业财务分析智能体 | generic HTTP wrapper -> `financial_report_agent` |
| `agent_007.json` | `a07_macro_sentiment` | L2 | sentiment | 分析层（17） | 舆情分析 | 宏观情绪感知智能体 | source not present / pending owner description |
| `agent_008.json` | `a08_industry_hotspot` | L2 | sentiment | 分析层（17） | 舆情分析 | 行业热点洞悉智能体 | source not present / pending owner description |
| `agent_009.json` | `a09_company_sentiment_radar` | L2 | sentiment | 分析层（17） | 舆情分析 | 企业舆情雷达智能体 | source not present / pending owner description |
| `agent_010.json` | `a10_stock_technical_analysis` | L2 | technical | 分析层（17） | 行为分析 | 个股技术分析智能体 | generic HTTP wrapper -> `technical_stock` |
| `agent_012.json` | `a12_research_synthesis` | L2 | behavior | 分析层（17） | 行为分析 | 分析师研报与观点集成智能体 | generic HTTP wrapper -> `analyst_research` |
| `agent_013.json` | `a13_fund_manager_behavior` | L2 | behavior | 分析层（17） | 行为分析 | 基金经理投资行为分析智能体 | source not present / pending owner description |
| `agent_014.json` | `a14_ipo_investor_behavior` | L2 | behavior | 分析层（17） | 行为分析 | IPO投资者构成与行为分析智能体 | generic HTTP wrapper -> `ipo_investor_behavior` |
| `agent_015.json` | `a15_entity_relation_extraction` | L2 | sentiment | 分析层（17） | 舆情分析 | 实体关系抽取智能体 | source not present / pending owner description |
| `agent_022.json` | `a22_financial_data_service` | L2 | data_support | 解析层（2） | 数据支撑 | 金融数据服务智能体 | generic HTTP wrapper -> `financial_data_service` |
| `agent_011.json` | `a11_index_technical_analysis` | L3 | valuation | 分析层（17） | 价值分析 | 股票指数估值智能体 | generic HTTP wrapper -> `valuation_index` |
| `agent_016.json` | `a16_ml_valuation` | L3 | valuation | 分析层（17） | 价值分析 | 机器学习企业估值智能体 | generic HTTP wrapper -> `valuation_ml` |
| `agent_017.json` | `a17_traditional_valuation` | L3 | valuation | 分析层（17） | 价值分析 | 传统企业估值智能体 | generic HTTP wrapper -> `valuation_traditional` |
| `agent_018.json` | `a18_meta_valuation` | L3 | valuation | 分析层（17） | 价值分析 | 元学习企业估值智能体 | generic HTTP wrapper -> `valuation_meta` |
| `agent_019.json` | `a19_risk_identification` | L3 | risk | 分析层（17） | 风险分析 | 风险识别智能体 | source not present / pending owner description |
| `agent_020.json` | `a20_compliance_review` | L3 | compliance | 分析层（17） | 风险分析 | 公告合规审查智能体 | source not present / pending owner description |
| `agent_023.json` | `a23_crash_risk` | L3 | risk | 分析层（17） | 风险分析 | 股价崩盘风险智能体 | generic HTTP wrapper -> `crash_risk` |
| `agent_024.json` | `a24_financial_fraud_risk` | L3 | risk | 分析层（17） | 风险分析 | 财务造假风险智能体 | source not present pending delivery |
| `agent_025.json` | `a25_report_center` | L4 | reporting | 报告层（1） | 报告生成 | 报告生成智能体 | special runtime role |
| `agent_026.json` | `a26_composite_valuation` | L3 | valuation | 应用层（3） | 估值研判 | 综合估值智能体 | generic HTTP wrapper -> `composite_valuation` |
| `agent_027.json` | `a27_risk_constraint` | L3 | risk | 应用层（3） | 风险控制 | 风险约束智能体 | standard route unclear pending fix |
| `agent_028.json` | `a28_composite_sentiment` | L3 | sentiment | 应用层（3） | 舆情判断 | 综合舆情智能体 | source not present / pending owner description |

## Disabled Non-Excel Functional Metadata

| File | Runtime agent id | Previous name | Rationale |
|---|---|---|---|
| `agent_005.json` | `a05_annual_report_analysis` | 公司年报分析智能体 | Not present in the latest layer sheet. Retained disabled for history; not a graph node and not in `AGENT_TOOLS`. |
| `agent_021.json` | `a21_portfolio_manager` | 投资组合经理智能体 | Not present in the latest layer sheet. Retained disabled for history; not a graph node and not in `AGENT_TOOLS`. |

## External HTTP P0 / P1-A Id Mapping

| Main system id | External service id | Default endpoint | Env override |
|---|---|---|---|
| `a03_macro_industry_research` | `macro_analysis` | `http://222.73.85.26:10014/v1/agent/invoke` | `MACRO_ANALYSIS_AGENT_URL` |
| `a04_commodity_hedging` | `price_influence_agent` | `http://222.73.85.26:10004/v1/agent/invoke` | `COMMODITY_PRICING_AGENT_URL` |
| `a06_financial_statement_analysis` | `financial_report_agent` | `http://222.73.85.26:10005/v1/agent/invoke` | `ENTERPRISE_FINANCIAL_ANALYSIS_AGENT_URL` |
| `a10_stock_technical_analysis` | `technical_stock` | `http://222.73.85.26:10009/v1/agent/invoke` | `STOCK_TECHNICAL_ANALYSIS_AGENT_URL` |
| `a11_index_technical_analysis` | `valuation_index` | `http://222.73.85.26:10003/v1/agent/invoke` | `INDEX_VALUATION_AGENT_URL` |
| `a12_research_synthesis` | `analyst_research` | `http://222.73.85.26:10006/v1/agent/invoke` | `RESEARCH_SYNTHESIS_AGENT_URL` |
| `a14_ipo_investor_behavior` | `ipo_investor_behavior` | `http://222.73.85.26:10008/v1/agent/invoke` | `IPO_INVESTOR_BEHAVIOR_AGENT_URL` |
| `a16_ml_valuation` | `valuation_ml` | `http://222.73.85.26:10001/v1/agent/invoke` | `VALUATION_ML_AGENT_URL` |
| `a17_traditional_valuation` | `valuation_traditional` | `http://222.73.85.26:10000/v1/agent/invoke` | `VALUATION_TRADITIONAL_AGENT_URL` |
| `a18_meta_valuation` | `valuation_meta` | `http://222.73.85.26:10002/v1/agent/invoke` | `VALUATION_META_AGENT_URL` |
| `a22_financial_data_service` | `financial_data_service` | `http://222.73.85.26:11000/v1/agent/invoke` | `FINANCIAL_DATA_AGENT_URL` |
| `a23_crash_risk` | `crash_risk` | `http://222.73.85.26:10012/v1/agent/invoke` | `CRASH_RISK_AGENT_URL` |
| `a26_composite_valuation` | `composite_valuation` | `http://222.73.85.26:10015/v1/agent/invoke` | `COMPOSITE_VALUATION_AGENT_URL` |

`EXTERNAL_AGENT_TIMEOUT_SECONDS` controls HTTP wrapper timeout and defaults to `90`.

The old `127.0.0.1:8101/8102/8103` valuation endpoints are now compatibility/local trial endpoints only and must be supplied through the env override variables if needed. They are not the formal default integration target.

## Pending Wrapper / Delivery Notes

- Agents present in Excel/CSV but missing under `/sdb/dlut/dev` remain enabled functional catalog entries. Their profile may be marked `NEEDS_OWNER_DESCRIPTION` when the description CSV lacks capability details.
- P1-A dev-present agents listed above now have repo-side wrapper registration. This does not prove the external services are live or healthy.
- Agents with dev source present but no repo-side wrapper still use default LLM tools. Future HTTP integration must register through `AGENT_TOOLS`.
- `a27_risk_constraint` remains held because its route standard is unclear. Source-missing agents remain pending delivery or endpoint-only policy approval.
- `/health` plus `/v1/agent/invoke` remain the expected external service boundary for later wrapper work; `/healthz` is not treated as the main standard.

## Boundaries

- Router L1-L4 JSON protocol is unchanged.
- `router_parse.py` core semantics are unchanged.
- No new graph State fields are introduced.
- Public API and frontend behavior are unchanged apart from the catalog data projected from metadata.
- `a01_cio_orchestrator` and `a25_report_center` keep their special runtime semantics.
- RP/SFT/RARP/manual_gold artifacts remain archived/offline only and are not current runtime routing authority.
