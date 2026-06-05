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
import type { PublicTurn, StructuredInputModel } from "../types/chat";
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

function threadSummary(title: string, preview: string) {
  return {
    id: "thread-live-1",
    title,
    updatedAt: "2026-04-04 18:06",
    preview,
    finalSource: "reset_skeleton",
    phase: "Live",
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
      citations: [{ label: "Fixed DAG bundle", note: "Final answer came from the public fixed DAG projection." }],
      evidenceCards: [{ title: "Workflow", note: "Structured public-safe output." }],
      evidenceCount: 1,
    },
    workflow: createWorkflowVariant(id),
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
  assert.equal(agentNameLabel("macro_commodity_pricing"), "Commodity pricing");
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

const forbiddenUiTokens = ["layerPlan", "layerMode", "agentSteps", "fusionSteps", "default_url", "env_var", "mainline", "baseline", "fused", "Fusion"];

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
  assert.equal(workflow.stepResults.route_planner?.runtime_kind, "deterministic_skeleton");
  assert.equal(workflow.stepResults.financial_data_service?.runtime_kind, "external_http_candidate");
  assert.equal(workflow.stepResults.sentiment_company_radar?.runtime_kind, "placeholder");
  assertNoForbiddenSerializedTokens(serialized);
}

function runTranscriptBoundaryChecks() {
  for (const turns of Object.values(TRANSCRIPTS_BY_SESSION)) {
    for (const turn of turns) {
      assert.ok(turn.role === "user" || turn.role === "assistant");
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
    "### Market Summary",
    "",
    "This paragraph contains **strong emphasis** and *supporting nuance*.",
    "",
    "- First point",
    "- Second point",
    "",
    "Watch the `run_id` field.",
  ].join("\n");

  const view = render(<AssistantAnswerCard turn={assistantTurn("assistant-markdown-1", markdownAnswer)} />);
  const article = view.getByRole("article");
  assert.equal(view.queryByText("### Market Summary"), null);
  assert.ok(view.getByRole("heading", { level: 3, name: "Market Summary" }));
  assert.ok(article.querySelector("strong"));
  assert.ok(article.querySelector("em"));
  fireEvent.click(view.getByRole("button", { name: /Workflow/ }));
  assert.ok(view.getByLabelText("Fixed DAG workflow inspector"));
  assert.ok(view.getByText("Stage timeline"));
  assert.ok(view.getAllByText("Route planner").length >= 1);
  assert.ok(view.getByText("Execution batches"));
  assert.ok(view.getByText("Dimension groups"));
  assert.ok(view.getByText("DAG step list"));
  assert.ok(view.getByText("Step result metadata"));
  assert.ok(view.getByText("Final source and provenance"));
  assert.ok(view.getAllByText("Fixed DAG skeleton").length >= 1);

  assert.ok(view.getByText("Selected step"));
  assert.ok(view.getByText("Runtime kind"));
  assert.ok(view.getAllByText("deterministic_skeleton").length >= 1);
  assert.ok(view.getByText("Implementation status"));
  assert.ok(view.getAllByText("No").length >= 2);

  fireEvent.click(view.getByRole("button", { name: /Financial data service/ }));
  assert.equal(view.getByRole("button", { name: /Financial data service/ }).getAttribute("aria-pressed"), "true");
  assert.ok(view.getAllByText("financial_data_service").length >= 1);
  assert.ok(view.getAllByText("external_http_candidate").length >= 1);
  assert.ok(view.getAllByText("external_candidate_disabled").length >= 1);
  assert.ok(view.getByText("External candidate is registered but not live verified in the mock path."));

  fireEvent.click(view.getByRole("button", { name: /Company sentiment radar/ }));
  assert.equal(view.getByRole("button", { name: /Company sentiment radar/ }).getAttribute("aria-pressed"), "true");
  assert.ok(view.getAllByText("placeholder").length >= 1);
  assert.ok(view.getAllByText("pending_implementation").length >= 1);
  assert.ok(view.getByText("Market sentiment path is placeholder-only in the local fixture."));

  assertNoForbiddenUiTokens(article.textContent);
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
    assert.ok(view.getByText("Input is too long. Please shorten it and try again."));
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
  const sentPayloads: Array<{ text: string; structuredInput?: StructuredInputModel }> = [];
  let finalRoles: string[] = [];

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
      return jsonResponse(AGENT_CATALOG);
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
      const answer = "Short live summary with the conclusion first.";
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
                { key: "planning", title: "Planning", status: "completed" },
                { key: "evidence", title: "Evidence seams", status: "completed" },
                { key: "l2_analysis", title: "L2 analysis", status: "running" },
                { key: "dimension_composite", title: "Dimension composites", status: "waiting" },
                { key: "decision", title: "Decision", status: "waiting" },
                { key: "report", title: "Report", status: "waiting" },
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
                thread: threadSummary("Market risk summary", answer),
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

  const taskInput = view.container.querySelector("#chat-composer") as HTMLTextAreaElement;
  await user.type(taskInput, "Summarize the market risk profile.");
  await waitFor(() => {
    assert.equal((view.container.querySelector(".composer__submit") as HTMLButtonElement).hasAttribute("disabled"), false);
  });
  await user.click(view.container.querySelector(".composer__submit") as HTMLButtonElement);

  await waitFor(() => {
    assert.ok(view.getByText("Short live summary with the conclusion first."));
  });
  assert.ok(view.getAllByText("Fixed DAG skeleton").length >= 1);

  assert.equal(sentPayloads[0].text, "Summarize the market risk profile.");
  assert.deepEqual(sentPayloads[0].structuredInput, { task: "Summarize the market risk profile." });
  assert.deepEqual(finalRoles, ["user", "assistant"]);
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
        thread: threadSummary("New thread", "Awaiting first message."),
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
              { key: "planning", title: "Planning", status: "completed" },
              { key: "evidence", title: "Evidence seams", status: "running" },
              { key: "l2_analysis", title: "L2 analysis", status: "waiting" },
              { key: "dimension_composite", title: "Dimension composites", status: "waiting" },
              { key: "decision", title: "Decision", status: "waiting" },
              { key: "report", title: "Report", status: "waiting" },
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
  await user.type(view.container.querySelector("#chat-composer") as HTMLTextAreaElement, failingPrompt);
  await user.click(view.container.querySelector(".composer__submit") as HTMLButtonElement);

  await waitFor(() => {
    assert.ok(view.getByText((content) => content.includes("LangGraph runtime invocation failed before a public answer could be produced.")));
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
  await runComposerLengthLimitChecks();
  await runStreamingSuccessScenario();
  await runStreamingErrorScenario();
  console.log("Frontend fixed DAG contract smoke checks passed.");
}

runSmoke().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
