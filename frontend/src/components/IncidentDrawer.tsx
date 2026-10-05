import { MapPin, X } from "lucide-react";
import type { ZoneIncident } from "../api/types";
import { hhmmToMin, minToHHMM } from "../lib/format";
import { FieldLabel, Slider } from "./ui/primitives";

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
    <div className="rounded-xl p-4" style={{ background: "rgba(255,181,71,.035)", border: "1px solid rgba(255,181,71,.3)" }}>
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[13px] font-semibold text-amber">
          <span className="dot-live dot-amber" /> Add incident zone
        </div>
        <button type="button" className="btn-ghost btn-sm" onClick={onClose} aria-label="Close incident drawer">
          <X size={14} strokeWidth={1.5} />
        </button>
      </div>
      <p className="mb-3 text-[12px] leading-relaxed text-mute">
        Click the map to set the centre. Travel times inside the zone are multiplied by the factor during the window (simulated incident and traffic).
      </p>
      <div className="mb-3 flex items-center gap-2 text-[12.5px]">
        <MapPin size={14} strokeWidth={1.5} className="text-amber" />
        {draft.center ? (
          <span className="num text-txt">
            {draft.center[0].toFixed(4)}, {draft.center[1].toFixed(4)}
          </span>
        ) : (
          <span className="text-amber">click the map…</span>
        )}
      </div>
      <FieldLabel right={`${draft.radius_m} m`}>Radius</FieldLabel>
      <Slider ariaLabel="Incident radius in metres" min={200} max={5000} step={100} value={draft.radius_m} fill="var(--amber)" onChange={(v) => onChange({ ...draft, radius_m: v })} />
      <div className="mt-2" />
      <FieldLabel right={`×${draft.factor.toFixed(1)}`}>Slow-down factor</FieldLabel>
      <Slider ariaLabel="Incident slow-down factor" min={1} max={10} step={0.5} value={draft.factor} fill="var(--amber)" onChange={(v) => onChange({ ...draft, factor: v })} />
      <div className="mt-3 grid grid-cols-2 gap-2">
        <div>
          <label className="label" htmlFor="inc-start">
            Start
          </label>
          <input id="inc-start" type="time" className="input num" value={minToHHMM(draft.start_min)} onChange={(e) => onChange({ ...draft, start_min: hhmmToMin(e.target.value) })} />
        </div>
        <div>
          <label className="label" htmlFor="inc-end">
            End
          </label>
          <input id="inc-end" type="time" className="input num" value={minToHHMM(draft.end_min)} onChange={(e) => onChange({ ...draft, end_min: hhmmToMin(e.target.value) })} />
        </div>
      </div>
      {draft.end_min <= draft.start_min && <div className="mt-1 text-[12px] text-danger">End must be after start.</div>}
      <button
        type="button"
        className="btn-warn mt-4 w-full"
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
        {busy ? "Re-optimizing…" : "Add incident & re-optimize"}
      </button>
    </div>
  );
}
