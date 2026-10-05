import { useMutation, useQuery } from "@tanstack/react-query";
import { Columns2, Table2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fleetCompare, getFleetDemo, getScenario } from "../api/client";
import type { FleetCompareResponse, FleetMode, FleetResult } from "../types/result";
import RouteMap from "../components/RouteMap";
import { Empty, ErrorState, Loading, MockBadge } from "../components/States";
import { DecisionLog, Hi, InsightBlock, InsightsColumn, SignalRow } from "../components/ui/Insights";
import { Chip, DataTable, FieldLabel, KpiCard, Panel, Slider } from "../components/ui/primitives";
import { PageShell, SubNav } from "../components/ui/Shell";
import { vcColor } from "../lib/colors";
import { useDemoMode } from "../lib/demoMode";
import { logEvent } from "../lib/eventLog";
import { algoLabel } from "../lib/labels";
import { fmt, minToHHMM } from "../lib/format";
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

function pct(a: number, b: number): number | null {
  if (!Number.isFinite(a) || !Number.isFinite(b) || a === 0) return null;
  return ((b - a) / Math.abs(a)) * 100;
}

function pctChange(a: number, b: number): string {
  const p = pct(a, b);
  return p == null ? "–" : `${p > 0 ? "+" : ""}${p.toFixed(1)}%`;
}

type Section = "maps" | "table";

function ModeMap({ mode, r, plain, customers, depot }: { mode: FleetMode; r: FleetResult | undefined; plain: boolean; customers?: Parameters<typeof RouteMap>[0]["customers"]; depot?: [number, number] | null }) {
  return (
    <Panel
      overlay
      title={MODE_LABEL[mode]}
      chips={
        r ? (
          <>
            <Chip tone={mode === "system_opt" ? "teal" : "amber"}>max V/C {fmt(r.max_vc, 2)}</Chip>
            <MockBadge text={r.job_id} />
          </>
        ) : undefined
      }
    >
      {!r ? (
        <div className="p-4 pt-12">
          <Empty title={`No ${mode} result`} />
        </div>
      ) : (
        <RouteMap routes={[]} edgeFlows={r.edge_flows} showFlows flowGlow customers={customers} depot={depot ?? r.routes[0]?.geometry[0] ?? null} plain={plain} height={360} />
      )}
    </Panel>
  );
}

