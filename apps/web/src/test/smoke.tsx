import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import React from "react";
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../app/App";
import { AssistantAnswerCard } from "../components/chat/AssistantAnswerCard";
import { UserBubble } from "../components/chat/UserBubble";
import { Composer } from "../components/shell/Composer";
import { agentNameLabel } from "../content/zh-CN";
import { AGENT_CATALOG } from "../mocks/agents";
import { TRANSCRIPTS_BY_SESSION } from "../mocks/transcript";
import { createWorkflowVariant } from "../mocks/workflow";
import type { PublicTurn, RoutingRequestModel, StructuredInputModel } from "../types/chat";
import type { WorkflowModel, WorkflowStageKey, WorkflowStageStatus } from "../types/workflow";
import { composeStructuredPrompt, parseStructuredUserTurn, toStructuredInputModel } from "../utils/structuredInput";

const dom = new JSDOM("<!doctype html><html><body></body></html>", {
  url: "http://localhost/",
});

globalThis.window = dom.window as unknown as Window & typeof globalThis;
globalThis.document = dom.window.document;
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.HTMLInputElement = dom.window.HTMLInputElement;
globalThis.HTMLTextAreaElement = dom.window.HTMLTextAreaElement;
globalThis.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);

Object.defineProperty(globalThis, "navigator", {
  configurable: true,
  value: dom.window.navigator,
});

Object.defineProperty(globalThis.HTMLElement.prototype, "attachEvent", {
  configurable: true,
  value() {},
});

Object.defineProperty(globalThis.HTMLElement.prototype, "detachEvent", {
  configurable: true,
  value() {},
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function ndjsonResponse(events: unknown[], delayMs = 8) {
  const encoder = new TextEncoder();
  let index = 0;
  const stream = new ReadableStream({
    async pull(controller) {
      if (index >= events.length) {
        controller.close();
        return;
      }
      controller.enqueue(encoder.encode(`${JSON.stringify(events[index])}\n`));
      index += 1;
      if (delayMs > 0) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    },
  });

  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "application/x-ndjson" },
  });
}

function installFetchMock(handler: (url: string, init?: RequestInit) => Promise<Response>) {
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    return handler(url, init);
  }) as typeof fetch;
}

function degradedHealthPayload() {
  return {
    status: "ok",
    apiVersion: "phase-r5",
    overallStatus: "degraded",
    checkpointer: {
      enabled: false,
      mode: "none",
      status: "disabled",
      code: "checkpointer_disabled",
      hint: "设置 REACT_AGENT_CHECKPOINTER=memory 或 sqlite 可启用持久连续性。",
    },
    continuityDefault: "replay",
    runtime: { status: "ready", code: "runtime_ready" },
    providerEnv: { status: "configured", code: "provider_env_configured" },
    searchEnv: {
      status: "missing",
      code: "search_env_missing",
      hint: "导入 react_agent.graph 前设置 TAVILY_API_KEY。",
    },
    store: "json-file",
  };
}

function threadSummary(title: string, preview: string) {
  return {
    id: "thread-live-1",
    title,
    updatedAt: "2026-04-04 18:06",
    preview,
    finalSource: "reset_skeleton",
    phase: "在线",
    continuityMode: "replay",
  };
}

function assistantTurn(id: string, answer: string): PublicTurn {
  return {
    id,
    role: "assistant",
    text: answer,
    createdAt: "2026-04-04 18:06",
    runId: `run-${id}`,
    continuityMode: "replay",
    answerCard: {
      answer,
      finalSource: "reset_skeleton",
      citations: [
        {
          label: "Fixed DAG bundle",
          note: "系统按照固定研判流程组织本轮分析，包括问题理解、信息整理、并行分析、维度综合与报告生成。",
        },
        { label: "User question", note: "围绕你提出的问题进行结构化梳理。" },
        { label: "Workflow", note: "如需查看过程，可展开“研判思维链”。" },
      ],
      evidenceCards: [{ title: "分析框架", note: "系统按照固定研判流程组织本轮分析。" }],
      evidenceCount: 3,
    },
    workflow: createWorkflowVariant(id),
  };
}

function runningWorkflow(stage: WorkflowStageKey): WorkflowModel {
  const workflow = createWorkflowVariant(`running-${stage}`);
  const stageOrder: WorkflowStageKey[] = ["planning", "evidence", "l2_analysis", "dimension_composite", "decision", "report"];
  const stageIndex = stageOrder.indexOf(stage);
  const completedStageKeys = new Set(stageOrder.slice(0, Math.max(stageIndex, 0)));
  const completedSteps = workflow.stages
    .filter((candidate) => completedStageKeys.has(candidate.key))
    .flatMap((candidate) => candidate.stepIds);

  return {
    ...workflow,
    currentStage: stage,
    completedSteps,
    liveProgress: workflow.stages.map((candidate) => {
      const candidateIndex = stageOrder.indexOf(candidate.key);
      let status: WorkflowStageStatus = "waiting";
      if (candidateIndex < stageIndex) {
        status = "completed";
      } else if (candidate.key === stage) {
        status = "running";
      }
      return { key: candidate.key, title: candidate.title, status };
    }),
  };
}

