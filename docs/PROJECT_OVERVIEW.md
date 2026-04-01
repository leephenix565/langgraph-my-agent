# Project Overview: Current Engineering Snapshot

> Scope note: this document is the narrative and current-snapshot entry for the repo. It does not define command truth. For runtime, benchmark, train, and eval commands, prefer `docs/SYSTEM_MAP.md` and `docs/RUNBOOK_ROUTER_SFT.md`. If this document conflicts with runtime code or S0 operation docs, prefer `src/react_agent/*`, focused tests, and the S0 docs listed in `docs/INDEX.md`.

## 1. What This Project Is

This repository is a layered multi-agent orchestration system built on LangGraph `StateGraph`, not a loose collection of standalone prompts or scripts. The current mainline runtime centers on `src/react_agent/`, `config/agents/`, `langgraph.json`, and the surrounding regression / training / observability tooling. Its runtime focus is a Router-led layered plan, Manager-led dispatch, per-agent structured outputs, and a unified final-answer path.

## 2. Current Engineering Snapshot

- Runtime skeleton: `langgraph.json -> src/react_agent/graph.py:graph`
- Main runtime chain: `router_node -> manager_broadcast -> agent nodes -> manager_summary -> (_run_final_summary / finalize_summary) -> optional memory_update -> __end__`
- a01 contract role: `a01_cio_orchestrator` can emit a structured contract, but Manager only consumes it after `extract_contract + validate_contract`; invalid contracts fall back to template assignment.
- Agent catalog snapshot: `config/agents/` currently contains 26 agent configs, and 25 agent nodes enter the runtime node set; `a02_task_router` is excluded because `default_enabled=false`.
- Optional capabilities boundary: `thread_summary`, `messages window`, `results pools`, `stable consume`, and `checkpointer` are env-gated features, not default-always-on behavior.
- Stage snapshot: the repo is closer to `structure-stable` than `quality-stable`; graph topology, state flow, protocol checks, and focused tests have a closed loop, while environment dependencies, training stack readiness, path drift in docs, and partial mojibake indicate that quality and documentation closure are not complete.

## 3. Runtime Mainline

The runtime entrypoint is defined in `langgraph.json` and compiled in `src/react_agent/graph.py`. The mainline behavior is:

1. `router_node` reads the current user turn and produces a layered plan plus layer modes.
2. `manager_broadcast` reads the current layer, mode, and result pool, then assigns work to one or more agents.
3. Agent nodes execute their subtasks and write structured outputs back to the current result pool.
4. `manager_summary` checks pending agents, advances layers when a layer is complete, and triggers final summarization on the terminal path.
5. `_run_final_summary` or `finalize_summary` produces the outward-facing answer.
6. `memory_update` writes `thread_summary` only when thread-summary support is enabled and the turn is already in the final step.

This means `manager_summary` is a layer-control node, not the sole final-answer node. Final answer generation is centralized in the final-summary path.

## 4. a01 Contract in Runtime

The a01 contract is already on the runtime hot path, but it is not treated as an unconditional source of truth.

- Generation: `a01_cio_orchestrator` is prompted to emit a structured `contract` alongside its normal structured output.
- Preservation: the agent output parser keeps extra keys, so `contract` survives parsing instead of being discarded.
- Validation: runtime uses `extract_contract(...)` and `validate_contract(...)` to check schema version, key set, selected agent coverage, and `tasks[].steps` constraints before dispatch consumption.
- Consumption: `manager_broadcast()` prefers contract-based assignment only when validation succeeds for the currently selected agent set.
- Fallback: if validation fails, or if an agent has no valid contract task, Manager falls back to the normal assignment templates.

The contract is therefore a validated dispatch protocol, not a blind override.

## 5. Optional Env-Gated Capabilities

The current repo has several context and persistence features, but they are opt-in.

- `REACT_AGENT_CHECKPOINTER`: enables persistent graph invocation via `graph_persistent` / `get_graph_for_invoke(thread_id)`.
- `REACT_AGENT_THREAD_SUMMARY`: enables post-turn `thread_summary` writeback and injects that summary into Router and final-summary prompt assembly.
- `REACT_AGENT_MESSAGES_WINDOW`: trims `state["messages"]` for Router and final-summary prompt assembly only.
- `REACT_AGENT_RESULTS_POOLS`: switches runtime reads to `ephemeral_results` and enables `stable_findings` accumulation on the final path.
- `REACT_AGENT_STABLE_CONSUME`: injects a bounded `stable_findings` summary into Router and final-summary prompt assembly only.
- `DISABLE_SEARCH`: disables ordinary analyst search at runtime; `a01_cio_orchestrator` and `a25_report_center` are already no-search agents regardless of this flag.
- `ROUTER_MODEL`, `ROUTER_OPENAI_BASE_URL`, `ROUTER_OPENAI_API_KEY`: only affect Router model selection and Router-side OpenAI-compatible endpoint override.

These controls should be described as optional runtime switches, not as default behavior.

## 6. Stage Positioning

The current repo snapshot supports a `structure-stable` reading, not a `quality-stable` one.

- What is already closed at the structure layer: entrypoint wiring, graph topology, Router parsing, contract validation and dispatch fallback, finalization routing, results-pool handling, and focused unit/integration coverage.
- What is not yet sufficient for a `quality-stable` claim: training dependencies are not universally available in the local baseline env, some runbook and changelog entries still carry historical path drift, and parts of the long-form docs still contain encoding damage.

This is a stronger statement than "still designing from scratch", but a weaker statement than "all engineering quality is stabilized".

## 7. Confirmed Current Engineering Focus

The repo directly supports the following current focus areas:

- protocol alignment between prompts, runtime validation, and tests
- regression and evaluation chains for Router-SFT and a01-SFT
- observability and trace analysis for runtime latency and failures
- environment baseline clarification and command-path consolidation
- documentation and runbook closure around the existing mainline

The repo does not provide direct evidence that the primary focus has already shifted to frontend experience or broad productization. That claim should be treated as unconfirmed unless additional repo evidence is added.

## 8. Short External Description

The following paragraph is intentionally short enough to reuse in proposals, reports, or engineering summaries:

> This project is a layered multi-agent orchestration system built on LangGraph `StateGraph`. Its main runtime entrypoint is `langgraph.json -> src/react_agent/graph.py:graph`, and its runtime path is `router_node -> manager_broadcast -> agent nodes -> manager_summary -> (_run_final_summary / finalize_summary) -> optional memory_update -> __end__`. The `a01` contract already sits on the runtime hot path, but it is consumed only after runtime validation and otherwise falls back to normal Manager assignment. Capabilities such as `thread_summary`, `messages window`, `results pools`, `stable consume`, and `checkpointer` are env-gated options rather than default-always-on behavior. The current repo is closer to `structure-stable` than `quality-stable`: runtime structure and protocol closure are in place, while environment, training, and documentation closure remain in progress.
