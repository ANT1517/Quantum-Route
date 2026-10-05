// Grouped bars: mean gap (%) per instance and algorithm, 3px rounded tops, teal gradient for ours.
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { algoColor, isOrTools, isOurs } from "../../lib/colors";
import { algoLabel } from "../../lib/labels";
import { ANIM_MS, GRID, TICK, TooltipCard } from "./theme";

type Row = Record<string, unknown>;

export default function GapBars({
  rows,
  instanceKey,
  algoKey,
  gapKey,
  height = 260,
  best,
}: {
  rows: Row[];
  instanceKey: string;
  algoKey: string;
  gapKey: string;
  height?: number;
  /** instance -> algo with the lowest gap (computed by the caller from the same rows) */
  best?: Map<string, string[]>;
}) {
  const instances = Array.from(new Set(rows.map((r) => String(r[instanceKey]))));
  const algos = Array.from(new Set(rows.map((r) => String(r[algoKey]))));
  // ours first, OR-Tools last
  algos.sort((a, b) => Number(isOurs(b)) - Number(isOurs(a)) || Number(isOrTools(a)) - Number(isOrTools(b)));
  const data = instances.map((inst) => {
    const o: Record<string, unknown> = { instance: inst };
    for (const r of rows) if (String(r[instanceKey]) === inst && typeof r[gapKey] === "number") o[String(r[algoKey])] = r[gapKey];
    return o;
  });
  const summary = instances
    .map((i) => `${i}: ${algos.filter((a) => typeof data.find((d) => d.instance === i)?.[a] === "number").map((a) => `${algoLabel(a)} ${(data.find((d) => d.instance === i)![a] as number).toFixed(2)}`).join(", ")}`)
    .join("; ");
  return (
    <div style={{ height }} role="img" aria-label={`Grouped bar chart of ${gapKey.replace(/_/g, " ")} per instance (lower is better). ${summary}.`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 0 }} barGap={2} barCategoryGap="22%">
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="instance" tick={TICK} tickLine={false} axisLine={{ stroke: GRID }} interval={0} />
          <YAxis tick={TICK} tickLine={false} axisLine={false} width={36} tickFormatter={(x: number) => `${x}`} />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,.025)" }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <TooltipCard
                  title={`${label} · ${gapKey.replace(/_/g, " ")}`}
                  rows={payload.map((p) => ({ k: algoLabel(String(p.dataKey)) + (best?.get(String(label))?.includes(String(p.dataKey)) ? " ★ best" : ""), v: `${Number(p.value).toFixed(3)}%`, color: algoColor(String(p.dataKey)) }))}
                />
              ) : null
            }
          />
          <Legend
            verticalAlign="top"
            height={28}
            iconType="circle"
            iconSize={7}
            payload={algos.map((a) => ({ value: a, id: a, type: "circle" as const, color: algoColor(a) }))}
            formatter={(v) => <span style={{ color: "#8C929B", fontFamily: "JetBrains Mono, monospace", fontSize: 10.5 }}>{algoLabel(String(v))}</span>}
          />
          {algos.map((a) => (
            <Bar
              key={a}
              dataKey={a}
              name={a}
              fill={isOurs(a) ? "url(#qr-bar-teal)" : algoColor(a)}
              radius={[3, 3, 0, 0]}
              maxBarSize={22}
              isAnimationActive
              animationDuration={ANIM_MS}
              stroke={isOrTools(a) ? "#8C929B" : undefined}
              strokeDasharray={isOrTools(a) ? "3 2" : undefined}
              fillOpacity={isOurs(a) ? 1 : 0.85}
            >
              {data.map((d) => (
                <Cell key={String(d.instance)} style={isOurs(a) ? { filter: "drop-shadow(0 0 5px rgba(79,227,209,.55))" } : undefined} />
              ))}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
