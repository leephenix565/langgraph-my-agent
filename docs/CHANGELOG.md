# CHANGELOG

## 2026-04-28 - RARP route-prior design document
- Files: `docs/ROUTE_PRIOR_RARP_DESIGN.md`, `docs/INDEX.md`, `docs/CHANGELOG.md`
- Added a docs-only design authority for Reliability-Aware Route Prior:
  - records the target RARP mental model as an internal reliability layer around the existing formal Router
  - preserves RP-1A/RP-1B as the current implemented foundation and separates planned RP-2/RP-3/RP-4 behavior from current code facts
  - documents agent-universe boundaries across the formal Router catalog, ordinary route-prior pool, and public `/api/agents` catalog
  - records planned profile-card, reliability-table, scoring, confidence-band, label, metric, artifact, trace/privacy, and promotion-boundary schemas
  - keeps RP-2 as shadow/eval-first and RP-3 as future non-binding advisory only after evidence gates
- Updated the docs index to register the design doc as S1 design authority, with runtime behavior still governed by `src/react_agent/*` and focused tests.
- Scope boundary:
  - documentation only
  - no runtime code changes
  - no Router prompt/parser changes
  - no State schema changes
  - no public API/workflow/health changes
  - no test or quality-gate changes
  - no route-prior eval promotion into the mainline gate

## 2026-04-26 - RP-1B DeepSeek teacher-proxy labeling path
- Files: `ops/regression/route_prior/generate_deepseek_teacher_labels.py`, `tests/unit_tests/test_deepseek_teacher_labels_rp1b.py`, `ops/regression/route_prior/eval_route_prior_outputs.py`, `tests/unit_tests/test_route_prior_eval_rp1b.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added an optional offline DeepSeek teacher-label generator for RP-1B route-prior experiments:
  - reads question JSONL and the tracked ordinary-agent catalog
  - calls the DeepSeek OpenAI-compatible chat-completions API when `DEEPSEEK_API_KEY` is present
  - writes `label_source="deepseek_teacher_v1"` teacher-proxy labels into ignored `ops/regression/route_prior/out/` artifacts
  - filters unknown or non-ordinary agent ids before evaluation
  - keeps generated labels explicitly model-generated proxy labels, not human/manual gold labels
- Updated RP-1B metrics metadata to keep DeepSeek teacher-label results as proxy-only with `quality_conclusion_allowed=false`.
- Scope boundary:
  - no runtime code changes
  - no RP-2 advisory-only behavior
  - no Router prompt/parser changes
  - no State or committed routing output changes
  - no public API or workflow changes
  - no `/api/health` expansion

## 2026-04-26 - RP-1B route-prior offline validation harness
- Files: `ops/regression/route_prior/__init__.py`, `ops/regression/route_prior/run_route_prior_eval.py`, `ops/regression/route_prior/eval_route_prior_outputs.py`, `ops/regression/route_prior/fixtures/rp1b_labeling_template.jsonl`, `tests/unit_tests/test_route_prior_eval_rp1b.py`, `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `.gitignore`
- Added an optional offline RP-1B eval harness under `ops/regression/route_prior`:
  - consumes labeled question JSONL and RP-1A `compute_route_prior_shadow(...)` outputs
  - writes per-case run records plus run summaries without emitting raw embeddings
  - aggregates top-k match, expected-agent recall at top 5, shortlist recall, low-confidence fallback rate, wildcard retention, formal-Router overlap observation, and false-negative examples
  - keeps default unit coverage network-free and independent of any local embeddings endpoint
  - supports optional live embedding runs through the private RP-1A OpenAI-compatible embedding envs
- Added a labeling template fixture with `draft_for_human_review` records only; these drafts are not final quality evidence until reviewed as `manual` labels.
- Scope boundary:
  - no runtime code changes
  - no RP-2 advisory-only behavior
  - no Router prompt/parser changes
  - no State or committed routing output changes
  - no public API or workflow changes
  - no `/api/health` expansion

## 2026-04-24 - Local clean-env quality validation docs
- Files: `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Documented the local clean Python 3.11 validation path for Windows/Codex without changing runtime code:
  - recorded a clean-env recipe using `pyproject.toml` as the mainline Python dependency truth
  - clarified local mainline install as `.[dev]` plus separately installed `pytest`
  - clarified that `requirements-hf.txt` and `requirements-train.txt` are optional non-mainline inputs for HF/model-side and training/fine-tuning workflows
  - documented `PYTHONNOUSERSITE=1` plus env-local `TEMP`, `TMP`, and `MYPY_CACHE_DIR` for avoiding user-site contamination, C-drive temp-space issues, and cache permission failures
  - kept `scripts/quality/run_quality.py` as the repo-level quality command source of truth
- Clean-env validation evidence:
  - static gate passed
  - RP-1A unit tests: `8 passed`
  - graph smoke: `1 passed`
  - public API integration: `12 passed`
- Scope boundary:
  - documentation only
  - no runtime code changes
  - no RP-1A semantic changes
  - no public contract changes
  - no quality runner changes

## 2026-04-18 - RP-1A embedding-first route-prior shadow landed
- Files: `src/react_agent/route_profile_registry.py`, `src/react_agent/route_prior_embeddings.py`, `src/react_agent/route_prior.py`, `src/react_agent/graph.py`, `tests/unit_tests/test_route_profile_registry_rp1a.py`, `tests/unit_tests/test_route_prior_embeddings_rp1a.py`, `tests/unit_tests/test_route_prior_rp1a.py`, `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/MAINLINE_RUNTIME_AUDIT.md`, `docs/CHANGELOG.md`
- Added RP-1A as an internal embedding-first semantic-retrieval shadow seam without changing runtime topology or public surfaces:
  - introduced a text-first ordinary-agent route-profile registry built only from tracked metadata and explicit wildcard overrides
  - added an explicit OpenAI-compatible embedding backend seam plus in-process profile embedding cache and deterministic cosine scoring
  - wired the shadow retrieval into `router_node` before the formal Router invoke while keeping Router prompt shape, parse semantics, committed routing outputs, and public workflow unchanged
  - kept the seam fail-open: disabled or broken embedding config now only disables shadow retrieval privately and falls back to the existing formal Router path
  - kept observability trace-only through `LOCAL_TRACE` / `run_logger` and did not expand `/api/health`
  - added deterministic unit coverage for registry derivation, embedding cache hit/miss, shortlist guardrails, low-confidence fallback, wildcard retention, and router committed-output invariance
- Scope boundary:
  - no graph topology change
  - no new graph node
  - no formal Router ownership change
  - no public contract / workflow / transcript truth change
  - no public readiness expansion

## 2026-04-14 - Custom-agent scaffolding landed into repo truth
- Files: `.codex/agents/repo_explorer.toml`, `.codex/agents/protocol_auditor.toml`, `.codex/agents/docs_impact_analyst.toml`, `.codex/agents/test_impact_analyst.toml`, `AGENTS.md`, `docs/CHANGELOG.md`
- Added repo-scoped custom-agent scaffolding without changing current runtime or product behavior:
  - landed project-scoped custom-agent definitions under `.codex/agents/` for `repo_explorer`, `protocol_auditor`, `docs_impact_analyst`, and `test_impact_analyst`
  - kept `.agents/skills/` scoped to skills and recorded the directory split in `AGENTS.md`
  - documented the four agents' responsibility boundaries and the single-writer closeout rule in repo truth
  - preserved the corrected `test_impact_analyst` definition as a read-only test impact analyst instead of a docs analyst
- Scope boundary:
  - no runtime code changes
  - no public contract changes
  - no frontend behavior changes
  - no test logic changes

## 2026-04-09 - Mainline doc truth alignment
- Files: `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/INDEX.md`, `docs/MAINLINE_RUNTIME_AUDIT.md`, `docs/CHANGELOG.md`
- Why this closure was needed:
  - the current mainline runtime code had already converged on the active topology and public-boundary rules, but the authority docs in HEAD still contained older phase labels and an outdated mainline chain description
  - the mainline runtime audit existed only as local working-tree output and had not yet been landed as a tracked repository document
  - this round closes the documentation truth gap so future runtime reviews start from code-aligned docs instead of stale narrative entrypoints
- What changed:
  - updated the authority docs to reflect the current code-backed topology `router -> manager_broadcast + baseline_sidecar -> ... -> final_emit`
  - repositioned the current engineering phase language to `Phase F3 + QS-2`, while keeping `WS-1` explicitly documented as a landed streaming seam rather than the current repo phase label
  - added the mainline runtime audit as a first-class document and linked it from the docs entrypoints
- Scope boundary:
  - documentation only
  - no runtime logic changes
  - no protocol or default-value changes
  - no frontend behavior changes
  - no test behavior changes

## 2026-04-08 - Agent replacement guide protocol expansion
- Files: `docs/AGENT_REPLACEMENT_GUIDE.md`, `docs/CHANGELOG.md`
- Expanded the functional-agent replacement guide to cover external protocol integration without changing current graph business semantics:
  - kept the main recommendation unchanged: preserve the original `agent_id` and replace only the executable implementation
  - added an explicit protocol-selection section that distinguishes same-repo Python wrapping, FastAPI/HTTP private service integration, and higher-cost alternatives such as gRPC
  - documented why FastAPI/HTTP is the most natural default external boundary for this repo: ordinary agent execution is still one async request/response through `tool.ainvoke(...)`, and the repo already depends on `fastapi` and `httpx`
  - added a minimal FastAPI `/invoke` service example plus a local `httpx.AsyncClient` wrapper example that still registers through `register_agent(...)`
  - clarified that graph does not directly "switch to a protocol"; the real replacement point remains `AGENT_TOOLS[agent_id]`
- Scope boundary:
  - documentation only
  - no runtime code changes
  - no graph business-semantic changes
  - no public transcript / store / replay truth change

## 2026-04-08 - Functional agent replacement integration guide
- Files: `docs/AGENT_REPLACEMENT_GUIDE.md`, `docs/INDEX.md`, `docs/CHANGELOG.md`
- Added a focused Chinese implementation guide for the specific engineering scenario of replacing an existing functional agent with a classmate-developed corresponding agent without changing current graph business semantics:
  - explained the real runtime chain across `config/agents/agent_*.json`, `src/react_agent/agents.py`, `src/react_agent/graph_bootstrap.py`, and `src/react_agent/graph.py`
  - clarified that metadata-only changes do not equal a real runtime replacement because graph execution ultimately depends on `AGENT_TOOLS`
  - documented the recommended minimal strategy of keeping the original `agent_id` and layer while replacing only the executable tool implementation
  - distinguished ordinary functional agents from higher-risk special roles such as `a01_cio_orchestrator`, `a25_report_center`, and `a02_task_router`
  - included a minimal metadata example, an external-agent adapter skeleton, and a concrete validation checklist for proving the graph is actually invoking the replacement implementation
- Scope boundary:
  - documentation only
  - no runtime code changes
  - no graph business-semantic changes
  - no public transcript / store / replay truth change

## 2026-04-05 - Chat view right-overflow containment fix
- Files: `apps/web/src/styles/app.css`, `apps/web/src/styles/components.css`, `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/CHANGELOG.md`
- Fixed the chat-view layout bug where long assistant Markdown content could visually run into or beyond the right viewport edge:
  - added a stable horizontal gutter to the message list so chat content no longer sits flush against the screen edge
  - tightened the assistant answer card to a reading-first max width without changing the surrounding chat structure
  - added wrapping and max-width containment to the assistant Markdown body so long prose and inline tokens break inside the card
  - kept wide Markdown code blocks and tables scrollable inside the answer card instead of letting them stretch the page
- Scope boundary:
  - no backend or contract changes
  - no runtime business-semantic changes
  - no transcript / store / replay truth change
  - no workflow-inspector structural change

## 2026-04-05 - Phase WS-1 workflow-first streaming
- Files: `src/react_agent/public_contracts.py`, `src/react_agent/public_runtime.py`, `src/react_agent/public_api.py`, `tests/unit_tests/test_public_runtime_streaming.py`, `tests/integration_tests/test_public_api.py`, `apps/web/src/services/api.ts`, `apps/web/src/services/chat.ts`, `apps/web/src/types/chat.ts`, `apps/web/src/types/workflow.ts`, `apps/web/src/app/App.tsx`, `apps/web/src/app/routes.tsx`, `apps/web/src/components/workflow/WorkflowPanel.tsx`, `apps/web/src/styles/components.css`, `apps/web/src/test/smoke.tsx`, `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/CHANGELOG.md`
- Added a workflow-first streaming seam without changing LangGraph runtime business semantics or public transcript truth:
  - introduced additive `POST /api/threads/{thread_id}/messages/stream` using `application/x-ndjson`
  - typed the safe public event surface as `run.started`, `workflow.stage`, `workflow.snapshot`, `answer.final`, and `error`
  - projected cumulative graph state into fixed product workflow stages instead of exposing raw graph messages, raw router output, raw agent JSON, or chain-of-thought
  - kept the existing sync `POST /api/threads/{thread_id}/messages` seam intact and available
  - updated the web shell to show one optimistic assistant placeholder plus live workflow progress and then replace it with the final persisted answer
  - kept progress events client-visible only and persisted only the final assistant turn through the existing store/transcript path
- Scope boundary:
  - no SSE
  - no token streaming
  - no raw graph-event streaming
  - no transcript / store / replay truth change
  - no multi-speaker agent transcript
  - no LangGraph runtime business-semantic change

## 2026-04-05 - Phase F3 frontend assistant Markdown rendering fix
- Files: `apps/web/package.json`, `apps/web/package-lock.json`, `apps/web/src/components/chat/AssistantAnswerCard.tsx`, `apps/web/src/styles/components.css`, `apps/web/src/test/smoke.tsx`, `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/CHANGELOG.md`
- Fixed the assistant answer card so completed answers render as Markdown on the client without changing backend or runtime semantics:
  - replaced the old paragraph-splitting renderer with `react-markdown` + `remark-gfm` inside the assistant answer body only
  - added restrained assistant-card Markdown styles for headings, lists, blockquotes, tables, inline code, and fenced code blocks
  - extended the active frontend smoke entry to assert semantic Markdown rendering rather than raw Markdown punctuation
- Scope boundary:
  - no Python public-adapter contract changes
  - no LangGraph runtime business-semantic changes
  - no transcript / store / replay truth change
  - no workflow inspector structural change

## 2026-04-05 - Debug Phase 3 public runtime context injection
- Files: `src/react_agent/public_runtime.py`, `tests/unit_tests/test_public_runtime_context_invoke.py`, `docs/CHANGELOG.md`
- Fixed the current first-scene 503 without changing LangGraph runtime business semantics:
  - passed an explicit `Context()` into `graph_app.ainvoke(...)` from the public adapter path so graph nodes no longer see `runtime.context is None`
  - kept the existing HTTP error categories and public transcript/store/replay truth unchanged
  - added a small regression test that locks the public-runtime invoke path to always pass `context`
- Scope boundary:
  - minimal first-scene fix only
  - no provider/model remediation yet
  - no frontend changes
  - no graph business-logic refactor

## 2026-04-05 - Debug Phase 2 runtime exception surfacing
- Files: `src/react_agent/public_runtime.py`, `docs/CHANGELOG.md`
- Added a minimal debug surfacing patch for swallowed runtime exceptions without changing LangGraph runtime business semantics:
  - printed the full traceback, `type(exc).__name__`, and `repr(exc)` for the public-runtime graph import path
  - printed the same exception detail plus safe request context for `graph_app.ainvoke(...)` failures and public mapping failures
  - included `thread_id`, `continuity_mode`, truncated `user_text`, `MODEL` / `ROUTER_MODEL` / `BASELINE_MODEL`, and API-key presence flags so the next local 503 reproduction exposes the real first failure site
- Scope boundary:
  - debug surfacing only
  - no business-logic fix
  - no HTTP contract change
  - no transcript / store / replay truth change

## 2026-04-05 - Phase QS-3 final residual polish
- Files: `scripts/quality/run_provider_live_smoke.py`, `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/INDEX.md`, `docs/RUNBOOK_ROUTER_SFT.md`, `docs/CHANGELOG.md`
- Closed the last narrow QS residuals without changing LangGraph runtime business semantics:
  - tightened the optional provider/live smoke artifact so the skipped path now summarizes the full residual prerequisite state instead of only the first missing condition
  - reran the optional smoke and kept the evidence honest: the current local artifact still remains `status="skipped"` because provider credentials, `TAVILY_API_KEY`, and provider-backed runtime readiness are still unavailable
  - advanced the authority docs from QS-2 to QS-3 wording and cleaned the remaining top-level phase/drift language that could still be misread as current truth
- Scope boundary:
  - no new product features
  - no LangGraph runtime business-semantic changes
  - no transcript / store / replay truth change
  - provider/live smoke remains optional and outside the default blocking gate

## 2026-04-05 - Phase QS-2 residual quality closure
- Files: `scripts/quality/run_quality.py`, `scripts/quality/run_provider_live_smoke.py`, `Makefile`, `.github/workflows/unit-tests.yml`, `.github/workflows/integration-tests.yml`, `tests/integration_tests/test_graph.py`, `apps/web/src/test/smoke.tsx`, `apps/web/src/test/app.smoke.legacy.tsx`, `apps/web/src/test/workflow.smoke.legacy.tsx`, `pyproject.toml`, `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/INDEX.md`, `docs/RUNBOOK_ROUTER_SFT.md`, `docs/CHANGELOG.md`, `docs/FRONTEND_ARCHITECTURE.md`, `AGENTS.md`
- Closed the main residual quality gaps without changing LangGraph runtime business semantics:
  - promoted `scripts/quality/run_quality.py` into a fuller blocking-gate source of truth by adding `ruff`, `mypy`, `codespell`, and the runtime graph smoke test
  - upgraded the blocking `Quality Gate` workflow so static checks and graph smoke now run through the same repo-level quality runner instead of living only in workflow-local steps
  - clarified the active test surface by keeping `tests/integration_tests/test_graph.py` in the blocking path and demoting the old frontend `.test.tsx` fixtures into `.legacy.tsx` reference files
  - kept provider/live smoke optional and non-blocking while making its artifact spell out residual conditions and rerun triggers when the environment is not ready
  - performed a second authority-doc cleanup pass so the current phase, command truth, active gate scope, and optional provider/live smoke boundary read consistently
- Scope boundary:
  - no new product features
  - no LangGraph runtime business-semantic changes
  - no transcript / store / replay truth change
  - provider/live smoke remains optional and outside the default blocking gate

> Historical note: entries below are preserved for continuity. Older pre-QS entries may retain original wording or encoding noise; for current repo-level truth, prefer the QS-3/QS-2 entries, `docs/SYSTEM_MAP.md`, and the code-backed validation paths.

## 2026-04-05 - Phase QS-1B quality-stable minimal closure
- Files: `scripts/quality/run_quality.py`, `scripts/quality/run_provider_live_smoke.py`, `Makefile`, `.github/workflows/unit-tests.yml`, `.github/workflows/integration-tests.yml`, `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `docs/INDEX.md`, `docs/RUNBOOK_ROUTER_SFT.md`
- Closed the first repo-level quality loop without changing LangGraph runtime business semantics:
  - introduced `scripts/quality/run_quality.py` as the single repo-level quality entry for unit tests, public adapter integration tests, frontend build/test, and the deterministic fusion gate
  - kept `Makefile` as a thin convenience wrapper around that quality runner instead of a second command source of truth
  - upgraded the main GitHub workflow into a blocking `Quality Gate` that now covers Python unit tests, public adapter integration tests, frontend build/test, and deterministic fusion gate artifacts
  - converted the previous integration workflow into an optional provider/live smoke workflow with a scripted artifact path under `ops/regression/provider/out/provider_live_smoke.json`
  - replaced the most authority-critical mojibake/drifted docs with clean QS-1B-aligned command and phase descriptions
