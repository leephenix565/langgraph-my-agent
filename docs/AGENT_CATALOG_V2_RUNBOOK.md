# Agent Catalog v2 Runbook

Phase: `EXCEL-CATALOG-ALIGN-1` + `EXTERNAL-HTTP-P0` + `EXTERNAL-HTTP-P1A` + `LATEST-LAYER-SHEET`
Business taxonomy authority: `/sdb/dlut/agent_layer_latest.xlsx`. Endpoint/profile lineage: `/sdb/dlut/智能体分工及访问接口.csv`, `/sdb/dlut/智能体的描述.csv`, and `docs/AGENT_CATALOG_V2_SHEET2_MAPPING.md`.

## Current Functional-Agent Authority

- `/sdb/dlut/agent_layer_latest.xlsx` is now the profile authority for formal business-layer, business-category, and business-order metadata on listed agents.
- Runtime `layer` is now the business layer code: `L1=解析层`, `L2=分析层`, `L3=应用层`, and `L4=报告层`.
- Agent id prefixes are stable runtime keys and no longer imply display or business order. Use `business_order` for the formal 24-agent business sequence.
- Router runtime, `a01_cio_orchestrator`, and `a25_report_center` are special system runtime roles and must not be replaced by external functional profiles.
- The enabled catalog now has 23 functional agents plus 2 special runtime roles: `runtimeCount=25`.
- `config/agents` keeps 27 metadata files because `a05_annual_report_analysis` and `a21_portfolio_manager` are retained disabled as non-Excel historical functional metadata.
- `config/agents/*.json` carries `business_order`, `business_role`, `business_status`, `business_layer`, `business_category`, and `business_subcategory` fields for the business taxonomy.
- `a03_macro_industry_research` remains enabled and callable because the a03 macro external wrapper is already live-verified. It is not listed in `/sdb/dlut/agent_layer_latest.xlsx`, so it is tagged `business_status=legacy_retained`, has no `business_order`, and is excluded from the formal 24-agent sequence.
- Disabled retained metadata may appear in catalog metadata, but disabled ids are not graph nodes, not `AGENT_TOOLS` tools, and not callable.
- Catalog/profile alignment remains separate from runtime wrapper integration.
- External HTTP P0 migrates `a16_ml_valuation`, `a17_traditional_valuation`, and `a18_meta_valuation` from early local trial defaults to generic table-driven HTTP wrappers using the Excel/CSV production invoke endpoints as formal defaults.
- Existing env var overrides remain compatible: `VALUATION_ML_AGENT_URL`, `VALUATION_TRADITIONAL_AGENT_URL`, and `VALUATION_META_AGENT_URL`.
- External HTTP P1-A registers 10 additional dev-present functional agents on the generic wrapper path: `a22_financial_data_service`, `a03_macro_industry_research`, `a04_commodity_hedging`, `a06_financial_statement_analysis`, `a10_stock_technical_analysis`, `a11_index_technical_analysis`, `a12_research_synthesis`, `a14_ipo_investor_behavior`, `a23_crash_risk`, and `a26_composite_valuation`.
- P0 + P1-A total 13 generic external HTTP wrapper configs. Wrapper registration is not live service verification.
- Enabled non-wrapper functional agents use a main-system
  `INTERNAL_LLM_SEARCH_PLACEHOLDER` path until a dedicated external service is
  delivered: `a07_macro_sentiment`, `a08_industry_hotspot`,
  `a09_company_sentiment_radar`, `a13_fund_manager_behavior`,
  `a15_entity_relation_extraction`, `a19_risk_identification`,
  `a20_compliance_review`, `a24_financial_fraud_risk`,
  `a27_risk_constraint`, and `a28_composite_sentiment`.
- Placeholder tools are not dedicated external-agent verification. They are
  generic LLM tools that use the agent profile, optional Tavily search, and
  structured fail-soft output. When search is disabled or unavailable, evidence
  records `source_type=llm_search_placeholder` with the limitation.
- Tavily is optional transitional fallback only. Missing `TAVILY_API_KEY` does
  not block public runtime by default; use `SEARCH_REQUIRED=true` only for
  explicit search-required validation. `DISABLE_SEARCH=1|true|yes|on` is the
  supported LLM-only placeholder mode.
