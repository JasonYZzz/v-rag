import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TraceView } from "@/components/playground/trace-view";

describe("TraceView", () => {
  it("renders routed path, route decision, and node IO summaries", () => {
    render(
      <TraceView
        trace={{
          id: "trace-1",
          intent: "knowledge_qa",
          route_trace: {
            reason: "semantic-direct",
            final_intent: "knowledge_qa",
            confidence: 0.92,
          },
          node_io: [
            { node_id: "classifier", output: { intent: "knowledge_qa" } },
            { node_id: "retrieve", output: { retrieved_docs: [{ chunk_id: "c1" }] } },
          ],
        }}
      />,
    );

    expect(screen.getByText("Why this route")).toBeInTheDocument();
    expect(screen.getByText("classifier")).toBeInTheDocument();
    expect(screen.getByText("retrieve")).toBeInTheDocument();
    expect(screen.getByText("semantic-direct")).toBeInTheDocument();
    expect(screen.getByText("knowledge_qa")).toBeInTheDocument();
  });
});
