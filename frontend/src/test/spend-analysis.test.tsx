import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SpendAnalysis } from "../pages/SpendAnalysis";

const suppliers = Array.from({ length: 12 }, (_, index) => ({
  supplier_id: `S${index + 1}`,
  supplier_name: `Supplier ${String(index + 1).padStart(2, "0")}`,
  country: index % 2 === 0 ? "India" : "Germany",
  spend: String((index + 1) * 1000),
  share_percent: String(index + 1),
  transaction_count: index + 1,
  average_order_value: "1000",
  total_quantity: "10",
  rank: index + 1,
}));

function mockSpendApi() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = new URL(String(input));
    if (url.pathname === "/api/suppliers") return new Response(JSON.stringify({ items: suppliers.map(({ spend: _spend, share_percent: _share, transaction_count: _transactions, average_order_value: _average, total_quantity: _quantity, rank: _rank, ...supplier }) => supplier), total: 12, page: 1, page_size: 100, pages: 1 }), { status: 200 });
    if (url.pathname.endsWith("/categories")) return new Response(JSON.stringify([{ category_id: 1, category_name: "Electronics", item_count: 2, total_spend: "5000" }]), { status: 200 });
    if (url.pathname.endsWith("/business-units")) return new Response(JSON.stringify([{ business_unit_id: 1, business_unit_name: "Operations", transaction_count: 4, total_spend: "5000" }]), { status: 200 });
    if (url.pathname.endsWith("/spend/monthly")) return new Response(JSON.stringify([{ month: "2025-01-01", spend: "5000", transaction_count: 4, average_order_value: "1250", growth_percent: null }]), { status: 200 });
    if (url.pathname.endsWith("/spend/categories")) return new Response(JSON.stringify([{ category_id: 1, category_name: "Electronics", spend: "5000", share_percent: "100", transaction_count: 4, average_order_value: "1250", supplier_count: 2 }]), { status: 200 });
    if (url.pathname.endsWith("/spend/suppliers")) return new Response(JSON.stringify(suppliers), { status: 200 });
    if (url.pathname.endsWith("/spend/business-units")) return new Response(JSON.stringify([{ business_unit_id: 1, business_unit_name: "Operations", spend: "5000", share_percent: "100", transaction_count: 4 }]), { status: 200 });
    if (url.pathname.endsWith("/supplier-concentration")) return new Response(JSON.stringify({ total_spend: "78000", supplier_count: 12, top_5_spend: "50000", top_5_concentration_percent: "64.1", top_10_spend: "75000", top_10_concentration_percent: "96.2" }), { status: 200 });
    return new Response(null, { status: 404 });
  });
}

describe("SpendAnalysis", () => {
  afterEach(() => vi.restoreAllMocks());

  it("applies all filter values through backend query parameters", async () => {
    const fetchMock = mockSpendApi();
    render(<MemoryRouter><SpendAnalysis /></MemoryRouter>);

    await screen.findByRole("option", { name: "Supplier 01" });
    fireEvent.change(screen.getByLabelText("From date"), { target: { value: "2025-01-01" } });
    fireEvent.change(screen.getByLabelText("To date"), { target: { value: "2025-06-30" } });
    await userEvent.selectOptions(screen.getByLabelText("Supplier"), "S1");
    await userEvent.selectOptions(screen.getByLabelText("Category"), "1");
    await userEvent.selectOptions(screen.getByLabelText("Business unit"), "1");
    await userEvent.selectOptions(screen.getByLabelText("Supplier country"), "India");
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => {
      const url = new URL(String(input));
      return url.pathname.endsWith("/spend/monthly") && url.searchParams.get("date_from") === "2025-01-01" && url.searchParams.get("date_to") === "2025-06-30" && url.searchParams.get("supplier_id") === "S1" && url.searchParams.get("category_id") === "1" && url.searchParams.get("business_unit_id") === "1" && url.searchParams.get("country") === "India";
    })).toBe(true));
  });

  it("sorts and paginates the supplier table without recalculating analytics", async () => {
    mockSpendApi();
    render(<MemoryRouter><SpendAnalysis /></MemoryRouter>);

    const table = await screen.findByRole("table");
    expect(within(table).getByText("Supplier 01")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(within(table).getByText("Supplier 11")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sort suppliers by Spend" }));
    expect(within(table).getByText("Supplier 12")).toBeInTheDocument();
  });
});
