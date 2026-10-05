import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Compass, LayoutDashboard } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { demoFile, getHomeKpis, getResultDemo, health } from "../api/client";
import type { ScenarioDetail } from "../api/types";
import CongestionChart, { CongestionLegend } from "../components/charts/CongestionChart";
import RouteMap from "../components/RouteMap";
import { Empty, MockBadge, QueryState } from "../components/States";
import { Hi, InsightBlock, InsightsColumn } from "../components/ui/Insights";
import { Chip, KpiCard, Panel, TrafficChip } from "../components/ui/primitives";
import { PageShell, SubNav } from "../components/ui/Shell";
import { setDemoMode, useDemoMode } from "../lib/demoMode";
import { fmt, minToHHMM } from "../lib/format";

const STEPS: Array<[string, string, string]> = [
  ["/scenario", "Scenario", "Pick Hyderabad-60 and a departure time"],
  ["/run", "Run", "Watch the swarm converge live"],
  ["/results", "Results", "Routes, congestion and KPIs; add an incident"],
  ["/fleet", "Fleet impact", "Naive vs system-optimal routing"],
  ["/path", "Shortest path", "Ambulance ETA with an incident"],
  ["/bench", "Benchmarks", "Fair, statistically tested comparisons"],
  ["/quantum", "Quantum lab", "QUBO slot on a classical sampler"],
];

type Section = "overview" | "walkthrough";

