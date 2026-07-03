import { describe, expect, it } from "vitest";

import { parseSSE } from "@/lib/sse";

function responseFromChunks(chunks: string[]) {
  const encoder = new TextEncoder();
  return new Response(
    new ReadableStream({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk));
        }
        controller.close();
      },
    }),
  );
}

describe("parseSSE", () => {
  it("splits retrieved events and token frames across stream chunks", async () => {
    const response = responseFromChunks([
      "event: retrieved\n",
      'data: [{"chunk_id":"c1","text":"hello","score":0.9,"page":1,"document_id":"d1"}]\n\n',
      "data: Hel",
      "lo\n\n",
      "data: [DONE]\n\n",
    ]);

    const frames = [];
    for await (const frame of parseSSE(response)) {
      frames.push(frame);
    }

    expect(frames).toEqual([
      {
        event: "retrieved",
        data: '[{"chunk_id":"c1","text":"hello","score":0.9,"page":1,"document_id":"d1"}]',
      },
      { event: undefined, data: "Hello" },
      { event: undefined, data: "[DONE]" },
    ]);
  });
});
