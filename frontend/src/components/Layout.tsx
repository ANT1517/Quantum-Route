import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { health } from "../api/client";
import { ENV_DEMO, setDemoMode, useDemoMode } from "../lib/demoMode";
import ErrorBoundary from "./ErrorBoundary";
import Toasts from "./Toasts";

const NAV: Array<[string, string]> = [
  ["/", "Home"],
  ["/scenario", "Scenario"],
  ["/run", "Run"],
  ["/results", "Results"],
  ["/fleet", "Fleet"],
  ["/path", "Path"],
  ["/bench", "Bench"],
  ["/quantum", "Quantum"],
];

function HealthDot() {
  const demo = useDemoMode();
  const q = useQuery({
    queryKey: ["health", demo],
    queryFn: ({ signal }) => health({ silent: true, signal }),
    refetchInterval: 30000,
    retry: false,
  });
  const color = demo ? "bg-fuchsia-400" : q.isSuccess ? "bg-emerald-400" : q.isError ? "bg-red-400" : "bg-slate-400";
  const label = demo ? "demo data" : q.isSuccess ? `API ${q.data.version ?? ""}` : q.isError ? "API offline" : "checking…";
  return (
    <span className="flex items-center gap-1 text-xs text-slate-300" title={label}>
      <span className={`h-2 w-2 rounded-full ${color}`} />
      <span className="hidden md:inline">{label}</span>
    </span>
  );
}

export default function Layout() {
  const demo = useDemoMode();
  const qc = useQueryClient();
  const loc = useLocation();

  const toggle = () => {
    setDemoMode(!demo);
    void qc.resetQueries();
  };

  return (
    <div className="flex min-h-full flex-col">
      <header className="bg-navy-900 text-white shadow">
        <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center gap-4 px-4 py-2">
          <NavLink to="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <svg width="24" height="24" viewBox="0 0 32 32" aria-hidden>
              <path d="M6 24 L13 10 L19 20 L26 8" stroke="#14b8a6" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            QuantumRoute
          </NavLink>
          <nav className="flex flex-1 flex-wrap gap-1">
            {NAV.map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `rounded px-2 py-1 text-sm ${isActive ? "bg-teal-600 text-white" : "text-slate-300 hover:bg-navy-700 hover:text-white"}`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <HealthDot />
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300" title={`Build default: ${ENV_DEMO ? "on" : "off"}`}>
            <span>Demo mode</span>
            <button
              role="switch"
              aria-checked={demo}
              onClick={toggle}
              className={`relative h-5 w-9 rounded-full transition ${demo ? "bg-fuchsia-500" : "bg-slate-600"}`}
            >
              <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition ${demo ? "left-4" : "left-0.5"}`} />
            </button>
          </label>
        </div>
        {demo && (
          <div className="bg-fuchsia-700 px-4 py-1 text-center text-xs">
            Demo mode: screens read results pre-exported from results/ into /demo (no backend, no network). Numbers match live mode; traffic is simulated.
          </div>
        )}
      </header>
      <main className="mx-auto w-full max-w-screen-2xl flex-1 p-4">
        <ErrorBoundary resetKey={loc.pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
      <footer className="px-4 py-2 text-center text-xs text-slate-500">
        QPSO is a classical, quantum-inspired metaheuristic running on ordinary CPUs. No quantum speedup is claimed. Traffic is simulated.
      </footer>
      <Toasts />
    </div>
  );
}
