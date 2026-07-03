"use client";

import { Brain, ChatCircleText, Database, GitBranch, MagnifyingGlass, PencilSimpleLine, Prohibit, Sparkle } from "@phosphor-icons/react";

import { Button } from "@/components/ui/button";
import type { RegistryNode } from "@/lib/graphs-api";
import { useOrchestrationStore } from "@/lib/orchestration-store";

const iconByType = {
  classifier: GitBranch,
  retrieve: MagnifyingGlass,
  generate: Sparkle,
  clarification: ChatCircleText,
  unsupported: Prohibit,
  memory_recall: Database,
  memory_write: PencilSimpleLine,
  reflect: Brain,
};

export function NodePalette({ nodes }: { nodes: RegistryNode[] }) {
  const addNode = useOrchestrationStore((state) => state.addNode);
  return (
    <section className="space-y-2" aria-label="Node palette">
      <h2 className="text-sm font-semibold">Node registry</h2>
      <div className="space-y-2">
        {nodes.map((node) => {
          const Icon = iconByType[node.type as keyof typeof iconByType] ?? Brain;
          return (
            <Button
              key={node.type}
              type="button"
              variant="ghost"
              className="h-auto w-full justify-start gap-3 rounded-[8px] border border-border bg-bg px-3 py-3 text-left"
              onClick={() => addNode(node.type)}
              draggable
              onDragStart={(event) => {
                event.dataTransfer.setData("application/vrag-node-type", node.type);
                event.dataTransfer.effectAllowed = "copy";
              }}
            >
              <Icon size={18} className="shrink-0 text-accent" />
              <span className="min-w-0">
                <span className="block font-mono text-xs text-text">{node.type}</span>
                <span className="mt-1 line-clamp-2 block text-xs leading-5 text-muted">
                  {node.description}
                </span>
              </span>
            </Button>
          );
        })}
      </div>
    </section>
  );
}
