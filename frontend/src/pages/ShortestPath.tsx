import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, addIncident, getScenario, getShortestPathDemo, shortestPath } from "../api/client";
import type { ShortestPathRequest, ZoneIncident } from "../api/types";
import type { ShortestPathResponse } from "../types/result";
import RouteMap, { type LatLon, type MapLine, type MapPoint } from "../components/RouteMap";
import { Empty, ErrorState, Loading, MockBadge } from "../components/States";
import { useDemoMode } from "../lib/demoMode";
import { fmt, hhmmToMin, minToHHMM } from "../lib/format";
import { isPlainSource, useSession } from "../lib/session";

type Algo = ShortestPathRequest["algorithm"];

interface Outcome {
  before: ShortestPathResponse | null;
  after: ShortestPathResponse | null;
  incident: ZoneIncident | null;
}

export default function ShortestPath() {
  const demo = useDemoMode();
  const session = useSession();
  const scenarioId = session.scenarioId ?? (demo ? "demo" : null);
  const scenario = useQuery({
    queryKey: ["scenario", scenarioId],
    queryFn: ({ signal }) => getScenario(scenarioId!, { signal, silent: true }),
    enabled: !!scenarioId,
  });
  const spDemo = useQuery({ queryKey: ["sp-demo"], queryFn: ({ signal }) => getShortestPathDemo({ signal, silent: true }), enabled: demo });

  const [src, setSrc] = useState<LatLon | null>(null);
  const [dst, setDst] = useState<LatLon | null>(null);
  const [picking, setPicking] = useState<"source" | "target">("source");
  const [depart, setDepart] = useState("17:30");
  const [algo, setAlgo] = useState<Algo>("dijkstra");
  const [withIncident, setWithIncident] = useState(false);
  const [busy, setBusy] = useState(false);
  const [noPath, setNoPath] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<Outcome | null>(null);

  useEffect(() => {
    if (demo && spDemo.data) {
      setSrc(spDemo.data.source);
      setDst(spDemo.data.target);
      setDepart(minToHHMM(spDemo.data.depart_min));
    } else if (!demo && scenario.data) {
      setDepart(minToHHMM(scenario.data.scenario.tau0));
    }
  }, [demo, spDemo.data, scenario.data]);

  const onMapClick = (lat: number, lon: number) => {
    if (picking === "source") {
      setSrc([lat, lon]);
      setPicking("target");
    } else {
      setDst([lat, lon]);
      setPicking("source");
    }
    setOut(null);
    setNoPath(false);
  };

  const compute = async () => {
    if (!src || !dst) return;
    const sid = scenario.data?.scenario.id ?? scenarioId;
    if (!sid) return;
    setBusy(true);
    setErr(null);
    setNoPath(false);
    const req: ShortestPathRequest = { scenario_id: sid, source: src, target: dst, depart_min: hhmmToMin(depart), algorithm: algo };
    try {
      const before = await shortestPath(req, { silent: true, demoIncident: false });
      let after: ShortestPathResponse | null = null;
      let incident: ZoneIncident | null = null;
      if (withIncident) {
        if (demo) {
          incident = spDemo.data?.incident ?? null;
        } else {
          // Zone on the computed fastest road path, at the point reached after ~50% of the travel time (D60),
          // active during the trip window; persisted on the scenario by the backend.
          const onPath = before.halfway_by_time ?? [(src[0] + dst[0]) / 2, (src[1] + dst[1]) / 2];
          incident = {
            type: "zone",
            center: [onPath[0], onPath[1]],
            radius_m: 1000,
            factor: 3,
            start_min: hhmmToMin(depart),
            end_min: hhmmToMin(depart) + 120,
          };
          await addIncident(sid, incident, { silent: true });
        }
        after = await shortestPath(req, { silent: true, demoIncident: true });
      }
      setOut({ before, after, incident });
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setNoPath(true);
      else setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!scenarioId) {
    return (
      <Empty title="No scenario selected">
        <Link to="/scenario" className="text-teal-700 underline">
          Pick a scenario
        </Link>
      </Empty>
    );
  }

  const lines: MapLine[] = [];
  if (out?.before) lines.push({ geometry: out.before.path_geometry, color: out.after ? "#64748b" : "#0d9488", weight: 5, dashed: !!out.after, label: `Before · ETA ${fmt(out.before.eta_min, 1)} min` });
  if (out?.after) lines.push({ geometry: out.after.path_geometry, color: "#0d9488", weight: 6, label: `With incident · ETA ${fmt(out.after.eta_min, 1)} min` });
  const pts: MapPoint[] = [];
  if (src) pts.push({ lat: src[0], lon: src[1], label: (demo && spDemo.data?.labels?.source) || "Source", color: "#0d9488" });
  if (dst) pts.push({ lat: dst[0], lon: dst[1], label: (demo && spDemo.data?.labels?.target) || "Target", color: "#dc2626" });

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <div className="card space-y-3">
        <h1 className="page-title">Shortest Path</h1>
        <p className="text-xs text-slate-500">Time-dependent shortest path (ambulance demo). Click the map to set the {picking}.</p>
        <div className="text-sm">
          <div>
            Source: {src ? <span className="font-mono">{src[0].toFixed(4)}, {src[1].toFixed(4)}</span> : <span className="text-amber-700">click map</span>}
          </div>
          <div>
            Target: {dst ? <span className="font-mono">{dst[0].toFixed(4)}, {dst[1].toFixed(4)}</span> : <span className="text-amber-700">click map</span>}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="label">Departure</label>
            <input type="time" className="input" value={depart} onChange={(e) => setDepart(e.target.value || "00:00")} />
          </div>
          <div>
            <label className="label">Algorithm</label>
            <select className="input" value={algo} onChange={(e) => setAlgo(e.target.value as Algo)}>
              <option value="dijkstra">TD-Dijkstra (exact)</option>
              <option value="astar">A*</option>
            </select>
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={withIncident} onChange={(e) => setWithIncident(e.target.checked)} />
          Incident on the way (recompute path + ETA)
        </label>
        {withIncident && !demo && (
          <div className="text-xs text-amber-700">Adds a 1 km zone (×3) on the computed path, at ~50% of its travel time, to this scenario on the backend.</div>
        )}
        <button className="btn-primary w-full justify-center" disabled={busy || !src || !dst} onClick={compute}>
          {busy ? "Computing…" : "Compute path"}
        </button>
        {demo && spDemo.data && <MockBadge text={spDemo.data.labels?.source ?? "MOCK"} />}
      </div>
      <div className="space-y-4">
        {scenario.isLoading || (demo && spDemo.isLoading) ? (
          <Loading />
        ) : scenario.isError ? (
          <ErrorState error={scenario.error} onRetry={() => scenario.refetch()} />
        ) : (
          <RouteMap
            customers={scenario.data?.customers}
            depot={scenario.data ? [scenario.data.depot.lat, scenario.data.depot.lon] : null}
            extraLines={lines}
            points={pts}
            incident={out?.incident ? { center: out.incident.center, radius_m: out.incident.radius_m } : null}
            plain={isPlainSource(scenario.data?.scenario.source ?? session.scenarioSource)}
            onMapClick={onMapClick}
            height={520}
          />
        )}
        {noPath && (
          <div className="rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-800" role="alert">
            <b>No path</b> between the selected points (404). Try points on the road network or a different departure time.
          </div>
        )}
        {err && <ErrorState error={err} onRetry={compute} />}
        {!out && !noPath && !err && <Empty title="No path computed yet">Pick source and target, then press Compute.</Empty>}
        {out && (
          <div className="grid gap-4 md:grid-cols-2">
            {([
              ["Before", out.before],
              ["With incident", out.after],
            ] as const).map(([label, r]) =>
              r ? (
                <div key={label} className="card">
                  <div className="label">{label}</div>
                  <div className="text-2xl font-bold text-teal-700">
                    {fmt(r.eta_min, 1)} <span className="text-sm font-normal text-slate-500">min ETA</span>
                  </div>
                  <div className="text-sm text-slate-600">
                    arrive {minToHHMM(hhmmToMin(depart) + r.eta_min)} · cost {fmt(r.cost, 2)} · runtime {fmt(r.runtime_s, 3)} s
                    {r.gap_pct != null && <> · gap {fmt(r.gap_pct, 2)}%</>}
                  </div>
                </div>
              ) : null,
            )}
          </div>
        )}
      </div>
    </div>
  );
}
