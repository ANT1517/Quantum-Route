// UI v3 §2: fixed algorithm colours app-wide; OR-Tools is drawn dashed in every line chart.
export const ALGO_COLORS: Record<string, string> = {
  qpso: "#4FE3D1", // teal — QPSO-noQUBO (tuned) and its variants
  qn: "#4FE3D1",
  a: "#4FE3D1", // ablation chain a0..a7 (QPSO variants)
  alpha: "#4FE3D1", // alpha sweep (QPSO-full variants)
  pso: "#9AA6FF", // violet
  ga: "#F3A6E0", // pink
  sa: "#7FD1FF", // sky
  rr: "#4B5260",
  ortools: "#6B7380",
  milp: "#E9ECEF",
};

export function algoColor(name: string | undefined | null, fallback = "#8C929B"): string {
  if (!name) return fallback;
  const key = name.toLowerCase().replace(/[^a-z0-9]/g, "");
  const letters = key.replace(/[0-9]/g, "");
  if (ALGO_COLORS[letters]) return ALGO_COLORS[letters];
  if (/^a[0-9]/.test(key)) return ALGO_COLORS.a;
  if (letters.startsWith("random")) return ALGO_COLORS.rr;
  if (letters.startsWith("simulated")) return ALGO_COLORS.sa;
  for (const k of ["qpso", "qn", "alpha", "pso", "ga", "sa", "rr", "ortools", "milp"]) if (letters.startsWith(k)) return ALGO_COLORS[k];
  return fallback;
}

export function isOrTools(name: string | undefined | null): boolean {
  return !!name && /or.?tools/i.test(name);
}

export function isOurs(name: string | undefined | null): boolean {
  return !!name && /^(qn|qpso)/i.test(name.replace(/[^a-z_]/gi, ""));
}

/** Vehicle colours (the only multi-colour element). */
export const VEHICLE_COLORS = ["#4FE3D1", "#9AA6FF", "#D6F25C", "#7FD1FF", "#F3A6E0", "#E9ECEF", "#FFB547", "#8FE3B0", "#C3A6F2", "#A9C4DA", "#E6C79A", "#A0A7B1"];

export function vehicleColor(index: number): string {
  return VEHICLE_COLORS[((index % VEHICLE_COLORS.length) + VEHICLE_COLORS.length) % VEHICLE_COLORS.length];
}

export const CONGESTION = "#FFB547";
export const INCIDENT = "#FFB547";

/** amber -> red by V/C ratio (0.5 .. 1.3). */
export function vcColor(vc: number): string {
  const t = Math.max(0, Math.min(1, (vc - 0.5) / 0.8));
  const a = [255, 181, 71];
  const b = [255, 92, 92];
  const c = a.map((x, i) => Math.round(x + (b[i] - x) * t));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
