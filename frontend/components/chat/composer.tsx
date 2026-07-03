"use client";

import { PaperPlaneTilt } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

export function Composer({
  disabled,
  onSend,
}: {
  disabled?: boolean;
  onSend: (value: string) => void;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "/") {
        event.preventDefault();
        ref.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) {
      return;
    }
    onSend(trimmed);
    setValue("");
  }

  return (
    <div className="rounded-[10px] border border-border bg-surface p-2">
      <textarea
        ref={ref}
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        rows={3}
        className="min-h-20 w-full resize-none bg-transparent px-2 py-2 text-sm leading-6 outline-none placeholder:text-muted"
        placeholder="Ask about indexed documents"
      />
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="font-mono text-xs text-muted">Enter send · Shift Enter newline</span>
        <Button variant="primary" onClick={submit} disabled={disabled || !value.trim()}>
          <PaperPlaneTilt size={16} weight="fill" />
          Send
        </Button>
      </div>
    </div>
  );
}
