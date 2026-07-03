"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChatCircleText,
  Database,
  GearSix,
  GitBranch,
  Heartbeat,
  Hexagon,
} from "@phosphor-icons/react";

import { BackendStatus } from "@/components/shell/backend-status";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/chat", label: "Chat", icon: ChatCircleText },
  { href: "/orchestrate", label: "Orchestrate", icon: GitBranch },
  { href: "/knowledge", label: "Knowledge", icon: Database },
  { href: "/config", label: "Config", icon: GearSix },
  { href: "/health", label: "Health", icon: Heartbeat },
];

export function Rail() {
  const pathname = usePathname();
  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-[76px] flex-col border-r border-border bg-surface px-3 py-4 md:w-[220px]">
      <Link href="/chat" className="mb-8 flex items-center gap-2 px-2 text-sm font-semibold">
        <span className="flex h-8 w-8 items-center justify-center rounded-[8px] bg-accent/12 text-accent">
          <Hexagon size={18} weight="duotone" />
        </span>
        <span className="hidden md:inline">v-rag</span>
      </Link>
      <nav className="flex flex-1 flex-col gap-1" aria-label="Primary">
        {nav.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative flex h-10 items-center gap-3 rounded-[8px] px-2 text-sm text-muted transition hover:bg-surface-2 hover:text-text",
                active && "bg-accent/10 text-accent",
              )}
            >
              {active && (
                <span className="absolute left-0 h-5 w-px rounded-full bg-accent" aria-hidden />
              )}
              <Icon size={18} weight={active ? "fill" : "regular"} />
              <span className="hidden md:inline">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="space-y-3">
        <BackendStatus />
        <ThemeToggle />
      </div>
    </aside>
  );
}
