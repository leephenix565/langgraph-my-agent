# Current Status

This is the current operational status entry for the Fixed DAG reset branch.
Use it for status and roadmap orientation before reading historical phase
records.

## Source Authority

- Branch: `reset/fixed-dag-v1`.
- Source authority: the current Git HEAD in `/sdb/dlut/dev/langgraph-my-agent`.
- Reset lineage anchor: `pre-fixed-dag-reset-20260604-1457`.
- This document intentionally avoids short-lived process identifiers and raw
  endpoint payloads.

## Runtime And Catalog

- The active graph remains `langgraph.json -> src/react_agent/graph.py:graph`.
- The formal catalog has 27 fixed DAG agent ids from
  `config/fixed_dag/agent_catalog.json`.
- Runtime binding authority remains
  `config/fixed_dag/runtime_bindings.json`.
- L4 `decision_synthesizer` and `report_generator` are the current
  compute-default external bindings. This is a compute path, not an invoke
  path.
- `default_external_invoke_enabled=false` remains the runtime-binding default.
  The two L4 compute-default rows also keep `invoke_enabled_by_default=false`.
- Non-L4 production external compute is governed by
  `config/fixed_dag/non_l4_external_compute_policy.json`, not by
  `runtime_bindings.json`. The policy is currently `enabled_by_default=true`
  and compute-only. Required enabled ids remain
  `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, `market_ipo_investor_behavior`,
  `market_capital_flow_chip`, `risk_crash`, `macro_analysis`,
  `macro_index_valuation`, and `value_composite`. RQ3A adds optional enabled
  coverage rows for `value_research_synthesis`, `market_stock_technical`,
  `sentiment_company_radar`, `risk_financial_fraud`,
  `risk_identification`, `risk_compliance_review`,
  `macro_commodity_pricing`, `market_composite`, `risk_composite`, and
  `macro_composite`.

## Router L1 Status

- Current Router theme: `ROUTER-L1-LLM-DIMENSION-ROUTING`.
- M1A implements an internal, default-off dimension router seam. Default
  production behavior remains the full `fixed_dag_plan_v1`.
- When `Context.enable_selected_routing=True` or
  `ENABLE_SELECTED_ROUTING=1` is explicitly set, `route_planner_node` uses a
  provider-free dimension-only route intent. The planner selects only
  `value`, `market`, `risk`, and `macro`; it does not select concrete agent
  ids.
- Concrete L2/L3/L4 steps are expanded deterministically from current
  catalog/constants. Invalid, unsafe, low-confidence, clarification,
  legacy-mode, runtime-binding, endpoint/env/secret/raw-response, or
  agent-level route output falls back to the full DAG.
- No external `route_planner` service, no scaffold copy, no port assignment,
  no runtime binding, no catalog, and no non-L4 policy change is part of M1A.
  `report_generator` remains on production compute port `10026`; `10028/8028`
  remains only a future external route-planner planning reservation.
- M1D adds a fake-provider-only internal LLM dimension-router seam for later
  provider integration. The provider-router flag
  `Context.enable_llm_dimension_router` / `ENABLE_LLM_DIMENSION_ROUTER=1`
  defaults false and is gated behind selected routing; selected routing alone
  does not call a provider, and the provider flag alone does not run when
  selected routing is disabled.
- M1D does not call a real provider, does not invoke `load_chat_model`, and
  does not retain raw fake/provider output. Fake structured output is parsed
  immediately as dimension-only `route_intent_v1`; invalid, unsafe, malformed,
  low-confidence, clarification, selected-agent, legacy-mode, exception,
  timeout, or unavailable provider cases fall back to the full DAG with safe
  reason codes. Public workflow metadata may expose only bounded router
  summaries such as provider-router enabled/invoked, mode `fake`, parse
  status, selected dimensions, and fallback reason.
- M1F0 adds a router-only provider preflight factory/wrapper for the future
  controlled real-provider dry run. It remains default-off and fail-closed: it
  records env var names only, does not read env values, does not call
  `load_chat_model`, does not create an OpenAI/DeepSeek client, and does not
  call a provider or endpoint. Future real-provider use must separately
  authorize selected routing, the LLM dimension router, env-value access, one
  provider call, call cap `1`, streaming `false`, retry `0`, timeout `<=8s`,
  max tokens `<=220`, no raw response/hash retention, no prompt/message
  retention, no process action, and route-plan/snapshot-only evidence.
- M1F0 also adds a router-provider artifact whitelist and unsafe scan. Allowed
  metadata is limited to provider-router enabled/invoked/mode/parse status,
  selected dimensions, safe fallback/error codes, latency/call/cap settings,
  and explicit no-retention booleans. Raw responses, raw response hashes,
  prompts, messages, endpoint/base URL material, env values, secrets,
  tracebacks, chain-of-thought, selected agents, runtime bindings, and DAG
  steps are rejected or omitted.
- M1F3 persists the controlled dry-run compatibility fix inside the
  router-only wrapper. It adds a pure OpenAI-compatible model normalization
  helper for project-style `provider/model` router model ids and a JSON object
  request contract for dimension-only `route_intent_v1` output. This is still
  not live provider enablement: no env values are read, no client is created,
  no provider is called, no prompt/messages or raw response are retained, and
  default production behavior remains the full fixed DAG unless later phases
  explicitly authorize a dry-run.

## Report Quality RQ2E Status

- Report-quality theme status: closed by RQ3C production-mode live verification.
- RQ2E live at commit `12faf7635a9e29b3392ca8c64e83924c0fbb2f4e` completed
  safely but scored `27/45`; RQ3A treats this as a production coverage and
  report-projection gap, not as sandbox drift or a reason to accept sandbox demo
  output.
- RQ3A lifted production-mode live quality to `28/45` and isolated the
  remaining blocker to the risk branch adapter: `risk_compliance_review`
  remains an honest adapter-failed coverage limitation, while RQ3B narrows the
  fix to allowing `risk_composite` partial mapping when a non-contributing risk
  member must be excluded from weighted evidence. RQ3C keeps that scope narrow:
  `risk_composite` evidence references that still point to non-contributors are
  dropped before final L3 validation and recorded as coverage limitations;
  `risk_compliance_review` unsupported-schema mapping is not fixed in RQ3C.
- RQ3C production-mode live verification reached `29/45` with
  `renderer_quality_gate.passed=true`, unsafe scan pass, traceability `1.0`,
  answer/section parity `1.0`, and research-point utilization `1.0`. The
  compute-only boundary held: `/v1/agent/invoke=0`, provider calls `0`, process
  actions `0`, env-value access `0`, and raw response retention `false`.
  `risk_compliance_review` remains a non-blocking backlog limitation.
- RQ2E is allowed only after preflight shows dev/prod/sandbox at the same
  approved HEAD, clean worktrees, matching catalog/runtime/non-L4 policy
  digests, authority docs in sync, and checksum-verifiable input artifacts.
- RQ2E acceptance uses the report-quality audit output for the controlled
  online E2E artifact: score `>=29/45`, `renderer_quality_gate.passed=true`,
  unsafe scan pass, `template_phrase_count<=8`,
  `answer_section_parity.parity_ratio>=0.90`, and
  `traceability.traceability_ratio>=0.85`.

## Sync Workflow Status

- The bidirectional agent sync validation topic is complete.
- The strict one-command publish-and-rebase workflow is operational.
- Final strict cycle: `cycle_strict_e7bc707d5b8b`.
- Current active external-agent baseline:
  `first-cycle-p2s_52d75b56543f`.
- Durable final cycle run:
  `/sdb/dlut/ops-artifacts/agent-sync/runs/run_cycle_strict_cycle_strict_e7bc707d5b8b_20260625T135349Z`.
- Future non-zero work should use the normal experiment workflow: fork an
  immutable baseline, register exact change units, generate exact S2P/P2S
  children, request machine approval, then execute the approved strict cycle.

## Repository Roles

- `/sdb/dlut/dev/langgraph-my-agent` is the main-system development authority.
- `/sdb/dlut/prod/langgraph-my-agent` is a runtime/deployment copy, not a source
  authority.
- `/sdb/dlut/sandbox/*` holds experiments and immutable baselines. The active
  baseline is not edited in place.
- External owner-dev repositories are read-only to this workflow unless a
  separate owner workflow grants write authority.

## Current Engineering Theme

Repository Authority & Active-Core Consolidation is complete. The final
closeout is `docs/REPOSITORY_CONSOLIDATION_CLOSEOUT.md`. The report-quality
theme is also closed by RQ3C. Current product work is the Router L1
dimension-routing theme.

M4A found P4 count `0`, so M4B deletion implementation is skipped. Current
mode returns to normal maintenance and product engineering on top of the fixed
DAG, strict sync workflow, consolidated docs authority, active-core package
boundaries, and Context/State compatibility metadata. No field deletion, public
contract change, graph topology change, catalog change, or runtime binding
change is part of this closeout.

## Current Non-Claims

- Passing static or mainline quality is not production readiness by itself.
- Current docs do not add runtime bindings, live flags, process actions, or
  provider calls.
- Default validation and sync quality gates do not call `/v1/agent/invoke`.
- RQ2E authority and preflight work does not call `/v1/agent/invoke`, make a
  provider direct call, start/stop/signal services, retain raw service/provider
  responses, or read env values.
- Compute evidence must not be recorded as invoke evidence. `externalInvoked`
  and invoke-default flags are `/v1/agent/invoke` claims only; they are not
  proof that no `/v1/agent/compute` call occurred in a later explicit live
  verification phase.
- The smoke/evidence ledgers in `docs/history/` are historical evidence, not
  runtime or configuration authority.
- Public transcripts must not expose secrets, raw graph messages, provider raw
  responses, manager assignment internals, or agent JSON.

## Evidence And History

- Start with `docs/INDEX.md` for the current reading order.
- Historical phase ledgers live under `docs/history/` and are indexed by
  `docs/history/MANIFEST.json`.
- Sync operator procedures live in
  `docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md` and
  `docs/CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md`.
