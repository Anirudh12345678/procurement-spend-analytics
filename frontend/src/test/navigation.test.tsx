import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";

describe("navigation", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.history.pushState({}, "", "/");
  });

  it("navigates to the optimization workspace", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = new URL(String(input)).pathname;
      if (path.endsWith("/opportunities/summary")) return new Response(JSON.stringify({ active_opportunity_count: 0, estimated_price_optimization_savings: "0", review_spend: "0", critical_count: 0, high_priority_count: 0, price_optimization_count: 0, contract_leakage_count: 0, supplier_consolidation_count: 0, supplier_performance_count: 0, savings_note: "No additive savings" }), { status: 200 });
      if (path.endsWith("/opportunities")) return new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 15, pages: 0 }), { status: 200 });
      return new Promise<Response>(() => undefined);
    });
    render(<App />);
    await userEvent.click(await screen.findByRole("link", { name: "Cost Optimization" }));
    expect(await screen.findByRole("heading", { name: /Prioritized, explainable procurement opportunities/i })).toBeInTheDocument();
    expect(screen.getByText("No opportunities match these filters.")).toBeInTheDocument();
  });

  it("shows all workspaces and applies spend dates from the top bar", async () => {
    window.history.pushState({}, "", "/spend");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = new URL(String(input));
      if (url.pathname === "/api/suppliers") return new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 100, pages: 0 }), { status: 200 });
      if (url.pathname.endsWith("/categories") || url.pathname.endsWith("/business-units")) return new Response(JSON.stringify([]), { status: 200 });
      if (url.pathname.endsWith("/supplier-concentration")) return new Response(JSON.stringify({ total_spend: "0", supplier_count: 0, top_5_spend: "0", top_5_concentration_percent: "0", top_10_spend: "0", top_10_concentration_percent: "0" }), { status: 200 });
      return new Response(JSON.stringify([]), { status: 200 });
    });

    render(<App />);

    expect(await screen.findByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Spend Analysis" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cost Optimization" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "AI Advisor" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Top bar from date"), { target: { value: "2025-01-01" } });
    await waitFor(() => expect(window.location.search).toContain("date_from=2025-01-01"));
  });
});