- Target architecture: business agents should ultimately be owner-provided
  external HTTP agent services. The main system should not depend on Tavily to
  fill permanent agent capability gaps.
- DeepSeek is currently documented in this repo as an LLM provider path only;
  do not claim default DeepSeek API web search unless a supported request
  contract is implemented and verified.
- Source-missing agents remain pending delivery or an explicitly approved
  endpoint-only policy even though they have a callable placeholder path.

## What AC-1A Changes

- Rebuilds `config/agents` around the current Excel/CSV functional-agent authority.
- Removes `a02_task_router` metadata without changing the real `router_node` runtime.
- Registers P0 + P1-A ids as generic external HTTP wrappers in `AGENT_TOOLS` before default LLM tool backfill.
- Backfills enabled non-wrapper functional ids with generic
  LLM/search-placeholder tools after wrapper registration.
- Keeps Router/a01/a25 protocol and public adapter schema unchanged.
- Keeps route-prior/RARP/SFT source in place as archived/offline helpers; those artifacts are no longer catalog-v2 mainline acceptance evidence.
- AC-1B-1 moves offline RP/RARP/SFT/manual-gold/teacher-proxy tests and markers into an archived/non-mainline posture.
- AC-1B-2A removes the old route-prior runtime shadow seam from `react_agent.graph`; the graph no longer imports or executes old route-prior logic.

## AC-1B Offline Evidence Archive Boundary

AC-1B-1 removes old offline RP/RARP/SFT/manual-gold/teacher-proxy evidence from
current mainline acceptance. AC-1B-2A removes the old route-prior runtime seam
from the graph while keeping old helper source and offline assets for archived
lineage only.

- `src/react_agent/route_prior.py`, `route_reliability.py`,
  `route_profile_registry.py`, and `route_prior_embeddings.py` remain in place
  as archived/offline helpers. `react_agent.graph` no longer imports them.
- Formal Router provider output plus `router_parse` L1-L4 parsing are the only
  current routing owners.
- Offline artifacts under `ops/regression/route_prior/`, `data/router_sft/`,
  `data/sft/`, and `data/a01_sft/` are historical lineage only.
- Archived offline tests live under `tests/archive/` and are not collected by
  the default `pytest tests/unit_tests` gate.
- The active unit gate keeps a focused no-route-prior runtime contract test
  proving graph import/router execution remain free of legacy route-prior state
  and public fields.

## Local Validation

Use the documented Python environment for this repo. In this workstation the passing focused command was:

```powershell
D:\AnacondaEnvs\cline_env\python.exe -m pytest tests\unit_tests -q -p no:cacheprovider --basetemp E:\muti-agent\langgraph-my-agent\tmp\pytest-ac1a-unit-3
```

Focused checks for this phase:

```powershell
D:\AnacondaEnvs\cline_env\python.exe -m pytest tests\unit_tests\test_agent_catalog_v2.py tests\unit_tests\test_external_valuation_agents.py tests\unit_tests\test_config_agents_tools.py tests\unit_tests\test_disabled_agents_nodes.py tests\integration_tests\test_public_api.py -q -p no:cacheprovider --basetemp E:\muti-agent\langgraph-my-agent\tmp\pytest-ac1a-focused
npm --prefix apps/web run test
```

`pytest` in this Windows/Codex setup may require an explicit `--basetemp` and normal Windows permissions. Bundled Python is not sufficient here because its user-site pytest dependency surface is incomplete.

## External HTTP P0 / P1-A Services

Default endpoints now come from the Excel/CSV production main-system invoke URLs:

