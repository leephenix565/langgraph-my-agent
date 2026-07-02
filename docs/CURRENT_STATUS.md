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

- Current Router theme: `ROUTER-L1-M2-SELECTED-ROUTING-IMPLEMENTATION`.
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
- M1F5 adds the missing OpenAI-compatible chat-completions endpoint path
  normalization contract to the same wrapper. Future controlled dry-runs should
  build the endpoint by appending `/chat/completions` to base paths ending in
  `/v1`, or `/v1/chat/completions` when `/v1` is absent. Only sanitized booleans
  such as path-normalized and v1-added are artifact-safe; endpoint/base URL
  values remain forbidden.
- M1F7 persists the strict route-intent message contract used by future
  controlled real-provider dry-runs. The router-only wrapper can now build
  OpenAI-compatible chat messages using a single strict user-message layout,
  which is the provider-compatible layout verified by controlled diagnostics.
  The message asks the provider to echo an exact locally-built
  `route_intent_v1` JSON object from deterministic dimension hints, allows only
  dimension-level `selected_dimensions`, forbids concrete agents and legacy route
  modes, and rejects analysis/report prose or markdown-wrapped output. The
  messages are in-memory request material only: artifacts may record safe
  contract versions, booleans, and the sanitized layout name, but prompt/message
  text remains forbidden. M1G2 changes the provider dimension-router draft to
  `task_type="general"` so focused value-only and market-only analysis routes
  can validate as dimension selection. It does not relax the fixed-DAG
  investment safeguard: `task_type="single"` and related investment-judgment
  task types still require the `risk` dimension.
- M1H closes Router M1. The persisted default-off provider path has passed a
  dev-only five-case real-provider stability matrix after the M1G2 patch:
  provider calls `5`, real LLM calls `5`, all status classes `2xx`, parse_ok
  cases `5/5`, selected plan compiled cases `5/5`, selected agents accepted
  `false`, under-routing failures `0`, artifact whitelist pass, unsafe scan
  pass, and no raw response/hash, prompt/messages, env values, endpoint/base
  URL, API key, traceback, or chain-of-thought retention. Two non-blocking
  conservative over-routing warnings remain: `risk_compliance_focus` selected
  `value+risk`, and `market_short_term_focus` selected `value+market`.
- Router M1 did not production-enable provider routing, but the current public
  API can now production-enable the persisted LLM dimension-router path through
  server-side operator configuration. Default `Context()` and omitted public
  `routing` still run the full fixed DAG. No external `route_planner` service
  exists, no route-planner port is assigned, `10028/8028` remains a future
  planning reservation only, `report_generator` remains on `10026`, and
  `/invoke` is not the default runtime.
- Router M2 closes the minimal default-off selected-routing graph E2E report
  path. When an explicit context enables selected routing, `route_planner_node`
  emits dimension-only `route_intent_v1`, compiles
  `selected_fixed_dag_plan_v1`, `execute_fixed_dag` executes the selected legal
  subgraph, L4 `decision_synthesizer` / `report_generator` still close the
  final report path, and the public workflow model exposes only public-safe
  selected-routing/provider-router provenance fields. Default `Context()`
  remains the full DAG; provider routing remains default-off/fake-only.
- Router M2 also adds an internal public-runtime context override seam for
  endpoint-free tests. The public HTTP/Web surface now adds a request-level
  `routing: {"mode": "selected"}` opt-in for sync and stream sends. Omitted or
  null `routing` keeps the existing server default and selected routing remains
  default-off. When the daemon runs with
  `PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER=1`, that selected request uses the
  real OpenAI-compatible LLM dimension router; otherwise it stays deterministic.
  The real-router parser now hardens production provider output by extracting a
  bounded JSON object from common wrappers before applying the strict
  dimension-only `route_intent_v1` normalizer. It also accepts
  OpenAI-compatible text content parts/lists and projects only safe
  output-shape error codes when a provider call returns no usable route text.
  If an LLM provider returns bounded safe dimension text such as
  `value and risk` or `选择维度：估值、下行风险`, the graph can repair that
  provider output into a `route_intent_v1` before normal validation. Multi-line
  selected/unselected summaries are filtered so unselected dimensions are not
  promoted. This path still does not infer dimensions directly from the user
  question.
  This improves live selected-DAG stability and diagnostics without accepting
  agent-level routing, unknown dimensions, low confidence, runtime controls,
  raw provider material, endpoint material, SQL, env values, secrets, prompts,
  or chain-of-thought.
  This does not add an explicit public `full_dag` force-off mode, public
  provider/model/key control, compute/invoke control, runtime binding change,
  catalog change, non-L4 policy change, or route-planner service/port
  authority.
