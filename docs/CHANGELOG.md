# Changelog

Historical changelog entries before this reset branch are preserved by tag
`pre-fixed-dag-reset-20260604-1457`.

## 2026-07-04 — Fix frontend thought-chain progress bugs and backend adapter compatibility

### Changed

- **Progress counter (43/27 fix)**: `graph.py` L2/L3/L4 nodes were appending
  `l2_conclusions` agent IDs (e.g. `value_traditional_valuation`) to
  `completed_steps`, but dagSteps use `l2:`-prefixed IDs. Removed the spurious
  concatenation.
- **Dimension summaries**: `_dimension_group_summary()` replaces hardcoded
  "维度综合结果。" with dynamic text derived from stance, confidence, and
  contributing_agents count. Summary is frontend-safe (no "置信度" token that
  `isPublicSafeCopy` would block).
- **StepResults key lookup**: Frontend `ResearchThoughtChain.tsx` was looking
  up `stepResults` by `agentId` (value_traditional_valuation) but keys are
  step IDs (`l2:value_traditional_valuation`). Fixed to use `step.id`.
- **Dimension title**: `dimensionTitle()` had `group?.title ? "${fallback}" : fallback`
  which always returned fallback. Fixed to `group?.title ?? fallback`.
- **Detail summary dedup**: `detailSummary()` now deduplicates identical step
  summaries with `[...new Set(...)]` before joining, and falls back to phase
  detail text when all summaries are identical.
- **Dimension member limit removed**: All dimension agents shown (was
  `slice(0, 3)` limiting display to first 3).
- **Layer-based progress**: Progress bar changed from 27-step granularity to
  L1/L2/L3/L4 layer counting. Labels now read "研判流程 · 3/4 层处理中".
- **Dimension cards grid**: Single-column changed to `repeat(auto-fit,
  minmax(280px, 1fr))` — 4 cards display in 2 columns on wider screens.

### Report Layout And Rendering

- **Card width**: `42rem` → `48rem` for better Chinese text line length.
- **Typography**: Body text 15px, line-height 1.9, paragraph gap 12px.
- **`renderSections()`**: `AnswerCardModel.sections` (7 structured cards)
  now rendered below answer body. Previously data was sent but never used.
- **`renderEvidenceCards()`**: `evidenceCards` field rendered as blue-tinted
  card grid below citations (previously data was never shown).
- **Citations card grid**: Left-border list → multi-column card grid
  (`auto-fit, minmax(200px, 1fr)`).
- **Message padding**: `8px 24px 24px` → `20px 32px 32px` for breathing room.
- **Bold heading conversion**: Added `_convert_bold_headers_to_markdown_headings()`
  in external adapter to convert `**Section Title**:` at paragraph starts to
  `## heading` + new paragraph.

### Report Paragraph Formatting

- Added `_format_report_paragraphs()` in `public_mapping.py` that splits
  agent-generated report text at semantic markers (业务判断, 覆盖限制,
  风险提示, 关键证据, 业务指标, 驱动因素, 研究判断引用), converting them
  to `**bold**` headings separated by `\n\n`.
- Marker patterns auto-derived from `AGENT_TITLE_LABELS` for all 27 agent
  names plus sub-markers.
- Fallback: sentence-grouping into 3-sentence paragraphs when no markers found.
- Applied to both `answer` body and every `section.content` in
  `build_assistant_turn()`.

### Adapter And Policy Changes

- **`validate_external_compute_envelope`**: now accepts both
  `external_agent_compute_v0` and `external_agent_response_v0` schemas.
  Previously rejected `response_v0` from 3 risk agents, causing unnecessary
  adapter failures.
- **Non-L4 policy**: L2 concurrency 4→20, agent timeouts 20→30s.
- **Quality summary text**: Changed from "L2 完成 7/18" to "L2 已获取 14/18
  个 agent 数据（9 完全完成 + 5 降级参考）".
- **Report section wording**: "二层分析（L2） 完成 7/18" updated to reflect
  combined complete + partial counts consistently.

### Production Agent Service Repairs (outside git)

- `risk_identification` (port 10010): `AGENT_ID` from `risk_rule_reasoning`
  → `risk_identification` to match policy. Restarted.
- `market_ipo_investor_behavior` (port 10008): Added `/v1/agent/compute`
  endpoint. Agent identity fields aligned. Restarted.
- `market_capital_flow_chip` (port 10022): Service had stopped. Restarted.
- `market_composite` (port 10023): L3 service had stopped. Restarted.

### Tests

- 470 unit tests passed (0 new failures).
- TypeScript typecheck (`tsc --noEmit`) zero errors.
- Adapter unit tests: 53 passed.
- Contracts unit tests: 46 passed.
- Diff reduced to 4 files changed, 40 insertions(+), 7 deletions(-).
- All pre-existing failures (6 unit, 7 integration, 4 legacy) unchanged —
  not caused by this change.

### Not Done

- `market_ipo_investor_behavior` can only serve IPO-stage companies (data
  scope constraint — not a bug).
- 3 L2 agents remain undeployed: `market_fund_manager_behavior`,
  `macro_sentiment`, `macro_industry_hotspot`.
- No API contract version bump, no graph topology change, no catalog change,
  no runtime binding change.
- No provider or external `/v1/agent/invoke` path was modified.

### Changed

- **Loading UX**: Added animated pulse indicator and progress counter visible in
  collapsed answer card view, without requiring thought chain expansion. Shows
  current workflow stage name and step progress (e.g. "12/27 个步骤已完成").
- **Routing badges**: Answer card header now shows a badge indicating the
  routing mode: "全量分析" (default full DAG), "选择路由：value、risk"
  (explicit selected routing with dimension chips), or a fallback warning.
- **Fallback display**: When `selectedRoutingFallback=true`, answer card shows
  a prominent "选择路由未稳定完成，已回退到全量分析" warning banner.
- **Uncovered dimensions**: For selected routing reports, if any of the four
  dimensions (value/market/risk/macro) are not covered, they are shown as
  an "未覆盖维度" pill derived from `selectedDimensions`.
- **Copy text polish**: Updated composer placeholder, helper text, structured
  input label, sidebar navigation, empty states, and routing toggle copy to
  be more natural and professional (e.g. "结构化输入" → "补充信息",
  "显式选择路由" → "选择路由", "能力" → "智能体").
- **CSS refinements**: Added loading animation keyframes, routing badge color
  variants, dimension chip colors, uncovered scope styling, and progress
  counter layout. No backend schema changes.

### Tests

- Updated smoke test assertions to match revised copy text.
- Frontend typecheck (`tsc --noEmit`), build (`tsc && vite build`), and
  smoke test all pass.

### Not Done

- No backend public API schema change, no Router change, no agent service
  change, no runtime binding change, no catalog change.
- History conversation sidebar badges are not implemented (ChatSessionSummary
  has no `provenance` field; routing mode is only shown on message cards).
- No commit/push unless explicitly authorized.

## 2026-07-03 - Align source default chat model to deepseek-v4-flash

### Changed

- Replaced the stale `deepseek/deepseek-chat` fallback model id with
  `deepseek/deepseek-v4-flash` in the active runtime source defaults: the
  `Context.model` default and the L2/L3/L4 LLM-seam fallbacks in
  `default_agents.py`, `fixed_dag_llm_placeholders.py`,
  `fixed_dag_l3_explanation_synthesizer.py`,
  `fixed_dag_l4_decision_synthesizer.py`, and `fixed_dag_report_synthesizer.py`.
- Runtime already resolved the chat model from the `MODEL` env var (which was
  already `deepseek-v4-flash`); this only aligns the code-level fallback so
  env-less checkouts, tests, and CI no longer silently fall back to the retired
  model name.

### Tests

- Updated 7 test files to the new model id, including the router
  provider-prefix normalization assertions
  (`test_router_provider_factory.py`) and the graph
  router-model → provider payload coupling (`test_graph.py`). Affected-test run:
  123 passed. `--mode static` (ruff + mypy + codespell) passed.

### Not Done

- No `.env` change (env already set to `deepseek-v4-flash`), no runtime
  binding, catalog, or non-L4 policy change, no public schema/topology change,
  no provider call, no `/v1/agent/invoke`, no push.
- Also aligned: `scripts/phase25_regress_10turn.py` and
  `ops/data_pipeline/synthesize_questions.py` fallback model-ids.
- Left unchanged (outside scope): the archived
  `ops/regression/fusion/run_fusion_regression.py`, runbook/plan doc
  examples, and historical CHANGELOG entries.

## 2026-07-02 - Explicit selected-router reliability telemetry hardening

### Changed

- Hardened the real LLM dimension-router path for explicit
  `routing: {"mode": "selected"}` requests while keeping omitted/null routing
  on the full-DAG server default unless an operator separately enables
  `PUBLIC_SELECTED_ROUTING_DEFAULT=1`.
- Reduced the explicit router provider budget to a bounded 8-second,
  two-attempt path and classified timeout, connect, protocol, transport, HTTP
  status, response JSON, choice/message/content, and parser failures into
  public-safe error codes.
- Added public-safe router diagnostics for attempt count, elapsed
  milliseconds, output shape, retry mode, parse stage, and last error code.

### Tests

- Added graph/public mapping regressions for router success telemetry,
  transport-error fallback telemetry, route-planner timing projection, and
  public payload leakage checks.

### Not Done

- No default selected routing enablement, no external agent service change, no
  runtime binding/catalog/non-L4 policy change, no `/v1/agent/invoke`, no
  direct provider call by Codex, no env-value access, and no raw response
  retention.
- L4 `report_generator` latency remains a separate known production
  performance limitation for a future optimization goal.

## 2026-07-02 - Explicit value/risk selected-router stability

### Changed

- Hardened the real LLM dimension-router path for explicit
  `routing: {"mode": "selected"}` value/risk requests while keeping selected
  routing default-off unless the operator separately sets
  `PUBLIC_SELECTED_ROUTING_DEFAULT=1`.
- Added value/risk few-shot guidance for valuation/downside-risk prompts,
  canonicalized bounded provider aliases such as `valuation` and
  `downside_risk`, and allowed unrepairable invalid JSON or transient router
  timeout exceptions to consume the existing bounded retry path before
  fail-closed fallback.

### Tests

- Added parser/provider/graph regressions for value/risk alias JSON, malformed
  bounded provider dimension text, invalid-JSON-to-text retry, timeout retry,
  and bilingual value/risk router hints.

### Not Done

- No default selected routing enablement, no deterministic user-question rescue,
  no runtime binding, catalog, non-L4 policy, external service,
  `/v1/agent/invoke`, direct provider, env-value, raw-response, or push change.

## 2026-07-02 - Public selected-routing server default

### Changed

- Added the server-side `PUBLIC_SELECTED_ROUTING_DEFAULT=1` switch so omitted
  or null public `routing` can default to selected routing. When combined with
  `PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER=1`, default public messages use
  the real LLM dimension router before selected-DAG execution.
- Extended `/api/health` with `selectedRoutingDefault` and
  `defaultRoutingMode` so clients and operators can distinguish selected
  server default from full-DAG server default.
- Updated the Composer copy from "default off" to an explicit selected-routing
  toggle: when the toggle is off, the frontend omits `routing` and follows the
  server default advertised by health.

### Tests

- Added sync and stream public API coverage for omitted/null `routing` mapping
  to real LLM selected routing when the server default switch is enabled.
- Updated frontend smoke coverage for the explicit selected-routing copy.

### Not Done

- No request-level provider/model/key controls, no explicit public `full_dag`
  force-off mode, no `/v1/agent/invoke`, no runtime binding, catalog, non-L4
  policy, external service, direct provider, env-value, raw-response, or push
  change.

## 2026-07-02 - Provider-backed L4 report preservation

### Changed

- Preserved external `report_generator` output when its sanitized telemetry
  shows a provider/LLM call. The deterministic report-quality renderer now
  remains a fallback for weak non-provider L4 reports instead of overwriting a
  provider-backed LLM final report.
- Projected provider-backed external L4 report generation into fixed-DAG
  provenance through the existing public-safe `provider_invoked` boolean.

### Tests

- Added a focused executor regression proving provider-backed external L4
  reports keep their title, body, and sections instead of being replaced by the
  deterministic renderer.

### Not Done

- No selected-routing default change, no public schema change, no runtime
  binding, catalog, non-L4 policy, external service, `/v1/agent/invoke`, direct
  provider, env-value, raw-response, or push change.

## 2026-07-02 - Public report terminology localization

### Changed

- Added a Chinese-first public terminology projection to the deterministic
  report-quality renderer so route scope, DAG mode, L2/L3/L4 labels, decision
  enums, metric keys, and runtime boundary terms render as Chinese text with
  English contract terms in parentheses when needed.
- Tightened the LLM report synthesis prompt to require Chinese-first output and
  to avoid bare public-report exposure of internal terms such as selected
  routing, selected scope, `balanced_watch`, `risk_score`, `current_price`,
  deterministic enrichment, compute-only, no-invoke, no-provider, and
  no-raw-response.

### Tests

- Added focused renderer and LLM-report-prompt regressions for Chinese-first
  selected-routing scope wording, metric labels, enum labels, and runtime
  boundary terms.

### Not Done

- No router behavior, selected-routing default, public schema, runtime binding,
  catalog, non-L4 policy, external agent service, `/v1/agent/invoke`, direct
  provider, env-value, raw-response, or push change.

## 2026-07-02 - LLM router output-shape diagnostics and store freshness repair

### Changed

- Extended the narrow LLM-output text repair path to accept bounded Chinese or
  English dimension text and selected/unselected multi-line summaries from the
  real router provider. Negated or unselected lines are ignored, JSON-like
  malformed payloads and unsafe markers still fail closed, and the repair uses
  only provider output text, not deterministic inference from the user request.
- When the first real-router response has no parseable route shape, bounded
  retries now switch from strict JSON mode to a compact dimension-id prompt
  (`value`, `market`, `risk`, `macro`) so providers that intermittently ignore
  or fail JSON mode can still return a safe LLM-selected dimension list.
- Extended the live OpenAI-compatible dimension-router response handling to
  accept text content parts/lists as well as plain `message.content` strings.
  Extracted text still goes through the same bounded JSON extraction and
  fail-closed `route_intent_v1` normalizer.
- Added public-safe router output-shape reason codes for successful provider
  calls that return no usable route text, including no choices, missing message,
  empty content, content-part empties, finish-length truncation, refusal, and
  invalid JSON response bodies. These codes are projected through existing
  `providerRouterFallbackReason` / `providerRouterErrorCode` fields without
  retaining raw provider output.
- Added a narrow LLM-output text repair path for short provider responses that
  contain only allowed dimension names/cues and safe connector text. This lets
  concise responses such as `value and risk` or `选择维度：估值、下行风险`
  still drive the selected DAG while longer prose, malformed JSON-like payloads,
  forbidden markers, agent ids, endpoint/env/secret/raw fields, SQL, prompts,
  tracebacks, and chain-of-thought continue to fail closed.
- Repaired the public JSON thread store freshness behavior so invalid legacy
  thread entries are isolated during read, valid threads are preserved, and the
  repaired envelope is written back. A stale thread entry can no longer make
  `/api/threads` or new-thread creation unavailable for the whole daemon.

### Tests

- Added focused selected-routing coverage for content-part provider responses
  compiling `value/risk` selected DAGs.
- Added focused selected-routing coverage for Chinese provider dimension text
  and selected/unselected multi-line text so unselected dimensions do not become
  contributors.
- Added focused coverage for retrying not-parseable provider text with the compact
  dimension-id prompt and compiling the second safe LLM output.
- Added focused coverage for safe output-shape error codes when a provider
  returns empty/truncated content.
- Added focused public-store coverage proving invalid legacy thread entries are
  repaired without blocking valid threads.

### Not Done

- No selected-routing default-on behavior, no public provider/model/key
  controls, no unbounded retry, no runtime binding/catalog/non-L4 policy
  changes, no `/v1/agent/invoke`, no raw provider response retention, and no
  push.

## 2026-07-02 - LLM router JSON contract hardening

### Changed

- Hardened the live OpenAI-compatible dimension-router prompt so selected
  public requests ask for a single dimension-level `route_intent_v1` JSON
  object and explicitly avoid agent-level routing, runtime controls, endpoint
  material, prompts, SQL, env values, secrets, and provider payloads.
- Updated the real-router parser to tolerate common provider wrappers by
  extracting the first bounded JSON object before applying the existing
  fail-closed dimension normalizer.
- Increased the bounded single-call router-provider timeout from 8s to 20s for
  production selected-routing stability and classified `httpx` timeout
  exceptions as `router_provider_timeout`.
- Allowed two bounded router-provider retries when earlier responses have no
  usable public content or return transient non-2xx responses; the call cap is
  still three and retry does not retain raw responses, prompts, messages, or
  endpoint material.
- Made the retry omit OpenAI JSON-mode `response_format` while keeping the same
  strict JSON-only prompt, so providers that intermittently return empty JSON
  mode content can still produce extractable bounded JSON.

### Tests

- Added focused coverage for markdown/prose-wrapped router JSON compiling a
  selected DAG while unknown dimensions, agent-level selection, forbidden
  fields, low confidence, and missing JSON still fall back safely.
- Added focused coverage for `httpx` router-provider timeouts mapping to the
  public-safe timeout reason code.
- Added focused coverage for a missing first router-provider response retrying
  once and compiling the second valid response into a selected DAG.
- Asserted that the retry request drops `response_format` while preserving the
  same no-raw-retention selected-DAG safety path.

### Not Done

- No selected-routing default-on behavior, no provider/model/key public
  controls, no unbounded retry loop, no runtime binding/catalog/non-L4 policy
  changes, no `/v1/agent/invoke`, no raw provider response retention, and no
  push.

## 2026-07-01 - Public LLM selected-router production enablement

### Changed

- Added an explicit `llm_dimension_router_mode` context field so the existing
  LLM dimension-router seam can remain fake by default while supporting a real
  OpenAI-compatible router path under operator authorization.
- Wired the real router provider path to a bounded JSON-only chat-completions
  request and projected only public-safe `providerRouter*` provenance.
- Added public API health fields for selected-routing router mode and LLM
  router enablement; selected public requests use the real LLM router only when
  the daemon is started with `PUBLIC_SELECTED_ROUTING_ENABLE_LLM_ROUTER=1`.

### Tests

- Added focused coverage for real-router OpenAI-compatible request shaping,
  selected plan compilation, public API context mapping, and health contract
  freshness.

### Not Done

- No public provider/model/key controls, no selected-routing default-on
  behavior for omitted requests, no runtime binding/catalog/non-L4 policy
  changes, no `/v1/agent/invoke`, no raw provider response retention, and no
  push.

## 2026-07-01 - Production performance telemetry and freshness guard

### Changed

- Added public health freshness fields so a live daemon can expose the current
  public API contract version, selected-routing request support, compute
  registry size, process start time, uptime, and a source-version marker.
- Added a public-safe performance telemetry model under workflow provenance.
  The model records request/graph/compute timing, compute call count, bounded
  per-agent timing/status rows, and explicit instrumentation gaps for provider
  or database timing that services do not report.
- Extended the compute bridge and fixed-DAG executor to carry sanitized service
  telemetry when it is present and to keep raw response, endpoint, prompt, SQL,
  provider payload, and secret material out of public projection.

### Tests

- Added focused regressions for the health contract, public workflow telemetry
  projection, and external compute telemetry sanitizer.
- Revalidated the public API, public mapping, external compute bridge, and
  fixed-DAG executor focused suite.

### Not Done

- No runtime binding, catalog, non-L4 policy, selected-routing default,
  `/v1/agent/invoke`, direct provider, env-value, raw-response, external agent
  dev-directory, or push change.

## 2026-07-01 - Real-agent report bundle and renderer quality

### Changed

- Added route-aware report scope metadata to `report_input_bundle_v1` and
  `agent_evidence_bundle_v1`, including selected/unselected dimensions and
  dimension coverage summaries.
- Updated deterministic report enrichment so selected-routing reports render
  only selected dimensions as active analysis and list unselected dimensions as
  uncovered scope.
- Tightened risk-compliance wording: zero readable evidence remains a
  limitation and cannot be described as risk-reducing evidence.
- Extended the offline report-quality harness with selected-scope integrity,
  unselected-dimension overstatement, evidence-bundle completeness,
  zero-evidence compliance wording, and limitations-honesty checks.

### Tests

- Added focused renderer, harness, contract, graph, and public API regressions.
- Revalidated compute-enabled full DAG report E2E at `33/45` with renderer gate
  pass, unsafe scan pass, evidence-bundle completeness pass, and selected-scope
  integrity pass.
- Revalidated selected value/risk compute report E2E with selected dimensions
  `value,risk`, expanded agent count `15`, fallback `false`, and unselected
  dimension overstatement count `0`.

### Not Done

- No runtime binding, catalog, non-L4 policy, selected-routing default,
  `/v1/agent/invoke`, provider, env-value, raw-response, external agent dev
  directory, or push change.

## 2026-07-01 - Real-agent report-quality contributor semantics

### Changed

- Tightened L3 real-contributor semantics in both the external adapter and the
  deterministic reducer. Fallback, stand-in, no-evidence, `not_evaluated`, and
  zero-weight members no longer survive as report contributors or evidence
  refs; public-safe provenance records the dropped refs and degraded members.
- Added `l3_contributor_integrity_v1` to the offline report-quality harness and
  made L3 transparency depend on that integrity check before passing the
  `29/45` report-quality floor.
- Updated the macro placeholder services and market composite service in the
  prod agent directories so placeholder/fallback members are exposed as
  downgraded non-contributors rather than report-grade evidence.

### Tests

- Added focused adapter and deterministic reducer regressions for fallback and
  no-evidence contributor exclusion.
- Revalidated full DAG compute-enabled report E2E at `29/45` with
  `renderer_quality_gate.passed=true` and zero L3 contributor-integrity
  violations.
- Generated selected value/risk compute E2E trust artifacts with selected-plan,
  workflow, evidence-bundle, report, provenance, and unsafe-scan summaries.

### Not Done

- No runtime binding, catalog, non-L4 policy, selected-routing default,
  `/v1/agent/invoke`, provider, env-value, raw-response, external agent dev
  directory, or push change.

## 2026-07-01 - Real-agent compute E2E status closeout

### Changed

- Added macro-composite adapter fail-soft handling for declared members that do
  not qualify as real contributors. The adapter now records those members as
  `missing_or_degraded_members`, drops their evidence refs from the mapped
  macro result, and downgrades a complete macro payload to partial instead of
  returning `fixed_dag_external_adapter_failure_v1`.
- Kept the macro identity, member-roster, dimension-weight, date, unsafe-text,
  and no-`stance` gates strict; the change only mirrors the existing risk
  composite contributor-limitation behavior for bounded macro partial coverage.

### Tests

- Added a unit regression for macro declared non-contributors.
- Revalidated the service-layer repair with targeted six-agent smoke,
  all-agent `/v1/agent/compute` smoke, full DAG compute-enabled report E2E, and
  selected value/risk compute-enabled report E2E under the no-invoke/no-provider
  boundary.

### Not Done

- No runtime binding, catalog, non-L4 policy, selected-routing default, provider,
  `/v1/agent/invoke`, external provider, env-value, raw-response, or external
  agent dev-directory change.

## 2026-07-01 - Real-agent compute registry formalization closeout

### Changed

- Added the three repaired/manual compute services
  `market_fund_manager_behavior`, `macro_sentiment`, and
  `macro_industry_hotspot` to the explicit demo/manual `/v1/agent/compute`
  registry so all 26 external fixed-DAG service ids are visible for controlled
  compute verification.
- Formalized `market_fund_manager_behavior` ops registry metadata with port
  `8503`, `/v1/agent/compute`, and external agent id `fund_manager_behavior`;
  also recorded repaired service-local ids for compliance, sentiment, and macro
  placeholder services.
- Updated current status and quality docs to distinguish the older RQ3C
  `risk_compliance_review` limitation from the later service-side repair that
  mapped `26/26` external agents in direct all-agent compute smoke.

### Tests

- Added focused registry tests proving all 26 external service ids are covered
  by loopback compute-only demo entries.
- Added policy-boundary coverage showing
  `market_fund_manager_behavior`, `macro_sentiment`, and
  `macro_industry_hotspot` remain excluded from the non-L4 production default
  policy.

### Not Done

- No runtime binding, fixed-DAG catalog, non-L4 policy, graph default,
  `/v1/agent/invoke`, provider, endpoint call, process action, env-value access,
  raw response retention, prod/sandbox source write, or service restart change.

## 2026-07-01 - Frontend selected-routing boundary docs closeout

### Changed

- Documented the public selected-routing composer toggle and sync/stream request
  shape in `docs/FRONTEND_V2.md`.
- Recorded that omitted or null `routing` preserves the server default, while
  `routing: {"mode": "selected"}` is the only public selected-routing opt-in.
- Reaffirmed that the frontend does not expose public `full_dag`,
  provider-router, compute, invoke, model, env, runtime-binding, catalog, or
  non-L4 policy controls.

## 2026-07-01 - Public selected-routing request toggle

### Changed

- Added the default-off public HTTP/Web request toggle
  `routing: {"mode": "selected"}` for sync and streaming message sends.
- Mapped that request field only to per-call
  `Context(enable_selected_routing=True)`, leaving omitted/null `routing` on the
  existing server default path and avoiding a public `full_dag` force-off mode.
- Added a default-off frontend composer switch that omits `routing` while off
  and sends `{mode: "selected"}` while on.

### Tests

- Added public API sync/stream coverage for omitted, null, selected, and invalid
  routing payloads, including an endpoint-free selected-routing report path.
- Added public-runtime context helper coverage and frontend smoke assertions for
  the selected-routing toggle and request serialization.

### Not Done

- No selected-routing default-on behavior, provider-router public control,
  compute/invoke public control, endpoint call, provider call, runtime binding
  change, catalog change, non-L4 policy change, prod/sandbox write, process
  action, env-value access, or raw response retention change.

## 2026-06-30 - Router M2 sandbox validation isolation

### Changed

- Isolated the L4 external-compute default unit regression from the production
  non-L4 default path so sandbox mainline validation cannot inherit a bridge
  fake through first-import timing.

### Tests

- Preserved runtime defaults while making the affected unit tests' L4-only and
  invalid-plan fallback scopes explicit with non-L4 rollback contexts.

## 2026-06-30 - Sync cycle offline pytest environment isolation

### Changed

- Cleared inherited `PYTEST_ADDOPTS` for strict sync-cycle offline child pytest
  runs so parent quality-gate basetemp settings cannot invalidate the child
  repo-local smoke command.
- Added the sync-cycle implementation and focused test file to static ruff
  coverage.

### Tests

- Added a regression that simulates parent `PYTEST_ADDOPTS` while executing the
  one-file strict publish-and-rebase cycle.

## 2026-06-30 - P2S package lockfile source classification

### Changed

- Classified a bounded set of package-manager lockfiles, including `uv.lock`,
  as `package_metadata` so current P2S source selection no longer treats
  ordinary dependency lockfiles as unknown binary material.
- Kept the P2S validator strict: arbitrary `.lock` files and other unknown
  files remain blocked until explicitly classified.

### Tests

- Added source-policy and inventory regressions for accepted package lockfiles
  and a negative arbitrary `.lock` case.

## 2026-06-30 - Router M2 quality blocker resolution

### Changed

- Hardened the SYNC-OPS-5A-R5X readonly listener probe so sandbox-denied local
  socket creation fails closed as a missing-listener blocker instead of
  crashing the quality gate.
- Switched the frontend quality smoke step to `node --import tsx` from
  `apps/web`, preserving the same smoke assertions while avoiding the `tsx` CLI
  IPC server in restricted quality sandboxes.

### Tests

- Added focused regressions for fail-closed readonly listener probes, single
  preflight listener-probe reuse, and the no-IPC frontend smoke dispatch.

## 2026-06-30 - Router M2 default-off selected-routing E2E report closure

### Changed

- Closed the minimal default-off selected-routing graph E2E report path:
  explicit selected-routing context now has focused coverage from
  dimension-only `route_intent_v1` through `selected_fixed_dag_plan_v1`,
  selected executor orchestration, L4 `decision_synthesizer` /
  `report_generator`, `final_emit`, and public assistant/workflow mapping.
- Added additive public-safe selected-routing/provider-router provenance fields
  to `WorkflowProvenanceModel` and mapped them field-by-field only from
  sanitized `workflow_snapshot_v2.provenance`.
- Added an internal explicit `Context` override to public runtime preparation
  and invoke helpers so endpoint-free tests can exercise selected routing
  without public HTTP schema changes.
- Updated frontend workflow types, mock workflow provenance, and the technical
  provenance view to understand the additive safe fields.
- Reconciled `enable_llm_dimension_router` in Context/State compatibility
  metadata and expanded static quality targets to include router helper
  surfaces.

### Tests

- Added focused public mapping/runtime and graph assertions for selected report
  closure, selected public provenance, default false/empty provenance fields,
  fake-provider no-leak behavior, and explicit context propagation.

### Not Done

- No default selected-routing enablement, real provider call, endpoint call,
  `/v1/agent/invoke`, `/v1/agent/compute` test call, runtime binding change,
  catalog change, non-L4 policy change, external `route_planner` service,
  route-planner port assignment, production/sandbox write, process action,
  env-value access, or raw response retention change.

## 2026-06-28 - Router M1H LLM dimension-routing closeout

### Closed

- Closed Router M1 internal default-off LLM dimension routing after the M1G2
  task-type compatibility patch and M1G rerun stability matrix.
- Recorded that the persisted real-provider router path completed a dev-only
  five-case matrix with provider calls `5`, real LLM calls `5`, all calls
  `2xx`, parse_ok `5/5`, selected plan compiled `5/5`, selected agents accepted
  `false`, under-routing failures `0`, artifact whitelist pass, unsafe scan
  pass, and no raw response/hash, prompt/messages, env/base URL/key,
  traceback, or chain-of-thought retention.
- Recorded two non-blocking conservative over-routing warnings:
  `risk_compliance_focus` selected `value+risk`, and
  `market_short_term_focus` selected `value+market`.

### Not Done

