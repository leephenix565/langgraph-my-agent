# System Map

## Phase EXCEL-CATALOG-ALIGN-1 Agent Catalog v2

- Business taxonomy authority: `/sdb/dlut/agent_layer_latest.xlsx`; endpoint/profile lineage remains `/sdb/dlut/智能体分工及访问接口.csv`, `/sdb/dlut/智能体的描述.csv`, plus `docs/AGENT_CATALOG_V2_SHEET2_MAPPING.md`.
- Runtime `layer` is now the business layer code: `L1=解析层`, `L2=分析层`, `L3=应用层`, and `L4=报告层`.
- Agent id prefixes are stable runtime keys, not business order. Formal display/acceptance order is carried by `business_order` for the 24 latest-sheet agents.
- Router runtime, `a01_cio_orchestrator`, and `a25_report_center` are special system runtime roles and must not be replaced by external functional profiles.
- Runtime catalog: 25 enabled roles in `config/agents`, with enabled layer counts L1=2, L2=19, L3=3, L4=1. This equals 23 enabled functional entries plus 2 special runtime roles; 22 enabled functional entries are listed in the latest layer sheet and `a03_macro_industry_research` is retained from the older CSV because its macro wrapper is already live-verified.
- Metadata catalog: 27 config files. `disabledIds=["a05_annual_report_analysis","a21_portfolio_manager"]` are retained non-Excel historical functional metadata and are not default runtime nodes.
- Agent metadata includes `business_order`, `business_role`, `business_status`, `business_layer`, `business_category`, and `business_subcategory` for latest-sheet taxonomy without changing State/public API schemas.
- Generic external HTTP wrappers currently register 13 configured agents in `AGENT_TOOLS`; wrapper registration is separate from live service verification.
- Ten enabled non-wrapper functional agents have a callable
  `INTERNAL_LLM_SEARCH_PLACEHOLDER` path in `AGENT_TOOLS`: a generic LLM tool
  using the agent profile plus optional Tavily search and fail-soft limitation
  evidence. This is not a claim that dedicated external services are live.
- Tavily is optional transitional fallback for placeholder agents, not a
  required main-system dependency. The target architecture is for business
  agents to be delivered as owner-provided external HTTP services.
- `a03_macro_industry_research` remains enabled and callable as a live-verified macro wrapper even though it is not listed in `/sdb/dlut/agent_layer_latest.xlsx`; it is marked `保留层（旧CSV）/价值分析` pending taxonomy decision.
- AC-1A kept Router/parser/State/public API schemas unchanged and left route-prior/RARP/SFT helper source in place; AC-1B-2A later removed the old runtime seam while retaining that helper source as archived/offline lineage.
- AC-1B-1 archives offline RP/RARP/SFT/manual-gold/teacher-proxy evidence from mainline acceptance.
- AC-1B-2A removes the old route-prior/RARP runtime shadow seam from `react_agent.graph`; the old helper source remains archived/offline and is no longer imported by graph runtime.
- Runbook: `docs/AGENT_CATALOG_V2_RUNBOOK.md`.

This document is the S0 operational source for the current repo snapshot.

## 1. Current Phase

- Frontend/runtime integration: `Phase F3`
- Repo-level closure: `Phase QS-2`
- Landed seam still in scope: `Phase WS-1` workflow-first streaming
- Scope: hardening the public-adapter/web mainline, continuity/readiness surfaces, and authority-doc truth without changing LangGraph runtime business semantics
- Non-goals:
  - no new product features
  - no file upload
  - no URL fetch / HTML parsing / snapshot persistence
  - no SSE
  - no token streaming
  - no raw graph-event or chain-of-thought streaming
  - no LangGraph runtime business-semantic changes

## 2. Environment Baseline

- Python requirement: `>=3.11,<4.0`
- Local baseline env: `cline_env`
- Clean Windows/Codex validation example: `D:\AnacondaEnvs\langgraph_agent_py311`
- Frontend baseline: `node` + `npm` under `apps/web/`
- Do not treat `pnpm` or `yarn` as the documented frontend baseline.
- Mainline Python dependency truth: `pyproject.toml`
- Local development/static install path: `python -m pip install -e ".[dev]"`, then `python -m pip install pytest`
- `.[dev]` supplies static tooling for `scripts/quality/run_quality.py --mode static`: `ruff`, `mypy`, and `codespell`.
- Phase AC-1A-V2: the quality runner resolves `codespell` from the active Python
  environment's local `Scripts`/`bin` directory before falling back to shell
  `PATH`, so Windows/conda validation does not depend on pre-mutating `PATH`.
