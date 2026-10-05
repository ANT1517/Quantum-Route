// UI v3 shell: TopNav, Hero, ConsoleFrame (SubNav | main | Insights), LiveRow.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { PanelRightOpen, X, type LucideIcon } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { health } from "../../api/client";
import { setDemoMode, useDemoMode, ENV_DEMO } from "../../lib/demoMode";
import { engineLine, engineName, useEngine } from "../../lib/engine";
import { useLastRunAt } from "../../lib/eventLog";

const NAV: Array<[string, string]> = [
  ["/", "Home"],
  ["/scenario", "Scenario"],
  ["/run", "Run"],
  ["/results", "Results"],
  ["/fleet", "Fleet impact"],
  ["/path", "Shortest path"],
  ["/bench", "Benchmarks"],
  ["/quantum", "Quantum lab"],
];

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5 rounded-md" aria-label="QuantumRoute home">
      <span
        className="grid h-7 w-7 place-items-center rounded-[8px] font-semibold text-[14px]"
        style={{
          background: "linear-gradient(140deg, #1d2a2f 0%, #0b1013 60%)",
          border: "1px solid rgba(79,227,209,.35)",
          color: "var(--teal)",
          boxShadow: "0 0 14px rgba(79,227,209,.25), inset 0 1px 0 rgba(255,255,255,.08)",
        }}
      >
        Q
      </span>
      <span className="text-[15px] font-semibold tracking-tight text-txt">QuantumRoute</span>
    </Link>
  );
}

