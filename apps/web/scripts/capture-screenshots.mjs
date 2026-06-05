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
      hint: "Set REACT_AGENT_CHECKPOINTER=memory or sqlite for persistent continuity.",
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
      { key: "planning", title: "Planning", stepIds: ["route_planner"] },
      { key: "evidence", title: "Evidence seams", stepIds: ["financial_data_service", "entity_relation_extractor"] },
      {
        key: "l2_analysis",
        title: "L2 analysis",
        stepIds: ["value_traditional_valuation", "market_stock_technical", "sentiment_company_radar", "risk_identification"],
      },
      {
        key: "dimension_composite",
        title: "Dimension composites",
        stepIds: ["value_composite", "market_composite", "risk_composite", "macro_composite"],
      },
      { key: "decision", title: "Decision", stepIds: ["decision_synthesizer"] },
      { key: "report", title: "Report", stepIds: ["report_generator"] },
    ],
    dagSteps: [
      {
        id: "route_planner",
        stage: "planning",
        agentId: "route_planner",
        dimension: "l1",
        title: "Route planner",
        summary: "Builds the deterministic fixed DAG plan for the public request.",
        status: "complete",
      },
      {
        id: "financial_data_service",
        stage: "evidence",
        agentId: "financial_data_service",
        dimension: "l1",
        title: "Financial data service",
        summary: "Prepares the public data seam without live external invocation in this fixture.",
        status: "complete",
      },
      {
        id: "entity_relation_extractor",
        stage: "evidence",
        agentId: "entity_relation_extractor",
        dimension: "l1",
        title: "Entity relation extractor",
        summary: "Prepares entity and relation context for downstream analysis.",
        status: "complete",
      },
      {
        id: "value_traditional_valuation",
        stage: "l2_analysis",
        agentId: "value_traditional_valuation",
        dimension: "value",
        title: "Traditional valuation",
        summary: "Represents the value analysis path in the screenshot fixture.",
        status: "pending_implementation",
      },
      {
        id: "market_stock_technical",
        stage: "l2_analysis",
        agentId: "market_stock_technical",
        dimension: "market",
        title: "Stock technical analysis",
        summary: "Represents the market analysis path in the screenshot fixture.",
        status: "pending_implementation",
      },
      {
        id: "sentiment_company_radar",
        stage: "l2_analysis",
        agentId: "sentiment_company_radar",
        dimension: "market",
        title: "Company sentiment radar",
        summary: "Feeds only the market dimension in the fixed DAG roster.",
        status: "pending_implementation",
      },
      {
        id: "risk_identification",
        stage: "l2_analysis",
        agentId: "risk_identification",
        dimension: "risk",
        title: "Risk identification",
        summary: "Represents the risk analysis path in the screenshot fixture.",
        status: "pending_implementation",
      },
      {
        id: "value_composite",
        stage: "dimension_composite",
        agentId: "value_composite",
        dimension: "value",
        title: "Value composite",
        summary: "Combines value-dimension signals.",
        status: "pending_implementation",
      },
      {
        id: "market_composite",
        stage: "dimension_composite",
        agentId: "market_composite",
        dimension: "market",
        title: "Market composite",
        summary: "Combines market signals including company sentiment.",
        status: "pending_implementation",
      },
      {
        id: "risk_composite",
        stage: "dimension_composite",
        agentId: "risk_composite",
        dimension: "risk",
        title: "Risk composite",
        summary: "Combines risk signals without company sentiment input.",
        status: "pending_implementation",
      },
      {
        id: "macro_composite",
        stage: "dimension_composite",
        agentId: "macro_composite",
        dimension: "macro",
        title: "Macro composite",
        summary: "Combines macro signals.",
        status: "pending_implementation",
      },
      {
        id: "decision_synthesizer",
        stage: "decision",
        agentId: "decision_synthesizer",
        dimension: "l4",
        title: "Decision synthesizer",
        summary: "Synthesizes dimension composites into a decision seam.",
        status: "pending_implementation",
      },
      {
        id: "report_generator",
        stage: "report",
        agentId: "report_generator",
        dimension: "l4",
        title: "Report generator",
        summary: "Projects the final public answer.",
        status: "pending_implementation",
      },
    ],
    dimensionGroups: [
      {
        id: "value",
        title: "Value dimension",
        stepIds: ["value_traditional_valuation", "value_composite"],
        status: "partial",
        summary: "Value path is represented as public-safe inspector metadata.",
      },
      {
        id: "market",
        title: "Market dimension",
        stepIds: ["market_stock_technical", "sentiment_company_radar", "market_composite"],
        status: "partial",
        summary: "Market path includes company sentiment radar.",
      },
      {
        id: "risk",
        title: "Risk dimension",
        stepIds: ["risk_identification", "risk_composite"],
        status: "partial",
        summary: "Risk path excludes company sentiment radar.",
      },
      {
        id: "macro",
        title: "Macro dimension",
        stepIds: ["macro_composite"],
        status: "partial",
        summary: "Macro path is represented as public-safe inspector metadata.",
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
        warnings: ["External candidate is registered but not live verified in the fixture."],
      },
      sentiment_company_radar: {
        status: "pending_implementation",
        runtime_kind: "placeholder",
        implementation_status: "pending_implementation",
        binding_source: "fixed_dag_runtime_registry",
        invoke_enabled: false,
        live_verified: false,
        warnings: ["Market sentiment path is placeholder-only in the fixture."],
      },
    },
    finalSource: "reset_skeleton",
    provenanceNote: "Public-safe fixed DAG workflow snapshot. Raw graph messages and raw provider responses are not transcript.",
    provenance: {
      source: "reset_skeleton",
      continuityMode: "replay",
      providerInvoked: false,
      externalInvoked: false,
      executionStatus: "deterministic_skeleton",
      fallbackUsed: false,
      limitations: ["Screenshot fixture only; provider and external live readiness are not verified."],
      summary: "Final answer is projected from the reset skeleton fixed DAG path.",
    },
  };
}

function mockThreadDetail() {
  const answer =
    "The fixed DAG skeleton keeps the public answer as a single assistant response. The inspector shows planning, evidence, parallel analysis, dimension composites, decision, and report seams without exposing raw provider or external responses.";

  return {
    thread: {
      id: "thread-visual-1",
      title: "Fixed DAG workflow inspection",
      updatedAt: "Today 10:18",
      preview: "Public answer with fixed DAG inspector metadata.",
      finalSource: "reset_skeleton",
      phase: "Live",
      continuityMode: "replay",
    },
    turns: [
      {
        id: "turn-user-1",
        role: "user",
        text: "Review a public-safe fixed DAG investment workflow.",
        createdAt: "Today 10:16",
      },
      {
        id: "turn-assistant-1",
        role: "assistant",
        text: answer,
        createdAt: "Today 10:18",
        runId: "run-r5b2-visual-001",
        continuityMode: "replay",
        answerCard: {
          answer,
          finalSource: "reset_skeleton",
          citations: [
            { label: "Fixed DAG bundle", note: "Final answer came from the public fixed DAG projection." },
            { label: "Workflow", note: "Workflow details remain in the inspector, not the transcript." },
          ],
          evidenceCards: [{ title: "Workflow", note: "Structured public-safe output." }],
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
    await page.screenshot({ path: resolve(outputDir, "chat-home-desktop.png") });

    const toggle = page.getByRole("button", { name: /Workflow|DAG inspector|Open DAG inspector/ });
    await toggle.click();
    await page.locator(".workflow-panel__content").waitFor();
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
