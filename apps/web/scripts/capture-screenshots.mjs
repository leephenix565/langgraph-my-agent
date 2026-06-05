import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, "..");
const outputDir = resolve(rootDir, "artifacts");
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
        summary: "为公开请求构建确定性的固定 DAG 计划。",
        status: "complete",
      },
      {
        id: "financial_data_service",
        stage: "evidence",
        agentId: "financial_data_service",
        dimension: "l1",
        title: "金融数据服务",
        summary: "在 fixture 中准备公开数据占位接口，不进行实时外部调用。",
        status: "complete",
      },
      {
        id: "entity_relation_extractor",
        stage: "evidence",
        agentId: "entity_relation_extractor",
        dimension: "l1",
        title: "实体关系抽取器",
        summary: "为下游分析准备实体与关系上下文。",
        status: "complete",
      },
      {
        id: "value_traditional_valuation",
        stage: "l2_analysis",
        agentId: "value_traditional_valuation",
        dimension: "value",
        title: "传统企业估值",
        summary: "在截图 fixture 中代表价值分析路径。",
        status: "pending_implementation",
      },
      {
        id: "market_stock_technical",
        stage: "l2_analysis",
        agentId: "market_stock_technical",
        dimension: "market",
        title: "个股技术分析",
        summary: "在截图 fixture 中代表市场分析路径。",
        status: "pending_implementation",
      },
      {
        id: "sentiment_company_radar",
        stage: "l2_analysis",
        agentId: "sentiment_company_radar",
        dimension: "market",
        title: "企业舆情雷达",
        summary: "在固定 DAG roster 中只汇入市场维度。",
        status: "pending_implementation",
      },
      {
        id: "risk_identification",
        stage: "l2_analysis",
        agentId: "risk_identification",
        dimension: "risk",
        title: "风险识别",
        summary: "在截图 fixture 中代表风险分析路径。",
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
        summary: "汇总市场信号，包含企业舆情。",
        status: "pending_implementation",
      },
      {
        id: "risk_composite",
        stage: "dimension_composite",
        agentId: "risk_composite",
        dimension: "risk",
        title: "风险综合",
        summary: "汇总风险信号，不读取企业舆情。",
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
        summary: "将维度综合结果汇入决策占位接口。",
        status: "pending_implementation",
      },
      {
        id: "report_generator",
        stage: "report",
        agentId: "report_generator",
        dimension: "l4",
        title: "报告生成器",
        summary: "投影生成最终公开回答。",
        status: "pending_implementation",
      },
    ],
    dimensionGroups: [
      {
        id: "value",
        title: "价值维度",
        stepIds: ["value_traditional_valuation", "value_composite"],
        status: "partial",
        summary: "价值路径以可公开展示的检查器元数据呈现。",
      },
      {
        id: "market",
        title: "市场维度",
        stepIds: ["market_stock_technical", "sentiment_company_radar", "market_composite"],
        status: "partial",
        summary: "市场路径包含企业舆情雷达。",
      },
      {
        id: "risk",
        title: "风险维度",
        stepIds: ["risk_identification", "risk_composite"],
        status: "partial",
        summary: "风险路径不读取企业舆情雷达。",
      },
      {
        id: "macro",
        title: "宏观维度",
        stepIds: ["macro_composite"],
        status: "partial",
        summary: "宏观路径以可公开展示的检查器元数据呈现。",
      },
    ],
    currentStage: "report",
    completedSteps: ["route_planner", "financial_data_service", "entity_relation_extractor"],
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
        runtime_kind: "deterministic_skeleton",
        implementation_status: "deterministic_skeleton",
        binding_source: "fixed_dag_runtime_registry",
        invoke_enabled: false,
        live_verified: false,
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
        warnings: ["外部候选已注册，但 fixture 没有实时验证。"],
      },
      sentiment_company_radar: {
        status: "pending_implementation",
        runtime_kind: "placeholder",
        implementation_status: "pending_implementation",
        binding_source: "fixed_dag_runtime_registry",
        invoke_enabled: false,
        live_verified: false,
        warnings: ["fixture 中市场舆情路径仍是占位实现。"],
      },
    },
    finalSource: "reset_skeleton",
    provenanceNote: "可公开展示的固定 DAG 工作流快照；raw graph messages 和 raw provider responses 不进入 transcript。",
    provenance: {
      source: "reset_skeleton",
      continuityMode: "replay",
      providerInvoked: false,
      externalInvoked: false,
      executionStatus: "deterministic_skeleton",
      fallbackUsed: false,
      limitations: ["仅截图 fixture；未验证 provider 或外部服务实时就绪状态。"],
      summary: "最终回答由重置骨架固定 DAG 路径投影生成。",
    },
  };
}

