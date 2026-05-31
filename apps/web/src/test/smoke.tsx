import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import React from "react";
import { cleanup, fireEvent, render, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../app/App";
import { AssistantAnswerCard } from "../components/chat/AssistantAnswerCard";
import { UserBubble } from "../components/chat/UserBubble";
import { Composer } from "../components/shell/Composer";
import { AGENT_CATALOG } from "../mocks/agents";
import type { StructuredInputModel } from "../types/chat";
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
    apiVersion: "phase-f3",
    overallStatus: "degraded",
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
    searchEnv: {
      status: "missing",
      code: "search_env_missing",
      hint: "Set TAVILY_API_KEY before importing react_agent.graph.",
    },
    store: "json-file",
  };
}

function liveAgentCatalogPayload() {
  return AGENT_CATALOG;
}

function assistantTurn(id: string, answer: string) {
  return {
    id,
    role: "assistant",
    text: answer,
    createdAt: "2026-04-04 18:06",
    answerCard: {
      answer,
      finalSource: "mainline",
      citations: [{ label: "Mainline bundle", note: "Final answer came from the public emitted bundle." }],
      evidenceCards: [{ title: "Research summary", note: "Structured public-safe output." }],
      evidenceCount: 1,
    },
    workflow: {
      layerPlan: [
        { layer: "L1", mode: "Chain", selected: ["a01_cio_orchestrator"] },
        { layer: "L2", mode: "Star", selected: ["a03_macro_industry_research"] },
        { layer: "L3", mode: "Star", selected: ["a20_compliance_review"] },
        { layer: "L4", mode: "Chain", selected: ["a25_report_center"] },
      ],
      layerMode: { L1: "Chain", L2: "Star", L3: "Star", L4: "Chain" },
      currentLayer: "L4",
      layerDone: ["L1", "L2", "L3", "L4"],
      agentSteps: [
        {
          id: "step-1",
          layer: "L1",
          agentId: "a01_cio_orchestrator",
          title: "CIO Orchestrator",
          summary: "Framed the request.",
          status: "complete",
        },
      ],
      fusionSteps: [
        {
          id: "fusion-baseline",
          kind: "baseline",
          label: "Baseline sidecar",
          status: "shadow",
          summary: "Baseline completed in shadow mode.",
        },
      ],
      finalSource: "mainline",
      provenanceNote: "Safe workflow projection only.",
      provenance: {
        emitPath: "mainline_summary",
        finalSource: "mainline",
        continuityMode: "replay",
        summary: "Public-safe workflow provenance.",
      },
    },
  };
}

function threadSummary(title: string, preview: string) {
  return {
    id: "thread-live-1",
    title,
    updatedAt: "2026-04-04 18:06",
    preview,
    finalSource: "mainline",
    phase: "Live",
    continuityMode: "replay",
  };
}

function historyThreadSummary(id: string, title: string, preview: string) {
  return {
    id,
    title,
    updatedAt: "2026-04-04 18:06",
    preview,
    finalSource: "mainline",
    phase: "Live",
    continuityMode: "replay",
  };
}

