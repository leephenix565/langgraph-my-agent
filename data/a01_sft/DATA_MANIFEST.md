# A01 SFT DATA MANIFEST (FINAL)

## FINAL artifacts (frozen)
- `data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl`
- `data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl`
- `data/a01_sft/final/a01_sft_teacher_stats_FINAL.json`

### Origin mapping
- `a01_sft_messages_FINAL.train.jsonl` <= `a01_sft_messages_obs_N500_w12.train.jsonl`
- `a01_sft_messages_FINAL.val.jsonl` <= `a01_sft_messages_obs_N500_w12.val.jsonl`
- `a01_sft_teacher_stats_FINAL.json` <= `a01_sft_teacher_stats_obs_N500_w12.json`

## FINAL stats summary (from stats_FINAL)
- total=735
- contract_ok=731
- teacher_error=0
- coverage_rate=0.9945578231292517
- dropped_reason_topk=[['invalid_steps', 3], ['task_agent_mismatch', 1]]

### Quality & observability percentiles
- elapsed_ms_p50=101618.31510000047
- elapsed_ms_p90=120844.05430000334
- elapsed_ms_p95=125760.5612000043
- usage_total_tokens_p50=4757.0
- usage_total_tokens_p90=5312.0
- usage_total_tokens_p95=5456.0
- generic_ratio_p50=0.5714285714285714
- generic_ratio_p90=0.6666666666666666
- generic_ratio_p95=0.7
- very_generic_ratio_p50=0.08163265306122448
- very_generic_ratio_p90=0.14814814814814814
- very_generic_ratio_p95=0.16666666666666666
- steps_per_task_p50=4.111111111111111
- steps_per_task_p90=5.111111111111111
- steps_per_task_p95=5.222222222222222

## Archive & immutability policy
- `final/` is immutable: do not overwrite FINAL artifacts once frozen.
- New outputs must be placed under `data/a01_sft/_archive/<YYYY-MM-DD>/` with original filenames preserved.

Example structure:
```
data/a01_sft/
  final/
    a01_sft_messages_FINAL.train.jsonl
    a01_sft_messages_FINAL.val.jsonl
    a01_sft_teacher_stats_FINAL.json
  _archive/
    2026-01-26/
      a01_sft_messages_20260126_*.jsonl
      a01_sft_teacher_stats_20260126_*.json
    2026-01-27/
      a01_sft_messages_obs_*.jsonl
      a01_sft_teacher_stats_obs_*.json
```

## Integrity checks (sha256)
```bash
python -c "import hashlib, pathlib; p=pathlib.Path('data/a01_sft/final/a01_sft_teacher_stats_FINAL.json'); print(p.name, hashlib.sha256(p.read_bytes()).hexdigest())"
python -c "import hashlib, pathlib; p=pathlib.Path('data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl'); print(p.name, hashlib.sha256(p.read_bytes()).hexdigest())"
python -c "import hashlib, pathlib; p=pathlib.Path('data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl'); print(p.name, hashlib.sha256(p.read_bytes()).hexdigest())"
```

## Input dependencies
- Router messages: `data/sft/router_sft_messages_20260108_b434e7a9a883_v1.train.jsonl`
- Questions pool: `data/questions/questions_pool_20260108_20260108_b434e7a9a883_v1.jsonl`
- Agent profiles: `config/agents/agent_*.json`

## Generation command template
```bash
python ops/train_eval/a01/generate_a01_teacher_contracts.py \
  --router-messages data/sft/router_sft_messages_20260108_b434e7a9a883_v1.train.jsonl \
  --questions data/questions/questions_pool_20260108_20260108_b434e7a9a883_v1.jsonl \
  --out-train data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl \
  --out-val data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl \
  --out-stats data/a01_sft/final/a01_sft_teacher_stats_FINAL.json \
  --max-items 500 \
  --workers 12 \
  --timeout 120
```

## Quick self-check
```python
import json
from pathlib import Path

stats = json.loads(Path("data/a01_sft/final/a01_sft_teacher_stats_FINAL.json").read_text(encoding="utf-8"))
print({k: stats.get(k) for k in ["total","contract_ok","teacher_error","coverage_rate"]})

line = Path("data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl").read_text(encoding="utf-8").splitlines()[0]
rec = json.loads(line)
print(sorted(rec["meta"].get("teacher", {}).keys()))
print(sorted(rec["meta"].get("quality", {}).keys()))
```
