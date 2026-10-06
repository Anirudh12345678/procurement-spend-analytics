import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, queryString } from "../api/client";
import { EmptyState, ErrorState, KpiCard, LoadingState, PageIntro, Pagination, Panel } from "../components/UI";
import { currency, percent } from "../format";
import { useAsync } from "../hooks/useAsync";
import type { BusinessUnitAnalytics, BusinessUnitRecord, CategoryAnalytics, CategoryRecord, MonthlyAnalytics, Paginated, SupplierAnalytics, SupplierConcentration, SupplierRecord } from "../types";

interface Filters {
  date_from: string;
  date_to: string;
  supplier_id: string;
  category_id: string;
  business_unit_id: string;
  country: string;
}

type SupplierSort = "rank" | "supplier_name" | "country" | "spend" | "share_percent";
type SortDirection = "asc" | "desc";

const initialFilters: Filters = { date_from: "", date_to: "", supplier_id: "", category_id: "", business_unit_id: "", country: "" };
const supplierPageSize = 10;

function filtersFromParams(params: URLSearchParams): Filters {
  return {
    date_from: params.get("date_from") ?? "",
    date_to: params.get("date_to") ?? "",
    supplier_id: params.get("supplier_id") ?? "",
    category_id: params.get("category_id") ?? "",
    business_unit_id: params.get("business_unit_id") ?? "",
    country: params.get("country") ?? "",
  };
}

async function loadSuppliers(): Promise<SupplierRecord[]> {
  const first = await api.get<Paginated<SupplierRecord>>("/suppliers?page=1&page_size=100");
  if (first.pages <= 1) return first.items;
  const remaining = await Promise.all(Array.from({ length: first.pages - 1 }, (_, index) => api.get<Paginated<SupplierRecord>>(`/suppliers?page=${index + 2}&page_size=100`)));
  return [first, ...remaining].flatMap((page) => page.items);
}

function SelectField({ label, value, onChange, disabled = false, children }: { label: string; value: string; onChange: (value: string) => void; disabled?: boolean; children: ReactNode }) {
  return <label className="text-xs font-semibold text-slate-600">{label}<select disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-slate-800 disabled:bg-slate-100 disabled:text-slate-400">{children}</select></label>;
}

function SortButton({ label, field, active, direction, onSort }: { label: string; field: SupplierSort; active: boolean; direction: SortDirection; onSort: (field: SupplierSort) => void }) {
  return <button type="button" onClick={() => onSort(field)} className="inline-flex items-center gap-1 font-semibold hover:text-slate-700" aria-label={`Sort suppliers by ${label}`}>{label}<span aria-hidden="true">{active ? (direction === "asc" ? "↑" : "↓") : "↕"}</span></button>;
}

