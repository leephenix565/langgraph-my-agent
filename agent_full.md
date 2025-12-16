# Multi-layer ReAct Router Agent Design (Current State)

Updated: 2025-12-11 14:52:58 +08:00  
Scope: current workspace (all recent fixes included)

## 1) Overview
- Purpose: 4-layer (L1/L2/L4/L5) Router → Manager → Agents → Summary graph, ReAct-style iteration, ready for LangGraph Studio.
- Core file: `src/react_agent/graph.py` defines the graph; `config/agents` holds 25 system-level roles; optional built-in 4 analysts (news/filing/data/ecc) via `ENABLE_BUILTIN_AGENTS=1`.
- Defaults: model `deepseek/deepseek-chat`; shared tool `tavily_search` (basic, max_results=5). Config agents now use LLM tools by default (not stubs), with search enabled; stub only if description is empty.

## 2) Flow & State
1. **Input**: external `messages` only (latest Human as current question).
2. **Router** (`router_node`): prompt enforces pure JSON `layers:[{layer,mode,selected}]`; compatible with legacy `{"selected":[...]}` (fills L2/Star). On parse failure, fallback to default plan (L1/L5=Chain, L2/L4=Star; selects L1:1, L2:5, L4:3, L5:1). Initializes `current_layer="L1"`, `chain_cursor=0`, `analyst_results={"__reset__": True}`.
3. **Manager dispatch** (`manager_broadcast`):  
   - Chain: send next agent in order.  
   - Star/Debate/Tree: parallel fan-out (Debate/Tree treated as Star for dispatch).  
   - Empty layer skips to summary. Assignment text from `MANAGER_ASSIGNMENT_USER`.
4. **Agent nodes** (`_build_agent_node`): build `AgentInput` and call `AGENT_TOOLS[agent_id]`.  
   - Config agents (25 roles) → LLM tool `_build_agent_tool` with default_allow_search=True.  
   - Built-in analysts (optional) → LLM tool with prompts + tool loop; stub used only if metadata description is missing.  
   - Outputs merged into `analyst_results[agent_id]` (with `parse_ok` flag), AIMessage appended.
5. **Manager summary** (`manager_summary`):  
   - If pending and mode=Chain, update `chain_cursor` and wait.  
   - Else mark `layer_done`, advance `current_layer`, reset `fanout_targets`.  
   - Final (L5) uses `Context.system_prompt` + `MANAGER_SUMMARY_USER`; filters out `parse_ok=False` entries and prepends meta note: `[meta] 本轮有 N 条输出因解析失败未参与汇总。`
6. **Conditional routing** (`route_from_manager_summary`):  
   - Pending + Chain → `manager_broadcast`.  
   - Pending + Star/Debate/Tree → first time (fanout_targets empty) `manager_broadcast`, else `noop`.  
   - No pending & not L5 → `manager_broadcast`; L5 → `__end__`.
7. **Graph edges**: `__start__` → router → manager_broadcast → agent_* → manager_summary → conditional (manager_broadcast/noop/__end__).

### State (src/react_agent/state.py)
- `messages` (add_messages merge), `plan`, `analyst_results` (supports `{"__reset__": True}`), `current_question`, `fanout_targets`, `layer_plan`, `layer_mode`, `current_layer`, `layer_done`, `chain_cursor`, `is_last_step`.

### Context (src/react_agent/context.py)
- `model`, `system_prompt`, `analyst_profiles`, `max_search_results`; env overrides by upper-case field name. Default `system_prompt` is Manager prompt.

## 3) Agent Assets
- **Config agents** (`config/agents/agent_*.json`): 25 roles, enabled by default, bound to LLM tool unless `description` empty (then stub). Distribution:  
  - L1×1: a01_cio_orchestrator  （a02_task_router 默认关闭，避免双路由角色；保留作对照/实验）  
  - L2×15: a03_macro_policy … a17_client_profile  
  - L4×7: a18_primary_secondary_valuation … a24_shared_services  
  - L5×1: a25_report_center
- **Built-in analysts (optional)**: news/filing/data/ecc (L2), enabled via `ENABLE_BUILTIN_AGENTS=1` or missing config directory; support search.
- **Registration order**: register built-ins (if enabled) → load config metadata → for each without tool: use `_build_agent_tool(desc, default_allow_search=True)` if description present; else fallback stub `build_generic_agent_tool` (marked `is_stub=True`).

## 4) Prompts, Tools, Parse/Retry
- Prompts in `src/react_agent/prompts.py`:  
  - Router: strict JSON, escaped braces, agent_catalog injected.  
  - Manager: dispatch + final summary.  
  - Analyst: strict JSON-only schema (analysis/key_points/evidence/confidence), braces escaped to avoid `.format` KeyError.
- Tools: `tavily_search` (tools.py), enabled by default for config LLM agents (via default_allow_search=True) unless tools_config overrides.
- Parse & retry (`default_agents.py`):  
  - `_parse_agent_output` sets `[PARSE_FALLBACK]` and `parse_ok=False` on failure.  
  - `_build_agent_tool` retries once with strict JSON-only prompt if first parse fails; `parse_ok=True` on success.

## 5) Testing & Demo
- Demo: `python demo_layered_run.py` (requires LLM/Tavily keys) shows layer_plan/layer_mode/analyst_results/final message.
- Unit tests: mode normalize, router parse compatibility, prompt format safety, parse fallback flag, JSON retry, summary filter, config agents tools. Integration: `tests/integration_tests/test_graph.py` validates graph basics.
- Makefile: `make test`, `make integration_tests`.

## 6) Behavioral Notes
- Debate/Tree are dispatch labels; execution equals Star (parallel); final answer only at L5.  
- Router parse failures or bad formats fall back to default 4-layer plan; legacy `{"selected":[...]}` populates L2/Star.  
- `analyst_results` merge clears on `{"__reset__": True}`.  
- manager_summary filters out `parse_ok=False` outputs; meta note reports filtered count.  
- Stubs remain only for missing-description agents; otherwise all config roles use LLM tools with search enabled by default.
