import { Bot, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { useState } from "react";
import { api, queryString } from "../api/client";
import { EmptyState, ErrorState, LoadingState, PageIntro, Pagination } from "../components/UI";
import { currency, label, percent } from "../format";
import { useAsync } from "../hooks/useAsync";
import type { Opportunity, Paginated, Recommendation } from "../types";

function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <article className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="p-5 md:p-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div><div className="mb-3 flex flex-wrap gap-2"><span className="rounded-full bg-cyan-100 px-2.5 py-1 text-xs font-semibold text-cyan-800">{label(recommendation.opportunity_type)}</span><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">Confidence {percent(Number(recommendation.confidence_score) * 100)}</span></div><h3 className="text-lg font-semibold text-slate-950">{recommendation.title}</h3><p className="mt-1 text-xs text-slate-500">{recommendation.item_name}{recommendation.supplier_name ? ` · ${recommendation.supplier_name}` : ""}</p></div><div className="shrink-0 rounded-xl bg-emerald-50 px-4 py-3 text-right"><p className="text-xs font-semibold uppercase text-emerald-700">Estimated impact</p><p className="mt-1 font-semibold text-emerald-900">{currency(recommendation.estimated_impact, true)}</p></div></div>
        <p className="mt-5 text-sm leading-6 text-slate-600">{recommendation.summary}</p>
        <div className="mt-5 rounded-xl border-l-4 border-cyan-500 bg-cyan-50 p-4"><p className="text-xs font-bold uppercase tracking-wider text-cyan-800">Recommended action</p><p className="mt-2 text-sm leading-6 text-slate-700">{recommendation.recommended_action}</p></div>
        <button onClick={() => setExpanded((value) => !value)} className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-700" aria-expanded={expanded}>{expanded ? <ChevronUp size={17} /> : <ChevronDown size={17} />} {expanded ? "Hide" : "Show"} reasoning and next steps</button>
        {expanded && <div className="mt-4 grid gap-5 border-t border-slate-100 pt-5 md:grid-cols-2"><div><h4 className="text-sm font-semibold">Reasoning</h4><p className="mt-2 text-sm leading-6 text-slate-600">{recommendation.reasoning}</p>{recommendation.risks && <><h4 className="mt-4 text-sm font-semibold">Risks</h4><p className="mt-2 text-sm leading-6 text-slate-600">{recommendation.risks}</p></>}</div><div><h4 className="text-sm font-semibold">Next steps</h4>{recommendation.next_steps.length ? <ol className="mt-2 space-y-2 text-sm text-slate-600">{recommendation.next_steps.map((step, index) => <li key={step} className="flex gap-2"><span className="font-semibold text-cyan-700">{index + 1}.</span>{step}</li>)}</ol> : <p className="mt-2 text-sm text-slate-500">No additional steps were supplied.</p>}</div></div>}
      </div>
      <footer className="border-t border-slate-100 px-5 py-3 text-xs text-slate-400">Generated with {recommendation.model_name} · Prompt {recommendation.prompt_version} · Verified context remains the source of truth</footer>
    </article>
  );
}

export function AIAdvisor() {
  const [page, setPage] = useState(1);
  const [selectedOpportunity, setSelectedOpportunity] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState("");
  const recommendations = useAsync(() => api.get<Paginated<Recommendation>>(`/recommendations${queryString({ page, page_size: 10 })}`), [page]);
  const opportunities = useAsync(() => api.get<Paginated<Opportunity>>("/opportunities?page=1&page_size=100&sort_by=priority_score&sort_direction=desc"));

  const generate = async () => {
    if (!selectedOpportunity) return;
    setGenerating(true);
    setGenerateError("");
    try {
      await api.post<Recommendation>("/recommendations/generate", { opportunity_id: Number(selectedOpportunity), force: true });
      setPage(1);
      recommendations.reload();
    } catch (reason) {
      setGenerateError(reason instanceof Error ? reason.message : "Recommendation generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <>
      <PageIntro eyebrow="AI procurement advisor" title="Turn verified findings into practical actions" description="The advisor explains deterministic backend results. It cannot invent or change suppliers, prices, savings, or performance facts." />
      <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-950 p-5 text-white shadow-sm md:p-6">
        <div className="flex items-start gap-4"><span className="rounded-xl bg-cyan-500 p-3 text-slate-950"><Sparkles size={22} /></span><div className="flex-1"><h3 className="font-semibold">Generate an advisory note</h3><p className="mt-1 text-sm leading-6 text-slate-400">Choose a verified opportunity. If the external model is unavailable, the backend safely produces a deterministic fallback recommendation.</p><div className="mt-4 flex flex-col gap-3 sm:flex-row"><select aria-label="Opportunity for recommendation" value={selectedOpportunity} onChange={(event) => setSelectedOpportunity(event.target.value)} className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"><option value="">Select an opportunity…</option>{opportunities.data?.items.map((opportunity) => <option key={opportunity.opportunity_id} value={opportunity.opportunity_id}>{opportunity.priority_level} · {label(opportunity.opportunity_type)} · {opportunity.item_name}</option>)}</select><button disabled={!selectedOpportunity || generating} onClick={generate} className="rounded-lg bg-cyan-500 px-5 py-2.5 text-sm font-bold text-slate-950 disabled:opacity-50">{generating ? "Generating…" : "Generate recommendation"}</button></div>{generateError && <p role="alert" className="mt-3 text-sm text-rose-300">{generateError}</p>}</div></div>
      </section>

      {recommendations.loading && <LoadingState label="Loading procurement recommendations…" />}
      {recommendations.error && <ErrorState message={recommendations.error.message} retry={recommendations.reload} />}
      {recommendations.data && (recommendations.data.items.length === 0 ? <EmptyState message="No recommendations have been generated yet. Select an opportunity above to create the first advisory note." /> : <div className="space-y-5">{recommendations.data.items.map((recommendation) => <RecommendationCard key={recommendation.recommendation_id} recommendation={recommendation} />)}<Pagination page={recommendations.data.page} pages={recommendations.data.pages} onPage={setPage} /></div>)}
      <div className="mt-6 flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 text-xs leading-5 text-slate-500"><Bot size={20} className="shrink-0 text-cyan-700" /><span>Estimated savings are opportunities, not guaranteed savings. Procurement should validate commercial, quality, delivery, and contract considerations before acting.</span></div>
    </>
  );
}
