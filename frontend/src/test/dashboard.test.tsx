import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Dashboard } from "../pages/Dashboard";

const responses: Record<string, unknown> = {
  "/dashboard/summary": { total_spend: "411183335.24", total_orders: 47128, average_order_value: "8725.00", supplier_count: 106, category_count: 10, business_unit_count: 5 },
  "/analytics/spend/monthly": [{ month: "2025-01-01", spend: "1000000", transaction_count: 10, average_order_value: "100000", growth_percent: null }],
  "/analytics/spend/categories": [{ category_id: 1, category_name: "Electronics", spend: "1000000", share_percent: "20", transaction_count: 10, average_order_value: "100000", supplier_count: 2 }],
  "/analytics/spend/suppliers": [{ supplier_id: "S1", supplier_name: "Atlas Supply", country: "India", spend: "1000000", share_percent: "20", transaction_count: 10, average_order_value: "100000", total_quantity: "50", rank: 1 }],
  "/analytics/spend/business-units": [{ business_unit_id: 1, business_unit_name: "Operations", spend: "1000000", share_percent: "20", transaction_count: 10 }],
  "/analytics/contract-compliance": { total_spend: "1000000", total_orders: 10, on_contract_spend: "800000", off_contract_spend: "200000", on_contract_percent: "80", off_contract_percent: "20", on_contract_order_count: 8, off_contract_order_count: 2 },
  "/opportunities/summary": { active_opportunity_count: 12, estimated_price_optimization_savings: "12500000", review_spend: "20000000", critical_count: 1, high_priority_count: 4, price_optimization_count: 8, contract_leakage_count: 2, supplier_consolidation_count: 1, supplier_performance_count: 1, savings_note: "Not additive" },
};

describe("Dashboard", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a loading state then renders live API metrics", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = new URL(String(input)).pathname.replace("/api", "");
      return new Response(JSON.stringify(responses[path]), { status: 200 });
    });
    render(<Dashboard />);
    expect(screen.getByText(/Loading verified analytics/i)).toBeInTheDocument();
    expect(await screen.findByText("47,128")).toBeInTheDocument();
    expect(screen.getAllByText("20.0%")).toHaveLength(2);
  });

  it("renders an actionable error state", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ error: { message: "Offline" } }), { status: 503 }));
    render(<Dashboard />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Offline"));
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
