import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ConvergencePoint } from "../api/types";

export interface ConvergenceSeries {
  name: string;
  color: string;
  points: ConvergencePoint[];
  dashed?: boolean;
}

const prec = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v.toPrecision(4) : String(v));

/** best_F vs evaluations; any number of overlaid series. */
export default function ConvergenceChart({ series, height = 280 }: { series: ConvergenceSeries[]; height?: number }) {
  const nonEmpty = series.filter((s) => s.points.length > 0);
  if (!nonEmpty.length) {
    return (
      <div className="flex items-center justify-center rounded-md border border-dashed border-slate-300 text-sm text-slate-500" style={{ height }}>
        No convergence points yet
      </div>
    );
  }
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart margin={{ top: 8, right: 16, bottom: 16, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="evals"
            type="number"
            domain={["dataMin", "dataMax"]}
            tick={{ fontSize: 11 }}
            label={{ value: "evaluations", position: "insideBottom", offset: -8, fontSize: 11 }}
            allowDuplicatedCategory={false}
          />
          <YAxis dataKey="best_F" type="number" domain={["auto", "auto"]} tick={{ fontSize: 11 }} width={56} tickFormatter={prec} />
          <Tooltip formatter={(v) => prec(v)} labelFormatter={(l) => `evals ${l}`} />
          {nonEmpty.length > 1 && <Legend verticalAlign="top" height={24} />}
          {nonEmpty.map((s) => (
            <Line
              key={s.name}
              name={s.name}
              data={s.points}
              dataKey="best_F"
              stroke={s.color}
              strokeWidth={2}
              strokeDasharray={s.dashed ? "6 4" : undefined}
              dot={false}
              isAnimationActive={false}
              type="stepAfter"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
