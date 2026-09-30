import { useSyncExternalStore } from "react";
import { readStore, writeStore } from "./storage";

// Tiny persisted session: the scenario being worked on and the last job id.
export interface SessionState {
  scenarioId: string | null;
  scenarioSource: string | null;
  lastJobId: string | null;
}

const KEY = "qr.session";
let state: SessionState = (() => {
  try {
    const raw = readStore(KEY);
    if (raw) return { scenarioId: null, scenarioSource: null, lastJobId: null, ...JSON.parse(raw) };
  } catch {
    /* ignore */
  }
  return { scenarioId: null, scenarioSource: null, lastJobId: null };
})();
const listeners = new Set<() => void>();

export function getSession(): SessionState {
  return state;
}

export function updateSession(patch: Partial<SessionState>) {
  state = { ...state, ...patch };
  writeStore(KEY, JSON.stringify(state));
  listeners.forEach((l) => l());
}

export function useSession(): SessionState {
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

/** Non-hyderabad sources use planar km / Euclidean coordinates, not lat/lon. */
export function isPlainSource(source: string | null | undefined): boolean {
  return !!source && source !== "hyderabad";
}