function assistantTurnWithWorkflow(id: string, answer: string, workflow: WorkflowModel): PublicTurn {
  const turn = assistantTurn(id, answer);
  return {
    ...turn,
    text: answer,
    answerCard: {
      ...turn.answerCard!,
      answer,
    },
    workflow,
  };
}

function runAgentCatalogContractChecks() {
  const allAgents = AGENT_CATALOG.layers.flatMap((layer) => layer.agents);
  assert.equal(AGENT_CATALOG.totals.configCount, 27);
  assert.equal(AGENT_CATALOG.totals.runtimeCount, 27);
  assert.deepEqual(AGENT_CATALOG.totals.disabledIds, []);
  assert.equal(AGENT_CATALOG.disabledAgents.length, 0);
  assert.equal(allAgents.length, 27);
  assert.equal(allAgents.some((agent) => /^a\d{2}_/.test(agent.id)), false);
  assert.ok(allAgents.find((agent) => agent.id === "sentiment_company_radar"));
  assert.equal(allAgents.some((agent) => agent.id === "value_financial_analysis"), false);
  assert.equal(agentNameLabel("macro_commodity_pricing"), "商品定价分析");
}

const forbiddenSerializedTokens = [
  "layerPlan",
  "layerMode",
  "agentSteps",
  "fusionSteps",
  "default_url",
  "env_var",
  "secret",
  "secrets",
  "api_key",
  "apiKey",
  "OPENAI_API_KEY",
  "TAVILY_API_KEY",
];

const forbiddenUiTokens = [
  "layerPlan",
  "layerMode",
  "agentSteps",
  "fusionSteps",
  "default_url",
  "env_var",
  "secret",
  "secrets",
  "api_key",
  "apiKey",
  "OPENAI_API_KEY",
  "TAVILY_API_KEY",
  "mainline",
  "baseline",
  "fused",
  "Fusion",
  "chain-of-thought",
];

const forbiddenDefaultUserCopyTokens = [
  "fixture",
  "roster",
  "transcript",
  "市场维度包含企业舆情雷达",
  "风险路径不读取企业舆情雷达",
  "固定 DAG 数据组",
  "固定 DAG 数据包",
  "检查器元数据",
  "No provider",
  "external endpoint",
  "reset_skeleton",
  "chain-of-thought",
];

function assertNoForbiddenSerializedTokens(value: string) {
  for (const token of forbiddenSerializedTokens) {
    assert.equal(value.includes(token), false, `Unexpected serialized token: ${token}`);
  }
}

function assertNoForbiddenUiTokens(value: string | null | undefined) {
  const text = value ?? "";
  for (const token of forbiddenUiTokens) {
    assert.equal(text.includes(token), false, `Unexpected UI token: ${token}`);
  }
}

function assertNoForbiddenDefaultUserCopy(value: string | null | undefined) {
  const text = value ?? "";
  for (const token of forbiddenDefaultUserCopyTokens) {
    assert.equal(text.includes(token), false, `Unexpected default user copy token: ${token}`);
  }
}

function runWorkflowFixtureContractChecks() {
  const workflow = createWorkflowVariant("contract");
  const serialized = JSON.stringify(workflow);
  assert.equal(workflow.schema, "workflow_snapshot_v2");
  assert.equal(workflow.finalSource, "reset_skeleton");
  assert.deepEqual(
    workflow.stages.map((stage) => stage.key),
    ["planning", "evidence", "l2_analysis", "dimension_composite", "decision", "report"],
  );
  assert.deepEqual(workflow.stages[1].stepIds, ["financial_data_service", "entity_relation_extractor"]);
  assert.equal(workflow.executionBatches.length, 6);
  assert.deepEqual(workflow.executionBatches[1], ["financial_data_service", "entity_relation_extractor"]);
  assert.ok(workflow.executionBatches[2].includes("sentiment_company_radar"));
  assert.ok(workflow.executionBatches[3].includes("macro_composite"));
  assert.deepEqual(
    workflow.dimensionGroups.map((group) => group.id),
    ["value", "market", "risk", "macro"],
  );
  assert.ok(workflow.dimensionGroups.find((group) => group.id === "market")?.stepIds.includes("sentiment_company_radar"));
  assert.equal(workflow.dimensionGroups.find((group) => group.id === "risk")?.stepIds.includes("sentiment_company_radar"), false);
  assert.equal(workflow.stepResults.route_planner?.runtime_kind, "deterministic_system");
  assert.equal(workflow.stepResults.financial_data_service?.runtime_kind, "external_http_candidate");
  assert.equal(workflow.stepResults.entity_relation_extractor?.runtime_kind, "pending_placeholder");
  assert.equal(workflow.stepResults.value_traditional_valuation?.runtime_kind, "external_http_candidate");
  assert.equal(workflow.stepResults.sentiment_company_radar?.runtime_kind, "pending_placeholder");
  assert.equal(workflow.provenance?.selectedRoutingRequested, false);
  assert.deepEqual(workflow.provenance?.selectedDimensions, []);
  assert.equal(workflow.provenance?.providerRouterEnabled, false);
  assert.equal(workflow.provenance?.providerRouterInvoked, false);
  assertNoForbiddenSerializedTokens(serialized);
}

