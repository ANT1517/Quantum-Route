import { useQuery } from "@tanstack/react-query";
import { Activity, Cpu, SlidersHorizontal, Users } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, cancelJob, createJob, getScenario } from "../api/client";
import type { Algorithm, Weights } from "../api/types";
import type { FleetMode } from "../types/result";
import ConvergenceChart from "../components/ConvergenceChart";
import { Empty, MockBadge } from "../components/States";
import { DecisionLog, Hi, InsightBlock, InsightsColumn, SignalRow } from "../components/ui/Insights";
import { Checkbox, Chip, FieldLabel, InfoTip, Panel, Segmented, Select, Slider } from "../components/ui/primitives";
import { PageShell, SubNav } from "../components/ui/Shell";
import { useJobProgress } from "../hooks/useJobProgress";
import { algoColor } from "../lib/colors";
import { useDemoMode } from "../lib/demoMode";
import { setEngine } from "../lib/engine";
import { logEvent } from "../lib/eventLog";
import { fmt, minToHHMM } from "../lib/format";
import { updateSession, useSession } from "../lib/session";
import { loadRatio, peakLabel } from "../lib/trafficProfile";

const ALGOS: Array<[Algorithm, string]> = [
  ["qpso", "QPSO-noQUBO (tuned) · default engine"],
  ["pso", "PSO"],
  ["ga", "GA"],
  ["sa", "Simulated annealing"],
  ["ortools", "OR-Tools (industry reference)"],
];

const PRESETS: Array<[string, Weights]> = [
  ["Balanced", { wT: 0.5, wD: 0.2, wC: 0.2, wE: 0.1 }],
  ["Fastest", { wT: 1, wD: 0, wC: 0, wE: 0 }],
  ["Greenest", { wT: 0.2, wD: 0, wC: 0, wE: 0.8 }],
  ["Least congestion", { wT: 0.3, wD: 0, wC: 0.7, wE: 0 }],
];

const WEIGHT_LABELS: Record<keyof Weights, string> = { wT: "Time wT", wD: "Distance wD", wC: "Congestion wC", wE: "CO₂ wE" };

const QUBO_TIP = "Validated quantum-ready module; on classical hardware it is slower than 2-opt — see Quantum Lab.";

/** Set one weight and rescale the others so the four sum to 1. */
function renormalise(w: Weights, key: keyof Weights, value: number): Weights {
  const v = Math.max(0, Math.min(1, value));
  const others = (Object.keys(w) as Array<keyof Weights>).filter((k) => k !== key);
  const rest = others.reduce((a, k) => a + w[k], 0);
  const out = { ...w, [key]: v } as Weights;
  for (const k of others) out[k] = rest > 1e-12 ? (w[k] * (1 - v)) / rest : (1 - v) / others.length;
  // round to 3 dp and push rounding residue into the edited key
  (Object.keys(out) as Array<keyof Weights>).forEach((k) => (out[k] = Math.round(out[k] * 1000) / 1000));
  const sum = out.wT + out.wD + out.wC + out.wE;
  out[key] = Math.round((out[key] + (1 - sum)) * 1000) / 1000;
  return out;
}

type Section = "objective" | "swarm" | "engine" | "live";

