// Shared chart theme (UI v3 §6) + one global <defs> block (glow filter, teal gradients) referenced by url(#…).
import type { ReactNode } from "react";

export const GRID = "#12161B";
export const TICK = { fill: "#5A616B", fontSize: 9.5, fontFamily: "JetBrains Mono, ui-monospace, monospace" };
export const ANIM_MS = 400;

/** Mount once (Layout). userSpaceOnUse filter region so flat lines still glow. */
export function GlobalSvgDefs() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden focusable="false">
      <defs>
        <filter id="qr-glow" filterUnits="userSpaceOnUse" x="-2000" y="-2000" width="8000" height="8000">
          <feGaussianBlur stdDeviation="3.5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="qr-glow-soft" filterUnits="userSpaceOnUse" x="-2000" y="-2000" width="8000" height="8000">
          <feGaussianBlur stdDeviation="2" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <linearGradient id="qr-stroke-teal" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#1FA99A" />
          <stop offset="60%" stopColor="#4FE3D1" />
          <stop offset="100%" stopColor="#C9FFF7" />
        </linearGradient>
        <linearGradient id="qr-area-teal" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#4FE3D1" stopOpacity={0.45} />
          <stop offset="100%" stopColor="#4FE3D1" stopOpacity={0} />
        </linearGradient>
        <radialGradient id="qr-incident-grad">
          <stop offset="0%" stopColor="#FFB547" stopOpacity={0.38} />
          <stop offset="55%" stopColor="#FFB547" stopOpacity={0.14} />
          <stop offset="100%" stopColor="#FFB547" stopOpacity={0} />
        </radialGradient>
        <linearGradient id="qr-bar-teal" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7FF0E2" />
          <stop offset="100%" stopColor="#1FA99A" />
        </linearGradient>
      </defs>
    </svg>
  );
}

/** Dark tooltip card with mono values. */
export function TooltipCard({ title, rows }: { title?: ReactNode; rows: Array<{ k: ReactNode; v: ReactNode; color?: string }> }) {
  return (
    <div className="rounded-lg px-3 py-2 font-mono text-[11px] shadow-2xl" style={{ background: "var(--card-2)", border: "1px solid var(--line-2)" }}>
      {title && <div className="mb-1 text-[10px] uppercase tracking-[0.14em] text-lbl">{title}</div>}
      {rows.map((r, i) => (
        <div key={i} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-mute">
            {r.color && <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: r.color }} />}
            {r.k}
          </span>
          <span className="text-txt">{r.v}</span>
        </div>
      ))}
    </div>
  );
}
