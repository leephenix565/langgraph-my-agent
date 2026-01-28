# Docs Index / 文档总览

本页用于定义文档分工、权威级别与导航入口；不包含操作命令与执行细节。

## 核心文档与权威级别
- `docs/SYSTEM_MAP.md`：权威级别 S0（Single Source of Truth）；运行/训练/评测命令与入口路径以此为准。
- `docs/RUNBOOK_ROUTER_SFT.md`：权威级别 S0；AutoDL 场景训练复现实操与事实证据记录。
- `docs/CHANGELOG.md`：权威级别 S0；变更记录与验收说明的唯一入口。
- `docs/A01_CONTRACT_SCHEMA_V0.md`：权威级别 S0；a01 合同 JSON schema v0 与运行态消费规则。
- `data/a01_sft/DATA_MANIFEST.md`：权威级别 S0；a01 SFT 数据证据链、FINAL 真源与归档规范。
- `docs/PROJECT_OVERVIEW.md`：权威级别 S1；对外叙事入口（路线图、指标体系、为何 SLM 更强），不包含命令细节。
- `project_analysis.md`：权威级别 S2；对当前仓库结构与流程的分析快照。
- `agent_full.md`：权威级别 S2；运行态设计与全量 Agent 说明（需与 `config/agents` 对齐）。
- `agent_profile.md`：权威级别 S2；Agent 清单与来源说明（与 `config/agents` 与 `智能体分配.xlsx` 对齐）。

## 冲突处理规则（优先级）
- 命令/路径/操作步骤冲突：以 `docs/SYSTEM_MAP.md` 与 `docs/RUNBOOK_ROUTER_SFT.md` 为准。
- 状态变更/版本记录冲突：以 `docs/CHANGELOG.md` 为准。
- 叙事/路线图/指标体系冲突：以 `docs/PROJECT_OVERVIEW.md` 为准。
- 数据真源/FINAL 产物路径冲突：以 `data/a01_sft/DATA_MANIFEST.md` 为准。

## 导航入口
- [SYSTEM_MAP（运行/训练/评测命令）](SYSTEM_MAP.md)
- [RUNBOOK_ROUTER_SFT（AutoDL 训练复现）](RUNBOOK_ROUTER_SFT.md)
- [CHANGELOG（变更记录）](CHANGELOG.md)
- [A01_CONTRACT_SCHEMA_V0（合同协议）](A01_CONTRACT_SCHEMA_V0.md)
- [PROJECT_OVERVIEW（叙事入口）](PROJECT_OVERVIEW.md)
