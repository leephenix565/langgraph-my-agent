# Agent Catalog v2 Sheet2 Mapping

Phase: `AC-1A`  
Business authority: `E:\muti-agent\智能体划分4.25.xlsx` Sheet2  
Repository authority after AC-1A: this mapping document plus `config/agents/*.json`

## Current Catalog Facts

- Sheet2 has 21 effective agent rows: L1=1, L2=13, L3=6, L4=1.
- Sheet2 does not contain an `agent_id` column. The stable runtime ids below are the repository mapping adopted in AC-1A.
- `configCount=21`, `runtimeCount=21`, `disabledIds=[]`.
- `a02_task_router` metadata is removed. The real Router runtime remains `router_node` inside `src/react_agent/graph.py` and is not represented as catalog metadata.
- Public transcript behavior is unchanged: one assistant persona, no raw graph messages rendered in the frontend.

## Runtime Chain

```text
config/agents/*.json
-> react_agent.agents.load_metadata_from_dir(...), sorted by filename
-> AGENT_METADATA
-> graph_bootstrap.bootstrap_agent_runtime()
-> external valuation wrapper registration for a16/a17/a18
-> default _build_agent_tool(...) fallback for remaining enabled agents
-> AGENT_TOOLS as the execution truth
-> /api/agents as public metadata projection
```

The three valuation agents are not allowed to fall back to ordinary LLM valuation tools. They are registered into `AGENT_TOOLS` before default tool backfill.

## Catalog Table

| File | Runtime agent id | Layer | Team | Sheet2 name | Execution |
|---|---:|---|---|---|---|
| `agent_001.json` | `a01_cio_orchestrator` | L1 | management | 资本市场决策协作智能体 | special runtime prompt / orchestration contract |
| `agent_003.json` | `a03_macro_industry_research` | L2 | fundamental | 宏观经济与产业链行业研究智能体 | default LLM tool |
| `agent_004.json` | `a04_commodity_hedging` | L2 | fundamental | 大宗商品价格分析与套期保值智能体 | default LLM tool |
| `agent_005.json` | `a05_annual_report_analysis` | L2 | fundamental | 公司年报分析智能体 | default LLM tool |
| `agent_006.json` | `a06_financial_statement_analysis` | L2 | fundamental | 公司财报分析智能体 | default LLM tool |
| `agent_007.json` | `a07_macro_sentiment` | L2 | sentiment | 宏观情绪感知智能体 | default LLM tool |
| `agent_008.json` | `a08_industry_hotspot` | L2 | sentiment | 行业热点洞悉智能体 | default LLM tool |
| `agent_009.json` | `a09_company_sentiment_radar` | L2 | sentiment | 企业舆情雷达智能体 | default LLM tool |
| `agent_010.json` | `a10_stock_technical_analysis` | L2 | technical | 个股技术分析智能体 | default LLM tool |
| `agent_011.json` | `a11_index_technical_analysis` | L2 | technical | 指数技术分析智能体 | default LLM tool |
| `agent_012.json` | `a12_research_synthesis` | L2 | behavior | 分析师研报与观点集成智能体 | default LLM tool |
| `agent_013.json` | `a13_fund_manager_behavior` | L2 | behavior | 基金经理投资行为分析智能体 | default LLM tool |
| `agent_014.json` | `a14_ipo_investor_behavior` | L2 | behavior | IPO投资者构成与行为分析智能体 | default LLM tool |
| `agent_015.json` | `a15_entity_relation_extraction` | L2 | behavior | 实体关系抽取智能体 | default LLM tool |
| `agent_016.json` | `a16_ml_valuation` | L3 | valuation | 机器学习估值智能体 | HTTP wrapper -> valuation_ml |
| `agent_017.json` | `a17_traditional_valuation` | L3 | valuation | 传统估值智能体 | HTTP wrapper -> valuation_traditional |
| `agent_018.json` | `a18_meta_valuation` | L3 | valuation | 元学习估值智能体 | HTTP wrapper -> valuation_meta |
| `agent_019.json` | `a19_risk_identification` | L3 | risk | 风险识别智能体 | default LLM tool |
| `agent_020.json` | `a20_compliance_review` | L3 | compliance | 合规审查智能体 | default LLM tool |
| `agent_021.json` | `a21_portfolio_manager` | L3 | investment | 投资组合经理智能体 | default LLM tool |
| `agent_025.json` | `a25_report_center` | L4 | reporting | 综合推理结构与报告生成智能体 | special runtime prompt / report center |

## External Valuation Id Mapping

| Main system id | External service id | Default endpoint | Env override |
|---|---|---|---|
| `a16_ml_valuation` | `valuation_ml` | `http://127.0.0.1:8102/v1/agent/invoke` | `VALUATION_ML_AGENT_URL` |
| `a17_traditional_valuation` | `valuation_traditional` | `http://127.0.0.1:8101/v1/agent/invoke` | `VALUATION_TRADITIONAL_AGENT_URL` |
| `a18_meta_valuation` | `valuation_meta` | `http://127.0.0.1:8103/v1/agent/invoke` | `VALUATION_META_AGENT_URL` |

`EXTERNAL_AGENT_TIMEOUT_SECONDS` controls HTTP wrapper timeout and defaults to `90`.

## Boundaries

- Router L1-L4 JSON protocol is unchanged.
- `router_parse.py` core semantics are unchanged.
- No new graph State fields are introduced.
- Public API schema is unchanged.
- `a01_cio_orchestrator` and `a25_report_center` keep their special runtime semantics.
- RP/SFT/RARP/manual_gold artifacts are not Agent Catalog v2 authority. As of AC-1B-2A, current `graph.py` no longer imports or executes the old route-prior/RARP runtime seam. The old route-prior source files remain only as archived/offline helper source.