- Scope boundary:
  - no new product features
  - no LangGraph runtime business-semantic changes
  - no transcript / store / replay truth change
  - provider/live smoke remains optional and outside the default blocking gate

## 2026-04-04 - Phase PF-2E-B URL reference minimal slice
- Files: `src/react_agent/public_contracts.py`, `src/react_agent/public_api.py`, `src/react_agent/public_mapping.py`, `tests/integration_tests/test_public_api.py`, `apps/web/src/types/chat.ts`, `apps/web/src/components/shell/Composer.tsx`, `apps/web/src/components/chat/UserBubble.tsx`, `apps/web/src/utils/structuredInput.ts`, `apps/web/src/styles/components.css`, `apps/web/src/test/smoke.tsx`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `AGENTS.md`
- Added the first minimal URL-reference input path on top of the existing typed seam without changing LangGraph runtime business semantics:
  - extended `structuredInput` with additive `urlReferences` as a simple ordered string list
  - compiled those URL references into a fixed canonical `【链接参考 / URL 引用】` transcript section while keeping `text` as the only replay/store truth
  - preserved strict ingress mismatch validation so the typed URL mirror cannot drift away from canonical transcript text
  - kept runtime invoke and replay text-only while letting the frontend prefer the typed mirror for user-bubble rendering
  - preserved compatibility for old turns, text-only messages, PF-2B/PF-2C structured input turns, and PF-2D pasted-material turns
- Scope boundary:
  - no URL fetch
  - no HTML parsing
  - no snapshot persistence
  - no file upload
  - no LangGraph runtime business-semantic changes
  - no SSE / streaming

## 2026-04-04 - Phase PF-2D-B pasted material / notes cards
- Files: `src/react_agent/public_contracts.py`, `src/react_agent/public_api.py`, `src/react_agent/public_mapping.py`, `tests/integration_tests/test_public_api.py`, `apps/web/src/types/chat.ts`, `apps/web/src/components/shell/Composer.tsx`, `apps/web/src/components/chat/UserBubble.tsx`, `apps/web/src/utils/structuredInput.ts`, `apps/web/src/styles/components.css`, `apps/web/src/test/smoke.tsx`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `AGENTS.md`
- Added the first minimal source-material input path on top of the existing typed seam without changing LangGraph runtime business semantics:
  - extended `structuredInput` with pasted `materials` / notes cards as a simple string list
  - compiled those notes cards into a fixed canonical `【补充材料/笔记】` transcript section while keeping `text` as the only replay/store truth
  - preserved strict ingress mismatch validation so the typed mirror cannot drift away from canonical transcript text
  - kept replay and runtime invoke text-only while letting the frontend prefer the typed mirror for user-bubble rendering
  - preserved compatibility for old turns, text-only messages, and earlier PF-2B / PF-2C structured input turns
- Scope boundary:
  - no file upload
  - no URL ingest
  - no LangGraph runtime business-semantic changes
  - no SSE / streaming

## 2026-04-04 - Phase PF-2C-B typed input contract implementation
- Files: `src/react_agent/public_contracts.py`, `src/react_agent/public_api.py`, `src/react_agent/public_mapping.py`, `tests/integration_tests/test_public_api.py`, `apps/web/src/types/chat.ts`, `apps/web/src/services/chat.ts`, `apps/web/src/components/shell/Composer.tsx`, `apps/web/src/components/chat/UserBubble.tsx`, `apps/web/src/utils/structuredInput.ts`, `apps/web/src/test/smoke.tsx`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `AGENTS.md`
- Upgraded PF-2B structured input from a frontend-only compile strategy into an additive typed public seam without changing LangGraph runtime business semantics:
  - added optional `structuredInput` to `SendMessageRequest` and `PublicTurn`
  - kept `text` as the canonical public transcript, public-store, and replay truth
  - added ingress validation that rejects requests when `text` and `structuredInput` do not compile to the same canonical transcript text
  - kept runtime invoke and replay text-only while allowing the frontend to prefer the typed mirror for user-bubble rendering
  - preserved compatibility for older turns and ordinary text-only messages through text fallback rendering
- Scope boundary:
  - no LangGraph runtime business-semantic changes
  - no file upload
  - no URL ingest
  - no SSE / streaming

## 2026-04-04 - Phase PF-2B structured input / context pack
- Files: `apps/web/src/components/shell/Composer.tsx`, `apps/web/src/components/chat/UserBubble.tsx`, `apps/web/src/utils/structuredInput.ts`, `apps/web/src/content/zh-CN.ts`, `apps/web/src/styles/components.css`, `apps/web/src/test/smoke.tsx`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `AGENTS.md`
- Added the first richer chat input surface without changing the public adapter or runtime contract:
  - introduced a collapsed structured input / context pack layer in the composer for task, background, constraints, and output preference
  - kept the existing `sendMessage(threadId, text)` seam by compiling structured input into normalized transcript text before submission
  - kept public transcript, JSON file-backed store, and replay continuity honest by treating the compiled user text as the only persisted truth source
  - added user-bubble parsing so compiled structured input can render as a lightweight structured card without introducing a second hidden input schema
  - kept the existing chat, settings, agents, workflow, and debug boundaries unchanged
- Scope boundary:
  - no Python public-adapter contract changes
  - no LangGraph runtime business-semantic changes
  - no file upload
  - no URL ingest
  - no SSE / streaming

## 2026-04-04 - Phase PF-1C live Agents
- Files: `src/react_agent/public_api.py`, `src/react_agent/public_contracts.py`, `tests/integration_tests/test_public_api.py`, `apps/web/src/app/App.tsx`, `apps/web/src/app/routes.tsx`, `apps/web/src/pages/AgentsPage.tsx`, `apps/web/src/components/agents/AgentCatalogView.tsx`, `apps/web/src/services/chat.ts`, `apps/web/src/types/agents.ts`, `apps/web/src/mocks/agents.ts`, `apps/web/src/content/zh-CN.ts`, `apps/web/src/styles/components.css`, `apps/web/src/test/smoke.tsx`, `apps/web/src/test/app.smoke.test.tsx`, `apps/web/src/test/workflow.smoke.test.tsx`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `AGENTS.md`
- Turned `/agents` from a frontend mock into a live read-only catalog without changing LangGraph runtime business semantics:
  - added `GET /api/agents` as a metadata-only public catalog seam
  - kept the catalog truth source on `config/agents/*.json`, `react_agent.agents.AGENT_METADATA`, and `default_enabled` filtering instead of importing graph bootstrap/runtime state
  - switched the web `Agents` page to fetch live catalog data on demand instead of reading a hardcoded mock constant on the product path
  - kept the page as a Chinese catalog/description surface rather than a runtime control panel
  - preserved the existing live chat and read-only settings flows without expanding the chat bootstrap surface
- Scope boundary:
  - no LangGraph runtime business-semantic changes
  - no direct rendering of raw graph messages
  - no multi-speaker agent transcript
  - no telemetry / runtime control console
  - no SSE / streaming

