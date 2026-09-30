// Visual rules §8.1: one accent colour per algorithm.
export const ALGO_COLORS: Record<string, string> = {
  qpso: "#0d9488", // teal
  pso: "#f59e0b", // amber
  ga: "#8b5cf6", // purple
  sa: "#6b7280", // grey
  ortools: "#111827", // black
  milp: "#2563eb",
};

export function algoColor(name: string | undefined | null, fallback = "#334155"): string {
  if (!name) return fallback;
  const key = name.toLowerCase().replace(/[^a-z]/g, "");
  if (ALGO_COLORS[key]) return ALGO_COLORS[key];
  for (const k of Object.keys(ALGO_COLORS)) if (key.startsWith(k)) return ALGO_COLORS[k];
  return fallback;
}

export const CONGESTION = "#f59e0b";
export const INCIDENT = "#dc2626";

/** amber -> red by V/C ratio (0.5 .. 1.3). */
export function vcColor(vc: number): string {
  const t = Math.max(0, Math.min(1, (vc - 0.5) / 0.8));
  const a = [245, 158, 11];
  const b = [220, 38, 38];
  const c = a.map((x, i) => Math.round(x + (b[i] - x) * t));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
