import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, "..");
const outputDir = process.env.SCREENSHOT_OUTPUT_DIR
  ? resolve(process.env.SCREENSHOT_OUTPUT_DIR)
  : resolve("E:/muti-agent/_tmp_r5c1_visual/screenshots");
const baseUrl = "http://127.0.0.1:4173";

function jsonResponse(route, body, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function waitForServer(url, timeoutMs = 20000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {
      // Retry until timeout.
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 400));
  }
  throw new Error(`Timed out waiting for preview server at ${url}`);
}

async function terminateProcessTree(pid) {
  if (!pid) {
    return;
  }
  const killer =
    process.platform === "win32"
      ? spawn("taskkill", ["/pid", String(pid), "/T", "/F"], { stdio: "ignore" })
      : null;
  if (!killer) {
    return;
  }
  await new Promise((resolveKill) => {
    killer.once("exit", resolveKill);
    killer.once("error", resolveKill);
  });
}

function delay(ms) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, ms));
}

function mockHealth() {
  return {
    status: "ok",
    apiVersion: "phase-r5",
    overallStatus: "ready",
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
    searchEnv: { status: "configured", code: "search_env_configured" },
    store: "json-file",
  };
}

const layerIds = {
  L1: ["route_planner", "financial_data_service", "entity_relation_extractor"],
  L2: [
    "value_traditional_valuation",
    "value_ml_valuation",
    "value_meta_valuation",
    "value_research_synthesis",
    "market_stock_technical",
    "market_fund_manager_behavior",
    "market_ipo_investor_behavior",
    "market_capital_flow_chip",
    "sentiment_company_radar",
    "risk_crash",
    "risk_financial_fraud",
    "risk_identification",
    "risk_compliance_review",
    "macro_analysis",
    "macro_commodity_pricing",
    "macro_index_valuation",
    "macro_sentiment",
    "macro_industry_hotspot",
  ],
  L3: ["value_composite", "market_composite", "risk_composite", "macro_composite"],
  L4: ["decision_synthesizer", "report_generator"],
};

function agentTeam(id) {
  if (id.startsWith("value_")) return "value";
  if (id.startsWith("market_") || id === "sentiment_company_radar") return "market";
  if (id.startsWith("risk_")) return "risk";
  if (id.startsWith("macro_")) return "macro";
  if (id.includes("composite")) return "composite";
  if (id === "decision_synthesizer" || id === "report_generator") return "l4";
  return "l1";
}

function mockAgentCatalog() {
  const layers = Object.entries(layerIds).map(([layer, ids]) => ({
    layer,
    agents: ids.map((id) => ({
      id,
      name: id,
      description: "固定流程能力。",
      capabilities: [agentTeam(id), layer.toLowerCase()],
      layer,
      team: agentTeam(id),
      roleType:
        layer === "L1"
          ? "evidence_service"
          : layer === "L2"
            ? "analysis_agent"
            : layer === "L3"
              ? "dimension_composite"
              : id === "decision_synthesizer"
                ? "decision_synthesizer"
                : "report_generator",
      defaultEnabled: true,
    })),
  }));

  return {
    totals: {
      configCount: 27,
      runtimeCount: 27,
      disabledIds: [],
    },
    layers,
    disabledAgents: [],
  };
}