- No runtime code change, test change, provider call, env-value access,
  endpoint call, process action, runtime binding change, agent catalog change,
  non-L4 policy change, external route-planner service, route-planner port
  assignment, `10028/8028` runtime implementation, `report_generator` `10026`
  change, selected-routing production enablement, external compute E2E, or
  report generation E2E.

## 2026-06-28 - Router M1G2 provider task-type compatibility

### Changed

- Changed the router-provider dimension draft from `task_type="single"` to
  `task_type="general"` so focused value-only and market-only dimension routes
  validate and compile as analysis routing rather than investment judgments.
- Preserved the fixed-DAG investment safeguard: `task_type="single"` and related
  investment task types still require the `risk` dimension, and provider
  `selected_agents` remain rejected in dimension mode.
- Added wrapper, parser, and graph regression coverage for focused provider
  drafts and the unchanged `single` risk requirement.

## 2026-06-28 - Router M1F7 strict provider route-intent message contract

### Changed

- Added a pure router-provider messages builder for future controlled
  OpenAI-compatible dry-runs. The builder produces in-memory chat messages that
  use the provider-compatible single user-message exact JSON echo layout. It
  drafts `route_intent_v1` locally from deterministic dimension hints, asks the
  provider to echo that JSON, and still relies on the parser/compiler as the
  authority. The contract allows only dimension-only `selected_dimensions`, no
  concrete agent ids, no legacy route modes, and no analysis/report prose or
  markdown around the JSON.
- Extended the router-provider request-contract metadata and artifact allowlist
  with safe route-intent message contract fields: contract version, schema name,
  strict-schema boolean, sanitized layout name, and allowed dimensions.
- Added focused unit coverage for the strict route-intent messages contract and
  for rejecting retained prompt/messages through the router-provider unsafe
  scan.

### Not Done

- No real provider call, env-value access, endpoint/base URL value retention,
  `load_chat_model` invocation, OpenAI/DeepSeek client creation, runtime binding
  change, route-planner port assignment, `10028/8028` runtime implementation,
  report-generator port change, process action, prompt/message retention, or raw
  provider response/hash retention change.

## 2026-06-28 - Router M1F5 provider endpoint path contract

### Changed

- Added a pure router-provider endpoint normalization helper for future
  OpenAI-compatible controlled dry-runs. The helper maps base paths ending in
  `/v1` to `/v1/chat/completions`, maps base paths without `/v1` to
  `/v1/chat/completions` under that base path, preserves already complete chat
  completions paths, and rejects unsupported URL shapes.
- Extended router-provider artifact allowlisting with safe booleans for
  chat-completions path normalization and whether a `/v1` path was added.
- Added focused unit coverage for missing `/v1`, existing `/v1`, complete
  endpoint passthrough, unsafe URL shape rejection, and artifact-safety
  metadata.

### Not Done

- No real provider call, env-value access, endpoint/base URL value retention,
  `load_chat_model` invocation, OpenAI/DeepSeek client creation, runtime
  binding change, route-planner port assignment, `10028/8028` runtime
  implementation, report-generator port change, process action, prompt/message
  retention, or raw provider response/hash retention change.

## 2026-06-28 - Router M1F3 provider compatibility contract

### Changed

- Added pure router-provider model normalization for controlled
  OpenAI-compatible dry-runs. Known project-style `provider/model` ids can now
  be converted to provider API model ids without reading env values, creating a
  client, or calling a provider.
- Added a safe router-provider request contract requiring JSON object response
  format for dimension-only `route_intent_v1` output, with no prompt/message,
  raw response, or raw response hash retention.
- Extended router-provider artifact allowlisting to cover model-normalization
  status, JSON response-format status, and the request contract version.
- Added focused unit coverage for model normalization, JSON request-contract
  metadata, and artifact/unsafe-scan safety.

### Not Done

- No real provider call, `load_chat_model` invocation, OpenAI/DeepSeek client
  creation, env-value access, runtime binding, agent catalog, non-L4 policy,
  external service directory, route-planner port assignment, `10028/8028`
  runtime implementation, `report_generator` port change, endpoint call,
  process action, prompt/message retention, or raw provider response/hash
  retention change.

## 2026-06-28 - Router M1F0 router-only provider preflight factory

### Changed

- Added `src/react_agent/router_provider.py` as a router-only provider
  factory/preflight safety wrapper for a future controlled real-provider
  single-call dry-run.
- Added fail-closed preflight policy for selected routing, LLM dimension-router
  enablement, explicit real-provider authorization, explicit env-value access
  authorization, provider-call authorization, call cap `1`, streaming `false`,
  retry `0`, timeout `<=8s`, max tokens `<=220`, artifact whitelist, no raw
  response retention, and no prompt/message retention.
- Added router-provider artifact allowlisting and unsafe scanning for raw
  responses, raw response hashes, prompts, messages, endpoint/base URL
  material, env values, API keys, secrets, tokens, tracebacks,
  chain-of-thought, `selected_agents`, `runtime_bindings`, and `dag_steps`.
- Added focused unit coverage for factory default-off behavior, preflight
  failure/pass-ready cases, no client creation, no `load_chat_model` usage, no
  env-value reads, no raw/hash retention, whitelist enforcement, and unsafe
  scan behavior.

### Not Done

- No real provider call, `load_chat_model` invocation, OpenAI/DeepSeek client
  creation, env-value access, runtime binding, agent catalog, non-L4 policy,
  external service directory, scaffold copy, route-planner port assignment,
  `10028/8028` runtime implementation, `10026/10027` migration,
  `/v1/agent/compute`, `/v1/agent/invoke`, `/health`, process action, or raw
  provider/LLM response/hash retention change.

## 2026-06-28 - Router M1D fake provider seam for dimension routing

### Changed

- Added `Context.enable_llm_dimension_router` /
  `ENABLE_LLM_DIMENSION_ROUTER=1` as a default-false fake-provider-only router
  provider flag gated behind selected routing. Selected routing alone still
  uses the M1A provider-free dimension path, and the provider flag alone keeps
  the full DAG when selected routing is disabled.
- Added an internal `route_planner` seam that accepts injected fake structured
  dimension-only `route_intent_v1` JSON, parses it immediately through the
  dimension parser, compiles a deterministic selected plan on valid output, and
  falls back to the full DAG on invalid or failed fake provider output.
- Added public-safe workflow provenance fields for fake provider-router
  metadata: enabled/invoked, mode, parse status, selected dimensions, fallback
  reason, and bounded error code.
- Added focused graph tests for default-off behavior, selected routing without
  provider, valid fake provider dimensions, selected-agent/unknown-dimension/
  forbidden-field/legacy/low-confidence/clarification/malformed JSON fallback,
  fake provider exception and timeout fallback, raw-output non-retention, and
  no real model factory invocation.

### Not Done

- No real provider call, `load_chat_model` live invocation, runtime binding,
  agent catalog, non-L4 policy, external service directory, scaffold copy,
  route-planner port assignment, `10028/8028` runtime implementation,
  `10026/10027` migration, `/v1/agent/compute`, `/v1/agent/invoke`, `/health`,
  process action, env-value access, or raw provider/LLM response retention
  change.

## 2026-06-27 - Router M1A default-off dimension route planning

### Changed

- Added an internal provider-free dimension router seam behind the existing
  default-off selected-routing flag. Planner output may select only `value`,
  `market`, `risk`, and `macro`; concrete agent ids are not accepted from the
  planner in dimension-only mode.
- Extended route-intent parsing and validation so invalid dimensions,
  low-confidence or clarification outputs, legacy route modes, runtime-binding
  fields, endpoint/env/secret/raw-response material, and agent-level selections
  fail soft to full-DAG fallback.
- Updated `compile_selected_fixed_dag_plan` so dimension-only intents expand
  deterministically from current `DIMENSION_GROUPS` and
  `DIMENSION_COMPOSITE_AGENT_IDS`, including required L1 evidence seams and
  L4 `decision_synthesizer` / `report_generator`.
- Added public-safe workflow provenance summary fields for selected routing:
  `selectedRoutingRequested`, `selectedRoutingFallback`, `fallbackReason`,
  `routeGranularity`, `selectedDimensions`, and `expandedAgentCount`.
- Added focused parser, prompt, compiler, graph, and public workflow tests for
  dimension-only selected routing and fallback behavior.

### Not Done

- No runtime binding, agent catalog, non-L4 policy, graph default behavior,
  external service directory, scaffold copy, route-planner port assignment,
  `10028/8028` runtime implementation, `10026/10027` migration,
  `/v1/agent/compute`, `/v1/agent/invoke`, provider, process, env-value, or raw
  response retention change.

## 2026-06-27 - RQ3C risk composite evidence reference cleanup

### Changed

- Updated the fixed-DAG external adapter so `risk_conclusion_v1` drops
  `risk_composite` evidence references that point to non-contributing risk
  members before final L3 validation.
- Preserved public-safe coverage metadata for dropped evidence refs and kept
  failed/non-real members out of `contributing_agents` instead of converting
  them into fake evidence.
- Added focused adapter coverage for the RQ3B live failure
  `evidence_ref_from_non_contributor` while preserving the prior
  `positive_weight_no_evidence_member` regression.

### Not Done

- No `risk_compliance_review` schema compatibility mapper, runtime binding,
  catalog, non-L4 policy, graph topology, public schema breaking, quality
  scoring threshold, `/v1/agent/invoke`, provider, process, env-value,
  service-source, or sandbox-demo acceptance change.

### Closeout

- RQ3C production-mode live verification reached `29/45` with
  `renderer_quality_gate.passed=true`, mapped `20/21` compute calls, and
  retained `risk_compliance_review` unsupported schema as the only adapter
  failure. This closes the report-quality theme at the minimum production-mode
  acceptance boundary.

## 2026-06-27 - RQ3B risk composite adapter coverage lift

### Changed

- Updated the fixed-DAG external adapter so `risk_conclusion_v1` can map a
  partial `risk_composite` when an upstream risk member has positive service
  weight but no public-safe business material. Such members are excluded from
  `contributing_agents` and retained as explicit coverage limitations in
  provenance instead of failing the whole L3 adapter mapping.
- Added focused adapter coverage for the live-like
  `positive_weight_no_evidence_member` case exposed by RQ3A.

### Not Done

- No runtime binding, catalog, graph topology, public schema breaking,
  quality-scoring threshold, non-L4 policy, `/v1/agent/invoke`, provider,
  process, env-value, service-source, or sandbox-demo acceptance change.
- `risk_compliance_review` remains represented honestly when its own adapter
  mapping fails; RQ3B does not convert failed compliance material into fake
  evidence.

## 2026-06-27 - RQ3A production coverage and projection lift

### Changed

- Expanded the source-controlled non-L4 production compute policy with
  optional, fail-soft coverage rows for `value_research_synthesis`,
  `market_stock_technical`, `sentiment_company_radar`,
  `risk_financial_fraud`, `risk_identification`,
  `risk_compliance_review`, `macro_commodity_pricing`, `market_composite`,
  and `risk_composite`.
- Updated deterministic report enrichment to use public-safe runtime status,
  distinguish `risk_compliance_review` not-called / adapter-failed / mapped
  states, remove production-visible demo wording, and project available
  `research_points` more fully into the report surface.
- Updated current authority docs to record that RQ2E live scored `27/45`
  because of production coverage/projection gaps, and that RQ3A acceptance must
  come from production-mode live evidence rather than sandbox demo output.

### Not Done

- No runtime binding, catalog, public schema, graph topology, quality scoring
  threshold, `/v1/agent/invoke`, provider, process, env-value, service-source,
  or sandbox-demo acceptance change.

## 2026-06-27 - RQ2E authority and manifest readiness notes

### Changed

- Added the current RQ2E authority entry and report-quality acceptance DoD:
  score `>=29/45`, `renderer_quality_gate.passed=true`, unsafe scan pass,
  `template_phrase_count<=8`, answer/section parity `>=0.90`, and traceability
  `>=0.85`.
- Documented the current compute-only boundary: L4 `external_compute_default`
  remains limited to `decision_synthesizer` and `report_generator`, and the
  source-controlled non-L4 production compute policy is separate from
  `runtime_bindings.json` with `enabled_by_default=true`.
- Clarified that compute evidence must not be recorded as invoke evidence and
  that RQ2E preflight/audit work does not call `/v1/agent/invoke`, make direct
  provider calls, perform process actions, read env values, or retain raw
  service/provider responses.

### Not Done

- No runtime code, public schema, graph topology, renderer/enrichment gate,
  quality scoring, runtime binding, catalog, non-L4 policy, service, endpoint,
  provider, process, env-value, prod owner-dev, or historical artifact mutation.

## 2026-06-27 - Documentation top-level history stub cleanup

### Changed

- Removed top-level `Historical Document Moved` stubs for archived phase
  records; historical evidence now resolves through `docs/history/README.md`
  and `docs/history/MANIFEST.json`.
- Updated maintained-doc quality targets and historical evidence references to
  use `docs/history/...` paths directly.

### Not Done

- No runtime behavior, public schema, graph topology, runtime binding, catalog,
  endpoint, provider, process, prod, sandbox, external service, or owner-dev
  change.

## 2026-06-27 - Report renderer enrichment gate

### Added

- Formalized the sandbox renderer experiment into dev as
  `react_agent.fixed_dag.report_quality_renderer`.
- Added a deterministic report enrichment gate in the fixed-DAG report stage:
  pending/template-style report results can be rebuilt from bounded
  `report_input_bundle` material, while high-quality external L4 reports remain
  primary.
- Added runtime and harness coverage for enrichment, no-overwrite guards,
  invalid/unsafe fallback, renderer quality gate metrics, and source-label
  leakage checks.

### Not Done

- No runtime binding, catalog, public schema, graph topology, L4 service,
  prompt, adapter, endpoint, provider, process, prod, sandbox, or owner-dev
  change.

## 2026-06-26 - Sandbox renderer runtime-gate followup

### Changed

- Polished the sandbox-only offline report renderer to keep core conclusions
  business-first and remove source-label leakage from the action summary.
- Added a pure renderer enrichment gate and a separate `renderer_quality_gate`
  to the offline report-quality harness while preserving the original pipeline
  score.
- Added focused tests for renderer gate true/false behavior, fixture rendering,
  source-label leakage, action implication, and threshold exits.

### Not Done

- No dev formalization, prod deployment, runtime binding change, catalog
  change, public contract change, endpoint call, provider call, process action,
  service modification, or default runtime behavior change.

## 2026-06-26 - Sandbox report renderer experiment

### Added

- Added sandbox-only offline `react_agent.fixed_dag.report_quality_renderer`
  for deterministic report-result enrichment from sanitized E2E artifacts.
- Added unit coverage for the pure renderer and artifact rewrite path.

### Not Done

- No dev formalization, prod deployment, runtime binding change, catalog
  change, public contract change, endpoint call, provider call, process action,
  service modification, or report-generation default behavior change.

## 2026-06-26 - Report quality artifact harness

### Added

- Added offline `scripts/quality/report_quality_audit.py` for sanitized
  fixed-DAG E2E report artifacts and compact report-quality fixtures.
- Added a public-safe baseline fixture and unit tests for report score,
  traceability, template-like wording, research-point utilization,
  answer/section parity, unsafe-scan behavior, and threshold exits.

### Not Done

- No report-generation behavior, prompt, adapter behavior, L4 service,
  runtime binding, catalog, public contract, graph topology, endpoint,
  provider, process, prod, sandbox, owner-dev, or artifact-store change.

## 2026-06-26 - System map post-closeout polish

### Changed

- Refreshed `docs/SYSTEM_MAP.md` heading and current-phase wording after the
  repository consolidation closeout.

### Not Done

- No source code, config, runtime binding, public contract, catalog, graph
  topology, endpoint, process, provider, prod, sandbox, owner-dev, or
  artifact-store change.

## 2026-06-26 - Repository authority and active-core consolidation closeout

### Changed

- Added `docs/REPOSITORY_CONSOLIDATION_CLOSEOUT.md` as the final closeout
  record for Repository Authority & Active-Core Consolidation.
- Recorded that documentation authority is consolidated, fixed-DAG active-core
  packages are split behind retained facades, and Context/State compatibility
  metadata is machine-checkable.
- Recorded the M4A dead-code decision: P4 count is `0`, deletion candidate
  count is `0`, and M4B deletion implementation is skipped.

### Not Done

- No source/runtime/config behavior change, code deletion, compatibility
  deletion, public contract change, catalog change, runtime binding change,
  graph topology change, endpoint call, process action, provider call, prod
  write, sandbox write, artifact-store write, or owner-dev write.

## 2026-06-26 - Context/State compatibility metadata isolation

### Changed

- Added `react_agent.compat.context_state` as a metadata-only helper for
  machine-checkable active, compat, legacy, and manual Context/State field
  groups.
- Added focused tests proving the Context dataclass surface, State/InputState
  TypedDict surface, result-pool reducers, and compatibility classifications
  remain stable.

### Not Done

- No Context/State field deletion, field rename, default change, reducer
  change, runtime shape change, public schema change, graph topology change,
  catalog change, runtime binding change, endpoint call, process action,
  provider call, prod write, sandbox write, artifact-store write, or owner-dev
  write.

## 2026-06-26 - Fixed-DAG executor runner boundary completion

### Changed

- Added `src/react_agent/fixed_dag/execution/runner.py` as the internal owner
  of `execute_fixed_dag_plan` and runner-local orchestration helpers.
- Preserved `react_agent.fixed_dag_executor` as the compatibility facade and
  public executor import path for graph, tests, and external callers.
- Added focused coverage proving the old facade delegates to the internal
  runner and that mapped L4 `report_generator` results suppress internal LLM
  report synthesis.

### Not Done

- No external adapter extraction, context/state compatibility isolation,
  compatibility deletion, public contract semantic change, catalog change,
  runtime binding change, endpoint call, process action, provider call, prod
  write, sandbox write, artifact-store write, or owner-dev write.

## 2026-06-26 - Fixed-DAG external bridge and runtime registry boundary split

### Changed

- Added the internal `src/react_agent/fixed_dag/external/` package for
  external compute constants, typed entries, demo registry metadata, request
  builders, loopback transport, and payload safety helpers.
- Added the internal `src/react_agent/fixed_dag/runtime/` package for runtime
  binding constants, typed metadata, validation, lookup, annotation, and L4
  review helpers.
- Preserved `react_agent.fixed_dag_external_compute_bridge` and
  `react_agent.fixed_dag_runtime_registry` as compatibility facades and public
  import paths for this consolidation phase.

### Not Done

- No executor runner extraction, external adapter extraction, context/state
  compatibility isolation, runtime binding/config/schema semantic change,
  endpoint call, process action, provider call, prod write, sandbox write,
  artifact-store write, or owner-dev write.

## 2026-06-26 - Fixed-DAG executor foundational extraction

### Changed

- Added the internal `src/react_agent/fixed_dag/execution/` package for
  execution constants, topology helpers, validation helpers, and step-result
  helpers.
- Preserved `react_agent.fixed_dag_executor` as the compatibility facade and
  public executor import path for this consolidation phase.
- Added focused facade/import-boundary coverage proving old/new helper
  equivalence and unchanged deterministic full DAG, selected DAG, workflow
  snapshot, and sync CLI help hashes.

### Not Done

- No external bridge extraction, runtime registry extraction, external adapter
  extraction, context/state compatibility isolation, public contract semantic
  change, catalog change, runtime binding change, endpoint call, process
  action, provider call, prod write, sandbox write, artifact-store write, or
  owner-dev write.

## 2026-06-26 - Fixed-DAG contracts foundational extraction

### Changed

- Added the internal `src/react_agent/fixed_dag/` package for foundational
  contract constants, types, labels, and public-safety helpers.
- Preserved `react_agent.fixed_dag_contracts` as the compatibility facade and
  public contract import path for this consolidation phase.
- Added focused facade/golden coverage proving old/new import equivalence and
  unchanged deterministic fixed-DAG plan, selected-plan, and workflow snapshot
  outputs.

### Not Done

- No executor extraction, external bridge extraction, runtime registry
  extraction, context/state compatibility isolation, public contract semantic
  change, catalog change, runtime binding change, endpoint call, process
  action, provider call, prod write, sandbox write, artifact-store write, or
  owner-dev write.

## 2026-06-26 - Repository documentation authority consolidation

### Changed

- Added `docs/CURRENT_STATUS.md` as the current status and next-theme entry.
- Moved historical phase records under `docs/history/` and added
  `docs/history/MANIFEST.json` to preserve original paths, content hashes, and
  artifact/backup/owner-reference classes.
- Reworked `README.md`, `docs/INDEX.md`, `docs/SYSTEM_MAP.md`,
  `docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md`, and `docs/QUALITY.md` so current
  authority is separated from historical evidence.
- Retained old historical paths as compatibility stubs for link stability and
  existing maintained-doc quality targets.

### Not Done

- No source/runtime/config behavior change, catalog change, runtime binding
  change, public contract change, endpoint call, process action, provider call,
  prod write, sandbox write, artifact-store write, or owner-dev write.

## 2026-06-25 - REPO-CONSOLIDATION-M1A quality baseline closure

### Fixed

- Restored deterministic mainline behavior for the SYNC-OPS-1R2
  materialization coverage test by replacing current-server P2S inventory reads
  with a hermetic temp fixture covering direct copy, sanitized derivative,
  metadata preservation, and shared-transaction coverage.
- Hardened P2S reconstruction so preserved sanitized derivatives and sandbox
  metadata bind exact source paths and fail closed on post-plan source drift,
  matching the existing copy-from-prod drift boundary.

### Not Done

- No runtime behavior change, sync contract change, production write, sandbox
  write, endpoint call, process action, provider call, or documentation
  migration.

## 2026-06-25 - SYNC-OPS-5C-FINAL strict nonzero execution

### Added

- Added formal strict non-zero execution support for
  `agent_sync_publish_and_rebase_cycle_v1` when an exact
  `agent_sync_cycle_approval_bundle_v1` is supplied.
- Added durable evidence for one-file S2P backup/apply/test, prod-after
  descriptor proof, first-cycle P2S stage/activation, final parity, experiment
  closeout, owner handoff, and lock release.
- Added focused coverage for strict one-file publish-and-rebase execution with
  exact action ids and no process/live/delete/provider/owner-dev capability.
- Closed cycle `cycle_strict_e7bc707d5b8b` with durable run
  `run_cycle_strict_cycle_strict_e7bc707d5b8b_20260625T135349Z`, final active
  baseline `first-cycle-p2s_52d75b56543f`, and pointer SHA
  `237f93bf0a90c0f8dcc4f2c4c240274b15af3bb2e980871d5a3929e40178e939`.

### Changed

- `agent-sync cycle publish-and-rebase --execute` now runs strict non-zero
  cycles through the formal cycle executor instead of rejecting every non-zero
  cycle after approval validation.

### Not Done

- No process restart, live endpoint call, `/invoke`, provider call, delete,
  owner-dev write, full-tree publish, or semantic merge.

## 2026-06-25 - SYNC-OPS-5C-R1 strict cycle envelope repair

### Added

- Added a deterministic strict-envelope builder that wraps the frozen first
  non-zero experiment, change unit, S2P child, projected prod-after descriptor,
  and P2S child in `agent_sync_publish_and_rebase_cycle_v1`.
- Added approval-request validation for `agent_sync_cycle_approval_request_v1`
  and publish-and-rebase dry-run support that reports
  `ready_for_machine_approval` without `--execute`.
- Added focused regressions for summary-plan rejection, strict child binding,
  request-versus-approval separation, child hash drift, and CLI dry-run.

### Changed

- Superseded the summary `agent_sync_first_nonzero_cycle_plan_v1` object as a
  non-executable cycle summary. The S2P/P2S child ids, hashes, action ids, and
  projected prod-after descriptor are unchanged.

### Not Done

- No machine approval, production write, sandbox write, pointer update,
  endpoint call, process action, owner-dev write, or cycle execution.

## 2026-06-25 - SYNC-OPS-5A-R7X cutover tree digest parity

### Fixed

- Hardened Full P2S Rebase V7 generation so recovered `risk_financial_fraud`
  stage actions are derived from the V7 source-loss file-action ledger instead
  of the legacy V4 compatibility shim.
- Hardened Full P2S Rebase V7 validation to reject placeholder
  `risk_financial_fraud/recovered/<n>` actions, non-SHA source hashes, missing
  recovered-action metadata, and stage-request action scopes that do not exactly
  match the materialization manifest.

### Added

- Added R7X physical tree descriptor contracts, classification manifest digest,
  directory mode authority, directory action ledger, action semantics binding,
  Source-Loss Recovery V7, V7 cutover request, downstream P2S/experiment/cycle
  V7 objects, and conditional approval chain V7.
- Added focused R7X tests for V6 fail-closed validation, physical digest path
  independence, classification digest separation, directory mode actions,
  exact 67-file rehearsal parity, V7 approval request separation, downstream
  chain blocking, and CLI rejection behavior.

### Changed

- Superseded Source-Loss V6 and downstream V6 objects because the clean
  projection physical digest did not match the exact 67-file materialization
  digest and directory modes were not explicit approval actions.

### Not Done

- No incumbent stop, canonical target modification, real fresh candidate
  materialization, recovered production start, P2S, active sandbox mutation,
  pointer write, owner-dev write, endpoint call, env-value access, machine
  approval, or first non-zero cycle execution.

## 2026-06-25 - SYNC-OPS-5A-R6X clean cutover candidate hardening

### Added

- Added R6X clean candidate projection contracts, post-start runtime artifact
  policy, Source-Loss Recovery V6, V6 cutover request, downstream P2S/
  experiment/cycle V6 objects, and conditional approval chain V6.
- Added focused R6X tests for V5 fail-closed validation, 67-action clean
  projection, file type/mode/executable metadata, 67-file temp materialization,
  offline validation non-mutation, post-start runtime policy, archive
  portability, and CLI rejection behavior.

### Changed

- Superseded Source-Loss V5 and downstream V5 objects because the fresh
  candidate expected descriptor included runtime/unknown `__pycache__` entries
  and the file actions did not bind complete metadata.

### Not Done

- No incumbent stop, canonical target modification, real fresh candidate
  materialization, recovered production start, P2S, active sandbox mutation,
  pointer write, owner-dev write, endpoint call, env-value access, machine
  approval, or first non-zero cycle execution.

## 2026-06-25 - SYNC-OPS-5A-R5X source-loss cutover contract

### Added

- Added R5X source-loss cutover contracts: full-tree descriptor, production
  launch authority, Source-Loss Recovery V5, cutover approval request V5, P2S
  V5, projected experiment/cycle V5, and conditional approval chain V5.
- Added `agent-sync source-loss` planning, validation, explanation, preflight,
  status, recovery, and approval-missing execute rejection commands.
- Added focused R5X tests for V4 supersession, dirty canary rejection, fresh
  candidate paths, production launch authority, exact action ids,
  roll-forward state machine simulation, downstream blocked chain, schema
  validation, and missing-approval CLI behavior.

### Changed

- Superseded Recovery V4/P2S V4/first-cycle V4 because cutover approval must
  bind complete tree descriptors, canonical/archive/fresh candidate paths,
  production launch authority, exact action ids, SIGTERM/no-SIGKILL, and
  roll-forward failure states.

### Not Done

- No incumbent stop, canonical target modification, real fresh candidate
  materialization, recovered production start, P2S, active sandbox mutation,
  pointer write, owner-dev write, endpoint call, env-value access, machine
  approval, or first non-zero cycle execution.

## 2026-06-25 - SYNC-OPS-5A-R4X real canary qualification

### Added

- Added R4X environment variable matrix, clean environment profile, incumbent
  versus canary equivalence, precutover canary plan, canary-only machine
  approval, Recovery V4, P2S V4, projected experiment/cycle V4, and
  conditional approval-chain contracts.
- Added focused R4X tests for environment contradiction rejection,
  environment parity, diagnostic body hashes, degradation blocking,
  canary-only permissions, P2S stage/activation separation, and the new
  `agent-sync risk-fraud freeze-source-loss-v4` CLI.
- Added process launcher stop semantics that require optional listener release
  proof without using SIGKILL.

### Changed

- Superseded the R3X broad compound request in favor of a closeout-bound
  approval chain. Cutover can now await approval only after a real canary
  closeout; P2S stage, P2S activation, experiment materialization, and first
  publish remain blocked behind later real closeouts.

### Not Done

- No incumbent stop, source-root cutover, recovered production start, active
  sandbox mutation, pointer write, owner-dev write, `/invoke`, provider call,
  env-value output, secret output, P2S stage/activate, or first non-zero cycle
  execution.

## 2026-06-25 - SYNC-OPS-5A-R3X approved launch authority

### Added

- Added source package provenance V1 contracts proving 67/67
  `risk_financial_fraud` files against the June 23 prod-to-sandbox manifests.
- Added `agent_sync_launch_authority_v1` and a bounded sync-ops supervised
  launcher contract with no shell, exact argv/cwd/executable, PID reuse
  protection, 0600 logs, and SIGTERM-only stop semantics.
- Added source-loss recovery V3, full P2S rebase V3, compound plan V3, and
  compound approval request V3 contracts.

### Changed

- Superseded R2X recovery, P2S, first-cycle, and compound plans because launch
  authority is now productized and must be rebound by hash.
- Promoted the final compound request to `awaiting_machine_approval` while
  keeping all real execution out of this phase.

### Not Done

- No real prod file modification, active sandbox mutation, pointer write,
  owner-dev write, endpoint call, process action, machine approval, or real
  cycle execution.

## 2026-06-24 - SYNC-OPS-5A-R2X source-loss recovery hardening

### Added

- Added irreversible source-loss recovery V2 contracts for the
  `risk_financial_fraud` deleted-source/live-process incident.
- Added full P2S rebase V2 contracts with concrete stage/candidate/archive
  paths and physical materialization manifests.
- Added R2X focused tests for old plan supersession, source-loss canary,
  launch-authority blocking, exact P2S manifests, candidate reselection, and
  compound approval requests.

### Changed

- Superseded the R1X recovery plan because it allowed in-place writes and
  empty-tree rollback semantics for a source-loss incident.
- Superseded the R1X P2S projection because it retained placeholder paths and
  lacked a physical materialization manifest.
