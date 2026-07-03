"use client";

import { Trash } from "@phosphor-icons/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DocStatusBadge } from "@/components/knowledge/doc-status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { deleteDoc, listDocs } from "@/lib/api";

export function DocList() {
  const queryClient = useQueryClient();
  const docs = useQuery({ queryKey: ["documents"], queryFn: listDocs });
  const remove = useMutation({
    mutationFn: deleteDoc,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  if (docs.isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
      </div>
    );
  }

  if (docs.isError) {
    return (
      <div className="rounded-[10px] border border-danger/25 bg-danger/10 p-4 text-sm text-danger">
        Failed to load documents
      </div>
    );
  }

  if (!docs.data?.length) {
    return (
      <div className="rounded-[10px] border border-border bg-surface p-8 text-center">
        <h2 className="text-base font-semibold">No documents yet</h2>
        <p className="mt-2 text-sm text-muted">Drop text or PDF files above to start indexing.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[10px] border border-border bg-surface">
      <table className="w-full border-collapse text-sm">
        <thead className="bg-surface-2 text-left text-xs text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">File</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Chunks</th>
            <th className="px-4 py-3 font-medium">Created</th>
            <th className="px-4 py-3 text-right font-medium">Action</th>
          </tr>
        </thead>
        <tbody>
          {docs.data.map((doc) => (
            <tr key={doc.id} className="border-t border-border">
              <td className="px-4 py-3 font-medium">{doc.filename}</td>
              <td className="px-4 py-3"><DocStatusBadge /></td>
              <td className="px-4 py-3 font-mono text-muted">{doc.chunks}</td>
              <td className="px-4 py-3 font-mono text-xs text-muted">
                {doc.created_at ? new Date(doc.created_at).toLocaleString() : "unknown"}
              </td>
              <td className="px-4 py-3 text-right">
                <Button
                  variant="ghost"
                  className="h-8"
                  onClick={() => {
                    if (window.confirm(`Delete ${doc.filename}?`)) {
                      remove.mutate(doc.id);
                    }
                  }}
                  aria-label={`Delete ${doc.filename}`}
                >
                  <Trash size={15} />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
