import type { ResultJSON } from "../types/result";
import { vehicleColor } from "../lib/colors";
import { fmt, minToHHMM } from "../lib/format";
import { DataTable } from "./ui/primitives";

/** Vehicle status table. Load bar = load / capacity; delay share = congestion delay / time. */
export default function RouteTable({ routes, compact = false }: { routes: ResultJSON["routes"]; compact?: boolean }) {
  if (!routes.length) return <div className="text-[13px] text-mute">No routes in this result.</div>;
  return (
    <DataTable>
      <thead>
        <tr>
          <th>Vehicle</th>
          {!compact && <th>Stops</th>}
          <th>Load / Q</th>
          <th>Depart → Return</th>
          <th>Time (min)</th>
          <th>Delay (min)</th>
          <th>Km</th>
          <th>CO₂ (kg, illustrative)</th>
        </tr>
      </thead>
      <tbody>
        {routes.map((r, i) => {
          const c = vehicleColor(i);
          const load = r.capacity ? r.load / r.capacity : 0;
          return (
            <tr key={r.vehicle}>
              <td>
                <span className="flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full" style={{ background: c, boxShadow: `0 0 8px ${c}` }} />
                  <span className="num text-txt">V{r.vehicle}</span>
                  <span className="text-[11px] text-lbl">{r.stops.length} stops</span>
                </span>
              </td>
              {!compact && <td className="n max-w-[280px] truncate text-[11px] text-mute" title={r.stops.join(" → ")}>{r.stops.join(" → ")}</td>}
              <td className="n">
                <span className="flex items-center gap-2">
                  <span className="relative inline-block h-1 w-14 overflow-hidden rounded" style={{ background: "var(--line-2)" }} aria-hidden>
                    <span className="absolute inset-y-0 left-0 rounded" style={{ width: `${Math.min(100, load * 100)}%`, background: c }} />
                  </span>
                  {fmt(r.load)} / {fmt(r.capacity)}
                </span>
              </td>
              <td className="n">
                {minToHHMM(r.depart_min)} → {minToHHMM(r.return_min)}
              </td>
              <td className="n text-txt">{fmt(r.time_min, 1)}</td>
              <td className="n" style={{ color: "var(--amber)" }}>
                {fmt(r.congestion_delay_min, 1)}
              </td>
              <td className="n">{fmt(r.distance_km, 1)}</td>
              <td className="n">{fmt(r.co2_kg, 1)}</td>
            </tr>
          );
        })}
      </tbody>
    </DataTable>
  );
}
