import { BarChart3, Bot, Gauge, Menu, Target, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", icon: Gauge },
  { to: "/spend", label: "Spend Analysis", icon: BarChart3 },
  { to: "/optimization", label: "Cost Optimization", icon: Target },
  { to: "/advisor", label: "AI Advisor", icon: Bot },
];

export function Layout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const pageTitle = links.find((entry) => entry.to === location.pathname)?.label ?? "Procurement";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-72 border-r border-slate-800 bg-slate-950 text-white transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex h-20 items-center justify-between border-b border-slate-800 px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-400">ProcureSight</p>
            <p className="mt-1 text-sm text-slate-400">Decision intelligence</p>
          </div>
          <button className="rounded-lg p-2 text-slate-300 lg:hidden" onClick={() => setOpen(false)} aria-label="Close navigation">
            <X size={20} />
          </button>
        </div>
        <nav className="space-y-2 p-4" aria-label="Main navigation">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors ${
                  isActive ? "bg-cyan-500 text-slate-950" : "text-slate-300 hover:bg-slate-900 hover:text-white"
                }`
              }
            >
              <Icon size={19} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-0 w-full border-t border-slate-800 p-5 text-xs leading-5 text-slate-500">
          Verified analytics<br />Deterministic source of truth
        </div>
      </aside>

      {open && <button className="fixed inset-0 z-30 bg-slate-950/50 lg:hidden" onClick={() => setOpen(false)} aria-label="Close navigation overlay" />}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur md:px-8">
          <div className="flex items-center gap-3">
            <button className="rounded-lg border border-slate-200 p-2 lg:hidden" onClick={() => setOpen(true)} aria-label="Open navigation">
              <Menu size={20} />
            </button>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Procurement analytics</p>
              <h1 className="text-xl font-semibold text-slate-900">{pageTitle}</h1>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 sm:flex">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Live data
          </div>
        </header>
        <main className="mx-auto max-w-[1600px] p-5 md:p-8"><Outlet /></main>
      </div>
    </div>
  );
}

