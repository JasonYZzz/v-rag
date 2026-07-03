"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, GitBranch } from "@phosphor-icons/react";

import { Skeleton } from "@/components/ui/skeleton";
import { listGraphs } from "@/lib/graphs-api";

export default function OrchestratePage() {
  const graphs = useQuery({ queryKey: ["graphs"], queryFn: listGraphs });
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold">Orchestrate</h1>
        <p className="mt-1 text-sm text-muted">Edit routed graph versions and inspect test-run traces.</p>
      </header>
      <section className="rounded-[10px] border border-border bg-surface p-4">
        {graphs.isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : graphs.data?.length ? (
          <div className="divide-y divide-border">
            {graphs.data.map((graph) => (
              <Link
                key={graph.id}
                href={`/orchestrate/${graph.id}`}
                className="flex items-center justify-between gap-4 py-4 text-sm hover:text-accent"
              >
                <span className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-[8px] bg-accent/10 text-accent">
                    <GitBranch size={18} />
                  </span>
                  <span>
                    <span className="block font-medium">{graph.name}</span>
                    <span className="font-mono text-xs text-muted">
                      published v{graph.current_published_version ?? "none"}
                    </span>
                  </span>
                </span>
                <ArrowRight size={18} />
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No graph configs found. Start the backend to seed the default graph.</p>
        )}
      </section>
    </div>
  );
}