function runTranscriptBoundaryChecks() {
  for (const turns of Object.values(TRANSCRIPTS_BY_SESSION)) {
    for (const turn of turns) {
      assert.ok(turn.role === "user" || turn.role === "assistant");
      if (turn.role === "assistant") {
        assert.equal(turn.answerCard?.confidence, undefined);
      }
    }
  }
}

function runStructuredInputHelperChecks() {
  const compiled = composeStructuredPrompt({
    task: "Summarize the earnings call risk profile.",
    context: "Public filings already cover the revenue mix and market positioning.",
    materialsText:
      "Material one: management said pricing pressure is still elevated.\n\nMaterial two: policy notes emphasize subsidy discipline.",
    urlReferencesText: "https://example.com/policy-brief\nhttps://example.com/company-update",
    constraints: "Use only public information.",
    outputPreference: "Write in Chinese with the conclusion first.",
  });

  const parsed = parseStructuredUserTurn(compiled);
  assert.ok(parsed);
  assert.equal(parsed?.task, "Summarize the earnings call risk profile.");
  assert.equal(parsed?.materials.length, 2);
  assert.equal(parsed?.urlReferences.length, 2);
  assert.equal(parsed?.urlReferences[0], "https://example.com/policy-brief");

  const mirrored = toStructuredInputModel({
    task: "Summarize the earnings call risk profile.",
    context: "Public filings already cover the revenue mix and market positioning.",
    materialsText:
      "Material one: management said pricing pressure is still elevated.\n\nMaterial two: policy notes emphasize subsidy discipline.",
    urlReferencesText: "https://example.com/policy-brief\nhttps://example.com/company-update",
    constraints: "Use only public information.",
    outputPreference: "Write in Chinese with the conclusion first.",
  });
  assert.ok(mirrored);
  assert.deepEqual(mirrored?.urlReferences, [
    "https://example.com/policy-brief",
    "https://example.com/company-update",
  ]);
}

async function runUserBubbleStructuredRenderChecks() {
  const view = render(
    <UserBubble
      turn={{
        id: "user-typed-1",
        role: "user",
        text: "Summarize the risk profile.",
        createdAt: "2026-04-04 18:10",
        structuredInput: {
          task: "Summarize the risk profile.",
          materials: ["Material one", "Material two"],
          urlReferences: ["https://example.com/policy-brief", "https://example.com/company-update"],
        },
      }}
    />,
  );

  assert.ok(view.getByText("Material one"));
  assert.equal(
    view.getByRole("link", { name: "https://example.com/policy-brief" }).getAttribute("href"),
    "https://example.com/policy-brief",
  );
  cleanup();
}

