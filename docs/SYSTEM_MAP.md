# SYSTEM_MAP (Single Source of Truth)

更新时间：2026-01-09

## 1) 运行态入口与最小启动

### LangGraph Studio / CLI
- 入口配置：`langgraph.json` 指向 `src/react_agent/graph.py:graph`。
```json
{
  "graphs": { "agent": "./src/react_agent/graph.py:graph" },
  "env": ".env"
}
```
- 仓库内未提供明确的 CLI 启动命令。使用 LangGraph Studio/CLI 时应读取上述 `langgraph.json`。

### Python 最小运行
- 示例脚本：`demo_layered_run.py`
```bash
python demo_layered_run.py
```
- 直接 import（最小示例）
```bash
python -c "from react_agent import graph_app; from react_agent.context import Context; import asyncio; print(asyncio.run(graph_app.ainvoke({'messages':[('user','hi')]} , context=Context())))"
```

## 2) 运行链路（入口 → graph → router → manager → agent → summary）
- graph 构建：`src/react_agent/graph.py`（StateGraph + add_node/add_edge）
- Router：`router_node()` 生成 `layer_plan/layer_mode` 并写入状态
- Manager：`manager_broadcast()` 根据 mode 派发；Debate/Tree 降级为 Star
- Agent：`_build_agent_node()` 封装 AgentInput 并写入 `analyst_results`
- Summary：`manager_summary()` 推进层级或生成最终答复

## 3) 训练态真实流程（Router SFT）

### 3.1 生成 RouterPlan 数据
脚本：`generate_router_plans.py`
```bash
python generate_router_plans.py \
  --questions data/questions/questions_pool_YYYYMMDD_<catalog_id>.jsonl \
  --catalog-id <catalog_id> \
  --out-ok data/router_sft/router_sft_<date>_<catalog_id>.jsonl \
  --out-fail data/router_sft/router_sft_fail_<date>_<catalog_id>.jsonl
```
输出字段（OK 样本核心字段）：
`catalog_id, question_id, source, bucket, question, mode_hint, teacher, router_plan_raw, router_plan_parsed, parser_ok, violations, [auto_fix, fix_notes]`

### 3.2 导出训练格式
脚本：`export_router_sft_dataset.py`
```bash
python export_router_sft_dataset.py \
  --in-ok data/router_sft/router_sft_<date>_<catalog_id>.jsonl \
  --catalog-prompt data/catalogs/catalog_<catalog_id>_prompt.json \
  --out-messages data/sft/router_sft_messages_<catalog_id>.train.jsonl
```
输出字段（messages 格式）：
`id, messages[system+user], response, meta`
MANIFEST（在 `data/router_sft/`）会记录：`seed, val_ratio, in_ok_sha256, out_train_sha256, out_val_sha256`。

### 3.3 数据准备（自动打标 + 过滤）
脚本：`tools/prepare_router_sft.py`
```bash
python tools/prepare_router_sft.py \
  --in-train data/sft/router_sft_messages_<catalog_id>.train.jsonl \
  --in-val data/sft/router_sft_messages_<catalog_id>.val.jsonl \
  --out-dir data/sft/prepared \
  --filter-mode strict \
  --emit-val-messages-strict
```
输出：`prepared_train.jsonl / prepared_val.jsonl`（messages 追加 assistant 回合，meta 写入 parse_ok/parse_error 等）。
strict 口径：`parse_ok == True && used_default_plan == False`。

### 3.4 QLoRA SFT 训练（Qwen3-4B）
依赖（可选）：`pip install -r requirements-train.txt`
脚本：`tools/train_router_sft_qlora.py`
Phase 3.1 默认启用合并产物：`--merge-and-save-full-model`。
兼容说明：transformers 4.57 使用 `eval_strategy`；completion-only 训练（prompt 屏蔽）由 Trainer 处理；QLoRA=4bit base + LoRA adapters（可训练）；长度由 `tokenizer.model_max_length` / `max_seq_len` 控制。
```bash
python tools/train_router_sft_qlora.py \
  --base-model-path /root/autodl-tmp/models/Qwen3-4B-Instruct-2507 \
  --train-jsonl data/sft/prepared/prepared_train.jsonl \
  --val-jsonl data/sft/prepared/prepared_val.jsonl \
  --output-dir /root/autodl-tmp/out/router_sft_qlora \
  --max-seq-len 8192 \
  --seed 42 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 16 \
  --lr 2e-4 \
  --num-epochs 1 \
  --merge-and-save-full-model
```

