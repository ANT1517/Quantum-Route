import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { dismiss, subscribeToasts, type Toast } from "../lib/toast";

const TONE: Record<string, string> = { error: "var(--red)", success: "var(--teal)", info: "var(--mute)" };

export default function Toasts() {
  const [items, setItems] = useState<Toast[]>([]);
  useEffect(() => subscribeToasts(setItems), []);
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[2000] flex w-80 flex-col gap-2">
      {items.map((t) => {
        const c = TONE[t.kind] ?? TONE.info;
        return (
          <div
            key={t.id}
            role="alert"
            className="qr-fade pointer-events-auto rounded-lg px-3.5 py-2.5 text-[12.5px] text-txt shadow-2xl"
            style={{ background: "var(--card-2)", border: "1px solid var(--line-2)", borderLeft: `2px solid ${c}`, boxShadow: `0 10px 30px rgba(0,0,0,.6), -4px 0 14px -6px ${c}` }}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="break-words">{t.message}</span>
              <button type="button" className="text-mute hover:text-txt" aria-label="Dismiss" onClick={() => dismiss(t.id)}>
                <X size={14} strokeWidth={1.5} />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
