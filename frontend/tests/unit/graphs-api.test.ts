import { beforeEach, describe, expect, it, vi } from "vitest";

import { listGraphs, publishGraph, saveDraft, testRunGraph } from "@/lib/graphs-api";

describe("graphs-api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches graph list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json([{ id: "g1", name: "Default" }])),
    );

    const graphs = await listGraphs();

    expect(graphs[0].id).toBe("g1");
    expect(fetch).toHaveBeenCalledWith("/api/graphs", expect.any(Object));
  });

  it("saves draft and runs graph lifecycle calls", async () => {
    const fetchMock = vi.fn(async () => Response.json({ ok: true, version: 2 }));
    vi.stubGlobal("fetch", fetchMock);
    const graph = { entry: "a", exits: ["a"], nodes: [{ id: "a", type: "generate" }], edges: [] };

    await saveDraft("g1", graph);
    await publishGraph("g1", 2);
    await testRunGraph("g1", 2, "hello");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/graphs/g1/draft",
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ graph }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/graphs/g1/publish",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ version: 2 }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/graphs/g1/test-run",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ version: 2, query: "hello" }),
      }),
    );
  });
});
