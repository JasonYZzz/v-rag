"use client";

import { useEffect, useMemo } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Edge, Node } from "@xyflow/react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getGraph, getRegistry, saveDraft } from "@/lib/graphs-api";
import { flowToGraphConfig, graphConfigToFlow, type FlowEdgeData, type FlowNodeData } from "@/lib/flow-graph";
import { useOrchestrationStore } from "@/lib/orchestration-store";
import { OrchestrationCanvas } from "./components/canvas";
import { EdgeConditionEditor } from "./components/edge-condition-editor";
import { NodePalette } from "./components/node-palette";
import { NodeParamForm } from "./components/node-param-form";
import { orchestrationNodeTypes } from "./components/nodes/typed-node";
import { TestRunPanel } from "./components/test-run-panel";
import { VersionPanel } from "./components/version-panel";

export default function OrchestrateEditorPage() {
  const params = useParams<{ configId: string }>();
  const configId = params.configId;
  const queryClient = useQueryClient();
  const graph = useQuery({ queryKey: ["graph", configId], queryFn: () => getGraph(configId) });
  const registry = useQuery({ queryKey: ["graphs-registry"], queryFn: getRegistry });
  const nodes = useOrchestrationStore((state) => state.nodes);
  const edges = useOrchestrationStore((state) => state.edges);
  const dirty = useOrchestrationStore((state) => state.dirty);
  const selectedNodeId = useOrchestrationStore((state) => state.selectedNodeId);
  const selectedEdgeId = useOrchestrationStore((state) => state.selectedEdgeId);
  const reset = useOrchestrationStore((state) => state.reset);
  const onNodesChange = useOrchestrationStore((state) => state.onNodesChange);
  const onEdgesChange = useOrchestrationStore((state) => state.onEdgesChange);
  const onConnect = useOrchestrationStore((state) => state.onConnect);
  const selectNode = useOrchestrationStore((state) => state.selectNode);
  const selectEdge = useOrchestrationStore((state) => state.selectEdge);
  const patchEdgeCondition = useOrchestrationStore((state) => state.patchEdgeCondition);
  const markSaved = useOrchestrationStore((state) => state.markSaved);

  const activeVersion = useMemo(() => {
    const versions = graph.data?.versions ?? [];
    return (
      versions.find((version) => version.status === "draft") ??
      versions.find((version) => version.status === "published") ??
      versions.at(-1) ??
      null
    );
  }, [graph.data?.versions]);

  useEffect(() => {
    if (activeVersion) {
      reset(graphConfigToFlow(activeVersion.graph));
    }
  }, [activeVersion, reset]);

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId) ?? null;
  const selectedRegistry = registry.data?.find((item) => item.type === selectedNode?.data.nodeType) ?? null;

  const save = useMutation({
    mutationFn: () => saveDraft(configId, flowToGraphConfig({ version: activeVersion?.version ?? 1, nodes, edges })),
    onSuccess: () => {
      markSaved();
      queryClient.invalidateQueries({ queryKey: ["graph", configId] });
    },
  });

  if (graph.isLoading || registry.isLoading) {
    return <Skeleton className="h-[calc(100vh-96px)] w-full" />;
  }

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Visual orchestration</h1>
          <p className="mt-1 font-mono text-xs text-muted">
            {configId} · v{activeVersion?.version ?? "none"} {dirty ? "· unsaved" : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="secondary" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
            Save draft
          </Button>
        </div>
      </header>
      <div className="rounded-[10px] border border-warn/30 bg-warn/10 p-3 text-sm text-muted xl:hidden">
        Canvas editing is optimized for desktop width. This view remains available for review on smaller screens.
      </div>
      {save.isError ? (
        <div className="rounded-[10px] border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {(save.error as Error).message || "Failed to save draft"}
        </div>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-[260px_minmax(0,1fr)_340px]">
        <aside className="space-y-4 rounded-[10px] border border-border bg-surface p-3">
          <NodePalette nodes={registry.data ?? []} />
        </aside>
        <section className="min-h-[620px]">
          <OrchestrationCanvas
            nodes={nodes}
            edges={edges}
            nodeTypes={orchestrationNodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_event, node: Node<FlowNodeData>) => selectNode(node.id)}
            onEdgeClick={(_event, edge: Edge<FlowEdgeData>) => selectEdge(edge.id)}
          />
        </section>
        <aside className="space-y-4 rounded-[10px] border border-border bg-surface p-3">
          <NodeParamForm node={selectedNode} schema={selectedRegistry?.config_schema ?? null} />
          {selectedEdge ? (
            <EdgeConditionEditor
              value={selectedEdge.data?.condition ?? null}
              onChange={(condition) => patchEdgeCondition(selectedEdge.id, condition)}
            />
          ) : null}
          <VersionPanel
            configId={configId}
            versions={graph.data?.versions ?? []}
            activeVersion={activeVersion?.version ?? null}
          />
          <TestRunPanel configId={configId} version={activeVersion?.version ?? null} />
        </aside>
      </div>
    </div>
  );
}