- `pytest` is installed separately in local and CI test gates unless dependency-group tooling is used explicitly.
- `requirements-hf.txt` and `requirements-train.txt` are optional non-mainline dependency sets for HF/model-side and training/fine-tuning workflows. They are not default mainline quality inputs.
- Search readiness is optional by default. `TAVILY_API_KEY` enables Tavily
  fallback search, `DISABLE_SEARCH=1|true|yes|on` is a supported LLM-only
  placeholder mode, and only `SEARCH_REQUIRED=true` makes missing search
  credentials block public runtime invocation.
- Web-P0B-lite public API trial guardrails are enabled by default:
  `PUBLIC_API_RATE_LIMIT_PER_MINUTE=120`,
  `PUBLIC_API_MAX_MESSAGE_CHARS=20000`,
  `PUBLIC_API_MAX_ACTIVE_STREAMS_PER_IP=3`, and
  `PUBLIC_API_REQUEST_TIMEOUT_SECONDS=300` for deployment planning. Values
  `<=0` disable the corresponding limiter/check. Client keys use
  `request.client.host`; reverse-proxy deployments must separately review
  trusted proxy headers. These are small-scope trial protections only, not
  token/auth, HTTPS, or formal public deployment security.
- Development 8200 demo stack:
  `scripts/dev/start_8200_demo_stack.sh` checks/starts the configured external
  wrapper services when safe, starts `react_agent.public_api:app` on
  `127.0.0.1:8210`, and starts the Vite shell on `0.0.0.0:8200` with
  `VITE_API_PROXY_TARGET=http://127.0.0.1:8210`. Status and stop helpers live in
  the same `scripts/dev` directory. Logs and PID files are under
  `/tmp/lma-demo-stack`. This is dev-demo operation only; it is not
  HTTPS/auth/reverse-proxy production deployment.
- DeepSeek is currently an LLM provider path only. Do not treat the DeepSeek App
  web-search feature as evidence that this repo has verified default DeepSeek
  API web search.
- Legacy `ROUTE_PRIOR_*` envs are archived/offline lineage only after AC-1B-2A. Current `react_agent.graph` no longer reads them, and they do not extend `/api/health` readiness or any public-safe contract.
- Offline RP/RARP/SFT/manual-gold/teacher-proxy artifacts under `ops/regression/route_prior/`, `data/router_sft/`, `data/sft/`, and `data/a01_sft/` are archived/non-mainline lineage as of AC-1B-1. They are not current Agent Catalog v2 acceptance evidence and are not default quality-gate promotion evidence.
- Static gate tooling lives in the repo's dev dependency surface and is required for `scripts/quality/run_quality.py --mode static`.
- Static gate executable resolution is a tooling concern only; it does not change
  Router/parser/State/public API/frontend schema, Agent Catalog v2 metadata, or
  external valuation wrapper behavior.

Recommended environment self-check:

```powershell
conda run --no-capture-output -n cline_env python --version
conda run --no-capture-output -n cline_env python -c "import sys; print(sys.executable)"
npm --version
```

Windows pytest note:

- Prefer `conda run --no-capture-output -n cline_env python ...`
- If `cline_env` is polluted or `conda run` is unavailable, prefer a clean Python 3.11 env for Windows/Codex validation.
- Use `PYTHONNOUSERSITE=1` so user-site packages do not contaminate validation.
- Use env-local `TEMP`, `TMP`, and `MYPY_CACHE_DIR` when C-drive temp space or repo-local cache permissions are unreliable.
- This is an execution-layer workaround for Windows terminal output issues, not a logic change

## 3. Repo-Level Quality Entry

