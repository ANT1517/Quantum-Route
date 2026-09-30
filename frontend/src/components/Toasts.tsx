import { useEffect, useState } from "react";
import { dismiss, subscribeToasts, type Toast } from "../lib/toast";

export default function Toasts() {
  const [items, setItems] = useState<Toast[]>([]);
  useEffect(() => subscribeToasts(setItems), []);
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[2000] flex w-80 flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          role="alert"
          className={`pointer-events-auto rounded-md px-4 py-2 text-sm shadow-lg ${
            t.kind === "error" ? "bg-red-600 text-white" : t.kind === "success" ? "bg-teal-600 text-white" : "bg-slate-800 text-white"
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <span className="break-words">{t.message}</span>
            <button className="opacity-80 hover:opacity-100" aria-label="Dismiss" onClick={() => dismiss(t.id)}>
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