async function runAssistantRenderChecks() {
  const markdownAnswer = [
    "### 市场摘要",
    "",
    "这段内容包含 **重点判断** 和 *补充说明*。",
    "",
    "- 第一项",
    "- 第二项",
    "",
    "保留 `run_id` 字段用于调试。",
  ].join("\n");

  const view = render(<AssistantAnswerCard turn={assistantTurn("assistant-markdown-1", markdownAnswer)} />);
  const article = view.getByRole("article");
  assert.equal(view.queryByText("### 市场摘要"), null);
  assert.ok(view.getByRole("heading", { level: 3, name: "市场摘要" }));
  assert.ok(article.querySelector("strong"));
  assert.ok(article.querySelector("em"));
  assert.ok(article.textContent?.includes("研判流程"));
  assert.ok(article.textContent?.includes("研判思维链"));
  assert.ok(article.textContent?.includes("系统按固定研判流程组织本轮回答"));
  assert.ok(article.textContent?.includes("技术流程详情"));
  assert.ok(article.textContent?.includes("展开技术详情"));
  assert.ok(article.textContent?.includes("研判依据"));
  assert.ok(article.textContent?.includes("分析框架"));
  assert.ok(article.textContent?.includes("用户问题"));
  assert.ok(article.textContent?.includes("流程记录"));
  assert.equal(article.textContent?.includes("执行批次"), false);
  assert.equal(article.textContent?.includes("步骤结果详情"), false);
  assert.equal(article.textContent?.includes("运行方式"), false);
  assert.equal(article.textContent?.includes("external_http_candidate"), false);
  assert.equal(article.textContent?.includes("external_candidate_disabled"), false);
  assert.equal(article.textContent?.includes("pending_implementation"), false);
  assert.equal(article.textContent?.includes("待实现"), false);
  assertNoForbiddenDefaultUserCopy(article.textContent);
  const thoughtChainToggle = view.getByRole("button", { name: /研判思维链/ });
  assert.equal(thoughtChainToggle.getAttribute("aria-expanded"), "false");
  assert.equal(view.queryByLabelText("研判思维链详情"), null);
  fireEvent.click(thoughtChainToggle);
  assert.equal(thoughtChainToggle.getAttribute("aria-expanded"), "true");
  const thoughtChainDetail = view.getByLabelText("研判思维链详情");
  for (const stageTitle of ["问题理解", "证据接入", "并行分析", "维度综合", "决策生成", "文字报告输出"]) {
    assert.ok(thoughtChainDetail.textContent?.includes(stageTitle), `Missing thought-chain stage: ${stageTitle}`);
  }
  assert.ok(thoughtChainDetail.textContent?.includes("当前阶段摘要"));
  assert.ok(thoughtChainDetail.textContent?.includes("四维流程信号"));
  assert.ok(thoughtChainDetail.textContent?.includes("研判流程进度"));
  assert.ok(thoughtChainDetail.textContent?.includes("6/6"));
  assert.ok(thoughtChainDetail.textContent?.includes("100%"));
  assert.ok(thoughtChainDetail.textContent?.includes("报告已输出"));
  assert.ok(thoughtChainDetail.textContent?.includes("最终文字报告已显示在上方主回答区。"));
  assert.ok(thoughtChainDetail.textContent?.includes("以普通 AI 回答形式输出结论、依据和限制。"));
  for (const stageTitle of ["并行分析", "维度综合", "决策生成"]) {
    const stageNode = Array.from(thoughtChainDetail.querySelectorAll(".thought-chain__step")).find((node) =>
      node.textContent?.includes(stageTitle),
    );
    assert.ok(stageNode, `Missing report-complete thought-chain stage node: ${stageTitle}`);
    assert.equal(stageNode.textContent?.includes("待执行"), false, `Unexpected waiting status for ${stageTitle}`);
    assert.equal(stageNode.textContent?.includes("待处理"), false, `Unexpected waiting status for ${stageTitle}`);
    assert.equal(stageNode.textContent?.includes("待生成"), false, `Unexpected waiting status for ${stageTitle}`);
    assert.ok(
      stageNode.textContent?.includes("已纳入") || stageNode.textContent?.includes("已完成"),
      `Expected completed/included status for ${stageTitle}`,
    );
  }
  for (const dimensionTitle of ["价值维度", "市场维度", "风险维度", "宏观维度"]) {
    assert.ok(thoughtChainDetail.textContent?.includes(dimensionTitle), `Missing user-facing dimension title: ${dimensionTitle}`);
  }
  for (const dimensionCopy of [
    "价值维度已纳入上方回答组织。",
    "市场维度已纳入上方回答组织。",
    "风险维度已纳入上方回答组织。",
    "宏观维度已纳入上方回答组织。",
  ]) {
    assert.ok(thoughtChainDetail.textContent?.includes(dimensionCopy), `Missing report-complete dimension copy: ${dimensionCopy}`);
  }
  for (const rawToken of [
    "PDF",
    "PPTX",
    "DOCX",
    "来自公开 workflow 快照",
    "raw provider",
    "fake confidence",
    "置信度 72%",
    "目标价",
    "买入",
    "卖出建议",
    "真实分析完成",
    "placeholder",
    "pending_implementation",
    "provider",
    "external endpoint",
    "runtime binding",
    "raw enum",
  ]) {
    assert.equal(thoughtChainDetail.textContent?.includes(rawToken), false, `Unexpected thought-chain token: ${rawToken}`);
  }
  assert.equal(thoughtChainDetail.textContent?.includes("external_http_candidate"), false);
  assert.equal(thoughtChainDetail.textContent?.includes("endpoint"), false);
  assertNoForbiddenUiTokens(thoughtChainDetail.textContent);

  const technicalToggle = view.getByRole("button", { name: /技术流程详情/ });
  assert.equal(technicalToggle.getAttribute("aria-expanded"), "false");
  assert.equal(view.queryByLabelText("固定 DAG 研判流程详情"), null);
  fireEvent.click(technicalToggle);
  assert.equal(technicalToggle.getAttribute("aria-expanded"), "true");
  assert.ok(view.getByLabelText("固定 DAG 研判流程详情"));
  assert.ok(view.getByText("阶段时间线"));
  assert.ok(view.getAllByText("路径规划器").length >= 1);
  assert.ok(view.getByText("执行批次"));
  assert.ok(view.getByText("维度分组"));
  assert.ok(view.getByText("流程步骤列表"));
  assert.ok(view.getByText("步骤结果详情"));
  assert.ok(view.getByText("最终来源与溯源"));
  assert.ok(view.getAllByText("固定研判流程").length >= 1);
  assert.ok(view.getAllByText((content) => content.includes("价值维度已纳入上方回答组织")).length >= 1);
  assert.ok(view.getAllByText((content) => content.includes("市场维度已纳入上方回答组织")).length >= 1);
  assert.ok(view.getAllByText((content) => content.includes("风险维度已纳入上方回答组织")).length >= 1);
  assert.ok(view.getAllByText((content) => content.includes("宏观维度已纳入上方回答组织")).length >= 1);

  assert.ok(view.getByText("当前步骤"));
  assert.ok(view.getByText("运行方式"));
  assert.ok(view.getAllByText("固定流程").length >= 1);
  assert.ok(view.getAllByText("deterministic_system").length >= 1);
  assert.ok(article.textContent?.includes("deterministic_system"));
  assert.ok(article.textContent?.includes("deterministic_skeleton"));
  assert.ok(view.getByText("接入状态"));
  assert.ok(view.getAllByText("否").length >= 2);

  fireEvent.click(view.getByRole("button", { name: /金融数据服务/ }));
  assert.equal(view.getByRole("button", { name: /金融数据服务/ }).getAttribute("aria-pressed"), "true");
  assert.ok(article.textContent?.includes("financial_data_service"));
  assert.ok(view.getByText("可接入连接"));
  assert.ok(view.getByText("external_http_candidate"));
  assert.ok(article.textContent?.includes("external_http_candidate"));
  assert.ok(view.getByText("高级连接未启用"));
  assert.ok(view.getByText("external_candidate_disabled"));
  assert.ok(article.textContent?.includes("external_candidate_disabled"));
  assert.ok(view.getByText("高级连接处于关闭状态，本轮使用本地流程。"));

  fireEvent.click(view.getByRole("button", { name: /传统企业估值/ }));
  assert.equal(view.getByRole("button", { name: /传统企业估值/ }).getAttribute("aria-pressed"), "true");
  assert.ok(view.getByText("单体智能体输入"));
  assert.ok(article.textContent?.includes("cautious_positive"));
  assert.ok(article.textContent?.includes("估值维度给出偏积极但需复核的结构化信号。"));

  fireEvent.click(view.getByRole("button", { name: /价值综合/ }));
  assert.equal(view.getByRole("button", { name: /价值综合/ }).getAttribute("aria-pressed"), "true");
  assert.ok(view.getByText("综合智能体输入"));
  assert.ok(view.getByText("成员"));
  assert.ok(article.textContent?.includes("价值综合智能体汇总了估值维度成员信号。"));

  fireEvent.click(view.getByRole("button", { name: /企业舆情雷达/ }));
  assert.equal(view.getByRole("button", { name: /企业舆情雷达/ }).getAttribute("aria-pressed"), "true");
  assert.ok(article.textContent?.includes("pending_placeholder"));
  assert.ok(view.getAllByText("待接入").length >= 1);
  assert.ok(view.getAllByText("pending_implementation").length >= 1);
  assert.ok(article.textContent?.includes("pending_implementation"));
  assert.ok(view.getByText("企业舆情雷达仍是待接入流程节点，默认用户面仅展示流程线索。"));

  for (const oldCopy of ["Stage timeline", "Execution batches", "Dimension groups", "Step result metadata"]) {
    assert.equal(article.textContent?.includes(oldCopy), false, `Unexpected old workflow copy: ${oldCopy}`);
  }

  assertNoForbiddenUiTokens(article.textContent);
  cleanup();
}