```powershell
# Env vars remain override-compatible. These examples show the formal defaults,
# not required local shell configuration.
$env:FINANCIAL_DATA_AGENT_URL = "http://222.73.85.26:11000/v1/agent/invoke"
$env:MACRO_ANALYSIS_AGENT_URL = "http://222.73.85.26:10014/v1/agent/invoke"
$env:COMMODITY_PRICING_AGENT_URL = "http://222.73.85.26:10004/v1/agent/invoke"
$env:ENTERPRISE_FINANCIAL_ANALYSIS_AGENT_URL = "http://222.73.85.26:10005/v1/agent/invoke"
$env:STOCK_TECHNICAL_ANALYSIS_AGENT_URL = "http://222.73.85.26:10009/v1/agent/invoke"
$env:INDEX_VALUATION_AGENT_URL = "http://222.73.85.26:10003/v1/agent/invoke"
$env:RESEARCH_SYNTHESIS_AGENT_URL = "http://222.73.85.26:10006/v1/agent/invoke"
$env:IPO_INVESTOR_BEHAVIOR_AGENT_URL = "http://222.73.85.26:10008/v1/agent/invoke"
$env:VALUATION_TRADITIONAL_AGENT_URL = "http://222.73.85.26:10000/v1/agent/invoke"
$env:VALUATION_ML_AGENT_URL = "http://222.73.85.26:10001/v1/agent/invoke"
$env:VALUATION_META_AGENT_URL = "http://222.73.85.26:10002/v1/agent/invoke"
$env:CRASH_RISK_AGENT_URL = "http://222.73.85.26:10012/v1/agent/invoke"
$env:COMPOSITE_VALUATION_AGENT_URL = "http://222.73.85.26:10015/v1/agent/invoke"
$env:EXTERNAL_AGENT_TIMEOUT_SECONDS = "90"
```

The old local trial defaults are no longer formal defaults:

```powershell
http://127.0.0.1:8101/v1/agent/invoke
http://127.0.0.1:8102/v1/agent/invoke
http://127.0.0.1:8103/v1/agent/invoke
```

Local trial endpoints can still be used through env overrides when explicitly needed. The default test suite uses fake HTTP clients and does not require real services on ports `8101`, `8102`, or `8103`, nor does it call the production endpoints.

Before claiming live E2E, verify each service health endpoint and then run an end-to-end graph invocation that selects the corresponding functional agent. P0/P1-A mock tests prove wrapper construction, request mapping, response mapping, endpoint default selection, env override compatibility, bootstrap registration, and fail-soft behavior; they do not prove live service availability or data freshness.

P1-A deliberately does not register `a27_risk_constraint` because the route standard is unclear. Source-missing agents remain pending delivery or a separately approved endpoint-only policy. Profile/catalog alignment remains separate from runtime wrapper integration, and runtime wrapper registration remains separate from live service verification.

## AC-1A-L2 Live Wrapper Smoke Evidence

Phase `AC-1A-L2` validated the three external valuation services through the
main-system `AGENT_TOOLS` wrappers. This is wrapper-level live evidence only:
it is not a graph-level provider-backed E2E claim, not a Router-selection
claim, and not investment advice.

Service startup evidence:

| Service | Directory | Startup runtime | Port | Result |
| --- | --- | --- | --- | --- |
| Traditional valuation | `E:\muti-agent\传统估值智能体` | `D:\anaconda3\python.exe` | `8101` | started |
| Machine-learning valuation | `E:\muti-agent\机器学习估值智能体` | `D:\anaconda3\python.exe` | `8102` | started |
| Meta valuation | `E:\muti-agent\元学习估值智能体` | `D:\anaconda3\python.exe` | `8103` | started |

Initial startup with `D:\AnacondaEnvs\cline_env\python.exe` failed because that
environment lacked service-side dependencies (`tushare`, `scipy`, and
`sklearn`). Reproduce the live service run with `D:\anaconda3\python.exe` or a
dedicated service environment with the service `requirements.txt` installed.

Health evidence:

| Port | Reachable | Status | External agent id | Agent name |
| --- | --- | --- | --- | --- |
| `8101` | yes | `ok` | `valuation_traditional` | 传统估值智能体 |
| `8102` | yes | `ok` | `valuation_ml` | 机器学习估值智能体 |
| `8103` | yes | `ok` | `valuation_meta` | 元学习估值智能体 |

TCP listeners were present on `127.0.0.1:8101`, `127.0.0.1:8102`, and
`127.0.0.1:8103`. `curl` health checks returned `status=ok` for all three
services. `httpx` health checks with both `trust_env=True` and
`trust_env=False` returned `200/ok`; no proxy bypass risk was reproduced in
this run. Proxy env variables were absent, and `NO_PROXY` / `no_proxy` did not
explicitly include `localhost` or `127.0.0.1`.

Wrapper registration evidence:

