// Right "Engine intelligence" column: title + blocks (uppercase label + content box) + decision log.
import { Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { clock, useEventLog } from "../../lib/eventLog";

export function InsightsColumn({ children, title = "Engine intelligence" }: { children: ReactNode; title?: string }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-[13px] font-semibold text-txt">
        <Sparkles size={15} strokeWidth={1.5} className="text-teal" style={{ filter: "drop-shadow(0 0 4px rgba(79,227,209,.7))" }} />
        {title}
        <span className="dot-live ml-auto" style={{ width: 6, height: 6 }} />
      </div>
      {children}
    </div>
  );
}

export function InsightBlock({ label, children, tone }: { label: ReactNode; children: ReactNode; tone?: "amber" | "teal" }) {
  return (
    <div>
      <div className="micro mb-1.5">{label}</div>
      <div
        className="box px-3 py-2.5 text-[12.5px] leading-relaxed text-txt2"
        style={tone ? { borderColor: tone === "amber" ? "rgba(255,181,71,.3)" : "rgba(79,227,209,.25)", background: tone === "amber" ? "rgba(255,181,71,.04)" : "rgba(79,227,209,.03)" } : undefined}
      >
        {children}
      </div>
    </div>
  );
}

/** Highlight a key phrase in teal / amber. */
export function Hi({ children, tone = "teal" }: { children: ReactNode; tone?: "teal" | "amber" | "lime" }) {
  return <span style={{ color: `var(--${tone})` }}>{children}</span>;
}

export function SignalRow({ k, v, tone }: { k: ReactNode; v: ReactNode; tone?: "teal" | "amber" | "lime" | "red" }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-0.5">
      <span className="text-mute">{k}</span>
      <span className="num text-right text-[12px]" style={{ color: tone ? `var(--${tone})` : "var(--txt)" }}>
        {v}
      </span>
    </div>
  );
}

/** Decision log: static lines from the result (data) followed by what happened in this session. */
export function DecisionLog({ lines = [] }: { lines?: Array<{ t?: string; text: ReactNode; tone?: "teal" | "amber" }> }) {
  const events = useEventLog();
  const all = [
    ...events.map((e) => ({ t: clock(e.at), text: e.text as ReactNode, tone: e.kind === "incident" || e.kind === "warn" ? ("amber" as const) : e.kind === "done" || e.kind === "reopt" ? ("teal" as const) : undefined })),
    ...lines,
  ];
  return (
    <div>
      <div className="micro mb-1.5">Decision log</div>
      <div className="box max-h-[260px] space-y-1.5 overflow-y-auto px-3 py-2.5 font-mono text-[10.5px] leading-relaxed">
        {all.length === 0 ? (
          <div className="text-lbl">No events yet.</div>
        ) : (
          all.map((l, i) => (
            <div key={i} className="flex gap-2">
              <span className="shrink-0 text-lbl">{l.t ?? "·"}</span>
              <span style={{ color: l.tone ? `var(--${l.tone})` : "var(--txt-2)" }}>{l.text}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
