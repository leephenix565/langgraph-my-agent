# Changelog

Historical changelog entries before this reset branch are preserved by tag
`pre-fixed-dag-reset-20260604-1457`.

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