| Main-system id | External id | In `AGENT_TOOLS` | Wrapper flag | Stub flag |
| --- | --- | --- | --- | --- |
| `a16_ml_valuation` | `valuation_ml` | yes | `is_external_valuation_wrapper=true` | `is_stub=false` |
| `a17_traditional_valuation` | `valuation_traditional` | yes | `is_external_valuation_wrapper=true` | `is_stub=false` |
| `a18_meta_valuation` | `valuation_meta` | yes | `is_external_valuation_wrapper=true` | `is_stub=false` |

The validation path used the main-system wrappers and `POST /v1/agent/invoke`;
`POST /v1/valuation/invoke` was not used as the main acceptance path.

Live wrapper call evidence:

| Main-system id | Question | Result | Evidence summary |
| --- | --- | --- | --- |
| `a16_ml_valuation` | `帮我用机器学习估值看看浦发银行到 2026 年底有没有上涨空间` | `parse_ok=true`, `confidence=0.6`, `fail_soft=false` | returned external `valuation_result` / `valuation_results`; `valuation_mode=machine_learning`; `model_name=xgboost_pe_monte_carlo`; `ticker=600000.SH`; `company_name=浦发银行` |
| `a17_traditional_valuation` | `帮我用传统估值看看中国能建现在是不是低估` | `parse_ok=true`, `confidence=0.6`, `fail_soft=false` | returned external `valuation_result` / `valuation_results`; `valuation_mode=traditional`; `model_name=PE（市盈率法）`; `ticker=601868.SH`; `company_name=中国能建`; `valuation_view=overvalued` |
| `a18_meta_valuation` | `帮我用元学习估值分析中国能建的同行支撑集` | `parse_ok=true`, `confidence=0.6`, `fail_soft=false` | returned external `valuation_result` / `valuation_results`; `valuation_mode=meta_learning`; `ticker=601868.SH`; `company_name=中国能建`; peer support-set evidence; warning: `LLM answer failed; returned template answer` |

Answer previews captured for validation:

- Machine-learning valuation: external answer reported `600000.SH`, target
  date `2026-12-31`, current price `9.03`, predicted fair PE `7.57`, predicted
  price center `11.49`, expected upside `+27.21%`, interval `[9.50 - 13.44]`,
  and model view `undervalued`.
- Traditional valuation: external answer reported `601868.SH`, PE-based fair
  value center about `1136.62` billion, fair range about `966.13` to `1307.11`
  billion, current market value about `1561.68` billion, and model view
  `overvalued`.
- Meta valuation: external answer reported `601868.SH`, model type `传统价值型模型`,
  suggested enterprise value `901.36` billion, reference multiples
  `PE 9.77 / PS 0.17`, and a top support set including 中国铁建、中国中铁、中国核建、
  中国交建、中国建筑.

These answer previews are acceptance artifacts only. They record that the
wrappers received live external service outputs; they are not investment
recommendations and do not establish data freshness.

Graph-level smoke was skipped because the shell did not have provider/search
prerequisites such as `OPENAI_API_KEY`, `ROUTER_OPENAI_API_KEY`,
`BASELINE_OPENAI_API_KEY`, `GOOGLE_API_KEY`, or optional Tavily credentials for
search-required runs. Missing `TAVILY_API_KEY` alone does not block public
runtime unless `SEARCH_REQUIRED=true`. This does not block the wrapper-level
live smoke.

Remaining risks after AC-1A-L2:

- Data freshness still needs a separate refresh and timestamp policy.
- Service startup depends on an external service runtime; `cline_env` was not
  sufficient for the three services.
- Proxy bypass risk was not reproduced, but localhost is not explicitly listed
  in `NO_PROXY` / `no_proxy`.
- Meta valuation returned a template answer because its LLM answer step failed;
  the wrapper still returned `parse_ok=true` with valuation evidence.
- Route-prior/RARP/SFT source deletion or future `router_prior_v2` design remains separate future work. This does not change the current AC-1B-2A runtime fact: `react_agent.graph` no longer imports or executes the old route-prior/RARP seam, and the helper source is archived/offline only.

## DS-1-V DeepSeek V4 Valuation Services Validation Evidence

