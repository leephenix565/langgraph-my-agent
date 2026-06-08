import { useId, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type { DagStep, DimensionGroup, WorkflowModel, WorkflowStageKey } from "../../types/workflow";

interface ResearchThoughtChainProps {
  workflow: WorkflowModel;
}

type PhaseStatus = "done" | "active" | "waiting";

interface PhaseConfig {
  key: WorkflowStageKey;
  title: string;
  summary: string;
  detail: string;
  thought: string;
}

interface PhaseView extends PhaseConfig {
  index: number;
  status: PhaseStatus;
  steps: DagStep[];
}

interface ProgressView {
  count: number;
  total: number;
  percent: number;
  label: string;
  helper: string;
}

interface EvidenceItem {
  label: string;
  value: string;
}

type DimensionSignalStatus = "waiting" | "forming" | "synthesizing" | "summarized" | "included";

interface DimensionSignalCopy {
  waiting: string;
  forming: string;
  synthesizing: string;
  summarized: string;
  included: string;
}

interface DimensionSignalConfig {
  id: string;
  title: string;
  copy: DimensionSignalCopy;
}

const PHASES: PhaseConfig[] = [
  {
    key: "planning",
    title: "问题理解",
    summary: "识别用户关注的对象、目标和约束。",
    detail: "把用户问题整理成可执行的研判任务，明确对象、目标、边界和输出偏好。",
    thought: "先把用户问题转成可执行的研判任务，明确本轮回答需要覆盖的对象、目标、边界和输出形式。",
  },
  {
    key: "evidence",
    title: "证据接入",
    summary: "整理本轮回答所需的基础材料。",
    detail: "接入公开给前端的结构化摘要，形成后续分析可引用的证据底座。",
    thought: "把问题所需的材料整理成后续阶段可引用的证据底座，先确认基础对象、关系和公开摘要。",
  },
  {
    key: "l2_analysis",
    title: "并行分析",
    summary: "从价值、市场、风险、宏观等方向并行生成线索。",
    detail: "将问题拆成多个分析视角，分别形成 public-safe 的维度线索。",
    thought: "将价值、市场、风险、宏观拆成并行视角，形成面向用户可追溯的维度线索。",
  },
  {
    key: "dimension_composite",
    title: "维度综合",
    summary: "汇总各维度流程线索并处理信号差异。",
    detail: "把价值、市场、风险、宏观流程线索收拢为回答组织依据。",
    thought: "把四类流程信号合并为回答组织依据，处理不同维度之间的差异和边界。",
  },
  {
    key: "decision",
    title: "决策生成",
    summary: "把综合画像转成回答框架。",
    detail: "将流程线索整理为结论、依据、限制和风险提示的回答结构。",
    thought: "把流程线索转成回答框架，组织结论、依据、限制和风险提示的呈现顺序。",
  },
  {
    key: "report",
    title: "文字报告输出",
    summary: "以普通 AI 回答形式输出结论、依据和限制。",
    detail: "最终文字报告已显示在上方主回答区；这里仅保留形成路径，方便追溯。",
    thought: "把结论、依据、风险和限制整理成面向用户的自然语言回答，最终报告仍回到上方主回答区。",
  },
];

const DIMENSION_ORDER: DimensionSignalConfig[] = [
  {
    id: "value",
    title: "价值维度",
    copy: {
      waiting: "等待价值相关线索形成。",
      forming: "正在整理估值、研究观点与价值信号。",
      synthesizing: "正在汇总价值维度信号与分歧。",
      summarized: "价值维度已进入结论组织。",
      included: "价值维度已纳入上方回答组织。",
    },
  },
  {
    id: "market",
    title: "市场维度",
    copy: {
      waiting: "等待市场相关线索形成。",
      forming: "正在整理价格趋势、资金行为与投资者关注度。",
      synthesizing: "正在汇总市场维度信号与分歧。",
      summarized: "市场维度已进入结论组织。",
      included: "市场维度已纳入上方回答组织。",
    },
  },
  {
    id: "risk",
    title: "风险维度",
    copy: {
      waiting: "等待风险相关线索形成。",
      forming: "正在识别价格波动、财务异常、合规事件与潜在约束。",
      synthesizing: "正在汇总风险维度信号与分歧。",
      summarized: "风险维度已进入结论组织。",
      included: "风险维度已纳入上方回答组织。",
    },
  },
  {
    id: "macro",
    title: "宏观维度",
    copy: {
      waiting: "等待宏观相关线索形成。",
      forming: "正在观察宏观环境、行业景气、商品与指数表现等外部影响。",
      synthesizing: "正在汇总宏观维度信号与分歧。",
      summarized: "宏观维度已进入结论组织。",
      included: "宏观维度已纳入上方回答组织。",
    },
  },
];

const PHASE_INDEX = new Map(PHASES.map((phase, index) => [phase.key, index]));
const USER_COPY_FORBIDDEN_TOKENS = [
  "placeholder",
  "pending_implementation",
  "runtime binding",
  "provider",
  "external endpoint",
  "raw enum",
  "workflow 快照",
  "来自公开 workflow 快照",
  "置信度",
  "目标价",
  "买入",
  "卖出建议",
  "真实分析完成",
];
const BACKEND_GENERIC_DIMENSION_SUMMARIES = new Set(["维度综合结果。", "维度综合结果"]);
const FALLBACK_EVIDENCE: Record<WorkflowStageKey, EvidenceItem[]> = {
  planning: [
    { label: "任务对象", value: "识别本轮问题关注的对象。" },
    { label: "研判目标", value: "明确用户希望得到的回答方向。" },
    { label: "输出形式", value: "组织为自然语言报告。" },
  ],
  evidence: [
    { label: "基础材料", value: "整理问题相关的公开摘要。" },
    { label: "实体关系", value: "识别公司、行业、事件等关键对象。" },
    { label: "引用底座", value: "形成后续阶段可追溯的材料基础。" },
  ],
  l2_analysis: [
    { label: "价值线索", value: "提取估值、研究观点与价值信号。" },
    { label: "市场线索", value: "观察价格趋势、资金行为与关注度。" },
    { label: "风险线索", value: "识别波动、异常、事件与潜在约束。" },
  ],
  dimension_composite: [
    { label: "流程汇总", value: "汇总四维流程信号与差异。" },
    { label: "差异处理", value: "处理不同维度之间的信号差异。" },
    { label: "输出边界", value: "保留限制条件和风险提示。" },
  ],
  decision: [
    { label: "回答框架", value: "组织结论、依据和限制顺序。" },
    { label: "风险提示", value: "把需要谨慎阅读的边界纳入回答。" },
    { label: "表达方式", value: "面向用户生成自然语言结构。" },
  ],
  report: [
    { label: "输出形式", value: "普通 AI 主回答。" },
    { label: "内容结构", value: "结论、依据、限制与风险提示。" },
    { label: "追溯位置", value: "思维链仅保留形成路径。" },
  ],
};

function stageStepIds(workflow: WorkflowModel, key: WorkflowStageKey) {
  const stage = workflow.stages.find((candidate) => candidate.key === key);
  if (stage?.stepIds.length) {
    return stage.stepIds;
  }
  return workflow.dagSteps.filter((step) => step.stage === key).map((step) => step.id);
}

function stageSteps(workflow: WorkflowModel, key: WorkflowStageKey) {
  const stepIds = stageStepIds(workflow, key);
  const byId = new Map(workflow.dagSteps.map((step) => [step.id, step]));
  const ordered = stepIds.map((stepId) => byId.get(stepId)).filter(Boolean) as DagStep[];
  if (ordered.length) {
    return ordered;
  }
  return workflow.dagSteps.filter((step) => step.stage === key);
}

function isReportComplete(workflow: WorkflowModel) {
  if (workflow.currentStage === "report") {
    return true;
  }
  const reportStepIds = stageStepIds(workflow, "report");
  return reportStepIds.length > 0 && reportStepIds.some((stepId) => workflow.completedSteps.includes(stepId));
}

function phaseStatus(workflow: WorkflowModel, key: WorkflowStageKey): PhaseStatus {
  if (isReportComplete(workflow)) {
    return "done";
  }

  const phaseIndex = PHASE_INDEX.get(key) ?? -1;
  const currentIndex = workflow.currentStage ? (PHASE_INDEX.get(workflow.currentStage) ?? -1) : -1;
  if (currentIndex >= 0 && phaseIndex >= 0) {
    if (phaseIndex < currentIndex) {
      return "done";
    }
    if (phaseIndex === currentIndex) {
      return "active";
    }
    return "waiting";
  }

  const liveStatus = workflow.liveProgress?.find((stage) => stage.key === key)?.status ?? null;
  if (liveStatus === "completed") {
    return "done";
  }
  if (liveStatus === "running" || liveStatus === "failed") {
    return "active";
  }

  const stepIds = stageStepIds(workflow, key);
  if (stepIds.length > 0 && stepIds.every((stepId) => workflow.completedSteps.includes(stepId))) {
    return "done";
  }
  if (workflow.currentStage === key) {
    return "active";
  }
  return "waiting";
}

function statusLabel(phase: PhaseView, workflow: WorkflowModel) {
  const reportComplete = isReportComplete(workflow);
  if (phase.key === "report" && reportComplete) {
    return "已完成";
  }
  if (reportComplete && phase.status === "done") {
    return "已纳入";
  }
  if (phase.status === "done") {
    return "已完成";
  }
  if (phase.status === "active") {
    return "当前阶段";
  }
  return phase.key === "report" ? "待生成" : "待处理";
}

function activePhase(phases: PhaseView[]) {
  return (
    phases.find((phase) => phase.status === "active") ??
    [...phases].reverse().find((phase) => phase.status === "done") ??
    phases[0]
  );
}

function detailSummary(phase: PhaseView, workflow: WorkflowModel) {
  if (phase.key === "report" && isReportComplete(workflow)) {
    return "最终文字报告已显示在上方主回答区。";
  }
  return phase.steps.map((step) => step.summary).filter(Boolean).slice(0, 2).join(" ") || phase.detail;
}

function dimensionTitle(group: DimensionGroup | undefined, fallback: string) {
  return group?.title ? `${fallback}` : fallback;
}

function isPublicSafeCopy(value: string | undefined | null) {
  const text = value?.trim();
  if (!text) {
    return false;
  }
  const normalized = text.toLowerCase();
  return USER_COPY_FORBIDDEN_TOKENS.every((token) => !normalized.includes(token.toLowerCase()));
}

function publicSafeOrFallback(value: string | undefined | null, fallback: string) {
  return isPublicSafeCopy(value) ? value!.trim() : fallback;
}

function dimensionSignalStatus(phase: PhaseView, reportComplete: boolean): DimensionSignalStatus {
  if (reportComplete) {
    return "included";
  }
  if (phase.key === "decision") {
    return "summarized";
  }
  if (phase.key === "dimension_composite") {
    return "synthesizing";
  }
  if (phase.key === "l2_analysis") {
    return "forming";
  }
  return "waiting";
}

function dimensionStatusLabel(status: DimensionSignalStatus) {
  const labels: Record<DimensionSignalStatus, string> = {
    waiting: "等待",
    forming: "形成中",
    synthesizing: "综合中",
    summarized: "已汇总",
    included: "已纳入",
  };
  return labels[status];
}

function canUseDimensionSummary(group: DimensionGroup | undefined, reportComplete: boolean) {
  if (!group || !isPublicSafeCopy(group.summary)) {
    return false;
  }
  if (BACKEND_GENERIC_DIMENSION_SUMMARIES.has(group.summary.trim())) {
    return false;
  }
  return reportComplete;
}

function dimensionSummary(
  group: DimensionGroup | undefined,
  copy: DimensionSignalCopy,
  reportComplete: boolean,
  status: DimensionSignalStatus,
) {
  if (!group) {
    return "该维度属于固定研判流程，当前无可展示业务摘要。";
  }
  if (canUseDimensionSummary(group, reportComplete)) {
    return group.summary.trim();
  }
  return copy[status];
}

function processEvidenceItems(phase: PhaseView, workflow: WorkflowModel): EvidenceItem[] {
  const stepItems = phase.steps
    .slice(0, 3)
    .map((step) => ({
      label: step.title,
      value: publicSafeOrFallback(step.summary, phase.detail),
    }))
    .filter((item) => item.label && item.value);

  if (stepItems.length) {
    return stepItems;
  }

  if (phase.key === "dimension_composite" && workflow.dimensionGroups.length) {
    return workflow.dimensionGroups.slice(0, 3).map((group) => ({
      label: group.title,
      value: publicSafeOrFallback(group.summary, phase.detail),
    }));
  }

  return FALLBACK_EVIDENCE[phase.key];
}

function provenanceSummary(workflow: WorkflowModel) {
  return workflow.provenance?.summary || workflow.provenanceNote || "本轮按照固定研判流程生成回答。";
}

function progressView(phases: PhaseView[], selectedPhase: PhaseView, reportComplete: boolean): ProgressView {
  const total = PHASES.length;
  const count = reportComplete ? total : Math.min(total, Math.max(1, selectedPhase.index + 1));
  const percent = Math.round((count / total) * 100);
  return {
    count,
    total,
    percent,
    label: reportComplete ? `研判流程 · ${count}/${total} 个阶段已纳入` : `研判流程 · ${count}/${total} 个阶段处理中`,
    helper: reportComplete
      ? "报告已输出，过程摘要可用于追溯回答形成路径。"
      : `${phases[count - 1]?.title ?? selectedPhase.title}正在推进，本进度仅表示固定研判流程阶段。`,
  };
}

export function ResearchThoughtChain({ workflow }: ResearchThoughtChainProps) {
  const [expanded, setExpanded] = useState(false);
  const contentId = useId();
  const phases = useMemo(
    () =>
      PHASES.map((phase, index) => ({
        ...phase,
        index,
        status: phaseStatus(workflow, phase.key),
        steps: stageSteps(workflow, phase.key),
      })),
    [workflow],
  );
  const selectedPhase = activePhase(phases);
  const selectedIndex = selectedPhase?.index ?? 0;
  const beamHeight = phases.length > 1 ? `${Math.round((selectedIndex / (phases.length - 1)) * 100)}%` : "0%";
  const evidenceItems = processEvidenceItems(selectedPhase, workflow);
  const reportComplete = isReportComplete(workflow);
  const dimensionStatus = dimensionSignalStatus(selectedPhase, reportComplete);
  const dimensions = DIMENSION_ORDER.map((dimension) => ({
    ...dimension,
    group: workflow.dimensionGroups.find((group) => group.id === dimension.id),
  }));
  const overallStatus = reportComplete ? "报告已输出" : "流程进行中";
  const progress = progressView(phases, selectedPhase, reportComplete);

  return (
    <section className="thought-chain" aria-label="研判思维链">
      <button
        type="button"
        className="thought-chain__toggle"
        aria-expanded={expanded}
        aria-controls={contentId}
        onClick={() => setExpanded((current) => !current)}
      >
        <span className="thought-chain__toggle-copy">
          <span className="thought-chain__mark" aria-hidden="true">
            链
          </span>
          <span>
            <strong>研判思维链</strong>
            <span>系统按固定研判流程组织本轮回答</span>
          </span>
        </span>
        <span className="thought-chain__toggle-meta">
          <span className={`thought-chain__status thought-chain__status--${reportComplete ? "done" : "active"}`}>
            {overallStatus}
          </span>
          <span className="thought-chain__action">{expanded ? "收起过程" : "展开过程"}</span>
        </span>
      </button>

      {expanded ? (
        <div className="thought-chain__content" id={contentId} aria-label="研判思维链详情">
          <div
            className="thought-chain__progress-band"
            style={{ "--thought-chain-progress": `${progress.percent}%` } as CSSProperties}
          >
            <div className="thought-chain__progress-copy">
              <span className="workflow-kicker">研判流程进度</span>
              <strong>{progress.label}</strong>
              <p>{progress.helper}</p>
            </div>
            <span className="thought-chain__progress-count">{progress.percent}%</span>
            <div className="thought-chain__progress-track" aria-hidden="true">
              <span />
            </div>
          </div>

          <div className="thought-chain__process-grid">
            <div className="thought-chain__rail" style={{ "--thought-chain-beam": beamHeight } as CSSProperties}>
              <div className="thought-chain__beam" aria-hidden="true" />
              <ol className="thought-chain__steps">
                {phases.map((phase) => (
                  <li className={`thought-chain__step thought-chain__step--${phase.status}`} key={phase.key}>
                    <span className="thought-chain__node" aria-hidden="true">
                      {phase.status === "done" ? "✓" : phase.index + 1}
                    </span>
                    <span className="thought-chain__step-body">
                      <strong>{phase.title}</strong>
                      <span>{phase.summary}</span>
                      <em>{statusLabel(phase, workflow)}</em>
                    </span>
                  </li>
                ))}
              </ol>
            </div>

            <div className="thought-chain__detail">
              <div className="thought-chain__detail-head">
                <div>
                  <span className="workflow-kicker">当前阶段摘要</span>
                  <h4>{selectedPhase.title}</h4>
                  <p>{detailSummary(selectedPhase, workflow)}</p>
                </div>
              </div>

              <div className="thought-chain__thought-line">
                <span className="thought-chain__thought-mark" aria-hidden="true">
                  链
                </span>
                <p>{selectedPhase.thought}</p>
              </div>

              <div className="thought-chain__evidence-strip" aria-label="阶段公开证据摘要">
                {evidenceItems.map((item) => (
                  <article className="thought-chain__evidence-card" key={`${selectedPhase.key}-${item.label}`}>
                    <small>{item.label}</small>
                    <strong>{item.value}</strong>
                  </article>
                ))}
              </div>

              <div className="thought-chain__dimension-area">
                <div className="thought-chain__section-head">
                  <strong>四维流程信号</strong>
                  <span>
                    {dimensionStatus === "waiting"
                      ? "展示回答组织中的维度线索，不代表实时市场数据或投资建议"
                      : "随研判阶段逐步纳入回答组织"}
                  </span>
                </div>
                <div className="thought-chain__dimensions">
                  {dimensions.map((dimension) => (
                    <article
                      className={`thought-chain__dimension thought-chain__dimension--${dimension.id}${
                        dimensionStatus === "waiting" ? " thought-chain__dimension--waiting" : ""
                      }`}
                      key={dimension.id}
                    >
                      <strong>{dimensionTitle(dimension.group, dimension.title)}</strong>
                      <p>
                        {dimensionStatus === "waiting"
                          ? "等待分析结果"
                          : dimensionSummary(dimension.group, dimension.copy, reportComplete, dimensionStatus)}
                      </p>
                      <span className="thought-chain__dimension-status">{dimensionStatusLabel(dimensionStatus)}</span>
                    </article>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <p className="thought-chain__provenance">{provenanceSummary(workflow)}</p>
        </div>
      ) : null}
    </section>
  );
}
