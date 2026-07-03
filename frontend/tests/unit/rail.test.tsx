import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Rail } from "@/components/shell/rail";

vi.mock("next/navigation", () => ({
  usePathname: () => "/chat",
}));

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-query")>(
    "@tanstack/react-query",
  );
  return {
    ...actual,
    useQuery: () => ({ isLoading: false, data: { status: "ok" } }),
  };
});

describe("Rail", () => {
  it("renders primary navigation items", () => {
    render(<Rail />);

    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Orchestrate")).toBeInTheDocument();
    expect(screen.getByText("Knowledge")).toBeInTheDocument();
    expect(screen.getByText("Config")).toBeInTheDocument();
    expect(screen.getByText("Health")).toBeInTheDocument();
  });
});
