import { useSyncExternalStore } from "react";
import { algoLabel } from "./labels";

// What the "ENGINE" card in the sub-nav shows. Defaults = the shipped engine (D53/D59):
// QPSO-noQUBO (tuned), fixed alpha 0.3, QUBO slot off. Run Optimizer updates it from its form
// (algorithm, custom alpha schedule, QUBO checkbox); a loaded result updates it from result.algorithm.
export interface EngineState {
  algorithm: string; // key understood by algoLabel
  qubo: boolean;
  alpha: { start: number; end: number } | null; // null = fixed 0.3 (tuned)
}

let state: EngineState = { algorithm: "qpso_noqubo_tuned", qubo: false, alpha: null };
const listeners = new Set<() => void>();

export function setEngine(patch: Partial<EngineState>) {
  const next = { ...state, ...patch };
  if (next.algorithm === state.algorithm && next.qubo === state.qubo && next.alpha?.start === state.alpha?.start && next.alpha?.end === state.alpha?.end) return;
  state = next;
  listeners.forEach((l) => l());
}

/** Map a result's algorithm key onto the engine card. */
export function setEngineFromResult(algorithm: string) {
  const a = algorithm.replace(/\+reroute$/, "");
  if (a === "qpso_tuned_qubo") setEngine({ algorithm: "qpso_noqubo_tuned", qubo: true, alpha: null });
  else if (a === "qpso_linear_qubo") setEngine({ algorithm: "qpso_noqubo_linear", qubo: true });
  else if (a === "qpso_noqubo_tuned" || a === "qpso") setEngine({ algorithm: "qpso_noqubo_tuned", qubo: false, alpha: null });
  else setEngine({ algorithm: a, qubo: false });
}

export function useEngine(): EngineState {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => {
        listeners.delete(l);
      };
    },
    () => state,
  );
}

export function engineName(e: EngineState): string {
  if (e.algorithm === "qpso_noqubo_tuned" || e.algorithm === "qpso_noqubo_linear" || e.algorithm === "qpso") {
    return e.qubo ? "QPSO-noQUBO (tuned) + QUBO slot" : "QPSO-noQUBO (tuned)";
  }
  return algoLabel(e.algorithm);
}

export function engineLine(e: EngineState): string {
  const isQpso = /^qpso/.test(e.algorithm);
  if (!isQpso) return "industry reference / baseline";
  const a = e.alpha ? `α ${e.alpha.start}→${e.alpha.end}` : "α 0.3";
  return `${e.alpha ? "custom" : "tuned"} · ${a} · QUBO ${e.qubo ? "on" : "off"}`;
}
