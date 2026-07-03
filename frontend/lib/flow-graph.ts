import type { Edge, Node } from "@xyflow/react";

export type IntentValue =
  | "chitchat"
  | "knowledge_qa"
  | "multimodal_doc"
  | "tool_action"
  | "complex_task"
  | "clarification_needed"
  | "unsupported_or_rejected";

export const intentValues: IntentValue[] = [
  "chitchat",
  "knowledge_qa",
  "multimodal_doc",
  "tool_action",
  "complex_task",
  "clarification_needed",
  "unsupported_or_rejected",
];

export type GraphNodeSpec = {
  id: string;
  type: string;
  config?: Record<string, unknown>;
};

export type GraphEdgeSpec = {
  from: string;
  to: string;
  condition?: string | null;
};

export type GraphConfig = {
  version?: number;
  nodes: GraphNodeSpec[];
  edges: GraphEdgeSpec[];
  entry: string;
  exits: string[];
};

export type FlowNodeData = {
  nodeType: string;
  config: Record<string, unknown>;
  entry?: boolean;
  exit?: boolean;
  label?: string;
};

export type FlowEdgeData = {
  condition?: string | null;
};

export type GraphFlow = {
  version?: number;
  nodes: Node<FlowNodeData>[];
  edges: Edge<FlowEdgeData>[];
};

const nodeGapX = 280;
const nodeGapY = 112;

export function graphConfigToFlow(config: GraphConfig): GraphFlow {
  return {
    version: config.version,
    nodes: config.nodes.map((node, index) => ({
      id: node.id,
      type: node.type,
      position: { x: (index % 3) * nodeGapX, y: Math.floor(index / 3) * nodeGapY },
      data: {
        nodeType: node.type,
        config: node.config ?? {},
        entry: node.id === config.entry,
        exit: config.exits.includes(node.id),
        label: labelForType(node.type),
      },
    })),
    edges: config.edges.map((edge) => {
      const condition = edge.condition ?? null;
      return {
        id: edgeId(edge.from, edge.to, condition),
        source: edge.from,
        target: edge.to,
        animated: Boolean(condition),
        className: condition ? "condition-edge" : undefined,
        label: condition || undefined,
        data: { condition },
      };
    }),
  };
}

export function flowToGraphConfig(flow: GraphFlow): GraphConfig {
  const nodes = flow.nodes.map((node) => ({
    id: node.id,
    type: node.data.nodeType,
    config: node.data.config ?? {},
  }));
  const entry =
    flow.nodes.find((node) => node.data.entry)?.id ??
    flow.nodes.find((node) => !flow.edges.some((edge) => edge.target === node.id))?.id ??
    flow.nodes[0]?.id ??
    "";
  const exits = flow.nodes
    .filter((node) => node.data.exit)
    .map((node) => node.id);
  const inferredExits = exits.length
    ? exits
    : flow.nodes
        .filter((node) => !flow.edges.some((edge) => edge.source === node.id))
        .map((node) => node.id);
  return {
    version: flow.version ?? 1,
    entry,
    exits: inferredExits.length ? inferredExits : entry ? [entry] : [],
    nodes,
    edges: flow.edges.map((edge) => ({
      from: edge.source,
      to: edge.target,
      condition: edge.data?.condition || undefined,
    })),
  };
}

export function isControlledCondition(condition: string): boolean {
  const normalized = condition.replace(/\s+/g, "");
  const [field, value, extra] = normalized.split("=");
  return field === "intent" && !extra && intentValues.includes(value as IntentValue);
}

export function makeCondition(value: IntentValue): string {
  return `intent=${value}`;
}

export function labelForType(type: string): string {
  return type
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function edgeId(source: string, target: string, condition: string | null): string {
  return `${source}-${target}${condition ? `-${condition.replace(/[^a-z0-9_]+/gi, "-")}` : ""}`;
}
