// Head-to-head counts computed from a benchmark table (never hard-coded). Direction = lower mean gap;
// significance = the table's own Holm-corrected Wilcoxon p vs the reference algorithm (< 0.05).
import { benchmarkKeys } from "./verdict";

type Row = Record<string, unknown>;
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

/** Prefer the short key column ("algo", e.g. qn_tuned) over the display-name column. */
export function algoKeyOf(rows: Row[]): string | null {
  if (rows.length && rows.every((r) => typeof r.algo === "string")) return "algo";
  return benchmarkKeys(rows).algorithm;
}

export interface HeadToHead {
  other: string;
  wins: number;
  ties: number;
  losses: number;
  instances: number;
}

/** Reference algorithm key = the one whose p-value column is "…_vs_<ref>" and whose own p is empty. */
export function referenceOf(rows: Row[], meta?: Record<string, unknown>): string | null {
  const algoKey = algoKeyOf(rows);
  if (!algoKey) return null;
  const metaRef = typeof meta?.reference === "string" ? meta.reference : null;
  const algos = new Set(rows.map((r) => String(r[algoKey])));
  if (metaRef && algos.has(metaRef)) return metaRef;
  const keys = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  for (const k of keys) {
    const m = /^wilcoxon_p_holm_vs_(.+)$/.exec(k);
    if (m && algos.has(m[1])) return m[1];
  }
  return null;
}

export function pKeyFor(rows: Row[], ref: string): string | null {
  const keys = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  return keys.find((k) => k === `wilcoxon_p_holm_vs_${ref}`) ?? keys.find((k) => k === `p_holm_vs_${ref}`) ?? null;
}

export function headToHead(rows: Row[], ref: string): HeadToHead[] {
  const k = { ...benchmarkKeys(rows), algorithm: algoKeyOf(rows) };
  if (!k.algorithm || !k.instance || !k.gap) return [];
  const pKey = pKeyFor(rows, ref);
  const byInst = new Map<string, Row[]>();
  rows.forEach((r) => byInst.set(String(r[k.instance!]), [...(byInst.get(String(r[k.instance!])) ?? []), r]));
  const out = new Map<string, HeadToHead>();
  for (const rs of byInst.values()) {
    const ours = rs.find((r) => String(r[k.algorithm!]) === ref);
    const og = ours ? num(ours[k.gap!]) : null;
    if (!ours || og === null) continue;
    for (const r of rs) {
      const a = String(r[k.algorithm!]);
      if (a === ref) continue;
      const g = num(r[k.gap!]);
      if (g === null) continue;
      const h = out.get(a) ?? { other: a, wins: 0, ties: 0, losses: 0, instances: 0 };
      h.instances += 1;
      const p = pKey ? num(r[pKey]) : null;
      if (p === null || p >= 0.05) h.ties += 1;
      else if (og < g) h.wins += 1;
      else if (og > g) h.losses += 1;
      else h.ties += 1;
      out.set(a, h);
    }
  }
  return Array.from(out.values());
}

/** instance -> algorithms with the lowest mean gap (all of them when tied). */
export function bestByInstance(rows: Row[]): Map<string, string[]> {
  const k = { ...benchmarkKeys(rows), algorithm: algoKeyOf(rows) };
  const min = new Map<string, number>();
  if (!k.algorithm || !k.instance || !k.gap) return new Map();
  for (const r of rows) {
    const g = num(r[k.gap]);
    if (g === null) continue;
    const i = String(r[k.instance]);
    min.set(i, Math.min(min.get(i) ?? Infinity, g));
  }
  const out = new Map<string, string[]>();
  for (const r of rows) {
    const g = num(r[k.gap]);
    const i = String(r[k.instance]);
    if (g === null || Math.abs(g - (min.get(i) ?? Infinity)) > 1e-9) continue;
    out.set(i, [...(out.get(i) ?? []), String(r[k.algorithm])]);
  }
  return out;
}

/** Runs whose gap is 0 (proven optimum reached) out of all runs, from the per-run gap array. */
export function optimumHits(row: Row): { hits: number; runs: number } | null {
  const arr = row.gap_runs_pct;
  if (!Array.isArray(arr) || !arr.every((v) => typeof v === "number")) return null;
  return { hits: (arr as number[]).filter((v) => Math.abs(v) < 1e-9).length, runs: arr.length };
}
