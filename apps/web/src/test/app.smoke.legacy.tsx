// Legacy fixture kept for local reference only.
// The active frontend gate entry is `src/test/smoke.tsx`.

import { render, screen } from "@testing-library/react";
import { AgentCatalogView } from "../components/agents/AgentCatalogView";
import { ChatPage } from "../pages/ChatPage";
import { SettingsPage } from "../pages/SettingsPage";
import { AGENT_CATALOG } from "../mocks/agents";
import { INITIAL_SESSIONS } from "../mocks/sessions";
import { TRANSCRIPTS_BY_SESSION } from "../mocks/transcript";

describe("chat, settings, and agents shell smoke", () => {
  it("renders the chat-first shell with a single assistant answer card", () => {
    render(
      <ChatPage
        session={INITIAL_SESSIONS[2]}
        turns={TRANSCRIPTS_BY_SESSION["session-fused"]}
        onSendMessage={() => {}}
        isLoading={false}
        isSending={false}
        unavailable={false}
        degraded={false}
        errorMessage={null}
        errorMeta={null}
        health={null}
      />,
    );

    expect(screen.getByLabelText("对话线程")).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "系统回答卡片" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "任务/问题" })).toBeInTheDocument();
    expect(screen.queryByText("系统回答")).not.toBeInTheDocument();
    expect(screen.queryByText("高把握")).not.toBeInTheDocument();
  });

  it("renders the read-only settings page from the existing health payload", () => {
    render(
      <SettingsPage
        isLoading={false}
        unavailable={false}
        health={{
          status: "ok",
          apiVersion: "phase-f3",
          overallStatus: "degraded",
          checkpointer: {
            enabled: false,
            mode: "none",
            status: "disabled",
            code: "checkpointer_disabled",
          },
          continuityDefault: "replay",
          runtime: { status: "ready", code: "runtime_ready" },
          providerEnv: { status: "configured", code: "provider_env_configured" },
          searchEnv: { status: "missing", code: "search_env_missing" },
          store: "json-file",
        }}
      />,
    );

    expect(screen.getByRole("heading", { name: "系统设置" })).toBeInTheDocument();
    expect(screen.getByText("系统总体状态")).toBeInTheDocument();
    expect(screen.getByText("默认连续性模式")).toBeInTheDocument();
    expect(screen.getByText("回放连续性")).toBeInTheDocument();
    expect(screen.getByText(/弱于持久线程连续性/)).toBeInTheDocument();
    expect(screen.getByText("JSON 文件存储")).toBeInTheDocument();
  });

  it("renders the live catalog shape with role type and capabilities", () => {
    render(<AgentCatalogView catalog={AGENT_CATALOG} query="" />);

    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("Task Decomposer")).toBeInTheDocument();
    expect(screen.getAllByText("系统角色").length).toBeGreaterThan(0);
    expect(screen.getByText("orchestrate")).toBeInTheDocument();
    expect(screen.getByText("Coordinates the layered workflow and final alignment.")).toBeInTheDocument();
  });
});
