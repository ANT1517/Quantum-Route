// Verdict text for Benchmark Studio, computed from whatever table the backend returns (never hard-coded).
type Row = Record<string, unknown>;

const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

export function findKey(rows: Row[], patterns: RegExp[], numeric = false): string | null {
  if (!rows.length) return null;
  const keys = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  for (const p of patterns) {
    const k = keys.find((key) => p.test(key) && (!numeric || rows.some((r) => num(r[key]) !== null)));
    if (k) return k;
  }
  return null;
}

export function benchmarkKeys(rows: Row[]) {
  return {
    instance: findKey(rows, [/^instance$/i, /instance/i, /^name$/i]),
    algorithm: findKey(rows, [/^algorithm$/i, /^algo$/i, /algo/i, /method/i]),
    gap: findKey(rows, [/mean.*gap/i, /gap.*mean/i, /^gap/i, /gap/i, /mean.*cost/i, /^mean/i], true),
    pval: findKey(rows, [/wilcoxon/i, /p.?val/i, /^p$/i, /p_vs/i], true),
    std: findKey(rows, [/std/i], true),
  };
}

function fmtNum(v: number) {
  return Number.isInteger(v) ? String(v) : v.toFixed(Math.abs(v) < 1 ? 3 : 2);
}

/** One sentence per instance: which algorithm has the lowest mean gap, and how QPSO compares. */
export function computeVerdict(rows: Row[]): string[] {
  const k = benchmarkKeys(rows);
  if (!k.gap || !k.algorithm) return ["No gap/algorithm columns found — cannot compute a verdict from this table."];
  const groups = new Map<string, Row[]>();
  for (const r of rows) {
    const inst = k.instance ? String(r[k.instance] ?? "all") : "all instances";
    if (!groups.has(inst)) groups.set(inst, []);
    groups.get(inst)!.push(r);
  }
  const out: string[] = [];
  for (const [inst, rs] of groups) {
    const valid = rs.filter((r) => num(r[k.gap!]) !== null);
    if (!valid.length) continue;
    const best = valid.reduce((a, b) => (num(b[k.gap!])! < num(a[k.gap!])! ? b : a));
    const bestAlg = String(best[k.algorithm]);
    let s = `On ${inst}, ${bestAlg} had the lowest ${k.gap.replace(/_/g, " ")} (${fmtNum(num(best[k.gap])!)}).`;
    const q = valid.find((r) => /qpso/i.test(String(r[k.algorithm!])) && r !== best);
    if (q) {
      s += ` QPSO: ${fmtNum(num(q[k.gap])!)}`;
      if (k.pval) {
        const p = num(best[k.pval]);
        if (p !== null) s += `; Wilcoxon p = ${fmtNum(p)} (${bestAlg} vs QPSO${p < 0.05 ? ", significant at 0.05" : ", not significant at 0.05"})`;
      }
      s += ".";
    } else if (/qpso/i.test(bestAlg) && k.pval) {
      const ps = valid.map((r) => num(r[k.pval!])).filter((p): p is number => p !== null);
      if (ps.length) s += ` Largest p-value vs QPSO among the others: ${fmtNum(Math.max(...ps))}.`;
    }
    out.push(s);
  }
  return out.length ? out : ["Table has no numeric gap values."];
}
