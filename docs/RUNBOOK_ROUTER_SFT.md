# Router-SFT Runbook

> Local/Codex baseline: commands below assume `conda run --no-capture-output -n cline_env python ...`. If your local env name differs, only replace the env name after `-n`.

This runbook is the clean command-oriented reference for the current Router-SFT preparation, training, and eval path. It intentionally keeps only the still-useful operational content.

## 1. Scope

This document covers:

- router SFT data preparation
- Router QLoRA training
- post-train HF eval / gate
- expected artifact paths

It does not define the repo-level quality gate. For `Phase QS-3：final residual polish`, use [SYSTEM_MAP.md](/E:/langgraph-my-agent/docs/SYSTEM_MAP.md) and [run_quality.py](/E:/langgraph-my-agent/scripts/quality/run_quality.py).

## 2. Environment Baseline

Observed baseline from the retained training notes:

- `torch 2.5.1+cu121`
- `transformers 4.57.6`
- `trl 0.27.0`
- `peft 0.18.1`

Keep the current local baseline command style:

```powershell
conda run --no-capture-output -n cline_env python --version
```

## 3. Data Preparation

Script:

- `tools/prepare_router_sft.py`

Reference command:

```powershell
conda run --no-capture-output -n cline_env python tools/prepare_router_sft.py `
  --in-train data/sft/router_sft_messages_20260108_b434e7a9a883_v1.train.jsonl `
  --in-val data/sft/router_sft_messages_20260108_b434e7a9a883_v1.val.jsonl `
  --out-dir data/sft/prepared `
  --filter-mode strict `
  --emit-val-messages-strict
```

Expected outputs:

- `data/sft/prepared/prepared_train.jsonl`
- `data/sft/prepared/prepared_val.jsonl`
- `data/sft/prepared/val_messages_strict.jsonl`

## 4. Training

Script:

- `tools/train_router_sft_qlora.py`

Reference command:

```powershell
conda run --no-capture-output -n cline_env python tools/train_router_sft_qlora.py `
  --base-model-path /root/autodl-tmp/models/Qwen3-4B-Instruct-2507 `
  --train-jsonl data/sft/prepared/prepared_train.jsonl `
  --val-jsonl data/sft/prepared/prepared_val.jsonl `
  --output-dir /root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903 `
  --max-seq-len 8192 `
  --seed 42 `
  --per-device-train-batch-size 1 `
  --gradient-accumulation-steps 16 `
  --lr 2e-4 `
  --max-steps 300 `
  --merge-and-save-full-model
```

## 5. Post-Train Eval / Gate

Primary script:

- `ops/regression/router/run_regression_eval.py`

Reference command:

```powershell
conda run --no-capture-output -n cline_env python ops/regression/router/run_regression_eval.py `
  --val-messages data/sft/router_sft_messages_20260108_b434e7a9a883_v1.val.jsonl `
  --mode hf `
  --hf-model-path /root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903/merged `
  --device cuda `
  --temperature 0 `
  --seed 42 `
  --max-items 15 `
  --gate-mode repro `
  --out-dir /root/autodl-tmp/out/regression_eval_qwen3_post_sft
```

## 6. Known Operational Notes

- completion-only training remains the intended Router-SFT training mode
- quantized training still requires LoRA attachment
- HF regression eval still expects canonical JSON outputs
- if Windows `conda run` output re-encoding becomes unstable, keep using `--no-capture-output`

## 7. Artifact Expectations

Typical artifact locations:

- training output directory under `/root/autodl-tmp/out/...`
- merged model directory under `.../merged`
- prepared JSONL files under `data/sft/prepared/`
- router regression outputs under the selected eval `--out-dir`

## 8. Archive Boundary

This document is a minimal current runbook, not a historical narrative dump. Historical training notes and non-mainline details should live in archive docs or commit history rather than being re-expanded here.
