# CHANGELOG

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

## 2026-01-09 - HF preds canonical JSON
- Files: `tools/generate_router_preds_hf.py`, `docs/SYSTEM_MAP.md`
- Normalize raw_text to first JSON object (compact dump) to improve valid_json_rate