The repo keeps one repo-level quality command source of truth:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
```

Available modes:

- `mainline`
- `static`
- `unit`
- `public-api`
- `graph-smoke`
- `frontend`
- `fusion-gate`

`mainline` currently runs:

1. `ruff`
2. `mypy`
3. `codespell`
4. `pytest tests/unit_tests`
5. `pytest tests/integration_tests/test_public_api.py`
6. `pytest tests/integration_tests/test_graph.py`
7. `npm --prefix apps/web run build`
8. `npm --prefix apps/web run test`
9. deterministic fusion regression / eval / gate

Current blocking static scope is intentionally narrower than the full repo:

- `scripts/quality/`
- active Python integration tests
- current authority docs / README / `AGENTS.md`

This keeps the default quality gate anchored to the maintained quality-closure surface instead of dragging historical bench/tooling debt into the blocking path.

Underlying convenience wrappers in `Makefile`:

- `make quality`
- `make quality_static`
- `make quality_unit`
- `make quality_public_api`
- `make quality_graph_smoke`
- `make quality_frontend`
- `make quality_fusion_gate`
- `make quality_provider_smoke`

The script path above is the command truth. `Makefile` is only a wrapper.

## 4. Mainline CI

Mainline blocking workflow:

- file: `.github/workflows/unit-tests.yml`
- workflow name: `Quality Gate`

Current blocking job split:

- `python-static`
- `python-unit`
- `public-adapter-integration`
- `graph-smoke`
- `frontend`
- `fusion-gate`

Responsibilities:

- blocking static checks: `ruff`, `mypy`, `codespell`
- Python unit tests
- public adapter integration tests
- runtime graph smoke
- frontend build/test
- deterministic fusion gate

This workflow is the mainline quality gate for `push` to `main`, `pull_request`, and `workflow_dispatch`.

## 5. Active Test Surface

Active default-gate tests:

- `tests/unit_tests/`
- `tests/integration_tests/test_public_api.py`
- `tests/integration_tests/test_graph.py`
- `apps/web/src/test/smoke.tsx`

Archived offline tests:

- `tests/archive/route_prior/`
- `tests/archive/router_eval/`
- `tests/archive/sft/`

These archive directories are retained for historical lineage and offline
reproducibility only. They are not collected by the default
`pytest tests/unit_tests` gate and are not current Agent Catalog v2 acceptance
evidence.

Legacy frontend fixtures:

- `apps/web/src/test/app.smoke.legacy.tsx`
- `apps/web/src/test/workflow.smoke.legacy.tsx`

They are retained only for reference and are not part of the default frontend gate.

## 6. Optional Provider / Live Smoke

Provider/live smoke is scripted, but it remains optional and non-blocking for the default gate.

Command:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_provider_live_smoke.py --out-dir ops/regression/provider/out
```

Output artifact:

- `ops/regression/provider/out/provider_live_smoke.json`

Artifact fields include:

- `status`
- `timestamp`
- `mode`
- `health`
- `prerequisites`
- `thread_id`
- `send_message_status`
- `continuity_mode`
- `error_code`
- `error_category`
- `residual_condition`
- `next_trigger_condition`

Behavior:

- if provider/search/checkpointer prerequisites are missing, the script writes `status="skipped"` and exits `0`
- if the environment is ready, the script exercises:
  - `GET /api/health`
  - `POST /api/threads`
  - `POST /api/threads/{id}/messages`
- if the live seam fails, the script writes `status="failed"` and exits non-zero

Optional workflow:

- file: `.github/workflows/integration-tests.yml`
- workflow name: `Optional Provider Live Smoke (Non-Blocking)`
- trigger: scheduled or manual only
- not part of the default blocking gate

Residual boundary:

- the current local evidence still remains a scripted `skipped` path rather than a passed provider-backed artifact
- current missing conditions in this environment are:
  - provider credentials (`OPENAI_API_KEY`, `ROUTER_OPENAI_API_KEY`, `BASELINE_OPENAI_API_KEY`, or `GOOGLE_API_KEY`)
  - optional Tavily search credentials only when a search-backed run is explicitly required
  - runtime import/readiness in a fully configured provider-backed state

## 7. Deterministic Fusion Gate

Deterministic FF-5B regression/eval/gate remains network-free and is part of the mainline quality entry.

Commands:

```powershell
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.run_fusion_regression --out-dir ops/regression/fusion/out
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.eval_fusion_outputs --in ops/regression/fusion/out/fusion_runs.jsonl --out ops/regression/fusion/out/fusion_metrics.json
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.gate_fusion_outputs --in ops/regression/fusion/out/fusion_metrics.json --out ops/regression/fusion/out/fusion_gate.json
```

Artifacts:

- `ops/regression/fusion/out/fusion_runs.jsonl`
- `ops/regression/fusion/out/fusion_metrics.json`
- `ops/regression/fusion/out/fusion_gate.json`

Default gate policy:

- deterministic
- network-free
- trace noise remains warning-only
- provider/live smoke remains outside the default blocking gate

## 8. Archived RP/RARP/SFT Offline Evidence

AC-1B-1 classifies the RP-1B/RP-2A/RP-2B/RP-3A route-prior/RARP offline
experiments, manual-gold fixtures, teacher-proxy labels, and Router-SFT/A01-SFT
data as archived/offline/non-mainline evidence. They are retained for
historical lineage and reproducibility only. They are not current Agent Catalog
v2 acceptance evidence, not default quality-gate evidence, and not current
routing-quality promotion evidence.

Current runtime fact: AC-1B-2A removes the old RP-1A/RP-2C runtime seam from
`react_agent.graph`. The graph no longer imports or executes `route_prior`,
`route_reliability`, `load_route_profile_cards`, or old route-prior comparison
logic. The archived helper source remains in `src/react_agent/` for historical
lineage and offline reproducibility only; it does not own current routing.

Archived lineage locations:

