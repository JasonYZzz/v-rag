"use client";

import { useCallback, useRef, useState } from "react";

import type { RetrievedChunk } from "@/lib/types";

export type SSEFrame = {
  event?: string;
  data: string;
};

export async function* parseSSE(response: Response): AsyncGenerator<SSEFrame> {
  if (!response.body) {
    return;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const parsed = parseFrame(frame);
      if (parsed) {
        yield parsed;
      }
    }
  }
  if (buffer.trim()) {
    const parsed = parseFrame(buffer);
    if (parsed) {
      yield parsed;
    }
  }
}

function parseFrame(frame: string): SSEFrame | null {
  let event: string | undefined;
  const data: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event: ")) {
      event = line.slice(7);
    }
    if (line.startsWith("data: ")) {
      data.push(line.slice(6));
    }
  }
  if (!event && data.length === 0) {
    return null;
  }
  return { event, data: data.join("\n") };
}

export function useChatStream() {
  const [chunks, setChunks] = useState<RetrievedChunk[]>([]);
  const [text, setText] = useState("");
  const [traceId, setTraceId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (query: string, topK = 4) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setChunks([]);
    setText("");
    setTraceId(null);
    setError(null);
    setStreaming(true);
    let finalText = "";
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: topK }),
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      for await (const frame of parseSSE(response)) {
        if (frame.event === "retrieved") {
          setChunks(JSON.parse(frame.data) as RetrievedChunk[]);
          continue;
        }
        if (frame.event === "trace") {
          setTraceId((JSON.parse(frame.data) as { trace_id: string }).trace_id);
          continue;
        }
        if (frame.event === "generation") {
          continue;
        }
        if (frame.data === "[DONE]") {
          break;
        }
        finalText += frame.data;
        setText(finalText);
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError((err as Error).message || "Chat request failed");
      }
    } finally {
      setStreaming(false);
    }
    return finalText;
  }, []);

  return { chunks, text, traceId, streaming, error, start };
}