async function runThoughtChainDynamicStageChecks() {
  const l2View = render(
    <AssistantAnswerCard
      turn={assistantTurnWithWorkflow("assistant-running-l2", "正在协作…", runningWorkflow("l2_analysis"))}
    />,
  );
  const l2Article = l2View.getByLabelText("系统回答卡片");
  assert.ok(l2View.getByRole("heading", { level: 3, name: "正在组织研判答案" }));
  assert.ok(l2Article.textContent?.includes("研判中，最终文字报告将在流程完成后直接出现在这里。"));
  assert.ok(l2Article.textContent?.includes("并行分析"));
  assert.equal(l2Article.textContent?.includes("### 市场摘要"), false);

  const l2Toggle = l2View.getByRole("button", { name: /研判思维链/ });
  fireEvent.click(l2Toggle);
  const l2Detail = l2View.getByLabelText("研判思维链详情");
  const l2StageNode = Array.from(l2Detail.querySelectorAll(".thought-chain__step")).find((node) =>
    node.textContent?.includes("并行分析"),
  );
  const decisionStageNode = Array.from(l2Detail.querySelectorAll(".thought-chain__step")).find((node) =>
    node.textContent?.includes("决策生成"),
  );
  assert.ok(l2StageNode);
  assert.ok(decisionStageNode);
  assert.ok(l2StageNode.textContent?.includes("当前阶段"));
  assert.ok(decisionStageNode.textContent?.includes("待处理"));
  assert.ok(l2Detail.textContent?.includes("研判流程 · 3/6 个阶段处理中"));
  assert.ok(l2Detail.textContent?.includes("四维流程信号"));
  assert.ok(l2Detail.textContent?.includes("形成中"));
  assert.ok(l2Detail.textContent?.includes("正在整理估值、研究观点与价值信号。"));
  assert.equal(l2Detail.textContent?.includes("已纳入"), false);
  for (const rawToken of ["pending_implementation", "placeholder", "provider", "external endpoint", "runtime binding"]) {
    assert.equal(l2Detail.textContent?.includes(rawToken), false, `Unexpected running thought-chain token: ${rawToken}`);
  }
  cleanup();

  const dimensionView = render(
    <AssistantAnswerCard
      turn={assistantTurnWithWorkflow("assistant-running-dimension", "正在协作…", runningWorkflow("dimension_composite"))}
    />,
  );
  const dimensionArticle = dimensionView.getByLabelText("系统回答卡片");
  assert.ok(dimensionView.getByRole("heading", { level: 3, name: "正在组织研判答案" }));
  assert.ok(dimensionArticle.textContent?.includes("维度综合"));
  assert.ok(dimensionArticle.textContent?.includes("正在汇总四维流程信号并处理差异。"));
  const dimensionToggle = dimensionView.getByRole("button", { name: /研判思维链/ });
  fireEvent.click(dimensionToggle);
  const dimensionDetail = dimensionView.getByLabelText("研判思维链详情");
  const dimensionStageNode = Array.from(dimensionDetail.querySelectorAll(".thought-chain__step")).find((node) =>
    node.textContent?.includes("维度综合"),
  );
  const reportStageNode = Array.from(dimensionDetail.querySelectorAll(".thought-chain__step")).find((node) =>
    node.textContent?.includes("文字报告输出"),
  );
  assert.ok(dimensionStageNode);
  assert.ok(reportStageNode);
  assert.ok(dimensionStageNode.textContent?.includes("当前阶段"));
  assert.ok(reportStageNode.textContent?.includes("待生成"));
  assert.ok(dimensionDetail.textContent?.includes("研判流程 · 4/6 个阶段处理中"));
  assert.ok(dimensionDetail.textContent?.includes("四维流程信号"));
  assert.ok(dimensionDetail.textContent?.includes("综合中"));
  assert.ok(dimensionDetail.textContent?.includes("正在汇总价值维度信号与分歧。"));
  assert.equal(dimensionDetail.textContent?.includes("报告已输出"), false);
  for (const rawToken of ["pending_implementation", "placeholder", "provider", "external endpoint", "runtime binding"]) {
    assert.equal(dimensionDetail.textContent?.includes(rawToken), false, `Unexpected dimension thought-chain token: ${rawToken}`);
  }
  cleanup();

  const evidenceView = render(
    <AssistantAnswerCard
      turn={assistantTurnWithWorkflow("assistant-running-evidence", "正在协作…", runningWorkflow("evidence"))}
    />,
  );
  const evidenceToggle = evidenceView.getByRole("button", { name: /研判思维链/ });
  fireEvent.click(evidenceToggle);
  const evidenceDetail = evidenceView.getByLabelText("研判思维链详情");
  assert.ok(evidenceDetail.textContent?.includes("研判流程 · 2/6 个阶段处理中"));
  assert.ok(evidenceDetail.textContent?.includes("不代表实时市场数据或投资建议"));
  assert.ok(evidenceDetail.textContent?.includes("等待分析结果"));
  assert.equal(evidenceDetail.textContent?.includes("已纳入"), false);
  cleanup();
}