- Requalified the first real change candidate to the existing market
  contract-test patch, while treating the wider market runtime bundle as outside
  the selected tests-only change unit.

### Not Done

- Launch authority remains unresolved for the live `risk_financial_fraud`
  process, so no executable recovery approval is created.
- No real prod file modification, active sandbox mutation, pointer write,
  owner-dev write, endpoint call, process action, machine approval, or real
  cycle execution.

## 2026-06-24 - SYNC-OPS-5A-R1X source authority final freeze

### Added

- Added source-authority and final-freeze documentation for
  `risk_financial_fraud`, including old repair supersession, prod source
  recovery, full-baseline P2S rebase, candidate requalification, and compound
  execution request boundaries.
- Added R1X planning contracts for risk-fraud prod source recovery, full
  P2S rebase projection, final compound execution plans, and compound approval
  requests.
- Added `agent-sync risk-fraud validate-old-repair` and `agent-sync risk-fraud
  freeze` read-only CLI entries.

### Changed

- The 5A 67-action baseline-only repair is now rejected as a side artifact, not
  an executable plan.
- `financial_data_service` first-candidate evidence is reclassified from
  docs/tests material to a superseded `B_protocol_wrapper` requiring process and
  live approval.

### Not Done

- No real prod file modification, active sandbox mutation, baseline pointer
  write, owner-dev write, endpoint call, process action, machine approval, or
  real cycle execution.

## 2026-06-24 - SYNC-OPS-5A first non-zero qualification

### Added

- Added first non-zero qualification documentation for baseline mapping,
  multi-transaction rehearsal, strict compensation, candidate selection, and
  5B entry.
- Added temp cycle helpers for two independent transactions, a shared member,
  and reverse-order compensation after a later transaction failure.

### Changed

- S2P validation now rejects normal Agents that have empty B/S/P inventory
  descriptors without an explicit registered-empty disposition.
- `cycle rehearse` now runs single-transaction, multi-transaction, and
  compensation rehearsals.
- Non-zero `cycle publish-and-rebase --execute` now reports the 5B approval
  boundary explicitly instead of relying on the no-op runner to reject it.

### Not Done

- No real non-zero prod write, process action, endpoint call, owner-dev write,
  active sandbox mutation, baseline pointer write, machine approval, or P2S
  repair execution.

## 2026-06-24 - SYNC-OPS-4X publish-and-rebase cycle

### Added

- Added typed digest descriptors, projected prod after-state schemas,
  publish-and-rebase cycle plans, cycle approval bundles, cycle run/recovery
  schemas, and experiment closeout schema registration.
- Added `sync_cycle.py` with cycle plan construction, approval-bundle
  validation, temp non-zero cycle rehearsal, real no-op cycle execution, archive
  policy validation, and recovery classification.
- Added `agent-sync cycle prepare/plan/validate/explain/rehearse/
  publish-and-rebase/status/recover/close`.
- Added `docs/SYNC_OPS_4X_PUBLISH_AND_REBASE_CYCLE.md`,
  `docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md`, and
  `docs/CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md`.

### Changed

- S2P mapping now records `risk_financial_fraud` as an explicit registered
  empty baseline/experiment source tree instead of a silent empty digest noop.
- `market_fund_manager_behavior` is now an explicit shared transaction member
  owned by the `market_composite` transaction.
- Cycle artifacts are minimized to manifests/evidence and reject raw workspace
  or source-tree archive entries.

### Not Done

- No real non-zero prod publish, active sandbox mutation, pointer write,
  owner-dev write, endpoint call, process action, `/v1/agent/invoke`, env-value
  access, or secret output.

## 2026-06-24 - SYNC-OPS-3X sandbox-to-prod automation

### Added

- Added executable S2P automation contracts for experiment manifests, B/S/P/D
  planning, S2P approvals, backup manifests, apply results, fake process/live
  gate results, recovery, owner handoff, and no-op run results.
- Added `sync_s2p.py` with experiment fork helpers, change-unit gated S2P
  planning support, no-op approval/run handling, temp historical replay,
  backup/apply/rollback primitives, fake process/live gates, and recovery
  classification.
- Added `agent-sync experiment fork/show/diff/close` and expanded `agent-sync
  s2p` to `plan/validate/explain/rehearse/apply/verify/smoke/rollback`.
- Added `docs/SYNC_OPS_3X_SANDBOX_TO_PROD_AUTOMATION.md` and ADRs 115-120.

### Changed

- S2P plans now use the current baseline pointer's immutable
  `versioned_baseline_path` as B, not stale registry baseline roots.
- S2P no-op plans preserve prod-only/runtime/backup/non-source and unchanged
  sandbox derivative rows without turning them into publish blockers.
- Default quality and CLI contracts now distinguish no-op rehearsal from a
  future non-zero publish.

### Not Done

- No real non-zero sandbox-to-prod publish.
- No prod file modification, active sandbox modification, owner-dev write,
  endpoint call, process action, `/v1/agent/invoke`, env-value access, or
  secret output.

## 2026-06-24 - SYNC-OPS-2B2X P2S activation, rollback, and closure

### Added

- Added `docs/SYNC_OPS_2B2X_P2S_ACTIVATION_ROLLBACK_CLOSEOUT.md`.
- Recorded final prod-to-sandbox automation topic closure and the
  `sync_ops_3x_sandbox_to_prod_automation` next topic.
- Added ADRs for activation/rollback/reactivation closure, separate
  post-rollback approval, and preserving immutable stage plus old active
  archive.

### Changed

- Updated reset docs to record the real activation cycle: first activation,
  controlled rollback proof, independent final reactivation, final active
  baseline `20260624T060045Z`, old active archive preservation, and no
  endpoint/process/prod/owner-dev/S2P scope.

### Not Done

- No production source modification.
- No owner-dev modification.
- No endpoint or process action.
- No S2P, publish-and-rebase, delete, or live validation.

## 2026-06-24 - SYNC-OPS-2B1 real P2S stage and verify

### Added

- Executed the exact stage-only P2S plan `p2s_cb655480f481` through the
  durable artifact store.
- Created the new versioned sandbox baseline stage at
  `/sdb/dlut/sandbox/prod-baselines/20260624T060045Z/fixed-dag-services`.
- Added `docs/SYNC_OPS_2B1_REAL_P2S_STAGE_VERIFY.md`.

### Changed

- Hardened stage compile validation so `py_compile` writes bytecode to a
  `/tmp` cache instead of leaving `__pycache__` files inside the versioned
  stage.

### Result

- Stage/verify completed under run `run_fbb3e73cd466` with 1582 actions, 1581
  physical writes, one shared noop, zero secret findings, zero hard compile
  failures, and matching projection digest
  `ca24a6ce521006131eca7d87aa2725783df2331d78f49859add6542f5afd8d8d`.
- Active sandbox and `PROD_BASELINE_POINTER.json` were unchanged.
- A new activation approval request is awaiting machine approval.

### Not Done

- No prod, active sandbox, owner-dev, baseline pointer, endpoint, process,
  activation, active rollback, env-value, or secret-output action was
  performed.

## 2026-06-24 - SYNC-OPS-2B0-R1 durable artifact-store bootstrap

### Added

- Executed the exact stable-binding artifact-store bootstrap for
  `/sdb/dlut/ops-artifacts/agent-sync`.
- Created the ten approved directories and one atomic `STORE_METADATA.json`
  file.
- Added `docs/SYNC_OPS_2B0_R1_DURABLE_ARTIFACT_STORE_BOOTSTRAP.md`.

### Result

- `STORE_METADATA.json` records the approved plan id/hash, environment binding
  SHA, approval id, bootstrap run id, and ownership ledger.
- The durable artifact store verified with 10/10 directories, zero unexpected
  paths, and zero secret findings.
- A new read-only P2S plan is stage-ready and a new stage-only approval request
  is awaiting machine approval.

### Not Done

- No prod, sandbox, owner-dev, P2S stage, P2S activation, baseline pointer,
  endpoint, process, provider, database, env-value, chown/chgrp, setuid/setgid,
  or secret-output action was performed.

## 2026-06-23 - SYNC-OPS-2A-R5 stable bootstrap environment binding

### Added

- Added `agent_sync_execution_environment_v2` with separate approval binding,
  execution constraints, and diagnostic observations.
- Added owner/group/other/ACL access-basis proof for artifact-store bootstrap
  environments.
- Added `agent-sync environment explain-binding` and
  `agent-sync environment validate`.
- Added `docs/SYNC_OPS_2A_R5_STABLE_ENVIRONMENT_BINDING.md` and ADRs
  106-109.

### Changed

- Bootstrap approval requests now bind `environment_binding_sha256` instead of
  exact volatile observations such as free bytes or unrelated supplementary
  groups.
- Bootstrap store metadata now records the approved
  `bootstrap_environment_binding_sha256` so later P2S plans can verify the
  durable store was initialized under the same stable authorization boundary.
- Free space is evaluated against `minimum_free_bytes` at execution time.
- Security-critical drift still fails closed for path state, root identity,
  uid, mode, device, inode, access basis, and relevant group membership.

### Not Done

- No real prod, sandbox, owner-dev, artifact-store, approval, lock, bootstrap,
  backup, stage, activation, endpoint, process, `.env`, provider, database, or
  secret-output action was performed.

## 2026-06-23 - SYNC-OPS-2B0 artifact-store bootstrap stale guard

### Added

- Added a bootstrap executor guard that rejects real bootstrap execution when
  the rebuilt environment snapshot SHA no longer matches the plan-bound SHA.
- Added single-final-replace metadata preparation so
  `STORE_METADATA.json` can include ownership ledger data without a second
  persistent metadata overwrite.
- Added `docs/SYNC_OPS_2B0_DURABLE_ARTIFACT_STORE_BOOTSTRAP.md`.

### Result

- The exact R4 bootstrap plan/request was not executed because the current
  environment snapshot differed from the approved snapshot.
- No machine approval was created, no real artifact-store directories were
  created, and no `STORE_METADATA.json` was written.

### Not Done

- No real prod, sandbox, owner-dev, artifact-store, approval, lock, bootstrap,
  backup, stage, activation, endpoint, process, `.env`, provider, database, or
  secret-output action was performed.

## 2026-06-23 - SYNC-OPS-2A-R4 bootstrap rollback atomicity

### Added

- Added bootstrap ownership ledger metadata so rollback can remove only paths
  created by the same bootstrap run.
- Added two-phase bootstrap rollback preflight with zero-mutation
  `noop_not_safe_to_remove` behavior for non-empty, foreign, or unknown store
  content.
- Added approval request/type separation: requests use `requested_action_ids`;
  machine approvals use `approved_action_ids` and `status=approved`.
- Added POSIX ZIP archive creation and validation coverage for portable
  artifact entries.
- Added `docs/SYNC_OPS_2A_R4_BOOTSTRAP_ROLLBACK_ATOMICITY.md` and ADRs
  101-104.

### Changed

- Bootstrap rollback now refuses the whole rollback before any deletion if a
  store contains later run/plan/approval/backup/lock/baseline/experiment/index
  content or unknown files.
- `noop_not_safe_to_remove` now means `mutation_count=0` with no removed files
  or directories.

### Not Done

- No real prod, sandbox, owner-dev, artifact-store, approval, lock, bootstrap,
  backup, stage, activation, endpoint, process, `.env`, provider, database, or
  secret-output action was performed.

## 2026-06-23 - SYNC-OPS-2A-R3 artifact-store bootstrap contract

### Added

- Added dedicated artifact-store bootstrap plan, environment, approval, and
  metadata schemas.
- Added bootstrap plan/validate/execute/verify/recover/rollback CLI commands.
- Added temp-only bootstrap, idempotency, rollback, recovery, and P2S
  pre-bootstrap guard tests.
- Added `docs/SYNC_OPS_2A_R3_ARTIFACT_STORE_BOOTSTRAP.md` and ADRs 097-100.

### Changed

- P2S stage no longer implicitly creates a missing artifact-store root.
- P2S plans generated before store metadata exists are blocked drafts, not
  executable stage plans.
- Artifact-store filesystem requirements are separated from sandbox activation
  filesystem requirements.

### Not Done

- No real prod, sandbox, owner-dev, artifact-store, approval, lock, backup,
  stage, activation, endpoint, process, `.env`, provider, database, or
  secret-output action was performed.

## 2026-06-23 - SYNC-OPS-2A-R2 executable P2S plan contract

### Added

- Added executable P2S plan contract metadata for artifact-store readiness,
  lock requirements, stage, verify, activation, rollback, and crash recovery.
- Added stage-only approval requests and activation approval templates.
- Added artifact-store read-only preflight and `agent-sync plan
  explain-execution`.
- Added a structured P2S summary source for plan, closeout, CLI, and terminal
  counts.
- Added `docs/SYNC_OPS_2A_R2_EXECUTABLE_PLAN_AND_STAGED_APPROVAL.md` and ADRs
  092-096.

### Changed

- P2S plans now reject read-only planner markers, rollback skeletons,
  future-phase activation rollback placeholders, broad stage+activate+rollback
  approval scope, and transaction/agent action drift.
- Stage and verify approval are independent from activation and rollback.
- Full-scale temp rehearsal proves stage-only approval cannot activate.

### Not Done

- No real prod, sandbox, owner-dev, artifact-store, approval, lock, stage,
  activation, rollback, endpoint, process, `.env`, provider, database, or
  secret-output action was performed.

## 2026-06-23 - SYNC-OPS-2A-R1 P2S source-policy closure

### Added

- Added role-based P2S source classification and a runtime asset manifest for
  explicit small fixture/static-asset exceptions.
- Added `agent-sync p2s source-audit` and temp-only `agent-sync p2s rehearse`
  commands.
- Added full-scale temp writer rehearsal coverage for the current actual P2S
  plan: stage, verify, activate, rollback, no-hardlink check, and recovery.
- Added `docs/SYNC_OPS_2A_R1_SOURCE_POLICY_AND_FULL_SCALE_REHEARSAL.md` and
  ADRs 072-076.

### Changed

- Tightened source selection so local editor/AI-tool metadata, hidden backups,
  generated artifacts/results/reports/outputs/runs, data assets, model assets,
  runtime noise, and sensitive files are excluded by default.
- Changed plan validation to reject `copy_from_prod` actions with
  `not_scanned`, sensitive, unknown, or non-materializable source categories.
- Updated sync policy docs/config to make source categories and manifest-only
  asset inclusion explicit.

### Not Done

- No real prod, sandbox, owner-dev, artifact-store, approval, lock, backup,
  stage, activation, endpoint, process, provider, database, env-value, or
  secret-output operation was performed.

## 2026-06-23 - SYNC-OPS-2A P2S writer dry-run hardening

### Added

- Added machine approval validation bound to exact plan SHA and environment
  snapshot SHA.
- Added non-sensitive environment snapshots, global plus transaction file
  locks, durable temp artifact-store helpers, and append-only recovery journals.
- Added P2S stage, verify, activate, rollback, and recovery primitives.
- Added validation profiles so runtime-required Python compile failures block
  activation while proven unreachable legacy files are diagnostic-only.
- Added temp-root end-to-end writer tests for stage/verify/activate/rollback,
  lock conflicts, approval denial, artifact integrity, hard-link prevention,
  and recovery state classification.

### Changed

- Current P2S plans now use the 2A writer-contract tool version and approval
  requirements for stage, activate, rollback, locks, artifacts, and validation
  profiles.
- The SYNC-OPS-1R2 plan/request is superseded because it predates the writer
  contract and environment binding.

### Not Done

- No real prod, sandbox, owner-dev, artifact-store, approval, lock, backup,
  stage, activate, rollback, endpoint, process, `.env`, provider, model/data
  bulk-copy, or secret-output action was performed.

## 2026-06-23 - SYNC-OPS-1R2 recursive P2S coverage repair

### Changed

- Repaired source inventory to recurse through registered source and support
  roots while preserving logical-root relative paths.
- Added source-subroot, stage-prefix, and source-unit metadata to the static
  Agent service registry.
- Added P2S historical baseline parity and current production coverage ledgers
  so files cannot silently disappear from plans.
- Added stage projection digests and temp-only `/tmp` reconstruction checks for
  planned P2S materialization.
- Added the read-only `agent-sync p2s coverage` CLI command.

### Validated

- The three previously misclassified no-source agents now have nonzero
  recursive safe source counts.
- Current P2S plan validation includes projection digest and coverage checks.
- Ops tests cover recursive traversal, support-root relative paths, parity,
  coverage, temp reconstruction, and unsupported write commands.

### Not Done

- No production, sandbox, owner-dev, artifact-store, approval, lock, backup,
  stage, activate, rollback, endpoint, process, `.env`, model/data bulk copy,
  or secret-output action was performed.

## 2026-06-23 - SYNC-OPS-1R P2S write-safety repair

### Changed

- Hardened P2S plan generation so observed diff, future versioned-stage
  materialization, and activation preconditions are separate plan sections.
- Added backup/runtime-noise filename exclusion for P2S inventory and planning.
- Modeled sanitized sandbox derivatives as `preserve_sanitized_derivative`
  actions with redacted structural fingerprints, not raw production replace
  actions.
- Preserved `SANDBOX_SECRET_REQUIREMENTS.md` as sandbox-generated metadata,
  not as production source.
- Added explicit per-Agent P2S dispositions, stage-root checks, target-drift
  fields, shared-root dedupe checks, and POSIX archive-entry validation.

### Validated

- The legacy SYNC-OPS-1 current P2S plan is rejected by the new validator with
  bounded reasons.
- The repaired current P2S plan has no backup actions, no empty copy source
  hashes, no active sandbox file targets, and complete 26-Agent dispositions.
- Sync ops unit and integration tests cover P2S safety regression cases,
  filesystem backup exclusion, schema validation, CLI unsupported-write
  behavior, and archive path normalization.

### Not Done

- No P2S stage/activate/rollback, S2P apply, lock, approval, backup, endpoint
  smoke, process action, artifact-store write, production write, sandbox write,
  owner-dev write, `.env` value access, or secret output was performed.

## 2026-06-23 - SYNC-OPS-1 read-only bidirectional sync planner

### Changed

- Added `config/ops/agent_service_registry.json`,
  `config/ops/agent_sync_policy.json`, Draft 2020-12 schemas, and protocol
  examples for external-agent sync planning.
- Added `src/react_agent/ops/` and `scripts/ops/agent_syncctl.py` for read-only
  inventory, baseline inspection, experiment validation, B/S/P/D diffing, and
  immutable P2S/S2P/cycle plan generation.
- Added docs and ADRs for immutable hash-bound plans, static/runtime registry
  separation, immutable active baselines, deferred publish-and-rebase, and
  non-publishable sanitized derivatives.

### Validated

- Real `jsonschema.Draft202012Validator` validates all sync schemas and
  examples.
- Canonical hash vectors, registry invariants, filesystem safety, inventory,
  diff, plan generation, and CLI unsupported-write behavior are covered by
  tests.
- The current environment rehearsal parses the active baseline pointer,
  generates a read-only P2S plan, blocks active-baseline S2P, and emits a
  deferred cycle plan.

### Not Done

- No production, sandbox, owner-dev, baseline pointer, artifact-store, lock,
  backup, process, endpoint, provider, database, or smoke action was performed.
- No P2S stage/activate, S2P apply/smoke, rollback, or lock acquisition command
  is available in SYNC-OPS-1.

## 2026-06-23 - P2S-CLOSE-R1 sensitive source closure and sandbox switch

### Changed

- Resolved the two P2S-BASELINE-X sensitive-source blockers without modifying
  production or owner-dev repositories.
- Created sandbox-only sanitized derivatives for runtime-required
  credential-bearing source in `value_research_synthesis` and
  `macro_index_valuation`.
- Safely omitted one unreachable legacy `financial_data_service` test file that
  contained token-like literal test material.
- Switched `/sdb/dlut/sandbox/r8-13a/services/prod` to the refreshed 26-agent
  production-derived baseline and preserved the previous sandbox tree at
  `/sdb/dlut/sandbox/r8-13a/services/prod-pre-p2s-20260623T060926Z`.
- Added the active baseline pointer at
  `/sdb/dlut/sandbox/r8-13a/services/PROD_BASELINE_POINTER.json`.

### Validated

- Covered all 26 formal external agents with no empty blocked roots.
- Verified exact SHA equality for exact-copied files and explicit manifests for
  sanitized derivatives.
- Ran credential-oriented source scan, JSON parse checks, symlink/runtime-noise
  checks, and staged Python py-compile using repo-external pycache.
- Verified the active fixed sandbox tree equals the versioned baseline content.

### Not Done

- Did not modify production files, owner-dev repositories, runtime bindings, or
  service processes.
- Did not call endpoints, read `.env` values, read `/proc/*/environ`, copy raw
  logs, copy secrets, or bulk-copy model/data assets.

## 2026-06-23 - P2S-BASELINE-X external-agent sandbox baseline refresh

### Changed

- Added `docs/PROD_TO_SANDBOX_AGENT_BASELINE_REFRESH.md`.
- Recorded a production-to-sandbox external-agent source-bearing baseline
  refresh after the completed backfill and runtime release cycle.
- Archived the old external-agent sandbox inventory and sandbox-only patches
  under `/sdb/dlut/sandbox/backups/p2s_pre_refresh_20260623T050419Z`.
- Staged a new production-derived 26-agent baseline under
  `/sdb/dlut/sandbox/prod-baselines/20260623T050419Z/fixed-dag-services`.
- Created a dev-HEAD based main-system sandbox baseline instead of copying the
  main-system production runtime copy.

### Validated

- Covered all 26 formal external agents.
- Verified SHA manifests for the sanitized artifact directory.
- Verified source hash equality for unblocked staged files.
- Compiled 815 staged Python files using repo-external pycache.
- Preserved old sandbox experiment patches without applying them to the new
  baseline.

### Not Done

- Did not switch `/sdb/dlut/sandbox/r8-13a/services/prod` because
  `value_research_synthesis` and `macro_index_valuation` contain
  high-confidence credential-like inline production source files that must not
  be copied.
- Did not modify production files, owner-dev repositories, runtime bindings, or
  service processes.
- Did not call endpoints, read `.env` values, read `/proc/*/environ`, copy raw
  logs, or bulk-copy model/data assets.

## 2026-06-23 - POST-BF-B2X non-L4 production runtime activation

### Changed

- Added `config/fixed_dag/non_l4_external_compute_policy.json` as the
  source-controlled production policy for the initial non-L4 `/compute`
  default set.
- Added `src/react_agent/fixed_dag_non_l4_runtime_registry.py` to validate the
  policy, activation artifact hash, exact required 9 ids, optional macro-only
  set, loopback compute endpoints, and excluded-agent boundary.
- Added `src/react_agent/fixed_dag_production_external_compute.py` for
  stage-bounded production non-L4 orchestration, deterministic result ordering,
  fail-soft fallback, and private provenance.
- Added `Context.disable_non_l4_external_compute_default` for rollback without
  disabling L4 `external_compute_default`.
- Updated the fixed-DAG executor so demo mode suppresses production non-L4
  calls, production non-L4 L2 overlays run before deterministic L3, production
  L3 overlays consume the current-run L2 outputs, and L4 default remains
  unchanged.
- Added `docs/POST_BF_B2X_NON_L4_RUNTIME_ACTIVATION_AND_RELEASE.md`.

### Validated

- Backfill remains `31/31`.
- `runtime_bindings.json` remains unchanged and still enables only the two L4
  compute-default rows.
- Development required canary mapped 9/9 production non-L4 required agents and
  mapped both L4 compute-default agents.
- Optional `macro_composite` canary passed twice and is enabled as degraded
  optional production non-L4 L3.
- Final development probe mapped 10/10 production non-L4 agents and 2/2 L4
  agents with demo disabled, provider false, and `external_invoked=false`.

### Not Done

- No `/v1/agent/invoke`, provider call, runtime-binding edit, live flag,
  demo-bridge production enablement, database write/migration, owner-dev repo
  write, or model/scoring/feature/training/fusion change was made.

## 2026-06-22 - POST-BF-B1X production readiness foundation

### Changed

- Added `docs/POST_BF_B1X_PRODUCTION_READINESS_FOUNDATION.md`.
- Added bounded readiness metadata to production entity/sentiment health
  wrappers without changing the primary `external_agent_health_v0` contract.
- Aligned `sentiment_company_radar` fixed-DAG `stock_sentiment` wrapper
  requests to the current core `sentiments` subtask while preserving
  market-only routing.
- Added bounded private timing and process-local immutable resource reuse for
  `value_traditional_valuation` compute.
- Recorded remaining formal L2 semantic blockers and a non-L4 activation
  candidate set for a future orchestration phase.

### Validated

- Backfill remains `31/31`.
- Default product external runtime remains L4-only.
- Entity and sentiment health/compute mapped through the current adapter as
  degraded/partial with explicit not-default-ready readiness state.
- Traditional valuation warm-up plus five serial 20-second samples passed;
  all five mapped through the adapter.
- The controlled default-off demo regression trace called and mapped 21/21
  agents, mapped both L4 compute-default agents, and passed PublicTurn plus
  unsafe-scan checks.

### Not Done

- No `/v1/agent/invoke`, provider call, runtime-binding change, live flag,
  default non-L4 activation, database write/migration, owner-dev repo write,
  or model/scoring/feature/training/fusion change was made.

## 2026-06-22 - BF-CLOSE-R1 backfill completion trace revalidation

### Changed

- Updated backfill closure docs to separate `backfill_scope_status` from
  `integrated_trace_status`.
- Recorded BF-CLOSE-R1 correction artifacts under
  `/tmp/lma-backfill-closure-revalidation-20260622T143215Z`.

### Validated

- BF-COMPLETE-X artifact SHA verification passed.
- The final sandbox-to-prod ledger remains 31/31 complete with zero unresolved
  units.
- `value_traditional_valuation` passed a single 20-second compute diagnostic
  using the current bridge-built request; the 60-second diagnostic was not
  needed.
- The final 21-agent trace called 21, mapped 21, failed 0, mapped both L1
  external bundles and both L4 compute-default agents, and passed PublicTurn
  plus unsafe-scan checks.

### Not Done

- No service code, runtime source, runtime binding, live flag, provider path,
  invoke path, owner-dev repo, model, scoring, feature, training, data-source,
  or fusion algorithm was changed.

## 2026-06-22 - BF-COMPLETE-X sandbox-to-prod backfill completion wave

### Changed

- Added the production `entity_relation_extractor` wrapper package for
  `entity_relation_bundle_v1` on port `10017`.
- Completed the production `sentiment_company_radar` wrapper import closure on
  port `10020` and kept it market-only.
- Corrected the default-off demo bridge external id for
  `sentiment_company_radar` to `company_radar_agent`.
- Added `docs/FULL_SANDBOX_PROD_BACKFILL_CLOSURE.md`.

### Validated

- Service py-compile and controlled health/compute/adapter checks passed for
  the two backfilled units with sanitized artifacts.
- The final ledger counts 31/31 current-relevant sandbox-to-prod change units
  as complete.
- The final controlled trace passed report input/result validation, L4 mapping,
  PublicTurn validation, and pre-scrub unsafe scan.

### Not Done

- BF-COMPLETE-X itself ended with `backfill_completion_validation_failed`
  because the final controlled trace timed out on existing
  `value_traditional_valuation` and therefore mapped 20/21 demo agents. That
  was later revalidated and closed by BF-CLOSE-R1.
- No `/v1/agent/invoke`, provider call, runtime-binding change, live flag,
  owner-dev repo write, or model/scoring/feature/training/fusion change was
  made.

## 2026-06-22 - CS1-C3R remaining evidence and durability recovery

### Changed

- Added a phase artifact integrity helper and tests so closeout artifacts are
  finalized before relative-path SHA256 manifests are generated and verified.
- Hardened L3 real-contributor semantics in the external adapter and report
  projection: pending, error, zero-confidence, or no-evidence members must not
  carry positive weight, enter `contributing_agents`, or emit evidence refs.
- Fixed the maintained trace runner so L3 member summaries are extracted from
  `provenance.member_weight_summary` instead of a nonexistent top-level
  `members` field.
- Patched the production `market_composite` wrapper/test so pending
  `sentiment_company_radar` and `market_fund_manager_behavior` slots retain
  formal coverage with `weight=0` and no evidence contribution.
- Copied portable owner handoff patches into the CS1-C3R artifact root.
- Added `docs/CS1_C3R_REMAINING_EVIDENCE_AND_DURABILITY_RECOVERY.md`.

### Validated

- Focused main-system tests for adapter, contracts, trace runner, and artifact
  integrity passed.
- `market_composite` focused service tests passed, then controlled health and
  compute smoke mapped through the main-system adapter.
- The final controlled trace called and mapped `19` demo compute agents and
  both L4 compute-default agents; L3 summaries are nonempty for all four
  dimensions.
- PublicTurn validation passed and unsafe scan before scrub was empty.

### Not Done

- No external agent invoke endpoint was called.
- No provider was called.
- No runtime binding, live flag, invoke-default flag, owner-dev repo, model,
  scoring, feature, training, data-source, or fusion algorithm was changed.
- `entity_relation_extractor`, `sentiment_company_radar`, and
  `market_fund_manager_behavior` remain explicit owner/source blockers.

## 2026-06-22 - CS1-C3X source durability and macro contract closure

### Changed

- Added macro L3 member fail-closed validation in the external adapter:
  `members` must be unique formal macro L2 ids, and pending/partial/error
  formal members cannot carry positive weight.
- Patched the production `macro_composite` wrapper so fixed-DAG responses
  project exactly five formal macro slots and no service-local stand-in member
  is emitted as public formal evidence.
- Closed `market_capital_flow_chip` service-local contract drift by aligning
  local schema/tests with canonical `dimension=market`.
- Generated reviewable owner-dev handoff patches for production wrapper/test
  drift and recorded source durability status in sanitized artifacts.
- Added `docs/CS1_C3X_SOURCE_DURABILITY_AND_REMAINING_EVIDENCE.md`.

### Validated

- `macro_composite` health, compute, and adapter mapping passed after a scoped
  restart of port `10024`.
- The final default-off trace called and mapped `19` demo compute agents and
  mapped both L4 compute-default agents.
