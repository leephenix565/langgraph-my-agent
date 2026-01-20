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