async function runComposerLengthLimitChecks() {
  const user = userEvent.setup({ document: dom.window.document });
  let submitCount = 0;
  const view = render(<Composer maxMessageChars={10} onSubmit={() => { submitCount += 1; }} />);
  const form = view.container.querySelector("form") as HTMLFormElement;
  const taskInput = view.container.querySelector("#chat-composer") as HTMLTextAreaElement;
  const sendButton = view.container.querySelector(".composer__submit") as HTMLButtonElement;

  await user.click(taskInput);
  await user.type(taskInput, "exceeds-limit");
  await waitFor(() => {
    assert.equal(sendButton.disabled, true);
    assert.ok(view.getByText("输入过长，请缩短后再试。"));
  });
  form.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
  assert.equal(submitCount, 0);

  await user.clear(taskInput);
  await user.type(taskInput, "Normal");
  await waitFor(() => {
    assert.equal(sendButton.disabled, false);
  });
  form.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
  assert.equal(submitCount, 1);
  cleanup();
}

async function runStreamingSuccessScenario() {
  dom.reconfigure({ url: "http://localhost/" });
  const user = userEvent.setup({ document: dom.window.document });
  const sentPayloads: Array<{
    text: string;
    structuredInput?: StructuredInputModel;
    routing?: RoutingRequestModel | null;
    hasRouting: boolean;
  }> = [];
  let finalRoles: string[] = [];

  const createdThread = {
    thread: threadSummary("新会话", "等待第一条消息。"),
    turns: [],
  };

  installFetchMock(async (url, init) => {
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/health")) {
      return jsonResponse(degradedHealthPayload());
    }
    if (url.endsWith("/api/threads") && method === "GET") {
      return jsonResponse({ threads: [] });
    }
    if (url.endsWith("/api/threads") && method === "POST") {
      return jsonResponse(createdThread);
    }
    if (url.endsWith("/api/agents") && method === "GET") {
      return jsonResponse(AGENT_CATALOG);
    }
    if (url.endsWith("/api/threads/thread-live-1/messages/stream") && method === "POST") {
      const payload = JSON.parse(String(init?.body ?? "{}")) as {
        text?: string;
        structuredInput?: StructuredInputModel;
        routing?: RoutingRequestModel | null;
      };
      sentPayloads.push({
        text: payload.text ?? "",
        structuredInput: payload.structuredInput,
        routing: payload.routing,
        hasRouting: "routing" in payload,
      });
      const answer = "简短实时摘要，先给结论。";
      const finalTurns: PublicTurn[] = [
        {
          id: "user-live-1",
          role: "user",
          text: payload.text ?? "",
          createdAt: "2026-04-04 18:05",
          structuredInput: payload.structuredInput,
        },
        assistantTurn("assistant-live-1", answer),
      ];
      finalRoles = finalTurns.map((turn) => turn.role);
      return ndjsonResponse(
        [
          {
            type: "run.started",
            data: { threadId: "thread-live-1", continuityMode: "replay" },
          },
          {
            type: "workflow.stage",
            data: {
              currentStage: "l2_analysis",
              stages: [
                { key: "planning", title: "规划", status: "completed" },
                { key: "evidence", title: "证据接入", status: "completed" },
                { key: "l2_analysis", title: "L2 分析", status: "running" },
                { key: "dimension_composite", title: "维度综合", status: "waiting" },
                { key: "decision", title: "决策", status: "waiting" },
                { key: "report", title: "报告", status: "waiting" },
              ],
            },
          },
          {
            type: "workflow.snapshot",
            data: {
              workflow: createWorkflowVariant("stream"),
              runId: "run-stream-1",
              continuityMode: "replay",
            },
          },
          {
            type: "answer.final",
            data: {
              response: {
                thread: threadSummary("市场风险摘要", answer),
                assistantTurn: assistantTurn("assistant-live-1", answer),
                turns: finalTurns,
              },
            },
          },
        ],
        16,
      );
    }

    return jsonResponse(
      { detail: { code: "unhandled_request", message: `Unhandled request: ${method} ${url}`, category: "request" } },
      500,
    );
  });

  const view = render(<App />);

  await waitFor(() => {
    assert.equal((view.container.querySelector("#chat-composer") as HTMLTextAreaElement).disabled, false);
  });
  assert.ok(view.getByText("开始一次资本市场研判"));
  assert.ok(view.getByRole("button", { name: "总结电动车公司的风险画像" }));

  const taskInput = view.container.querySelector("#chat-composer") as HTMLTextAreaElement;
  await user.type(taskInput, "Summarize the market risk profile.");
  await waitFor(() => {
    assert.equal((view.container.querySelector(".composer__submit") as HTMLButtonElement).hasAttribute("disabled"), false);
  });
  await user.click(view.container.querySelector(".composer__submit") as HTMLButtonElement);

  await waitFor(() => {
    assert.ok(view.getByText("简短实时摘要，先给结论。"));
  });
  assert.ok(view.container.textContent?.includes("研判思维链"));
  assert.ok(view.container.textContent?.includes("技术流程详情"));
  assert.ok(view.container.textContent?.includes("展开技术详情"));
  assert.equal(view.container.textContent?.includes("执行批次"), false);
  assert.equal(view.container.textContent?.includes("步骤结果详情"), false);
  assert.equal(view.container.textContent?.includes("运行方式"), false);
  assert.equal(view.queryByLabelText("固定 DAG 研判流程详情"), null);
  assert.equal(view.container.textContent?.includes("external_candidate_disabled"), false);
  assert.equal(view.container.textContent?.includes("pending_implementation"), false);
  assert.equal(view.container.textContent?.includes("待实现"), false);
  assertNoForbiddenDefaultUserCopy(view.container.textContent);

  assert.equal(sentPayloads[0].text, "Summarize the market risk profile.");
  assert.deepEqual(sentPayloads[0].structuredInput, { task: "Summarize the market risk profile." });
  assert.equal(sentPayloads[0].hasRouting, false);
  assert.deepEqual(finalRoles, ["user", "assistant"]);
  assertNoForbiddenUiTokens(view.container.textContent);
  cleanup();
}

