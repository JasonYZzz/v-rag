import { describe, expect, it } from "vitest";

import {
  flowToGraphConfig,
  graphConfigToFlow,
  isControlledCondition,
} from "@/lib/flow-graph";

describe("flow-graph conversion", () => {
  it("converts GraphConfig to React Flow nodes and edges", () => {
    const flow = graphConfigToFlow({
      version: 2,
      entry: "classifier",
      exits: ["generate"],
      nodes: [
        { id: "classifier", type: "classifier", config: {} },
        { id: "generate", type: "generate", config: { tone: "short" } },
      ],
      edges: [{ from: "classifier", to: "generate", condition: "intent=knowledge_qa" }],
    });

    expect(flow.nodes[0]).toMatchObject({
      id: "classifier",
      type: "classifier",
      data: { nodeType: "classifier", config: {}, entry: true, exit: false },
    });
    expect(flow.nodes[1].data.config).toEqual({ tone: "short" });
    expect(flow.edges[0]).toMatchObject({
      source: "classifier",
      target: "generate",
      data: { condition: "intent=knowledge_qa" },
      animated: true,
    });
  });

  it("round-trips Flow nodes and edges to GraphConfig", () => {
    const graph = flowToGraphConfig({
      version: 3,
      nodes: [
        {
          id: "classifier",
          type: "classifier",
          position: { x: 0, y: 0 },
          data: { nodeType: "classifier", config: {}, entry: true },
        },
        {
          id: "generate",
          type: "generate",
          position: { x: 320, y: 0 },
          data: { nodeType: "generate", config: {}, exit: true },
        },
      ],
      edges: [
        {
          id: "classifier-generate",
          source: "classifier",
          target: "generate",
          data: { condition: "intent=chitchat" },
        },
      ],
    });

    expect(graph).toEqual({
      version: 3,
      entry: "classifier",
      exits: ["generate"],
      nodes: [
        { id: "classifier", type: "classifier", config: {} },
        { id: "generate", type: "generate", config: {} },
      ],
      edges: [{ from: "classifier", to: "generate", condition: "intent=chitchat" }],
    });
  });

  it("recovers entry and exits when Flow metadata is missing", () => {
    const graph = flowToGraphConfig({
      nodes: [
        {
          id: "a",
          type: "default",
          position: { x: 0, y: 0 },
          data: { nodeType: "classifier", config: {} },
        },
        {
          id: "b",
          type: "default",
          position: { x: 0, y: 120 },
          data: { nodeType: "generate", config: {} },
        },
      ],
      edges: [{ id: "a-b", source: "a", target: "b" }],
    });

    expect(graph.entry).toBe("a");
    expect(graph.exits).toEqual(["b"]);
  });

  it("validates controlled conditions", () => {
    expect(isControlledCondition("intent=knowledge_qa")).toBe(true);
    expect(isControlledCondition("intent = unsupported_or_rejected")).toBe(true);
    expect(isControlledCondition("query=hello")).toBe(false);
    expect(isControlledCondition("intent=drop table")).toBe(false);
  });
});
