import type { ResultJSON } from "../types/result";
import { fmt, minToHHMM } from "../lib/format";

export default function RouteTable({ routes }: { routes: ResultJSON["routes"] }) {
  if (!routes.length) return <div className="text-sm text-slate-500">No routes in this result.</div>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-500">
            <th className="py-2 pr-4">Veh</th>
            <th className="py-2 pr-4">Stops</th>
            <th className="py-2 pr-4">Load / Q</th>
            <th className="py-2 pr-4">Depart → Return</th>
            <th className="py-2 pr-4">Time (min)</th>
            <th className="py-2 pr-4">Delay (min)</th>
            <th className="py-2 pr-4">Km</th>
            <th className="py-2 pr-4">CO₂ (kg)</th>
          </tr>
        </thead>
        <tbody>
          {routes.map((r) => (
            <tr key={r.vehicle} className="border-b border-slate-100">
              <td className="py-2 pr-4">
                <span className="mr-2 inline-block h-3 w-3 rounded-full align-middle" style={{ background: r.color }} />
                {r.vehicle}
              </td>
              <td className="py-2 pr-4 font-mono text-xs">{r.stops.join(" → ")}</td>
              <td className="py-2 pr-4">
                {fmt(r.load)} / {fmt(r.capacity)}
              </td>
              <td className="py-2 pr-4">
                {minToHHMM(r.depart_min)} → {minToHHMM(r.return_min)}
              </td>
              <td className="py-2 pr-4">{fmt(r.time_min, 1)}</td>
              <td className="py-2 pr-4 text-amber-700">{fmt(r.congestion_delay_min, 1)}</td>
              <td className="py-2 pr-4">{fmt(r.distance_km, 1)}</td>
              <td className="py-2 pr-4">{fmt(r.co2_kg, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
