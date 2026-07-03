import { cn } from "@/lib/utils";

export function DocStatusBadge({ status = "ready" }: { status?: "ready" | "failed" | "indexing" }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-1 text-xs",
        status === "ready" && "bg-success/10 text-success",
        status === "failed" && "bg-danger/10 text-danger",
        status === "indexing" && "bg-warn/10 text-warn",
      )}
    >
      {status === "ready" ? "Ready" : status === "indexing" ? "Indexing" : "Failed"}
    </span>
  );
}
