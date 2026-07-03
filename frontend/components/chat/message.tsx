import { cn } from "@/lib/utils";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
};

export function Message({ message }: { message: ChatMessage }) {
  const user = message.role === "user";
  return (
    <div className={cn("flex", user ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75ch] rounded-[10px] px-4 py-3 text-sm leading-6",
          user
            ? "bg-accent text-accent-fg"
            : "border border-border bg-surface text-text",
        )}
      >
        {message.content || (message.streaming ? "Thinking" : "")}
        {message.streaming ? <span className="ml-1 font-mono text-accent">▌</span> : null}
      </div>
    </div>
  );
}
