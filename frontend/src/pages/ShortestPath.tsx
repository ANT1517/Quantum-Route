import { useQuery } from "@tanstack/react-query";
import { ListChecks, Navigation } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, addIncident, getScenario, getShortestPathDemo, shortestPath } from "../api/client";
import type { ShortestPathRequest, ZoneIncident } from "../api/types";
import type { ShortestPathResponse } from "../types/result";
import RouteMap, { type LatLon, type MapLine, type MapPoint } from "../components/RouteMap";
import { Empty, ErrorState, Loading, MockBadge } from "../components/States";
import { DecisionLog, Hi, InsightBlock, InsightsColumn, SignalRow } from "../components/ui/Insights";
import { Checkbox, Chip, DataTable, KpiCard, Panel, Segmented, TrafficChip } from "../components/ui/primitives";
import { PageShell, SubNav } from "../components/ui/Shell";
import { useDemoMode } from "../lib/demoMode";
import { logEvent } from "../lib/eventLog";
import { fmt, hhmmToMin, minToHHMM } from "../lib/format";
import { isPlainSource, useSession } from "../lib/session";
import { loadRatio, peakLabel } from "../lib/trafficProfile";

type Algo = ShortestPathRequest["algorithm"];

interface Outcome {
  before: ShortestPathResponse | null;
  after: ShortestPathResponse | null;
  incident: ZoneIncident | null;
}

