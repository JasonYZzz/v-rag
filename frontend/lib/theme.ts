"use client";

import { create } from "zustand";

export type ThemeMode = "system" | "light" | "dark";

type ThemeState = {
  mode: ThemeMode;
  resolved: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
  cycle: () => void;
};

const modes: ThemeMode[] = ["system", "light", "dark"];

export function resolveTheme(mode: ThemeMode): "light" | "dark" {
  if (mode !== "system") {
    return mode;
  }
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "light";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(mode: ThemeMode) {
  const resolved = resolveTheme(mode);
  if (typeof document !== "undefined") {
    document.documentElement.classList.toggle("dark", resolved === "dark");
    document.documentElement.dataset.theme = mode;
  }
  if (typeof localStorage !== "undefined" && typeof localStorage.setItem === "function") {
    localStorage.setItem("vrag-theme", mode);
  }
  return resolved;
}

function initialMode(): ThemeMode {
  if (typeof localStorage === "undefined" || typeof localStorage.getItem !== "function") {
    return "system";
  }
  const stored = localStorage.getItem("vrag-theme");
  return stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
}

export const useThemeStore = create<ThemeState>((set, get) => {
  const mode = initialMode();
  return {
    mode,
    resolved: resolveTheme(mode),
    setMode: (nextMode) => {
      const resolved = applyTheme(nextMode);
      set({ mode: nextMode, resolved });
    },
    cycle: () => {
      const current = get().mode;
      const next = modes[(modes.indexOf(current) + 1) % modes.length];
      get().setMode(next);
    },
  };
});
