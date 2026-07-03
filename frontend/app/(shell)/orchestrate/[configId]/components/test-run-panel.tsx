"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { testRunGraph } from "@/lib/graphs-api";

type TestRunPanelProps = {
  configId: string;
  version: number | null;
};

export function TestRunPanel({ configId, version }: TestRunPanelProps) {
  const [query, setQuery] = useState("产品怎么配置");
  const testRun = useMutation({
    mutationFn: () => {
      if (!version) {
        throw new Error("No version selected");
      }
      return testRunGraph(configId, version, query);
    },
  });
  const state = testRun.data?.state;
  return (
    <section className="space-y-3 rounded-[8px] border border-border bg-bg p-3">
      <h2 className="text-sm font-semibold">Test run</h2>
      <textarea
        className="min-h-20 w-full resize-none rounded-[8px] border border-border bg-surface px-3 py-2 text-sm"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <Button type="button" variant="primary" onClick={() => testRun.mutate()} disabled={!version || testRun.isPending}>
        Run draft
      </Button>
      {testRun.isError ? <p className="text-sm text-danger">{(testRun.error as Error).message}</p> : null}
      {state ? (
        <div className="space-y-3 rounded-[8px] bg-surface p-3">
          <div className="font-mono text-xs text-muted">intent</div>
          <div className="font-mono text-sm">{String(state.intent ?? "unknown")}</div>
          <div className="font-mono text-xs text-muted">route_trace</div>
          <pre className="max-h-48 overflow-auto rounded-[8px] bg-bg p-2 text-xs leading-5">
            {JSON.stringify(state.route_trace ?? {}, null, 2)}
          </pre>
          <div className="font-mono text-xs text-muted">generation</div>
          <p className="text-sm leading-6 text-muted">{String(state.generation ?? "")}</p>
        </div>
      ) : null}
    </section>
  );
}
