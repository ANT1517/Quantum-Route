import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Download, LayoutDashboard, Route as RouteIcon, ScrollText, Truck } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
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
import CongestionChart, { CongestionLegend } from "../components/charts/CongestionChart";
import ConvergenceChart from "../components/ConvergenceChart";
import ExplanationPanel from "../components/ExplanationPanel";
import IncidentDrawer, { defaultDraft, type IncidentDraft } from "../components/IncidentDrawer";
import RouteMap, { type LatLon, type MapLine, type MapPoint } from "../components/RouteMap";
import RouteTable from "../components/RouteTable";
import { Empty, ErrorState, Loading, MockBadge } from "../components/States";
import { DecisionLog, Hi, InsightBlock, InsightsColumn, SignalRow } from "../components/ui/Insights";
import { Checkbox, Chip, DataTable, KpiCard, Panel, Segmented, Select } from "../components/ui/primitives";
import { PageShell, SubNav, type SubNavItem } from "../components/ui/Shell";
import { useJobProgress } from "../hooks/useJobProgress";
import { algoLabel } from "../lib/labels";
import { algoColor, vehicleColor } from "../lib/colors";
import { useDemoMode } from "../lib/demoMode";
import { setEngineFromResult } from "../lib/engine";
import { logEvent } from "../lib/eventLog";
import { downloadJson, fmt, minToHHMM } from "../lib/format";
import { isPlainSource, useSession } from "../lib/session";
import { notify } from "../lib/toast";
import { loadRatio, peakLabel } from "../lib/trafficProfile";

interface Compare {
  before: ResultJSON;
  after: ResultJSON;
  incident: ZoneIncident;
  report?: IncidentDemo["report"];
  source: "demo" | "live";
}

type Section = "overview" | "routes" | "vehicles" | "incidents" | "log";

function departOf(r: ResultJSON): number {
  const d = r.routes.map((x) => x.depart_min).filter((x) => Number.isFinite(x));
  return d.length ? Math.min(...d) : r.meta.tau0;
}

function deltaOf(a: number, b: number, unit: string, digits = 1): { text: string; tone: "lime" | "red" | "plain" } {
  const d = b - a;
  return { text: `${d > 0 ? "+" : ""}${fmt(d, digits)} ${unit}`, tone: d < 0 ? "lime" : d > 0 ? "red" : "plain" };
}

function Delta({ a, b, unit }: { a: number; b: number; unit: string }) {
  const d = deltaOf(a, b, unit);
  return <span style={{ color: d.tone === "plain" ? "var(--mute)" : `var(--${d.tone})` }}>{d.text}</span>;
}

