# A01-SFT Data v0 (Teacher Contracts)

> 权威级别：S0（数据规范）。本页定义 a01 合同 SFT 数据输入包、输出结构、过滤规则与生成命令。

## 1) 输入数据包
可接受两种入口之一：
- Router-SFT 原始数据：`data/router_sft/router_sft_<date>_<catalog_id>.jsonl`
- Router-SFT messages：`data/sft/router_sft_messages_<catalog_id>.train.jsonl`

最低字段依赖（用于生成合同）：
- `question_id`, `question`
- `router_plan_parsed` 或 `router_plan_raw`（需含 `layers[].layer/mode/selected`）

如问题文本缺失，可用 `data/questions/questions_pool_*.jsonl` 通过 `question_id` 回填。

## 2) Short Profile Pack（给 a01/teacher）
从 `config/agents/agent_*.json` 裁剪字段，固定格式（按 `selected_agents` 顺序）：
- `id`, `name`, `description`, `capabilities`, `layer`, `role_type`

## 3) a01 合同 schema v0 约束
合同必须满足 `a01_contract_v0`（见 `docs/A01_CONTRACT_SCHEMA_V0.md`），并增加 steps v0 阈值：
- `tasks[].steps` 为字符串列表，长度必须在 **[2, 6]**。
- `selected_agents` 覆盖集合必须包含 `a01_cio_orchestrator`，并等于 Router 选中集合（跨 L1-L4 的全量去重结果）。

示例（selected_agents 覆盖集合）：
```
selected_agents = ["a01_cio_orchestrator", "a03_macro_policy", "...", "a25_report_center"]
```

## 4) 过滤与原因码
输出仅保留“合同校验通过”的样本。常见原因码（drop）：
- `invalid_json`
- `missing_contract`
- `schema_version_mismatch`
- `contract_keys_mismatch`
- `invalid_objective`
- `invalid_constraints`
- `invalid_selected_agents`
- `selected_agents_mismatch`
- `invalid_aggregation`
- `invalid_budget`
- `invalid_output_spec`
- `invalid_output_spec_sections`
- `invalid_output_spec_format`
- `invalid_tasks`
- `invalid_task_type`
- `missing_task_keys`
- `task_agent_mismatch`
- `duplicate_task_agent`
- `invalid_task_id`
- `invalid_task_objective`
- `invalid_steps`
- `invalid_extension_flag`
- `invalid_extension_policy`
- `tasks_cover_mismatch`

## 5) 输出结构（messages 风格）
与 Router-SFT 一致：
```
{
  "id": "<question_id>",
  "messages": [{"role":"system",...},{"role":"user",...}],
  "response": "<compact JSON>",
  "meta": { ... }
}
```

## 6) 生成命令
```bash
python ops/train_eval/a01/generate_a01_teacher_contracts.py \
  --router-sft data/router_sft/router_sft_<date>_<catalog_id>.jsonl \
  --questions data/questions/questions_pool_<date>_<catalog_id>.jsonl \
  --out-train data/a01_sft/a01_sft_messages_<date>_<catalog_id>.train.jsonl \
  --out-val data/a01_sft/a01_sft_messages_<date>_<catalog_id>.val.jsonl \
  --out-stats data/a01_sft/a01_sft_teacher_stats_<date>_<catalog_id>.json \
  --val-ratio 0.02
```

可选：使用 Router-SFT messages 作为输入
```bash
python ops/train_eval/a01/generate_a01_teacher_contracts.py \
  --router-messages data/sft/router_sft_messages_<catalog_id>.train.jsonl \
  --questions data/questions/questions_pool_<catalog_id>.jsonl \
  --out-train data/a01_sft/a01_sft_messages_<date>_<catalog_id>.train.jsonl \
  --out-val data/a01_sft/a01_sft_messages_<date>_<catalog_id>.val.jsonl \
  --out-stats data/a01_sft/a01_sft_teacher_stats_<date>_<catalog_id>.json
```

默认 teacher：DeepSeek (`DEEPSEEK_API_KEY` 环境变量或 `--api-key`).
默认 base_url 为 `https://api.deepseek.com`；也可使用 `https://api.deepseek.com/v1`，生成器会将最终路径归一化为 `/chat/completions`。

## FINAL 产物路径
- `data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl`
- `data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl`
- `data/a01_sft/final/a01_sft_teacher_stats_FINAL.json`
交接包：`docs/archive/handoff/HANDOFF_A01_SFT_FINAL.md`。

## 7) 统计输出（验收口径）
`--out-stats` 将写入 JSON（与 stdout 同步），最少包含：
- `total`
- `json_extracted_ok`
- `contract_ok`
- `teacher_error`（teacher 调用异常计数，含 HTTP/timeout/传输错误）
- `dropped_reason_topk`
- `steps_len_stats`
- `coverage_rate`（contract_ok / total）
- `overreach_rate`（selected_agents 相关违规占比，包含 `selected_agents_mismatch` / `task_agent_mismatch` / `duplicate_task_agent` / `tasks_cover_mismatch` / `missing_a01`）
- `generic_steps_ratio_v1`（全局：generic_steps / total_steps）
- `very_generic_steps_ratio_v1`（更严格的空泛步骤比例）
- `duplicate_steps_contract_count`（合同内 steps 文本完全重复的合同数）
- `avg_steps_per_task`（总 steps / tasks_count）
- `generic_ratio_p50` / `generic_ratio_p90` / `generic_ratio_p95`
- `very_generic_ratio_p50` / `very_generic_ratio_p90` / `very_generic_ratio_p95`
- `steps_per_task_p50` / `steps_per_task_p90` / `steps_per_task_p95`
- `duplicate_steps_contract_rate`（duplicate_steps_contract_count / contract_ok）
- `elapsed_ms_p50` / `elapsed_ms_p90` / `elapsed_ms_p95`
- `assistant_chars_p50` / `assistant_chars_p90` / `assistant_chars_p95`
- `usage_total_tokens_p50` / `usage_total_tokens_p90` / `usage_total_tokens_p95`（若 usage 不可得则为 0）

## 8) Eval report（Phase 4.1）
- `ops/train_eval/a01/eval_a01_sft.py` 输出 `eval_report.json`，其中 `meta.max_new_tokens` 记录实际解码上限。
- 默认 `--max-new-tokens=4096`（见 `docs/SYSTEM_MAP.md` Phase 4.1 runbook）；smoke 如需更快可手动降到 2048，但需注意可能截断 JSON。

记录级 meta 增量（可选，不影响旧消费者）：
- `meta.quality.generic_ratio`
- `meta.quality.very_generic_ratio`
- `meta.quality.has_duplicate_steps`
- `meta.quality.steps_len_stats_per_record`
- `meta.teacher.elapsed_ms`
- `meta.teacher.assistant_chars`
- `meta.teacher.raw_chars`
- `meta.teacher.usage_total_tokens`（可选）