## 2026-04-04 - Phase PF-1B real Settings / readiness
- Files: `apps/web/src/app/App.tsx`, `apps/web/src/app/routes.tsx`, `apps/web/src/pages/SettingsPage.tsx`, `apps/web/src/pages/ChatPage.tsx`, `apps/web/src/components/shell/Sidebar.tsx`, `apps/web/src/components/shell/ThreadHeader.tsx`, `apps/web/src/components/shell/Composer.tsx`, `apps/web/src/components/shell/MessageList.tsx`, `apps/web/src/components/chat/AssistantAnswerCard.tsx`, `apps/web/src/components/chat/UserBubble.tsx`, `apps/web/src/config/appConfig.ts`, `apps/web/src/content/zh-CN.ts`, `apps/web/src/styles/app.css`, `apps/web/src/styles/components.css`, `apps/web/src/test/smoke.tsx`, `apps/web/src/test/app.smoke.test.tsx`, `apps/web/src/test/workflow.smoke.test.tsx`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added the first real `/settings` product page on top of the frozen frontend baseline without changing public-adapter or runtime semantics:
  - turned the sidebar settings entry into a real route instead of a disabled placeholder
  - reused the existing `GET /api/health` contract to render a read-only readiness/status page in Chinese product copy
  - kept continuity disclosure honest by stating that replay continuity is weaker than persistent graph continuity
  - preserved the existing chat thread list/detail/send-message live path and kept technical provenance/debug folded out of the primary chat view
- Scope boundary:
  - no LangGraph runtime business-semantic changes
  - no new backend endpoint when `/api/health` is already sufficient
  - no direct rendering of raw graph messages
  - no multi-speaker agent transcript
  - no SSE / streaming

## 2026-04-04 - Phase UX-1F 阅读节奏与引用/流程细节精修
- Files: `apps/web/src/components/chat/AssistantAnswerCard.tsx`, `apps/web/src/styles/app.css`, `apps/web/src/styles/components.css`, `apps/web/src/test/smoke.tsx`, `apps/web/scripts/capture-screenshots.mjs`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Continued refining the existing Chinese-first live shell without changing adapter or runtime semantics:
  - tightened sidebar/header/composer density by one more step for a lighter reading-first shell
  - made citations feel more like post-answer references instead of a second component block
  - kept technical provenance/debug folded by default and further protected the main view from operator-style copy
  - reduced workflow rail width, card weight, padding, and badge prominence so the expanded inspector reads more like a light timeline than stacked panels
  - refreshed screenshot regression output for the chat homepage and expanded workflow state
- Scope boundary:
  - no Python public-adapter contract changes
  - no LangGraph runtime business-semantic changes
  - no direct rendering of raw graph messages
  - no multi-speaker agent transcript
  - no SSE / streaming

## 2026-04-04 - Phase UX-1E 排版节奏与 workflow 轻量化精修
- Files: `apps/web/src/config/appConfig.ts`, `apps/web/src/content/zh-CN.ts`, `apps/web/src/components/shell/Sidebar.tsx`, `apps/web/src/components/shell/ThreadHeader.tsx`, `apps/web/src/components/shell/Composer.tsx`, `apps/web/src/components/chat/AssistantAnswerCard.tsx`, `apps/web/src/components/workflow/*`, `apps/web/src/styles/*`, `apps/web/src/test/*`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Tightened the existing Chinese-first live shell without changing adapter or runtime semantics:
  - reduced brand-block, header, message-list, workflow, and composer density for a calmer reading rhythm
  - kept technical provenance/debug details folded by default and out of the main reading layer
  - further lightened the expanded workflow inspector into a thinner timeline-and-stage presentation
  - softened the sidebar primary action and secondary navigation hierarchy without changing the live thread flow
  - refreshed screenshot regression output for the chat homepage and expanded workflow state
- Scope boundary:
  - no Python public-adapter contract changes
  - no LangGraph runtime business-semantic changes
  - no direct rendering of raw graph messages
  - no multi-speaker agent transcript
  - no SSE / streaming

## 2026-04-04 - Phase UX-1D 中文产品化微调与截图回归
- Files: `apps/web/src/content/zh-CN.ts`, `apps/web/src/components/shell/Sidebar.tsx`, `apps/web/src/components/chat/AssistantAnswerCard.tsx`, `apps/web/src/components/workflow/*`, `apps/web/src/styles/app.css`, `apps/web/src/styles/components.css`, `apps/web/src/test/*`, `apps/web/scripts/capture-screenshots.mjs`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Tightened the Chinese-first live shell toward the target reference without changing the public adapter or runtime semantics:
  - removed continuity/checkpointer hints from the default degraded banner and kept technical provenance/debug inside a folded `技术详情` layer
  - lightened the workflow expanded state by reducing gutter width, padding, card weight, and overall vertical footprint
  - reduced composer height and whitespace while preserving the existing live request/response behavior
  - refined sidebar spacing, history selection, and secondary navigation hierarchy for a steadier product surface
  - refreshed screenshot regression artifacts for the chat homepage and expanded workflow inspector
- Scope boundary:
  - no Python public-adapter contract changes
  - no LangGraph runtime business-semantic changes
  - no direct rendering of raw graph messages
  - no multi-speaker agent transcript
  - no SSE / streaming

## 2026-04-04 - Phase UX-1C 参考图驱动的中文产品化视觉对齐
- Files: `apps/web/src/config/appConfig.ts`, `apps/web/src/content/zh-CN.ts`, `apps/web/src/app/App.tsx`, `apps/web/src/components/shell/*`, `apps/web/src/components/chat/*`, `apps/web/src/components/workflow/*`, `apps/web/src/pages/AgentsPage.tsx`, `apps/web/src/components/agents/AgentCatalogView.tsx`, `apps/web/src/mocks/*`, `apps/web/src/styles/*`, `apps/web/src/test/*`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Realigned the live web shell toward a calmer, Chinese-first product surface without changing the Python adapter contract or LangGraph runtime semantics:
  - replaced the previous editorial / engineering-cockpit styling with a gray-left-rail + white-reading-surface shell
  - centralized shell copy and brand presentation for `资本市场认知智能体系统`
  - moved workflow back to a lightweight answer-level inspector, collapsed by default into a one-line collaboration summary
  - reduced the visual weight of provenance/debug metadata while keeping the existing safe fields available
  - de-emphasized developer-phase wording and translated primary navigation, state, and workflow copy into Chinese
  - added reproducible desktop screenshots for the chat homepage and expanded workflow inspector under `apps/web/artifacts/`
- Scope boundary:
  - no Python public-adapter contract changes
  - no LangGraph runtime business-semantic changes
  - no direct rendering of raw graph messages
  - no multi-speaker agent transcript
  - no SSE / streaming

## 2026-04-03 - Phase F3 health hardening + continuity/debug polish
- Files: `src/react_agent/public_api.py`, `src/react_agent/public_contracts.py`, `src/react_agent/public_mapping.py`, `src/react_agent/public_runtime.py`, `tests/integration_tests/test_public_api.py`, `apps/web/src/app/App.tsx`, `apps/web/src/app/routes.tsx`, `apps/web/src/pages/ChatPage.tsx`, `apps/web/src/components/shell/*`, `apps/web/src/components/chat/*`, `apps/web/src/components/workflow/*`, `apps/web/src/services/api.ts`, `apps/web/src/types/*`, `apps/web/src/test/*`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `AGENTS.md`, `.agents/skills/langgraph-public-adapter/SKILL.md`, `.agents/skills/docs-sync/SKILL.md`
- Hardened the existing public adapter and live web shell without changing LangGraph runtime business semantics:
  - expanded `/api/health` into a public-safe readiness surface for runtime import, provider env, search env, checkpointer status, and overall degraded-vs-ready state
  - unified continuity classification so health and message invoke use the same adapter-side readiness probe and only label continuity as `persistent` on the canonical persistent graph path
  - extended the public turn/workflow contract with safe provenance/debug fields: `runId`, assistant-turn `continuityMode`, `evidenceCount`, and normalized emit-path provenance
  - replaced plain-string adapter/runtime errors with structured sanitized error details and added failure-path contract coverage for `503` runtime unavailability
  - upgraded the web shell to distinguish unavailable, degraded, and ordinary request-error states while keeping a single assistant persona and workflow-only collaboration UI
- Scope boundary:
  - no LangGraph runtime business-semantic changes
  - no direct rendering of raw graph messages
  - no raw router output / raw manager assignment / raw agent JSON exposure
  - no raw baseline / judge / writer payload exposure
  - no multi-speaker agent transcript
  - no SSE / streaming

## 2026-04-03 - Phase F2 public adapter + live sync integration
- Files: `src/react_agent/public_api.py`, `src/react_agent/public_contracts.py`, `src/react_agent/public_mapping.py`, `src/react_agent/public_runtime.py`, `src/react_agent/public_store.py`, `tests/integration_tests/test_public_api.py`, `apps/web/src/app/App.tsx`, `apps/web/src/app/routes.tsx`, `apps/web/src/pages/ChatPage.tsx`, `apps/web/src/components/shell/*`, `apps/web/src/components/chat/*`, `apps/web/src/components/workflow/*`, `apps/web/src/services/*`, `apps/web/src/types/*`, `apps/web/src/test/*`, `pyproject.toml`, `README.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/INDEX.md`, `docs/CHANGELOG.md`, `AGENTS.md`, `.agents/skills/langgraph-public-adapter/SKILL.md`, `.agents/skills/docs-sync/SKILL.md`
- Added a Python public adapter / BFF and switched `apps/web` chat threads from mock-first to live sync integration:
  - introduced `FastAPI + uvicorn` public endpoints for health, thread list/detail, thread creation, and sync send-message flows
  - added a JSON file-backed public store at `var/public_api/threads.json`
  - mapped runtime state into a safe public contract based on `emitted_bundle`, `final_answer_source`, and workflow status fields
  - kept `/agents` on the existing mock catalog path
  - refactored the frontend to use live API services plus loading/error/unavailable states instead of direct mock imports as the primary chat data source
  - added adapter contract coverage and frontend live integration smoke coverage
- Scope boundary:
  - no LangGraph runtime business-semantic changes
  - no direct rendering of raw graph messages
  - no raw router output / raw manager assignment / raw agent JSON exposure
  - no multi-speaker agent transcript
  - no SSE / streaming
  - transcript replay remains a weaker continuity fallback and is explicitly labeled as such

## 2026-04-03 - Phase F1 Frontend shell + mock workflow + Codex collaboration scaffolding
- Files: `apps/web/package.json`, `apps/web/tsconfig.json`, `apps/web/vite.config.ts`, `apps/web/index.html`, `apps/web/src/app/App.tsx`, `apps/web/src/app/routes.tsx`, `apps/web/src/pages/ChatPage.tsx`, `apps/web/src/pages/AgentsPage.tsx`, `apps/web/src/components/**/*`, `apps/web/src/mocks/*`, `apps/web/src/types/*`, `apps/web/src/styles/*`, `apps/web/src/test/*`, `AGENTS.md`, `.agents/skills/*/SKILL.md`, `docs/FRONTEND_ARCHITECTURE.md`, `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SYSTEM_MAP.md`, `docs/INDEX.md`, `docs/CHANGELOG.md`, `.gitignore`
- Added a mock-first DeerFlow-style chat shell without touching LangGraph runtime business semantics:
  - introduced `apps/web/` as a local `npm + Vite + React + TypeScript` frontend project
  - added a chat-first shell with sidebar, single-assistant thread, composer, answer card, and default-collapsed workflow inspector
  - added an `Agents` page with the audited 26-config / 25-runtime-node catalog snapshot and explicit `a02_task_router` disabled state
  - kept workflow as a summarized planning/execution/fusion/final-source layer instead of multi-speaker chat
  - added root `AGENTS.md`, repo skills under `.agents/skills/`, and `docs/FRONTEND_ARCHITECTURE.md`
  - added frontend smoke coverage through `vitest` component tests
- Scope boundary:
  - no live backend integration
  - no Python HTTP adapter
  - no LangGraph runtime semantic changes
  - no direct rendering of raw graph messages
  - no conversion of internal agents into public chat speakers

## 2026-04-03 - FF-5B Fusion Regression / Eval / Gate
- Files: `ops/regression/fusion/__init__.py`, `ops/regression/fusion/scenario_catalog.py`, `ops/regression/fusion/run_fusion_regression.py`, `ops/regression/fusion/eval_fusion_outputs.py`, `ops/regression/fusion/gate_fusion_outputs.py`, `tests/unit_tests/test_fusion_regression_eval_gate_ff5b.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added a deterministic, network-free fusion regression/eval/gate toolchain without changing graph business semantics:
  - introduced a fixed FF-5B scenario catalog covering the flag/source/baseline-terminal/shadow-consistency/emitted-provenance/results-pool-isolation matrices
  - `run_fusion_regression.py` now materializes deterministic fusion run records into `ops/regression/fusion/out/fusion_runs.jsonl`
  - `eval_fusion_outputs.py` aggregates those runs into `fusion_metrics.json`
  - `gate_fusion_outputs.py` converts metrics into `fusion_gate.json` with explicit thresholds and separate warning vs failing checks
  - tracing noise classification is now first-class in the deterministic gate schema and is tracked separately from business failures
- Scope boundary:
  - no Router / a01 / a25 / baseline sidecar / judge / writer / source-switch business-logic changes
  - no live provider call is required for the default gate
  - `memory_update`, `final_emit`, and baseline isolation semantics remain unchanged

## 2026-04-03 - FF-4B Final source switch
- Files: `src/react_agent/context.py`, `src/react_agent/state.py`, `src/react_agent/graph.py`, `tests/unit_tests/test_final_source_switch_ff4b.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Enabled guarded final source switching on top of the existing source-neutral `final_emit` seam:
  - added `Context.enable_fair_fusion_source_switch` (default off) and `State.emitted_bundle`
  - `final_emit_payload` now materializes real `mainline` / `baseline` / `fused` payloads when the source-switch flag is enabled
  - `_emit_final_answer(...)` now records the actual `final_answer_source` and `emitted_bundle`, and `stable_findings` now uses the emitted bundle's question/answer instead of assuming mainline text
  - the staged mainline bundle remains canonical in `multi_agent_bundle`; non-mainline emits no longer overwrite it
