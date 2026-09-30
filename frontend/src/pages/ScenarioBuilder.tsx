import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, createScenario, getScenario, listScenarios } from "../api/client";
import type { CreateScenarioRequest, ScenarioSource, ScenarioSummary } from "../api/types";
import RouteMap from "../components/RouteMap";
import { Empty, ErrorState, Loading, MockBadge, QueryState } from "../components/States";
import { useDemoMode } from "../lib/demoMode";
import { fmt, hhmmToMin, minToHHMM } from "../lib/format";
import { isPlainSource, updateSession, useSession } from "../lib/session";
import { notify } from "../lib/toast";

const SOURCES: Array<[ScenarioSource, string]> = [
  ["hyderabad", "Hyderabad (real road graph)"],
  ["synth", "SynthCity (synthetic, planar km)"],
  ["cvrplib", "CVRPLIB instance"],
];

export default function ScenarioBuilder() {
  const demo = useDemoMode();
  const nav = useNavigate();
  const qc = useQueryClient();
  const session = useSession();
  const [form, setForm] = useState({ name: "Hyderabad demo", source: "hyderabad" as ScenarioSource, n: 60, K: 6, Q: 100, seed: 7, depart: "17:30" });
  const [formError, setFormError] = useState<ApiError | null>(null);

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

  const pickScenario = (s: ScenarioSummary) => updateSession({ scenarioId: s.id, scenarioSource: s.source });

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

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <div className="space-y-4">
        <div className="card space-y-3">
          <h1 className="page-title">Scenario Builder</h1>
          {demo && <div className="rounded bg-fuchsia-50 p-2 text-xs text-fuchsia-800">Demo mode: creating returns the pre-exported demo scenario.</div>}
          <div>
            <label className="label">Name</label>
            <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div>
            <label className="label">Source</label>
            <select className="input" value={form.source} onChange={(e) => set("source", e.target.value as ScenarioSource)}>
              {SOURCES.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="label">n customers</label>
              <input type="number" min={1} className="input" value={form.n} onChange={(e) => set("n", Number(e.target.value))} />
            </div>
            <div>
              <label className="label">K vehicles</label>
              <input type="number" min={1} className="input" value={form.K} onChange={(e) => set("K", Number(e.target.value))} />
            </div>
            <div>
              <label className="label">Q capacity</label>
              <input type="number" min={1} className="input" value={form.Q} onChange={(e) => set("Q", Number(e.target.value))} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="label">Seed</label>
              <input type="number" className="input" value={form.seed} onChange={(e) => set("seed", Number(e.target.value))} />
            </div>
            <div>
              <label className="label">Departure</label>
              <input type="time" className="input" value={form.depart} onChange={(e) => set("depart", e.target.value || "00:00")} />
              <div className="mt-1 text-xs text-slate-400">τ₀ = {hhmmToMin(form.depart)} min</div>
            </div>
          </div>
          {clientErrors.length > 0 && <ul className="text-xs text-red-600">{clientErrors.map((m) => <li key={m}>{m}</li>)}</ul>}
          {formError && (
            <div className="rounded-md border border-red-300 bg-red-50 p-2 text-sm text-red-800" role="alert">
              <div className="font-semibold">
                {formError.status === 422 ? "Infeasible scenario" : "Could not create scenario"} ({formError.code})
              </div>
              <div>{formError.message}</div>
              {formError.status === 422 && <div className="mt-1 text-xs">Fix: increase K or Q, reduce n, or check that every customer is reachable.</div>}
            </div>
          )}
          <button className="btn-primary w-full justify-center" disabled={create.isPending || clientErrors.length > 0} onClick={submit}>
            {create.isPending ? "Creating…" : "Create scenario"}
          </button>
        </div>

        <div className="card">
          <div className="label">Existing scenarios</div>
          <QueryState q={list} isEmpty={(d) => d.length === 0} empty={<Empty title="No scenarios yet" />}>
            {(items) => (
              <ul className="divide-y divide-slate-100 text-sm">
                {items.map((s) => (
                  <li key={s.id} className="flex items-center justify-between gap-2 py-2">
                    <div>
                      <div className="font-medium">
                        {s.name} <MockBadge text={s.id} />
                      </div>
                      <div className="text-xs text-slate-500">
                        {s.source} · n={s.n_customers} · K={s.K} · Q={s.Q} · {minToHHMM(s.tau0)}
                      </div>
                    </div>
                    <button className={session.scenarioId === s.id ? "btn-primary" : "btn-secondary"} onClick={() => pickScenario(s)}>
                      {session.scenarioId === s.id ? "Selected" : "Use"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </QueryState>
        </div>
      </div>

      <div className="space-y-4">
        <div className="card">
          <div className="mb-2 flex items-center justify-between">
            <div>
              <div className="label">Live preview</div>
              {preview.data && (
                <div className="text-sm">
                  {preview.data.scenario.name} <MockBadge text={preview.data.scenario.id} /> · {preview.data.customers.length} customers · depart{" "}
                  {minToHHMM(preview.data.scenario.tau0)}
                </div>
              )}
            </div>
            <button className="btn-primary" disabled={!preview.data} onClick={() => nav("/run")}>
              Next: Run optimizer →
            </button>
          </div>
          {!previewId ? (
            <Empty title="No scenario selected">Create one or pick an existing scenario.</Empty>
          ) : preview.isLoading ? (
            <Loading />
          ) : preview.isError ? (
            <ErrorState error={preview.error} onRetry={() => preview.refetch()} />
          ) : preview.data ? (
            <>
              <RouteMap
                customers={preview.data.customers}
                depot={[preview.data.depot.lat, preview.data.depot.lon]}
                plain={isPlainSource(preview.data.scenario.source)}
                height={520}
              />
              {feas && (
                <div className={`mt-2 text-sm ${feas.msgs.length ? "text-red-700" : "text-slate-600"}`}>
                  Total demand {fmt(feas.total)} / fleet capacity K·Q = {fmt(feas.cap)}
                  {feas.msgs.map((m) => (
                    <div key={m} className="font-semibold">
                      ⚠ {m}
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
