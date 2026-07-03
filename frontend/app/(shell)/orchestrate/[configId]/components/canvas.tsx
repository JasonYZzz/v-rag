"use client";

import {
  Background,
  Controls,
  type Edge,
  type Node,
  ReactFlow,
  type ReactFlowProps,
} from "@xyflow/react";
import { useCallback } from "react";

import type { FlowEdgeData, FlowNodeData } from "@/lib/flow-graph";
import { useOrchestrationStore } from "@/lib/orchestration-store";
import { cn } from "@/lib/utils";

type CanvasProps = {
  nodes: Node<FlowNodeData>[];
  edges: Edge<FlowEdgeData>[];
  nodeTypes?: ReactFlowProps["nodeTypes"];
  onNodesChange?: ReactFlowProps<Node<FlowNodeData>, Edge<FlowEdgeData>>["onNodesChange"];
  onEdgesChange?: ReactFlowProps<Node<FlowNodeData>, Edge<FlowEdgeData>>["onEdgesChange"];
  onConnect?: ReactFlowProps<Node<FlowNodeData>, Edge<FlowEdgeData>>["onConnect"];
  onNodeClick?: ReactFlowProps<Node<FlowNodeData>, Edge<FlowEdgeData>>["onNodeClick"];
  onEdgeClick?: ReactFlowProps<Node<FlowNodeData>, Edge<FlowEdgeData>>["onEdgeClick"];
  readonly?: boolean;
  className?: string;
};

export function OrchestrationCanvas({
  nodes,
  edges,
  nodeTypes,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onEdgeClick,
  readonly = false,
  className,
}: CanvasProps) {
  const addNode = useOrchestrationStore((state) => state.addNode);
  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      const type = event.dataTransfer.getData("application/vrag-node-type");
      if (type) {
        event.preventDefault();
        addNode(type);
      }
    },
    [addNode],
  );
  return (
    <div
      className={cn("h-full min-h-[520px] overflow-hidden rounded-[10px] border border-border", className)}
      onDragOver={(event) => event.preventDefault()}
      onDrop={handleDrop}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={readonly ? undefined : onNodesChange}
        onEdgesChange={readonly ? undefined : onEdgesChange}
        onConnect={readonly ? undefined : onConnect}
        onNodeClick={readonly ? undefined : onNodeClick}
        onEdgeClick={readonly ? undefined : onEdgeClick}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={!readonly}
        nodesConnectable={!readonly}
        elementsSelectable={!readonly}
        className="bg-bg text-text"
      >
        <Background color="var(--border)" gap={24} size={1} />
        <Controls
          showInteractive={false}
          className="overflow-hidden rounded-[8px] border border-border bg-surface text-text shadow-sm"
        />
      </ReactFlow>
    </div>
  );
}
