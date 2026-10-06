import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { ApiError, api, queryString } from "../api/client";
import { EmptyState, ErrorState, KpiCard, LoadingState, PageIntro, Pagination, Panel, PriorityBadge } from "../components/UI";
import { currency, label, number, percent } from "../format";
import { useAsync } from "../hooks/useAsync";
import type { Benchmark, Opportunity, OpportunitySummary, Paginated, Recommendation, SupplierDetail } from "../types";

interface OpportunityDetailData {
  opportunity: Opportunity;
  benchmark: Benchmark | null;
  supplier: SupplierDetail | null;
  recommendation: Recommendation | null;
}

async function optionalGet<T>(path: string): Promise<T | null> {
  try {
    return await api.get<T>(path);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

async function loadOpportunityDetail(opportunity: Opportunity): Promise<OpportunityDetailData> {
  const [detail, benchmark, supplier, recommendations] = await Promise.all([
    api.get<Opportunity>(`/opportunities/${opportunity.opportunity_id}`),
    optionalGet<Benchmark>(`/benchmarks/${opportunity.item_id}`),
    opportunity.supplier_id ? optionalGet<SupplierDetail>(`/suppliers/${opportunity.supplier_id}`) : Promise.resolve(null),
    api.get<Paginated<Recommendation>>(`/recommendations${queryString({ opportunity_id: opportunity.opportunity_id, page: 1, page_size: 1 })}`),
  ]);
  return { opportunity: detail, benchmark, supplier, recommendation: recommendations.items[0] ?? null };
}

function DetailMetric({ term, value }: { term: string; value: string }) {
  return <div className="rounded-lg bg-slate-50 p-3"><dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">{term}</dt><dd className="mt-1 text-sm font-medium text-slate-800">{value}</dd></div>;
}

function OpportunityDetail({ initialOpportunity, close }: { initialOpportunity: Opportunity; close: () => void }) {
  const details = useAsync(() => loadOpportunityDetail(initialOpportunity), [initialOpportunity.opportunity_id]);
  const opportunity = details.data?.opportunity ?? initialOpportunity;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") close(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [close]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/55" role="dialog" aria-modal="true" aria-labelledby="opportunity-title" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
      <div className="h-full w-full max-w-2xl overflow-y-auto bg-white p-6 shadow-2xl md:p-8">
        <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-wider text-cyan-700">{label(opportunity.opportunity_type)}</p><h2 id="opportunity-title" className="mt-2 text-2xl font-semibold">{opportunity.item_name}</h2><p className="mt-1 text-sm text-slate-500">{opportunity.supplier_name ?? opportunity.category_name}</p></div><button autoFocus onClick={close} aria-label="Close opportunity detail" className="rounded-lg border border-slate-200 p-2"><X size={20} /></button></div>
        <div className="mt-6 flex flex-wrap gap-2"><PriorityBadge priority={opportunity.priority_level} /><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">Confidence {percent(Number(opportunity.confidence_score) * 100)}</span><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{label(opportunity.status)}</span></div>

        {details.loading ? <div className="mt-6"><LoadingState label="Loading verified opportunity evidence…" /></div> : null}
        {details.error ? <div className="mt-6"><ErrorState message={details.error.message} retry={details.reload} /></div> : null}
        {details.data ? <>
          <div className="mt-7 grid gap-3 sm:grid-cols-2">
            <KpiCard label="Estimated opportunity" value={currency(opportunity.estimated_savings, true)} detail="Not guaranteed savings" accent="emerald" />
            <KpiCard label="Spend under review" value={currency(opportunity.review_spend, true)} />
            <KpiCard label="Actual price" value={opportunity.actual_price !== null ? currency(opportunity.actual_price) : "Not applicable"} />
            <KpiCard label="Benchmark price" value={opportunity.benchmark_price !== null ? currency(opportunity.benchmark_price) : "Not applicable"} accent="cyan" />
          </div>

          <Panel title="Opportunity explanation" className="mt-6"><p className="text-sm leading-6 text-slate-600">This deterministic finding was generated from verified purchase-order data. {opportunity.price_variance_percent !== null ? `The weighted actual unit price is ${percent(opportunity.price_variance_percent)} above the item benchmark.` : "The review trigger reflects configured procurement policy and supplier-performance thresholds."}</p></Panel>

          <Panel title="Benchmark evidence" subtitle="Stored item-price distribution calculated by the backend" className="mt-4">
            {details.data.benchmark ? <dl className="grid gap-3 sm:grid-cols-2"><DetailMetric term="P25 benchmark" value={currency(details.data.benchmark.p25_price)} /><DetailMetric term="Median price" value={currency(details.data.benchmark.median_price)} /><DetailMetric term="Observed range" value={`${currency(details.data.benchmark.min_price)} – ${currency(details.data.benchmark.max_price)}`} /><DetailMetric term="Supplier coverage" value={`${details.data.benchmark.supplier_count.toLocaleString()} suppliers`} /><DetailMetric term="Quantity covered" value={number(details.data.benchmark.total_quantity)} /><DetailMetric term="Calculated" value={new Date(details.data.benchmark.calculated_at).toLocaleDateString()} /></dl> : <EmptyState message="No stored benchmark is available for this item." />}
          </Panel>

          <Panel title="Supplier information" subtitle="Verified supplier performance from purchase-order history" className="mt-4">
            {details.data.supplier ? <dl className="grid gap-3 sm:grid-cols-2"><DetailMetric term="Supplier" value={details.data.supplier.supplier_name} /><DetailMetric term="Country" value={details.data.supplier.country} /><DetailMetric term="Total spend" value={currency(details.data.supplier.total_spend, true)} /><DetailMetric term="Transactions" value={details.data.supplier.transaction_count.toLocaleString()} /><DetailMetric term="On contract" value={percent(details.data.supplier.on_contract_percent)} /><DetailMetric term="Quality rejection rate" value={percent(details.data.supplier.rejection_rate_percent)} /><DetailMetric term="Late delivery rate" value={percent(details.data.supplier.late_delivery_rate_percent)} /></dl> : <EmptyState message="This opportunity is category-level and has no individual supplier record." />}
          </Panel>

          <Panel title="Supporting metrics" className="mt-4">
            {Object.keys(opportunity.supporting_metrics).length === 0 ? <EmptyState message="No additional supporting metrics are available." /> : <dl className="grid gap-3 sm:grid-cols-2">{Object.entries(opportunity.supporting_metrics).map(([key, value]) => <DetailMetric key={key} term={label(key)} value={String(value)} />)}</dl>}
          </Panel>

          <Panel title="Recommended action" subtitle="Available only when an advisory note has been generated" className="mt-4">
            {details.data.recommendation ? <div><p className="font-semibold text-slate-900">{details.data.recommendation.title}</p><p className="mt-2 text-sm leading-6 text-slate-600">{details.data.recommendation.recommended_action}</p><p className="mt-3 text-xs text-slate-500">Estimated impact {currency(details.data.recommendation.estimated_impact, true)} · {details.data.recommendation.model_name}</p></div> : <EmptyState message="No AI recommendation has been generated for this opportunity yet." />}
          </Panel>
          <p className="mt-5 text-xs leading-5 text-slate-500">Opportunity values are independently calculated and should not be summed across overlapping findings without procurement review.</p>
        </> : null}
      </div>
    </div>
  );
}

export function CostOptimization() {
  const [page, setPage] = useState(1);
  const [type, setType] = useState("");
  const [priority, setPriority] = useState("");
  const [selected, setSelected] = useState<Opportunity | null>(null);
  const query = queryString({ page, page_size: 15, opportunity_type: type, priority });
  const summary = useAsync(() => api.get<OpportunitySummary>("/opportunities/summary"));
  const opportunities = useAsync(() => api.get<Paginated<Opportunity>>(`/opportunities${query}`), [query]);

  if (summary.loading) return <LoadingState />;
  if (summary.error || !summary.data) return <ErrorState message={summary.error?.message ?? "Opportunity summary is unavailable."} retry={summary.reload} />;

  return (
    <>
      <PageIntro eyebrow="Cost optimization" title="Prioritized, explainable procurement opportunities" description="Savings values represent deterministic opportunities—not guarantees—and non-price findings are separated as spend under review." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Total opportunities" value={summary.data.active_opportunity_count.toLocaleString()} detail={`${summary.data.critical_count} critical`} />
        <KpiCard label="Estimated opportunity" value={currency(summary.data.estimated_price_optimization_savings, true)} detail="Price optimization only" accent="emerald" />
        <KpiCard label="High priority" value={summary.data.high_priority_count.toLocaleString()} detail="Procurement review recommended" accent="amber" />
        <KpiCard label="Price optimization" value={summary.data.price_optimization_count.toLocaleString()} detail={summary.data.savings_note} accent="cyan" />
      </div>
      <Panel title="Opportunity register" subtitle="Use the filters to focus the deterministic review queue" className="mt-6">
        <div className="mb-5 flex flex-wrap gap-3">
          <label className="text-xs font-semibold text-slate-600">Opportunity type<select aria-label="Opportunity type" value={type} onChange={(event) => { setType(event.target.value); setPage(1); }} className="ml-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal"><option value="">All types</option><option value="PRICE_OPTIMIZATION">Price optimization</option><option value="CONTRACT_LEAKAGE">Contract leakage</option><option value="SUPPLIER_CONSOLIDATION">Supplier consolidation</option><option value="SUPPLIER_PERFORMANCE">Supplier performance</option></select></label>
          <label className="text-xs font-semibold text-slate-600">Priority<select aria-label="Priority" value={priority} onChange={(event) => { setPriority(event.target.value); setPage(1); }} className="ml-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal"><option value="">All priorities</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label>
        </div>
        {opportunities.loading && <LoadingState label="Loading opportunity register…" />}
        {opportunities.error && <ErrorState message={opportunities.error.message} retry={opportunities.reload} />}
        {opportunities.data && (opportunities.data.items.length === 0 ? <EmptyState message="No opportunities match these filters." /> : <>
          <div className="overflow-x-auto"><table className="w-full min-w-[960px] text-left text-sm"><thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400"><tr><th className="pb-3">Priority</th><th>Opportunity</th><th>Item / supplier</th><th className="text-right">Actual</th><th className="text-right">Benchmark</th><th className="text-right">Variance</th><th className="text-right">Estimated value</th><th className="text-right">Confidence</th></tr></thead><tbody>{opportunities.data.items.map((opportunity) => <tr key={opportunity.opportunity_id} className="border-b border-slate-100 hover:bg-slate-50"><td className="py-4"><PriorityBadge priority={opportunity.priority_level} /></td><td className="font-medium text-slate-800"><button aria-label={`View opportunity ${opportunity.opportunity_id}`} onClick={() => setSelected(opportunity)} className="text-left font-medium text-cyan-800 hover:underline">{label(opportunity.opportunity_type)}</button></td><td><span className="block font-medium">{opportunity.item_name}</span><span className="text-xs text-slate-500">{opportunity.supplier_name ?? opportunity.category_name}</span></td><td className="text-right">{opportunity.actual_price !== null ? currency(opportunity.actual_price) : "—"}</td><td className="text-right">{opportunity.benchmark_price !== null ? currency(opportunity.benchmark_price) : "—"}</td><td className="text-right">{opportunity.price_variance_percent !== null ? percent(opportunity.price_variance_percent) : "—"}</td><td className="text-right font-semibold">{currency(Number(opportunity.estimated_savings) > 0 ? opportunity.estimated_savings : opportunity.review_spend, true)}</td><td className="text-right">{number(Number(opportunity.confidence_score) * 100)}%</td></tr>)}</tbody></table></div>
          <Pagination page={opportunities.data.page} pages={opportunities.data.pages} onPage={setPage} />
        </>)}
      </Panel>
      {selected ? <OpportunityDetail initialOpportunity={selected} close={() => setSelected(null)} /> : null}
    </>
  );
}
