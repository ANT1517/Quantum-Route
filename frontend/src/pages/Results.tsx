import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ApiError,
  addIncident,
  createJob,
  getIncidentDemo,
  getJobResult,
  getScenario,
  getShortestPathDemo,
  shortestPath,
} from "../api/client";
import type { Algorithm, IncidentDemo, ZoneIncident } from "../api/types";
import type { ResultJSON, ShortestPathResponse } from "../types/result";
import ExplanationPanel from "../components/ExplanationPanel";
import IncidentDrawer, { defaultDraft, type IncidentDraft } from "../components/IncidentDrawer";
import KpiCards from "../components/KpiCards";
import RouteMap, { type LatLon, type MapLine, type MapPoint } from "../components/RouteMap";
import RouteTable from "../components/RouteTable";
import { Empty, ErrorState, Loading, MockBadge } from "../components/States";
import { useJobProgress } from "../hooks/useJobProgress";
import { algoColor } from "../lib/colors";
import { useDemoMode } from "../lib/demoMode";
import { downloadJson, fmt, minToHHMM } from "../lib/format";
import { isPlainSource, useSession } from "../lib/session";
import { notify } from "../lib/toast";

interface Compare {
  before: ResultJSON;
  after: ResultJSON;
  incident: ZoneIncident;
  report?: IncidentDemo["report"];
  source: "demo" | "live";
}

function departOf(r: ResultJSON): number {
  const d = r.routes.map((x) => x.depart_min).filter((x) => Number.isFinite(x));
  return d.length ? Math.min(...d) : r.meta.tau0;
}

function Delta({ a, b, unit }: { a: number; b: number; unit: string }) {
  const d = b - a;
  const cls = d < 0 ? "text-teal-700" : d > 0 ? "text-red-700" : "text-slate-500";
  return (
    <span className={cls}>
      {d > 0 ? "+" : ""}
      {fmt(d, 1)} {unit}
    </span>
  );
}