function mockThreadDetail() {
  const answer =
    "固定 DAG 骨架将公开回答保持为单条助手回复。检查器展示规划、证据、并行分析、维度综合、决策和报告阶段，不暴露 raw provider 或外部响应。";

  return {
    thread: {
      id: "thread-visual-1",
      title: "固定 DAG 工作流检查",
      updatedAt: "今天 10:18",
      preview: "包含固定 DAG 检查器元数据的公开回答。",
      finalSource: "reset_skeleton",
      phase: "在线",
      continuityMode: "replay",
    },
    turns: [
      {
        id: "turn-user-1",
        role: "user",
        text: "复核一个可公开展示的固定 DAG 投资工作流。",
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
            { label: "Fixed DAG bundle", note: "最终回答来自公开固定 DAG 投影。" },
            { label: "Workflow", note: "工作流细节保留在检查器中，不进入 transcript。" },
          ],
          evidenceCards: [{ title: "Workflow", note: "结构化可公开输出。" }],
          evidenceCount: 1,
        },
        workflow: mockWorkflow(),
      },
    ],
  };
}

async function installApiRoutes(page) {
  const threadDetail = mockThreadDetail();

  await page.route("**/api/health", (route) => jsonResponse(route, mockHealth()));
  await page.route("**/api/threads/thread-visual-1/messages", (route) =>
    jsonResponse(route, {
      thread: threadDetail.thread,
      assistantTurn: threadDetail.turns[1],
      turns: threadDetail.turns,
    }),
  );
  await page.route("**/api/threads/thread-visual-1", (route) => jsonResponse(route, threadDetail));
  await page.route("**/api/threads", async (route, request) => {
    if (request.method() === "POST") {
      return jsonResponse(route, threadDetail);
    }
    return jsonResponse(route, { threads: [threadDetail.thread] });
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
  for (const token of ["secret", "secrets", "default_url", "env_var", "api_key", "apiKey", "OPENAI_API_KEY", "TAVILY_API_KEY"]) {
    await assertPageExcludes(page, token);
  }
}

async function main() {
  await mkdir(outputDir, { recursive: true });

  const preview =
    process.platform === "win32"
      ? spawn("cmd.exe", ["/c", "npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", "4173"], {
          cwd: rootDir,
          stdio: "pipe",
        })
      : spawn("npm", ["run", "preview", "--", "--host", "127.0.0.1", "--port", "4173"], {
          cwd: rootDir,
          stdio: "pipe",
        });

  try {
    await waitForServer(baseUrl);

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({
      viewport: { width: 1400, height: 1024 },
      deviceScaleFactor: 1,
    });

    await installApiRoutes(page);
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.locator(".assistant-card").waitFor();
    await assertPageContains(page, "固定 DAG 工作流检查");
    await assertPageExcludes(page, "Fixed DAG workflow inspection");
    await assertPageExcludes(page, "Public answer with fixed DAG inspector metadata");
    await assertNoForbiddenTokens(page);
    await page.screenshot({ path: resolve(outputDir, "chat-home-desktop.png") });

    const toggle = page.getByRole("button", { name: /工作流|DAG 检查器|打开 DAG 检查器/ });
    await toggle.click();
    await page.locator(".workflow-panel__content").waitFor();
    for (const expected of ["阶段时间线", "执行批次", "维度分组", "步骤结果元数据", "最终来源与溯源"]) {
      await assertPageContains(page, expected);
    }
    for (const expectedRaw of ["financial_data_service", "external_http_candidate", "external_candidate_disabled"]) {
      await assertPageContains(page, expectedRaw);
    }
    for (const oldCopy of ["Stage timeline", "Execution batches", "Dimension groups", "Step result metadata"]) {
      await assertPageExcludes(page, oldCopy);
    }
    await assertNoForbiddenTokens(page);
    await page.locator(".workflow-panel").scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollBy(0, -84));
    await page.screenshot({ path: resolve(outputDir, "workflow-expanded-desktop.png") });

    await browser.close();
  } finally {
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(preview.pid), "/T", "/F"], { stdio: "ignore" });
    } else {
      preview.kill("SIGTERM");
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
