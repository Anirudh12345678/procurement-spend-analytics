import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { ErrorState, KpiCard, LoadingState, PageIntro, Panel } from "../components/UI";
import { currency, percent } from "../format";
import { useAsync } from "../hooks/useAsync";
import type { BusinessUnitAnalytics, CategoryAnalytics, ContractAnalytics, DashboardSummary, MonthlyAnalytics, OpportunitySummary, SupplierAnalytics } from "../types";

interface DashboardData {
  summary: DashboardSummary;
  monthly: MonthlyAnalytics[];
  categories: CategoryAnalytics[];
  suppliers: SupplierAnalytics[];
  businessUnits: BusinessUnitAnalytics[];
  contract: ContractAnalytics;
  opportunities: OpportunitySummary;
}

function loadDashboard(): Promise<DashboardData> {
  return Promise.all([
    api.get<DashboardSummary>("/dashboard/summary"),
    api.get<MonthlyAnalytics[]>("/analytics/spend/monthly"),
    api.get<CategoryAnalytics[]>("/analytics/spend/categories"),
    api.get<SupplierAnalytics[]>("/analytics/spend/suppliers"),
    api.get<BusinessUnitAnalytics[]>("/analytics/spend/business-units"),
    api.get<ContractAnalytics>("/analytics/contract-compliance"),
    api.get<OpportunitySummary>("/opportunities/summary"),
  ]).then(([summary, monthly, categories, suppliers, businessUnits, contract, opportunities]) => ({ summary, monthly, categories, suppliers, businessUnits, contract, opportunities }));
}

const tooltipFormatter = (value: unknown) => currency(Array.isArray(value) ? value[0] : value as number | string | undefined, true);

export function Dashboard() {
  const { data, error, loading, reload } = useAsync(loadDashboard);

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error?.message ?? "Dashboard data is unavailable."} retry={reload} />;

  const monthly = data.monthly.map((row) => ({ ...row, value: Number(row.spend), label: new Date(row.month).toLocaleDateString("en-US", { month: "short", year: "2-digit", timeZone: "UTC" }) }));
  const categories = data.categories.slice(0, 8).map((row) => ({ name: row.category_name, value: Number(row.spend) }));
  const suppliers = data.suppliers.slice(0, 8).map((row) => ({ name: row.supplier_name, value: Number(row.spend) }));
  const businessUnits = data.businessUnits.map((row) => ({ name: row.business_unit_name, value: Number(row.spend) }));
  const contract = [
    { name: "On contract", value: Number(data.contract.on_contract_spend), color: "#0891b2" },
    { name: "Off contract", value: Number(data.contract.off_contract_spend), color: "#f59e0b" },
  ];

  return (
    <>
      <PageIntro eyebrow="Executive overview" title="Procurement performance at a glance" description="A verified view of spend, supplier exposure, contract behavior, and identified cost opportunities." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <KpiCard label="Total spend" value={currency(data.summary.total_spend, true)} detail={currency(data.summary.total_spend)} accent="cyan" />
        <KpiCard label="Total orders" value={data.summary.total_orders.toLocaleString()} detail="Purchase-order lines" />
        <KpiCard label="Suppliers" value={data.summary.supplier_count.toLocaleString()} detail={`${data.summary.category_count} categories`} />
        <KpiCard label="Average order value" value={currency(data.summary.average_order_value, true)} detail={currency(data.summary.average_order_value)} />
        <KpiCard label="Off-contract spend" value={percent(data.contract.off_contract_percent)} detail={currency(data.contract.off_contract_spend, true)} accent="amber" />
        <KpiCard label="Cost opportunities" value={currency(data.opportunities.estimated_price_optimization_savings, true)} detail={`${data.opportunities.active_opportunity_count} active findings`} accent="emerald" />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Panel title="Monthly spend" subtitle="Spend movement across the available period" className="xl:col-span-2">
          <div className="h-80" aria-label="Monthly spend line chart">
            <ResponsiveContainer width="100%" height="100%"><LineChart data={monthly} margin={{ left: 8, right: 8 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" /><XAxis dataKey="label" tick={{ fontSize: 11 }} /><YAxis tickFormatter={(value) => currency(value, true)} tick={{ fontSize: 11 }} width={72} /><Tooltip formatter={tooltipFormatter} /><Line type="monotone" dataKey="value" name="Spend" stroke="#0891b2" strokeWidth={3} dot={false} /></LineChart></ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Contract compliance" subtitle={`${percent(data.contract.on_contract_percent)} of spend is on contract`}>
          <div className="h-64" aria-label="Contract compliance chart"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={contract} dataKey="value" nameKey="name" innerRadius={65} outerRadius={90} paddingAngle={3}>{contract.map((entry) => <Cell key={entry.name} fill={entry.color} />)}</Pie><Tooltip formatter={tooltipFormatter} /></PieChart></ResponsiveContainer></div>
          <div className="grid grid-cols-2 gap-3 text-center text-sm"><div className="rounded-lg bg-cyan-50 p-3"><strong className="block text-cyan-800">{percent(data.contract.on_contract_percent)}</strong><span className="text-xs text-slate-500">On contract</span></div><div className="rounded-lg bg-amber-50 p-3"><strong className="block text-amber-800">{percent(data.contract.off_contract_percent)}</strong><span className="text-xs text-slate-500">Off contract</span></div></div>
        </Panel>
        <Panel title="Category spend" subtitle="Highest-spend categories">
          <div className="h-72" aria-label="Category spend chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={categories} layout="vertical" margin={{ left: 10 }}><XAxis type="number" tickFormatter={(value) => currency(value, true)} tick={{ fontSize: 10 }} /><YAxis type="category" dataKey="name" width={105} tick={{ fontSize: 11 }} /><Tooltip formatter={tooltipFormatter} /><Bar dataKey="value" name="Spend" fill="#0f172a" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></div>
        </Panel>
        <Panel title="Top suppliers" subtitle="Spend ranked by supplier">
          <div className="h-72" aria-label="Supplier spend chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={suppliers} layout="vertical" margin={{ left: 10 }}><XAxis type="number" tickFormatter={(value) => currency(value, true)} tick={{ fontSize: 10 }} /><YAxis type="category" dataKey="name" width={115} tick={{ fontSize: 10 }} /><Tooltip formatter={tooltipFormatter} /><Bar dataKey="value" name="Spend" fill="#0891b2" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></div>
        </Panel>
        <Panel title="Business-unit spend" subtitle="Spend ownership across the organization">
          <div className="h-72" aria-label="Business unit spend chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={businessUnits}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis tickFormatter={(value) => currency(value, true)} tick={{ fontSize: 10 }} width={65} /><Tooltip formatter={tooltipFormatter} /><Bar dataKey="value" name="Spend" fill="#14b8a6" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div>
        </Panel>
      </div>
    </>
  );
}