export default function FleetImpact() {
  const demo = useDemoMode();
  const session = useSession();
  const [S, setS] = useState(25);
  const [section, setSection] = useState<Section>("maps");
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
    onMutate: () => logEvent("run", `fleet compare · S = ${S} · naive / user_eq / system_opt`),
    onSuccess: () => logEvent("done", `fleet compare finished · S = ${S}`),
  });

  useEffect(() => {
    if (demo && demoQ.data) setS(demoQ.data.S);
  }, [demo, demoQ.data]);

  const data: FleetCompareResponse | undefined = demo ? demoQ.data && { modes: demoQ.data.modes } : live.data;
  const plain = isPlainSource(scenario.data?.scenario.source ?? session.scenarioSource);
  const depot: [number, number] | null = scenario.data ? [scenario.data.depot.lat, scenario.data.depot.lon] : null;
  const modes = data?.modes ?? {};
  const present = (Object.keys(MODE_LABEL) as FleetMode[]).filter((m) => modes[m]);
  const n = modes.naive;
  const so = modes.system_opt;
  const sc = scenario.data?.scenario;

  const hero = {
    title: "Don't just avoid congestion —",
    titleAccent: "stop creating it.",
    lead: "Naive routing sends every van down the fastest corridor. System-optimal routing prices each van's marginal cost, so the fleet spreads its own load. Traffic is simulated.",
  };

  if (!demo && !scenarioId) {
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

  const ext = n && so ? pct(n.externality_veh_h, so.externality_veh_h) : null;
  const eyebrow = n && so ? `FLEET COMPARE · S = ${S} · ${sc ? `${sc.name.toUpperCase()} · ${minToHHMM(sc.tau0)}` : "SIMULATED TRAFFIC"}` : `FLEET IMPACT · S = ${S}`;
  const pending = demo ? demoQ.isLoading : live.isPending;

  const controls = (
    <Panel title="Platform scale factor" meta="modelling assumption" bodyClassName="px-4 pb-4">
      <div className="flex flex-wrap items-end gap-4">
        <div className="min-w-[220px] flex-1">
          <FieldLabel right={`S = ${S}`}>S (vehicle-equivalents per route)</FieldLabel>
          <Slider ariaLabel="Scale factor S" min={1} max={100} step={1} value={S} disabled={demo} onChange={setS} />
          {demo && <div className="mt-1 text-[11.5px] text-mute">Demo mode shows the precomputed S only.</div>}
        </div>
        {!demo && (
          <button type="button" className="btn-primary" disabled={live.isPending || !scenario.data} onClick={() => live.mutate()}>
            {live.isPending ? "Comparing…" : "Compare modes →"}
          </button>
        )}
      </div>
    </Panel>
  );

  let main;
  if (pending)
    main = (
      <div className="space-y-3">
        {controls}
        <Loading label="Computing fleet comparison…" />
      </div>
    );
  else if (demo && demoQ.isError) main = <ErrorState error={demoQ.error} onRetry={() => demoQ.refetch()} />;
  else if (!demo && live.isError) main = <ErrorState error={live.error} onRetry={() => live.mutate()} />;
  else if (!data)
    main = (
      <div className="space-y-3">
        {controls}
        <Empty title="No comparison yet">Set S and press “Compare modes”.</Empty>
      </div>
    );
  else if (present.length === 0) main = <Empty title="Response contained no modes" />;
  else if (section === "maps") {
    main = (
      <div className="space-y-3">
        {n && so && (
          <div className="grid gap-3 sm:grid-cols-3">
            {(
              [
                ["Externality", (r: FleetResult) => r.externality_veh_h, "veh-h", 1],
                ["Edges over capacity", (r: FleetResult) => r.edges_over_capacity, "", 0],
                ["Congestion delay", (r: FleetResult) => r.kpis.congestion_delay_min, "min", 1],
              ] as const
            ).map(([label, get, unit, d]) => {
              const p = pct(get(n), get(so));
              return (
                <KpiCard
                  key={label}
                  label={`${label} · system-optimal`}
                  value={fmt(get(so), d)}
                  unit={unit}
                  delta={p == null ? undefined : { text: `${p > 0 ? "+" : ""}${p.toFixed(1)}%`, tone: p < 0 ? "lime" : p > 0 ? "red" : "plain" }}
                  context={`vs naive ${fmt(get(n), d)}`}
                />
              );
            })}
          </div>
        )}
        <div className="grid gap-3 min-[1300px]:grid-cols-2">
          <ModeMap mode="naive" r={modes.naive} plain={plain} customers={scenario.data?.customers} depot={depot} />
          <ModeMap mode="system_opt" r={modes.system_opt} plain={plain} customers={scenario.data?.customers} depot={depot} />
        </div>
        <div className="flex flex-wrap items-center gap-3 font-mono text-[10px] text-mute">
          Edge colour by V/C:
          {[0.5, 0.8, 1.0, 1.2, 1.4].map((v) => (
            <span key={v} className="flex items-center gap-1">
              <span className="inline-block h-[3px] w-6 rounded" style={{ background: vcColor(v) }} />
              {v}
            </span>
          ))}
          · width and glow = fleet flow
        </div>
        {controls}
      </div>
    );
  } else {
    main = (
      <div className="space-y-3">
        <Panel title="All modes" meta="system_opt vs naive = relative change" bodyClassName="px-4 pb-3">
          <DataTable>
            <thead>
              <tr>
                <th>Metric</th>
                {present.map((m) => (
                  <th key={m}>{m}</th>
                ))}
                {n && so && <th>system_opt vs naive</th>}
              </tr>
            </thead>
            <tbody>
              {METRICS.map(([k, label, unit, get]) => {
                const p = n && so ? pct(get(n), get(so)) : null;
                return (
                  <tr key={String(k)}>
                    <td>
                      {label} {unit && <span className="text-lbl">({unit})</span>}
                    </td>
                    {present.map((m) => (
                      <td key={m} className="n">
                        {fmt(get(modes[m]!), 2)}
                      </td>
                    ))}
                    {n && so && (
                      <td className="n" style={{ color: p == null ? undefined : p < 0 ? "var(--lime)" : p > 0 ? "var(--red)" : undefined }}>
                        {pctChange(get(n), get(so))}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </DataTable>
        </Panel>
        {controls}
      </div>
    );
  }

  return (
    <PageShell
      hero={{
        eyebrow,
        ...hero,
        meta: n ? `planner · ${algoLabel(n.algorithm)} · weights ${n.weights.wT} / ${n.weights.wD} / ${n.weights.wC} / ${n.weights.wE} · seed ${n.seed}` : undefined,
        actions: (
          <>
            <Link to="/results" className="btn-secondary">
              ← Results
            </Link>
            <Link to="/path" className="btn-primary">
              Shortest path →
            </Link>
          </>
        ),
      }}
      subnav={
        <SubNav
          title="Fleet impact"
          active={section}
          onChange={setSection}
          items={[
            { id: "maps", label: "Twin maps", icon: Columns2, count: present.length || null },
            { id: "table", label: "All modes", icon: Table2, count: present.length ? METRICS.length : null },
          ]}
        />
      }
      insights={
        <InsightsColumn>
          <InsightBlock label="Recommended action" tone="teal">
            {n && so && ext != null ? (
              <>
                System-optimal routing changes the fleet's externality by <Hi tone={ext < 0 ? "lime" : "amber"}>{`${ext > 0 ? "+" : ""}${ext.toFixed(1)}%`}</Hi> vs naive,
                with max V/C <Hi>{fmt(so.max_vc, 2)}</Hi> instead of {fmt(n.max_vc, 2)} (simulated traffic).
              </>
            ) : (
              "Run the comparison to see how much delay the fleet adds to everyone else."
            )}
          </InsightBlock>
          <InsightBlock label="The S assumption" tone="amber">
            <Hi tone="amber">S = {S}</Hi> is the platform scale factor, a modelling assumption: each planned route is treated as S vehicles on the road so the
            fleet's own flow is visible in the simulated traffic (load-ratio profiles + BPR), not measured.
          </InsightBlock>
          {n && so && (
            <InsightBlock label="Signal summary">
              <SignalRow k="Externality naive" v={`${fmt(n.externality_veh_h, 1)} veh-h`} tone="amber" />
              <SignalRow k="Externality system-opt" v={`${fmt(so.externality_veh_h, 1)} veh-h`} tone="teal" />
              <SignalRow k="Corridors used" v={`${fmt(n.corridors_used)} → ${fmt(so.corridors_used)}`} />
              <SignalRow k="CO₂ (illustrative)" v={`${fmt(n.kpis.co2_kg, 1)} → ${fmt(so.kpis.co2_kg, 1)} kg`} />
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
