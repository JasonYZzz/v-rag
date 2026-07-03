"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { Composer } from "@/components/chat/composer";
import { type ChatMessage, Message } from "@/components/chat/message";
import { RetrievalPanel } from "@/components/chat/retrieval-panel";
import { TraceView } from "@/components/playground/trace-view";
import { Skeleton } from "@/components/ui/skeleton";
import { listDocs } from "@/lib/api";
import { getRunTrace } from "@/lib/graphs-api";
import { useChatStream } from "@/lib/sse";

export function ChatView() {
  const docs = useQuery({ queryKey: ["documents"], queryFn: listDocs });
  const stream = useChatStream();
  const trace = useQuery({
    queryKey: ["run-trace", stream.traceId],
    queryFn: () => getRunTrace(stream.traceId ?? ""),
    enabled: Boolean(stream.traceId),
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const visibleMessages = useMemo(() => {
    if (!stream.streaming) {
      return messages;
    }
    return [
      ...messages,
      {
        id: "assistant-streaming",
        role: "assistant" as const,
        content: stream.text,
        streaming: stream.streaming,
      },
    ];
  }, [messages, stream.streaming, stream.text]);

  async function send(query: string) {
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: query },
    ]);
    const finalText = await stream.start(query, 4);
    if (finalText) {
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "assistant", content: finalText },
      ]);
    }
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
      <section className="flex min-h-[calc(100vh-64px)] flex-col rounded-[10px] border border-border bg-bg">
        <header className="border-b border-border px-5 py-4">
          <h1 className="text-xl font-semibold">Chat playground</h1>
          <p className="mt-1 text-sm text-muted">
            Ask questions against indexed documents and inspect retrieved context.
          </p>
        </header>
        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-5">
          {docs.isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-2/3" />
              <Skeleton className="ml-auto h-16 w-1/2" />
            </div>
          ) : docs.data?.length === 0 ? (
            <div className="rounded-[10px] border border-border bg-surface p-8 text-center">
              <h2 className="text-base font-semibold">Upload documents first</h2>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">
                Add text files in Knowledge, then return here to ask questions and review retrieval hits.
              </p>
            </div>
          ) : visibleMessages.length === 0 ? (
            <div className="rounded-[10px] border border-border bg-surface p-8 text-center">
              <h2 className="text-base font-semibold">Ready for questions</h2>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">
                The answer stream will appear here, with retrieved chunks shown beside the answer.
              </p>
            </div>
          ) : (
            visibleMessages.map((message) => <Message key={message.id} message={message} />)
          )}
          {stream.error ? (
            <div className="rounded-[8px] border border-danger/25 bg-danger/10 p-3 text-sm text-danger">
              {stream.error}
            </div>
          ) : null}
        </div>
        <div className="border-t border-border p-4">
          <Composer disabled={stream.streaming || docs.data?.length === 0} onSend={send} />
        </div>
      </section>
      <div className="lg:sticky lg:top-8 lg:h-fit">
        <RetrievalPanel chunks={stream.chunks} />
        <div className="mt-4">
          <TraceView trace={trace.data ?? null} />
        </div>
      </div>
    </div>
  );
}
