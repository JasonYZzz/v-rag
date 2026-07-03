import type { Edge, Node, NodeChange, EdgeChange, Connection } from "@xyflow/react";
import { addEdge, applyEdgeChanges, applyNodeChanges } from "@xyflow/react";
import { create } from "zustand";

import {
  type FlowEdgeData,
  type FlowNodeData,
  type GraphFlow,
  isControlledCondition,
} from "@/lib/flow-graph";

export type JsonSchema = {
  type?: string;
  properties?: Record<string, JsonSchemaProperty>;
  required?: string[];
};

export type JsonSchemaProperty = {
  type?: string | string[];
  title?: string;
  description?: string;
  default?: unknown;
  enum?: unknown[];
  minimum?: number;
  maximum?: number;
};

type OrchestrationState = GraphFlow & {
  selectedNodeId: string | null;
  dirty: boolean;
  reset: (flow: GraphFlow) => void;
  selectNode: (nodeId: string | null) => void;
  setNodes: (nodes: Node<FlowNodeData>[]) => void;
  setEdges: (edges: Edge<FlowEdgeData>[]) => void;
  onNodesChange: (changes: NodeChange<Node<FlowNodeData>>[]) => void;
  onEdgesChange: (changes: EdgeChange<Edge<FlowEdgeData>>[]) => void;
  onConnect: (connection: Connection, condition?: string | null) => void;
  addNode: (type: string) => void;
  patchNodeConfig: (nodeId: string, patch: Record<string, unknown>, schema?: JsonSchema | null) => void;
  markSaved: () => void;
};

export const useOrchestrationStore = create<OrchestrationState>((set, get) => ({
  version: 1,
  nodes: [],
  edges: [],
  selectedNodeId: null,
  dirty: false,
  reset: (flow) => set({ ...flow, selectedNodeId: null, dirty: false }),
  selectNode: (selectedNodeId) => set({ selectedNodeId }),
  setNodes: (nodes) => set({ nodes, dirty: true }),
  setEdges: (edges) => set({ edges, dirty: true }),
  onNodesChange: (changes) =>
    set((state) => ({ nodes: applyNodeChanges(changes, state.nodes), dirty: true })),
  onEdgesChange: (changes) =>
    set((state) => ({ edges: applyEdgeChanges(changes, state.edges), dirty: true })),
  onConnect: (connection, condition = null) => {
    if (condition && !isAllowedCondition(condition)) {
      return;
    }
    set((state) => ({
      edges: addEdge(
        {
          ...connection,
          animated: Boolean(condition),
          className: condition ? "condition-edge" : undefined,
          label: condition || undefined,
          data: { condition },
        },
        state.edges,
      ),
      dirty: true,
    }));
  },
  addNode: (type) => {
    const index = get().nodes.length;
    const id = `${type}-${crypto.randomUUID().slice(0, 8)}`;
    set((state) => ({
      nodes: [
        ...state.nodes,
        {
          id,
          type,
          position: { x: 80 + (index % 3) * 260, y: 80 + Math.floor(index / 3) * 120 },
          data: { nodeType: type, config: {}, entry: state.nodes.length === 0 },
        },
      ],
      selectedNodeId: id,
      dirty: true,
    }));
  },
  patchNodeConfig: (nodeId, patch, schema = null) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              data: {
                ...node.data,
                config: {
                  ...node.data.config,
                  ...(schema ? filterConfigBySchema(patch, schema) : patch),
                },
              },
            }
          : node,
      ),
      dirty: true,
    })),
  markSaved: () => set({ dirty: false }),
}));

export function filterConfigBySchema(
  config: Record<string, unknown>,
  schema?: JsonSchema | null,
): Record<string, unknown> {
  if (!schema?.properties) {
    return {};
  }
  return Object.fromEntries(
    Object.entries(config).filter(([key]) => Object.hasOwn(schema.properties ?? {}, key)),
  );
}

export function isAllowedCondition(condition: string): boolean {
  return isControlledCondition(condition);
}
