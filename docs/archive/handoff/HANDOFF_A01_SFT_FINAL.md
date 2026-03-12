# Handoff: A01 SFT FINAL (Phase 3.3)

## 1) 当前阶段与状态
- Phase 3.3 已完成：a01 SFT 数据冻结与仓库卫生（FINAL 单一真源 + 历史产物归档）。
- 本交接包用于在新对话/新机器上延续 Phase 4.1 训练闭环。

## 2) FINAL 三件套路径（单一真源）
- `data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl`
- `data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl`
- `data/a01_sft/final/a01_sft_teacher_stats_FINAL.json`

> 备注：FINAL 由 `a01_sft_messages_obs_N500_w12.*` 与 `a01_sft_teacher_stats_obs_N500_w12.json` 冻结而来，禁止覆盖。

## 3) FINAL stats 摘要（来自 stats_FINAL）
- total=735
- contract_ok=731
- teacher_error=0
- coverage_rate=0.9945578231292517
- dropped_reason_topk=[["invalid_steps",3],["task_agent_mismatch",1]]

### 质量/时延观测分位数
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

## 4) 关键生成命令（仅参考，不建议重复生成）
```bash
python tools/generate_a01_teacher_contracts.py \
  --router-messages data/sft/router_sft_messages_20260108_b434e7a9a883_v1.train.jsonl \
  --questions data/questions/questions_pool_20260108_20260108_b434e7a9a883_v1.jsonl \
  --out-train data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl \
  --out-val data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl \
  --out-stats data/a01_sft/final/a01_sft_teacher_stats_FINAL.json \
  --max-items 500 \
  --workers 12 \
  --timeout 120
```

## 5) 观测字段（record-level）
- meta.teacher keys：`elapsed_ms`, `assistant_chars`, `raw_chars`, `usage_total_tokens`
- meta.quality keys：`generic_ratio`, `very_generic_ratio`, `has_duplicate_steps`, `steps_len_stats_per_record`

## 6) 下一阶段 Phase 4.1（训练闭环）建议任务清单
1) 训练输入验证：读取 FINAL train/val，确认 messages/response/meta 结构完整与可读。
2) 训练配置准备：确认训练脚本/配置使用 FINAL 路径且不覆盖 final。
3) 小样本训练 smoke test：N=50（或更小）确保 loss 正常、无格式错误。
4) 训练产物命名规范：输出模型与日志路径纳入新 _archive/<date>/。
5) 评测闭环衔接：使用现有 eval/gate 入口验证输出 JSON 合规率。

## 7) 数据版本管理规范
- 新产物必须进入 `data/a01_sft/_archive/<date>/`。
- `data/a01_sft/final/` 永不覆盖，仅做读引用。

## 8) 本地自检命令
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
