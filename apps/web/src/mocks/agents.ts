import type { AgentCatalogModel } from "../types/agents";

export const AGENT_CATALOG: AgentCatalogModel = {
  totals: {
    configCount: 5,
    runtimeCount: 4,
    disabledIds: ["a02_task_router"],
  },
  layers: [
    {
      layer: "L1",
      agents: [
        {
          id: "a01_cio_orchestrator",
          name: "CIO Orchestrator",
          description: "Coordinates the layered workflow and final alignment.",
          capabilities: ["orchestrate", "prioritize"],
          layer: "L1",
          team: "management",
          roleType: "system",
          defaultEnabled: true,
        },
      ],
    },
    {
      layer: "L2",
      agents: [
        {
          id: "a03_macro_policy",
          name: "Macro Policy Analyst",
          description: "Tracks macro and policy signals for research planning.",
          capabilities: ["macro", "policy"],
          layer: "L2",
          team: "research",
          roleType: "system",
          defaultEnabled: true,
        },
      ],
    },
    {
      layer: "L3",
      agents: [
        {
          id: "a21_reg_compliance",
          name: "Compliance Monitor",
          description: "Maps public guidance into compliance checks.",
          capabilities: ["compliance"],
          layer: "L3",
          team: "compliance",
          roleType: "system",
          defaultEnabled: true,
        },
      ],
    },
    {
      layer: "L4",
      agents: [
        {
          id: "a25_report_center",
          name: "Report Center",
          description: "Builds the final external-facing answer.",
          capabilities: ["report", "synthesis"],
          layer: "L4",
          team: "reporting",
          roleType: "system",
          defaultEnabled: true,
        },
      ],
    },
  ],
  disabledAgents: [
    {
      id: "a02_task_router",
      name: "Task Decomposer",
      description: "Reserved for experiments and disabled by default.",
      capabilities: ["route", "plan"],
      layer: "L1",
      team: "management",
      roleType: "system",
      defaultEnabled: false,
    },
  ],
};
