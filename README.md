# langgraph-my-agent

This branch is the Fixed DAG reset branch. It replaces old route-mode,
Router-SFT, route-prior, A01 contract dispatch, and Fair Fusion mainline
material with the current fixed-DAG runtime and strict sync workflow.

For current status, read `docs/CURRENT_STATUS.md`. The Repository Authority &
Active-Core Consolidation theme is complete and recorded in
`docs/history/REPOSITORY_CONSOLIDATION_CLOSEOUT.md`. Historical phase ledgers and
closeouts are retained under `docs/history/` with a machine-readable manifest;
they are evidence, not current authority.

> **Vibe Coding Culture**: This repo is AI-assisted development (`AGENTS.md` §Vibe Coding Culture).
> The docs *are* the shared context — change code and docs in the same pass.
> No doc debt. Leave docs better than you found them.

## Current Authority Reading Order

1. `README.md`
2. `AGENTS.md`
3. `docs/INDEX.md`
4. `docs/CURRENT_STATUS.md`
5. `docs/FRONTEND_V2.md`
6. `docs/ARCHITECTURE_FIXED_DAG.md`
7. `docs/CONTRACTS.md`
8. `docs/QUALITY.md`
9. `docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md`

## Current Branch Scope

- Branch: `frontend-ui-refinements`.
- Runtime entry: `langgraph.json -> src/react_agent/graph.py:graph`.
- Public Python workflow contract: `workflow_snapshot_v2`.
- Public agent catalog: fixed DAG 27-agent `snake_case` projection from
  `config/fixed_dag/agent_catalog.json`.
- Runtime binding authority: `config/fixed_dag/runtime_bindings.json`; the
  source-controlled non-L4 production compute policy is separate and lives in
  `config/fixed_dag/non_l4_external_compute_policy.json`.
- Sync workflow: strict publish-and-rebase has completed a real non-zero cycle;
  future work uses normal experiment/change-unit/approval flow.
- Repository Authority & Active-Core Consolidation: complete; M4A found no P4
  deletion candidates and skipped M4B deletion.
- Production status: this repository records source and contracts. Passing
  tests or docs gates is not production readiness by itself.

## Active Runtime Skeleton

The active graph is provider-free and has no external `/v1/agent/invoke` path:

```text
user input
  -> route_planner
  -> prepare_l1_context
  -> run_l2_conclusions (incremental L2 phase with production compute overlay)
  -> run_dimension_composites (incremental L3 phase)
  -> decision_synthesizer (incremental L4 decision + report phase)
  -> final_emit
  -> memory_update
```

