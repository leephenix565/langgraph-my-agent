# CHANGELOG

## 2026-01-28 - Phase 4.1 branch self-consistency (Phase 4.1.4)
- Files: `tools/server_preflight.py`, `tools/eval_a01_sft.py`, `docs/SYSTEM_MAP.md`, `docs/CHANGELOG.md`, `docs/DECISION_LOG.md`
- Ensured data/router-sft-v1 contains Phase 4.1 scripts and evidence fields referenced by SYSTEM_MAP.
- Acceptance: `rg -n "Phase 4.1" docs/SYSTEM_MAP.md` and `python tools/server_preflight.py --help`
Phase positioning: This Phase 4.1.4 update aligns branch contents with the documented runbook. It does not change schema or training logic, only ensures missing scripts and evidence fields are present on the branch. Next, push the branch and re-run server preflight on AutoDL.

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
- Files: `docs/INDEX.md`, `data/a01_sft/DATA_MANIFEST.md`, `project_analysis.md`, `docs/SYSTEM_MAP.md`, `docs/DECISION_LOG.md`, `docs/CHANGELOG.md`
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
- Acceptance: verify `data/a01_sft/final/*` exists, read `docs/HANDOFF_A01_SFT_FINAL.md`, and run the self-check snippet from DATA_MANIFEST.
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
- Files: `tools/eval_router_outputs.py`, `tools/generate_router_preds.py`, `tools/generate_router_preds_hf.py`, `export_router_sft_dataset.py`, `docs/SYSTEM_MAP.md`
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

## 2026-01-28 - Phase 4.1.6 eval truncation hardening
- Raise eval default `--max-new-tokens` to 4096 to avoid truncation-caused gate false-fail.
