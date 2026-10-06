import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AIAdvisor } from "../pages/AIAdvisor";

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
  supporting_metrics: {},
  created_at: "2026-01-10T10:00:00Z",
};

const recommendation = {
  recommendation_id: 8,
  opportunity_id: 1,
  opportunity_type: "PRICE_OPTIMIZATION",
  item_name: opportunity.item_name,
  supplier_name: "Supplier X",
  title: "Negotiate verified price variance",
  summary: "Verified analytical evidence supports a focused procurement review.",
  reasoning: "The recommendation relies only on deterministic backend values.",
  recommended_action: "Review the benchmark and initiate a structured price negotiation.",
  estimated_impact: "89460",
  risks: "Validate continuity and quality before action.",
  next_steps: ["Confirm scope with the procurement owner."],
  confidence_score: "0.87",
  model_name: "mock-model",
  prompt_version: "phase1-v1",
  created_at: "2026-01-11T10:00:00Z",
};

describe("AIAdvisor", () => {
  afterEach(() => vi.restoreAllMocks());

  it("generates a recommendation for a selected backend opportunity and refreshes the list", async () => {
    let generated = false;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/opportunities")) return new Response(JSON.stringify({ items: [opportunity], total: 1, page: 1, page_size: 100, pages: 1 }), { status: 200 });
      if (url.pathname.endsWith("/recommendations/generate") && init?.method === "POST") {
        generated = true;
        return new Response(JSON.stringify(recommendation), { status: 201 });
      }
      if (url.pathname.endsWith("/recommendations")) return new Response(JSON.stringify({ items: generated ? [recommendation] : [], total: generated ? 1 : 0, page: 1, page_size: 10, pages: generated ? 1 : 0 }), { status: 200 });
      return new Response(null, { status: 404 });
    });

    render(<AIAdvisor />);

    await userEvent.selectOptions(await screen.findByLabelText("Opportunity for recommendation"), "1");
    await userEvent.click(screen.getByRole("button", { name: "Generate recommendation" }));

    expect(await screen.findByText("Negotiate verified price variance")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.some(([input, init]) => {
      if (!String(input).endsWith("/recommendations/generate") || init?.method !== "POST") return false;
      return JSON.parse(String(init.body)).opportunity_id === 1;
    })).toBe(true));
  });
});