`execute_fixed_dag` walks the 27-agent `fixed_dag_plan_v1` by validated
dependencies, produces topological batches, records per-step execution results,
and fills the L2/L3/L4 result contracts. Current compute-only defaults are part
of that runtime boundary: the non-L4 production compute policy is
`enabled_by_default=true`, and L4 `external_compute_default` remains limited to
`decision_synthesizer` and `report_generator`. Compute evidence must not be
recorded as invoke evidence; `/v1/agent/invoke` remains out of the default path.
Explicit public selected routing can use the real LLM dimension router only
when the request asks for `routing: {"mode": "selected"}` and the daemon is
operator-configured for `llm_real`. Omitted or null public `routing` remains on
the server default, which is full DAG unless an operator separately enables
`PUBLIC_SELECTED_ROUTING_DEFAULT=1`. The explicit selected-router path now
projects bounded public-safe diagnostics for attempt count, elapsed time,
output shape, retry mode, parse stage, and safe error code; it still never
exposes prompts, raw provider output, endpoint material, env values, or
credentials. Long-tail L4 `report_generator` latency is a separate operational
limitation and is not a selected-routing default or safety change.
RQ3A expands the non-L4 policy with optional, fail-soft production coverage
rows to improve report quality in production mode; this is not a runtime
binding change and not sandbox demo acceptance.
RQ3B keeps that policy unchanged and narrows the remaining report-quality lift
to adapter handling for the risk branch: `risk_composite` may map as partial
when a non-contributing risk member is retained only as a coverage limitation.
RQ3C keeps the same scope and additionally drops risk-composite evidence
references that point at non-contributing members before final L3 validation.
The later real-agent service repair fixed `risk_compliance_review` service-side
compute output so it now maps through the adapter in direct all-agent smoke,
without changing runtime bindings, the fixed-DAG catalog, or the non-L4
production default policy.
The RQ3C production-mode live verification reached the minimum report-quality
acceptance score `29/45` with `renderer_quality_gate.passed=true`, closing the
current report-quality theme at the compute-only boundary. The later
real-agent report-quality semantics pass keeps that floor but tightens the
meaning of L3 support: fallback, stand-in, zero-weight, no-evidence, and
`not_evaluated` members are filtered out of `contributing_agents` and
`evidence_refs`, and the offline harness now audits those public-safe
contributor-integrity fields before passing the `29/45` gate.
The RQ2 bundle/renderer follow-up raises the controlled full-DAG compute report
quality to `33/45` and makes selected-routing reports route-aware: selected
runs render only selected dimensions as active analysis and place unselected
dimensions in an explicit uncovered-scope section. The harness now also checks
evidence-bundle completeness, selected-scope integrity, unselected-dimension
overstatement count `0`, and risk-compliance zero-evidence wording.
The public report language pass keeps that runtime behavior unchanged but makes
the final public report Chinese-first: route, DAG, L2/L3/L4, metric, enum, and
runtime-boundary contract terms are rendered as Chinese labels with English
terms in parentheses only when useful.
When the external L4 `report_generator` reports a provider-backed LLM call via
sanitized telemetry, its `report_result_v1` is the primary final report and the
deterministic report-quality renderer must not overwrite it. The deterministic
renderer remains a public-safe fallback for weak or non-provider L4 report
results.
The public API production-observability follow-up adds a freshness guard to
`/api/health` and a bounded `performanceTelemetry` projection in workflow
provenance. This lets operators distinguish stale daemons from current
contract-capable ones and profile request/graph/compute/agent timing without
exposing raw responses, SQL, prompts, provider payloads, endpoint URLs, env
values, or secrets.
The LLM router enablement follow-up allows operators to set
`PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER=1` for the public API daemon. When
`PUBLIC_SELECTED_ROUTING_DEFAULT=1` is also set, omitted or null public
`routing` uses the same selected-routing path by server default. In either
case, selected routing uses the OpenAI-compatible LLM dimension router before
compiling the selected fixed DAG; the public request still cannot provide
provider, model, base URL, API key, compute, or invoke controls. The live
router still asks the provider for a
strict `route_intent_v1` JSON object, but the graph now tolerates common
provider wrapping such as JSON code fences by extracting the first bounded JSON
object and then applying the existing fail-closed route-intent normalizer. It
also accepts OpenAI-compatible text content parts/lists and records only safe
output-shape reason codes when a provider call has no usable route text. A
bounded safe LLM response such as `value and risk` or `选择维度：估值、下行风险`
may be repaired into `route_intent_v1`; selected/unselected multi-line text is
filtered so unselected dimensions are not promoted. The graph does not use this
path to infer dimensions directly from the user question. If the first provider
response is not parseable, bounded retries switch to a compact dimension-id
prompt so the real LLM can still return `value`, `market`, `risk`, and/or
`macro` without JSON-mode fragility.
The explicit selected value/risk hardening keeps the server default on the
full DAG unless `PUBLIC_SELECTED_ROUTING_DEFAULT=1` is set, but improves
explicit `routing: {"mode": "selected"}` requests by teaching the live prompt
that valuation/downside-risk language maps to `value,risk`, canonicalizing
bounded provider aliases such as `valuation` and `downside_risk`, and letting
transient router timeouts or unrepairable invalid JSON consume the bounded
retry budget before failing closed.
Unknown dimensions, agent-level selection, forbidden fields, low confidence,
empty/truncated provider content, raw provider material, endpoint material,
prompts, SQL, env values, and secrets still force full-DAG fallback instead of
selected execution.
The public JSON thread store repairs stale legacy thread entries during reads,
preserving valid current-contract sessions while preventing one historical bad
thread from blocking new public API sessions.

R8-1 keeps this full DAG path as the regression baseline and fallback. It adds
`route_intent_v1` as a planner-output contract and
`selected_fixed_dag_plan_v1` as the future deterministic compiler/validator
target. `route_intent_v1` is not executable; the selected plan contract allows
omitted dimensions and agents only when they are explicitly recorded, keeps
`report_generator` always on for selected plans, requires risk and
`decision_synthesizer` for investment-judgment task types, and rejects legacy
route-mode fields, runtime binding fields, provider/external invocation claims,
and unsafe fallback text. R8-1 does not connect an LLM planner, does not change
`graph.py`, and does not enable selected execution.