function mockWorkflow() {
  return {
    schema: "workflow_snapshot_v2",
    planId: "visual-fixed-dag-plan",
    stages: [
      { key: "planning", title: "规划", stepIds: ["route_planner"] },
      { key: "evidence", title: "证据接入", stepIds: ["financial_data_service", "entity_relation_extractor"] },
      {
        key: "l2_analysis",
        title: "L2 分析",
        stepIds: ["value_traditional_valuation", "market_stock_technical", "sentiment_company_radar", "risk_identification"],
      },
      {
        key: "dimension_composite",
        title: "维度综合",
        stepIds: ["value_composite", "market_composite", "risk_composite", "macro_composite"],
      },
      { key: "decision", title: "决策", stepIds: ["decision_synthesizer"] },
      { key: "report", title: "报告", stepIds: ["report_generator"] },
    ],
    dagSteps: [
      {
        id: "route_planner",
        stage: "planning",
        agentId: "route_planner",
        dimension: "l1",
        title: "路径规划器",
        summary: "理解问题并组织本轮研判流程。",
        status: "complete",
      },
      {
        id: "financial_data_service",
        stage: "evidence",
        agentId: "financial_data_service",
        dimension: "l1",
        title: "金融数据服务",
        summary: "整理分析所需的基础数据与上下文。",
        status: "complete",
      },
      {
        id: "entity_relation_extractor",
        stage: "evidence",
        agentId: "entity_relation_extractor",
        dimension: "l1",
        title: "实体关系抽取器",
        summary: "识别公司、行业、事件等关键对象及其关系。",
        status: "complete",
      },
      {
        id: "value_traditional_valuation",
        stage: "l2_analysis",
        agentId: "value_traditional_valuation",
        dimension: "value",
        title: "传统企业估值",
        summary: "整理价值维度流程线索。",
        status: "pending_implementation",
      },
      {
        id: "market_stock_technical",
        stage: "l2_analysis",
        agentId: "market_stock_technical",
        dimension: "market",
        title: "个股技术分析",
        summary: "观察价格走势、成交变化与技术形态。",
        status: "pending_implementation",
      },
      {
        id: "sentiment_company_radar",
        stage: "l2_analysis",
        agentId: "sentiment_company_radar",
        dimension: "market",
        title: "企业舆情雷达",
        summary: "跟踪公司相关公开信息、媒体关注与市场情绪变化。",
        status: "pending_implementation",
      },
      {
        id: "risk_identification",
        stage: "l2_analysis",
        agentId: "risk_identification",
        dimension: "risk",
        title: "风险识别",
        summary: "识别可能影响判断的风险线索。",
        status: "pending_implementation",
      },
      {
        id: "value_composite",
        stage: "dimension_composite",
        agentId: "value_composite",
        dimension: "value",
        title: "价值综合",
        summary: "汇总价值维度信号。",
        status: "pending_implementation",
      },
      {
        id: "market_composite",
        stage: "dimension_composite",
        agentId: "market_composite",
        dimension: "market",
        title: "市场综合",
        summary: "汇总市场维度流程线索与差异。",
        status: "pending_implementation",
      },
      {
        id: "risk_composite",
        stage: "dimension_composite",
        agentId: "risk_composite",
        dimension: "risk",
        title: "风险综合",
        summary: "汇总风险维度流程线索与差异。",
        status: "pending_implementation",
      },
      {
        id: "macro_composite",
        stage: "dimension_composite",
        agentId: "macro_composite",
        dimension: "macro",
        title: "宏观综合",
        summary: "汇总宏观信号。",
        status: "pending_implementation",
      },
      {
        id: "decision_synthesizer",
        stage: "decision",
        agentId: "decision_synthesizer",
        dimension: "l4",
        title: "决策综合器",
        summary: "将维度流程信号汇入回答组织。",
        status: "pending_implementation",
      },
      {
        id: "report_generator",
        stage: "report",
        agentId: "report_generator",
        dimension: "l4",
        title: "报告生成器",
        summary: "生成最终公开回答。",
        status: "pending_implementation",
      },
    ],
    dimensionGroups: [
      {
        id: "value",
        title: "价值维度",
        stepIds: ["value_traditional_valuation", "value_composite"],
        status: "partial",
        summary: "价值维度已纳入上方回答组织。",
      },
      {
        id: "market",
        title: "市场维度",
        stepIds: ["market_stock_technical", "sentiment_company_radar", "market_composite"],
        status: "partial",
        summary: "市场维度已纳入上方回答组织。",
      },
      {
        id: "risk",
        title: "风险维度",
        stepIds: ["risk_identification", "risk_composite"],
        status: "partial",
        summary: "风险维度已纳入上方回答组织。",
      },
      {
        id: "macro",
        title: "宏观维度",
        stepIds: ["macro_composite"],
        status: "partial",
        summary: "宏观维度已纳入上方回答组织。",
      },
    ],
    currentStage: "report",
    completedSteps: [
      "route_planner",
      "financial_data_service",
      "entity_relation_extractor",
      "value_traditional_valuation",
      "market_stock_technical",
      "sentiment_company_radar",
      "risk_identification",
      "value_composite",
      "market_composite",
      "risk_composite",
      "macro_composite",
      "decision_synthesizer",
      "report_generator",
    ],
    executionBatches: [
      ["route_planner"],
      ["financial_data_service", "entity_relation_extractor"],
      ["value_traditional_valuation", "market_stock_technical", "sentiment_company_radar", "risk_identification"],
      ["value_composite", "market_composite", "risk_composite", "macro_composite"],
      ["decision_synthesizer"],
      ["report_generator"],
    ],
    stepResults: {
      route_planner: {
        status: "complete",
        runtime_kind: "deterministic_system",
        implementation_status: "deterministic_skeleton",
        binding_source: "fixed_dag_runtime_registry",
        invoke_enabled: true,
        live_verified: true,
      },
      financial_data_service: {
        status: "complete",
        runtime_kind: "external_http_candidate",
        implementation_status: "external_candidate_disabled",
        binding_source: "fixed_dag_runtime_registry",
        legacy_agent_id: "a22_financial_data_service",
        external_agent_id: "financial_data_service",
        invoke_enabled: false,
        live_verified: false,
        warnings: ["高级连接处于关闭状态，本轮使用本地流程。"],
      },
      sentiment_company_radar: {
        status: "pending_implementation",
        runtime_kind: "pending_placeholder",
        implementation_status: "pending_implementation",
        binding_source: "fixed_dag_runtime_registry",
        invoke_enabled: false,
        live_verified: false,
        warnings: ["企业舆情雷达仍是待接入流程节点，默认用户面仅展示流程线索。"],
      },
    },
    finalSource: "reset_skeleton",
    provenanceNote: "本轮研判流程已完成，过程记录可在流程详情中查看。",
    provenance: {
      source: "reset_skeleton",
      continuityMode: "replay",
      providerInvoked: false,
      externalInvoked: false,
      executionStatus: "deterministic_skeleton",
      fallbackUsed: false,
      limitations: ["当前示例使用本地固定流程，高级连接状态可在设置诊断中查看。"],
      summary: "本轮研判流程已完成，过程记录可在流程详情中查看。",
    },
  };
}

