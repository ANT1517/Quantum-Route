import type { ZoneIncident } from "../api/types";
import { hhmmToMin, minToHHMM } from "../lib/format";

export interface IncidentDraft {
  center: [number, number] | null;
  radius_m: number;
  factor: number;
  start_min: number;
  end_min: number;
}

export function defaultDraft(startMin = 1050): IncidentDraft {
  return { center: null, radius_m: 1500, factor: 3, start_min: startMin, end_min: startMin + 120 };
}

/**
 * Controlled drawer. The parent map's click handler sets `draft.center`.
 * Emits {type:"zone", center, radius_m, factor, start_min, end_min}.
 */
export default function IncidentDrawer({
  draft,
  onChange,
  onSubmit,
  onClose,
  busy,
}: {
  draft: IncidentDraft;
  onChange: (d: IncidentDraft) => void;
  onSubmit: (inc: ZoneIncident) => void;
  onClose: () => void;
  busy?: boolean;
}) {
  const valid = draft.center !== null && draft.end_min > draft.start_min && draft.factor >= 1;
  return (
    <div className="card border-red-200">
      <div className="mb-2 flex items-center justify-between">
        <div className="font-semibold text-red-700">Add incident zone</div>
        <button className="text-slate-400 hover:text-slate-700" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>
      <p className="mb-2 text-xs text-slate-500">
        Click the map to set the centre. Travel times inside the zone are multiplied by the factor during the window (simulated traffic).
      </p>
      <div className="mb-2 text-sm">
        Centre:{" "}
        {draft.center ? (
          <span className="font-mono">
            {draft.center[0].toFixed(4)}, {draft.center[1].toFixed(4)}
          </span>
        ) : (
          <span className="text-amber-700">click the map…</span>
        )}
      </div>
      <label className="label">Radius: {draft.radius_m} m</label>
      <input
        type="range"
        min={200}
        max={5000}
        step={100}
        value={draft.radius_m}
        className="w-full accent-red-600"
        onChange={(e) => onChange({ ...draft, radius_m: Number(e.target.value) })}
      />
      <label className="label mt-2">Slow-down factor: ×{draft.factor.toFixed(1)}</label>
      <input
        type="range"
        min={1}
        max={10}
        step={0.5}
        value={draft.factor}
        className="w-full accent-red-600"
        onChange={(e) => onChange({ ...draft, factor: Number(e.target.value) })}
      />
      <div className="mt-2 grid grid-cols-2 gap-2">
        <div>
          <label className="label">Start</label>
          <input type="time" className="input" value={minToHHMM(draft.start_min)} onChange={(e) => onChange({ ...draft, start_min: hhmmToMin(e.target.value) })} />
        </div>
        <div>
          <label className="label">End</label>
          <input type="time" className="input" value={minToHHMM(draft.end_min)} onChange={(e) => onChange({ ...draft, end_min: hhmmToMin(e.target.value) })} />
        </div>
      </div>
      {draft.end_min <= draft.start_min && <div className="mt-1 text-xs text-red-600">End must be after start.</div>}
      <button
        className="btn-danger mt-4 w-full justify-center"
        disabled={!valid || busy}
        onClick={() =>
          draft.center &&
          onSubmit({
            type: "zone",
            center: draft.center,
            radius_m: draft.radius_m,
            factor: draft.factor,
            start_min: draft.start_min,
            end_min: draft.end_min,
          })
        }
      >
        {busy ? "Re-optimizing…" : "Add incident & Re-optimize"}
      </button>
    </div>
  );
}