- Scope boundary:
  - default behavior remains unchanged when `ENABLE_FAIR_FUSION_SOURCE_SWITCH=false`
  - no Router / a01 / a25 prompt changes
  - no baseline writes into `layer_plan`, a01 contract, `analyst_results`, or `ephemeral_results`
  - no direct writer-side writes into `messages`
  - `memory_update` still follows only final emitted `messages`

## 2026-04-03 - FF-4A Fusion Writer shadow mode + source-neutral final emit seam
- Files: `src/react_agent/state.py`, `src/react_agent/graph.py`, `src/react_agent/prompts.py`, `tests/unit_tests/test_fusion_writer_shadow_ff4a.py`, `tests/unit_tests/test_fusion_judge_shadow_ff3b.py`, `tests/unit_tests/test_fan_in_seam_ff3a.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added a shadow-only fusion writer and a source-neutral final emit seam without changing the current visible answer source:
  - introduced isolated writer/emit state: `writer_status`, `writer_output`, and `final_emit_payload`
  - expanded `fusion_verdict` into a writer-ready protocol with `decision` (`mainline|baseline|fused`), `rewrite_plan`, and `accepted_cards`
  - inserted `fusion_writer_shadow` between `fusion_judge_shadow` and final emit; the writer reads only `fusion_verdict`, `multi_agent_bundle`, `baseline_status`, and `baseline_bundle`
  - generalized the staged closeout path into `final_emit`, while keeping the current emitted answer mapped to the mainline bundle and preserving `messages` / `is_last_step` / `stable_findings` / `memory_update`
- Scope boundary:
  - no Router / a01 / a25 prompt changes
  - no writes into `analyst_results` / `ephemeral_results`
  - no writer-side writes into `messages` or `final_answer_source`
  - no final answer source switch; `final_answer_source` still ends as `"mainline"`

## 2026-04-02 - FF-3B Fusion Judge shadow mode
- Files: `src/react_agent/state.py`, `src/react_agent/graph.py`, `src/react_agent/prompts.py`, `tests/unit_tests/test_fusion_judge_shadow_ff3b.py`, `tests/unit_tests/test_fan_in_seam_ff3a.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added a shadow-only fusion judge behind the existing FF-3A fan-in seam:
  - introduced isolated judge state: `judge_status` and `fusion_verdict`
  - `router_node(...)` now resets judge sidecars each new turn
  - `fusion_gate` now routes compare-ready A/B inputs to `fusion_judge_shadow`, and only routes to `mainline_emit` after the judge reaches a terminal state
  - `fusion_judge_shadow` compares `multi_agent_bundle` against `baseline_bundle` and records a structured JSON verdict without writing `messages` or changing `final_answer_source`
- Scope boundary:
  - no Router / a01 / a25 prompt changes
  - no writes into `analyst_results` / `ephemeral_results`
  - no fusion writer yet
  - no final answer source switch; `final_answer_source` still ends as `"mainline"`

## 2026-04-02 - FF-3A Judge-ready fan-in seam
- Files: `src/react_agent/state.py`, `src/react_agent/graph.py`, `tests/unit_tests/test_fan_in_seam_ff3a.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added a Judge-ready fan-in seam without changing the current final answer source:
  - introduced isolated state for staged mainline readiness and emit recovery: `mainline_status`, `mainline_emit_payload`, and `final_answer_source`
  - when `enable_fair_fusion=True`, final-layer mainline summary now stages `multi_agent_bundle` and a deferred emit payload before writing the final answer
  - replaced `baseline_sidecar -> __end__` with `baseline_sidecar -> fusion_gate`, and added a branch-safe `fusion_gate` plus `mainline_emit`
  - `mainline_emit` now owns the staged final write path and still closes out through the existing `messages` / `is_last_step` / `stable_findings` / `memory_update` semantics
- Scope boundary:
  - no Router / a01 / a25 prompt changes
  - no a01 contract dispatch changes
  - no writes into `analyst_results` / `ephemeral_results`
  - no Judge prompt, no Writer node, and no final answer source switch yet

## 2026-04-02 - FF-2B.1 Gemini grounding JSON compatibility fix
- Files: `src/react_agent/baseline_sidecar.py`, `tests/unit_tests/test_baseline_sidecar_gemini_ff2b.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Fixed Gemini Developer API grounding request construction for the isolated baseline sidecar:
  - when Gemini grounding/search tool use is enabled, the baseline sidecar no longer sends `response_mime_type="application/json"`
  - Gemini output remains JSON-constrained by prompt and is parsed locally from `response.text`
  - grounding receipts and best-effort citation extraction remain unchanged
- Scope boundary:
  - no Router / Manager / Agent / Summary mainline control-flow changes
  - no a01 contract dispatch changes
  - no FINAL_LAYER finalize changes
  - no writes into `analyst_results` / `ephemeral_results`
  - no generic-provider baseline behavior change

## 2026-04-02 - FF-2B Gemini baseline hardening
- Files: `src/react_agent/baseline_sidecar.py`, `tests/unit_tests/test_baseline_sidecar_gemini_ff2b.py`, `.env.example`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `pyproject.toml`
- Hardened the isolated Fair Fusion baseline sidecar for Gemini Developer API usage without changing mainline graph behavior:
  - when `baseline_model` resolves to `google_genai/...`, the baseline sidecar now bypasses the generic LangChain `model.ainvoke(...)` path and calls Gemini Developer API directly via `google-genai`
  - Gemini runs request Google Search grounding through the provider-native tool path instead of only recording prompt/meta intent
  - `baseline_bundle.search_meta` now distinguishes request intent from execution receipts via provider/search grounding fields such as `search_executed`, `grounding_metadata_present`, `web_search_queries`, and grounding counts
  - `baseline_bundle.evidence_cards` now best-effort merges Gemini grounding citation data when available
- Scope boundary:
  - no Router / Manager / Agent / Summary mainline control-flow changes
  - no a01 contract dispatch changes
  - no FINAL_LAYER finalize changes
  - no writes into `analyst_results` / `ephemeral_results`
  - no final answer source switching and no fusion judge / fusion writer yet

## 2026-04-02 - FF-2A baseline sidecar shadow scaffold
- Files: `src/react_agent/context.py`, `src/react_agent/state.py`, `src/react_agent/prompts.py`, `src/react_agent/baseline_sidecar.py`, `src/react_agent/graph.py`, `tests/unit_tests/test_baseline_sidecar_shadow_ff2a.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added isolated Fair Fusion baseline scaffold state:
  - `State.baseline_status`
  - `State.baseline_bundle`
- Added baseline-specific context knobs:
  - `baseline_model`
  - `baseline_openai_base_url`
  - `baseline_openai_api_key`
  - `enable_fair_fusion`
  - `baseline_force_search`
- Added a new `baseline_sidecar` shadow branch after `router`:
  - feature-flagged by `enable_fair_fusion` (default off)
  - writes only `baseline_status` / `baseline_bundle`
  - does not join `layer_plan`, a01 contract, `analyst_results`, or `ephemeral_results`
- Router now explicitly resets FF sidecar fields each new turn:
  - `multi_agent_bundle`
  - `baseline_status`
  - `baseline_bundle`
- Scope boundary:
  - no Router / Manager / Agent / Summary control-flow change on the mainline path
  - no a01 contract dispatch change
  - no FINAL_LAYER finalize change
  - no fusion judge / fusion writer yet
  - no final answer source switching yet

## 2026-04-02 - FF-1 mainline bundle seam for final summary
- Files: `src/react_agent/state.py`, `src/react_agent/graph.py`, `tests/unit_tests/test_mainline_bundle_seam_ff1.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added optional `State.multi_agent_bundle` as a final-summary sidecar for future Fair Fusion work while keeping current user-visible output unchanged.
- Split `_run_final_summary(...)` into two internal responsibilities without changing graph topology or closeout routing:
  - `_build_mainline_bundle(...)` builds the current mainline summary payload and returns the existing final `AIMessage`.
  - `_emit_final_answer(...)` preserves the current closeout write path (`messages`, `is_last_step`, `layer_done`, and opt-in `stable_findings` append).
- Kept current boundaries unchanged:
  - No Router / Manager / Agent control-flow changes.
  - No a01 contract dispatch changes.
  - No FINAL_LAYER finalize routing changes.
  - No new writes into `analyst_results` / `ephemeral_results`.
- Added focused seam coverage for `multi_agent_bundle` generation and final-summary/finalize compatibility.

## 2026-04-02 - Studio schema compatibility for AgentOutput
- Files: `src/react_agent/agents.py`, `tests/unit_tests/test_agent_output_schema_surface.py`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Replaced the old `class AgentOutput(Dict[str, Any])` surface with a schema-generatable dict-shaped `TypedDict` so LangGraph Studio / API schema export can describe `AgentOutput` without hitting `Unable to generate pydantic-core schema for <class 'react_agent.agents.AgentOutput'>`.
- Preserved current runtime compatibility:
  - Agent results remain plain dict objects at runtime.
  - `parse_ok` and `contract` are explicitly represented on the type surface.
  - Extra parser keys are still preserved by runtime code because graph/default-agent logic continues to read and write plain dicts rather than validated model instances.
- Added a focused schema regression test covering both `TypeAdapter(AgentOutput).json_schema()` and `TypeAdapter(State).json_schema()`.
- Scope boundary: Studio schema / type compatibility only. No Router / Manager / Agent / Summary control-flow changes, no a01 contract dispatch changes, no FINAL_LAYER finalize changes, and no reducer semantic changes.

## 2026-04-02 - Warning hardening for local dev baseline
- Files: `src/react_agent/tools.py`, `.env.example`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Removed the local dev Tavily deprecation warning by switching the search tool implementation from deprecated `langchain_community.tools.tavily_search.TavilySearchResults` to the already-installed `langchain_tavily.TavilySearch`.
- Kept Tavily import-time behavior and public surface unchanged for current runtime callers:
  - `tavily_search` remains the module-level tool instance.
  - `build_tavily_search(max_results)` still returns a named Tavily tool configured with `search_depth="basic"`.
  - No Router / Manager / Agent / Summary control-flow changes, no a01 contract dispatch changes, and no FINAL_LAYER finalize behavior changes.
- Clarified the local dev tracing baseline:
  - `.env.example` now documents LangSmith tracing as explicit opt-in instead of an implied baseline.
  - README and SYSTEM_MAP now distinguish repo-local `LOCAL_TRACE` JSONL logging from remote LangSmith tracing.
  - Existing untracked local `.env` files may still carry `LANGSMITH_TRACING=true`; aligning that local file is outside version-controlled repo changes.
- Scope boundary: warning / baseline / docs only. This change does not touch `AgentOutput` / `State` schema surface and does not address `/assistants/{assistant_id}/schemas` warnings.