- `ops/regression/route_prior/README_ARCHIVED.md`
- `data/router_sft/README_ARCHIVED.md`
- `data/sft/README_ARCHIVED.md`
- `data/a01_sft/DATA_MANIFEST.md`
- `tests/archive/route_prior/`
- `tests/archive/router_eval/`
- `tests/archive/sft/`

The commands and inventory below are historical reproduction notes only.

Local Qwen embedding service inventory for RP-1A/RP-3A-5C experiments:

```text
latest checked status:
  service health is currently ok on http://127.0.0.1:8001/healthz
  model reported by health: Qwen/Qwen3-Embedding-0.6B
  this is a project-external local process, so re-check health before each live route-prior experiment

historical purpose:
  project-external local OpenAI-compatible embeddings endpoint for archived
  RP-1A / RP-3A route-prior experiments

  model:
  Qwen/Qwen3-Embedding-0.6B
  output dimension: 1024
  last known endpoint smoke: count=2, dims=[1024, 1024]
  latest RP-3A-5F route-prior artifact: enabled_count=20, disabled_count=0, cards_non_empty_count=20

serving:
  project-external FastAPI + SentenceTransformers wrapper
  not repo runtime code
  health endpoint: http://127.0.0.1:8001/healthz
  embeddings endpoint: http://127.0.0.1:8001/v1/embeddings
  request model: Qwen/Qwen3-Embedding-0.6B
  local placeholder authorization token: local-test

local paths:
  embedding env: D:\AnacondaEnvs\qwen_embedding_py311
  service dir: D:\LocalEmbeddingServices\qwen3_embedding_server
  service file: D:\LocalEmbeddingServices\qwen3_embedding_server\qwen_embedding_server.py
  stdout log: D:\LocalEmbeddingServices\qwen3_embedding_server\server.out.log
  stderr log: D:\LocalEmbeddingServices\qwen3_embedding_server\server.err.log
  HF cache root: D:\Models\huggingface\sentence-transformers\models--Qwen--Qwen3-Embedding-0.6B
  snapshot: D:\Models\huggingface\sentence-transformers\models--Qwen--Qwen3-Embedding-0.6B\snapshots\97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3
  snapshot ref: 97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3
  cache size: 25 files, approximately 1.125 GB
  main model file: model.safetensors, approximately 1.19 GB

env versions:
  Python: 3.11.15
  torch: 2.11.0+cpu
  transformers: 5.6.2
  sentence_transformers: 5.4.1
  fastapi: 0.136.1
  uvicorn: 0.46.0
  httpx: 0.28.1
  pydantic: 2.13.3

hardware note:
  NVIDIA GeForce RTX 3060 Laptop GPU is present, 6144 MiB VRAM
  qwen_embedding_py311 currently uses CPU torch, so serving runs on CPU
  GPU serving requires a separate CUDA torch rebuild and must not pollute the repo clean env

service behavior:
  Authorization header is accepted but ignored locally
  raw input is not written to disk
  full embeddings are not printed
  logs only record batch size, model, dimension, elapsed ms, and cache hit/miss counts
  normalize_embeddings=True by default
  default batch size: 8
  default prefix: empty string
  optional QWEN_EMBEDDING_PREFIX is supported
  optional QWEN_EMBEDDING_DEVICE is supported
  process-local memory cache is keyed by input text sha256 and is cleared on restart
  empty string or empty input list returns 400
```

Historical reproduction command for the project-external embedding service:

```powershell
$env:QWEN_EMBED_ENV = "D:\AnacondaEnvs\qwen_embedding_py311"
$env:HF_HOME = "D:\Models\huggingface"
$env:HUGGINGFACE_HUB_CACHE = "D:\Models\huggingface\hub"
$env:TRANSFORMERS_CACHE = "D:\Models\huggingface\transformers"
$env:SENTENCE_TRANSFORMERS_HOME = "D:\Models\huggingface\sentence-transformers"
$env:TORCH_HOME = "D:\Models\torch"
$env:PYTHONNOUSERSITE = "1"
$env:TEMP = "$env:QWEN_EMBED_ENV\pip-tmp"
$env:TMP = "$env:QWEN_EMBED_ENV\pip-tmp"
$env:Path = "$env:QWEN_EMBED_ENV;$env:QWEN_EMBED_ENV\Scripts;$env:QWEN_EMBED_ENV\Library\bin;$env:Path"

$env:QWEN_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
$env:QWEN_EMBEDDING_CACHE = "D:\Models\huggingface\sentence-transformers"
$env:QWEN_EMBEDDING_BATCH_SIZE = "8"
$env:QWEN_EMBEDDING_PREFIX = ""

Start-Process -FilePath "$env:QWEN_EMBED_ENV\python.exe" `
  -ArgumentList "-m uvicorn qwen_embedding_server:app --host 127.0.0.1 --port 8001" `
  -WorkingDirectory "D:\LocalEmbeddingServices\qwen3_embedding_server" `
  -RedirectStandardOutput "D:\LocalEmbeddingServices\qwen3_embedding_server\server.out.log" `
  -RedirectStandardError "D:\LocalEmbeddingServices\qwen3_embedding_server\server.err.log" `
  -PassThru