function mockThreadDetail() {
  const answer =
    "已完成本轮研判流程。系统按照固定研判流程组织本轮分析，包括问题理解、信息整理、并行分析、维度综合与报告生成。";

  return {
    thread: {
      id: "thread-visual-1",
      title: "研判流程",
      updatedAt: "今天 10:18",
      preview: "包含研判流程详情的公开回答。",
      finalSource: "reset_skeleton",
      phase: "在线",
      continuityMode: "replay",
    },
    turns: [
      {
        id: "turn-user-1",
        role: "user",
        text: "复核一个公开研判流程。",
        createdAt: "今天 10:16",
      },
      {
        id: "turn-assistant-1",
        role: "assistant",
        text: answer,
        createdAt: "今天 10:18",
        runId: "run-r5b2-visual-001",
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
            { label: "Workflow", note: "如需查看过程，可展开“流程详情”。" },
          ],
          evidenceCards: [{ title: "分析框架", note: "系统按照固定研判流程组织本轮分析。" }],
          evidenceCount: 3,
        },
        workflow: mockWorkflow(),
      },
    ],
  };
}

function mockEmptyThreadDetail() {
  return {
    thread: {
      id: "thread-empty-1",
      title: "新会话",
      updatedAt: "今天 10:12",
      preview: "等待第一条消息。",
      finalSource: "reset_skeleton",
      phase: "在线",
      continuityMode: "replay",
    },
    turns: [],
  };
}