## 2026-03-31 - Docs narrative alignment for current engineering snapshot
- Files: `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/INDEX.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Aligned narrative-facing docs with the current runtime and test-backed repo reality:
  - README now describes the repo as a LangGraph layered multi-agent system, not a generic template overview.
  - PROJECT_OVERVIEW now serves as the primary narrative snapshot for the current repo, including runtime entry, main chain, a01 contract role, env-gated capability boundaries, and stage positioning.
  - INDEX now separates document roles more explicitly: `PROJECT_OVERVIEW` for narrative snapshot, `SYSTEM_MAP` / `RUNBOOK_ROUTER_SFT` for operational truth, runtime code plus focused tests for behavior truth.
  - SYSTEM_MAP received a minimal scope-boundary note so high-level narrative does not get confused with command/runtime truth.
- Clarified current stage wording as `structure-stable`, not `quality-stable`, and avoided upgrading optional env-gated features into default behavior.
- Scope boundary: documentation alignment only. No runtime business-logic changes, no schema changes, no prompt/runtime contract changes, and no test semantic changes.

## 2026-03-11 - 502 observability slice (trace + analyzer)
- Files: `src/react_agent/graph.py`, `src/react_agent/default_agents.py`, `src/react_agent/run_logger.py`, `ops/regression/analyze_trace.py`, `tests/unit_tests/test_trace_analyze_smoke.py`, `scripts/README.md`, `docs/CHANGELOG.md`
- Added richer error-trace context without changing business semantics:
  - `router_error` / `router_provider_fallback` now include `node`, `elapsed_ms`, `exception_type`, `exception_repr`, and router/fallback model fields.
  - `agent_error` now includes `node`, `elapsed_ms`, `exception_type`, `exception_repr`, and model fields.
  - Added `summary_error` event in final summary LLM failure path with the same context schema.
  - Added `agent_model_error` / `agent_tool_error` events around `default_agents._call_with_tools(...)` invocation failures; exceptions are still re-raised unchanged.
- Improved trace reliability and aggregation for failure analysis:
  - `run_logger` now serializes same-process JSONL writes via a global lock to reduce interleaved malformed lines under concurrent async logging.
  - `analyze_trace` now reports `malformed_jsonl` counts/samples and provides `error_summary` grouped by node/agent/event/status/error signature.
- Scope boundary: observability-only enhancement for 502 debugging; no Router/Manager/Agent/Summary logic changes, no retry, no benchmark KPI formula change.

## 2026-03-11 - Speed-Profile minimal slice (node-level latency sidecar)
- Files: `src/react_agent/graph.py`, `tools/bench_doubao_seed2_speed.py`, `ops/regression/analyze_trace.py`, `tests/unit_tests/test_trace_analyze_smoke.py`, `docs/archive/benchmark/BENCHMARK_DOUBAO_SEED2_SPEED.md`, `docs/SYSTEM_MAP.md`, `scripts/README.md`, `docs/CHANGELOG.md`
- Added observability-only `node_latency` trace events in graph nodes without changing Router/Manager/Agent/Summary business semantics:
  - `router`, `manager_broadcast`, `agent`, `manager_summary`, `summary`, `finalize_summary`.
- Extended benchmark harness with optional profiling mode (`--enable-profiling`) that aligns E2E runs to trace artifacts via explicit `run_id` and `LOG_DIR`, while keeping benchmark main CSV/Markdown schema unchanged.
- Added profiling sidecar JSON output (default `<out-csv-stem>_profile.json`) that aggregates node-level latency from trace logs.
- Extended trace analyzer to summarize `latency_profile` (`by_node` + `agent_elapsed_ms`) while preserving existing context/stable-consume summaries.
- Added minimal unit smoke coverage for latency-profile aggregation (`test_trace_analyze_smoke`).
- Scope boundary: observability/profiling only; no route/contract/tool-calling/summary behavior change.

## 2026-03-11 - Qwen server benchmark run (raw + E2E, docs/evidence update)
- Files: `docs/archive/benchmark/BENCHMARK_DOUBAO_SEED2_SPEED.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `outputs/benchmarks/qwen30b_e2e_20260311.csv`, `outputs/benchmarks/qwen30b_e2e_20260311.md`
- Reused existing harness `tools/bench_doubao_seed2_speed.py` to benchmark OpenAI-compatible server model `Qwen3-30B-A3B-Instruct-2507-int8` on `http://10.7.46.122:8000/v1`.
- Confirmed Router override envs were unset (`ROUTER_MODEL`, `ROUTER_OPENAI_BASE_URL`, `ROUTER_OPENAI_API_KEY`) so full-system benchmark routing stayed on one global model path.
- Dry-run succeeded with payload probe evidence; real run completed `runs=3` after increasing E2E timeout to `--e2e-timeout 1200` for this server/model path.
- Recorded benchmark outputs and key metrics: `raw_latency_ms_p50=275.91`, `e2e_latency_ms_p50=538749.71`, and `e2e_search_tool_calls_total=0` (`DISABLE_SEARCH=1` noise control).
- Scope boundary: benchmark execution + docs/evidence update only; no mainline business logic change.

