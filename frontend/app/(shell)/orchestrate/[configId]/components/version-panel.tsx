"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import type { GraphVersion } from "@/lib/graphs-api";
import { publishGraph, rollbackGraph } from "@/lib/graphs-api";
import { cn } from "@/lib/utils";

type VersionPanelProps = {
  configId: string;
  versions: GraphVersion[];
  activeVersion: number | null;
};

export function VersionPanel({ configId, versions, activeVersion }: VersionPanelProps) {
  const queryClient = useQueryClient();
  const publish = useMutation({
    mutationFn: (version: number) => publishGraph(configId, version),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["graph", configId] }),
  });
  const rollback = useMutation({
    mutationFn: (version: number) => rollbackGraph(configId, version),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["graph", configId] }),
  });
  return (
    <section className="space-y-3 rounded-[8px] border border-border bg-bg p-3">
      <h2 className="text-sm font-semibold">Versions</h2>
      <div className="space-y-2">
        {versions.map((version) => (
          <div
            key={version.version}
            className={cn(
              "rounded-[8px] border border-border bg-surface p-3",
              version.status === "published" && "border-accent/45",
            )}
          >
            <div className="flex items-center justify-between gap-3">
              <span>
                <span className="font-mono text-xs">v{version.version}</span>
                <span className="ml-2 text-xs text-muted">{version.status}</span>
              </span>
              {version.version === activeVersion ? (
                <span className="rounded-[5px] bg-accent/10 px-1.5 py-0.5 text-[11px] text-accent">
                  Active
                </span>
              ) : null}
            </div>
            <div className="mt-3 flex gap-2">
              <Button
                type="button"
                variant="secondary"
                className="h-8"
                disabled={version.status === "published" || publish.isPending}
                onClick={() => publish.mutate(version.version)}
              >
                Publish
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="h-8"
                disabled={rollback.isPending}
                onClick={() => rollback.mutate(version.version)}
              >
                Rollback
              </Button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
