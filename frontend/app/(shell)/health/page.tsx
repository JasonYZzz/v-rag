"use client";

import { useQuery } from "@tanstack/react-query";

import { ConfigView } from "@/components/config/config-view";
import { Skeleton } from "@/components/ui/skeleton";
import { getHealth } from "@/lib/api";

export default function HealthPage() {
  const health = useQuery({ queryKey: ["health-detail"], queryFn: getHealth, refetchInterval: 5000 });

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold">Health</h1>
        <p className="mt-1 text-sm text-muted">Monitor backend reachability and current runtime posture.</p>
      </header>
      <section className="rounded-[10px] border border-border bg-surface p-5">
        <h2 className="text-base font-semibold">Backend</h2>
        {health.isLoading ? (
          <Skeleton className="mt-4 h-10 w-40" />
        ) : health.isError ? (
          <p className="mt-3 text-sm text-danger">Down</p>
        ) : (
          <p className="mt-3 font-mono text-sm text-success">{health.data?.status}</p>
        )}
      </section>
      <ConfigView />
    </div>
  );
}
