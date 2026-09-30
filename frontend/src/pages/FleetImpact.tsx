import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fleetCompare, getFleetDemo, getScenario } from "../api/client";
import type { FleetCompareResponse, FleetMode, FleetResult } from "../types/result";
import RouteMap from "../components/RouteMap";
import { Empty, ErrorState, Loading, MockBadge } from "../components/States";
import { vcColor } from "../lib/colors";
import { useDemoMode } from "../lib/demoMode";
import { fmt } from "../lib/format";
import { isPlainSource, useSession } from "../lib/session";

const MODE_LABEL: Record<FleetMode, string> = {
  naive: "NAIVE (everyone fastest)",
  user_eq: "USER EQUILIBRIUM",
  system_opt: "SYSTEM-OPTIMAL (marginal cost)",
};

const METRICS: Array<[keyof FleetResult | string, string, string, (r: FleetResult) => number]> = [
  ["externality_veh_h", "Externality", "veh-h", (r) => r.externality_veh_h],
  ["max_vc", "Max V/C", "", (r) => r.max_vc],
  ["edges_over_capacity", "Edges over capacity", "", (r) => r.edges_over_capacity],
  ["corridors_used", "Corridors used", "", (r) => r.corridors_used],
  ["co2_kg", "CO₂ (illustrative)", "kg", (r) => r.kpis.co2_kg],
  ["total_time_min", "Total time", "min", (r) => r.kpis.total_time_min],
  ["congestion_delay_min", "Congestion delay", "min", (r) => r.kpis.congestion_delay_min],
];

function pctChange(a: number, b: number): string {
  if (!Number.isFinite(a) || !Number.isFinite(b) || a === 0) return "–";
  const p = ((b - a) / Math.abs(a)) * 100;
  return `${p > 0 ? "+" : ""}${p.toFixed(1)}%`;
}

