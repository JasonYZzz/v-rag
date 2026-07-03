"use client";

import { CaretDown, FileText } from "@phosphor-icons/react";
import { useState } from "react";

import type { RetrievedChunk } from "@/lib/types";
import { cn } from "@/lib/utils";

export function RetrievalPanel({ chunks }: { chunks: RetrievedChunk[] }) {
  return (
    <aside className="rounded-[10px] border border-border bg-surface p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold">Retrieved chunks</h2>
        <span className="font-mono text-xs text-muted">{chunks.length}</span>
      </div>
      {chunks.length === 0 ? (
        <div className="rounded-[8px] bg-surface-2 px-3 py-8 text-center text-sm text-muted">
          No relevant chunks yet
        </div>
      ) : (
        <div className="space-y-2">
          {chunks.map((chunk) => (
            <ChunkItem key={chunk.chunk_id} chunk={chunk} />
          ))}
        </div>
      )}
    </aside>
  );
}

function ChunkItem({ chunk }: { chunk: RetrievedChunk }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <button
      className="w-full rounded-[8px] border border-border bg-bg p-3 text-left transition hover:bg-surface-2"
      onClick={() => setExpanded((current) => !current)}
      aria-expanded={expanded}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="flex min-w-0 items-center gap-2 text-sm font-medium">
          <FileText size={16} className="shrink-0 text-accent" />
          <span className="truncate">{chunk.document_id ?? "document"}</span>
          {chunk.page ? <span className="font-mono text-xs text-muted">p{chunk.page}</span> : null}
        </span>
        <span className="flex items-center gap-2 font-mono text-xs text-muted">
          {chunk.score.toFixed(3)}
          <CaretDown
            size={14}
            className={cn("transition", expanded && "rotate-180")}
          />
        </span>
      </div>
      <p className={cn("mt-2 text-sm leading-6 text-muted", !expanded && "line-clamp-3")}>
        {chunk.text}
      </p>
    </button>
  );
}
