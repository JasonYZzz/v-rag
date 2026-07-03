import { describe, expect, it } from "vitest";

import {
  filterConfigBySchema,
  isAllowedCondition,
  useOrchestrationStore,
} from "@/lib/orchestration-store";

describe("orchestration store", () => {
  it("tracks graph edits and selected node state", () => {
    const store = useOrchestrationStore.getState();
    store.reset({
      version: 1,
      nodes: [
        {
          id: "classifier",
          type: "classifier",
          position: { x: 0, y: 0 },
          data: { nodeType: "classifier", config: {}, entry: true },
        },
      ],
      edges: [],
    });

    useOrchestrationStore.getState().selectNode("classifier");
    useOrchestrationStore.getState().patchNodeConfig("classifier", { top_k: 6 });

    const state = useOrchestrationStore.getState();
    expect(state.selectedNodeId).toBe("classifier");
    expect(state.dirty).toBe(true);
    expect(state.nodes[0].data.config).toEqual({ top_k: 6 });
  });

  it("filters arbitrary config fields through JSON schema properties", () => {
    const filtered = filterConfigBySchema(
      { top_k: 5, hidden: true, mode: "fast" },
      {
        type: "object",
        properties: {
          top_k: { type: "number" },
          mode: { type: "string" },
        },
      },
    );

    expect(filtered).toEqual({ top_k: 5, mode: "fast" });
  });

  it("accepts only controlled field=value conditions", () => {
    expect(isAllowedCondition("intent=knowledge_qa")).toBe(true);
    expect(isAllowedCondition("intent=unsupported_or_rejected")).toBe(true);
    expect(isAllowedCondition("query=knowledge_qa")).toBe(false);
    expect(isAllowedCondition("intent=custom")).toBe(false);
  });
});