R8-2 implements the deterministic compiler for that seam:
`compile_selected_fixed_dag_plan(route_intent, user_text, as_of)` validates the
intent, adds required L1/evidence seams, adds selected L2 steps, adds selected
dimension composites, includes `decision_synthesizer` for investment-judgment
task types, keeps `report_generator` always present, and emits a
dependency-closed `selected_fixed_dag_plan_v1`. Executor-side selected
validation is available through `validate_selected_dag_steps` and
`topological_batches_for_selected_plan`. The active `route_planner` node and
`execute_fixed_dag` path still use the full `fixed_dag_plan_v1` unless a later
phase explicitly changes the runtime.

R8-3 adds the planner seam that can produce `route_intent_v1` before compiler
handoff. `build_default_route_intent(question)` is deterministic and
provider-free; `FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT` and
`build_route_intent_prompt(question)` define the future LLM/semantic planner
protocol; `parse_route_intent_json` and `normalize_route_intent` parse or
fail-soft raw planner JSON into public-safe route intent. The planner seam never
outputs executable `dag_steps` or dependencies. The selected compiler remains
the only path from intent to selected DAG, and it is not wired into the active
graph default in R8-3.

R8-4 adds RouteEval for the route-intent seam:
`load_route_eval_cases(path)` reads a small JSONL gold set,
`evaluate_route_intents(cases, planner_fn)` evaluates deterministic/mock
planner output, and `route_eval_report_to_dict(report)` emits stable metrics.
The metrics cover task type accuracy, target exact-or-partial match, dimension
precision/recall/F1, agent precision/recall/F1, over-selection,
under-selection, clarification accuracy, and fallback rate. RouteEval does not
evaluate Star/Chain/Debate/Tree modes and does not call providers, search, or
external `/v1/agent/invoke`. The first 12-case fixture is a baseline only; the
future formal Route F1 gate should use a larger gold set.
R8-4 does not modify `src/react_agent/graph.py`, public workflow mapping,
frontend rendering, runtime bindings, provider/search readiness, or external
adapter readiness.

R8-5 wires the selected route intent and compiler pipeline into
`route_planner_node` behind an explicit default-off flag. With
`Context(enable_selected_routing=True)` or `ENABLE_SELECTED_ROUTING=1`, the
graph builds `route_intent_v1` through `build_default_dimension_route_intent`,
compiles it into `selected_fixed_dag_plan_v1`, and executes selected DAG steps
through the selected executor validation path. Compile or selected validation
failure falls back to the full `fixed_dag_plan_v1` with public-safe provenance
(`selected_routing_requested`, `selected_routing_fallback`, and a safe fallback
reason). R8-5 still does not call an LLM/provider, search backend, external
`/v1/agent/invoke`, or runtime binding adapter.

Router M1A keeps the same default-off boundary and updates the internal
selected-routing seam to dimension-level planning. With selected routing
explicitly enabled, the internal route planner now builds a provider-free
dimension-only intent: the planner may select only `value`, `market`, `risk`,
and `macro`; it does not select concrete agent ids. The deterministic compiler
expands selected dimensions from the current catalog/constants into
same-dimension L2 agents, matching L3 composites, required L1 evidence seams,
and L4 `decision_synthesizer` / `report_generator`. Invalid, unsafe,
low-confidence, clarification, legacy Star/Chain/Debate/Tree, runtime-binding,
endpoint/env/secret/raw-response, or agent-level route output falls back to the
full DAG. M1A creates no external router service, assigns no route-planner
port, leaves `10028/8028` as planning-only reservation, preserves
`report_generator` on port `10026`, and does not modify runtime bindings,
agent catalog, or non-L4 policy.

Router M1D adds the next internal seam without enabling a real provider:
`Context.enable_llm_dimension_router` / `ENABLE_LLM_DIMENSION_ROUTER=1` is a
fake-provider-only router-provider flag, defaults false, and is gated behind
selected routing. `ENABLE_SELECTED_ROUTING=1` alone still does not call a
provider. When both flags are enabled in tests, fake structured JSON is parsed
immediately through the dimension-only `route_intent_v1` parser; raw provider
text, prompts, messages, endpoint material, env values, tracebacks, and
chain-of-thought are not retained in graph state, workflow snapshots, final
emit payloads, artifacts, or public output. Invalid provider output, provider
exceptions, simulated timeouts, `selected_agents`, forbidden fields, legacy
route modes, low confidence, and clarification requests all fail soft to the
full DAG with safe fallback codes. M1D still creates no external
`route_planner` service, assigns no route-planner port, leaves `10028/8028` as
planning-only reservation, preserves `report_generator` on port `10026`, and
does not modify runtime bindings, agent catalog, or non-L4 policy.