### 3.5 Post-train eval / gate（HF）
使用 merge 后模型路径或 adapter 合并后的模型路径：
```bash
python tools/run_regression_eval.py \
  --val-messages data/sft/router_sft_messages_<catalog_id>.val.jsonl \
  --mode hf \
  --hf-model-path /root/autodl-tmp/out/router_sft_qlora/merged \
  --device cuda \
  --temperature 0 \
  --seed 42 \
  --max-items 2 \
  --gate-mode repro \
  --out-dir /root/autodl-tmp/out/regression_eval
```

## 4) 评测 / 批跑（run_graph_batch 缺失的替代流程）

仓库中**不存在** `run_graph_batch` 脚本。实际替代流程如下：

### 4.1 生成 preds.jsonl（provider 模型）
脚本：`tools/generate_router_preds.py`
```bash
python tools/generate_router_preds.py \
  --in data/sft/router_sft_messages_...val.jsonl \
  --out tmp/preds.jsonl \
  --model deepseek/deepseek-chat
```
每条记录会附带 `meta`：`provider/model, prompt_format, source_val_path/source_val_sha256, run_ts`。

### 4.2 生成 preds.jsonl（本地 HF 模型）
脚本：`tools/generate_router_preds_hf.py`
依赖（可选）：`pip install -r requirements-hf.txt`
```bash
python tools/generate_router_preds_hf.py \
  --in data/sft/router_sft_messages_...val.jsonl \
  --out tmp/preds.jsonl \
  --model-path <hf_model_path_or_name> \
  --max-items 2 --device cpu
```
每条记录会附带 `meta`：`hf_model_id, prompt_format, source_val_path/source_val_sha256, run_ts, seed, do_sample, temperature`。

### 4.3 评测
脚本：`tools/eval_router_outputs.py`
```bash
python tools/eval_router_outputs.py --in tmp/preds.jsonl --out tmp/metrics.json
```
metrics.json 字段（节选）：
`valid_json_rate, used_default_plan_rate, l2_trunc_rate, avg_filtered_agents, mode_dist, l2_len_dist, l3_len_dist, meta`
可选：`--val-messages <val.jsonl>` 以补齐 `val_messages_*` 元信息。

### 4.4 可回归评测（meta 对齐）
- 评测前先核对 `metrics.json.meta`：`git_commit`, `preds_path/preds_sha256`, `catalog_*`, `val_messages_*`。
- `preds.jsonl` 每行包含 `meta`（模型/提示格式/val 源信息/时间戳），用于追溯生成条件。
- 对比 baseline/训练后结果时，应先确认 `meta` 一致，再比较统计指标。

## 5) 关键环境变量（读取位置）
- `Context`（`src/react_agent/context.py`）：`MODEL`, `SYSTEM_PROMPT`, `RUN_ID` 等通过字段名大写读取 env。
- `run_logger`（`src/react_agent/run_logger.py`）：`LOCAL_TRACE`, `LOG_DIR`, `TRACE_MAX_CHARS`。
- `graph`（`src/react_agent/graph.py`）：`ENABLE_BUILTIN_AGENTS`, `INCLUDE_DISABLED_AGENTS`。
- `tools`（`src/react_agent/tools.py`）：`TAVILY_API_KEY`（TavilySearchResults）。

## 6) 回归/验证命令
```bash
python -m pytest tests/unit_tests/
python -m pytest tests/integration_tests/
```

## 7) Phase 3 回归验收（评测门禁）

对同一 val_messages 连跑两次 preds->eval，并对比 `metrics.json.meta` 的关键字段一致性。

```bash
python tools/run_regression_eval.py \
  --val-messages data/sft/router_sft_messages_...val.jsonl \
  --mode provider \
  --model deepseek/deepseek-chat \
  --out-dir tmp/regression_eval
```

判定规则：
- `--gate-mode repro`（默认）：用于本地 HF、temperature=0，要求完全复现；比较 `preds_content_sha256`（稳定内容哈希）并看 `meta_match` 与 `diff_keys`。
- `--gate-mode condition`：用于 provider 或允许随机场景，忽略 `preds_sha256`；看 `hard_match` 与 `soft_mismatch_keys`。

HF 可复现推荐命令（CPU）：
```bash
python tools/run_regression_eval.py \
  --val-messages data/sft/router_sft_messages_...val.jsonl \
  --mode hf \
  --hf-model-path <hf_model_path_or_name> \
  --device cpu \
  --temperature 0 \
  --seed 42 \
  --gate-mode repro \
  --out-dir tmp/regression_eval
```
