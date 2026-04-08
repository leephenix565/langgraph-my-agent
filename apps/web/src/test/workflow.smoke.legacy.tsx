// Legacy fixture kept for local reference only.
// The active frontend gate entry is `src/test/smoke.tsx`.

import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { ChatPage } from "../pages/ChatPage";
import { AgentCatalogView } from "../components/agents/AgentCatalogView";
import { AGENT_CATALOG } from "../mocks/agents";
import { INITIAL_SESSIONS } from "../mocks/sessions";
import { TRANSCRIPTS_BY_SESSION } from "../mocks/transcript";

describe("workflow and agents smoke", () => {
  it("expands the workflow panel into planning, execution, fusion, and final source sections", async () => {
    const user = userEvent.setup();

    render(
      <ChatPage
        session={INITIAL_SESSIONS[0]}
        turns={TRANSCRIPTS_BY_SESSION["session-mainline"]}
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

    const toggle = screen.getByRole("button", { name: /协作过程 路 4个阶段已完成/ });
    expect(toggle).toBeInTheDocument();
    await user.click(toggle);

    expect(screen.getByRole("heading", { name: "规划" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "执行" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "融合" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "最终来源" })).toBeInTheDocument();
  });

  it("renders a catalog grouped by runtime layers", () => {
    render(<AgentCatalogView catalog={AGENT_CATALOG} query="" />);

    expect(screen.getByRole("heading", { name: "统筹与规划" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "研究与市场情报" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "风险、估值与组合检查" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "最终成文" })).toBeInTheDocument();
  });
});
