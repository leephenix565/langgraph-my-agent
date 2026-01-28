# Project Overview: SLM Router + SLM a01 for Layered Multi-Agent Orchestration

> 本文为第三人称叙事入口，不包含运行/训练/评测命令；操作细节以 `docs/SYSTEM_MAP.md` 与 `docs/RUNBOOK_ROUTER_SFT.md` 为准。

## 1. 项目定位与长期目标（第三人称）
- 该项目将 Router 与 a01 视为系统骨架模块，并优先训练为 SLM；具体分析类 agents 由不同开发者维护，可接入商业 API 或本地模型。
- 长期目标是构建“可训练、可评测、可回归、可复现”的编排能力，而不是单次回答“看起来更聪明”。
- 骨架能力与执行能力解耦评估：Router/a01 负责协议合规与任务分解，agents 负责领域输出质量。

## 2. 当前进展（截至 2026-01-23）
- Router-SFT 已完成闭环：数据治理（strict + canonical JSON）、completion-only、QLoRA + LoRA、HF preds JSON 规范化、repro gate。
- 结论：合规性与可执行性稳定，但 L2/L3 选人一致性与质量指标仍需迭代。
- 下一步主线：a01 合同 schema v0（宪法级协议 + 校验器）与 a01-SFT；Judge 作为端到端评测基础设施。

## 3. 为什么 SLM 微调优于直接商业 API（因果链）
- 商业 API 直推的问题：输出稳定性不足、协议合规难控、成本与供应方更新带来回归风险。
- SLM 的优势来自训练对象选对：训练“路由与合同等骨架能力”，而非训练金融百科或通用知识。
- 明确的训练与工程措施使其更稳：
  - strict + canonical JSON 标签
  - completion-only masking（只学习 JSON completion）
  - QLoRA 量化训练必须挂 LoRA
  - 推理输出规范化以匹配 parser/eval（抽取首个 JSON + compact）
  - 回归门禁（repro + regression eval）

## 4. 推进计划（里程碑 + DoD）
- M1：a01 合同 JSON schema v0（宪法级协议 + 校验器）
- M2：a01-SFT 数据集 v0（strict/canonical/分桶元数据）
- M3：a01 QLoRA + completion-only 训练闭环（merged 可推理 + 评测）
- M4：LLM Judge + 人工校准（gold set、多 trial、rubric graders）
- M5：双线回归门禁固化（路由指标 + 推理指标 + 成本/延迟）
- 注：多候选/重评分属于可选增强路线，目前待定，不作为硬依赖

## 5. 指标体系：路由指标 vs 端到端推理指标
### 5.1 Router / 路由指标（L0 硬栅栏 + L1 质量 + 稳定性/成本）
- L0：valid_json_rate、parse_ok_rate、used_default_plan_rate、constraint_violation_rate、l2_truncated、filtered_agents
- L1：mode_acc、selected_jaccard（按层，重点 L2/L3）、coverage_score、redundancy_penalty
- 稳定性：repro gate、paraphrase stability、drift monitor
- 成本：activated_agents、token_proxy、latency_proxy

### 5.2 End-to-End / 推理质量指标（LLM judge + 人工校准）
- Rubric（建议 6 维 0–2 分）：覆盖度、证据链、内部一致性、不确定性与风险披露、可执行性、合规边界
- 校准：gold set、judge 多 trial 方差、与人工一致性、失败标签体系
- tracked metrics：turns、toolcalls、tokens、latency

## 6. Anthropic 方法论参考（官方链接，原样放入）
```
Building effective agents: https://www.anthropic.com/research/building-effective-agents
How we built our multi-agent research system: https://www.anthropic.com/engineering/multi-agent-research-system
Effective harnesses for long-running agents: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
Demystifying evals for AI agents: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
```

## 7. 风险与对策（面向汇报）
- judge 偏差与 prompt hack：gold set 校准 + 多 trial + 必要时多 judge。
- agents 后端不统一：骨架质量（Router/a01）与执行质量解耦评估。
- 多解问题：exact_match → 集合/类别指标 + 成本维度。
