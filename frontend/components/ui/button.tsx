import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
};

export function Button({ className, variant = "secondary", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex h-9 items-center justify-center gap-2 rounded-[8px] px-3 text-sm font-medium transition duration-150 ease-out active:translate-y-px disabled:opacity-50",
        variant === "primary" &&
          "bg-accent text-accent-fg hover:opacity-90",
        variant === "secondary" &&
          "border border-border bg-surface text-text hover:bg-surface-2",
        variant === "ghost" && "text-muted hover:bg-surface-2 hover:text-text",
        variant === "danger" &&
          "border border-danger/30 bg-danger/10 text-danger hover:bg-danger/15",
        className,
      )}
      {...props}
    />
  );
}