Router M1F0 adds the router-only provider preflight factory used by the next
controlled dry-run phase. It is still default-off and fail-closed: the factory
does not call a real provider, does not invoke `load_chat_model`, does not read
env values, does not create an OpenAI/DeepSeek client, and does not call any
endpoint. The preflight gate records env var names only and requires explicit
future authorization for selected routing, the LLM dimension-router flag,
real-provider use, env-value access, and one provider call. The first real
dry-run contract is bounded to call cap `1`, streaming `false`, retry `0`,
timeout `<=8s`, max tokens `<=220`, no raw response/hash retention, no
prompt/message retention, no endpoint/process/external service, and
route-plan/snapshot-only evidence. M1F0 also adds a router-provider artifact
whitelist and unsafe scan for raw responses, hashes, prompts, messages,
endpoints, env values, secrets, tracebacks, chain-of-thought, selected agents,
runtime bindings, and DAG steps.

Router M1F3 persists the compatibility contract learned from the controlled
dry-run diagnostics without enabling live provider use. The router-only
provider wrapper now exposes a pure model-normalization helper for
OpenAI-compatible HTTP APIs, so project-level `provider/model` router model ids
can be converted to the provider API model id inside an explicitly authorized
dry-run. It also exposes a safe request contract requiring JSON object response
format for dimension-only `route_intent_v1` output. These helpers do not read
env values, do not create a provider client, do not retain prompts/messages or
raw responses, and do not change runtime bindings, route-planner ports, or
default full-DAG behavior.

Router M1F5 persists the remaining OpenAI-compatible endpoint path contract.
The router-only wrapper now exposes a pure helper that builds the chat
completions endpoint by appending `/chat/completions` when the configured base
path already ends in `/v1`, or `/v1/chat/completions` otherwise. The helper is
for controlled dry-run use only; it does not read env values, create clients,
call providers, retain endpoint values in artifacts, assign a route-planner
port, or change default full-DAG behavior.

Router M1F7 persists the strict route-intent message contract needed by the
controlled real-provider dry-run. The router-only wrapper now exposes a pure
messages builder for OpenAI-compatible chat requests. The compatibility layout
is a single strict user message because controlled diagnostics showed that this
provider returns parseable JSON with that layout while system+user routing
messages were not stable. The message asks the provider to echo an exact
locally-built `route_intent_v1` JSON object from deterministic dimension hints,
so routing correctness is still guarded by the parser and compiler rather than
free-form provider generation. The contract allows only dimension-level
`selected_dimensions`, no agent-level choices, no legacy route modes, no
analysis/report prose, and no markdown around the JSON. The request-contract
metadata records only safe booleans, contract
versions, and the sanitized layout name; prompts/messages remain forbidden in
artifacts and public workflow metadata. M1G2 makes that provider dimension
router draft use `task_type="general"` because it is an analysis-dimension
selection contract, not an investment judgment. The fixed-DAG safeguard for
investment task types is unchanged: `task_type="single"` and related investment
types still require the `risk` dimension. This still does not create a provider
client, read env values, call a provider, assign a route-planner port, or change
default full-DAG behavior.

Router M1H closes the internal default-off LLM dimension-routing milestone.
The persisted router path has been verified through a dev-only real-provider
stability matrix after the M1G2 task-type patch: 5 provider calls returned
`2xx`, all 5 provider outputs parsed as dimension-only `route_intent_v1`, all 5
selected plans compiled, selected agents were not accepted, under-routing
failures were `0`, and safety scans passed with no raw response/hash,
prompt/message, env, base URL, key, traceback, or chain-of-thought retention.
Two non-blocking conservative over-routing warnings remain in backlog:
`risk_compliance_focus` selected `value+risk`, and
`market_short_term_focus` selected `value+market`. M1H is a milestone closeout,
not production enablement: selected routing and provider routing remain
default-off, there is no external `route_planner` service or route-planner
port, `10028/8028` remains a future planning reservation, `report_generator`
stays on `10026`, runtime bindings are unchanged, and Router M2 owns the
controlled selected-routing graph E2E closure under the same default-off
boundary.

Router M2 closes the minimal default-off selected-routing E2E report path. An
explicit selected-routing context can produce a dimension-only `route_intent_v1`,
compile `selected_fixed_dag_plan_v1`, execute the selected legal subgraph
through `execute_fixed_dag`, retain L4 `decision_synthesizer` /
`report_generator` report closure, and expose public-safe selected-routing
provenance through the public workflow model. Default `Context()` still runs
the full DAG. Provider routing remains default-off/fake-only, tests disable
external compute defaults, runtime bindings/catalog/non-L4 policy are
unchanged, and `/v1/agent/invoke` is still not a default runtime path.