function getComposerElements(container: HTMLElement) {
  const taskInput = container.querySelector("#chat-composer") as HTMLTextAreaElement | null;
  const sendButton = container.querySelector(".composer__submit") as HTMLButtonElement | null;
  const toggleButton = container.querySelector(".composer__toggle") as HTMLButtonElement | null;
  assert.ok(taskInput);
  assert.ok(sendButton);
  assert.ok(toggleButton);
  return { taskInput, sendButton, toggleButton };
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
  const typedOnly = render(
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

  const typedScope = within(typedOnly.getByRole("article"));
  assert.ok(typedScope.getByText("Material one"));
  assert.equal(
    typedScope.getByRole("link", { name: "https://example.com/policy-brief" }).getAttribute("href"),
    "https://example.com/policy-brief",
  );
  cleanup();

  const fallbackText = composeStructuredPrompt({
    task: "Summarize the risk profile.",
    materialsText: "Material one\n\nMaterial two",
    urlReferencesText: "https://example.com/policy-brief\nhttps://example.com/company-update",
  });

  const fallback = render(
    <UserBubble
      turn={{
        id: "user-fallback-1",
        role: "user",
        text: fallbackText,
        createdAt: "2026-04-04 18:11",
      }}
    />,
  );

  const fallbackScope = within(fallback.getByRole("article"));
  assert.ok(fallbackScope.getByText("Material two"));
  assert.equal(
    fallbackScope.getByRole("link", { name: "https://example.com/company-update" }).getAttribute("href"),
    "https://example.com/company-update",
  );
  cleanup();
}

async function runAssistantMarkdownRenderChecks() {
  const markdownAnswer = [
    "### Market Summary",
    "",
    "This paragraph contains **strong emphasis** and *supporting nuance*.",
    "",
    "- First point",
    "- Second point",
    "",
    "> Quoted observation.",
    "",
    "| Metric | View |",
    "| --- | --- |",
    "| Valuation | Neutral |",
    "",
    "Watch the `run_id` field.",
    "",
    "```ts",
    'const signal = "watch";',
    "```",
  ].join("\n");

  const view = render(
    <AssistantAnswerCard
      turn={{
        id: "assistant-markdown-1",
        role: "assistant",
        text: markdownAnswer,
        createdAt: "2026-04-05 16:30",
        answerCard: {
          answer: markdownAnswer,
          finalSource: "mainline",
        },
      }}
    />,
  );

  const article = view.getByRole("article");
  const scope = within(article);
  assert.equal(scope.queryByText("### Market Summary"), null);
  assert.ok(scope.getByRole("heading", { level: 3, name: "Market Summary" }));
  assert.ok(article.querySelector("strong"));
  assert.ok(article.querySelector("em"));
  assert.ok(article.querySelector("blockquote"));
  assert.ok(scope.getByRole("table"));
  assert.ok(article.querySelector("pre code"));
  assert.ok(scope.getByText('const signal = "watch";'));

  cleanup();
}

async function runComposerLengthLimitChecks() {
  const user = userEvent.setup({ document: dom.window.document });
  let submitCount = 0;
  const view = render(<Composer maxMessageChars={10} onSubmit={() => { submitCount += 1; }} />);
  const form = view.container.querySelector("form") as HTMLFormElement;
  const { taskInput, sendButton } = getComposerElements(view.container);

  await user.click(taskInput);
  await user.type(taskInput, "exceeds-limit");
  await waitFor(() => {
    assert.equal(sendButton.disabled, true);
    assert.ok(view.getByText("输入过长，请缩短后重试。"));
  });
  fireEvent.submit(form);
  assert.equal(submitCount, 0);

  await user.clear(taskInput);
  await user.type(taskInput, "Normal");
  await waitFor(() => {
    assert.equal(sendButton.disabled, false);
  });
  fireEvent.submit(form);
  assert.equal(submitCount, 1);
  cleanup();
}

async function runStreamingSuccessScenario() {
  dom.reconfigure({ url: "http://localhost/" });
  const user = userEvent.setup({ document: dom.window.document });
  const sentPayloads: Array<{ text: string; structuredInput?: StructuredInputModel }> = [];

  const createdThread = {
    thread: threadSummary("New thread", "Awaiting first message."),
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
      return jsonResponse(liveAgentCatalogPayload());
    }
    if (url.endsWith("/api/threads/thread-live-1/messages/stream") && method === "POST") {
      const payload = JSON.parse(String(init?.body ?? "{}")) as {
        text?: string;
        structuredInput?: StructuredInputModel;
      };
      sentPayloads.push({
        text: payload.text ?? "",
        structuredInput: payload.structuredInput,
      });

      const ordinaryUser = sentPayloads[0];
      const structuredUser = sentPayloads[1];

      if (sentPayloads.length === 1) {
        const ordinaryAnswer = "Short live summary with the conclusion first.";
        return ndjsonResponse([
          {
            type: "run.started",
            data: { threadId: "thread-live-1", continuityMode: "replay" },
          },
          {
            type: "workflow.stage",
            data: {
              currentStage: "analysis",
              stages: [
                { key: "routing", title: "\u8def\u7531\u89c4\u5212", status: "completed" },
                { key: "analysis", title: "\u591a\u89d2\u5ea6\u5206\u6790", status: "running" },
                { key: "risk", title: "\u98ce\u9669\u6821\u9a8c", status: "waiting" },
                { key: "summary", title: "\u6c47\u603b\u7ed3\u8bba", status: "waiting" },
                { key: "fusion", title: "\u878d\u5408\u5224\u65ad", status: "waiting" },
              ],
            },
          },
          {
            type: "workflow.snapshot",
            data: {
              workflow: {
                ...(assistantTurn("assistant-live-1", ordinaryAnswer).workflow ?? {}),
              },
              runId: "run-stream-1",
              continuityMode: "replay",
            },
          },
          {
            type: "answer.final",
            data: {
              response: {
                thread: threadSummary("Market risk summary", ordinaryAnswer),
                assistantTurn: assistantTurn("assistant-live-1", ordinaryAnswer),
                turns: [
                  {
                    id: "user-live-1",
                    role: "user",
                    text: ordinaryUser.text,
                    createdAt: "2026-04-04 18:05",
                    structuredInput: ordinaryUser.structuredInput,
                  },
                  assistantTurn("assistant-live-1", ordinaryAnswer),
                ],
              },
            },
          },
        ]);
      }

      const structuredAnswer = "Structured live summary generated from task, notes, and URL references.";
      return ndjsonResponse([
        {
          type: "run.started",
          data: { threadId: "thread-live-1", continuityMode: "replay" },
        },
        {
          type: "workflow.stage",
          data: {
            currentStage: "summary",
            stages: [
              { key: "routing", title: "\u8def\u7531\u89c4\u5212", status: "completed" },
              { key: "analysis", title: "\u591a\u89d2\u5ea6\u5206\u6790", status: "completed" },
              { key: "risk", title: "\u98ce\u9669\u6821\u9a8c", status: "completed" },
              { key: "summary", title: "\u6c47\u603b\u7ed3\u8bba", status: "running" },
              { key: "fusion", title: "\u878d\u5408\u5224\u65ad", status: "waiting" },
            ],
          },
        },
        {
          type: "workflow.snapshot",
          data: {
            workflow: {
              ...(assistantTurn("assistant-live-2", structuredAnswer).workflow ?? {}),
            },
            runId: "run-stream-2",
            continuityMode: "replay",
          },
        },
        {
          type: "answer.final",
          data: {
            response: {
              thread: threadSummary("Structured summary", structuredAnswer),
              assistantTurn: assistantTurn("assistant-live-2", structuredAnswer),
              turns: [
                {
                  id: "user-live-1",
                  role: "user",
                  text: ordinaryUser.text,
                  createdAt: "2026-04-04 18:05",
                  structuredInput: ordinaryUser.structuredInput,
                },
                assistantTurn("assistant-live-1", "Short live summary with the conclusion first."),
                {
                  id: "user-live-2",
                  role: "user",
                  text: structuredUser.text,
                  createdAt: "2026-04-04 18:06",
                  structuredInput: structuredUser.structuredInput,
                },
                assistantTurn("assistant-live-2", structuredAnswer),
              ],
            },
          },
        },
      ]);
    }
    if (url.endsWith("/api/threads/thread-live-1/messages") && method === "POST") {
      return jsonResponse(
        {
          detail: {
            code: "sync_path_unexpected",
            message: "Streaming path should be preferred.",
            category: "request",
          },
        },
        500,
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

  const taskInput = view.container.querySelector("#chat-composer") as HTMLTextAreaElement;
  const toggleButton = view.container.querySelector(".composer__toggle") as HTMLButtonElement;
  await user.type(taskInput, "Summarize the market risk profile.");
  await waitFor(() => {
    assert.equal((view.container.querySelector(".composer__submit") as HTMLButtonElement).hasAttribute("disabled"), false);
  });
  await user.click(view.container.querySelector(".composer__submit") as HTMLButtonElement);

  await waitFor(() => {
    assert.ok(view.getByText("\u6b63\u5728\u534f\u4f5c\u2026"));
  });
  await waitFor(() => {
    assert.ok(view.getByText("\u591a\u89d2\u5ea6\u5206\u6790"));
    assert.ok(view.getByText("\u8fdb\u884c\u4e2d"));
  });
  await waitFor(() => {
    assert.ok(view.getByText("Short live summary with the conclusion first."));
  });

  assert.equal(sentPayloads[0].text, "Summarize the market risk profile.");
  assert.deepEqual(sentPayloads[0].structuredInput, { task: "Summarize the market risk profile." });

  await user.click(toggleButton);

  const structuredDraft = {
    task: "Draft a concise committee summary.",
    context: "The subject is a public EV company with continuing pricing pressure.",
    materialsText:
      "Material one: earnings-call notes highlight pricing pressure.\n\nMaterial two: policy notes emphasize subsidy discipline.",
    urlReferencesText: "https://example.com/policy-brief\nhttps://example.com/company-update",
    constraints: "Use only public information.",
    outputPreference: "Respond in Chinese with the conclusion first.",
  };
  const compiledStructuredText = composeStructuredPrompt(structuredDraft);
  const expectedStructuredInput = toStructuredInputModel(structuredDraft);
  assert.ok(expectedStructuredInput);

  await user.clear(taskInput);
  await user.type(taskInput, structuredDraft.task);
  await user.type(view.container.querySelector("#chat-context") as HTMLTextAreaElement, structuredDraft.context);
  await user.type(view.container.querySelector("#chat-materials") as HTMLTextAreaElement, structuredDraft.materialsText);
  await user.type(
    view.container.querySelector("#chat-url-references") as HTMLTextAreaElement,
    structuredDraft.urlReferencesText,
  );
  await user.type(view.container.querySelector("#chat-constraints") as HTMLTextAreaElement, structuredDraft.constraints);
  await user.type(
    view.container.querySelector("#chat-output-preference") as HTMLTextAreaElement,
    structuredDraft.outputPreference,
  );
  await user.click(view.container.querySelector(".composer__submit") as HTMLButtonElement);

  await waitFor(() => {
    assert.ok(view.getByText("Structured live summary generated from task, notes, and URL references."));
  });

  assert.equal(sentPayloads[1].text, compiledStructuredText);
  assert.deepEqual(sentPayloads[1].structuredInput, expectedStructuredInput);
  assert.equal(
    view.getByRole("link", { name: "https://example.com/policy-brief" }).getAttribute("href"),
    "https://example.com/policy-brief",
  );

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
        thread: threadSummary("New thread", "Awaiting first message."),
        turns: [],
      });
    }
    if (url.endsWith("/api/agents") && method === "GET") {
      return jsonResponse(liveAgentCatalogPayload());
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
            currentStage: "risk",
            stages: [
              { key: "routing", title: "\u8def\u7531\u89c4\u5212", status: "completed" },
              { key: "analysis", title: "\u591a\u89d2\u5ea6\u5206\u6790", status: "completed" },
              { key: "risk", title: "\u98ce\u9669\u6821\u9a8c", status: "running" },
              { key: "summary", title: "\u6c47\u603b\u7ed3\u8bba", status: "waiting" },
              { key: "fusion", title: "\u878d\u5408\u5224\u65ad", status: "waiting" },
            ],
          },
        },
        {
          type: "error",
          data: {
            code: "runtime_invoke_unavailable",
            message: "LangGraph runtime invocation failed before a public answer could be produced.",
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
  const taskInput = view.container.querySelector("#chat-composer") as HTMLTextAreaElement;
  await user.type(taskInput, failingPrompt);
  await user.click(view.container.querySelector(".composer__submit") as HTMLButtonElement);

  await waitFor(() => {
    assert.ok(view.getByText("\u6b63\u5728\u534f\u4f5c\u2026"));
  });
  await waitFor(() => {
    assert.ok(view.getByText((content) => content.includes("LangGraph runtime invocation failed before a public answer could be produced.")));
  });
  await waitFor(() => {
    assert.equal(view.queryByText("\u6b63\u5728\u534f\u4f5c\u2026"), null);
  });
  assert.equal(view.queryByText(failingPrompt), null);

  cleanup();
}

async function runHistoryMutationScenario() {
  dom.reconfigure({ url: "http://localhost/" });
  const user = userEvent.setup({ document: dom.window.document });
  const confirmCalls: string[] = [];
  const originalConfirm = dom.window.confirm;
  const confirmHandler = (message?: string) => {
    confirmCalls.push(message ?? "");
    return true;
  };
  dom.window.confirm = confirmHandler;
  globalThis.confirm = confirmHandler;

  const activeThread = historyThreadSummary("thread-live-1", "Active Thread", "Stored answer before clear.");
  const oldThread = historyThreadSummary("thread-old-2", "Old Thread", "Older answer.");
  let deletedThreadId: string | null = null;
  let clearedThreadId: string | null = null;

  installFetchMock(async (url, init) => {
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/health")) {
      return jsonResponse(degradedHealthPayload());
    }
    if (url.endsWith("/api/threads") && method === "GET") {
      const threads = deletedThreadId ? [activeThread] : [activeThread, oldThread];
      return jsonResponse({ threads });
    }
    if (url.endsWith("/api/threads/thread-live-1") && method === "GET") {
      return jsonResponse({
        thread: activeThread,
        turns: [
          {
            id: "user-before-clear",
            role: "user",
            text: "Stored prompt before clear.",
            createdAt: "2026-04-04 18:04",
          },
          assistantTurn("assistant-before-clear", "Stored answer before clear."),
        ],
      });
    }
    if (url.endsWith("/api/threads/thread-live-1/messages") && method === "DELETE") {
      clearedThreadId = "thread-live-1";
      return jsonResponse({
        thread: { ...activeThread, preview: "Awaiting first message.", updatedAt: "2026-04-04 18:08" },
        turns: [],
      });
    }
    if (url.endsWith("/api/threads/thread-old-2") && method === "DELETE") {
      deletedThreadId = "thread-old-2";
      return new Response(null, { status: 204 });
    }
    if (url.endsWith("/api/agents") && method === "GET") {
      return jsonResponse(liveAgentCatalogPayload());
    }

    return jsonResponse(
      { detail: { code: "unhandled_request", message: `Unhandled request: ${method} ${url}`, category: "request" } },
      500,
    );
  });

  const view = render(<App />);

  await waitFor(() => {
    assert.ok(view.getByText("Stored answer before clear."));
  });

  await user.click(view.getByRole("button", { name: "清空记录" }));
  await waitFor(() => {
    assert.equal(clearedThreadId, "thread-live-1");
    assert.equal(view.queryByText("Stored answer before clear."), null);
    assert.ok(view.getByText("从一个问题开始"));
  });

  await user.click(view.getByRole("button", { name: "删除会话: Old Thread" }));
  await waitFor(() => {
    assert.equal(deletedThreadId, "thread-old-2");
    assert.equal(view.queryByText("Old Thread"), null);
  });

  assert.deepEqual(confirmCalls, ["确认清空当前会话记录？此操作不可撤销。", "确认删除此会话？此操作不可撤销。"]);
  dom.window.confirm = originalConfirm;
  cleanup();
}

async function runUnavailableScenario() {
  dom.reconfigure({ url: "http://localhost/" });
  installFetchMock(async () => {
    throw new Error("connect ECONNREFUSED");
  });

  const view = render(<App />);
  const taskInput = view.container.querySelector("#chat-composer") as HTMLTextAreaElement;

  await waitFor(() => {
    assert.ok(view.getByText((content) => content.includes("系统暂时不可用，请稍后重试")));
  });
  assert.equal(taskInput.disabled, true);

  cleanup();
}

async function runSmoke() {
  runStructuredInputHelperChecks();
  await runUserBubbleStructuredRenderChecks();
  await runAssistantMarkdownRenderChecks();
  await runComposerLengthLimitChecks();
  await runStreamingSuccessScenario();
  await runStreamingErrorScenario();
  await runHistoryMutationScenario();
  await runUnavailableScenario();
  console.log("Frontend live integration smoke checks passed.");
}

runSmoke().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