```

Foreground start alternative:

```powershell
cd D:\LocalEmbeddingServices\qwen3_embedding_server
D:\AnacondaEnvs\qwen_embedding_py311\python.exe -m uvicorn qwen_embedding_server:app --host 127.0.0.1 --port 8001
```

Historical RP-1A route-prior env for this local service. Keep these in the
local shell or local `.env` only; do not add them to `.env.example`:

```powershell
$env:ROUTE_PRIOR_EMBEDDINGS_ENABLED = "1"
$env:ROUTE_PRIOR_EMBEDDINGS_MODEL = "Qwen/Qwen3-Embedding-0.6B"
$env:ROUTE_PRIOR_OPENAI_BASE_URL = "http://127.0.0.1:8001/v1"
$env:ROUTE_PRIOR_OPENAI_API_KEY = "local-test"
```

Historical local probes, without printing full embeddings:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/healthz

D:\AnacondaEnvs\qwen_embedding_py311\python.exe -c "import httpx; r=httpx.post('http://127.0.0.1:8001/v1/embeddings', json={'model':'Qwen/Qwen3-Embedding-0.6B','input':['macro rates valuation','portfolio risk compliance'],'encoding_format':'float'}, headers={'Authorization':'Bearer local-test'}, timeout=120); print('status', r.status_code); r.raise_for_status(); b=r.json(); items=b.get('data', []); print('model', b.get('model')); print('count', len(items)); print('dims', [len(i.get('embedding', [])) for i in items]); print('sample_heads', [[round(float(x), 6) for x in i.get('embedding', [])[:3]] for i in items])"
```

Last known RP-1B DeepSeek teacher-proxy + Qwen route-prior eval result, recorded
as diagnostic evidence only and not manual-gold promotion evidence:

```text
case_count=20
enabled_rate=1.0
retrieval_reason_counts={"ok":20}
confidence_band_counts={"low":12,"normal":6,"wide":2}
low_confidence_fallback_rate=0.6
avg_shortlist_size=17.2
avg_shortlist_ratio=0.7478260869565216
top1_match_rate=0.9
top3_match_rate=1.0
top5_match_rate=1.0
shortlist_recall=0.95
full_expected_covered_rate=0.85
```

Boundary: this local service is outside the repo. It does not change Router
prompt/parser behavior, State schema, public API, `/api/health`, frontend,
manager dispatch, or the mainline quality gate. When unavailable, RP-1A remains
shadow-only and fail-open.

Historical offline replay commands:

```powershell
python -m ops.regression.route_prior.run_route_prior_eval --dataset ops/regression/route_prior/fixtures/rp1b_labeling_template.jsonl --out-dir ops/regression/route_prior/out --max-items 10 --prewarm-endpoint
python -m ops.regression.route_prior.eval_route_prior_outputs --runs ops/regression/route_prior/out/route_prior_runs.jsonl --out ops/regression/route_prior/out/route_prior_metrics.json
```

Historical optional RP-2B reliability-card artifact generation:

```powershell
python -m ops.regression.route_prior.run_route_prior_eval --dataset ops/regression/route_prior/fixtures/rp2_labeling_template.jsonl --out-dir ops/regression/route_prior/out --enable-rarp-scoring --profile-cards-dir config/route_profiles --reliability-table ops/regression/route_prior/out/route_reliability_table.json
```

Historical private RP-2C runtime-trace envs for archived lineage only:

```powershell
$env:ROUTE_PRIOR_RELIABILITY_ENABLED="1"
$env:LOCAL_TRACE="1"
```

RP-2A label-template fixture:

```powershell
ops/regression/route_prior/fixtures/rp2_labeling_template.jsonl
```

RP-3 manual-gold seed-template fixture:

```powershell
ops/regression/route_prior/fixtures/rp3_manual_gold_seed_template.jsonl
```

This RP-3 seed template is a candidate labeling file only. Its records remain
`draft_for_human_review` with `quality_conclusion_allowed=false` until a human
reviewer explicitly confirms them as `manual_gold`.

Accepted RP-3 manual-gold smoke fixture:

```powershell
ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl
```

This fixture contains 20 GPT Pro assisted records accepted by the project owner
as reviewed `manual_gold`. It is smoke evidence for schema / fixture / prompt
A/B dry-run preparation only; it is not an initial or promotion-quality dataset.

Historical network-free RP-3A-1 Router advisory A/B parser dry-run:

