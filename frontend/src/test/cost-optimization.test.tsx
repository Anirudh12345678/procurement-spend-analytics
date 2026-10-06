import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CostOptimization } from "../pages/CostOptimization";

const opportunity = {
  opportunity_id: 1,
  opportunity_type: "PRICE_OPTIMIZATION",
  item_id: 10,
  item_name: "PCB Assembly A-11",
  category_id: 2,
  category_name: "Electronics",
  supplier_id: "S1",
  supplier_name: "Supplier X",
  actual_price: "82.50",
  benchmark_price: "61.20",
  price_variance_percent: "34.8",
  quantity: "4200",
  estimated_savings: "89460",
  review_spend: "0",
  confidence_score: "0.87",
  priority_score: "82",
  priority_level: "CRITICAL",
  status: "OPEN",
  supporting_metrics: { supplier_score: "58" },
  created_at: "2026-01-10T10:00:00Z",
};

describe("CostOptimization", () => {
  afterEach(() => vi.restoreAllMocks());

  it("opens a detail view backed by opportunity, benchmark, supplier, and recommendation APIs", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/opportunities/summary")) return new Response(JSON.stringify({ active_opportunity_count: 1, estimated_price_optimization_savings: "89460", review_spend: "0", critical_count: 1, high_priority_count: 0, price_optimization_count: 1, contract_leakage_count: 0, supplier_consolidation_count: 0, supplier_performance_count: 0, savings_note: "Price only" }), { status: 200 });
      if (url.pathname.endsWith("/opportunities/1")) return new Response(JSON.stringify(opportunity), { status: 200 });
      if (url.pathname.endsWith("/opportunities")) return new Response(JSON.stringify({ items: [opportunity], total: 1, page: 1, page_size: 15, pages: 1 }), { status: 200 });
      if (url.pathname.endsWith("/benchmarks/10")) return new Response(JSON.stringify({ benchmark_id: 3, item_id: 10, item_name: opportunity.item_name, category_id: 2, category_name: "Electronics", benchmark_price: "61.20", min_price: "55", max_price: "90", median_price: "65", p25_price: "61.20", p75_price: "75", supplier_count: 5, total_quantity: "10000", total_spend: "700000", calculated_at: "2026-01-09T10:00:00Z" }), { status: 200 });
      if (url.pathname.endsWith("/suppliers/S1")) return new Response(JSON.stringify({ supplier_id: "S1", supplier_name: "Supplier X", country: "India", total_spend: "500000", transaction_count: 20, total_quantity: "7000", on_contract_percent: "72", rejection_rate_percent: "3", late_delivery_rate_percent: "12" }), { status: 200 });
      if (url.pathname.endsWith("/recommendations")) return new Response(JSON.stringify({ items: [{ recommendation_id: 8, opportunity_id: 1, opportunity_type: "PRICE_OPTIMIZATION", item_name: opportunity.item_name, supplier_name: "Supplier X", title: "Negotiate verified price variance", summary: "Verified evidence supports a focused commercial review.", reasoning: "The deterministic benchmark and supplier history support review.", recommended_action: "Review the benchmark and initiate a structured price negotiation.", estimated_impact: "89460", risks: null, next_steps: [], confidence_score: "0.87", model_name: "mock-model", prompt_version: "phase1-v1", created_at: "2026-01-11T10:00:00Z" }], total: 1, page: 1, page_size: 1, pages: 1 }), { status: 200 });
      return new Response(null, { status: 404 });
    });

    render(<CostOptimization />);

    await userEvent.click(await screen.findByRole("button", { name: "View opportunity 1" }));
    expect(await screen.findByRole("heading", { name: "Benchmark evidence" })).toBeInTheDocument();
    expect(screen.getByText("5 suppliers")).toBeInTheDocument();
    expect(screen.getByText("Supplier information")).toBeInTheDocument();
    expect(screen.getByText("12.0%")).toBeInTheDocument();
    expect(screen.getByText("Review the benchmark and initiate a structured price negotiation.")).toBeInTheDocument();
  });
});