function ModePanel({ mode, r, plain, customers, depot }: { mode: FleetMode; r: FleetResult | undefined; plain: boolean; customers?: Parameters<typeof RouteMap>[0]["customers"]; depot?: [number, number] | null }) {
  return (
    <div className="card space-y-2">
      <div className="flex items-center justify-between">
        <div className="font-semibold">{MODE_LABEL[mode]}</div>
        {r && <MockBadge text={r.job_id} />}
      </div>
      {!r ? (
        <Empty title={`No ${mode} result`} />
      ) : (
        <>
          <RouteMap routes={[]} edgeFlows={r.edge_flows} showFlows customers={customers} depot={depot ?? r.routes[0]?.geometry[0] ?? null} plain={plain} height={380} />
          <div className="grid grid-cols-2 gap-2 text-sm">
            {METRICS.slice(0, 5).map(([k, label, unit, get]) => (
              <div key={String(k)} className="rounded border border-slate-200 px-2 py-1">
                <div className="text-xs text-slate-500">{label}</div>
                <div className="font-semibold">
                  {fmt(get(r), 2)} <span className="text-xs font-normal text-slate-500">{unit}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function FleetImpact() {
  const demo = useDemoMode();
  const session = useSession();
  const [S, setS] = useState(25);
  const scenarioId = session.scenarioId ?? (demo ? "demo" : null);

  const demoQ = useQuery({ queryKey: ["fleet-demo"], queryFn: ({ signal }) => getFleetDemo({ signal, silent: true }), enabled: demo });
  const scenario = useQuery({
    queryKey: ["scenario", scenarioId],
    queryFn: ({ signal }) => getScenario(scenarioId!, { signal, silent: true }),
    enabled: !!scenarioId,
  });
  const live = useMutation({
    mutationFn: () =>
      fleetCompare(
        { scenario_id: scenario.data?.scenario.id ?? scenarioId!, modes: ["naive", "user_eq", "system_opt"], S, weights: { wT: 0.5, wD: 0.2, wC: 0.2, wE: 0.1 }, seed: 7 },
        { silent: true },
      ),
  });

  useEffect(() => {
    if (demo && demoQ.data) setS(demoQ.data.S);
  }, [demo, demoQ.data]);

  const data: FleetCompareResponse | undefined = demo ? demoQ.data && { modes: demoQ.data.modes } : live.data;
  const plain = isPlainSource(scenario.data?.scenario.source ?? session.scenarioSource);
  const depot: [number, number] | null = scenario.data ? [scenario.data.depot.lat, scenario.data.depot.lon] : null;
  const modes = data?.modes ?? {};
  const present = (Object.keys(MODE_LABEL) as FleetMode[]).filter((m) => modes[m]);

  if (!demo && !scenarioId) {
    return (
      <Empty title="No scenario selected">
        <Link to="/scenario" className="text-teal-700 underline">
          Pick a scenario
        </Link>
      </Empty>
    );
  }

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-end gap-4">
        <div>
          <h1 className="page-title">Fleet Impact</h1>
          <div className="text-sm text-slate-600">Does our own fleet create the jam? Naive routing vs system-optimal (marginal-cost) routing.</div>
        </div>
        <div className="ml-auto w-72">
          <label className="label">
            S (vehicle-equivalents per route): <b className="text-slate-900">{S}</b>
          </label>
          <input type="range" min={1} max={100} step={1} value={S} disabled={demo} className="w-full accent-teal-600" onChange={(e) => setS(Number(e.target.value))} />
          {demo && <div className="text-xs text-slate-500">Demo mode shows the precomputed S only.</div>}
        </div>
        {!demo && (
          <button className="btn-primary" disabled={live.isPending || !scenario.data} onClick={() => live.mutate()}>
            {live.isPending ? "Comparing…" : "Compare modes"}
          </button>
        )}
      </div>
      <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">
        S = platform scale factor, a modelling assumption: each planned route is treated as S vehicles on the road so the fleet's own flow is visible in the
        simulated traffic. Traffic is simulated (load-ratio profiles + BPR), not measured.
      </div>

      {(demo ? demoQ.isLoading : live.isPending) && <Loading label="Computing fleet comparison…" />}
      {demo && demoQ.isError && <ErrorState error={demoQ.error} onRetry={() => demoQ.refetch()} />}
      {!demo && live.isError && <ErrorState error={live.error} onRetry={() => live.mutate()} />}
      {!data && !demo && !live.isPending && !live.isError && <Empty title="No comparison yet">Set S and press “Compare modes”.</Empty>}

      {data && present.length === 0 && <Empty title="Response contained no modes" />}
      {data && present.length > 0 && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <ModePanel mode="naive" r={modes.naive} plain={plain} customers={scenario.data?.customers} depot={depot} />
            <ModePanel mode="system_opt" r={modes.system_opt} plain={plain} customers={scenario.data?.customers} depot={depot} />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-600">
            Edge colour by V/C:
            {[0.5, 0.8, 1.0, 1.2, 1.4].map((v) => (
              <span key={v} className="flex items-center gap-1">
                <span className="inline-block h-2 w-6 rounded" style={{ background: vcColor(v) }} />
                {v}
              </span>
            ))}
            · width = fleet flow
          </div>
          <div className="card overflow-x-auto">
            <div className="label">All modes</div>
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-500">
                  <th className="py-2 pr-4">Metric</th>
                  {present.map((m) => (
                    <th key={m} className="py-2 pr-4">
                      {m}
                    </th>
                  ))}
                  {modes.naive && modes.system_opt && <th className="py-2 pr-4">system_opt vs naive</th>}
                </tr>
              </thead>
              <tbody>
                {METRICS.map(([k, label, unit, get]) => (
                  <tr key={String(k)} className="border-b border-slate-100">
                    <td className="py-1.5 pr-4">
                      {label} {unit && <span className="text-xs text-slate-400">({unit})</span>}
                    </td>
                    {present.map((m) => (
                      <td key={m} className="py-1.5 pr-4 tabular-nums">
                        {fmt(get(modes[m]!), 2)}
                      </td>
                    ))}
                    {modes.naive && modes.system_opt && <td className="py-1.5 pr-4 tabular-nums">{pctChange(get(modes.naive), get(modes.system_opt))}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