```powershell
python -m ops.regression.route_prior.run_router_advisory_ab --dataset ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl --out-dir ops/regression/route_prior/out --max-items 20 --mode network-free
```

This harness makes no provider calls. It replays supplied or deterministic-stub
Router outputs through `parse_router_layers_with_stats(...)` and writes ignored
local artifacts under `ops/regression/route_prior/out/` for parser-stability and
selected-agent-delta inspection. It is not a runtime Router advisory.

RP-3A-2B hardens that same offline harness prediction-artifact schema. The
optional `--predictions` JSONL still accepts legacy `baseline_raw` /
`advisory_raw`, and now also accepts enriched `baseline` / `advisory` side
objects with model name/spec, prompt char count, token count, latency,
prompt/catalog hash, and parse latency metadata. The harness records this
metadata in A/B artifacts and aggregates token/latency deltas when provided. It
does not call a live model, does not store full prompt bodies, does not implement
runtime advisory, and does not create promotion evidence by itself.

Historical optional RP-3A-3 Router advisory prediction artifact generator:

```powershell
python -m ops.regression.route_prior.generate_router_advisory_predictions --dataset ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl --out ops/regression/route_prior/out/router_advisory_predictions_dry_run.jsonl --summary-out ops/regression/route_prior/out/router_advisory_predictions_dry_run_summary.json --max-items 20 --mode dry-run
```

This generator writes enriched `router_advisory_prediction_v0` JSONL artifacts
for the A/B replay harness. Default `dry-run` mode is network-free and uses a
deterministic label-derived `advisory_source="label_stub"` smoke path. Explicit
`--mode live` may call a configured Router model; missing provider env writes a
`status="skipped"` summary and exits without promoting any gate. The tool does
not persist full prompt bodies and does not implement runtime Router advisory.
RP-3A-5 extends this same optional generator with
`--advisory-source provided_artifact|rarp_shadow` and `--advisory-artifact` for
local RP-2 route-prior / route-reliability JSONL artifacts. Provided-artifact
cases are keyed by case id, grouped by the formal Router layer catalog, and
record artifact hash, confidence, fallback, agent ids, reason codes, retrieval
status, and missing reasons in prediction JSONL. Missing, disabled, or empty
reliability-card cases are marked as `provided_artifact_missing` /
`rarp_shadow_missing` and never silently fall back to label-derived advisory.
RP-3A-5B further treats missing, disabled, low-confidence, and empty-card cases
as `advisory_applied=false` / `noop_no_advisory`: the generator does not render
an advisory block and live mode reuses baseline output/metadata instead of
making a second advisory-side call. A/B replay records noop comparisons without
counting them as advisory-induced critical regressions.
RP-3A-5E hardens the applied `provided_artifact` renderer after real Qwen-backed
RARP-card live smoke showed wildcard-only advisory ids could over-narrow the
Router. If strong/candidate groups are empty, the generator now prefers
top-ranked non-wildcard route-prior cards as weak non-binding candidates and
keeps wildcard ids as secondary context only. If no non-wildcard card exists,
the case is marked `noop_wildcard_only`. This is still offline generator behavior
only and is not runtime advisory or promotion evidence.
RP-3A-5F records the latest real RARP provided-artifact live-stability evidence.
The Qwen-backed route-prior artifact was enabled for all 20 `manual_gold_20`
cases, with non-empty reliability cards for all 20. Three full DeepSeek live
reruns produced no parse/default regressions across 60 case replays and one
critical miss regression on `rp3-manual-gold-0017` in run 1 only. The ignored
report artifacts are `ops/regression/route_prior/out/rp3_routing_case_report.md`
and `ops/regression/route_prior/out/rp3_routing_case_table.json`. This remains
20-case smoke evidence for the offline experiment path, not runtime advisory or
promotion evidence.
RP-3A-4D hardens this label-stub prompt path after a 5-case DeepSeek live smoke
showed `rp3-manual-gold-0004` placing L3 critical agent `a19_market_risk` in
L2. The stub now renders `must_include_agents_by_layer`,
`critical_agents_by_layer`, and `nice_to_have_agents_by_layer` from label
`expected_layers` plus the formal catalog, with explicit layer-constraint text.
This remains offline harness/prediction-generator behavior only; it does not
modify runtime Router prompt construction, parser behavior, State/public
surfaces, frontend behavior, manager dispatch, agent execution, quality gates,
or `/api/health`.

Historical optional DeepSeek teacher-proxy labeling:

```powershell
python -m ops.regression.route_prior.generate_deepseek_teacher_labels --input ops/regression/route_prior/out/rp1b_manual_draft_20.jsonl --out ops/regression/route_prior/out/rp1b_deepseek_teacher_v1_20.jsonl --max-items 20
```

