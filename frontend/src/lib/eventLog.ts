import { useSyncExternalStore } from "react";

// In-memory log of what actually happened in this browser session (job started/finished, incident added, …).
// Feeds the "Decision log" and the "LAST RUN: x s ago" line; nothing here is invented.
export interface LogEvent {
  at: number; // Date.now()
  kind: "run" | "done" | "incident" | "reopt" | "info" | "warn";
  text: string;
}

let events: LogEvent[] = [];
let lastRunAt: number | null = null;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

export function logEvent(kind: LogEvent["kind"], text: string) {
  events = [{ at: Date.now(), kind, text }, ...events].slice(0, 40);
  if (kind === "done" || kind === "reopt") lastRunAt = Date.now();
  emit();
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}

export function useEventLog(): LogEvent[] {
  return useSyncExternalStore(subscribe, () => events);
}

export function useLastRunAt(): number | null {
  return useSyncExternalStore(subscribe, () => lastRunAt);
}

export function clock(at: number): string {
  const d = new Date(at);
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map((x) => String(x).padStart(2, "0")).join(":");
}
