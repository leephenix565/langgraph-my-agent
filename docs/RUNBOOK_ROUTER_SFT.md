# Router-SFT Runbook (AutoDL)

目标：把 Phase 3.1.2/3.1.3（completion-only + JSON canonicalization + eval 稳定性）的进展固化为可复制运行手册。  
**只记录已发生的事实**；不确定部分标注 TODO。

更新时间：2026-01-23

## 0) Phase 定位
- Phase 3.1.2：数据准备与过滤（strict + canonical JSON）
- Phase 3.1.3：QLoRA 训练（completion-only）+ 合并 + post-train eval/gate

## 0.1 关键 commit（远端分支 data/router-sft-v1）
> 来自 AutoDL 日志记录（供定位问题用）
- `712de7d`：Reduce eval OOM via eval batch and accumulation
- `5631d8e`：Canonicalize HF preds raw_text to JSON

## 1) 环境证据（AutoDL）
- torch: **2.5.1+cu121**
- transformers: **4.57.6**
- trl: **0.27.0**
- peft: **0.18.1**

> TODO: 记录 `merged/model.safetensors` sha256（如需可用 `sha256sum` 补齐）

## 2) 数据准备与标签规范化
脚本：`tools/prepare_router_sft.py`

关键事实（来自日志）：
- strict 过滤：train **735/735** kept；val **15/15** kept
- `canon_success=100%`
- strict 口径：`parse_ok == True && used_default_plan == False`
- assistant 标签 canonicalize：抽首个完整 JSON + `json.dumps(..., separators=(",",":"))`

命令（可复制）：
```bash
python tools/prepare_router_sft.py \
  --in-train data/sft/router_sft_messages_20260108_b434e7a9a883_v1.train.jsonl \
  --in-val data/sft/router_sft_messages_20260108_b434e7a9a883_v1.val.jsonl \
  --out-dir data/sft/prepared \
  --filter-mode strict \
  --emit-val-messages-strict
```

产物：
- `data/sft/prepared/prepared_train.jsonl`
- `data/sft/prepared/prepared_val.jsonl`
- `data/sft/prepared/val_messages_strict.jsonl`（可选）

## 3) 训练策略（completion-only）
脚本：`tools/train_router_sft_qlora.py`

关键事实：
- completion-only：prompt tokens 的 labels 置为 `-100`，只对 assistant JSON 计算 loss  
- 解释：避免拟合系统/用户 prompt，专注 RouterPlan JSON 合规输出

训练命令（可复制）：
```bash
python tools/train_router_sft_qlora.py \
  --base-model-path /root/autodl-tmp/models/Qwen3-4B-Instruct-2507 \
  --train-jsonl data/sft/prepared/prepared_train.jsonl \
  --val-jsonl data/sft/prepared/prepared_val.jsonl \
  --output-dir /root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903 \
  --max-seq-len 8192 \
  --seed 42 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 16 \
  --lr 2e-4 \
  --max-steps 300 \
  --merge-and-save-full-model
```

## 4) QLoRA 修复（量化模型必须挂 LoRA）
关键事实：
- 报错根因：`ValueError: cannot fine-tune purely quantized models`
- 修复：`prepare_model_for_kbit_training` + `get_peft_model`
- target_modules：q/k/v/o + gate/up/down proj（动态交集）
- trainable params 约 **33,030,144（0.8145%）**

## 5) HF 推理 JSON 规范化（关键）
脚本：`tools/generate_router_preds_hf.py`

关键事实：
- raw_text 规范化为“首个 JSON 对象 + compact dump”
- raw_text_full 保留原文本用于 debug
- 修复后回归评测（N=15）：
  - `valid_json_rate = 1.0`
  - `used_default_plan_rate = 0.0`
  - gate_mode=repro：两次 run `hard_match=True`、`meta_match=True`

## 6) post-train eval / gate
使用 merged 目录：
```bash
python tools/run_regression_eval.py \
  --val-messages data/sft/router_sft_messages_20260108_b434e7a9a883_v1.val.jsonl \
  --mode hf \
  --hf-model-path /root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903/merged \
  --device cuda \
  --temperature 0 \
  --seed 42 \
  --max-items 15 \
  --gate-mode repro \
  --out-dir /root/autodl-tmp/out/regression_eval_qwen3_post_sft
```

## 7) 指标解释（N=15）
- exact_match：**0/15**（要求 JSON 全字段/全层完全一致）
- mode_acc：L1/L3/L4=1.0，L2≈0.8667
- Jaccard（集合相似度）：
  - L2≈0.4357
  - L3≈0.5367
  - L2+L3≈0.4862

含义：
- mode_acc：层级协作模式一致性（Star/Chain/…）
- Jaccard：该层 selected agent_ids 的集合重合度
- exact_match：最严格（全字段完全一致）

## 8) 产物与下载
示例产物（来自 AutoDL 日志）：
- 训练目录：`/root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903/`
- merged：`.../merged`（约 3.3G）
- 打包：
  - `..._merged.tgz`（约 2.4G，**可直接 HF 加载**）
  - `..._full.tgz`（全目录）

打包与下载：
```bash
cd /root/autodl-tmp/out
tar -czf router_sft_qwen3_4b_qlora_full_20260123_155903_merged.tgz \
  router_sft_qwen3_4b_qlora_full_20260123_155903/merged

scp root@<autodl-host>:/root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903_merged.tgz .
```

## 9) 网络与同步（GitHub 443 超时应急）
现象（AutoDL）：`github.com:443` 经常超时，`api.github.com` 正常。

### 9.1 Contents API（单文件）
```bash
curl -L \
  "https://api.github.com/repos/leephenix565/langgraph-my-agent/contents/tools/train_router_sft_qlora.py?ref=data/router-sft-v1" \
  | python - <<'PY'
import sys, json, base64
obj = json.load(sys.stdin)
print(base64.b64decode(obj["content"]).decode("utf-8"), end="")
PY
```

### 9.2 Tarball + rsync（整分支）
```bash
curl -L -o repo.tgz \
  "https://api.github.com/repos/leephenix565/langgraph-my-agent/tarball/data/router-sft-v1"
mkdir -p /tmp/repo_sync
tar -xzf repo.tgz -C /tmp/repo_sync --strip-components=1
rsync -av --delete \
  --exclude ".git" --exclude ".venv" --exclude "data" \
  /tmp/repo_sync/ /root/autodl-tmp/work/my-agent/
```

## 10) 已知坑与解决
- 量化模型必须挂 LoRA 才能训练（否则报 “cannot fine-tune purely quantized models”）
- HF preds 必须 canonical JSON，否则 eval `valid_json_rate=0` 且 used_default_plan=1
- 训练期 eval 易 OOM（长序列）；如不需要训练期评估，使用 `--max-eval-samples 0`

## 11) 下一步（TODO）
- 提升 exact_match / Jaccard 指标（更高一致性）
- 扩大 N 与长序列稳定性验证
- 记录 merged/model.safetensors 的 sha256