async function installApiRoutes(page, options = {}) {
  const threadDetail = options.empty ? mockEmptyThreadDetail() : mockThreadDetail();

  await page.route("**/api/health", (route) => jsonResponse(route, mockHealth()));
  await page.route("**/api/agents", (route) => jsonResponse(route, mockAgentCatalog()));
  await page.route("**/api/threads/thread-visual-1/messages", (route) =>
    jsonResponse(route, {
      thread: threadDetail.thread,
      assistantTurn: threadDetail.turns[1],
      turns: threadDetail.turns,
    }),
  );
  await page.route("**/api/threads/thread-visual-1", (route) => jsonResponse(route, threadDetail));
  await page.route("**/api/threads/thread-empty-1", (route) => jsonResponse(route, threadDetail));
  await page.route("**/api/threads", async (route, request) => {
    if (request.method() === "POST") {
      return jsonResponse(route, threadDetail);
    }
    return jsonResponse(route, { threads: options.empty ? [] : [threadDetail.thread] });
  });
}

async function pageText(page) {
  return (await page.locator("body").textContent()) ?? "";
}

async function assertPageContains(page, expected) {
  const text = await pageText(page);
  if (!text.includes(expected)) {
    throw new Error(`Expected page text to include: ${expected}`);
  }
}

async function assertPageExcludes(page, forbidden) {
  const text = await pageText(page);
  if (text.includes(forbidden)) {
    throw new Error(`Unexpected page text: ${forbidden}`);
  }
}

async function assertNoForbiddenTokens(page) {
  for (const token of [
    "secret",
    "secrets",
    "default_url",
    "env_var",
    "api_key",
    "apiKey",
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    "fake confidence",
    "置信度 72%",
    "目标价",
    "买入",
    "卖出建议",
    "真实分析完成",
  ]) {
    await assertPageExcludes(page, token);
  }
}

