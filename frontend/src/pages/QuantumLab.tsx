import { useQuery } from "@tanstack/react-query";
import { Atom, Grid3x3, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, getJobResult, getQuboRouteDemo, quantumValidation, solveRouteQubo } from "../api/client";
import type { SolveRouteRequest, SolveRouteResponse } from "../api/types";
import QuboHeatmap from "../components/QuboHeatmap";
import { Empty, MockBadge, QueryState } from "../components/States";
import StatsTable from "../components/StatsTable";
import { DecisionLog, Hi, InsightBlock, InsightsColumn, SignalRow } from "../components/ui/Insights";
import { Chip, Panel, Segmented, Select } from "../components/ui/primitives";
import { PageShell, SubNav } from "../components/ui/Shell";
import { useDemoMode } from "../lib/demoMode";
import { logEvent } from "../lib/eventLog";
import { fmt } from "../lib/format";
import { useSession } from "../lib/session";

type Backend = SolveRouteRequest["backend"];
const MAX_STOPS = 7;
type Section = "solve" | "example" | "validation";

function labelsFor(stops: number[], n: number): string[] | undefined {
  const m = stops.length;
  if (m * m !== n) return undefined;
  const out: string[] = [];
  for (let i = 0; i < m; i++) for (let p = 0; p < m; p++) out.push(`${stops[i]}@${p + 1}`);
  return out;
}

