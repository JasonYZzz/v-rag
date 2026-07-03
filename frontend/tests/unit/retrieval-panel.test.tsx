import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RetrievalPanel } from "@/components/chat/retrieval-panel";

describe("RetrievalPanel", () => {
  it("renders retrieved chunk metadata and text", () => {
    render(
      <RetrievalPanel
        chunks={[
          {
            chunk_id: "c1",
            text: "indexed source text",
            score: 0.88,
            page: 3,
            document_id: "doc-1",
          },
        ]}
      />,
    );

    expect(screen.getByText("doc-1")).toBeInTheDocument();
    expect(screen.getByText("p3")).toBeInTheDocument();
    expect(screen.getByText("0.880")).toBeInTheDocument();
    expect(screen.getByText("indexed source text")).toBeInTheDocument();
  });
});