async function runSelectedRoutingToggleScenario() {
  dom.reconfigure({ url: "http://localhost/" });
  const user = userEvent.setup({ document: dom.window.document });
  const sentPayloads: Array<{
    text: string;
    structuredInput?: StructuredInputModel;
    routing?: RoutingRequestModel | null;
    hasRouting: boolean;
  }> = [];

  installFetchMock(async (url, init) => {
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/health")) {
      return jsonResponse(degradedHealthPayload());
    }
    if (url.endsWith("/api/threads") && method === "GET") {
      return jsonResponse({ threads: [] });
    }
    if (url.endsWith("/api/threads") && method === "POST") {
      return jsonResponse({
        thread: threadSummary("新会话", "等待第一条消息。"),
        turns: [],
      });
    }
    if (url.endsWith("/api/agents") && method === "GET") {
      return jsonResponse(AGENT_CATALOG);
    }
    if (url.endsWith("/api/threads/thread-live-1/messages/stream") && method === "POST") {
      const payload = JSON.parse(String(init?.body ?? "{}")) as {
        text?: string;
        structuredInput?: StructuredInputModel;
        routing?: RoutingRequestModel | null;
      };
      sentPayloads.push({
        text: payload.text ?? "",
        structuredInput: payload.structuredInput,
        routing: payload.routing,
        hasRouting: "routing" in payload,
      });
      const answer = "已按选择路由生成摘要。";
      return ndjsonResponse([
        {
          type: "run.started",
          data: { threadId: "thread-live-1", continuityMode: "replay" },
        },
        {
          type: "answer.final",
          data: {
            response: {
              thread: threadSummary("选择路由摘要", answer),
              assistantTurn: assistantTurn("assistant-selected-1", answer),
              turns: [
                {
                  id: "user-selected-1",
                  role: "user",
                  text: payload.text ?? "",
                  createdAt: "2026-04-04 18:05",
                  structuredInput: payload.structuredInput,
                },
                assistantTurn("assistant-selected-1", answer),
              ],
            },
          },
        },
      ]);
    }

    return jsonResponse(
      { detail: { code: "unhandled_request", message: `Unhandled request: ${method} ${url}`, category: "request" } },
      500,
    );
  });

  const view = render(<App />);

  await waitFor(() => {
    assert.equal((view.container.querySelector("#chat-composer") as HTMLTextAreaElement).disabled, false);
  });
  assert.ok(view.getByText("选择路由（默认关闭）"));
  assert.ok(view.getByText("开启后，系统会尝试按问题选择更细粒度的路由；关闭时沿用固定研判流程。"));

  const taskInput = view.container.querySelector("#chat-composer") as HTMLTextAreaElement;
  await user.type(taskInput, "Analyze the valuation drivers.");
  await user.click(view.container.querySelector("#chat-selected-routing") as HTMLInputElement);
  await user.click(view.container.querySelector(".composer__submit") as HTMLButtonElement);

  await waitFor(() => {
    assert.ok(view.getByText("已按选择路由生成摘要。"));
  });
  assert.deepEqual(sentPayloads[0].routing, { mode: "selected" });
  assert.equal(sentPayloads[0].hasRouting, true);
  assert.deepEqual(sentPayloads[0].structuredInput, { task: "Analyze the valuation drivers." });
  assertNoForbiddenUiTokens(view.container.textContent);
  cleanup();
}