Phase DS-1 scoped the commercial API line to the Fair Fusion baseline sidecar
and the three valuation services' internal parser/answerer LLM paths. It did
not migrate the main multi-agent global provider path
(`MODEL` / `OPENAI_BASE_URL` / `OPENAI_API_KEY`), did not enable Fair Fusion
source switching, and did not change Agent Catalog v2, Router, State, public
API, frontend, or the external valuation wrapper implementation.

Baseline sidecar recommended DeepSeek configuration:

```env
BASELINE_MODEL=openai/deepseek-v4-pro
BASELINE_OPENAI_BASE_URL=https://api.deepseek.com
BASELINE_OPENAI_API_KEY=
ENABLE_FAIR_FUSION=0
ENABLE_FAIR_FUSION_SOURCE_SWITCH=0
```

This is a baseline sidecar / Fair Fusion commercial API line configuration.
It does not affect the visible mainline answer unless Fair Fusion is enabled,
and the source-switch default remains off.

DeepSeek V4 probe evidence from DS-1:

- `GET /models` against the DeepSeek OpenAI-compatible endpoint returned `200`.
- A minimal chat completion using `deepseek-v4-pro` and prompt
  `Return exactly: OK` returned `OK`.
- `reasoning_content` existed in the provider response shape but was not
  printed, stored in docs, or exposed through the public transcript.

DS-1-M2 meta valuation parser/resolver hardening evidence:

- Scope was limited to `E:\muti-agent\元学习估值智能体`.
- `langgraph-my-agent`, the main-system wrapper, and real `.env` files were not
  changed.
- The resolver now handles a single embedded ticker or a single embedded full
  company name when the security can be uniquely identified.
- Verified normalization cases:
  - `601868.SH` resolved.
  - Chinese Energy Engineering's company name resolved.
  - `601868.SH` plus the company name resolved through embedded ticker
    normalization.
  - Task words plus the company name resolved through embedded name
    normalization.
- Multiple tickers or multiple company names still keep clarification behavior
  instead of guessing.
- `tests/test_resolver_normalization.py` passed with `9 passed`; `compileall`
  and focused `codespell` also passed.
- `/v1/agent/invoke` and `/v1/valuation/invoke` checks returned `status=ok`
  with `valuation_result` present for the focused meta valuation cases.

DS-1-V real-env validation used:

| Item | Value |
| --- | --- |
| Audit working directory | `E:\muti-agent` |
| Audit Python | `D:\AnacondaEnvs\cline_env\python.exe` (`Python 3.11.14`) |
| Service startup Python | `D:\anaconda3\python.exe` (`Python 3.12.7`) |
| Real service `.env` files | Not modified by Codex |
| Local proxy handling | `NO_PROXY` / `no_proxy` set in process for `127.0.0.1,localhost`; not persisted to service `.env` |

Real service environment safe summary:

| Service | LLM base host | Runtime model | API key | Tushare token | Backend | Proxy env |
| --- | --- | --- | --- | --- | --- | --- |
| Traditional valuation | `api.deepseek.com` | `deepseek-v4-flash` | present | present | `direct` | HTTP/HTTPS/ALL absent |
| Machine-learning valuation | `api.deepseek.com` | `deepseek-v4-flash` | present | present | `direct` | HTTP/HTTPS/ALL absent |
| Meta valuation | `api.deepseek.com` | `deepseek-v4-flash` | present | present | `direct` | HTTP/HTTPS/ALL absent |

`deepseek-v4-flash` is the DS-1 documented DeepSeek V4 cost/speed alternative
to `deepseek-v4-pro`.

Service startup and health evidence:

| Port | Service | PID | Health status | Agent id | LLM configured | Data backend | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `8101` | Traditional valuation | `22092` | `ok` | `valuation_traditional` | `true` | `direct` | none |
| `8102` | Machine-learning valuation | `18980` | `ok` | `valuation_ml` | `true` | `direct` | none |
| `8103` | Meta valuation | `24804` | `ok` | `valuation_meta` | `true` | `direct` | none |

Service-level `POST /v1/agent/invoke` evidence:

