import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getHomeKpis } from "../api/client";
import { Empty, MockBadge, QueryState } from "../components/States";
import { setDemoMode, useDemoMode } from "../lib/demoMode";
import { fmt } from "../lib/format";

export default function Home() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const demo = useDemoMode();
  const kpis = useQuery({ queryKey: ["home-kpis"], queryFn: ({ signal }) => getHomeKpis({ signal, silent: true }) });

  const runDemo = () => {
    if (!demo) {
      setDemoMode(true);
      void qc.resetQueries();
    }
    nav("/run?autostart=1");
  };

  return (
    <div className="space-y-8">
      <section className="rounded-xl bg-navy-900 px-8 py-12 text-white">
        <h1 className="text-3xl font-bold tracking-tight">QuantumRoute</h1>
        <p className="mt-4 max-w-4xl text-lg text-slate-200">
          QuantumRoute plans delivery-fleet routes on Hyderabad's real road network with a quantum-inspired swarm optimizer (QPSO), routes
          the fleet so it does not create its own traffic jams, minimizes time, distance, congestion and CO₂, re-plans when traffic changes,
          has a quantum-ready solver slot built into the pipeline — and proves every claim in a fair, reproducible Benchmark Studio.
        </p>
        <div className="mt-8 flex flex-wrap gap-4">
          <button className="btn-primary px-6 py-3 text-base" onClick={runDemo}>
            Run demo
          </button>
          <button className="btn bg-white/10 px-6 py-3 text-base text-white hover:bg-white/20" onClick={() => nav("/scenario")}>
            Open scenario
          </button>
        </div>
        <p className="mt-4 text-xs text-slate-400">
          QPSO is a classical metaheuristic inspired by quantum-mechanical mathematics; it runs on ordinary CPUs. Traffic is simulated.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Headline numbers (from exported results)</h2>
        <QueryState
          q={kpis}
          isEmpty={(d) => !Array.isArray(d) || d.length === 0}
          empty={<Empty title="No exported KPIs yet">Run scripts/export_demo.py to produce home_kpis.json.</Empty>}
        >
          {(items) => (
            <div className="grid gap-4 md:grid-cols-3">
              {items.slice(0, 3).map((k, i) => (
                <div key={i} className="card">
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-sm text-slate-500">{k.label}</div>
                    <MockBadge text={`${k.label} ${k.source}`} />
                  </div>
                  <div className="mt-2 text-3xl font-bold text-teal-700">
                    {typeof k.value === "number" ? fmt(k.value, 1) : k.value} <span className="text-base font-normal text-slate-500">{k.unit}</span>
                  </div>
                  <div className="mt-2 text-xs text-slate-400">Source: {k.source}</div>
                </div>
              ))}
            </div>
          )}
        </QueryState>
      </section>
    </div>
  );
}
