import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Layers, Map as MapIcon, PlusCircle } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, createScenario, getScenario, listScenarios } from "../api/client";
import type { CreateScenarioRequest, ScenarioSource, ScenarioSummary } from "../api/types";
import RouteMap from "../components/RouteMap";
import CongestionChart from "../components/charts/CongestionChart";
import { Empty, ErrorState, Loading, MockBadge, QueryState } from "../components/States";
import { DecisionLog, Hi, InsightBlock, InsightsColumn, SignalRow } from "../components/ui/Insights";
import { Chip, Panel, Segmented, Select, TrafficChip } from "../components/ui/primitives";
import { PageShell, SubNav } from "../components/ui/Shell";
import { useDemoMode } from "../lib/demoMode";
import { logEvent } from "../lib/eventLog";
import { fmt, hhmmToMin, minToHHMM } from "../lib/format";
import { isPlainSource, updateSession, useSession } from "../lib/session";
import { notify } from "../lib/toast";
import { loadRatio, peakLabel, TRAFFIC_PROFILE } from "../lib/trafficProfile";

const SOURCES: Array<[ScenarioSource, string]> = [
  ["hyderabad", "Hyderabad (real road graph)"],
  ["synth", "SynthCity (synthetic, planar km)"],
  ["cvrplib", "CVRPLIB instance"],
];

type Section = "existing" | "create" | "preview";