export default function Home() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const demo = useDemoMode();
  const [section, setSection] = useState<Section>("overview");
  const kpis = useQuery({ queryKey: ["home-kpis"], queryFn: ({ signal }) => getHomeKpis({ signal, silent: true }) });
  const demoResult = useQuery({ queryKey: ["home-result-demo"], queryFn: ({ signal }) => getResultDemo({ signal, silent: true }) });
  const demoScenario = useQuery({ queryKey: ["home-scenario-demo"], queryFn: ({ signal }) => demoFile<ScenarioDetail>("scenario_demo.json", { signal, silent: true }) });
  const api = useQuery({ queryKey: ["health", demo], queryFn: ({ signal }) => health({ silent: true, signal }), retry: false });

  const runDemo = () => {
    if (!demo) {
      setDemoMode(true);
      void qc.resetQueries();
    }
    nav("/run?autostart=1");
  };

  const r = demoResult.data;
  const depart = r ? Math.min(...r.routes.map((x) => x.depart_min).filter((x) => Number.isFinite(x))) : null;
  const eyebrow = demo ? "DEMO DATA · OFFLINE" : api.isSuccess ? "SYSTEM ONLINE" : api.isError ? "API OFFLINE · DEMO MODE AVAILABLE" : "CONNECTING";

  return (
    <PageShell
      hero={{
        eyebrow,
        eyebrowTone: demo || api.isError ? "amber" : "teal",
        title: "The command center for",
        titleAccent: "city fleet routing.",
        lead: "QuantumRoute plans delivery-fleet routes on Hyderabad's road network with QPSO-noQUBO (tuned), a quantum-inspired swarm optimizer that runs on ordinary CPUs, and shows how it compares with PSO, GA, SA and OR-Tools (industry reference) — including where it does not win.",
        meta: "engine · QPSO-noQUBO (tuned) → classical, quantum-inspired; no quantum speedup claimed",
        actions: (
          <>
            <Link to="/bench" className="btn-secondary">
              View benchmarks
            </Link>
            <button type="button" className="btn-primary" onClick={runDemo}>
              Start demo →
            </button>
          </>
        ),
      }}
      subnav={
        <SubNav
          title="Home"
          active={section}
          onChange={setSection}
          items={[
            { id: "overview", label: "Overview", icon: LayoutDashboard },
            { id: "walkthrough", label: "Walkthrough", icon: Compass, count: STEPS.length },
          ]}
        />
      }
      insights={
        <InsightsColumn title="What it does">
          <InsightBlock label="Engine" tone="teal">
            <Hi>QPSO-noQUBO (tuned)</Hi> with optimal Split decoding and memetic local search, on time-dependent (BPR) traffic. It weighs time, distance,
            congestion delay and CO₂ (illustrative).
          </InsightBlock>
          <InsightBlock label="Beyond one route">
            System-optimal fleet planning, incident re-routing with warm start, ambulance shortest path and an optional <Hi tone="amber">QUBO slot</Hi> on a classical
            sampler.
          </InsightBlock>
          <InsightBlock label="Honesty" tone="amber">
            QPSO is a classical metaheuristic inspired by quantum-mechanical mathematics; it runs on ordinary CPUs. Traffic and incidents are simulated.
          </InsightBlock>
        </InsightsColumn>
      }
    >
      <div key={section} className="qr-fade">
        {section === "overview" ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="micro">Demo scenario numbers</span>
              <Chip tone="amber">simulated, not benchmarks</Chip>
              <span className="font-mono text-[10.5px] text-lbl">Hyderabad-60 · simulated traffic</span>
            </div>
            <QueryState
              q={kpis}
              isEmpty={(d) => !Array.isArray(d) || d.length === 0}
              empty={<Empty title="No exported KPIs yet">Run scripts/export_demo.py to produce home_kpis.json.</Empty>}
            >
              {(items) => (
                <div className="grid gap-3 md:grid-cols-3">
                  {items.slice(0, 3).map((k, i) => (
                    <KpiCard
                      key={i}
                      label={
                        <span className="flex items-center gap-2">
                          {k.label} <MockBadge text={`${k.label} ${k.source}`} />
                        </span>
                      }
                      value={typeof k.value === "number" ? fmt(k.value, 1) : k.value}
                      unit={k.unit}
                      tone={i === 0 ? "teal" : undefined}
                      context={<span className="font-mono text-[10px]">{k.source}</span>}
                    />
                  ))}
                </div>
              )}
            </QueryState>
            <div className="grid gap-3 min-[1300px]:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
              <Panel overlay title="Demo plan" chips={
                  r ? (
                    <>
                      <Chip tone="teal">{r.routes.length} routes</Chip>
                      <TrafficChip at={depart} />
                    </>
                  ) : undefined
                } meta={r ? `${r.meta.instance} · ${minToHHMM(depart)}` : undefined}>
                {r ? (
                  <RouteMap
                    routes={r.routes}
                    customers={demoScenario.data?.customers}
                    depot={demoScenario.data ? [demoScenario.data.depot.lat, demoScenario.data.depot.lon] : null}
                    height={300}
                  />
                ) : (
                  <div className="h-[300px]" />
                )}
              </Panel>
              <Panel title="Network congestion · 24 h" chips={<Chip>ρ = V/C</Chip>} meta={<CongestionLegend />} bodyClassName="px-2 pb-2">
                <CongestionChart departMin={depart} height={240} />
                <div className="px-2 font-mono text-[10px] text-lbl">Simulated time-of-day profile; marker = demo departure.</div>
              </Panel>
            </div>
          </div>
        ) : (
          <ol className="grid gap-2 sm:grid-cols-2">
            {STEPS.map(([to, label, text], i) => (
              <li key={to}>
                <Link to={to} className="group flex items-center gap-3 rounded-xl px-4 py-3 transition" style={{ background: "rgba(255,255,255,.015)", border: "1px solid var(--line)" }}>
                  <span className="num text-[11px] text-lbl">{String(i + 1).padStart(2, "0")}</span>
                  <span className="flex-1">
                    <span className="block text-[13.5px] font-semibold text-txt">{label}</span>
                    <span className="block text-[12px] text-mute">{text}</span>
                  </span>
                  <ArrowRight size={15} strokeWidth={1.5} className="text-lbl transition group-hover:text-teal" />
                </Link>
              </li>
            ))}
          </ol>
        )}
      </div>
    </PageShell>
  );
}
