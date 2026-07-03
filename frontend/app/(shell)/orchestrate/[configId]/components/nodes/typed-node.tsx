"use client";

import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { Brain, ChatCircleText, Database, GitBranch, MagnifyingGlass, PencilSimpleLine, Prohibit, Sparkle } from "@phosphor-icons/react";

import type { FlowNodeData } from "@/lib/flow-graph";
import { cn } from "@/lib/utils";

const nodeMeta = {
  classifier: { title: "Classifier", icon: GitBranch },
  retrieve: { title: "Retrieve", icon: MagnifyingGlass },
  generate: { title: "Generate", icon: Sparkle },
  clarification: { title: "Clarify", icon: ChatCircleText },
  unsupported: { title: "Unsupported", icon: Prohibit },
  memory_recall: { title: "Memory recall", icon: Database },
  memory_write: { title: "Memory write", icon: PencilSimpleLine },
  reflect: { title: "Reflect", icon: Brain },
};

export function TypedNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const meta = nodeMeta[data.nodeType as keyof typeof nodeMeta] ?? { title: data.nodeType, icon: Brain };
  const Icon = meta.icon;
  return (
    <div
      className={cn(
        "min-w-[180px] rounded-[8px] border border-border bg-surface px-3 py-3 shadow-sm",
        selected && "border-accent shadow-[0_0_0_2px_color-mix(in_oklch,var(--accent)_20%,transparent)]",
      )}
    >
      <Handle type="target" position={Position.Left} className="!h-2.5 !w-2.5 !border-border !bg-bg" />
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-[7px] bg-accent/10 text-accent">
          <Icon size={16} />
        </span>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{meta.title}</div>
          <div className="font-mono text-[11px] text-muted">{data.nodeType}</div>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-normal text-muted">
        {data.entry ? <span className="rounded-[5px] bg-accent/10 px-1.5 py-0.5 text-accent">Entry</span> : null}
        {data.exit ? <span className="rounded-[5px] bg-surface-2 px-1.5 py-0.5">Exit</span> : null}
      </div>
      <Handle type="source" position={Position.Right} className="!h-2.5 !w-2.5 !border-border !bg-accent" />
    </div>
  );
}

export const orchestrationNodeTypes = {
  classifier: TypedNode,
  retrieve: TypedNode,
  generate: TypedNode,
  clarification: TypedNode,
  unsupported: TypedNode,
  memory_recall: TypedNode,
  memory_write: TypedNode,
  reflect: TypedNode,
};