async function main() {
  await mkdir(outputDir, { recursive: true });

  const preview =
    process.platform === "win32"
      ? spawn("cmd.exe", ["/c", "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "4173"], {
          cwd: rootDir,
          stdio: "ignore",
        })
      : spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", "4173"], {
          cwd: rootDir,
          stdio: "ignore",
        });

  let browser = null;
  try {
    await waitForServer(baseUrl);

    browser = await chromium.launch({ headless: true });
    console.log(`[screenshots] writing to ${outputDir}`);

    const emptyPage = await browser.newPage({
      viewport: { width: 1400, height: 1024 },
      deviceScaleFactor: 1,
    });
    emptyPage.setDefaultTimeout(10000);
    console.log("[screenshots] chat empty");
    await installApiRoutes(emptyPage, { empty: true });
    await emptyPage.goto(baseUrl, { waitUntil: "networkidle" });
    await emptyPage.locator(".thread-empty").waitFor({ timeout: 10000 });
    await assertPageContains(emptyPage, "开始一次资本市场研判");
    await assertPageContains(emptyPage, "总结电动车公司的风险画像");
    await assertPageExcludes(emptyPage, "Provider 环境未配置");
    await assertPageExcludes(emptyPage, "待实现");
    await assertNoForbiddenTokens(emptyPage);
    await emptyPage.screenshot({ path: resolve(outputDir, "chat-empty-desktop.png"), timeout: 10000 });
    await emptyPage.close();

    const page = await browser.newPage({
      viewport: { width: 1400, height: 1024 },
      deviceScaleFactor: 1,
    });
    page.setDefaultTimeout(10000);

    await installApiRoutes(page);
    console.log("[screenshots] chat answer summary");
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.locator(".assistant-card").waitFor({ timeout: 10000 });
    await assertPageContains(page, "研判依据");
    await assertPageContains(page, "分析框架");
    await assertPageContains(page, "用户问题");
    await assertPageContains(page, "流程记录");
    await assertPageContains(page, "研判思维链");
    await assertPageContains(page, "技术流程详情");
    await assertPageContains(page, "展开技术详情");
    await assertPageExcludes(page, "执行批次");
    await assertPageExcludes(page, "步骤结果详情");
    await assertPageExcludes(page, "运行方式");
    await assertPageExcludes(page, "external_http_candidate");
    await assertPageExcludes(page, "external_candidate_disabled");
    await assertPageExcludes(page, "pending_implementation");
    await assertPageExcludes(page, "待实现");
    await assertPageExcludes(page, "fixture");
    await assertPageExcludes(page, "roster");
    await assertPageExcludes(page, "transcript");
    await assertPageExcludes(page, "检查器元数据");
    await assertPageExcludes(page, "固定 DAG 数据组");
    await assertPageExcludes(page, "固定 DAG 数据包");
    await assertPageExcludes(page, "No provider");
    await assertPageExcludes(page, "external endpoint");
    await assertPageExcludes(page, "Fixed DAG workflow inspection");
    await assertPageExcludes(page, "Public answer with fixed DAG inspector metadata");
    await assertNoForbiddenTokens(page);
    await page.screenshot({ path: resolve(outputDir, "chat-answer-summary-desktop.png"), timeout: 10000 });

    console.log("[screenshots] workflow expanded");
    await page.locator(".technical-workflow__toggle").waitFor({ timeout: 10000 });
    await page.$eval(".technical-workflow__toggle", (button) => button.click());
    await page.locator(".workflow-panel__content").waitFor({ timeout: 10000 });
    for (const expected of ["阶段时间线", "执行批次", "维度分组", "步骤结果详情", "最终来源与溯源"]) {
      await assertPageContains(page, expected);
    }
    for (const expected of [
      "价值维度已纳入上方回答组织",
      "市场维度已纳入上方回答组织",
      "风险维度已纳入上方回答组织",
      "宏观维度已纳入上方回答组织",
    ]) {
      await assertPageContains(page, expected);
    }
    await page.getByRole("button", { name: /金融数据服务/ }).click({ timeout: 10000 });
    for (const expectedRaw of ["financial_data_service", "external_http_candidate", "external_candidate_disabled"]) {
      await assertPageContains(page, expectedRaw);
    }
    for (const oldCopy of ["Stage timeline", "Execution batches", "Dimension groups", "Step result metadata"]) {
      await assertPageExcludes(page, oldCopy);
    }
    for (const oldCopy of ["fixture", "roster", "风险路径不读取企业舆情雷达", "市场路径包含企业舆情雷达", "检查器元数据"]) {
      await assertPageExcludes(page, oldCopy);
    }
    await assertNoForbiddenTokens(page);
    await page.locator(".workflow-result-card").scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollBy(0, -84));
    await page.screenshot({ path: resolve(outputDir, "workflow-expanded-desktop.png"), timeout: 10000 });

    console.log("[screenshots] agents");
    await page.goto(`${baseUrl}/agents`, { waitUntil: "networkidle" });
    await page.locator(".agent-catalog").waitFor({ timeout: 10000 });
    await assertPageContains(page, "智能体能力结构");
    await assertPageContains(page, "解析与证据");
    await assertPageContains(page, "价值维");
    await assertPageExcludes(page, "外部候选未启用");
    await assertPageExcludes(page, "待实现");
    await assertNoForbiddenTokens(page);
    await page.screenshot({ path: resolve(outputDir, "agents-desktop.png"), timeout: 10000 });

    console.log("[screenshots] settings");
    await page.goto(`${baseUrl}/settings`, { waitUntil: "networkidle" });
    await page.locator(".settings-summary").waitFor({ timeout: 10000 });
    await assertPageContains(page, "设置与状态诊断");
    await assertPageContains(page, "高级诊断");
    await assertPageExcludes(page, "Provider 环境");
    await assertPageExcludes(page, "降级");
    await assertNoForbiddenTokens(page);
    await page.screenshot({ path: resolve(outputDir, "settings-desktop.png"), timeout: 10000 });

    console.log("[screenshots] complete");
  } finally {
    if (browser) {
      await Promise.race([browser.close(), delay(3000)]).catch(() => undefined);
    }
    if (process.platform === "win32") {
      await terminateProcessTree(preview.pid);
    } else {
      preview.kill("SIGTERM");
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
