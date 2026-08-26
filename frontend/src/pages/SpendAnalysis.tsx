import { useMemo, useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, queryString } from "../api/client";
import { EmptyState, ErrorState, KpiCard, LoadingState, PageIntro, Panel } from "../components/UI";
import { currency, percent } from "../format";
import { useAsync } from "../hooks/useAsync";
import type { BusinessUnitAnalytics, BusinessUnitRecord, CategoryAnalytics, CategoryRecord, MonthlyAnalytics, Paginated, SupplierAnalytics, SupplierConcentration, SupplierRecord } from "../types";

interface Filters { date_from: string; date_to: string; supplier_id: string; category_id: string; business_unit_id: string; country: string }
const initialFilters: Filters = { date_from: "", date_to: "", supplier_id: "", category_id: "", business_unit_id: "", country: "" };

function SelectField({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: ReactNode }) {
  return <label className="text-xs font-semibold text-slate-600">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-slate-800">{children}</select></label>;
}

export function SpendAnalysis() {
  const [draft, setDraft] = useState(initialFilters);
  const [filters, setFilters] = useState(initialFilters);
  const filterQuery = useMemo(() => queryString({ ...filters }), [filters]);
  const reference = useAsync(() => Promise.all([
    api.get<Paginated<SupplierRecord>>("/suppliers?page_size=100"),
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

  const update = (key: keyof Filters, value: string) => setDraft((current) => ({ ...current, [key]: value }));
  const countries = [...new Set(reference.data?.[0].items.map((supplier) => supplier.country) ?? [])].sort();

  return (
    <>
      <PageIntro eyebrow="Spend intelligence" title="Understand where procurement value flows" description="Filter the deterministic analytics by time, supplier, category, business unit, or supplier country." />
      <Panel title="Analysis filters" subtitle="Filters are applied consistently across every chart and table below">
        <form className="grid gap-3 md:grid-cols-2 xl:grid-cols-6" onSubmit={(event) => { event.preventDefault(); setFilters(draft); }}>
          <label className="text-xs font-semibold text-slate-600">From date<input type="date" value={draft.date_from} onChange={(event) => update("date_from", event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          <label className="text-xs font-semibold text-slate-600">To date<input type="date" value={draft.date_to} onChange={(event) => update("date_to", event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          <SelectField label="Supplier" value={draft.supplier_id} onChange={(value) => update("supplier_id", value)}><option value="">All suppliers</option>{reference.data?.[0].items.map((item) => <option key={item.supplier_id} value={item.supplier_id}>{item.supplier_name}</option>)}</SelectField>
          <SelectField label="Category" value={draft.category_id} onChange={(value) => update("category_id", value)}><option value="">All categories</option>{reference.data?.[1].map((item) => <option key={item.category_id} value={item.category_id}>{item.category_name}</option>)}</SelectField>
          <SelectField label="Business unit" value={draft.business_unit_id} onChange={(value) => update("business_unit_id", value)}><option value="">All business units</option>{reference.data?.[2].map((item) => <option key={item.business_unit_id} value={item.business_unit_id}>{item.business_unit_name}</option>)}</SelectField>
          <SelectField label="Supplier country" value={draft.country} onChange={(value) => update("country", value)}><option value="">All countries</option>{countries.map((country) => <option key={country}>{country}</option>)}</SelectField>
          <div className="flex gap-2 xl:col-span-6 xl:justify-end"><button type="button" onClick={() => { setDraft(initialFilters); setFilters(initialFilters); }} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium">Reset</button><button type="submit" className="rounded-lg bg-slate-950 px-5 py-2 text-sm font-medium text-white">Apply filters</button></div>
        </form>
      </Panel>

      <div className="mt-6">
        {analytics.loading && <LoadingState label="Applying spend filters…" />}
        {analytics.error && <ErrorState message={analytics.error.message} retry={analytics.reload} />}
        {analytics.data && (() => {
          const [monthly, categories, suppliers, units, concentration] = analytics.data;
          const monthlyData = monthly.map((row) => ({ label: new Date(row.month).toLocaleDateString("en-US", { month: "short", year: "2-digit", timeZone: "UTC" }), spend: Number(row.spend) }));
          const categoryData = categories.map((row) => ({ name: row.category_name, spend: Number(row.spend) }));
          const unitData = units.map((row) => ({ name: row.business_unit_name, spend: Number(row.spend) }));
          const spendTooltip = (value: unknown) => currency(Array.isArray(value) ? value[0] : value as number | string | undefined, true);
          return <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><KpiCard label="Filtered spend" value={currency(concentration.total_spend, true)} accent="cyan" /><KpiCard label="Active suppliers" value={concentration.supplier_count.toLocaleString()} /><KpiCard label="Top 5 concentration" value={percent(concentration.top_5_concentration_percent)} detail={currency(concentration.top_5_spend, true)} accent="amber" /><KpiCard label="Top 10 concentration" value={percent(concentration.top_10_concentration_percent)} detail={currency(concentration.top_10_spend, true)} /></div>
            <div className="mt-6 grid gap-6 xl:grid-cols-2">
              <Panel title="Monthly spend" subtitle="Filtered monthly movement"><div className="h-72"><ResponsiveContainer width="100%" height="100%"><LineChart data={monthlyData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" tick={{ fontSize: 10 }} /><YAxis tickFormatter={(value) => currency(value, true)} width={65} tick={{ fontSize: 10 }} /><Tooltip formatter={spendTooltip} /><Line dataKey="spend" stroke="#0891b2" strokeWidth={3} dot={false} /></LineChart></ResponsiveContainer></div></Panel>
              <Panel title="Category breakdown" subtitle="Spend by procurement category"><div className="h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={categoryData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis tickFormatter={(value) => currency(value, true)} width={65} tick={{ fontSize: 10 }} /><Tooltip formatter={spendTooltip} /><Bar dataKey="spend" fill="#0f172a" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div></Panel>
              <Panel title="Business-unit breakdown" subtitle="Organizational spend ownership"><div className="h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={unitData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis tickFormatter={(value) => currency(value, true)} width={65} tick={{ fontSize: 10 }} /><Tooltip formatter={spendTooltip} /><Bar dataKey="spend" fill="#14b8a6" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div></Panel>
              <Panel title="Supplier ranking" subtitle="Sorted by spend contribution">
                {suppliers.length === 0 ? <EmptyState message="No supplier spend matches these filters." /> : <div className="max-h-72 overflow-auto"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-white text-xs uppercase text-slate-400"><tr><th className="py-2">Rank</th><th>Supplier</th><th>Country</th><th className="text-right">Spend</th><th className="text-right">Share</th></tr></thead><tbody>{suppliers.map((supplier) => <tr key={supplier.supplier_id} className="border-t border-slate-100"><td className="py-3 font-medium">#{supplier.rank}</td><td>{supplier.supplier_name}</td><td className="text-slate-500">{supplier.country}</td><td className="text-right font-medium">{currency(supplier.spend, true)}</td><td className="text-right">{percent(supplier.share_percent)}</td></tr>)}</tbody></table></div>}
              </Panel>
            </div>
          </>;
        })()}
      </div>
    </>
  );
}
