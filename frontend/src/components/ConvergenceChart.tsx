// best F vs evaluations. Best-so-far values never rise, so curves use monotoneX (no overshoot).
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ConvergencePoint } from "../api/types";
import { isOrTools } from "../lib/colors";
import { ANIM_MS, GRID, TICK, TooltipCard } from "./charts/theme";

export interface ConvergenceSeries {
  name: string;
  color: string;
  points: ConvergencePoint[];
  dashed?: boolean;
}

const prec = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v.toPrecision(4) : String(v));

function summary(series: ConvergenceSeries[]): string {
  return series
    .map((s) => {
      const a = s.points[0];
      const b = s.points[s.points.length - 1];
      return `${s.name}: best F from ${prec(a.best_F)} at ${a.evals} evaluations to ${prec(b.best_F)} at ${b.evals} evaluations`;
    })
    .join("; ");
}

/** best_F vs evaluations; any number of overlaid series. First series is drawn with the teal glow + area. */
export default function ConvergenceChart({ series, height = 280, animate = false }: { series: ConvergenceSeries[]; height?: number; animate?: boolean }) {
  const nonEmpty = series.filter((s) => s.points.length > 0);
  if (!nonEmpty.length) {
    return (
      <div className="flex items-center justify-center rounded-xl font-mono text-[11px] uppercase tracking-[0.14em] text-lbl" style={{ height, border: "1px dashed var(--line-2)" }}>
        No convergence points yet
      </div>
    );
  }
  const single = nonEmpty.length === 1;
  return (
    <div style={{ height }} role="img" aria-label={`Convergence chart (best-so-far, never rises). ${summary(nonEmpty)}.`}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart margin={{ top: 10, right: 14, bottom: 14, left: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis
            dataKey="evals"
            type="number"
            domain={["dataMin", "dataMax"]}
            tick={TICK}
            tickLine={false}
            axisLine={{ stroke: GRID }}
            label={{ value: "EVALUATIONS", position: "insideBottom", offset: -8, ...TICK, letterSpacing: "0.14em" }}
            allowDuplicatedCategory={false}
          />
          <YAxis dataKey="best_F" type="number" domain={["auto", "auto"]} tick={TICK} tickLine={false} axisLine={false} width={52} tickFormatter={prec} />
          <Tooltip
            cursor={{ stroke: "#2a3038", strokeDasharray: "3 3" }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <TooltipCard
                  title={`evals ${label}`}
                  rows={payload.filter((p) => p.type !== "none" && p.dataKey === "best_F" && p.name !== "__area").map((p) => ({ k: String(p.name), v: prec(p.value), color: String(p.color ?? "") }))}
                />
              ) : null
            }
          />
          {!single && <Legend verticalAlign="top" height={26} iconType="plainline" wrapperStyle={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10.5, color: "#8C929B" }} />}
          {single && (
            <Area
              name="__area"
              legendType="none"
              data={nonEmpty[0].points}
              dataKey="best_F"
              type="monotoneX"
              stroke="none"
              fill="url(#qr-area-teal)"
              isAnimationActive={animate}
              animationDuration={ANIM_MS}
              baseValue="dataMin"
              tooltipType="none"
            />
          )}
          {nonEmpty.map((s, i) => {
            const ours = i === 0 && /4fe3d1/i.test(s.color);
            const flat = s.points.every((p) => p.best_F === s.points[0].best_F);
            const dashed = s.dashed || isOrTools(s.name);
            return (
              <Line
                key={s.name}
                name={s.name}
                data={s.points}
                dataKey="best_F"
                stroke={ours && !flat ? "url(#qr-stroke-teal)" : s.color}
                strokeWidth={2.4}
                strokeDasharray={dashed ? "6 4" : undefined}
                dot={false}
                activeDot={{ r: 4, fill: s.color, stroke: "#030304", strokeWidth: 2 }}
                isAnimationActive={animate}
                animationDuration={ANIM_MS}
                type="monotoneX"
                filter={ours ? "url(#qr-glow)" : undefined}
              />
            );
          })}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
