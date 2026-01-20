# Tools

- `eval_router_outputs.py`: Offline evaluator for router raw outputs.
- `sample_router_preds.jsonl`: Minimal sample input.
- `generate_router_preds_hf.py`: Local HF inference for preds.jsonl.

How to generate preds:
1) Run any model on your validation prompts.
2) Save raw assistant outputs into JSONL lines with fields `{id, raw_text}`.

Local HF baseline:
1) Prepare val messages JSONL (see export_router_sft_dataset.py).
2) Run:
   `python tools/generate_router_preds_hf.py --in <val.jsonl> --out tmp/preds.jsonl --model-path <hf_model>`
3) Evaluate:
   `python tools/eval_router_outputs.py --in tmp/preds.jsonl --out tmp/metrics.json`
