// Simple SVG box plot (whiskers = min/max, box = Q1..Q3, bold line = median).
export interface BoxGroup {
  label: string;
  values: number[];
  color: string;
}

function quantile(sorted: number[], q: number): number {
  if (!sorted.length) return NaN;
  const pos = (sorted.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

export default function BoxPlot({ groups, unit = "", height = 240 }: { groups: BoxGroup[]; unit?: string; height?: number }) {
  const gs = groups.filter((g) => g.values.length);
  if (!gs.length) return <div className="text-sm text-slate-500">No per-run values to plot.</div>;
  const all = gs.flatMap((g) => g.values);
  let lo = Math.min(...all);
  let hi = Math.max(...all);
  if (hi === lo) {
    hi += 1;
    lo -= 1;
  }
  const padV = (hi - lo) * 0.08;
  lo -= padV;
  hi += padV;
  const W = Math.max(320, gs.length * 80);
  const H = height;
  const left = 48;
  const bottom = 28;
  const top = 8;
  const plotH = H - top - bottom;
  const y = (v: number) => top + plotH - ((v - lo) / (hi - lo)) * plotH;
  const bw = Math.min(40, ((W - left) / gs.length) * 0.5);
  const ticks = Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: H }} role="img" aria-label="Box plot">
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={left} x2={W} y1={y(t)} y2={y(t)} stroke="#e2e8f0" />
          <text x={left - 6} y={y(t) + 4} textAnchor="end" fontSize={10} fill="#64748b">
            {t.toPrecision(3)}
          </text>
        </g>
      ))}
      {unit && (
        <text x={4} y={top + 10} fontSize={10} fill="#64748b">
          {unit}
        </text>
      )}
      {gs.map((g, i) => {
        const s = [...g.values].sort((a, b) => a - b);
        const cx = left + ((W - left) / gs.length) * (i + 0.5);
        const mn = s[0];
        const q1 = quantile(s, 0.25);
        const md = quantile(s, 0.5);
        const q3 = quantile(s, 0.75);
        const mx = s[s.length - 1];
        return (
          <g key={g.label}>
            <title>{`${g.label}: min ${mn}, Q1 ${q1.toFixed(3)}, median ${md.toFixed(3)}, Q3 ${q3.toFixed(3)}, max ${mx} (n=${s.length})`}</title>
            <line x1={cx} x2={cx} y1={y(mx)} y2={y(mn)} stroke={g.color} />
            <line x1={cx - bw / 4} x2={cx + bw / 4} y1={y(mx)} y2={y(mx)} stroke={g.color} />
            <line x1={cx - bw / 4} x2={cx + bw / 4} y1={y(mn)} y2={y(mn)} stroke={g.color} />
            <rect x={cx - bw / 2} y={y(q3)} width={bw} height={Math.max(1, y(q1) - y(q3))} fill={g.color} fillOpacity={0.25} stroke={g.color} />
            <line x1={cx - bw / 2} x2={cx + bw / 2} y1={y(md)} y2={y(md)} stroke={g.color} strokeWidth={2.5} />
            <text x={cx} y={H - 8} textAnchor="middle" fontSize={11} fill="#334155">
              {g.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