| Service | HTTP / status | Parser summary | Structured valuation evidence | Answer |
| --- | --- | --- | --- | --- |
| Traditional valuation | `HTTP 200`, `status=ok` | LLM parser selected Chinese Energy Engineering | `valuation_result` present, `valuation_results_count=1` | non-empty; PE valuation view reported the current market value above the fair range and explicitly did not present investment advice |
| Machine-learning valuation | `HTTP 200`, `status=ok` | LLM parser selected Shanghai Pudong Development Bank with target date `20261231` | `valuation_result` present, `valuation_results_count=1` | non-empty; XGBoost plus Monte Carlo output included target price center, confidence interval, and expected upside |
| Meta valuation | `HTTP 200`, `status=ok` | LLM parser emitted `601868.SH` plus company name; DS-1-M2 normalization resolved the security | `valuation_result` present, `valuation_results_count=1` | non-empty; peer support-set valuation output included model type, enterprise value, PE/PS, and peer-sample explanation |

Meta valuation domain endpoint sanity:

- `POST /v1/valuation/invoke` with explicit `601868.SH` returned `HTTP 200`
  and `status=ok`.
- `valuation_result` was present, `valuation_results_count=1`, answer was
  non-empty, and warnings/errors were absent.
- This was a domain sanity check only; the main wrapper acceptance path remained
  `POST /v1/agent/invoke`.

Main-system wrapper smoke evidence:

| Main-system id | External id | Registered | Wrapper flag | Stub flag | Result |
| --- | --- | --- | --- | --- | --- |
| `a16_ml_valuation` | `valuation_ml` | yes | `is_external_valuation_wrapper=true` | `is_stub=false` | `parse_ok=true`, `confidence=0.6`, `evidence_count=2`, `fail_soft=false` |
| `a17_traditional_valuation` | `valuation_traditional` | yes | `is_external_valuation_wrapper=true` | `is_stub=false` | `parse_ok=true`, `confidence=0.6`, `evidence_count=2`, `fail_soft=false` |
| `a18_meta_valuation` | `valuation_meta` | yes | `is_external_valuation_wrapper=true` | `is_stub=false` | `parse_ok=true`, `confidence=0.6`, `evidence_count=2`, `fail_soft=false` |

The three main-system wrapper calls used `AGENT_TOOLS` and returned evidence
summaries derived from external `valuation_result` / `tool_result` outputs.
They were not default LLM tools and were not generic stubs. `POST
/v1/valuation/invoke` was not used as the main wrapper acceptance path.

DS-1-V final verdict:

- `DS-1-V passed` for the three DeepSeek V4 valuation services plus the
  main-system wrapper smoke.
- Graph-level provider-backed smoke was skipped in DS-1-V because the DS-1-V
  acceptance target was service-level validation plus wrapper-level live smoke;
  graph-level smoke would introduce separate provider-call variables.
- This record does not claim graph-level smoke passed, Web/public adapter was
  revalidated, or Fair Fusion visible answers switched to DeepSeek.

Remaining risks after DS-1-V:

- Real service `.env` files used `deepseek-v4-flash`, not `deepseek-v4-pro`;
  this is the documented DeepSeek V4 cost/speed option.
- Service runtime depended on `D:\anaconda3\python.exe`; `cline_env` did not
  contain all service-side dependencies.
- `NO_PROXY` / `no_proxy` was not persisted in the service `.env` files.
- Graph-level smoke was skipped for this phase.
- Data freshness remains a separate validation topic.

## DS-1-B DeepSeek Baseline Sidecar Shadow Smoke Evidence

Phase DS-1-B validated that the Fair Fusion baseline sidecar can call the
DeepSeek V4 baseline provider at runtime while source switch remains off and
the visible answer stays on the mainline path. This was a shadow-path smoke
only; it did not validate source switching and did not replace the mainline
answer.

Validation environment:

| Item | Value |
| --- | --- |
| Working directory | `E:\muti-agent\langgraph-my-agent` |
| Python | `D:\AnacondaEnvs\cline_env\python.exe` (`Python 3.11.14`) |
| Global model | `openai/qwen-3-235b-a22b-instruct-2507` |
| Global base URL host | `api.cerebras.ai` |
| Global API key | present |
| Baseline model | `openai/deepseek-v4-pro` |
| Baseline base URL host | `api.deepseek.com` |
| Baseline API key | present |
| `ENABLE_FAIR_FUSION` | `1` |
| `ENABLE_FAIR_FUSION_SOURCE_SWITCH` | `0` |
| Proxy env | `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` absent |
| Localhost bypass | `NO_PROXY` / `no_proxy` contained `127.0.0.1,localhost` |
| Search | `DISABLE_SEARCH=1` |
| Trace | `LOCAL_TRACE=1`; `LOG_DIR=E:\muti-agent\langgraph-my-agent\tmp\ds1b_baseline_trace` |

