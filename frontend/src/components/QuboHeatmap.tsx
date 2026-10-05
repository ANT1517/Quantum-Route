// SVG heatmap of a QUBO matrix. Sequential ramp on |Q| (black → violet → teal); the sign is in the tooltip
// and negative cells carry a dot (colour is never the only cue).
function ramp(t: number): string {
  const stops: Array<[number, number[]]> = [
    [0, [7, 8, 10]],
    [0.5, [154, 166, 255]],
    [1, [79, 227, 209]],
  ];
  const i = t <= 0.5 ? 0 : 1;
  const [a, ca] = stops[i];
  const [b, cb] = stops[i + 1];
  const u = (t - a) / (b - a);
  const c = ca.map((x, k) => Math.round(x + (cb[k] - x) * u));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

export default function QuboHeatmap({ matrix, labels: allLabels, size = 420 }: { matrix: number[][]; labels?: string[]; size?: number }) {
  const n = matrix.length;
  // axis labels only while readable; cell tooltips always carry them
  const labels = allLabels && n <= 25 ? allLabels : undefined;
  if (!n) return <div className="text-[13px] text-mute">Empty QUBO matrix.</div>;
  const maxAbs = Math.max(1e-9, ...matrix.flatMap((r) => r.map((v) => Math.abs(v))));
  const pad = labels ? 56 : 8;
  const cell = (size - pad) / n;
  const color = (v: number) => (v === 0 ? "#07080A" : ramp(0.12 + 0.88 * Math.sqrt(Math.min(1, Math.abs(v) / maxAbs))));
  const fs = Math.min(9, cell * 0.8);
  const neg = matrix.flat().filter((v) => v < 0).length;
  return (
    <div>
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="w-full max-w-[440px]"
        role="img"
        aria-label={`QUBO matrix heatmap, ${n} by ${n} variables, ${neg} negative entries, max |Q| ${maxAbs.toPrecision(4)}`}
      >
        {labels &&
          labels.map((l, i) => (
            <g key={`${l}-${i}`}>
              <text x={pad - 4} y={pad + cell * (i + 0.5) + 3} textAnchor="end" fontSize={fs} fill="#5A616B" fontFamily="JetBrains Mono, monospace">
                {l}
              </text>
              <text
                x={pad + cell * (i + 0.5)}
                y={pad - 4}
                textAnchor="start"
                fontSize={fs}
                fill="#5A616B"
                fontFamily="JetBrains Mono, monospace"
                transform={`rotate(-60 ${pad + cell * (i + 0.5)} ${pad - 4})`}
              >
                {l}
              </text>
            </g>
          ))}
        {matrix.map((row, i) =>
          row.map((v, j) => (
            <g key={`${i}-${j}`}>
              <rect x={pad + j * cell} y={pad + i * cell} width={cell} height={cell} fill={color(v)} stroke="#030304" strokeWidth={0.5}>
                <title>{`Q[${allLabels?.[i] ?? i}, ${allLabels?.[j] ?? j}] = ${v}`}</title>
              </rect>
              {v < 0 && cell >= 5 && <circle cx={pad + (j + 0.5) * cell} cy={pad + (i + 0.5) * cell} r={Math.min(1.6, cell * 0.15)} fill="#030304" pointerEvents="none" />}
            </g>
          )),
        )}
      </svg>
      <div className="mt-3 flex flex-wrap items-center gap-3 font-mono text-[10px] text-mute">
        <span className="flex items-center gap-2">
          |Q| 0
          <span className="inline-block h-2 w-24 rounded" style={{ background: "linear-gradient(90deg,#07080A,#9AA6FF,#4FE3D1)" }} />
          {maxAbs.toPrecision(4)}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: "#030304", boxShadow: "0 0 0 1px #8C929B" }} /> dot = negative entry
        </span>
      </div>
    </div>
  );
}