DeepSeek records use `label_source="deepseek_teacher_v1"`. They are model-generated proxy labels for offline RP-1B experiments, not human/manual gold labels and not runtime truth.

Artifacts:

- `ops/regression/route_prior/out/route_prior_runs.jsonl`
- `ops/regression/route_prior/out/route_prior_run_summary.json`
- `ops/regression/route_prior/out/route_prior_metrics.json` (`route_prior_metrics_v2` after RP-2A, legacy RP-1B fields retained)
- `ops/regression/route_prior/out/route_prior_false_negatives.json`
- `ops/regression/route_prior/out/router_advisory_ab_runs.jsonl`
- `ops/regression/route_prior/out/router_advisory_ab_summary.json`

Archive policy:

- archived/offline/non-mainline unless future work explicitly re-promotes it with new acceptance evidence
- default unit coverage stays network-free and does not require a local embeddings endpoint
- live runs require the private RP-1A embedding envs and a local OpenAI-compatible `/v1/embeddings` service
- fixture records marked `draft_for_human_review` are labeling drafts, not final quality evidence
- records marked `deepseek_teacher_v1` are teacher-proxy labels only; metrics should keep `quality_conclusion_allowed=false`
- RP-2B is offline-first profile-card/reliability tooling: no runtime graph change, Router prompt/parser change, State schema change, manager dispatch change, public API change, public workflow change, frontend change, `/api/agents` route-profile exposure, `/api/health` expansion, or mainline quality-gate promotion
- RP-2C was historical runtime trace/comparison only: default off, fail-open, no Router prompt/parser change, no committed `layer_plan`/`layer_mode`/`current_layer` mutation, no State schema field, no public API/workflow/frontend change, no `/api/agents` reliability-card exposure, no `/api/health` expansion, no advisory, no repair, and no mainline quality-gate promotion. AC-1B-2A removes that runtime wiring from current graph execution.
- RP-3A-0D is a docs-only Router advisory experiment design checkpoint. It records prompt A/B dry-run artifact shape, parse-stability metrics, manual-gold evidence requirements, token/latency budget evidence, and rollback policy expectations. It adds no command truth, no runtime code, no Router prompt/parser behavior, no State/public/API/workflow/health surface, no tests, no frontend changes, and no mainline quality-gate promotion. RP-3 advisory remains unimplemented.
- RP-3A-1 adds a network-free offline A/B harness only. It does not modify `ROUTER_SYSTEM_PROMPT`, parser behavior, State schema, graph runtime routing, public contracts, workflow snapshots, `/api/agents`, `/api/health`, frontend behavior, manager dispatch, agent execution, or quality gates.
- RP-3A-2B only hardens the offline A/B prediction-artifact schema and summary metadata aggregation. It is not an optional-live runner, not runtime advisory, not a Router prompt/parser change, and not promotion evidence.
- RP-3A-3 adds an optional prediction artifact generator for the offline A/B harness. Its default dry-run path is network-free; live mode is explicit and optional. It does not change runtime Router prompt construction, parser behavior, State/public surfaces, frontend behavior, manager dispatch, agent execution, or quality gates.
- RP-3A-4D only hardens the offline `label_stub` advisory with per-layer advisory groups and layer-constraint wording. It addresses a wrong-layer smoke regression in the experiment harness and is still not runtime advisory or promotion evidence.
- RP-3A-5 adds offline `provided_artifact` / `rarp_shadow` advisory-source experiments for the optional `generate_router_advisory_predictions` path only. It does not implement runtime Router advisory, does not change `ROUTER_SYSTEM_PROMPT`, parser behavior, graph runtime routing, State schema, or any public API/workflow/health/frontend surface, and the resulting artifacts are evidence inputs only, not routing-quality promotion evidence.
- RP-3A-5B hardens the offline no-advisory fallback for missing, disabled, low-confidence, or empty-card provided artifacts. These cases are explicit noop comparisons, not RARP-card quality evidence, and remain optional/non-blocking.
- RP-3A-5E hardens the offline provided-artifact renderer so wildcard-only advisories are not treated as clean applied signals. Strong/candidate-empty cases use top-ranked non-wildcard cards as weak layer-aware candidates, with wildcard retained only as secondary context; no runtime Router advisory or public surface changes are introduced.
- RP-3A-5F is evidence consolidation only: it records three full `manual_gold_20` DeepSeek live provided-artifact reruns and per-case routing report artifacts. It has real RARP cards (`enabled_count=20`, `cards_non_empty_count=20`) and parse/default stability across 60 replays, but still has one stochastic critical miss and remains smoke evidence, not promotion evidence.
- Prompt A/B and route-prior promotion evidence remain optional/non-blocking until a future change explicitly lands the harness and promotes any gate.

## 9. Runtime and Public Boundary