const HERO = { title: "Every van, routed through", titleAccent: "live city traffic." };

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

  const [section, setSection] = useState<Section>("overview");
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
    if (result.data) {
      setDraft(defaultDraft(departOf(result.data)));
      setEngineFromResult(result.data.algorithm);
    }
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
          logEvent("reopt", `re-optimized ${after.job_id} · total time ${fmt(after.kpis.total_time_min, 1)} min`);
        })
        .catch(() => undefined)
        .finally(() => setBusy(false));
    } else {
      notify(`Re-optimization ${reopt.status}${reopt.error ? `: ${reopt.error}` : ""}`);
      logEvent("warn", `re-optimization ${reopt.status}`);
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
        logEvent("incident", `incident zone ${d.incident.radius_m} m ×${d.incident.factor} (pre-exported demo)`);
        logEvent("reopt", `re-plan ${d.report.accepted ? "accepted" : "rejected"} · delay avoided ${fmt(d.report.delay_avoided_min, 1)} min`);
        return;
      }
      const r = result.data;
      await addIncident(r.scenario_id, inc);
      logEvent("incident", `incident zone ${inc.radius_m} m ×${inc.factor} ${minToHHMM(inc.start_min)}–${minToHHMM(inc.end_min)}`);
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
      logEvent("run", `re-optimizing ${job.job_id} (warm start from ${r.job_id})`);
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

  const shell = (eyebrow: string, children: ReactNode, lead = "Fleet routes on the time-dependent road network, with the congestion they meet. Traffic is simulated.") => (
    <PageShell hero={{ eyebrow, ...HERO, lead }}>{children}</PageShell>
  );

  if (!jobId) {
    return shell(
      "NO PLAN YET",
      <Empty title="No result yet">
        <Link to="/run" className="text-teal underline">
          Run the optimizer
        </Link>{" "}
        or switch on demo mode.
      </Empty>,
    );
  }
  if (result.isLoading) return shell("LOADING PLAN", <Loading label="Loading result…" />);
  if (result.isError) {
    const e = result.error;
    const msg = e instanceof ApiError && e.status === 409 ? "Job has not finished yet." : undefined;
    return shell("RESULT UNAVAILABLE", <ErrorState error={msg ?? e} onRetry={() => result.refetch()} />);
  }
  if (!shown) return shell("RESULT EMPTY", <Empty title="Result is empty" />);

  const k = shown.kpis;
  const depart = departOf(shown);
  const peak = peakLabel(depart);
  const plain = isPlainSource(scenario.data?.scenario.source ?? session.scenarioSource);
  const delayShare = k.total_time_min > 0 ? (k.congestion_delay_min / k.total_time_min) * 100 : null;
  const stops = shown.routes.reduce((a, r) => a + r.stops.length, 0);
  const before = compare?.before.kpis;

  const extraLines: MapLine[] = sp.res ? [{ geometry: sp.res.path_geometry, color: "#FFFFFF", weight: 4, dashed: true, label: `Shortest path · ETA ${fmt(sp.res.eta_min, 1)} min` }] : [];
  const spPoints: MapPoint[] =
    sp.res && sp.src && sp.dst
      ? [
          { lat: sp.src[0], lon: sp.src[1], label: "S", color: "#4FE3D1" },
          { lat: sp.dst[0], lon: sp.dst[1], label: "T", color: "#FFB547" },
        ]
      : [];

  const eyebrow = [
    compare ? (view === "after" ? "RE-PLANNED AROUND INCIDENT" : "ORIGINAL PLAN") : shown.status === "COMPLETED_PARTIAL" ? "PARTIAL PLAN" : "PLAN READY",
    String(shown.meta.instance).toUpperCase(),
    `${minToHHMM(depart)}${peak ? ` ${peak}` : ""}`,
  ].join(" · ");

  const subItems: Array<SubNavItem<Section>> = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "routes", label: "Routes", icon: RouteIcon, count: shown.routes.length },
    { id: "vehicles", label: "Vehicles", icon: Truck, count: k.vehicles_used },
    { id: "incidents", label: "Incidents", icon: AlertTriangle, count: compare ? 1 : null, countTone: "amber" },
    { id: "log", label: "Event log", icon: ScrollText, count: shown.explanation.length || null },
  ];

  const openIncident = () => {
    setDrawerOpen(true);
    setSection("incidents");
  };

  const mapFor = (opts: { height: number; clickable?: boolean; flows?: boolean; sp?: boolean }) => (
    <RouteMap
      routes={shown.routes}
      edgeFlows={shown.edge_flows}
      showFlows={opts.flows ? showFlows : false}
      customers={scenario.data?.customers}
      depot={scenario.data ? [scenario.data.depot.lat, scenario.data.depot.lon] : null}
      incident={incidentCircle}
      extraLines={opts.sp ? extraLines : undefined}
      points={opts.sp ? spPoints : undefined}
      plain={plain}
      height={opts.height}
      onMapClick={opts.clickable && drawerOpen ? (lat, lon) => setDraft((d) => ({ ...d, center: [lat, lon] })) : undefined}
    />
  );

  const beforeAfter = compare && (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <Segmented
        ariaLabel="Plan version"
        value={view}
        onChange={setView}
        options={[
          ["before", "Before (original plan)"],
          ["after", "After re-optimize"],
        ]}
      />
      <button type="button" className="btn-ghost btn-sm" onClick={() => setCompare(null)}>
        clear incident view
      </button>
      {compare.source === "demo" && <Chip tone="amber">pre-exported incident (demo)</Chip>}
    </div>
  );

  const kpiRow = (
    <div className="grid gap-3 sm:grid-cols-3">
      <KpiCard
        label="Total fleet time"
        value={fmt(k.total_time_min, 1)}
        unit="min"
        delta={before ? deltaOf(before.total_time_min, k.total_time_min, "min") : undefined}
        context={before ? "vs original plan" : `${k.vehicles_used} vehicles · ${stops} stops`}
      />
      <KpiCard
        label="Congestion delay"
        value={fmt(k.congestion_delay_min, 1)}
        unit="min"
        tone="amber"
        delta={before ? deltaOf(before.congestion_delay_min, k.congestion_delay_min, "min") : delayShare != null ? { text: `${delayShare.toFixed(0)}%`, tone: "amber" } : undefined}
        context={before ? "vs original plan" : "of driving time · simulated traffic"}
      />
      <KpiCard
        label="Feasibility"
        value={k.feasible ? "Feasible" : "Infeasible"}
        tone={k.feasible ? "lime" : "red"}
        context={`${fmt(k.vehicles_used)}${k.fleet_limit != null ? ` / ${fmt(k.fleet_limit)}` : ""} vehicles · ${fmt(k.total_distance_km, 1)} km · CO₂ ${fmt(k.co2_kg, 1)} kg (illustrative)`}
        title={`Distance ${fmt(k.total_distance_km, 1)} km · CO₂ ${fmt(k.co2_kg, 1)} kg (illustrative model) · runtime ${fmt(k.runtime_s, 2)} s · ${fmt(k.evals)} evaluations · F ${fmt(k.fitness, 4)}`}
      />
    </div>
  );

  const vehicleLegend = (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-mute">
      {shown.routes.map((r, i) => (
        <span key={r.vehicle} className="flex items-center gap-1.5">
          <span className="inline-block h-[2px] w-3.5 rounded" style={{ background: vehicleColor(i), boxShadow: `0 0 6px ${vehicleColor(i)}` }} />V{r.vehicle}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2 w-2 rounded-[2px] bg-white" style={{ boxShadow: "0 0 6px #fff" }} /> depot
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2 w-2 rounded-full" style={{ background: "#030304", boxShadow: "0 0 0 1px #CFD3D8" }} /> customer
      </span>
    </div>
  );

  let main: ReactNode;
  if (section === "overview") {
    main = (
      <div className="space-y-3">
        {beforeAfter}
        {kpiRow}
        <Panel
          overlay
          title="Live route map"
          chips={
            <>
              <Chip tone="teal">{shown.routes.length} routes</Chip>
              {compare && <Chip tone="amber">incident zone</Chip>}
            </>
          }
          meta={`${minToHHMM(depart)} departure · simulated traffic`}
        >
          {mapFor({ height: 380 })}
          <div className="px-4 py-2.5" style={{ borderTop: "1px solid var(--line)" }}>
            {vehicleLegend}
          </div>
        </Panel>
        <Panel title="Network congestion · 24 h" chips={<Chip>ρ = V/C · background</Chip>} meta={<CongestionLegend />} bodyClassName="px-2 pb-2">
          <CongestionChart departMin={depart} height={200} />
          <div className="px-2 pb-1 font-mono text-[10px] text-lbl">Simulated time-of-day load-ratio profiles (engine/qflux/traffic/profiles.py), not measurements.</div>
        </Panel>
      </div>
    );
  } else if (section === "routes") {
    main = (
      <div className="space-y-3">
        {beforeAfter}
        <Panel overlay title="Routes" chips={<Chip tone="teal">{shown.routes.length} vehicles</Chip>} meta={sp.res ? `shortest path ETA ${fmt(sp.res.eta_min, 1)} min` : undefined}>
          {mapFor({ height: 460, flows: true, sp: true })}
          <div className="flex flex-wrap items-center gap-4 px-4 py-2.5" style={{ borderTop: "1px solid var(--line)" }}>
            {vehicleLegend}
            <div className="ml-auto">
              <Checkbox checked={showFlows} onChange={setShowFlows}>
                Congested edges (amber → red by V/C, width = fleet flow)
              </Checkbox>
            </div>
            {!shown.edge_flows?.length && <span className="font-mono text-[10px] text-lbl">no edge_flows in this result</span>}
          </div>
        </Panel>
        <Panel title="Shortest path (TD-Dijkstra)" bodyClassName="px-4 pb-4 space-y-3">
          {demo ? (
            <div className="text-[12px] text-mute">Demo mode uses the pre-exported source/target from shortest_path_demo.json.</div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <Select aria-label="Shortest path source" value={spFrom} onChange={(e) => setSpFrom(e.target.value)}>
                {nodes.map((n) => (
                  <option key={n.key} value={n.key}>
                    {n.label}
                  </option>
                ))}
              </Select>
              <Select aria-label="Shortest path target" value={spTo} onChange={(e) => setSpTo(e.target.value)}>
                <option value="">target…</option>
                {nodes.map((n) => (
                  <option key={n.key} value={n.key}>
                    {n.label}
                  </option>
                ))}
              </Select>
            </div>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" className="btn-secondary" disabled={sp.busy || (!demo && (!spTo || !nodes.length))} onClick={runSp}>
              {sp.busy ? "Computing…" : "Compute path"}
            </button>
            {sp.err && <span className="text-[12.5px] text-danger">{sp.err}</span>}
            {sp.res && (
              <span className="num text-[12.5px] text-txt2">
                ETA <span className="text-teal">{fmt(sp.res.eta_min, 1)} min</span> · cost {fmt(sp.res.cost, 2)} · {fmt(sp.res.runtime_s, 3)} s
                {sp.res.gap_pct != null && <> · gap {fmt(sp.res.gap_pct, 2)}%</>}{" "}
                <Link to="/path" className="font-sans text-teal underline">
                  open Shortest path
                </Link>
              </span>
            )}
          </div>
        </Panel>
      </div>
    );
  } else if (section === "vehicles") {
    main = (
      <div className="space-y-3">
        {beforeAfter}
        <Panel title="Vehicle status" chips={<Chip tone="teal">{k.vehicles_used} in use</Chip>} meta={k.fleet_limit != null ? `fleet limit ${k.fleet_limit}` : undefined} bodyClassName="px-4 pb-3">
          <RouteTable routes={shown.routes} />
        </Panel>
      </div>
    );
  } else if (section === "incidents") {
    main = (
      <div className="space-y-3">
        {beforeAfter}
        <div className={`grid gap-3 ${drawerOpen ? "min-[1300px]:grid-cols-[minmax(0,1fr)_300px]" : ""}`}>
          <Panel overlay title="Incident map" chips={drawerOpen ? <Chip tone="amber">click the map to place the zone</Chip> : compare ? <Chip tone="amber">incident zone</Chip> : undefined}>
            {mapFor({ height: 420, clickable: true })}
          </Panel>
          {drawerOpen && <IncidentDrawer draft={draft} onChange={setDraft} onSubmit={submitIncident} onClose={() => setDrawerOpen(false)} busy={busy} />}
        </div>
        {busy && reoptJob && (
          <div className="box flex items-center gap-2 px-3 py-2 font-mono text-[11.5px] text-txt2" role="status">
            <span className="dot-live dot-amber" />
            Re-optimizing (warm start from {result.data?.job_id}) — {reopt.status ?? "queued"}
            {reopt.progress != null ? ` ${Math.round(reopt.progress * 100)}%` : ""} via {reopt.transport}
          </div>
        )}
        {!compare && !drawerOpen && (
          <Empty title="No incident on this plan">
            <button type="button" className="btn-warn mt-2" onClick={openIncident}>
              + Add incident
            </button>
          </Empty>
        )}
        {compare && (
          <Panel title="Incident impact" chips={compare.source === "demo" ? <MockBadge text={compare.after.job_id} /> : undefined} meta="simulated incident" bodyClassName="px-4 pb-4 space-y-3">
            {compare.source === "demo" && <div className="text-[12px] text-mute">Demo mode shows the pre-exported incident scenario, not the zone you drew.</div>}
            <DataTable>
              <thead>
                <tr>
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
                    ["CO₂ (illustrative)", "co2_kg", "kg"],
                  ] as const
                ).map(([label, kk, u]) => (
                  <tr key={kk}>
                    <td>{label}</td>
                    <td className="n">{fmt(compare.before.kpis[kk], 1)}</td>
                    <td className="n text-txt">{fmt(compare.after.kpis[kk], 1)}</td>
                    <td className="n">
                      <Delta a={compare.before.kpis[kk]} b={compare.after.kpis[kk]} unit={u} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
            {compare.report && (
              <>
                <div className="num text-[12px] text-txt2">
                  Re-plan <Hi tone={compare.report.accepted ? "lime" : "amber"}>{compare.report.accepted ? "accepted" : "rejected"}</Hi> · delay avoided{" "}
                  <Hi>{fmt(compare.report.delay_avoided_min, 1)} min</Hi> · re-opt time {fmt(compare.report.reopt_time_s, 2)} s
                </div>
                <DataTable>
                  <thead>
                    <tr>
                      <th>Vehicle</th>
                      <th>ETA before</th>
                      <th>ETA after</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compare.report.eta_change.map((e) => (
                      <tr key={e.vehicle}>
                        <td className="n">V{e.vehicle}</td>
                        <td className="n">{minToHHMM(e.before_min)}</td>
                        <td className="n">{minToHHMM(e.after_min)}</td>
                      </tr>
                    ))}
                  </tbody>
                </DataTable>
              </>
            )}
          </Panel>
        )}
      </div>
    );
  } else {
    main = (
      <div className="space-y-3">
        <ExplanationPanel lines={shown.explanation} />
        <Panel title="Convergence of this plan" chips={<Chip>best-so-far F</Chip>} meta={`${fmt(k.evals)} evaluations · ${fmt(k.runtime_s, 2)} s`} bodyClassName="px-2 pb-2">
          <ConvergenceChart series={[{ name: algoLabel(shown.algorithm), color: algoColor(shown.algorithm), points: shown.convergence }]} height={220} />
        </Panel>
        <Panel title="Run record" bodyClassName="px-4 pb-4">
          <DataTable>
            <tbody>
              {(
                [
                  ["Job", shown.job_id],
                  ["Engine", algoLabel(shown.algorithm)],
                  ["Seed", shown.seed],
                  ["Status", shown.status],
                  ["Instance", shown.meta.instance],
                  ["Config hash", shown.meta.config_hash],
                  ["Weights (T/D/C/E)", `${shown.weights.wT} / ${shown.weights.wD} / ${shown.weights.wC} / ${shown.weights.wE}`],
                ] as Array<[string, unknown]>
              ).map(([a, b]) => (
                <tr key={a}>
                  <td className="micro">{a}</td>
                  <td className="n text-txt">{fmt(b)}</td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </Panel>
      </div>
    );
  }

  const insights = (
    <InsightsColumn>
      <InsightBlock label="Recommended action" tone={compare ? "amber" : "teal"}>
        {compare?.report ? (
          <>
            Re-plan <Hi tone={compare.report.accepted ? "lime" : "amber"}>{compare.report.accepted ? "accepted" : "rejected"}</Hi>: it avoids{" "}
            <Hi>{fmt(compare.report.delay_avoided_min, 1)} min</Hi> of incident delay (simulated incident).
          </>
        ) : shown.explanation.length ? (
          <ul className="space-y-1.5">
            {shown.explanation.slice(0, 2).map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        ) : (
          "No explanation sentences in this result."
        )}
        <div className="mt-2 flex gap-2">
          <button type="button" className="btn-warn btn-sm" onClick={openIncident} disabled={busy}>
            + Add incident
          </button>
          <Link to="/fleet" className="btn-secondary btn-sm">
            Fleet impact →
          </Link>
        </div>
      </InsightBlock>
      <InsightBlock label="Signal summary">
        <SignalRow k="Congestion share" v={delayShare != null ? `${delayShare.toFixed(1)}%` : "–"} tone="amber" />
        <SignalRow k={`Arterial ρ at ${minToHHMM(depart)}`} v={loadRatio(depart, 0).toFixed(2)} tone={peak === "PEAK" ? "amber" : undefined} />
        <SignalRow k="Vehicles" v={`${fmt(k.vehicles_used)}${k.fleet_limit != null ? ` / ${fmt(k.fleet_limit)}` : ""}`} />
        <SignalRow k="Evaluations" v={fmt(k.evals)} />
        <SignalRow k="Runtime" v={`${fmt(k.runtime_s, 2)} s`} />
        <SignalRow k="Fitness F" v={fmt(k.fitness, 4)} tone="teal" />
      </InsightBlock>
      <DecisionLog
        lines={[
          { t: minToHHMM(depart), text: `plan departs · ${shown.meta.instance}` },
          { text: `${algoLabel(shown.algorithm)} · seed ${shown.seed}` },
          { text: `job ${shown.job_id} · ${shown.status}`, tone: shown.status === "COMPLETED" ? "teal" : "amber" },
          ...(compare ? [{ t: minToHHMM(compare.incident.start_min), text: `incident ${compare.incident.radius_m} m ×${compare.incident.factor} (simulated)`, tone: "amber" as const }] : []),
        ]}
      />
    </InsightsColumn>
  );

  return (
    <PageShell
      hero={{
        eyebrow,
        eyebrowTone: compare && view === "after" ? "amber" : "teal",
        ...HERO,
        lead: `${k.vehicles_used} vehicles serve ${stops} stops on the time-dependent road network, departing ${minToHHMM(depart)}. Congestion and CO₂ come from the traffic model (simulated traffic, illustrative CO₂).`,
        meta: (
          <span className="flex flex-wrap items-center gap-2">
            engine · {algoLabel(shown.algorithm)} → <span>job {shown.job_id}</span> <MockBadge text={shown.job_id} />
          </span>
        ),
        actions: (
          <>
            <button type="button" className="btn-warn" onClick={openIncident} disabled={busy}>
              + Add incident
            </button>
            <button type="button" className="btn-secondary" onClick={() => downloadJson(shown, `quantumroute_${shown.job_id}.json`)}>
              <Download size={14} strokeWidth={1.5} /> Export JSON
            </button>
            <Link to="/fleet" className="btn-primary">
              Fleet impact →
            </Link>
          </>
        ),
      }}
      subnav={<SubNav title="Results" items={subItems} active={section} onChange={setSection} />}
      insights={insights}
    >
      {shown.status === "COMPLETED_PARTIAL" && (
        <div className="mb-3 rounded-lg px-3 py-2 text-[12.5px] text-amber" style={{ background: "rgba(255,181,71,.06)", border: "1px solid rgba(255,181,71,.3)" }}>
          Partial result: the job stopped early (budget, cancel or time limit). Best solution found so far is shown.
        </div>
      )}
      <div key={section} className="qr-fade">
        {main}
      </div>
    </PageShell>
  );
}