- Macro members in report input are now the canonical five-member packet:
  `macro_analysis`, `macro_commodity_pricing`, `macro_index_valuation`,
  `macro_sentiment`, and `macro_industry_hotspot`.
- PublicTurn validation passed and the pre-scrub unsafe scan was empty.

### Not Done

- No external agent invoke endpoint was called.
- No provider was called.
- No runtime binding, live flag, invoke-default flag, model, scoring, feature,
  training, data-source, or fusion algorithm was changed.
- `entity_relation_extractor`, `sentiment_company_radar`, and
  `market_fund_manager_behavior` remain explicit owner/source/listener
  blockers.

## 2026-06-22 - CS1-C2X temporal market public closure

### Changed

- Projected requested `as_of` into top-level, context, and options aliases for
  external compute requests so migrated production services consume the same
  historical boundary.
- Removed a literal external invoke endpoint string from L4 workflow
  provenance limitations; the non-claim remains present without an unsafe
  endpoint marker.
- Patched production wrapper/protocol files for four temporal-rejected services:
  `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, and `risk_crash`.
- Added the production compute route wrapper for
  `market_ipo_investor_behavior`.
- Restored production listeners for `market_capital_flow_chip` and
  `market_composite`.
- Added `docs/CS1_C2X_TEMPORAL_MARKET_PUBLIC_CLOSURE.md` and ADR entries for
  public-turn pre-scrub safety and real request-as-of data-window compliance.

### Validated

- Controlled health, compute, and adapter mapping passed for the six changed
  service wrappers and the two recovered market services; `market_composite`
  mapped as `partial` because fund-manager and sentiment members remain absent.
- New full logical DAG trace called and mapped `19` default-off demo compute
  services and mapped both L4 compute-default services.
- Temporal rejected agents are now `[]` for the 2024-12-31 trace.
- PublicTurn validation passed and the original public object passed unsafe
  scan before artifact scrub.

### Not Done

- No external agent invoke endpoint was called.
- No provider was called.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No model, scoring, threshold, feature, training, data-source, dependency, or
  fusion algorithm was changed.
- `market_fund_manager_behavior` and `sentiment_company_radar` remain explicit
  blockers.

## 2026-06-22 - CS1-C1X accelerated bulk readiness convergence

### Changed

- Added a main-system health identity validator with canonical and explicit
  compatibility profiles in `fixed_dag_external_health.py`.
- Added request-`as_of` temporal fail-closed checks to the external compute
  bridge so future-dated external outputs cannot enter fixed-DAG state for a
  historical request.
- Patched production wrapper files for `market_stock_technical`,
  `macro_analysis`, `market_ipo_investor_behavior`, and `value_composite`.
- Recovered production listeners for L4 compute-only services
  `decision_synthesizer` and `report_generator`.
- Added `docs/CS1_C1X_ACCELERATED_BULK_REMEDIATION.md` and ADR entries for
  health identity migration profiles and request-as-of temporal integrity.

### Validated

- Focused main-system tests passed: `166 passed`.
- Service-local focused tests passed for the four patched production services.
- Controlled health re-audit produced canonical pass for
  `market_ipo_investor_behavior`, `value_composite`, `market_stock_technical`,
  `macro_analysis`, `decision_synthesizer`, and `report_generator`; ten
  additional agents passed under compatibility profiles.
- Accelerated full-logical-DAG trace called `17` default-off demo compute
  agents, mapped `12`, and failed closed `5`; L4 compute-default called and
  mapped both `decision_synthesizer` and `report_generator`.

### Not Done

- No external agent invoke endpoint was called.
- No `.env` value was inspected or changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No model, scoring, threshold, feature, training, data-source, dependency, or
  deployment configuration was changed.
- No provider call was made.

## 2026-06-21 - Phase BG4 post-backfill full-DAG E2E QA

### Validated

- Ran a post-BG2/BG3 full fixed-DAG QA for the question:
  "请从估值、市场、风险和宏观角度分析贵州茅台 600519.SH 当前是否值得关注。"
- Used the default-off external compute demo bridge with an explicit L2/L3
  allowlist. The run called allowlisted production `/v1/agent/compute` paths
  only and did not call any external agent invoke path.
- Preserved the current L4 `external_compute_default` runtime path. Both L4
  compute-default services were attempted and failed closed because their
  production ports were not listening, so the executor kept the fallback
  decision/report path.
- Wrote sanitized QA artifacts under
  `/tmp/lma-bg4-post-backfill-e2e-20260621_151711`: `qa_summary.json`,
  `report_input_bundle.json`, `agent_evidence_bundle.json`,
  `workflow_trace.json`, `report_result.json`, and `final_report.md`.
- The QA mapped `13` default-off demo compute agents and recorded `4`
  demo failures. The mapped set included `risk_crash`,
  `risk_compliance_review`, `risk_financial_fraud`, and
  `macro_index_valuation`.

### Report Material

- `risk_crash`: `7` evidence items, `5` research points, and `6` drivers
  reached `agent_evidence_bundle_v1`.
- `risk_compliance_review`: `3` evidence items, `3` research points, and `4`
  drivers reached `agent_evidence_bundle_v1`.
- `risk_financial_fraud`: `4` evidence items, `3` research points, and `6`
  drivers reached `agent_evidence_bundle_v1`; the agent remains `partial`
  because the HyFormer feature/model path was unavailable for the requested
  `as_of`.
- `macro_index_valuation`: `6` evidence items, `4` research points, and `7`
  drivers reached `agent_evidence_bundle_v1`.
- `risk_composite` consumed the three enhanced risk L2 members, including the
  low-weight `risk_financial_fraud` partial member. `macro_composite` consumed
  `macro_index_valuation` as an owner-approved macro L2 direction input.

### Not Done

- No external agent invoke endpoint was called.
- No `.env` value was inspected or changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No production service code was modified.
- No raw service response, provider raw response, credential, traceback text,
  or chain-of-thought was stored in the repository.
- The final report used the fallback report path because L4 compute-default
  services were unavailable and configured LLM report synthesis lacked
  credentials in the current process environment.

## 2026-06-21 - Phase BG3 B2C duo report-material backfill

### Changed

- Backfilled public-safe report-material wrappers for the two BG2-unlocked
  candidates: `risk_financial_fraud` and `macro_index_valuation`.
- `risk_financial_fraud`: updated the production `app/agent/core.py`
  report-material projection and added a focused service-local
  `tests/test_report_material.py`.
- `macro_index_valuation`: updated the production `service.py`
  report-material projection and expanded
  `tests/test_domain_payload_agent.py`.
- Restarted only the two target production services after local validation:
  `risk_financial_fraud` on port `10013` and `macro_index_valuation` on port
  `10003`.
- Ran controlled production `/health` and fixed-DAG `/v1/agent/compute` smoke
  for both services, then verified provider-free main-system adapter mapping to
  `conclusion_object_v1`.

### Validated

- `risk_financial_fraud`: local `py_compile` passed; focused pytest passed
  `10` tests; controlled compute returned `4` evidence items, `3` research
  points, and `5` raw drivers; adapter mapping preserved `4` evidence items,
  `3` research points, and `6` drivers.
- `macro_index_valuation`: local `py_compile` passed; focused pytest passed
  `5` compute-path tests with the invoke test deselected; controlled compute
  returned `6` evidence items, `4` research points, and `6` raw drivers;
  adapter mapping preserved `6` evidence items, `4` research points, and `7`
  drivers.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No `.env` value was inspected or changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No model, scoring, feature, training, data, dependency, or deployment file
  was changed.

## 2026-06-21 - Phase BG2 blocker unlock smoke

### Changed

- Ran the BG2 blocker-unlock pass for the next backfill candidates:
  `risk_financial_fraud`, `market_capital_flow_chip`,
  `macro_index_valuation`, `value_traditional_valuation`, and
  `value_meta_valuation`.
- Restored the missing `risk_financial_fraud` production process on port
  `10013` using the documented prod service command, without changing service
  code.
- Ran controlled production `/health` and `/v1/agent/compute` smoke for
  `risk_financial_fraud` and `macro_index_valuation`, then verified
  provider-free main-system adapter mapping to `conclusion_object_v1`.
- Recorded sanitized BG2 smoke evidence in
  `docs/CONTROLLED_READINESS_SMOKE_LOG.md`.

### Unblocked

- `risk_financial_fraud`: production process restored on port `10013`; health,
  compute, and adapter mapping passed. The current production output is still
  report-material thin, so the sandbox report-material wrapper is the next B2C
  patch-plan candidate.
- `macro_index_valuation`: owner semantic approval is present in the service
  repo; production process on port `10003` passed health, compute, and adapter
  mapping. The sandbox report-material wrapper is the next B2C patch-plan
  candidate.

### Still Blocked

- `market_capital_flow_chip`: no production listener was present on port
  `10022`, and focused local contract tests still fail on the service-local
  dimension validator expecting legacy Chinese dimension labels while the
  fixed-DAG output uses `market`.
- `value_traditional_valuation`: sandbox/prod drift includes valuation fusion,
  adapter assumptions, and data-loader/cache behavior, not only report-material
  wrapper changes.
- `value_meta_valuation`: sandbox/prod drift changes valuation output behavior,
  including historical valuation safety-floor semantics, not only wrapper
  changes.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No `.env` file was read or changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No production service code, model, scoring, feature, training, data,
  dependency, or deployment file was changed.

## 2026-06-21 - Phase BG1 backfill preflight blocker batch

### Changed

- Recorded the BG1 sandbox-to-prod backfill preflight for the next priority
  candidates:
  `risk_financial_fraud`, `market_capital_flow_chip`,
  `macro_index_valuation`, `value_traditional_valuation`, and
  `value_meta_valuation`.
- No candidate met the full BG1 implementation gate. Each candidate was
  skipped before file writes, restart, or endpoint smoke.
- Added blocker cards to the pre-backfill ledger and readiness matrix so later
  work does not confuse sandbox report-material experiments with production
  backfill readiness.
- Lightly reviewed the non-write watchlist without endpoint calls:
  `value_ml_valuation`, `value_research_synthesis`, `market_stock_technical`,
  `risk_identification`, `macro_analysis`, `financial_data_service`,
  `macro_commodity_pricing`, and `entity_relation_extractor`.

### Blocked / Skipped

- `risk_financial_fraud`: production files already match the audited sandbox
  wrapper files for the checked paths, but no production listener/process was
  present on port `10013`; BG1 did not start a missing service.
- `market_capital_flow_chip`: no production listener/process was present on
  port `10022`, and `service.py` / `compute_core.py` / `schemas.py` differ
  across sandbox, prod, and owner-dev, requiring manual merge planning.
- `macro_index_valuation`: production process exists on port `10003`, but
  `service.py` differs across sandbox, prod, and owner-dev while readiness
  documentation still carries semantic-deferred risk for owner-led confirmation.
- `value_traditional_valuation`: production process exists on port `10000`,
  but sandbox changes include a `tools/data_loader.py` local finance-cache
  fallback in addition to report-material wrapper changes, which is outside the
  BG1 wrapper-only write scope.
- `value_meta_valuation`: production process exists on port `10002`, but
  sandbox/prod drift spans `service.py`, `spts_store.py`, adapter/agent code,
  data-cache behavior, and tests; sandbox also omits prod-only model-context
  explanations that must be preserved.

### Not Done

- No production service file was modified.
- No service was restarted or started.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was
  called.
- No `.env` file was read or changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No model, scoring, feature, training, data, dependency, or deployment file
  was changed.

## 2026-06-21 - Phase B3 risk report-material controlled restart smoke

### Changed

- Restarted only the two Phase B2A/B2B backfilled production risk L2 services:
  `risk_crash` on port `10012` and `risk_compliance_review` on port `10011`.
- Ran controlled production `/health` and fixed-DAG `/v1/agent/compute` smoke
  for both services.
- Verified provider-free main-system adapter mapping to `conclusion_object_v1`
  for both backfilled wrappers.
- Recorded sanitized smoke evidence in
  `docs/CONTROLLED_READINESS_SMOKE_LOG.md`.

### Validated

- `risk_crash`: health passed, compute returned fixed-DAG
  `agent_conclusion_v1` with `agent_id=risk_crash`, and adapter mapping passed
  with report-facing evidence, research points, drivers, and data-quality
  material.
- `risk_compliance_review`: health passed, compute returned fixed-DAG
  `agent_conclusion_v1` with `agent_id=risk_compliance_review`, and adapter
  mapping passed with report-facing evidence, research points, drivers, and
  data-quality material.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No `.env` file was read or changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No model, scoring, rubric, feature, data, dependency, or deployment file was
  changed.

## 2026-06-21 - Phase B2B risk_compliance_review production file-level backfill

### Changed

- Backfilled the public-safe report-material wrapper and `as_of` alias support
  for `risk_compliance_review` from the audited sandbox service files into the
  prod running service directory.
- The wrapper projects existing deterministic compliance outputs into bounded
  rubric tables, weakest dimensions, finding summaries, top terms, slice
  summaries, corpus notices, `drivers`, `research_points`, thicker `evidence`,
  and `quality` material.
- Added prod-local focused contract coverage for the fixed-DAG `as_of` alias
  and report-material projection.

### Not Done

- No scoring, rubric, text-analysis, data, dependency, or deployment file was
  changed.
- No service restart was performed.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called.
- No `.env` file was read or changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- At B2B closeout, controlled smoke was deferred to Phase B3; the separate B3
  entry above records the later controlled restart and smoke.

## 2026-06-21 - Phase B2A risk_crash production file-level backfill

### Changed

- Backfilled the public-safe report-material wrapper for `risk_crash` from the
  audited sandbox service file into the prod running service directory.
- Added the prod-local `risk_crash` report-material focused test copied from
  the audited sandbox service.
- The wrapper only projects existing crash-risk outputs into bounded
  `drivers`, `research_points`, thicker `evidence`, and `quality` material.

### Not Done

- No model, scoring, feature engineering, data, dependency, or deployment
  file was changed.
- No service restart was performed.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called.
- No `.env` file was read or changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- At B2A closeout, controlled smoke was deferred to Phase B3; the separate B3
  entry above records the later controlled restart and smoke.

## 2026-06-19 - Pre-backfill audit documentation

### Changed

- Added `docs/PRE_BACKFILL_AUDIT_FIXED_DAG.md` as the current pre-backfill
  ledger for what changed in the main system, what remains sandbox-only, what
  already reached prod service directories, and which agents should or should
  not be backfilled next.
- Updated `docs/NEXT_PHASE_ROADMAP_FIXED_DAG.md` from the older R8-13I snapshot
  to the current R8-13Q state, including the L4 compute-only default runtime
  exception and non-L4 runtime boundaries.
- Added the pre-backfill ledger to `docs/INDEX.md`,
  `docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md`, and the suggested new-session
  reading list.

### Not Done

- No source code was changed.
- No `.env` file was changed.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called.
- No external service backfill was applied.
- No runtime binding or live flag was changed.

## 2026-06-19 - L4 external compute default runtime

### Changed

- Added `external_compute_default` runtime binding support for L4
  compute-only services.
- Switched `decision_synthesizer` and `report_generator` in
  `config/fixed_dag/runtime_bindings.json` from deterministic L4 seams to
  external compute-default bindings on ports `10025` and `10026`.
- Taught the fixed-DAG executor to call L4 `/v1/agent/compute` from runtime
  bindings without enabling the demo bridge and without calling `/invoke`.
- Added `disable_external_compute_default` as a rollback/test context control.
- Synchronized the L4 `决策融合智能体` and `报告生成智能体` service directories
  from sandbox to both `/sdb/dlut/dev` and `/sdb/dlut/prod`.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_fixed_dag_executor.py tests/unit_tests/test_public_mapping_fixed_dag.py tests/unit_tests/test_fixed_dag_reset_docs.py tests/unit_tests/test_fixed_dag_contracts.py`
  returned 151 passed.
- `PYTHONDONTWRITEBYTECODE=1 pytest -q /sdb/dlut/dev/决策融合智能体/tests/test_l4_decision_service.py /sdb/dlut/dev/报告生成智能体/tests/test_l4_report_service.py`
  returned 9 passed.
- `PYTHONDONTWRITEBYTECODE=1 pytest -q /sdb/dlut/prod/决策融合智能体/tests/test_l4_decision_service.py /sdb/dlut/prod/报告生成智能体/tests/test_l4_report_service.py`
  returned 9 passed.
- Controlled runtime-default smoke validated a full fixed-DAG execution with
  `external_compute_demo_enabled=false`, default-called/mapped agents
  `decision_synthesizer` and `report_generator`, no failed L4 agents, a mapped
  `decision_result_v1`, and a complete mapped `report_result_v1` titled
  `贵州茅台(600519.SH) 固定流程投资研判报告`.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No `.env` file was changed.
- Non-L4 service owner backfill remains a separate follow-up.

## 2026-06-19 - L4 runtime binding phase preflight

### Changed

- Added `build_l4_runtime_binding_phase_plan` as a non-mutating preflight for a
  future external-L4 runtime binding phase.
- The preflight proves that current `runtime_bindings.json` schema does not yet
  represent a default external L4 compute path: existing external HTTP
  candidates are explicitly disabled, and L4 default compute requires a schema
  and executor phase before any config edit.
- The plan still lists the intended compute-only target for
  `decision_synthesizer` and `report_generator`, but returns
  `config_edit_allowed=false` and `runtime_bindings_changed=false`.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py`
  returned 20 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_public_mapping_fixed_dag.py tests/unit_tests/test_fixed_dag_reset_docs.py`
  returned 88 passed.

### Not Done

- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called
  for this preflight.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- External L4 default runtime remains deferred.

## 2026-06-19 - L4 runtime review candidate package

### Changed

- Added `build_l4_runtime_review_candidate_package` as the repo-recorded R8-13O
  L4 runtime review package.
- Added `docs/L4_RUNTIME_REVIEW_EVIDENCE_R8_13O.md` with the candidate evidence,
  rollback plan, non-claims, and remaining operator-approval gate.
- The candidate package marks provider compute, transcript safety, and rollback
  plan evidence as passing from current repository artifacts, while keeping
  `operator_approval` pending.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py`
  returned 18 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_public_mapping_fixed_dag.py tests/unit_tests/test_fixed_dag_reset_docs.py`
  returned 86 passed.

### Not Done

- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called
  for R8-13O.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- External L4 runtime binding remains deferred until explicit operator approval
  and a separate runtime binding phase.

## 2026-06-19 - L4 runtime review evidence package seam

### Changed

- Added `build_l4_runtime_review_evidence_package` and
  `fixed_dag_l4_runtime_review_evidence_package_v1` as a local, side-effect-free
  package builder for the explicit L4 runtime review.
- The package requires four safe evidence records before it can report
  `ready_for_explicit_runtime_binding_phase`: provider compute pass,
  transcript safety pass, rollback plan readiness, and operator approval.
- Evidence records only preserve bounded safe fields: `reference`, `summary`,
  `validated_by`, and `validated_at`. Missing references, unsafe references,
  unsafe text, or non-passing records keep the package blocked.
- The package embeds the R8-13M dry run and preserves the same non-actions:
  no endpoint call, no `.env` edit, no runtime binding edit, no live flag
  change, and no default invoke change.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py`
  returned 17 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_public_mapping_fixed_dag.py tests/unit_tests/test_fixed_dag_reset_docs.py`
  returned 85 passed.

### Not Done

- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called
  for R8-13N.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- The evidence package does not itself grant runtime approval; it only tells
  maintainers whether the explicit runtime binding phase can be opened.

## 2026-06-19 - L4 runtime binding dry-run seam

### Changed

- Added `build_l4_runtime_binding_dry_run` and
  `fixed_dag_l4_runtime_binding_dry_run_v1` as a metadata-only runtime review
  seam for the two L4 ids: `decision_synthesizer` and `report_generator`.
- The dry run reports current deterministic runtime-binding state, proposed
  production compute URLs, prerequisite booleans, blocking reasons, and the
  recommended next action without editing runtime config.
- Per-agent dry-run rows explicitly scope existing `live_verified` and
  `invoke_enabled_by_default` flags to the deterministic internal L4 seam, and
  keep proposed external L4 live/default flags false.
- Documented the dry-run contract and decision in `docs/CONTRACTS.md`,
  `docs/SYSTEM_MAP.md`, `docs/ARCHITECTURE_FIXED_DAG.md`, and
  `docs/DECISIONS.md`.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py`
  returned 14 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_public_mapping_fixed_dag.py tests/unit_tests/test_fixed_dag_reset_docs.py`
  returned 82 passed.

### Not Done

- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called
  for R8-13M.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- The dry run can report `ready_for_runtime_binding_review`, but even that
  state is not a runtime binding edit and does not enable external L4 by
  default.

## 2026-06-19 - L4 runtime binding review checklist

### Changed

- Added ADR-064 documenting that R8-13J provider-backed L4 `/v1/agent/compute`
  pass does not enable default external L4 runtime binding.
- Documented the minimum external-L4 runtime review checklist in
  `docs/CONTRACTS.md`, `docs/SYSTEM_MAP.md`, and
  `docs/ARCHITECTURE_FIXED_DAG.md`.
- Added a runtime registry regression test that keeps
  `decision_synthesizer` and `report_generator` as deterministic L4 seams with
  no external agent id, env var, or default URL until a later explicit runtime
  review changes `runtime_bindings.json`.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_runtime_registry.py`
  returned 12 passed.

### Not Done

- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No external L4 service was made a default graph dependency.

## 2026-06-19 - L4 runtime and transcript readiness audit

### Changed

- Documented the R8-13K L4 runtime/public-transcript gate in `docs/CONTRACTS.md`:
  provider-backed `/v1/agent/compute` pass does not imply runtime binding
  enablement, and a future runtime phase must separately review public answer
  safety, workflow detail safety, rollback behavior, and runtime binding edits.
- Added adapter regression tests proving that provider-backed L4
  `decision_result_v1` and `report_result_v1` payloads containing raw provider
  artifacts, secrets, endpoint URLs, tracebacks, raw external JSON, or
  chain-of-thought markers are rejected as adapter failures instead of entering
  the final transcript path.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_public_mapping_fixed_dag.py`
  returned 66 passed.

### Not Done

- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called
  for R8-13K.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- Runtime binding review remains a later explicit phase.

## 2026-06-19 - L4 provider-backed compute smoke

### Changed

- Restarted production L4 service processes on ports 10025 and 10026 with
  provider credentials loaded from the existing production main-system `.env`
  into the process environment. The `.env` file was not modified and credential
  values were not printed.

### Validated

- Controlled `/health` smoke for `decision_synthesizer` and `report_generator`
  returned `llm_preflight_status=ok` with production-source service versions.
- Controlled default-off `/v1/agent/compute` bridge smoke mapped
  `decision_synthesizer` to a valid `decision_result_v1` with
  `decision=manual_review`, `status=partial`, and four reasoning trace entries.
- Controlled default-off `/v1/agent/compute` bridge smoke mapped
  `report_generator` to a valid `report_result_v1` with `status=complete`,
  title `贵州茅台（600519.SH）综合研判报告（2026-06-19）`, 5 sections, and 5
  evidence cards.
- Direct service metadata check confirmed `provider_invoked=true` and
  `used_llm_* = true` for both L4 services, with zero service warnings.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No raw provider response, credential value, endpoint URL, or raw graph message
  was stored in the repository.
- Runtime binding review remains separate; provider-backed compute pass does
  not make L4 a default runtime dependency.

## 2026-06-19 - L4 production-source service smoke

### Changed

- Formalized production service directories for the L4
  `decision_synthesizer` and `report_generator` under
  `/sdb/dlut/prod/决策融合智能体` and `/sdb/dlut/prod/报告生成智能体`.
- Backfilled the minimal L4 main-system helpers required by those production
  services into `/sdb/dlut/prod/langgraph-my-agent/src/react_agent/`:
  `fixed_dag_l4_decision_synthesizer.py` and the provider-preflight-aware
  `fixed_dag_report_synthesizer.py`.
- Updated the L4 service wrappers to resolve the nearest
  `langgraph-my-agent/src` tree, so the same source can run from sandbox,
  development, or production service roots.
- Updated L4 service READMEs to remove sandbox-only wording and document both
  production-candidate and development-candidate loopback ports.
- Restarted production L4 ports from production service roots:
  `decision_synthesizer=10025` and `report_generator=10026`. Development
  candidate ports `8025` and `8026` remain sourced from the sandbox service
  roots.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the
  production L4 service files, their tests, and the two production main-system
  helper files.
- `PYTHONDONTWRITEBYTECODE=1 pytest -q /sdb/dlut/prod/决策融合智能体/tests/test_l4_decision_service.py /sdb/dlut/prod/报告生成智能体/tests/test_l4_report_service.py`
  returned 9 passed.
- Controlled `/health` smoke passed for production ports 10025/10026 and
  development ports 8025/8026. Production services reported
  `0.1.0-production-source`; development services reported `0.1.0-sandbox`.
- Controlled `/v1/agent/compute` smoke through the default-off main-system
  bridge passed for production-source ports 10025/10026 and development
  candidate ports 8025/8026. Both runs mapped `decision_synthesizer` to
  `decision_result_v1` and `report_generator` to `report_result_v1`; the report
  contained 6 sections and 5 evidence cards.
- Provider credentials were unavailable in the service environment, so both L4
  services used deterministic fallback and returned `pending_implementation`
  status.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- Provider-backed LLM decision/report behavior is still not verified; the
  production-source smoke proves compute contract reachability and deterministic
  fallback only.

## 2026-06-19 - Sandbox L4 service contract test prep

### Changed

- Hardened the sandbox-only L4 `decision_synthesizer` and `report_generator`
  service wrappers under `/sdb/dlut/sandbox/r8-13a/services/prod/` by replacing
  mutable request defaults with Pydantic `Field(default_factory=dict)`.
- Changed both sandbox L4 service health payloads to report secret-free provider
  preflight metadata instead of hard-coding `llm_configured=true`.
- Added offline service contract tests for the sandbox L4 decision and report
  services. The tests call the in-process handler functions directly and cover
  health payload safety, deterministic fallback, fake valid LLM output, invalid
  LLM-output fallback, report boundary normalization, and public-safe text
  normalization.
- Updated both sandbox L4 service READMEs with local contract-test commands,
  provider-preflight boundaries, and compute-only/no-invoke test scope.
- Fixed the default-off compute bridge's L4 report request path so a validated
  `report_input_bundle_v1` is passed intact to `report_generator` instead of
  being truncated by the generic context sanitizer. This prevents the L4 report
  service from falling back to a template report despite receiving a valid
  public-safe report bundle.
- Fixed the sandbox L4 report service boundary normalization so machine fields
  such as `schema`, `schema_version`, and `status` remain contract enums while
  public-facing text is translated into business Chinese.
- Started sandbox L4 services on production-candidate ports 10025/10026 and
  development-candidate ports 8025/8026 for controlled smoke.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the two
  sandbox L4 service files and their new tests.
- `PYTHONDONTWRITEBYTECODE=1 pytest -q /sdb/dlut/sandbox/r8-13a/services/prod/决策融合智能体/tests/test_l4_decision_service.py /sdb/dlut/sandbox/r8-13a/services/prod/报告生成智能体/tests/test_l4_report_service.py`
  returned 9 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_external_compute_bridge.py`
  returned 22 passed in both dev main and sandbox main.
- In-process bridge regression passed by replacing the bridge transport with
  direct calls to the sandbox L4 `compute()` handlers. The run mapped
  `decision_synthesizer` to `decision_result_v1` with `decision=positive_watch`
  and mapped `report_generator` to `report_result_v1` with
  `status=complete`, 2 sections, and 2 evidence cards. No live HTTP endpoint
  was called.
- Controlled health smoke passed for ports 10025, 10026, 8025, and 8026. Each
  endpoint returned `external_agent_health_v0` with the expected fixed DAG id
  and secret-free `llm_preflight_status=missing_credential`.
- Controlled compute smoke passed for production-candidate ports 10025/10026
  and development-candidate ports 8025/8026 through the default-off main-system
  compute bridge. Both runs mapped `decision_synthesizer` to
  `decision_result_v1` and `report_generator` to `report_result_v1`; provider
  credentials were absent, so both services used deterministic fallback.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- The L4 services are still sourced from sandbox directories; the controlled
  health/compute smoke is candidate-port evidence, not formal production
  service-source readiness or default runtime enablement.

## 2026-06-19 - Search fallback metadata test fix

### Changed

- Preserved normalized `max_results` metadata on the fail-soft Tavily search
  fallback tool when optional `langchain_tavily` is unavailable or cannot be
  initialized.

### Validated

- Broad local test run initially exposed
  `tests/unit_tests/test_tools.py::test_build_tavily_search_max_results` failing
  in this environment because `langchain_tavily` is not installed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_tools.py`
  returned 2 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests tests/integration_tests`
  returned 366 passed.

### Not Done

- No search provider was called.
- No `.env` or runtime binding file was changed.

## 2026-06-19 - Dev main-system L4 compute/report handoff

### Changed

- Added main-system mapping support for external `decision_result_v1` and
  `report_result_v1` payloads returned through the default-off
  `/v1/agent/compute` bridge. The adapter validates the mapped L4 objects and
  strips unsafe text such as secrets, endpoint URLs, raw provider responses,
  tracebacks, and internal reasoning drafts.
- Added default-off bridge registry and request context support for
  `decision_synthesizer` and `report_generator`. L4 compute requests can carry
  bounded `dimension_results`, `decision_result`, and
  `report_input_bundle_v1`; only these two L4 ids may request
  `options.allow_llm=true`, and they still use compute-only loopback entries.
- Documented loopback-only `EXTERNAL_COMPUTE_DEMO_URL_<AGENT_ID>` overrides so
  controlled sandbox/prod port comparison can select local service ports without
  changing runtime bindings or production-default routing.
- Updated the executor so an explicit external compute demo allowlist can
  overlay L4 decision and report results. A mapped external `report_generator`
  result is not overwritten by the internal LLM report synthesis seam.
- Added a default-off L4 decision synthesis helper used by the sandbox L4
  service path. It can ask a configured model for language-level decision
  synthesis, but deterministic `build_decision_result` remains the fallback and
  risk gates still guard optimistic model output.
- Exposed `report_result_v1.sections`, `evidence_cards`, and `limitations`
  through `final_emit_payload`, `emitted_bundle`, and public assistant answer
  cards. The R8-13A smoke runner now writes a full `final_report.md` rendered
  from the structured report, not only the final answer string.
- Strengthened the report synthesis prompt so final Chinese reports explain L3
  quality packets, risk override details, and enum values in business Chinese
  instead of leaking internal schema wording.
- Aligned L4 documentation and frontend TypeScript public types with the dev
  handoff state: L4 remains production-deferred, but the main system now has a
  default-off compute handoff; `AnswerCardModel` accepts optional `sections`
  and `limitations` from the backend public contract.
- Recorded the L4 handoff as `ADR-063` and updated the developer L4 prompt so
  service-owner follow-up uses controlled compute evidence instead of the older
  design-only wording.

### Validated

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...` passed for the modified
  L4 adapter, bridge, executor, contracts, public mapping, report synthesizer,
  smoke runner, and focused tests.