The public HTTP/Web surface now offers a per-request selected-routing opt-in:
`routing: {"mode": "selected"}` on `/api/threads/{thread_id}/messages` and the
matching stream route. Omitting `routing` or sending `routing: null` preserves
the server default. With `PUBLIC_SELECTED_ROUTING_DEFAULT=1`, the server
default is selected routing; otherwise it is the full DAG. This public switch
maps to `Context(enable_selected_routing=True)` for that request. When the
server-side `PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER=1` flag is set, selected
routing also enables `Context.enable_llm_dimension_router` with
`llm_dimension_router_mode` `real`; otherwise it stays on deterministic
selected routing. The request does not expose provider router, compute, invoke,
model, base URL, API key, or env controls, and it does not provide an explicit
`full_dag` force-off mode. The real-router path accepts only a sanitized
dimension-level `route_intent_v1`;
JSON wrapped in markdown/prose may be extracted, but unsafe or unsupported
fields, empty provider content, and truncated provider responses still fail
closed to the full DAG with only public-safe reason codes.

The reset target has 27 formal agent ids:

- L1 planning/evidence seams: 3 target ids.
- L2 conclusion placeholders: 18 target ids.
- L3 dimension composites: 4 target ids.
- L4 decision/report: 2 target ids.

The v4 feedback-aligned roster removes the enterprise financial analysis target.
`sentiment_company_radar` belongs to the market dimension and routes only to
`market_composite`; it is not a direct risk-composite input in this reset
runtime.

See `docs/ARCHITECTURE_FIXED_DAG.md` for the current skeleton map.

## Active Agent Catalog

R4-A makes the fixed DAG catalog the active backend catalog source:

- `config/fixed_dag/agent_catalog.json`
- `src/react_agent/fixed_dag_catalog.py`

The catalog is aligned to the v4 feedback workbook:

- `新架构_固定DAG_最终分层级智能体表_v4_反馈修正版.xlsx`

The public `/api/agents` endpoint now projects 27 enabled `snake_case` reset
agents with layer counts L1=3, L2=18, L3=4, L4=2. Its public shape remains
compatible with the existing `AgentCatalogResponse`, but in R4-A
`configCount`, `runtimeCount`, and `disabledIds` describe the fixed DAG reset
catalog, not the old aNN config catalog.

## Active Runtime Bindings

R4-B adds a backend-only runtime binding source:

- `config/fixed_dag/runtime_bindings.json`
- `src/react_agent/fixed_dag_runtime_registry.py`

The binding registry covers the same 27 fixed DAG ids as the active catalog and
records how each id currently maps to one of these runtime categories:

- deterministic skeleton seams
- external HTTP candidates
- external compute defaults
- pending placeholders

Only `decision_synthesizer` and `report_generator` are
`external_compute_default`, and those bindings target loopback
`/v1/agent/compute`, not `/v1/agent/invoke`. Other external HTTP candidates
remain disabled by default. Legacy aNN ids may appear only as `legacy_agent_id`
migration notes, never as primary reset ids.

The executor annotates `fixed_dag_step_result_v1` records with binding metadata
such as `runtime_kind`, `implementation_status`, `binding_source`,
`legacy_agent_id`, `external_agent_id`, `invoke_enabled`, and `live_verified`.
It does not include endpoint URLs or env var values in step results.

## Current Runtime Boundary

R3/R4-C keeps the graph deterministic and routes graph/public fallback
construction through contract, executor, and public mapping seams:

- `src/react_agent/fixed_dag_contracts.py`
- `src/react_agent/fixed_dag_executor.py`
- `src/react_agent/fixed_dag_runtime_registry.py`
- `src/react_agent/graph.py`
- `src/react_agent/prompts.py`
- `src/react_agent/router_parse.py`
- `src/react_agent/state.py`
- `src/react_agent/agent_types.py`
- `src/react_agent/public_contracts.py`
- `src/react_agent/public_mapping.py`
- `src/react_agent/public_runtime.py`
- `src/react_agent/public_api.py`

The graph state now carries `dag_execution`, `dag_step_results`, and
`execution_batches` in addition to the reset result contracts. R4-B step
results include runtime binding metadata for workflow inspection, but this does
not mean any external service was invoked.

R4-C adds an explicit legacy boundary:

- `src/react_agent/legacy_agent_registry.py` owns historical `AGENT_METADATA`
  and `AGENT_TOOLS`.
- `src/react_agent/graph_bootstrap.py` is legacy-only compatibility bootstrap.
- `src/react_agent/agents.py` keeps shared typing and lazy compatibility
  exports, but active fixed-DAG state imports types from `agent_types.py`.
