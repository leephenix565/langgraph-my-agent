export interface AgentDescriptor {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
  layer: "L1" | "L2" | "L3" | "L4";
  team: string;
  roleType?: string;
  defaultEnabled: boolean;
}

export interface AgentLayerGroup {
  layer: "L1" | "L2" | "L3" | "L4";
  agents: AgentDescriptor[];
}

export interface AgentCatalogModel {
  totals: {
    configCount: number;
    runtimeCount: number;
    disabledIds: string[];
  };
  layers: AgentLayerGroup[];
  disabledAgents: AgentDescriptor[];
}