- The public API health contract now includes freshness/capability markers:
  `publicApiContractVersion`, `routingRequestSupported`,
  `selectedRoutingRequestSchema`, `selectedRoutingRouterMode`,
  `llmDimensionRouterEnabled`, `computeRegistryVersion`,
  `computeRegistryAgentCount`, `processStartTime`, `processUptimeSeconds`, and
  `sourceVersionMarker`. These fields make daemon drift and router-mode drift
  visible without exposing env values or raw endpoint material.
- The file-backed public thread store now repairs stale legacy thread entries
  during reads: valid current-contract threads are preserved, invalid legacy
  entries are isolated, and the repaired envelope is written back. A historical
  bad thread should not block new public API sessions.
- Public workflow provenance may include `performanceTelemetry` with bounded
  request, graph, compute, and per-agent timing/status summaries. Provider and
  DB timings are populated only when a service reports safe counts/durations;
  otherwise the telemetry records explicit instrumentation gaps. This remains
  `/v1/agent/compute` observability and does not expose `/invoke`, raw provider
  payloads, SQL, prompts, endpoint URLs, or secrets.

## Report Quality RQ2E Status

- Report-quality theme status: closed by RQ3C production-mode live verification.
- RQ2E live at commit `12faf7635a9e29b3392ca8c64e83924c0fbb2f4e` completed
  safely but scored `27/45`; RQ3A treats this as a production coverage and
  report-projection gap, not as sandbox drift or a reason to accept sandbox demo
  output.
- RQ3A lifted production-mode live quality to `28/45` and isolated the
  remaining blocker to the risk branch adapter: `risk_compliance_review`
  remained an honest adapter-failed coverage limitation at that time, while
  RQ3B narrowed the fix to allowing `risk_composite` partial mapping when a
  non-contributing risk member must be excluded from weighted evidence. RQ3C
  kept that scope narrow: `risk_composite` evidence references that still point
  to non-contributors are dropped before final L3 validation and recorded as
  coverage limitations.
- RQ3C production-mode live verification reached `29/45` with
  `renderer_quality_gate.passed=true`, unsafe scan pass, traceability `1.0`,
  answer/section parity `1.0`, and research-point utilization `1.0`. The
  compute-only boundary held: `/v1/agent/invoke=0`, provider calls `0`, process
  actions `0`, env-value access `0`, and raw response retention `false`.
  A later real-agent service repair fixed `risk_compliance_review` service-side
  no-data compute output and direct all-agent smoke mapped `26/26` external
  services with hard unsafe marker count `0`; that repair did not alter
  runtime bindings, the agent catalog, or non-L4 production default policy.
- The follow-up real-agent content/status closeout repaired the remaining
  scoped service-level status blockers and added macro-composite adapter
  fail-soft handling for declared but non-real contributors. Controlled
  verification reached `26/26` external service health, `26/26` compute JSON,
  `26/26` adapter mapping, hard unsafe marker count `0`, full DAG
  compute-enabled report E2E with `failed_agents=[]`, and selected value/risk
  compute-enabled report E2E with a final report. The boundary remained
  compute-only: `/v1/agent/invoke=0`, provider calls `0`, env-value access `0`,
  and raw response retention `0`.
- The report-quality semantics follow-up keeps `26/26` external compute
  mapping while tightening L3 contributor semantics in the adapter and
  deterministic reducer. Fallback/stand-in/no-evidence/zero-weight members are
  retained only as degraded limitations, selected value/risk trust artifacts are
  generated, and the offline report-quality harness now records
  `l3_contributor_integrity_v1`. The full DAG compute report E2E passes the
  source-controlled floor at `29/45` with `renderer_quality_gate.passed=true`
  and no L3 contributor-integrity violations.
- The RQ2 bundle/renderer follow-up keeps the same compute-only boundary and
  improves report trustworthiness: `report_input_bundle_v1` now carries
  route-aware scope and dimension coverage metadata, selected value/risk reports
  render only value/risk as active sections, market/macro are shown as
  unselected scope, risk-compliance zero-readable-evidence wording is
  limitation-only, and the controlled full DAG compute report audit reaches
  `33/45` with renderer gate, selected-scope integrity, evidence-bundle
  completeness, L3 contributor integrity, and unsafe scan passing.
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
theme is also closed by RQ3C. Router L1 M1 is closed by M1H, and Router L1 M2
now closes default-off selected-routing graph E2E report behavior with
public-safe provenance. External route-planner service, route-planner port
authority, real provider routing, live endpoint E2E, and production enablement
remain later phases.

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
