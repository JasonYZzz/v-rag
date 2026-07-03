"use client";

import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UploadSimple } from "@phosphor-icons/react";

import { Button } from "@/components/ui/button";
import { uploadDoc } from "@/lib/api";
import { cn } from "@/lib/utils";

export function UploadDropzone() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: uploadDoc,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  function upload(file: File | undefined) {
    if (file) {
      mutation.mutate(file);
    }
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        upload(event.dataTransfer.files[0]);
      }}
      className={cn(
        "rounded-[10px] border border-dashed border-border bg-surface p-6 transition",
        dragging && "border-accent bg-accent/8",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.md,.pdf,text/plain"
        className="hidden"
        onChange={(event) => upload(event.target.files?.[0])}
      />
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <UploadSimple size={17} className="text-accent" />
            Upload document
          </div>
          <p className="mt-1 text-sm text-muted">Drop a text file here or pick one from disk.</p>
          {mutation.isError ? (
            <p className="mt-2 text-sm text-danger">{(mutation.error as Error).message}</p>
          ) : null}
          {mutation.isSuccess ? <p className="mt-2 text-sm text-success">Indexed successfully</p> : null}
        </div>
        <Button variant="primary" onClick={() => inputRef.current?.click()} disabled={mutation.isPending}>
          {mutation.isPending ? "Uploading" : "Choose file"}
        </Button>
      </div>
    </div>
  );
}