function Solution({ stops, r, label }: { stops: number[]; r: SolveRouteResponse; label?: string }) {
  const cost = (r as SolveRouteResponse & { cost?: number }).cost;
  const atOpt = cost != null && r.optimal_cost != null && Math.abs(cost - r.optimal_cost) < 1e-6;
  return (
    <div className="grid gap-5 min-[1300px]:grid-cols-[minmax(0,440px)_minmax(0,1fr)]">
      <QuboHeatmap matrix={r.qubo_matrix} labels={labelsFor(stops, r.qubo_matrix.length)} />
      <div className="space-y-3 text-[12.5px]">
        {label && (
          <div className="flex flex-wrap items-center gap-2">
            <Chip>{label}</Chip>
            <MockBadge text={label} />
          </div>
        )}
        <div>
          <div className="micro mb-1.5">Stops (input order)</div>
          <div className="flex flex-wrap gap-1">
            {stops.map((s) => (
              <Chip key={s}>{s}</Chip>
            ))}
          </div>
        </div>
        <div>
          <div className="micro mb-1.5">Decoded order</div>
          <div className="flex flex-wrap items-center gap-1">
            <Chip>depot</Chip>
            {r.order.map((s, i) => (
              <span key={`${s}-${i}`} className="flex items-center gap-1">
                <span className="text-lbl">→</span>
                <Chip tone="teal">{s}</Chip>
              </span>
            ))}
            <span className="text-lbl">→</span>
            <Chip>depot</Chip>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Chip tone={r.feasible ? "lime" : "red"}>{r.feasible ? "feasible" : "infeasible · original order kept"}</Chip>
          {cost != null && <Chip tone={atOpt ? "lime" : "amber"}>cost {fmt(cost, 3)}</Chip>}
          {r.optimal_cost != null && <Chip>optimum (brute force) {fmt(r.optimal_cost, 3)}</Chip>}
          {cost != null && r.optimal_cost != null && <Chip tone={atOpt ? "lime" : "amber"}>{atOpt ? "matches optimum" : `+${fmt(((cost - r.optimal_cost) / r.optimal_cost) * 100, 2)}% vs optimum`}</Chip>}
        </div>
        <div className="num space-y-0.5 text-[11.5px] text-txt2">
          <div>energy {fmt(r.energy, 3)}</div>
          {r.time_s != null && <div>time {fmt(r.time_s, 3)} s</div>}
        </div>
        <div className="text-[11.5px] leading-relaxed text-mute">
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

  const [section, setSection] = useState<Section>("solve");
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
      logEvent("done", `QUBO ${backend} · ${stops.length} stops · ${res.feasible ? "feasible" : "infeasible"}${res.time_s != null ? ` · ${fmt(res.time_s, 3)} s` : ""}`);
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 422 ? `422: ${e.message} (QUBO slot accepts at most ${MAX_STOPS} stops)` : String((e as Error).message);
      setSolve({ busy: false, err: msg, res: null, stops: [] });
    }
  };

  const vtAll = validation.data?.table ?? [];
  // Signal ranges use the CVRPLIB rows (20 routes each) when present; single-route rows would widen them.
  const vtCvrp = vtAll.filter((r) => /cvrplib/i.test(String(r.source ?? "")));
  const vt = vtCvrp.length ? vtCvrp : vtAll;
  const nums = (k: string) => vt.map((r) => r[k]).filter((v): v is number => typeof v === "number");
  const range = (a: number[], d = 0) => (a.length ? (Math.min(...a) === Math.max(...a) ? fmt(a[0], d) : `${fmt(Math.min(...a), d)}–${fmt(Math.max(...a), d)}`) : "–");

  let main;
  if (section === "solve") {
    main = (
      <Panel title="Solve one route's stop order as a QUBO" meta={`at most ${MAX_STOPS} stops (m² variables)`} bodyClassName="px-4 pb-4 space-y-4">
        {!lastResult.data ? (
          <div className="text-[13px] text-mute">No result loaded — run the optimizer first (or use demo mode).</div>
        ) : (
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="label" htmlFor="ql-route">
                Route
              </label>
              <Select id="ql-route" className="w-auto" value={route?.vehicle ?? ""} onChange={(e) => setVehicle(Number(e.target.value))}>
                {routes.map((r) => (
                  <option key={r.vehicle} value={r.vehicle}>
                    Vehicle {r.vehicle} ({r.stops.length} stops)
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <div className="label">Backend</div>
              <Segmented
                ariaLabel="QUBO backend"
                size="sm"
                value={backend}
                onChange={setBackend}
                options={[
                  ["neal", "neal (simulated annealing)"],
                  ["brute", "brute force (exact)"],
                  ["2opt", "2-opt"],
                  ["qiskit", "qiskit QAOA (m ≤ 4)"],
                ]}
              />
            </div>
            <button type="button" className="btn-primary" disabled={solve.busy || !route || tooMany} onClick={run}>
              {solve.busy ? "Solving…" : "Build QUBO & solve →"}
            </button>
            {tooMany && (
              <span className="text-[12.5px] text-danger">
                Route has {route!.stops.length} stops; the QUBO slot accepts ≤ {MAX_STOPS}.
              </span>
            )}
          </div>
        )}
        {demo && <div className="text-[11.5px] text-mute">Demo mode returns the pre-exported qubo_route_demo.json regardless of the route picked.</div>}
        {solve.err && <div className="rounded-lg px-3 py-2 text-[12.5px] text-danger" style={{ background: "rgba(255,122,122,.05)", border: "1px solid rgba(255,122,122,.3)" }}>{solve.err}</div>}
        {solve.res && <Solution stops={solve.stops} r={solve.res} label={demo ? String((solve.res as { label?: string }).label ?? "pre-exported demo route") : undefined} />}
        {!solve.res && !solve.err && lastResult.data && <Empty title="No QUBO solved yet">Pick a route with at most {MAX_STOPS} stops and a backend.</Empty>}
      </Panel>
    );
  } else if (section === "example") {
    main = (
      <Panel title="Example QUBO heatmap" meta="qubo_route_demo.json" bodyClassName="px-4 pb-4">
        <QueryState q={demoRoute} isEmpty={(d) => !d.qubo_matrix?.length} empty={<Empty title="No example QUBO exported" />}>
          {(d) => <Solution stops={d.route_stops} r={d} label={d.label ?? d.backend} />}
        </QueryState>
      </Panel>
    );
  } else {
    main = (
      <Panel title="QUBO validation (sampler vs brute force vs 2-opt)" meta={<Link to="/bench" className="text-teal underline">Benchmarks →</Link>} bodyClassName="px-4 pb-3">
        <QueryState q={validation} isEmpty={(d) => !d?.table?.length} empty={<Empty title="No validation table yet">Run scripts/run_qubo_check.py.</Empty>}>
          {(d) => <StatsTable rows={d.table} />}
        </QueryState>
      </Panel>
    );
  }

  return (
    <PageShell
      hero={{
        eyebrow: `QUBO SLOT · CLASSICAL SAMPLER · ≤ ${MAX_STOPS} STOPS${vtAll.length ? ` · ${vtAll.length} VALIDATION ROWS` : ""}`,
        title: "Quantum-ready today,",
        titleAccent: "classical sampler inside.",
        lead: "Each route's stop order can be written as a QUBO and handed to a sampler. Today that sampler is a classical simulated annealer; the same call can later target a quantum annealer.",
        meta: "slot · off by default in the shipped engine QPSO-noQUBO (tuned)",
        actions: (
          <>
            <Link to="/run" className="btn-secondary">
              Try the QUBO checkbox →
            </Link>
            <button type="button" className="btn-primary" disabled={solve.busy || !route || tooMany} onClick={() => (setSection("solve"), void run())}>
              {solve.busy ? "Solving…" : "Solve a route →"}
            </button>
          </>
        ),
      }}
      subnav={
        <SubNav
          title="Quantum lab"
          active={section}
          onChange={setSection}
          items={[
            { id: "solve", label: "Solve a route", icon: Atom, count: routes.length || null },
            { id: "example", label: "Example QUBO", icon: Grid3x3 },
            { id: "validation", label: "Validation", icon: ShieldCheck, count: vtAll.length || null },
          ]}
        />
      }
      insights={
        <InsightsColumn>
          <InsightBlock label="Honesty note" tone="amber">
            The QUBO sub-route slot runs a <Hi tone="amber">classical simulated annealer</Hi> today. We claim <Hi>readiness, not advantage</Hi> — measured by how often
            the sampler matches the brute-force optimum. On classical hardware it is slower than 2-opt.
          </InsightBlock>
          {vt.length > 0 && (
            <InsightBlock label={`Signal summary (${vtCvrp.length ? "CVRPLIB routes (≤7 stops)" : "validation table"})`}>
              <SignalRow k="neal feasible" v={`${range(nums("neal_feasible_pct"))}%`} tone="lime" />
              <SignalRow k="neal optimal" v={`${range(nums("neal_optimal_pct"))}%`} />
              <SignalRow k="neal ms / route" v={range(nums("time_per_route_neal_ms"))} tone="amber" />
              <SignalRow k="2-opt ms / route" v={range(nums("time_per_route_2opt_ms"), 3)} />
            </InsightBlock>
          )}
          <DecisionLog />
        </InsightsColumn>
      }
    >
      <div key={section} className="qr-fade">
        {main}
      </div>
    </PageShell>
  );
}