export function SpendAnalysis() {
  const [searchParams, setSearchParams] = useSearchParams();
  const appliedKey = searchParams.toString();
  const filters = useMemo(() => filtersFromParams(new URLSearchParams(appliedKey)), [appliedKey]);
  const [draft, setDraft] = useState<Filters>(() => filters);
  const [supplierSort, setSupplierSort] = useState<SupplierSort>("rank");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [supplierPage, setSupplierPage] = useState(1);
  const filterQuery = useMemo(() => queryString({ ...filters }), [filters]);

  useEffect(() => setDraft(filters), [filters]);

  const reference = useAsync(() => Promise.all([
    loadSuppliers(),
    api.get<CategoryRecord[]>("/categories"),
    api.get<BusinessUnitRecord[]>("/business-units"),
  ]));
  const analytics = useAsync(() => Promise.all([
    api.get<MonthlyAnalytics[]>(`/analytics/spend/monthly${filterQuery}`),
    api.get<CategoryAnalytics[]>(`/analytics/spend/categories${filterQuery}`),
    api.get<SupplierAnalytics[]>(`/analytics/spend/suppliers${filterQuery}`),
    api.get<BusinessUnitAnalytics[]>(`/analytics/spend/business-units${filterQuery}`),
    api.get<SupplierConcentration>(`/analytics/supplier-concentration${filterQuery}`),
  ]), [filterQuery]);

  const supplierRows = useMemo(() => {
    const rows = [...(analytics.data?.[2] ?? [])];
    return rows.sort((left, right) => {
      const numeric = supplierSort === "rank" || supplierSort === "spend" || supplierSort === "share_percent";
      const leftValue = numeric ? Number(left[supplierSort]) : String(left[supplierSort]).toLocaleLowerCase();
      const rightValue = numeric ? Number(right[supplierSort]) : String(right[supplierSort]).toLocaleLowerCase();
      const comparison = typeof leftValue === "number" && typeof rightValue === "number" ? leftValue - rightValue : String(leftValue).localeCompare(String(rightValue));
      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [analytics.data, sortDirection, supplierSort]);
  const supplierPages = Math.max(1, Math.ceil(supplierRows.length / supplierPageSize));
  const visibleSupplierPage = Math.min(supplierPage, supplierPages);
  const visibleSuppliers = supplierRows.slice((visibleSupplierPage - 1) * supplierPageSize, visibleSupplierPage * supplierPageSize);

  const update = (key: keyof Filters, value: string) => setDraft((current) => ({ ...current, [key]: value }));
  const countries = useMemo(() => [...new Set(reference.data?.[0].map((supplier) => supplier.country) ?? [])].sort(), [reference.data]);

  const applyFilters = () => {
    const next = new URLSearchParams();
    Object.entries(draft).forEach(([key, value]) => { if (value) next.set(key, value); });
    setSupplierPage(1);
    setSearchParams(next);
  };

  const resetFilters = () => {
    setDraft(initialFilters);
    setSupplierPage(1);
    setSearchParams(new URLSearchParams());
  };

  const sortSuppliers = (field: SupplierSort) => {
    if (field === supplierSort) setSortDirection((current) => current === "asc" ? "desc" : "asc");
    else {
      setSupplierSort(field);
      setSortDirection(field === "supplier_name" || field === "country" || field === "rank" ? "asc" : "desc");
    }
    setSupplierPage(1);
  };

  return (
    <>
      <PageIntro eyebrow="Spend intelligence" title="Understand where procurement value flows" description="Filter deterministic analytics by time, supplier, category, business unit, or supplier country. Applied filters are preserved in the page URL." />
      <Panel title="Analysis filters" subtitle="Filters are applied consistently across every chart and table below">
        <form className="grid gap-3 md:grid-cols-2 xl:grid-cols-6" onSubmit={(event) => { event.preventDefault(); applyFilters(); }}>
          <label className="text-xs font-semibold text-slate-600">From date<input type="date" value={draft.date_from} onChange={(event) => update("date_from", event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          <label className="text-xs font-semibold text-slate-600">To date<input type="date" value={draft.date_to} onChange={(event) => update("date_to", event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          <SelectField label="Supplier" disabled={reference.loading || Boolean(reference.error)} value={draft.supplier_id} onChange={(value) => update("supplier_id", value)}><option value="">All suppliers</option>{reference.data?.[0].map((item) => <option key={item.supplier_id} value={item.supplier_id}>{item.supplier_name}</option>)}</SelectField>
          <SelectField label="Category" disabled={reference.loading || Boolean(reference.error)} value={draft.category_id} onChange={(value) => update("category_id", value)}><option value="">All categories</option>{reference.data?.[1].map((item) => <option key={item.category_id} value={item.category_id}>{item.category_name}</option>)}</SelectField>
          <SelectField label="Business unit" disabled={reference.loading || Boolean(reference.error)} value={draft.business_unit_id} onChange={(value) => update("business_unit_id", value)}><option value="">All business units</option>{reference.data?.[2].map((item) => <option key={item.business_unit_id} value={item.business_unit_id}>{item.business_unit_name}</option>)}</SelectField>
          <SelectField label="Supplier country" disabled={reference.loading || Boolean(reference.error)} value={draft.country} onChange={(value) => update("country", value)}><option value="">All countries</option>{countries.map((country) => <option key={country} value={country}>{country}</option>)}</SelectField>
          <div className="flex items-center gap-3 text-xs text-slate-500 xl:col-span-4">{reference.loading ? <span>Loading filter options…</span> : null}{reference.error ? <span role="alert" className="text-rose-700">Filter options failed to load. <button type="button" onClick={reference.reload} className="font-semibold underline">Retry</button></span> : null}</div>
          <div className="flex gap-2 xl:col-span-2 xl:justify-end"><button type="button" onClick={resetFilters} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium">Reset</button><button type="submit" className="rounded-lg bg-slate-950 px-5 py-2 text-sm font-medium text-white">Apply filters</button></div>
        </form>
      </Panel>

      <div className="mt-6">
        {analytics.loading && <LoadingState label="Applying spend filters…" />}
        {analytics.error && <ErrorState message={analytics.error.message} retry={analytics.reload} />}
        {analytics.data && (() => {
          const [monthly, categories, , units, concentration] = analytics.data;
          const monthlyData = monthly.map((row) => ({ label: new Date(row.month).toLocaleDateString("en-US", { month: "short", year: "2-digit", timeZone: "UTC" }), spend: Number(row.spend) }));
          const categoryData = categories.map((row) => ({ name: row.category_name, spend: Number(row.spend) }));
          const unitData = units.map((row) => ({ name: row.business_unit_name, spend: Number(row.spend) }));
          const spendTooltip = (value: unknown) => currency(Array.isArray(value) ? value[0] : value as number | string | undefined, true);
          return <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><KpiCard label="Filtered spend" value={currency(concentration.total_spend, true)} accent="cyan" /><KpiCard label="Active suppliers" value={concentration.supplier_count.toLocaleString()} /><KpiCard label="Top 5 concentration" value={percent(concentration.top_5_concentration_percent)} detail={currency(concentration.top_5_spend, true)} accent="amber" /><KpiCard label="Top 10 concentration" value={percent(concentration.top_10_concentration_percent)} detail={currency(concentration.top_10_spend, true)} /></div>
            <div className="mt-6 grid gap-6 xl:grid-cols-2">
              <Panel title="Monthly spend" subtitle="Filtered monthly movement">{monthlyData.length === 0 ? <EmptyState message="No monthly spend matches these filters." /> : <div className="h-72 min-w-0"><ResponsiveContainer width="100%" height="100%" minWidth={0}><LineChart data={monthlyData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" tick={{ fontSize: 10 }} /><YAxis tickFormatter={(value) => currency(value, true)} width={65} tick={{ fontSize: 10 }} /><Tooltip formatter={spendTooltip} /><Line dataKey="spend" stroke="#0891b2" strokeWidth={3} dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></div>}</Panel>
              <Panel title="Category breakdown" subtitle="Spend by procurement category">{categoryData.length === 0 ? <EmptyState message="No category spend matches these filters." /> : <div className="h-72 min-w-0"><ResponsiveContainer width="100%" height="100%" minWidth={0}><BarChart data={categoryData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis tickFormatter={(value) => currency(value, true)} width={65} tick={{ fontSize: 10 }} /><Tooltip formatter={spendTooltip} /><Bar dataKey="spend" fill="#0f172a" radius={[5, 5, 0, 0]} isAnimationActive={false} /></BarChart></ResponsiveContainer></div>}</Panel>
              <Panel title="Business-unit breakdown" subtitle="Organizational spend ownership">{unitData.length === 0 ? <EmptyState message="No business-unit spend matches these filters." /> : <div className="h-72 min-w-0"><ResponsiveContainer width="100%" height="100%" minWidth={0}><BarChart data={unitData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis tickFormatter={(value) => currency(value, true)} width={65} tick={{ fontSize: 10 }} /><Tooltip formatter={spendTooltip} /><Bar dataKey="spend" fill="#14b8a6" radius={[5, 5, 0, 0]} isAnimationActive={false} /></BarChart></ResponsiveContainer></div>}</Panel>
              <Panel title="Supplier ranking" subtitle="Sortable and paginated supplier-spend contribution">
                {supplierRows.length === 0 ? <EmptyState message="No supplier spend matches these filters." /> : <><div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="text-xs uppercase text-slate-400"><tr><th className="py-2" aria-sort={supplierSort === "rank" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}><SortButton label="Rank" field="rank" active={supplierSort === "rank"} direction={sortDirection} onSort={sortSuppliers} /></th><th aria-sort={supplierSort === "supplier_name" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}><SortButton label="Supplier" field="supplier_name" active={supplierSort === "supplier_name"} direction={sortDirection} onSort={sortSuppliers} /></th><th aria-sort={supplierSort === "country" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}><SortButton label="Country" field="country" active={supplierSort === "country"} direction={sortDirection} onSort={sortSuppliers} /></th><th className="text-right" aria-sort={supplierSort === "spend" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}><SortButton label="Spend" field="spend" active={supplierSort === "spend"} direction={sortDirection} onSort={sortSuppliers} /></th><th className="text-right" aria-sort={supplierSort === "share_percent" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}><SortButton label="Share" field="share_percent" active={supplierSort === "share_percent"} direction={sortDirection} onSort={sortSuppliers} /></th></tr></thead><tbody>{visibleSuppliers.map((supplier) => <tr key={supplier.supplier_id} className="border-t border-slate-100"><td className="py-3 font-medium">#{supplier.rank}</td><td>{supplier.supplier_name}</td><td className="text-slate-500">{supplier.country}</td><td className="text-right font-medium">{currency(supplier.spend, true)}</td><td className="text-right">{percent(supplier.share_percent)}</td></tr>)}</tbody></table></div><Pagination page={visibleSupplierPage} pages={supplierPages} onPage={setSupplierPage} /></>}
              </Panel>
            </div>
          </>;
        })()}
      </div>
    </>
  );
}
