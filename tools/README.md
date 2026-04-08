# Tools

> Transition note (Phase 2B U1): Router regression scripts moved from `tools/` to `ops/regression/router/`.

- `ops/regression/router/generate_router_preds.py`: provider-based preds generator.
- `ops/regression/router/generate_router_preds_hf.py`: local HF preds generator.
- `ops/regression/router/eval_router_outputs.py`: offline evaluator for router raw outputs.
- `ops/regression/router/run_regression_eval.py`: two-pass regression runner with meta gate.
- `tools/sample_router_preds.jsonl`: minimal sample input.

How to generate preds and evaluate:
1) Run any model on your validation prompts.
2) Save raw assistant outputs into JSONL lines with fields `{id, raw_text}`.
3) Run:
   `conda run -n cline_env python ops/regression/router/generate_router_preds_hf.py --in <val.jsonl> --out tmp/preds.jsonl --model-path <hf_model>`
4) Evaluate:
   `conda run -n cline_env python ops/regression/router/eval_router_outputs.py --in tmp/preds.jsonl --out tmp/metrics.json`
