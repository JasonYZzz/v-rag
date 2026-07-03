import { describe, expect, it } from "vitest";

import { applyTheme } from "@/lib/theme";

describe("theme", () => {
  it("applies dark class for dark mode", () => {
    expect(applyTheme("dark")).toBe("dark");

    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