- `config/agents/*.json` remains as migration/readiness input only.
- `src/react_agent/external_http_config.py` keeps offline external candidate
  metadata; `src/react_agent/external_http_agents.py` remains retained wrapper
  infrastructure, not live-verified runtime.

Importing `react_agent.graph` must not import or execute legacy bootstrap,
`AGENT_TOOLS`, default LLM/search placeholder registration, generic agent
registration, or HTTP wrapper implementation modules. `config/agents/*.json` is
still retained, but it is no longer the active reset public catalog or runtime
registration truth.

## Previous R3.6 Cleanup Boundary

R3.6 removed high-confidence dead local artifacts and legacy test fixtures that
were not active entry points, and added the v4 feedback workbook to the repo:

- `新架构_固定DAG_最终分层级智能体表_v4_反馈修正版.xlsx`

That workbook is the R4 baseline input for the `snake_case` catalog/runtime
registry. R4-A adds the backend catalog source and public projection. R3.6 did
not delete the old aNN catalog/config files, the existing web workflow
implementation, external wrapper production code, baseline/fusion regression
inputs, or tracked historical benchmark/trace artifacts that still need an
archive policy.

## Public Transcript Boundary

The product keeps a single assistant transcript. Internal graph steps, raw graph
messages, manager assignments, agent JSON, and provider raw responses must not
be treated as public transcript content.

The workflow inspector is a diagnostic panel. The Python public adapter projects
DAG stages, steps, dimensions, provenance, and final source as
`workflow_snapshot_v2` through reset contract seams. R3 also exposes
`executionBatches` and `stepResults` for the inspector. R4-B adds binding
metadata to `stepResults`. R5-B1 updates the frontend workflow/chat types,
streaming placeholder, mocks, and smoke fixtures to consume this public shape.
R5-B2 renders stage timeline, execution batches, dimension groups, selected
step result metadata, final source, and provenance in the inspector while
preserving the single user/assistant transcript boundary.
R5-B2.6 keeps that boundary and localizes the visible web copy, inspector
labels, status labels, mock/screenshot fixture copy, and deterministic
public-safe reset skeleton answer. It keeps technical ids, schema names, and
runtime enum values available where needed for debugging.
R5-C keeps the same public contracts but reduces engineering/status noise in
normal UI. Chat empty state, answer cards, workflow collapsed summaries, Agents
overview, and Settings default view are product-facing. Provider/search/live
readiness, raw runtime enums, and execution provenance remain available in
technical details, advanced diagnostics, docs, and tests.
R5-C1 keeps the same public contracts and further professionalizes business
copy in the default user surface: dimension summaries avoid route-wiring
explanations, step summaries avoid fixture/roster/transcript language, and
answer cards use "研判依据", "分析框架", "用户问题", and "流程记录" labels.
R7-I keeps the single user/assistant transcript and adds a public-safe
"研判思维链" disclosure below the assistant report. It is a structured process
summary derived from `workflow_snapshot_v2`, not hidden chain-of-thought or raw
runtime/provider/external output.

## Documentation Index

Use `docs/INDEX.md` as the navigation map. The short current entry set is:

- `README.md` - repository overview.
- `AGENTS.md` - workflow and safety policy.
- `docs/CURRENT_STATUS.md` - current status and next engineering theme.
- `docs/SYSTEM_MAP.md` - operational runtime topology.
- `docs/ARCHITECTURE_FIXED_DAG.md` - fixed DAG architecture and 27-agent catalog.
- `docs/CONTRACTS.md` - runtime/public contract payload boundaries.
- `docs/QUALITY.md` - safe quality commands and live/manual exclusions.
- `docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md` - strict sync operations runbook.

Historical phase records live under `docs/history/` and are indexed by
`docs/history/MANIFEST.json`.

## Safe Local Validation