export default function RunOptimizer() {
  const demo = useDemoMode();
  const session = useSession();
  const [params] = useSearchParams();
  const [algorithm, setAlgorithm] = useState<Algorithm>("qpso");
  const [weights, setWeights] = useState<Weights>(PRESETS[0][1]);
  const [N, setN] = useState(40);
  const [iters, setIters] = useState(150);
  const [alphaStart, setAlphaStart] = useState(1.0);
  const [alphaEnd, setAlphaEnd] = useState(0.5);
  // Default = the shipped engine QPSO-noQUBO (tuned): fixed alpha 0.3, chosen on CVRPLIB tuning instances (D54/D59).
  // A linear alpha schedule is sent only when the user asks for it.
  const [customAlpha, setCustomAlpha] = useState(false);
  // D60: optional QUBO sub-route slot (classical sampler); off by default
  const [quboSlot, setQuboSlot] = useState(false);
  const [seed, setSeed] = useState(7);
  const [fleetMode, setFleetMode] = useState<FleetMode>("naive");
  const [jobId, setJobId] = useState<string | null>(null);
  const [startErr, setStartErr] = useState<ApiError | null>(null);
  const [starting, setStarting] = useState(false);
  const [section, setSection] = useState<Section>("objective");
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [endedAt, setEndedAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const autoStarted = useRef(false);
  const loggedDone = useRef<string | null>(null);

  const scenarioId = session.scenarioId ?? (demo ? "demo" : null);
  const scenario = useQuery({
    queryKey: ["scenario", scenarioId],
    queryFn: ({ signal }) => getScenario(scenarioId!, { signal, silent: true }),
    enabled: !!scenarioId,
  });

  const budgetEvals = N * iters;
  const prog = useJobProgress(jobId, budgetEvals);
  const running = !!jobId && !prog.done;

  // engine card in the sub-nav reflects the form (QUBO checkbox, custom alpha)
  useEffect(() => {
    if (algorithm === "qpso") setEngine({ algorithm: "qpso_noqubo_tuned", qubo: quboSlot, alpha: customAlpha ? { start: alphaStart, end: alphaEnd } : null });
    else setEngine({ algorithm, qubo: false, alpha: null });
  }, [algorithm, quboSlot, customAlpha, alphaStart, alphaEnd]);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setNow(Date.now()), 200);
    return () => clearInterval(t);
  }, [running]);

  useEffect(() => {
    if (!jobId || !prog.done || loggedDone.current === jobId) return;
    loggedDone.current = jobId;
    setEndedAt(Date.now());
    const last = prog.points[prog.points.length - 1];
    if (prog.status === "COMPLETED" || prog.status === "COMPLETED_PARTIAL") {
      logEvent("done", `job ${jobId} ${prog.status}${last ? ` · best F ${last.best_F.toPrecision(4)}` : ""}`);
    } else {
      logEvent("warn", `job ${jobId} ${prog.status ?? "ended"}`);
    }
  }, [jobId, prog.done, prog.status, prog.points]);

  const start = async () => {
    const sid = scenario.data?.scenario.id ?? scenarioId;
    if (!sid) return;
    setStartErr(null);
    setStarting(true);
    try {
      const p: Record<string, unknown> = { N, iterations: iters };
      if (algorithm === "qpso" && quboSlot) p.qubo_slot = true;
      if (algorithm === "qpso" && customAlpha) {
        p.alpha_start = alphaStart;
        p.alpha_end = alphaEnd;
      }
      const res = await createJob(
        { scenario_id: sid, algorithm, weights, params: p, seed, budget: { evals: budgetEvals, time_s: null }, fleet_mode: fleetMode },
        { silent: true },
      );
      setJobId(null);
      setTimeout(() => setJobId(res.job_id), 0);
      setStartedAt(Date.now());
      setEndedAt(null);
      setSection("live");
      document.getElementById("run-live")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      logEvent("run", `job ${res.job_id} queued · ${algorithm}${algorithm === "qpso" && quboSlot ? " + QUBO slot" : ""} · seed ${seed} · ${budgetEvals.toLocaleString()} evals`);
      updateSession({ lastJobId: res.job_id });
    } catch (e) {
      setStartErr(e instanceof ApiError ? e : new ApiError(0, "ERROR", String((e as Error).message)));
    } finally {
      setStarting(false);
    }
  };

  useEffect(() => {
    if (params.get("autostart") === "1" && !autoStarted.current && scenario.data) {
      autoStarted.current = true;
      void start();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, scenario.data]);

  const cancel = async () => {
    if (!jobId) return;
    try {
      await cancelJob(jobId);
    } catch {
      /* toast already shown */
    }
  };

  const hero = {
    title: "Configure the swarm,",
    titleAccent: "then let it search.",
    lead: "Set the objective weights and the search budget, then watch the best plan found so far improve, evaluation by evaluation.",
  };

  if (!scenarioId) {
    return (
      <PageShell hero={{ eyebrow: "NO SCENARIO SELECTED", ...hero }}>
        <Empty title="No scenario selected">
          <Link className="text-teal underline" to="/scenario">
            Create or pick a scenario first
          </Link>
        </Empty>
      </PageShell>
    );
  }

  const sc = scenario.data?.scenario;
  const pct = prog.progress != null ? Math.round(prog.progress * 100) : null;
  const last = prog.points[prog.points.length - 1];
  const elapsed = startedAt != null ? ((endedAt ?? now) - startedAt) / 1000 : null;
  const wSum = weights.wT + weights.wD + weights.wC + weights.wE;
  const eyebrow = running
    ? `SEARCHING · ${last ? `ITER ${last.iter} · ${last.evals.toLocaleString()} EVALS` : (prog.status ?? "QUEUED")}`
    : sc
      ? `SCENARIO ${sc.name.toUpperCase()} · ${sc.n_customers} CUSTOMERS · DEPART ${minToHHMM(sc.tau0)}${peakLabel(sc.tau0) ? ` ${peakLabel(sc.tau0)}` : ""}`
      : "LOADING SCENARIO";

  const go = (s: Section) => {
    setSection(s);
    document.getElementById(`run-${s}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  const statusTone = prog.status === "FAILED" ? "red" : prog.done ? "teal" : "amber";

  return (
    <PageShell
      hero={{
        eyebrow,
        ...hero,
        meta: (
          <span className="flex items-center gap-2">
            scenario ·{" "}
            {scenario.isLoading ? "loading…" : sc ? `${sc.name} (${sc.id})` : <span className="text-danger">could not load ({scenarioId})</span>}
            {sc && <MockBadge text={sc.id} />}
          </span>
        ),
        actions: (
          <>
            <button type="button" className="btn-secondary" disabled={!running} onClick={cancel}>
              Cancel
            </button>
            <button type="button" className="btn-primary" disabled={running || starting || !scenario.data} onClick={start}>
              {starting ? "Starting…" : running ? "Running…" : "Run optimizer →"}
            </button>
          </>
        ),
      }}
      subnav={
        <SubNav
          title="Run"
          active={section}
          onChange={go}
          items={[
            { id: "objective", label: "Objective", icon: SlidersHorizontal },
            { id: "swarm", label: "Swarm & budget", icon: Users },
            { id: "engine", label: "Engine options", icon: Cpu },
            { id: "live", label: "Live convergence", icon: Activity, count: prog.points.length || null },
          ]}
        />
      }
      insights={
        <InsightsColumn>
          <InsightBlock label="Recommended action">
            The default engine is <Hi>QPSO-noQUBO (tuned)</Hi>: α = 0.3 fixed, tuned on CVRPLIB tuning instances only. Leave the{" "}
            <Hi tone="amber">QUBO slot</Hi> off for speed; it is a validated, classical-sampler module, slower than 2-opt on classical hardware.
          </InsightBlock>
          <InsightBlock label="Signal summary">
            <SignalRow k="Σ weights" v={wSum.toFixed(3)} tone={Math.abs(wSum - 1) < 1e-6 ? "lime" : "red"} />
            <SignalRow k="Budget" v={`${budgetEvals.toLocaleString()} evals`} />
            {sc && <SignalRow k="Customers · K · Q" v={`${sc.n_customers} · ${sc.K} · ${sc.Q}`} />}
            {sc && <SignalRow k={`Arterial ρ at ${minToHHMM(sc.tau0)}`} v={loadRatio(sc.tau0, 0).toFixed(2)} tone={peakLabel(sc.tau0) === "PEAK" ? "amber" : undefined} />}
            <SignalRow k="Fleet mode" v={fleetMode} />
          </InsightBlock>
          <DecisionLog />
        </InsightsColumn>
      }
    >
      <div className="grid gap-3 min-[1300px]:grid-cols-[minmax(0,330px)_minmax(0,1fr)]">
        <div className="space-y-3">
          <Panel id="run-objective" title="Objective weights" meta={<span className={Math.abs(wSum - 1) < 1e-6 ? "text-lime" : "text-danger"}>Σ = {wSum.toFixed(3)}</span>} bodyClassName="px-4 pb-4">
            <div className="mb-3 flex flex-wrap gap-1.5">
              {PRESETS.map(([name, w]) => {
                const on = (Object.keys(w) as Array<keyof Weights>).every((k) => Math.abs(w[k] - weights[k]) < 1e-9);
                return (
                  <button key={name} type="button" className={`btn-secondary btn-sm ${on ? "!border-[rgba(79,227,209,.45)] !text-teal" : ""}`} aria-pressed={on} onClick={() => setWeights(w)}>
                    {name}
                  </button>
                );
              })}
            </div>
            <div className="space-y-2">
              {(Object.keys(WEIGHT_LABELS) as Array<keyof Weights>).map((k) => (
                <div key={k}>
                  <FieldLabel right={weights[k].toFixed(3)}>{WEIGHT_LABELS[k]}</FieldLabel>
                  <Slider
                    ariaLabel={WEIGHT_LABELS[k]}
                    min={0}
                    max={1}
                    step={0.01}
                    value={weights[k]}
                    fill={k === "wC" ? "var(--amber)" : undefined}
                    onChange={(v) => setWeights((w) => renormalise(w, k, v))}
                  />
                </div>
              ))}
            </div>
          </Panel>
          <Panel id="run-swarm" title="Swarm & budget" meta={`${budgetEvals.toLocaleString()} evals = N × iterations`} bodyClassName="px-4 pb-4">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="label" htmlFor="run-algo">
                  Algorithm
                </label>
                <Select id="run-algo" value={algorithm} onChange={(e) => setAlgorithm(e.target.value as Algorithm)}>
                  {ALGOS.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="label" htmlFor="run-seed">
                  Seed
                </label>
                <input id="run-seed" type="number" className="input num" value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
              </div>
              <div>
                <label className="label" htmlFor="run-n">
                  Swarm / pop N
                </label>
                <input id="run-n" type="number" min={2} className="input num" value={N} onChange={(e) => setN(Math.max(2, Number(e.target.value)))} />
              </div>
              <div>
                <label className="label" htmlFor="run-iters">
                  Iterations
                </label>
                <input id="run-iters" type="number" min={1} className="input num" value={iters} onChange={(e) => setIters(Math.max(1, Number(e.target.value)))} />
              </div>
            </div>
            <div className="mt-3">
              <div className="label">Fleet mode</div>
              <Segmented
                ariaLabel="Fleet mode"
                size="sm"
                value={fleetMode}
                onChange={setFleetMode}
                options={[
                  ["naive", "naive"],
                  ["user_eq", "user_eq"],
                  ["system_opt", "system_opt"],
                ]}
              />
            </div>
          </Panel>
          <Panel id="run-engine" title="Engine options" bodyClassName="px-4 pb-4 space-y-3">
            {algorithm === "qpso" ? (
              <>
                <Checkbox checked={customAlpha} onChange={setCustomAlpha}>
                  Custom α schedule (linear)
                </Checkbox>
                {!customAlpha && <div className="text-[12px] text-mute">α = 0.3 fixed — QPSO-noQUBO (tuned), tuned on CVRPLIB tuning instances only.</div>}
                {customAlpha && (
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="label" htmlFor="run-a0">
                        α start
                      </label>
                      <input id="run-a0" type="number" step={0.05} className="input num" value={alphaStart} onChange={(e) => setAlphaStart(Number(e.target.value))} />
                    </div>
                    <div>
                      <label className="label" htmlFor="run-a1">
                        α end
                      </label>
                      <input id="run-a1" type="number" step={0.05} className="input num" value={alphaEnd} onChange={(e) => setAlphaEnd(Number(e.target.value))} />
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  <Checkbox checked={quboSlot} onChange={setQuboSlot} title={QUBO_TIP}>
                    Quantum QUBO slot (classical sampler; slower)
                  </Checkbox>
                  <InfoTip text={QUBO_TIP} label="QUBO slot" />
                </div>
              </>
            ) : (
              <div className="text-[12px] text-mute">Engine options apply to QPSO only.</div>
            )}
          </Panel>
          {startErr && (
            <div className="rounded-lg px-3 py-2 text-[12.5px] text-danger" role="alert" style={{ background: "rgba(255,122,122,.05)", border: "1px solid rgba(255,122,122,.3)" }}>
              <b>{startErr.code}</b>: {startErr.message}
              {startErr.status === 429 && <div className="text-[12px]">Two jobs are already running; wait or cancel one.</div>}
            </div>
          )}
          <button type="button" className="btn-primary h-11 w-full text-[14px]" disabled={running || starting || !scenario.data} onClick={start}>
            {starting ? "Starting…" : running ? "Running…" : "Run optimizer →"}
          </button>
        </div>

        <Panel
          id="run-live"
          title="Live convergence"
          chips={
            jobId ? (
              <>
                <Chip tone={statusTone}>{prog.status ?? "…"}</Chip>
                <MockBadge text={jobId} />
              </>
            ) : undefined
          }
          meta={jobId ? `job ${jobId} · via ${prog.transport}` : "best F vs evaluations"}
          className="self-start"
          bodyClassName="px-2 pb-3"
        >
          {jobId && !prog.done && (
            <div className="mx-2 mb-2 h-[3px] overflow-hidden rounded" style={{ background: "var(--line-2)" }}>
              <div className="h-full rounded transition-all" style={{ width: `${pct ?? 5}%`, background: "var(--teal)", boxShadow: "0 0 10px var(--teal)" }} />
            </div>
          )}
          {!jobId ? (
            <div className="px-2">
              <Empty title="No job running">Configure the run and press Run optimizer.</Empty>
            </div>
          ) : (
            <ConvergenceChart series={[{ name: algorithm.toUpperCase(), color: algoColor(algorithm), points: prog.points }]} height={360} />
          )}
          <div className="mx-2 mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {(
              [
                ["Iteration", last ? fmt(last.iter) : "–"],
                ["Evals", last ? last.evals.toLocaleString() : "–"],
                ["Best F", last ? last.best_F.toPrecision(5) : "–"],
                ["Elapsed", elapsed != null ? `${elapsed.toFixed(1)} s` : "–"],
              ] as const
            ).map(([kk, v]) => (
              <div key={kk} className="box px-3 py-2">
                <div className="micro">{kk}</div>
                <div className={`num mt-1 text-[15px] ${kk === "Best F" && last ? "text-teal" : "text-txt"}`}>{v}</div>
              </div>
            ))}
          </div>
          <div className="mx-2 mt-2 space-y-2">
            {prog.error && prog.status !== "FAILED" && <div className="text-[12px] text-amber">Transport note: {prog.error}</div>}
            {prog.status === "FAILED" && (
              <div className="flex items-center gap-2 text-[12.5px] text-danger">
                Job failed{prog.error ? `: ${prog.error}` : ""}.
                <button type="button" className="btn-secondary btn-sm" onClick={start}>
                  Retry
                </button>
              </div>
            )}
            {prog.status === "CANCELLED" && <div className="text-[12.5px] text-mute">Job cancelled.</div>}
            {prog.done && (prog.status === "COMPLETED" || prog.status === "COMPLETED_PARTIAL") && (
              <div className="flex items-center gap-2">
                {prog.status === "COMPLETED_PARTIAL" && <Chip tone="amber">Partial result</Chip>}
                <Link className="btn-primary" to={`/results?job=${encodeURIComponent(jobId!)}`}>
                  View results →
                </Link>
              </div>
            )}
          </div>
        </Panel>
      </div>
    </PageShell>
  );
}
