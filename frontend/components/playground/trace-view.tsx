"use client";

import type { GraphRunTrace } from "@/lib/graphs-api";

type TraceViewProps = {
  trace: Partial<GraphRunTrace> | null | undefined;
};

export function TraceView({ trace }: TraceViewProps) {
  if (!trace) {
    return (
      <section className="rounded-[10px] border border-border bg-surface p-4">
        <h2 className="text-base font-semibold">Why this route</h2>
        <p className="mt-2 text-sm text-muted">Run a chat request to inspect node-level routing.</p>
      </section>
    );
  }
  const nodeIo = trace.node_io ?? [];
  const routeTrace = trace.route_trace ?? {};
  return (
    <section className="rounded-[10px] border border-border bg-surface p-4">
      <h2 className="text-base font-semibold">Why this route</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {nodeIo.map((node, index) => (
          <span
            key={`${String(node.node_id ?? index)}-${index}`}
            className="rounded-[6px] bg-accent/10 px-2 py-1 font-mono text-xs text-accent"
          >
            {String(node.node_id ?? "unknown")}
          </span>
        ))}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="font-mono text-xs text-muted">intent</dt>
          <dd className="mt-1 font-mono">{trace.intent ?? String(routeTrace.final_intent ?? "unknown")}</dd>
        </div>
        <div>
          <dt className="font-mono text-xs text-muted">reason</dt>
          <dd className="mt-1 font-mono">{String(routeTrace.reason ?? "unknown")}</dd>
        </div>
        <div>
          <dt className="font-mono text-xs text-muted">confidence</dt>
          <dd className="mt-1 font-mono">{String(routeTrace.confidence ?? "n/a")}</dd>
        </div>
      </dl>
      <details className="mt-4 rounded-[8px] border border-border bg-bg p-3">
        <summary className="cursor-pointer font-mono text-xs text-muted">route_trace</summary>
        <pre className="mt-3 max-h-48 overflow-auto text-xs leading-5">
          {JSON.stringify(routeTrace, null, 2)}
        </pre>
      </details>
      <details className="mt-3 rounded-[8px] border border-border bg-bg p-3">
        <summary className="cursor-pointer font-mono text-xs text-muted">node_io</summary>
        <pre className="mt-3 max-h-56 overflow-auto text-xs leading-5">
          {JSON.stringify(nodeIo, null, 2)}
        </pre>
      </details>
    </section>
  );
}
