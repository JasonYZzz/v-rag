"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { applyTheme, useThemeStore } from "@/lib/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const mode = useThemeStore((state) => state.mode);

  useEffect(() => {
    applyTheme(mode);
  }, [mode]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => {
      if (useThemeStore.getState().mode === "system") {
        useThemeStore.getState().setMode("system");
      }
    };
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