export default function Results() {
  const demo = useDemoMode();
  const session = useSession();
  const [params] = useSearchParams();
  const jobId = params.get("job") ?? session.lastJobId ?? (demo ? "demo" : null);

  const result = useQuery({
    queryKey: ["result", jobId],
    queryFn: ({ signal }) => getJobResult(jobId!, { signal, silent: true }),
    enabled: !!jobId,
  });
  const scenarioId = result.data?.scenario_id ?? null;
  const scenario = useQuery({
    queryKey: ["scenario", scenarioId],
    queryFn: ({ signal }) => getScenario(scenarioId!, { signal, silent: true }),
    enabled: !!scenarioId,
  });

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [draft, setDraft] = useState<IncidentDraft>(defaultDraft());
  const [compare, setCompare] = useState<Compare | null>(null);
  const [view, setView] = useState<"before" | "after">("after");
  const [reoptJob, setReoptJob] = useState<string | null>(null);
  const [pendingIncident, setPendingIncident] = useState<ZoneIncident | null>(null);
  const [busy, setBusy] = useState(false);
  const [showFlows, setShowFlows] = useState(true);
  const reopt = useJobProgress(reoptJob);

  // SP panel
  const [spFrom, setSpFrom] = useState<string>("depot");
  const [spTo, setSpTo] = useState<string>("");
  const [sp, setSp] = useState<{ res: ShortestPathResponse | null; err: string | null; busy: boolean; src?: LatLon; dst?: LatLon }>({
    res: null,
    err: null,
    busy: false,
  });

  useEffect(() => {
    if (result.data) setDraft(defaultDraft(departOf(result.data)));
    setCompare(null);
  }, [result.data]);

  // live re-optimisation finished -> fetch after-result
  useEffect(() => {
    if (!reoptJob || !reopt.done || !result.data || !pendingIncident) return;
    if (reopt.status === "COMPLETED" || reopt.status === "COMPLETED_PARTIAL") {
      getJobResult(reoptJob)
        .then((after) => {
          setCompare({ before: result.data!, after, incident: pendingIncident, source: "live" });
          setView("after");
        })
        .catch(() => undefined)
        .finally(() => setBusy(false));
    } else {
      notify(`Re-optimization ${reopt.status}${reopt.error ? `: ${reopt.error}` : ""}`);
      setBusy(false);
    }
    setReoptJob(null);
  }, [reopt.done, reopt.status, reopt.error, reoptJob, result.data, pendingIncident]);

  const submitIncident = async (inc: ZoneIncident) => {
    if (!result.data) return;
    setBusy(true);
    try {
      if (demo) {
        const d = await getIncidentDemo();
        setCompare({ before: d.before, after: d.after, incident: d.incident, report: d.report, source: "demo" });
        setView("after");
        setDrawerOpen(false);
        setBusy(false);
        return;
      }
      const r = result.data;
      await addIncident(r.scenario_id, inc);
      const job = await createJob({
        scenario_id: r.scenario_id,
        algorithm: r.algorithm as Algorithm,
        weights: { wT: r.weights.wT, wD: r.weights.wD, wC: r.weights.wC, wE: r.weights.wE },
        params: {},
        seed: r.seed,
        budget: { evals: r.kpis.evals || null, time_s: null },
        fleet_mode: "naive",
        warm_start_job_id: r.job_id,
      });
      setPendingIncident(inc);
      setReoptJob(job.job_id);
      setDrawerOpen(false);
    } catch {
      setBusy(false); // toast already shown by client
    }
  };

  const shown: ResultJSON | undefined = compare ? (view === "after" ? compare.after : compare.before) : result.data;
  const incidentCircle = compare ? { center: compare.incident.center, radius_m: compare.incident.radius_m } : drawerOpen && draft.center ? { center: draft.center, radius_m: draft.radius_m } : null;

  const nodes = useMemo(() => {
    const out: Array<{ key: string; label: string; ll: LatLon }> = [];
    const s = scenario.data;
    if (s) {
      out.push({ key: "depot", label: "Depot", ll: [s.depot.lat, s.depot.lon] });
      s.customers.forEach((c) => out.push({ key: `c${c.id}`, label: `Customer ${c.id}`, ll: [c.lat, c.lon] }));
    }
    return out;
  }, [scenario.data]);

  const runSp = async () => {
    if (!result.data) return;
    setSp((s) => ({ ...s, busy: true, err: null }));
    try {
      let src: LatLon | undefined;
      let dst: LatLon | undefined;
      if (demo) {
        const d = await getShortestPathDemo();
        src = d.source;
        dst = d.target;
      } else {
        src = nodes.find((n) => n.key === spFrom)?.ll;
        dst = nodes.find((n) => n.key === spTo)?.ll;
      }
      if (!src || !dst) throw new Error("Pick a source and a target");
      const res = await shortestPath(
        { scenario_id: result.data.scenario_id, source: src, target: dst, depart_min: departOf(result.data), algorithm: "dijkstra" },
        { silent: true, demoIncident: !!compare },
      );
      setSp({ res, err: null, busy: false, src, dst });
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 404 ? "No path between these points." : String((e as Error).message);
      setSp({ res: null, err: msg, busy: false });
    }
  };

  if (!jobId) {
    return (
      <Empty title="No result yet">
        <Link to="/run" className="text-teal-700 underline">
          Run the optimizer
        </Link>{" "}
        or switch on demo mode.
      </Empty>
    );
  }
  if (result.isLoading) return <Loading label="Loading result…" />;
  if (result.isError) {
    const e = result.error;
    const msg = e instanceof ApiError && e.status === 409 ? "Job has not finished yet." : undefined;
    return <ErrorState error={msg ?? e} onRetry={() => result.refetch()} />;
  }
  if (!shown) return <Empty title="Result is empty" />;

  const plain = isPlainSource(scenario.data?.scenario.source ?? session.scenarioSource);
  const extraLines: MapLine[] = sp.res ? [{ geometry: sp.res.path_geometry, color: "#0b1530", weight: 5, dashed: true, label: `Shortest path · ETA ${fmt(sp.res.eta_min, 1)} min` }] : [];
  const spPoints: MapPoint[] = sp.res && sp.src && sp.dst ? [
    { lat: sp.src[0], lon: sp.src[1], label: "S", color: "#0d9488" },
    { lat: sp.dst[0], lon: sp.dst[1], label: "T", color: "#dc2626" },
  ] : [];

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-center gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm">Job {shown.job_id}</span>
          <MockBadge text={shown.job_id} />
          <span className="badge text-white" style={{ background: algoColor(shown.algorithm) }}>
            {shown.algorithm.toUpperCase()}
          </span>
          <span className="text-sm text-slate-600">seed {shown.seed}</span>
          <span className="text-sm text-slate-600">depart {minToHHMM(departOf(shown))}</span>
          <span className={`badge ${shown.status === "COMPLETED" ? "bg-teal-100 text-teal-800" : "bg-amber-100 text-amber-800"}`}>
            {shown.status === "COMPLETED_PARTIAL" ? "Partial result" : "Completed"}
          </span>
          <span className="text-xs text-slate-500">instance {shown.meta.instance}</span>
        </div>
        <div className="ml-auto flex gap-2">
          <button className="btn-danger" onClick={() => setDrawerOpen((o) => !o)} disabled={busy}>
            + Incident
          </button>
          <button className="btn-secondary" onClick={() => downloadJson(shown, `quantumroute_${shown.job_id}.json`)}>
            Export JSON
          </button>
        </div>
      </div>

      {shown.status === "COMPLETED_PARTIAL" && (
        <div className="rounded-md bg-amber-50 p-2 text-sm text-amber-800">
          Partial result: the job stopped early (budget, cancel or time limit). Best solution found so far is shown.
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <div className="space-y-2">
          {compare && (
            <div className="flex items-center gap-2">
              <div className="inline-flex overflow-hidden rounded-md border border-slate-300">
                {(["before", "after"] as const).map((v) => (
                  <button key={v} className={`px-4 py-1 text-sm ${view === v ? "bg-teal-600 text-white" : "bg-white"}`} onClick={() => setView(v)}>
                    {v === "before" ? "Before (original plan)" : "After re-optimize"}
                  </button>
                ))}
              </div>
              <button className="text-xs text-slate-500 underline" onClick={() => setCompare(null)}>
                clear incident view
              </button>
            </div>
          )}
          <RouteMap
            routes={shown.routes}
            edgeFlows={shown.edge_flows}
            showFlows={showFlows}
            customers={scenario.data?.customers}
            depot={scenario.data ? [scenario.data.depot.lat, scenario.data.depot.lon] : null}
            incident={incidentCircle}
            extraLines={extraLines}
            points={spPoints}
            plain={plain}
            height={540}
            onMapClick={drawerOpen ? (lat, lon) => setDraft((d) => ({ ...d, center: [lat, lon] })) : undefined}
          />
          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
            <label className="flex items-center gap-1">
              <input type="checkbox" checked={showFlows} onChange={(e) => setShowFlows(e.target.checked)} />
              Congested edges (amber → red by V/C, width = fleet flow)
            </label>
            {!shown.edge_flows?.length && <span className="text-slate-400">(no edge_flows in this result)</span>}
            <span>★ depot · ○ customer</span>
          </div>
        </div>
        <div className="space-y-4">
          {drawerOpen && <IncidentDrawer draft={draft} onChange={setDraft} onSubmit={submitIncident} onClose={() => setDrawerOpen(false)} busy={busy} />}
          {busy && reoptJob && (
            <div className="card text-sm">
              Re-optimizing (warm start from {result.data?.job_id}) — {reopt.status ?? "queued"}
              {reopt.progress != null ? ` ${Math.round(reopt.progress * 100)}%` : ""} via {reopt.transport}
            </div>
          )}
          <KpiCards kpis={shown.kpis} />
          {compare && (
            <div className="card space-y-2 text-sm">
              <div className="label">Incident impact {compare.source === "demo" && <MockBadge text={compare.after.job_id} />}</div>
              {compare.source === "demo" && <div className="text-xs text-slate-500">Demo mode shows the pre-exported incident scenario, not the zone you drew.</div>}
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs text-slate-500">
                    <th>KPI</th>
                    <th>Before</th>
                    <th>After</th>
                    <th>Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {(
                    [
                      ["Total time", "total_time_min", "min"],
                      ["Congestion delay", "congestion_delay_min", "min"],
                      ["Distance", "total_distance_km", "km"],
                      ["CO₂", "co2_kg", "kg"],
                    ] as const
                  ).map(([label, k, u]) => (
                    <tr key={k}>
                      <td>{label}</td>
                      <td>{fmt(compare.before.kpis[k], 1)}</td>
                      <td>{fmt(compare.after.kpis[k], 1)}</td>
                      <td>
                        <Delta a={compare.before.kpis[k]} b={compare.after.kpis[k]} unit={u} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {compare.report && (
                <div className="space-y-1 border-t border-slate-100 pt-2">
                  <div>
                    Re-plan {compare.report.accepted ? "accepted" : "rejected"} · delay avoided {fmt(compare.report.delay_avoided_min, 1)} min · re-opt time{" "}
                    {fmt(compare.report.reopt_time_s, 2)} s
                  </div>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-slate-500">
                        <th>Vehicle</th>
                        <th>ETA before</th>
                        <th>ETA after</th>
                      </tr>
                    </thead>
                    <tbody>
                      {compare.report.eta_change.map((e) => (
                        <tr key={e.vehicle}>
                          <td>{e.vehicle}</td>
                          <td>{minToHHMM(e.before_min)}</td>
                          <td>{minToHHMM(e.after_min)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
          <div className="card space-y-2 text-sm">
            <div className="label">Shortest path (TD-Dijkstra)</div>
            {demo ? (
              <div className="text-xs text-slate-500">Demo mode uses the pre-exported source/target from shortest_path_demo.json.</div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <select className="input" value={spFrom} onChange={(e) => setSpFrom(e.target.value)}>
                  {nodes.map((n) => (
                    <option key={n.key} value={n.key}>
                      {n.label}
                    </option>
                  ))}
                </select>
                <select className="input" value={spTo} onChange={(e) => setSpTo(e.target.value)}>
                  <option value="">target…</option>
                  {nodes.map((n) => (
                    <option key={n.key} value={n.key}>
                      {n.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <button className="btn-primary" disabled={sp.busy || (!demo && (!spTo || !nodes.length))} onClick={runSp}>
              {sp.busy ? "Computing…" : "Compute path"}
            </button>
            {sp.err && <div className="text-red-700">{sp.err}</div>}
            {sp.res && (
              <div>
                ETA <b>{fmt(sp.res.eta_min, 1)} min</b> · cost {fmt(sp.res.cost, 2)} · {fmt(sp.res.runtime_s, 3)} s
                {sp.res.gap_pct != null && <> · gap {fmt(sp.res.gap_pct, 2)}%</>}{" "}
                <Link to="/path" className="text-teal-700 underline">
                  open Shortest Path
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="label">Routes</div>
        <RouteTable routes={shown.routes} />
      </div>
      <ExplanationPanel lines={shown.explanation} />
    </div>
  );
}
