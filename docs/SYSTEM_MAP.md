# SYSTEM_MAP (Single Source of Truth)

更新时间：2026-01-23

高层叙事入口：`docs/PROJECT_OVERVIEW.md`（路线图 + 指标体系 + 为何 SLM 更强；不包含命令与操作细节）
a01 合同协议入口：`docs/A01_CONTRACT_SCHEMA_V0.md`（schema v0 + 运行态消费规则）

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

### Testing/Dev setup（单测环境）
推荐本地最小安装链路（与 CI 对齐）：
```bash
uv venv
uv pip install .
uv pip install pytest
uv run pytest tests/unit_tests/test_manager_contract_dispatch.py
```
说明：`requirements-hf.txt` 与 `requirements-train.txt` 为训练专用依赖，不保证覆盖运行态或单测所需包。

## 2) 运行链路（入口 → graph → router → manager → agent → summary）
- graph 构建：`src/react_agent/graph.py`（StateGraph + add_node/add_edge）
- Router：`router_node()` 生成 `layer_plan/layer_mode` 并写入状态
- Manager：`manager_broadcast()` 根据 mode 派发；Debate/Tree 降级为 Star
- 合同驱动：当 `analyst_results["a01_cio_orchestrator"]["contract"]` 可用且校验通过，`manager_broadcast()` 按 agent_id 切片派发 steps；失败回退模板广播
- Agent：`_build_agent_node()` 封装 AgentInput 并写入 `analyst_results`
- Summary：`manager_summary()` 推进层级或生成最终答复

## 3) 训练态真实流程（Router SFT）
详细操作与证据归档请见：`docs/RUNBOOK_ROUTER_SFT.md`。

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
兼容说明：transformers 4.57 使用 `eval_strategy`；completion-only 训练（prompt 屏蔽）由 Trainer 处理；QLoRA=4bit base + LoRA adapters（可训练）；长度由 `tokenizer.model_max_length` / `max_seq_len` 控制。训练中设置 `remove_unused_columns=False`。eval 默认使用与 train 相同的 batch size 并设置 eval_accumulation_steps=1，以避免长序列 OOM；如需彻底关闭训练期 eval，可传 `--max-eval-samples 0`（会将 eval_strategy 设为 `no` 且不构建 eval_dataset）。
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

#### 3.4.1 Completion-only 训练（prompt 屏蔽）
- 训练仅对 assistant（RouterPlan JSON）回合计算 loss；prompt token 的 labels 设为 `-100`。
- 原因：避免拟合系统/用户提示，聚焦 RouterPlan JSON 合规输出。
- 实现位置：`tools/train_router_sft_qlora.py`（completion-only tokenize + labels masking + collator）。

#### 3.4.2 JSON canonicalization（prepare 阶段）
- `tools/prepare_router_sft.py` 在 append assistant 回合前，抽取 response 中“首个完整 JSON”，并 `json.dumps(..., separators=(",",":"))` 规范化。
- 目的：减少训练期输出混入非 JSON 前后缀，提升 eval 的 `valid_json_rate`。

#### 3.4.3 QLoRA 训练要点
- 量化模型必须挂 LoRA adapters 才能训练：`prepare_model_for_kbit_training` + `get_peft_model`。
- target_modules 采用动态扫描（q/k/v/o + gate/up/down proj 的交集）。
- 训练结束可用 `--merge-and-save-full-model` 输出 `output-dir/merged`（可直接 HF 加载）。

#### 3.4.4 训练期 eval 稳定性
- `remove_unused_columns=False` 避免 “No columns match forward signature”。
- eval 默认使用与 train 相同的 batch size，并设置 `eval_accumulation_steps=1` 以降低长序列 OOM 风险。
- 如需彻底关闭训练期 eval：`--max-eval-samples 0`（eval_strategy="no"，不构建 eval_dataset）。

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

### 3.6 产物与下载（AutoDL）
示例产物路径（来自 AutoDL 日志）：
- 训练输出目录：`/root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903/`
- 合并模型目录：`/root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903/merged`
  - 约 3.3G，包含 `model.safetensors` + `config.json` + tokenizer 文件
- 打包产物：
  - `..._merged.tgz`（约 2.4G）：合并后的全量模型权重，可直接 HF 加载推理
  - `..._full.tgz`：全目录包（含训练日志/适配器/状态等）

打包与下载示例：
```bash
# 打包 merged
cd /root/autodl-tmp/out
tar -czf router_sft_qwen3_4b_qlora_full_20260123_155903_merged.tgz \
  router_sft_qwen3_4b_qlora_full_20260123_155903/merged

# 打包全目录
tar -czf router_sft_qwen3_4b_qlora_full_20260123_155903_full.tgz \
  router_sft_qwen3_4b_qlora_full_20260123_155903

# 下载（示例：scp）
scp root@<autodl-host>:/root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903_merged.tgz .
```

本地验证加载：
```python
from transformers import AutoTokenizer, AutoModelForCausalLM
tok = AutoTokenizer.from_pretrained("path/to/merged", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained("path/to/merged", trust_remote_code=True)
```