async function runStreamingErrorScenario() {
  dom.reconfigure({ url: "http://localhost/" });
  const user = userEvent.setup({ document: dom.window.document });

  installFetchMock(async (url, init) => {
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/health")) {
      return jsonResponse(degradedHealthPayload());
    }
    if (url.endsWith("/api/threads") && method === "GET") {
      return jsonResponse({ threads: [] });
    }
    if (url.endsWith("/api/threads") && method === "POST") {
      return jsonResponse({
        thread: threadSummary("新会话", "等待第一条消息。"),
        turns: [],
      });
    }
    if (url.endsWith("/api/agents") && method === "GET") {
      return jsonResponse(AGENT_CATALOG);
    }
    if (url.endsWith("/api/threads/thread-live-1/messages/stream") && method === "POST") {
      return ndjsonResponse([
        {
          type: "run.started",
          data: { threadId: "thread-live-1", continuityMode: "replay" },
        },
        {
          type: "workflow.stage",
          data: {
            currentStage: "evidence",
            stages: [
              { key: "planning", title: "规划", status: "completed" },
              { key: "evidence", title: "证据接入", status: "running" },
              { key: "l2_analysis", title: "L2 分析", status: "waiting" },
              { key: "dimension_composite", title: "维度综合", status: "waiting" },
              { key: "decision", title: "决策", status: "waiting" },
              { key: "report", title: "报告", status: "waiting" },
            ],
          },
        },
        {
          type: "error",
          data: {
            code: "runtime_invoke_unavailable",
            message: "LangGraph 运行时在生成公开回答前调用失败。",
            category: "runtime",
          },
        },
      ]);
    }

    return jsonResponse(
      { detail: { code: "unhandled_request", message: `Unhandled request: ${method} ${url}`, category: "request" } },
      500,
    );
  });

  const view = render(<App />);

  await waitFor(() => {
    assert.equal((view.container.querySelector("#chat-composer") as HTMLTextAreaElement).disabled, false);
  });

  const failingPrompt = "Trigger a streaming runtime failure.";
  await user.type(view.container.querySelector("#chat-composer") as HTMLTextAreaElement, failingPrompt);
  await user.click(view.container.querySelector(".composer__submit") as HTMLButtonElement);

  await waitFor(() => {
    assert.ok(view.getByText((content) => content.includes("LangGraph 运行时在生成公开回答前调用失败。")));
  });
  await waitFor(() => {
    assert.equal(view.queryByText(failingPrompt), null);
  });

  cleanup();
}

async function runSmoke() {
  runAgentCatalogContractChecks();
  runWorkflowFixtureContractChecks();
  runTranscriptBoundaryChecks();
  runStructuredInputHelperChecks();
  await runUserBubbleStructuredRenderChecks();
  await runAssistantRenderChecks();
  await runThoughtChainDynamicStageChecks();
  await runComposerLengthLimitChecks();
  await runStreamingSuccessScenario();
  await runSelectedRoutingToggleScenario();
  await runStreamingErrorScenario();
  console.log("Frontend fixed DAG contract smoke checks passed.");
}

runSmoke().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