The main multi-agent global provider was not changed to DeepSeek. The
DeepSeek configuration was used only through the baseline sidecar
`BASELINE_*` path.

Baseline DeepSeek provider probe:

- Probe used the repository `load_chat_model` path.
- Model: `openai/deepseek-v4-pro`.
- Base URL host: `api.deepseek.com`.
- Prompt: `Return exactly: OK`.
- Result preview: `OK`.
- DeepSeek `reasoning_content` was not printed or stored.

Valuation service health before graph smoke:

| Port | Reachable | Status | Agent id | Warnings |
| --- | --- | --- | --- | --- |
| `8101` | true | `ok` | `valuation_traditional` | none |
| `8102` | true | `ok` | `valuation_ml` | none |
| `8103` | true | `ok` | `valuation_meta` | none |

Graph baseline shadow smoke:

| Field | Evidence |
| --- | --- |
| Question class | Traditional valuation question for China Energy Engineering |
| Graph invoke | success |
| Run id | `ds1b_baseline_shadow_1778837621` |
| Trace file | `E:\muti-agent\langgraph-my-agent\tmp\ds1b_baseline_trace\ds1b_baseline_shadow_1778837621.jsonl` |
| Router parse | `router_parse_ok=true`, `router_used_default_plan=false` |
| Selected L3 agent | `a17_traditional_valuation` |
| Target output | `parse_ok=true`, `confidence=0.6`, `evidence_count=2`, `fail_soft=false` |
| Baseline status | `baseline_status=ready` |
| Baseline bundle | `baseline_bundle` present |
| Baseline error | false |
| Judge / writer | `judge_status=ready`, `writer_status=ready` |
| Final source | `final_answer_source=mainline` |
| Source switch | disabled; `ENABLE_FAIR_FUSION_SOURCE_SWITCH=0` |
| Visible answer | stayed mainline |
| Summary/provider errors | none in trace |

Baseline answer preview was a separate traditional-valuation style answer that
noted it could not verify real-time data directly and suggested comparing
current valuation against industry and historical levels. This baseline answer
was not emitted as the visible final answer.

The emitted final answer remained a natural-language mainline report based on
the traditional PE valuation result, concluding that China Energy Engineering
was not undervalued and was above the estimated fair range.

DS-1-B final verdict:

- `DS-1-B passed` for the DeepSeek baseline sidecar shadow path.
- The run proves baseline sidecar runtime connectivity and `baseline_bundle`
  production under Fair Fusion shadow mode.
- It does not prove source switch behavior, visible-answer replacement,
  Web/public adapter behavior, or any frontend path.

Remaining risks after DS-1-B:

- Source switch was not validated.
- The visible answer intentionally stayed on the mainline path.
- Web/public adapter was not revalidated in this phase.
- Provider capacity and rate limits remain external runtime risks.

## Expected Catalog Output

`GET /api/agents` should expose:

```json
{"configCount":27,"runtimeCount":25,"disabledIds":["a05_annual_report_analysis","a21_portfolio_manager"]}
```

Layer counts should be:

```json
{"enabledRuntimeRoles":{"L1":1,"L2":12,"L3":11,"L4":1},"publicCatalogRowsIncludingDisabled":{"L1":1,"L2":13,"L3":12,"L4":1}}
```

## Fail-Soft Behavior

The generic HTTP wrappers return `AgentOutput` with `parse_ok=false` and `confidence=0` for timeout, network error, non-2xx status, invalid JSON, missing `status`, invalid schema, or unexpected exception. The failure output intentionally avoids traceback, API key, token, and raw provider response leakage.

## Rollback Notes

Rollback for P0 requires restoring the previous valuation-wrapper registration path and default endpoints. Route-prior helpers remain archived/offline only after AC-1B-2A; future `router_prior_v2` work must be rebuilt from stable Agent Catalog v2 metadata, new profile cards, and new manual labels before any graph runtime integration.
