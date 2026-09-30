// SVG heatmap of a QUBO matrix (diverging: negative = teal, positive = red).
export default function QuboHeatmap({ matrix, labels, size = 420 }: { matrix: number[][]; labels?: string[]; size?: number }) {
  const n = matrix.length;
  if (!n) return <div className="text-sm text-slate-500">Empty QUBO matrix.</div>;
  const maxAbs = Math.max(1e-9, ...matrix.flatMap((r) => r.map((v) => Math.abs(v))));
  const pad = labels ? 56 : 8;
  const cell = (size - pad) / n;
  const color = (v: number) => {
    if (v === 0) return "#f8fafc";
    const t = Math.min(1, Math.abs(v) / maxAbs);
    const base = v < 0 ? [13, 148, 136] : [220, 38, 38];
    const c = base.map((b) => Math.round(255 + (b - 255) * (0.15 + 0.85 * t)));
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  };
  const fs = Math.min(10, cell * 0.8);
  return (
    <div>
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-md" role="img" aria-label="QUBO matrix heatmap">
        {labels &&
          labels.map((l, i) => (
            <g key={`${l}-${i}`}>
              <text x={pad - 4} y={pad + cell * (i + 0.5) + 3} textAnchor="end" fontSize={fs} fill="#475569">
                {l}
              </text>
              <text
                x={pad + cell * (i + 0.5)}
                y={pad - 4}
                textAnchor="start"
                fontSize={fs}
                fill="#475569"
                transform={`rotate(-60 ${pad + cell * (i + 0.5)} ${pad - 4})`}
              >
                {l}
              </text>
            </g>
          ))}
        {matrix.map((row, i) =>
          row.map((v, j) => (
            <rect key={`${i}-${j}`} x={pad + j * cell} y={pad + i * cell} width={cell} height={cell} fill={color(v)} stroke="#fff" strokeWidth={0.5}>
              <title>{`Q[${labels?.[i] ?? i}, ${labels?.[j] ?? j}] = ${v}`}</title>
            </rect>
          )),
        )}
      </svg>
      <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <span className="inline-block h-3 w-3" style={{ background: "rgb(13,148,136)" }} /> negative
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-3 w-3" style={{ background: "rgb(220,38,38)" }} /> positive (penalty / distance)
        </span>
        <span>|max| = {maxAbs.toPrecision(4)}</span>
      </div>
    </div>
  );
}