Use the project conda environment when available. R6-B makes `mainline` the
default reset quality gate:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode unit
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode public-api
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode graph-smoke
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode frontend
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
```

`frontend` uses TypeScript no-emit, the frontend smoke test, and a temporary
repo-external Vite build `--outDir`; it must not write `apps/web/dist`.

Do not use successful tests as production readiness evidence.

The report-quality theme is closed by RQ3C production-mode live verification:
score `29/45`, `renderer_quality_gate.passed=true`, unsafe scan pass,
answer/section parity `1.0`, traceability `1.0`, and research-point
utilization `1.0`. Historical RQ2E preflight/audit work did not call
`/v1/agent/invoke`, make direct provider calls, perform process actions, read
env values, or retain raw service/provider responses.

For R8-2 selected compiler changes, use the narrow additive gate:

```powershell
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py src/react_agent/fixed_dag_executor.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py -q
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
git diff --check
```

These commands do not run provider live smoke, external live invoke, demo
stack, fusion-gate, frontend build, active graph selected execution, or live
selected routing.

R7-H restores `E:\muti-agent\external_agent_scaffold` from the tracked repo
mirror when that local distribution working copy is missing. Scaffold
validation can then run the restored repo-external package tests and ruff for
`E:\muti-agent\external_agent_scaffold`, the tracked repo mirror tests and ruff
for `examples/fixed_dag_external_agent_scaffold/`, then use the same
non-provider static and mainline commands. These checks do not call providers,
do not call external `/v1/agent/invoke`, and do not prove live external
readiness.

## Explicit Non-Claims

- No provider or live external service was verified by
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1/R6-B/R7-B/R7-C/R7-D/R7-E/R7-F/R7-G/R7-H/R7-I.
- No `external /v1/agent/invoke` call is part of
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1/R6-B/R7-B/R7-C/R7-D/R7-E/R7-F/R7-G/R7-H/R7-I validation.
- No demo stack startup is part of
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1/R6-B/R7-B/R7-C/R7-D/R7-E/R7-F/R7-G/R7-H/R7-I validation.
- No real business algorithms for individual agents are implemented in
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1.
- R5-B2 completes the frontend inspector UI rewrite only; it does not change
  backend executor semantics, provider readiness, external readiness, or
  business-agent correctness.
- R5-B2.6 completes Chinese visible-copy localization and visual copy polish
  only; it does not add a runtime locale switch, change public schemas, or
  change fixed DAG topology, roster, provider readiness, external readiness, or
  business-agent correctness.
- R5-C completes user-facing simplification and diagnostic disclosure cleanup
  only; it does not change public schemas, fixed DAG topology, roster, provider
  readiness, external readiness, or business-agent correctness.
- R5-C1 completes user-facing business copy professionalization only; it does
  not change public schemas, fixed DAG topology, roster, provider readiness,
  external readiness, or business-agent correctness.
- R6-B rebuilds the default reset mainline quality gate only. It does not
  restore fusion acceptance, and `fusion-gate` remains archived/manual.
- R7-B adds external developer handoff docs, payload mapping docs, readiness
  ladder docs, sample payload docs, and a sample-only local scaffold. It does
  not register the scaffold into the graph, modify runtime bindings, enable
  external candidates, live-verify services, or force one internal
  implementation mode for external agents.
- R7-C upgrades the original repo-external scaffold source package and syncs a
  tracked repo mirror. It does not turn the scaffold into active runtime code,
  enable `runtime_bindings`, register wrappers, or prove live service
  readiness.
- R7-D only tightens external handoff wording and consistency. It does not
  change active runtime behavior, enable bindings, bridge legacy wrappers, or
  prove live readiness.
- R7-E only expands developer-side AI coding instructions for adapting
  external agent projects. It does not change service runtime behavior,
  schemas, samples, active runtime, runtime bindings, or live readiness.
- R7-G patches the scaffold v2.3.1 contract semantics and validators. It does
  not change active runtime behavior, enable bindings, bridge legacy wrappers,
  call providers, call external live invoke, or prove live readiness.
- R7-H only repairs frontend fixture metadata, documentation wording, and the
  local scaffold distribution working copy. It does not change active runtime
  behavior, runtime bindings, fixed DAG topology, provider readiness, or
  external live readiness.
- R7-I only adds a frontend report-first "研判思维链" presentation disclosure.
  It does not change public schemas, backend runtime behavior, runtime
  bindings, fixed DAG topology, provider/search readiness, external invocation,
  demo stack acceptance, or business-agent correctness.
- R8-1 only adds selected routing contracts and validators. It does not change
  active graph behavior, default full DAG fallback, runtime bindings, fixed DAG
  roster, provider/search readiness, external invocation, LLM planning,
  deterministic selected compilation, RouteEval, or external adapter readiness.
- R8-2 only adds deterministic selected DAG compilation and selected plan
  validation helpers. It does not change active graph behavior, default full DAG
  fallback, runtime bindings, fixed DAG roster, public workflow fields,
  frontend behavior, provider/search readiness, external invocation, LLM
  planning, RouteEval, or external adapter readiness.
- R8-3 only adds provider-free route-intent planner/prompt/parser seams. It
  does not change active graph behavior, enable selected routing, call
  providers/search, invoke external services, or add RouteEval/external adapter
  readiness.
- R8-4 only adds provider-free RouteEval helpers, a small local gold fixture,
  and unit coverage. It does not change active graph behavior, enable selected
  routing, add a provider-backed LLM planner, call external services, or create
  a formal >=80% Route F1 acceptance gate.
- R8-5 only adds default-off selected routing graph integration. It does not
  change the default full DAG behavior, call LLMs/providers/search, invoke
  external services, modify runtime bindings, change frontend behavior, or
  implement real business agents/external adapter readiness.
- Provider live smoke, external invoke checks, Router-SFT, RARP/route-prior,
  demo stack acceptance, and browser screenshot visual capture remain outside
  the default reset mainline.
- R4-C isolates legacy registry/bootstrap but does not delete
  `config/agents/*.json` or live-verify external candidates.
- No production auth, rate limit, HTTPS, deployment, or observability claim is made here.
- SYNC-OPS-1R2 repairs the read-only P2S planner's recursive source coverage.
  It adds full source/support-root inventory, historical baseline parity,
  current production coverage ledgers, stage projection digests, and `/tmp`
  reconstruction checks. It still does not write prod, sandbox, owner-dev,
  approval, lock, backup, stage, activate, endpoint, process, or artifact-store
  state.
- SYNC-OPS-2A-R1 closes P2S source selection and full-scale temp rehearsal
  before real execution approval. It still does not write prod, sandbox,
  owner-dev, real artifact-store, approval, lock, backup, stage, activate,
  endpoint, process, or environment-value state.
- SYNC-OPS-2A-R2 turns the P2S plan into an executable contract and splits
  first real execution into stage/verify approval followed by a later
  activation/rollback approval. It still does not write prod, sandbox,
  owner-dev, real artifact-store, approval, lock, stage, activation, endpoint,
  process, or environment-value state.
- SYNC-OPS-2A-R3 splits durable artifact-store bootstrap into its own
  infrastructure approval. Until `/sdb/dlut/ops-artifacts/agent-sync` has valid
  store metadata, P2S plans remain blocked drafts and `p2s stage` rejects them
  before creating run artifacts.
- SYNC-OPS-2A-R4 makes artifact-store bootstrap rollback all-or-nothing with a
  per-path ownership ledger and POSIX archive entries. It still does not create
  the real artifact store.
- SYNC-OPS-2B0 correctly blocked the first real bootstrap before approval or
  write because the old environment snapshot no longer matched.
- SYNC-OPS-2A-R5 replaces volatile full-snapshot authorization with stable
  environment binding, execution constraints, and diagnostic observations. It
  still does not create prod, sandbox, owner-dev, artifact-store, approval,
  lock, backup, stage, activation, endpoint, process, or environment-value
  state.
- SYNC-OPS-2B0-R1 creates only the approved durable artifact-store directories
  and metadata. It does not execute P2S stage, activation, rollback, endpoint,
  process, prod, sandbox, owner-dev, or baseline-pointer writes.
- SYNC-OPS-2B1 creates and verifies only the approved versioned stage. It does
  not activate, roll back, archive the active sandbox, update the pointer, call
  endpoints, operate processes, or write prod/owner-dev.

## SYNC-OPS-5C-R1 Strict Cycle Envelope

- `agent_sync_first_nonzero_cycle_plan_v1` is a summary/readiness object, not
  the executable publish-and-rebase contract.
- The executable contract is `agent_sync_publish_and_rebase_cycle_v1` with
  `mode=strict_all_or_nothing`, projected prod after-state, and a precomputed
  P2S child.
- The strict envelope preserves the frozen experiment, change unit, S2P child,
  P2S child, projected prod-after digest, and the two action ids.
- Dry-run `agent-sync cycle publish-and-rebase` validates strict plan plus
  awaiting approval request and reports `ready_for_machine_approval`.
- This repair does not write prod, sandbox, pointer, owner-dev, processes,
  endpoints, or secrets.

## SYNC-OPS-5C-FINAL Strict Nonzero Execution

- Strict non-zero publish-and-rebase execution now uses the formal
  `agent_sync_publish_and_rebase_cycle_v1` plan with an exact
  `agent_sync_cycle_approval_bundle_v1`.
- The approved first cycle contains one S2P action and one P2S action for
  `risk_financial_fraud/tests/test_report_material.py`.
- The executor creates a durable single-file backup, performs an atomic
  production replace, runs the focused offline test, verifies the projected
  prod-after descriptor, stages the matching P2S update, activates the new
  sandbox baseline, updates the pointer, and records owner handoff evidence.
- Process restart, live endpoint calls, `/invoke`, provider calls, deletes,
  semantic merge, full-tree publish, and owner-dev writes remain outside this
  approval.
