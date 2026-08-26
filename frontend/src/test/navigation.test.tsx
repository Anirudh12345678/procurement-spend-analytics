import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";

describe("navigation", () => {
  afterEach(() => vi.restoreAllMocks());

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
});
