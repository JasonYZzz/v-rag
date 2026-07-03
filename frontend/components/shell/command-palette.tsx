"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { MagnifyingGlass } from "@phosphor-icons/react";

import { Button } from "@/components/ui/button";
import { useThemeStore } from "@/lib/theme";
import { cn } from "@/lib/utils";

type Command = {
  label: string;
  hint: string;
  action: () => void;
};

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const setTheme = useThemeStore((state) => state.setMode);

  const commands = useMemo<Command[]>(
    () => [
      { label: "Open Chat", hint: "Playground", action: () => router.push("/chat") },
      { label: "Open Orchestrate", hint: "Graphs", action: () => router.push("/orchestrate") },
      { label: "Open Knowledge", hint: "Documents", action: () => router.push("/knowledge") },
      { label: "Open Config", hint: "Runtime", action: () => router.push("/config") },
      { label: "Open Health", hint: "Status", action: () => router.push("/health") },
      { label: "Theme Light", hint: "Appearance", action: () => setTheme("light") },
      { label: "Theme Dark", hint: "Appearance", action: () => setTheme("dark") },
      { label: "Theme System", hint: "Appearance", action: () => setTheme("system") },
    ],
    [router, setTheme],
  );
  const filtered = commands.filter((command) =>
    `${command.label} ${command.hint}`.toLowerCase().includes(query.toLowerCase()),
  );

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((current) => !current);
      }
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (!open) {
    return (
      <Button
        variant="ghost"
        className="fixed right-4 top-4 z-30 hidden border border-border bg-surface px-2 font-mono text-xs text-muted shadow-[0_8px_18px_var(--shadow)] md:inline-flex"
        onClick={() => setOpen(true)}
      >
        Cmd K
      </Button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-bg/70 p-4 backdrop-blur-sm" role="presentation">
      <div className="mx-auto mt-[12vh] max-w-xl overflow-hidden rounded-[12px] border border-border bg-surface shadow-[0_14px_40px_var(--shadow)]">
        <div className="flex items-center gap-2 border-b border-border px-3 py-2">
          <MagnifyingGlass size={17} className="text-muted" />
          <input
            autoFocus
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActive(0);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setActive((current) => Math.min(current + 1, filtered.length - 1));
              }
              if (event.key === "ArrowUp") {
                event.preventDefault();
                setActive((current) => Math.max(current - 1, 0));
              }
              if (event.key === "Enter" && filtered[active]) {
                filtered[active].action();
                setOpen(false);
              }
            }}
            className="h-10 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
            placeholder="Search commands"
          />
        </div>
        <div className="max-h-72 overflow-auto p-2">
          {filtered.length === 0 ? (
            <div className="px-3 py-8 text-center text-sm text-muted">No commands found</div>
          ) : (
            filtered.map((command, index) => (
              <button
                key={command.label}
                className={cn(
                  "flex w-full items-center justify-between rounded-[8px] px-3 py-2 text-left text-sm",
                  index === active ? "bg-accent/10 text-accent" : "text-text hover:bg-surface-2",
                )}
                onMouseEnter={() => setActive(index)}
                onClick={() => {
                  command.action();
                  setOpen(false);
                }}
              >
                <span>{command.label}</span>
                <span className="font-mono text-xs text-muted">{command.hint}</span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