## 2026-03-10 - Env-1 Windows pytest execution encoding workaround
- Files: `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Updated Windows pytest recommended command to:
  - `conda run --no-capture-output -n cline_env python -m pytest ...`
- Clarified root cause as execution-layer conda output capture/re-print encoding behavior (`UnicodeEncodeError(gbk)`), not pytest logic and not project business logic.
- Kept direct interpreter invocation as verification-only fallback:
  - `D:\AnacondaEnvs\cline_env\python.exe -m pytest ...`
- Out of scope: business-code changes, test-logic changes, and conda internals patching.

## 2026-03-10 - Baseline-C manager contract dispatch test fixture alignment
- Files: `tests/unit_tests/test_manager_contract_dispatch.py`, `docs/A01_CONTRACT_SCHEMA_V0.md`, `docs/CHANGELOG.md`
- Fixed blocker in `test_manager_contract_dispatch` by aligning the "valid contract" fixture with current runtime validation (`validate_contract` requires `steps` length in `2..6`).
- Kept runtime behavior unchanged: no modifications to manager dispatch logic, no fallback-path changes, and no relaxation of `contract_utils.validate_contract(..., steps_min=2)`.
- Synced schema doc wording from `steps non-empty` to `steps 2..6 items` to match runtime contract semantics.
- Out of scope: Windows `conda run` encoding issue, any business-code changes, and unrelated test debt/refactor work.

## 2026-03-10 - Phase 2 stable snapshot (structure-stable)
- Type: `structure-stable` snapshot (not `quality-stable`).
- Completed structure stages: Phase 2A low-risk cleanup, Env-0 environment entrypoint unification, Phase 2B U5/U1/U2 high-coupling unit relocation, and Baseline-A/B baseline debt fixes.
- Deferred backlog: U4 (`tests/` structure + `conftest` + CI + Makefile linkage refactor) is intentionally postponed.
- Known blockers (not resolved in this snapshot):
  - `tests/unit_tests/test_manager_contract_dispatch.py` currently failing in local validation.
  - On Windows terminals, `conda run -n cline_env python -m pytest ...` may fail with `UnicodeEncodeError(gbk)` in conda output handling.
- Scope boundary for this snapshot: no additional directory migration, no U4 execution, no blocker fixes, and no business-code changes.
- Current focus shift: primary risk has moved from structure organization to test baseline and environment execution stability.

## 2026-03-10 - Baseline-B train CLI/help friendliness fix
- Files: `ops/train_eval/a01/train_a01_sft_qlora.py`, `docs/CHANGELOG.md`
- Refactored dependency loading in `train_a01_sft_qlora.py` from module-top imports to an explicit runtime check in `main()`, so `--help` can print without requiring training packages.
- Preserved training failure behavior when dependencies are missing: entering the training path still exits with `Missing training deps...` if `torch`/`transformers`/`peft`/`datasets` are unavailable.
- No training logic enhancement and no environment dependency installation included in this change.

## 2026-03-10 - Test baseline fix for U2 teacher wiring assertion
- Files: `tests/unit_tests/test_teacher_wiring_no_router_gen.py`, `docs/CHANGELOG.md`
- Replaced a stale variable-name hardcoded assertion with semantic wiring assertions: local `_call_teacher` tuple unpacking is validated without binding to a specific second variable name, and that unpacked second value is consumed by `compute_teacher_observability(...)`.
- Preserved the original risk boundary assertion that `router_gen._call_teacher` is not referenced.
- No U2 business logic rollback: `ops/train_eval/a01/generate_a01_teacher_contracts.py` was not modified.
- Out of scope: training dependency remediation (`torch` etc.) and train-script CLI/help friendliness.

## 2026-03-10 - Phase 2B U2 a01 teacher/train/eval chain relocation
- Files: `ops/train_eval/a01/generate_a01_teacher_contracts.py`, `ops/train_eval/a01/train_a01_sft_qlora.py`, `ops/train_eval/a01/eval_a01_sft.py`, `ops/train_eval/a01/gate_a01_sft.py`, `ops/train_eval/a01/server_preflight.py`, `ops/train_eval/a01/__init__.py`, `tests/unit_tests/test_a01_quality_distribution_stats.py`, `tests/unit_tests/test_a01_quality_metrics.py`, `tests/unit_tests/test_a01_teacher_observability.py`, `tests/unit_tests/test_teacher_endpoint_resolution.py`, `tests/unit_tests/test_teacher_wiring_no_router_gen.py`, `docs/SYSTEM_MAP.md`, `docs/A01_SFT_DATA_V0.md`, `data/a01_sft/DATA_MANIFEST.md`, `docs/INDEX.md`, `docs/CHANGELOG.md`
- Moved the U2 a01 tooling chain from `tools/` to `ops/train_eval/a01/` as the next Phase 2B high-coupling migration slice.
- Updated `generate_a01_teacher_contracts.py` repo-root resolution from fixed parent indexing to upward `pyproject.toml` discovery and anchored `config/agents` lookup to repo root.
- Kept runtime contracts unchanged: `server_preflight.py` FINAL triple verification semantics are unchanged; `gate_a01_sft.py` still defaults to `eval_report` sibling `run_manifest.json`.
- Updated only U2-direct tests/imports and script path constant references to the new location.
- Updated U2 command/script references in SYSTEM_MAP, A01_SFT_DATA_V0, and DATA_MANIFEST (command template path only; FINAL freeze semantics unchanged).
- Explicitly out of scope: `tools/` non-U2 scripts, U1/U4 migration units, CI, Makefile, runtime mainline directories, `data/a01_sft/final/*` content changes, and training dependency remediation.
- Known baseline issues (pre-existing, not introduced by this relocation): `tests/unit_tests/test_teacher_wiring_no_router_gen.py` still fails on assertion text expectation; `train_a01_sft_qlora.py --help` may fail in `cline_env` when `torch` is missing.
Phase positioning: This is a Phase 2B U2 path-and-contract migration only. It validates move + minimal linkage updates without changing a01 schema rules, FINAL evidence chain semantics, or training/eval business logic. The next step should continue with the same unit-scoped approach for remaining high-coupling units.

## 2026-03-10 - Phase 2B U1 router regression chain relocation
- Files: `ops/regression/router/run_regression_eval.py`, `ops/regression/router/generate_router_preds.py`, `ops/regression/router/generate_router_preds_hf.py`, `ops/regression/router/eval_router_outputs.py`, `ops/regression/router/__init__.py`, `tests/unit_tests/test_eval_router_outputs.py`, `docs/SYSTEM_MAP.md`, `docs/RUNBOOK_ROUTER_SFT.md`, `tools/README.md`, `docs/INDEX.md`, `docs/CHANGELOG.md`
- Moved the U1 router regression chain from `tools/` to `ops/regression/router/` as the second Phase 2B high-coupling migration slice.
- Updated `run_regression_eval.py` to resolve sibling scripts via `SCRIPT_DIR`, removing hardcoded `tools/...` subprocess paths.
- Updated repo-root/path resolution in `generate_router_preds.py` and `eval_router_outputs.py` to search upward for `pyproject.toml`, so `src/` imports and `data/catalogs/*` anchors remain valid after relocation.
- Updated U1-linked unit test import to `from ops.regression.router import eval_router_outputs`.
- Updated U1 path references in `docs/SYSTEM_MAP.md`, `docs/RUNBOOK_ROUTER_SFT.md`, and kept `tools/README.md` as a transition navigation page pointing to the new location.
- Explicitly out of scope: `tools/` non-U1 scripts, U2/U4 migration units, `data/a01_sft/final/*`, `data/a01_sft/DATA_MANIFEST.md`, CI, Makefile, and runtime mainline directories.
Phase positioning: This is a Phase 2B targeted migration of one high-coupling unit with minimal linkage changes (script pathing, one unit test import, and command docs). It is not a full `tools/` migration and does not change business runtime graph behavior. Next steps should continue by unit boundary (U2/U4) with the same move + path + test + docs pattern.

## 2026-03-10 - Phase 2B MVP U5 analyze_trace relocation
- Files: `ops/regression/analyze_trace.py`, `tests/unit_tests/test_trace_analyze_smoke.py`, `scripts/README.md`, `docs/INDEX.md`, `docs/CHANGELOG.md`
- Moved U5 trace analyzer script from `scripts/analyze_trace.py` to `ops/regression/analyze_trace.py` as the first high-coupling migration MVP slice.
- Updated the U5 smoke unit test loader path to the new script location; test behavior remains unchanged.
- Updated `scripts/README.md` analyze section commands/path and rollback note to the new script location.
- Added docs navigation note for `ops/regression/` under non-mainline archive locations.
- Explicitly out of scope in this MVP: `tools/`, U1/U2/U4 migration units, `data/a01_sft/final/*`, `data/a01_sft/DATA_MANIFEST.md`, CI, and Makefile.
Phase positioning: This is a Phase 2B MVP pilot to validate migration mechanics (file move + test linkage + doc sync) on a single non-splittable unit (U5). It does not represent completion of high-coupling migration and does not alter runtime mainline closure. The next natural step is to apply the same pattern to the next approved high-coupling unit.

## 2026-03-10 - Environment baseline unification (conda `cline_env`)
- Files: `README.md`, `docs/SYSTEM_MAP.md`, `docs/RUNBOOK_ROUTER_SFT.md`, `docs/INDEX.md`, `docs/CHANGELOG.md`
- Unified local/Codex validation entrypoints to `conda run -n cline_env python ...` for README quickstart, SYSTEM_MAP local demo/import/pytest, and RUNBOOK command examples (including here-doc invocation).
- Added explicit baseline statement: Python `>=3.11,<4.0`, official conda env `cline_env`, and warning that bare `python` may resolve to system Python 3.7 and cause false failures.
- Added minimal placeholder smoke guidance for local import checks with `TAVILY_API_KEY=test-key` (no real key in repo).
- Kept training/runtime semantics unchanged; this is a docs/command-entry normalization pass only.
Phase positioning: This is an environment-entrypoint normalization slice after Phase 1 storage cleanup. It reduces false negatives from interpreter drift without touching runtime graph logic, schemas, or data contracts. The next natural step is optional high-coupling command-path cleanup across CI/Makefile/tests when explicitly scheduled.

## 2026-03-10 - Phase 1 low-risk storage cleanup (non-mainline archive)
- Files: `README.md`, `docs/INDEX.md`, `docs/SYSTEM_MAP.md`, `docs/A01_SFT_DATA_V0.md`, `docs/CHANGELOG.md`, `ops/data_pipeline/*`, `docs/archive/*`, `assets/reference/*`
- Moved non-mainline research notes from repo root to `docs/archive/research_notes/`: `project_analysis.md`, `agent_full.md`, `agent_profile.md`.
- Moved historical handoff/benchmark docs to archive folders: `docs/archive/handoff/HANDOFF_A01_SFT_FINAL.md`, `docs/archive/benchmark/BENCHMARK_DOUBAO_SEED2_SPEED.md`.
- Moved reference assets to `assets/reference/`: `智能体分配.xlsx`, `langchain_community-0.2.14-py3-none-any.whl`, and additional historical reference artifacts.
- Moved root offline data-build scripts to `ops/data_pipeline/`: `export_agent_catalog.py`, `extract_real_questions.py`, `synthesize_questions.py`, `merge_questions_pool.py`, `generate_router_plans.py`, `export_router_sft_dataset.py`.
- Updated `ops/data_pipeline/export_router_sft_dataset.py` default `--system-template-from` to resolve sibling `generate_router_plans.py` after relocation.
- Mainline runtime closure remains unchanged (`src/react_agent/`, `config/agents/`, `langgraph.json`, `pyproject.toml`, `react_agent/`, `sitecustomize.py`); no runtime topology/schema changes.
Phase positioning: This is a Phase 1 storage cleanup to reduce root-level noise while preserving runtime behavior and entrypoints. It intentionally avoids high-coupling directories (`tools/`, `scripts/`, `tests/`, `data/`, `outputs/`, `tmp/`, `log/`) and avoids any business-logic refactor. The next natural step is a dedicated high-coupling migration phase with coordinated updates across tooling/docs/tests/CI.

## 2026-02-27 - Phase 3.1 FINAL_LAYER must finalize (empty plan fallback)
- Files: `src/react_agent/graph.py`, `tests/unit_tests/test_final_layer_finalize_phase31.py`, `docs/CHANGELOG.md`
- Added shared final-summary helper `_run_final_summary(...)` and new graph node `finalize_summary` to force final answer generation when `current_layer==FINAL_LAYER` and pending agents are empty.
- Updated `route_from_manager_summary` so FINAL_LAYER with no pending no longer returns direct `__end__`; it now routes to `finalize_summary`, which sets `is_last_step=True` and preserves existing stable/thread-summary write behavior.
- Added `route_after_finalize` conditional routing to keep existing end semantics: `memory_update` when thread summary is enabled, otherwise `__end__`.
- Added unit coverage for the new invariant (`route_from_manager_summary -> finalize_summary`, `finalize_summary` output includes `is_last_step=True` and message, and `route_after_finalize` behavior).
- Rollback: revert this commit to restore prior direct-`__end__` behavior on FINAL_LAYER empty-plan states.
Phase positioning: This Phase 3.1 fix hardens end-of-turn semantics so FINAL_LAYER always produces a closing summary path instead of silently ending with `is_last_step=False`. It does not alter RouterPlan schema, parser behavior, or agent dispatch contracts. The change is scoped to finalization routing and summary-node wiring. Next step is to rerun Phase 2.5 acceptance runs and verify `manager_ctx` / `stable_findings_update` / `thread_summary_update` appear consistently under long-turn persistence.

## 2026-02-26 - Phase 2.5 optional stable_findings consumption (Router + Manager Summary only)
- Files: `src/react_agent/graph.py`, `tests/unit_tests/test_stable_consume_phase25.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added env-gated stable-findings consumption via `REACT_AGENT_STABLE_CONSUME` (default off), with bounded summary controls `REACT_AGENT_STABLE_SUMMARY_MAX_CHARS` and `REACT_AGENT_STABLE_SUMMARY_MAX_ITEMS`.
- Implemented deterministic/extractive `stable_summary` builder from `state["stable_findings"]` with non-list/empty tolerance and per-field truncation.
- Injected `stable_summary` only into Router and Manager Summary system-context assembly before `thread_summary`, preserving the configured order with messages windowing.
- Added lightweight `stable_consume` trace event (`node/enabled/stable_len/stable_summary_len`) for LOCAL_TRACE observability; default off keeps zero extra logging output.
- Kept boundaries unchanged: no Agent/shared_context stable injection, no manager assignment text changes, no RouterPlan/parser changes.
- Rollback: unset `REACT_AGENT_STABLE_CONSUME` (or set `0`) and restart long-lived processes.
Phase positioning: This phase activates controlled use of retained stable findings after pools (2.4-B) and context controls (2.2/2.3). It improves cross-turn continuity for Router/Manager decisions without widening agent context. The implementation remains opt-in to preserve default runtime cost and behavior. Next, Phase 2.5 follow-up should audit stable summary quality/ordering effects and define stricter observability gates.

## 2026-02-26 - Phase 2.4-B.1 robustness hardening (stable_findings type coercion)
- Files: `src/react_agent/graph.py`, `tests/unit_tests/test_results_pools_phase24b.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Hardened `manager_summary` final-path stable write logic: when `REACT_AGENT_RESULTS_POOLS=1` and `state["stable_findings"]` is not a list, runtime now coerces to `[]` instead of raising.
- Added LOCAL_TRACE-only observability event `stable_findings_coerce` with `prev_type` and `stable_len_after`, plus existing `stable_findings_update` remains unchanged.
- Added unit coverage for non-list `stable_findings` state shape to verify append still succeeds and outputs a list entry.
- Updated SYSTEM_MAP wording to clarify source-of-truth semantics under pools mode: runtime reads `ephemeral_results`; `analyst_results` is compatibility mirror only.
- Rollback: keep `REACT_AGENT_RESULTS_POOLS=0` (default) or revert this commit; no schema/runtime contract changes introduced.
Phase positioning: This is a narrow Phase 2.4-B.1 robustness pass, not a new feature slice. It reduces failure risk from polluted historical state while preserving all 2.4-B gates and semantics. No Router/Agent contract behavior changes were introduced. The next natural step is Phase 2.5 audit focusing on long-run state hygiene and observability completeness.

## 2026-02-26 - Phase 2.4-B optional stable/ephemeral results pools + evidence index
- Files: `src/react_agent/state.py`, `src/react_agent/graph.py`, `tests/unit_tests/test_results_pools_phase24b.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added env-gated results pools via `REACT_AGENT_RESULTS_POOLS` (default off): `ephemeral_results` for per-turn runtime aggregation (with reset) and `stable_findings` for cross-turn retained final findings.
- Kept backward compatibility by retaining `analyst_results` as a mirror field while switching runtime readers (`manager_broadcast`, `manager_summary`, `route_from_manager_summary`, AgentInput `shared_context`) to a pool-selection helper.
- Router reset now conditionally clears both `analyst_results` and `ephemeral_results` when pools are enabled; disabled mode preserves the original reset/update path and cost profile.
- `manager_summary` final branch now appends bounded stable findings (`kind/question/final_answer/evidence/run_id`) with evidence extracted from filtered agent outputs (`evidence`/`key_points`) under configurable caps.
- Added unit tests for env gating, router reset behavior, runtime pool selection, agent write mirroring, and stable-finding append behavior without external model/network dependency.
- Rollback: unset `REACT_AGENT_RESULTS_POOLS` (or set `0`) and restart long-lived processes; runtime immediately returns to legacy `analyst_results` semantics.
Phase positioning: This is Phase 2.4-B state-layer hardening after Phase 2.1 persistence, Phase 2.2 thread summary, and Phase 2.3 message windowing. It separates per-turn execution artifacts from cross-turn retained findings while preserving existing call sites through a compatibility mirror. The implementation keeps default behavior unchanged unless explicitly opted in. Next, the natural continuation is introducing stable-finding read policy (who can consume it and when) and adding regression metrics for pool-size drift and evidence quality.

## 2026-02-26 - Phase 2.3 optional messages window/trim (Router + Manager Summary input only)
- Files: `src/react_agent/graph.py`, `demo_layered_run.py`, `tests/unit_tests/test_messages_window_phase23.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added env-gated messages windowing for Router and Manager Summary LLM inputs only via `REACT_AGENT_MESSAGES_WINDOW` and `REACT_AGENT_MESSAGES_WINDOW_SIZE` (default off).
- Kept all full-message readers unchanged (`_get_latest_user_question`, `thread_summary` construction, manager dispatch, Agent subtask extraction), so the feature only trims the LLM context payloads for Router/Manager Summary.
- Preserved Phase 2.2 ordering when enabled: `system_prompt + (optional thread_summary msg) + window_messages` (and `+ user_msg` for Manager Summary).
- Added optional trace observability (`router_ctx` / `manager_ctx`) with numeric fields `ctx_messages_len`, `full_messages_len`, and `window_size` for LOCAL_TRACE-based validation.
- `demo_layered_run.py` now prints messages-window envs and hints to inspect `router_ctx/manager_ctx` when `LOCAL_TRACE=1`.
- Rollback: unset `REACT_AGENT_MESSAGES_WINDOW` (or set `0`) and restart long-lived processes; inputs revert to full `state["messages"]`.
Phase positioning: This is Phase 2.3 context-budget hardening on top of Phase 2.1 persistence and Phase 2.2 thread_summary. It limits only Router and Manager Summary LLM inputs while preserving reducer semantics and agent dispatch behavior. The goal is to control long-thread token growth and prompt drift without changing routing/agent logic. Next, validate window sizes on long conversations and decide whether to introduce role-aware trimming or message window defaults.

## 2026-02-26 - Phase 2.2 optional thread_summary (extractive thread archive, Router + Manager Summary injection)
- Files: `src/react_agent/state.py`, `src/react_agent/graph.py`, `demo_layered_run.py`, `tests/unit_tests/test_thread_summary_phase22.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added optional `State.thread_summary` and a new `memory_update` node that runs only on the final-turn path (`is_last_step=True`) to build an extractive thread summary from explicit text (no extra LLM call).
- Added env-gated injection of `thread_summary` into Router and Manager Summary LLM inputs only (`REACT_AGENT_THREAD_SUMMARY`, `REACT_AGENT_THREAD_SUMMARY_MAX_CHARS`); AgentInput and manager assignment text remain unchanged.
- Default behavior/cost stays unchanged when the feature is disabled (default off): no extra node work on normal end path beyond existing routing, no extra prompt messages, no extra model calls.
- `demo_layered_run.py` now prints `thread_summary_len` and a short snippet so same-thread persistence + summary behavior can be observed with `REACT_AGENT_CHECKPOINTER=memory` and `REACT_AGENT_THREAD_SUMMARY=1`.
- Rollback: unset `REACT_AGENT_THREAD_SUMMARY` (or set `0`) and restart long-lived processes; optionally disable `REACT_AGENT_CHECKPOINTER` to return to single-invoke state behavior.
Phase positioning: This is Phase 2.2 on top of Phase 2.1 thread persistence, adding a bounded, opt-in thread archive without changing RouterPlan parsing or agent dispatch semantics. The summary is deterministic/extractive to avoid extra cost and hallucination risk. Router and Manager Summary can now see prior-turn context in persisted threads, while agents remain isolated from the archive. Next, Phase 2.3 can add messages windowing/trim rules to control context growth using `thread_summary` as the stable carry-over channel.

## 2026-02-26 - Phase 2.1 optional Python thread persistence (checkpointer + thread_id)
- Files: `src/react_agent/graph.py`, `demo_layered_run.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added an optional business-graph checkpointer switch via `REACT_AGENT_CHECKPOINTER` (default `none`), with `memory` mode enabled in-process and optional `sqlite` mode that degrades to no-op if dependencies are unavailable.
- `graph.py` now keeps the default `graph` (Studio/CLI entry) non-persistent and exposes an optional persistent graph variant compiled with `checkpointer=` only when the env switch is enabled.
- `demo_layered_run.py` now includes a minimal two-round same-thread demo (`thread_id`) and a no-thread control group, printing `messages_len` and final answer snippets for verification.
- SYSTEM_MAP documents how to enable thread persistence for Python/self-hosted API calls and how to roll back (`REACT_AGENT_CHECKPOINTER=none` or unset, then restart).
Phase positioning: This is Phase 2.1 infrastructure wiring for optional short-term state persistence in the business graph layer. It deliberately avoids changing Router/Manager/Agent semantics, RouterPlan parser behavior, or Studio defaults. The goal is to make Python/self-hosted calls capable of thread reuse with an explicit opt-in. Next, validate same-thread memory behavior with a real model and decide whether to add summary/window controls on top of persisted messages.

## 2026-02-22 - Runtime search toggle fix (DISABLE_SEARCH read per-call)
- Files: `src/react_agent/graph.py`, `tests/unit_tests/test_search_toggle_runtime.py`, `docs/CHANGELOG.md`
- Fixed `DISABLE_SEARCH` caching behavior by reading the env at agent dispatch time instead of module import time, so long-lived processes can reflect env changes.
- Added unit tests to verify (1) `DISABLE_SEARCH` toggles `allow_search` from `True` to `False` at runtime and (2) `tool_calls` can trigger Tavily tool invocation in the agent tool loop.
Phase positioning: This is a runtime wiring correctness fix for search enable/disable behavior and tool-call activation evidence. It does not change graph topology or schemas. Next, validate in the actual Studio/API process by toggling `DISABLE_SEARCH` and confirming tool calls/logs in a live run.

## 2026-02-22 - Doubao Seed2.0 speed benchmark harness (benchmarking / inference observability)
- Files: `tools/bench_doubao_seed2_speed.py`, `src/react_agent/graph.py`, `docs/archive/benchmark/BENCHMARK_DOUBAO_SEED2_SPEED.md`, `docs/CHANGELOG.md`
- Added a Doubao Seed2.0 benchmark harness that measures both raw OpenAI-compatible chat speed and end-to-end LangGraph latency, and writes CSV + Markdown tables.
- Raw benchmark uses `stream=true` + `stream_options.include_usage=true` and sends `thinking={"type":"disabled"}` explicitly in the request body.
- E2E benchmark runs the existing graph once per sample and forces `DISABLE_SEARCH=1` to reduce search-tool noise; the default runtime behavior remains unchanged when the env is unset.
- Added benchmark documentation with env requirements, reproducible commands, output paths, and evidence probes (`raw_payload_probe`, `e2e_thinking_probe`, search-call counter).
Phase positioning: This is a benchmarking harness milestone for provider/model speed comparison and observability. It does not change RouterPlan/a01 schemas or the LangGraph topology. Next, run the harness against the three Ark Doubao Seed2.0 variants and archive the generated benchmark tables as evidence.

## 2026-02-04 - Multi-turn state reset for Studio threads (runtime bugfix)
- Files: `src/react_agent/graph.py`, `docs/CHANGELOG.md`
- Reset `is_last_step` in router_node to avoid short-circuiting the next question in the same thread.
- Acceptance: ask two different questions in the same Studio thread; Router should re-run and not end early.
Phase positioning: This is a minimal runtime fix for multi-turn thread safety. It preserves message accumulation and existing schema while preventing stale end-state from short-circuiting new turns. Next, validate with a two-turn Studio repro.

## 2026-02-04 - Router endpoint override + fallback (system integration / inference config)
- Files: `src/react_agent/context.py`, `src/react_agent/graph.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added Router-only OpenAI endpoint env (`ROUTER_OPENAI_BASE_URL` / `ROUTER_OPENAI_API_KEY`) with automatic fallback to global provider on failure.
- Kept `ROUTER_MODEL` override (defaults to `MODEL` when unset) for Router-only model routing.
- SYSTEM_MAP documents Router endpoint/model overrides and example env.
- Acceptance: set `ROUTER_OPENAI_BASE_URL=http://127.0.0.1:18000/v1` + `ROUTER_MODEL=openai/router`; Router should use vLLM when reachable and fall back to global provider when not.
Phase positioning: This is a config-only integration step for Phase 4.1 inference wiring. It keeps schemas and runtime logic unchanged, only adds an optional Router-specific endpoint with safe fallback. Next, validate on a live run that Router requests go to the intended provider.

## 2026-02-04 - S0 docs alignment (Cerebras config + eval default note)
- Files: `docs/SYSTEM_MAP.md`, `docs/A01_SFT_DATA_V0.md`, `docs/CHANGELOG.md`
- Added Cerebras OpenAI-compatible config guidance (OPENAI_BASE_URL / CEREBRAS_API_KEY / MODEL) to SYSTEM_MAP.
- Documented `eval_report.meta.max_new_tokens` default 4096 in A01_SFT_DATA_V0 (align with Phase 4.1 runbook).
- Acceptance: `rg -n "Cerebras|api.cerebras.ai" docs/SYSTEM_MAP.md` and `rg -n "max_new_tokens" docs/A01_SFT_DATA_V0.md`
Phase positioning: Docs-only alignment for S0 entrypoints, keeping runtime logic unchanged. This makes provider configuration and eval defaults self-consistent across S0 docs. Next, keep doc updates tied to script defaults.

## 2026-01-28 - Phase 4.1 eval truncation hardening (Phase 4.1.6)
- Files: `tools/eval_a01_sft.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `docs/DECISION_LOG.md`
- Raised eval default `--max-new-tokens` to 4096 and recorded `max_new_tokens` in eval_report meta.
- Deferred heavy imports in eval so `--help` works without torch.
- SYSTEM_MAP runbook notes the 4096 default and the 2048 smoke tradeoff.
- Acceptance: `python tools/eval_a01_sft.py --help | rg "max-new-tokens"`
Phase positioning: Phase 4.1.6 improves eval/gate robustness without changing training logic or schema. It targets JSON truncation false failures by setting a safer default and recording the evidence field. Next, keep 4096 for gate runs and only lower for smoke when explicitly accepted.

## 2026-01-28 - Phase 4.1 branch self-consistency (Phase 4.1.4)
- Files: `tools/server_preflight.py`, `tools/eval_a01_sft.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `docs/DECISION_LOG.md`
- Ensured data/router-sft-v1 contains Phase 4.1 scripts and evidence fields referenced by SYSTEM_MAP.
- Acceptance: `rg -n "Phase 4.1" docs/SYSTEM_MAP.md` and `python tools/server_preflight.py --help`
Phase positioning: This Phase 4.1.4 update aligns branch contents with the documented runbook. It does not change schema or training logic, only ensures missing scripts and evidence fields are present on the branch. Next, push the branch and re-run server preflight on AutoDL.

## 2026-01-28 - Phase 4.1 AutoDL 4090 runbook (Phase 4.1.5)
- Files: `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `docs/DECISION_LOG.md`
- Added AutoDL 4090 (24GB) smoke runbook with preflight/train/eval/gate commands and evidence file checklist.
- Acceptance: copy the runbook block in SYSTEM_MAP and verify `preflight.txt`, `run_manifest.json`, `eval_report.json` exist under `runs/a01_sft/<run_id>_smoke/`.
Phase positioning: This Phase 4.1.5 update strengthens operational reproducibility for server runs. It does not alter training logic or schemas, only adds a concrete, auditable runbook. Next, execute smoke runs and archive evidence files alongside manifests.

## 2026-01-28 - a01 SFT Phase 4.1 minimal train/eval/gate (Phase 4.1)
- Files: `tools/train_a01_sft_qlora.py`, `tools/eval_a01_sft.py`, `tools/gate_a01_sft.py`, `docs/SYSTEM_MAP.md`, `docs/DECISION_LOG.md`, `docs/CHANGELOG.md`
- Added a01 SFT completion-only QLoRA training entry (smoke capable) that reads FINAL train/val and writes run_manifest.json.
- Added eval script to compute valid_json_rate / contract_ok_rate / schema_keys_match_rate and emit eval_report.json.
- Added gate script to assert eval thresholds and require run_manifest evidence.
- Acceptance: `python tools/train_a01_sft_qlora.py --base-model-path <model> --train-jsonl data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl --val-jsonl data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl --output-dir runs/a01_sft/<run_id> --max-steps 10` then `python tools/eval_a01_sft.py --model-path runs/a01_sft/<run_id> --val-jsonl data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl --out-dir runs/a01_sft/<run_id>` and `python tools/gate_a01_sft.py --eval-report runs/a01_sft/<run_id>/eval_report.json`.
Phase positioning: This is Phase 4.1 to establish a minimal a01 SFT training loop (train → eval → gate) without changing schema or runtime logic. It keeps FINAL data read-only and stores evidence in run manifests. The goal is to make smoke training repeatable on servers and to provide measurable gates for JSON validity and contract compliance. Next, scale training steps and set thresholds based on eval distribution while keeping FINAL frozen.

## 2026-01-28 - Phase 4.1 server preflight evidence (Phase 4.1.1)
- Files: `tools/server_preflight.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added server preflight script to capture git commit/dirty status, FINAL sha256+line counts, python/pip/torch/cuda versions, and nvidia-smi summary into `runs/.../preflight.txt`.
- SYSTEM_MAP now references preflight command and run_manifest evidence fields.
- Acceptance: `python tools/server_preflight.py --out-dir runs/a01_sft/<run_id>`
Phase positioning: This is a Phase 4.1.1 evidence add-on that does not change training logic. It only adds reproducibility metadata for server runs, making SSH+tmux workflows auditable. Next, run preflight before each smoke train and archive `preflight.txt` with run_manifest and eval_report.

## 2026-01-28 - Phase 4.1 eval evidence hardening (Phase 4.1.2)
- Files: `tools/eval_a01_sft.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `docs/DECISION_LOG.md`
- eval_report now includes model weight hashes (if present) and model directory size for reproducibility.
- SYSTEM_MAP documents the new eval_report evidence fields.
- Acceptance: `python tools/eval_a01_sft.py --model-path runs/a01_sft/<run_id> --val-jsonl data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl --out-dir runs/a01_sft/<run_id>`
Phase positioning: This Phase 4.1.2 update strengthens eval evidence without changing training or schema. It makes model artifacts auditable by attaching hashes and size to eval reports. Next, use these fields in server runbooks and archive them alongside run_manifest and preflight logs.

## 2026-01-28 - Phase 4.1 preflight hardening (Phase 4.1.3)
- Files: `tools/server_preflight.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `docs/DECISION_LOG.md`
- preflight now captures `df -h` summary; SYSTEM_MAP notes AutoDL cache paths and runs/ symlink guidance.
- Acceptance: `python tools/server_preflight.py --out-dir runs/a01_sft/<run_id>`
Phase positioning: This Phase 4.1.3 update hardens server evidence capture without changing training logic. It ensures storage context is recorded alongside git/data/model evidence. Next, run preflight before each smoke train and keep preflight.txt with run_manifest and eval_report.

## 2026-01-28 - data evidence chain + trace flag clarification (Phase 3.3.1)
- Files: `docs/INDEX.md`, `data/a01_sft/DATA_MANIFEST.md`, `docs/archive/research_notes/project_analysis.md`, `docs/SYSTEM_MAP.md`, `docs/DECISION_LOG.md`, `docs/CHANGELOG.md`
- Added DATA_MANIFEST to S0 authority list and conflict rules for FINAL data paths.
- Documented a01 SFT archive/immutability policy + sha256 integrity checks.
- Clarified runtime fallback: L3 is not truncated in normal parse; default_plan fallback caps L3 at 3.
- Explained LOCAL_TRACE/LOG_DIR/TRACE_MAX_CHARS behavior in SYSTEM_MAP; added D4 decision entry.
- Acceptance: `pytest -q tests/unit_tests/`
Phase positioning: This is Phase 3.3.1 documentation hardening to make the data evidence chain and trace logging behavior explicit. It does not change any RouterPlan or a01 contract schema and does not alter runtime behavior. The only updates are to authority mapping, archive policy, and clarification of fallback behavior. Next, proceed to Phase 4.1 training using FINAL data, keeping future outputs under `_archive` with checksums.

## 2026-01-27 - a01 SFT FINAL freeze + archive (Phase 3.3)
- Files: `data/a01_sft/DATA_MANIFEST.md`, `data/a01_sft/final/*`, `data/a01_sft/_archive/2026-01-26/*`, `data/a01_sft/_archive/2026-01-27/*`, `docs/CHANGELOG.md`
- Frozen FINAL dataset to `data/a01_sft/final` and archived all prior probe/smallrun/obs outputs under dated folders.
- Added DATA_MANIFEST with origin mapping, stats summary, inputs, and self-check snippet.
- Added handoff doc and decision log references for continuation in a new session.
- Acceptance: verify `data/a01_sft/final/*` exists, read `docs/archive/handoff/HANDOFF_A01_SFT_FINAL.md`, and run the self-check snippet from DATA_MANIFEST.
Phase positioning: This is Phase 3.3 to freeze a single source of truth for a01 SFT outputs and reduce data sprawl. It does not change any training logic or schema; only organizes artifacts and documentation. Next, use the FINAL dataset for training/eval gates and keep future runs under `_archive` with date stamps.

## 2026-01-26 - a01 teacher observability + parallel workers (Phase 3.2.5)
- Files: `tools/generate_a01_teacher_contracts.py`, `tests/unit_tests/test_a01_teacher_observability.py`, `docs/A01_SFT_DATA_V0.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added per-record teacher observability fields (elapsed_ms, assistant/raw chars, optional usage tokens) and distribution stats in stats.json.
- Added optional parallel workers and rate limiting flags for higher throughput (default workers=1).
- Acceptance: `pytest -q tests/unit_tests/test_a01_teacher_observability.py`
Phase positioning: This is Phase 3.2.5 to make large-sample profiling feasible without changing contract rules or record structure. Observability fields quantify latency/length/usage for quality bar calibration. Parallel workers are optional and default to off, preserving current behavior. Next, run N=500/1000 with workers and use percentiles to set training quality thresholds or decide whether to gate.

## 2026-01-26 - a01 teacher quality distribution stats (Phase 3.2.4)
- Files: `tools/generate_a01_teacher_contracts.py`, `tests/unit_tests/test_a01_quality_distribution_stats.py`, `docs/A01_SFT_DATA_V0.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added record-level distribution stats in stats.json (p50/p90/p95 for generic/very-generic ratios and steps-per-task) plus duplicate_steps_contract_rate.
- Kept record structure unchanged and reused existing per-record quality metrics.
- Acceptance: `pytest -q tests/unit_tests/test_a01_quality_distribution_stats.py`
Phase positioning: This is Phase 3.2.4 (quality bar evidence) to quantify per-record distribution without changing contract rules or adding gates. These percentiles provide the evidence needed to set training quality thresholds. It preserves the existing generation pipeline and only enriches stats.json. Next, use these percentiles to decide whether a hard quality bar or filter should be introduced in a later phase.

## 2026-01-26 - a01 teacher quality observability (Phase 3.2.3)
- Files: `tools/generate_a01_teacher_contracts.py`, `tests/unit_tests/test_a01_quality_metrics.py`, `docs/A01_SFT_DATA_V0.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added quality observability stats for a01 teacher outputs (generic/very-generic ratios, duplicate-steps contracts, avg steps per task).
- Each record now includes `meta.quality` with per-record ratios and step-length stats (structure unchanged).
- Acceptance: `pytest -q tests/unit_tests/test_a01_quality_metrics.py`
Phase positioning: This is Phase 3.2.3 to quantify teacher output quality without changing contract rules or the generation pipeline. The metrics make it possible to judge whether prompt/filters should be tightened before scaling. It is read-only with respect to schema and validation, focusing on observability. Next, use the stats to decide if prompt constraints or filtering should be adjusted in a follow-up phase.

## 2026-01-26 - a01 teacher call wiring fix (Phase 3.2.2 hotfix)
- Files: `tools/generate_a01_teacher_contracts.py`, `tests/unit_tests/test_teacher_wiring_no_router_gen.py`, `docs/CHANGELOG.md`
- Teacher generator now calls the local `_call_teacher` directly (no `router_gen` indirection).
- Added a pure-local unit test to lock the wiring invariant (no network).
- Acceptance: `pytest -q tests/unit_tests/test_teacher_wiring_no_router_gen.py`
Phase positioning: This is a Phase 3.2.2 hotfix focused on teacher-call correctness. It does not change contract rules or graph topology; it only ensures the generator actually invokes its internal HTTP call. Next, re-run a max-items=1 probe to confirm errors are HTTP/timeout rather than NameError.

## 2026-01-26 - a01 contract rule lock (Phase 3.2.1)
- Files: `src/react_agent/contract_utils.py`, `tools/generate_a01_teacher_contracts.py`, `docs/A01_SFT_DATA_V0.md`, `docs/SYSTEM_MAP.md`, `tests/unit_tests/test_contract_utils.py`, `docs/CHANGELOG.md`
- Locked contract validation defaults to steps length [2,6] and enforced `selected_agents` to include `a01_cio_orchestrator`.
- A01_SFT_DATA_V0 and SYSTEM_MAP now define the single source of truth for steps and selected_agents coverage.
- Added unit test for contract steps boundary and a01 coverage.
- Acceptance: `pytest -q tests/unit_tests/test_contract_utils.py`
Phase positioning: This is Phase 3.2.1 hardening to keep validation and data generation aligned. It does not change graph topology or routing flow, only locks contract schema defaults and documentation consistency. Acceptance is the focused unit test plus doc checks. Next, run a small teacher batch to ensure drop reasons align with the locked rules, then proceed to a01-SFT training.

## 2026-01-26 - a01 teacher small-run stats (Phase 3.2.2)
- Files: `tools/generate_a01_teacher_contracts.py`, `docs/A01_SFT_DATA_V0.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Generator now writes stats JSON with coverage/overreach rates for small-run acceptance.
- Stats output (example): `data/a01_sft/a01_sft_teacher_stats_20260126_smallrun.json`
- Acceptance: `python tools/generate_a01_teacher_contracts.py --router-sft data/router_sft/router_sft_20260108_20260106_b434e7a9a883.jsonl --questions data/questions/questions_pool_20260108_20260108_b434e7a9a883_v1.jsonl --out-train data/a01_sft/a01_sft_messages_20260126_smallrun.train.jsonl --out-val data/a01_sft/a01_sft_messages_20260126_smallrun.val.jsonl --out-stats data/a01_sft/a01_sft_teacher_stats_20260126_smallrun.json --max-items 50`
Phase positioning: This change bridges Phase 3.2.1 to 3.2.2 by making teacher small-run outputs reproducible and auditable. It introduces stats JSON output without changing contract logic. Acceptance is the N=50 run with stats persisted. Next, review the stats for prompt/profile pack adjustments before scaling.

## 2026-01-26 - a01 teacher endpoint resolution (Phase 3.2.2)
- Files: `tools/generate_a01_teacher_contracts.py`, `tests/unit_tests/test_teacher_endpoint_resolution.py`, `docs/A01_SFT_DATA_V0.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Teacher endpoint now always resolves to `/chat/completions`, and the default DeepSeek base_url is `https://api.deepseek.com`.
- Added unit test for URL resolution invariants (root, /v1, trailing slash, no scheme).
- Acceptance: `pytest -q tests/unit_tests/test_teacher_endpoint_resolution.py`
Phase positioning: This is Phase 3.2.2 endpoint hardening to eliminate 404s from malformed DeepSeek paths. It keeps the http.client transport and validation rules unchanged. Acceptance is the URL resolution unit test and doc alignment. Next, re-run a small teacher batch to confirm non-404 responses.

## 2026-01-25 - a01 SFT teacher data v0 (Phase 3.2.1)
- Files: `tools/generate_a01_teacher_contracts.py`, `src/react_agent/contract_utils.py`, `src/react_agent/json_utils.py`, `tools/prepare_router_sft.py`, `docs/A01_SFT_DATA_V0.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added a01-SFT teacher data generator (DeepSeek) with contract validation, hard-rule filtering, and stats output.
- Canonical JSON extraction is now reusable via `react_agent.json_utils`.
- SYSTEM_MAP documents a01-SFT data loop entry command and doc reference.
- Acceptance: `python tools/generate_a01_teacher_contracts.py --router-sft data/router_sft/router_sft_<date>_<catalog_id>.jsonl --questions data/questions/questions_pool_<date>_<catalog_id>.jsonl --out-train data/a01_sft/a01_sft_messages_<date>_<catalog_id>.train.jsonl --out-val data/a01_sft/a01_sft_messages_<date>_<catalog_id>.val.jsonl`
Phase positioning: This change belongs to Phase 3.2.1, focused on making a01 contract SFT data generation reproducible and rule-checked. It adds a teacher-only data path without introducing judge evaluation. The acceptance focus is correct contract filtering (steps length, coverage, schema) and a clean messages-style export. Next, validate on a small batch and confirm filter statistics stability before scaling. After that, proceed to a01-SFT training with consistent canonical JSON.

## 2026-01-25 - a01 contract-driven dispatch v0 (Phase 3)
- Files: `src/react_agent/graph.py`, `src/react_agent/prompts.py`, `src/react_agent/default_agents.py`, `tests/unit_tests/test_manager_contract_dispatch.py`, `docs/A01_CONTRACT_SCHEMA_V0.md`, `docs/SYSTEM_MAP.md`, `docs/INDEX.md`, `docs/CHANGELOG.md`
- Added a01 contract schema v0 doc and indexed it as protocol authority.
- Prompts now require a01 to emit strong-structure contract JSON aligned with router selection.
- Manager dispatch prefers contract tasks by agent_id with fail-open fallback; run_logger records contract usage summary.
- Tests cover contract-driven dispatch and fallback paths.
- CI workflows now install project dependencies via `uv pip install .` to honor `pyproject.toml`.
- SYSTEM_MAP now documents testing/dev setup and clarifies `requirements-hf.txt`/`requirements-train.txt` scope.
- Acceptance: `pytest -q tests/unit_tests/test_manager_contract_dispatch.py`
Phase positioning: This change belongs to Phase 3 runtime hardening and Phase 3.2.2 acceptance hardening for dependency/test chains. It updates CI install commands so unit tests reflect runtime imports defined in `pyproject.toml`. It keeps LangGraph topology and contract logic intact while improving reproducibility. Immediate acceptance is the unit test command above in a clean venv plus CI workflow pass. Next, expand validation to the full unit test suite before proceeding with a01-SFT/judge work.

## 2026-01-24 - Docs alignment + overview entry (Phase 2)
- Files: `docs/INDEX.md`, `docs/PROJECT_OVERVIEW.md`, `README.md`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`
- Added docs index and project overview as long-term narrative/roadmap entry points.
- README: added Docs Index / Project Overview links (SYSTEM_MAP remains the command source of truth).
- SYSTEM_MAP: added a high-level narrative pointer to PROJECT_OVERVIEW and clarified its non-operational scope.
- Doc alignment retained: default model text, `max_search_results` wiring note, and L2 truncation statement.
Phase positioning: This change belongs to Phase 2 documentation landing, focusing on long-term narrative and navigation rather than runtime changes. It intentionally avoids modifying execution logic and preserves SYSTEM_MAP/RUNBOOK as the only operational authorities. The goal is to stabilize onboarding and audit references before expanding SLM training scope. Next acceptance should verify the new doc links and review PROJECT_OVERVIEW against current metrics and plans. After that, Phase 3 work can proceed on a01 contract schema and judge infrastructure without further doc drift.

## 2026-01-23 - Phase 3.1 train eval stability guard
- Files: `tools/train_router_sft_qlora.py`, `docs/SYSTEM_MAP.md`, `docs/RUNBOOK_ROUTER_SFT.md`
- Added `remove_unused_columns=False` and optional eval disable when `--max-eval-samples 0`; kept eval batch guard with `per_device_eval_batch_size` defaulting to train batch
- Docs consolidated Phase 3.1 evidence (completion-only, canonical JSON labels, LoRA attach, HF preds canonical JSON) + AutoDL network sync workarounds (Contents API / tarball + rsync excludes)
- Why: prevent eval-time "no columns" / OOM spikes on long sequences; make AutoDL reproduction resilient to GitHub 443 timeouts
- Verify: run training with `--max-eval-samples 0` (no eval during training) and confirm merged output exists, then run post-train eval

## 2026-01-09 - 评测可回归 meta v1
- Files: `tools/eval_router_outputs.py`, `tools/generate_router_preds.py`, `tools/generate_router_preds_hf.py`, `ops/data_pipeline/export_router_sft_dataset.py`, `docs/SYSTEM_MAP.md`
- Added meta fields for reproducible evaluation: git commit, preds/catalog/val sha256, model/prompt_format, and run timestamps
- Manifest extended with seed/val_ratio and I/O file hashes for val/train export
- Why: enable baseline vs. finetune comparisons with traceable inputs
- Verify: run preds -> eval twice on the same val set and compare `metrics.json.meta`

## 2026-01-09 - 回归评测门禁 v1
- Files: `tools/run_regression_eval.py`, `docs/SYSTEM_MAP.md`
- Added two-pass regression runner with `compare.json` meta consistency report
- Why: provide a fast pass/fail signal for Phase 3 regression acceptance
- Verify: `python tools/run_regression_eval.py --val-messages ... --out-dir tmp/regression_eval`

## 2026-01-09 - 门禁口径分级
- Files: `tools/run_regression_eval.py`, `docs/SYSTEM_MAP.md`
- Added `--gate-mode repro|condition` to switch strict vs. condition-only gating
- Why: avoid false failures for stochastic provider outputs while keeping reproducible HF checks

## 2026-01-09 - HF baseline 可复现最小增强
- Files: `tools/generate_router_preds_hf.py`, `requirements-hf.txt`, `docs/SYSTEM_MAP.md`
- Added seed control and meta fields for reproducible HF preds; documented optional HF deps
- Verify: HF preds -> eval -> regression gate with `--gate-mode repro`

## 2026-01-09 - Runner 透传 seed
- Files: `tools/run_regression_eval.py`, `docs/SYSTEM_MAP.md`
- Added `--seed` to regression runner and passed through to HF preds generation
- Verify: `python tools/run_regression_eval.py --mode hf --seed 42 --gate-mode repro ...`

## 2026-01-09 - HF preds 输入截断
- Files: `tools/generate_router_preds_hf.py`
- Added truncation for overlong prompts with max context detection; caps total length by reserving tokens for generation
- Verify: `python tools/generate_router_preds_hf.py --model-path sshleifer/tiny-gpt2 --max-items 2 --max-new-tokens 512 ...`

## 2026-01-09 - Repro gate uses content hash
- Files: `tools/eval_router_outputs.py`, `tools/run_regression_eval.py`, `docs/SYSTEM_MAP.md`
- Added `preds_content_sha256` (id+raw_text) and use it for repro gating to ignore meta run_ts
- Verify: run HF repro gate twice and confirm `diff_keys` empty

## 2026-01-09 - Phase 3.1 Router-SFT minimal chain
- Files: `tools/prepare_router_sft.py`, `tools/train_router_sft_qlora.py`, `requirements-train.txt`, `docs/SYSTEM_MAP.md`
- Added parse-based data prep (strict by parse_ok) and QLoRA SFT trainer; documented prepare/train/eval commands
- Verify: run prepare -> train (small subset) -> run_regression_eval on merged model

## 2026-01-09 - Phase 3.1 strict+merge alignment
- Files: `tools/prepare_router_sft.py`, `tools/train_router_sft_qlora.py`, `docs/SYSTEM_MAP.md`
- Strict filter now means parse_ok==True AND used_default_plan==False; training command requires merge output for post-train eval
- Verify: prepare summary includes used_default_plan count; merged dir exists after training

## 2026-01-09 - Phase 3.1 training script compatibility
- Files: `tools/train_router_sft_qlora.py`, `docs/SYSTEM_MAP.md`
- Added completion-only masking via Trainer and prompt truncation control to avoid invalid JSON outputs
- Verify: smoke train then post-train eval valid_json_rate > 0

## 2026-01-09 - QLoRA attach LoRA adapters
- Files: `tools/train_router_sft_qlora.py`, `docs/SYSTEM_MAP.md`
- Attach LoRA adapters to 4-bit base (QLoRA) so Trainer can fine-tune; print trainable params
- Verify: smoke train no longer errors on quantized model

## 2026-01-09 - QLoRA eval OOM guard
- Files: `tools/train_router_sft_qlora.py`, `docs/SYSTEM_MAP.md`
- Added per-device-eval-batch-size (defaults to train batch) and eval_accumulation_steps=1 to reduce eval OOM risk

## 2026-01-09 - HF preds canonical JSON
- Files: `tools/generate_router_preds_hf.py`, `docs/SYSTEM_MAP.md`
- Normalize raw_text to first JSON object (compact dump) to improve valid_json_rate
