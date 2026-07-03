"use client";

import { useQuery } from "@tanstack/react-query";

import { Skeleton } from "@/components/ui/skeleton";
import { getConfig } from "@/lib/api";

export function ConfigView() {
  const config = useQuery({ queryKey: ["config"], queryFn: getConfig });

  if (config.isLoading) {
    return <Skeleton className="h-80" />;
  }
  if (config.isError) {
    return (
      <div className="rounded-[10px] border border-danger/25 bg-danger/10 p-4 text-sm text-danger">
        Failed to load config
      </div>
    );
  }
  if (!config.data) {
    return null;
  }

  const rows = [
    ["LLM provider", config.data.llm_provider],
    ["Embedding provider", config.data.embed_provider],
    ["OpenAI base URL", config.data.openai_base_url],
    ["Ollama base URL", config.data.ollama_base_url],
    ["Ollama LLM", config.data.ollama_llm_model],
    ["Ollama embedding", config.data.ollama_embed_model],
    ["Embedding dim", String(config.data.embed_dim)],
    ["Vector store", config.data.vector_store],
    ["Database", config.data.database_url],
    ["OpenAI key", config.data.has_openai_key ? "Configured" : "Not configured"],
  ];

  return (
    <div className="rounded-[10px] border border-border bg-surface">
      <div className="border-b border-border px-5 py-4">
        <h2 className="text-base font-semibold">Runtime config</h2>
        <p className="mt-1 text-sm text-muted">P0 is read only. Change backend environment variables to edit values.</p>
      </div>
      <dl className="divide-y divide-border">
        {rows.map(([label, value]) => (
          <div key={label} className="grid gap-2 px-5 py-3 md:grid-cols-[220px_1fr]">
            <dt className="text-sm text-muted">{label}</dt>
            <dd className="break-all font-mono text-sm text-text">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