- Focused L4/public tests passed:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q ...` returned 16 passed.
- Existing bridge/executor/report/public regression slice passed:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_fixed_dag_executor.py tests/unit_tests/test_fixed_dag_report_synthesizer.py tests/unit_tests/test_public_mapping_fixed_dag.py tests/unit_tests/test_mainline_bundle_seam_ff1.py`
  returned 57 passed.
- Broader related regression slice passed:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_l4_decision_synthesizer.py tests/unit_tests/test_fixed_dag_executor.py tests/unit_tests/test_fixed_dag_report_synthesizer.py tests/unit_tests/test_public_mapping_fixed_dag.py tests/unit_tests/test_mainline_bundle_seam_ff1.py tests/unit_tests/test_run_r8_13a_e2e_smoke.py`
  returned 138 passed.
- Offline R8-13A smoke passed without live endpoints:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/dev/run_r8_13a_e2e_smoke.py --artifact-root /tmp/lma-dev-l4-offline-smoke-20260619`.
  The artifact rendered a full `final_report.md` with 7 sections, 5 evidence
  cards, and 4 limitations. The offline fake bridge now accepts the same L4
  context kwargs as the real bridge and has safe L4 fixtures for
  `decision_result_v1` / `report_result_v1`.
- Frontend contract type check passed via
  `npm --prefix apps/web run build`; the app has no separate `typecheck`
  script.

### Not Done

- No external agent service repository was modified in this dev phase.
- No `.env` or `config/fixed_dag/runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No live HTTP `/health`, `/compute`, or `/invoke` endpoint was called.
- This does not make the demo bridge production-default, and it does not turn
  `/compute` evidence into `/invoke` evidence.

## 2026-06-19 - Sandbox L3 research packet material pass

### Changed

- Extended the default-off external compute bridge so allowlisted external L3
  compute requests receive bounded public-safe L2 report material, not only
  summary/stance/confidence. The safe upstream context may now include
  `domain_metrics`, `drivers`, `research_points`, `data_quality`, and bounded
  evidence while still stripping endpoint URLs, secrets, raw responses,
  tracebacks, and internal reasoning drafts.
- Extended `agent_task_v1.upstream_results` with the same public-safe L2 report
  material so L3 services can read richer context from either the request
  context or the task object.
- Extended the external adapter allowlist for L3 service-owned research packet
  fields: `composite_research_packet`, `composite_quality`,
  `conflict_summary`, `dominant_signals`, `missing_or_degraded_members`,
  `final_implication`, and `limitations`.
- Enhanced the sandbox `value_composite`, `market_composite`,
  `risk_composite`, and `macro_composite` service wrappers with deterministic
  service-owned research packets. These packets explain member consensus,
  dominant signals, conflicts, coverage, partial members, and decision
  implications without changing `stance`, `confidence`, `gate`, `risk_score`,
  `dimension_weights`, member weights, or status.

### Validated

- Main-system focused tests passed:
  `PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_contracts.py`
  returned 88 passed.
- Sandbox L3 service `py_compile` passed for the modified value, market, risk,
  and macro service files plus their focused tests.
- Sandbox L3 focused tests passed:
  `tests/test_fixed_dag_l3_wrapper.py` returned 5 passed,
  `tests/test_service.py::test_fixed_dag_market_upstream_adds_research_packet`
  returned 1 passed, `tests/test_fixed_dag_upstream_wrapper.py` returned
  1 passed, and
  `tests/test_synthesis.py::test_fixed_dag_macro_conclusion_merges_upstream_outputs`
  returned 1 passed.

### Not Done

- No production service file was modified.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No live HTTP `/health`, `/compute`, or `/invoke` endpoint was called in this
  phase. The value L3 focused test suite still includes its existing in-process
  FastAPI TestClient compute-handler regression.

## 2026-06-18 - Sandbox L2 report-material wrapper progress

### Changed

- Enhanced the sandbox `risk_crash` service wrapper report material without
  retraining the model or changing runtime bindings. The wrapper now projects
  existing crash-risk model outputs into bounded public-safe `drivers`,
  `research_points`, thicker `evidence`, and `quality` material for downstream
  fixed-DAG report input bundles.
- Refined the sandbox `risk_crash` model-vintage boundary. Its warning and
  report material now distinguish input-feature anti-lookahead from the
  separate caveat that a historical `as_of` run uses the current production
  model version trained through a later feature year.
- Enhanced deterministic `risk_composite` report material so member-level
  warnings and model/data boundaries are retained as `member_boundary_summary`
  in L3 `drivers`, `research_points`, and `data_quality`. This keeps caveats
  visible after L3 compression without changing `risk_score`, `gate`, or member
  weights.
- Documented the current P0 L2 wrapper state for
  `value_research_synthesis`, `risk_crash`, and `macro_index_valuation`.
  `value_research_synthesis` and `macro_index_valuation` already had sandbox
  report-material wrappers from the prior experiment; this phase filled the
  missing `risk_crash` gap.
- Audited the next P1 L2 candidates. `value_ml_valuation` and
  `value_meta_valuation` already carry sandbox report material. Enhanced the
  sandbox `risk_identification` wrapper so its existing rule-margin/MD&A-hit
  risk outputs are projected into public-safe risk tables, drivers,
  `research_points`, thicker `evidence`, and `quality` material.
- Enhanced the sandbox `risk_financial_fraud` wrapper without retraining its
  HyFormer model, changing risk-gate thresholds, or adding LLM usage. The wrapper
  now projects existing model probability, threshold, feature availability,
  annual feature timing, gate action, and evidence context into public-safe
  `fraud_risk_bridge`, `model_context`, `feature_diagnostics`,
  `risk_gate_rule`, `drivers`, `research_points`, thicker `evidence`, and
  `quality`.
- Enhanced the sandbox `macro_analysis` wrapper without changing macro-cycle
  rules, nowcast thresholds, or `/compute` LLM behavior. The wrapper now projects
  existing macro signals, investment-clock regime, asset allocation view, sector
  rotation ledger, macro data window, and Zeping crosscheck material into
  public-safe `macro_regime_bridge`, `macro_signal_table`,
  `asset_allocation_view`, `sector_rotation_summary`, `macro_data_window`,
  `zeping_crosscheck_context`, `drivers`, `research_points`, thicker
  `evidence`, and `quality`.
- Fixed sandbox `value_ml_valuation` and `value_meta_valuation` direction
  wrappers to expose top-level `stance` and `confidence` alongside
  `normalized`, so the main-system adapter can consume their existing report
  material without `direction_stance_missing`.
- Extended dev and sandbox-main adapter allowlists so the financial-fraud and
  macro-analysis report material can enter `provenance.domain_metrics`,
  `drivers`, `research_points`, `data_quality`, and
  `report_input_bundle_v1.agent_evidence_bundle.l2_agent_outputs[]`.
- Updated the readiness matrix to keep production status unchanged while noting
  the sandbox-only report-material progress.

### Validated

- `PYTHONPYCACHEPREFIX=/tmp/lma-risk-crash-pycache /tmp/lma-service-test-venv/bin/python -m py_compile crash_risk_model/agent/compute_core.py crash_risk_model/agent/tests/test_report_material.py`
- `PYTHONPYCACHEPREFIX=/tmp/lma-risk-crash-pycache /tmp/lma-service-test-venv/bin/python -m pytest crash_risk_model/agent/tests/test_report_material.py -q -p no:cacheprovider --basetemp /tmp/lma-risk-crash-report-material-tests-final`
- Direct `risk_crash` compute-core validation completed in 2.59s and returned
  `agent_conclusion_v1` with 5 `research_points` and the expected model-driver
  names.
- Direct `risk_crash` endpoint-handler validation completed in 3.48s without
  TestClient/HTTP and preserved 5 `research_points` after fixed-DAG
  `gate_member` projection.
- `value_research_synthesis` report-material test passed:
  `tests/test_domain_payload.py::test_domain_payload_adds_analyst_report_material_without_llm`.
  This is an offline fixture/material projection test, not live data evidence.
- Direct `macro_index_valuation` compute-core + domain-attach validation
  completed in 0.70s and returned `agent_conclusion_v1` with 4
  `research_points` and the expected macro-driver names.
- Direct `macro_index_valuation` endpoint-handler validation completed in 0.73s
  without TestClient/HTTP and preserved the same report material.
- Ran a P0 direct sandbox bundle check with no live HTTP, no TestClient, and no
  `/invoke`; artifact:
  `/tmp/lma-p0-direct-bundle-check/20260618T070209Z`.
- The direct bundle check mapped all three P0 L2 outputs through the main-system
  adapter, built `report_input_bundle_v1`, and built fallback `report_result_v1`.
  Both validators returned `ok`; fallback report text contained the three P0
  L2 sections and the `研究判断` marker.
  `value_research_synthesis` and `risk_crash` used `600519.SH` with
  `as_of=2026-06-17`; `macro_index_valuation` used `000300.SH` with the same
  as-of date as macro context.
- Main-system fixed-DAG material/report tests passed locally:
  `PYTHONPATH=src pytest -q tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py tests/unit_tests/test_fixed_dag_report_synthesizer.py tests/unit_tests/test_fixed_dag_l3_explanation_synthesizer.py`
  returned 104 passed.
- `risk_identification` sandbox report-material code and test passed
  `py_compile`.
- `risk_identification`新增纯本地 report-material 单测 2 passed; tests call
  `MarketRiskCore.compute()` and app-layer fixed-DAG projection directly, with
  no HTTP and no TestClient request.
- `risk_financial_fraud` sandbox report-material code and tests passed:
  `PYTHONPYCACHEPREFIX=/tmp/lma-financial-fraud-pycache python3 -m py_compile app/agent/core.py tests/test_report_material.py`
  and
  `PYTHONPYCACHEPREFIX=/tmp/lma-financial-fraud-pycache python3 -m pytest -q tests/test_report_material.py -p no:cacheprovider --basetemp /tmp/lma-financial-fraud-report-material-tests`
  returned 2 passed. The tests call `compute_core()` and app-layer fixed-DAG
  projection directly, with no HTTP, no `/invoke`, and no provider.
- `macro_analysis` sandbox report-material code and tests passed:
  `PYTHONPYCACHEPREFIX=/tmp/lma-macro-analysis-pycache python3 -m py_compile service.py tests/test_report_material.py`
  and
  `PYTHONPYCACHEPREFIX=/tmp/lma-macro-analysis-pycache python3 -m pytest -q tests/test_report_material.py -p no:cacheprovider --basetemp /tmp/lma-macro-analysis-report-material-tests`
  returned 2 passed. The tests call `compute_core()` directly and validate both
  nowcast and explicit-scenario report-material paths, with no HTTP,
  no `/invoke`, and no provider.
- Existing sandbox `value_ml_valuation` tests passed: `py_compile` plus
  `tests/test_domain_contract_v1.py`, `tests/test_service_contract.py`, and
  `tests/test_v21_compliance.py` returned 22 passed.
- Existing sandbox `value_meta_valuation` tests passed: `py_compile` plus
  `tests/test_domain_contract_v1.py` and `tests/test_v21_compliance.py`
  returned 8 passed.
- Direct `risk_identification` fixed-DAG handler validation returned
  `agent_id=risk_identification`, `role=gate_member`, `risk_score=0.0171`,
  5 `research_points`, 7 drivers, and 10 evidence items for `600519.SH` at
  `as_of=2024-12-31`.
- Main-system adapter projection for the same direct `risk_identification`
  payload returned `conclusion_object_v1` with 5 `research_points`, 9 drivers,
  10 evidence items, no adapter failure, and public-safe `risk_score` in
  provenance/domain metrics.
- After the top-level stance fix, direct adapter projection for
  `value_ml_valuation` returned `partial` with 4 `research_points`, 6 drivers,
  and 7 evidence items; `value_meta_valuation` returned `complete` with 3
  `research_points`, 6 drivers, and 6 evidence items.
- Ran a 6-agent direct sandbox bundle check with no live HTTP, no TestClient,
  and no `/invoke`; artifact:
  `/tmp/lma-6agent-direct-bundle-check/20260618T073557Z`.
- The 6-agent bundle check mapped
  `value_research_synthesis`, `value_ml_valuation`, `value_meta_valuation`,
  `risk_crash`, `risk_identification`, and `macro_index_valuation` through the
  main-system adapter and built a validated `report_input_bundle_v1` plus
  fallback `report_result_v1`. Result: 5 complete L2, 1 partial L2, 0 adapter
  failures, 0 L2 without readable evidence, and fallback report answer length
  11138 characters.
- Ran default-off real LLM report synthesis from the 6-agent
  `report_input_bundle_v1`; artifact:
  `/tmp/lma-6agent-real-llm-report-synthesis/20260618T075202Z`.
- The real LLM synthesis used `deepseek/deepseek-chat` through the report
  synthesizer only. It did not call live agent HTTP, TestClient, or `/invoke`,
  and did not store raw provider response. The sanitized `report_result_v1`
  validated successfully with `status=complete`, 5 sections, 7 evidence cards,
  and 7 limitations.
- Rebuilt the same 6-agent direct L2 artifact through the main-system
  deterministic L3 builders and default-off LLM report synthesis; artifact:
  `/tmp/lma-6agent-l3-llm-report-synthesis/20260618T075647Z`.
- The L3-enriched report input validated with 6 L2 outputs and 3 L3 outputs:
  `value` partial, `risk` complete with `gate=pass` and `risk_score=0.0949`,
  and `macro` complete with `regime=neutral`. Quality summary was
  L2 complete 5/6, L2 partial 1/6, L3 complete 2/3, L3 partial 1/3.
- The L3-enriched LLM report used `deepseek/deepseek-chat` through the
  report synthesizer only. It validated as `report_result_v1` with
  `status=complete`, 3 sections, 4 evidence cards, and 5 limitations, and
  no longer described L3 as missing.
- The L3-enriched report exposed the next material-quality gaps:
  `value_ml_valuation` remains partial because the sandbox run lacked a
  financial snapshot, and `risk_identification` carries an older data date
  than the shared `as_of`.
- Added a sandbox-only local financial-cache fallback for
  `value_ml_valuation`. The wrapper can now read a configured
  `VALUATION_FINANCIAL_CACHE_DIR` or service-local `_pe_train_cache`, select
  the latest financial row with `ann_date <= as_of`, join `rd_exp` from the
  matching local income cache, and surface `financial_report_period` plus
  `financial_publish_time` in public-safe report material.
- Extended the main-system external adapter public-safe allowlist so
  `financial_report_period` and `financial_publish_time` can enter
  `domain_metrics` and `data_quality`.
- Extended the main-system external adapter public-safe allowlist so
  `model_vintage_boundary`, `feature_data_anti_lookahead_passed`, and
  `model_vintage_caveat` can enter report-facing provenance without preserving
  raw external JSON.
- Rebuilt the 6-agent bundle by reusing the five existing direct mapped L2
  artifacts and rerunning sandbox `value_ml_valuation` with the configured
  local financial cache; artifact:
  `/tmp/lma-6agent-ml-financial-cache-l3-llm/20260618T080604Z`.
- The rebuilt bundle validated with L2 complete 6/6 and L3 complete 3/3.
  `value_ml_valuation` returned `status=ok`,
  `financial_data_source=local_financial_cache`,
  `financial_report_period=20240930`, `financial_publish_time=20241026`,
  ROE `26.833`, growth `16.9078`, valuation center `1813.801`, and upside
  `19.0158`.
- The rebuilt LLM report validated with `status=complete`, 6 sections, 4
  evidence cards, and 6 limitations. It now treats value L3 as complete while
  still explaining the conflict between sell-side/research synthesis,
  machine-learning valuation, and peer meta valuation.
- Added a sandbox `risk_identification` 2024Q3 numeric period for 600519.SH in
  its local `companies.json` snapshot. The numeric features were derived from
  existing local parquet/csv/pkl snapshots, use `report_period=2024-09-30` and
  `ann_date=2024-10-26`, and intentionally leave `mda_text` empty because the
  corresponding MD&A source text was not available in local evidence.
- Updated the sandbox `risk_identification` as-of leakage test so
  `as_of=2024-12-31` now expects the 2024Q3 period instead of the older 2023
  annual period.
- Rebuilt the 6-agent bundle again after refreshing `risk_identification`;
  artifact: `/tmp/lma-6agent-ml-risk-current-l3-llm/20260618T081227Z`.
- The refreshed risk output returned `status=ok`, `data_as_of=2024-10-26`,
  `report_period=2024-09-30`, `risk_score=0.019`, confidence `0.765`, and a
  public warning that MD&A text was unavailable so text `_hit` features were
  zeroed.
- The latest bundle remained L2 complete 6/6 and L3 complete 3/3. The risk L3
  stayed `gate=pass` with composite `risk_score=0.1036`. The latest LLM report
  validated with `status=complete`, 4 sections, 4 evidence cards, and 5
  limitations.
- Promoted the sandbox `value_ml_valuation` financial snapshot from a temporary
  read-only dev-cache dependency to a service-owned CSV cache under
  `data/cache/financial/`. The service now treats local cache files as
  `available()` data and can read `fina_indicator_*.csv` / `income_*.csv`
  alongside pickle snapshots.
- Added service-owned 600519.SH financial CSV rows for 2024Q3 and 2024 annual
  report. The as-of picker still selects 2024Q3 for `as_of=2024-12-31` because
  the annual report has `ann_date=2025-04-03`.
- Rebuilt the 6-agent bundle using the service-owned `value_ml_valuation`
  financial CSV path and the refreshed `risk_identification` 2024Q3 snapshot;
  artifact: `/tmp/lma-6agent-service-owned-cache-l3-llm/20260618T082145Z`.
- The service-owned-cache bundle validated with L2 complete 6/6 and L3 complete
  3/3. The default-off LLM report validated with `status=complete`, 5 sections,
  7 evidence cards, and 5 limitations.
- Focused `risk_crash` model-vintage validation passed:
  `crash_risk_model/agent/tests/test_report_material.py` plus
  `test_asof_leakage_probe.py` returned 8 passed. Direct handler validation
  for `600519.SH`, `as_of=2024-12-31` returned `risk_score=0.2079`,
  `confidence=0.62`, `feature_data_anti_lookahead_passed=true`, and
  `model_vintage_caveat=true`; the main-system adapter preserved
  `model_vintage_boundary` in `provenance.domain_metrics` and `drivers`.
- Main-system adapter focused tests passed in both dev and sandbox main copies:
  dev returned 35 passed and sandbox main returned 38 passed.
- Main-system financial-fraud/macro report-material projection tests passed
  after this extension: dev `test_fixed_dag_external_adapter.py` returned
  36 passed, dev `test_fixed_dag_contracts.py` returned 36 passed, and sandbox
  main `test_fixed_dag_external_adapter.py` + `test_fixed_dag_contracts.py`
  returned 76 passed.
- A direct sandbox material check called `risk_financial_fraud` app-layer
  `compute_payload()` and `macro_analysis.compute_core()` directly, then mapped
  both outputs through the sandbox main adapter into `report_input_bundle_v1`
  and fallback `report_result_v1`. It did not use live HTTP, `/invoke`,
  TestClient, or providers. Results: both mapped conclusions validated; the
  bundle and fallback report validated; `risk_financial_fraud` entered
  `l2_agent_outputs` with 4 `research_points`, 6 drivers, and 5 evidence items;
  `macro_analysis` entered with 5 `research_points`, 10 drivers, and 8 evidence
  items.
- Rebuilt the 6-agent report after the L3 risk boundary change; artifact:
  `/tmp/lma-6agent-risk-l3-boundary-l3-llm/20260618T084040Z`.
  The run reused five mapped L2 artifacts, reran sandbox `risk_crash` by direct
  handler, built deterministic L3 with `member_boundary_summary`, and ran
  default-off `deepseek/deepseek-chat` report synthesis. It did not call live
  agent HTTP or `/invoke`.
- The rebuilt report validated with L2 complete 6/6 and L3 complete 3/3. The
  final LLM report had `status=complete`, 5 sections, 9 evidence cards, and 7
  limitations; it no longer used the old "training-data forward-looking" phrase
  and explicitly surfaced the risk model-version boundary.

### Not Done

- No production service file was modified.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No live HTTP `/health`, `/v1/agent/compute`, or `/v1/agent/invoke`
  endpoint was called.
- A direct `value_research_synthesis` handler smoke with the default current
  date attempted its internal live quote lookup and received a sandbox network
  permission warning; that smoke is not counted as live evidence.
- No placeholder agent was treated as real evidence.
- Full TestClient endpoint suites were not completed in this session. Direct
  compute-core calls were fast, but in-process TestClient requests stalled in
  the local Python 3.14 Starlette/httpx/anyio portal path and were interrupted,
  so they are not counted as validation evidence.
- `value_research_synthesis` needed one same-process direct retry in the
  6-agent bundle because its first cold-start compute attempt can return the
  service's own timeout downgrade.
- Optional tracing export attempted by the provider stack returned a 403 during
  the LLM report run; the report synthesis itself completed and validated.
- The L3-enriched run still used direct mapped L2 artifacts and deterministic
  main-system L3 builders; it did not call external L3 services or prove live
  L3 `/invoke` readiness.
- The earlier `value_ml_valuation` financial-cache validation used a read-only
  dev external-agent cache path supplied through process environment. The
  later service-owned-cache run no longer requires that env override, but
  production still needs the same owned cache/data path copied, mounted, or
  replaced by a formal data service feed.
- The `risk_identification` 2024Q3 update is a sandbox snapshot enhancement
  for 600519.SH only. It does not solve full-universe snapshot freshness or
  provide 2024Q3 MD&A text; production should replace the local demo snapshot
  through the service owner's data pipeline before readiness advancement.

## 2026-06-18 - Phase R8-13N provider validation record

### Changed

- Recorded the controlled R8-13N real-provider validation for default-off L3
  explanation synthesis and default-off final LLM report synthesis.
- Updated the controlled smoke log and Chinese report-improvement plan with the
  sanitized artifact path and validation outcome.

### Evidence

- Artifact directory:
  `/tmp/lma-r8-13n-l3-real-provider-demo/20260618T061151Z`.
- Model: `openai/deepseek-v4-flash`.
- L3 explanation: `attempted=true`, `provider_invoked=true`,
  `used_llm_explanation=true`.
- Final report synthesis: `attempted=true`, `provider_invoked=true`,
  `used_llm_report=true`.
- `report_input_bundle_v1` validation: pass.
- `report_result_v1` validation: pass.

### Not Done

- No runtime behavior changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called.
- No raw provider response, credentials, endpoint URLs, or raw graph messages
  were stored in the repository.
- This does not make placeholder agents real evidence.

## 2026-06-18 - Phase R8-13N-QA static target closure

### Changed

- Added the R8-13N L3 explanation synthesizer and its unit test to
  `scripts/quality/run_quality.py --mode static` ruff targets.
- Added quality-runner regression coverage so the L3 explanation surface stays
  in the maintained static gate.
- Updated quality documentation for the R8-13N static coverage boundary.

### Validated

- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `.venv/bin/python -m pytest tests/unit_tests/test_quality_runner_codespell.py -q`

### Not Done

- No runtime behavior changed.
- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No provider, `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint
  was called.

## 2026-06-18 - Phase R8-13N default-off L3 explanation synthesis

### Added

- Added `fixed_dag_l3_explanation_synthesizer.py` as a default-off L3 language
  explanation seam. It reads only public-safe L2 conclusions and deterministic
  L3 composite results, then may add bounded Chinese `research_points` and
  `provenance.llm_explanation` to L3 outputs.
- Added `Context.enable_llm_l3_explanation` /
  `ENABLE_LLM_L3_EXPLANATION=1` and optional
  `Context.llm_l3_explanation_model` / `LLM_L3_EXPLANATION_MODEL`.
- Wired the explanation step after deterministic/external-overlaid L3 results
  and before decision/report generation so `report_input_bundle_v1` can carry
  the L3 explanation material.
- Added unit coverage for default-off env behavior, public-safe prompt
  construction, language-only L3 enrichment, missing-credential preflight, and
  executor propagation into the report input bundle.

### Changed

- Execution provenance now records `llm_l3_explanation_*` fields separately
  from `llm_report_synthesis_*` fields. Public `provider_invoked` remains true
  only when an explicit model-backed seam actually invokes the configured
  provider.
- Updated contracts, architecture notes, ADRs, and the Chinese report plan to
  make L3 LLM usage language-only and non-authoritative for fusion.

### Validated

- `python3 -m pytest tests/unit_tests/test_fixed_dag_l3_explanation_synthesizer.py tests/unit_tests/test_fixed_dag_executor.py::test_llm_l3_explanation_enriches_l3_without_overriding_fusion -q`
- `python3 -m pytest tests/unit_tests/test_fixed_dag_l3_explanation_synthesizer.py tests/unit_tests/test_fixed_dag_executor.py::test_llm_l3_explanation_enriches_l3_without_overriding_fusion tests/unit_tests/test_fixed_dag_executor.py::test_llm_report_synthesis_reads_external_agent_evidence tests/unit_tests/test_fixed_dag_contracts.py::test_l3_composites_project_partial_research_material_from_available_l2 -q`
- `python3 -m pytest tests/unit_tests/test_fixed_dag_executor.py tests/unit_tests/test_fixed_dag_l3_explanation_synthesizer.py tests/unit_tests/test_fixed_dag_report_synthesizer.py tests/unit_tests/test_fixed_dag_contracts.py tests/integration_tests/test_graph.py -q`
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `.venv/bin/python -m ruff check src/react_agent/fixed_dag_l3_explanation_synthesizer.py tests/unit_tests/test_fixed_dag_l3_explanation_synthesizer.py src/react_agent/context.py src/react_agent/fixed_dag_executor.py tests/unit_tests/test_fixed_dag_executor.py`

### Not Done

- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called.
- No real provider was invoked in this phase; tests use fake models or
  missing-credential preflight.
- The L3 explanation layer does not override deterministic `stance`,
  `confidence`, `status`, `gate`, `risk_score`, `dimension_weights`, member
  weights, or contributing agents.
- This does not make placeholder agents real evidence.

## 2026-06-17 - Phase R8-13M fallback report evidence-focused rendering

### Changed

- Tightened fallback report rendering so the final Chinese report expands only
  L2 outputs with public-safe report material or error status.
- Kept no-evidence placeholder/pending L2 entries in `report_input_bundle_v1`
  and workflow trace, but summarized them as missing coverage instead of
  rendering each placeholder as a pseudo research line.
- Replaced the long per-agent task-instruction dump in fallback reports with a
  compact `agent_task_v1` orchestration overview. Full task summaries remain in
  `report_input_bundle_v1`.
- Updated contracts and the Chinese report-improvement plan for the new report
  rendering boundary.

### Not Done

- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No `/v1/agent/invoke` endpoint was called.
- No placeholder agent was promoted to real evidence.

## 2026-06-17 - Phase R8-13L deterministic L3 report material projection

### Changed

- Added deterministic L3 material projection from available L2 conclusions.
  Value and market composites now expose confidence-weighted direction member
  material; risk composite exposes a bounded risk gate from risk-member
  `risk_score`; macro composite records missing macro coverage and keeps
  default value/market weights when macro evidence is unavailable.
- Added L3 `member_weight_summary`, `domain_metrics`, `drivers`,
  `research_points`, and `data_quality` provenance for report input bundles.
- Kept placeholder and pending members at weight `0`; L3 composites only become
  `partial` or `complete` when selected L2 members have usable output.
- Preserved the risk/sentiment boundary: `risk_composite` only reads risk L2
  members and does not consume `sentiment_company_radar`.
- Updated contracts, architecture notes, and the Chinese report-improvement
  plan for the deterministic L3 projection boundary.

### Validated

- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_contracts.py -q`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_executor.py tests/unit_tests/test_fixed_dag_report_synthesizer.py tests/integration_tests/test_graph.py -q`

### Not Done

- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called.
- No provider was invoked; L3 language explanation remains default-off future
  work and cannot override deterministic fusion fields.
- This does not make placeholder L2/L3 agents real evidence.

## 2026-06-17 - Phase R8-13K report material projection backfill

### Changed

- Backfilled the sandbox-proven main-system report material layer into dev.
- Extended the fixed-DAG external adapter so mapped external L2/L3 outputs can
  project bounded `domain_metrics`, `drivers`, `research_points`, and
  `data_quality` into provenance without preserving raw external JSON.
- Extended `agent_evidence_bundle_v1` and fallback report rendering so final
  reports prefer detailed L2/L3 evidence bundle entries over compact summaries
  and can display research judgments, key evidence, metrics, drivers, data
  quality, and L3 member previews.
- Added L3 quality counts for `partial`, `error`, and available outputs so
  demo reports distinguish partial L3 availability from missing L3 output.
- Added `Context.fixed_dag_as_of` and wired it through fixed-DAG plan creation
  plus the R8-13A smoke runner.
- Added secret-free LLM report provider preflight diagnostics; missing
  DeepSeek/OpenAI credentials now short-circuit without provider invocation.
- Fixed default-off demo bridge upstream projection for risk `gate_member`
  outputs so bounded `provenance.risk_score` can reach `risk_composite`.
