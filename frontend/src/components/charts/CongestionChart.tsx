// "Network congestion · 24 h": background load ratio rho(t) per road class from traffic_profile.json
// (exact copy of engine/qflux/traffic/profiles.py), sampled every 10 min with the engine's linear
// interpolation. The only wave-shaped chart in the app. Marker = departure time.
import { useMemo } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { minToHHMM } from "../../lib/format";
import { loadRatio, profileSeries } from "../../lib/trafficProfile";
import { ANIM_MS, GRID, TICK, TooltipCard } from "./theme";

const TICKS = [0, 180, 360, 540, 720, 900, 1080, 1260, 1440];

/** Small card beside the departure marker (left of it late in the day so it stays inside the plot). */
function MarkerLabel({ viewBox, t, v, r }: { viewBox?: { x: number; y: number }; t: number; v: number; r: number }) {
  if (!viewBox) return null;
  const w = 112;
  const x = t > 1080 ? viewBox.x - w - 12 : viewBox.x + 12;
  return (
    <g transform={`translate(${x},${Math.max(2, viewBox.y - 12)})`}>
      <rect width={w} height={30} rx={5} fill="#0A0C0F" stroke="#262B33" />
      <text x={9} y={13} fontSize={9.5} fill="#FFB547" fontFamily="JetBrains Mono, monospace" letterSpacing="0.06em">
        ARTERIAL ×{v.toFixed(2)}
      </text>
      <text x={9} y={24} fontSize={9.5} fill="#8C929B" fontFamily="JetBrains Mono, monospace" letterSpacing="0.06em">
        RESIDENTIAL ×{r.toFixed(2)}
      </text>
      <title>{`Departure ${minToHHMM(t)}: arterial ρ ${v.toFixed(2)}, residential ρ ${r.toFixed(2)} (simulated profile)`}</title>
    </g>
  );
}

export default function CongestionChart({ departMin, height = 220 }: { departMin?: number | null; height?: number }) {
  const data = useMemo(() => profileSeries(10), []);
  const t = departMin != null && Number.isFinite(departMin) ? ((departMin % 1440) + 1440) % 1440 : null;
  const v = t != null ? loadRatio(t, 0) : null;
  const res = t != null ? loadRatio(t, 2) : null;
  const peak = data.reduce((a, b) => (b.arterial > a.arterial ? b : a));
  return (
    <div
      style={{ height }}
      role="img"
      aria-label={`24-hour background load ratio by road class (simulated traffic profile). Arterial peaks at ${peak.arterial.toFixed(2)} around ${minToHHMM(peak.t)}${t != null && v != null ? `; at departure ${minToHHMM(t)} the arterial load ratio is ${v.toFixed(2)}` : ""}.`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 12, right: 14, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="t" type="number" domain={[0, 1440]} ticks={TICKS} tickFormatter={(x) => minToHHMM(x)} tick={TICK} tickLine={false} axisLine={{ stroke: GRID }} />
          <YAxis tick={TICK} tickLine={false} axisLine={false} width={34} domain={[0, "auto"]} tickFormatter={(x: number) => x.toFixed(1)} />
          <Tooltip
            cursor={{ stroke: "#2a3038", strokeDasharray: "3 3" }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <TooltipCard
                  title={`${minToHHMM(Number(label))} · ρ = V/C`}
                  rows={payload
                    .filter((p) => p.name !== "__area")
                    .map((p) => ({ k: String(p.name), v: Number(p.value).toFixed(2), color: String(p.color ?? "") }))}
                />
              ) : null
            }
          />
          <Area name="__area" dataKey="arterial" type="monotone" stroke="none" fill="url(#qr-area-teal)" isAnimationActive animationDuration={ANIM_MS} tooltipType="none" />
          <Line name="residential" dataKey="residential" type="monotone" stroke="#C9A75B" strokeOpacity={0.7} strokeDasharray="3 3" strokeWidth={1.3} dot={false} isAnimationActive animationDuration={ANIM_MS} />
          <Line name="secondary" dataKey="secondary" type="monotone" stroke="#9AA6FF" strokeOpacity={0.45} strokeWidth={1.2} dot={false} isAnimationActive animationDuration={ANIM_MS} />
          <Line
            name="arterial"
            dataKey="arterial"
            type="monotone"
            stroke="url(#qr-stroke-teal)"
            strokeWidth={2.4}
            dot={false}
            activeDot={{ r: 4, fill: "#4FE3D1", stroke: "#030304", strokeWidth: 2 }}
            filter="url(#qr-glow)"
            isAnimationActive
            animationDuration={ANIM_MS}
          />
          {t != null && v != null && (
            <>
              <ReferenceLine x={t} stroke="rgba(201,255,247,.35)" strokeDasharray="2 3" />
              <ReferenceDot x={t} y={v} r={9} fill="rgba(79,227,209,.12)" stroke="rgba(79,227,209,.5)" strokeWidth={1} />
              <ReferenceDot x={t} y={v} r={3.5} fill="#C9FFF7" stroke="#4FE3D1" strokeWidth={1.5} filter="url(#qr-glow)" label={<MarkerLabel t={t} v={v} r={res ?? 0} />} />
            </>
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CongestionLegend() {
  return (
    <div className="flex flex-wrap items-center gap-3 font-mono text-[10px] text-mute">
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-[2px] w-4 rounded" style={{ background: "#4FE3D1", boxShadow: "0 0 6px #4FE3D1" }} /> arterial
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-[2px] w-4 rounded" style={{ background: "#9AA6FF" }} /> secondary
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block w-4 border-t border-dashed" style={{ borderColor: "#C9A75B" }} /> residential
      </span>
    </div>
  );
}