type Section = "path" | "details";

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
  const [section, setSection] = useState<Section>("path");

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
      logEvent("done", `${algo === "astar" ? "A*" : "TD-Dijkstra"} path · ETA ${fmt(before.eta_min, 1)} min${after ? ` → ${fmt(after.eta_min, 1)} min with incident` : ""}`);
      if (incident) logEvent("incident", `incident zone ${incident.radius_m} m ×${incident.factor} on the path (simulated)`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setNoPath(true);
      else setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const hero = {
    title: "Fastest path,",
    titleAccent: "even after an incident.",
    lead: "Time-dependent shortest path for an emergency vehicle: the ETA is recomputed when an incident slows the roads ahead. Incident and traffic are simulated.",
  };

  if (!scenarioId) {
    return (
      <PageShell hero={{ eyebrow: "NO SCENARIO SELECTED", ...hero }}>
        <Empty title="No scenario selected">
          <Link to="/scenario" className="text-teal underline">
            Pick a scenario
          </Link>
        </Empty>
      </PageShell>
    );
  }

  const lines: MapLine[] = [];
  if (out?.before) lines.push({ geometry: out.before.path_geometry, color: out.after ? "#9AA6FF" : "#4FE3D1", weight: out.after ? 3.5 : 4.5, dashed: !!out.after, glow: !out.after, label: `Before · ETA ${fmt(out.before.eta_min, 1)} min` });
  if (out?.after) lines.push({ geometry: out.after.path_geometry, color: "#4FE3D1", weight: 4.5, label: `With incident · ETA ${fmt(out.after.eta_min, 1)} min` });
  const pts: MapPoint[] = [];
  if (src) pts.push({ lat: src[0], lon: src[1], label: (demo && spDemo.data?.labels?.source) || "Source", color: "#4FE3D1" });
  if (dst) pts.push({ lat: dst[0], lon: dst[1], label: (demo && spDemo.data?.labels?.target) || "Target", color: "#FFB547" });

  const dMin = hhmmToMin(depart);
  const peak = peakLabel(dMin);
  const b = out?.before;
  const a = out?.after;
  const eyebrow = a
    ? `INCIDENT ON ROUTE · ETA ${fmt(b?.eta_min, 1)} → ${fmt(a.eta_min, 1)} MIN · ${depart}${peak ? ` ${peak}` : ""}`
    : b
      ? `PATH READY · ETA ${fmt(b.eta_min, 1)} MIN · ${depart}${peak ? ` ${peak}` : ""}`
      : `SHORTEST PATH · DEPART ${depart}${peak ? ` ${peak}` : ""}`;

  const controls = (
    <Panel title="Trip" meta={`click the map to set the ${picking}`} bodyClassName="px-4 pb-4">
      <div className="grid gap-3 min-[1300px]:grid-cols-[1fr_auto_auto]">
        <div className="space-y-1 font-mono text-[11.5px]">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-teal" style={{ boxShadow: "0 0 6px var(--teal)" }} />
            <span className="text-lbl">SOURCE</span>
            {src ? <span className="text-txt">{src[0].toFixed(4)}, {src[1].toFixed(4)}</span> : <span className="text-amber">click map</span>}
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-amber" style={{ boxShadow: "0 0 6px var(--amber)" }} />
            <span className="text-lbl">TARGET</span>
            {dst ? <span className="text-txt">{dst[0].toFixed(4)}, {dst[1].toFixed(4)}</span> : <span className="text-amber">click map</span>}
          </div>
        </div>
        <div className="flex items-end gap-2">
          <div>
            <label className="label" htmlFor="sp-depart">
              Departure
            </label>
            <input id="sp-depart" type="time" className="input num w-[110px]" value={depart} onChange={(e) => setDepart(e.target.value || "00:00")} />
          </div>
          <div>
            <div className="label">Algorithm</div>
            <Segmented
              ariaLabel="Shortest path algorithm"
              size="sm"
              value={algo}
              onChange={setAlgo}
              options={[
                ["dijkstra", "TD-Dijkstra (exact)"],
                ["astar", "A*"],
              ]}
            />
          </div>
        </div>
        <div className="flex flex-col justify-end gap-2">
          <Checkbox checked={withIncident} onChange={setWithIncident}>
            Incident on the way
          </Checkbox>
          <button type="button" className="btn-primary" disabled={busy || !src || !dst} onClick={compute}>
            {busy ? "Computing…" : "Compute path →"}
          </button>
        </div>
      </div>
      {withIncident && !demo && <div className="mt-2 text-[11.5px] text-amber">Adds a 1 km zone (×3) on the computed path, at ~50% of its travel time, to this scenario on the backend.</div>}
      {demo && spDemo.data && (
        <div className="mt-2 flex items-center gap-2 text-[11.5px] text-mute">
          Demo mode uses the pre-exported trip ({spDemo.data.labels?.source} → {spDemo.data.labels?.target}). <MockBadge text={spDemo.data.labels?.source ?? "MOCK"} />
        </div>
      )}
    </Panel>
  );

  let main;
  if (scenario.isLoading || (demo && spDemo.isLoading)) main = <Loading />;
  else if (scenario.isError) main = <ErrorState error={scenario.error} onRetry={() => scenario.refetch()} />;
  else if (section === "path") {
    main = (
      <div className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <KpiCard
            label={a ? "ETA · before → with incident" : "ETA"}
            value={b ? (a ? `${fmt(b.eta_min, 1)} → ${fmt(a.eta_min, 1)}` : fmt(b.eta_min, 1)) : "–"}
            unit="min"
            tone={a ? "amber" : b ? "teal" : undefined}
            delta={b && a ? { text: `${a.eta_min - b.eta_min > 0 ? "+" : ""}${fmt(a.eta_min - b.eta_min, 1)} min`, tone: "amber" } : undefined}
            context={b ? `arrive ${minToHHMM(dMin + (a ?? b).eta_min)}` : "compute a path"}
          />
          <KpiCard label="Arterial load ratio ρ" value={loadRatio(dMin, 0).toFixed(2)} context={`at ${depart} · simulated profile`} tone={peak === "PEAK" ? "amber" : undefined} />
          <KpiCard label="Runtime" value={b ? fmt((a ?? b).runtime_s, 3) : "–"} unit="s" context={algo === "astar" ? "A*" : "TD-Dijkstra (exact)"} />
        </div>
        <Panel
          overlay
          title="Path map"
          chips={
            <>
              {b && !a && <Chip tone="teal">fastest path</Chip>}
              {a && <Chip tone="violet">before (dashed)</Chip>}
              {a && <Chip tone="teal">after incident</Chip>}
              {out?.incident && <Chip tone="amber">incident zone · simulated</Chip>}
              <TrafficChip at={dMin} />
            </>
          }
        >
          <RouteMap
            customers={scenario.data?.customers}
            depot={scenario.data ? [scenario.data.depot.lat, scenario.data.depot.lon] : null}
            extraLines={lines}
            points={pts}
            incident={out?.incident ? { center: out.incident.center, radius_m: out.incident.radius_m } : null}
            plain={isPlainSource(scenario.data?.scenario.source ?? session.scenarioSource)}
            onMapClick={onMapClick}
            height={420}
          />
        </Panel>
        {noPath && (
          <div className="rounded-lg px-3 py-2 text-[12.5px] text-danger" role="alert" style={{ background: "rgba(255,122,122,.05)", border: "1px solid rgba(255,122,122,.3)" }}>
            <b>No path</b> between the selected points (404). Try points on the road network or a different departure time.
          </div>
        )}
        {err && <ErrorState error={err} onRetry={compute} />}
        {controls}
      </div>
    );
  } else {
    main = (
      <div className="space-y-3">
        {!out ? (
          <Empty title="No path computed yet">Pick source and target, then press Compute.</Empty>
        ) : (
          <Panel title="Outcome" bodyClassName="px-4 pb-3">
            <DataTable>
              <thead>
                <tr>
                  <th>Run</th>
                  <th>ETA (min)</th>
                  <th>Arrive</th>
                  <th>Cost</th>
                  <th>Runtime (s)</th>
                  <th>Gap</th>
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ["Before", out.before],
                    ["With incident", out.after],
                  ] as const
                ).map(([label, r]) =>
                  r ? (
                    <tr key={label}>
                      <td>{label}</td>
                      <td className="n text-txt">{fmt(r.eta_min, 1)}</td>
                      <td className="n">{minToHHMM(dMin + r.eta_min)}</td>
                      <td className="n">{fmt(r.cost, 2)}</td>
                      <td className="n">{fmt(r.runtime_s, 3)}</td>
                      <td className="n">{r.gap_pct != null ? `${fmt(r.gap_pct, 2)}%` : "–"}</td>
                    </tr>
                  ) : null,
                )}
              </tbody>
            </DataTable>
          </Panel>
        )}
        {controls}
      </div>
    );
  }

  return (
    <PageShell
      hero={{
        eyebrow,
        eyebrowTone: a ? "amber" : "teal",
        ...hero,
        meta: `router · ${algo === "astar" ? "A*" : "TD-Dijkstra (exact)"} · time-dependent BPR travel times`,
        actions: (
          <>
            <Link to="/fleet" className="btn-secondary">
              ← Fleet impact
            </Link>
            <button type="button" className="btn-primary" disabled={busy || !src || !dst} onClick={compute}>
              {busy ? "Computing…" : "Compute path →"}
            </button>
          </>
        ),
      }}
      subnav={
        <SubNav
          title="Shortest path"
          active={section}
          onChange={setSection}
          items={[
            { id: "path", label: "Path map", icon: Navigation },
            { id: "details", label: "Details", icon: ListChecks, count: out ? (out.after ? 2 : 1) : null },
          ]}
        />
      }
      insights={
        <InsightsColumn>
          <InsightBlock label="Recommended action" tone={a ? "amber" : "teal"}>
            {b && a ? (
              <>
                With the incident the fastest path takes <Hi tone="amber">{fmt(a.eta_min - b.eta_min, 1)} min</Hi> longer: ETA <Hi>{fmt(b.eta_min, 1)}</Hi> →{" "}
                <Hi tone="amber">{fmt(a.eta_min, 1)} min</Hi>. Dispatch on the recomputed path (simulated incident).
              </>
            ) : b ? (
              <>
                Fastest path ETA <Hi>{fmt(b.eta_min, 1)} min</Hi>. Tick “Incident on the way” to see how the route and ETA change.
              </>
            ) : (
              "Pick a source and a target on the map, then compute the path."
            )}
          </InsightBlock>
          <InsightBlock label="Signal summary">
            <SignalRow k="Departure" v={depart} />
            <SignalRow k="Arterial ρ" v={loadRatio(dMin, 0).toFixed(2)} tone={peak === "PEAK" ? "amber" : undefined} />
            {out?.incident && <SignalRow k="Incident" v={`${out.incident.radius_m} m ×${out.incident.factor}`} tone="amber" />}
            {out?.incident && <SignalRow k="Window" v={`${minToHHMM(out.incident.start_min)}–${minToHHMM(out.incident.end_min)}`} />}
            {b && <SignalRow k="Cost" v={fmt(b.cost, 2)} />}
          </InsightBlock>
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
