import type { ReactNode } from "react";

export function PageIntro({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) {
  return (
    <section className="mb-7 flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
      <div className="max-w-3xl">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-cyan-700">{eyebrow}</p>
        <h2 className="text-2xl font-semibold tracking-tight text-slate-950 md:text-3xl">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
      </div>
      {actions}
    </section>
  );
}

export function KpiCard({ label, value, detail, accent = "slate" }: { label: string; value: string; detail?: string; accent?: "slate" | "cyan" | "amber" | "emerald" }) {
  const colors = { slate: "bg-slate-900", cyan: "bg-cyan-500", amber: "bg-amber-400", emerald: "bg-emerald-500" };
  return (
    <article className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <span className={`absolute left-0 top-0 h-full w-1 ${colors[accent]}`} />
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
      {detail && <p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p>}
    </article>
  );
}

export function Panel({ title, subtitle, children, className = "" }: { title: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${className}`}>
      <header className="border-b border-slate-100 px-5 py-4">
        <h3 className="font-semibold text-slate-900">{title}</h3>
        {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

export function LoadingState({ label = "Loading verified analytics…" }: { label?: string }) {
  return <div className="flex min-h-52 items-center justify-center rounded-2xl border border-slate-200 bg-white text-sm text-slate-500"><span className="mr-3 h-4 w-4 animate-spin rounded-full border-2 border-cyan-600 border-t-transparent" />{label}</div>;
}

export function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">
      <p className="font-semibold">Unable to load this view</p><p className="mt-1">{message}</p>
      <button onClick={retry} className="mt-4 rounded-lg bg-rose-700 px-4 py-2 font-medium text-white">Try again</button>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="rounded-xl border border-dashed border-slate-300 px-5 py-12 text-center text-sm text-slate-500">{message}</div>;
}

export function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    CRITICAL: "bg-rose-100 text-rose-700",
    HIGH: "bg-amber-100 text-amber-800",
    MEDIUM: "bg-cyan-100 text-cyan-800",
    LOW: "bg-slate-100 text-slate-700",
  };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${colors[priority] ?? colors.LOW}`}>{priority}</span>;
}

export function Pagination({ page, pages, onPage }: { page: number; pages: number; onPage: (page: number) => void }) {
  if (pages <= 1) return null;
  return (
    <div className="mt-5 flex items-center justify-between text-sm text-slate-500">
      <span>Page {page} of {pages}</span>
      <div className="flex gap-2">
        <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="rounded-lg border border-slate-200 px-3 py-2 disabled:opacity-40">Previous</button>
        <button disabled={page >= pages} onClick={() => onPage(page + 1)} className="rounded-lg border border-slate-200 px-3 py-2 disabled:opacity-40">Next</button>
      </div>
    </div>
  );
}
