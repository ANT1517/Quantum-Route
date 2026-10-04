import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, cancelJob, createJob, getScenario } from "../api/client";
import type { Algorithm, Weights } from "../api/types";
import type { FleetMode } from "../types/result";
import ConvergenceChart from "../components/ConvergenceChart";
import { Empty, MockBadge } from "../components/States";
import { useJobProgress } from "../hooks/useJobProgress";
import { algoColor } from "../lib/colors";
import { useDemoMode } from "../lib/demoMode";
import { minToHHMM } from "../lib/format";
import { updateSession, useSession } from "../lib/session";

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
  const [seed, setSeed] = useState(7);
  const [fleetMode, setFleetMode] = useState<FleetMode>("naive");
  const [jobId, setJobId] = useState<string | null>(null);
  const [startErr, setStartErr] = useState<ApiError | null>(null);
  const [starting, setStarting] = useState(false);
  const autoStarted = useRef(false);

  const scenarioId = session.scenarioId ?? (demo ? "demo" : null);
  const scenario = useQuery({
    queryKey: ["scenario", scenarioId],
    queryFn: ({ signal }) => getScenario(scenarioId!, { signal, silent: true }),
    enabled: !!scenarioId,
  });

  const budgetEvals = N * iters;
  const prog = useJobProgress(jobId, budgetEvals);
  const running = !!jobId && !prog.done;

  const start = async () => {
    const sid = scenario.data?.scenario.id ?? scenarioId;
    if (!sid) return;
    setStartErr(null);
    setStarting(true);
    try {
      const p: Record<string, unknown> = { N, iterations: iters };
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

  if (!scenarioId) {
    return (
      <Empty title="No scenario selected">
        <Link className="text-teal-700 underline" to="/scenario">
          Create or pick a scenario first
        </Link>
      </Empty>
    );
  }

  const pct = prog.progress != null ? Math.round(prog.progress * 100) : null;
  const statusColor =
    prog.status === "FAILED" ? "bg-red-100 text-red-800" : prog.done ? "bg-teal-100 text-teal-800" : "bg-amber-100 text-amber-800";

  return (
    <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
      <div className="card space-y-4">
        <h1 className="page-title">Run Optimizer</h1>
        <div className="text-sm text-slate-600">
          Scenario:{" "}
          {scenario.isLoading ? "loading…" : scenario.data ? (
            <>
              <b>{scenario.data.scenario.name}</b> <MockBadge text={scenario.data.scenario.id} /> · depart {minToHHMM(scenario.data.scenario.tau0)}
            </>
          ) : (
            <span className="text-red-700">could not load ({scenarioId})</span>
          )}
        </div>
        <div>
          <label className="label">Algorithm</label>
          <select className="input" value={algorithm} onChange={(e) => setAlgorithm(e.target.value as Algorithm)}>
            {ALGOS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Objective weights (sum = 1)</label>
          <div className="mb-2 flex flex-wrap gap-1">
            {PRESETS.map(([name, w]) => (
              <button key={name} className="btn-secondary px-2 py-1 text-xs" onClick={() => setWeights(w)}>
                {name}
              </button>
            ))}
          </div>
          {(Object.keys(WEIGHT_LABELS) as Array<keyof Weights>).map((k) => (
            <div key={k} className="mb-1">
              <div className="flex justify-between text-xs">
                <span>{WEIGHT_LABELS[k]}</span>
                <span className="tabular-nums">{weights[k].toFixed(3)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={weights[k]}
                className={`w-full ${k === "wC" ? "accent-amber-500" : "accent-teal-600"}`}
                onChange={(e) => setWeights((w) => renormalise(w, k, Number(e.target.value)))}
              />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="label">Swarm / pop N</label>
            <input type="number" min={2} className="input" value={N} onChange={(e) => setN(Math.max(2, Number(e.target.value)))} />
          </div>
          <div>
            <label className="label">Iterations</label>
            <input type="number" min={1} className="input" value={iters} onChange={(e) => setIters(Math.max(1, Number(e.target.value)))} />
          </div>
          {algorithm === "qpso" && (
            <div className="col-span-2 text-xs text-slate-600">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={customAlpha} onChange={(e) => setCustomAlpha(e.target.checked)} />
                Custom α schedule (linear)
              </label>
              {!customAlpha && <div className="mt-1">α = 0.3 fixed — QPSO-noQUBO (tuned), tuned on CVRPLIB tuning instances only.</div>}
            </div>
          )}
          {algorithm === "qpso" && customAlpha && (
            <>
              <div>
                <label className="label">α start</label>
                <input type="number" step={0.05} className="input" value={alphaStart} onChange={(e) => setAlphaStart(Number(e.target.value))} />
              </div>
              <div>
                <label className="label">α end</label>
                <input type="number" step={0.05} className="input" value={alphaEnd} onChange={(e) => setAlphaEnd(Number(e.target.value))} />
              </div>
            </>
          )}
          <div>
            <label className="label">Seed</label>
            <input type="number" className="input" value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
          </div>
          <div>
            <label className="label">Fleet mode</label>
            <select className="input" value={fleetMode} onChange={(e) => setFleetMode(e.target.value as FleetMode)}>
              <option value="naive">naive</option>
              <option value="user_eq">user_eq</option>
              <option value="system_opt">system_opt</option>
            </select>
          </div>
        </div>
        <div className="text-xs text-slate-500">Budget: {budgetEvals.toLocaleString()} evaluations (N × iterations)</div>
        {startErr && (
          <div className="rounded-md border border-red-300 bg-red-50 p-2 text-sm text-red-800" role="alert">
            <b>{startErr.code}</b>: {startErr.message}
            {startErr.status === 429 && <div className="text-xs">Two jobs are already running; wait or cancel one.</div>}
          </div>
        )}
        <div className="flex gap-2">
          <button className="btn-primary flex-1 justify-center" disabled={running || starting || !scenario.data} onClick={start}>
            {starting ? "Starting…" : running ? "Running…" : "Start"}
          </button>
          <button className="btn-secondary" disabled={!running} onClick={cancel}>
            Cancel
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <div className="card">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div className="label">Live convergence (best F vs evaluations)</div>
            {jobId && (
              <div className="flex items-center gap-2 text-xs">
                <span className="font-mono">job {jobId}</span>
                <MockBadge text={jobId} />
                <span className={`badge ${statusColor}`}>{prog.status ?? "…"}</span>
                {pct != null && !prog.done && <span>{pct}%</span>}
                <span className="text-slate-400">via {prog.transport}</span>
              </div>
            )}
          </div>
          {jobId && !prog.done && (
            <div className="mb-2 h-2 w-full overflow-hidden rounded bg-slate-100">
              <div className="h-full bg-teal-600 transition-all" style={{ width: `${pct ?? 5}%` }} />
            </div>
          )}
          {!jobId ? (
            <Empty title="No job running">Configure the run and press Start.</Empty>
          ) : (
            <ConvergenceChart series={[{ name: algorithm.toUpperCase(), color: algoColor(algorithm), points: prog.points }]} height={340} />
          )}
          {prog.error && prog.status !== "FAILED" && <div className="mt-2 text-xs text-amber-700">Transport note: {prog.error}</div>}
          {prog.status === "FAILED" && (
            <div className="mt-2 flex items-center gap-2 rounded bg-red-50 p-2 text-sm text-red-800">
              Job failed{prog.error ? `: ${prog.error}` : ""}.
              <button className="btn-secondary" onClick={start}>
                Retry
              </button>
            </div>
          )}
          {prog.status === "CANCELLED" && <div className="mt-2 text-sm text-slate-600">Job cancelled.</div>}
          {prog.done && (prog.status === "COMPLETED" || prog.status === "COMPLETED_PARTIAL") && (
            <div className="mt-4 flex items-center gap-2">
              {prog.status === "COMPLETED_PARTIAL" && <span className="badge bg-amber-100 text-amber-800">Partial result</span>}
              <Link className="btn-primary" to={`/results?job=${encodeURIComponent(jobId!)}`}>
                View results →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
