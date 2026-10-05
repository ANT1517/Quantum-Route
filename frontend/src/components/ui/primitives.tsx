// UI v3 primitives: Button, Chip, Panel, KpiCard, Segmented, Slider, Checkbox, Select, InfoTip, DataTable, Skeleton.
import { Info } from "lucide-react";
import { useId, useState, type ButtonHTMLAttributes, type CSSProperties, type ReactNode, type SelectHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "warn" | "ghost";

export function Button({
  variant = "secondary",
  size,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" }) {
  return <button type="button" className={`btn-${variant} ${size === "sm" ? "btn-sm" : ""} ${className}`} {...rest} />;
}

export type Tone = "teal" | "lime" | "amber" | "red" | "violet" | "plain";

export function Chip({ tone = "plain", children, title, className = "" }: { tone?: Tone; children: ReactNode; title?: string; className?: string }) {
  return (
    <span className={`chip ${tone !== "plain" ? `chip-${tone}` : ""} ${className}`} title={title}>
      {children}
    </span>
  );
}

/** "TRAFFIC 17:30 · SIMULATED" — every map/traffic view says the traffic is simulated. */
export function TrafficChip({ at }: { at?: number | null }) {
  const t = at != null && Number.isFinite(at) ? ((Math.round(at) % 1440) + 1440) % 1440 : null;
  const hhmm = t == null ? "" : `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")} `;
  return (
    <Chip tone="amber" title="Traffic is simulated (time-of-day load-ratio profiles + BPR), not live data.">
      TRAFFIC {hhmm}· SIMULATED
    </Chip>
  );
}

export function Panel({
  title,
  chips,
  meta,
  children,
  overlay = false,
  className = "",
  bodyClassName = "",
  id,
}: {
  title?: ReactNode;
  chips?: ReactNode;
  meta?: ReactNode;
  children: ReactNode;
  /** Header floats on a gradient over the content (maps). */
  overlay?: boolean;
  className?: string;
  bodyClassName?: string;
  id?: string;
}) {
  const head =
    title || chips || meta ? (
      <div
        className={`flex flex-wrap items-center gap-2 px-4 ${overlay ? "pointer-events-none absolute inset-x-0 top-0 z-[500] pb-6 pt-3" : "pb-2 pt-3"}`}
        style={overlay ? { background: "linear-gradient(180deg, rgba(6,8,10,.92) 0%, rgba(6,8,10,.6) 60%, transparent 100%)" } : undefined}
      >
        {title && <div className="micro text-txt2" style={{ color: "var(--txt-2)" }}>{title}</div>}
        {chips && <div className="pointer-events-auto flex flex-wrap items-center gap-1.5">{chips}</div>}
        {meta && <div className="pointer-events-auto ml-auto font-mono text-[10.5px] text-mute">{meta}</div>}
      </div>
    ) : null;
  return (
    <section id={id} className={`panel relative overflow-hidden ${className}`}>
      {head}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

export function KpiCard({
  label,
  value,
  unit,
  delta,
  context,
  tone,
  title,
}: {
  label: ReactNode;
  value: ReactNode;
  unit?: ReactNode;
  delta?: { text: ReactNode; tone: Tone };
  context?: ReactNode;
  tone?: "lime" | "teal" | "amber" | "red";
  title?: string;
}) {
  const color = tone ? `var(--${tone})` : "var(--txt)";
  return (
    <div className="qr-kpi px-4 py-3" title={title}>
      <div className="micro">{label}</div>
      <div className="mt-1.5 flex items-baseline gap-1.5">
        <span className="text-[30px] font-semibold leading-none tracking-[-0.02em] tabular-nums" style={{ color, textShadow: tone ? `0 0 18px var(--${tone})55` : undefined }}>
          {value}
        </span>
        {unit && <span className="text-[13px] text-mute">{unit}</span>}
      </div>
      {(delta || context) && (
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11.5px]">
          {delta && (
            <span className="num" style={{ color: delta.tone === "plain" ? "var(--mute)" : `var(--${delta.tone})` }}>
              {delta.text}
            </span>
          )}
          {context && <span className="text-mute">{context}</span>}
        </div>
      )}
    </div>
  );
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
  size,
}: {
  options: Array<[T, ReactNode]>;
  value: T;
  onChange: (v: T) => void;
  ariaLabel: string;
  size?: "sm";
}) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className="inline-flex flex-wrap gap-0.5 rounded-lg p-0.5" style={{ background: "var(--card-2)", border: "1px solid var(--line-2)" }}>
      {options.map(([v, l]) => {
        const on = v === value;
        return (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(v)}
            className={`rounded-md font-mono transition ${size === "sm" ? "px-2 py-1 text-[10.5px]" : "px-3 py-1.5 text-[11.5px]"}`}
            style={
              on
                ? { background: "rgba(79,227,209,.1)", color: "var(--teal)", boxShadow: "inset 0 0 0 1px rgba(79,227,209,.35), 0 0 12px rgba(79,227,209,.15)" }
                : { color: "var(--mute)" }
            }
          >
            {l}
          </button>
        );
      })}
    </div>
  );
}

export function Slider({
  value,
  min,
  max,
  step,
  onChange,
  fill,
  disabled,
  ariaLabel,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  fill?: string;
  disabled?: boolean;
  ariaLabel: string;
}) {
  const pct = `${((value - min) / Math.max(1e-9, max - min)) * 100}%`;
  return (
    <input
      type="range"
      className="qr-slider"
      aria-label={ariaLabel}
      min={min}
      max={max}
      step={step}
      value={value}
      disabled={disabled}
      style={{ "--pct": pct, "--fill": fill } as CSSProperties}
      onChange={(e) => onChange(Number(e.target.value))}
    />
  );
}

export function Checkbox({
  checked,
  onChange,
  children,
  title,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  children: ReactNode;
  title?: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 text-[12.5px] text-txt2" title={title}>
      <input type="checkbox" className="qr-check" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{children}</span>
    </label>
  );
}

export function Select({ className = "", ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`input ${className}`} {...rest} />;
}

/** Info icon with a dark tooltip card (hover and keyboard focus). */
export function InfoTip({ text, label = "More information" }: { text: string; label?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-label={`${label}: ${text}`}
        aria-describedby={open ? id : undefined}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full text-mute hover:text-teal"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        <Info size={13} strokeWidth={1.5} />
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute bottom-6 left-1/2 z-[1500] w-64 -translate-x-1/2 rounded-lg px-3 py-2 text-[11.5px] leading-snug text-txt2 shadow-2xl"
          style={{ background: "var(--card-2)", border: "1px solid var(--line-2)" }}
        >
          {text}
        </span>
      )}
    </span>
  );
}

export function DataTable({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="data-table">{children}</table>
    </div>
  );
}

export function Skeleton({ height = 16, className = "" }: { height?: number | string; className?: string }) {
  return <div className={`qr-skeleton ${className}`} style={{ height }} aria-hidden />;
}

export function FieldLabel({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-1.5 flex items-center justify-between">
      <span className="micro">{children}</span>
      {right && <span className="num text-[11px] text-txt2">{right}</span>}
    </div>
  );
}
