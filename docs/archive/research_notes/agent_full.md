# Multi-layer ReAct Router Agent Design (Current State)

Updated: 2026-01-06
Scope: current workspace state.

## 1) Overview
- Graph: 4-layer Router → Manager → Agents → Summary pipeline defined in `src/react_agent/graph.py` and compiled as `graph`.
- Entry points: `langgraph.json` → `src/react_agent/graph.py:graph`; `react_agent.graph_app` exports the compiled graph; `demo_layered_run.py` demonstrates a minimal run.
- Agent config: `config/agents` holds 26 system-level roles (L1=2, L2=15, L3=8, L4=1). `a02_task_router` is default disabled.
- Built-in analysts: optional `news/filing/data/ecc` (L2) only when `ENABLE_BUILTIN_AGENTS=1` or config directory is missing.

## 2) Agent Inventory (IDs)
**L1**
- a01_cio_orchestrator — CIO Orchestrator
- a02_task_router — Task Decomposer (default_enabled=false)

**L2**
- a03_macro_policy — 宏观与货币政策研究智能体
- a04_industry_layout — 产业链与行业格局研究智能体
- a05_product_pricing — 大宗商品价格预测智能体
- a06_financial_reports — 公司年报分析智能体4
- a07_financial_modeling — 公司财报分析智能体
- a08_tech_due_diligence — 上市材料分析智能体
- a09_macro_sentiment — 宏观舆情感知智能体6
- a10_industry_sentiment — 中观行业舆情感知智能体7
- a11_equity_sentiment — 微观个股舆情感知智能体8
- a12_ipo_investor_behavior — IPO投资者构成与行为分析智能体
- a13_index_technical_analysis — 指数技术分析智能体5
- a14_single_stock_tech — 个股技术分析智能体
- a15_research_synthesis — 分析师研报与观点集成智能体2
- a16_fund_manager_behavior — 基金经理投资行为分析智能体
- a17_client_profile — 客户画像（风险偏好）智能体

**L3**
- a18_primary_secondary_valuation — 企业通用估值智能体1
- a19_market_risk — 股价相关风险智能体
- a20_fundamental_risk — 财务困境风险智能体
- a21_reg_compliance — 监管合规与投资者保护规则审查智能体
- a22_suitability_review — 投资者适当性与风险承受匹配审查智能体
- a23_portfolio_opt — 投资组合优化智能体
- a26_sci_tech_valuation — 科创企业估值智能体3
- a27_portfolio_backtest — 投资组合历史回测智能体

**L4**
- a25_report_center — Report & Decision Center

## 3) Graph Flow & State
1. **Input**: `messages` is the only external input; latest Human message is used as the question.
2. **Router (`router_node`)**: builds `agent_catalog`, asks `ROUTER_SYSTEM_PROMPT` for JSON; parses via `_parse_router_layers`. Fallback plan uses `_default_layer_plan` (L1:1, L2:≤5, L3:≤3, L4:1) and `DEFAULT_MODES` (L1/L4=Chain, L2/L3=Star). Initializes `current_layer="L1"`, `chain_cursor=0`, `analyst_results={"__reset__": True}`.
3. **Manager dispatch (`manager_broadcast`)**:
   - Chain: dispatch next `agent_id` and set `fanout_targets=[next_id]` + `chain_cursor`.
   - Star/Debate/Tree: dispatch remaining agents in parallel (Debate/Tree are treated as Star for dispatch).
   - Empty layer → `manager_summary` directly.
4. **Agent nodes (`_build_agent_node`)**: build `agent_input` with `tools_config` (`allow_search` false only for a01/a25; otherwise true) and invoke `AGENT_TOOLS[agent_id]`.
5. **Summary (`manager_summary`)**: if Chain has pending agents, return `chain_cursor` to continue; else mark layer done and advance. Final layer uses `Context.system_prompt` + `MANAGER_SUMMARY_USER`, filters `parse_ok=false`, and prepends a meta note when filtered.
6. **Conditional routing (`route_from_manager_summary`)**: pending+Chain → `manager_broadcast`; pending+Star/Debate/Tree → `manager_broadcast` then `noop`; final layer → `__end__`.
7. **Noop**: `noop()` returns empty update while waiting for parallel results.

**State fields** (`src/react_agent/state.py`): `messages`, `plan`, `analyst_results`, `run_id`, `current_question`, `fanout_targets`, `layer_plan`, `layer_mode`, `current_layer`, `layer_done`, `chain_cursor`, `is_last_step`.

**Context fields** (`src/react_agent/context.py`): `model` (env `MODEL`), `system_prompt` (env `SYSTEM_PROMPT`), `run_id` (env `RUN_ID`), `analyst_profiles`, `max_search_results` (default 10; wired into `tavily_search` via `default_agents.py` when `allow_search=true`, selecting `build_tavily_search(max_search_results)`).

## 4) Tools & Prompts
- Tool: `tavily_search` in `src/react_agent/tools.py` (`max_results=5`, `search_depth="basic"`, uses `TAVILY_API_KEY`).
- `tools_config.allow_search` default true for config agents; forced false for a01/a25.
- `_build_agent_tool` retries once if JSON parse fails; `_parse_agent_output` marks `parse_ok=false` on fallback.

## 5) Logging & Tests
- Local trace: `LOCAL_TRACE=1` writes JSONL to `log/<YYYYMMDD>/<run_id>.jsonl`; `TRACE_MAX_CHARS` and `LOG_DIR` are supported.
- Tests: `tests/unit_tests` + `tests/integration_tests/test_graph.py` cover router parsing, prompt formatting, fail-soft behavior, and graph wiring.
