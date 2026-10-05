// 24-hour background load ratio rho(t, road class) — exact copy of engine/qflux/traffic/profiles.py
// (values in ../data/traffic_profile.json, checked by tests/traffic/test_traffic_profile_json.py).
// Same linear interpolation between slot centres as profiles.slot_weights, wrapping around midnight.
import profile from "../data/traffic_profile.json";

export const TRAFFIC_PROFILE = profile as {
  source: string;
  day_min: number;
  slot_centers_min: number[];
  slot_labels: string[];
  groups: string[];
  load_ratio: number[][];
};

/** rho(t) for road-class index g (0 arterial, 1 secondary, 2 residential). */
export function loadRatio(tMin: number, g: number): number {
  const c = TRAFFIC_PROFILE.slot_centers_min;
  const M = TRAFFIC_PROFILE.load_ratio;
  const day = TRAFFIC_PROFILE.day_min;
  const S = c.length;
  const t = ((tMin % day) + day) % day;
  let s: number;
  let s1: number;
  let lam: number;
  if (t < c[0] || t >= c[S - 1]) {
    s = S - 1;
    s1 = 0;
    const span = c[0] + day - c[S - 1];
    lam = (((t - c[S - 1]) % day) + day) % day / span;
  } else {
    s = 0;
    for (let i = 0; i < S; i++) if (c[i] <= t) s = i;
    s1 = s + 1;
    lam = (t - c[s]) / (c[s1] - c[s]);
  }
  return (1 - lam) * M[s][g] + lam * M[s1][g];
}

export interface ProfilePoint {
  t: number;
  arterial: number;
  secondary: number;
  residential: number;
}

/** Samples every `step` minutes over 0..1440 (inclusive). */
export function profileSeries(step = 10): ProfilePoint[] {
  const out: ProfilePoint[] = [];
  for (let t = 0; t <= TRAFFIC_PROFILE.day_min; t += step) {
    out.push({ t, arterial: loadRatio(t, 0), secondary: loadRatio(t, 1), residential: loadRatio(t, 2) });
  }
  return out;
}

/** "PEAK" / "OFF-PEAK" / "" from the arterial load ratio at t (data-driven label for hero eyebrows). */
export function peakLabel(tMin: number): string {
  const rows = TRAFFIC_PROFILE.load_ratio.map((r) => r[0]);
  const max = Math.max(...rows);
  const min = Math.min(...rows);
  const v = loadRatio(tMin, 0);
  if (v >= max - 0.1 * (max - min)) return "PEAK";
  if (v <= min + 0.2 * (max - min)) return "OFF-PEAK";
  return "";
}
