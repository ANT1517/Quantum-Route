import { useSyncExternalStore } from "react";
import { readStore, writeStore } from "./storage";

// Build-time default from VITE_DEMO_MODE; a runtime toggle in the header overrides it (persisted).
const KEY = "qr.demoMode";
export const ENV_DEMO = String(import.meta.env.VITE_DEMO_MODE ?? "false").toLowerCase() === "true";

let current: boolean = (() => {
  const v = readStore(KEY);
  if (v === "true") return true;
  if (v === "false") return false;
  return ENV_DEMO;
})();

const listeners = new Set<() => void>();

export function isDemoMode(): boolean {
  return current;
}

export function setDemoMode(on: boolean) {
  current = on;
  writeStore(KEY, on ? "true" : "false");
  listeners.forEach((l) => l());
}

export function useDemoMode(): boolean {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => {
        listeners.delete(l);
      };
    },
    () => current,
  );
}
