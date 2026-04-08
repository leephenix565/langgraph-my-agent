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
    apiVersion: "phase-f3",
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

function mockThreadDetail() {
  return {
    thread: {
      id: "thread-visual-1",
      title: "新能源汽车企业财报与风险",
      updatedAt: "今天 10:18",
      preview: "保留主线配置方向，同时压低高波动暴露。",
      finalSource: "fused",
      phase: "Live",
      continuityMode: "replay",
    },
    turns: [
      {
        id: "turn-user-1",
        role: "user",
        text: "请帮我深度分析一下目前国内新能源汽车行业头部的几家公司财务健康度，以及未来一年的主要政策风险。",
        createdAt: "今天 10:16",
      },
      {
        id: "turn-assistant-1",
        role: "assistant",
        text:
          "基于对国内新能源汽车行业头部企业（如比亚迪、理想、蔚来等）的最新财务数据与宏观政策的综合研判，以下是深度分析结果：\n\n1. 财务健康度分化明显。头部企业已实现规模效应，季度净利润持续为正，自由现金流充裕，具备较强的抗周期能力。部分新势力车企营收增长仍依赖促销与研发投入，现金流和利润率仍处于承压阶段。\n\n2. 未来一年主要政策与宏观风险。补贴退出与价格战会继续压缩行业毛利；海外关税与本地化合规要求也会提升全球化成本，企业需要在规模扩张与利润纪律之间重新平衡。\n\n3. 组合建议。保留主线配置方向，同时压低高波动暴露，把价格战敏感、对外部融资依赖较高的环节控制在可承受范围内。",
        createdAt: "今天 10:18",
        runId: "run-ux-1f-001",
        continuityMode: "replay",
        answerCard: {
          answer:
            "基于对国内新能源汽车行业头部企业（如比亚迪、理想、蔚来等）的最新财务数据与宏观政策的综合研判，以下是深度分析结果：\n\n1. 财务健康度分化明显。头部企业已实现规模效应，季度净利润持续为正，自由现金流充裕，具备较强的抗周期能力。部分新势力车企营收增长仍依赖促销与研发投入，现金流和利润率仍处于承压阶段。\n\n2. 未来一年主要政策与宏观风险。补贴退出与价格战会继续压缩行业毛利；海外关税与本地化合规要求也会提升全球化成本，企业需要在规模扩张与利润纪律之间重新平衡。\n\n3. 组合建议。保留主线配置方向，同时压低高波动暴露，把价格战敏感、对外部融资依赖较高的环节控制在可承受范围内。",
          finalSource: "fused",
          confidence: "high",
          citations: [
            { label: "主线摘要", note: "最终回答来自安全映射后的公开摘要。" },
            { label: "协作过程", note: "协作过程被压缩为可展开的检查层，而不是多位聊天角色。" },
          ],
          evidenceCards: [{ title: "宏观背景", note: "流动性压力边际缓和，但价格竞争仍在持续。" }],
          evidenceCount: 1,
        },
        workflow: {
          layerPlan: [
            { layer: "L1", mode: "Chain", selected: ["a01_cio_orchestrator"], note: "明确问题边界与对外回答结构。" },
            {
              layer: "L2",
              mode: "Star",
              selected: ["a03_macro_policy", "a06_financial_reports", "a10_industry_sentiment", "a15_research_synthesis"],
              note: "并行获取政策、财务与行业背景。",
            },
            {
              layer: "L3",
              mode: "Star",
              selected: ["a18_primary_secondary_valuation", "a19_market_risk", "a23_portfolio_opt"],
              note: "补足估值、波动与组合约束判断。",
            },
            { layer: "L4", mode: "Chain", selected: ["a25_report_center"], note: "整理为最终对外回答。" },
          ],
          layerMode: { L1: "Chain", L2: "Star", L3: "Star", L4: "Chain" },
          currentLayer: "L4",
          layerDone: ["L1", "L2", "L3", "L4"],
          agentSteps: [
            {
              id: "step-1",
              layer: "L1",
              agentId: "a01_cio_orchestrator",
              title: "首席投资统筹",
              summary: "识别到深度分析意图，并先约束最终输出结构。",
              status: "complete",
            },
            {
              id: "step-2",
              layer: "L2",
              agentId: "a06_financial_reports",
              title: "财务报告分析师",
              summary: "识别到 Q3 营收超预期，但现金流承压。",
              status: "complete",
            },
            {
              id: "step-3",
              layer: "L2",
              agentId: "a03_macro_policy",
              title: "宏观政策分析师",
              summary: "行业补贴政策在下季度退坡，存在宏观阻力。",
              status: "complete",
            },
            {
              id: "step-4",
              layer: "L3",
              agentId: "a21_reg_compliance",
              title: "合规风险监控",
              summary: "暂未发现近期重大诉讼或合规违约风险。",
              status: "complete",
            },
          ],
          fusionSteps: [
            {
              id: "fusion-baseline",
              kind: "baseline",
              label: "Baseline sidecar",
              status: "shadow",
              summary: "基线侧车补充了更偏风险表达的对照观点。",
            },
            {
              id: "fusion-judge",
              kind: "judge",
              label: "Fusion judge",
              status: "ready",
              summary: "融合评判选择保留主线结构，并吸收基线的风险表述。",
            },
            {
              id: "fusion-writer",
              kind: "writer",
              label: "Fusion writer",
              status: "selected",
              summary: "融合写作生成了最终对外可见的回答。",
            },
          ],
          finalSource: "fused",
          provenanceNote: "最终回答来自融合写作路径，连续性为回放模式。",
          provenance: {
            emitPath: "fusion_writer",
            finalSource: "fused",
            continuityMode: "replay",
            summary: "最终回答来自融合写作路径，并保留主线研究框架。",
          },
        },
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

    const toggle = page.getByRole("button", { name: /协作过程/ });
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
