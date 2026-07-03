import type { GraphConfig } from "@/lib/flow-graph";

export type RegistryNode = {
  type: string;
  description: string;
  config_schema: Record<string, unknown> | null;
};

export type GraphSummary = {
  id: string;
  name: string;
  workspace_id: string;
  current_published_version: number | null;
};

export type GraphVersion = {
  version: number;
  status: "draft" | "published" | "archived";
  graph: GraphConfig;
};

export type GraphDetail = {
  id: string;
  versions: GraphVersion[];
};

export type GraphRunTrace = {
  id: string;
  route_trace: Record<string, unknown>;
  node_io: Array<Record<string, unknown>>;
  intent: string | null;
  budget?: Record<string, unknown>;
};

export type TestRunResult = {
  state: Record<string, unknown>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw new Error((await response.text()) || response.statusText);
  }
  return (await response.json()) as T;
}

export function getRegistry() {
  return request<RegistryNode[]>("/graphs/registry");
}

export function listGraphs() {
  return request<GraphSummary[]>("/graphs");
}

export function getGraph(configId: string) {
  return request<GraphDetail>(`/graphs/${encodeURIComponent(configId)}`);
}

export function saveDraft(configId: string, graph: GraphConfig) {
  return request<{ id: string; version: number; status: string }>(
    `/graphs/${encodeURIComponent(configId)}/draft`,
    {
      method: "PUT",
      body: JSON.stringify({ graph }),
    },
  );
}

export function publishGraph(configId: string, version: number) {
  return request<{ id: string; version: number; status: string }>(
    `/graphs/${encodeURIComponent(configId)}/publish`,
    {
      method: "POST",
      body: JSON.stringify({ version }),
    },
  );
}

export function rollbackGraph(configId: string, version: number) {
  return request<{ id: string; version: number; status: string }>(
    `/graphs/${encodeURIComponent(configId)}/rollback`,
    {
      method: "POST",
      body: JSON.stringify({ version }),
    },
  );
}

export function testRunGraph(configId: string, version: number, query: string) {
  return request<TestRunResult>(`/graphs/${encodeURIComponent(configId)}/test-run`, {
    method: "POST",
    body: JSON.stringify({ version, query }),
  });
}

export function getRunTrace(traceId: string) {
  return request<GraphRunTrace>(`/runs/${encodeURIComponent(traceId)}`);
}
