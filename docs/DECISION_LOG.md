# DECISION_LOG

## D1 — FINAL 数据单一真源路径
- Decision: 固定 FINAL 三件套路径为：
  - `data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl`
  - `data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl`
  - `data/a01_sft/final/a01_sft_teacher_stats_FINAL.json`
- Rationale: Phase 3.3 完成数据冻结与归档，避免未来覆盖。
- Evidence:
  - `docs/A01_SFT_DATA_V0.md` “FINAL 产物路径”
  - `docs/SYSTEM_MAP.md` “FINAL 冻结路径”
  - `data/a01_sft/DATA_MANIFEST.md`

## D2 — 质量观测字段与口径
- Decision: stats.json 与 record meta.quality / meta.teacher 作为质量与时延观测真源。
- Rationale: Phase 3.2.3–3.2.5 已增加分位数统计与观测字段。
- Evidence:
  - `tools/generate_a01_teacher_contracts.py`：`compute_quality_metrics`, `compute_quality_distribution_stats`, `compute_teacher_observability`
  - `docs/A01_SFT_DATA_V0.md` 统计字段说明
  - `docs/CHANGELOG.md` Phase 3.2.3–3.2.5 记录

## D3 — 数据版本管理规范
- Decision: 新产物进入 `data/a01_sft/_archive/<date>/`；`final/` 永不覆盖。
- Rationale: 避免数据漂移并保持可复现性。
- Evidence:
  - `data/a01_sft/DATA_MANIFEST.md` “数据版本管理规范”
  - `docs/CHANGELOG.md` Phase 3.3 记录

## D4 — 数据证据链与观测开关说明
- Decision: 将 `data/a01_sft/DATA_MANIFEST.md` 纳入 S0 权威链，并显式说明 trace 日志开关与截断规则。
- Rationale: 保障交接时的数据真源与可回溯日志口径一致。
- Evidence:
  - `docs/INDEX.md` S0 列表与冲突处理规则
  - `data/a01_sft/DATA_MANIFEST.md` 归档/校验规范
  - `docs/SYSTEM_MAP.md` 环境变量说明（LOCAL_TRACE/LOG_DIR/TRACE_MAX_CHARS）

## D5 — Phase 4.1 a01 SFT 训练闭环最小化
- Decision: a01 SFT 训练采用 completion-only QLoRA（沿用 Router 训练栈思想），评测与门禁分离，run_manifest 作为证据链落盘。
- Rationale: 保持 FINAL 数据只读，训练与评测可复现且可在服务器批量执行。
- Evidence:
  - `tools/train_a01_sft_qlora.py`（completion-only masking + run_manifest）
  - `tools/eval_a01_sft.py`（valid_json/contract_ok/schema_keys 评测）
  - `tools/gate_a01_sft.py`（阈值门禁 + manifest 断言）
  - `docs/SYSTEM_MAP.md` Phase 4.1 入口命令

## D6 — Phase 4.1 eval 可复核证据
- Decision: eval_report 记录模型权重 sha256 与模型目录大小，作为评测可复核证据。
- Rationale: 使服务器评测结果可被追溯到具体模型权重与产物规模。
- Evidence:
  - `tools/eval_a01_sft.py`（model_sha256 / model_dir_bytes / model_dir_human）
  - `docs/SYSTEM_MAP.md` Phase 4.1 eval_report 字段说明

## D7 — Phase 4.1 服务器 preflight 证据必备项
- Decision: preflight.txt 需包含 git 状态、FINAL 校验、torch/cuda、nvidia-smi 与 `df -h` 存储摘要。
- Rationale: 保证服务器执行环境与存储上下文可审计。
- Evidence:
  - `tools/server_preflight.py`
  - `docs/SYSTEM_MAP.md` Phase 4.1 preflight 命令与说明

## D8 — Phase 4.1 分支自洽化
- Decision: data/router-sft-v1 必须包含 Phase 4.1 runbook 依赖的脚本与证据字段。
- Rationale: 避免 AutoDL 上按文档执行时出现缺脚本的问题。
- Evidence:
  - `docs/CHANGELOG.md` Phase 4.1.4 记录
  - `tools/server_preflight.py`
  - `tools/eval_a01_sft.py`
