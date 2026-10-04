import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, getJobResult, getQuboRouteDemo, quantumValidation, solveRouteQubo } from "../api/client";
import type { SolveRouteRequest, SolveRouteResponse } from "../api/types";
import QuboHeatmap from "../components/QuboHeatmap";
import { Empty, MockBadge, QueryState } from "../components/States";
import StatsTable from "../components/StatsTable";
import { useDemoMode } from "../lib/demoMode";
import { fmt } from "../lib/format";
import { useSession } from "../lib/session";

type Backend = SolveRouteRequest["backend"];
const MAX_STOPS = 7;

function labelsFor(stops: number[], n: number): string[] | undefined {
  const m = stops.length;
  if (m * m !== n) return undefined;
  const out: string[] = [];
  for (let i = 0; i < m; i++) for (let p = 0; p < m; p++) out.push(`${stops[i]}@${p + 1}`);
  return out;
}

function Solution({ stops, r, label }: { stops: number[]; r: SolveRouteResponse; label?: string }) {
  return (
    <div className="grid gap-4 md:grid-cols-[auto_1fr]">
      <QuboHeatmap matrix={r.qubo_matrix} labels={labelsFor(stops, r.qubo_matrix.length)} />
      <div className="space-y-1 text-sm">
        {label && <MockBadge text={label} />}
        <div>
          Stops: <span className="font-mono">{stops.join(", ")}</span>
        </div>
        <div>
          Decoded order: <span className="font-mono">depot → {r.order.join(" → ")} → depot</span>
        </div>
        <div>Energy: {fmt(r.energy, 3)}</div>
        <div>
          Feasible:{" "}
          <span className={r.feasible ? "text-teal-700" : "text-red-700"}>{r.feasible ? "yes" : "no (original order kept)"}</span>
        </div>
        {r.optimal_cost != null && <div>Optimal cost (brute force): {fmt(r.optimal_cost, 3)}</div>}
        {r.time_s != null && <div>Time: {fmt(r.time_s, 3)} s</div>}
        <div className="pt-2 text-xs text-slate-500">
          Variables x(stop, position); labels read “stop@position”. One-hot penalties sit on the diagonal/blocks; distances couple consecutive positions.
        </div>
      </div>
    </div>
  );
}

export default function QuantumLab() {
  const demo = useDemoMode();
  const session = useSession();
  const validation = useQuery({ queryKey: ["qubo-validation"], queryFn: ({ signal }) => quantumValidation({ signal }) });
  const demoRoute = useQuery({ queryKey: ["qubo-route-demo"], queryFn: ({ signal }) => getQuboRouteDemo({ signal, silent: true }) });
  const jobId = session.lastJobId ?? (demo ? "demo" : null);
  const lastResult = useQuery({
    queryKey: ["result", jobId],
    queryFn: ({ signal }) => getJobResult(jobId!, { signal, silent: true }),
    enabled: !!jobId,
  });

  const [vehicle, setVehicle] = useState<number | null>(null);
  const [backend, setBackend] = useState<Backend>("neal");
  const [solve, setSolve] = useState<{ busy: boolean; err: string | null; res: SolveRouteResponse | null; stops: number[] }>({ busy: false, err: null, res: null, stops: [] });

  const routes = lastResult.data?.routes ?? [];
  const route = routes.find((r) => r.vehicle === vehicle) ?? routes[0];
  const tooMany = !!route && route.stops.length > MAX_STOPS;

  const run = async () => {
    if (!route) return;
    setSolve({ busy: true, err: null, res: null, stops: route.stops });
    try {
      const res = await solveRouteQubo({ route_stops: route.stops, backend }, { silent: true });
      const stops = demo && "route_stops" in res ? (res as { route_stops: number[] }).route_stops : route.stops;
      setSolve({ busy: false, err: null, res, stops });
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 422 ? `422: ${e.message} (QUBO slot accepts at most ${MAX_STOPS} stops)` : String((e as Error).message);
      setSolve({ busy: false, err: msg, res: null, stops: [] });
    }
  };

  return (
    <div className="space-y-4">
      <div className="card">
        <h1 className="page-title">Quantum Lab</h1>
        <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-sm text-amber-900">
          Honesty note: the QUBO sub-route slot runs a <b>classical simulated annealer</b> today. We claim <b>readiness, not advantage</b> — measured by
          how often the sampler matches the brute-force optimum. The same call can later target a quantum annealer without redesign.
        </div>
      </div>

      <div className="card">
        <div className="label">QUBO validation (sampler vs brute force vs 2-opt)</div>
        <QueryState
          q={validation}
          isEmpty={(d) => !d?.table?.length}
          empty={<Empty title="No validation table yet">Run scripts/run_qubo_check.py.</Empty>}
        >
          {(d) => <StatsTable rows={d.table} />}
        </QueryState>
      </div>

      <div className="card space-y-2">
        <div className="label">Solve one route’s stop order as a QUBO</div>
        {!lastResult.data ? (
          <div className="text-sm text-slate-500">No result loaded — run the optimizer first (or use demo mode).</div>
        ) : (
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className="label">Route</label>
              <select className="input" value={route?.vehicle ?? ""} onChange={(e) => setVehicle(Number(e.target.value))}>
                {routes.map((r) => (
                  <option key={r.vehicle} value={r.vehicle}>
                    Vehicle {r.vehicle} ({r.stops.length} stops)
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Backend</label>
              <select className="input" value={backend} onChange={(e) => setBackend(e.target.value as Backend)}>
                <option value="neal">neal (simulated annealing)</option>
                <option value="brute">brute force (exact)</option>
                <option value="2opt">2-opt</option>
                <option value="qiskit">qiskit QAOA (m ≤ 4)</option>
              </select>
            </div>
            <button className="btn-primary" disabled={solve.busy || !route || tooMany} onClick={run}>
              {solve.busy ? "Solving…" : "Build QUBO & solve"}
            </button>
            {tooMany && <span className="text-sm text-red-700">Route has {route!.stops.length} stops; the QUBO slot accepts ≤ {MAX_STOPS}.</span>}
          </div>
        )}
        {demo && <div className="text-xs text-slate-500">Demo mode returns the pre-exported qubo_route_demo.json regardless of the route picked.</div>}
        {solve.err && <div className="rounded bg-red-50 p-2 text-sm text-red-800">{solve.err}</div>}
        {solve.res && <Solution stops={solve.stops} r={solve.res} label={demo ? String((solve.res as { label?: string }).label ?? "pre-exported demo route") : undefined} />}
      </div>

      <div className="card space-y-2">
        <div className="label">Example QUBO heatmap (qubo_route_demo.json)</div>
        <QueryState q={demoRoute} isEmpty={(d) => !d.qubo_matrix?.length} empty={<Empty title="No example QUBO exported" />}>
          {(d) => <Solution stops={d.route_stops} r={d} label={d.label ?? d.backend} />}
        </QueryState>
      </div>
    </div>
  );
}
