"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleNotch, Pulse } from "@phosphor-icons/react";

import { getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

export function BackendStatus() {
  const query = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 5000,
    retry: 1,
  });
  const status = query.isLoading ? "checking" : query.data?.status === "ok" ? "ok" : "down";

  return (
    <>
      {status === "down" && (
        <div className="fixed inset-x-0 top-0 z-40 border-b border-danger/25 bg-danger/10 px-4 py-1 text-center text-xs text-danger">
          Backend unreachable. Check the API process.
        </div>
      )}
      <div
        className={cn(
          "inline-flex items-center gap-2 rounded-full border px-2 py-1 text-xs",
          status === "ok" && "border-success/30 bg-success/10 text-success",
          status === "down" && "border-danger/30 bg-danger/10 text-danger",
          status === "checking" && "border-border bg-surface text-muted",
        )}
      >
        {status === "checking" ? <CircleNotch size={14} /> : <Pulse size={14} />}
        <span>{status}</span>
      </div>
    </>
  );
}
