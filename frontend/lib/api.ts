import type { ConfigOut, DocOut, HealthOut } from "@/lib/types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || response.statusText, response.status);
  }
  return (await response.json()) as T;
}

export function getHealth() {
  return request<HealthOut>("/health");
}

export function listDocs() {
  return request<DocOut[]>("/documents");
}

export function getConfig() {
  return request<ConfigOut>("/config");
}

export async function uploadDoc(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<{ document_id: string; chunks: string }>("/documents", {
    method: "POST",
    body: form,
  });
}

export function deleteDoc(id: string) {
  return request<{ deleted: string }>(`/documents/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}