export default function ScenarioBuilder() {
  const demo = useDemoMode();
  const nav = useNavigate();
  const qc = useQueryClient();
  const session = useSession();
  const [form, setForm] = useState({ name: "Hyderabad demo", source: "hyderabad" as ScenarioSource, n: 60, K: 6, Q: 100, seed: 7, depart: "17:30" });
  const [formError, setFormError] = useState<ApiError | null>(null);
  const [section, setSection] = useState<Section>("existing");

  const list = useQuery({ queryKey: ["scenarios"], queryFn: ({ signal }) => listScenarios({ signal }) });
  const previewId = session.scenarioId ?? (demo ? "demo" : null);
  const preview = useQuery({
    queryKey: ["scenario", previewId],
    queryFn: ({ signal }) => getScenario(previewId!, { signal, silent: true }),
    enabled: !!previewId,
  });

  const create = useMutation({
    mutationFn: (req: CreateScenarioRequest) => createScenario(req, { silent: true }),
    onMutate: () => setFormError(null),
    onSuccess: ({ scenario }) => {
      updateSession({ scenarioId: scenario.id, scenarioSource: scenario.source });
      void qc.invalidateQueries({ queryKey: ["scenarios"] });
      notify(`Scenario ${scenario.id} ready`, "success", 3000);
      logEvent("done", `scenario ${scenario.id} ready · n=${scenario.n_customers} K=${scenario.K} Q=${scenario.Q}`);
    },
    onError: (e) => {
      if (e instanceof ApiError) setFormError(e);
      else setFormError(new ApiError(0, "ERROR", String((e as Error).message)));
    },
  });

  const clientErrors: string[] = [];
  if (form.n < 1) clientErrors.push("n must be ≥ 1");
  if (form.K < 1) clientErrors.push("K must be ≥ 1");
  if (form.Q <= 0) clientErrors.push("Q must be > 0");
  if (!form.name.trim()) clientErrors.push("Name is required");

  const submit = () => {
    if (clientErrors.length) return;
    create.mutate({ name: form.name.trim(), source: form.source, n_customers: form.n, K: form.K, Q: form.Q, seed: form.seed, tau0: hhmmToMin(form.depart) });
  };

  const pickScenario = (s: ScenarioSummary) => {
    updateSession({ scenarioId: s.id, scenarioSource: s.source });
    logEvent("info", `scenario ${s.id} selected`);
  };

  // Client-side infeasibility check on the loaded scenario (demand > K·Q, single demand > Q).
  const feas = (() => {
    const d = preview.data;
    if (!d) return null;
    const total = d.customers.reduce((a, c) => a + (c.demand ?? 0), 0);
    const maxD = d.customers.reduce((a, c) => Math.max(a, c.demand ?? 0), 0);
    const cap = d.scenario.K * d.scenario.Q;
    const msgs: string[] = [];
    if (total > cap) msgs.push(`Total demand ${fmt(total)} > K·Q = ${fmt(cap)}. Increase K or Q, or reduce n.`);
    if (maxD > d.scenario.Q) msgs.push(`A single customer demands ${fmt(maxD)} > Q = ${fmt(d.scenario.Q)}. Increase Q.`);
    return { total, cap, msgs };
  })();

  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) => setForm((f) => ({ ...f, [k]: v }));
  const go = (s: Section) => {
    setSection(s);
    document.getElementById(`sc-${s}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  const sc = preview.data?.scenario;
  const slotOptions = TRAFFIC_PROFILE.slot_labels.map((l) => [l, l] as [string, string]);
  const departMin = hhmmToMin(form.depart);
  const eyebrow = sc
    ? `SCENARIO SELECTED · ${sc.name.toUpperCase()} · ${sc.n_customers} CUSTOMERS · ${minToHHMM(sc.tau0)}${peakLabel(sc.tau0) ? ` ${peakLabel(sc.tau0)}` : ""}`
    : "NO SCENARIO SELECTED";

  return (
    <PageShell
      hero={{
        eyebrow,
        eyebrowTone: sc ? "teal" : "amber",
        title: "Choose a city,",
        titleAccent: "set the clock.",
        lead: "Pick a road network and a departure time. The same customers meet very different traffic at 03:00 and at 17:30 (simulated time-of-day profiles).",
        meta: sc ? (
          <span className="flex items-center gap-2">
            scenario · {sc.id} · source {sc.source} <MockBadge text={sc.id} />
          </span>
        ) : undefined,
        actions: (
          <button type="button" className="btn-primary" disabled={!preview.data} onClick={() => nav("/run")}>
            Next: Run optimizer →
          </button>
        ),
      }}
      subnav={
        <SubNav
          title="Scenario"
          active={section}
          onChange={go}
          items={[
            { id: "existing", label: "Scenarios", icon: Layers, count: list.data?.length ?? null },
            { id: "create", label: "New scenario", icon: PlusCircle },
            { id: "preview", label: "Preview map", icon: MapIcon, count: preview.data?.customers.length ?? null },
          ]}
        />
      }
      insights={
        <InsightsColumn>
          <InsightBlock label="Recommended action" tone={feas?.msgs.length ? "amber" : "teal"}>
            {feas?.msgs.length ? (
              feas.msgs.map((m) => <div key={m}>{m}</div>)
            ) : sc ? (
              <>
                <Hi>{sc.name}</Hi> is ready: total demand {fmt(feas?.total)} fits fleet capacity K·Q = {fmt(feas?.cap)}. Next, run the optimizer.
              </>
            ) : (
              "Pick an existing scenario or create one."
            )}
          </InsightBlock>
          {sc && (
            <InsightBlock label="Signal summary">
              <SignalRow k="Customers" v={fmt(sc.n_customers)} />
              <SignalRow k="Vehicles K · capacity Q" v={`${sc.K} · ${sc.Q}`} />
              <SignalRow k="Departure" v={minToHHMM(sc.tau0)} />
              <SignalRow k="Arterial ρ at departure" v={loadRatio(sc.tau0, 0).toFixed(2)} tone={peakLabel(sc.tau0) === "PEAK" ? "amber" : undefined} />
              {feas && <SignalRow k="Demand / capacity" v={`${fmt(feas.total)} / ${fmt(feas.cap)}`} tone={feas.msgs.length ? "red" : "lime"} />}
            </InsightBlock>
          )}
          <DecisionLog />
        </InsightsColumn>
      }
    >
      <div className="grid gap-3 min-[1300px]:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        <div className="space-y-3">
          <Panel id="sc-existing" title="Scenarios" bodyClassName="px-3 pb-3">
            {demo && <div className="mb-2 px-1 text-[11.5px] text-amber">Demo mode: creating returns the pre-exported demo scenario.</div>}
            <QueryState q={list} isEmpty={(d) => d.length === 0} empty={<Empty title="No scenarios yet" />}>
              {(items) => (
                <ul className="max-h-[300px] space-y-1.5 overflow-y-auto pr-1">
                  {items.map((s) => {
                    const on = session.scenarioId === s.id || (!session.scenarioId && demo && previewId === "demo" && sc?.id === s.id);
                    return (
                      <li key={s.id}>
                        <button
                          type="button"
                          aria-pressed={on}
                          onClick={() => pickScenario(s)}
                          className="relative w-full rounded-lg px-3 py-2.5 text-left transition"
                          style={
                            on
                              ? { background: "rgba(79,227,209,.06)", border: "1px solid rgba(79,227,209,.45)", boxShadow: "0 0 18px -4px rgba(79,227,209,.45)" }
                              : { background: "rgba(255,255,255,.015)", border: "1px solid var(--line)" }
                          }
                        >
                          <div className="flex items-center gap-2 text-[13px] font-medium text-txt">
                            {s.name}
                            <MockBadge text={s.id} />
                            {on && <Check size={14} strokeWidth={1.5} className="ml-auto text-teal" />}
                          </div>
                          <div className="mt-1 font-mono text-[10.5px] text-mute">
                            {s.source} · n={s.n_customers} · K={s.K} · Q={s.Q} · {minToHHMM(s.tau0)}
                          </div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </QueryState>
          </Panel>
          <Panel id="sc-create" title="New scenario" bodyClassName="px-4 pb-4 space-y-3">
            <div>
              <label className="label" htmlFor="sc-name">
                Name
              </label>
              <input id="sc-name" className="input" value={form.name} onChange={(e) => set("name", e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="sc-source">
                Source
              </label>
              <Select id="sc-source" value={form.source} onChange={(e) => set("source", e.target.value as ScenarioSource)}>
                {SOURCES.map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </Select>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {(
                [
                  ["n", "n customers"],
                  ["K", "K vehicles"],
                  ["Q", "Q capacity"],
                ] as const
              ).map(([k, l]) => (
                <div key={k}>
                  <label className="label" htmlFor={`sc-${k}`}>
                    {l}
                  </label>
                  <input id={`sc-${k}`} type="number" min={1} className="input num" value={form[k]} onChange={(e) => set(k, Number(e.target.value))} />
                </div>
              ))}
            </div>
            <div>
              <div className="label">Departure</div>
              <Segmented ariaLabel="Departure time slot" size="sm" value={slotOptions.some(([v]) => v === form.depart) ? form.depart : ""} onChange={(v) => set("depart", v)} options={slotOptions} />
              <div className="mt-2 flex items-center gap-2">
                <input aria-label="Custom departure time" type="time" className="input num w-[110px]" value={form.depart} onChange={(e) => set("depart", e.target.value || "00:00")} />
                <span className="font-mono text-[10.5px] text-mute">
                  τ₀ = {departMin} min · ρ {loadRatio(departMin, 0).toFixed(2)}
                  {peakLabel(departMin) ? ` · ${peakLabel(departMin)}` : ""}
                </span>
              </div>
            </div>
            <div>
              <label className="label" htmlFor="sc-seed">
                Seed
              </label>
              <input id="sc-seed" type="number" className="input num" value={form.seed} onChange={(e) => set("seed", Number(e.target.value))} />
            </div>
            {clientErrors.length > 0 && (
              <ul className="text-[12px] text-danger">
                {clientErrors.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            )}
            {formError && (
              <div className="rounded-lg px-3 py-2 text-[12.5px] text-danger" role="alert" style={{ background: "rgba(255,122,122,.05)", border: "1px solid rgba(255,122,122,.3)" }}>
                <div className="font-semibold">
                  {formError.status === 422 ? "Infeasible scenario" : "Could not create scenario"} ({formError.code})
                </div>
                <div>{formError.message}</div>
                {formError.status === 422 && <div className="mt-1 text-[12px]">Fix: increase K or Q, reduce n, or check that every customer is reachable.</div>}
              </div>
            )}
            <button type="button" className="btn-secondary w-full" disabled={create.isPending || clientErrors.length > 0} onClick={submit}>
              {create.isPending ? "Creating…" : "Create scenario"}
            </button>
          </Panel>
        </div>

        <div className="space-y-3">
          <Panel
            id="sc-preview"
            overlay
            title="Preview"
            chips={
              preview.data ? (
                <>
                  <Chip tone="teal">{preview.data.customers.length} customers</Chip>
                  <TrafficChip at={preview.data.scenario.tau0} />
                </>
              ) : undefined
            }
            meta={preview.data?.scenario.name}
          >
            {!previewId ? (
              <div className="p-4 pt-12">
                <Empty title="No scenario selected">Create one or pick an existing scenario.</Empty>
              </div>
            ) : preview.isLoading ? (
              <div className="pt-10">
                <Loading />
              </div>
            ) : preview.isError ? (
              <div className="p-4 pt-12">
                <ErrorState error={preview.error} onRetry={() => preview.refetch()} />
              </div>
            ) : preview.data ? (
              <RouteMap customers={preview.data.customers} depot={[preview.data.depot.lat, preview.data.depot.lon]} plain={isPlainSource(preview.data.scenario.source)} height={400} />
            ) : null}
            {feas && (
              <div className="px-4 py-2.5 font-mono text-[11px]" style={{ borderTop: "1px solid var(--line)", color: feas.msgs.length ? "var(--red)" : "var(--mute)" }}>
                Total demand {fmt(feas.total)} / fleet capacity K·Q = {fmt(feas.cap)}
                {feas.msgs.map((m) => (
                  <div key={m} className="font-semibold">
                    ⚠ {m}
                  </div>
                ))}
              </div>
            )}
          </Panel>
          <Panel title="Network congestion · 24 h" chips={<Chip>simulated profile</Chip>} meta={`marker = ${sc ? "scenario" : "chosen"} departure`} bodyClassName="px-2 pb-2">
            <CongestionChart departMin={sc ? sc.tau0 : departMin} height={180} />
          </Panel>
        </div>
      </div>
    </PageShell>
  );
}