### 3.6 a01-SFT 数据闭环（teacher 合同生成）
规范：`docs/A01_SFT_DATA_V0.md`
硬规则：`selected_agents` 必须包含 `a01_cio_orchestrator` 且等于 Router 选中集合；`tasks[].steps` 长度必须在 [2,6]。
```bash
python tools/generate_a01_teacher_contracts.py \
  --router-sft data/router_sft/router_sft_<date>_<catalog_id>.jsonl \
  --questions data/questions/questions_pool_<date>_<catalog_id>.jsonl \
  --out-train data/a01_sft/a01_sft_messages_<date>_<catalog_id>.train.jsonl \
  --out-val data/a01_sft/a01_sft_messages_<date>_<catalog_id>.val.jsonl \
  --out-stats data/a01_sft/a01_sft_teacher_stats_<date>_<catalog_id>.json
```
DeepSeek teacher 默认 base_url 为 `https://api.deepseek.com`，endpoint 固定为 `/chat/completions`（输入 `https://api.deepseek.com/v1` 也会归一化到该路径）。
`teacher_error` 仅统计 teacher 调用异常（HTTP/timeout/传输错误），不包含后续的 JSON/合同校验失败。
统计产物包含质量观测指标（generic_steps_ratio_v1 / very_generic_steps_ratio_v1 / duplicate_steps_contract_count / avg_steps_per_task），并补充记录级分布（generic_ratio_p50/p90/p95、very_generic_ratio_p50/p90/p95、steps_per_task_p50/p90/p95、duplicate_steps_contract_rate）；同时输出观测字段分位数（elapsed_ms_*、assistant_chars_*、usage_total_tokens_*），且每条记录 meta.quality / meta.teacher 中留痕。
FINAL 冻结路径：`data/a01_sft/final/a01_sft_messages_FINAL.{train,val}.jsonl` 与 `data/a01_sft/final/a01_sft_teacher_stats_FINAL.json`。
交接包：`docs/HANDOFF_A01_SFT_FINAL.md`。

### 3.6.1 Phase 4.1 a01-SFT 训练闭环（smoke train → eval → gate）
依赖安装（训练/评测环境）：
```bash
pip install -e .
pip install -r requirements-train.txt
pip install -r requirements-hf.txt
```
训练（completion-only QLoRA；只读 FINAL，不覆盖 data/a01_sft/final）：
```bash
python tools/train_a01_sft_qlora.py \
  --base-model-path <base_model_or_adapter> \
  --train-jsonl data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl \
  --val-jsonl data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl \
  --output-dir runs/a01_sft/20260128_smoke \
  --max-steps 50 \
  --max-train-samples 200
```
评测（greedy，温度 0）：
```bash
python tools/eval_a01_sft.py \
  --model-path runs/a01_sft/20260128_smoke \
  --val-jsonl data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl \
  --out-dir runs/a01_sft/20260128_smoke
```
门禁（断言 metrics + run_manifest）：
```bash
python tools/gate_a01_sft.py \
  --eval-report runs/a01_sft/20260128_smoke/eval_report.json
```

### 3.7 AutoDL 事实证据（日志摘记）
- strict 过滤：train 735/735 kept；val 15/15 kept；canon_success=100%（来自 prepare 日志）
- completion-only：prompt labels = -100（避免拟合 prompt）
- QLoRA 修复：trainable params ≈ 33,030,144（0.8145%）
- HF preds canonical JSON 后评测：`valid_json_rate=1.0`、`used_default_plan_rate=0.0`
- gate_mode=repro：两次 run `hard_match=True`、`meta_match=True`
- N=15 指标补充：exact_match=0/15；mode_acc：L1/L3/L4=1.0，L2≈0.8667；Jaccard：L2≈0.4357，L3≈0.5367，L2+L3≈0.4862

### 3.8 Phase 3.1.2 / 3.1.3 当前状态
- 3.1.2（数据准备与过滤）：完成（strict+canonical JSON + stats）
- 3.1.3（训练与 post-train eval）：完成最小闭环（completion-only + QLoRA merge + HF eval/gate）
- 下一步：提升 exact_match / Jaccard 指标，扩大 N 与长序列稳定性验证（TODO）

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
HF preds 会将 `raw_text` 规范化为首个 JSON 对象的 compact 形式（若无 JSON 则保留原文本）。

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
- `run_logger`（`src/react_agent/run_logger.py`）：`LOCAL_TRACE`, `LOG_DIR`, `TRACE_MAX_CHARS`。`LOCAL_TRACE=1` 才会写 JSONL；默认输出到 `log/YYYYMMDD/`，可用 `LOG_DIR` 覆盖路径；`TRACE_MAX_CHARS` 控制字段截断长度（默认 4000），并会自动剔除敏感键（token/secret/password）。
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

## 8) 网络与同步（AutoDL 应急方案）
现象（AutoDL 日志）：`github.com:443` 常超时；`api.github.com` 可访问。

### 8.1 GitHub Contents API（单文件覆盖）
适合快速同步 `tools/*.py` / `docs/*.md`：
```bash
# 例：下载 docs/SYSTEM_MAP.md
curl -L \
  "https://api.github.com/repos/leephenix565/langgraph-my-agent/contents/docs/SYSTEM_MAP.md?ref=data/router-sft-v1" \
  | python - <<'PY'
import sys, json, base64
obj = json.load(sys.stdin)
print(base64.b64decode(obj["content"]).decode("utf-8"), end="")
PY
```

### 8.2 GitHub tarball（整分支快照）
```bash
curl -L -o repo.tgz \
  "https://api.github.com/repos/leephenix565/langgraph-my-agent/tarball/data/router-sft-v1"
mkdir -p /tmp/repo_sync
tar -xzf repo.tgz -C /tmp/repo_sync --strip-components=1

# 只覆盖代码/文档，避免污染虚拟环境与数据
rsync -av --delete \
  --exclude ".git" --exclude ".venv" --exclude "data" \
  /tmp/repo_sync/ /root/autodl-tmp/work/my-agent/
```
