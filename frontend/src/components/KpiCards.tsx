import type { ResultJSON } from "../types/result";
import { fmt } from "../lib/format";

export default function KpiCards({ kpis, compact = false }: { kpis: ResultJSON["kpis"]; compact?: boolean }) {
  const items: Array<{ label: string; value: string; unit?: string; accent?: string }> = [
    { label: "Total time", value: fmt(kpis.total_time_min, 1), unit: "min" },
    { label: "Congestion delay", value: fmt(kpis.congestion_delay_min, 1), unit: "min", accent: "text-amber-600" },
    { label: "Distance", value: fmt(kpis.total_distance_km, 1), unit: "km" },
    { label: "CO₂ (illustrative)", value: fmt(kpis.co2_kg, 1), unit: "kg" },
    { label: "Vehicles", value: `${fmt(kpis.vehicles_used)}${kpis.fleet_limit != null ? ` / ${fmt(kpis.fleet_limit)}` : ""}` },
    { label: "Runtime", value: fmt(kpis.runtime_s, 2), unit: "s" },
  ];
  if (!compact) {
    items.push({ label: "Evaluations", value: fmt(kpis.evals) });
    items.push({ label: "Fitness F", value: fmt(kpis.fitness, 4) });
  }
  return (
    <div className={`grid gap-2 ${compact ? "grid-cols-2 sm:grid-cols-3" : "grid-cols-2"}`}>
      {items.map((it) => (
        <div key={it.label} className="rounded-md border border-slate-200 bg-white px-3 py-2">
          <div className="text-xs text-slate-500">{it.label}</div>
          <div className={`text-lg font-semibold ${it.accent ?? "text-slate-900"}`}>
            {it.value} {it.unit && <span className="text-xs font-normal text-slate-500">{it.unit}</span>}
          </div>
        </div>
      ))}
      {!kpis.feasible && (
        <div className="col-span-full rounded-md bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">Solution flagged infeasible</div>
      )}
    </div>
  );
}
