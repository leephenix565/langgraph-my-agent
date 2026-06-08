# Changelog

Historical changelog entries before this reset branch are preserved by tag
`pre-fixed-dag-reset-20260604-1457`.

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