- Added `docs/报告完善计划（中文）.md` documenting the report-material plan and
  the boundary that L3 may use LLM only for language explanation/conflict
  summarization, not deterministic fusion decisions.
- Began Phase 2 sandbox service wrapper alignment by comparing prod and
  sandbox copies of `value_traditional_valuation`, `market_stock_technical`,
  and `risk_compliance_review`; preserved prod-only traditional valuation
  top-level `stance` / `confidence` direction projection, `assumptions` /
  `method_details` fields, and the related explanatory evidence in the
  sandbox service copy.

### Validated

- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_report_synthesizer.py tests/unit_tests/test_fixed_dag_executor.py tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/integration_tests/test_graph.py -q`
- Static compilation of the three sandbox service wrapper files touched or
  audited for Phase 2.
- Sandbox service-local contract tests in isolated temporary environment
  `/tmp/lma-service-test-venv`:
  `传统企业估值智能体/tests/test_domain_contract_v1.py` (7 passed),
  `个股技术分析智能体/tests/test_domain_contract_v1.py -k 'not invoke'`
  (9 passed, 1 deselected), and
  `公告合规审查智能体/announcement_compliance/agent/tests/test_domain_contract.py`
  (11 passed).
- Controlled sandbox compute demo artifact:
  `/tmp/lma-phase3-sandbox-compute-demo/20260617T1510Z`.
  The demo used dev main-system code plus sandbox service TestClient
  `/v1/agent/compute` handlers for `value_traditional_valuation`,
  `market_stock_technical`, and `risk_compliance_review`; all three mapped
  into `agent_evidence_bundle_v1` with `research_points`, `domain_metrics`,
  `drivers`, `data_quality`, and `evidence_items`.

### Not Done

- No `runtime_bindings.json` field was changed.
- No `live_verified` or `invoke_enabled_by_default` flag was changed.
- No live runtime `/health` or `/v1/agent/invoke` endpoint was called.
- No production external agent service source was modified in this phase.
- No external `/v1/agent/invoke` was called; the technical-analysis service
  `/invoke` TestClient case was explicitly deselected.
- The controlled demo report remains `partial`: only 3/18 L2 are real complete
  outputs, 15 L2 are placeholder/partial, and 0/4 L3 composites are available.
- The controlled demo used provider-missing fallback report synthesis; it did
  not prove a real LLM report provider.
- This does not make placeholder agents real evidence.
- This does not let LLM override L3 fusion fields such as gate, risk score,
  stance, dimension weights, member weights, or confidence.

## 2026-06-17 - Documentation clarification for external agent repo ownership

### Changed

- Clarified in the repository environment guide that
  `/sdb/dlut/dev/langgraph-my-agent` is the main-system dev authority, while
  other `/sdb/dlut/dev/*` agent repositories are owned by their corresponding
  developers.
- Documented that user sandbox agent experiments may be synchronized by the
  user to prod, while other developers synchronize their own dev-agent changes
  to prod through their service workflows.
- Updated README, roadmap, docs index, and ADR wording so future sessions do
  not treat external agent dev repositories as main-system writable authority.

### Not Done

- No runtime binding was enabled.
- No live flags were set.
- No endpoint was called.
- No production service source was modified.
- No external agent repository was modified.

## 2026-06-17 - Phase R8-13J next phase roadmap

### Changed

- Added `docs/NEXT_PHASE_ROADMAP_FIXED_DAG.md` as the current roadmap entry
  point for new Codex sessions and project planning.
- Consolidated current progress, A/B/C agent work classes, P0/P1/P2/P3/P4
  next work, medium/long-term runtime preparation, documentation cleanup
  guidance, and a copy-ready new-session Codex prompt.
- Updated README and docs index so the roadmap is discoverable alongside the
  repository environment guide and readiness matrix.

### Not Done

- No runtime binding was enabled.
- No live flags were set.
- No endpoint was called.
- No production service source was modified.
- No phase-record document was deleted or archived.

## 2026-06-17 - Phase R8-13I repository environment and docs authority guide

### Changed

- Added `docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md` to define the main-system
  `dev`, `sandbox`, and `prod` directory roles on this server.
- Documented the expected sync flow: sandbox experiments are reviewed and
  backfilled into dev, dev commits are pushed to GitHub, and prod is updated
  from a stable pushed commit.
- Added a documentation authority map that separates current authority docs
  from phase-record docs and future merge candidates.
- Updated README and docs index so the new environment/docs guide is discoverable.

### Not Done

- No runtime binding was enabled.
- No live flags were set.
- No `/v1/agent/invoke` evidence was created.
- No external production agent service source was moved into the main-system
  repository.

## 2026-06-12 - Phase R8-13H sandbox A-class L1/L2 bridge integration

### Changed

- Extended the default-off external compute demo bridge in the sandbox so L1
  `financial_data_service` and `entity_relation_extractor` compute results can
  map into the executor before L2 `agent_task_v1` construction.
- Added sandbox demo registry entries for `macro_commodity_pricing` and
  `macro_index_valuation` as macro L2 `agent_conclusion_v1` candidates.
- Preserved the existing default-off behavior: no HTTP call is made unless
  `ENABLE_EXTERNAL_COMPUTE_DEMO=1` and the agent is explicitly allowlisted.
- Added unit coverage for L1 data/entity bundle mapping, L1-before-L2 task
  propagation, and macro L2 A-class registry overlays.
- Extended the offline R8-13A trace runner with `data_bundle_v1` and
  `entity_relation_bundle_v1` fixtures so A-class sandbox traces can exercise
  L1 evidence without calling endpoints.

### Evidence

- This phase ports sandbox-validated implementation and test evidence into the
  default-off demo path. It does not record production readiness evidence.
- Targeted sandbox checks:
  `ruff check src/react_agent/fixed_dag_external_compute_bridge.py src/react_agent/fixed_dag_executor.py tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_fixed_dag_executor.py`
  and
  `pytest tests/unit_tests/test_fixed_dag_external_compute_bridge.py tests/unit_tests/test_fixed_dag_executor.py -q`.
- Offline fixture trace:
  `/tmp/lma-r8-13h-a-class-offline-trace/20260612T095736Z`.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No runtime binding or live flag was changed.
- No production service source was modified.
- No production default external invocation was enabled.

## 2026-06-12 - Phase R8-13G value L2 stance remediation

### Changed

- Backfilled top-level `stance` / `confidence` protocol projections in the
  three production value L2 valuation service wrappers:
  `value_traditional_valuation`, `value_ml_valuation`, and
  `value_meta_valuation`.
- Added service-local contract tests to prevent future
  `direction_stance_missing` regressions.
- Documented the service-side wrapper changes in the affected service
  directories and added `docs/R8_13G_VALUE_L2_STANCE_REMEDIATION.md`.

### Evidence

- Service backup root:
  `/tmp/lma-r8-13g-value-l2-stance-backfill/20260612T033501Z`.
- Restart log root:
  `/tmp/lma-r8-13g-value-l2-restart/20260612T033801Z`.
- Production re-smoke artifact:
  `/tmp/lma-r8-13g-value-l2-resmoke/20260612T033846Z`.
- Configured-report E2E trace:
  `/tmp/lma-r8-13g-prod-e2e-llm-report/20260612T033912Z`.
- All three value L2 services passed production `/health`, production
  `/v1/agent/compute`, and main-system adapter mapping.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No runtime binding or live flag was changed.
- No default graph production invocation was enabled.
- Valuation models, feature engineering, scoring algorithms, data files, and
  deployment configuration were not changed.

## 2026-06-12 - Phase R8-13F end-to-end production trace QA

### Changed

- Restored the sandbox-proven main-system `agent_task_v1` and
  `agent_evidence_bundle_v1` trace path in this branch.
- Extended the default-off compute bridge so allowlisted L3 production compute
  requests receive bounded current-run L2 `context.upstream_outputs`.
- Added `scripts/dev/run_r8_13a_e2e_smoke.py` as a reusable trace runner for
  offline fixture mode or explicitly enabled real production compute mode.
- Updated unit coverage for agent tasks, evidence bundles, L3 upstream output
  propagation, task-aware placeholders, and executor trace projection.
- Added `docs/R8_13F_END_TO_END_PRODUCTION_TRACE_QA.md`.

### Evidence

- Real production compute with fake report model:
  `/tmp/lma-r8-13f-prod-e2e/20260612T030650Z`.
- Real production compute with configured LLM report model:
  `/tmp/lma-r8-13f-prod-e2e-llm-report/20260612T030735Z`.
- The configured-report run mapped 17 production compute agents, used 5
  explicit placeholder L2 slots, and generated a natural Chinese report from
  `report_input_bundle_v1`.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No runtime binding or live flag was changed.
- No default graph production invocation was enabled.
- Raw external responses, endpoint URLs, credentials, and provider raw output
  were not stored in the repository.

## 2026-06-12 - Phase R8-13E production L3 backfill and smoke

### Changed

- Applied the R8-13D reviewed protocol-wrapper patches to the four production
  L3 composite service directories:
  `value_composite`, `market_composite`, `risk_composite`, and
  `macro_composite`.
- Added support for `context.upstream_outputs` in the production L3 services so
  they can synthesize L3 payloads from the current run's L2 outputs.
- Added focused service tests for the upstream-output wrapper behavior where
  needed.
- Added `docs/R8_13E_PRODUCTION_L3_BACKFILL_SMOKE.md` with changed files,
  backup path, validation, restart, smoke artifacts, rollback, and non-claims.

### Evidence

- Backup root:
  `/tmp/lma-r8-13e-prod-l3-backfill/20260612T024513Z`.
- Restart log root:
  `/tmp/lma-r8-13e-prod-l3-restart/20260612T024553Z`.
- Smoke artifact root:
  `/tmp/lma-r8-13e-prod-l3-smoke/20260612T024649Z`.
- All four L3 services passed production `/health`, production
  `/v1/agent/compute`, and main-system adapter mapping.

### Not Done

- No `/v1/agent/invoke` endpoint was called.
- No runtime binding or live flag was changed.
- No default graph production invocation was enabled.
- Business models, feature engineering, scoring algorithms, data files, and
  deployment configuration were not changed.

## 2026-06-12 - Phase R8-13D sandbox L3 backfill handoff package

### Changed

- Generated the R8-13D handoff package under
  `/tmp/lma-r8-13d-handoff-package/20260612T023822Z`.
- Packaged the sandbox main-system patch from
  `e030d57 feat(demo): pass l2 evidence to sandbox l3 composites`.
- Packaged reviewable candidate service patches for the four L3 composite
  services:
  `value_composite`, `market_composite`, `risk_composite`, and
  `macro_composite`.
- Copied the sanitized R8-13C E2E trace artifacts into the package:
  `summary.json`, `final_report.md`, `agent_tasks.json`,
  `agent_evidence_bundle.json`, and `workflow_trace.json`.
- Added `docs/R8_13D_SANDBOX_L3_BACKFILL_HANDOFF.md` with the service-by-service
  modification summary, safe production backfill sequence, validation,
  rollback, and non-claims.

### Not Done

- No production service directory was modified.
- No endpoint was called during package generation.
- No `/v1/agent/invoke` call was made.
- No runtime binding or live flag was changed.
- The package is a review/handoff artifact, not production readiness.

## 2026-06-11 - Phase R8-12D version anchor and fallback boundary note

### Changed

- Added local version-management documentation for tag
  `r8-12d-llm-report-synthesizer-fallback`.
- Clarified that the current LLM report synthesizer is a main-system
  fallback/demo seam, not the final external `report_generator` agent
  integration.
- Documented the intended future handoff: `report_generator` should consume
  `report_input_bundle_v1` and return `report_result_v1` through the
  external-agent contract.

### Not Done

- No endpoint was called.
- No runtime binding or live flag was changed.
- No production deployment or push was performed.

## 2026-06-11 - Phase R8-12D LLM report synthesizer with active evidence

### Changed

- Added `Context.enable_llm_report_synthesis` and optional
  `llm_report_synthesis_model` / `LLM_REPORT_SYNTHESIS_MODEL`.
- Added `fixed_dag_report_synthesizer.py`, a default-off report generator that
  passes only `report_input_bundle_v1` to the configured chat model and expects
  a validated `report_result_v1` response.
- Wired the synthesizer into `execute_fixed_dag_plan` after L2/L3 evidence
  mapping and report bundle construction.
- Allowed public workflow provenance to mark `providerInvoked=true` only when
  the explicit LLM report synthesis path invokes the configured model.
- Updated the demo runbook and docs to distinguish template report fallback
  from natural-language LLM report synthesis.

### Validated

- `.venv/bin/python -m ruff check src/react_agent tests`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_report_synthesizer.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py -q`
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No real provider was called during validation.
- No production endpoint was called during validation.
- No external agent `/v1/agent/invoke` endpoint was called.
- No runtime binding or live flag was changed.
- No production main-system deployment was performed in this commit.

## 2026-06-11 - Phase R8-12C report generator evidence bundle integration

### Changed

- Added `report_input_bundle_v1` as the public-safe input package consumed by
  the fixed DAG report generator.
- Wired report generation to L2 agent summaries, L3 composite summaries, risk
  gate summary, macro regulator summary, and decision context.
- Projected bounded `agent_evidence` and `composite_evidence` summaries into
  `workflow_snapshot_v2.stepResults` for Web workflow details.
- Updated the Web workflow step details view to show the report-consumed agent
  and composite summaries when present.

### Validated

- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py -q`
- `.venv/bin/python -m ruff check src/react_agent tests`
- `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`
- `npm --prefix apps/web run test`
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No production endpoint was called.
- No `/v1/agent/invoke` endpoint was called.
- No runtime binding or live flag was changed.
- No raw external response, endpoint URL, secret, error stack, or internal
  reasoning draft is stored in the report bundle or public workflow.
- No production main-system deployment was performed in this commit.

## 2026-06-11 - Phase R8-12B local remote agent demo tunnel tooling

### Changed

- Added Bash and PowerShell SSH tunnel helpers for local same-port access to
  the 16 R8-12 production compute demo agents.
- Added a local allowlist example JSON for the SSH tunnel setup. This file is
  documentation/config sample only and is not a runtime binding source.
- Added a Chinese local remote-agent demo runbook covering tunnel startup,
  local API/Web startup, security boundaries, troubleshooting, and shutdown.
- Updated README, docs index, quality notes, and ADR documentation for the
  local remote-agent demo boundary.

### Validated

- `bash -n scripts/dev/start_agent_tunnels.sh`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode static`

### Not Done

- No push.
- No SSH tunnel was started.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` endpoint was called.
- No `.env` file or runtime binding was modified.
- No production port is exposed publicly by the helper scripts.

## 2026-06-11 - Phase R8-12 default-off external compute demo integration

### Changed

- Added `Context.enable_external_compute_demo`,
  `external_compute_demo_allowlist`, and
  `external_compute_demo_timeout_seconds`.
- Added `fixed_dag_external_compute_bridge.py`, a default-off demo bridge that
  calls only allowlisted loopback production `/v1/agent/compute` endpoints and
  maps responses through the provider-free fixed-DAG adapter.
- Integrated mapped L2/L3 compute results into `execute_fixed_dag_plan` behind
  the explicit demo flag and allowlist while preserving deterministic behavior
  when flags are off.
- Added a Chinese demo report/workflow summary and a runbook for local
  API/Web demo startup.

### Validated

- `.venv/bin/python -m ruff check src/react_agent tests`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_external_compute_bridge.py -q`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py -q`

### Not Done

- No push.
- No `/v1/agent/invoke` call from the bridge.
- No runtime binding change.
- No live flag change.
- No default external invocation.
- No raw external response stored in the repo.

## 2026-06-11 - Phase R8-11B first controlled production invoke smoke

### Changed

- Ran the first tiny allowlist controlled production `/v1/agent/invoke` smoke
  after source-level invoke audit.
- Recorded controlled invoke + adapter mapping evidence for
  `risk_identification`, `risk_compliance_review`, `risk_crash`,
  `risk_financial_fraud`, and `value_research_synthesis`.
- Kept the smoke on production endpoints only and used no-LLM style options
  (`allow_llm=false` plus service-compatible structured/template flags).
- Updated README, readiness matrix, controlled smoke log, readiness ladder,
  quality, changelog, and ADR documentation for the R8-11B boundary.

### Validated

- Controlled production invoke smoke artifact:
  `/tmp/lma-r8-11b-prod-invoke-smoke/20260611T022513Z`.
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No default graph invocation.
- No public transcript update.

## 2026-06-11 - Phase R8-8Q production remediation and re-smoke

### Changed

- Remediated bounded production protocol wrapper issues for selected L1/L2
  services without changing main-system runtime bindings or adapter gates.
- Recorded production `/health` + `/v1/agent/compute` + adapter mapping
  evidence for `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, `value_research_synthesis`,
  `market_stock_technical`, `market_capital_flow_chip`,
  `sentiment_company_radar`, and `market_ipo_investor_behavior`.
- Kept `sentiment_company_radar` market-only and explicitly excluded risk
  routing.
- Recorded `financial_data_service` and `macro_commodity_pricing` as still
  requiring production remediation.
- Updated README, readiness matrix, controlled smoke log, readiness ladder,
  quality, developer prompts, changelog, and ADR documentation for the R8-8Q
  boundary.

### Validated

- Service changed-file `py_compile` for the remediated production service
  wrappers.
- Controlled production smoke artifact:
  `/tmp/lma-r8-8q-prod-resmoke/20260611T020302Z`.
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No provider call.
- No `/v1/agent/invoke` call.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No public transcript update.
- No production default invocation readiness claim.

## 2026-06-10 - Phase R8-10F value composite production remediation

### Changed

- Remediated `value_composite` production health identity on port `10015` so
  `/health` identifies the L3 value composite service instead of the value-ML
  sample identity.
- Preserved and verified the existing
  `external_agent_compute_v0.tool_result.dimension_conclusion_v1` production
  compute wrapper for `value_composite`.
- Recorded production health + compute + adapter mapping evidence for
  `value_composite`.
- Updated README, readiness matrix, controlled smoke log, readiness ladder,
  quality, changelog, and ADR documentation for the R8-10F boundary.

### Validated

- `python3 -m py_compile service.py schemas.py tests/test_fixed_dag_l3_wrapper.py`
  in `/sdb/dlut/prod/综合估值智能体`.
- `python3 -m pytest tests/test_fixed_dag_l3_wrapper.py -q` in
  `/sdb/dlut/prod/综合估值智能体`.
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No provider call.
- No `/v1/agent/invoke` call.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No public transcript update.
- No production default invocation readiness claim.

## 2026-06-10 - Phase R8-10E L3 production controlled compute smoke

### Changed

- Recorded authorized controlled restart and production L3 `/health` +
  `/v1/agent/compute` smoke evidence for the four L3 production services.
- Added production compute evidence for `market_composite`, `risk_composite`,
  and `macro_composite`; each mapped through the main-system L3 adapter into
  `dimension_composite_result_v1`.
- Recorded `value_composite` as still blocked by production health identity
  mismatch; compute remained skipped fail-closed.
- Updated readiness matrix, controlled smoke log, readiness ladder, quality,
  README, and ADR documentation for the R8-10E boundary.

### Validated

- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `/v1/agent/invoke` call.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No public transcript update.
- No production default invocation readiness claim.

## 2026-06-10 - Phase R8-10D-SNAPSHOT L3 service shadow handoff repository

### Changed

- Added service-local `FIXED_DAG_PROTOCOL_BACKFILL.md` notes beside the four L3
  production service directories so service owners can see fixed DAG identity,
  expected L3 payload, changed files, backup manifest, and R8-10E restart/smoke
  boundary.
- Created a temporary local shadow handoff repository at
  `/sdb/dlut/service-shadow-repos/l3-composite-services` with service notes,
  the R8-10D manifest, and zero-context protocol patch files.
- Updated README, readiness matrix, developer prompt catalog, quality docs, and
  ADRs to clarify that the shadow repository is a handoff artifact, not the
  long-term source of truth and not production readiness evidence.

### Validated

- Shadow repo initialized on branch `main` with commit
  `7a3c517 chore(snapshot): capture l3 protocol backfill handoff`.
- Sensitive-pattern scan reviewed at file/line classification level; no raw
  secret value was intentionally copied into the shadow handoff repo.
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`

### Not Done

- No push.
- No endpoint call.
- No service restart.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No production readiness evidence.

## 2026-06-10 - Phase R8-10D L3 service protocol wrapper backfill

### Changed

- Backfilled bounded fixed DAG L3 protocol wrappers in the four L3 service
  directories for `value_composite`, `market_composite`, `risk_composite`, and
  `macro_composite`.
- Recorded repo-external service backups and patch manifest at
  `/tmp/lma-r8-10d-l3-service-backup/20260610T142216Z/service_patch_manifest.json`.
- Updated readiness matrix, developer prompts, payload mapping, readiness
  ladder, quality, README, and ADR documentation to show that L3 wrappers are
  locally backfilled but not smoke verified.

### Validated

- Service changed-file `py_compile` for all four L3 service directories.
- Focused service pytest coverage for value, market, risk, and macro L3 wrapper
  behavior.
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/health` call.
- No `/v1/agent/compute` call.
- No `/v1/agent/invoke` call.
- No prod or dev endpoint call.
- No service start, stop, or restart.
- No main-system `src/`, `config/`, runtime binding, graph, executor, public
  API/runtime/mapping, frontend, or active runtime integration change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No L3 production readiness evidence; controlled L3 smoke remains R8-10E.

## 2026-06-10 - Phase R8-10C L3 service protocol backfill audit

### Changed

- Added an R8-10C L3 service protocol backfill audit to the fixed DAG readiness
  matrix for `value_composite`, `market_composite`, `risk_composite`, and
  `macro_composite`.
- Added service-owner prompt entries for each L3 composite service so owners
  can backfill `dimension_conclusion_v1`, `risk_conclusion_v1`, or
  `macro_conclusion_v1` without changing main-system runtime bindings.
- Clarified that R8-10C does not call endpoints, does not modify services, does
  not enable runtime bindings, and does not create L3 production readiness
  evidence.

### Validated

- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

## 2026-06-10 - Phase R8-10B L3 composite adapter mapping

### Changed

- Added provider-free pure adapter mappings for L3 payloads:
  `dimension_conclusion_v1`, `risk_conclusion_v1`, and
  `macro_conclusion_v1`.
- Added direct, `external_agent_compute_v0.tool_result`, and
  `external_agent_response_v0.tool_result` dispatch for those L3 payloads into
  `dimension_composite_result_v1`.
- Unified deterministic macro composite placeholder weights to `value` and
  `market` only, matching the R8-10A/R8-10B macro regulator decision.
- Added L3 adapter and contract unit tests for value/market members, risk
  gates, manual review, macro value/market weights, envelope dispatch, and safe
  provenance.
- Updated contract, payload mapping, sample, readiness, developer prompt,
  matrix, quality, README, and ADR documentation for the L3 pure mapping
  boundary.

### Validated

- `.venv/bin/python -m ruff check src/react_agent/fixed_dag_external_adapter.py src/react_agent/fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_contracts.py`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_contracts.py -q`
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/health` call.
- No `/v1/agent/compute` call.
- No `/v1/agent/invoke` call.
- No prod or dev port access.
- No service start, stop, or restart.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No active L3 runtime integration.
- No graph, executor, public API, public runtime, public mapping, frontend, or
  external service code change.
- No adapter test is treated as live readiness.

## 2026-06-10 - Phase R8-8P-DOCS-QA production readiness problem playbook

### Changed

- Deepened `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` from a production status
  matrix into a production problem playbook with per-agent current status,
  production test result, problem type, failure cause, impact, service-owner
  action, main-system maintainer action, resmoke boundary, and prompt id.
- Rewrote `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` as a Chinese,
  copy-ready production remediation prompt catalog with agent-specific prompts
  for health, endpoint, identity, compute wrapper, semantic-decision, L3/L4
  design, and invoke-audit-prep work.
- Tightened wording from broad "production pass" language to production
  health+compute+adapter pass candidates where applicable.
- Added ADR-045 for turning production failures into developer remediation
  prompts without changing runtime behavior.

### Validated

- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/health` call.
- No `/v1/agent/compute` call.
- No `/v1/agent/invoke` call.
- No prod or dev port access.
- No service start, stop, or restart.
- No production service code modification.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No adapter logic change.
- No graph, executor, public API, public runtime, public mapping, frontend, or
  fixed DAG roster change.

## 2026-06-10 - Phase R8-8P production endpoint readiness rebaseline

### Changed

- Rebaselined fixed DAG readiness against production endpoints instead of
  dev-only controlled smoke evidence.
- Rewrote `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` as a production-first
  matrix with production endpoint status, production health/compute/adapter
  results, dev-historical appendix, and production next actions.
- Rewrote `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` as a production-first
  prompt catalog for health, compute, identity, adapter, backfill, semantic
  deferral, L3/L4 design, and invoke-audit-prep work.
- Recorded R8-8P production artifact root in
  `docs/CONTROLLED_READINESS_SMOKE_LOG.md`.
- Added ADR-044 for separating production evidence from previous dev evidence.

### Validated

- Production smoke artifact root:
  `/tmp/lma-r8-8p-prod-readiness/20260610T104456Z`.
- Production pass agents:
  `risk_identification`, `risk_compliance_review`, `risk_financial_fraud`,
  `risk_crash`, and `macro_analysis`.
- `.venv/bin/python -m ruff check src/react_agent/fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_adapter.py || true`
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No dev endpoint counted as production evidence.
- No production service code modification.
- No service start, stop, or restart.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend, or
  fixed DAG roster change.
- No production default invocation claim.

## 2026-06-10 - Phase R8-8N-DOCS agent readiness matrix persistence

### Changed

- Added `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` as the formal persisted
  fixed DAG readiness matrix for the full 27-agent roster.
- Added `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` as the copy-ready
  developer prompt catalog for service owners and coding agents.
- Linked the new readiness handoff docs from `README.md` and `docs/INDEX.md`.
- Updated readiness, quality, and decision docs to keep the R8-8N-DOCS
  boundary explicit.

### Validated

- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/health` call.
- No `/v1/agent/compute` call.
- No `/v1/agent/invoke` call.
- No prod port access.
- No service start, stop, or restart.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend,
  adapter logic, external service code, or fixed DAG roster change.
- No production readiness claim.

## 2026-06-10 - Phase R8-8N agent readiness matrix handoff

### Changed

- Added `docs/AGENT_READINESS_MATRIX_R8_8N.md` as the developer handoff for the
  full 27-agent readiness audit.
- Consolidated fixed DAG roster truth, controlled compute evidence, deferred
  agents, service patch backfill inventory, and copy-ready developer prompts.
- Kept the R8-8N boundary explicit: controlled compute evidence is not
  production readiness and does not imply `/v1/agent/invoke`, runtime binding
  enablement, `live_verified=true`, or `invoke_enabled_by_default=true`.

### Validated

- Documentation-only change.

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No endpoint call.
- No `/v1/agent/invoke` call.
- No prod port access.
- No runtime binding change.
- No live flag change.
- No graph, executor, public API, public runtime, public mapping, frontend, or
  fixed DAG roster change.

## 2026-06-10 - Phase R8-8M remaining L2 controlled compute coverage

### Changed

- Recorded sanitized controlled readiness evidence for
  `market_capital_flow_chip` after R8-8M dev-only health, compute, and
  provider-free adapter mapping checks.
- Documented bounded dev service protocol remediation for fixed-DAG identity,
  external service id preservation, canonical market dimension, and L2
  `agent_conclusion_v1 role=direction` output normalization.
- Recorded explicit deferred reasons for the remaining R8-8M candidates:
  unsupported IPO scaffold/business output, commodity dev listener and compute
  endpoint gap, macro-index semantic uncertainty, macro regulator payloads, and
  missing non-stub fund-manager service metadata.
- Added ADR-042 for extending remaining L2 controlled compute evidence without
  runtime enablement.
- Kept runtime bindings, live flags, graph, executor, public API, frontend,
  fixed DAG roster, L3/L4 active runtime, and public transcript unchanged.

### Validated

- `market_capital_flow_chip` service validation before smoke:
  `python3 -m py_compile service.py schemas.py compute_core.py agents/money_flow_agent.py`
- Controlled dev smoke for the R8-8M passing candidate:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.
- R8-8M deferred candidates were not called at `/health` or `/v1/agent/compute`.

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No prod port smoke.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend,
  L3/L4 active runtime, or fixed DAG roster change.
- No public transcript update.
- No production readiness claim.

## 2026-06-10 - Phase R8-8L remaining risk and market controlled compute evidence

### Changed

- Recorded sanitized controlled readiness evidence for `risk_financial_fraud`
  and `risk_crash` after R8-8L dev-only health, compute, and provider-free
  adapter mapping checks.
- Documented bounded dev service protocol remediations for fixed-DAG identity,
  external service id preservation, canonical risk dimension, and L2
  `agent_conclusion_v1 role=gate_member` output normalization.
- Recorded that the remaining market/macro candidates in the R8-8L queue were
  deferred when the dev listener was absent, the response builder was not a
  small fixed-DAG L2 wrapper, or the service semantics did not clearly support
  the requested fixed-DAG dimension.
- Added ADR-041 for recording remaining risk and market controlled compute
  evidence without runtime enablement.
- Kept runtime bindings, live flags, graph, executor, public API, frontend,
  fixed DAG roster, L3/L4 active runtime, and public transcript unchanged.

### Validated

- `risk_financial_fraud` service validation before smoke:
  `python3 -m py_compile app/main.py app/schemas.py`
- `risk_crash` service validation before smoke:
  `python3 -m py_compile crash_risk_model/agent/app.py crash_risk_model/agent/protocol.py`
- Controlled dev smoke for both R8-8L risk candidates:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No prod port smoke.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend,
  L3/L4 active runtime, or fixed DAG roster change.
- No public transcript update.
- No production readiness claim.

## 2026-06-10 - Phase R8-8K entity and risk controlled compute evidence

### Changed

- Recorded sanitized controlled readiness evidence for
  `entity_relation_extractor`, `risk_identification`, and
  `risk_compliance_review` after R8-8K dev-only health, compute, and
  provider-free adapter mapping checks.
- Added provider-free adapter support for
  `external_agent_compute_v0.tool_result.entity_relation_bundle_v1 ->
  entity_relation_bundle_v1` so L1 entity-relation compute envelopes can be
  validated without HTTP/provider calls or active graph integration.
- Documented bounded dev service protocol remediations for fixed-DAG identity,
  external service id preservation, entity-relation bundle wrapping, and risk
  L2 `gate_member` output normalization.
- Added ADR-040 for extending controlled entity-relation and risk compute
  evidence without runtime enablement.
- Kept runtime bindings, live flags, graph, executor, public API, frontend,
  fixed DAG roster, L3/L4 active runtime, and public transcript unchanged.

### Validated

- Main-system adapter validation:
  `.venv/bin/python -m ruff check src/react_agent/fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_adapter.py`
- Main-system adapter tests:
  `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py -q`
- `entity_relation_extractor` service validation before smoke:
  `python3 -m py_compile entity_relation_agent/service.py entity_relation_agent/schemas.py`
- `risk_identification` service validation before smoke:
  `python3 -m py_compile market_risk_model/agent/app.py market_risk_model/agent/protocol.py`
- `risk_compliance_review` service validation before smoke:
  `python3 -m py_compile announcement_compliance/agent/app.py announcement_compliance/agent/protocol.py`
- Controlled dev smoke for all three R8-8K candidates:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No prod port smoke.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend,
  L3/L4 active runtime, or fixed DAG roster change.
- No public transcript update.
- No production readiness claim.

## 2026-06-10 - Phase R8-8J controlled compute evidence expansion

### Changed

- Recorded sanitized controlled readiness evidence for
  `financial_data_service` after R8-8J dev-only health, compute, and
  provider-free adapter mapping checks.
- Added provider-free adapter support for
  `external_agent_compute_v0.tool_result.data_bundle_v1 -> data_bundle_v1` so
  L1 data-service compute envelopes can be validated without HTTP/provider
  calls or active graph integration.
- Documented the bounded dev service protocol remediation for
  `financial_data_service`: structured health JSON, fixed-DAG identity, and an
  L1 `data_bundle_v1` compute wrapper.
- Added ADR-039 for expanding controlled compute evidence without runtime
  enablement.
- Kept runtime bindings, live flags, graph, executor, public API, frontend,
  fixed DAG roster, L3/L4 active runtime, and public transcript unchanged.

### Validated

- Main-system adapter validation:
  `.venv/bin/python -m ruff check src/react_agent/fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_adapter.py`
- Main-system adapter tests:
  `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py -q`
- `financial_data_service` service validation before smoke:
  `python3 -m py_compile app/main.py`
- `financial_data_service` controlled dev smoke:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode static`
- Main repo validation:
  `git diff --check`
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No prod port smoke.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend,
  L3/L4 active runtime, or fixed DAG roster change.
- No public transcript update.
- No production readiness claim.

## 2026-06-10 - Phase R8-8I-QA sentiment radar evidence log completion

### Changed

- Completed the R8-8I documentation QA record for
  `sentiment_company_radar` controlled readiness evidence.
- Confirmed the evidence is documented as market-only health, compute, and
  provider-free adapter mapping evidence with no risk routing claim.
- Added ADR-038 for the R8-8I-QA evidence logging completion boundary.
- Kept runtime bindings, live flags, graph, executor, public API, frontend,
  fixed DAG roster, L3/L4 active runtime, and public transcript unchanged.

### Validated

- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode static`
- Main repo validation:
  `git diff --check`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No prod port smoke.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend,
  L3/L4 active runtime, or fixed DAG roster change.
- No public transcript update.
- No production readiness claim.

## 2026-06-10 - Phase R8-8I broaden controlled compute evidence

### Changed

- Recorded sanitized controlled readiness evidence for
  `sentiment_company_radar` after R8-8I dev-only health, compute, and
  provider-free adapter mapping checks.
- Documented the bounded dev service protocol remediation for
  `sentiment_company_radar`: fixed-DAG primary id, external service id,
  structured health identity, and canonical `market` L2 dimension.
- Added ADR-037 for broadening controlled compute evidence without runtime
  enablement.
- Kept runtime bindings, live flags, graph, executor, public API, frontend,
  fixed DAG roster, L3/L4 active runtime, and public transcript unchanged.

### Validated

- `sentiment_company_radar` service validation before smoke:
  `python3 -m py_compile company_radar_agent/service.py company_radar_agent/schemas.py company_radar_agent/tests/conftest.py company_radar_agent/tests/test_service_contract.py`
- `sentiment_company_radar` controlled dev smoke:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode static`
- Main repo validation:
  `git diff --check`
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No prod port smoke.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend,
  L3/L4 active runtime, or fixed DAG roster change.
- No public transcript update.
- No production readiness claim.

## 2026-06-10 - Phase R8-8H expanded controlled compute evidence batch

### Changed

- Recorded sanitized controlled readiness evidence for `value_meta_valuation`,
  `value_research_synthesis`, and `market_stock_technical` after R8-8H dev-only
  health, compute, and provider-free adapter mapping checks.
- Documented bounded dev service protocol remediations for fixed-DAG identity,
  external service id preservation, and canonical L2 dimensions where required.
- Added ADR-036 for recording expanded controlled compute evidence without
  runtime binding enablement.
- Kept runtime bindings, live flags, graph, executor, public API, frontend,
  fixed DAG roster, L3/L4 active runtime, and public transcript unchanged.

### Validated

- `value_meta_valuation` service validation before smoke:
  `python3 -m py_compile service.py tests/test_v21_compliance.py`
- `value_meta_valuation` service validation before smoke:
  `python3 -m pytest tests/test_v21_compliance.py tests/test_domain_contract_v1.py -q`
- `value_meta_valuation` controlled dev smoke:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.
- `value_research_synthesis` service validation before smoke:
  `python3 -m py_compile service.py`
- `value_research_synthesis` service validation before smoke:
  `python3 -m pytest tests/test_service_contract.py tests/test_compute_endpoint.py tests/test_domain_payload.py tests/test_local_data_offline.py -q`
- `value_research_synthesis` controlled dev smoke:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.
- `market_stock_technical` service validation before smoke:
  `python3 -m py_compile service.py schemas.py tests/test_compute_endpoint.py tests/test_domain_contract_v1.py tests/test_service_contract.py`
- `market_stock_technical` service validation before smoke:
  `python3 -m pytest tests/test_service_contract.py tests/test_compute_endpoint.py tests/test_domain_contract_v1.py tests/test_local_data_offline.py -q -p no:cacheprovider`
- `market_stock_technical` controlled dev smoke:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode static`
- Main repo validation:
  `git diff --check`
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No prod port smoke.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend,
  L3/L4 active runtime, or fixed DAG roster change.
- No public transcript update.
- No production readiness claim.

## 2026-06-10 - Phase R8-8G accelerated controlled compute evidence

### Changed

- Recorded sanitized controlled readiness evidence for `macro_analysis` and
  `value_traditional_valuation` after R8-8G dev-only health, compute, and
  provider-free adapter mapping checks.
- Documented that `macro_analysis` required no service patch for controlled
  compute mapping.
- Documented that `value_traditional_valuation` required a bounded dev service
  identity remediation before passing adapter mapping.
- Added ADR-035 for recording additional controlled compute evidence without
  runtime binding enablement.
- Kept runtime bindings, live flags, graph, executor, public API, frontend, and
  fixed DAG roster unchanged.

### Validated

- `macro_analysis` controlled dev smoke:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.
- `value_traditional_valuation` service validation before smoke:
  `python3 -m py_compile service.py tests/test_v21_compliance.py`
- `value_traditional_valuation` service validation before smoke:
  `python3 -m pytest tests/test_v21_compliance.py -q`
- `value_traditional_valuation` service validation before smoke:
  `python3 -m pytest tests/test_domain_contract_v1.py -q`
- `value_traditional_valuation` controlled dev smoke:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode static`
- Main repo validation:
  `git diff --check`
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No prod port smoke.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend, or
  fixed DAG roster change.
- No public transcript update.
- No production readiness claim.

## 2026-06-10 - Phase R8-8E value ML controlled compute evidence

### Changed

- Recorded sanitized controlled readiness evidence for `value_ml_valuation`
  after dev service identity remediation and R8-8D-ID re-smoke.
- Added `docs/CONTROLLED_READINESS_SMOKE_LOG.md` as the internal evidence log
  for controlled health/compute smoke results.
- Updated the readiness ladder, quality boundary, README, and ADR log to state
  that the evidence is health + compute + adapter mapping only.
- Kept the main-system adapter identity gate, runtime bindings, live flags,
  graph, executor, public API, frontend, and fixed DAG roster unchanged.

### Validated

- Dev service validation before smoke:
  `python3 -m py_compile service.py tests/test_v21_compliance.py`
- Dev service validation before smoke:
  `python3 -m pytest tests/test_v21_compliance.py -q`
- Dev service validation before smoke:
  `python3 -m pytest tests/test_service_contract.py -q`
- Controlled dev re-smoke for `value_ml_valuation`:
  `GET /health` pass, `POST /v1/agent/compute` pass, adapter mapping pass.
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode static`
- Main repo validation:
  `git diff --check`
- Main repo validation:
  `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No push.
- No `.env` change.
- No provider call.
- No `/v1/agent/invoke` call.
- No prod port smoke.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend, or
  fixed DAG roster change.
- No public transcript update.
- No production readiness claim.

## 2026-06-09 - Phase R8-8C compute envelope adapter compatibility

### Changed

- Extended the provider-free fixed DAG external adapter to accept
  `external_agent_compute_v0` as adapter input only when it contains a
  supported L2 `agent_conclusion_v1` tool result.
- Added controlled failure handling for compute envelopes that declare a tool
  result schema but lack a concrete `tool_result`.
- Recorded compute-envelope provenance with the adapter input schema and
  compute envelope status while keeping `provider_invoked=false` and
  `external_invoked=false`.
- Added unit coverage for compute-envelope mapping, missing tool results,
  anti-lookahead rejection, identity rejection, unsafe raw-content filtering,
  health payload rejection, and the existing no-HTTP import path.
- Updated README, payload mapping, readiness ladder, quality, and decisions
  docs for the R8-8C adapter-only boundary.

### Validated

- `.venv/bin/python -m ruff check src/react_agent/fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_adapter.py`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py -q`
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No HTTP call.
- No provider call.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` call.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No graph, executor, public API, public runtime, public mapping, frontend, or
  fixed DAG roster change.
- `financial_data_service` remains blocked on structured JSON `/health`.
- `value_ml_valuation` requires R8-8D re-smoke before readiness advancement.

## 2026-06-09 - Phase R8-7B provider-free external adapter mapping

### Changed

- Added `src/react_agent/fixed_dag_external_adapter.py` as a provider-free pure
  mapping layer for already-available fixed-DAG external payload dictionaries.
- Added first-slice mappings for `agent_conclusion_v1 -> conclusion_object_v1`
  and `data_bundle_v1 -> data_bundle_v1`.
- Added controlled adapter failure records for unsupported schemas, invalid
  identity, status errors, anti-lookahead failures, and unsafe mapping cases.
- Added unit tests for direction L2 conclusions, risk gate-member handling,
  status mapping, identity rejection, sentiment-to-risk rejection, unsafe raw
  payload sanitization, data bundle compression, scaffold sample smoke, and no
  HTTP import path.
- Updated README, system map, contracts, quality, external payload mapping,
  readiness ladder, and decisions docs for the R8-7B adapter boundary.

### Validated

- `.venv/bin/python -m ruff check src/react_agent/fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_adapter.py`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py -q`
- `.venv/bin/python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q`
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No HTTP call.
- No provider call.
- No `/health`, `/v1/agent/compute`, or `/v1/agent/invoke` call.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No fixed DAG roster change.
- No active graph or executor live integration.
- No L3/L4 active executor mapping.
- Passing adapter tests does not imply live readiness.

## 2026-06-09 - Phase R8-6B-QA static quality closure

### Changed

- Closed the static quality gate after R8-6B under the server `.venv` Python
  3.14 lint profile.
- Converted static-gate-reported `Optional[...]` annotations in maintained
  public API source to `X | None` style.
- Kept changes type-style only: no public response fields, Pydantic defaults,
  fixed-DAG runtime behavior, internal LLM placeholder behavior, runtime
  bindings, or frontend code changed.

### Validated

- `.venv/bin/python -m ruff check src/react_agent/public_contracts.py src/react_agent/public_store.py`
- `.venv/bin/python scripts/quality/run_quality.py --mode static`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_llm_placeholders.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py -q`
- `git diff --check`
- `.venv/bin/python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No provider/live smoke.
- No external `/v1/agent/invoke` call.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding change.
- No R8-6B runtime semantics change.

## 2026-06-09 - Phase R8-6B default-off internal LLM placeholders

### Changed

- Added `Context.enable_internal_llm_placeholders` with
  `ENABLE_INTERNAL_LLM_PLACEHOLDERS=1` env support through the existing boolean
  parser.
- Added `src/react_agent/fixed_dag_llm_placeholders.py` for bounded internal LLM
  placeholder generation of L2 `conclusion_object_v1` payloads.
- Wired `execute_fixed_dag_plan(..., context=...)` and `execute_fixed_dag_node`
  so the optional placeholder seam can run in the active graph only when the flag
  is enabled.
- Kept the default path on deterministic `build_l2_conclusions`; no provider is
  loaded when the flag is off.
- Kept L3 composites, L4 decision synthesis, and report generation
  deterministic in this slice.
- Added fail-soft fallback to deterministic pending conclusions when provider
  loading, model invocation, JSON parsing, or safety checks fail.
- Added docs-only deployed-but-deferred inventory for server-side agent evidence
  without changing runtime bindings.
- Added tests for default-off behavior, fake-provider success, provider missing
  fallback, parse failure fallback, unsafe text sanitization, selected routing
  coexistence, and no external HTTP invocation.
- Updated README, system map, contracts, quality, readiness ladder, changelog,
  and decision docs for R8-6B boundaries.

### Validated

- `.venv/bin/python -m ruff check src/react_agent/context.py src/react_agent/fixed_dag_llm_placeholders.py src/react_agent/fixed_dag_executor.py src/react_agent/graph.py tests/unit_tests/test_fixed_dag_llm_placeholders.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_llm_placeholders.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py -q`
- `.venv/bin/python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_public_mapping_fixed_dag.py tests/unit_tests/test_fixed_dag_runtime_registry.py -q`
- `git diff --check`

### Not Done

- No provider/live smoke.
- No external `/v1/agent/invoke` call.
- No runtime binding change.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No fixed DAG roster change.
- No external adapter readiness or live integration.
- No frontend rewrite.
- No L3/L4/report LLM generation.
- `scripts/quality/run_quality.py --mode static` did not complete in the local
  `.venv` because its broader ruff target reports pre-existing Python 3.14
  `UP045` style findings in `public_contracts.py` and `public_store.py`; R8-6B
  did not modify those files.

## 2026-06-09 - Phase R8-5 default-off selected routing graph integration

### Changed

- Added `Context.enable_selected_routing` with `ENABLE_SELECTED_ROUTING=1`
  env support through the existing boolean parser.
- Wired `route_planner_node` to use provider-free `build_default_route_intent`
  and deterministic `compile_selected_fixed_dag_plan` only when selected
  routing is explicitly enabled.
- Kept default graph behavior on the full `fixed_dag_plan_v1` path.
- Added selected executor dispatch so `selected_fixed_dag_plan_v1` uses
  `validate_selected_dag_steps` and `topological_batches_for_selected_plan`
  instead of the full DAG validator.
- Made selected execution emit selected L2 conclusions, selected dimension
  composites, selected step results, and selected-subset
  `workflow_snapshot_v2`.
- Added safe full-DAG fallback provenance for selected compile/validation
  failures.
- Added graph and executor tests for default-off behavior, env/context flag
  enablement, selected execution, and selected fallback.
- Updated README, architecture, contracts, system map, quality, changelog, and
  decision docs for R8-5 boundaries.

### Validated

- `conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/context.py src/react_agent/graph.py src/react_agent/fixed_dag_contracts.py src/react_agent/fixed_dag_executor.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py -q`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `git diff --check`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline`

### Not Done

- No default active behavior change; selected routing remains default-off.
- No provider/search call.
- No external `/v1/agent/invoke` call.
- No demo stack startup.
- No fusion-gate run.
- No runtime binding enable/live change.
- No frontend change.
- No provider-backed LLM planner, external adapter readiness, final Route F1
  gate, or real business-agent implementation.

## 2026-06-09 - Phase R8-4 route intent evaluation baseline

### Changed

- Added provider-free RouteEval helpers in `src/react_agent/route_eval.py` for
  evaluating `route_intent_v1` task type, targets, selected dimensions,
  selected agents, clarification, and fallback behavior.
- Added a small deterministic JSONL gold set in
  `tests/fixtures/route_eval_gold.jsonl` covering single, compare, screen,
  macro, sentiment, industry, event, general, unclear, explicit exclusion,
  investment-risk policy, and sentiment market-only cases.
- Added unit coverage for fixture loading, exact-match metrics, false
  positives/false negatives, acceptable extra agents, must-not agents,
  deterministic planner evaluation, legacy mode non-evaluation,
  sentiment-to-risk penalties, and clarification accuracy.
- Kept RouteEval offline and deterministic; it does not call an LLM, provider,
  search backend, external service, demo stack, or fusion-gate.
- Kept the active graph default on the full `fixed_dag_plan_v1` path; R8-4
  does not modify `src/react_agent/graph.py` or enable selected routing.
- Updated README, architecture, contracts, system map, quality, changelog, and
  decision docs for R8-4 boundaries.

### Validated

- `conda run --no-capture-output -n cline_env python -m ruff check src/react_agent tests scripts/quality`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_route_eval.py -q`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_parse_router_layers.py -q`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `git diff --check`

### Not Done

- No active runtime default behavior change.
- No `src/react_agent/graph.py` change.
- No active selected-routing feature flag integration.
- No provider/search call.
- No external `/v1/agent/invoke` call.
- No demo stack startup.
- No fusion-gate run.
- No final Route F1 acceptance threshold; the first gold set is a small
  deterministic baseline, not the future 200-500 case gold suite.

## 2026-06-09 - Phase R8-3 route intent planner seam

### Changed

- Added provider-free `build_default_route_intent` as a deterministic/mock
  planner seam that returns `route_intent_v1` without calling an LLM, provider,
  search backend, or external service.
- Added `FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT` and
  `build_route_intent_prompt` as the future LLM/semantic planner contract.
  The prompt targets route intent only and forbids executable DAG output,
  dependency output, runtime binding changes, and live invocation claims.
- Added `parse_route_intent_json` and `normalize_route_intent` to normalize raw
  planner JSON into public-safe `route_intent_v1` or a clarification/fallback
  route intent.
- Kept the active graph default on the full `fixed_dag_plan_v1` path; R8-3
  does not modify `src/react_agent/graph.py` or enable selected routing.
- Added unit coverage for deterministic route intent construction, route-intent
  prompt boundaries, valid route intent parsing, unknown/removed/legacy agent
  fallback, executable-field fallback, sentiment market-only enforcement, and
  investment risk policy enforcement.
- Updated README, architecture, contracts, system map, quality, changelog, and
  decision docs for R8-3 boundaries.

### Validated

- `conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py src/react_agent/router_parse.py src/react_agent/prompts.py src/react_agent/context.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_parse_router_layers.py`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_parse_router_layers.py -q`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `git diff --check`

### Not Done

- No active runtime default behavior change.
- No `src/react_agent/graph.py` change.
- No active LLM planner, RouteEval, or external adapter implementation.
- No fixed DAG roster, catalog, runtime binding, runtime registry, public
  workflow, frontend, or public API change.
- No provider/search call.
- No external `/v1/agent/invoke` call.
- No demo stack startup.
- No fusion-gate run.

## 2026-06-09 - Phase R8-2 deterministic selected DAG compiler

### Changed

- Added deterministic `compile_selected_fixed_dag_plan` to compile
  `route_intent_v1` into dependency-closed `selected_fixed_dag_plan_v1` plans.
- The compiler adds fixed L1/evidence seams, selected L2 agents, selected
  dimension composites, policy-gated `decision_synthesizer`, and
  `report_generator` without calling LLMs, providers, search, or external
  services.
- Added selected executor validation helpers:
  `validate_selected_dag_steps` and `topological_batches_for_selected_plan`.
- Kept the active graph default on the full `fixed_dag_plan_v1` path; selected
  compilation is available as an internal deterministic seam only.
- Added unit coverage for value-only selected compilation, investment selected
  compilation with risk and decision, selected topological batches, selected
  dependency rejection, sentiment-to-risk rejection, and full DAG regression
  separation.
- Updated README, architecture, contracts, system map, quality, changelog, and
  decision docs for R8-2 boundaries.

### Validated

- `conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py src/react_agent/fixed_dag_executor.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py -q`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `git diff --check`

### Not Done

- No active runtime default behavior change.
- No `src/react_agent/graph.py` change.
- No LLM planner, RouteEval, or external adapter implementation.
- No fixed DAG roster, catalog, runtime binding, runtime registry, public
  workflow, frontend, or public API change.
- No provider/search call.
- No external `/v1/agent/invoke` call.
- No demo stack startup.
- No fusion-gate run.

## 2026-06-09 - Phase R8-1 selected fixed DAG plan contract

### Changed

- Added additive `route_intent_v1` and `selected_fixed_dag_plan_v1` contract
  seams in `fixed_dag_contracts.py` for future controlled dynamic routing.
- Added selected-routing validators for task type, route confidence, selected
  dimensions, selected agents, explicit omitted dimensions/agents, fallback
  metadata, investment-judgment risk/decision policy gates, report-generator
  inclusion, sentiment market-only routing, and public-safe fallback text.
- Kept `build_default_fixed_dag_plan` and `validate_fixed_dag_plan` as the full
  27-agent regression baseline; selected plans do not pass the full-plan
  validator and are not active graph defaults.
- Added unit coverage for valid selected intents, general value-only selected
  plans, omitted-field reconciliation, removed/legacy agent rejection, legacy
  mode rejection, unsafe fallback text rejection, and sentiment-to-risk
  dependency rejection.
- Updated reset architecture, contracts, system map, quality, README, and
  decision docs to mark R8-1 as contract foundation only.

### Validated

- `conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_contracts.py`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py -q`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_executor.py -q`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `git diff --check`

### Not Done

- No active runtime default behavior change.
- No `src/react_agent/graph.py` change.
- No selected DAG compiler or selected execution enablement.
- No LLM planner, RouteEval, or external adapter implementation.
- No fixed DAG roster, catalog, runtime binding, runtime registry, public
  workflow, or frontend change.
- No provider/search call.
- No external `/v1/agent/invoke` call.
- No demo stack startup.
- No fusion-gate run.

## 2026-06-08 - Phase R7-I demo presentation mode - user A report-first thought chain

### Changed

- Added a report-first `apps/web` assistant answer disclosure named
  "研判思维链". The assistant report remains the primary Markdown answer, while
  the disclosure maps the existing `workflow_snapshot_v2` payload to six
  public-safe stages, current-stage summary, four dimension summaries, and safe
  provenance copy.
- Kept the existing WorkflowPanel as the technical fixed DAG inspector for raw
  ids, runtime enum values, execution batches, selected step metadata, and
  provenance details.
- Updated frontend smoke coverage for the collapsed/expanded thought-chain
  disclosure and six product stage labels.
- Polished report-complete thought-chain semantics so prior stages render as
  included/complete, report output explains that the report body is above the
  disclosure, and dimension summaries use concise user-facing copy.
- Visually validated the report-first thought-chain surface with fresh desktop
  and mobile screenshots; report-complete prior stages no longer appear pending
  after report output.
- Polished the expanded thought-chain layout for R7-I.3: the disclosure now
  opens into a larger process panel with a derived stage progress band, wider
  stage/detail columns, and a full-width dimension summary area.
- Aligned the User A thought-chain with the reference HTML dynamic stage model
  for R7-I.4: streaming placeholder answers now show a stage-driven pending
  answer, the process panel uses current-stage detail plus evidence and
  dimension signal rows, and the final "文字报告输出" step remains a process node
  while the report stays in the main assistant Markdown body.
- Polished dimension signal authenticity for R7-I.5: the User A thought-chain now
  presents four-dimension content as workflow-stage-derived process signals with
  waiting/forming/synthesizing/summarized/included states, not as real
  business-agent conclusions, live market data, investment advice, confidence
  scores, or external-service results.
- Replaced the default WorkflowPanel surface for R7-I.7 normal users: the
  report-first thought chain is now the default process display, while the full
  WorkflowPanel is retained behind a collapsed "技术流程详情" technical disclosure.
- Aligned the screenshot helper's public mock runtime literals with backend
  runtime binding truth without running browser screenshot capture.
- Updated frontend boundary docs and reset map for R7-I as a presentation-layer
  change over the existing public contract.

### Validated

- `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`
- `npm --prefix apps/web run test`
- `npm --prefix apps/web run screenshots`
- `git diff --check`

### Not Done

- No Python backend runtime change.
- No `src/react_agent/graph.py` change.
- No fixed DAG catalog change.
- No runtime binding change.
- No runtime registry change.
- No provider call.
- No search call.
- No external `/v1/agent/invoke` call.
- No external candidate enablement.
- No demo stack startup.
- No fusion-gate run.
- No public schema change.
- No business-agent correctness claim.

## 2026-06-07 - Phase R7-H reset consistency repair

### Changed

- Repaired frontend workflow fixture runtime metadata so `runtime_kind` values
  match backend runtime binding truth, including `deterministic_system` for
  `route_planner` and `pending_placeholder` for
  `sentiment_company_radar`.
- Completed frontend `WorkflowRuntimeKind` coverage for backend legal runtime
  literals by adding `deterministic_l1_bundle`.
- Restored the missing local repo-external scaffold distribution working copy
  from the tracked repo mirror at `examples/fixed_dag_external_agent_scaffold/`.
- Updated current docs so `E:\muti-agent\external_agent_scaffold` is described
  as a restored local distribution working copy and the tracked mirror remains
  the auditable repo truth.
- Aligned R7-C/R7-D/R7-G wording: R7-C is source package rewrite and mirror
  sync, R7-D is documentation/wrapper-compatibility consistency, and R7-G is
  the v2.3.1 scaffold contract patch.

### Validated

- `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`
- `npm --prefix apps/web run test`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_executor.py tests/unit_tests/test_public_mapping_fixed_dag.py tests/unit_tests/test_fixed_dag_graph_skeleton.py tests/unit_tests/test_quality_runner_dispatch.py -q`
- `conda run --no-capture-output -n cline_env python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check examples/fixed_dag_external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python -m pytest E:\muti-agent\external_agent_scaffold\tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check E:\muti-agent\external_agent_scaffold`
- `git diff --check`

### Not Done

- No active runtime topology change.
- No fixed DAG roster change.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No external candidate enablement.
- No `live_verified=true` or `invoke_enabled_by_default=true` change.
- No demo stack startup.
- No fusion-gate run.

## 2026-06-07 - Legacy artifact cleanup

### Changed

- Removed tracked historical run logs under `log/**`.
- Removed tracked historical benchmark outputs under `outputs/benchmarks/**`.
- Removed tracked temporary trace, metric, screenshot, and provider-output
  artifacts under `tmp/**`.
- Removed obsolete root-level scripts `bench_e2e_qwen35.py` and
  `demo_layered_run.py`; they were not current fixed DAG runtime or quality
  entrypoints.
- Cleaned local Python, mypy, pytest, and ruff cache directories from the repo
  and external scaffold working copy.
- Updated `.gitignore` so generated `log/`, `tmp/`, `outputs/benchmarks/`, and
  `.ruff_cache/` content stays out of the tracked reset branch.

### Not Done

- No active runtime change.
- No fixed DAG roster change.
- No provider call.
- No external live invoke.
- No demo stack startup.
- No fusion-gate run.
- No push.

## 2026-06-07 - Phase R7-G v2.3.1 scaffold contract patch

### Changed

- Upgraded the external scaffold package and repo mirror to
  `external-agent-scaffold-v2.3.1-fixed-dag`.
- Patched L2 `agent_conclusion_v1` so `direction` results require `stance`
  and risk `gate_member` results require `risk_score`.
- Added safe `raw_output` and `quality` dictionaries for L2 handoff audit
  metadata; these are not graph state.
- Added `manual_review` as a risk gate.
- Changed `dimension_conclusion_v1.members` to canonical `DimensionMember[]`
  with member weight and weighted stance validation.
- Normalized supported date formats before anti-lookahead comparison.
- Restricted macro `dimension_weights` to directional `value` and `market`.
- Relaxed L4 score/final-score tolerance to `0.01` and validated distinct
  reasoning stages.
- Updated samples, tests, package docs, repo docs, ADRs, and quality docs for
  the v2.3.1 contract patch.

### Not Done

- No active graph registration.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No demo stack startup.
- No fusion-gate run.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.

## 2026-06-06 - Phase R7-F v2.3 domain payload superset and semantic validators

### Changed

- Upgraded the external scaffold package and repo mirror to
  `external-agent-scaffold-v2.3-fixed-dag`.
- Restored the v2.3 domain payload family:
  `agent_conclusion_v1`, `dimension_conclusion_v1`, `risk_conclusion_v1`,
  `macro_conclusion_v1`, `decision_conclusion_v1`, `eval_record_v1`,
  `fixed_dag_plan_v1`, and `data_bundle_v1`.
- Added scaffold-local semantic validation for anti-lookahead,
  `publish_time`, evidence, confidence, dimension aliases, value/market
  weights, risk gate placement, macro regulator placement, L4 reasoning depth,
  L4 score trace, data bundle replay ids, and aNN primary-id rejection.
- Added v2.3 domain sample payloads under
  `examples/fixed_dag_external_agent_scaffold/sample_requests/`.
- Updated README, docs index, external handoff docs, payload mapping, readiness
  ladder, sample payload docs, contracts, system map, quality docs, ADRs, and
  external package docs/changelog for the v2.3 compatibility superset.

### Validated

- `conda run --no-capture-output -n cline_env python -m pytest E:\muti-agent\external_agent_scaffold\tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check E:\muti-agent\external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check examples/fixed_dag_external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline`
- `git diff --check`

### Not Done

- No active graph registration.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No demo stack startup.
- No fusion-gate run.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No production deployment claim.
- No push.

## 2026-06-06 - Phase R7-E expand AI coding handoff

### Changed

- Expanded `examples/fixed_dag_external_agent_scaffold/AI_CODING_HANDOFF.md`
  into a full Codex / Claude Code operating manual for adapting a
  developer-owned agent project into a fixed DAG external service.
- Added guidance for inputs, hard rules, fixed DAG id usage, implementation
  mode neutrality, audit-first workflow, adaptation patterns, required
  endpoints, payload rules, mapping targets, developer project file strategy,
  local tests, validation commands, handoff bundle, final response format, and
  copy-paste prompt.
- Updated README, documentation index, fixed DAG external handoff docs, quality
  docs, ADRs, and package changelog to point to the expanded AI coding handoff.

### Validated

- `conda run --no-capture-output -n cline_env python -m pytest E:\muti-agent\external_agent_scaffold\tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check E:\muti-agent\external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check examples/fixed_dag_external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline`
- `git diff --check`

### Not Done

- No service runtime behavior change.
- No schema, sample payload, or test behavior change.
- No active graph registration.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No demo stack startup.
- No fusion-gate run.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No production deployment claim.
- No push.

## 2026-06-06 - Phase R7-D external handoff documentation consistency fix

### Changed

- Clarified external scaffold status mapping across external service status,
  adapter decision, and fixed DAG validator-facing status.
- Clarified that existing legacy wrapper compatibility code may still carry
  `main_agent_id` inside compact context shapes until R8 adapter work, but new
  external services must implement the fixed DAG scaffold contract.
- Clarified the relationship between the tracked repo mirror, local
  distribution working copy, and generated zip artifact.
- Tightened the external developer handoff checklist with ids, samples, test
  output, timestamp/evidence/confidence policies, performance notes,
  dependency list, known limitations, and no-secrets confirmation.
- Updated scaffold mapper provenance so `legacy_agent_id` is read from the
  response being mapped rather than a global sample constant.

### Validated

- `conda run --no-capture-output -n cline_env python -m pytest E:\muti-agent\external_agent_scaffold\tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check E:\muti-agent\external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check examples/fixed_dag_external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline`
- `git diff --check`

### Not Done

- No active graph registration.
- No runtime binding change.
- No provider call.
- No external live invoke.
- No demo stack startup.
- No fusion-gate run.
- No `live_verified=true`.
- No `invoke_enabled_by_default=true`.
- No production deployment claim.
- No push.

## 2026-06-05 - Phase R7-C external scaffold source package rewrite

### Added

- Added the upgraded external scaffold source package contents to the tracked
  repo mirror `examples/fixed_dag_external_agent_scaffold/`, including package
  docs, `.env.example`, sample requests/responses, typed-error samples, service
  code, schemas, and tests.
- Added scaffold docs for fixed DAG developer onboarding, integration standard,
  domain payload mapping, performance/backtest compliance, AI coding handoff,
  and package-local changelog.
- Added `sample_requests/error.response.json` to show safe rejection of a
  legacy aNN id used as the primary `agent_id`.

### Changed

- Upgraded the repo-external source package
  `E:\muti-agent\external_agent_scaffold` from the old v2.1-v2.2.1 lineage into
  a fixed DAG package using `agent_id`, `external_agent_id`, and
  migration-only `legacy_agent_id`.
- Synced the upgraded external package into
  `examples/fixed_dag_external_agent_scaffold/` using the Strategy A mirror
  policy so repo review and external distribution do not drift.
- Updated README, documentation index, contracts, system map, quality, ADR,
  handoff, payload mapping, and readiness ladder docs to describe R7-C as a
  source-package rewrite, not a runtime binding or live-readiness change.

### Validated

- `conda run --no-capture-output -n cline_env python -m pytest E:\muti-agent\external_agent_scaffold\tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check E:\muti-agent\external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check examples/fixed_dag_external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline`
- `git diff --check`

### Not Done

- No fixed DAG topology, roster, runtime binding, public schema, frontend
  product UI, provider integration, external wrapper, or real business-agent
  implementation change.
- No scaffold registration into `react_agent.graph`, legacy registry,
  `AGENT_TOOLS`, runtime binding registry, or wrapper table.
- No `runtime_bindings` change, no `invoke_enabled_by_default=true`, and no
  `live_verified=true`.
- No provider, search, external `/v1/agent/invoke`, demo stack, Router-SFT,
  RARP/route-prior, browser screenshot, or archived fusion-gate validation.
- No claim that the scaffold package is a live service, live verified external
  candidate, production service, or active fixed DAG runtime component.
- No push.

## 2026-06-05 - Phase R7-B fixed DAG external agent handoff scaffold

### Added

- Added `examples/fixed_dag_external_agent_scaffold/` as a sample-only runnable
  FastAPI scaffold for fixed DAG external developer handoff.
- Added scaffold schemas for `external_agent_health_v0`,
  `external_agent_request_v0`, `external_agent_response_v0`, typed errors,
  evidence, event flags, implementation notes, and `agent_conclusion_v1`
  tool results.
- Added deterministic scaffold endpoints for `GET /health`,
  `POST /v1/agent/compute`, and `POST /v1/agent/invoke`.
- Added sample request and response JSON files for health, compute, and invoke.
- Added example-local tests for health schema, compute success, invoke success,
  request id roundtrip, `as_of`/`data_as_of` anti-lookahead, confidence range,
  evidence, event flags, no secret or traceback leakage, aNN primary id
  rejection, fixed DAG payload mapping, and no provider/external calls.

### Changed

- Updated README, documentation index, contracts, system map, quality, ADR, and
  external handoff docs to describe the sample scaffold as local handoff
  guidance, not active runtime.
- Clarified that the sample scaffold adapts reusable ideas from the historical
  scaffold protocol package / v2.1-v2.2.1 lineage while replacing
  `main_agent_id` and aNN primary ids with fixed DAG `snake_case` ids.
- Clarified that external agent internals may be ML, rules, data service, LLM,
  LLM with tools, deterministic compute, or hybrid; the standardized object is
  the boundary contract and readiness evidence.

### Validated

- `conda run --no-capture-output -n cline_env python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q`
- `conda run --no-capture-output -n cline_env python -m ruff check examples/fixed_dag_external_agent_scaffold`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline`
- `git diff --check`

### Not Done

- No fixed DAG topology, roster, runtime binding, public schema, frontend
  product UI, provider integration, external wrapper, or real business-agent
  implementation change.
- No scaffold registration into `react_agent.graph`, legacy registry,
  `AGENT_TOOLS`, runtime binding registry, or wrapper table.
- No `runtime_bindings` change, no `invoke_enabled_by_default=true`, and no
  `live_verified=true`.
- No provider, search, external `/v1/agent/invoke`, demo stack, Router-SFT,
  RARP/route-prior, browser screenshot, or archived fusion-gate validation.
- No claim that the sample scaffold is a live service, live verified external
  candidate, production service, or active fixed DAG runtime component.
- No push.

## 2026-06-05 - Phase R7-B fixed DAG external developer handoff docs

### Added

- Added `docs/EXTERNAL_AGENT_HANDOFF_FIXED_DAG.md` as the fixed DAG external
  developer handoff entry point.
- Added `docs/EXTERNAL_AGENT_PAYLOAD_MAPPING_FIXED_DAG.md` for mapping
  external response envelopes into fixed DAG runtime contracts.
- Added `docs/EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md` for docs-only,
  mock, health, compute, controlled live, binding, live-verified, and
  invoke-enabled readiness levels.
- Added `docs/EXTERNAL_AGENT_SAMPLE_PAYLOADS_FIXED_DAG.md` with
  documentation-only health, invoke, compute, mapped, partial, and failure
  payload examples.

### Changed

- Updated README, documentation index, contracts, system map, quality, and ADR
  docs so external developer handoff points at the fixed DAG catalog, runtime
  binding registry, contract seams, public adapter boundary, and reset quality
  gate.
- Documented the historical scaffold v2.1-v2.2.1 lineage as reusable guidance
  only, not an active runtime package or live-readiness signal.
- Clarified that fixed DAG integration standardizes boundary contracts and
  readiness evidence, not a single internal implementation mode for all
  external agents.

### Validated

- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline`
- `git diff --check`

### Not Done

- No fixed DAG topology, roster, runtime binding, public schema, frontend
  product UI, provider integration, external wrapper, or real business-agent
  implementation change.
- No provider, search, external `/v1/agent/invoke`, demo stack, Router-SFT,
  RARP/route-prior, browser screenshot, or archived fusion-gate validation.
- No scaffold registration, runnable scaffold addition, external candidate
  enablement, or live verification.
- No claim that external services, provider readiness, or production deployment
  are live verified.
- No push.

## 2026-06-05 - Phase R6-B reset quality mainline rebuild

### Changed

- Rebuilt `scripts/quality/run_quality.py --mode mainline` as the default
  fixed-DAG reset quality gate: static, unit, public-api, graph-smoke, and
  frontend.
- Removed `fusion-gate` from default mainline dispatch and kept it as an
  explicit archived/manual mode.
- Changed frontend quality mode to run TypeScript no-emit, frontend smoke, and
  Vite build with a temporary repo-external `--outDir` instead of writing
  `apps/web/dist`.
- Expanded quality runner unit coverage for mainline dispatch, frontend command
  sequencing, repo-external build output, and static target path existence.
- Updated Makefile help and GitHub Actions so PR/push default quality no longer
  blocks on fusion-gate; provider live smoke remains optional manual/scheduled.
- Updated reset docs for R6-B quality boundaries and non-claims.

### Validated

- `conda run --no-capture-output -n cline_env python -m ruff check scripts/quality/run_quality.py tests/unit_tests/test_quality_runner_codespell.py tests/unit_tests/test_quality_runner_dispatch.py`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_quality_runner_codespell.py tests/unit_tests/test_quality_runner_dispatch.py -q`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --help`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode frontend`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline`
- `git diff --check`

### Not Done

- No fixed DAG topology, roster, runtime binding, provider integration,
  external wrapper, frontend product UI, or real business-agent implementation
  change.
- No provider, search, external `/v1/agent/invoke`, demo stack, Router-SFT,
  RARP/route-prior, browser screenshot, or archived fusion-gate validation.
- No claim that external services, provider readiness, fusion acceptance,
  visual screenshots, or production deployment are live verified.
- No full-tree lint gate.
- No push.

## 2026-06-05 - Phase R5-C1 user-facing business copy professionalization

### Changed

- Replaced remaining default-surface implementation-note copy in the web UI
  with business-facing Chinese copy.
- Changed answer-card evidence from "参考依据"/data-bundle style wording to
  "研判依据" with "分析框架", "用户问题", and "流程记录" items.
- Rewrote dimension group summaries for value, market, risk, and macro so they
  describe analysis purpose instead of DAG route wiring.
- Rewrote frontend mock and screenshot fixture step summaries to avoid fixture,
  roster, transcript, path-wiring, metadata, and checker wording in default
  user-visible surfaces.
- Updated public-safe fixed DAG report/fallback copy without changing schemas,
  topology, roster, or runtime binding semantics.
- Updated frontend smoke assertions and Python public copy assertions.
- Updated reset docs for the R5-C1 business-copy boundary and non-claims.

### Validated

- `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`
- `npm --prefix apps/web run test`
- `npm --prefix apps/web run build -- --outDir E:/muti-agent/_tmp_web_build_r5c1`
- `conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_public_api.py -q`
- `conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py src/react_agent/fixed_dag_executor.py src/react_agent/graph.py src/react_agent/public_mapping.py tests/integration_tests/test_public_api.py tests/integration_tests/test_graph.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_graph_skeleton.py tests/unit_tests/test_llm_json_retry_and_summary_filter.py tests/unit_tests/test_manager_summary_a25_output.py`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests -q`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `npm --prefix apps/web run screenshots`
- `git diff --check`

### Visual Check

- Temporary Vite process only, using Playwright API route interception and no
  provider/external invocation. Screenshots saved outside the repo under
  `E:/muti-agent/_tmp_r5c1_visual/screenshots`.

### Not Done

- No fixed DAG topology, roster, runtime binding, provider integration,
  external wrapper, or real business-agent implementation change.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No claim that external services, provider readiness, or production deployment
  are live verified.
- No push.

## 2026-06-04 - Phase R5-C frontend product polish and user-facing simplification

### Changed

- Simplified the normal Chinese chat surface so degraded/provider/search/live
  readiness details are not prominent in the main user flow.
- Added example question buttons to the empty chat state and softened the local
  fixed-DAG mode notice.
- Changed the assistant answer and workflow summary copy to product-facing
  fixed DAG研判流程 language while keeping workflow details out of the public
  transcript.
- Kept workflow `stepResults`, provenance, and raw enum values available only
  after users expand the workflow technical details, with Chinese primary labels
  and smaller raw enum chips.
- Changed the Agents page from a registry-style page into a lighter capability
  structure page with layer and dimension summaries and collapsible details.
- Moved provider/search/checkpointer readiness from the default Settings view
  into an advanced diagnostics disclosure.
- Updated frontend mocks, screenshot fixture copy, smoke assertions, Python
  public-safe answer copy, and related unit/integration assertions.
- Updated reset docs to record that R5-C is user-facing noise reduction and
  product polish, not a runtime/topology/readiness change.

### Validated

- `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`
- `npm --prefix apps/web run test`
- `npm --prefix apps/web run build -- --outDir E:/muti-agent/_tmp_web_build_r5c`
- `npm --prefix apps/web run screenshots`
- `conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py src/react_agent/fixed_dag_executor.py src/react_agent/graph.py src/react_agent/public_mapping.py tests/integration_tests/test_graph.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_graph_skeleton.py tests/unit_tests/test_llm_json_retry_and_summary_filter.py tests/unit_tests/test_manager_summary_a25_output.py`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests -q`
- `conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_public_api.py -q`
- `conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_graph.py -q`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `git diff --check`

### Visual Check

- Temporary Vite process only, using Playwright API route interception and no
  provider/external invocation. Screenshots saved outside the repo under
  `E:/muti-agent/_tmp_r5c_visual/screenshots`.

### Not Done

- No fixed DAG topology, roster, runtime binding, provider integration,
  external wrapper, or real business-agent implementation change.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No claim that external services, provider readiness, or production deployment
  are live verified.
- No push.

## 2026-06-05 - Phase R5-B2.6 Chinese localization and visual copy polish

### Changed

- Localized visible `apps/web` copy for sidebar, thread, assistant answer,
  composer, workflow inspector, Agents page, and Settings page.
- Polished WorkflowPanel labels, status labels, empty states, selected step
  metadata, provenance, and raw enum display around `workflow_snapshot_v2`.
- Localized deterministic fixed DAG public-safe skeleton answer, workflow step
  summaries, executor limitations, public runtime hints, and public adapter
  error copy while preserving then-current validation sentinel phrases.
- Updated frontend mocks, screenshot fixture script, and smoke assertions to
  check localized UI copy while keeping technical ids and enum values visible
  where needed for debugging.
- Updated reset docs for the R5-B2.6 localization boundary and non-claims.

### Validated

- `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`
- `npm --prefix apps/web run test`
- `npm --prefix apps/web run build -- --outDir E:/muti-agent/_tmp_web_build_r5b26`
- `conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_public_api.py -q`
- `conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py src/react_agent/fixed_dag_executor.py src/react_agent/fixed_dag_catalog.py src/react_agent/public_runtime.py src/react_agent/public_mapping.py src/react_agent/public_store.py tests/integration_tests/test_public_api.py tests/integration_tests/test_graph.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_graph_skeleton.py`
- `conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests`
- `conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static`
- `git diff --check`

### Visual Check

- Temporary local API and Vite processes only, with screenshots saved outside
  the repo under `E:/muti-agent/_tmp_r5b26_visual/screenshots`.

### Not Done

- No fixed DAG topology, roster, provider integration, external wrapper, or
  real business-agent implementation change.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No full runtime locale switch or multilingual framework claim.
- No production auth, rate-limit, HTTPS, deployment, persistence, or
  observability claim.
- No push.

## 2026-06-04 - Phase R5-B2 workflow DAG inspector UI rewrite

### Changed

- Changed WorkflowPanel from the R5-B1 minimal DAG summary into a fixed DAG
  inspector over `workflow_snapshot_v2`.
- Added stage timeline rendering from `stages`, `currentStage`, and live
  `workflow.stage` progress.
- Added execution batch rendering from `executionBatches`.
- Added dimension group rendering from `dimensionGroups`.
- Added selectable DAG step cards from `dagSteps`.
- Added public-safe selected step result metadata rendering from `stepResults`.
- Added final source and provenance rendering from `finalSource` and
  `provenance`.
- Updated fixed DAG workflow mocks, screenshot fixture script, and frontend
  smoke checks for inspector rendering and transcript safety.

### Validated

- `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`
- `npm --prefix apps/web run test`

### Not Done

- No Python backend contract, executor, catalog, or runtime binding change.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No external HTTP candidate was enabled or live verified.
- No `/api/agents` runtime binding field exposure.
- No production auth, rate-limit, HTTPS, deployment, persistence, or
  observability claim.
- No push.

## 2026-06-04 - Phase R5-B1 frontend DAG contract migration

### Changed

- Changed frontend workflow/chat types to consume `workflow_snapshot_v2` with
  `finalSource=reset_skeleton`.
- Changed the streaming placeholder and `workflow.stage` merge path to use
  fixed DAG stages: planning, evidence, L2 analysis, dimension composite,
  decision, and report.
- Changed the existing WorkflowPanel subviews to render a minimal DAG summary
  from `stages`, `dagSteps`, `dimensionGroups`, `executionBatches`,
  `completedSteps`, and public provenance.
- Changed frontend mocks to use the 27 enabled `snake_case` fixed DAG catalog
  and v2 workflow snapshot fixtures.
- Changed frontend smoke tests to assert the fixed DAG contract and transcript
  boundary instead of the old layer/fusion/source model.

### Validated

- `npm --prefix apps/web run test`
- `npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json`

### Not Done

- No complete R5-B2 WorkflowPanel UI rewrite.
- No Python backend contract, executor, catalog, or runtime binding change.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No external HTTP candidate was enabled or live verified.
- No `/api/agents` runtime binding field exposure.
- No production auth, rate-limit, HTTPS, deployment, persistence, or
  observability claim.
- No push.

## 2026-06-04 - Phase R4-C legacy registry boundary cleanup

### Added

- Added `src/react_agent/agent_types.py` as the no-legacy-import home for shared
  `AgentInput` and `AgentOutput` typing.
- Added `src/react_agent/legacy_agent_registry.py` as the explicit compatibility
  home for historical `AGENT_METADATA`, `AGENT_TOOLS`, metadata loading,
  sorting, and registration helpers.
- Added `src/react_agent/external_http_config.py` as configuration-only retained
  external candidate metadata for fixed-DAG binding validation.
- Added import-boundary coverage proving `react_agent.graph` does not load
  legacy registry/bootstrap/default/generic/external-wrapper implementation
  modules.

### Changed

- Changed `src/react_agent/graph.py` to avoid legacy bootstrap and old registry
  globals on the active fixed-DAG graph import path.
- Changed `src/react_agent/agents.py` into a shared typing facade with lazy
  compatibility exports for legacy registry names.
- Changed legacy catalog, disabled-agent, placeholder, and compatibility tests
  to target `legacy_agent_registry.py` and `graph_bootstrap.py` explicitly.
- Changed public workflow title mapping to use the fixed DAG catalog rather
  than old `config/agents/*.json` metadata.
- Changed fixed DAG runtime binding validation to read external candidate
  metadata from the config-only module instead of the HTTP wrapper module.

### Removed

- Removed `src/react_agent/external_valuation_agents.py` after valuation tests
  migrated to the retained generic `external_http_agents.py` wrapper.
- Removed unreferenced `src/react_agent/json_utils.py`.

### Not Done

- No real business-agent algorithm implementation.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No external HTTP candidate was enabled or live verified.
- No deletion of `config/agents/*.json`.
- No R5 frontend workflow UI rewrite.
- No R6 mainline/fusion/provider readiness rebuild.
- No push.

## 2026-06-04 - Phase R4-B fixed DAG runtime binding registry

### Added

- Added `config/fixed_dag/runtime_bindings.json` as the backend runtime binding
  source for the same 27 fixed DAG `snake_case` agents.
- Added `src/react_agent/fixed_dag_runtime_registry.py` with runtime binding
  loading, validation, grouping, summary, external-candidate lookup, and step
  result annotation helpers.
- Added tests covering runtime binding schema/count/id alignment, forbidden
  primary ids, disabled external candidates, legacy wrapper mapping alignment,
  sentiment market-only routing, and executor annotation.

### Changed

- Changed `fixed_dag_step_result_v1` construction to annotate each executed
  step with runtime binding metadata: `runtime_kind`,
  `implementation_status`, `binding_source`, `legacy_agent_id`,
  `external_agent_id`, `invoke_enabled`, and `live_verified`.
- Changed graph and public workflow tests to prove binding annotation remains
  metadata-only and does not call providers or external HTTP.
- Strengthened `/api/agents` tests to confirm the public catalog schema remains
  unchanged and does not expose runtime binding internals.
- Updated reset docs to record R4-B runtime binding ownership and later R4-C/R5/R6
  boundaries.

### Not Done

- No real business-agent algorithm implementation.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No external HTTP candidate was enabled or live verified.
- No R4-C legacy aNN config cleanup.
- No R5 frontend workflow UI rewrite.
- No R6 mainline/fusion/provider readiness rebuild.
- No push.

## 2026-06-04 - Phase R4-A fixed DAG catalog source and public projection

### Added

- Added `config/fixed_dag/agent_catalog.json` as the active reset backend
  catalog source for the 27 formal `snake_case` fixed DAG agents.
- Added `src/react_agent/fixed_dag_catalog.py` with stdlib-only catalog loading,
  validation, grouping helpers, and public catalog projection.
- Added catalog tests covering schema, counts, duplicate ids, legacy aNN id
  rejection, sentiment market-only routing, risk-composite exclusion of
  sentiment, and public projection counts.

### Changed

- Changed fixed DAG roster constants to derive from the fixed DAG catalog.
- Changed public `/api/agents` to project the fixed DAG 27-agent catalog through
  the existing `AgentCatalogResponse` shape.
- Changed public API catalog tests from old `27/25/aNN` config semantics to
  reset `27/27/snake_case` semantics.
- Updated reset docs to mark old `config/agents/*.json` as legacy migration
  input, not active reset public catalog truth.

### Not Done

- No real business-agent algorithm implementation.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No external endpoint mapping adapter.
- No R4-C legacy aNN config cleanup.
- No R5 frontend workflow UI rewrite.
- No R6 mainline/fusion/provider readiness rebuild.
- No push.

## 2026-06-04 - Phase R3.6 safe dead-file cleanup and R4 Excel baseline

### Added

- Added `新架构_固定DAG_最终分层级智能体表_v4_反馈修正版.xlsx` as the R4
  `snake_case` catalog/runtime registry input workbook.

### Removed

- Removed high-confidence dead local artifacts and legacy fixtures that were not
  active quality or runtime entry points.

### Changed

- Updated reset docs to record the R3.6 cleanup boundary and non-claims.

### Not Done

- No R4 catalog/runtime registry migration.
- No R5 frontend DAG workflow UI rewrite.
- No R6 mainline/fusion/provider readiness rebuild.
- No provider, search, external `/v1/agent/invoke`, demo stack, mainline, or
  fusion-gate validation.
- No deletion of `config/agents`, external wrappers, baseline/fusion regression
  inputs, `assets/reference`, or historical `log/tmp/outputs` artifacts.
- No push.

## 2026-06-04 - Phase R3 plan-driven fixed DAG execution

### Added

- Added `src/react_agent/fixed_dag_executor.py` with deterministic DAG
  validation, topological batching, step result construction, plan execution,
  and execution result validation.
- Added `fixed_dag_execution_v1` and `fixed_dag_step_result_v1` runtime
  contracts.
- Added workflow projection for `executionBatches` and `stepResults`.
- Added unit and integration coverage for dependency validation, invalid-plan
  fallback, executor output, graph integration, and public workflow mapping.

### Changed

- Changed the active graph edge path to
  `route_planner -> prepare_l1_context -> execute_fixed_dag -> final_emit ->
  memory_update`.
- Changed public workflow contracts and mapping to include executor trace fields
  while keeping the transcript as a single assistant answer.
- Changed the final reset bundle to include `dag_execution`, `dag_step_results`,
  and `execution_batches`.
- Updated reset docs for R3 execution orchestration and later R4/R5/R6
  ownership.

### Not Done

- No business-agent algorithm implementation.
- No provider, search, or external live verification.
- No frontend workflow UI rewrite.
- No snake_case catalog/runtime registry migration.
- No mainline or fusion-gate artifact-writing validation.
- No push.

## 2026-06-04 - Phase R2 contract and function seam hardening

### Added

- Added deterministic constructors, normalizers, and validators for fixed DAG
  plan, L1 bundles, L2 conclusions, L3 composites, L4 decision/report, workflow
  snapshot, and final emit bundles.
- Added authoritative roster partition constants for L1, L2, L3, L4, and
  value/market/risk/macro dimensions.
- Added unit coverage for R2 contract invariants, sentiment market-only routing,
  risk-composite exclusion of sentiment, public workflow fallback, and graph
  final bundle shape.

### Changed

- Changed graph nodes to consume contract/function seams instead of scattering
  payload fields in node bodies.
- Changed public workflow fallback mapping to reuse `build_workflow_snapshot_v2`
  so dimension groups remain stable.
- Updated reset docs to describe R2 seam hardening and later R4/R5/R6 ownership.

### Not Done

- No provider, search, or external live verification.
- No frontend workflow UI rewrite.
- No snake_case catalog/runtime registry migration.
- No real business agent algorithm implementation.
- No mainline or fusion-gate artifact-writing validation.
- No push.

## 2026-06-04 - Phase R1-B-Delta fixed DAG roster alignment

### Changed

- Aligned the active reset roster with the v4 feedback table: 27 formal agent
  ids with L1=3, L2=18, L3=4, and L4=2.
- Removed the enterprise financial analysis target from the fixed-DAG runtime
  skeleton.
- Moved `sentiment_company_radar` to the market dimension and limited its output
  route to `market_composite`.
- Renamed the L3 value dimension composite from the earlier fundamental wording
  to `value_composite`.
- Updated reset docs and tests to reject the stale pre-delta target-count,
  L2-count, and sentiment-to-risk wording.

### Not Done

- No real business agent implementation.
- No provider, search, or external live verification.
- No frontend v2 workflow rewrite.
- No production deployment hardening.

# 2026-06-25 - SYNC-OPS-5B-X source-loss recovery and P2S activation

## Added

- Added `docs/SYNC_OPS_5B_X_SOURCE_LOSS_AND_P2S_CLOSEOUT.md`.
- Documented the repaired V7 source-loss cutover and full P2S rebase closeout.

## Changed

- Updated sync-ops docs to record that stale downstream change units supersede
  only experiment/cycle packets, not completed source-loss or P2S closeouts.
- Recorded active sandbox baseline
  `risk-fraud-rebase-full_p2s_rebase_9f7f07553392` as the upstream closeout
  baseline for the next exact first non-zero cycle packet.

## Not Done

- No `/v1/agent/invoke` call.
- No provider call.
- No SIGKILL.
- No owner-dev modification.
- No first real non-zero publish cycle execution.

## 2026-06-04 - Phase R1-B fixed DAG runtime protocol skeleton

### Added

- Added `src/react_agent/fixed_dag_contracts.py` with deterministic reset
  contracts and `workflow_snapshot_v2` builder.
- Added fixed-DAG parser tests, contract tests, graph skeleton tests, and public
  workflow v2 tests.

### Changed

- Replaced active `src/react_agent/graph.py` routing with the deterministic
  skeleton:
  `route_planner -> prepare_l1_context -> run_l2_conclusions ->
  run_dimension_composites -> decision_synthesizer -> report_generator ->
  final_emit -> memory_update`.
- Changed router prompt/parser surfaces from old route-mode planning to
  `fixed_dag_plan_v1`.
- Changed Python public workflow contracts from layer/mode/fusion fields to DAG
  stages, steps, dimension groups, provenance, and `reset_skeleton` final source.
- Updated reset docs to describe R1-B runtime scope and non-claims.

### Not Done

- No real business agent implementation.
- No provider, search, or external live verification.
- No frontend v2 workflow rewrite.
- No production deployment hardening.
- No mainline or fusion-gate artifact-writing validation.

## 2026-06-04 - Phase R1-A hard slimming reset baseline

### Removed

- Removed old Agent Catalog v2 documentation and replacement runbooks.
- Removed old mainline audit, A01 contract/SFT, route-prior/RARP, Router-SFT,
  external integration, archive, and handoff docs.
- Removed archive tests for route-prior, router eval, and A01 SFT.
- Removed route-prior helper source and its offline regression bundle.
- Removed Router-SFT data, A01 SFT data, Router-SFT tools, old router regression
  scripts, and SFT train/eval requirements.
- Removed old external-agent scaffold package and generated zip.

### Added

- Added reset documentation set:
  - `docs/ARCHITECTURE_FIXED_DAG.md`
  - `docs/CONTRACTS.md`
  - `docs/FRONTEND_V2.md`
  - `docs/QUALITY.md`
  - `docs/DECISIONS.md`
- Added reset-focused docs test coverage.

### Changed

- Rewrote `README.md`, `AGENTS.md`, `docs/INDEX.md`, and `docs/SYSTEM_MAP.md`
  for the reset branch.
- Updated static quality documentation targets so they no longer reference
  deleted docs.

### Not Done

- No runtime graph rewrite in R1-A.
- No prompt/parser/state/public workflow deletion in R1-A.
- No Fair Fusion or baseline sidecar deletion in R1-A.
- No frontend v2 rewrite.
- No provider or external live verification.
- No push.