export function TopNav() {
  const demo = useDemoMode();
  const qc = useQueryClient();
  const loc = useLocation();
  const toggle = () => {
    setDemoMode(!demo);
    void qc.resetQueries();
  };
  return (
    <header className="sticky top-0 z-[1000] backdrop-blur-md" style={{ background: "rgba(3,3,4,.72)", borderBottom: "1px solid var(--line)" }}>
      <div className="mx-auto flex h-[62px] max-w-[1480px] items-center gap-3 px-4 lg:px-6">
        <Logo />
        <nav aria-label="Main" className="flex min-w-0 flex-1 justify-center overflow-x-auto">
          <ul className="flex items-stretch gap-0.5">
            {NAV.map(([to, label]) => (
              <li key={to} className="flex">
                <NavLink
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) =>
                    `relative flex h-[62px] items-center whitespace-nowrap px-1.5 text-[12.5px] transition min-[1180px]:px-2.5 min-[1180px]:text-[13px] ${isActive ? "qr-nav-active text-white" : "text-[#B9BEC5] hover:text-white"}`
                  }
                >
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="flex items-center gap-2">
          <button
            type="button"
            role="switch"
            aria-checked={demo}
            onClick={toggle}
            title={`Demo mode reads pre-exported results (no backend). Build default: ${ENV_DEMO ? "on" : "off"}`}
            className="btn-secondary btn-sm gap-2"
          >
            <span className="relative inline-block h-3.5 w-6 rounded-full transition" style={{ background: demo ? "rgba(255,181,71,.35)" : "var(--line-2)" }}>
              <span className="absolute top-0.5 h-2.5 w-2.5 rounded-full transition-all" style={{ left: demo ? 12 : 2, background: demo ? "var(--amber)" : "var(--mute)" }} />
            </span>
            Demo
          </button>
          {loc.pathname !== "/run" && (
            <Link to="/run" className="btn-primary btn-sm hidden min-[1180px]:inline-flex">
              Run optimizer →
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

export interface HeroProps {
  eyebrow: ReactNode;
  eyebrowTone?: "teal" | "amber";
  title: ReactNode;
  titleAccent: ReactNode;
  lead: ReactNode;
  actions?: ReactNode;
  meta?: ReactNode;
}

export function Hero({ eyebrow, eyebrowTone = "teal", title, titleAccent, lead, actions, meta }: HeroProps) {
  return (
    <section className="qr-hero qr-fade flex flex-wrap items-end gap-6 pb-7 pt-9">
      <div className="min-w-0 max-w-[820px] flex-1">
        <div
          className="mb-4 inline-flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.16em]"
          style={{ color: `var(--${eyebrowTone})`, textShadow: `0 0 12px var(--${eyebrowTone})88` }}
        >
          <span className={`dot-live ${eyebrowTone === "amber" ? "dot-amber" : ""}`} />
          {eyebrow}
        </div>
        <h1 className="qr-hero-title text-txt">
          <span className="block">{title}</span>
          <span className="grad-text block pb-1">{titleAccent}</span>
        </h1>
        <p className="mt-3 max-w-[640px] text-[15px] leading-relaxed text-mute">{lead}</p>
        {meta && <div className="mt-2 font-mono text-[11px] text-lbl">{meta}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 pb-1">{actions}</div>}
    </section>
  );
}

export interface SubNavItem<T extends string> {
  id: T;
  label: string;
  icon: LucideIcon;
  count?: number | null;
  countTone?: "amber";
}

export function SubNav<T extends string>({
  title,
  items,
  active,
  onChange,
}: {
  title: string;
  items: Array<SubNavItem<T>>;
  active: T;
  onChange: (id: T) => void;
}) {
  const engine = useEngine();
  return (
    <div className="flex h-full flex-col">
      <div className="micro px-3 pb-2 pt-1">{title}</div>
      <nav aria-label={`${title} sections`}>
        <ul className="flex gap-0.5 overflow-x-auto pb-1 min-[1000px]:flex-col min-[1000px]:overflow-visible">
          {items.map((it) => {
            const on = it.id === active;
            const Icon = it.icon;
            return (
              <li key={it.id}>
                <button
                  type="button"
                  aria-current={on ? "page" : undefined}
                  onClick={() => onChange(it.id)}
                  className={`relative flex h-9 w-full items-center gap-2.5 whitespace-nowrap rounded-md pl-3 pr-2 text-left text-[13px] transition ${on ? "qr-subnav-active text-white" : "text-mute hover:text-txt2"}`}
                  style={on ? { background: "rgba(255,255,255,.035)" } : undefined}
                >
                  <Icon size={16} strokeWidth={1.5} style={on ? { color: "var(--teal)", filter: "drop-shadow(0 0 4px rgba(79,227,209,.7))" } : undefined} />
                  <span className="flex-1">{it.label}</span>
                  {it.count != null && (
                    <span
                      className="num rounded-full px-1.5 text-[10px] leading-[16px]"
                      style={{
                        background: it.countTone === "amber" ? "rgba(255,181,71,.1)" : "#0b0e12",
                        color: it.countTone === "amber" ? "var(--amber)" : "var(--mute)",
                        border: `1px solid ${it.countTone === "amber" ? "rgba(255,181,71,.3)" : "var(--line)"}`,
                      }}
                    >
                      {it.count}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="mt-auto hidden px-3 pt-4 min-[1000px]:block" style={{ borderTop: "1px solid var(--line)" }}>
        <div className="micro flex items-center gap-2">
          <span className="dot-live" style={{ width: 5, height: 5 }} /> Engine
        </div>
        <div className="mt-1.5 text-[13px] font-semibold leading-snug text-txt">{engineName(engine)}</div>
        <div className="mt-1 font-mono text-[10.5px] text-mute">{engineLine(engine)}</div>
      </div>
    </div>
  );
}

function agoText(at: number | null, now: number): string {
  if (at == null) return "—";
  const s = (now - at) / 1000;
  if (s < 60) return `${s.toFixed(1)} S AGO`;
  if (s < 3600) return `${Math.floor(s / 60)} MIN AGO`;
  return `${Math.floor(s / 3600)} H AGO`;
}

export function LiveRow() {
  const demo = useDemoMode();
  const lastRun = useLastRunAt();
  const [now, setNow] = useState(Date.now());
  const q = useQuery({
    queryKey: ["health", demo],
    queryFn: ({ signal }) => health({ silent: true, signal }),
    refetchInterval: 30000,
    retry: false,
  });
  useEffect(() => {
    if (lastRun == null) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [lastRun]);

  let left: ReactNode;
  if (demo) {
    left = (
      <span className="flex items-center gap-2 text-amber" title="Screens read results pre-exported from results/ into /demo (no backend, no network). Traffic is simulated.">
        <span className="dot-live dot-amber" /> DEMO DATA · OFFLINE
      </span>
    );
  } else if (q.isError) {
    left = (
      <span className="flex items-center gap-2 text-danger">
        <span className="dot-live dot-red" /> API OFFLINE · SWITCH ON DEMO MODE
      </span>
    );
  } else {
    left = (
      <span className="flex items-center gap-2 text-teal" style={{ textShadow: "0 0 10px rgba(79,227,209,.5)" }}>
        <span className="dot-live" /> {q.isSuccess ? `SYSTEM LIVE · API ${q.data.version ?? ""}` : "CONNECTING…"}
      </span>
    );
  }
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 font-mono text-[10px] uppercase tracking-[0.16em]" style={{ borderBottom: "1px solid var(--line)" }}>
      {left}
      <span className="text-lbl">
        LAST RUN: <span className="text-txt2">{agoText(lastRun, now)}</span>
      </span>
    </div>
  );
}

export function ConsoleFrame({ subnav, insights, children }: { subnav?: ReactNode; insights?: ReactNode; children: ReactNode }) {
  const [drawer, setDrawer] = useState(false);
  const loc = useLocation();
  useEffect(() => setDrawer(false), [loc.pathname]);
  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawer(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer]);
  const cols = subnav
    ? insights
      ? "min-[1000px]:grid-cols-[190px_minmax(0,1fr)] min-[1200px]:grid-cols-[190px_minmax(0,1fr)_260px] min-[1400px]:grid-cols-[200px_minmax(0,1fr)_290px]"
      : "min-[1000px]:grid-cols-[190px_minmax(0,1fr)] min-[1400px]:grid-cols-[200px_minmax(0,1fr)]"
    : insights
      ? "min-[1200px]:grid-cols-[minmax(0,1fr)_260px] min-[1400px]:grid-cols-[minmax(0,1fr)_290px]"
      : "";
  return (
    <div className="qr-frame qr-fade mb-8">
      <LiveRow />
      <div className={`grid grid-cols-1 ${cols}`}>
        {subnav && (
          <aside className="p-2 min-[1000px]:py-4" style={{ borderRight: "1px solid var(--line)" }}>
            {subnav}
          </aside>
        )}
        <div className="min-w-0 p-4">
          {insights && (
            <div className="mb-3 flex justify-end min-[1200px]:hidden">
              <button type="button" className="btn-secondary btn-sm" onClick={() => setDrawer(true)} aria-expanded={drawer} aria-controls="qr-insights">
                <PanelRightOpen size={14} strokeWidth={1.5} /> Engine intelligence
              </button>
            </div>
          )}
          {children}
        </div>
        {insights && (
          <>
            <aside className="hidden p-4 min-[1200px]:block" style={{ borderLeft: "1px solid var(--line)" }} aria-label="Engine intelligence">
              {insights}
            </aside>
            {drawer && (
              <div className="fixed inset-0 z-[1800] min-[1200px]:hidden" role="dialog" aria-modal="true" aria-label="Engine intelligence">
                <div className="absolute inset-0 bg-black/60" onClick={() => setDrawer(false)} />
                <div id="qr-insights" className="absolute inset-y-0 right-0 w-[320px] max-w-[90vw] overflow-y-auto p-4" style={{ background: "var(--frame-1)", borderLeft: "1px solid var(--frame-border)" }}>
                  <div className="mb-2 flex justify-end">
                    <button type="button" className="btn-ghost btn-sm" onClick={() => setDrawer(false)} aria-label="Close engine intelligence" autoFocus>
                      <X size={14} strokeWidth={1.5} />
                    </button>
                  </div>
                  {insights}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export function PageShell({ hero, subnav, insights, children }: { hero: HeroProps; subnav?: ReactNode; insights?: ReactNode; children: ReactNode }) {
  return (
    <>
      <Hero {...hero} />
      <ConsoleFrame subnav={subnav} insights={insights}>
        {children}
      </ConsoleFrame>
    </>
  );
}