Runtime entry:

- `langgraph.json -> src/react_agent/graph.py:graph`

Current runtime topology:

- `__start__ -> router`
- `router -> manager_broadcast` and `router -> baseline_sidecar`
- `agent nodes -> manager_summary`
- `manager_summary/finalize_summary -> fusion_gate -> fusion_judge_shadow -> fusion_writer_shadow -> final_emit -> (memory_update | __end__)`
- `mainline_emit` remains a compatibility wrapper; current graph routing targets `final_emit`

Current public path:

- `apps/web -> /api/* -> react_agent.public_api -> react_agent.public_runtime -> react_agent.graph.get_graph_for_invoke(...)`

Default answer-source behavior:

- Fair Fusion baseline/judge/writer sidecars exist in runtime
- `enable_fair_fusion=false` and `enable_fair_fusion_source_switch=false` by default
- the visible answer therefore stays on the mainline path unless source switching is explicitly enabled
- Phase DS-1 defines the commercial API line as the baseline sidecar/Fair Fusion `BASELINE_*` provider path plus the three valuation-service internal `LLM_*` provider paths. It does not migrate the main multi-agent global `MODEL` / `OPENAI_BASE_URL` / `OPENAI_API_KEY` path.
- The checked-in `.env.example` baseline sidecar example is DeepSeek V4 Pro via the OpenAI-compatible path: `BASELINE_MODEL=openai/deepseek-v4-pro`, `BASELINE_OPENAI_BASE_URL=https://api.deepseek.com`, and `BASELINE_OPENAI_API_KEY`
- `.env.example` keeps `ENABLE_FAIR_FUSION_SOURCE_SWITCH=0`; baseline output cannot replace the visible mainline answer unless source switching is explicitly enabled.
- The `google_genai/...` Gemini grounding branch in `baseline_sidecar.py` remains an explicit opt-in implementation path, not the default baseline model in `.env.example`

Important boundaries that remain unchanged on the current mainline:

- formal Router provider output plus `router_parse` own current routing
- do not reintroduce old route-prior / RARP shadow logic into graph runtime without rebuilding a catalog-v2 `router_prior_v2`
- do not surface legacy `ROUTE_PRIOR_*` config/readiness on `/api/health`
- do not treat `state["messages"]` as the public transcript
- do not turn internal agents into separate public chat speakers
- keep workflow as a summarized inspector
- keep `text` as the canonical transcript / store / replay truth
- keep replay continuity explicitly weaker than persistent graph continuity
- keep `structuredInput`, `materials`, and `urlReferences` additive only
- keep Fair Fusion as baseline/judge/writer sidecars rather than ordinary L1-L4 agents

## 10. Public Adapter Truthfulness

The current public adapter truth surface remains:

- `/api/health`
- `/api/threads`
- `/api/agents`
- `/api/threads/{thread_id}`
- `/api/threads/{thread_id}/messages`
- `/api/threads/{thread_id}/messages/stream`

Stream-event surface:

- transport: `application/x-ndjson`
- safe event types only:
  - `run.started`
  - `workflow.stage`
  - `workflow.snapshot`
  - `answer.final`
  - `error`

Truthfulness rules that still apply:

- `text` remains canonical on send-message ingress and stored user turns
- replay reconstructs continuity from `turn.text` alone
- `structuredInput` is an additive mirror only
- `materials` and `urlReferences` must still compile into canonical transcript text
- workflow stays an inspector, not a raw graph dump
- stream progress events are public-safe projections only and are never persisted as transcript turns
- `answer.final` is the only streaming event that carries the final persisted assistant answer payload

## 11. Frontend Baseline

Frontend commands still live under `apps/web/`:

```powershell
npm --prefix apps/web install
npm --prefix apps/web run build
npm --prefix apps/web run test
npm --prefix apps/web run screenshots
```

Important current test fact:

- the active frontend gate entry is `tsx src/test/smoke.tsx`
- the assistant answer card now renders `answerCard.answer` through a client-side Markdown renderer with GFM table support
- the chat message column now keeps a stable horizontal gutter and constrains assistant Markdown blocks so they wrap or scroll inside the answer card instead of overflowing the viewport
- the chat shell now prefers the additive NDJSON stream seam and falls back to the sync seam when a readable stream is unavailable
- this frontend rendering change does not alter backend contracts, transcript truth, or replay semantics
- legacy fixture files with a `.legacy.tsx` suffix are not part of the default gate

## 12. Router-SFT Runbook Position

Router-SFT training/eval command truth lives in:

- `docs/RUNBOOK_ROUTER_SFT.md`

It is archived/offline/non-mainline as of AC-1B-1. It is not part of the
default mainline quality gate and is not current Agent Catalog v2 acceptance
evidence.
