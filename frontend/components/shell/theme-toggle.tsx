"use client";

import { Desktop, Moon, Sun } from "@phosphor-icons/react";

import { Button } from "@/components/ui/button";
import { useThemeStore } from "@/lib/theme";

export function ThemeToggle() {
  const mode = useThemeStore((state) => state.mode);
  const cycle = useThemeStore((state) => state.cycle);
  const Icon = mode === "dark" ? Moon : mode === "light" ? Sun : Desktop;

  return (
    <Button
      variant="ghost"
      className="w-full justify-start px-2 text-xs"
      onClick={cycle}
      aria-label="Switch theme"
    >
      <Icon size={16} weight="regular" />
      <span className="hidden md:inline">{mode}</span>
    </Button>
  );
}
