import { AlertTriangle, Inbox, RotateCcw } from "lucide-react";
import type { ReactNode } from "react";
import { Skeleton } from "./ui/primitives";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="space-y-2 p-4" role="status" aria-live="polite">
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-mute">
        <span className="dot-live" />
        {label}
      </div>
      <Skeleton height={10} className="w-2/3" />
      <Skeleton height={10} className="w-1/2" />
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : String(error ?? "Unknown error");
  return (
    <div className="rounded-xl p-4 text-[13px]" role="alert" style={{ background: "rgba(255,122,122,.05)", border: "1px solid rgba(255,122,122,.3)" }}>
      <div className="flex items-center gap-2 font-semibold text-danger">
        <AlertTriangle size={15} strokeWidth={1.5} /> Something went wrong
      </div>
      <div className="mt-1 text-txt2">{msg}</div>
      {onRetry && (
        <button type="button" className="btn-secondary btn-sm mt-3" onClick={onRetry}>
          <RotateCcw size={13} strokeWidth={1.5} /> Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl p-8 text-center text-[13px] text-mute" style={{ border: "1px dashed var(--line-2)", background: "rgba(255,255,255,.01)" }}>
      <Inbox size={20} strokeWidth={1.5} className="mx-auto mb-2 text-lbl" />
      <div className="font-semibold text-txt2">{title}</div>
      {children && <div className="mt-2">{children}</div>}
    </div>
  );
}

interface QueryLike<T> {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  data: T | undefined;
  refetch: () => unknown;
}

/** Render loading / error / empty / success from a react-query result. */
export function QueryState<T>({
  q,
  isEmpty,
  empty,
  children,
  loadingLabel,
}: {
  q: QueryLike<T>;
  isEmpty?: (d: T) => boolean;
  empty?: ReactNode;
  loadingLabel?: string;
  children: (d: T) => ReactNode;
}) {
  if (q.isLoading) return <Loading label={loadingLabel} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  if (q.data === undefined || (isEmpty && isEmpty(q.data))) return <>{empty ?? <Empty title="No data" />}</>;
  return <>{children(q.data)}</>;
}

/** Shown whenever an id/label contains "MOCK" so placeholder data is never mistaken for results. */
export function MockBadge({ text }: { text?: string | null }) {
  if (!text || !/mock/i.test(text)) return null;
  return (
    <span className="chip chip-amber" title="Placeholder data, not a real result">
      MOCK DATA
    </span>
  );
}
